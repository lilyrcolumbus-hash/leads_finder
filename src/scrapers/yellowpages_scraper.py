"""Yellow Pages scraper for finding local businesses."""

import time
import re
from typing import List
from bs4 import BeautifulSoup

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class YellowPagesScraper(BaseScraper):
    """Scraper for Yellow Pages business directory."""

    source = LeadSource.GOOGLE_MAPS  # Using same source type for local businesses
    BASE_URL = "https://www.yellowpages.com/search"

    # Business categories to search
    BUSINESS_TYPES = [
        "plumber",
        "electrician",
        "hvac",
        "dentist",
        "lawyer",
        "accountant",
        "contractor",
        "auto repair",
        "veterinarian",
        "landscaping",
        "roofing",
        "cleaning service",
        "restaurant",
        "salon"
    ]

    # Locations to search
    LOCATIONS = [
        "Miami, FL",
        "Houston, TX",
        "Phoenix, AZ",
        "Los Angeles, CA",
        "Chicago, IL",
        "Dallas, TX",
        "Atlanta, GA",
        "Denver, CO"
    ]

    def __init__(self):
        super().__init__()

    def scrape(self, time_filter: str = None, location: str = None) -> LeadBatch:
        """
        Scrape Yellow Pages for business listings.

        Args:
            time_filter: Not used
            location: Optional specific location to search

        Returns:
            LeadBatch with found leads
        """
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        locations = [location] if location else self.LOCATIONS[:3]  # Limit locations
        business_types = self.BUSINESS_TYPES[:5]  # Limit types

        self.logger.info(f"Starting Yellow Pages scrape for {len(business_types)} business types")

        for biz_type in business_types:
            for loc in locations:
                try:
                    leads = self._search_businesses(biz_type, loc)
                    all_leads.extend(leads)
                    self.logger.info(f"Found {len(leads)} {biz_type} businesses in {loc}")
                    time.sleep(2)  # Rate limiting
                except Exception as e:
                    error_msg = f"Error searching {biz_type} in {loc}: {str(e)}"
                    self.logger.warning(error_msg)
                    batch.errors.append(error_msg)

        # Deduplicate
        unique_leads = list({lead.id: lead for lead in all_leads}.values())

        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(f"Yellow Pages scrape complete: {batch.total_found} businesses found")
        return batch

    def _search_businesses(self, business_type: str, location: str) -> List[Lead]:
        """Search Yellow Pages for a business type in a location."""
        leads = []

        # Format location for URL
        loc_formatted = location.replace(", ", "-").replace(" ", "-").lower()
        search_term = business_type.replace(" ", "-").lower()

        url = f"https://www.yellowpages.com/{loc_formatted}/{search_term}"

        try:
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find business listings
            listings = soup.find_all('div', class_='result')
            if not listings:
                listings = soup.find_all('div', class_='search-results')
                if listings:
                    listings = listings[0].find_all('div', class_='v-card')

            for listing in listings[:20]:  # Limit per search
                lead = self._parse_listing(listing, business_type, location)
                if lead:
                    leads.append(lead)

        except Exception as e:
            self.logger.debug(f"Yellow Pages search failed: {e}")

        return leads

    def _parse_listing(self, listing, business_type: str, location: str) -> Lead | None:
        """Parse a Yellow Pages listing into a Lead."""
        try:
            # Extract business name
            name_elem = listing.find('a', class_='business-name') or listing.find('h2')
            if not name_elem:
                return None
            name = name_elem.get_text(strip=True)

            # Extract phone
            phone_elem = listing.find('div', class_='phones') or listing.find(class_='phone')
            phone = phone_elem.get_text(strip=True) if phone_elem else None

            # Extract address
            addr_elem = listing.find('div', class_='adr') or listing.find('p', class_='adr')
            address = addr_elem.get_text(strip=True) if addr_elem else None

            # Extract website
            website = None
            website_elem = listing.find('a', class_='track-visit-website')
            if website_elem:
                website = website_elem.get('href', '')

            # Extract rating
            rating = None
            rating_elem = listing.find('div', class_='rating')
            if rating_elem:
                rating_text = rating_elem.get('class', [])
                for cls in rating_text:
                    if 'rating-' in cls:
                        try:
                            rating = float(cls.replace('rating-', '').replace('-', '.'))
                        except:
                            pass

            # Build URL
            link_elem = listing.find('a', class_='business-name')
            url = f"https://www.yellowpages.com{link_elem.get('href', '')}" if link_elem else ""

            lead = Lead(
                id=self.generate_id("yp", f"{name}-{location}"),
                source=self.source,
                title=name,
                content=f"{business_type} in {location}. {address or ''}",
                url=url,
                phone=phone,
                address=address,
                website=website,
                rating=rating,
                business_type=business_type,
                location=location,
                keywords_matched=[],
                has_pain=False  # Will be determined by AI
            )

            return lead

        except Exception as e:
            self.logger.debug(f"Error parsing YP listing: {e}")
            return None
