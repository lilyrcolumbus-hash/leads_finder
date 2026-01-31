"""Hunter.io integration for email lookup and verification."""

import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from src.config import settings
from src.utils.logger import get_logger


@dataclass
class EmailResult:
    """Result from Hunter.io email lookup."""
    email: str
    confidence: int  # 0-100
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position: Optional[str] = None
    verified: bool = False


class HunterClient:
    """Client for Hunter.io API to find and verify emails."""

    BASE_URL = "https://api.hunter.io/v2"

    def __init__(self):
        self.logger = get_logger("Hunter")
        self.api_key = settings.hunter_api_key
        self.client = httpx.Client(timeout=30.0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def is_configured(self) -> bool:
        """Check if Hunter.io API key is configured."""
        return bool(self.api_key)

    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL."""
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            # Remove www. prefix
            domain = re.sub(r'^www\.', '', domain)
            # Remove path if accidentally included
            domain = domain.split('/')[0]
            return domain if '.' in domain else None
        except Exception:
            return None

    def domain_search(self, domain: str, limit: int = 5) -> List[EmailResult]:
        """
        Search for emails associated with a domain.

        Args:
            domain: Domain to search (e.g., 'company.com')
            limit: Maximum number of results

        Returns:
            List of EmailResult objects
        """
        if not self.is_configured():
            self.logger.warning("Hunter.io not configured")
            return []

        url = f"{self.BASE_URL}/domain-search"
        params = {
            "domain": domain,
            "api_key": self.api_key,
            "limit": limit
        }

        try:
            response = self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            results = []
            for email_data in data.get("data", {}).get("emails", []):
                result = EmailResult(
                    email=email_data.get("value", ""),
                    confidence=email_data.get("confidence", 0),
                    first_name=email_data.get("first_name"),
                    last_name=email_data.get("last_name"),
                    position=email_data.get("position"),
                    verified=email_data.get("verification", {}).get("status") == "valid"
                )
                results.append(result)

            self.logger.info(f"Found {len(results)} emails for domain {domain}")
            return results

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self.logger.error("Invalid Hunter.io API key")
            elif e.response.status_code == 429:
                self.logger.warning("Hunter.io rate limit reached")
            else:
                self.logger.error(f"Hunter.io API error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error searching domain {domain}: {e}")
            return []

    def email_finder(self, domain: str, first_name: str = None, last_name: str = None,
                     full_name: str = None) -> Optional[EmailResult]:
        """
        Find email for a specific person at a company.

        Args:
            domain: Company domain
            first_name: Person's first name
            last_name: Person's last name
            full_name: Full name (alternative to first/last)

        Returns:
            EmailResult if found, None otherwise
        """
        if not self.is_configured():
            return None

        url = f"{self.BASE_URL}/email-finder"
        params = {
            "domain": domain,
            "api_key": self.api_key
        }

        if full_name:
            params["full_name"] = full_name
        else:
            if first_name:
                params["first_name"] = first_name
            if last_name:
                params["last_name"] = last_name

        try:
            response = self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json().get("data", {})

            if data.get("email"):
                return EmailResult(
                    email=data["email"],
                    confidence=data.get("score", 0),
                    first_name=data.get("first_name"),
                    last_name=data.get("last_name"),
                    position=data.get("position"),
                    verified=data.get("verification", {}).get("status") == "valid"
                )
            return None

        except Exception as e:
            self.logger.debug(f"Email finder error: {e}")
            return None

    def verify_email(self, email: str) -> Dict[str, Any]:
        """
        Verify if an email address is valid.

        Args:
            email: Email address to verify

        Returns:
            Dict with verification results
        """
        if not self.is_configured():
            return {"status": "unknown", "error": "Not configured"}

        url = f"{self.BASE_URL}/email-verifier"
        params = {
            "email": email,
            "api_key": self.api_key
        }

        try:
            response = self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json().get("data", {})

            return {
                "status": data.get("status", "unknown"),
                "result": data.get("result", "unknown"),
                "score": data.get("score", 0),
                "disposable": data.get("disposable", False),
                "webmail": data.get("webmail", False),
                "accept_all": data.get("accept_all", False)
            }

        except Exception as e:
            self.logger.debug(f"Email verification error: {e}")
            return {"status": "error", "error": str(e)}

    def find_email_for_lead(self, url: str = None, company: str = None,
                            name: str = None) -> Optional[EmailResult]:
        """
        Try to find an email for a lead using available information.

        Strategy:
        1. If URL available, extract domain and search
        2. If company name available, try common domain patterns
        3. If name available with domain, use email finder

        Args:
            url: Lead's URL (to extract domain)
            company: Company name
            name: Person's name

        Returns:
            Best EmailResult found, or None
        """
        if not self.is_configured():
            return None

        domain = None

        # Try to get domain from URL
        if url:
            domain = self._extract_domain(url)
            # Skip social media and forum domains
            skip_domains = ['reddit.com', 'news.ycombinator.com', 'producthunt.com',
                           'twitter.com', 'facebook.com', 'linkedin.com', 'youtube.com']
            if domain and any(skip in domain for skip in skip_domains):
                domain = None

        # Try to guess domain from company name
        if not domain and company:
            # Clean company name and try common patterns
            clean_name = re.sub(r'[^a-zA-Z0-9]', '', company.lower())
            if clean_name:
                # Try common domain patterns
                for tld in ['.com', '.io', '.co', '.net']:
                    test_domain = clean_name + tld
                    results = self.domain_search(test_domain, limit=1)
                    if results:
                        domain = test_domain
                        break

        if not domain:
            return None

        # If we have a name, try email finder first
        if name and domain:
            result = self.email_finder(domain, full_name=name)
            if result and result.confidence >= 50:
                return result

        # Fall back to domain search
        results = self.domain_search(domain, limit=3)
        if results:
            # Return highest confidence result
            return max(results, key=lambda x: x.confidence)

        return None

    def get_account_info(self) -> Dict[str, Any]:
        """Get Hunter.io account information including remaining requests."""
        if not self.is_configured():
            return {"error": "Not configured"}

        url = f"{self.BASE_URL}/account"
        params = {"api_key": self.api_key}

        try:
            response = self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json().get("data", {})

            return {
                "email": data.get("email"),
                "plan_name": data.get("plan_name"),
                "requests_used": data.get("requests", {}).get("searches", {}).get("used", 0),
                "requests_available": data.get("requests", {}).get("searches", {}).get("available", 0)
            }

        except Exception as e:
            return {"error": str(e)}
