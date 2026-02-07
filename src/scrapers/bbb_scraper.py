"""BBB (Better Business Bureau) scraper - Extract business leads from bbb.org."""

import re
import time
from typing import List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class BBBScraper(BaseScraper):
    """Scraper that searches Better Business Bureau for businesses."""

    source = LeadSource.BBB
    BASE_URL = "https://www.bbb.org/search"

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

        self.logger.info(f"Starting BBB scrape: {len(self.niches)} niches x {len(self.locations)} locations")

        for niche in self.niches:
            for location in self.locations:
                try:
                    leads = self._search_bbb(niche, location)
                    all_leads.extend(leads)
                    self.logger.info(f"BBB: Found {len(leads)} results for '{niche}' in '{location}'")
                    time.sleep(2)
                except Exception as e:
                    error_msg = f"BBB error for '{niche}' in '{location}': {str(e)}"
                    self.logger.error(error_msg)
                    batch.errors.append(error_msg)

                if len(all_leads) >= settings.max_leads_per_source:
                    break
            if len(all_leads) >= settings.max_leads_per_source:
                break

        unique_leads = list({lead.id: lead for lead in all_leads}.values())
        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(f"BBB scrape complete: {batch.total_found} leads found")
        return batch

    def _search_bbb(self, niche: str, location: str) -> List[Lead]:
        """Search BBB for businesses."""
        leads = []
        url = f"{self.BASE_URL}?find_country=US&find_text={quote(niche)}&find_loc={quote(location)}&find_type=Category"

        try:
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.text, "lxml")
            leads = self._parse_bbb_results(soup, niche, location)
        except Exception as e:
            self.logger.debug(f"BBB search failed: {e}")
            leads = self._fallback_search(niche, location)

        return leads

    def _parse_bbb_results(self, soup: BeautifulSoup, niche: str, location: str) -> List[Lead]:
        """Parse BBB search results."""
        leads = []

        # BBB listing containers
        listings = soup.select(
            'div.bds-listing, '
            'div.result-item, '
            'a.listing-link'
        )

        if not listings:
            return self._extract_from_raw(soup, niche, location)

        for listing in listings:
            try:
                # Business name
                name_el = listing.select_one(
                    'h3.listing-name, '
                    'span.listing-name, '
                    'h3 a'
                )
                if not name_el:
                    continue

                name = name_el.get_text(strip=True)
                href_el = listing.select_one("a[href]")
                href = href_el.get("href", "") if href_el else ""
                biz_url = f"https://www.bbb.org{href}" if href.startswith("/") else href

                # Phone
                phone_el = listing.select_one(
                    'a[href^="tel:"], '
                    'span.listing-phone'
                )
                phone = phone_el.get_text(strip=True) if phone_el else None

                # Address
                address_el = listing.select_one(
                    'p.listing-address, '
                    'div.listing-address'
                )
                address = address_el.get_text(strip=True) if address_el else None

                # Rating
                rating_el = listing.select_one('span.rating-text, span.bds-rating')
                rating = rating_el.get_text(strip=True) if rating_el else ""

                lead = Lead(
                    id=self.generate_id("bbb", name, location),
                    source=self.source,
                    title=name,
                    content=f"{niche} in {location}. BBB Rating: {rating}. {address or ''}",
                    url=biz_url,
                    company=name,
                    phone=phone,
                    address=address,
                    niche=niche,
                    location=location,
                    keywords_matched=[niche, location, "bbb_listed"],
                )
                leads.append(lead)
            except Exception as e:
                self.logger.debug(f"Error parsing BBB listing: {e}")

        return leads

    def _extract_from_raw(self, soup: BeautifulSoup, niche: str, location: str) -> List[Lead]:
        """Extract from raw HTML."""
        leads = []

        for link in soup.find_all("a", href=re.compile(r"/profile/")):
            name = link.get_text(strip=True)
            if not name or len(name) < 3 or len(name) > 100:
                continue

            href = link.get("href", "")
            biz_url = f"https://www.bbb.org{href}" if href.startswith("/") else href

            lead = Lead(
                id=self.generate_id("bbb_raw", name, location),
                source=self.source,
                title=name,
                content=f"{niche} in {location}. BBB listed.",
                url=biz_url,
                company=name,
                niche=niche,
                location=location,
                keywords_matched=[niche, location, "bbb_listed"],
            )
            leads.append(lead)

        return leads

    def _fallback_search(self, niche: str, location: str) -> List[Lead]:
        """Use Google to find BBB listings."""
        leads = []
        query = f'site:bbb.org "{niche}" "{location}"'

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
                    id=self.generate_id("bbb_g", title, location),
                    source=self.source,
                    title=title.replace(" | Better Business Bureau", "").strip(),
                    content=snippet,
                    url=link,
                    company=title.split(" | ")[0].strip() if " | " in title else title,
                    phone=phone_match.group(0) if phone_match else None,
                    niche=niche,
                    location=location,
                    keywords_matched=[niche, location, "bbb_listed"],
                )
                leads.append(lead)
        except Exception as e:
            self.logger.debug(f"BBB fallback failed: {e}")

        return leads
