# Google Service Account Credentials

This directory stores the service account JSON key file for Google Sheets access.

## Your Service Account

- **Email**: `leads-writer@cc-leadsfinder.iam.gserviceaccount.com`
- **Project**: `cc-leadsfinder`
- **Key ID**: `ec80e407a50480d86bb788b3fcc83109e632c371`

## Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/iam-admin/serviceaccounts?project=cc-leadsfinder)
2. Click on `leads-writer@cc-leadsfinder.iam.gserviceaccount.com`
3. Go to **Keys** tab
4. Click **Add Key** -> **Create new key** -> **JSON**
5. Save the downloaded file as `google_sheets_sa.json` in this directory
6. Share your Google Sheet with `leads-writer@cc-leadsfinder.iam.gserviceaccount.com` (Editor)

## Required APIs (enable in Google Cloud Console)

- Google Sheets API
- Google Drive API
- Places API (for the Python scraper)

## File

The expected file is: `google_sheets_sa.json`

**IMPORTANT**: Never commit the JSON key file to git. It's in .gitignore.
