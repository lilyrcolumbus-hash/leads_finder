"""Google Apps Script client for searching businesses via the deployed web app.

Calls the Apps Script deployment URL to search businesses using Google Places API
and write results directly to a Google Sheet. This is the simplest integration path
since the Apps Script handles everything server-side (Places API + Sheet writing).

No local API keys or service account files are needed - just the deployment URL.

Usage:
    from src.sheets.apps_script_client import AppsScriptClient

    client = AppsScriptClient()

    # Search and write to sheet
    result = client.search_businesses("dentist", "Miami, FL", max_results=20)

    # Result contains:
    #   status, message, tab, spreadsheet, total_leads,
    #   with_email, with_phone, with_pain, leads[]
"""

import httpx
from typing import Optional, Dict, Any, List

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Timeout for Apps Script calls (can take a while with email extraction)
REQUEST_TIMEOUT = 360.0  # 6 minutes max (Apps Script limit)


class AppsScriptClient:
    """Client for calling the Google Apps Script deployment URL.

    The Apps Script searches Google Places API and writes results
    directly into the linked Google Sheet.

    Usage:
        with AppsScriptClient() as client:
            result = client.search_businesses("plumber", "Houston, TX")
            print(f"Found {result['total_leads']} leads")
    """

    def __init__(self, deployment_url: Optional[str] = None):
        """
        Initialize the Apps Script client.

        Args:
            deployment_url: The Apps Script deployment URL. If not provided,
                           reads from settings (APPS_SCRIPT_DEPLOYMENT_URL).
        """
        self.deployment_url = deployment_url or settings.apps_script_deployment_url
        self.client: Optional[httpx.Client] = None

    def __enter__(self):
        self.client = httpx.Client(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.client.close()
            self.client = None

    def is_configured(self) -> bool:
        """Check if the Apps Script deployment URL is configured."""
        return bool(self.deployment_url and self.deployment_url.startswith("https://"))

    def search_businesses(
        self,
        industry: str,
        location: str,
        max_results: int = 60,
        analyze_reviews: bool = True,
    ) -> Dict[str, Any]:
        """
        Search for businesses and write them to the Google Sheet.

        Calls the Apps Script doGet() endpoint which:
        1. Searches Google Places API for businesses
        2. Gets details (phone, email, reviews, etc.)
        3. Writes results to a new tab in the linked Sheet
        4. Returns a JSON summary

        Args:
            industry: Type of business (e.g., "dentist", "plumber")
            location: City and state (e.g., "Miami, FL")
            max_results: Maximum number of businesses to process (default: 60)
            analyze_reviews: Whether to analyze reviews for pain points (default: True)

        Returns:
            Dict with results:
                {
                    "status": "ok",
                    "message": "Busqueda completada",
                    "tab": "Dentist - Miami, FL",
                    "spreadsheet": "https://docs.google.com/spreadsheets/d/.../edit",
                    "total_leads": 20,
                    "with_email": 5,
                    "with_phone": 15,
                    "with_pain": 3,
                    "leads": [{"name": "...", "email": "...", ...}]
                }

        Raises:
            ValueError: If deployment URL is not configured
            httpx.HTTPError: If the HTTP request fails
        """
        if not self.is_configured():
            raise ValueError(
                "Apps Script deployment URL not configured. "
                "Set APPS_SCRIPT_DEPLOYMENT_URL in .env"
            )

        params = {
            "industry": industry,
            "location": location,
            "max": str(max_results),
            "reviews": "true" if analyze_reviews else "false",
        }

        logger.info(f"Calling Apps Script: {industry} in {location} (max={max_results})")

        if not self.client:
            self.client = httpx.Client(
                timeout=REQUEST_TIMEOUT,
                follow_redirects=True,
            )

        try:
            response = self.client.get(self.deployment_url, params=params)
            response.raise_for_status()

            data = response.json()

            if data.get("status") == "error":
                error_msg = data.get("message", "Unknown error from Apps Script")
                logger.error(f"Apps Script error: {error_msg}")
                return data

            total = data.get("total_leads", 0)
            emails = data.get("with_email", 0)
            phones = data.get("with_phone", 0)
            pain = data.get("with_pain", 0)

            logger.info(
                f"Apps Script result: {total} leads "
                f"({emails} emails, {phones} phones, {pain} with pain)"
            )

            return data

        except httpx.TimeoutException:
            logger.error("Apps Script call timed out (>6 min)")
            return {
                "status": "error",
                "message": "La busqueda tardo demasiado (timeout). Intenta con menos resultados (?max=20)",
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling Apps Script: {e.response.status_code}")
            return {
                "status": "error",
                "message": f"Error HTTP {e.response.status_code} al llamar Apps Script",
            }
        except Exception as e:
            logger.error(f"Error calling Apps Script: {e}")
            return {
                "status": "error",
                "message": f"Error: {str(e)}",
            }

    def search_multiple(
        self,
        industries: List[str],
        location: str,
        max_results: int = 60,
        analyze_reviews: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search for multiple industries in a single location.

        Args:
            industries: List of business types
            location: City and state
            max_results: Max results per industry
            analyze_reviews: Whether to analyze reviews

        Returns:
            List of result dicts, one per industry
        """
        results = []
        for industry in industries:
            result = self.search_businesses(
                industry=industry,
                location=location,
                max_results=max_results,
                analyze_reviews=analyze_reviews,
            )
            results.append(result)
        return results

    def test_connection(self) -> Dict[str, Any]:
        """
        Test the Apps Script connection with a minimal request.

        Sends a request without required params to check if the URL responds.

        Returns:
            Dict with status and message
        """
        if not self.is_configured():
            return {
                "status": "error",
                "message": "APPS_SCRIPT_DEPLOYMENT_URL no configurada",
            }

        try:
            if not self.client:
                self.client = httpx.Client(
                    timeout=30.0,
                    follow_redirects=True,
                )

            response = self.client.get(self.deployment_url)
            response.raise_for_status()
            data = response.json()

            # The script returns an error about missing params, but that means it's working
            if data.get("status") == "error" and "parametros" in data.get("message", "").lower():
                return {
                    "status": "ok",
                    "message": "Apps Script conectado correctamente",
                }

            # If we get a different error, the API key might not be configured
            if data.get("status") == "error" and "API_KEY" in data.get("message", ""):
                return {
                    "status": "error",
                    "message": "Apps Script conectado, pero la Google Places API Key no esta configurada en el script",
                }

            return data

        except Exception as e:
            return {
                "status": "error",
                "message": f"No se pudo conectar al Apps Script: {str(e)}",
            }
