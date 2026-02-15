"""Yelp scraper for finding businesses with phone/service complaints."""

import time
import re
import json
from typing import List
from urllib.parse import quote

from bs4 import BeautifulSoup

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class YelpScraper(BaseScraper):
    """Scraper for Yelp - find businesses with bad reviews about phone/service."""

    source = LeadSource.YELP
    BASE_URL = "https://www.yelp.com/search"

    def __init__(self):
        super().__init__()
        # Business categories likely to need phone answering
        self.categories = [
            "plumbers",
            "hvac",
            "electricians",
            "dentists",
            "doctors",
            "lawyers",
            "contractors",
            "auto repair",
            "salons",
            "veterinarians"
        ]
        # Better headers to avoid blocking
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def scrape(self, time_filter: str = "week", location: str = "") -> LeadBatch:
        """
        Scrape Yelp for businesses.

        Args:
            time_filter: Time range (not used by Yelp, but kept for API consistency)
            location: Location to search (city, state, zip code)
        """
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        self.search_location = location
        location_msg = f" in {location}" if location else ""
        self.logger.info(f"Starting Yelp scrape for businesses{location_msg}")

        # Search businesses in target categories
        for category in self.categories[:5]:
            try:
                leads = self._search_category(category, location)
                all_leads.extend(leads)
                self.logger.info(f"Found {len(leads)} businesses in '{category}'")
                time.sleep(2)  # More delay to avoid blocking
            except Exception as e:
                error_msg = f"Error searching Yelp for '{category}': {str(e)}"
                self.logger.warning(error_msg)
                batch.errors.append(error_msg)

        # Deduplicate
        unique_leads = list({lead.company: lead for lead in all_leads if lead.company}.values())

        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(f"Yelp scrape complete: {batch.total_found} businesses found")
        return batch

    def _search_category(self, category: str, user_location: str = "") -> List[Lead]:
        """Search Yelp for businesses in a category."""
        leads = []

        # Use user-provided location or default to major US cities
        if user_location:
            locations = [user_location]
        else:
            locations = ["Miami, FL", "Houston, TX", "Phoenix, AZ", "Los Angeles, CA", "Chicago, IL"]

        for location in locations[:3]:
            url = f"{self.BASE_URL}?find_desc={quote(category)}&find_loc={quote(location)}"

            try:
                response = self.session.get(url, headers=self.headers, timeout=15)

                if response.status_code != 200:
                    self.logger.debug(f"Yelp returned {response.status_code} for {category} in {location}")
                    continue

                soup = BeautifulSoup(response.text, "lxml")

                # Method 1: Try to find JSON data embedded in the page
                leads_from_json = self._extract_from_json(response.text, category, location)
                if leads_from_json:
                    leads.extend(leads_from_json)
                    continue

                # Method 2: Parse HTML directly with multiple selectors
                leads_from_html = self._extract_from_html(soup, category, location)
                leads.extend(leads_from_html)

                time.sleep(1)

            except Exception as e:
                self.logger.debug(f"Yelp search failed for '{category}' in {location}: {e}")

        return leads

    def _extract_from_json(self, html: str, category: str, location: str) -> List[Lead]:
        """Try to extract business data from embedded JSON."""
        leads = []

        try:
            # Look for JSON-LD data
            json_pattern = r'<script type="application/ld\+json">(.*?)</script>'
            matches = re.findall(json_pattern, html, re.DOTALL)

            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict) and data.get("@type") == "LocalBusiness":
                        lead = self._json_to_lead(data, category, location)
                        if lead:
                            leads.append(lead)
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get("@type") == "LocalBusiness":
                                lead = self._json_to_lead(item, category, location)
                                if lead:
                                    leads.append(lead)
                except:
                    continue

            # Also try to find embedded search results data
            search_data_pattern = r'"searchPageProps":\s*(\{.*?\})\s*[,}]'
            search_match = re.search(search_data_pattern, html)
            if search_match:
                try:
                    # This is complex nested JSON, just look for business names and URLs
                    biz_pattern = r'"name":\s*"([^"]+)".*?"businessUrl":\s*"([^"]+)"'
                    biz_matches = re.findall(biz_pattern, html)
                    for name, url in biz_matches[:15]:
                        if name and len(name) > 2:
                            lead = Lead(
                                id=self.generate_id("yelp", name, location),
                                source=self.source,
                                title=f"{name} - {category.title()}",
                                content=f"{name} is a {category} business in {location}. Found on Yelp.",
                                url=f"https://www.yelp.com{url}" if url.startswith("/") else url,
                                company=name,
                                keywords_matched=[f"category:{category}", f"location:{location}"],
                                has_pain=True,
                            )
                            leads.append(lead)
                except:
                    pass

        except Exception as e:
            self.logger.debug(f"JSON extraction failed: {e}")

        return leads

    def _json_to_lead(self, data: dict, category: str, location: str) -> Lead | None:
        """Convert JSON-LD LocalBusiness to Lead."""
        try:
            name = data.get("name", "")
            if not name or len(name) < 3:
                return None

            url = data.get("url", "")
            phone = data.get("telephone", "")
            address = ""
            if "address" in data:
                addr = data["address"]
                if isinstance(addr, dict):
                    address = f"{addr.get('streetAddress', '')}, {addr.get('addressLocality', '')}, {addr.get('addressRegion', '')}"

            rating = data.get("aggregateRating", {}).get("ratingValue", "")

            # Try to extract email from business website (not Yelp URL)
            email = None
            website = url if url and "yelp.com" not in url else None
            if website:
                try:
                    email = self.extract_email_from_website(website)
                except Exception:
                    pass

            lead = Lead(
                id=self.generate_id("yelp", name, location),
                source=self.source,
                title=f"{name} - {category.title()}",
                content=f"{name} is a {category} business in {location}. Rating: {rating}/5. {address}",
                url=url,
                company=name,
                phone=phone,
                address=address,
                website=website,
                email=email,
                rating=float(rating) if rating else None,
                keywords_matched=[f"category:{category}", f"location:{location}"],
                has_pain=True,
            )
            return lead
        except:
            return None

    def _extract_from_html(self, soup: BeautifulSoup, category: str, location: str) -> List[Lead]:
        """Extract businesses from HTML using multiple methods."""
        leads = []

        # Try multiple selectors for business names
        selectors = [
            ("a", {"href": lambda x: x and "/biz/" in str(x)}),
            ("h3", {}),
            ("span", {"class": lambda x: x and "businessName" in str(x) if x else False}),
        ]

        seen_names = set()

        for tag, attrs in selectors:
            elements = soup.find_all(tag, attrs)[:20]

            for elem in elements:
                try:
                    # Get the text and clean it
                    name = elem.get_text(strip=True)

                    # Skip if too short, already seen, or looks like navigation
                    if not name or len(name) < 3 or len(name) > 100:
                        continue
                    if name.lower() in seen_names:
                        continue
                    if any(skip in name.lower() for skip in ["yelp", "sign up", "log in", "write a review", "more", "map"]):
                        continue

                    seen_names.add(name.lower())

                    # Get URL if available
                    url = ""
                    if tag == "a":
                        url = elem.get("href", "")
                    else:
                        link = elem.find_parent("a") or elem.find("a")
                        if link:
                            url = link.get("href", "")

                    if url and not url.startswith("http"):
                        url = f"https://www.yelp.com{url}"

                    # Only include if it looks like a business page
                    if url and "/biz/" not in url:
                        continue

                    lead = Lead(
                        id=self.generate_id("yelp", name, location),
                        source=self.source,
                        title=f"{name} - {category.title()}",
                        content=f"{name} is a {category} business in {location}. Found on Yelp - local service business.",
                        url=url or f"https://www.yelp.com/search?find_desc={quote(name)}&find_loc={quote(location)}",
                        company=name,
                        keywords_matched=[f"category:{category}", f"location:{location}"],
                        has_pain=True,
                    )
                    leads.append(lead)

                except Exception as e:
                    continue

        return leads
