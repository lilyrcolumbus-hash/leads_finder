# CLAUDE.md - AI Assistant Guide for Lead Generation App

This document provides context for AI assistants working with this codebase.

## Project Overview

A modular, multi-source lead generation application designed to find business owners with communication pain points (missed calls, scheduling issues, customer communication problems). The app scrapes 13+ platforms, filters leads using AI (Gemini/OpenAI/Anthropic), enriches contact data (Hunter.io/Apollo.io), persists locally in SQLite, syncs to Google Sheets, and pushes qualified leads to HubSpot CRM.

**Key Features:**
- Multi-source lead scraping (Reddit, Hacker News, Google Search, Product Hunt, Google Maps, Indeed, Yelp, LinkedIn, Facebook, Yellow Pages, BBB, Craigslist)
- **Google Maps review analysis** - Detects communication pain points in business reviews
- Triple-score lead qualification: Pain + Intent + Fit (0-100)
- AI-powered lead filtering (Google Gemini primary, OpenAI fallback, Anthropic fallback)
- **Gemini business analysis** - Website/social media/software needs detection
- Email enrichment via Hunter.io and Apollo.io
- Local SQLite database for lead persistence and deduplication
- Google Sheets sync via Apps Script webhook
- HubSpot CRM integration with full CRUD operations
- Concurrent scraping with ThreadPoolExecutor (4 workers)
- Dual interfaces: CLI (Rich TUI) and Web (Streamlit with analytics dashboard)
- Spanish-language CLI interface

## Directory Structure

```
leads_finder/
├── main.py                        # CLI entry point with interactive menu
├── web_app.py                     # Streamlit web interface (analytics, bilingual)
├── apps_script_template.js        # Google Apps Script for Sheets webhook receiver
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
├── .gitignore                     # Git exclusions
├── README.md                      # Documentation (Spanish)
├── data/                          # SQLite database (auto-created)
│   └── leads.db                   # Local lead persistence
├── logs/                          # Log files (auto-created)
│   └── lead_gen_YYYYMMDD_HHMMSS.log
└── src/
    ├── __init__.py
    ├── config.py                  # Centralized Pydantic settings
    ├── scrapers/                  # Multi-source lead scrapers (13 scrapers)
    │   ├── __init__.py
    │   ├── base_scraper.py        # Abstract base class
    │   ├── reddit_scraper.py      # Reddit RSS feeds
    │   ├── hackernews_scraper.py  # HN Algolia API
    │   ├── google_scraper.py      # Google Custom Search
    │   ├── producthunt_scraper.py # Product Hunt RSS
    │   ├── google_maps_scraper.py # Google Maps/Places API with review analysis
    │   ├── googlemaps_scraper.py  # Google Maps web scraping version
    │   ├── indeed_scraper.py      # Indeed job listings (hiring receptionist signals)
    │   ├── yelp_scraper.py        # Yelp reviews for service complaints
    │   ├── linkedin_scraper.py    # LinkedIn via Google Search
    │   ├── facebook_scraper.py    # Facebook business pages
    │   ├── yellowpages_scraper.py # Yellow Pages business listings
    │   ├── bbb_scraper.py         # Better Business Bureau listings
    │   └── craigslist_scraper.py  # Craigslist services/jobs
    ├── filters/
    │   ├── __init__.py
    │   ├── ai_filter.py           # Gemini/OpenAI/Anthropic lead scorer
    │   └── gemini_analyzer.py     # Gemini business website analyzer
    ├── crm/
    │   ├── __init__.py
    │   └── hubspot.py             # HubSpot CRUD operations
    ├── database/
    │   ├── __init__.py
    │   └── sqlite_db.py           # Local SQLite lead persistence
    ├── enrichment/
    │   ├── __init__.py
    │   ├── hunter.py              # Hunter.io email lookup & verification
    │   └── apollo_enricher.py     # Apollo.io contact enrichment
    ├── sheets/
    │   ├── __init__.py
    │   └── google_sheets.py       # Google Sheets sync via Apps Script
    └── utils/
        ├── __init__.py
        ├── models.py              # Pydantic data models (Lead, LeadBatch, enums)
        ├── logger.py              # Rich-formatted logging
        ├── scoring.py             # Triple Score System (Pain + Intent + Fit)
        ├── lead_manager.py        # Lead deduplication, JSON persistence, CSV export
        ├── background_tasks.py    # Background task management
        └── hunter_enricher.py     # Hunter.io wrapper utilities
```

## Quick Reference Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Run CLI (interactive menu)
python main.py

# CLI with arguments
python main.py --scrape              # Run scraping only
python main.py --stats               # View statistics
python main.py --scrape --no-interactive  # Non-interactive mode

# Run Web Interface
streamlit run web_app.py
```

## Required Environment Variables

```
# CRM
HUBSPOT_API_KEY              # Required for CRM operations

# Google APIs
GOOGLE_API_KEY               # Required for Google Search scraping
GOOGLE_SEARCH_ENGINE_ID      # Required for Google Search scraping
GOOGLE_PLACES_API_KEY        # Optional (Google Maps scraping, falls back to GOOGLE_API_KEY)

# AI Providers (at least one recommended)
GEMINI_API_KEY               # Preferred AI provider (Gemini 2.0 Flash)
OPENAI_API_KEY               # Optional (AI filtering fallback)
ANTHROPIC_API_KEY            # Optional (AI filtering fallback)

# Enrichment
HUNTER_API_KEY               # Optional (email lookup via Hunter.io)
APOLLO_API_KEY               # Optional (contact enrichment via Apollo.io)

# Social
FACEBOOK_ACCESS_TOKEN        # Optional (Facebook scraping)

# Google Sheets Sync
GOOGLE_SHEETS_WEBHOOK_URL    # Optional (Apps Script web app URL for Sheets sync)
```

## Code Conventions

### Type Hints and Data Validation
- **Pydantic** for all data models (`src/utils/models.py`)
- Type hints on all function signatures
- `Optional[T]` with `Field(default=None)` for nullable fields
- Enums for constants (`LeadSource`, `LeadStage`, `LeadUrgency`, `LeadCategory`)

### Naming Conventions
- **Classes**: PascalCase (`BaseScraper`, `HubSpotCRM`, `LeadSource`)
- **Functions/Methods**: snake_case (`run_scraping`, `filter_leads_with_ai`)
- **Private methods**: underscore prefix (`_scrape_subreddit`, `_call_openai`)
- **Constants**: UPPERCASE (`BASE_URL`, `SYSTEM_PROMPT`)
- **Files**: snake_case (`reddit_scraper.py`, `ai_filter.py`)

### Class Patterns
- Abstract base classes with ABC (`BaseScraper`)
- Context managers (`__enter__`/`__exit__`) for resource management
- Pydantic `BaseModel` for data classes
- `@dataclass` for simple data containers (e.g., `HubSpotContact`)

### Error Handling
- Try/except with graceful degradation in scrapers
- `@retry` decorator with exponential backoff (tenacity)
- Fallback mechanisms (Gemini -> OpenAI -> Anthropic -> keyword matching)
- Logging at INFO (console), DEBUG (file)

### Documentation Style
- Module docstrings at top of files
- Function docstrings with Args/Returns
- Inline comments for complex logic only
- Rich console output for user-facing messages

## Architecture Overview

### Scraping Pipeline
1. Scrapers fetch from sources (RSS, APIs, web scraping)
2. `BaseScraper` provides: `fetch_url()`, `find_keywords()`, `extract_email()`, `extract_company()`
3. Results converted to `Lead` Pydantic models
4. Concurrent execution via ThreadPoolExecutor (4 workers)
5. Deduplication via hash-based tracking in `LeadManager`
6. Leads persisted to local SQLite database
7. Auto-sync to Google Sheets (if configured)

### Triple Score System (`src/utils/scoring.py`)
Leads are scored on three dimensions (each 0-100):
1. **Pain Score** - Based on pain keyword matches and urgency keywords
2. **Intent Score** - Detects hiring signals, solution-seeking, comparison shopping, budget readiness, urgency
3. **Fit Score** - Industry match, business type, company size indicators

Total Score = weighted combination of Pain + Intent + Fit. Leads are graded A/B/C/D.

### AI Filtering (`src/filters/ai_filter.py`)
1. Batch leads (default: 10 per batch)
2. Try Gemini first (preferred), fallback to OpenAI, then Anthropic
3. Score 0-1 with categorization: **pain**, **opportunity**, or **cold**
4. Threshold: `>= 0.3` to qualify (pain >= 0.6 with explicit pain, opportunity 0.3-0.6)
5. If AI fails completely, use keyword count threshold
6. Returns `ai_score`, `ai_reasoning`, `has_explicit_pain`, `lead_category`

### Gemini Business Analyzer (`src/filters/gemini_analyzer.py`)
- Analyzes business websites via Google Gemini REST API
- Detects: social media presence, chatbot/live chat, online booking, software needs
- Populates `has_website`, `has_social_media`, `software_needs`, `gemini_analysis` fields

### Local Database (`src/database/sqlite_db.py`)
- SQLite persistence at `data/leads.db`
- Full Lead model storage with all fields
- Scrape run tracking with `start_scrape_run()` / `run_id`
- Deduplication by lead ID
- CSV export for qualified or all leads
- Statistics queries (total, qualified, by-source breakdown)

### Enrichment Services
- **Hunter.io** (`src/enrichment/hunter.py`): Email lookup by domain, email verification, domain employee discovery
- **Apollo.io** (`src/enrichment/apollo_enricher.py`): Email verification (95%+ accuracy), direct phone numbers, company data (size, revenue, industry), LinkedIn profiles, job title/seniority

### Google Sheets Sync (`src/sheets/google_sheets.py`)
- Sends leads to Google Sheets via Apps Script webhook
- Buffered batch sending (configurable batch size, default 10)
- Auto-flushes every N leads
- Context manager support
- `apps_script_template.js` provides the receiver-side Apps Script code

### CRM Integration
1. Qualified leads sent to HubSpot
2. Placeholder emails generated if none found: `{lead_id}@leadgen.placeholder`
3. Full lifecycle tracking (NEW -> CONTACTED -> DEMO -> PROPOSAL -> CLOSED)
4. Methods: `create_contact()`, `send_leads_to_crm()`, `search_contacts()`, `update_lead_stage()`, `add_note()`, `mark_as_won()`, `mark_as_lost()`, `delete_contact()`, `test_connection()`, `get_statistics()`

### Google Maps Scraper (Pain Detection)
The Google Maps scraper (`src/scrapers/google_maps_scraper.py`) uses Google Places API to:

1. **Search businesses** by type and location (configurable in settings)
2. **Extract contact info**: phone, address, website, email
3. **Analyze reviews** for communication pain points
4. **Calculate pain score** (0-1) based on negative review frequency
5. **Mark leads** with `has_pain` flag regardless of pain detection

**Pain Detection Process:**
```
Reviews → Keyword Matching → Pain Score Calculation → Lead Flagging
```

**Review Pain Keywords** (configurable in `settings.review_pain_keywords`):
- "never answers", "no one picks up", "can't get through"
- "went to voicemail", "hard to reach", "no response"
- "terrible communication", "ignored my calls"

**Business Types** (configurable in `settings.google_maps_business_types`):
- plumber, electrician, hvac, dentist, lawyer
- accountant, real_estate_agent, contractor
- auto_repair, veterinarian, medical_clinic, salon, restaurant

**Locations** (configurable in `settings.google_maps_locations`):
- Default: Miami FL, Houston TX, Phoenix AZ, Los Angeles CA, Chicago IL

## Key Data Models

### LeadSource Enum
```python
class LeadSource(str, Enum):
    REDDIT = "reddit"
    HACKER_NEWS = "hacker_news"
    GOOGLE_SEARCH = "google_search"
    PRODUCT_HUNT = "product_hunt"
    GOOGLE_MAPS = "google_maps"
    INDEED = "indeed"
    YELP = "yelp"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
```

### LeadUrgency Enum
```python
class LeadUrgency(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    HOT = "hot"
    MEDIUM = "medium"
    WARM = "warm"
    LOW = "low"
    COLD = "cold"
```

### LeadCategory Enum
```python
class LeadCategory(str, Enum):
    PAIN = "pain"               # Explicit pain/problem detected
    OPPORTUNITY = "opportunity"  # No explicit pain but potential customer
    COLD = "cold"               # Low potential
```

### Lead (`src/utils/models.py`)
```python
class Lead(BaseModel):
    # Identification
    id: str
    source: LeadSource

    # Contact info
    username: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    name: Optional[str]
    company: Optional[str]

    # Professional & Social
    linkedin: Optional[str]
    twitter: Optional[str]
    position: Optional[str]
    author: Optional[str]

    # Company info
    employees: Optional[str]        # e.g., '10-50'
    revenue: Optional[str]
    country: Optional[str]

    # Content
    title: str
    content: str
    url: str

    # Metadata
    keywords_matched: List[str]
    subreddit: Optional[str]
    industry: Optional[str]

    # Triple Score System (0-100 each)
    pain_score: Optional[float]
    intent_score: Optional[float]
    fit_score: Optional[float]
    total_score: Optional[float]
    urgency: Optional[LeadUrgency]
    urgency_keywords_matched: List[str]
    score_breakdown: Optional[dict]

    # Google Maps specific
    address: Optional[str]
    review_count: Optional[int]
    business_type: Optional[str]
    place_id: Optional[str]

    # Pain detection (Google Maps reviews)
    has_pain: bool = False
    pain_reviews: List[str]
    pain_summary: Optional[str]

    # AI Analysis
    ai_score: Optional[float]       # 0-1 from AI filter
    ai_reasoning: Optional[str]
    is_qualified: bool = False
    lead_category: Optional[LeadCategory]
    has_explicit_pain: bool = False

    # Gemini Business Analysis
    software_needs: Optional[str]
    has_website: Optional[bool]
    has_social_media: Optional[bool]
    gemini_analysis: Optional[str]

    # Tracking
    found_at: datetime
    sent_to_crm: bool = False
    hubspot_id: Optional[str]
    posted_at: Optional[datetime]
    location: Optional[str]
    website: Optional[str]
    rating: Optional[float]         # 1-5

    # CRM fields
    status: Optional[str] = "new"
    notes: Optional[str]
    tags: List[str]

    # Extra data (enrichment services)
    extra_data: Optional[Dict[str, Any]]
```

### Settings (`src/config.py`)
- Loaded via `pydantic-settings` from `.env`
- Includes: API keys (10+), subreddit list, pain keywords, urgency keywords, search queries, industries dict, scoring weights, batch sizes, Google Maps config
- Access via: `from src.config import settings`
- Notable settings:
  - `scoring_weights`: dict with 6 components (keyword_match, urgency_keyword, multiple_pain_points, recent_post, solution_seeking, industry_match)
  - `industries`: dict mapping 10 industry names to keyword lists
  - `urgency_keywords`: 17 urgency-related keywords
  - `max_leads_per_source`: 50 (default)
  - `ai_filter_batch_size`: 10 (default)
  - `google_sheets_batch_size`: 10 (default)
  - `google_maps_max_results_per_search`: 20
  - `google_maps_max_reviews_per_business`: 10
  - `google_maps_min_reviews`: 5

## Dependencies

| Package | Purpose |
|---------|---------|
| `pydantic`, `pydantic-settings` | Data validation, settings |
| `httpx`, `requests` | HTTP clients |
| `beautifulsoup4`, `lxml` | HTML/XML parsing |
| `openai` | OpenAI API client |
| `anthropic` | Anthropic API client |
| `google-generativeai` | Google Gemini API |
| `tenacity` | Retry logic |
| `rich` | Terminal formatting |
| `streamlit`, `pandas` | Web interface |
| `python-dotenv` | Environment loading |

## Technical Decisions

1. **No feedparser**: Uses stdlib `xml.etree.ElementTree` for RSS parsing
2. **Mobile-first Streamlit**: CSS media queries, collapsed sidebar by default
3. **Triple AI providers**: Gemini primary, OpenAI fallback, Anthropic fallback
4. **Keyword fallback**: If all AI providers fail, qualification via keyword matching
5. **Context managers**: All HTTP-heavy classes support `with` statement
6. **Rate limiting**: 1-2 second delays between requests
7. **Gemini REST API**: Uses direct HTTP calls to avoid gRPC/SSL issues with the SDK
8. **SQLite local persistence**: Leads survive between runs, enables deduplication
9. **Concurrent scraping**: ThreadPoolExecutor with 4 workers for parallel scraping
10. **Google Sheets via Apps Script**: Webhook-based sync avoids OAuth complexity
11. **Dual Google Maps scrapers**: API version (Places API) and web scraping version

## Adding a New Scraper

1. Create `src/scrapers/new_source_scraper.py`
2. Inherit from `BaseScraper`:
```python
from src.scrapers.base_scraper import BaseScraper

class NewSourceScraper(BaseScraper):
    def __init__(self, settings):
        super().__init__(settings)

    def scrape(self) -> List[Lead]:
        # Implementation
        pass
```
3. Add source to `LeadSource` enum in `src/utils/models.py`
4. Export in `src/scrapers/__init__.py`
5. Register in `main.py` menu system

## Logging

- Logs directory: `logs/`
- File format: `lead_gen_YYYYMMDD_HHMMSS.log`
- Console: INFO level with Rich formatting
- File: DEBUG level for detailed tracing
- Logger usage: `from src.utils.logger import get_logger; logger = get_logger(__name__)`

## Common Tasks

### Run full scraping pipeline
```python
from src.scrapers import RedditScraper, HackerNewsScraper, GoogleScraper, ProductHuntScraper, GoogleMapsScraper
from src.filters.ai_filter import AILeadFilter
from src.crm.hubspot import HubSpotCRM
from src.database.sqlite_db import LeadDatabase
from src.config import settings

# Initialize database
db = LeadDatabase()

# Scrape all sources
leads = []
with RedditScraper() as scraper:
    leads.extend(scraper.scrape().leads)

# Filter with AI
ai_filter = AILeadFilter()
all_leads = ai_filter.filter_leads(leads)  # Returns ALL leads with categories

# Separate by category
pain_leads = [l for l in all_leads if l.lead_category == LeadCategory.PAIN]
opportunity_leads = [l for l in all_leads if l.lead_category == LeadCategory.OPPORTUNITY]

# Save to local database
for lead in all_leads:
    db.save_lead(lead)

# Send qualified leads to CRM
with HubSpotCRM() as crm:
    for lead in pain_leads:
        crm.create_contact(lead)
```

### Enrich leads with Hunter.io
```python
from src.enrichment.hunter import HunterClient

hunter = HunterClient()
result = hunter.find_email("example.com")
verification = hunter.verify_email("user@example.com")
```

### Sync leads to Google Sheets
```python
from src.sheets.google_sheets import GoogleSheetsSync

with GoogleSheetsSync() as sheets:
    sheets.send_leads(leads_list)
```

### Scrape Google Maps with pain detection
```python
from src.scrapers import GoogleMapsScraper

with GoogleMapsScraper() as scraper:
    batch = scraper.scrape()

    # Filter leads WITH pain detected
    pain_leads = [l for l in batch.leads if l.has_pain]

    for lead in pain_leads:
        print(f"{lead.title}: {lead.phone}")
        print(f"  Pain Score: {lead.pain_score}")
        print(f"  Pain Summary: {lead.pain_summary}")
```

### Scrape specific business type or location
```python
from src.scrapers import GoogleMapsScraper

with GoogleMapsScraper() as scraper:
    batch = scraper.scrape_single_location("Austin, TX")
    batch = scraper.scrape_single_type("dentist")
```

### Score leads with Triple Score System
```python
from src.utils.scoring import score_lead, grade_lead

scored_lead = score_lead(lead)
print(f"Pain: {scored_lead.pain_score}, Intent: {scored_lead.intent_score}, Fit: {scored_lead.fit_score}")
print(f"Total: {scored_lead.total_score}, Grade: {grade_lead(scored_lead)}")
```

### Access local database
```python
from src.database.sqlite_db import LeadDatabase

db = LeadDatabase()
all_leads = db.get_all_leads()
stats = db.get_statistics()
db.export_csv("leads_export.csv")
```

### Access CRM data
```python
from src.crm.hubspot import HubSpotCRM
from src.config import settings

with HubSpotCRM(settings) as crm:
    crm.test_connection()
    contacts = crm.get_all_contacts()
    stats = crm.get_statistics()
```

## Notes for AI Assistants

- **Language**: CLI interface and README are in Spanish; code comments in English
- **No tests**: No test suite currently exists
- **No CI/CD**: No GitHub Actions or similar configured
- **No linting config**: No .flake8, pyproject.toml, or similar
- When modifying scrapers, maintain the context manager pattern
- Rate limiting is important - respect 1-2 second delays
- Always validate against Pydantic models
- AI filter class is named `AILeadFilter` (not `AIFilter`)
- Gemini uses REST API directly via `httpx` (not the Python SDK) to avoid gRPC SSL issues
- The `ai_score` field is 0-1 (from AI filter), while `pain_score`/`intent_score`/`fit_score`/`total_score` are 0-100
- Two Google Maps scrapers exist: `GoogleMapsScraper` (API) and `GoogleMapsWebScraper` (web scraping)
- Local SQLite database at `data/leads.db` persists leads between sessions
