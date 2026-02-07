"""Yelp scraper - Extract business leads from Yelp listings."""

import re
import time
from typing import List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class YelpScraper(BaseScraper):
    """Scraper that searches Yelp for local businesses."""

    source = LeadSource.YELP
    BASE_URL = "https://www.yelp.com/search"

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

        self.logger.info(f"Starting Yelp scrape: {len(self.niches)} niches x {len(self.locations)} locations")

        for niche in self.niches:
            for location in self.locations:
                try:
                    leads = self._search_yelp(niche, location)
                    all_leads.extend(leads)
                    self.logger.info(f"Yelp: Found {len(leads)} results for '{niche}' in '{location}'")
                    time.sleep(2)
                except Exception as e:
                    error_msg = f"Yelp error for '{niche}' in '{location}': {str(e)}"
                    self.logger.error(error_msg)
                    batch.errors.append(error_msg)

                if len(all_leads) >= settings.max_leads_per_source:
                    break
            if len(all_leads) >= settings.max_leads_per_source:
                break

        unique_leads = list({lead.id: lead for lead in all_leads}.values())
        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(f"Yelp scrape complete: {batch.total_found} leads found")
        return batch

    def _search_yelp(self, niche: str, location: str) -> List[Lead]:
        """Search Yelp for businesses."""
        leads = []
        url = f"{self.BASE_URL}?find_desc={quote(niche)}&find_loc={quote(location)}"

        try:
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.text, "lxml")
            leads = self._parse_yelp_results(soup, niche, location)
        except Exception as e:
            self.logger.debug(f"Yelp search failed: {e}")
            # Fallback via Google
            leads = self._fallback_search(niche, location)

        return leads

    def _parse_yelp_results(self, soup: BeautifulSoup, niche: str, location: str) -> List[Lead]:
        """Parse Yelp search results page."""
        leads = []

        # Yelp uses various container classes for business listings
        containers = soup.select(
            '[data-testid="serp-ia-card"], '
            'div.container__09f24__FeTO6, '
            'div.arrange-unit__09f24__rqHTg, '
            'li.border-color--default__09f24__NPAKY'
        )

        if not containers:
            # Try to extract from JSON-LD
            leads = self._extract_from_jsonld(soup, niche, location)
            if not leads:
                leads = self._extract_from_raw(soup, niche, location)
            return leads

        for container in containers:
            try:
                # Business name
                name_el = container.select_one(
                    'a.css-19v1rkv, '
                    'h3 a, '
                    'a[href*="/biz/"]'
                )
                if not name_el:
                    continue

                name = name_el.get_text(strip=True)
                href = name_el.get("href", "")
                biz_url = f"https://www.yelp.com{href}" if href.startswith("/") else href

                # Phone
                phone = self._extract_phone_from_container(container)

                # Address
                address_el = container.select_one(
                    'address, '
                    'span.css-chan6m, '
                    'p.css-chan6m'
                )
                address = address_el.get_text(strip=True) if address_el else None

                # Rating
                rating_el = container.select_one('[aria-label*="star"]')
                rating = rating_el.get("aria-label", "") if rating_el else ""

                lead = Lead(
                    id=self.generate_id("yelp", name, location),
                    source=self.source,
                    title=name,
                    content=f"{niche} in {location}. {rating}. {address or ''}",
                    url=biz_url,
                    company=name,
                    phone=phone,
                    address=address,
                    niche=niche,
                    location=location,
                    keywords_matched=[niche, location],
                )
                leads.append(lead)
            except Exception as e:
                self.logger.debug(f"Error parsing Yelp result: {e}")

        return leads

    def _extract_from_jsonld(self, soup: BeautifulSoup, niche: str, location: str) -> List[Lead]:
        """Extract business data from JSON-LD script tags."""
        import json
        leads = []

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    for item in data:
                        lead = self._jsonld_to_lead(item, niche, location)
                        if lead:
                            leads.append(lead)
                elif isinstance(data, dict):
                    if data.get("@type") == "LocalBusiness":
                        lead = self._jsonld_to_lead(data, niche, location)
                        if lead:
                            leads.append(lead)
            except (json.JSONDecodeError, TypeError):
                continue

        return leads

    def _jsonld_to_lead(self, data: dict, niche: str, location: str) -> Optional[Lead]:
        """Convert JSON-LD data to Lead."""
        name = data.get("name")
        if not name:
            return None

        address_data = data.get("address", {})
        address = None
        if address_data:
            parts = [
                address_data.get("streetAddress", ""),
                address_data.get("addressLocality", ""),
                address_data.get("addressRegion", ""),
            ]
            address = ", ".join(p for p in parts if p)

        return Lead(
            id=self.generate_id("yelp", name, location),
            source=self.source,
            title=name,
            content=f"{niche} in {location}. {address or ''}",
            url=data.get("url", f"https://www.yelp.com/search?find_desc={quote(name)}"),
            company=name,
            phone=data.get("telephone"),
            website=data.get("url"),
            address=address,
            niche=niche,
            location=location,
            keywords_matched=[niche, location],
        )

    def _extract_from_raw(self, soup: BeautifulSoup, niche: str, location: str) -> List[Lead]:
        """Extract from raw HTML as last resort."""
        leads = []
        # Find all links to business pages
        for link in soup.find_all("a", href=re.compile(r"/biz/")):
            name = link.get_text(strip=True)
            if not name or len(name) < 3 or len(name) > 80:
                continue

            href = link.get("href", "")
            biz_url = f"https://www.yelp.com{href}" if href.startswith("/") else href

            lead = Lead(
                id=self.generate_id("yelp", name, location),
                source=self.source,
                title=name,
                content=f"{niche} in {location}",
                url=biz_url,
                company=name,
                niche=niche,
                location=location,
                keywords_matched=[niche, location],
            )
            leads.append(lead)

        return leads

    def _fallback_search(self, niche: str, location: str) -> List[Lead]:
        """Use Google to find Yelp listings."""
        leads = []
        query = f'site:yelp.com "{niche}" "{location}"'

        try:
            url = f"https://www.google.com/search?q={quote(query)}&num=10"
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.text, "lxml")

            for result in soup.select("div.g, div.tF2Cxc"):
                title_el = result.select_one("h3")
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                link_el = result.select_one("a")
                link = link_el.get("href", "") if link_el else ""
                snippet_el = result.select_one("div.VwiC3b")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                phone = self._extract_phone(f"{title} {snippet}")

                lead = Lead(
                    id=self.generate_id("yelp_g", title, location),
                    source=self.source,
                    title=title,
                    content=snippet,
                    url=link,
                    company=title.replace(" - Yelp", "").strip(),
                    phone=phone,
                    niche=niche,
                    location=location,
                    keywords_matched=[niche, location],
                )
                leads.append(lead)
        except Exception as e:
            self.logger.debug(f"Yelp fallback search failed: {e}")

        return leads

    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text."""
        pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        match = re.search(pattern, text)
        return match.group(0) if match else None

    def _extract_phone_from_container(self, container) -> Optional[str]:
        """Extract phone from a container element."""
        text = container.get_text()
        return self._extract_phone(text)
