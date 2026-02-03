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

    def scrape(self, time_filter: str = None, location: str = None) -> LeadBatch:
        """
        Scrape Google Search for leads.

        Args:
            time_filter: Optional time filter
            location: Optional location filter

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

        failed_queries = 0
        for query in self.search_queries:
            try:
                leads = self._search_google(query)
                all_leads.extend(leads)
                if leads:
                    self.logger.info(f"Found {len(leads)} results for: {query}")
                time.sleep(1)  # Rate limiting
            except Exception as e:
                failed_queries += 1
                self.logger.debug(f"Query failed: {query}")

        # Report summary if all queries failed
        if failed_queries == len(self.search_queries) and len(all_leads) == 0:
            batch.errors.append("Google API: All queries failed. Check quota (100/day free) or API key.")

        # Also search review sites for complaint patterns
        try:
            review_leads = self._search_reviews()
            all_leads.extend(review_leads)
        except Exception as e:
            self.logger.debug(f"Review search skipped: {e}")

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

            # Check HTTP status code for common errors
            if hasattr(response, 'status_code'):
                if response.status_code == 403:
                    self.logger.warning("Google API: Access denied (403). Check API key permissions or quota.")
                    return leads
                elif response.status_code == 429:
                    self.logger.warning("Google API: Rate limit exceeded (429). Daily quota may be exhausted.")
                    return leads
                elif response.status_code == 400:
                    self.logger.warning("Google API: Bad request (400). Check Search Engine ID.")
                    return leads
                elif response.status_code != 200:
                    self.logger.warning(f"Google API: HTTP {response.status_code}")
                    return leads

            data = response.json()

            # Check for API-level errors
            if "error" in data:
                error_info = data["error"]
                error_code = error_info.get("code", "unknown")
                error_msg = error_info.get("message", "Unknown API error")

                if error_code == 403:
                    self.logger.warning(f"Google API quota exceeded or access denied: {error_msg}")
                elif error_code == 400:
                    self.logger.warning(f"Google API bad request: {error_msg}")
                else:
                    self.logger.warning(f"Google API error ({error_code}): {error_msg}")
                return leads

            for item in data.get("items", []):
                lead = self._item_to_lead(item, query)
                if lead:
                    leads.append(lead)

        except Exception as e:
            error_str = str(e).lower()
            if "403" in error_str or "forbidden" in error_str:
                self.logger.warning("Google API: Access forbidden. Quota may be exceeded (100/day free limit).")
            elif "429" in error_str or "rate" in error_str:
                self.logger.warning("Google API: Rate limited. Try again later.")
            elif "401" in error_str or "unauthorized" in error_str:
                self.logger.warning("Google API: Invalid API key.")
            elif "400" in error_str:
                self.logger.warning("Google API: Invalid Search Engine ID.")
            else:
                self.logger.debug(f"Google search failed: {e}")
            # Don't raise, just return empty to continue with other sources
            return leads

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
