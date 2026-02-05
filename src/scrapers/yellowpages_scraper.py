"""Yellow Pages scraper for finding local businesses."""

import time
import re
import json
from typing import List
from urllib.parse import quote
from bs4 import BeautifulSoup

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class YellowPagesScraper(BaseScraper):
    """Scraper for Yellow Pages business directory."""

    source = LeadSource.GOOGLE_MAPS  # Using same source type for local businesses

    # Business categories to search
    BUSINESS_TYPES = [
        "plumber",
        "electrician",
        "hvac",
        "dentist",
        "lawyer",
        "accountant",
        "contractor",
        "auto repair",
        "veterinarian",
        "landscaping",
        "roofing",
        "cleaning service",
    ]

    # Locations to search
    LOCATIONS = [
        "Miami, FL",
        "Houston, TX",
        "Phoenix, AZ",
        "Los Angeles, CA",
        "Chicago, IL",
        "Dallas, TX",
        "Atlanta, GA",
        "Denver, CO"
    ]

    def __init__(self):
        super().__init__()
        # Better headers to avoid blocking
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    def scrape(self, time_filter: str = None, location: str = None) -> LeadBatch:
        """Scrape Yellow Pages for business listings."""
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        locations = [location] if location else self.LOCATIONS[:3]
        business_types = self.BUSINESS_TYPES[:5]

        self.logger.info(f"Starting Yellow Pages scrape for {len(business_types)} business types")

        for biz_type in business_types:
            for loc in locations:
                try:
                    leads = self._search_businesses(biz_type, loc)
                    all_leads.extend(leads)
                    self.logger.info(f"Found {len(leads)} {biz_type} businesses in {loc}")
                    time.sleep(2)
                except Exception as e:
                    error_msg = f"Error searching {biz_type} in {loc}: {str(e)}"
                    self.logger.warning(error_msg)
                    batch.errors.append(error_msg)

        # Deduplicate
        unique_leads = list({lead.id: lead for lead in all_leads}.values())

        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(f"Yellow Pages scrape complete: {batch.total_found} businesses found")
        return batch

    def _search_businesses(self, business_type: str, location: str) -> List[Lead]:
        """Search Yellow Pages for a business type in a location."""
        leads = []

        # Format location for URL
        loc_formatted = location.replace(", ", "-").replace(" ", "-").lower()
        search_term = business_type.replace(" ", "-").lower()

        url = f"https://www.yellowpages.com/{loc_formatted}/{search_term}"

        try:
            response = self.session.get(url, headers=self.headers, timeout=15)

            if response.status_code != 200:
                self.logger.debug(f"Yellow Pages returned {response.status_code}")
                return leads

            soup = BeautifulSoup(response.text, 'lxml')

            # Method 1: Try JSON-LD structured data
            json_leads = self._extract_from_json(response.text, business_type, location)
            if json_leads:
                return json_leads

            # Method 2: Multiple HTML selectors
            # Try organic results
            listings = soup.select('div.result, div.v-card, article.result')

            if not listings:
                # Try info cards
                listings = soup.select('[class*="info"], [class*="listing"], [class*="business"]')

            if not listings:
                # Find any links to business pages
                biz_links = soup.find_all('a', href=lambda x: x and '/mip/' in str(x))
                for link in biz_links[:20]:
                    name = link.get_text(strip=True)
                    if name and len(name) > 2 and len(name) < 100:
                        href = link.get('href', '')
                        lead = Lead(
                            id=self.generate_id("yp", f"{name}-{location}"),
                            source=self.source,
                            title=name,
                            content=f"{business_type.title()} in {location}. Found on Yellow Pages.",
                            url=f"https://www.yellowpages.com{href}" if href.startswith('/') else href,
                            business_type=business_type,
                            keywords_matched=[f"category:{business_type}", f"location:{location}"],
                            has_pain=True,
                        )
                        leads.append(lead)
                return leads

            for listing in listings[:20]:
                lead = self._parse_listing(listing, business_type, location)
                if lead:
                    leads.append(lead)

        except Exception as e:
            self.logger.debug(f"Yellow Pages search failed: {e}")

        return leads

    def _extract_from_json(self, html: str, business_type: str, location: str) -> List[Lead]:
        """Extract business data from JSON-LD."""
        leads = []

        try:
            # Look for JSON-LD structured data
            json_pattern = r'<script type="application/ld\+json">(.*?)</script>'
            matches = re.findall(json_pattern, html, re.DOTALL)

            for match in matches:
                try:
                    data = json.loads(match)

                    # Handle list of businesses
                    if isinstance(data, list):
                        for item in data:
                            lead = self._json_to_lead(item, business_type, location)
                            if lead:
                                leads.append(lead)
                    elif isinstance(data, dict):
                        # Check for itemList
                        if "itemListElement" in data:
                            for item in data.get("itemListElement", []):
                                item_data = item.get("item", item)
                                lead = self._json_to_lead(item_data, business_type, location)
                                if lead:
                                    leads.append(lead)
                        else:
                            lead = self._json_to_lead(data, business_type, location)
                            if lead:
                                leads.append(lead)
                except json.JSONDecodeError:
                    continue

        except Exception as e:
            self.logger.debug(f"JSON extraction failed: {e}")

        return leads

    def _json_to_lead(self, data: dict, business_type: str, location: str) -> Lead | None:
        """Convert JSON-LD data to Lead."""
        try:
            if not isinstance(data, dict):
                return None

            name = data.get("name", "")
            if not name or len(name) < 3:
                return None

            # Skip if it's not a local business type
            data_type = data.get("@type", "")
            if data_type and data_type not in ["LocalBusiness", "Organization", "Place", "ProfessionalService"]:
                if not any(biz in str(data_type) for biz in ["Business", "Service", "Store"]):
                    return None

            url = data.get("url", "")
            phone = data.get("telephone", "")

            address = ""
            addr_data = data.get("address", {})
            if isinstance(addr_data, dict):
                parts = [
                    addr_data.get("streetAddress", ""),
                    addr_data.get("addressLocality", ""),
                    addr_data.get("addressRegion", ""),
                    addr_data.get("postalCode", "")
                ]
                address = ", ".join([p for p in parts if p])

            rating = None
            agg_rating = data.get("aggregateRating", {})
            if agg_rating:
                rating = agg_rating.get("ratingValue")
                if rating:
                    try:
                        rating = float(rating)
                    except:
                        rating = None

            lead = Lead(
                id=self.generate_id("yp", f"{name}-{location}"),
                source=self.source,
                title=name,
                content=f"{business_type.title()} in {location}. {address}",
                url=url,
                phone=phone,
                address=address,
                rating=rating,
                business_type=business_type,
                keywords_matched=[f"category:{business_type}", f"location:{location}"],
                has_pain=True,
            )
            return lead

        except Exception as e:
            self.logger.debug(f"Error converting JSON to lead: {e}")
            return None

    def _parse_listing(self, listing, business_type: str, location: str) -> Lead | None:
        """Parse a Yellow Pages listing into a Lead."""
        try:
            # Try multiple selectors for name
            name_elem = (
                listing.find('a', class_='business-name') or
                listing.find('h2') or
                listing.find('a', href=lambda x: x and '/mip/' in str(x)) or
                listing.find(class_=lambda x: x and 'name' in str(x).lower() if x else False)
            )
            if not name_elem:
                return None

            name = name_elem.get_text(strip=True)
            if not name or len(name) < 3:
                return None

            # Extract phone - try multiple patterns
            phone = None
            phone_elem = (
                listing.find('div', class_='phones') or
                listing.find(class_='phone') or
                listing.find('a', href=lambda x: x and 'tel:' in str(x))
            )
            if phone_elem:
                phone = phone_elem.get_text(strip=True)
            else:
                # Try regex for phone pattern
                phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', listing.get_text())
                if phone_match:
                    phone = phone_match.group()

            # Extract address
            address = None
            addr_elem = (
                listing.find('div', class_='adr') or
                listing.find('p', class_='adr') or
                listing.find(class_=lambda x: x and 'address' in str(x).lower() if x else False)
            )
            if addr_elem:
                address = addr_elem.get_text(strip=True)

            # Extract website
            website = None
            website_elem = listing.find('a', class_='track-visit-website') or listing.find('a', text=re.compile(r'website', re.I))
            if website_elem:
                website = website_elem.get('href', '')

            # Build URL
            url = ""
            link_elem = listing.find('a', class_='business-name') or listing.find('a', href=lambda x: x and '/mip/' in str(x))
            if link_elem:
                href = link_elem.get('href', '')
                url = f"https://www.yellowpages.com{href}" if href.startswith('/') else href

            lead = Lead(
                id=self.generate_id("yp", f"{name}-{location}"),
                source=self.source,
                title=name,
                content=f"{business_type.title()} in {location}. {address or ''}",
                url=url,
                phone=phone,
                address=address,
                website=website,
                business_type=business_type,
                keywords_matched=[f"category:{business_type}", f"location:{location}"],
                has_pain=True,
            )

            return lead

        except Exception as e:
            self.logger.debug(f"Error parsing YP listing: {e}")
            return None
