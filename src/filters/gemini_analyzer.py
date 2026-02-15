"""Gemini-powered business analyzer - investigates websites and detects software needs."""

import json
import re
import time
import requests
from typing import List, Optional

from src.config import settings
from src.utils.logger import get_logger
from src.utils.models import Lead


class GeminiBusinessAnalyzer:
    """
    Uses Google Gemini to analyze each business and determine software needs.

    Investigates: website quality, social media presence, chatbot, automation,
    online booking, and other software gaps.
    """

    ANALYSIS_PROMPT = """You are a business technology analyst. Analyze this business and determine what software/technology they need.

Business Info:
- Name: {name}
- Industry: {industry}
- Website: {website}
- Phone: {phone}
- Address: {address}
- Website Content Summary: {web_content}

Based on what you can see, determine:
1. Do they have a professional website? (yes/no/basic)
2. Do they have social media links on their site? (yes/no)
3. Do they have a chatbot or live chat? (yes/no)
4. Do they have online booking/scheduling? (yes/no)
5. Do they have online reviews management? (yes/no)
6. What is their main software/technology need?

Respond ONLY with valid JSON:
{{
    "has_professional_website": "yes|no|basic",
    "has_social_media": true/false,
    "has_chatbot": true/false,
    "has_online_booking": true/false,
    "has_reviews_management": true/false,
    "software_needs": "Brief list of what they need, comma separated. Example: 'Website redesign, Chatbot, Social media, Online booking system'",
    "analysis": "One sentence explaining the biggest opportunity"
}}"""

    def __init__(self):
        self.logger = get_logger("GeminiAnalyzer")
        self.model = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self._init_gemini()

    def _init_gemini(self):
        """Initialize Gemini client."""
        if settings.gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.gemini_api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                self.logger.info("Gemini Business Analyzer initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Gemini: {e}")

    def analyze_leads(self, leads: List[Lead], progress_callback=None) -> List[Lead]:
        """
        Analyze a list of leads with Gemini to detect software needs.

        Args:
            leads: List of leads to analyze
            progress_callback: Optional callback(current, total) for progress updates

        Returns:
            List of leads with software_needs populated
        """
        if not self.model:
            self.logger.warning("Gemini not available - skipping business analysis")
            return leads

        total = len(leads)
        self.logger.info(f"Analyzing {total} businesses with Gemini...")

        for i, lead in enumerate(leads):
            try:
                self._analyze_single_lead(lead)
            except Exception as e:
                self.logger.debug(f"Error analyzing {lead.company}: {e}")
                lead.software_needs = "Analysis unavailable"

            if progress_callback:
                progress_callback(i + 1, total)

            time.sleep(0.5)  # Rate limiting for Gemini API

        analyzed = len([l for l in leads if l.software_needs and l.software_needs != "Analysis unavailable"])
        self.logger.info(f"Gemini analysis complete: {analyzed}/{total} businesses analyzed")

        return leads

    def _analyze_single_lead(self, lead: Lead):
        """Analyze a single business with Gemini."""
        # Fetch website content if available
        web_content = "No website available"
        if lead.website:
            web_content = self._fetch_website_summary(lead.website)

        # Build prompt
        prompt = self.ANALYSIS_PROMPT.format(
            name=lead.company or lead.title or "Unknown",
            industry=lead.industry or "Unknown",
            website=lead.website or "None",
            phone=lead.phone or "None",
            address=lead.address or lead.extra_data.get('address', 'Unknown') if lead.extra_data else "Unknown",
            web_content=web_content[:2000]  # Limit content size
        )

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            # Clean markdown code blocks
            if result_text.startswith("```"):
                lines = result_text.split("\n")
                result_text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            data = json.loads(result_text)

            # Populate lead fields
            lead.software_needs = data.get("software_needs", "Unknown")
            lead.has_website = data.get("has_professional_website", "no") != "no"
            lead.has_social_media = bool(data.get("has_social_media", False))
            lead.gemini_analysis = data.get("analysis", "")

        except json.JSONDecodeError:
            # Try to extract useful info even if JSON fails
            lead.software_needs = "Analysis format error"
            self.logger.debug(f"JSON parse error for {lead.company}")
        except Exception as e:
            lead.software_needs = "Analysis unavailable"
            self.logger.debug(f"Gemini error for {lead.company}: {e}")

    def _fetch_website_summary(self, url: str) -> str:
        """Fetch website and extract key content for analysis."""
        try:
            if not url.startswith('http'):
                url = 'https://' + url

            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return "Website returned error"

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove scripts and styles
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()

            # Get text content
            text = soup.get_text(separator=' ', strip=True)

            # Check for key features
            html_lower = response.text.lower()
            features = []
            if any(w in html_lower for w in ['chat', 'livechat', 'tawk', 'intercom', 'drift', 'zendesk', 'crisp']):
                features.append("HAS_CHATBOT")
            if any(w in html_lower for w in ['booking', 'schedule', 'appointment', 'calendly', 'acuity']):
                features.append("HAS_BOOKING")
            if any(w in html_lower for w in ['facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com', 'tiktok.com']):
                features.append("HAS_SOCIAL_LINKS")
            if any(w in html_lower for w in ['mailto:', '@']):
                features.append("HAS_EMAIL")

            # Title
            title = soup.title.string if soup.title else "No title"

            # Meta description
            meta_desc = ""
            meta_tag = soup.find('meta', attrs={'name': 'description'})
            if meta_tag:
                meta_desc = meta_tag.get('content', '')

            summary = f"Title: {title}\nDescription: {meta_desc}\nFeatures detected: {', '.join(features)}\nContent preview: {text[:500]}"
            return summary

        except Exception as e:
            return f"Could not fetch website: {str(e)[:100]}"
