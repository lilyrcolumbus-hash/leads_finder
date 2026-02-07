"""Craigslist scraper - Find businesses posting services or hiring."""

import re
import time
from typing import List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


# Major Craigslist city subdomains mapped to state
CRAIGSLIST_CITIES = {
    "Texas": ["dallas", "houston", "austin", "sanantonio"],
    "Florida": ["miami", "orlando", "tampa", "jacksonville"],
    "California": ["sfbay", "losangeles", "sandiego", "sacramento"],
    "New York": ["newyork", "buffalo", "albany"],
    "Illinois": ["chicago", "springfieldil"],
}


class CraigslistScraper(BaseScraper):
    """Scraper that searches Craigslist for business services and hiring."""

    source = LeadSource.CRAIGSLIST
    BASE_DOMAIN = "https://{city}.craigslist.org"

    SEARCH_SECTIONS = [
        "d/services/search/bbb",  # Business services
        "d/skilled-trades/search/skl",  # Skilled trades
    ]

    def __init__(self, locations: Optional[List[str]] = None, niches: Optional[List[str]] = None):
        super().__init__()
        self.locations = locations or settings.maps_locations
        self.niches = niches or settings.maps_niches
        self.client.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def scrape(self) -> LeadBatch:
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        self.logger.info(f"Starting Craigslist scrape for {len(self.locations)} locations")

        for location in self.locations:
            cities = CRAIGSLIST_CITIES.get(location, [])
            if not cities:
                continue

            # Only use first city per state to stay within limits
            city = cities[0]

            for niche in self.niches[:5]:  # Limit niches per city
                try:
                    leads = self._search_craigslist(city, niche, location)
                    all_leads.extend(leads)
                    self.logger.info(f"Craigslist: Found {len(leads)} results for '{niche}' in '{city}'")
                    time.sleep(2)
                except Exception as e:
                    error_msg = f"Craigslist error for '{niche}' in '{city}': {str(e)}"
                    self.logger.error(error_msg)
                    batch.errors.append(error_msg)

                if len(all_leads) >= settings.max_leads_per_source:
                    break
            if len(all_leads) >= settings.max_leads_per_source:
                break

        unique_leads = list({lead.id: lead for lead in all_leads}.values())
        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(f"Craigslist scrape complete: {batch.total_found} leads found")
        return batch

    def _search_craigslist(self, city: str, niche: str, location: str) -> List[Lead]:
        """Search Craigslist for business postings."""
        leads = []
        base_url = self.BASE_DOMAIN.format(city=city)

        for section in self.SEARCH_SECTIONS:
            url = f"{base_url}/{section}?query={quote(niche)}"
            try:
                response = self.fetch_url(url)
                soup = BeautifulSoup(response.text, "lxml")
                section_leads = self._parse_craigslist_results(soup, niche, location, city)
                leads.extend(section_leads)
                time.sleep(1)
            except Exception as e:
                self.logger.debug(f"Craigslist section search failed: {e}")

        if not leads:
            leads = self._fallback_search(niche, location)

        return leads

    def _parse_craigslist_results(self, soup: BeautifulSoup, niche: str, location: str, city: str) -> List[Lead]:
        """Parse Craigslist search results."""
        leads = []

        # Craigslist listing rows
        rows = soup.select(
            'li.cl-static-search-result, '
            'li.result-row, '
            'div.result-info'
        )

        if not rows:
            return self._extract_from_raw(soup, niche, location, city)

        for row in rows[:20]:
            try:
                # Title and link
                title_el = row.select_one(
                    'div.title, '
                    'a.titlestring, '
                    'a.result-title'
                )
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                if not title:
                    continue

                href = ""
                link_el = title_el if title_el.name == "a" else title_el.find("a")
                if link_el:
                    href = link_el.get("href", "")

                post_url = href
                if href.startswith("/"):
                    post_url = f"https://{city}.craigslist.org{href}"

                # Price (may indicate business)
                price_el = row.select_one('span.priceinfo, span.result-price')
                price = price_el.get_text(strip=True) if price_el else ""

                # Location
                loc_el = row.select_one('span.result-hood, span.nearby')
                post_location = loc_el.get_text(strip=True) if loc_el else location

                # Extract phone from title/content
                full_text = row.get_text()
                phone = self._extract_phone(full_text)

                lead = Lead(
                    id=self.generate_id("cl", title, city),
                    source=self.source,
                    title=title[:100],
                    content=f"Craigslist {niche} posting in {city}. {price} {post_location}",
                    url=post_url,
                    phone=phone,
                    niche=niche,
                    location=location,
                    keywords_matched=[niche, location],
                )
                leads.append(lead)
            except Exception as e:
                self.logger.debug(f"Error parsing Craigslist row: {e}")

        return leads

    def _extract_from_raw(self, soup: BeautifulSoup, niche: str, location: str, city: str) -> List[Lead]:
        """Extract from raw HTML."""
        leads = []

        for link in soup.find_all("a", href=re.compile(r"\d{10}\.html")):
            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            href = link.get("href", "")
            post_url = href if href.startswith("http") else f"https://{city}.craigslist.org{href}"

            lead = Lead(
                id=self.generate_id("cl_raw", title, city),
                source=self.source,
                title=title[:100],
                content=f"Craigslist posting for {niche} in {location}",
                url=post_url,
                niche=niche,
                location=location,
                keywords_matched=[niche, location],
            )
            leads.append(lead)

        return leads

    def _fallback_search(self, niche: str, location: str) -> List[Lead]:
        """Use Google to find Craigslist listings."""
        leads = []
        query = f'site:craigslist.org "{niche}" "{location}"'

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

                lead = Lead(
                    id=self.generate_id("cl_g", title, location),
                    source=self.source,
                    title=title[:100],
                    content=snippet,
                    url=link,
                    niche=niche,
                    location=location,
                    keywords_matched=[niche, location],
                )
                leads.append(lead)
        except Exception as e:
            self.logger.debug(f"Craigslist fallback failed: {e}")

        return leads

    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text."""
        pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        match = re.search(pattern, text)
        return match.group(0) if match else None
