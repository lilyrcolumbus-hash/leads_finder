"""Email extractor - Visit websites and extract contact emails using regex."""

import re
import time
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from src.config import settings
from src.utils.logger import get_logger
from src.utils.models import Lead


class EmailExtractor:
    """Visit business websites and extract email addresses."""

    # Email regex pattern
    EMAIL_PATTERN = re.compile(
        r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    )

    # Pages likely to contain contact info
    CONTACT_PATHS = [
        "/contact",
        "/contact-us",
        "/contacto",
        "/about",
        "/about-us",
        "/team",
        "/staff",
    ]

    def __init__(self):
        self.logger = get_logger("EmailExtractor")
        self.client = httpx.Client(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
        )
        self.junk_domains = set(settings.junk_domains)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def close(self):
        self.client.close()

    def extract_emails_from_leads(self, leads: List[Lead]) -> List[Lead]:
        """
        Visit websites of leads that have a website but no email,
        and try to extract emails.
        """
        updated = 0

        for lead in leads:
            # Skip leads that already have email or no website
            if lead.email or not lead.website:
                continue

            try:
                emails = self.extract_from_website(lead.website)
                if emails:
                    lead.email = emails[0]  # Use first valid email
                    updated += 1
                    self.logger.info(f"Found email for {lead.company or lead.title}: {lead.email}")
                time.sleep(1)  # Rate limiting
            except Exception as e:
                self.logger.debug(f"Error extracting email from {lead.website}: {e}")

        self.logger.info(f"Email extraction complete: {updated}/{len(leads)} leads updated with emails")
        return leads

    def extract_from_website(self, url: str) -> List[str]:
        """
        Extract emails from a website.
        Checks the main page and common contact pages.
        """
        all_emails: Set[str] = set()

        # Normalize URL
        if not url.startswith("http"):
            url = f"https://{url}"

        # Check main page
        emails = self._extract_from_page(url)
        all_emails.update(emails)

        # If no emails found on main page, check contact pages
        if not all_emails:
            base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            for path in self.CONTACT_PATHS:
                contact_url = urljoin(base_url, path)
                try:
                    emails = self._extract_from_page(contact_url)
                    all_emails.update(emails)
                    if all_emails:
                        break
                    time.sleep(0.5)
                except Exception:
                    continue

        return list(all_emails)

    def _extract_from_page(self, url: str) -> Set[str]:
        """Extract emails from a single page."""
        emails = set()

        try:
            response = self.client.get(url)
            if response.status_code != 200:
                return emails

            html = response.text

            # Method 1: Extract from mailto: links
            soup = BeautifulSoup(html, "lxml")
            for mailto in soup.select('a[href^="mailto:"]'):
                href = mailto.get("href", "")
                email = href.replace("mailto:", "").split("?")[0].strip()
                if self._is_valid_email(email):
                    emails.add(email.lower())

            # Method 2: Extract from raw HTML using regex
            found = self.EMAIL_PATTERN.findall(html)
            for email in found:
                if self._is_valid_email(email):
                    emails.add(email.lower())

            # Method 3: Check meta tags
            for meta in soup.find_all("meta", content=self.EMAIL_PATTERN):
                content = meta.get("content", "")
                meta_emails = self.EMAIL_PATTERN.findall(content)
                for email in meta_emails:
                    if self._is_valid_email(email):
                        emails.add(email.lower())

        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            self.logger.debug(f"Request failed for {url}: {e}")
        except Exception as e:
            self.logger.debug(f"Error extracting from {url}: {e}")

        return emails

    def _is_valid_email(self, email: str) -> bool:
        """Check if an email is valid and not from a junk domain."""
        if not email or "@" not in email:
            return False

        # Check length
        if len(email) < 5 or len(email) > 254:
            return False

        domain = email.split("@")[1].lower()

        # Check against junk domains
        for junk in self.junk_domains:
            if domain == junk or domain.endswith(f".{junk}"):
                return False

        # Skip common invalid patterns
        invalid_patterns = [
            "example.",
            "test@",
            "noreply@",
            "no-reply@",
            "donotreply@",
            "mailer-daemon@",
            ".png",
            ".jpg",
            ".gif",
            ".css",
            ".js",
        ]
        email_lower = email.lower()
        for pattern in invalid_patterns:
            if pattern in email_lower:
                return False

        return True
