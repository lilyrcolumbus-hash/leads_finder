"""Indeed scraper for finding companies hiring receptionists."""

import time
from typing import List
from urllib.parse import quote

from bs4 import BeautifulSoup

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class IndeedScraper(BaseScraper):
    """Scraper for Indeed job postings - companies hiring receptionists need AI solutions."""

    source = LeadSource.INDEED
    BASE_URL = "https://www.indeed.com/jobs"

    def __init__(self):
        super().__init__()
        # Job titles that indicate need for receptionist/phone handling
        self.job_queries = [
            "receptionist",
            "front desk",
            "phone answering",
            "appointment scheduler",
            "customer service representative",
            "office administrator",
            "virtual assistant"
        ]

    def scrape(self, time_filter: str = "week") -> LeadBatch:
        """
        Scrape Indeed for companies hiring receptionists.

        Companies posting these jobs = potential customers for AI receptionist.
        """
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        # Map time filter to Indeed's date posted filter
        time_map = {
            "day": "1",
            "week": "7",
            "month": "30",
            "quarter": "30",
            "year": "30",
            "all": ""
        }
        date_filter = time_map.get(time_filter, "7")

        self.logger.info(f"Starting Indeed scrape for receptionist jobs")

        for query in self.job_queries[:4]:  # Limit queries for speed
            try:
                leads = self._search_jobs(query, date_filter)
                all_leads.extend(leads)
                self.logger.info(f"Found {len(leads)} job postings for '{query}'")
                time.sleep(1)  # Rate limiting
            except Exception as e:
                error_msg = f"Error searching Indeed for '{query}': {str(e)}"
                self.logger.warning(error_msg)
                batch.errors.append(error_msg)

        # Deduplicate by company name
        unique_leads = list({lead.company: lead for lead in all_leads if lead.company}.values())

        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(f"Indeed scrape complete: {batch.total_found} companies found")
        return batch

    def _search_jobs(self, query: str, date_filter: str) -> List[Lead]:
        """Search Indeed for job postings."""
        leads = []

        # Build URL
        url = f"{self.BASE_URL}?q={quote(query)}&sort=date"
        if date_filter:
            url += f"&fromage={date_filter}"

        try:
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.text, "lxml")

            # Find job cards
            job_cards = soup.find_all("div", class_=lambda x: x and "job_seen_beacon" in str(x))

            # Also try other selectors
            if not job_cards:
                job_cards = soup.find_all("div", {"data-jk": True})

            if not job_cards:
                job_cards = soup.find_all("td", class_="resultContent")

            for card in job_cards[:15]:  # Limit per query
                lead = self._parse_job_card(card, query)
                if lead:
                    leads.append(lead)

        except Exception as e:
            self.logger.debug(f"Indeed search failed for '{query}': {e}")

        return leads

    def _parse_job_card(self, card, search_query: str) -> Lead | None:
        """Parse a job card into a Lead."""
        try:
            # Extract company name
            company_elem = card.find("span", {"data-testid": "company-name"})
            if not company_elem:
                company_elem = card.find("span", class_=lambda x: x and "company" in str(x).lower())

            company = company_elem.get_text(strip=True) if company_elem else None

            if not company:
                return None

            # Extract job title
            title_elem = card.find("h2", class_=lambda x: x and "jobTitle" in str(x))
            if not title_elem:
                title_elem = card.find("a", {"data-jk": True})

            title = title_elem.get_text(strip=True) if title_elem else search_query

            # Extract location
            location_elem = card.find("div", {"data-testid": "text-location"})
            if not location_elem:
                location_elem = card.find("div", class_=lambda x: x and "location" in str(x).lower())

            location = location_elem.get_text(strip=True) if location_elem else ""

            # Extract link
            link_elem = card.find("a", href=True)
            link = f"https://www.indeed.com{link_elem['href']}" if link_elem else ""

            # Create lead - company hiring receptionist = needs AI solution
            lead = Lead(
                id=self.generate_id("indeed", company, title),
                source=self.source,
                title=f"Hiring: {title}",
                content=f"{company} is hiring a {title} in {location}. This company needs phone/reception help and could benefit from an AI receptionist solution.",
                url=link,
                company=company,
                keywords_matched=[f"hiring:{search_query}", "receptionist needed"],
            )

            return lead

        except Exception as e:
            self.logger.debug(f"Error parsing job card: {e}")
            return None
