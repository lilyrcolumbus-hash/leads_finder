"""Enhanced Indeed scraper with customizable search parameters.

This is the core engine for the AI Sales Team lead finder.
Supports custom keywords, locations, date ranges, job types, and salary filters.
"""

import re
import time
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from src.utils.logger import get_logger
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


@dataclass
class IndeedSearchParams:
    """Search parameters for Indeed job search."""

    keywords: List[str] = field(default_factory=lambda: ["receptionist"])
    location: str = "United States"
    date_range: int = 14  # days: 1, 3, 7, 14, 30
    job_type: str = ""  # fulltime, parttime, contract, temporary, internship, ""=all
    salary_min: str = ""  # e.g. "$40,000", "$20/hr"
    remote: str = ""  # "remote", "temporarily_remote", ""=all
    sort_by: str = "date"  # "date" or "relevance"
    radius: int = 25  # miles: 5, 10, 15, 25, 50, 100
    max_results: int = 50
    experience_level: str = ""  # entry_level, mid_level, senior_level


class IndeedSearchScraper(BaseScraper):
    """
    Enhanced Indeed scraper with full search customization.

    Designed as the core tool for an AI sales team to find
    companies that are actively hiring - these are warm leads
    for any B2B service.
    """

    source = LeadSource.INDEED
    BASE_URL = "https://www.indeed.com"

    def __init__(self, params: Optional[IndeedSearchParams] = None):
        super().__init__()
        self.params = params or IndeedSearchParams()
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
        """Run the Indeed search with configured parameters."""
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        self.logger.info(
            f"Indeed Search: {len(self.params.keywords)} keywords "
            f"in '{self.params.location}' | "
            f"last {self.params.date_range} days | "
            f"type: {self.params.job_type or 'all'}"
        )

        for keyword in self.params.keywords:
            try:
                # Search multiple pages if needed
                for page in range(0, min(3, (self.params.max_results // 15) + 1)):
                    leads = self._search_page(keyword, page * 10)
                    all_leads.extend(leads)

                    self.logger.info(
                        f"Indeed: '{keyword}' page {page + 1} -> {len(leads)} leads"
                    )

                    # Rate limiting
                    time.sleep(2)

                    if len(all_leads) >= self.params.max_results:
                        break

            except Exception as e:
                error_msg = f"Indeed error for '{keyword}': {str(e)}"
                self.logger.warning(error_msg)
                batch.errors.append(error_msg)

            if len(all_leads) >= self.params.max_results:
                break

        # Deduplicate by company name
        seen_companies = set()
        unique_leads = []
        for lead in all_leads:
            company_key = (lead.company or "").lower().strip()
            if company_key and company_key not in seen_companies:
                seen_companies.add(company_key)
                unique_leads.append(lead)
            elif not company_key:
                unique_leads.append(lead)

        batch.leads = unique_leads[:self.params.max_results]
        batch.total_found = len(unique_leads)

        self.logger.info(
            f"Indeed search complete: {batch.total_found} unique leads "
            f"({len(seen_companies)} unique companies)"
        )
        return batch

    def _build_url(self, keyword: str, start: int = 0) -> str:
        """Build Indeed search URL with all filters."""
        params = [
            f"q={quote_plus(keyword)}",
            f"l={quote_plus(self.params.location)}",
            f"sort={self.params.sort_by}",
            f"fromage={self.params.date_range}",
            f"radius={self.params.radius}",
        ]

        if start > 0:
            params.append(f"start={start}")

        if self.params.job_type:
            params.append(f"jt={self.params.job_type}")

        if self.params.salary_min:
            params.append(f"salary={quote_plus(self.params.salary_min)}")

        if self.params.remote:
            params.append(f"remotejob={self.params.remote}")

        if self.params.experience_level:
            params.append(f"explvl={self.params.experience_level}")

        return f"{self.BASE_URL}/jobs?{'&'.join(params)}"

    def _search_page(self, keyword: str, start: int = 0) -> List[Lead]:
        """Search a single page of Indeed results."""
        leads = []
        url = self._build_url(keyword, start)

        try:
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.text, "lxml")

            job_cards = soup.select(
                "div.job_seen_beacon, "
                "div.jobsearch-ResultsList div.result, "
                "div[data-jk], "
                "li div.cardOutline, "
                "div.slider_container div.slider_item"
            )

            if not job_cards:
                job_cards = soup.find_all(
                    "div", class_=re.compile(r"job|result|card", re.I)
                )

            for card in job_cards[:15]:
                lead = self._parse_job_card(card, keyword)
                if lead:
                    leads.append(lead)

        except Exception as e:
            self.logger.debug(f"Indeed page search failed: {e}")
            raise

        return leads

    def _parse_job_card(self, card, search_keyword: str) -> Optional[Lead]:
        """Parse an Indeed job card into a Lead object."""
        try:
            # Job title
            title_elem = (
                card.select_one("h2.jobTitle a, h2.jobTitle span, a.jcs-JobTitle")
                or card.select_one("h2 a, h2 span")
                or card.find("a", attrs={"data-jk": True})
            )
            job_title = title_elem.get_text(strip=True) if title_elem else ""

            # Company name
            company_elem = (
                card.select_one(
                    "span[data-testid='company-name'], span.companyName"
                )
                or card.select_one("span.company, a.companyOverviewLink")
                or card.find("span", class_=re.compile(r"company", re.I))
            )
            company_name = company_elem.get_text(strip=True) if company_elem else ""

            # Location
            location_elem = (
                card.select_one(
                    "div[data-testid='text-location'], div.companyLocation"
                )
                or card.select_one("span.location, div.location")
                or card.find("div", class_=re.compile(r"location", re.I))
            )
            job_location = (
                location_elem.get_text(strip=True)
                if location_elem
                else self.params.location
            )

            # Salary
            salary_elem = (
                card.select_one("div.salary-snippet-container, span.salaryText")
                or card.select_one("div[class*='salary'], span[class*='salary']")
            )
            salary_text = salary_elem.get_text(strip=True) if salary_elem else ""

            # Description snippet
            snippet_elem = (
                card.select_one("div.job-snippet, div[class*='snippet']")
                or card.select_one("table.jobCardShelfContainer")
            )
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

            # Job URL
            job_link = None
            link_elem = card.select_one(
                "a[data-jk], h2.jobTitle a, a.jcs-JobTitle"
            )
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
                job_link = self._build_url(search_keyword)

            # Skip empty cards
            if not company_name and not job_title:
                return None

            # Build content
            content_parts = []
            if job_title:
                content_parts.append(f"Position: {job_title}")
            if company_name:
                content_parts.append(f"Company: {company_name}")
            if job_location:
                content_parts.append(f"Location: {job_location}")
            if salary_text:
                content_parts.append(f"Salary: {salary_text}")
            if snippet:
                content_parts.append(f"Description: {snippet}")

            content = "\n".join(content_parts)

            # Keywords matched
            keywords = self.find_keywords(content)
            keywords.append(f"hiring:{search_keyword}")

            return Lead(
                id=self.generate_id("indeed", company_name or job_title, job_location),
                source=self.source,
                title=f"{company_name or 'Company'} - {job_title or search_keyword}",
                content=content,
                url=job_link,
                company=company_name or None,
                keywords_matched=keywords,
            )

        except Exception as e:
            self.logger.debug(f"Error parsing job card: {e}")
            return None
