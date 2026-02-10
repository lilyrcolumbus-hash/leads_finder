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
        "Elida Ohio",
        "Delphos Ohio",
        "Spencerville Ohio",
        "Bluffton Ohio",
        "Cairo Ohio",
        "Harrod Ohio",
        "Lafayette Ohio",
        "Beaverdam Ohio",
        "Wapakoneta Ohio",
        "Findlay Ohio",
        "Sidney Ohio",
        "Van Wert Ohio",
        "Kenton Ohio",
        "Celina Ohio",
        "St Marys Ohio",
    ],
}

# Column headers for the Sheet
SHEET_HEADERS = [
    "Fecha",
    "Fuente",
    "Empresa",
    "Telefono",
    "Email",
    "Website",
    "Direccion",
    "Ciudad",
    "Rating Google",
    "Total Resenas",
    "NECESITA AI RECEPTIONIST?",
    "Evidencia AI Receptionist",
    "Quejas Comunicacion (Clientes)",
    "Quejas del Negocio",
    "Website Calidad",
    "Redes Sociales",
    "Otros Servicios Posibles",
    "Mensaje Sugerido",
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

            # Skip aggregators
            if any(skip in link for skip in ["youtube.com", "wikipedia.org", "facebook.com", "mapquest.com", "nextdoor.com"]):
                continue

            phone = ""
            phone_match = re.search(r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', snippet)
            if phone_match:
                phone = phone_match.group()

            # Extract address hints
            address = ""
            addr_match = re.search(r'\d+\s+[\w\s]+(?:St|Ave|Rd|Dr|Blvd|Ln|Way|Ct|Pkwy|Hwy)[\w\s,]*', snippet)
            if addr_match:
                address = addr_match.group().strip()

            leads.append({
                "name": title,
                "phone": phone,
                "website": link,
                "address": address,
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

        # Clean name
        name = re.sub(r'\s*[-–]\s*(Yelp|Reviews|Updated).*$', '', title).strip()
        name = re.sub(r'^\d+\.\s*', '', name).strip()

        if not name or len(name) < 3:
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

        # Clean name
        name = re.sub(r'\s*[-–|]\s*(Yellow Pages|YP|Reviews).*$', '', title, flags=re.IGNORECASE).strip()
        name = re.sub(r'^\d+\.\s*', '', name).strip()

        if not name or len(name) < 3:
            continue

        phone = ""
        phone_match = re.search(r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', snippet)
        if phone_match:
            phone = phone_match.group()

        address = ""
        addr_match = re.search(r'\d+\s+[\w\s]+(?:St|Ave|Rd|Dr|Blvd|Ln|Way|Ct)[\w\s,]*', snippet)
        if addr_match:
            address = addr_match.group().strip()

        leads.append({
            "name": name,
            "phone": phone,
            "website": link,
            "address": address,
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

        # Clean name
        name = re.sub(r'\s*[-–|]\s*(BBB|Better Business|Reviews|Accredited|Bureau).*$', '', title, flags=re.IGNORECASE).strip()
        name = re.sub(r'^\d+\.\s*', '', name).strip()

        if not name or len(name) < 3:
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

        # Clean name
        name = re.sub(r'\s*[-–|]\s*(LinkedIn|Company|Overview|Profile).*$', '', title, flags=re.IGNORECASE).strip()
        name = re.sub(r'^\d+\.\s*', '', name).strip()

        if not name or len(name) < 3:
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

            # Try to extract company name from Indeed title format: "Job Title - Company Name"
            name = ""
            if " - " in title:
                parts = title.split(" - ")
                if len(parts) >= 2:
                    # Company is usually the second part
                    name = re.sub(r'\s*[-–|]\s*(Indeed|Job|Review).*$', '', parts[1], flags=re.IGNORECASE).strip()

            if not name or len(name) < 3:
                # Try from snippet
                name = re.sub(r'\s*[-–|]\s*(Indeed|Job|Review).*$', '', title, flags=re.IGNORECASE).strip()

            if not name or len(name) < 3:
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

        # Clean name
        name = re.sub(r'\s*[-–·]\s*(Google Maps|Maps|Reviews).*$', '', title, flags=re.IGNORECASE).strip()
        name = re.sub(r'^\d+\.\s*', '', name).strip()

        if not name or len(name) < 3:
            continue

        phone = ""
        phone_match = re.search(r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', snippet)
        if phone_match:
            phone = phone_match.group()

        # Extract rating from snippet
        rating = ""
        rating_match = re.search(r'(\d+\.?\d*)\s*(?:stars?|estrellas?|rating)', snippet, re.IGNORECASE)
        if rating_match:
            rating = rating_match.group(1)

        address = ""
        addr_match = re.search(r'\d+\s+[\w\s]+(?:St|Ave|Rd|Dr|Blvd|Ln|Way|Ct|Pkwy|Hwy)[\w\s,]*', snippet)
        if addr_match:
            address = addr_match.group().strip()

        leads.append({
            "name": name,
            "phone": phone,
            "website": link,
            "address": address,
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

        # Clean name
        name = re.sub(r'\s*[-–|]\s*(Facebook|Posts|Reviews|Photos|Videos).*$', '', title, flags=re.IGNORECASE).strip()
        name = re.sub(r'^\d+\.\s*', '', name).strip()

        if not name or len(name) < 3:
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

        # Clean name
        name = re.sub(r'\s*[-–|]\s*(Angi|Angie|Reviews|Ratings|Cost).*$', '', title, flags=re.IGNORECASE).strip()
        name = re.sub(r'^\d+\.\s*', '', name).strip()

        if not name or len(name) < 3:
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

        # Clean name
        name = re.sub(r'\s*[-–|]\s*(Thumbtack|Reviews|Cost|Prices).*$', '', title, flags=re.IGNORECASE).strip()
        name = re.sub(r'^\d+\.\s*', '', name).strip()

        if not name or len(name) < 3:
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

        # Clean name
        name = re.sub(r'\s*[-–|]\s*(Manta|Company Profile|Reviews).*$', '', title, flags=re.IGNORECASE).strip()
        name = re.sub(r'^\d+\.\s*', '', name).strip()

        if not name or len(name) < 3:
            continue

        phone = ""
        phone_match = re.search(r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', snippet)
        if phone_match:
            phone = phone_match.group()

        address = ""
        addr_match = re.search(r'\d+\s+[\w\s]+(?:St|Ave|Rd|Dr|Blvd|Ln|Way|Ct)[\w\s,]*', snippet)
        if addr_match:
            address = addr_match.group().strip()

        leads.append({
            "name": name,
            "phone": phone,
            "website": link,
            "address": address,
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

        # Clean name - Nextdoor titles are often recommendations
        name = re.sub(r'\s*[-–|]\s*(Nextdoor|Neighborhood|Recommend).*$', '', title, flags=re.IGNORECASE).strip()
        name = re.sub(r'^\d+\.\s*', '', name).strip()

        if not name or len(name) < 3:
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

        name = re.sub(r'\s*[-–|]\s*(Craigslist|CL).*$', '', title, flags=re.IGNORECASE).strip()
        name = re.sub(r'^\d+\.\s*', '', name).strip()
        # Remove price patterns
        name = re.sub(r'\$[\d,.]+', '', name).strip()

        if not name or len(name) < 3:
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

                # Skip non-business pages
                if any(skip in link for skip in ["youtube.com", "wikipedia.org", "reddit.com/r/"]):
                    continue

                phone = ""
                phone_match = re.search(r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', snippet)
                if phone_match:
                    phone = phone_match.group()

                leads.append({
                    "name": title,
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
    """Extract emails from website + DuckDuckGo search as fallback."""
    emails = set()
    skip_sites = [
        "yelp.com", "yellowpages.com", "bbb.org", "google.com",
        "facebook.com", "linkedin.com", "indeed.com", "angi.com",
        "thumbtack.com", "manta.com", "nextdoor.com", "craigslist.org",
    ]

    has_own_website = url and not any(d in url for d in skip_sites)

    # Method 1: Scrape website directly (home + contact + about pages)
    if has_own_website:
        pages_to_check = [url]
        try:
            resp = client.get(url)
            soup = BeautifulSoup(resp.text, "lxml")

            # Find contact/about/team pages
            for a in soup.select("a[href]"):
                href = a.get("href", "").lower()
                text = a.get_text(strip=True).lower()
                if any(kw in href or kw in text for kw in ["contact", "about", "contacto", "team", "staff"]):
                    full_url = urljoin(url, a["href"])
                    if full_url not in pages_to_check:
                        pages_to_check.append(full_url)

        except Exception:
            pass

        for page in pages_to_check[:4]:
            try:
                resp = client.get(page)
                text = resp.text

                # Regex for emails
                found = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
                for email in found:
                    domain = email.split("@")[1].lower()
                    if domain not in JUNK_DOMAINS and not email.endswith(".png") and not email.endswith(".jpg"):
                        emails.add(email.lower())

                # Mailto links
                soup = BeautifulSoup(text, "lxml")
                for a in soup.select("a[href^='mailto:']"):
                    email = a["href"].replace("mailto:", "").split("?")[0].strip()
                    if email and "@" in email:
                        domain = email.split("@")[1].lower()
                        if domain not in JUNK_DOMAINS:
                            emails.add(email.lower())

                random_delay(0.3, 0.8)

            except Exception:
                pass

    # Method 2: DuckDuckGo search for email (always, as fallback or complement)
    if name:
        try:
            results = search_ddg(f'"{name}" {city} email contact @', max_results=8)
            for r in results:
                text = r.get("body", "") + " " + r.get("title", "")
                found = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
                for email in found:
                    domain = email.split("@")[1].lower()
                    if domain not in JUNK_DOMAINS and not email.endswith(".png") and not email.endswith(".jpg"):
                        emails.add(email.lower())
            random_delay(0.5, 1)
        except Exception:
            pass

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
        worksheet.update("A1", [SHEET_HEADERS])
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
                lead.get("social_media", ""),
                lead.get("other_services", ""),
                lead.get("message", ""),
            ])

    if new_rows:
        # Append after last row
        next_row = len(existing) + 1
        worksheet.update(f"A{next_row}", new_rows)

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

def find_leads(niche: str, city: str):
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

        all_leads.extend(scrape_linkedin_search(niche, search_city))
        random_delay(1, 3)

        all_leads.extend(scrape_indeed_hiring(niche, search_city))
        random_delay(1, 3)

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

    # Deduplicate by name
    seen = set()
    unique_leads = []
    for lead in all_leads:
        name_key = lead["name"].lower().strip()
        if name_key and name_key not in seen and len(name_key) > 3:
            seen.add(name_key)
            unique_leads.append(lead)

    print(f"\n  Total empresas unicas encontradas: {len(unique_leads)}\n")

    if not unique_leads:
        print("  No se encontraron resultados. Intenta con otra busqueda.")
        return

    # Step 2: Investigate each lead
    print(f"[2/4] INVESTIGANDO {len(unique_leads)} EMPRESAS...\n")

    investigated_leads = []
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
        lead_city = lead.get("city", city)
        reviews = search_reviews_for_pain(name, lead_city)
        random_delay(1, 2)

        # Check social media
        social = check_social_media(name, lead_city)
        random_delay(0.5, 1)

        # Determine AI Receptionist need
        hiring_role = lead.get("hiring_role", "")
        has_complaint = lead.get("has_complaint", False)
        need_level, evidence = determine_ai_receptionist_need(reviews, website_quality, social, hiring_role, has_complaint)

        # Suggest other services
        other_services = suggest_other_services(website_quality, social)

        # Generate personalized message
        message = generate_message(name, need_level, evidence, niche)

        investigated_leads.append({
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
            "social_media": social,
            "other_services": other_services,
            "message": message,
            "source": lead.get("source", ""),
        })

        # Print quick status
        icon = "!!!" if need_level == "ALTO" else "!" if need_level == "MEDIO" else "-"
        platforms = reviews.get("platforms_found", [])
        platform_str = f" | Encontrado en: {', '.join(platforms)}" if platforms else ""
        print(f"    AI Receptionist: {need_level} {icon}{platform_str}")

    # Step 3: Sort by priority
    print(f"\n[3/4] ORGANIZANDO RESULTADOS...\n")

    priority_order = {"ALTO": 0, "MEDIO": 1, "BAJO": 2}
    investigated_leads.sort(key=lambda x: priority_order.get(x["need_level"], 3))

    alto = sum(1 for l in investigated_leads if l["need_level"] == "ALTO")
    medio = sum(1 for l in investigated_leads if l["need_level"] == "MEDIO")
    bajo = sum(1 for l in investigated_leads if l["need_level"] == "BAJO")

    print(f"  ALTO (contactar ya):    {alto}")
    print(f"  MEDIO (vale la pena):   {medio}")
    print(f"  BAJO (skip o vende otro): {bajo}")

    # Step 4: Write to Google Sheets
    print(f"\n[4/4] ESCRIBIENDO EN GOOGLE SHEETS...\n")

    try:
        spreadsheet = connect_to_sheets()
        tab_name = niche.title()
        written = write_leads_to_sheet(spreadsheet, tab_name, investigated_leads)
        print(f"  {written} leads nuevos escritos en tab '{tab_name}'")
        print(f"\n  Abre tu Sheet para ver los resultados!")
    except Exception as e:
        print(f"  Error escribiendo en Sheet: {e}")
        print(f"  Guardando en CSV como respaldo...")

        # Fallback to CSV
        import csv
        csv_file = f"leads_{niche}_{city}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SHEET_HEADERS)
            writer.writeheader()
            for lead in investigated_leads:
                writer.writerow({
                    "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Fuente": lead["source"],
                    "Empresa": lead["name"],
                    "Telefono": lead["phone"],
                    "Email": lead["email"],
                    "Website": lead["website"],
                    "Direccion": lead["address"],
                    "Ciudad": lead["city"],
                    "Rating Google": lead["rating"],
                    "Total Resenas": lead["total_reviews"],
                    "NECESITA AI RECEPTIONIST?": lead["need_level"],
                    "Evidencia AI Receptionist": lead["evidence"],
                    "Quejas Comunicacion (Clientes)": lead["client_complaints"],
                    "Quejas del Negocio": lead["business_complaints"],
                    "Website Calidad": lead["website_quality"],
                    "Redes Sociales": lead["social_media"],
                    "Otros Servicios Posibles": lead["other_services"],
                    "Mensaje Sugerido": lead["message"],
                })
        print(f"  Guardado en: {csv_file}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  RESUMEN")
    print(f"  Total leads: {len(investigated_leads)}")
    print(f"  ALTO prioridad: {alto}")
    print(f"  MEDIO prioridad: {medio}")
    print(f"  BAJO prioridad: {bajo}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CC Lead Finder - by Claude Code")
    parser.add_argument("niche", help="Industria a buscar (ej: plomeros, hvac, dentistas)")
    parser.add_argument("city", help="Ciudad (ej: Miami, Houston, 'Los Angeles')")

    args = parser.parse_args()
    find_leads(args.niche, args.city)
