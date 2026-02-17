#!/usr/bin/env python3
"""
Lead Generation App - Main Entry Point

A modular lead generation tool that:
1. Scrapes multiple sources for potential leads
2. Filters them using AI
3. Manages them in HubSpot CRM

Usage:
    python main.py              # Interactive menu
    python main.py --scrape     # Run scraping only
    python main.py --stats      # Show statistics
"""

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings
from src.utils.logger import setup_logger
from src.utils.models import Lead, LeadBatch, LeadSource
from src.scrapers import (
    RedditScraper, HackerNewsScraper, GoogleScraper, ProductHuntScraper, GoogleMapsScraper,
    IndeedScraper, YelpScraper, LinkedInScraper, FacebookScraper,
    YellowPagesScraper, BBBScraper, CraigslistScraper, GoogleMapsWebScraper
)
from src.filters import AILeadFilter
from src.crm import HubSpotCRM, LeadStage
from src.database import LeadDatabase
from src.enrichment import HunterClient
from src.sheets import GoogleSheetsSync

# Initialize
console = Console()
logger = setup_logger("main")
db = LeadDatabase()  # SQLite database for local persistence


def display_banner():
    """Display application banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║           LEAD GENERATION APP v1.0                        ║
    ║     Find business owners with communication pain points   ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(Panel(banner, style="bold blue"))


def display_main_menu() -> str:
    """Display main menu and get user choice."""
    console.print("\n[bold cyan]═══ MENU PRINCIPAL ═══[/bold cyan]\n")
    console.print("  [1] Buscar nuevos leads")
    console.print("  [2] Ver leads locales (SQLite)")
    console.print("  [3] Ver leads en HubSpot")
    console.print("  [4] Actualizar lead")
    console.print("  [5] Ver estadisticas")
    console.print("  [6] Buscar lead")
    console.print("  [7] Configuracion")
    console.print("  [8] [bold green]Contactos por industria/ciudad → Google Sheets[/bold green]")
    console.print("  [0] Salir")
    console.print()

    return Prompt.ask("Selecciona una opcion", choices=["0", "1", "2", "3", "4", "5", "6", "7", "8"], default="1")


# ==================== 1. SCRAPING ====================

def _run_single_scraper(name: str, ScraperClass) -> Tuple[str, LeadBatch, Optional[str]]:
    """Run a single scraper and return results. Used for concurrent execution."""
    try:
        with ScraperClass() as scraper:
            batch = scraper.scrape()
            return (name, batch, None)
    except Exception as e:
        source = getattr(ScraperClass, 'source', LeadSource.GOOGLE_SEARCH)
        empty_batch = LeadBatch(source=source)
        return (name, empty_batch, str(e))


def run_scraping() -> List[Lead]:
    """Run all scrapers concurrently and collect leads."""
    all_leads: List[Lead] = []
    errors: List[str] = []

    console.print("\n[bold green]Iniciando busqueda de leads (modo paralelo)...[/bold green]\n")

    scrapers = [
        ("Reddit", RedditScraper),
        ("Hacker News", HackerNewsScraper),
        ("Google Search", GoogleScraper),
        ("Product Hunt", ProductHuntScraper),
        ("Google Maps", GoogleMapsScraper),
        ("Indeed", IndeedScraper),
        ("Yelp", YelpScraper),
        ("LinkedIn", LinkedInScraper),
        ("Facebook", FacebookScraper),
        ("Yellow Pages", YellowPagesScraper),
        ("BBB", BBBScraper),
        ("Craigslist", CraigslistScraper),
    ]

    # Record scrape run
    source_names = [name for name, _ in scrapers]
    run_id = db.start_scrape_run(source_names)

    # Track timing
    start_time = time.time()

    # Show initial status
    console.print(f"[cyan]Ejecutando {len(scrapers)} scrapers en paralelo...[/cyan]")
    for name, _ in scrapers:
        console.print(f"  [dim]- {name}[/dim]")
    console.print()

    # Run all scrapers concurrently
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all scraping tasks
        futures = {
            executor.submit(_run_single_scraper, name, ScraperClass): name
            for name, ScraperClass in scrapers
        }

        # Collect results as they complete
        completed = 0
        for future in as_completed(futures):
            name, batch, error = future.result()
            completed += 1

            if error:
                console.print(f"  [red][{completed}/{len(scrapers)}] {name}: Error - {error}[/red]")
                errors.append(f"{name}: {error}")
            else:
                all_leads.extend(batch.leads)
                errors.extend(batch.errors)
                console.print(f"  [green][{completed}/{len(scrapers)}] {name}: {len(batch.leads)} leads encontrados[/green]")

    # Calculate time taken
    elapsed = time.time() - start_time
    console.print(f"\n[cyan]Tiempo total: {elapsed:.1f} segundos[/cyan]")

    # Auto email enrichment pipeline (crawl websites + Hunter.io + verify)
    if all_leads:
        all_leads = run_email_enrichment(all_leads)

    # Save leads to local database
    if all_leads:
        console.print("\n[cyan]Guardando leads en base de datos local...[/cyan]")
        result = db.save_leads(all_leads)
        console.print(f"[green]Guardados: {result['saved']} nuevos, {result['duplicates']} duplicados omitidos[/green]")

        # Auto-sync to Google Sheets (every 10 leads)
        sync_to_google_sheets(all_leads)

    # Show summary
    console.print(f"\n[bold]Total leads encontrados: {len(all_leads)}[/bold]")

    if errors:
        console.print(f"[yellow]Errores encontrados: {len(errors)}[/yellow]")
        for err in errors[:5]:
            logger.warning(err)

    return all_leads


def filter_leads_with_ai(leads: List[Lead]) -> List[Lead]:
    """Filter leads using AI."""
    if not leads:
        return []

    console.print("\n[bold cyan]Filtrando leads con AI...[/bold cyan]")

    ai_filter = AILeadFilter()
    filtered = ai_filter.filter_leads(leads)

    # Update leads in database with AI scores
    for lead in filtered:
        db.update_lead(
            lead.id,
            ai_score=lead.ai_score,
            ai_reasoning=lead.ai_reasoning,
            is_qualified=lead.is_qualified
        )

    qualified = [l for l in filtered if l.is_qualified]
    console.print(f"[green]Leads calificados: {len(qualified)}/{len(leads)}[/green]")

    return qualified


def send_to_hubspot(leads: List[Lead]) -> None:
    """Send qualified leads to HubSpot."""
    if not leads:
        console.print("[yellow]No hay leads para enviar[/yellow]")
        return

    if not Confirm.ask(f"\nEnviar {len(leads)} leads a HubSpot?"):
        return

    with HubSpotCRM() as crm:
        if not crm.is_configured():
            console.print("[red]HubSpot no esta configurado. Agrega HUBSPOT_API_KEY en .env[/red]")
            return

        results = crm.send_leads_to_crm(leads)

        console.print(f"\n[green]Creados: {results['created']}[/green]")
        console.print(f"[yellow]Ya existentes: {results['existing']}[/yellow]")
        console.print(f"[red]Fallidos: {results['failed']}[/red]")


def sync_to_google_sheets(leads: List[Lead]) -> None:
    """Send leads to Google Sheets via Apps Script webhook (only leads with real emails)."""
    sheets = GoogleSheetsSync()
    if not sheets.is_configured():
        return

    # Count leads with real emails upfront
    with_email = sum(1 for l in leads if l.email and not l.email.endswith("@leadgen.placeholder"))
    without_email = len(leads) - with_email

    console.print(f"\n[cyan]Sincronizando leads a Google Sheets (solo con email real)...[/cyan]")
    if without_email:
        console.print(f"[yellow]  Omitiendo {without_email} leads sin email real[/yellow]")

    try:
        with sheets:
            sheets.add_leads(leads)
            # flush() is called automatically on __exit__

        stats = sheets.get_stats()
        console.print(f"[green]Google Sheets: {stats['total_sent']} enviados con email real[/green]")

    except Exception as e:
        console.print(f"[red]Error sincronizando Google Sheets: {e}[/red]")
        logger.error(f"Google Sheets sync error: {e}")


# ==================== AUTO ENRICHMENT ====================

def auto_enrich_emails(leads: List[Lead]) -> List[Lead]:
    """Automatically enrich leads with emails by crawling business websites.

    For every lead that has a ``website`` but no ``email``, crawls the website
    (homepage + common contact pages) to extract a real business email.

    Args:
        leads: Leads to enrich.

    Returns:
        Same list with emails populated where found.
    """
    needs_email = [l for l in leads if l.website and not l.email]
    if not needs_email:
        return leads

    console.print(f"\n[bold cyan]Buscando emails en websites de negocios ({len(needs_email)} sitios)...[/bold cyan]")

    from src.scrapers.base_scraper import BaseScraper

    # Create a lightweight helper that inherits all email-extraction logic
    class _EmailCrawler(BaseScraper):
        source = LeadSource.GOOGLE_SEARCH  # unused, just satisfies ABC
        def scrape(self):
            pass  # not used

    crawler = _EmailCrawler()
    enriched = 0

    try:
        for i, lead in enumerate(needs_email, 1):
            try:
                email = crawler.extract_email_from_website(lead.website)
                if email:
                    lead.email = email
                    enriched += 1
                    console.print(
                        f"  [{i}/{len(needs_email)}] [green]{(lead.company or lead.title or '')[:35]}[/green] "
                        f"-> {email}"
                    )
                else:
                    console.print(
                        f"  [{i}/{len(needs_email)}] [dim]{(lead.company or lead.title or '')[:35]}[/dim] "
                        f"-> no encontrado"
                    )
            except Exception:
                console.print(
                    f"  [{i}/{len(needs_email)}] [dim]{(lead.company or lead.title or '')[:35]}[/dim] "
                    f"-> error"
                )
            time.sleep(0.3)
    finally:
        crawler.close()

    console.print(f"[green]Emails encontrados via website: {enriched}/{len(needs_email)}[/green]")
    return leads


def auto_enrich_with_hunter(leads: List[Lead]) -> List[Lead]:
    """Use Hunter.io to find emails for leads still missing them.

    Only runs if HUNTER_API_KEY is configured.  For each lead without an email,
    calls Hunter.io's domain search / email finder.

    Args:
        leads: Leads to enrich.

    Returns:
        Same list with emails populated where Hunter found them.
    """
    if not settings.hunter_api_key:
        return leads

    needs_email = [
        l for l in leads
        if not l.email or l.email.endswith("@leadgen.placeholder")
    ]
    if not needs_email:
        return leads

    console.print(
        f"\n[bold cyan]Buscando emails con Hunter.io ({len(needs_email)} leads)...[/bold cyan]"
    )

    enriched = 0
    with HunterClient() as hunter:
        if not hunter.is_configured():
            return leads

        for i, lead in enumerate(needs_email, 1):
            try:
                result = hunter.find_email_for_lead(
                    url=lead.website or lead.url,
                    company=lead.company,
                    name=lead.name or lead.username,
                )
                if result:
                    lead.email = result.email
                    if result.first_name and result.last_name and not lead.name:
                        lead.name = f"{result.first_name} {result.last_name}"
                    if result.position and not lead.position:
                        lead.position = result.position
                    enriched += 1
                    console.print(
                        f"  [{i}/{len(needs_email)}] [green]{(lead.company or lead.title or '')[:35]}[/green] "
                        f"-> {result.email} ({result.confidence}%)"
                    )
                else:
                    console.print(
                        f"  [{i}/{len(needs_email)}] [dim]{(lead.company or lead.title or '')[:35]}[/dim] "
                        f"-> no encontrado"
                    )
            except Exception as e:
                console.print(
                    f"  [{i}/{len(needs_email)}] [dim]{(lead.company or lead.title or '')[:35]}[/dim] "
                    f"-> error: {e}"
                )

    console.print(f"[green]Emails encontrados via Hunter.io: {enriched}/{len(needs_email)}[/green]")
    return leads


def auto_verify_emails(leads: List[Lead]) -> List[Lead]:
    """Verify discovered emails using Hunter.io email verifier.

    Marks invalid/disposable emails as empty so they don't pollute the CRM.
    Only runs if HUNTER_API_KEY is configured.

    Args:
        leads: Leads whose emails should be verified.

    Returns:
        Same list with invalid emails cleared.
    """
    if not settings.hunter_api_key:
        return leads

    with_email = [
        l for l in leads
        if l.email and not l.email.endswith("@leadgen.placeholder")
    ]
    if not with_email:
        return leads

    console.print(
        f"\n[bold cyan]Verificando {len(with_email)} emails con Hunter.io...[/bold cyan]"
    )

    verified_count = 0
    invalid_count = 0

    with HunterClient() as hunter:
        if not hunter.is_configured():
            return leads

        for lead in with_email:
            try:
                result = hunter.verify_email(lead.email)
                status = result.get("status", "unknown")

                if status == "valid":
                    verified_count += 1
                elif status in ("invalid", "disposable"):
                    # Clear bad emails
                    logger.info(f"Invalid email removed: {lead.email} ({status})")
                    lead.email = None
                    invalid_count += 1
                # "unknown" or "accept_all" -> keep as-is
            except Exception:
                pass

    console.print(
        f"[green]Verificados: {verified_count}[/green] | "
        f"[red]Invalidos removidos: {invalid_count}[/red]"
    )
    return leads


def run_email_enrichment(leads: List[Lead]) -> List[Lead]:
    """Run the full automatic email enrichment pipeline.

    Steps:
    1. Crawl business websites for emails (free, no API key needed)
    2. Use Hunter.io for remaining leads (if configured)
    3. Verify found emails (if Hunter.io configured)

    Args:
        leads: Leads to enrich.

    Returns:
        Enriched leads.
    """
    if not leads:
        return leads

    before_count = sum(1 for l in leads if l.email and not l.email.endswith("@leadgen.placeholder"))

    # Step 1: Website crawling (always runs, free)
    leads = auto_enrich_emails(leads)

    # Step 2: Hunter.io enrichment (only if configured)
    leads = auto_enrich_with_hunter(leads)

    # Step 3: Email verification (only if Hunter configured)
    leads = auto_verify_emails(leads)

    after_count = sum(1 for l in leads if l.email and not l.email.endswith("@leadgen.placeholder"))
    new_emails = after_count - before_count

    if new_emails > 0:
        console.print(
            f"\n[bold green]Enriquecimiento completado: {new_emails} emails nuevos encontrados "
            f"(total con email: {after_count}/{len(leads)})[/bold green]"
        )
    else:
        console.print(
            f"\n[dim]Enriquecimiento completado: {after_count}/{len(leads)} leads con email[/dim]"
        )

    return leads


def menu_search_leads():
    """Main option 1: Search for new leads."""
    # Select sources
    console.print("\n[bold]Selecciona fuentes para buscar:[/bold]")
    console.print("  [1] Todas las fuentes")
    console.print("  [2] Solo Reddit")
    console.print("  [3] Solo Hacker News")
    console.print("  [4] Solo Google Search")
    console.print("  [5] Solo Product Hunt")
    console.print("  [6] Solo Google Maps (con analisis de reviews)")

    source = Prompt.ask("Opcion", choices=["1", "2", "3", "4", "5", "6"], default="1")

    # Run scraping
    leads = run_scraping() if source == "1" else run_single_source(source)

    if not leads:
        console.print("[yellow]No se encontraron leads[/yellow]")
        return

    # Show preview
    display_leads_table(leads[:10], title="Preview de leads encontrados")

    # AI filtering
    if Confirm.ask("\nFiltrar leads con AI?", default=True):
        leads = filter_leads_with_ai(leads)

    if not leads:
        console.print("[yellow]No quedaron leads despues del filtrado[/yellow]")
        return

    # Send to HubSpot
    send_to_hubspot(leads)


def run_single_source(source: str) -> List[Lead]:
    """Run a single scraper based on selection."""
    scrapers = {
        "2": ("Reddit", RedditScraper),
        "3": ("Hacker News", HackerNewsScraper),
        "4": ("Google", GoogleScraper),
        "5": ("Product Hunt", ProductHuntScraper),
        "6": ("Google Maps", GoogleMapsScraper),
    }

    name, ScraperClass = scrapers.get(source, ("Reddit", RedditScraper))

    console.print(f"\n[cyan]Buscando en {name}...[/cyan]")

    try:
        with ScraperClass() as scraper:
            batch = scraper.scrape()
            leads = batch.leads

        # Auto email enrichment
        if leads:
            leads = run_email_enrichment(leads)

        return leads
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return []


# ==================== 2. VIEW LOCAL LEADS ====================

def menu_view_local_leads():
    """Main option 2: View leads from local SQLite database."""
    console.print("\n[bold]Ver leads locales (SQLite):[/bold]")
    console.print("  [1] Todos los leads")
    console.print("  [2] Solo calificados")
    console.print("  [3] Pendientes de enviar a CRM")
    console.print("  [4] Por fuente")
    console.print("  [5] Estadisticas locales")
    console.print("  [6] Enviar pendientes a HubSpot")
    console.print("  [7] Exportar a CSV")
    console.print("  [8] Buscar emails (Hunter.io)")
    console.print("  [9] Enviar a Google Sheets")
    console.print("  [0] Volver")

    choice = Prompt.ask("Opcion", choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"], default="1")

    if choice == "0":
        return

    if choice == "1":
        leads = db.get_all_leads(limit=50)
        display_leads_table(leads, "Todos los leads locales")
        console.print(f"\n[dim]Total en base de datos: {db.get_statistics()['total_leads']}[/dim]")

    elif choice == "2":
        leads = db.get_qualified_leads(limit=50)
        display_leads_table(leads, "Leads calificados")

    elif choice == "3":
        leads = db.get_unsent_leads(limit=50)
        if leads:
            display_leads_table(leads, "Leads pendientes de enviar")
            console.print(f"\n[cyan]Hay {len(leads)} leads listos para enviar a HubSpot[/cyan]")
        else:
            console.print("[yellow]No hay leads pendientes de enviar[/yellow]")

    elif choice == "4":
        # Select source
        console.print("\n[bold]Selecciona fuente:[/bold]")
        console.print("  [1] Reddit")
        console.print("  [2] Hacker News")
        console.print("  [3] Google Search")
        console.print("  [4] Product Hunt")

        source_choice = Prompt.ask("Fuente", choices=["1", "2", "3", "4"], default="1")
        from src.utils.models import LeadSource
        sources = {
            "1": LeadSource.REDDIT,
            "2": LeadSource.HACKER_NEWS,
            "3": LeadSource.GOOGLE_SEARCH,
            "4": LeadSource.PRODUCT_HUNT,
        }
        leads = db.get_leads_by_source(sources[source_choice])
        display_leads_table(leads, f"Leads de {sources[source_choice].value}")

    elif choice == "5":
        # Show local statistics
        stats = db.get_statistics()
        console.print(Panel(f"""
[bold]ESTADISTICAS LOCALES (SQLite)[/bold]

Total de leads: [cyan]{stats['total_leads']}[/cyan]
Leads calificados: [green]{stats['qualified_leads']}[/green]
Enviados a CRM: [blue]{stats['sent_to_crm']}[/blue]
Pendientes de enviar: [yellow]{stats['pending_send']}[/yellow]

Score AI promedio: [cyan]{stats['avg_ai_score']}[/cyan]
Leads encontrados hoy: [green]{stats['leads_today']}[/green]

[bold]Por fuente:[/bold]
""" + "\n".join([f"  - {k}: {v}" for k, v in stats['by_source'].items()]) + """

[bold]Top keywords:[/bold]
""" + "\n".join([f"  - {k}: {v}" for k, v in list(stats['top_keywords'].items())[:5]]),
            title="Base de Datos Local", border_style="cyan"))

    elif choice == "6":
        # Send pending leads to HubSpot
        leads = db.get_unsent_leads(limit=50)
        if not leads:
            console.print("[yellow]No hay leads pendientes de enviar[/yellow]")
            return

        console.print(f"\n[cyan]Hay {len(leads)} leads pendientes[/cyan]")
        send_to_hubspot(leads)

        # Mark as sent in local DB
        for lead in leads:
            if lead.sent_to_crm:
                db.mark_as_sent(lead.id, lead.hubspot_id or "")

    elif choice == "7":
        # Export to CSV
        console.print("\n[bold]Exportar leads a CSV:[/bold]")
        console.print("  [1] Todos los leads")
        console.print("  [2] Solo calificados")

        export_choice = Prompt.ask("Opcion", choices=["1", "2"], default="1")
        qualified_only = export_choice == "2"

        filepath = db.export_to_csv(qualified_only=qualified_only)
        console.print(f"\n[green]Exportado exitosamente a:[/green]")
        console.print(f"  [cyan]{filepath}[/cyan]")

    elif choice == "8":
        # Enrich leads with Hunter.io
        enrich_leads_with_hunter()

    elif choice == "9":
        # Send to Google Sheets
        sheets = GoogleSheetsSync()
        if not sheets.is_configured():
            console.print("[red]Google Sheets no configurado. Agrega GOOGLE_SHEETS_WEBHOOK_URL en .env[/red]")
            return

        console.print("\n[bold]Enviar a Google Sheets:[/bold]")
        console.print("  [1] Todos los leads")
        console.print("  [2] Solo calificados")

        sheet_choice = Prompt.ask("Opcion", choices=["1", "2"], default="2")
        if sheet_choice == "1":
            leads = db.get_all_leads(limit=200)
        else:
            leads = db.get_qualified_leads(limit=200)

        if not leads:
            console.print("[yellow]No hay leads para enviar[/yellow]")
            return

        if Confirm.ask(f"Enviar {len(leads)} leads a Google Sheets?"):
            sync_to_google_sheets(leads)


def enrich_leads_with_hunter():
    """Use Hunter.io to find emails for leads without email."""
    with HunterClient() as hunter:
        if not hunter.is_configured():
            console.print("[red]Hunter.io no configurado. Agrega HUNTER_API_KEY en .env[/red]")
            return

        # Show account info
        account = hunter.get_account_info()
        if "error" not in account:
            console.print(f"\n[cyan]Hunter.io - Requests disponibles: {account.get('requests_available', '?')}[/cyan]")

        # Get leads without email (or with placeholder email)
        leads = db.get_all_leads(limit=100)
        leads_without_email = [
            l for l in leads
            if not l.email or l.email.endswith("@leadgen.placeholder")
        ]

        if not leads_without_email:
            console.print("[yellow]Todos los leads ya tienen email[/yellow]")
            return

        console.print(f"\n[bold]Encontrados {len(leads_without_email)} leads sin email[/bold]")

        # Ask how many to process
        max_to_process = IntPrompt.ask(
            "Cuantos leads procesar?",
            default=min(10, len(leads_without_email))
        )

        leads_to_process = leads_without_email[:max_to_process]
        found_count = 0
        errors = 0

        console.print(f"\n[cyan]Buscando emails para {len(leads_to_process)} leads...[/cyan]\n")

        for i, lead in enumerate(leads_to_process, 1):
            try:
                result = hunter.find_email_for_lead(
                    url=lead.url,
                    company=lead.company,
                    name=lead.name or lead.username
                )

                if result:
                    # Update lead in database
                    db.update_lead(lead.id, email=result.email)

                    # Also update name if found
                    if result.first_name and result.last_name:
                        full_name = f"{result.first_name} {result.last_name}"
                        db.update_lead(lead.id, name=full_name)

                    console.print(
                        f"  [{i}/{len(leads_to_process)}] [green]{lead.title[:30]}...[/green] "
                        f"-> {result.email} (confianza: {result.confidence}%)"
                    )
                    found_count += 1
                else:
                    console.print(
                        f"  [{i}/{len(leads_to_process)}] [yellow]{lead.title[:30]}...[/yellow] "
                        f"-> No encontrado"
                    )

            except Exception as e:
                console.print(
                    f"  [{i}/{len(leads_to_process)}] [red]{lead.title[:30]}...[/red] "
                    f"-> Error: {e}"
                )
                errors += 1

        # Summary
        console.print(f"\n[bold]Resumen:[/bold]")
        console.print(f"  [green]Emails encontrados: {found_count}[/green]")
        console.print(f"  [yellow]No encontrados: {len(leads_to_process) - found_count - errors}[/yellow]")
        if errors:
            console.print(f"  [red]Errores: {errors}[/red]")


# ==================== 3. VIEW HUBSPOT LEADS ====================

def menu_view_hubspot_leads():
    """Main option 3: View leads in HubSpot CRM."""
    console.print("\n[bold]Ver leads en HubSpot:[/bold]")
    console.print("  [1] Todos los leads")
    console.print("  [2] Por etapa del pipeline")
    console.print("  [0] Volver")

    choice = Prompt.ask("Opcion", choices=["0", "1", "2"], default="1")

    with HubSpotCRM() as crm:
        if not crm.is_configured():
            console.print("[red]HubSpot no configurado[/red]")
            return

        if choice == "1":
            contacts = crm.get_all_contacts(limit=50)
            display_contacts_table(contacts, "Todos los leads")

        elif choice == "2":
            # Show stage submenu
            console.print("\n[bold]Selecciona etapa:[/bold]")
            for i, stage in enumerate(LeadStage, 1):
                console.print(f"  [{i}] {stage.value}")

            stage_choice = IntPrompt.ask("Etapa", default=1)
            stages = list(LeadStage)
            if 1 <= stage_choice <= len(stages):
                selected_stage = stages[stage_choice - 1]
                contacts = crm.get_contacts_by_stage(selected_stage)
                display_contacts_table(contacts, f"Leads en etapa: {selected_stage.value}")


def display_leads_table(leads: List[Lead], title: str = "Leads"):
    """Display leads in a rich table."""
    table = Table(title=title, show_lines=True)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Fuente", style="cyan")
    table.add_column("Titulo", style="green", max_width=40)
    table.add_column("Keywords", style="yellow", max_width=30)
    table.add_column("Score", justify="center")
    table.add_column("Dolor", justify="center")

    for lead in leads[:20]:
        score = f"{lead.ai_score:.2f}" if lead.ai_score else "-"

        # Pain indicator for Google Maps leads
        if lead.source.value == "google_maps":
            if lead.has_pain:
                pain_str = f"[red]SI ({lead.pain_score:.1f})[/red]" if lead.pain_score else "[red]SI[/red]"
            else:
                pain_str = "[green]NO[/green]"
        else:
            pain_str = "-"

        table.add_row(
            lead.id[:8],
            lead.source.value,
            lead.title[:40],
            ", ".join(lead.keywords_matched[:3]),
            score,
            pain_str
        )

    console.print(table)


def display_contacts_table(contacts: List, title: str = "Contacts"):
    """Display HubSpot contacts in a table."""
    if not contacts:
        console.print("[yellow]No se encontraron contactos[/yellow]")
        return

    table = Table(title=title, show_lines=True)
    table.add_column("ID", style="dim", width=12)
    table.add_column("Nombre", style="green")
    table.add_column("Email", style="cyan")
    table.add_column("Empresa", style="yellow")
    table.add_column("Etapa", style="magenta")
    table.add_column("Fuente", style="blue")

    for contact in contacts[:30]:
        name = f"{contact.firstname or ''} {contact.lastname or ''}".strip() or "-"
        table.add_row(
            contact.id,
            name,
            contact.email or "-",
            contact.company or "-",
            contact.lead_stage.value,
            contact.source or "-"
        )

    console.print(table)
    console.print(f"\nTotal: {len(contacts)} contactos")


# ==================== 3. UPDATE LEAD ====================

def menu_update_lead():
    """Main option 3: Update a lead."""
    console.print("\n[bold]Actualizar lead:[/bold]")
    console.print("  [1] Cambiar etapa")
    console.print("  [2] Agregar nota")
    console.print("  [3] Marcar como ganado")
    console.print("  [4] Marcar como perdido")
    console.print("  [5] Eliminar lead")
    console.print("  [0] Volver")

    choice = Prompt.ask("Opcion", choices=["0", "1", "2", "3", "4", "5"], default="1")

    if choice == "0":
        return

    # Get contact ID
    contact_id = Prompt.ask("ID del contacto")

    with HubSpotCRM() as crm:
        if not crm.is_configured():
            console.print("[red]HubSpot no configurado[/red]")
            return

        # Verify contact exists
        contact = crm.get_contact(contact_id)
        if not contact:
            console.print("[red]Contacto no encontrado[/red]")
            return

        console.print(f"[green]Contacto: {contact.firstname} {contact.lastname} ({contact.email})[/green]")

        if choice == "1":
            # Change stage
            console.print("\n[bold]Nueva etapa:[/bold]")
            for i, stage in enumerate(LeadStage, 1):
                console.print(f"  [{i}] {stage.value}")
            stage_num = IntPrompt.ask("Etapa", default=1)
            stages = list(LeadStage)
            if 1 <= stage_num <= len(stages):
                if crm.update_lead_stage(contact_id, stages[stage_num - 1]):
                    console.print("[green]Etapa actualizada[/green]")

        elif choice == "2":
            # Add note
            note = Prompt.ask("Escribe la nota")
            if crm.add_note(contact_id, note):
                console.print("[green]Nota agregada[/green]")

        elif choice == "3":
            # Mark as won
            if Confirm.ask("Marcar como ganado?"):
                if crm.mark_as_won(contact_id):
                    console.print("[green]Marcado como ganado![/green]")

        elif choice == "4":
            # Mark as lost
            reason = Prompt.ask("Razon de perdida (opcional)", default="")
            if crm.mark_as_lost(contact_id, reason):
                console.print("[yellow]Marcado como perdido[/yellow]")

        elif choice == "5":
            # Delete
            if Confirm.ask("[red]Eliminar este contacto? Esta accion no se puede deshacer[/red]"):
                if crm.delete_contact(contact_id):
                    console.print("[green]Contacto eliminado[/green]")


# ==================== 4. STATISTICS ====================

def menu_statistics():
    """Main option 4: View statistics."""
    with HubSpotCRM() as crm:
        if not crm.is_configured():
            console.print("[red]HubSpot no configurado[/red]")
            return

        console.print("\n[bold cyan]Obteniendo estadisticas...[/bold cyan]")
        stats = crm.get_statistics()

        if "error" in stats:
            console.print(f"[red]{stats['error']}[/red]")
            return

        # Display stats panel
        console.print(Panel(f"""
[bold]ESTADISTICAS DE LEADS[/bold]

Total de leads: [cyan]{stats['total_leads']}[/cyan]

[bold]Por etapa:[/bold]
  - Nuevos:     {stats['by_stage'].get('new', 0)}
  - Contactados: {stats['by_stage'].get('contacted', 0)}
  - Demo:       {stats['by_stage'].get('demo', 0)}
  - Propuesta:  {stats['by_stage'].get('proposal', 0)}
  - Ganados:    [green]{stats['by_stage'].get('closed_won', 0)}[/green]
  - Perdidos:   [red]{stats['by_stage'].get('closed_lost', 0)}[/red]

[bold]Metricas:[/bold]
  - Tasa de conversion: [cyan]{stats['conversion_rate']}%[/cyan]
  - Tasa de cierre:     [green]{stats['win_rate']}%[/green]

[bold]Por fuente:[/bold]
""" + "\n".join([f"  - {k}: {v}" for k, v in stats['by_source'].items()]),
            title="Dashboard", border_style="green"))


# ==================== 5. SEARCH ====================

def menu_search():
    """Main option 5: Search for a lead."""
    query = Prompt.ask("Buscar por nombre o email")

    with HubSpotCRM() as crm:
        if not crm.is_configured():
            console.print("[red]HubSpot no configurado[/red]")
            return

        contacts = crm.search_contacts(query)
        display_contacts_table(contacts, f"Resultados para: {query}")


# ==================== 6. CONFIGURATION ====================

def menu_configuration():
    """Main option 7: View/edit configuration."""
    console.print("\n[bold cyan]═══ CONFIGURACION ═══[/bold cyan]\n")

    # Check API keys
    console.print("[bold]Estado de APIs:[/bold]")
    console.print(f"  HubSpot:   {'[green]Configurado[/green]' if settings.hubspot_api_key else '[red]No configurado[/red]'}")
    console.print(f"  Google:    {'[green]Configurado[/green]' if settings.google_api_key else '[red]No configurado[/red]'}")
    console.print(f"  OpenAI:    {'[green]Configurado[/green]' if settings.openai_api_key else '[red]No configurado[/red]'}")
    console.print(f"  Anthropic: {'[green]Configurado[/green]' if settings.anthropic_api_key else '[red]No configurado[/red]'}")
    console.print(f"  Hunter.io: {'[green]Configurado[/green]' if settings.hunter_api_key else '[red]No configurado[/red]'}")
    console.print(f"  G. Sheets: {'[green]Configurado[/green]' if settings.google_sheets_webhook_url else '[red]No configurado[/red]'}")

    # Database info
    console.print(f"\n[bold]Base de datos local:[/bold]")
    console.print(f"  Ubicacion: [cyan]{db.db_path}[/cyan]")
    local_stats = db.get_statistics()
    console.print(f"  Leads guardados: [green]{local_stats['total_leads']}[/green]")

    console.print(f"\n[bold]Subreddits configurados:[/bold]")
    console.print(f"  {', '.join(settings.subreddits)}")

    console.print(f"\n[bold]Keywords de dolor:[/bold]")
    for kw in settings.pain_keywords[:10]:
        console.print(f"  - {kw}")
    console.print(f"  ... y {len(settings.pain_keywords) - 10} mas")

    console.print("\n[dim]Edita el archivo .env para cambiar la configuracion[/dim]")


# ==================== 8. CONTACTS TO GOOGLE SHEETS ====================

def menu_contacts_to_sheet():
    """Main option 8: Search business contacts by industry + city (+ radius) and send to Google Sheets."""
    # Check Google Sheets config first
    sheets = GoogleSheetsSync()
    if not sheets.is_configured():
        console.print("[red]Google Sheets no configurado. Agrega GOOGLE_SHEETS_WEBHOOK_URL en .env[/red]")
        console.print("[dim]Ver apps_script_contacts.js para instrucciones de configuracion[/dim]")
        return

    console.print("\n[bold cyan]═══ CONTACTOS → GOOGLE SHEETS ═══[/bold cyan]")
    console.print("[dim]Busca negocios por industria, ciudad y radio, y envialos a tu Google Sheet[/dim]\n")

    # Verify Sheet connection
    console.print("[cyan]Verificando conexion a Google Sheets...[/cyan]")
    check = sheets.verify_connection()
    if check["ok"]:
        console.print(f"[green]Sheet conectada: {check['message']}[/green]\n")
    else:
        console.print(f"[red]No se pudo conectar a la Sheet: {check['message']}[/red]")
        console.print("[dim]Verifica tu GOOGLE_SHEETS_WEBHOOK_URL en .env[/dim]")
        if not Confirm.ask("Continuar de todas formas?", default=False):
            return
        console.print()

    # Select business type / industry
    console.print("[bold]Selecciona industria:[/bold]")
    business_types = settings.google_maps_business_types
    for i, bt in enumerate(business_types, 1):
        console.print(f"  [{i}] {bt.replace('_', ' ').title()}")
    console.print(f"  [{len(business_types) + 1}] Otro (escribir manualmente)")

    type_choices = [str(i) for i in range(1, len(business_types) + 2)]
    type_choice = Prompt.ask("Industria", choices=type_choices, default="1")
    type_idx = int(type_choice) - 1

    if type_idx < len(business_types):
        selected_type = business_types[type_idx]
    else:
        selected_type = Prompt.ask("Escribe el tipo de negocio (ej: florist, gym, bakery)")
        if not selected_type.strip():
            console.print("[yellow]Tipo de negocio vacio, cancelando[/yellow]")
            return

    # Get city
    console.print(f"\n[bold]Ciudad:[/bold]")
    console.print("[dim]Ejemplos: Lima OH, Miami FL, Houston TX, Austin TX[/dim]")
    city = Prompt.ask("Escribe la ciudad")
    if not city.strip():
        console.print("[yellow]Ciudad vacia, cancelando[/yellow]")
        return

    # Get radius (optional)
    console.print(f"\n[bold]Radio de busqueda (millas):[/bold]")
    console.print("[dim]Deja vacio para busqueda normal sin radio. Max ~31 millas.[/dim]")
    radius_input = Prompt.ask("Radio en millas (Enter para omitir)", default="")
    radius_miles = None
    if radius_input.strip():
        try:
            radius_miles = float(radius_input.strip())
            if radius_miles <= 0:
                console.print("[yellow]Radio debe ser positivo, usando busqueda sin radio[/yellow]")
                radius_miles = None
            elif radius_miles > 31:
                console.print("[yellow]Radio maximo es ~31 millas (50km). Usando 31.[/yellow]")
                radius_miles = 31.0
        except ValueError:
            console.print("[yellow]Radio invalido, usando busqueda sin radio[/yellow]")

    # Confirm search
    search_desc = f"[bold]{selected_type.replace('_', ' ').title()}[/bold] en [bold]{city}[/bold]"
    if radius_miles:
        search_desc += f" (radio: [bold]{radius_miles} millas[/bold])"
    console.print(f"\n[cyan]Buscando: {search_desc}[/cyan]")

    if not Confirm.ask("Continuar?", default=True):
        return

    # Run Google Maps scraper
    console.print(f"\n[bold green]Buscando negocios...[/bold green]")

    try:
        with GoogleMapsScraper() as scraper:
            batch = scraper.scrape(
                location=city,
                category=selected_type,
                radius_miles=radius_miles,
            )
    except Exception as e:
        console.print(f"[red]Error en la busqueda: {e}[/red]")
        return

    if not batch.leads:
        console.print("[yellow]No se encontraron negocios. Intenta otra industria o ciudad.[/yellow]")
        if batch.errors:
            for err in batch.errors[:3]:
                console.print(f"  [red]{err}[/red]")
        return

    # Auto email enrichment for leads still missing emails
    leads = run_email_enrichment(batch.leads)
    console.print(f"\n[green]Encontrados: {len(leads)} negocios[/green]")

    # Display preview table
    title = f"{selected_type.replace('_', ' ').title()} en {city}"
    if radius_miles:
        title += f" ({radius_miles} mi)"
    table = Table(title=title, show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Negocio", style="green", max_width=30)
    table.add_column("Telefono", style="cyan", max_width=18)
    table.add_column("Email", style="yellow", max_width=25)
    table.add_column("Rating", justify="center", width=7)
    table.add_column("Reviews", justify="center", width=8)
    table.add_column("Dolor", justify="center", width=8)

    for i, lead in enumerate(leads[:15], 1):
        pain_str = "[red]SI[/red]" if lead.has_pain else "[green]NO[/green]"
        rating_str = f"{lead.rating:.1f}" if lead.rating else "-"
        table.add_row(
            str(i),
            (lead.company or lead.title or "")[:30],
            lead.phone or "-",
            lead.email or "-",
            rating_str,
            str(lead.review_count or "-"),
            pain_str
        )

    console.print(table)

    if len(leads) > 15:
        console.print(f"[dim]... y {len(leads) - 15} mas[/dim]")

    # Summary stats
    with_phone = sum(1 for l in leads if l.phone)
    with_email = sum(1 for l in leads if l.email)
    with_pain = sum(1 for l in leads if l.has_pain)
    with_website = sum(1 for l in leads if l.website)

    console.print(f"\n[bold]Resumen:[/bold]")
    console.print(f"  Con telefono: [cyan]{with_phone}[/cyan]")
    console.print(f"  Con email:    [cyan]{with_email}[/cyan]")
    console.print(f"  Con website:  [cyan]{with_website}[/cyan]")
    console.print(f"  Con dolor:    [red]{with_pain}[/red]")

    # Confirm send to Google Sheets
    if not Confirm.ask(f"\nEnviar {len(leads)} contactos a Google Sheets?", default=True):
        # Still save to local DB
        if Confirm.ask("Guardar en base de datos local?", default=True):
            result = db.save_leads(leads)
            console.print(f"[green]Guardados: {result['saved']} nuevos[/green]")
        return

    # Save to local database first
    result = db.save_leads(leads)
    console.print(f"[green]Guardados localmente: {result['saved']} nuevos, {result['duplicates']} duplicados omitidos[/green]")

    # Send to Google Sheets
    console.print(f"\n[cyan]Enviando contactos a Google Sheets...[/cyan]")
    try:
        result = sheets.send_leads(leads)
        console.print(f"[bold green]Enviados a Google Sheets: {result['sent']} contactos[/bold green]")
        if result['failed']:
            console.print(f"[yellow]Fallidos: {result['failed']}[/yellow]")
        console.print(f"[dim]Revisa tu Google Sheet para ver los resultados[/dim]")

    except Exception as e:
        console.print(f"[red]Error enviando a Google Sheets: {e}[/red]")
        logger.error(f"Google Sheets sync error: {e}")


# ==================== MAIN ====================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Lead Generation App")
    parser.add_argument("--scrape", action="store_true", help="Run scraping only")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--no-interactive", action="store_true", help="Non-interactive mode")

    args = parser.parse_args()

    # Load environment
    from dotenv import load_dotenv
    load_dotenv()

    display_banner()

    # Quick commands
    if args.scrape:
        leads = run_scraping()
        filtered = filter_leads_with_ai(leads)
        if not args.no_interactive:
            send_to_hubspot(filtered)
        return

    if args.stats:
        menu_statistics()
        return

    # Interactive menu loop
    while True:
        try:
            choice = display_main_menu()

            if choice == "0":
                console.print("\n[bold green]Hasta luego![/bold green]\n")
                break
            elif choice == "1":
                menu_search_leads()
            elif choice == "2":
                menu_view_local_leads()
            elif choice == "3":
                menu_view_hubspot_leads()
            elif choice == "4":
                menu_update_lead()
            elif choice == "5":
                menu_statistics()
            elif choice == "6":
                menu_search()
            elif choice == "7":
                menu_configuration()
            elif choice == "8":
                menu_contacts_to_sheet()

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Operacion cancelada[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            logger.exception("Unexpected error")


if __name__ == "__main__":
    main()
