#!/usr/bin/env python3
"""
CC Lead Finder - by Claude Code
Finds leads, investigates them deeply, and writes results to Google Sheets.

Usage:
    python cc_lead_finder.py "plumbers" "Lima Ohio"
    python cc_lead_finder.py "hvac" "Houston"
    python cc_lead_finder.py "dentists" "Los Angeles"

Requirements:
    pip install gspread google-auth httpx beautifulsoup4 lxml ddgs
"""

import sys
import re
import json
import time
import random
import argparse
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

# Google Sheets
import gspread
from google.oauth2.service_account import Credentials

# ==================== CONFIG ====================

SHEET_ID = "1P0A_7ptV2791YwQHH9wHAm0C41oPMmW7K1rn7afqHPY"
CREDENTIALS_FILE = Path(__file__).parent / "credentials" / "google_sheets.json"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
]

def get_headers():
    """Get randomized headers to avoid detection."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

# Nearby cities/towns for expanded area search
# Add more areas as needed - format: "main city state" -> [list of nearby towns]
AREA_EXPANSIONS = {
    "lima ohio": [
        "Lima Ohio",
        "Allen County Ohio",
        "Wapakoneta Ohio",
        "Findlay Ohio",
        "Sidney Ohio",
        "Van Wert Ohio",
    ],
}

# Column headers for the Sheet
SHEET_HEADERS = [
    "Date",
    "Source",
    "Business",
    "Phone",
    "Email",
    "Website",
    "Address",
    "City",
    "Google Rating",
    "Total Reviews",
    "NEEDS AI RECEPTIONIST?",
    "AI Receptionist Evidence",
    "Communication Complaints (Clients)",
    "Business Complaints",
    "Website Quality",
]

# Keywords that indicate communication pain
PAIN_KEYWORDS_CLIENTS = [
    "no contestan", "no answer", "never answer", "don't answer",
    "no devuelven", "never call back", "didn't call back", "no callback",
    "imposible comunicarse", "can't reach", "hard to reach", "unreachable",
    "no responden", "no response", "never responded", "didn't respond",
    "left voicemail", "voicemail", "buzón", "buzon",
    "waited forever", "long wait", "on hold", "esperé mucho",
    "poor communication", "mala comunicación", "bad communication",
    "never picked up", "didn't pick up", "no pick up",
    "called multiple times", "llamé varias veces",
    "no one answered", "nadie contestó", "nadie contesto",
    "couldn't get through", "couldn't get ahold",
    "ignored my call", "ignored my message",
    "terrible customer service", "worst customer service",
    "rude on the phone", "rude receptionist",
    "missed appointment", "forgot appointment", "no-show",
]

PAIN_KEYWORDS_BUSINESS = [
    "can't answer all calls", "miss calls", "missing calls",
    "too busy to answer", "overwhelmed with calls",
    "need receptionist", "need someone to answer",
    "losing customers", "losing clients", "perdemos clientes",
    "no time to answer", "no tengo tiempo",
    "after hours", "fuera de horario",
    "need help with phones", "need front desk",
    "short staffed", "understaffed", "falta personal",
]

JUNK_DOMAINS = [
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "aol.com", "mail.com", "icloud.com", "example.com",
    "wixsite.com", "squarespace.com", "wordpress.com",
    "facebook.com", "instagram.com", "twitter.com",
    "yelp.com", "google.com", "bbb.org",
    "sentry.io", "sentry.wixpress.com",
    "onmschina.cn", "partner.onmschina.cn",
    "fourthcoffee.partner.onmschina.cn",
    "indeed.com", "linkedin.com",
    "protection.outlook.com",
]

# Junk email patterns - emails that are never from a real local business
JUNK_EMAIL_PATTERNS = [
    r"@.*\.gov$",        # Government emails
    r"@.*\.edu$",        # University emails
    r"@.*\.mil$",        # Military emails
    r"noreply@", r"no-reply@", r"donotreply@",
    r"@example\.", r"@test\.", r"@localhost",
    r"@.*onmschina", r"@.*fourthcoffee",
    r"marketing@.*wdn\.", r"editor@", r"webmaster@",
    r"abuse@", r"postmaster@", r"hostmaster@",
    r"@.*sentry\.", r"@.*wixpress\.",
]

# URLs from these domains are NEVER a real local business - always skip
SKIP_URL_DOMAINS = [
    "amazon.com", "amazon.co", "ebay.com", "walmart.com", "target.com",
    "homedepot.com", "lowes.com", "menards.com", "costco.com",
    "tiktok.com", "pinterest.com", "reddit.com", "quora.com",
    "wikipedia.org", "wikihow.com", "britannica.com",
    "youtube.com", "vimeo.com", "dailymotion.com",
    "nytimes.com", "washingtonpost.com", "cnn.com", "foxnews.com",
    "bbc.com", "bbc.co.uk", "usatoday.com", "npr.org",
    "indeed.com/career-advice", "indeed.com/q-", "glassdoor.com",
    "ziprecruiter.com", "monster.com", "careerbuilder.com",
    "tripadvisor.com", "zillow.com", "realtor.com", "redfin.com",
    "irs.gov", "sba.gov", "usa.gov", "ohio.gov", "state.oh.us",
    "census.gov", "bls.gov", "osha.gov",
    "ashley", "wayfair.com", "overstock.com", "ikea.com",
    "arbys.com", "mcdonalds.com", "wendys.com", "subway.com",
    "dating", "match.com", "tinder.com",
    "webmd.com", "healthline.com", "mayoclinic.org",
    "twitter.com", "x.com", "instagram.com",
    "forbes.com", "inc.com", "entrepreneur.com", "businessinsider.com",
    "medium.com", "blogspot.com", "tumblr.com",
    "coursera.org", "udemy.com", "edu/",
    "apple.com", "microsoft.com", "samsung.com",
    "mapquest.com", "waze.com",
    "dmv", "bmv", "ezpass", "e-zpass",
    "crimegrade.org", "neighborhoodscout.com", "areavibes.com",
    "salary.com", "payscale.com", "zippia.com",
    "prnewswire.com", "globenewswire.com", "accesswire.com",
    "patch.com", "news", "gazette", "herald", "tribune",
    "onmschina.cn", "partner.onmschina",
]


# ==================== SCRAPING ====================

def get_client():
    """Create HTTP client with retry and anti-detection."""
    return httpx.Client(
        headers=get_headers(),
        timeout=30,
        follow_redirects=True,
        verify=True,
    )


def random_delay(min_s=1, max_s=3):
    """Random delay to be respectful."""
    time.sleep(random.uniform(min_s, max_s))


def search_ddg(query: str, max_results: int = 25) -> list:
    """Search DuckDuckGo using the proper library."""
    try:
        results = list(DDGS().text(query, max_results=max_results))
        return results
    except Exception as e:
        print(f"    Error DDG search: {e}")
        return []


# Words that indicate a list/aggregator page, not an individual business
LIST_SKIP_WORDS = [
    "top 10", "top 5", "top 15", "top 20", "top 25", "top 50",
    "best 10", "best 20", "best 30", "best of",
    "the best", "the top", "the most",
    "best plumb", "best hvac", "best dent", "best law", "best electric",
    "best roof", "best paint", "best landscap", "best pest", "best clean",
    "top rated", "top-rated", "highest rated", "highest-rated",
    "most trusted", "most reliable",
    "homeadvisor", "home advisor", "homeguide", "porch.com",
    "networx", "house method", "angi list",
    "services provided by", "services experts",
    "near me", "near you", "in your area",
    "directory", "listing", "listings",
    "companies in", "services in", "contractors in", "providers in",
    "how to", "what is", "how much", "cost of", "vs ",
    "plumbers in", "hvac in", "dentists in", "lawyers in",
    "electricians in", "roofers in", "painters in",
    " near ", "results for", "search results",
    "find a ", "find the best", "hire a ", "call a ",
    "choosing a ", "choosing the", "picking a ",
    "fixtures near", "supplies near", "parts near",
    "all plumb", "all hvac", "all dent",
    "category", "categories",
    "tips for", "guide to", "advice", "things to know",
    "compare ", "comparison", "alternatives",
    "jobs in", "careers in", "salary",
    "review of", "reviews of",
    "map of", "locations in",
    "free estimates", "get quotes", "request a quote",
    "certified ", "licensed ",
    "wikipedia", "wiki",
    "what to look for", "questions to ask",
    "signs you need", "when to call", "when to hire",
    "average cost", "price range", "pricing guide",
    "do you need", "should you", "why you need",
    "emergency plumb", "emergency hvac", "emergency electric",
    "24/7 plumb", "24/7 hvac", "24 hour plumb", "24 hour hvac",
]

# Patterns like "Plumber near Lima" or "HVAC Services Lima OH"
LIST_SKIP_PATTERNS = [
    r'^(plumb|hvac|dent|law|electric|roof|paint|carpet|landscap|pest|clean)\w*\s+(near|in|around|for)\s+',
    r'^(plumb|hvac|dent|law|electric|roof|paint|carpet|landscap|pest|clean)\w*\s+services?\s*$',
    r'^(plumb|hvac|dent|law|electric|roof|paint|carpet|landscap|pest|clean)\w*\s+services?\s+(in|near|around)\s+',
    r'^(plumb|hvac|dent|law|electric|roof|paint|carpet|landscap|pest|clean)\w*\s+compan',
    r'^(plumb|hvac|dent|law|electric|roof|paint|carpet|landscap|pest|clean)\w*\s+contractor',
    r'^(plumb|hvac|dent|law|electric|roof|paint|carpet|landscap|pest|clean)\w*\s+repair',
    r'^(plumb|hvac|dent|law|electric|roof|paint|carpet|landscap|pest|clean)\w*\s+fixture',
    r'^\d+\s+(best|top|cheap|affordable|rated)',
    r'^the\s+\d+\s+(best|top|most)',
    r'^(best|top|cheap|affordable|reliable|trusted|expert)\s+(plumb|hvac|dent|law|electric|roof|paint|landscap|pest|clean)',
    r'better business bureau',
    r'bbb\.org',
    r'yelp\.com',
    r'yellowpages\.com',
    r'angi\.com|angieslist',
    r'thumbtack\.com',
]


def is_list_page(title: str) -> bool:
    """Check if a title is a list/aggregator page instead of a real business."""
    title_lower = title.lower().strip()
    # Check skip words
    if any(skip in title_lower for skip in LIST_SKIP_WORDS):
        return True
    # Check regex patterns
    if any(re.search(pat, title_lower) for pat in LIST_SKIP_PATTERNS):
        return True
    # Too short to be a real business name
    if len(title_lower) < 4:
        return True
    return False


# Keywords that indicate a business is relevant to each niche
NICHE_KEYWORDS = {
    "plumbers": ["plumb", "plumber", "plumbing", "drain", "sewer", "pipe", "water heater",
                  "faucet", "toilet", "septic", "backflow", "rooter", "hydro jetting"],
    "hvac": ["hvac", "heating", "cooling", "air condition", "furnace", "heat pump",
             "ventilation", "duct", "ac repair", "boiler"],
    "dentists": ["dent", "dental", "orthodont", "oral", "tooth", "teeth", "implant",
                 "periodon", "endodon", "prosthodon"],
    "lawyers": ["law", "lawyer", "attorney", "legal", "firm", "counsel", "litigation",
                "paralegal", "solicitor"],
    "electricians": ["electric", "electrician", "wiring", "panel", "circuit", "voltage",
                     "generator", "lighting"],
    "roofers": ["roof", "roofing", "gutter", "shingle", "siding"],
    "painters": ["paint", "painting", "stain", "coat", "drywall"],
    "landscapers": ["landscap", "lawn", "mowing", "tree service", "irrigation", "garden"],
    "pest control": ["pest", "exterminator", "termite", "rodent", "bug", "insect"],
    "cleaners": ["clean", "cleaning", "janitorial", "maid", "housekeep", "carpet clean"],
}


def is_relevant_to_niche(name: str, snippet: str, niche: str) -> bool:
    """Check if a business name or snippet is actually relevant to the niche."""
    niche_lower = niche.lower().strip()
    text = (name + " " + snippet).lower()

    # Get keywords for this niche
    keywords = NICHE_KEYWORDS.get(niche_lower, [])

    # If niche not in our dictionary, use the niche word itself
    if not keywords:
        keywords = [niche_lower.rstrip("s"), niche_lower]

    return any(kw in text for kw in keywords)


def should_skip_url(url: str) -> bool:
    """Check if a URL belongs to a non-business site that should always be skipped."""
    url_lower = url.lower()
    return any(domain in url_lower for domain in SKIP_URL_DOMAINS)


def is_generic_name(name: str) -> bool:
    """Check if a cleaned name is a generic phrase, not an actual business name."""
    n = name.lower().strip()
    # Generic article/listicle phrases
    generic_starts = [
        "the best ", "the top ", "the most ", "best ", "top ",
        "cheap ", "cheapest ", "affordable ", "reliable ", "trusted ",
        "expert ", "professional ", "quality ", "emergency ",
        "24 hour ", "24/7 ", "local ", "nearby ",
        "how to ", "what to ", "when to ", "why ", "where to ",
        "find ", "hire ", "call ", "choose ", "choosing ",
        "signs you", "do you need", "should you", "things to",
    ]
    if any(n.startswith(prefix) for prefix in generic_starts):
        return True
    # Generic endings that indicate an article, not a business
    generic_ends = [
        " near me", " near you", " in your area",
        " you can trust", " to call", " to hire",
        " for your home", " for your business",
        " worth the money", " this year",
    ]
    if any(n.endswith(suffix) for suffix in generic_ends):
        return True
    # Name is ONLY a niche word + optional city/state (e.g. "Plumbing Lima OH", "Plumber Services")
    only_niche = re.match(
        r'^(plumb\w*|hvac|heat\w*|cool\w*|dent\w*|law\w*|attorney\w*|electric\w*|'
        r'roof\w*|paint\w*|landscap\w*|pest\w*|clean\w*|drain\w*|sewer\w*|septic\w*)'
        r'(\s+(services?|repair|company|contractors?|inc|llc|pro|pros|experts?|specialists?|solutions?'
        r'|in|near|around|of|\w{2,15}))*\s*$',
        n, re.IGNORECASE
    )
    if only_niche:
        return True
    # Non-English content (common foreign words from directories)
    foreign_words = ["aadress", "telefon", "lahtiolekuajad", "öppettider", "horario",
                     "adresse", "telefonnummer", "adresa", "numéro", "indirizzo"]
    if any(fw in n for fw in foreign_words):
        return True
    # "Home - Something" or "Home | Something" (usually not a business name)
    if n.startswith("home ") and len(n.split()) <= 5:
        return True
    # "Services provided by..." pattern
    if "services provided by" in n or "services experts" in n:
        return True
    return False


def clean_business_name(title: str) -> str:
    """Clean a business name from a search result title."""
    # Remove common suffixes from search engines and directories
    name = re.sub(r'\s*[-–|:]\s*(Yelp|Google|BBB|Better Business|Yellow Pages|YP|Facebook|'
                  r'Angi|Angie|Thumbtack|Manta|LinkedIn|Indeed|Nextdoor|Craigslist|'
                  r'Reviews|Updated|Bing|Yahoo|Maps|Company Profile|Overview|'
                  r'Ratings|Cost|Prices|Photos|Videos|Posts|HomeAdvisor|Porch|'
                  r'Networx|Houzz|Expertise|Bark|TaskRabbit).*$', '', title, flags=re.IGNORECASE).strip()
    # Remove "aadress, telefon..." (foreign directory suffixes)
    name = re.sub(r'\s*[-–—,]\s*(aadress|telefon|öppettider|horario|adresse|numéro).*$', '', name, flags=re.IGNORECASE).strip()
    # Remove leading numbers
    name = re.sub(r'^\d+\.\s*', '', name).strip()
    # Remove parenthetical info
    name = re.sub(r'\s*\(.*?\)\s*', ' ', name).strip()
    # Remove price patterns
    name = re.sub(r'\$[\d,.]+', '', name).strip()
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def extract_phone_from_text(text: str) -> str:
    """Extract a US phone number from text."""
    match = re.search(r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', text)
    return match.group() if match else ""


def is_junk_email(email: str) -> bool:
    """Check if an email is junk (government, generic, fake, etc.)."""
    email_lower = email.lower()
    domain = email_lower.split("@")[1] if "@" in email_lower else ""
    if domain in JUNK_DOMAINS:
        return True
    if email_lower.endswith(".png") or email_lower.endswith(".jpg"):
        return True
    return any(re.search(pat, email_lower) for pat in JUNK_EMAIL_PATTERNS)


def extract_email_from_text(text: str) -> str:
    """Extract an email from text."""
    match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    if match:
        email = match.group().lower()
        if not is_junk_email(email):
            return email
    return ""


def extract_address_from_text(text: str) -> str:
    """Extract a US street address from text."""
    match = re.search(r'\d+\s+[\w\s]+(?:St|Ave|Rd|Dr|Blvd|Ln|Way|Ct|Pkwy|Hwy)[\w\s,]*', text)
    return match.group().strip() if match else ""


def scrape_general_search(niche: str, city: str) -> list:
    """Find businesses via DuckDuckGo text search."""
    leads = []

    queries = [
        f"{niche} in {city} phone number",
        f"best {niche} {city} contact",
        f"emergency {niche} {city}",
        f"24 hour {niche} {city}",
        f"{niche} near {city} Ohio",
    ]

    print(f"  Buscando negocios: {niche} in {city}...")

    for query_text in queries:
        results = search_ddg(query_text, max_results=20)

        for r in results:
            title = r.get("title", "")
            link = r.get("href", "")
            snippet = r.get("body", "")

            # Skip non-business sites
            if should_skip_url(link):
                continue

            # Skip list pages
            if is_list_page(title):
                continue

            name = clean_business_name(title)
            if not name or len(name) < 3 or len(name) > 80 or is_generic_name(name):
                continue

            leads.append({
                "name": name,
                "phone": extract_phone_from_text(snippet),
                "email_snippet": extract_email_from_text(snippet),
                "website": link,
                "address": extract_address_from_text(snippet),
                "city": city,
                "snippet": snippet,
                "source": "Web Search",
            })

        random_delay(1, 2)

    print(f"    Web Search: {len(leads)} resultados")
    return leads


def scrape_yelp_search(niche: str, city: str) -> list:
    """Find Yelp listings via DuckDuckGo."""
    leads = []

    print(f"  Buscando en Yelp: {niche} in {city}...")

    all_results = []
    for q in [f"site:yelp.com {niche} {city}", f"site:yelp.com best {niche} near {city}"]:
        all_results.extend(search_ddg(q, max_results=15))
        random_delay(0.5, 1)

    results = all_results

    for r in results:
        title = r.get("title", "")
        link = r.get("href", "")
        snippet = r.get("body", "")

        if "yelp.com/biz/" not in link:
            continue
        if is_list_page(title):
            continue

        name = clean_business_name(title)
        if not name or len(name) < 3 or len(name) > 80 or is_generic_name(name):
            continue

        leads.append({
            "name": name,
            "phone": extract_phone_from_text(snippet),
            "website": link,
            "address": extract_address_from_text(snippet),
            "city": city,
            "source": "Yelp",
        })

    print(f"    Yelp: {len(leads)} resultados")
    return leads


def scrape_yellowpages_search(niche: str, city: str) -> list:
    """Find Yellow Pages listings via DuckDuckGo."""
    leads = []

    print(f"  Buscando en Yellow Pages: {niche} in {city}...")

    all_results = []
    for q in [f"site:yellowpages.com {niche} {city}", f"site:yellowpages.com {niche} near {city} Ohio"]:
        all_results.extend(search_ddg(q, max_results=15))
        random_delay(0.5, 1)

    results = all_results

    for r in results:
        title = r.get("title", "")
        link = r.get("href", "")
        snippet = r.get("body", "")

        if "yellowpages.com" not in link:
            continue
        if is_list_page(title):
            continue

        name = clean_business_name(title)
        if not name or len(name) < 3 or len(name) > 80 or is_generic_name(name):
            continue

        leads.append({
            "name": name,
            "phone": extract_phone_from_text(snippet),
            "website": link,
            "address": extract_address_from_text(snippet),
            "city": city,
            "source": "Yellow Pages",
        })

    print(f"    Yellow Pages: {len(leads)} resultados")
    return leads


def scrape_bbb_search(niche: str, city: str) -> list:
    """Find BBB listings and complaints via DuckDuckGo."""
    leads = []

    print(f"  Buscando en BBB: {niche} in {city}...")

    queries = [
        f"site:bbb.org {niche} {city}",
        f"site:bbb.org {niche} {city} complaints",
        f"site:bbb.org {niche} {city} customer reviews",
    ]

    all_results = []
    for q in queries:
        all_results.extend(search_ddg(q, max_results=10))
        random_delay(0.5, 1)

    results = all_results

    for r in results:
        title = r.get("title", "")
        link = r.get("href", "")
        snippet = r.get("body", "")

        if "bbb.org" not in link:
            continue
        if is_list_page(title):
            continue

        name = clean_business_name(title)
        if not name or len(name) < 3 or len(name) > 80 or is_generic_name(name):
            continue

        leads.append({
            "name": name,
            "phone": extract_phone_from_text(snippet),
            "website": link,
            "address": extract_address_from_text(snippet),
            "city": city,
            "source": "BBB",
        })

    print(f"    BBB: {len(leads)} resultados")
    return leads


def scrape_linkedin_search(niche: str, city: str) -> list:
    """Find business LinkedIn profiles via DuckDuckGo."""
    leads = []

    print(f"  Buscando en LinkedIn: {niche} in {city}...")

    results = search_ddg(f"site:linkedin.com/company {niche} {city}", max_results=15)

    for r in results:
        title = r.get("title", "")
        link = r.get("href", "")
        snippet = r.get("body", "")

        if "linkedin.com" not in link:
            continue
        if is_list_page(title):
            continue

        name = clean_business_name(title)
        if not name or len(name) < 3 or len(name) > 80 or is_generic_name(name):
            continue

        leads.append({
            "name": name,
            "phone": extract_phone_from_text(snippet),
            "website": link,
            "address": "",
            "city": city,
            "source": "LinkedIn",
        })

    print(f"    LinkedIn: {len(leads)} resultados")
    return leads


def scrape_indeed_hiring(niche: str, city: str) -> list:
    """Find businesses hiring receptionist/customer service via DuckDuckGo + Indeed."""
    leads = []

    print(f"  Buscando en Indeed (contratando recepcionista): {niche} in {city}...")

    queries = [
        f"site:indeed.com receptionist {niche} {city}",
        f"site:indeed.com \"customer service\" {niche} {city}",
        f"site:indeed.com \"front desk\" {niche} {city}",
        f"site:indeed.com \"phone\" {niche} {city} hiring",
        f"site:indeed.com \"office assistant\" {niche} {city}",
        f"site:indeed.com \"office manager\" {niche} {city}",
        f"site:indeed.com \"answering service\" OR \"call center\" {niche} {city}",
        f"site:indeed.com \"secretary\" OR \"dispatcher\" {niche} {city}",
    ]

    for query_text in queries:
        results = search_ddg(query_text, max_results=10)

        for r in results:
            title = r.get("title", "")
            link = r.get("href", "")
            snippet = r.get("body", "")

            if "indeed.com" not in link:
                continue

            # Skip Indeed search pages, career advice, company reviews pages, and salary pages
            if any(skip in link.lower() for skip in [
                "indeed.com/q-", "indeed.com/jobs?", "indeed.com/career-advice",
                "indeed.com/career", "indeed.com/salaries", "indeed.com/companies",
                "indeed.com/hire", "indeed.com/l-", "/pagead/", "indeed.com/cmp",
            ]):
                continue

            # Skip generic Indeed titles that aren't actual job postings
            title_lower = title.lower()
            if any(skip in title_lower for skip in [
                "indeed.com", "jobs in", "job search", "career advice",
                "salary", "how to", "what is", "interview questions",
                "resume", "cover letter",
            ]):
                continue

            # Try to extract company name from Indeed title format: "Job Title - Company Name"
            name = ""
            if " - " in title:
                parts = title.split(" - ")
                if len(parts) >= 2:
                    # Company is usually the second part; strip Indeed suffixes
                    candidate = parts[1].strip()
                    candidate = re.sub(r'\s*[-–|]\s*(Indeed|Job|Review|Hiring|Salary).*$', '', candidate, flags=re.IGNORECASE).strip()
                    # Skip if the "company" is just Indeed or a location
                    if candidate.lower() not in ["indeed", "indeed.com", ""] and len(candidate) >= 3:
                        name = candidate

            if not name or len(name) < 3 or is_generic_name(name):
                continue

            # Skip if name looks like a generic Indeed page title
            if any(skip in name.lower() for skip in ["indeed", "job search", "career"]):
                continue

            # Detect what they're hiring for
            hiring_role = ""
            for keyword in ["receptionist", "customer service", "front desk", "phone operator", "office manager", "secretary", "answering", "office assistant", "dispatcher", "call center"]:
                if keyword in title.lower() or keyword in snippet.lower():
                    hiring_role = keyword
                    break

            leads.append({
                "name": name,
                "phone": "",
                "website": link,
                "address": "",
                "city": city,
                "source": "Indeed",
                "hiring_role": hiring_role,
            })

        random_delay(1, 2)

    # Deduplicate within Indeed results
    seen = set()
    unique = []
    for lead in leads:
        key = lead["name"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(lead)

    print(f"    Indeed (contratando): {len(unique)} resultados")
    return unique


def scrape_google_maps_search(niche: str, city: str) -> list:
    """Find Google Maps/Business listings via DuckDuckGo."""
    leads = []

    print(f"  Buscando en Google Maps: {niche} in {city}...")

    results = search_ddg(f"site:google.com/maps {niche} {city}", max_results=15)

    for r in results:
        title = r.get("title", "")
        link = r.get("href", "")
        snippet = r.get("body", "")

        if "google.com" not in link:
            continue
        # Skip Google Maps utility/search pages (not individual business pages)
        if any(skip in link.lower() for skip in [
            "google.com/maps/search", "google.com/maps/place/@",
            "google.com/maps/dir", "google.com/maps?", "google.com/search",
            "support.google.com", "about.google.com",
        ]):
            continue
        if is_list_page(title):
            continue

        name = clean_business_name(title)
        if not name or len(name) < 3 or len(name) > 80 or is_generic_name(name):
            continue

        # Skip if name looks like a Google product page
        if any(skip in name.lower() for skip in ["google maps", "google search", "google my business"]):
            continue

        # Extract rating from snippet
        rating = ""
        rating_match = re.search(r'(\d+\.?\d*)\s*(?:stars?|estrellas?|rating)', snippet, re.IGNORECASE)
        if rating_match:
            rating = rating_match.group(1)

        leads.append({
            "name": name,
            "phone": extract_phone_from_text(snippet),
            "website": link,
            "address": extract_address_from_text(snippet),
            "city": city,
            "rating": rating,
            "source": "Google Maps",
        })

    print(f"    Google Maps: {len(leads)} resultados")
    return leads


def scrape_facebook_search(niche: str, city: str) -> list:
    """Find Facebook business pages via DuckDuckGo."""
    leads = []

    print(f"  Buscando en Facebook: {niche} in {city}...")

    results = search_ddg(f"site:facebook.com {niche} {city}", max_results=15)

    for r in results:
        title = r.get("title", "")
        link = r.get("href", "")
        snippet = r.get("body", "")

        if "facebook.com" not in link:
            continue

        # Skip personal profiles, groups, marketplace
        if any(skip in link for skip in ["/groups/", "/marketplace/", "/people/", "/events/"]):
            continue
        if is_list_page(title):
            continue

        name = clean_business_name(title)
        if not name or len(name) < 3 or len(name) > 80 or is_generic_name(name):
            continue

        leads.append({
            "name": name,
            "phone": extract_phone_from_text(snippet),
            "website": link,
            "address": "",
            "city": city,
            "source": "Facebook",
        })

    print(f"    Facebook: {len(leads)} resultados")
    return leads


def scrape_angi_search(niche: str, city: str) -> list:
    """Find Angi (Angie's List) listings via DuckDuckGo."""
    leads = []

    print(f"  Buscando en Angi: {niche} in {city}...")

    results = search_ddg(f"site:angi.com {niche} {city}", max_results=15)

    for r in results:
        title = r.get("title", "")
        link = r.get("href", "")
        snippet = r.get("body", "")

        if "angi.com" not in link:
            continue
        if is_list_page(title):
            continue

        name = clean_business_name(title)
        if not name or len(name) < 3 or len(name) > 80 or is_generic_name(name):
            continue

        leads.append({
            "name": name,
            "phone": extract_phone_from_text(snippet),
            "website": link,
            "address": "",
            "city": city,
            "source": "Angi",
        })

    print(f"    Angi: {len(leads)} resultados")
    return leads


def scrape_thumbtack_search(niche: str, city: str) -> list:
    """Find Thumbtack listings via DuckDuckGo."""
    leads = []

    print(f"  Buscando en Thumbtack: {niche} in {city}...")

    results = search_ddg(f"site:thumbtack.com {niche} {city}", max_results=15)

    for r in results:
        title = r.get("title", "")
        link = r.get("href", "")
        snippet = r.get("body", "")

        if "thumbtack.com" not in link:
            continue
        if is_list_page(title):
            continue

        name = clean_business_name(title)
        if not name or len(name) < 3 or len(name) > 80 or is_generic_name(name):
            continue

        leads.append({
            "name": name,
            "phone": extract_phone_from_text(snippet),
            "website": link,
            "address": "",
            "city": city,
            "source": "Thumbtack",
        })

    print(f"    Thumbtack: {len(leads)} resultados")
    return leads


def scrape_manta_search(niche: str, city: str) -> list:
    """Find Manta business listings via DuckDuckGo."""
    leads = []

    print(f"  Buscando en Manta: {niche} in {city}...")

    results = search_ddg(f"site:manta.com {niche} {city}", max_results=15)

    for r in results:
        title = r.get("title", "")
        link = r.get("href", "")
        snippet = r.get("body", "")

        if "manta.com" not in link:
            continue
        if is_list_page(title):
            continue

        name = clean_business_name(title)
        if not name or len(name) < 3 or len(name) > 80 or is_generic_name(name):
            continue

        leads.append({
            "name": name,
            "phone": extract_phone_from_text(snippet),
            "website": link,
            "address": extract_address_from_text(snippet),
            "city": city,
            "source": "Manta",
        })

    print(f"    Manta: {len(leads)} resultados")
    return leads


def scrape_nextdoor_search(niche: str, city: str) -> list:
    """Find Nextdoor recommendations/complaints via DuckDuckGo."""
    leads = []

    print(f"  Buscando en Nextdoor: {niche} in {city}...")

    results = search_ddg(f"site:nextdoor.com {niche} {city}", max_results=15)

    for r in results:
        title = r.get("title", "")
        link = r.get("href", "")
        snippet = r.get("body", "")

        if "nextdoor.com" not in link:
            continue
        if is_list_page(title):
            continue

        name = clean_business_name(title)
        if not name or len(name) < 3 or len(name) > 80 or is_generic_name(name):
            continue

        leads.append({
            "name": name,
            "phone": extract_phone_from_text(snippet),
            "website": link,
            "address": "",
            "city": city,
            "source": "Nextdoor",
        })

    print(f"    Nextdoor: {len(leads)} resultados")
    return leads


def scrape_craigslist_search(niche: str, city: str) -> list:
    """Find Craigslist service ads via DuckDuckGo."""
    leads = []

    print(f"  Buscando en Craigslist: {niche} in {city}...")

    results = search_ddg(f"site:craigslist.org {niche} {city}", max_results=15)

    for r in results:
        title = r.get("title", "")
        link = r.get("href", "")
        snippet = r.get("body", "")

        if "craigslist.org" not in link:
            continue
        # Skip Craigslist search/category listing pages
        if any(skip in link.lower() for skip in ["/search/", "/d/", "?query="]):
            continue
        if is_list_page(title):
            continue

        name = clean_business_name(title)
        if not name or len(name) < 3 or len(name) > 80 or is_generic_name(name):
            continue

        # Craigslist posts must mention the niche to be relevant
        combined = (title + " " + snippet).lower()
        niche_lower = niche.lower().strip()
        niche_kws = NICHE_KEYWORDS.get(niche_lower, [niche_lower.rstrip("s"), niche_lower])
        if not any(kw in combined for kw in niche_kws):
            continue

        leads.append({
            "name": name,
            "phone": extract_phone_from_text(snippet),
            "website": link,
            "address": "",
            "city": city,
            "source": "Craigslist",
        })

    print(f"    Craigslist: {len(leads)} resultados")
    return leads


def scrape_complaints_search(niche: str, city: str) -> list:
    """Search specifically for businesses with communication complaints."""
    leads = []

    print(f"  Buscando quejas de comunicacion: {niche} in {city}...")

    queries = [
        f'{niche} {city} "never answer" OR "don\'t answer" OR "no answer"',
        f'{niche} {city} "never call back" OR "didn\'t call back" OR "won\'t return calls"',
        f'{niche} {city} "can\'t reach" OR "hard to reach" OR "unreachable"',
        f'{niche} {city} "poor communication" OR "terrible communication" OR "no communication"',
        f'{niche} {city} "left voicemail" OR "went to voicemail" OR "straight to voicemail"',
    ]

    for query_text in queries:
        try:
            results = search_ddg(query_text, max_results=10)

            for r in results:
                title = r.get("title", "")
                link = r.get("href", "")
                snippet = r.get("body", "")

                # Skip non-business sites globally
                if should_skip_url(link):
                    continue

                # Skip generic articles/blogs that aren't about a specific business
                title_lower = title.lower()
                if any(skip in title_lower for skip in [
                    "how to", "what is", "why do", "tips for", "guide",
                    "troubleshoot", "fix your", "solved", "tutorial",
                    "scam", "spam", "virus", "malware",
                    "voicemail setup", "voicemail greeting", "voicemail not working",
                    "phone not working", "phone settings",
                ]):
                    continue

                # Must be somewhat relevant to the niche
                combined_text = (title + " " + snippet).lower()
                niche_lower = niche.lower().strip()
                niche_kws = NICHE_KEYWORDS.get(niche_lower, [niche_lower.rstrip("s"), niche_lower])
                if not any(kw in combined_text for kw in niche_kws):
                    continue

                name = clean_business_name(title)
                if not name or len(name) < 3 or is_generic_name(name):
                    continue

                phone = ""
                phone_match = re.search(r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', snippet)
                if phone_match:
                    phone = phone_match.group()

                leads.append({
                    "name": name,
                    "phone": phone,
                    "website": link,
                    "address": "",
                    "city": city,
                    "snippet": snippet,
                    "source": "Complaints Search",
                    "has_complaint": True,
                })

            random_delay(1, 2)

        except Exception:
            pass

    print(f"    Quejas encontradas: {len(leads)} resultados")
    return leads


# ==================== INVESTIGATION ====================

def extract_emails_from_website(url: str, client: httpx.Client, name: str = "", city: str = "") -> list:
    """Extract emails aggressively from website + multiple DuckDuckGo searches."""
    emails = set()
    skip_sites = [
        "yelp.com", "yellowpages.com", "bbb.org", "google.com",
        "facebook.com", "linkedin.com", "indeed.com", "angi.com",
        "thumbtack.com", "manta.com", "nextdoor.com", "craigslist.org",
    ]

    has_own_website = url and not any(d in url for d in skip_sites)

    # Method 1: Scrape website directly (home + contact + about + team + footer pages)
    if has_own_website:
        pages_to_check = [url]
        try:
            resp = client.get(url)
            soup = BeautifulSoup(resp.text, "lxml")

            # Find contact/about/team/footer pages
            for a in soup.select("a[href]"):
                href = a.get("href", "").lower()
                text = a.get_text(strip=True).lower()
                if any(kw in href or kw in text for kw in [
                    "contact", "about", "team", "staff", "footer",
                    "locations", "email", "reach", "connect", "support",
                ]):
                    full_url = urljoin(url, a["href"])
                    if full_url not in pages_to_check:
                        pages_to_check.append(full_url)

        except Exception:
            pass

        for page in pages_to_check[:5]:
            try:
                resp = client.get(page)
                text = resp.text

                # Regex for emails
                found = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
                for email in found:
                    if not is_junk_email(email):
                        emails.add(email.lower())

                # Mailto links
                soup = BeautifulSoup(text, "lxml")
                for a in soup.select("a[href^='mailto:']"):
                    email = a["href"].replace("mailto:", "").split("?")[0].strip()
                    if email and "@" in email and not is_junk_email(email):
                        emails.add(email.lower())

                random_delay(0.3, 0.8)

            except Exception:
                pass

        # Method 2 removed: no fake/guessed emails

    # Method 2: DuckDuckGo search for email (multiple queries - dig deep)
    if name:
        ddg_queries = [
            f'"{name}" {city} email',
            f'"{name}" {city} contact email @',
            f'"{name}" email address',
            f'"{name}" {city} gmail OR yahoo OR hotmail OR outlook',
        ]
        # If STILL no emails, try even harder with variations
        if not emails:
            ddg_queries.extend([
                f'"{name}" contact us email',
                f'"{name}" owner email',
                f'"{name}" Ohio email OR contact',
                f'{name} {city} "@" email',
            ])

        for q in ddg_queries:
            try:
                results = search_ddg(q, max_results=8)
                for r in results:
                    text = r.get("body", "") + " " + r.get("title", "")
                    found = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
                    for email in found:
                        if not is_junk_email(email):
                            emails.add(email.lower())
                random_delay(0.5, 1)
            except Exception:
                pass
            # Only stop early if we found a GOOD email (not after first 2 queries)
            if emails and ddg_queries.index(q) >= 3:
                break

    # Method 3: If still no email, try scraping directory pages (BBB, Manta, etc.)
    if not emails and name:
        directory_queries = [
            f'site:bbb.org "{name}"',
            f'site:manta.com "{name}"',
            f'site:chamberofcommerce.com "{name}"',
            f'site:mapquest.com "{name}" {city}',
        ]
        for q in directory_queries:
            try:
                results = search_ddg(q, max_results=3)
                for r in results:
                    page_url = r.get("href", "")
                    if not page_url:
                        continue
                    try:
                        resp = client.get(page_url)
                        found = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', resp.text)
                        for email in found:
                            if not is_junk_email(email):
                                emails.add(email.lower())
                    except Exception:
                        pass
                random_delay(0.5, 1)
            except Exception:
                pass
            if emails:
                break

    return list(emails)


def analyze_website_quality(url: str, client: httpx.Client) -> str:
    """Analyze website quality."""
    directory_sites = [
        "yelp.com", "yellowpages.com", "bbb.org", "google.com",
        "facebook.com", "linkedin.com", "indeed.com", "angi.com",
        "thumbtack.com", "manta.com", "nextdoor.com", "craigslist.org",
    ]
    if not url or any(d in url for d in directory_sites):
        return "Sin website propio"

    try:
        resp = client.get(url)
        soup = BeautifulSoup(resp.text, "lxml")
        html = resp.text.lower()

        issues = []

        # Check mobile responsive
        if not soup.select_one('meta[name="viewport"]'):
            issues.append("No responsive/mobile")

        # Check for chat
        has_chat = any(chat in html for chat in [
            "livechat", "tawk.to", "intercom", "drift", "zendesk",
            "crisp.chat", "tidio", "hubspot", "chat-widget", "chatbot"
        ])
        if not has_chat:
            issues.append("Sin chat")

        # Check for online booking/scheduling
        has_booking = any(book in html for book in [
            "book online", "schedule", "appointment", "booking",
            "calendly", "acuity", "setmore", "reservar", "agendar"
        ])
        if not has_booking:
            issues.append("Sin citas online")

        # Check for contact form
        forms = soup.select("form")
        has_contact_form = any(
            "contact" in (f.get("action", "") + f.get("id", "") + f.get("class", [""])[0] if isinstance(f.get("class"), list) else f.get("class", "")).lower()
            for f in forms
        ) if forms else False
        if not has_contact_form and not forms:
            issues.append("Sin formulario contacto")

        # Check SSL
        if url.startswith("http://"):
            issues.append("Sin SSL/HTTPS")

        if len(issues) >= 3:
            return f"BAJO - {', '.join(issues)}"
        elif len(issues) >= 1:
            return f"MEDIO - {', '.join(issues)}"
        else:
            return "BUENO"

    except Exception:
        return "No se pudo analizar"


def search_reviews_for_pain(name: str, city: str) -> dict:
    """Search for reviews/complaints across multiple platforms."""
    result = {
        "rating": "",
        "total_reviews": "",
        "client_complaints": [],
        "business_complaints": [],
        "platforms_found": [],
    }

    # 2 smart queries: reviews + complaints (fast, no redundancy)
    queries = [
        f'"{name}" {city} reviews rating',
        f'"{name}" {city} "no answer" OR "never call back" OR "voicemail" OR "poor communication"',
    ]

    for query_text in queries:
        try:
            search_results = search_ddg(query_text, max_results=8)

            for r in search_results:
                text = (r.get("body", "") + " " + r.get("title", "")).lower()
                link = r.get("href", "").lower()

                # Track which platforms this business appears on
                for platform in ["yelp.com", "google.com", "bbb.org", "facebook.com", "angi.com", "thumbtack.com"]:
                    if platform in link and platform not in result["platforms_found"]:
                        result["platforms_found"].append(platform)

                # Extract rating
                if not result["rating"]:
                    rating_match = re.search(r'(\d+\.?\d*)\s*(?:star|out of|/\s*5|★)', text)
                    if rating_match:
                        result["rating"] = rating_match.group(1)

                # Extract review count
                if not result["total_reviews"]:
                    review_match = re.search(r'(\d+[\d,]*)\s*reviews?', text)
                    if review_match:
                        result["total_reviews"] = review_match.group(1)

                for kw in PAIN_KEYWORDS_CLIENTS:
                    if kw.lower() in text:
                        complaint = text[:150]
                        if complaint not in result["client_complaints"]:
                            result["client_complaints"].append(complaint)
                        break

                for kw in PAIN_KEYWORDS_BUSINESS:
                    if kw.lower() in text:
                        complaint = text[:150]
                        if complaint not in result["business_complaints"]:
                            result["business_complaints"].append(complaint)
                        break

            random_delay(0.5, 1.5)

        except Exception:
            pass

    return result


def check_social_media(name: str, city: str) -> str:
    """Check social media presence across multiple platforms."""
    found = []
    missing = []

    try:
        results = search_ddg(f'"{name}" {city} facebook instagram linkedin google', max_results=10)
        all_text = " ".join([r.get("href", "") + " " + r.get("body", "") for r in results]).lower()

        checks = [
            ("facebook.com", "Facebook"),
            ("instagram.com", "Instagram"),
            ("linkedin.com", "LinkedIn"),
            ("twitter.com", "Twitter/X"),
            ("x.com", "Twitter/X"),
            ("tiktok.com", "TikTok"),
        ]

        for domain, name_platform in checks:
            if domain in all_text:
                if name_platform not in found:
                    found.append(name_platform)
            else:
                if name_platform not in missing and name_platform not in found:
                    missing.append(name_platform)

        random_delay(0.5, 1)

    except Exception:
        return "No se pudo verificar"

    parts = []
    if found:
        parts.append(f"Tiene: {', '.join(found)}")
    if missing:
        parts.append(f"Sin: {', '.join(missing)}")
    return " | ".join(parts) if parts else "No se encontraron redes"


def determine_ai_receptionist_need(reviews: dict, website_quality: str, social: str, hiring_role: str = "", has_complaint: bool = False) -> tuple:
    """Determine if business needs AI Receptionist. Returns (level, evidence)."""
    score = 0
    evidence = []

    # Hiring receptionist/customer service (STRONGEST signal - automatic ALTO)
    if hiring_role:
        score += 10
        evidence.append(f"CONTRATANDO: {hiring_role} (Indeed)")

    # Found via complaint search (very strong signal)
    if has_complaint:
        score += 6
        evidence.append("Encontrado en busqueda de quejas de comunicacion")

    # Low online presence (not found on review platforms = small, needs help)
    platforms = reviews.get("platforms_found", [])
    if len(platforms) == 0:
        score += 1
        evidence.append("Presencia online minima - no encontrado en plataformas de reviews")
    elif len(platforms) >= 3:
        evidence.append(f"Presente en: {', '.join(platforms)}")

    # Client complaints about communication (strongest signal)
    if reviews["client_complaints"]:
        score += 3 * len(reviews["client_complaints"])
        for complaint in reviews["client_complaints"][:3]:
            evidence.append(f"Cliente: \"{complaint[:80]}...\"")

    # Business complaints (very strong signal)
    if reviews["business_complaints"]:
        score += 5 * len(reviews["business_complaints"])
        for complaint in reviews["business_complaints"][:2]:
            evidence.append(f"Negocio: \"{complaint[:80]}...\"")

    # Low rating
    if reviews["rating"]:
        try:
            rating = float(reviews["rating"])
            if rating < 3.5:
                score += 3
                evidence.append(f"Rating bajo: {rating} estrellas")
            elif rating < 4.0:
                score += 1
                evidence.append(f"Rating: {rating} estrellas")
        except ValueError:
            pass

    # No website at all (strong signal - small business, no tech)
    if "Sin website propio" in website_quality:
        score += 2
        evidence.append("Sin website propio - negocio pequeno sin tecnologia")

    # Website issues
    if "Sin chat" in website_quality:
        score += 1
        evidence.append("Website sin chat")
    if "Sin citas online" in website_quality:
        score += 1
        evidence.append("Sin sistema de citas online")
    if "BAJO" in website_quality:
        score += 2

    # Determine level
    if score >= 5:
        level = "ALTO"
    elif score >= 2:
        level = "MEDIO"
    else:
        level = "BAJO"

    return level, " | ".join(evidence) if evidence else "Sin evidencia clara"


def suggest_other_services(website_quality: str, social: str) -> str:
    """Suggest other services based on investigation."""
    services = []

    if "Sin website" in website_quality or "BAJO" in website_quality:
        services.append("Website ($1,500-3,000)")
    if "Sin chat" in website_quality:
        services.append("Bot Web/Chat ($197-397/mes)")
    if "Sin citas online" in website_quality:
        services.append("Sistema Citas ($197-297/mes)")
    if "Sin formulario" in website_quality:
        services.append("Formulario Contacto")
    if "Sin Facebook" in social or "Sin Instagram" in social:
        services.append("Redes Sociales ($497-997/mes)")

    return ", ".join(services) if services else "Evaluar en llamada"


def generate_message(name: str, need_level: str, evidence: str, niche: str) -> str:
    """Generate personalized outreach message."""
    if need_level == "ALTO":
        if "no contestan" in evidence.lower() or "no answer" in evidence.lower():
            return f"Hola, vi que algunos clientes de {name} mencionan dificultad para contactarlos por telefono. Tenemos una solucion de AI que contesta llamadas 24/7, agenda citas y responde preguntas automaticamente. Le interesaria una demo gratuita?"
        elif "voicemail" in evidence.lower():
            return f"Hola, note que {name} podria estar perdiendo llamadas que van a buzon de voz. Nuestra AI receptionist contesta cada llamada, agenda citas y nunca pierde un cliente. Le gustaria ver como funciona?"
        else:
            return f"Hola, trabajo con {niche} en el area y ayudo a que no pierdan ninguna llamada de clientes con una AI receptionist. Contesta 24/7, agenda citas automaticamente. Le interesaria una demo?"
    elif need_level == "MEDIO":
        return f"Hola, trabajo con {niche} en el area ayudandoles a automatizar la atencion telefonica. Nuestra AI contesta llamadas, agenda citas y responde preguntas 24/7. Tienen algun sistema similar actualmente?"
    else:
        return f"Hola, ofrecemos soluciones de automatizacion para {niche}. Le interesaria conocer como podemos ayudarle?"


# ==================== GOOGLE SHEETS ====================

def connect_to_sheets():
    """Connect to Google Sheets."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(str(CREDENTIALS_FILE), scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)


def get_or_create_tab(spreadsheet, tab_name: str):
    """Get existing tab or create new one with headers."""
    try:
        worksheet = spreadsheet.worksheet(tab_name)
        return worksheet
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=len(SHEET_HEADERS))
        worksheet.update(values=[SHEET_HEADERS], range_name="A1")
        # Bold headers
        worksheet.format("A1:R1", {"textFormat": {"bold": True}})
        return worksheet


def write_leads_to_sheet(spreadsheet, tab_name: str, leads_data: list):
    """Write leads to a specific tab in the Sheet."""
    worksheet = get_or_create_tab(spreadsheet, tab_name)

    # Get existing names from ALL tabs to avoid duplicates across industries
    existing_names = set()
    for ws in spreadsheet.worksheets():
        try:
            rows = ws.get_all_values()
            for row in rows[1:]:
                if len(row) > 2 and row[2].strip():
                    existing_names.add(row[2].lower())
        except Exception:
            pass

    # Also get current tab rows to know where to append
    existing = worksheet.get_all_values()

    # Prepare new rows
    new_rows = []
    for lead in leads_data:
        if lead["name"].lower() not in existing_names:
            new_rows.append([
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                lead.get("source", ""),
                lead.get("name", ""),
                lead.get("phone", ""),
                lead.get("email", ""),
                lead.get("website", ""),
                lead.get("address", ""),
                lead.get("city", ""),
                lead.get("rating", ""),
                lead.get("total_reviews", ""),
                lead.get("need_level", ""),
                lead.get("evidence", ""),
                lead.get("client_complaints", ""),
                lead.get("business_complaints", ""),
                lead.get("website_quality", ""),
            ])

    if new_rows:
        # Append after last row
        next_row = len(existing) + 1
        worksheet.update(values=new_rows, range_name=f"A{next_row}")

        # Color code the NECESITA AI RECEPTIONIST column (Column K, index 10)
        for i, row in enumerate(new_rows):
            cell_row = next_row + i
            need_level = row[10]  # Column K
            if need_level == "ALTO":
                worksheet.format(f"K{cell_row}", {"backgroundColor": {"red": 0.8, "green": 0.2, "blue": 0.2}})
            elif need_level == "MEDIO":
                worksheet.format(f"K{cell_row}", {"backgroundColor": {"red": 1.0, "green": 0.8, "blue": 0.2}})
            else:
                worksheet.format(f"K{cell_row}", {"backgroundColor": {"red": 0.7, "green": 0.9, "blue": 0.7}})

    return len(new_rows)


# ==================== MAIN ====================

def find_leads(niche: str, city: str, limit: int = 0):
    """Main function: find leads, investigate, write to Sheet."""

    # Check if we have expanded area for this city
    city_key = city.lower().strip()
    search_cities = AREA_EXPANSIONS.get(city_key, [city])

    print(f"\n{'='*60}")
    print(f"  CC LEAD FINDER - by Claude Code")
    print(f"  Industria: {niche}")
    print(f"  Area: {city} ({len(search_cities)} zonas)")
    print(f"{'='*60}\n")

    # Step 1: Scrape multiple sources across all cities in area
    print(f"[1/4] BUSCANDO EMPRESAS EN {len(search_cities)} ZONAS...\n")

    client = get_client()
    all_leads = []

    for ci, search_city in enumerate(search_cities):
        print(f"  --- Zona {ci+1}/{len(search_cities)}: {search_city} ---")

        all_leads.extend(scrape_general_search(niche, search_city))
        random_delay(1, 3)

        all_leads.extend(scrape_yelp_search(niche, search_city))
        random_delay(1, 3)

        all_leads.extend(scrape_yellowpages_search(niche, search_city))
        random_delay(1, 3)

        all_leads.extend(scrape_bbb_search(niche, search_city))
        random_delay(1, 3)

        # LinkedIn e Indeed desactivados - son para otra sheet (contrataciones)
        # all_leads.extend(scrape_linkedin_search(niche, search_city))
        # random_delay(1, 3)
        # all_leads.extend(scrape_indeed_hiring(niche, search_city))
        # random_delay(1, 3)

        all_leads.extend(scrape_google_maps_search(niche, search_city))
        random_delay(1, 3)

        all_leads.extend(scrape_facebook_search(niche, search_city))
        random_delay(1, 3)

        all_leads.extend(scrape_angi_search(niche, search_city))
        random_delay(1, 3)

        all_leads.extend(scrape_thumbtack_search(niche, search_city))
        random_delay(1, 3)

        all_leads.extend(scrape_manta_search(niche, search_city))
        random_delay(1, 3)

        all_leads.extend(scrape_nextdoor_search(niche, search_city))
        random_delay(1, 3)

        all_leads.extend(scrape_craigslist_search(niche, search_city))
        random_delay(1, 3)

        all_leads.extend(scrape_complaints_search(niche, search_city))
        random_delay(2, 4)

    # Deduplicate by name + filter relevant to niche
    # Normalize names for dedup: lowercase, strip punctuation, strip city/state suffixes
    def normalize_for_dedup(name: str) -> str:
        n = name.lower().strip()
        # Remove punctuation (apostrophes, commas, periods, pipes, dashes)
        n = re.sub(r"['\",.|:;!?&\-–—]", "", n)
        # Remove common suffixes: LLC, Inc, Ltd, city names, state, phone numbers
        n = re.sub(r'\b(llc|inc|ltd|corp|co)\b', '', n)
        n = re.sub(r'\b(oh|ohio)\b', '', n)
        # Remove phone numbers
        n = re.sub(r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', '', n)
        # Remove extra whitespace
        n = re.sub(r'\s+', ' ', n).strip()
        return n

    seen = set()
    unique_leads = []
    skipped_irrelevant = 0
    for lead in all_leads:
        name_key = normalize_for_dedup(lead["name"])
        if name_key and name_key not in seen and len(name_key) > 3:
            # Check if business is actually relevant to the niche
            if not is_relevant_to_niche(lead["name"], lead.get("snippet", ""), niche):
                skipped_irrelevant += 1
                continue
            seen.add(name_key)
            unique_leads.append(lead)

    print(f"\n  Total empresas unicas encontradas: {len(unique_leads)}")
    if skipped_irrelevant:
        print(f"  Filtradas por no ser relevantes a '{niche}': {skipped_irrelevant}")

    # Apply limit if set
    if limit and limit > 0 and len(unique_leads) > limit:
        print(f"  MODO PRUEBA: limitando a {limit} negocios")
        unique_leads = unique_leads[:limit]

    print()

    if not unique_leads:
        print("  No se encontraron resultados. Intenta con otra busqueda.")
        return

    # Connect to Google Sheets early so we can write progressively
    spreadsheet = None
    tab_name = niche.title()
    try:
        spreadsheet = connect_to_sheets()
        print(f"  Conectado a Google Sheets - tab: {tab_name}\n")
    except Exception as e:
        print(f"  No se pudo conectar a Sheets: {e}")
        print(f"  Se guardara en CSV al final.\n")

    # Step 2: Investigate each lead and write to Sheet every 10
    print(f"[2/3] INVESTIGANDO {len(unique_leads)} EMPRESAS...\n")

    investigated_leads = []
    batch = []
    total_written = 0

    for i, lead in enumerate(unique_leads):
        name = lead["name"]
        print(f"  [{i+1}/{len(unique_leads)}] Investigando: {name}...")

        # Extract emails from website + DuckDuckGo search
        lead_city = lead.get("city", city)
        emails = extract_emails_from_website(lead.get("website", ""), client, name, lead_city)
        random_delay(0.5, 1)

        # Analyze website quality
        website_quality = analyze_website_quality(lead.get("website", ""), client)
        random_delay(0.5, 1)

        # Search reviews for communication pain
        reviews = search_reviews_for_pain(name, lead_city)
        random_delay(1, 2)

        # Determine AI Receptionist need (without social media)
        hiring_role = lead.get("hiring_role", "")
        has_complaint = lead.get("has_complaint", False)
        need_level, evidence = determine_ai_receptionist_need(reviews, website_quality, "", hiring_role, has_complaint)

        # Combine emails: from website scrape + from snippet
        snippet_email = lead.get("email_snippet", "")
        if snippet_email and snippet_email not in emails:
            emails.append(snippet_email)

        lead_data = {
            "name": name,
            "phone": lead.get("phone", ""),
            "email": ", ".join(emails) if emails else "",
            "website": lead.get("website", ""),
            "address": lead.get("address", ""),
            "city": city,
            "rating": reviews.get("rating", lead.get("rating", "")),
            "total_reviews": reviews.get("total_reviews", ""),
            "need_level": need_level,
            "evidence": evidence,
            "client_complaints": " | ".join(reviews["client_complaints"][:3]),
            "business_complaints": " | ".join(reviews["business_complaints"][:2]),
            "website_quality": website_quality,
            "source": lead.get("source", ""),
        }

        investigated_leads.append(lead_data)
        batch.append(lead_data)

        # Print quick status
        icon = "!!!" if need_level == "ALTO" else "!" if need_level == "MEDIO" else "-"
        platforms = reviews.get("platforms_found", [])
        platform_str = f" | Found on: {', '.join(platforms)}" if platforms else ""
        print(f"    AI Receptionist: {need_level} {icon}{platform_str}")

        # Write to Sheet every 10 businesses
        if len(batch) >= 10 and spreadsheet:
            try:
                written = write_leads_to_sheet(spreadsheet, tab_name, batch)
                total_written += written
                print(f"\n    >>> {written} leads written to Sheet (total: {total_written}) <<<\n")
                batch = []
            except Exception as e:
                print(f"\n    >>> Error writing to Sheet: {e} <<<\n")

    # Write remaining batch
    if batch and spreadsheet:
        try:
            written = write_leads_to_sheet(spreadsheet, tab_name, batch)
            total_written += written
            print(f"\n    >>> {written} final leads written to Sheet (total: {total_written}) <<<\n")
        except Exception as e:
            print(f"\n    >>> Error writing final batch: {e} <<<\n")

    # Step 3: Summary
    print(f"\n[3/3] RESUMEN\n")

    alto = sum(1 for l in investigated_leads if l["need_level"] == "ALTO")
    medio = sum(1 for l in investigated_leads if l["need_level"] == "MEDIO")
    bajo = sum(1 for l in investigated_leads if l["need_level"] == "BAJO")

    print(f"  ALTO (contact now):     {alto}")
    print(f"  MEDIO (worth it):       {medio}")
    print(f"  BAJO (skip or sell other): {bajo}")

    if spreadsheet:
        print(f"\n  Total written to Sheet: {total_written}")
        print(f"  Tab: {tab_name}")
        print(f"\n  Open your Sheet to see results!")
    else:
        # Fallback to CSV
        print(f"\n  Saving to CSV...")

        import csv
        csv_file = f"leads_{niche}_{city}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SHEET_HEADERS)
            writer.writeheader()
            for lead in investigated_leads:
                writer.writerow({
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Source": lead["source"],
                    "Business": lead["name"],
                    "Phone": lead["phone"],
                    "Email": lead["email"],
                    "Website": lead["website"],
                    "Address": lead["address"],
                    "City": lead["city"],
                    "Google Rating": lead["rating"],
                    "Total Reviews": lead["total_reviews"],
                    "NEEDS AI RECEPTIONIST?": lead["need_level"],
                    "AI Receptionist Evidence": lead["evidence"],
                    "Communication Complaints (Clients)": lead["client_complaints"],
                    "Business Complaints": lead["business_complaints"],
                    "Website Quality": lead["website_quality"],
                })
        print(f"  Saved to: {csv_file}")

    # Final summary
    print(f"\n{'='*60}")
    print(f"  DONE")
    print(f"  Total leads: {len(investigated_leads)}")
    print(f"  ALTO: {alto}")
    print(f"  MEDIO: {medio}")
    print(f"  BAJO: {bajo}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CC Lead Finder - by Claude Code")
    parser.add_argument("niche", help="Industria a buscar (ej: plomeros, hvac, dentistas)")
    parser.add_argument("city", help="Ciudad (ej: Miami, Houston, 'Los Angeles')")
    parser.add_argument("--limit", type=int, default=0, help="Limite de negocios a investigar (0=sin limite)")

    args = parser.parse_args()
    find_leads(args.niche, args.city, limit=args.limit)
