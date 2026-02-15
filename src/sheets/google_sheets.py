"""Google Sheets sync via Apps Script Web App.

Sends leads to a Google Sheet by POSTing JSON data to a deployed
Google Apps Script web app endpoint. Buffers leads and flushes
every N leads (default 10).

Sends ALL leads (with or without email) - local businesses often
have phone numbers but no email, and those are still valuable contacts.
"""

import time
from typing import List, Optional, Dict, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.utils.logger import get_logger
from src.utils.models import Lead

logger = get_logger("GoogleSheets")


class GoogleSheetsSync:
    """Syncs leads to Google Sheets via Apps Script webhook.

    Usage:
        with GoogleSheetsSync() as sheets:
            sheets.add_lead(lead)        # Buffers, auto-flushes at batch_size
            sheets.flush()               # Force send remaining leads

    Or as part of scraping pipeline:
        sheets = GoogleSheetsSync()
        sheets.send_leads(leads_list)    # Send a list directly
    """

    BATCH_SIZE = 10

    def __init__(self, webhook_url: Optional[str] = None, batch_size: int = 10):
        """Initialize Google Sheets sync.

        Args:
            webhook_url: Apps Script web app URL. Falls back to settings.
            batch_size: Number of leads to buffer before auto-sending.
        """
        self.webhook_url = webhook_url or settings.google_sheets_webhook_url
        self.batch_size = batch_size
        self._buffer: List[Lead] = []
        self._total_sent = 0
        self._total_failed = 0
        self.client = httpx.Client(timeout=30.0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()
        self.client.close()

    def close(self):
        """Flush remaining leads and close HTTP client."""
        self.flush()
        self.client.close()

    def is_configured(self) -> bool:
        """Check if the webhook URL is set."""
        return bool(self.webhook_url)

    def _lead_to_row(self, lead: Lead) -> Dict[str, Any]:
        """Convert a Lead to a flat dict matching spreadsheet columns.

        Columns: Nombre, Email, Telefono, Empresa, Website, Direccion,
                 Industria, Rating, Fuente, URL, Pain Score, AI Score,
                 Software Needs, Gemini Analysis, Has Website, Has Social Media
        """
        name = lead.name or lead.company or lead.title or lead.username or ""
        email = lead.email or ""
        # Skip placeholder emails
        if email.endswith("@leadgen.placeholder"):
            email = ""

        return {
            "nombre": name,
            "email": email,
            "telefono": lead.phone or "",
            "empresa": lead.company or lead.title or "",
            "website": lead.website or "",
            "direccion": lead.address or lead.location or "",
            "industria": lead.industry or lead.business_type or "",
            "rating": lead.rating or "",
            "fuente": lead.source.value,
            "url": lead.url,
            "pain_score": lead.pain_score or "",
            "ai_score": round((lead.ai_score or 0) * 100),
            "software_needs": lead.software_needs or "",
            "gemini_analysis": lead.gemini_analysis or "",
            "has_website": "Yes" if lead.has_website else ("No" if lead.has_website is False else ""),
            "has_social_media": "Yes" if lead.has_social_media else ("No" if lead.has_social_media is False else ""),
        }

    def _has_contact_info(self, lead: Lead) -> bool:
        """Check if lead has any useful contact info (email, phone, or website)."""
        if lead.email and not lead.email.endswith("@leadgen.placeholder"):
            return True
        if lead.phone:
            return True
        if lead.website:
            return True
        # Even if no contact info, the business name + address is useful
        if lead.company or lead.title:
            return True
        return False

    def add_lead(self, lead: Lead) -> None:
        """Add a lead to the buffer.

        Sends all leads that have any useful info (name, phone, email, website).

        Args:
            lead: Lead to buffer for sending.
        """
        if not self._has_contact_info(lead):
            logger.debug(f"Skipped lead {lead.id} (no contact info at all)")
            return

        self._buffer.append(lead)
        if len(self._buffer) >= self.batch_size:
            self.flush()

    def add_leads(self, leads: List[Lead]) -> None:
        """Add multiple leads to the buffer.

        Args:
            leads: List of leads to buffer.
        """
        for lead in leads:
            self.add_lead(lead)

    def flush(self) -> Dict[str, int]:
        """Send all buffered leads to the Google Sheet.

        Returns:
            Dict with 'sent' and 'failed' counts.
        """
        if not self._buffer:
            return {"sent": 0, "failed": 0}

        result = self._post_leads(self._buffer)
        self._buffer.clear()
        return result

    def send_leads(self, leads: List[Lead]) -> Dict[str, int]:
        """Send a list of leads directly (no buffering).

        Args:
            leads: Leads to send immediately.

        Returns:
            Dict with 'sent' and 'failed' counts.
        """
        valid_leads = [l for l in leads if self._has_contact_info(l)]
        skipped = len(leads) - len(valid_leads)
        if skipped:
            logger.info(f"Skipped {skipped} leads without any contact info")

        if not valid_leads:
            return {"sent": 0, "failed": 0}

        return self._post_leads(valid_leads)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _post_leads(self, leads: List[Lead]) -> Dict[str, int]:
        """POST leads to the Apps Script web app.

        Args:
            leads: Leads to send.

        Returns:
            Dict with 'sent' and 'failed' counts.
        """
        if not self.is_configured():
            logger.warning("Google Sheets webhook URL not configured")
            return {"sent": 0, "failed": len(leads)}

        rows = [self._lead_to_row(lead) for lead in leads]
        payload = {"leads": rows}

        try:
            response = self.client.post(
                self.webhook_url,
                json=payload,
                follow_redirects=True,
            )

            if response.status_code == 200:
                self._total_sent += len(leads)
                logger.info(f"Sent {len(leads)} leads to Google Sheets (total: {self._total_sent})")
                return {"sent": len(leads), "failed": 0}
            else:
                self._total_failed += len(leads)
                logger.error(f"Google Sheets returned status {response.status_code}: {response.text[:200]}")
                return {"sent": 0, "failed": len(leads)}

        except Exception as e:
            self._total_failed += len(leads)
            logger.error(f"Failed to send leads to Google Sheets: {e}")
            raise  # Let tenacity retry

    def get_stats(self) -> Dict[str, int]:
        """Get sync statistics.

        Returns:
            Dict with total_sent, total_failed, and buffered counts.
        """
        return {
            "total_sent": self._total_sent,
            "total_failed": self._total_failed,
            "buffered": len(self._buffer),
        }
