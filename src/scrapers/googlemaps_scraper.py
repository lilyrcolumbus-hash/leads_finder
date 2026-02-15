#!/usr/bin/env python3
"""
Google Maps Scraper - Find local businesses with contact info
Extracts: Name, Phone, Website, Address, Rating, Reviews

Method: Web scraping Google Maps search results
"""

import re
import time
import requests
from typing import List, Optional, Dict
from datetime import datetime
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from ..config import settings
from ..utils.models import Lead, LeadSource, LeadBatch
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class GoogleMapsScraper:
    """
    Scrapes Google Maps for local businesses.

    Finds: Dental offices, HVAC companies, Law firms, etc.
    Extracts: Name, Phone, Website, Address, Rating
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

        # Business categories relevant for AI receptionist
        self.business_categories = [
            "dentist",
            "dental office",
            "hvac contractor",
            "plumber",
            "lawyer",
            "law firm",
            "medical clinic",
            "doctor office",
            "chiropractor",
            "veterinarian",
            "auto repair",
            "hair salon",
            "spa",
            "real estate agent",
            "insurance agent",
            "accountant",
            "fitness center",
            "yoga studio"
        ]

        # Default cities to search if no location provided
        self.default_cities = [
            "Miami, FL",
            "Los Angeles, CA",
            "Houston, TX",
            "Phoenix, AZ",
            "Dallas, TX",
            "San Diego, CA",
            "Austin, TX",
            "Denver, CO",
            "Atlanta, GA",
            "Chicago, IL"
        ]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def scrape(self, time_filter: str = "week", location: str = "",
               category: str = "") -> LeadBatch:
        """
        Scrape Google Maps for local businesses.

        Args:
            time_filter: Not used (businesses don't have time filter)
            location: City/State to search (e.g., "Miami, FL")
            category: Business category (e.g., "dentist")

        Returns:
            LeadBatch with found businesses
        """
        all_leads = []

        # Determine locations to search
        # Only use defaults if NO location was provided at all
        if location and location.strip():
            locations = [location.strip()]
            logger.info(f"Google Maps: Using user location: '{location.strip()}'")
        else:
            locations = self.default_cities[:3]
            logger.info(f"Google Maps: No location provided, using defaults: {locations}")

        # Determine categories to search
        categories = [category.strip()] if category and category.strip() else self.business_categories[:4]

        logger.info(f"Google Maps Scraper: Searching {len(categories)} categories in {len(locations)} locations")

        for loc in locations:
            for cat in categories:
                try:
                    leads = self._search_maps(cat, loc)
                    all_leads.extend(leads)
                    logger.info(f"Found {len(leads)} businesses for '{cat}' in {loc}")
                    time.sleep(2)  # Be respectful with rate limiting
                except Exception as e:
                    logger.error(f"Error searching {cat} in {loc}: {e}")

        # Deduplicate by phone number or name
        unique_leads = self._deduplicate(all_leads)

        # Try to find emails for businesses with websites (all of them)
        unique_leads = self._enrich_with_emails(unique_leads)

        logger.info(f"Google Maps Scraper: Found {len(unique_leads)} unique businesses")

        return LeadBatch(
            leads=unique_leads,
            source=LeadSource.GOOGLE_MAPS,
            scraped_at=datetime.now()
        )

    def _search_maps(self, category: str, location: str) -> List[Lead]:
        """Search Google Maps for a category in a location."""
        leads = []

        query = f"{category} in {location}"
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&tbm=lcl"

        try:
            response = self.session.get(search_url, timeout=15)

            if response.status_code != 200:
                logger.warning(f"Google returned status {response.status_code}")
                return leads

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find business listings
            # Google's HTML structure changes frequently, so we try multiple selectors
            business_divs = soup.find_all('div', {'class': re.compile(r'VkpGBb|rllt__details')})

            if not business_divs:
                # Try alternative structure
                business_divs = soup.find_all('div', {'data-attrid': re.compile(r'kc:/local')})

            for div in business_divs[:10]:  # Limit to 10 per search
                try:
                    lead = self._parse_business(div, category, location)
                    if lead:
                        leads.append(lead)
                except Exception as e:
                    logger.debug(f"Error parsing business: {e}")
                    continue

            # Also try to extract from JSON-LD if present
            json_leads = self._extract_from_jsonld(soup, category, location)
            leads.extend(json_leads)

        except (ConnectionError, OSError) as e:
            logger.warning(f"Google Maps connection blocked for '{category}' in {location} (proxy/firewall restriction)")
        except Exception as e:
            logger.error(f"Error fetching Google Maps: {e}")

        return leads

    def _parse_business(self, div, category: str, location: str) -> Optional[Lead]:
        """Parse a business div into a Lead."""
        try:
            # Extract business name
            name_elem = div.find(['span', 'div'], {'class': re.compile(r'OSrXXb|dbg0pd')})
            if not name_elem:
                name_elem = div.find('a', {'class': re.compile(r'rllt__link')})

            name = name_elem.get_text(strip=True) if name_elem else None
            if not name:
                return None

            # Extract phone number
            phone = None
            phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            text = div.get_text()
            phone_match = re.search(phone_pattern, text)
            if phone_match:
                phone = phone_match.group()

            # Extract address
            address = None
            addr_elem = div.find(['span', 'div'], {'class': re.compile(r'rllt__details|lqhpac')})
            if addr_elem:
                address = addr_elem.get_text(strip=True)

            # Extract rating
            rating = None
            rating_elem = div.find(['span'], {'class': re.compile(r'yi40Hd|Aq14fc')})
            if rating_elem:
                try:
                    rating = float(rating_elem.get_text(strip=True))
                except:
                    pass

            # Extract website (if available in snippet)
            website = None
            link_elem = div.find('a', href=re.compile(r'http'))
            if link_elem and 'google.com' not in link_elem.get('href', ''):
                website = link_elem.get('href')

            # Determine industry
            industry = self._map_category_to_industry(category)

            lead = Lead(
                id=f"gmaps_{hash(f'{name}{phone}{location}')}",
                source=LeadSource.GOOGLE_MAPS,
                title=name,
                content=f"{category.title()} business in {location}." + (f"\nAddress: {address}" if address else ""),
                url=f"https://www.google.com/search?q={quote_plus(name + ' ' + location)}",
                company=name,
                phone=phone,
                website=website,
                industry=industry,
                found_at=datetime.now(),
                pain_score=50,  # Base score for local businesses
                keywords_matched=[category],
                is_qualified=True,
                extra_data={
                    'address': address,
                    'rating': rating,
                    'category': category,
                    'location': location,
                    'platform': 'google_maps'
                }
            )

            return lead

        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return None

    def _extract_from_jsonld(self, soup, category: str, location: str) -> List[Lead]:
        """Extract business info from JSON-LD structured data."""
        leads = []

        try:
            scripts = soup.find_all('script', {'type': 'application/ld+json'})

            for script in scripts:
                try:
                    import json
                    data = json.loads(script.string)

                    # Handle both single object and array
                    items = data if isinstance(data, list) else [data]

                    for item in items:
                        if item.get('@type') in ['LocalBusiness', 'Organization', 'MedicalBusiness', 'LegalService']:
                            name = item.get('name')
                            if not name:
                                continue

                            phone = item.get('telephone')
                            website = item.get('url')

                            address_obj = item.get('address', {})
                            address = None
                            if isinstance(address_obj, dict):
                                address = f"{address_obj.get('streetAddress', '')} {address_obj.get('addressLocality', '')} {address_obj.get('addressRegion', '')}"

                            lead = Lead(
                                id=f"gmaps_json_{hash(f'{name}{phone}')}",
                                source=LeadSource.GOOGLE_MAPS,
                                title=name,
                                content=f"{category.title()} in {location}",
                                url=website or f"https://www.google.com/search?q={quote_plus(name)}",
                                company=name,
                                phone=phone,
                                website=website,
                                industry=self._map_category_to_industry(category),
                                found_at=datetime.now(),
                                pain_score=50,
                                keywords_matched=[category],
                                is_qualified=True,
                                extra_data={
                                    'address': address,
                                    'rating': item.get('aggregateRating', {}).get('ratingValue'),
                                    'category': category
                                }
                            )
                            leads.append(lead)

                except:
                    continue

        except Exception as e:
            logger.debug(f"JSON-LD extraction error: {e}")

        return leads

    def _enrich_with_emails(self, leads: List[Lead]) -> List[Lead]:
        """Try to find emails by visiting business websites."""
        for lead in leads:
            if lead.website and not lead.email:
                try:
                    email = self._find_email_on_website(lead.website)
                    if email:
                        lead.email = email
                        logger.info(f"Found email for {lead.company}: {email}")
                except Exception as e:
                    logger.debug(f"Error finding email for {lead.company}: {e}")

                time.sleep(1)  # Rate limiting

        return leads

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
        "username", "email@", "your@", "name@",
        "example", "test@", "null@",
    }

    _PREFERRED_PREFIXES = [
        "info", "contact", "hello", "hola", "office", "sales",
        "enquiries", "inquiries", "service", "support",
    ]

    def _is_real_email(self, email: str) -> bool:
        """Check if an email looks like a real business email (not junk)."""
        email_lower = email.lower().strip()

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

        # Skip image file extensions embedded in emails
        if any(ext in email_lower for ext in ['.png', '.jpg', '.gif', '.svg', '.webp']):
            return False

        return True

    def _pick_best_email(self, emails: list) -> Optional[str]:
        """Pick the best email from a list, preferring business-contact ones."""
        if not emails:
            return None
        if len(emails) == 1:
            return emails[0]

        for pref in self._PREFERRED_PREFIXES:
            for email in emails:
                if email.lower().startswith(pref):
                    return email

        return emails[0]

    def _find_email_on_website(self, url: str) -> Optional[str]:
        """Scrape a website homepage and many sub-pages to find real emails."""
        try:
            if not url.startswith('http'):
                url = 'https://' + url

            base = url.rstrip('/')
            all_emails: list = []

            # Expanded list of pages to crawl for emails
            pages = [
                '', '/contact', '/contact-us', '/contacto',
                '/about', '/about-us', '/sobre-nosotros',
                '/team', '/our-team', '/staff',
                '/support', '/help', '/faq',
                '/locations', '/location',
                '/services', '/our-services',
                '/get-in-touch', '/reach-us',
                '/connect', '/info', '/company',
            ]

            for page in pages:
                try:
                    page_url = base + page
                    response = self.session.get(page_url, timeout=8, allow_redirects=True)
                    if response.status_code == 200:
                        html = response.text

                        # Standard email regex
                        found = re.findall(
                            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                            html
                        )
                        all_emails.extend(e for e in found if self._is_real_email(e))

                        # Also check mailto: links
                        mailto_matches = re.findall(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', html)
                        all_emails.extend(e for e in mailto_matches if self._is_real_email(e))

                        # Check for emails in JSON-LD structured data
                        try:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(html, 'html.parser')
                            for script in soup.find_all('script', {'type': 'application/ld+json'}):
                                if script.string:
                                    import json
                                    ld_data = json.loads(script.string)
                                    items = ld_data if isinstance(ld_data, list) else [ld_data]
                                    for item in items:
                                        if isinstance(item, dict):
                                            for key in ['email', 'contactPoint']:
                                                val = item.get(key)
                                                if isinstance(val, str) and '@' in val:
                                                    clean = val.replace('mailto:', '')
                                                    if self._is_real_email(clean):
                                                        all_emails.append(clean)
                                                elif isinstance(val, dict) and val.get('email'):
                                                    clean = val['email'].replace('mailto:', '')
                                                    if self._is_real_email(clean):
                                                        all_emails.append(clean)
                        except Exception:
                            pass

                        # If we found good emails, no need to crawl more pages
                        real_so_far = [e for e in all_emails if self._is_real_email(e)]
                        if len(set(e.lower() for e in real_so_far)) >= 2:
                            break

                except Exception:
                    continue
                time.sleep(0.3)

            # Deduplicate preserving order
            seen = set()
            unique = []
            for e in all_emails:
                lower = e.lower()
                if lower not in seen:
                    seen.add(lower)
                    unique.append(e)

            return self._pick_best_email(unique)

        except Exception as e:
            logger.debug(f"Error fetching {url}: {e}")
            return None

    def _map_category_to_industry(self, category: str) -> str:
        """Map search category to industry."""
        category_lower = category.lower()

        industry_map = {
            'dentist': 'Healthcare',
            'dental': 'Healthcare',
            'doctor': 'Healthcare',
            'medical': 'Healthcare',
            'clinic': 'Healthcare',
            'chiropractor': 'Healthcare',
            'veterinarian': 'Healthcare',
            'lawyer': 'Legal',
            'law firm': 'Legal',
            'attorney': 'Legal',
            'hvac': 'Home Services',
            'plumber': 'Home Services',
            'contractor': 'Home Services',
            'roofing': 'Home Services',
            'auto repair': 'Automotive',
            'mechanic': 'Automotive',
            'salon': 'Beauty & Wellness',
            'spa': 'Beauty & Wellness',
            'fitness': 'Fitness',
            'gym': 'Fitness',
            'yoga': 'Fitness',
            'real estate': 'Real Estate',
            'insurance': 'Insurance',
            'accountant': 'Financial'
        }

        for key, value in industry_map.items():
            if key in category_lower:
                return value

        return 'Local Business'

    def _deduplicate(self, leads: List[Lead]) -> List[Lead]:
        """Remove duplicate businesses."""
        seen = set()
        unique = []

        for lead in leads:
            # Use phone or name+location as unique key
            key = lead.phone or f"{lead.company}_{lead.extra_data.get('location', '')}"
            if key and key not in seen:
                seen.add(key)
                unique.append(lead)

        return unique

    def search_category(self, category: str, locations: List[str]) -> LeadBatch:
        """
        Search for a specific business category in multiple locations.

        Args:
            category: Business type (e.g., "dentist")
            locations: List of cities/states

        Returns:
            LeadBatch with found businesses
        """
        all_leads = []

        for location in locations:
            leads = self._search_maps(category, location)
            all_leads.extend(leads)
            time.sleep(2)

        unique_leads = self._deduplicate(all_leads)

        return LeadBatch(
            leads=unique_leads,
            source=LeadSource.GOOGLE_MAPS,
            scraped_at=datetime.now()
        )
