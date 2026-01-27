"""Base scraper class with common functionality."""

import hashlib
import re
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.utils.logger import get_logger
from src.utils.models import Lead, LeadBatch, LeadSource


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    source: LeadSource = NotImplemented

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.client = httpx.Client(
            timeout=30.0,
            headers={"User-Agent": "LeadGenBot/1.0 (Educational Purpose)"}
        )
        self.pain_keywords = settings.pain_keywords

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    @abstractmethod
    def scrape(self) -> LeadBatch:
        """
        Scrape leads from the source.

        Returns:
            LeadBatch containing found leads
        """
        pass

    def generate_id(self, *args) -> str:
        """Generate a unique ID from given arguments."""
        content = "|".join(str(a) for a in args)
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def find_keywords(self, text: str) -> List[str]:
        """
        Find pain keywords in text.

        Args:
            text: Text to search

        Returns:
            List of matched keywords
        """
        text_lower = text.lower()
        matched = []
        for keyword in self.pain_keywords:
            if keyword.lower() in text_lower:
                matched.append(keyword)
        return matched

    def extract_email(self, text: str) -> Optional[str]:
        """Extract email address from text if present."""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(email_pattern, text)
        return match.group(0) if match else None

    def extract_company(self, text: str) -> Optional[str]:
        """Try to extract company name from text."""
        patterns = [
            r"(?:my|our)\s+(?:company|business|shop|store|firm)\s+(?:called|named)?\s*['\"]?([A-Z][A-Za-z0-9\s&']+)['\"]?",
            r"(?:at|for|with)\s+([A-Z][A-Za-z0-9\s&']+(?:LLC|Inc|Corp|Co\.?))",
            r"(?:I own|I run|running)\s+([A-Z][A-Za-z0-9\s&']+)"
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def fetch_url(self, url: str) -> httpx.Response:
        """Fetch URL with retry logic."""
        response = self.client.get(url)
        response.raise_for_status()
        return response
