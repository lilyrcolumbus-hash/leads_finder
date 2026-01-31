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
from src.utils.models import Lead, LeadBatch
from src.scrapers import RedditScraper, HackerNewsScraper, GoogleScraper, ProductHuntScraper
from src.filters import AILeadFilter
from src.crm import HubSpotCRM, LeadStage
from src.database import LeadDatabase

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
    console.print("  [0] Salir")
    console.print()

    return Prompt.ask("Selecciona una opcion", choices=["0", "1", "2", "3", "4", "5", "6", "7"], default="1")


# ==================== 1. SCRAPING ====================

def _run_single_scraper(name: str, ScraperClass) -> Tuple[str, LeadBatch, Optional[str]]:
    """Run a single scraper and return results. Used for concurrent execution."""
    try:
        with ScraperClass() as scraper:
            batch = scraper.scrape()
            return (name, batch, None)
    except Exception as e:
        empty_batch = LeadBatch(source=ScraperClass.source)
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
    ]

    # Record scrape run
    source_names = [name for name, _ in scrapers]
    run_id = db.start_scrape_run(source_names)

    # Track timing
    start_time = time.time()

    # Show initial status
    console.print("[cyan]Ejecutando 4 scrapers en paralelo...[/cyan]")
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
                console.print(f"  [red][{completed}/4] {name}: Error - {error}[/red]")
                errors.append(f"{name}: {error}")
            else:
                all_leads.extend(batch.leads)
                errors.extend(batch.errors)
                console.print(f"  [green][{completed}/4] {name}: {len(batch.leads)} leads encontrados[/green]")

    # Calculate time taken
    elapsed = time.time() - start_time
    console.print(f"\n[cyan]Tiempo total: {elapsed:.1f} segundos[/cyan]")

    # Save leads to local database
    if all_leads:
        console.print("\n[cyan]Guardando leads en base de datos local...[/cyan]")
        result = db.save_leads(all_leads)
        console.print(f"[green]Guardados: {result['saved']} nuevos, {result['duplicates']} duplicados omitidos[/green]")

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


def menu_search_leads():
    """Main option 1: Search for new leads."""
    # Select sources
    console.print("\n[bold]Selecciona fuentes para buscar:[/bold]")
    console.print("  [1] Todas las fuentes")
    console.print("  [2] Solo Reddit")
    console.print("  [3] Solo Hacker News")
    console.print("  [4] Solo Google Search")
    console.print("  [5] Solo Product Hunt")

    source = Prompt.ask("Opcion", choices=["1", "2", "3", "4", "5"], default="1")

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
    }

    name, ScraperClass = scrapers.get(source, ("Reddit", RedditScraper))

    console.print(f"\n[cyan]Buscando en {name}...[/cyan]")

    try:
        with ScraperClass() as scraper:
            batch = scraper.scrape()
            return batch.leads
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
    console.print("  [0] Volver")

    choice = Prompt.ask("Opcion", choices=["0", "1", "2", "3", "4", "5", "6", "7"], default="1")

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

    for lead in leads[:20]:
        score = f"{lead.ai_score:.2f}" if lead.ai_score else "-"
        table.add_row(
            lead.id[:8],
            lead.source.value,
            lead.title[:40],
            ", ".join(lead.keywords_matched[:3]),
            score
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

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Operacion cancelada[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            logger.exception("Unexpected error")


if __name__ == "__main__":
    main()
