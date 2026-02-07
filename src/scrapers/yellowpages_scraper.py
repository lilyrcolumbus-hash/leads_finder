"""Yellow Pages scraper - Extract business leads from yellowpages.com."""

import re
import time
from typing import List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class YellowPagesScraper(BaseScraper):
    """Scraper that searches Yellow Pages for local businesses."""

    source = LeadSource.YELLOW_PAGES
    BASE_URL = "https://www.yellowpages.com/search"

    def __init__(self, niches: Optional[List[str]] = None, locations: Optional[List[str]] = None):
        super().__init__()
        self.niches = niches or settings.maps_niches
        self.locations = locations or settings.maps_locations
        self.client.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def scrape(self) -> LeadBatch:
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        self.logger.info(f"Starting Yellow Pages scrape: {len(self.niches)} niches x {len(self.locations)} locations")

        for niche in self.niches:
            for location in self.locations:
                try:
                    leads = self._search_yp(niche, location)
                    all_leads.extend(leads)
                    self.logger.info(f"YP: Found {len(leads)} results for '{niche}' in '{location}'")
                    time.sleep(2)
                except Exception as e:
                    error_msg = f"YP error for '{niche}' in '{location}': {str(e)}"
                    self.logger.error(error_msg)
                    batch.errors.append(error_msg)

                if len(all_leads) >= settings.max_leads_per_source:
                    break
            if len(all_leads) >= settings.max_leads_per_source:
                break

        unique_leads = list({lead.id: lead for lead in all_leads}.values())
        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(f"Yellow Pages scrape complete: {batch.total_found} leads found")
        return batch

    def _search_yp(self, niche: str, location: str) -> List[Lead]:
        """Search Yellow Pages for businesses."""
        leads = []
        url = f"{self.BASE_URL}?search_terms={quote(niche)}&geo_location_terms={quote(location)}"

        try:
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.text, "lxml")
            leads = self._parse_yp_results(soup, niche, location)
        except Exception as e:
            self.logger.debug(f"YP search failed: {e}")
            leads = self._fallback_search(niche, location)

        return leads

    def _parse_yp_results(self, soup: BeautifulSoup, niche: str, location: str) -> List[Lead]:
        """Parse Yellow Pages search results."""
        leads = []

        # Yellow Pages listing containers
        listings = soup.select(
            'div.result, '
            'div.search-results div.info, '
            'div.v-card'
        )

        if not listings:
            return self._extract_from_raw(soup, niche, location)

        for listing in listings:
            try:
                # Business name
                name_el = listing.select_one(
                    'a.business-name, '
                    'h2.n a, '
                    'a.listing-name'
                )
                if not name_el:
                    continue

                name = name_el.get_text(strip=True)
                href = name_el.get("href", "")
                biz_url = f"https://www.yellowpages.com{href}" if href.startswith("/") else href

                # Phone
                phone_el = listing.select_one(
                    'div.phones, '
                    'div.phone, '
                    'a[href^="tel:"]'
                )
                phone = phone_el.get_text(strip=True) if phone_el else None

                # Address
                address_el = listing.select_one(
                    'div.adr, '
                    'p.adr, '
                    'div.street-address'
                )
                address = address_el.get_text(strip=True) if address_el else None

                # Website
                website_el = listing.select_one('a.track-visit-website, a[href*="website"]')
                website = website_el.get("href") if website_el else None

                # Categories
                cat_el = listing.select_one('div.categories, div.links')
                categories = cat_el.get_text(strip=True) if cat_el else ""

                lead = Lead(
                    id=self.generate_id("yp", name, location),
                    source=self.source,
                    title=name,
                    content=f"{niche} in {location}. {categories}. {address or ''}",
                    url=biz_url,
                    company=name,
                    phone=phone,
                    website=website,
                    address=address,
                    niche=niche,
                    location=location,
                    keywords_matched=[niche, location],
                )
                leads.append(lead)
            except Exception as e:
                self.logger.debug(f"Error parsing YP listing: {e}")

        return leads

    def _extract_from_raw(self, soup: BeautifulSoup, niche: str, location: str) -> List[Lead]:
        """Extract from raw HTML."""
        leads = []
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'

        for link in soup.find_all("a", href=re.compile(r"/mip/")):
            name = link.get_text(strip=True)
            if not name or len(name) < 3:
                continue

            href = link.get("href", "")
            biz_url = f"https://www.yellowpages.com{href}" if href.startswith("/") else href

            # Try to find phone near the link
            parent = link.find_parent("div")
            phone = None
            if parent:
                phone_match = re.search(phone_pattern, parent.get_text())
                phone = phone_match.group(0) if phone_match else None

            lead = Lead(
                id=self.generate_id("yp_raw", name, location),
                source=self.source,
                title=name,
                content=f"{niche} in {location}",
                url=biz_url,
                company=name,
                phone=phone,
                niche=niche,
                location=location,
                keywords_matched=[niche, location],
            )
            leads.append(lead)

        return leads

    def _fallback_search(self, niche: str, location: str) -> List[Lead]:
        """Use Google to find Yellow Pages listings."""
        leads = []
        query = f'site:yellowpages.com "{niche}" "{location}"'

        try:
            url = f"https://www.google.com/search?q={quote(query)}&num=10"
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.text, "lxml")

            for result in soup.select("div.g"):
                title_el = result.select_one("h3")
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                link_el = result.select_one("a")
                link = link_el.get("href", "") if link_el else ""
                snippet_el = result.select_one("div.VwiC3b")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', snippet)

                lead = Lead(
                    id=self.generate_id("yp_g", title, location),
                    source=self.source,
                    title=title.replace(" | Yellow Pages", "").strip(),
                    content=snippet,
                    url=link,
                    company=title.split(" - ")[0].strip() if " - " in title else title,
                    phone=phone_match.group(0) if phone_match else None,
                    niche=niche,
                    location=location,
                    keywords_matched=[niche, location],
                )
                leads.append(lead)
        except Exception as e:
            self.logger.debug(f"YP fallback failed: {e}")

        return leads
