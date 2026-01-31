"""Google Custom Search scraper."""

import time
from typing import List
from urllib.parse import quote

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class GoogleScraper(BaseScraper):
    """Scraper using Google Custom Search API."""

    source = LeadSource.GOOGLE_SEARCH
    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self):
        super().__init__()
        self.api_key = settings.google_api_key
        self.search_engine_id = settings.google_search_engine_id
        self.search_queries = settings.google_search_queries

    def scrape(self) -> LeadBatch:
        """
        Scrape Google Search for leads.

        Returns:
            LeadBatch with found leads
        """
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        if not self.api_key or not self.search_engine_id:
            error_msg = "Google API key or Search Engine ID not configured"
            self.logger.warning(error_msg)
            batch.errors.append(error_msg)
            return batch

        self.logger.info(f"Starting Google Search scrape with {len(self.search_queries)} queries")

        for query in self.search_queries:
            try:
                leads = self._search_google(query)
                all_leads.extend(leads)
                self.logger.info(f"Found {len(leads)} results for: {query}")
                time.sleep(1)  # Rate limiting
            except Exception as e:
                error_msg = f"Error searching Google for '{query}': {str(e)}"
                self.logger.error(error_msg)
                batch.errors.append(error_msg)

        # Also search review sites for complaint patterns
        try:
            review_leads = self._search_reviews()
            all_leads.extend(review_leads)
        except Exception as e:
            batch.errors.append(f"Error searching reviews: {str(e)}")

        # Deduplicate
        unique_leads = list({lead.id: lead for lead in all_leads}.values())

        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(f"Google scrape complete: {batch.total_found} leads found")
        return batch

    def _search_google(self, query: str, start: int = 1) -> List[Lead]:
        """
        Execute a Google Custom Search.

        Args:
            query: Search query string
            start: Starting result index (1-based)

        Returns:
            List of leads found
        """
        leads = []

        url = (
            f"{self.BASE_URL}"
            f"?key={self.api_key}"
            f"&cx={self.search_engine_id}"
            f"&q={quote(query)}"
            f"&start={start}"
            f"&num=10"
        )

        try:
            response = self.fetch_url(url)
            data = response.json()

            if "error" in data:
                raise Exception(data["error"].get("message", "Unknown API error"))

            for item in data.get("items", []):
                lead = self._item_to_lead(item, query)
                if lead:
                    leads.append(lead)

        except Exception as e:
            self.logger.debug(f"Google search failed: {e}")
            raise

        return leads

    def _search_reviews(self) -> List[Lead]:
        """Search for negative reviews mentioning phone/communication issues."""
        leads = []

        review_queries = [
            'site:yelp.com "never answers phone" OR "can\'t get through"',
            'site:google.com/maps "no one answers" OR "phone goes to voicemail"',
            '"terrible customer service" "phone" small business',
            '"couldn\'t reach" "business" review'
        ]

        for query in review_queries:
            try:
                results = self._search_google(query)
                leads.extend(results)
                time.sleep(1)
            except Exception as e:
                self.logger.debug(f"Review search failed for '{query}': {e}")

        return leads

    def _item_to_lead(self, item: dict, search_query: str) -> Lead | None:
        """
        Convert Google Search result to Lead object.

        Args:
            item: Search result item
            search_query: Original search query

        Returns:
            Lead object or None if not relevant
        """
        try:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            link = item.get("link", "")

            full_text = f"{title} {snippet}"

            # Check for pain keywords
            keywords = self.find_keywords(full_text)

            # Even if no exact keyword match, if it came from our targeted search
            # it might still be relevant
            if not keywords:
                # Add the search query as context
                keywords = [f"search:{search_query[:30]}"]

            # Try to extract structured data if available
            pagemap = item.get("pagemap", {})
            metatags = pagemap.get("metatags", [{}])[0] if pagemap.get("metatags") else {}

            lead = Lead(
                id=self.generate_id("google", link),
                source=self.source,
                title=title,
                content=snippet,
                url=link,
                keywords_matched=keywords,
                email=self.extract_email(full_text),
                phone=self.extract_phone(full_text),
                company=self.extract_company(full_text) or metatags.get("og:site_name")
            )

            return lead

        except Exception as e:
            self.logger.debug(f"Error parsing Google result: {e}")
            return None
