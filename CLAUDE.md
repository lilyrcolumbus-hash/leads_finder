# CLAUDE.md - AI Assistant Guide for Lead Generation App

This document provides context for AI assistants working with this codebase.

## Project Overview

A modular, multi-source lead generation application designed to find business owners with communication pain points (missed calls, scheduling issues, customer communication problems). The app scrapes multiple platforms, filters leads using AI, and syncs them to HubSpot CRM.

**Key Features:**
- Multi-source lead scraping (Reddit, Hacker News, Google Search, Product Hunt, Google Maps)
- **Google Maps review analysis** - Detects communication pain points in business reviews
- AI-powered lead qualification (OpenAI/Anthropic)
- HubSpot CRM integration with full CRUD operations
- Dual interfaces: CLI (Rich TUI) and Web (Streamlit)
- Spanish-language CLI interface

## Directory Structure

```
lead-generation/
├── main.py                     # CLI entry point with interactive menu
├── web_app.py                  # Streamlit web interface (mobile-optimized)
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── .gitignore                  # Git exclusions
├── README.md                   # Documentation (Spanish)
└── src/
    ├── config.py               # Centralized Pydantic settings
    ├── scrapers/               # Multi-source lead scrapers
    │   ├── base_scraper.py     # Abstract base class
    │   ├── reddit_scraper.py   # Reddit RSS feeds
    │   ├── hackernews_scraper.py # HN Algolia API
    │   ├── google_scraper.py   # Google Custom Search
    │   ├── producthunt_scraper.py # Product Hunt RSS
    │   └── google_maps_scraper.py # Google Maps/Places API with review analysis
    ├── filters/
    │   └── ai_filter.py        # OpenAI/Anthropic lead scorer
    ├── crm/
    │   └── hubspot.py          # HubSpot CRUD operations
    └── utils/
        ├── models.py           # Pydantic data models
        └── logger.py           # Rich-formatted logging
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
HUBSPOT_API_KEY         # Required for CRM operations
GOOGLE_API_KEY          # Required for Google Search scraping
GOOGLE_SEARCH_ENGINE_ID # Required for Google Search scraping
GOOGLE_PLACES_API_KEY   # Optional (Google Maps scraping, falls back to GOOGLE_API_KEY)
OPENAI_API_KEY          # Optional (AI filtering)
ANTHROPIC_API_KEY       # Optional (AI filtering fallback)
```

## Code Conventions

### Type Hints and Data Validation
- **Pydantic** for all data models (`src/utils/models.py`)
- Type hints on all function signatures
- `Optional[T]` with `Field(default=None)` for nullable fields
- Enums for constants (`LeadSource`, `LeadStage`)

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
- Fallback mechanisms (AI fails -> keyword matching)
- Logging at INFO (console), DEBUG (file)

### Documentation Style
- Module docstrings at top of files
- Function docstrings with Args/Returns
- Inline comments for complex logic only
- Rich console output for user-facing messages

## Architecture Overview

### Scraping Pipeline
1. Scrapers fetch from sources (RSS, APIs)
2. `BaseScraper` provides: `fetch_url()`, `find_keywords()`, `extract_email()`, `extract_company()`
3. Results converted to `Lead` Pydantic models
4. Deduplication via dict with `lead.id` as key

### AI Filtering
1. Batch leads (default: 10 per batch)
2. Try OpenAI first, fallback to Anthropic
3. Score 0-1 based on business owner likelihood + urgency
4. Threshold: `>= 0.6` to qualify
5. If AI fails completely, use keyword count threshold

### CRM Integration
1. Qualified leads sent to HubSpot
2. Placeholder emails generated if none found: `{lead_id}@leadgen.placeholder`
3. Full lifecycle tracking (NEW -> CONTACTED -> DEMO -> PROPOSAL -> CLOSED)

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
- auto_repair, veterinarian, medical_clinic

**Locations** (configurable in `settings.google_maps_locations`):
- Default: Miami FL, Houston TX, Phoenix AZ, Los Angeles CA, Chicago IL

## Key Data Models

### Lead (`src/utils/models.py`)
```python
class Lead(BaseModel):
    id: str                          # Unique identifier
    source: LeadSource               # reddit, hacker_news, google_search, product_hunt, google_maps
    username: Optional[str]
    email: Optional[str]
    title: str
    content: str
    url: str
    keywords_matched: List[str]
    ai_score: Optional[float]        # 0-1
    is_qualified: bool
    sent_to_crm: bool
    hubspot_id: Optional[str]

    # Google Maps specific fields
    phone: Optional[str]             # Business phone number
    address: Optional[str]           # Business address
    website: Optional[str]           # Business website
    rating: Optional[float]          # Google Maps rating 1-5
    review_count: Optional[int]      # Total number of reviews
    business_type: Optional[str]     # Type of business
    place_id: Optional[str]          # Google Place ID

    # Pain detection fields
    has_pain: bool                   # Whether pain points detected in reviews
    pain_score: Optional[float]      # Pain intensity score 0-1
    pain_reviews: List[str]          # Reviews containing pain keywords
    pain_summary: Optional[str]      # Summary of pain points found
```

### LeadSource Enum
```python
class LeadSource(str, Enum):
    REDDIT = "reddit"
    HACKER_NEWS = "hacker_news"
    GOOGLE_SEARCH = "google_search"
    PRODUCT_HUNT = "product_hunt"
    GOOGLE_MAPS = "google_maps"
```

### Settings (`src/config.py`)
- Loaded via `pydantic-settings` from `.env`
- Includes: API keys, subreddit list, pain keywords, search queries, batch sizes
- Access via: `from src.config import settings`

## Dependencies

| Package | Purpose |
|---------|---------|
| `pydantic`, `pydantic-settings` | Data validation, settings |
| `httpx`, `requests` | HTTP clients |
| `beautifulsoup4`, `lxml` | HTML/XML parsing |
| `openai`, `anthropic` | AI APIs |
| `tenacity` | Retry logic |
| `rich` | Terminal formatting |
| `streamlit`, `pandas` | Web interface |
| `python-dotenv` | Environment loading |

## Technical Decisions

1. **No feedparser**: Uses stdlib `xml.etree.ElementTree` for RSS parsing
2. **Mobile-first Streamlit**: CSS media queries, collapsed sidebar by default
3. **Dual AI providers**: OpenAI primary, Anthropic fallback
4. **Keyword fallback**: If AI fails, qualification via keyword matching
5. **Context managers**: All HTTP-heavy classes support `with` statement
6. **Rate limiting**: 1-2 second delays between requests

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
4. Register in `main.py` menu system

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
from src.filters.ai_filter import AIFilter
from src.crm.hubspot import HubSpotCRM
from src.config import settings

# Scrape all sources
leads = []
with RedditScraper() as scraper:
    leads.extend(scraper.scrape().leads)

# Filter with AI
ai_filter = AIFilter()
qualified = ai_filter.filter_leads(leads)

# Send to CRM
with HubSpotCRM() as crm:
    for lead in qualified:
        crm.create_contact(lead)
```

### Scrape Google Maps with pain detection
```python
from src.scrapers import GoogleMapsScraper

with GoogleMapsScraper() as scraper:
    batch = scraper.scrape()

    # All leads (with or without pain)
    all_leads = batch.leads

    # Filter leads WITH pain detected
    pain_leads = [l for l in batch.leads if l.has_pain]

    # Filter leads WITHOUT pain (still valid contacts)
    no_pain_leads = [l for l in batch.leads if not l.has_pain]

    for lead in pain_leads:
        print(f"{lead.title}: {lead.phone}")
        print(f"  Pain Score: {lead.pain_score}")
        print(f"  Pain Summary: {lead.pain_summary}")
```

### Scrape specific business type or location
```python
from src.scrapers import GoogleMapsScraper

with GoogleMapsScraper() as scraper:
    # Single location, all business types
    batch = scraper.scrape_single_location("Austin, TX")

    # Single business type, all locations
    batch = scraper.scrape_single_type("dentist")
```

### Access CRM data
```python
from src.crm.hubspot import HubSpotCRM
from src.config import settings

with HubSpotCRM(settings) as crm:
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
