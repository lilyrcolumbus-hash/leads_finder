"""Hacker News scraper using the public Algolia API."""

import time
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import quote

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class HackerNewsScraper(BaseScraper):
    """Scraper for Hacker News using the Algolia Search API."""

    source = LeadSource.HACKER_NEWS
    SEARCH_URL = "https://hn.algolia.com/api/v1/search"
    ITEM_URL = "https://news.ycombinator.com/item?id={item_id}"

    # Map time filter to days
    TIME_MAP = {
        "day": 1,
        "week": 7,
        "month": 30,
        "quarter": 90,
        "year": 365,
        "all": 0  # No filter
    }

    def __init__(self):
        super().__init__()
        # Additional HN-specific keywords
        self.hn_keywords = [
            "small business phone",
            "receptionist startup",
            "answering service",
            "customer calls",
            "missed calls business",
            "phone support overwhelmed",
            "scheduling customers",
            "appointment booking",
            "call center small business"
        ]

    def scrape(self, time_filter: str = "week") -> LeadBatch:
        """
        Scrape Hacker News for leads.

        Args:
            time_filter: Time range for results (day, week, month, quarter, year, all)

        Returns:
            LeadBatch with found leads
        """
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        # Calculate timestamp filter
        days = self.TIME_MAP.get(time_filter, 7)
        if days > 0:
            cutoff = datetime.now() - timedelta(days=days)
            self.min_timestamp = int(cutoff.timestamp())
        else:
            self.min_timestamp = 0

        self.logger.info(f"Starting Hacker News scrape (time: {time_filter})")

        # Search for general pain keywords
        search_terms = self.pain_keywords[:8] + self.hn_keywords

        for term in search_terms:
            try:
                leads = self._search_hn(term)
                all_leads.extend(leads)
                self.logger.debug(f"Found {len(leads)} results for '{term}'")
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                error_msg = f"Error searching HN for '{term}': {str(e)}"
                self.logger.warning(error_msg)
                batch.errors.append(error_msg)

        # Also check "Ask HN" posts
        try:
            ask_leads = self._search_ask_hn()
            all_leads.extend(ask_leads)
        except Exception as e:
            batch.errors.append(f"Error searching Ask HN: {str(e)}")

        # Deduplicate
        unique_leads = list({lead.id: lead for lead in all_leads}.values())

        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(f"HN scrape complete: {batch.total_found} leads found")
        return batch

    def _search_hn(self, query: str, tags: Optional[str] = None) -> List[Lead]:
        """
        Search Hacker News using Algolia API.

        Args:
            query: Search query
            tags: Optional HN tags filter (e.g., 'story', 'comment', 'ask_hn')

        Returns:
            List of leads found
        """
        leads = []

        params = {
            "query": query,
            "hitsPerPage": 30,
            "attributesToRetrieve": "objectID,title,url,author,story_text,comment_text,created_at"
        }

        if tags:
            params["tags"] = tags

        url = f"{self.SEARCH_URL}?query={quote(query)}&hitsPerPage=30"
        if tags:
            url += f"&tags={tags}"

        # Add time filter if set
        min_ts = getattr(self, 'min_timestamp', 0)
        if min_ts > 0:
            url += f"&numericFilters=created_at_i>{min_ts}"

        try:
            response = self.fetch_url(url)
            data = response.json()

            for hit in data.get("hits", []):
                lead = self._hit_to_lead(hit, search_query=query)
                if lead:
                    leads.append(lead)

        except Exception as e:
            self.logger.debug(f"HN search failed for '{query}': {e}")

        return leads

    def _search_ask_hn(self) -> List[Lead]:
        """Search 'Ask HN' posts for business owners seeking help."""
        leads = []

        # Search for Ask HN posts about business problems
        queries = [
            "small business",
            "startup phone",
            "customer service",
            "scheduling system"
        ]

        for query in queries:
            try:
                results = self._search_hn(query, tags="ask_hn")
                leads.extend(results)
                time.sleep(0.3)
            except Exception as e:
                self.logger.debug(f"Ask HN search failed: {e}")

        return leads

    def _hit_to_lead(self, hit: dict, search_query: str = None) -> Lead | None:
        """
        Convert Algolia hit to Lead object.

        Args:
            hit: Search result from Algolia
            search_query: The query used to find this hit (optional)

        Returns:
            Lead object or None if not relevant
        """
        try:
            object_id = hit.get("objectID", "")
            title = hit.get("title", "") or ""
            story_text = hit.get("story_text", "") or ""
            comment_text = hit.get("comment_text", "") or ""
            content = story_text or comment_text

            full_text = f"{title} {content}"

            # Check for pain keywords
            keywords = self.find_keywords(full_text)

            # If no keywords found but we have a search query, use that
            if not keywords and search_query:
                keywords = [f"search:{search_query}"]
            elif not keywords:
                return None

            # Build URL
            url = hit.get("url") or self.ITEM_URL.format(item_id=object_id)

            lead = Lead(
                id=self.generate_id("hn", object_id),
                source=self.source,
                username=hit.get("author", ""),
                title=title,
                content=content[:2000],
                url=url,
                keywords_matched=keywords,
                email=self.extract_email(full_text),
                company=self.extract_company(full_text)
            )

            return lead

        except Exception as e:
            self.logger.debug(f"Error parsing HN hit: {e}")
            return None
