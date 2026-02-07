#!/usr/bin/env python3
"""
Lead Generation App - Main Entry Point

A modular lead generation tool that:
1. Scrapes multiple sources for potential leads (10 sources)
2. Extracts emails from business websites
3. Filters them using AI (Ollama/Gemini/OpenAI/Anthropic)
4. Exports to CSV or Google Sheets
5. Manages them in HubSpot CRM

Usage:
    python main.py              # Interactive menu
    python main.py --scrape     # Run scraping only
    python main.py --stats      # Show statistics
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

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
from src.scrapers import (
    RedditScraper, HackerNewsScraper, GoogleScraper, ProductHuntScraper,
    GoogleMapsScraper, YelpScraper, IndeedScraper, YellowPagesScraper,
    BBBScraper, CraigslistScraper, EmailExtractor,
)
from src.filters import AILeadFilter, OllamaGeminiFilter
from src.crm import HubSpotCRM, LeadStage
from src.utils.csv_export import export_leads_to_csv, export_leads_for_google_sheets

# Initialize
console = Console()
logger = setup_logger("main")


def display_banner():
    """Display application banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║           LEAD GENERATION APP v2.0                        ║
    ║     10 fuentes | Ollama/Gemini AI | CSV Export             ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(Panel(banner, style="bold blue"))


def display_main_menu() -> str:
    """Display main menu and get user choice."""
    console.print("\n[bold cyan]═══ MENU PRINCIPAL ═══[/bold cyan]\n")
    console.print("  [1] Buscar nuevos leads")
    console.print("  [2] Ver mis leads")
    console.print("  [3] Actualizar lead")
    console.print("  [4] Ver estadisticas")
    console.print("  [5] Buscar lead")
    console.print("  [6] Exportar a CSV")
    console.print("  [7] Extraer emails de websites")
    console.print("  [8] Generar mensajes personalizados")
    console.print("  [9] Configuracion")
    console.print("  [0] Salir")
    console.print()

    return Prompt.ask("Selecciona una opcion", choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"], default="1")


# ==================== 1. SCRAPING ====================

def run_scraping(selected_sources: Optional[List[str]] = None) -> List[Lead]:
    """Run scrapers and collect leads."""
    all_leads: List[Lead] = []
    errors: List[str] = []

    console.print("\n[bold green]Iniciando busqueda de leads...[/bold green]\n")

    all_scrapers = [
        ("Reddit", RedditScraper, "1"),
        ("Hacker News", HackerNewsScraper, "2"),
        ("Google Search", GoogleScraper, "3"),
        ("Product Hunt", ProductHuntScraper, "4"),
        ("Google Maps", GoogleMapsScraper, "5"),
        ("Yelp", YelpScraper, "6"),
        ("Indeed", IndeedScraper, "7"),
        ("Yellow Pages", YellowPagesScraper, "8"),
        ("BBB", BBBScraper, "9"),
        ("Craigslist", CraigslistScraper, "10"),
    ]

    # Filter to selected sources
    if selected_sources:
        scrapers = [(n, c, i) for n, c, i in all_scrapers if i in selected_sources]
    else:
        scrapers = all_scrapers

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        for name, ScraperClass, _ in scrapers:
            task = progress.add_task(f"Buscando en {name}...", total=None)
            try:
                with ScraperClass() as scraper:
                    batch = scraper.scrape()
                    all_leads.extend(batch.leads)
                    errors.extend(batch.errors)
                    progress.update(task, description=f"[green]{name}: {len(batch.leads)} leads encontrados")
            except Exception as e:
                progress.update(task, description=f"[red]{name}: Error - {e}")
                errors.append(f"{name}: {str(e)}")
            progress.remove_task(task)

    # Show summary
    console.print(f"\n[bold]Total leads encontrados: {len(all_leads)}[/bold]")

    if errors:
        console.print(f"[yellow]Errores encontrados: {len(errors)}[/yellow]")
        for err in errors[:5]:
            logger.warning(err)

    return all_leads


def filter_leads_with_ai(leads: List[Lead]) -> List[Lead]:
    """Filter leads using AI (tries Ollama/Gemini first, then OpenAI/Anthropic)."""
    if not leads:
        return []

    # Try Ollama/Gemini first (free)
    ollama_filter = OllamaGeminiFilter()
    if ollama_filter.is_available():
        console.print(f"\n[bold cyan]Filtrando leads con {ollama_filter.get_backend_name()} (gratis)...[/bold cyan]")
        filtered = ollama_filter.filter_leads(leads)
        qualified = [l for l in filtered if l.is_qualified]
        console.print(f"[green]Leads calificados: {len(qualified)}/{len(leads)}[/green]")
        return qualified

    # Fallback to OpenAI/Anthropic
    console.print("\n[bold cyan]Filtrando leads con AI (OpenAI/Anthropic)...[/bold cyan]")
    ai_filter = AILeadFilter()
    filtered = ai_filter.filter_leads(leads)
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
    console.print("\n[bold]Selecciona fuentes para buscar:[/bold]")
    console.print("  [1]  Todas las fuentes (10)")
    console.print("  [2]  Solo foros (Reddit + HN + Product Hunt)")
    console.print("  [3]  Solo directorios (Google Maps + Yelp + YP + BBB)")
    console.print("  [4]  Solo empleo (Indeed + Craigslist)")
    console.print("  [5]  Seleccionar manualmente")

    choice = Prompt.ask("Opcion", choices=["1", "2", "3", "4", "5"], default="1")

    selected = None
    if choice == "2":
        selected = ["1", "2", "4"]  # Reddit, HN, PH
    elif choice == "3":
        selected = ["5", "6", "8", "9"]  # GMaps, Yelp, YP, BBB
    elif choice == "4":
        selected = ["7", "10"]  # Indeed, Craigslist
    elif choice == "5":
        selected = _select_sources_manually()

    leads = run_scraping(selected)

    if not leads:
        console.print("[yellow]No se encontraron leads[/yellow]")
        return

    # Store leads in memory for later use
    _store_leads(leads)

    # Show preview
    display_leads_table(leads[:10], title="Preview de leads encontrados")

    # Email extraction
    websites_count = sum(1 for l in leads if l.website and not l.email)
    if websites_count > 0 and Confirm.ask(f"\nExtraer emails de {websites_count} sitios web?", default=True):
        _run_email_extraction(leads)

    # AI filtering
    if Confirm.ask("\nFiltrar leads con AI?", default=True):
        leads = filter_leads_with_ai(leads)
        _store_leads(leads)

    if not leads:
        console.print("[yellow]No quedaron leads despues del filtrado[/yellow]")
        return

    # Export options
    console.print("\n[bold]Que quieres hacer con los leads?[/bold]")
    console.print("  [1] Enviar a HubSpot")
    console.print("  [2] Exportar a CSV")
    console.print("  [3] Ambos")
    console.print("  [4] Nada por ahora")

    action = Prompt.ask("Opcion", choices=["1", "2", "3", "4"], default="2")

    if action in ["1", "3"]:
        send_to_hubspot(leads)
    if action in ["2", "3"]:
        _export_csv(leads)


def _select_sources_manually() -> List[str]:
    """Let user select individual sources."""
    sources = [
        ("1", "Reddit"),
        ("2", "Hacker News"),
        ("3", "Google Search"),
        ("4", "Product Hunt"),
        ("5", "Google Maps"),
        ("6", "Yelp"),
        ("7", "Indeed"),
        ("8", "Yellow Pages"),
        ("9", "BBB"),
        ("10", "Craigslist"),
    ]

    console.print("\n[bold]Fuentes disponibles:[/bold]")
    for num, name in sources:
        console.print(f"  [{num}] {name}")

    selected_str = Prompt.ask("Ingresa los numeros separados por coma (ej: 1,5,6)")
    return [s.strip() for s in selected_str.split(",")]


# ==================== LEADS STORAGE ====================

_current_leads: List[Lead] = []


def _store_leads(leads: List[Lead]):
    """Store leads in memory."""
    global _current_leads
    _current_leads = leads


def _get_leads() -> List[Lead]:
    """Get stored leads."""
    return _current_leads


# ==================== 2. VIEW LEADS ====================

def menu_view_leads():
    """Main option 2: View leads in CRM."""
    console.print("\n[bold]Ver leads:[/bold]")
    console.print("  [1] Leads de esta sesion")
    console.print("  [2] Leads en HubSpot")
    console.print("  [0] Volver")

    choice = Prompt.ask("Opcion", choices=["0", "1", "2"], default="1")

    if choice == "1":
        leads = _get_leads()
        if not leads:
            console.print("[yellow]No hay leads en esta sesion. Usa opcion 1 para buscar.[/yellow]")
            return
        display_leads_table(leads, "Leads de esta sesion")

    elif choice == "2":
        with HubSpotCRM() as crm:
            if not crm.is_configured():
                console.print("[red]HubSpot no configurado[/red]")
                return

            console.print("\n[bold]Filtrar por etapa:[/bold]")
            console.print("  [1] Todos")
            for i, stage in enumerate(LeadStage, 2):
                console.print(f"  [{i}] {stage.value}")

            stage_choice = Prompt.ask("Opcion", default="1")

            if stage_choice == "1":
                contacts = crm.get_all_contacts(limit=50)
                display_contacts_table(contacts, "Todos los leads")
            else:
                stages = list(LeadStage)
                idx = int(stage_choice) - 2
                if 0 <= idx < len(stages):
                    contacts = crm.get_contacts_by_stage(stages[idx])
                    display_contacts_table(contacts, f"Leads en etapa: {stages[idx].value}")


def display_leads_table(leads: List[Lead], title: str = "Leads"):
    """Display leads in a rich table."""
    table = Table(title=title, show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Fuente", style="cyan", width=12)
    table.add_column("Empresa", style="green", max_width=25)
    table.add_column("Email", style="yellow", max_width=25)
    table.add_column("Telefono", style="blue", max_width=15)
    table.add_column("Ubicacion", style="magenta", max_width=15)
    table.add_column("Score", justify="center", width=6)

    for i, lead in enumerate(leads[:30], 1):
        score = f"{lead.ai_score:.0%}" if lead.ai_score else "-"
        table.add_row(
            str(i),
            lead.source.value,
            (lead.company or lead.title)[:25],
            (lead.email or "-")[:25],
            lead.phone or "-",
            (lead.location or "-")[:15],
            score
        )

    console.print(table)
    console.print(f"\nTotal: {len(leads)} leads")


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
            console.print("\n[bold]Nueva etapa:[/bold]")
            for i, stage in enumerate(LeadStage, 1):
                console.print(f"  [{i}] {stage.value}")
            stage_num = IntPrompt.ask("Etapa", default=1)
            stages = list(LeadStage)
            if 1 <= stage_num <= len(stages):
                if crm.update_lead_stage(contact_id, stages[stage_num - 1]):
                    console.print("[green]Etapa actualizada[/green]")

        elif choice == "2":
            note = Prompt.ask("Escribe la nota")
            if crm.add_note(contact_id, note):
                console.print("[green]Nota agregada[/green]")

        elif choice == "3":
            if Confirm.ask("Marcar como ganado?"):
                if crm.mark_as_won(contact_id):
                    console.print("[green]Marcado como ganado![/green]")

        elif choice == "4":
            reason = Prompt.ask("Razon de perdida (opcional)", default="")
            if crm.mark_as_lost(contact_id, reason):
                console.print("[yellow]Marcado como perdido[/yellow]")

        elif choice == "5":
            if Confirm.ask("[red]Eliminar este contacto? Esta accion no se puede deshacer[/red]"):
                if crm.delete_contact(contact_id):
                    console.print("[green]Contacto eliminado[/green]")


# ==================== 4. STATISTICS ====================

def menu_statistics():
    """Main option 4: View statistics."""
    leads = _get_leads()

    if leads:
        console.print("\n[bold cyan]═══ ESTADISTICAS DE SESION ═══[/bold cyan]")

        # By source
        source_counts = {}
        for lead in leads:
            source_counts[lead.source.value] = source_counts.get(lead.source.value, 0) + 1

        table = Table(title="Leads por fuente")
        table.add_column("Fuente", style="cyan")
        table.add_column("Cantidad", justify="center", style="green")
        table.add_column("Con email", justify="center", style="yellow")
        table.add_column("Con telefono", justify="center", style="blue")

        for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
            source_leads = [l for l in leads if l.source.value == source]
            with_email = sum(1 for l in source_leads if l.email)
            with_phone = sum(1 for l in source_leads if l.phone)
            table.add_row(source, str(count), str(with_email), str(with_phone))

        console.print(table)

        qualified = sum(1 for l in leads if l.is_qualified)
        console.print(f"\nTotal: {len(leads)} | Calificados: {qualified} | Con email: {sum(1 for l in leads if l.email)} | Con telefono: {sum(1 for l in leads if l.phone)}")

    # HubSpot stats
    with HubSpotCRM() as crm:
        if crm.is_configured():
            if Confirm.ask("\nVer estadisticas de HubSpot?", default=True):
                stats = crm.get_statistics()
                if "error" not in stats:
                    console.print(Panel(f"""
[bold]ESTADISTICAS DE HUBSPOT[/bold]

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
""", title="HubSpot Dashboard", border_style="green"))


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


# ==================== 6. CSV EXPORT ====================

def menu_export_csv():
    """Main option 6: Export leads to CSV."""
    leads = _get_leads()
    if not leads:
        console.print("[yellow]No hay leads para exportar. Usa opcion 1 para buscar primero.[/yellow]")
        return

    _export_csv(leads)


def _export_csv(leads: List[Lead]):
    """Export leads to CSV."""
    console.print("\n[bold]Formato de exportacion:[/bold]")
    console.print("  [1] CSV estandar")
    console.print("  [2] Google Sheets (TSV)")

    fmt = Prompt.ask("Opcion", choices=["1", "2"], default="1")

    try:
        if fmt == "1":
            filepath = export_leads_to_csv(leads)
        else:
            filepath = export_leads_for_google_sheets(leads)

        console.print(f"\n[green]Exportado exitosamente: {filepath}[/green]")
        console.print(f"[dim]Total: {len(leads)} leads exportados[/dim]")
    except Exception as e:
        console.print(f"[red]Error al exportar: {e}[/red]")


# ==================== 7. EMAIL EXTRACTION ====================

def menu_extract_emails():
    """Main option 7: Extract emails from websites."""
    leads = _get_leads()
    if not leads:
        console.print("[yellow]No hay leads. Usa opcion 1 para buscar primero.[/yellow]")
        return

    websites_count = sum(1 for l in leads if l.website and not l.email)
    if websites_count == 0:
        console.print("[yellow]No hay sitios web pendientes de extraer emails.[/yellow]")
        return

    console.print(f"\n[cyan]Se encontraron {websites_count} sitios web sin email.[/cyan]")
    if Confirm.ask("Iniciar extraccion de emails?", default=True):
        _run_email_extraction(leads)


def _run_email_extraction(leads: List[Lead]):
    """Run email extraction on leads."""
    console.print("\n[cyan]Extrayendo emails de sitios web...[/cyan]")

    with EmailExtractor() as extractor:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Extrayendo emails...", total=None)
            extractor.extract_emails_from_leads(leads)
            progress.remove_task(task)

    emails_found = sum(1 for l in leads if l.email)
    console.print(f"[green]Emails encontrados: {emails_found}/{len(leads)}[/green]")
    _store_leads(leads)


# ==================== 8. PERSONALIZED MESSAGES ====================

def menu_generate_messages():
    """Main option 8: Generate personalized messages."""
    leads = _get_leads()
    if not leads:
        console.print("[yellow]No hay leads. Usa opcion 1 para buscar primero.[/yellow]")
        return

    qualified = [l for l in leads if l.is_qualified and not l.personalized_message]
    if not qualified:
        console.print("[yellow]No hay leads calificados sin mensaje. Filtra con AI primero.[/yellow]")
        return

    ollama_filter = OllamaGeminiFilter()
    if not ollama_filter.is_available():
        console.print("[red]Se necesita Ollama o Gemini para generar mensajes.[/red]")
        console.print("[dim]Instala Ollama o configura GEMINI_API_KEY en .env[/dim]")
        return

    console.print(f"\n[cyan]Generando mensajes para {len(qualified)} leads con {ollama_filter.get_backend_name()}...[/cyan]")

    generated = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Generando mensajes...", total=len(qualified))
        for lead in qualified:
            try:
                message = ollama_filter.generate_message(lead)
                if message:
                    generated += 1
                progress.update(task, advance=1, description=f"Generando mensajes... ({generated}/{len(qualified)})")
            except Exception as e:
                logger.error(f"Error generating message: {e}")

    console.print(f"[green]Mensajes generados: {generated}/{len(qualified)}[/green]")

    # Show sample
    sample = [l for l in qualified if l.personalized_message][:3]
    for lead in sample:
        console.print(Panel(
            f"[bold]{lead.company or lead.title}[/bold]\n\n{lead.personalized_message}",
            border_style="green"
        ))

    _store_leads(leads)


# ==================== 9. CONFIGURATION ====================

def menu_configuration():
    """Main option 9: View/edit configuration."""
    console.print("\n[bold cyan]═══ CONFIGURACION ═══[/bold cyan]\n")

    # Check AI backends
    console.print("[bold]Estado de AI:[/bold]")

    ollama_filter = OllamaGeminiFilter()
    if ollama_filter.ollama_available:
        console.print(f"  Ollama:    [green]Activo ({settings.ollama_model})[/green]")
    else:
        console.print("  Ollama:    [red]No disponible[/red] [dim](instala Ollama y ejecuta: ollama pull qwen2.5-coder:7b)[/dim]")

    console.print(f"  Gemini:    {'[green]Configurado[/green]' if settings.gemini_api_key else '[yellow]No configurado[/yellow] [dim](gratis: GEMINI_API_KEY en .env)[/dim]'}")
    console.print(f"  OpenAI:    {'[green]Configurado[/green]' if settings.openai_api_key else '[dim]No configurado[/dim]'}")
    console.print(f"  Anthropic: {'[green]Configurado[/green]' if settings.anthropic_api_key else '[dim]No configurado[/dim]'}")

    console.print(f"\n[bold]Estado de APIs:[/bold]")
    console.print(f"  HubSpot:   {'[green]Configurado[/green]' if settings.hubspot_api_key else '[red]No configurado[/red]'}")
    console.print(f"  Google:    {'[green]Configurado[/green]' if settings.google_api_key else '[yellow]No configurado[/yellow]'}")

    console.print(f"\n[bold]Fuentes disponibles (10):[/bold]")
    console.print("  Reddit, Hacker News, Google Search, Product Hunt,")
    console.print("  Google Maps, Yelp, Indeed, Yellow Pages, BBB, Craigslist")

    console.print(f"\n[bold]Nichos configurados:[/bold]")
    console.print(f"  {', '.join(settings.maps_niches)}")

    console.print(f"\n[bold]Ubicaciones:[/bold]")
    console.print(f"  {', '.join(settings.maps_locations)}")

    console.print(f"\n[bold]Keywords de dolor:[/bold]")
    for kw in settings.pain_keywords[:10]:
        console.print(f"  - {kw}")
    if len(settings.pain_keywords) > 10:
        console.print(f"  ... y {len(settings.pain_keywords) - 10} mas")

    console.print("\n[dim]Edita el archivo .env para cambiar la configuracion[/dim]")


# ==================== MAIN ====================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Lead Generation App v2.0")
    parser.add_argument("--scrape", action="store_true", help="Run scraping only")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--export", action="store_true", help="Scrape and export to CSV")
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
        if args.export:
            filepath = export_leads_to_csv(filtered)
            console.print(f"[green]Exported to: {filepath}[/green]")
        elif not args.no_interactive:
            send_to_hubspot(filtered)
        return

    if args.export:
        leads = run_scraping()
        filepath = export_leads_to_csv(leads)
        console.print(f"[green]Exported to: {filepath}[/green]")
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
                menu_view_leads()
            elif choice == "3":
                menu_update_lead()
            elif choice == "4":
                menu_statistics()
            elif choice == "5":
                menu_search()
            elif choice == "6":
                menu_export_csv()
            elif choice == "7":
                menu_extract_emails()
            elif choice == "8":
                menu_generate_messages()
            elif choice == "9":
                menu_configuration()

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Operacion cancelada[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            logger.exception("Unexpected error")


if __name__ == "__main__":
    main()
