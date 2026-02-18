"""Google Sheets client for writing business leads to spreadsheets.

Uses gspread with a service account to create/update Google Sheets
with business leads organized by industry tabs.
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


class GoogleSheetsClient:
    """Client for writing business leads to Google Sheets.

    Organizes leads by industry, with each industry in a separate tab (worksheet).
    Uses a service account for authentication.

    Usage:
        with GoogleSheetsClient("path/to/credentials.json") as sheets:
            sheets.write_leads_to_sheet(
                spreadsheet_name="Business Leads",
                industry="dentist",
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
        - Cannot contain: [ ] * / \ ? :
        """
        sanitized = re.sub(r'[\[\]*/?:\\]', '', name)
        return sanitized[:100].strip()

    def get_or_create_spreadsheet(self, name: str) -> gspread.Spreadsheet:
        """
        Get an existing spreadsheet by name, or create a new one.

        Args:
            name: Name of the spreadsheet

        Returns:
            gspread.Spreadsheet object
        """
        try:
            spreadsheet = self.gc.open(name)
            logger.info(f"Opened existing spreadsheet: {name}")
            return spreadsheet
        except gspread.SpreadsheetNotFound:
            spreadsheet = self.gc.create(name)
            logger.info(f"Created new spreadsheet: {name}")
            return spreadsheet

    def _get_or_create_worksheet(
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
        """
        Convert a Lead object to a row of strings for the sheet.

        Args:
            lead: Lead object to convert

        Returns:
            List of string values matching SHEET_HEADERS order
        """
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

    def write_leads_to_sheet(
        self,
        spreadsheet_name: str,
        industry: str,
        leads: List[Lead],
        clear_existing: bool = False,
    ) -> Dict[str, Any]:
        """
        Write leads to a Google Sheet, organized by industry tab.

        Each industry gets its own tab (worksheet) in the spreadsheet.
        If the tab already exists, new leads are appended (unless clear_existing=True).

        Args:
            spreadsheet_name: Name of the Google Spreadsheet
            industry: Industry name (used as tab name)
            leads: List of Lead objects to write
            clear_existing: If True, clear existing data before writing

        Returns:
            Dict with results: {"spreadsheet_url": str, "tab": str, "rows_written": int}
        """
        if not leads:
            logger.warning("No leads to write")
            return {"spreadsheet_url": "", "tab": industry, "rows_written": 0}

        spreadsheet = self.get_or_create_spreadsheet(spreadsheet_name)
        worksheet = self._get_or_create_worksheet(spreadsheet, industry)

        # Check if we need to write headers
        existing_data = worksheet.get_all_values()
        has_headers = len(existing_data) > 0 and existing_data[0] == SHEET_HEADERS

        if clear_existing or not has_headers:
            worksheet.clear()
            worksheet.append_row(SHEET_HEADERS)
            # Format header row bold
            worksheet.format("1:1", {"textFormat": {"bold": True}})
            start_row = 2
        else:
            start_row = len(existing_data) + 1

        # Convert leads to rows
        rows = [self._lead_to_row(lead) for lead in leads]

        # Batch write all rows at once for efficiency
        if rows:
            worksheet.append_rows(rows, value_input_option="USER_ENTERED")
            logger.info(f"Wrote {len(rows)} leads to tab '{industry}'")

        # Remove default "Sheet1" if it exists and is empty
        self._cleanup_default_sheet(spreadsheet)

        result = {
            "spreadsheet_url": spreadsheet.url,
            "tab": industry,
            "rows_written": len(rows),
            "total_rows": start_row - 1 + len(rows),
        }

        logger.info(f"Sheet updated: {result}")
        return result

    def _cleanup_default_sheet(self, spreadsheet: gspread.Spreadsheet):
        """Remove the default 'Sheet1' tab if empty and other tabs exist."""
        try:
            worksheets = spreadsheet.worksheets()
            if len(worksheets) > 1:
                for ws in worksheets:
                    if ws.title in ("Sheet1", "Hoja 1") and ws.row_count <= 1:
                        spreadsheet.del_worksheet(ws)
                        logger.debug("Removed empty default sheet")
                        break
        except Exception:
            pass  # Not critical

    def share_spreadsheet(self, spreadsheet_name: str, email: str, role: str = "writer"):
        """
        Share a spreadsheet with an email address.

        Args:
            spreadsheet_name: Name of the spreadsheet
            email: Email to share with
            role: Permission role ('reader', 'writer', 'owner')
        """
        spreadsheet = self.gc.open(spreadsheet_name)
        spreadsheet.share(email, perm_type="user", role=role)
        logger.info(f"Shared '{spreadsheet_name}' with {email} as {role}")

    def share_spreadsheet_public(self, spreadsheet_name: str):
        """
        Make a spreadsheet accessible to anyone with the link.

        Args:
            spreadsheet_name: Name of the spreadsheet
        """
        spreadsheet = self.gc.open(spreadsheet_name)
        spreadsheet.share("", perm_type="anyone", role="reader")
        logger.info(f"Made '{spreadsheet_name}' public (read-only)")

    def list_tabs(self, spreadsheet_name: str) -> List[str]:
        """
        List all tab names in a spreadsheet.

        Args:
            spreadsheet_name: Name of the spreadsheet

        Returns:
            List of tab names
        """
        spreadsheet = self.gc.open(spreadsheet_name)
        return [ws.title for ws in spreadsheet.worksheets()]
