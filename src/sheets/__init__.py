"""Google Sheets integration for lead export.

Available clients:
    - AppsScriptClient: Calls Apps Script deployment URL (no local API keys needed)
    - GoogleSheetsClient: Uses gspread + service account (import separately when needed)

GoogleSheetsClient requires gspread + google-auth + cryptography.
Import it directly when needed:
    from src.sheets.google_sheets import GoogleSheetsClient
"""

from src.sheets.apps_script_client import AppsScriptClient

__all__ = ["AppsScriptClient"]
