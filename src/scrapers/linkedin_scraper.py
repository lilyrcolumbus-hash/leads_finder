#!/usr/bin/env python3
"""
LinkedIn Scraper - Uses Google Search to find LinkedIn profiles
No paid LinkedIn API required!

Method: site:linkedin.com/in "job title" "location"
"""

import re
import time
import requests
from typing import List, Optional
from datetime import datetime
from urllib.parse import quote_plus

from ..config import settings
from ..utils.models import Lead, LeadSource, LeadBatch
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class LinkedInScraper:
    """
    Scrapes LinkedIn profiles using Google Custom Search API.

    Searches for: site:linkedin.com/in "owner" "dental" "miami"
    Extracts: Name, Title, Company, Location, Profile URL
    """

    def __init__(self):
        self.api_key = settings.google_api_key
        self.search_engine_id = settings.google_search_engine_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Job titles to search for (decision makers)
        self.job_titles = [
            "owner",
            "founder",
            "ceo",
            "president",
            "director",
            "manager",
            "practice owner",
            "business owner"
        ]

        # Industries relevant to AI receptionist
        self.industries = [
            "dental",
            "dentist",
            "hvac",
            "plumber",
            "plumbing",
            "lawyer",
            "attorney",
            "law firm",
            "medical",
            "doctor",
            "clinic",
            "salon",
            "spa",
            "real estate",
            "insurance",
            "contractor",
            "roofing",
            "landscaping",
            "veterinary",
            "vet",
            "chiropractic",
            "chiropractor",
            "accounting",
            "accountant",
            "fitness",
            "gym",
            "auto repair",
            "mechanic"
        ]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def _search_google(self, query: str, start: int = 1) -> List[dict]:
        """Execute Google Custom Search API query."""
        if not self.api_key or not self.search_engine_id:
            logger.warning("Google API not configured")
            return []

        params = {
            'key': self.api_key,
            'cx': self.search_engine_id,
            'q': query,
            'start': start,
            'num': 10  # Max 10 per request
        }

        try:
            response = self.session.get(self.base_url, params=params, timeout=15)

            if response.status_code == 403:
                logger.error("Google API returned 403 - Check API key and enable Custom Search API")
                return []

            if response.status_code != 200:
                logger.error(f"Google API error: {response.status_code}")
                return []

            data = response.json()
            return data.get('items', [])

        except Exception as e:
            logger.error(f"Google search error: {e}")
            return []

    def _parse_linkedin_result(self, item: dict) -> Optional[Lead]:
        """Parse a Google search result into a Lead."""
        try:
            url = item.get('link', '')
            title = item.get('title', '')
            snippet = item.get('snippet', '')

            # Only process LinkedIn profile URLs
            if '/in/' not in url:
                return None

            # Extract name from title (usually "Name - Title - Company | LinkedIn")
            name = ""
            job_title = ""
            company = ""

            if ' - ' in title:
                parts = title.replace(' | LinkedIn', '').split(' - ')
                if len(parts) >= 1:
                    name = parts[0].strip()
                if len(parts) >= 2:
                    job_title = parts[1].strip()
                if len(parts) >= 3:
                    company = parts[2].strip()
            else:
                name = title.replace(' | LinkedIn', '').strip()

            # Extract location from snippet if available
            location = ""
            location_patterns = [
                r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)*,\s*[A-Z]{2})',  # City, ST
                r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)*\s+Area)',  # City Area
            ]
            for pattern in location_patterns:
                match = re.search(pattern, snippet)
                if match:
                    location = match.group(1)
                    break

            # Determine industry from content
            industry = self._detect_industry(f"{title} {snippet}")

            # Create lead
            lead = Lead(
                id=f"linkedin_{abs(hash(url)) % 10**12}",
                source=LeadSource.LINKEDIN,
                title=name or title,
                content=snippet,
                url=url,
                author=name,
                username=name,
                company=company,
                industry=industry,
                found_at=datetime.now(),
                keywords_matched=[],
                extra_data={
                    'job_title': job_title,
                    'location': location,
                    'platform': 'linkedin'
                }
            )

            return lead

        except Exception as e:
            logger.error(f"Error parsing LinkedIn result: {e}")
            return None

    def _detect_industry(self, text: str) -> str:
        """Detect industry from text content."""
        text_lower = text.lower()

        industry_keywords = {
            'Healthcare': ['dental', 'dentist', 'doctor', 'medical', 'clinic', 'healthcare', 'physician', 'hospital'],
            'Legal': ['lawyer', 'attorney', 'law firm', 'legal', 'paralegal'],
            'Home Services': ['hvac', 'plumber', 'plumbing', 'contractor', 'roofing', 'landscaping', 'electrician'],
            'Automotive': ['auto repair', 'mechanic', 'car dealer', 'automotive'],
            'Beauty & Wellness': ['salon', 'spa', 'beauty', 'hair', 'nail', 'massage'],
            'Fitness': ['gym', 'fitness', 'personal trainer', 'yoga', 'crossfit'],
            'Real Estate': ['real estate', 'realtor', 'property', 'broker'],
            'Insurance': ['insurance', 'agent', 'broker'],
            'Financial': ['accounting', 'accountant', 'cpa', 'financial', 'tax'],
            'Veterinary': ['veterinary', 'vet', 'animal', 'pet'],
            'Chiropractic': ['chiropractic', 'chiropractor']
        }

        for industry, keywords in industry_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return industry

        return 'Business'

    def scrape(self, time_filter: str = "week", location: str = "",
               industry: str = "", job_title: str = "") -> LeadBatch:
        """
        Scrape LinkedIn profiles using Google Search.

        Args:
            time_filter: Not used for LinkedIn (profiles don't have dates)
            location: City/State to search (e.g., "Miami, FL")
            industry: Specific industry to search (e.g., "dental")
            job_title: Specific job title (e.g., "owner")

        Returns:
            LeadBatch with found leads
        """
        all_leads = []

        # Build search queries
        queries = self._build_queries(location, industry, job_title)

        logger.info(f"LinkedIn Scraper: Running {len(queries)} search queries")

        for query in queries[:5]:  # Limit to 5 queries to conserve API quota
            logger.info(f"Searching: {query}")

            # Get first page of results
            results = self._search_google(query)

            for item in results:
                lead = self._parse_linkedin_result(item)
                if lead:
                    all_leads.append(lead)

            # Respect rate limits
            time.sleep(1)

        # Deduplicate by URL
        seen_urls = set()
        unique_leads = []
        for lead in all_leads:
            if lead.url not in seen_urls:
                seen_urls.add(lead.url)
                unique_leads.append(lead)

        logger.info(f"LinkedIn Scraper: Found {len(unique_leads)} unique profiles")

        return LeadBatch(
            leads=unique_leads,
            source=LeadSource.LINKEDIN,
            scraped_at=datetime.now()
        )

    def _build_queries(self, location: str = "", industry: str = "",
                       job_title: str = "") -> List[str]:
        """Build Google search queries for LinkedIn."""
        queries = []

        # Base query
        base = 'site:linkedin.com/in'

        # Use provided values or defaults
        titles = [job_title] if job_title else self.job_titles[:3]
        industries_to_search = [industry] if industry else self.industries[:5]

        for title in titles:
            for ind in industries_to_search:
                query = f'{base} "{title}" "{ind}"'

                if location:
                    query += f' "{location}"'

                queries.append(query)

        return queries

    def search_specific(self, keywords: List[str], location: str = "") -> LeadBatch:
        """
        Search for specific keywords on LinkedIn.

        Args:
            keywords: List of keywords to search
            location: Optional location filter

        Returns:
            LeadBatch with found leads
        """
        all_leads = []

        for keyword in keywords[:3]:  # Limit keywords
            query = f'site:linkedin.com/in "{keyword}"'

            if location:
                query += f' "{location}"'

            results = self._search_google(query)

            for item in results:
                lead = self._parse_linkedin_result(item)
                if lead:
                    all_leads.append(lead)

            time.sleep(1)

        # Deduplicate
        seen_urls = set()
        unique_leads = []
        for lead in all_leads:
            if lead.url not in seen_urls:
                seen_urls.add(lead.url)
                unique_leads.append(lead)

        return LeadBatch(
            leads=unique_leads,
            source=LeadSource.LINKEDIN,
            scraped_at=datetime.now()
        )


# Alternative: Direct Google search without API (using requests)
class LinkedInScraperFree:
    """
    Free LinkedIn scraper using direct Google search.
    Note: This may be blocked by Google if used excessively.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def search(self, query: str) -> List[str]:
        """
        Search Google for LinkedIn profiles.
        Returns list of LinkedIn profile URLs.

        Warning: This may be rate-limited or blocked by Google.
        """
        search_url = f"https://www.google.com/search?q={quote_plus(query)}"

        try:
            response = self.session.get(search_url, timeout=10)

            if response.status_code != 200:
                return []

            # Extract LinkedIn URLs using regex
            linkedin_pattern = r'https://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9\-]+'
            urls = re.findall(linkedin_pattern, response.text)

            return list(set(urls))  # Deduplicate

        except Exception as e:
            logger.error(f"Free search error: {e}")
            return []
