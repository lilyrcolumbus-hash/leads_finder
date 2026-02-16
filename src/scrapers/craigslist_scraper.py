"""Craigslist scraper for finding businesses offering services."""

import time
import re
from typing import List
from bs4 import BeautifulSoup

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class CraigslistScraper(BaseScraper):
    """Scraper for Craigslist - finds businesses offering services (potential clients)."""

    source = LeadSource.CRAIGSLIST

    # Craigslist cities
    CITIES = [
        "miami",
        "houston",
        "phoenix",
        "losangeles",
        "chicago",
        "atlanta",
        "dallas",
        "denver",
        "seattle",
        "boston"
    ]

    # Service categories to search (these are business owners!)
    SERVICE_CATEGORIES = [
        "hvac",
        "plumbing",
        "electrical",
        "roofing",
        "landscaping",
        "cleaning",
        "painting",
        "moving",
        "handyman",
        "automotive"
    ]

    def __init__(self):
        super().__init__()

    def scrape(self, time_filter: str = None, location: str = None) -> LeadBatch:
        """
        Scrape Craigslist services section for businesses.

        Args:
            time_filter: Not used
            location: Optional specific city

        Returns:
            LeadBatch with found leads
        """
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        cities = [location] if location else self.CITIES[:5]
        categories = self.SERVICE_CATEGORIES[:6]

        self.logger.info(f"Starting Craigslist scrape for {len(categories)} service types")

        for city in cities:
            for category in categories:
                try:
                    leads = self._search_services(city, category)
                    all_leads.extend(leads)
                    self.logger.info(f"Found {len(leads)} {category} services in {city}")
                    time.sleep(3)  # Craigslist is strict about rate limiting
                except Exception as e:
                    error_msg = f"Error searching {category} in {city}: {str(e)}"
                    self.logger.warning(error_msg)
                    batch.errors.append(error_msg)

        # Deduplicate
        unique_leads = list({lead.id: lead for lead in all_leads}.values())

        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(f"Craigslist scrape complete: {batch.total_found} service providers found")
        return batch

    def _search_services(self, city: str, category: str) -> List[Lead]:
        """Search Craigslist services in a city."""
        leads = []

        # Craigslist URL format for services
        url = f"https://{city}.craigslist.org/search/bbs?query={category}"

        try:
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find listings
            listings = soup.find_all('li', class_='result-row') or \
                       soup.find_all('div', class_='result-row') or \
                       soup.find_all('li', class_='cl-static-search-result')

            for listing in listings[:15]:
                lead = self._parse_listing(listing, city, category)
                if lead:
                    leads.append(lead)

        except Exception as e:
            self.logger.debug(f"Craigslist search failed for {city}/{category}: {e}")

        return leads

    def _parse_listing(self, listing, city: str, category: str) -> Lead | None:
        """Parse a Craigslist listing."""
        try:
            # Extract title
            title_elem = listing.find('a', class_='result-title') or \
                         listing.find('a', class_='titlestring') or \
                         listing.find('a')

            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            if not title or len(title) < 5:
                return None

            # Get URL
            url = title_elem.get('href', '')
            if not url.startswith('http'):
                url = f"https://{city}.craigslist.org{url}"

            # Extract location/neighborhood
            location_elem = listing.find('span', class_='result-hood') or \
                           listing.find('span', class_='nearby')
            location_text = location_elem.get_text(strip=True) if location_elem else city

            # Extract price (some service listings have prices)
            price = None
            price_elem = listing.find('span', class_='result-price')
            if price_elem:
                price = price_elem.get_text(strip=True)

            # Try to get more details from the listing page
            phone = None
            content = f"{category.title()} service in {city}. {title}"

            # Check for urgency/pain indicators in title
            pain_indicators = ['urgent', 'asap', 'immediate', 'help', 'needed', 'emergency',
                              'same day', 'available now', 'call now', 'free estimate']
            has_pain = any(indicator in title.lower() for indicator in pain_indicators)

            # Extract phone from title if present
            phone_match = re.search(r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})', title)
            if phone_match:
                phone = phone_match.group(1)

            lead = Lead(
                id=self.generate_id("cl", url),
                source=self.source,
                title=title,
                content=content,
                url=url,
                phone=phone,
                location=location_text.strip('() '),
                business_type=category,
                keywords_matched=["urgent"] if has_pain else [],
                has_pain=has_pain
            )

            return lead

        except Exception as e:
            self.logger.debug(f"Error parsing CL listing: {e}")
            return None
