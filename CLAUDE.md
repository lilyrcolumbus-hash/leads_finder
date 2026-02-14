# CLAUDE.md - Loads-Generation Project Guide

## What Is This Project?

Lead generation tool for an **AI receptionist sales team**. Finds companies that are actively hiring receptionists, front desk, and customer service roles — these are warm leads because they clearly need phone/customer handling, making them ideal prospects for an AI receptionist service.

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Indeed Leads Finder (main tool - Streamlit web app)
streamlit run indeed_app.py

# General lead generation web app (all sources)
streamlit run web_app.py

# CLI version (interactive menu)
python main.py
```

## Project Structure

```
Loads-Generation/
├── indeed_app.py              # Indeed Leads Finder (Streamlit) - PRIMARY TOOL
├── web_app.py                 # General lead gen web app (Streamlit, mobile-ready)
├── main.py                    # CLI version with interactive menu
├── requirements.txt           # Python dependencies
├── .env                       # API keys (not in git)
├── .env.example               # Template for .env
├── src/
│   ├── config.py              # Settings (API keys, keywords, locations)
│   ├── scrapers/
│   │   ├── base_scraper.py    # Abstract base class (httpx + retry + keyword matching)
│   │   ├── indeed_scraper.py  # Indeed scraper (multi-query, multi-location)
│   │   ├── indeed_search.py   # Enhanced Indeed scraper with full search params
│   │   ├── reddit_scraper.py  # Reddit scraper
│   │   ├── hackernews_scraper.py
│   │   ├── google_scraper.py
│   │   └── producthunt_scraper.py
│   ├── filters/
│   │   └── ai_filter.py       # AI lead qualification (OpenAI or Anthropic)
│   ├── crm/
│   │   └── hubspot.py         # HubSpot CRM integration (full CRUD + pipeline)
│   └── utils/
│       ├── models.py          # Lead, LeadBatch, LeadSource (Pydantic models)
│       └── logger.py          # Logging setup
```

## Key Components

### indeed_app.py (Primary Tool)
- Streamlit app dedicated to Indeed lead finding
- Sidebar filters: keywords, location, radius, date range, job type, remote, experience level
- Results shown as Lead Cards, Data Table, and Export (CSV/TSV)
- Uses `IndeedSearchScraper` from `src/scrapers/indeed_search.py`

### IndeedSearchScraper (src/scrapers/indeed_search.py)
- Enhanced scraper with `IndeedSearchParams` dataclass
- Supports: keywords, location, date_range, job_type, salary_min, remote, sort_by, radius, max_results, experience_level
- Paginates through results, deduplicates by company name
- Rate limits with 2-second delays between requests

### IndeedScraper (src/scrapers/indeed_scraper.py)
- Original Indeed scraper used by `main.py` and `web_app.py`
- Searches multiple queries x multiple locations from config
- Rate limits with 3-second delays

### Data Models (src/utils/models.py)
- `Lead`: Pydantic model with id, source, company, title, content, url, keywords_matched, ai_score, is_qualified
- `LeadBatch`: Collection of leads with errors tracking
- `LeadSource`: Enum (reddit, hacker_news, google_search, product_hunt, indeed)

### AI Filter (src/filters/ai_filter.py)
- Scores leads 0-1 using OpenAI or Anthropic
- Qualifies leads with score >= 0.6
- Checks for business owners with communication pain points

### HubSpot CRM (src/crm/hubspot.py)
- Full pipeline: NEW -> CONTACTED -> DEMO -> PROPOSAL -> CLOSED_WON / CLOSED_LOST
- CRUD operations, search, statistics, notes

## API Keys Needed (.env file)

```
HUBSPOT_API_KEY=...        # CRM integration
GOOGLE_API_KEY=...         # Google search scraper
GOOGLE_SEARCH_ENGINE_ID=...
OPENAI_API_KEY=...         # AI lead filtering
ANTHROPIC_API_KEY=...      # Alternative AI filtering
```

None are required to run — scrapers that need keys will just fail gracefully.

## Tech Stack

- **Python 3.10+**
- **Streamlit** - Web UI
- **httpx** - HTTP client (with tenacity retries)
- **BeautifulSoup4 + lxml** - HTML parsing
- **Pydantic** - Data models and settings
- **Rich** - CLI interface
- **OpenAI / Anthropic** - AI filtering
- **pandas** - Data tables and export

## Git Workflow

- **Main branch**: `master`
- **Feature branches**: `claude/<feature-name>-<id>`
- Current feature branch: `claude/indeed-receptionist-leads-GrmX3`

## Development History

1. Base lead generation app with multi-source scraping + HubSpot CRM
2. Added Streamlit web interface (mobile-optimized)
3. Added Indeed scraper for companies hiring receptionists
4. Generated research reports for AI receptionist leads
5. Created CSV/TSV spreadsheets with leads (Lima, OH area focus)
6. Built dedicated Indeed Leads Finder app (`indeed_app.py`) with full search filters

## Important Notes

- Indeed scraping uses browser-like User-Agent headers
- Rate limiting is built in (2-3 second delays) — don't remove it
- The app deduplicates leads by company name
- Default search focus: receptionist, front desk, customer service roles
- Default test location: Lima, OH (configurable in the app)
- All scrapers extend `BaseScraper` and use the context manager pattern (`with Scraper() as s:`)
