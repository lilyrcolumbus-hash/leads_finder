"""BBB (Better Business Bureau) scraper for finding businesses with complaints."""

import time
import re
from typing import List

import httpx
from bs4 import BeautifulSoup

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class BBBScraper(BaseScraper):
    """Scraper for Better Business Bureau - finds businesses with complaints (pain!)."""

    source = LeadSource.YELP  # Using Yelp source type for review-based
    BASE_URL = "https://www.bbb.org/search"

    # Business categories
    BUSINESS_TYPES = [
        "plumbers",
        "electricians",
        "contractors",
        "auto repair",
        "dentists",
        "lawyers",
        "hvac",
        "roofing",
        "landscaping",
        "cleaning services"
    ]

    # Cities to search
    LOCATIONS = [
        "miami-fl",
        "houston-tx",
        "phoenix-az",
        "los-angeles-ca",
        "chicago-il",
        "atlanta-ga",
        "dallas-tx",
        "denver-co"
    ]

    def __init__(self):
        super().__init__()

    def scrape(self, time_filter: str = None, location: str = None, category: str = None) -> LeadBatch:
        """
        Scrape BBB for businesses (especially those with complaints).

        Args:
            time_filter: Not used
            location: Optional specific location

        Returns:
            LeadBatch with found leads
        """
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        # Use user-provided location or fall back to defaults
        if location:
            # Format for BBB URL: "lima-oh", "houston-tx"
            locations = [location.replace(", ", "-").replace(" ", "-").lower()]
        else:
            locations = self.LOCATIONS[:4]
        # Use custom category if provided, otherwise default list
        business_types = [category] if category else self.BUSINESS_TYPES[:5]

        self.logger.info(f"Starting BBB scrape for {len(business_types)} categories")

        for biz_type in business_types:
            for loc in locations:
                try:
                    leads = self._search_bbb(biz_type, loc)
                    all_leads.extend(leads)
                    self.logger.info(f"Found {len(leads)} {biz_type} in {loc}")
                    time.sleep(2)
                except Exception as e:
                    error_msg = f"Error searching BBB {biz_type} in {loc}: {str(e)}"
                    self.logger.warning(error_msg)
                    batch.errors.append(error_msg)

        # Deduplicate
        unique_leads = list({lead.id: lead for lead in all_leads}.values())

        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(f"BBB scrape complete: {batch.total_found} businesses found")
        return batch

    def _search_bbb(self, business_type: str, location: str) -> List[Lead]:
        """Search BBB for businesses."""
        leads = []

        url = f"https://www.bbb.org/search?find_country=USA&find_loc={location}&find_text={business_type.replace(' ', '%20')}&page=1&touched=1"

        try:
            response = self.client.get(url, timeout=15.0, follow_redirects=True)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find business cards
            listings = soup.find_all('div', class_='result-item') or \
                       soup.find_all('a', class_='result-business-name') or \
                       soup.find_all('div', {'data-testid': 'search-result'})

            # Alternative: look for any business result containers
            if not listings:
                listings = soup.find_all('div', class_=re.compile(r'search.*result|result.*card'))

            for listing in listings[:15]:
                lead = self._parse_bbb_listing(listing, business_type, location)
                if lead:
                    leads.append(lead)

        except (httpx.TransportError, ConnectionError, OSError) as e:
            self.logger.warning(f"BBB connection blocked for {business_type} in {location} (proxy/firewall restriction)")
        except Exception as e:
            self.logger.warning(f"BBB search failed: {e}")

        return leads

    def _parse_bbb_listing(self, listing, business_type: str, location: str) -> Lead | None:
        """Parse a BBB listing."""
        try:
            # Extract business name
            name_elem = listing.find('span', class_='text-blue-medium') or \
                        listing.find('a', class_='result-business-name') or \
                        listing.find('h3') or \
                        listing.find('a')

            if not name_elem:
                return None

            name = name_elem.get_text(strip=True)
            if not name or len(name) < 3:
                return None

            # Extract phone
            phone = None
            phone_elem = listing.find('a', href=re.compile(r'^tel:'))
            if phone_elem:
                phone = phone_elem.get_text(strip=True)

            # Extract address
            address = None
            addr_elem = listing.find('p', class_=re.compile(r'address|location'))
            if addr_elem:
                address = addr_elem.get_text(strip=True)

            # Extract rating/grade
            rating = None
            grade_elem = listing.find('span', class_=re.compile(r'rating|grade'))
            if grade_elem:
                grade_text = grade_elem.get_text(strip=True)
                # Convert letter grades to numbers
                grade_map = {'A+': 5, 'A': 4.5, 'A-': 4, 'B+': 3.5, 'B': 3, 'B-': 2.5,
                            'C+': 2, 'C': 1.5, 'C-': 1, 'D': 0.5, 'F': 0}
                rating = grade_map.get(grade_text, None)

            # Extract complaint count (this is the PAIN indicator!)
            complaints = 0
            has_pain = False
            complaint_elem = listing.find(string=re.compile(r'complaint', re.I))
            if complaint_elem:
                has_pain = True
                # Try to extract number
                match = re.search(r'(\d+)\s*complaint', str(complaint_elem), re.I)
                if match:
                    complaints = int(match.group(1))

            # URL
            url = ""
            link = listing.find('a', href=re.compile(r'/profile/'))
            if link:
                url = f"https://www.bbb.org{link.get('href', '')}"

            # Extract business website from listing
            website = None
            website_elem = listing.find('a', href=re.compile(r'^https?://(?!www\.bbb\.org)'))
            if website_elem:
                href = website_elem.get('href', '')
                if href and 'bbb.org' not in href:
                    website = href

            # Crawl business website for real email
            email = None
            if website:
                try:
                    email = self.extract_email_from_website(website)
                except Exception:
                    pass

            content = f"{business_type} in {location}."
            if complaints > 0:
                content += f" Has {complaints} complaints on BBB."
                has_pain = True

            lead = Lead(
                id=self.generate_id("bbb", f"{name}-{location}"),
                source=self.source,
                title=name,
                content=content,
                url=url,
                phone=phone,
                address=address,
                website=website,
                email=email,
                rating=rating,
                business_type=business_type,
                location=location.replace("-", ", ").title(),
                keywords_matched=["complaints"] if has_pain else [],
                has_pain=has_pain,
                review_count=complaints
            )

            return lead

        except Exception as e:
            self.logger.debug(f"Error parsing BBB listing: {e}")
            return None
