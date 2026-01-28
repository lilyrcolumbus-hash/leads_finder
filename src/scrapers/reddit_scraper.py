"""Reddit scraper using RSS feeds."""

import time
from typing import List
from xml.etree import ElementTree as ET

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class RedditScraper(BaseScraper):
    """Scraper for Reddit using public RSS feeds."""

    source = LeadSource.REDDIT
    BASE_URL = "https://www.reddit.com/r/{subreddit}/search.rss"

    # XML namespaces for Atom feeds
    NAMESPACES = {
        'atom': 'http://www.w3.org/2005/Atom',
    }

    def __init__(self):
        super().__init__()
        self.subreddits = settings.subreddits

    # Map time filter values to Reddit's t parameter
    TIME_MAP = {
        "day": "day",
        "week": "week",
        "month": "month",
        "quarter": "month",  # Reddit doesn't have quarter, use month
        "year": "year",
        "all": "all"
    }

    def scrape(self, time_filter: str = "week") -> LeadBatch:
        """
        Scrape Reddit for leads matching pain keywords.

        Args:
            time_filter: Time range for posts (day, week, month, quarter, year, all)

        Returns:
            LeadBatch with found leads
        """
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        # Convert time filter to Reddit's format
        reddit_time = self.TIME_MAP.get(time_filter, "week")
        self.current_time_filter = reddit_time

        self.logger.info(f"Starting Reddit scrape for {len(self.subreddits)} subreddits (time: {reddit_time})")

        for subreddit in self.subreddits:
            try:
                leads = self._scrape_subreddit(subreddit)
                all_leads.extend(leads)
                self.logger.info(f"Found {len(leads)} potential leads in r/{subreddit}")
                time.sleep(2)  # Rate limiting
            except Exception as e:
                error_msg = f"Error scraping r/{subreddit}: {str(e)}"
                self.logger.error(error_msg)
                batch.errors.append(error_msg)

        # Deduplicate by ID
        unique_leads = list({lead.id: lead for lead in all_leads}.values())

        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(f"Reddit scrape complete: {batch.total_found} total leads found")
        return batch

    def _scrape_subreddit(self, subreddit: str) -> List[Lead]:
        """
        Scrape a single subreddit for matching posts.

        Args:
            subreddit: Name of subreddit to scrape

        Returns:
            List of leads found
        """
        leads = []

        # Search for each pain keyword
        for keyword in self.pain_keywords[:10]:  # Limit to avoid rate limits
            try:
                leads.extend(self._search_keyword(subreddit, keyword))
                time.sleep(1)  # Be nice to Reddit
            except Exception as e:
                self.logger.warning(f"Error searching '{keyword}' in r/{subreddit}: {e}")

        # Also get recent posts from the subreddit
        try:
            leads.extend(self._get_recent_posts(subreddit))
        except Exception as e:
            self.logger.warning(f"Error getting recent posts from r/{subreddit}: {e}")

        return leads

    def _search_keyword(self, subreddit: str, keyword: str) -> List[Lead]:
        """Search subreddit for a specific keyword."""
        leads = []
        time_param = getattr(self, 'current_time_filter', 'week')
        url = f"https://www.reddit.com/r/{subreddit}/search.rss?q={keyword}&restrict_sr=1&sort=new&t={time_param}&limit=25"

        try:
            response = self.fetch_url(url)
            entries = self._parse_rss(response.text)

            for entry in entries:
                lead = self._entry_to_lead(entry, subreddit)
                if lead and lead.keywords_matched:
                    leads.append(lead)

        except Exception as e:
            self.logger.debug(f"Search failed for '{keyword}' in r/{subreddit}: {e}")

        return leads

    def _get_recent_posts(self, subreddit: str) -> List[Lead]:
        """Get recent posts from subreddit RSS feed."""
        leads = []
        time_param = getattr(self, 'current_time_filter', 'week')
        # Use top posts with time filter instead of just new
        url = f"https://www.reddit.com/r/{subreddit}/top.rss?t={time_param}&limit=50"

        try:
            response = self.fetch_url(url)
            entries = self._parse_rss(response.text)

            for entry in entries:
                lead = self._entry_to_lead(entry, subreddit)
                if lead and lead.keywords_matched:
                    leads.append(lead)

        except Exception as e:
            self.logger.debug(f"Failed to get recent posts from r/{subreddit}: {e}")

        return leads

    def _parse_rss(self, xml_content: str) -> List[dict]:
        """Parse RSS/Atom XML feed into list of entries."""
        entries = []
        try:
            root = ET.fromstring(xml_content)

            # Handle Atom feed format (Reddit uses this)
            for entry in root.findall('atom:entry', self.NAMESPACES):
                entry_data = {
                    'title': self._get_text(entry, 'atom:title'),
                    'link': self._get_attr(entry, 'atom:link', 'href'),
                    'id': self._get_text(entry, 'atom:id'),
                    'author': self._get_text(entry, 'atom:author/atom:name'),
                    'content': self._get_text(entry, 'atom:content'),
                }
                entries.append(entry_data)

            # Also try RSS 2.0 format
            for item in root.findall('.//item'):
                entry_data = {
                    'title': item.findtext('title', ''),
                    'link': item.findtext('link', ''),
                    'id': item.findtext('guid', ''),
                    'author': item.findtext('author', ''),
                    'content': item.findtext('description', ''),
                }
                entries.append(entry_data)

        except ET.ParseError as e:
            self.logger.debug(f"XML parse error: {e}")

        return entries

    def _get_text(self, element: ET.Element, path: str) -> str:
        """Get text from XML element by path."""
        el = element.find(path, self.NAMESPACES)
        return el.text if el is not None and el.text else ''

    def _get_attr(self, element: ET.Element, path: str, attr: str) -> str:
        """Get attribute from XML element by path."""
        el = element.find(path, self.NAMESPACES)
        return el.get(attr, '') if el is not None else ''

    def _entry_to_lead(self, entry: dict, subreddit: str) -> Lead | None:
        """
        Convert RSS entry to Lead object.

        Args:
            entry: Parsed RSS entry dict
            subreddit: Name of subreddit

        Returns:
            Lead object or None if not relevant
        """
        try:
            title = entry.get("title", "")
            content = entry.get("content", "")
            full_text = f"{title} {content}"

            # Check for pain keywords
            keywords = self.find_keywords(full_text)
            if not keywords:
                return None

            # Extract author
            author = entry.get("author", "").replace("/u/", "")

            lead = Lead(
                id=self.generate_id("reddit", entry.get("id", entry.get("link", ""))),
                source=self.source,
                username=author,
                title=title,
                content=content[:2000],  # Limit content length
                url=entry.get("link", ""),
                keywords_matched=keywords,
                subreddit=subreddit,
                email=self.extract_email(full_text),
                company=self.extract_company(full_text)
            )

            return lead

        except Exception as e:
            self.logger.debug(f"Error parsing entry: {e}")
            return None
