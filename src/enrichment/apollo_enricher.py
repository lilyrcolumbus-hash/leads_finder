"""
Apollo.io Integration for Lead Enrichment

Apollo.io provides:
- Verified email addresses (95%+ accuracy)
- Direct phone numbers (mobile/direct dial)
- Company data (size, revenue, industry)
- LinkedIn profile URLs
- Job titles and seniority

API Documentation: https://apolloio.github.io/apollo-api-docs/

PRICING (as of 2024):
- Free: 50 credits/month
- Basic: $49/month - 200 credits
- Professional: $99/month - 400 credits
- Organization: Custom pricing

Each enrichment uses 1 credit.
"""

import os
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import requests

from src.utils.models import Lead
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ApolloContact:
    """Enriched contact data from Apollo.io"""
    email: Optional[str] = None
    email_status: Optional[str] = None  # verified, guessed, unavailable
    phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    seniority: Optional[str] = None  # c_suite, vp, director, manager, etc.
    linkedin_url: Optional[str] = None

    # Company data
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    company_phone: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    industry: Optional[str] = None
    employees: Optional[int] = None
    employees_range: Optional[str] = None
    revenue: Optional[str] = None
    revenue_range: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None

    # Metadata
    apollo_id: Optional[str] = None
    confidence_score: Optional[float] = None
    raw_data: Optional[Dict[str, Any]] = None


class ApolloEnricher:
    """
    Apollo.io API client for lead enrichment.

    Usage:
        enricher = ApolloEnricher(api_key="your_api_key")

        # Enrich by email
        contact = enricher.enrich_by_email("john@company.com")

        # Enrich by domain + name
        contact = enricher.enrich_by_domain("company.com", first_name="John", last_name="Doe")

        # Search for people at company
        contacts = enricher.search_people(domain="company.com", titles=["owner", "ceo"])
    """

    BASE_URL = "https://api.apollo.io/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Apollo enricher.

        Args:
            api_key: Apollo.io API key. If not provided, looks for APOLLO_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("APOLLO_API_KEY")
        self.session = requests.Session()
        self._rate_limit_remaining = None
        self._rate_limit_reset = None

    def is_configured(self) -> bool:
        """Check if Apollo API key is configured."""
        return bool(self.api_key)

    def _make_request(self, endpoint: str, method: str = "POST",
                      data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make API request to Apollo.io

        Args:
            endpoint: API endpoint (e.g., "/people/match")
            method: HTTP method
            data: Request payload

        Returns:
            Response JSON or None if error
        """
        if not self.is_configured():
            logger.warning("Apollo.io API key not configured")
            return None

        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache"
        }

        # Add API key to request data
        if data is None:
            data = {}
        data["api_key"] = self.api_key

        try:
            if method == "POST":
                response = self.session.post(url, json=data, headers=headers, timeout=30)
            else:
                response = self.session.get(url, params=data, headers=headers, timeout=30)

            # Track rate limits
            self._rate_limit_remaining = response.headers.get("X-Rate-Limit-Remaining")
            self._rate_limit_reset = response.headers.get("X-Rate-Limit-Reset")

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logger.warning("Apollo.io rate limit exceeded")
                return None
            else:
                logger.error(f"Apollo.io API error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Apollo.io request failed: {e}")
            return None

    def enrich_by_email(self, email: str) -> Optional[ApolloContact]:
        """
        Enrich a lead by email address.

        This is the most accurate method - uses 1 credit.

        Args:
            email: Email address to enrich

        Returns:
            ApolloContact with enriched data or None
        """
        data = {
            "email": email,
            "reveal_personal_emails": True,
            "reveal_phone_number": True
        }

        result = self._make_request("/people/match", data=data)

        if result and result.get("person"):
            return self._parse_person(result["person"])
        return None

    def enrich_by_domain(self, domain: str, first_name: Optional[str] = None,
                         last_name: Optional[str] = None,
                         title: Optional[str] = None) -> Optional[ApolloContact]:
        """
        Enrich a lead by company domain and optional name/title.

        Args:
            domain: Company domain (e.g., "company.com")
            first_name: Contact's first name
            last_name: Contact's last name
            title: Job title to search for

        Returns:
            ApolloContact with enriched data or None
        """
        data = {
            "domain": domain,
            "reveal_personal_emails": True,
            "reveal_phone_number": True
        }

        if first_name:
            data["first_name"] = first_name
        if last_name:
            data["last_name"] = last_name
        if title:
            data["title"] = title

        result = self._make_request("/people/match", data=data)

        if result and result.get("person"):
            return self._parse_person(result["person"])
        return None

    def search_people(self, domain: Optional[str] = None,
                      company_name: Optional[str] = None,
                      titles: Optional[List[str]] = None,
                      seniority: Optional[List[str]] = None,
                      limit: int = 5) -> List[ApolloContact]:
        """
        Search for people at a company.

        Useful for finding decision makers when you only have company info.
        Uses 1 credit per person returned.

        Args:
            domain: Company domain
            company_name: Company name
            titles: List of job titles to search for (e.g., ["owner", "ceo", "founder"])
            seniority: List of seniority levels (e.g., ["owner", "c_suite", "vp"])
            limit: Maximum number of results

        Returns:
            List of ApolloContact objects
        """
        data = {
            "per_page": limit,
            "reveal_personal_emails": True,
            "reveal_phone_number": True
        }

        # Build organization query
        if domain:
            data["q_organization_domains"] = domain
        if company_name:
            data["q_organization_name"] = company_name

        # Filter by titles
        if titles:
            data["person_titles"] = titles

        # Filter by seniority
        if seniority:
            data["person_seniorities"] = seniority
        else:
            # Default to decision makers
            data["person_seniorities"] = ["owner", "founder", "c_suite", "vp", "director"]

        result = self._make_request("/mixed_people/search", data=data)

        contacts = []
        if result and result.get("people"):
            for person in result["people"][:limit]:
                contact = self._parse_person(person)
                if contact:
                    contacts.append(contact)

        return contacts

    def get_company_info(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Get company information by domain.

        Args:
            domain: Company domain

        Returns:
            Dict with company data or None
        """
        data = {"domain": domain}
        result = self._make_request("/organizations/enrich", data=data)

        if result and result.get("organization"):
            org = result["organization"]
            return {
                "name": org.get("name"),
                "domain": org.get("primary_domain"),
                "phone": org.get("phone"),
                "industry": org.get("industry"),
                "employees": org.get("estimated_num_employees"),
                "employees_range": self._get_employee_range(org.get("estimated_num_employees")),
                "revenue": org.get("annual_revenue_printed"),
                "linkedin_url": org.get("linkedin_url"),
                "city": org.get("city"),
                "state": org.get("state"),
                "country": org.get("country"),
                "description": org.get("short_description"),
                "founded_year": org.get("founded_year"),
                "technologies": org.get("technologies", [])
            }
        return None

    def _parse_person(self, person: Dict) -> Optional[ApolloContact]:
        """Parse Apollo person response into ApolloContact."""
        if not person:
            return None

        org = person.get("organization") or {}

        return ApolloContact(
            email=person.get("email"),
            email_status=person.get("email_status"),
            phone=person["phone_numbers"][0].get("sanitized_number") if isinstance(person.get("phone_numbers"), list) and person["phone_numbers"] else None,
            mobile_phone=person.get("mobile_phone"),
            first_name=person.get("first_name"),
            last_name=person.get("last_name"),
            title=person.get("title"),
            seniority=person.get("seniority"),
            linkedin_url=person.get("linkedin_url"),
            company_name=org.get("name"),
            company_domain=org.get("primary_domain"),
            company_phone=org.get("phone"),
            company_linkedin_url=org.get("linkedin_url"),
            industry=org.get("industry"),
            employees=org.get("estimated_num_employees"),
            employees_range=self._get_employee_range(org.get("estimated_num_employees")),
            revenue=org.get("annual_revenue_printed"),
            city=person.get("city") or org.get("city"),
            state=person.get("state") or org.get("state"),
            country=person.get("country") or org.get("country"),
            apollo_id=person.get("id"),
            confidence_score=person.get("email_confidence"),
            raw_data=person
        )

    @staticmethod
    def _get_employee_range(employees: Optional[int]) -> Optional[str]:
        """Convert employee count to range string."""
        if not employees:
            return None
        if employees <= 10:
            return "1-10"
        elif employees <= 50:
            return "11-50"
        elif employees <= 200:
            return "51-200"
        elif employees <= 500:
            return "201-500"
        else:
            return "500+"

    def get_credits_remaining(self) -> Optional[int]:
        """Get remaining API credits (if available from last request)."""
        return self._rate_limit_remaining


def enrich_lead_with_apollo(lead: Lead, enricher: ApolloEnricher) -> Lead:
    """
    Enrich a single lead with Apollo.io data.

    Tries multiple strategies:
    1. If email exists - enrich by email
    2. If website exists - search by domain
    3. If company name exists - search by company name

    Args:
        lead: Lead to enrich
        enricher: ApolloEnricher instance

    Returns:
        Enriched Lead
    """
    if not enricher.is_configured():
        logger.info("Apollo.io not configured, skipping enrichment")
        return lead

    contact = None

    # Strategy 1: Enrich by email (most accurate)
    if lead.email:
        contact = enricher.enrich_by_email(lead.email)

    # Strategy 2: Search by website domain
    if not contact and lead.website:
        # Extract domain from website
        domain = lead.website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]

        # Search for decision makers
        contacts = enricher.search_people(
            domain=domain,
            titles=["owner", "founder", "ceo", "president", "director", "manager"],
            limit=1
        )
        if contacts:
            contact = contacts[0]

    # Strategy 3: Search by company name
    if not contact and lead.company:
        contacts = enricher.search_people(
            company_name=lead.company,
            titles=["owner", "founder", "ceo", "president"],
            limit=1
        )
        if contacts:
            contact = contacts[0]

    # Apply enriched data to lead
    if contact:
        # Contact info
        if contact.email and not lead.email:
            lead.email = contact.email
        if contact.phone and not lead.phone:
            lead.phone = contact.phone
        if contact.mobile_phone:
            lead.phone = contact.mobile_phone  # Prefer mobile

        # Name
        if contact.first_name and contact.last_name:
            lead.name = f"{contact.first_name} {contact.last_name}"

        # Professional info
        if contact.title and not lead.position:
            lead.position = contact.title
        if contact.linkedin_url and not lead.linkedin:
            lead.linkedin = contact.linkedin_url

        # Company info
        if contact.company_name and not lead.company:
            lead.company = contact.company_name
        if contact.company_domain and not lead.website:
            lead.website = f"https://{contact.company_domain}"
        if contact.industry and not lead.industry:
            lead.industry = contact.industry
        if contact.employees_range and not lead.employees:
            lead.employees = contact.employees_range
        if contact.revenue and not lead.revenue:
            lead.revenue = contact.revenue

        # Location
        if contact.city and contact.state:
            lead.location = f"{contact.city}, {contact.state}"
        if contact.country:
            lead.country = contact.country

        # Store extra data
        if not lead.extra_data:
            lead.extra_data = {}
        lead.extra_data["apollo_enriched"] = True
        lead.extra_data["apollo_id"] = contact.apollo_id
        lead.extra_data["email_status"] = contact.email_status
        lead.extra_data["seniority"] = contact.seniority

        logger.info(f"Enriched lead with Apollo: {lead.company or lead.name}")

    return lead


def enrich_leads_with_apollo(leads: List[Lead], api_key: Optional[str] = None,
                              max_enrichments: int = 15,
                              delay_seconds: float = 0.5) -> List[Lead]:
    """
    Enrich multiple leads with Apollo.io data.

    Args:
        leads: List of leads to enrich
        api_key: Apollo API key (or uses env var)
        max_enrichments: Maximum number of leads to enrich (to control costs)
        delay_seconds: Delay between API calls

    Returns:
        List of enriched leads
    """
    enricher = ApolloEnricher(api_key=api_key)

    if not enricher.is_configured():
        logger.warning("Apollo.io API key not configured. Set APOLLO_API_KEY env var or pass api_key.")
        return leads

    enriched_count = 0

    for lead in leads:
        if enriched_count >= max_enrichments:
            logger.info(f"Reached max enrichments ({max_enrichments}), stopping")
            break

        # Skip if already has email AND phone
        if lead.email and lead.phone:
            continue

        # Enrich
        try:
            enrich_lead_with_apollo(lead, enricher)
            enriched_count += 1

            # Rate limiting delay
            if delay_seconds > 0:
                time.sleep(delay_seconds)

        except Exception as e:
            logger.error(f"Error enriching lead: {e}")
            continue

    logger.info(f"Apollo.io enriched {enriched_count} leads")
    return leads
