"""Indeed scraper - Find businesses hiring (indicates growth/need for services)."""

import re
import time
from typing import List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class IndeedScraper(BaseScraper):
    """Scraper that searches Indeed for businesses hiring receptionists/customer service."""

    source = LeadSource.INDEED
    BASE_URL = "https://www.indeed.com/jobs"

    # Job titles that indicate a business needs help with phones/communication
    HIRING_QUERIES = [
        "receptionist",
        "front desk",
        "answering service",
        "customer service representative",
        "phone operator",
        "appointment scheduler",
    ]

    def __init__(self, locations: Optional[List[str]] = None):
        super().__init__()
        self.locations = locations or settings.maps_locations
        self.client.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def scrape(self) -> LeadBatch:
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        self.logger.info(f"Starting Indeed scrape: {len(self.HIRING_QUERIES)} queries x {len(self.locations)} locations")

        for query in self.HIRING_QUERIES:
            for location in self.locations:
                try:
                    leads = self._search_indeed(query, location)
                    all_leads.extend(leads)
                    self.logger.info(f"Indeed: Found {len(leads)} results for '{query}' in '{location}'")
                    time.sleep(2)
                except Exception as e:
                    error_msg = f"Indeed error for '{query}' in '{location}': {str(e)}"
                    self.logger.error(error_msg)
                    batch.errors.append(error_msg)

                if len(all_leads) >= settings.max_leads_per_source:
                    break
            if len(all_leads) >= settings.max_leads_per_source:
                break

        unique_leads = list({lead.id: lead for lead in all_leads}.values())
        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(f"Indeed scrape complete: {batch.total_found} leads found")
        return batch

    def _search_indeed(self, query: str, location: str) -> List[Lead]:
        """Search Indeed for job listings."""
        leads = []
        url = f"{self.BASE_URL}?q={quote(query)}&l={quote(location)}&sort=date"

        try:
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.text, "lxml")
            leads = self._parse_indeed_results(soup, query, location)
        except Exception as e:
            self.logger.debug(f"Indeed search failed: {e}")
            leads = self._fallback_search(query, location)

        return leads

    def _parse_indeed_results(self, soup: BeautifulSoup, query: str, location: str) -> List[Lead]:
        """Parse Indeed search results."""
        leads = []

        # Indeed job cards
        job_cards = soup.select(
            'div.job_seen_beacon, '
            'div.jobsearch-SerpJobCard, '
            'div.cardOutline, '
            'li.css-5lfssm'
        )

        if not job_cards:
            return self._extract_from_raw(soup, query, location)

        for card in job_cards:
            try:
                # Job title
                title_el = card.select_one(
                    'h2.jobTitle a, '
                    'a.jcs-JobTitle, '
                    'h2 a span'
                )
                job_title = title_el.get_text(strip=True) if title_el else None
                if not job_title:
                    continue

                # Company name
                company_el = card.select_one(
                    'span.companyName, '
                    'span[data-testid="company-name"], '
                    'span.css-63koeb'
                )
                company = company_el.get_text(strip=True) if company_el else None
                if not company:
                    continue

                # Location
                loc_el = card.select_one(
                    'div.companyLocation, '
                    'div[data-testid="text-location"]'
                )
                job_location = loc_el.get_text(strip=True) if loc_el else location

                # Link
                link_el = card.select_one("a[href]")
                href = link_el.get("href", "") if link_el else ""
                job_url = f"https://www.indeed.com{href}" if href.startswith("/") else href

                # Snippet
                snippet_el = card.select_one("div.job-snippet, td.snip")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                lead = Lead(
                    id=self.generate_id("indeed", company, job_title),
                    source=self.source,
                    title=f"{company} - Hiring: {job_title}",
                    content=f"Hiring {job_title} in {job_location}. {snippet}",
                    url=job_url,
                    company=company,
                    location=job_location,
                    niche=query,
                    keywords_matched=[query, "hiring"],
                )
                leads.append(lead)
            except Exception as e:
                self.logger.debug(f"Error parsing Indeed card: {e}")

        return leads

    def _extract_from_raw(self, soup: BeautifulSoup, query: str, location: str) -> List[Lead]:
        """Extract from raw HTML as fallback."""
        leads = []
        for link in soup.find_all("a", href=re.compile(r"/rc/clk|/viewjob")):
            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            href = link.get("href", "")
            job_url = f"https://www.indeed.com{href}" if href.startswith("/") else href

            lead = Lead(
                id=self.generate_id("indeed_raw", title, location),
                source=self.source,
                title=title,
                content=f"Job posting in {location} for {query}",
                url=job_url,
                niche=query,
                location=location,
                keywords_matched=[query, "hiring"],
            )
            leads.append(lead)

        return leads

    def _fallback_search(self, query: str, location: str) -> List[Lead]:
        """Use Google to find Indeed listings."""
        leads = []
        search_query = f'site:indeed.com "{query}" "{location}"'

        try:
            url = f"https://www.google.com/search?q={quote(search_query)}&num=10"
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.text, "lxml")

            for result in soup.select("div.g"):
                title_el = result.select_one("h3")
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                link_el = result.select_one("a")
                link = link_el.get("href", "") if link_el else ""
                snippet_el = result.select_one("div.VwiC3b")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                # Extract company name from Indeed title pattern "Job Title - Company Name"
                company = None
                if " - " in title:
                    parts = title.split(" - ")
                    if len(parts) >= 2:
                        company = parts[1].replace(" | Indeed.com", "").strip()

                lead = Lead(
                    id=self.generate_id("indeed_g", title, location),
                    source=self.source,
                    title=title,
                    content=snippet,
                    url=link,
                    company=company,
                    niche=query,
                    location=location,
                    keywords_matched=[query, "hiring"],
                )
                leads.append(lead)
        except Exception as e:
            self.logger.debug(f"Indeed fallback failed: {e}")

        return leads
