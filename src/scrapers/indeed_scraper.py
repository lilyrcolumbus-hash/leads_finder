"""Indeed job listing scraper for finding companies hiring receptionists/customer service."""

import re
import time
from typing import List, Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class IndeedScraper(BaseScraper):
    """
    Scraper that searches Indeed for companies hiring receptionists,
    customer service reps, and similar roles.

    These companies are ideal prospects for AI receptionist services
    because they clearly have a need for phone/customer handling.
    """

    source = LeadSource.INDEED
    BASE_URL = "https://www.indeed.com"

    def __init__(self):
        super().__init__()
        self.job_queries = settings.indeed_job_queries
        self.locations = settings.indeed_locations
        # Use a browser-like User-Agent for Indeed
        self.client.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def scrape(self) -> LeadBatch:
        """
        Scrape Indeed for job listings related to receptionist/customer service.

        Returns:
            LeadBatch with company leads found
        """
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        self.logger.info(
            f"Starting Indeed scrape: {len(self.job_queries)} queries x "
            f"{len(self.locations)} locations"
        )

        for query in self.job_queries:
            for location in self.locations:
                try:
                    leads = self._search_jobs(query, location)
                    all_leads.extend(leads)
                    self.logger.info(
                        f"Indeed: '{query}' in {location} -> {len(leads)} leads"
                    )
                    # Rate limiting - be respectful
                    time.sleep(3)
                except Exception as e:
                    error_msg = f"Indeed error for '{query}' in {location}: {str(e)}"
                    self.logger.warning(error_msg)
                    batch.errors.append(error_msg)

                # Stop early if we have enough leads
                if len(all_leads) >= settings.max_leads_per_source * 2:
                    break

            if len(all_leads) >= settings.max_leads_per_source * 2:
                break

        # Deduplicate by company name (keep first occurrence)
        seen_companies = set()
        unique_leads = []
        for lead in all_leads:
            company_key = (lead.company or "").lower().strip()
            if company_key and company_key not in seen_companies:
                seen_companies.add(company_key)
                unique_leads.append(lead)
            elif not company_key:
                unique_leads.append(lead)

        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(
            f"Indeed scrape complete: {batch.total_found} unique company leads "
            f"({len(seen_companies)} unique companies)"
        )
        return batch

    def _search_jobs(self, query: str, location: str) -> List[Lead]:
        """
        Search Indeed for job listings matching query and location.

        Args:
            query: Job search query (e.g. "receptionist")
            location: Location string (e.g. "Miami, FL")

        Returns:
            List of leads extracted from job listings
        """
        leads = []

        url = (
            f"{self.BASE_URL}/jobs"
            f"?q={quote_plus(query)}"
            f"&l={quote_plus(location)}"
            f"&sort=date"  # Most recent first
            f"&fromage=14"  # Last 14 days
        )

        try:
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.text, "lxml")

            # Indeed uses various card structures for job listings
            job_cards = soup.select(
                "div.job_seen_beacon, "
                "div.jobsearch-ResultsList div.result, "
                "div[data-jk], "
                "li div.cardOutline, "
                "div.slider_container div.slider_item"
            )

            if not job_cards:
                # Fallback: try to find any structured job data
                job_cards = soup.find_all("div", class_=re.compile(r"job|result|card", re.I))

            for card in job_cards[:15]:  # Limit per page
                lead = self._parse_job_card(card, query, location)
                if lead:
                    leads.append(lead)

        except Exception as e:
            self.logger.debug(f"Indeed search failed for '{query}' in {location}: {e}")
            raise

        return leads

    def _parse_job_card(
        self, card, search_query: str, location: str
    ) -> Optional[Lead]:
        """
        Parse an Indeed job card into a Lead object.

        The key data we extract:
        - Company name (this is the prospect)
        - Job title (indicates what they need)
        - Location (where the business is)
        - Job URL (for reference)

        Args:
            card: BeautifulSoup element of the job card
            search_query: Original search query
            location: Search location

        Returns:
            Lead object or None
        """
        try:
            # Extract job title
            title_elem = (
                card.select_one("h2.jobTitle a, h2.jobTitle span, a.jcs-JobTitle") or
                card.select_one("h2 a, h2 span") or
                card.find("a", attrs={"data-jk": True})
            )
            job_title = title_elem.get_text(strip=True) if title_elem else ""

            # Extract company name - this is our prospect
            company_elem = (
                card.select_one("span[data-testid='company-name'], span.companyName") or
                card.select_one("span.company, a.companyOverviewLink") or
                card.find("span", class_=re.compile(r"company", re.I))
            )
            company_name = company_elem.get_text(strip=True) if company_elem else ""

            # Extract location
            location_elem = (
                card.select_one("div[data-testid='text-location'], div.companyLocation") or
                card.select_one("span.location, div.location") or
                card.find("div", class_=re.compile(r"location", re.I))
            )
            job_location = location_elem.get_text(strip=True) if location_elem else location

            # Extract salary if available
            salary_elem = (
                card.select_one("div.salary-snippet-container, span.salaryText") or
                card.select_one("div[class*='salary'], span[class*='salary']")
            )
            salary_text = salary_elem.get_text(strip=True) if salary_elem else ""

            # Extract job snippet/description
            snippet_elem = (
                card.select_one("div.job-snippet, div[class*='snippet']") or
                card.select_one("table.jobCardShelfContainer")
            )
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

            # Build job URL
            job_link = None
            link_elem = card.select_one("a[data-jk], h2.jobTitle a, a.jcs-JobTitle")
            if link_elem:
                href = link_elem.get("href", "")
                if href.startswith("/"):
                    job_link = f"{self.BASE_URL}{href}"
                elif href.startswith("http"):
                    job_link = href

            job_key = card.get("data-jk") or ""
            if not job_link and job_key:
                job_link = f"{self.BASE_URL}/viewjob?jk={job_key}"

            if not job_link:
                job_link = f"{self.BASE_URL}/jobs?q={quote_plus(search_query)}&l={quote_plus(location)}"

            # Skip if we couldn't extract meaningful data
            if not company_name and not job_title:
                return None

            # Build content text for keyword matching and AI scoring
            content_parts = []
            if job_title:
                content_parts.append(f"Hiring: {job_title}")
            if company_name:
                content_parts.append(f"Company: {company_name}")
            if job_location:
                content_parts.append(f"Location: {job_location}")
            if salary_text:
                content_parts.append(f"Salary: {salary_text}")
            if snippet:
                content_parts.append(f"Description: {snippet}")
            content_parts.append(
                f"This company is actively hiring for '{search_query}' - "
                "potential prospect for AI receptionist service."
            )

            content = "\n".join(content_parts)

            # Match keywords from the job content
            keywords = self.find_keywords(content)
            # Always add the search context as a keyword match
            keywords.append(f"hiring:{search_query}")

            lead = Lead(
                id=self.generate_id("indeed", company_name or job_title, job_location),
                source=self.source,
                title=f"[HIRING] {company_name or 'Company'} - {job_title or search_query}",
                content=content,
                url=job_link,
                company=company_name or None,
                keywords_matched=keywords,
            )

            return lead

        except Exception as e:
            self.logger.debug(f"Error parsing Indeed job card: {e}")
            return None
