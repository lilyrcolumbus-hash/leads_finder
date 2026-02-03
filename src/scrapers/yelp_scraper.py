"""Yelp scraper for finding businesses with phone/service complaints."""

import time
from typing import List
from urllib.parse import quote

from bs4 import BeautifulSoup

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class YelpScraper(BaseScraper):
    """Scraper for Yelp - find businesses with bad reviews about phone/service."""

    source = LeadSource.YELP
    BASE_URL = "https://www.yelp.com/search"

    def __init__(self):
        super().__init__()
        # Business categories likely to need phone answering
        self.categories = [
            "plumbers",
            "hvac",
            "electricians",
            "dentists",
            "doctors",
            "lawyers",
            "contractors",
            "auto repair",
            "salons",
            "veterinarians"
        ]
        # Keywords indicating phone problems in reviews
        self.review_keywords = [
            "never answers",
            "can't get through",
            "no one picks up",
            "voicemail",
            "didn't return call",
            "hard to reach",
            "phone goes to",
            "couldn't reach",
            "won't answer",
            "poor communication"
        ]

    def scrape(self, time_filter: str = "week", location: str = "") -> LeadBatch:
        """
        Scrape Yelp for businesses with phone/service complaints.

        Args:
            time_filter: Time range (not used by Yelp, but kept for API consistency)
            location: Location to search (city, state, zip code)
        """
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        # Store location for use in search
        self.search_location = location

        location_msg = f" in {location}" if location else ""
        self.logger.info(f"Starting Yelp scrape for businesses{location_msg}")

        # Search businesses in target categories
        for category in self.categories[:5]:  # Limit for speed
            try:
                leads = self._search_category(category, location)
                all_leads.extend(leads)
                self.logger.info(f"Found {len(leads)} businesses in '{category}'")
                time.sleep(1)
            except Exception as e:
                error_msg = f"Error searching Yelp for '{category}': {str(e)}"
                self.logger.warning(error_msg)
                batch.errors.append(error_msg)

        # Deduplicate
        unique_leads = list({lead.company: lead for lead in all_leads if lead.company}.values())

        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(f"Yelp scrape complete: {batch.total_found} businesses found")
        return batch

    def _search_category(self, category: str, user_location: str = "") -> List[Lead]:
        """Search Yelp for businesses in a category."""
        leads = []

        # Use user-provided location or default to major US cities
        if user_location:
            locations = [user_location]
        else:
            locations = ["New York", "Los Angeles", "Chicago", "Houston", "Miami"]

        for location in locations[:3]:  # Limit locations for speed
            url = f"{self.BASE_URL}?find_desc={quote(category)}&find_loc={quote(location)}"

            try:
                response = self.fetch_url(url)
                soup = BeautifulSoup(response.text, "lxml")

                # Find business cards
                business_cards = soup.find_all("div", {"data-testid": "serp-ia-card"})

                if not business_cards:
                    business_cards = soup.find_all("div", class_=lambda x: x and "businessName" in str(x))

                if not business_cards:
                    # Try alternate selector
                    business_cards = soup.find_all("h3", class_=lambda x: x and "css-" in str(x))

                for card in business_cards[:10]:
                    lead = self._parse_business(card, category, location)
                    if lead:
                        leads.append(lead)

                time.sleep(0.5)

            except Exception as e:
                self.logger.debug(f"Yelp search failed for '{category}' in {location}: {e}")

        return leads

    def _parse_business(self, card, category: str, location: str) -> Lead | None:
        """Parse a business card into a Lead."""
        try:
            # Extract business name
            name_elem = card.find("a", class_=lambda x: x and "css-" in str(x))
            if not name_elem:
                name_elem = card.find("a", href=lambda x: x and "/biz/" in str(x))

            if not name_elem:
                return None

            name = name_elem.get_text(strip=True)
            href = name_elem.get("href", "")

            if not name or len(name) < 3:
                return None

            # Build URL
            url = f"https://www.yelp.com{href}" if href.startswith("/") else href

            # Extract rating if available
            rating_elem = card.find("div", {"aria-label": lambda x: x and "star rating" in str(x).lower()})
            rating = rating_elem.get("aria-label", "") if rating_elem else ""

            # Create lead
            lead = Lead(
                id=self.generate_id("yelp", name, location),
                source=self.source,
                title=f"{name} - {category.title()}",
                content=f"{name} is a {category} business in {location}. {rating}. Local service businesses often struggle with phone management and could benefit from AI receptionist.",
                url=url,
                company=name,
                keywords_matched=[f"category:{category}", f"location:{location}"],
            )

            return lead

        except Exception as e:
            self.logger.debug(f"Error parsing Yelp business: {e}")
            return None
