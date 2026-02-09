# Loads-Generation - Lead Finding Platform

## What is this project?
A lead generation platform that finds local businesses (plumbers, HVAC, dentists, lawyers, etc.) and investigates them to determine if they need AI Receptionist services or other digital services. Results are written to Google Sheets for sales outreach.

## Owner
- Communicates in Spanish but ALL code comments and output can be in Spanish
- Business brand: **NEXUS Voice** (AI Receptionist service built with Vapi)
- Services offered: AI Receptionist (priority #1), websites, web chatbots, appointment systems, social media, invoicing automation
- Target market: Local businesses in the US

## Key Files

### cc_lead_finder.py (Main tool - by Claude Code)
- Standalone script that finds leads, investigates them deeply, and writes to Google Sheets
- Usage: `python cc_lead_finder.py "plumbers" "Lima Ohio"`
- Uses `ddgs` package (DuckDuckGo search) - the ONLY search method that works from GitHub Codespace
- Searches 4 sources: Web Search, Yelp, Yellow Pages, BBB (all via DuckDuckGo)
- Investigates each business: website quality, reviews/complaints, social media, email extraction
- Scores AI Receptionist need: ALTO/MEDIO/BAJO with evidence
- Writes to Google Sheets with color coding (red=ALTO, yellow=MEDIO, green=BAJO)
- Creates industry-specific tabs (Plumbers, Hvac, Dentists, etc.)
- Falls back to CSV if Google Sheets connection fails

### main.py
- Original lead generation platform with TUI (Terminal User Interface)
- Has 10 scrapers: Reddit, Hacker News, Google Search, Product Hunt, Google Maps, Yelp, Indeed, Yellow Pages, BBB, Craigslist
- DO NOT modify without explicit permission

### web_app.py
- Web interface for the platform using Flask
- DO NOT modify without explicit permission

## Google Sheets Integration
- Sheet ID: `1P0A_7ptV2791YwQHH9wHAm0C41oPMmW7K1rn7afqHPY`
- Sheet name: "CC Leads"
- Service account: `leads-writer@cc-leadsfinder.iam.gserviceaccount.com`
- Credentials file: `credentials/google_sheets.json` (gitignored)
- Required APIs enabled: Google Sheets API + Google Drive API

## Tech Details
- Search library: `ddgs` (formerly `duckduckgo-search`, was renamed)
- Import with fallback: `from ddgs import DDGS` with fallback to `from duckduckgo_search import DDGS`
- Direct scraping of Google/Yelp/YP/BBB does NOT work (bot detection/Cloudflare) - always use DuckDuckGo library
- HTTP client: httpx with randomized User-Agent headers
- Dependencies: `gspread google-auth httpx beautifulsoup4 lxml ddgs`

## Important Rules
- NEVER change existing code (main.py, web_app.py, scrapers/) without being explicitly asked
- NEVER modify the UI or add features not requested
- credentials/ directory is gitignored - never commit credentials
- Script runs from GitHub Codespace (not from Claude Code sandbox due to SSL issues)

## Related Projects
- **nexus-voice-app** (separate repo) - NEXUS Voice business platform (Next.js + Supabase + Vercel)
- Context file: `/home/user/nexus-voice-CLAUDE.md`

## Search Progress
Industries searched so far (update as new searches are run):
- Plumbers in Lima Ohio - 70 businesses found, investigated, written to Sheet

## Known Issues
- SSL certificate errors when running from Claude Code sandbox - must run from Codespace
- DuckDuckGo may rate-limit after many consecutive searches - delays are built into the script
- Some businesses will have sparse data (no email, no reviews) - they still get written to Sheet
