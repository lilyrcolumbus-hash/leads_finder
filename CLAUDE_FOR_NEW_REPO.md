# CLAUDE.md - hiring_apps

## What Is This Project?

Lead generation tool for an **AI receptionist sales team**. Finds companies that are actively hiring receptionists, front desk, and customer service roles — these are warm leads because they clearly need phone/customer handling, making them ideal prospects for an AI receptionist service.

This project continues the work started in the `Loads-Generation` repo.

## What We Already Built (Loads-Generation repo)

### Apps
- **indeed_app.py** - Streamlit app dedicated to Indeed lead finding (PRIMARY TOOL)
  - Sidebar filters: keywords, location, radius, date range, job type, remote, experience level
  - Results as Lead Cards, Data Table, Export (CSV/TSV)
- **web_app.py** - General lead gen web app (Streamlit, mobile-optimized)
  - Sources: Reddit, Hacker News, Google, Product Hunt, Indeed
  - AI filtering, HubSpot CRM integration
- **main.py** - CLI version with interactive menu (Rich library)

### Scrapers (src/scrapers/)
- **BaseScraper** - Abstract base class with httpx + tenacity retries + keyword matching
  - All scrapers use context manager pattern: `with Scraper() as s:`
  - `find_keywords()` matches pain keywords in text
  - `fetch_url()` with 3-attempt retry + exponential backoff
- **IndeedSearchScraper** - Enhanced scraper with `IndeedSearchParams` dataclass
  - Supports: keywords, location, date_range, job_type, salary_min, remote, sort_by, radius, max_results, experience_level
  - Paginates results, deduplicates by company name
  - 2-second rate limiting between requests
- **IndeedScraper** - Original Indeed scraper (multi-query x multi-location from config)
  - 3-second rate limiting
- **RedditScraper, HackerNewsScraper, GoogleScraper, ProductHuntScraper**

### AI Filter (src/filters/ai_filter.py)
- Scores leads 0-1 using OpenAI or Anthropic
- Qualifies leads with score >= 0.6
- Checks for business owners with communication pain points

### HubSpot CRM (src/crm/hubspot.py)
- Pipeline: NEW -> CONTACTED -> DEMO -> PROPOSAL -> CLOSED_WON / CLOSED_LOST
- Full CRUD operations, search, statistics, notes

### Data Models (src/utils/models.py)
- **Lead**: Pydantic model — id, source, company, title, content, url, keywords_matched, ai_score, is_qualified
- **LeadBatch**: Collection of leads with errors tracking
- **LeadSource**: Enum (reddit, hacker_news, google_search, product_hunt, indeed)

### Config (src/config.py)
- Pydantic Settings loading from .env
- Pain keywords: "missed calls", "need receptionist", "can't answer phone", etc.
- Indeed job queries: receptionist, front desk, customer service, dental receptionist, etc.
- Indeed locations: 10 major US cities
- Subreddits: smallbusiness, HVAC, Plumbing, electricians, dentistry, realtors, etc.

## API Keys (.env file)

```
HUBSPOT_API_KEY=...        # CRM integration
GOOGLE_API_KEY=...         # Google search scraper
GOOGLE_SEARCH_ENGINE_ID=...
OPENAI_API_KEY=...         # AI lead filtering
ANTHROPIC_API_KEY=...      # Alternative AI filtering
```

None are required — scrapers that need keys fail gracefully.

## Tech Stack

- **Python 3.10+**
- **Streamlit** - Web UI
- **httpx** - HTTP client (with tenacity retries)
- **BeautifulSoup4 + lxml** - HTML parsing
- **Pydantic + pydantic-settings** - Data models and config
- **Rich** - CLI interface
- **OpenAI / Anthropic** - AI lead filtering
- **pandas** - Data tables and export

## Development History

1. Base lead generation app with multi-source scraping + HubSpot CRM
2. Added Streamlit web interface (mobile-optimized)
3. Added Indeed scraper for companies hiring receptionists
4. Generated research reports for AI receptionist leads
5. Created CSV/TSV spreadsheets with leads (Lima, OH area focus)
6. Built dedicated Indeed Leads Finder app (`indeed_app.py`) with full search filters
7. **-> Moved to hiring_apps repo to continue development**

## Important Rules

- Indeed scraping uses browser-like User-Agent headers — keep it
- Rate limiting is built in (2-3 second delays) — don't remove it
- Deduplication by company name is important
- Default search focus: receptionist, front desk, customer service roles
- Default test location: Lima, OH (configurable)
- All scrapers extend `BaseScraper` with context manager pattern
