"""Base scraper class with common functionality."""

import hashlib
import re
import time
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

    # Emails to ignore (generic, CMS-generated, or not real business emails)
    _JUNK_EMAIL_DOMAINS = {
        "example.com", "test.com", "sentry.io", "wixpress.com",
        "squarespace.com", "wordpress.com", "godaddy.com",
        "mailchimp.com", "hubspot.com", "googleapis.com",
        "googleusercontent.com", "gstatic.com", "schema.org",
        "w3.org", "facebook.com", "twitter.com", "instagram.com",
        "change.org", "gravatar.com",
    }
    _JUNK_EMAIL_PREFIXES = {
        "noreply", "no-reply", "donotreply", "do-not-reply",
        "mailer-daemon", "postmaster", "webmaster", "hostmaster",
        "admin@wix", "username", "email@", "your@", "name@",
        "example", "test@", "null@",
    }

    # Sub-pages likely to contain contact emails
    _CONTACT_PATHS = [
        "", "/contact", "/contact-us", "/contacto",
        "/about", "/about-us", "/sobre-nosotros",
    ]

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

    def extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text if present."""
        # Multiple phone patterns for different formats
        patterns = [
            # US formats: (123) 456-7890, 123-456-7890, 123.456.7890
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            # International: +1 123 456 7890, +44 20 7123 4567
            r'\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
            # Simple: 1234567890 (10 digits)
            r'\b\d{10}\b',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group(0)
                # Clean up the phone number
                digits = re.sub(r'\D', '', phone)
                # Validate: should have 10-15 digits
                if 10 <= len(digits) <= 15:
                    return phone
        return None

    def _is_real_email(self, email: str) -> bool:
        """Check if an email looks like a real business email (not junk)."""
        email_lower = email.lower().strip()

        if email_lower.endswith("@leadgen.placeholder"):
            return False

        domain = email_lower.split("@")[-1]
        for junk_domain in self._JUNK_EMAIL_DOMAINS:
            if domain == junk_domain or domain.endswith("." + junk_domain):
                return False

        local_part = email_lower.split("@")[0]
        for prefix in self._JUNK_EMAIL_PREFIXES:
            if local_part.startswith(prefix):
                return False

        if "." not in domain or len(domain) < 4:
            return False

        if len(local_part) < 2:
            return False

        return True

    def _extract_all_emails(self, html: str) -> List[str]:
        """Extract all unique real email addresses from HTML text."""
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        found = set(re.findall(pattern, html))
        return [e for e in found if self._is_real_email(e)]

    def _pick_best_email(self, emails: List[str]) -> Optional[str]:
        """Pick the best email from a list, preferring business-contact ones."""
        if not emails:
            return None
        if len(emails) == 1:
            return emails[0]

        preferred = ["info", "contact", "hello", "hola", "office", "sales",
                      "enquiries", "inquiries", "service", "support"]
        for pref in preferred:
            for email in emails:
                if email.lower().startswith(pref):
                    return email

        return emails[0]

    def extract_email_from_website(self, website: str) -> Optional[str]:
        """
        Extract a real business email by crawling the website homepage
        and common contact/about pages.

        Returns the best real email found, or None.
        """
        if not website:
            return None

        base = website.rstrip("/")
        if not base.startswith("http"):
            base = "https://" + base

        all_emails: List[str] = []

        for path in self._CONTACT_PATHS:
            url = base + path
            try:
                response = self.client.get(url, timeout=10.0, follow_redirects=True)
                if response.status_code == 200:
                    page_emails = self._extract_all_emails(response.text)
                    all_emails.extend(page_emails)
            except Exception:
                continue

            if path != self._CONTACT_PATHS[-1]:
                time.sleep(0.3)

        # Deduplicate while preserving order
        seen = set()
        unique: List[str] = []
        for e in all_emails:
            lower = e.lower()
            if lower not in seen:
                seen.add(lower)
                unique.append(e)

        return self._pick_best_email(unique)

    def enrich_leads_emails(self, leads: List[Lead]) -> List[Lead]:
        """Crawl websites to find emails for leads that have a website but no email.

        Iterates over leads, and for any that have a ``website`` field set
        but are missing an ``email``, calls :meth:`extract_email_from_website`
        to scrape the business site.

        Args:
            leads: List of leads to enrich.

        Returns:
            Same list with ``email`` populated where an address was found.
        """
        enriched = 0
        for lead in leads:
            if lead.website and not lead.email:
                try:
                    email = self.extract_email_from_website(lead.website)
                    if email:
                        lead.email = email
                        enriched += 1
                        self.logger.info(
                            f"Email found for {lead.company or lead.title}: {email}"
                        )
                except Exception as e:
                    self.logger.debug(
                        f"Error crawling website for {lead.company or lead.title}: {e}"
                    )
                time.sleep(0.5)

        if enriched:
            self.logger.info(f"Website crawling enriched {enriched} leads with emails")
        return leads

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def fetch_url(self, url: str) -> httpx.Response:
        """Fetch URL with retry logic."""
        response = self.client.get(url)
        response.raise_for_status()
        return response
