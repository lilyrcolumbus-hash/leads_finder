"""Hunter.io email enrichment for leads without emails."""

import re
import time
from typing import List, Optional
from urllib.parse import urlparse

import httpx

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger("HunterEnricher")


class HunterEnricher:
    """Find emails for leads using Hunter.io API."""

    BASE_URL = "https://api.hunter.io/v2"

    def __init__(self):
        self.api_key = settings.hunter_api_key
        self.client = httpx.Client(timeout=30.0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def is_configured(self) -> bool:
        """Check if Hunter.io API is configured."""
        return bool(self.api_key)

    def extract_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL."""
        if not url:
            return None
        try:
            # Handle URLs without scheme
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            parsed = urlparse(url)
            domain = parsed.netloc
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            # Skip social media and common platforms
            skip_domains = [
                'reddit.com', 'news.ycombinator.com', 'producthunt.com',
                'twitter.com', 'x.com', 'facebook.com', 'linkedin.com',
                'youtube.com', 'instagram.com', 'github.com', 'medium.com',
                'google.com', 'yelp.com', 'trustpilot.com'
            ]
            if any(domain.endswith(skip) for skip in skip_domains):
                return None
            return domain if domain else None
        except Exception:
            return None

    def find_email_for_domain(self, domain: str) -> Optional[dict]:
        """
        Find email for a domain using Hunter.io domain search.

        Returns dict with email and confidence if found.
        """
        if not self.api_key or not domain:
            return None

        try:
            url = f"{self.BASE_URL}/domain-search"
            params = {
                "domain": domain,
                "api_key": self.api_key,
                "limit": 1  # Just get the first/best email
            }

            response = self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                emails = data.get("data", {}).get("emails", [])
                if emails:
                    best_email = emails[0]
                    return {
                        "email": best_email.get("value"),
                        "confidence": best_email.get("confidence", 0),
                        "first_name": best_email.get("first_name"),
                        "last_name": best_email.get("last_name"),
                        "position": best_email.get("position"),
                        "domain": domain
                    }
            elif response.status_code == 401:
                logger.error("Hunter.io API key is invalid")
            elif response.status_code == 429:
                logger.warning("Hunter.io rate limit reached")

        except Exception as e:
            logger.debug(f"Hunter.io error for {domain}: {e}")

        return None

    def enrich_leads(self, leads: List, max_lookups: int = 20) -> tuple:
        """
        Enrich leads without emails using Hunter.io.

        Args:
            leads: List of Lead objects
            max_lookups: Maximum number of API calls to make

        Returns:
            Tuple of (enriched_count, leads_list)
        """
        if not self.is_configured():
            logger.warning("Hunter.io API key not configured")
            return 0, leads

        enriched_count = 0
        lookups_made = 0
        domains_checked = set()  # Avoid duplicate domain lookups

        for lead in leads:
            # Skip if already has email
            if lead.email:
                continue

            # Stop if we've hit the limit
            if lookups_made >= max_lookups:
                logger.info(f"Hunter.io lookup limit reached ({max_lookups})")
                break

            # Try to get domain from URL or company
            domain = self.extract_domain(lead.url)

            # Skip if no valid domain or already checked
            if not domain or domain in domains_checked:
                continue

            domains_checked.add(domain)

            # Look up email
            result = self.find_email_for_domain(domain)
            lookups_made += 1

            if result and result.get("email"):
                lead.email = result["email"]
                # Store additional info in extra_data
                if lead.extra_data is None:
                    lead.extra_data = {}
                lead.extra_data["hunter_data"] = result
                enriched_count += 1
                logger.info(f"Found email for {domain}: {result['email']}")

            # Small delay to respect rate limits
            time.sleep(0.5)

        logger.info(f"Hunter.io enrichment: {enriched_count} emails found from {lookups_made} lookups")
        return enriched_count, leads


def enrich_leads_with_hunter(leads: List, max_lookups: int = 20) -> tuple:
    """
    Convenience function to enrich leads with Hunter.io.

    Returns:
        Tuple of (enriched_count, leads_list)
    """
    with HunterEnricher() as enricher:
        return enricher.enrich_leads(leads, max_lookups)
