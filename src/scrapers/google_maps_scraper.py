"""Google Maps/Places API scraper for business leads with review analysis."""

import time
from typing import List, Optional, Tuple
from urllib.parse import quote

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class GoogleMapsScraper(BaseScraper):
    """
    Scraper using Google Places API to find businesses and analyze their reviews.

    Searches for businesses by type and location, extracts contact info,
    and analyzes reviews to detect communication pain points.
    """

    source = LeadSource.GOOGLE_MAPS

    # Google Places API endpoints
    PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

    def __init__(self):
        super().__init__()
        # Use dedicated Places API key if available, otherwise fall back to general Google API key
        self.api_key = settings.google_places_api_key or settings.google_api_key
        self.business_types = settings.google_maps_business_types
        self.locations = settings.google_maps_locations
        self.review_pain_keywords = settings.review_pain_keywords
        self.max_results = settings.google_maps_max_results_per_search
        self.max_reviews = settings.google_maps_max_reviews_per_business
        self.min_reviews = settings.google_maps_min_reviews

    def scrape(self) -> LeadBatch:
        """
        Scrape Google Maps for business leads.

        Returns:
            LeadBatch with found leads including pain analysis
        """
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        if not self.api_key:
            error_msg = "Google Places API key not configured (GOOGLE_PLACES_API_KEY or GOOGLE_API_KEY)"
            self.logger.warning(error_msg)
            batch.errors.append(error_msg)
            return batch

        self.logger.info(
            f"Starting Google Maps scrape: {len(self.business_types)} business types, "
            f"{len(self.locations)} locations"
        )

        # Search for each business type in each location
        for business_type in self.business_types:
            for location in self.locations:
                try:
                    leads = self._search_businesses(business_type, location)
                    all_leads.extend(leads)
                    self.logger.info(
                        f"Found {len(leads)} businesses: {business_type} in {location}"
                    )
                    time.sleep(1)  # Rate limiting between searches
                except Exception as e:
                    error_msg = f"Error searching {business_type} in {location}: {str(e)}"
                    self.logger.error(error_msg)
                    batch.errors.append(error_msg)

        # Deduplicate by place_id
        unique_leads = list({lead.place_id: lead for lead in all_leads if lead.place_id}.values())

        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        # Count leads with pain detected
        pain_count = sum(1 for lead in batch.leads if lead.has_pain)
        self.logger.info(
            f"Google Maps scrape complete: {batch.total_found} businesses found, "
            f"{pain_count} with communication pain detected"
        )

        return batch

    def _search_businesses(self, business_type: str, location: str) -> List[Lead]:
        """
        Search for businesses of a specific type in a location.

        Args:
            business_type: Type of business (e.g., "plumber", "dentist")
            location: Location to search (e.g., "Miami, FL")

        Returns:
            List of Lead objects with business info and pain analysis
        """
        leads = []
        query = f"{business_type} in {location}"

        url = (
            f"{self.PLACES_SEARCH_URL}"
            f"?query={quote(query)}"
            f"&key={self.api_key}"
        )

        try:
            response = self.fetch_url(url)
            data = response.json()

            if data.get("status") != "OK":
                error_status = data.get("status", "Unknown error")
                error_message = data.get("error_message", "")
                self.logger.warning(f"Places API error: {error_status} - {error_message}")
                return leads

            results = data.get("results", [])[:self.max_results]

            for place in results:
                place_id = place.get("place_id")
                if not place_id:
                    continue

                # Get detailed info including reviews
                lead = self._get_place_details(place_id, business_type, location)
                if lead:
                    leads.append(lead)
                    time.sleep(0.5)  # Rate limiting between detail requests

        except Exception as e:
            self.logger.debug(f"Search failed for '{query}': {e}")
            raise

        return leads

    def _get_place_details(
        self, place_id: str, business_type: str, location: str
    ) -> Optional[Lead]:
        """
        Get detailed information about a place including reviews.

        Args:
            place_id: Google Place ID
            business_type: Type of business
            location: Search location

        Returns:
            Lead object or None if not relevant
        """
        fields = [
            "name",
            "formatted_address",
            "formatted_phone_number",
            "international_phone_number",
            "website",
            "rating",
            "user_ratings_total",
            "reviews",
            "url",
            "business_status"
        ]

        url = (
            f"{self.PLACE_DETAILS_URL}"
            f"?place_id={place_id}"
            f"&fields={','.join(fields)}"
            f"&key={self.api_key}"
        )

        try:
            response = self.fetch_url(url)
            data = response.json()

            if data.get("status") != "OK":
                return None

            result = data.get("result", {})

            # Skip if business is not operational
            if result.get("business_status") != "OPERATIONAL":
                return None

            # Skip if too few reviews
            review_count = result.get("user_ratings_total", 0)
            if review_count < self.min_reviews:
                return None

            # Analyze reviews for pain points
            reviews = result.get("reviews", [])
            has_pain, pain_score, pain_reviews, pain_summary = self._analyze_reviews(reviews)

            # Extract contact info
            name = result.get("name", "Unknown Business")
            phone = result.get("formatted_phone_number") or result.get("international_phone_number")
            address = result.get("formatted_address", "")
            website = result.get("website")
            rating = result.get("rating")
            maps_url = result.get("url", f"https://www.google.com/maps/place/?q=place_id:{place_id}")

            # Build content from reviews
            review_texts = [r.get("text", "") for r in reviews[:5]]
            content = f"Business: {name}\nLocation: {address}\n\nRecent Reviews:\n" + "\n---\n".join(review_texts[:3])

            # Find general pain keywords in content
            keywords = self.find_keywords(content)
            keywords.extend(self._find_review_keywords(content))
            keywords = list(set(keywords))  # Deduplicate

            lead = Lead(
                id=self.generate_id("gmaps", place_id),
                source=self.source,
                title=name,
                content=content,
                url=maps_url,
                keywords_matched=keywords,
                # Contact info
                company=name,
                phone=phone,
                address=address,
                website=website,
                email=self._extract_email_from_website(website) if website else None,
                # Google Maps specific
                rating=rating,
                review_count=review_count,
                business_type=business_type,
                place_id=place_id,
                # Pain detection
                has_pain=has_pain,
                pain_score=pain_score,
                pain_reviews=pain_reviews,
                pain_summary=pain_summary
            )

            return lead

        except Exception as e:
            self.logger.debug(f"Error getting place details for {place_id}: {e}")
            return None

    def _analyze_reviews(self, reviews: List[dict]) -> Tuple[bool, Optional[float], List[str], Optional[str]]:
        """
        Analyze reviews for communication pain points.

        Args:
            reviews: List of review objects from Google Places API

        Returns:
            Tuple of (has_pain, pain_score, pain_reviews, pain_summary)
        """
        if not reviews:
            return False, None, [], None

        pain_reviews = []
        total_pain_matches = 0

        for review in reviews[:self.max_reviews]:
            text = review.get("text", "").lower()
            rating = review.get("rating", 5)

            # Check for pain keywords
            matched_keywords = []
            for keyword in self.review_pain_keywords:
                if keyword.lower() in text:
                    matched_keywords.append(keyword)
                    total_pain_matches += 1

            # If review has pain keywords or is low rating with communication mention
            if matched_keywords or (rating <= 2 and any(
                word in text for word in ["call", "phone", "contact", "reach", "response", "answer"]
            )):
                # Store a snippet of the review
                snippet = text[:200] + "..." if len(text) > 200 else text
                pain_reviews.append(snippet)

        has_pain = len(pain_reviews) > 0

        # Calculate pain score (0-1 based on frequency of pain mentions)
        pain_score = None
        if has_pain:
            # Score based on: number of pain reviews + keyword matches
            raw_score = (len(pain_reviews) / len(reviews)) + (total_pain_matches / (len(reviews) * 2))
            pain_score = min(1.0, raw_score)  # Cap at 1.0

        # Generate summary
        pain_summary = None
        if has_pain:
            pain_summary = f"Found {len(pain_reviews)} reviews mentioning communication issues. "
            if total_pain_matches > 0:
                pain_summary += f"Detected {total_pain_matches} pain keyword matches."

        return has_pain, pain_score, pain_reviews[:5], pain_summary  # Limit stored reviews

    def _find_review_keywords(self, text: str) -> List[str]:
        """Find review-specific pain keywords in text."""
        text_lower = text.lower()
        matched = []
        for keyword in self.review_pain_keywords:
            if keyword.lower() in text_lower:
                matched.append(keyword)
        return matched

    def _extract_email_from_website(self, website: str) -> Optional[str]:
        """
        Attempt to extract email from business website.

        Note: This is a basic implementation. For production, consider
        using a dedicated web scraping approach with proper rate limiting.
        """
        if not website:
            return None

        try:
            # Simple attempt to fetch homepage and find email
            response = self.client.get(website, timeout=10.0, follow_redirects=True)
            if response.status_code == 200:
                return self.extract_email(response.text)
        except Exception:
            pass  # Website fetch failed, return None

        return None

    def scrape_single_location(self, location: str) -> LeadBatch:
        """
        Scrape all business types for a single location.

        Args:
            location: Location to search (e.g., "Miami, FL")

        Returns:
            LeadBatch with found leads
        """
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        if not self.api_key:
            batch.errors.append("Google Places API key not configured")
            return batch

        self.logger.info(f"Scraping {len(self.business_types)} business types in {location}")

        for business_type in self.business_types:
            try:
                leads = self._search_businesses(business_type, location)
                all_leads.extend(leads)
                time.sleep(1)
            except Exception as e:
                batch.errors.append(f"{business_type}: {str(e)}")

        unique_leads = list({lead.place_id: lead for lead in all_leads if lead.place_id}.values())
        batch.leads = unique_leads
        batch.total_found = len(unique_leads)

        return batch

    def scrape_single_type(self, business_type: str) -> LeadBatch:
        """
        Scrape a single business type across all locations.

        Args:
            business_type: Type of business (e.g., "plumber")

        Returns:
            LeadBatch with found leads
        """
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        if not self.api_key:
            batch.errors.append("Google Places API key not configured")
            return batch

        self.logger.info(f"Scraping {business_type} in {len(self.locations)} locations")

        for location in self.locations:
            try:
                leads = self._search_businesses(business_type, location)
                all_leads.extend(leads)
                time.sleep(1)
            except Exception as e:
                batch.errors.append(f"{location}: {str(e)}")

        unique_leads = list({lead.place_id: lead for lead in all_leads if lead.place_id}.values())
        batch.leads = unique_leads
        batch.total_found = len(unique_leads)

        return batch
