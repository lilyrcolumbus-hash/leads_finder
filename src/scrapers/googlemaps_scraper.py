"""Google Maps scraper - Extract business leads by niche and location."""

import re
import time
from typing import List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class GoogleMapsScraper(BaseScraper):
    """Scraper that searches Google Maps for local businesses."""

    source = LeadSource.GOOGLE_MAPS
    SEARCH_URL = "https://www.google.com/maps/search/{query}"

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

        self.logger.info(f"Starting Google Maps scrape: {len(self.niches)} niches x {len(self.locations)} locations")

        for niche in self.niches:
            for location in self.locations:
                try:
                    leads = self._search_maps(niche, location)
                    all_leads.extend(leads)
                    self.logger.info(f"Found {len(leads)} results for '{niche}' in '{location}'")
                    time.sleep(2)  # Rate limiting
                except Exception as e:
                    error_msg = f"Error searching '{niche}' in '{location}': {str(e)}"
                    self.logger.error(error_msg)
                    batch.errors.append(error_msg)

                if len(all_leads) >= settings.max_leads_per_source:
                    break
            if len(all_leads) >= settings.max_leads_per_source:
                break

        # Deduplicate
        unique_leads = list({lead.id: lead for lead in all_leads}.values())
        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(f"Google Maps scrape complete: {batch.total_found} leads found")
        return batch

    def _search_maps(self, niche: str, location: str) -> List[Lead]:
        """Search Google Maps for businesses."""
        leads = []
        query = f"{niche} in {location}"
        url = self.SEARCH_URL.format(query=quote(query))

        try:
            response = self.fetch_url(url)
            html = response.text

            # Extract business data from Google Maps HTML
            leads = self._parse_maps_html(html, niche, location)
        except Exception as e:
            self.logger.debug(f"Maps search failed for '{query}': {e}")
            # Fallback: use Google search to find maps listings
            leads = self._fallback_google_search(niche, location)

        return leads

    def _parse_maps_html(self, html: str, niche: str, location: str) -> List[Lead]:
        """Parse Google Maps HTML to extract business info."""
        leads = []
        soup = BeautifulSoup(html, "lxml")

        # Extract business names, addresses, phones from maps results
        # Google Maps uses dynamic JS, so we parse what's available in initial HTML
        business_blocks = soup.find_all("div", class_=re.compile(r"Nv2PK|THOPZb|lI9IFe"))

        if not business_blocks:
            # Try alternative patterns in the raw HTML
            leads = self._extract_from_raw_html(html, niche, location)
            return leads

        for block in business_blocks:
            try:
                name = self._extract_text(block, ["span.OSrXXb", "span.NkKgQb", "div.qBF1Pd"])
                if not name:
                    continue

                address = self._extract_text(block, ["span.W4Efsd:last-child", "div.W4Efsd"])
                phone = self._extract_phone_from_block(block)
                website = self._extract_website_from_block(block)

                lead = Lead(
                    id=self.generate_id("gmaps", name, location),
                    source=self.source,
                    title=name,
                    content=f"{niche} business in {location}. {address or ''}",
                    url=f"https://www.google.com/maps/search/{quote(f'{name} {location}')}",
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
                self.logger.debug(f"Error parsing maps block: {e}")

        return leads

    def _extract_from_raw_html(self, html: str, niche: str, location: str) -> List[Lead]:
        """Extract business data from raw HTML using regex patterns."""
        leads = []

        # Phone numbers
        phone_pattern = r'\(\d{3}\)\s*\d{3}[-.]?\d{4}|\d{3}[-.]?\d{3}[-.]?\d{4}'
        # Website URLs in maps results
        url_pattern = r'https?://(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})(?:/[^\s"\'<>]*)?'

        # Try to find structured data in JSON-LD or embedded data
        # Google Maps embeds business data in script tags
        name_pattern = r'\["([^"]{3,50})",\s*"[^"]*",\s*\[[\d.-]+,\s*[\d.-]+\]'
        names_found = re.findall(name_pattern, html)

        phones_found = re.findall(phone_pattern, html)
        urls_found = re.findall(url_pattern, html)

        # Filter junk domains
        clean_domains = [d for d in urls_found if not any(junk in d for junk in settings.junk_domains)]

        # Create leads from whatever data we found
        seen = set()
        for i, name in enumerate(names_found[:20]):
            if name.lower() in seen or len(name) < 3:
                continue
            seen.add(name.lower())

            phone = phones_found[i] if i < len(phones_found) else None
            domain = clean_domains[i] if i < len(clean_domains) else None

            lead = Lead(
                id=self.generate_id("gmaps", name, location),
                source=self.source,
                title=name,
                content=f"{niche} business in {location}",
                url=f"https://www.google.com/maps/search/{quote(f'{name} {location}')}",
                company=name,
                phone=phone,
                website=f"https://{domain}" if domain else None,
                niche=niche,
                location=location,
                keywords_matched=[niche, location],
            )
            leads.append(lead)

        return leads

    def _fallback_google_search(self, niche: str, location: str) -> List[Lead]:
        """Use regular Google search as fallback to find business listings."""
        leads = []
        query = f'site:google.com/maps "{niche}" "{location}"'

        try:
            url = (
                f"https://www.google.com/search"
                f"?q={quote(query)}"
                f"&num=10"
            )
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.text, "lxml")

            for result in soup.select("div.g, div.tF2Cxc"):
                title_el = result.select_one("h3")
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                snippet_el = result.select_one("div.VwiC3b, span.aCOpRe")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                link_el = result.select_one("a")
                link = link_el.get("href", "") if link_el else ""

                phone = self._extract_phone(f"{title} {snippet}")

                lead = Lead(
                    id=self.generate_id("gmaps_fallback", title, location),
                    source=self.source,
                    title=title,
                    content=snippet,
                    url=link,
                    company=title,
                    phone=phone,
                    niche=niche,
                    location=location,
                    keywords_matched=[niche, location],
                )
                leads.append(lead)
        except Exception as e:
            self.logger.debug(f"Fallback search failed: {e}")

        return leads

    def _extract_text(self, block, selectors: List[str]) -> Optional[str]:
        """Try multiple CSS selectors to extract text."""
        for selector in selectors:
            el = block.select_one(selector)
            if el:
                return el.get_text(strip=True)
        return None

    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text."""
        pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        match = re.search(pattern, text)
        return match.group(0) if match else None

    def _extract_phone_from_block(self, block) -> Optional[str]:
        """Extract phone number from a BeautifulSoup block."""
        text = block.get_text()
        return self._extract_phone(text)

    def _extract_website_from_block(self, block) -> Optional[str]:
        """Extract website URL from a BeautifulSoup block."""
        for a in block.find_all("a", href=True):
            href = a["href"]
            if "google.com" not in href and "maps" not in href and href.startswith("http"):
                return href
        return None
