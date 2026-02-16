"""Facebook scraper for public groups and pages."""

from typing import List, Optional
from datetime import datetime
import httpx

from src.config import settings
from src.utils.logger import get_logger
from src.utils.models import Lead, LeadBatch, LeadSource


class FacebookScraper:
    """Scraper for Facebook public groups and pages using Graph API."""

    source = LeadSource.FACEBOOK
    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.access_token = getattr(settings, 'facebook_access_token', '')
        self.client = httpx.Client(timeout=30.0)
        self.pain_keywords = settings.pain_keywords

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def is_configured(self) -> bool:
        """Check if Facebook API is configured."""
        return bool(self.access_token)

    def search_groups(self, query: str, limit: int = 25) -> List[dict]:
        """
        Search public Facebook groups.

        Note: Facebook Graph API has limited search capabilities.
        This searches for groups matching the query.
        """
        if not self.is_configured():
            self.logger.warning("Facebook access token not configured")
            return []

        try:
            url = f"{self.BASE_URL}/search"
            params = {
                "q": query,
                "type": "group",
                "limit": limit,
                "access_token": self.access_token
            }

            response = self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            elif response.status_code == 400:
                error = response.json().get("error", {})
                self.logger.warning(f"Facebook API error: {error.get('message', 'Unknown error')}")
                return []
            else:
                self.logger.error(f"Facebook API returned {response.status_code}")
                return []

        except Exception as e:
            self.logger.error(f"Error searching Facebook groups: {e}")
            return []

    def get_group_feed(self, group_id: str, limit: int = 50) -> List[dict]:
        """
        Get posts from a public Facebook group.

        Args:
            group_id: The Facebook group ID
            limit: Maximum number of posts to retrieve
        """
        if not self.is_configured():
            return []

        try:
            url = f"{self.BASE_URL}/{group_id}/feed"
            params = {
                "fields": "id,message,from,created_time,permalink_url",
                "limit": limit,
                "access_token": self.access_token
            }

            response = self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            else:
                self.logger.warning(f"Cannot access group {group_id}: {response.status_code}")
                return []

        except Exception as e:
            self.logger.error(f"Error fetching group feed: {e}")
            return []

    def search_pages(self, query: str, limit: int = 25) -> List[dict]:
        """
        Search public Facebook pages (businesses).
        """
        if not self.is_configured():
            return []

        try:
            url = f"{self.BASE_URL}/search"
            params = {
                "q": query,
                "type": "page",
                "fields": "id,name,category,phone,website,location,about",
                "limit": limit,
                "access_token": self.access_token
            }

            response = self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            else:
                return []

        except Exception as e:
            self.logger.error(f"Error searching Facebook pages: {e}")
            return []

    def scrape(self, queries: List[str] = None, group_ids: List[str] = None) -> LeadBatch:
        """
        Scrape leads from Facebook groups and pages.

        Args:
            queries: Search queries to find groups/pages
            group_ids: Specific group IDs to scrape
        """
        leads = []

        if not self.is_configured():
            self.logger.warning("Facebook not configured - skipping")
            return LeadBatch(leads=[], source=self.source)

        # Default queries for lead generation
        if queries is None:
            queries = [
                "small business owners",
                "HVAC contractors",
                "plumbers",
                "local business networking"
            ]

        # Search pages for businesses
        for query in queries:
            self.logger.info(f"Searching Facebook pages: {query}")
            pages = self.search_pages(query, limit=20)

            for page in pages:
                lead = self._page_to_lead(page)
                if lead:
                    leads.append(lead)

        # Scrape specific groups if provided
        if group_ids:
            for group_id in group_ids:
                self.logger.info(f"Scraping Facebook group: {group_id}")
                posts = self.get_group_feed(group_id, limit=50)

                for post in posts:
                    lead = self._post_to_lead(post, group_id)
                    if lead and self._has_pain_keywords(post.get("message", "")):
                        leads.append(lead)

        self.logger.info(f"Found {len(leads)} leads from Facebook")
        return LeadBatch(leads=leads, source=self.source)

    def _page_to_lead(self, page: dict) -> Optional[Lead]:
        """Convert a Facebook page to a Lead."""
        try:
            page_id = page.get("id", "")
            name = page.get("name", "Unknown")

            location_data = page.get("location", {})
            location = None
            if location_data:
                city = location_data.get("city", "")
                state = location_data.get("state", "")
                location = f"{city}, {state}".strip(", ")

            return Lead(
                id=f"fb_page_{page_id}",
                source=LeadSource.FACEBOOK,
                title=name or page.get("name", "Facebook Page"),
                company=name,
                phone=page.get("phone"),
                website=page.get("website"),
                location=location,
                industry=page.get("category"),
                content=page.get("about", ""),
                url=f"https://facebook.com/{page_id}",
                keywords_matched=[],
                found_at=datetime.now()
            )
        except Exception as e:
            self.logger.error(f"Error converting page to lead: {e}")
            return None

    def _post_to_lead(self, post: dict, group_id: str) -> Optional[Lead]:
        """Convert a Facebook group post to a Lead."""
        try:
            post_id = post.get("id", "")
            message = post.get("message", "")
            author = post.get("from", {})

            # Parse created time
            created_time = post.get("created_time", "")
            posted_at = None
            if created_time:
                try:
                    posted_at = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    posted_at = datetime.now()

            # Extract keywords
            keywords = self._find_keywords(message)

            return Lead(
                id=f"fb_post_{post_id}",
                source=LeadSource.FACEBOOK,
                username=author.get("name", "Unknown"),
                title=message[:100] if message else "Facebook Post",
                content=message[:500] if message else "",
                keywords_matched=keywords,
                url=post.get("permalink_url", f"https://facebook.com/{post_id}"),
                posted_at=posted_at,
                found_at=datetime.now(),
                extra_data={"group_id": group_id}
            )
        except Exception as e:
            self.logger.error(f"Error converting post to lead: {e}")
            return None

    def _has_pain_keywords(self, text: str) -> bool:
        """Check if text contains pain keywords."""
        if not text:
            return False
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in self.pain_keywords)

    def _find_keywords(self, text: str) -> List[str]:
        """Find pain keywords in text."""
        if not text:
            return []
        text_lower = text.lower()
        return [kw for kw in self.pain_keywords if kw.lower() in text_lower]

    def test_connection(self) -> dict:
        """Test Facebook API connection."""
        if not self.is_configured():
            return {
                "success": False,
                "message": "Facebook access token not configured"
            }

        try:
            # Test by getting basic info about the token
            url = f"{self.BASE_URL}/me"
            params = {"access_token": self.access_token}

            response = self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "message": "Connected to Facebook API",
                    "app_name": data.get("name", "Unknown")
                }
            elif response.status_code == 400:
                error = response.json().get("error", {})
                return {
                    "success": False,
                    "message": f"Invalid token: {error.get('message', 'Unknown error')}"
                }
            else:
                return {
                    "success": False,
                    "message": f"Facebook API returned status {response.status_code}"
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Connection error: {str(e)}"
            }
