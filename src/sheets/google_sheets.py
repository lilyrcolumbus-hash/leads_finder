"""Google Sheets client for writing business leads to spreadsheets.

Uses gspread with a service account to write leads into an EXISTING
Google Sheet, organized by industry tabs (one tab per industry search).

Setup:
    1. Google Cloud Console -> Create project (or use existing)
    2. Enable: Google Sheets API + Google Drive API
    3. Create Service Account -> Download JSON key
    4. Save JSON to credentials/google_sheets_sa.json
    5. Open your Google Sheet -> Share it with the service account email
       (the email looks like: name@project.iam.gserviceaccount.com)
    6. Copy the spreadsheet ID from the URL and put it in .env:
       GOOGLE_SHEETS_SPREADSHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
"""

import re
from typing import List, Optional, Dict, Any

import gspread
from google.oauth2.service_account import Credentials

from src.utils.logger import get_logger
from src.utils.models import Lead

logger = get_logger(__name__)

# Column headers for the business leads sheet
SHEET_HEADERS = [
    "Negocio",
    "Email",
    "Telefono",
    "Direccion",
    "Website",
    "Rating",
    "Reviews",
    "Tipo de Negocio",
    "Pain Score",
    "Resumen de Pain Points",
    "Google Maps URL",
    "Place ID",
]

# Scopes required for Google Sheets API
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def extract_spreadsheet_id(url_or_id: str) -> str:
    """Extract spreadsheet ID from a full Google Sheets URL or return as-is if already an ID.

    Handles URLs like:
        https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit
        1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
    """
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url_or_id)
    if match:
        return match.group(1)
    return url_or_id.strip()


class GoogleSheetsClient:
    """Client for writing business leads into an existing Google Sheet.

    Opens a sheet by its ID and creates new tabs for each industry search.

    Usage:
        with GoogleSheetsClient("path/to/credentials.json") as sheets:
            sheets.write_leads_to_tab(
                spreadsheet_id="1BxiMVs...",
                tab_name="Dentist - Miami, FL",
                leads=leads_list
            )
    """

    def __init__(self, credentials_path: str):
        """
        Initialize the Google Sheets client.

        Args:
            credentials_path: Path to the service account JSON credentials file
        """
        self.credentials_path = credentials_path
        self.gc: Optional[gspread.Client] = None
        self._connect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # gspread doesn't need explicit cleanup

    def _connect(self):
        """Establish connection to Google Sheets API."""
        try:
            creds = Credentials.from_service_account_file(
                self.credentials_path, scopes=SCOPES
            )
            self.gc = gspread.authorize(creds)
            logger.info("Connected to Google Sheets API")
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            raise

    def _sanitize_tab_name(self, name: str) -> str:
        """Sanitize a string for use as a worksheet tab name.

        Google Sheets tab names have restrictions:
        - Max 100 characters
        - Cannot contain: [ ] * / \\ ? :
        """
        sanitized = re.sub(r'[\[\]*/?:\\]', '', name)
        return sanitized[:100].strip()

    def open_spreadsheet(self, spreadsheet_id: str) -> gspread.Spreadsheet:
        """
        Open an existing spreadsheet by its ID.

        Args:
            spreadsheet_id: The spreadsheet ID or full URL

        Returns:
            gspread.Spreadsheet object
        """
        sheet_id = extract_spreadsheet_id(spreadsheet_id)
        spreadsheet = self.gc.open_by_key(sheet_id)
        logger.info(f"Opened spreadsheet: {spreadsheet.title} (ID: {sheet_id})")
        return spreadsheet

    def _get_or_create_tab(
        self, spreadsheet: gspread.Spreadsheet, tab_name: str
    ) -> gspread.Worksheet:
        """
        Get an existing worksheet tab or create a new one.

        Args:
            spreadsheet: The spreadsheet object
            tab_name: Name for the worksheet tab

        Returns:
            gspread.Worksheet object
        """
        tab_name = self._sanitize_tab_name(tab_name)

        try:
            worksheet = spreadsheet.worksheet(tab_name)
            logger.info(f"Found existing tab: {tab_name}")
            return worksheet
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=tab_name, rows=1000, cols=len(SHEET_HEADERS)
            )
            logger.info(f"Created new tab: {tab_name}")
            return worksheet

    def _lead_to_row(self, lead: Lead) -> List[str]:
        """Convert a Lead object to a row of strings for the sheet."""
        return [
            lead.title or lead.company or "",
            lead.email or "",
            lead.phone or "",
            lead.address or "",
            lead.website or "",
            str(lead.rating) if lead.rating else "",
            str(lead.review_count) if lead.review_count else "",
            lead.business_type or "",
            f"{lead.pain_score:.2f}" if lead.pain_score else "",
            lead.pain_summary or "",
            lead.url or "",
            lead.place_id or "",
        ]

    def write_leads_to_tab(
        self,
        spreadsheet_id: str,
        tab_name: str,
        leads: List[Lead],
        clear_existing: bool = False,
    ) -> Dict[str, Any]:
        """
        Write leads into a new tab of an existing Google Sheet.

        Creates the tab if it doesn't exist. If the tab already exists,
        appends new rows (unless clear_existing=True).

        Args:
            spreadsheet_id: Spreadsheet ID or full URL
            tab_name: Name for the tab (typically: "Industry - Location")
            leads: List of Lead objects to write
            clear_existing: If True, clear existing data before writing

        Returns:
            Dict with results: {"spreadsheet_url", "tab", "rows_written", "total_rows"}
        """
        if not leads:
            logger.warning("No leads to write")
            return {"spreadsheet_url": "", "tab": tab_name, "rows_written": 0, "total_rows": 0}

        spreadsheet = self.open_spreadsheet(spreadsheet_id)
        worksheet = self._get_or_create_tab(spreadsheet, tab_name)

        # Check if we need to write headers
        existing_data = worksheet.get_all_values()
        has_headers = len(existing_data) > 0 and existing_data[0] == SHEET_HEADERS

        if clear_existing or not has_headers:
            worksheet.clear()
            worksheet.append_row(SHEET_HEADERS)
            worksheet.format("1:1", {"textFormat": {"bold": True}})
            start_row = 2
        else:
            start_row = len(existing_data) + 1

        # Convert leads to rows
        rows = [self._lead_to_row(lead) for lead in leads]

        # Batch write all rows at once
        if rows:
            worksheet.append_rows(rows, value_input_option="USER_ENTERED")
            logger.info(f"Wrote {len(rows)} leads to tab '{tab_name}'")

        result = {
            "spreadsheet_url": spreadsheet.url,
            "tab": tab_name,
            "rows_written": len(rows),
            "total_rows": start_row - 1 + len(rows),
        }

        logger.info(f"Sheet updated: {result}")
        return result

    def list_tabs(self, spreadsheet_id: str) -> List[str]:
        """
        List all tab names in a spreadsheet.

        Args:
            spreadsheet_id: Spreadsheet ID or full URL

        Returns:
            List of tab names
        """
        spreadsheet = self.open_spreadsheet(spreadsheet_id)
        return [ws.title for ws in spreadsheet.worksheets()]
