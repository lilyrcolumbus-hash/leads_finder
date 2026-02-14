# CC Lead Finder Contacts

## What is this project?
Herramienta que busca negocios locales (plumbers, HVAC, dentists, lawyers, etc.) en 12 plataformas, los investiga, y escribe los resultados en Google Sheets para outreach de ventas.

**REGLA PRINCIPAL: Solo se escriben en la Sheet negocios que tengan email REAL verificado. Sin email = no se incluye.**

## Owner
- Communicates in Spanish but ALL code comments and output can be in Spanish
- Business brand: **NEXUS Voice** (AI Receptionist service built with Vapi)
- Services offered: AI Receptionist (priority #1), websites, web chatbots, appointment systems, social media, invoicing automation
- Target market: Local businesses in the US

## Key Files

### cc_lead_finder.py (Main tool)
- Usage: `python cc_lead_finder.py "plumbers" "Lima Ohio"`
- Uses `ddgs` package (DuckDuckGo search) - the ONLY search method that works from GitHub Codespace
- Searches 12 sources: Web Search, Yelp, Yellow Pages, BBB, Google Maps, Manta, Facebook, Angi, Thumbtack, Nextdoor, Craigslist, Complaints (all via DuckDuckGo)
- Investigates each business: website quality, reviews/complaints, email extraction
- **Solo incluye negocios con email real** - sin email = se salta
- **Deduplica por email** - si el mismo email ya se encontro, no se repite
- **Filtra emails basura**: BBB chapters (toledobbb.org, cualquier dominio con "bbb"), emails genericos, gobierno, etc.
- Scores AI Receptionist need: ALTO/MEDIO/BAJO with evidence
- Writes to Google Sheets with color coding (red=ALTO, yellow=MEDIO, green=BAJO)
- Creates industry-specific tabs (Plumbers, Hvac, Dentists, etc.)
- Falls back to CSV if Google Sheets connection fails

## Google Sheets Integration
- Sheet ID: `1P0A_7ptV2791YwQHH9wHAm0C41oPMmW7K1rn7afqHPY`
- Sheet name: "CC Leads"
- Service account: `leads-writer@cc-leadsfinder.iam.gserviceaccount.com`
- Credentials file: `credentials/google_sheets.json` (gitignored)
- Required APIs enabled: Google Sheets API + Google Drive API

## Filtros de Email (CRITICO)
El sistema filtra agresivamente emails falsos/genericos para que solo queden emails reales de negocios:

### Dominios bloqueados (JUNK_DOMAINS)
- Redes sociales: gmail, yahoo, hotmail, facebook, instagram, linkedin, etc.
- Directorios: yelp, bbb.org, yellowpages, mapquest, homeadvisor, etc.
- BBB locales: toledobbb.org, richmondbbb.org, bbbsoutheast.org, etc.
- Servicios tech: cloudflare, googleapis, amazonaws, mailchimp, hubspot, etc.

### Patrones bloqueados (JUNK_EMAIL_PATTERNS)
- `@.*bbb` - cualquier dominio que contenga "bbb"
- `@.*betterbus` - Better Business Bureau variantes
- Gobierno (.gov, .edu, .mil)
- noreply@, admin@, support@, webmaster@, etc.

### Logica de filtrado en la investigacion
1. Busca email en website del negocio (mailto links, texto visible, atributos HTML)
2. Busca email via DuckDuckGo (multiples queries)
3. Busca en directorios (BBB, Manta, Chamber of Commerce)
4. **Si no encuentra email real despues de todo -> SALTA el negocio**
5. **Si el email ya se vio en otro negocio -> SALTA (duplicado)**

## Tech Details
- Search library: `ddgs` (formerly `duckduckgo-search`, was renamed)
- Import with fallback: `from ddgs import DDGS` with fallback to `from duckduckgo_search import DDGS`
- Direct scraping of Google/Yelp/YP/BBB does NOT work (bot detection/Cloudflare) - always use DuckDuckGo library
- HTTP client: httpx with randomized User-Agent headers
- Dependencies: `gspread google-auth httpx beautifulsoup4 lxml ddgs`

## Important Rules
- credentials/ directory is gitignored - never commit credentials
- Script runs from GitHub Codespace (not from Claude Code sandbox due to SSL issues)
- **Solo negocios con email REAL van a la Sheet** - esta es la regla #1

## Search Progress
Industries searched so far (update as new searches are run):
- Plumbers in Lima Ohio

## Known Issues
- SSL certificate errors when running from Claude Code sandbox - must run from Codespace
- DuckDuckGo may rate-limit after many consecutive searches - delays are built into the script
- Nextdoor/Craigslist/Facebook rara vez traen emails reales, pero se mantienen activos por si encuentran negocios cuyos emails se extraen de su website propio
