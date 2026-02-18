#!/usr/bin/env python3
"""
Business Leads to Google Sheet

Busca negocios por industria y ciudad y los inserta automaticamente
en tu Google Sheet. Soporta dos metodos:

  1. Apps Script (recomendado): Llama al deployment URL que busca en
     Google Places y escribe directo en la Sheet. Solo necesitas el URL.

  2. Python directo: Usa el scraper de Google Maps + gspread para
     buscar y escribir. Necesita Places API Key + Service Account JSON.

Uso:
    # Modo interactivo
    python business_leads_sheet.py

    # Con argumentos (automatico)
    python business_leads_sheet.py --industry "dentist" --location "Miami, FL"
    python business_leads_sheet.py --industry "plumber" --location "Houston, TX"

    # Multiples industrias de una vez (una pestana por cada una)
    python business_leads_sheet.py --industry "dentist,plumber,hvac" --location "Miami, FL"

    # Forzar metodo especifico
    python business_leads_sheet.py --method apps-script --industry "dentist" --location "Miami, FL"
    python business_leads_sheet.py --method python --industry "dentist" --location "Miami, FL"
"""

import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings
from src.utils.logger import setup_logger
from src.utils.models import Lead
from src.sheets.apps_script_client import AppsScriptClient

console = Console()
logger = setup_logger("business_leads_sheet")


def display_banner():
    """Display application banner."""
    banner = """
    ╔════════════════════════════════════════════════════╗
    ║       BUSINESS LEADS -> GOOGLE SHEET               ║
    ║   Busca negocios y exporta a Sheet por industria   ║
    ╚════════════════════════════════════════════════════╝
    """
    console.print(Panel(banner, style="bold blue"))


def get_available_method() -> str:
    """Determine which method is available for searching.

    Returns:
        "apps-script" if deployment URL is configured,
        "python" if Places API key + Sheet credentials are available,
        "none" if nothing is configured.
    """
    # Check Apps Script first (simpler setup)
    if settings.apps_script_deployment_url:
        return "apps-script"

    # Check Python path (needs API key + credentials + spreadsheet ID)
    has_api_key = bool(
        settings.google_places_api_key
        and settings.google_places_api_key != "TU_GOOGLE_PLACES_API_KEY_AQUI"
    )
    has_credentials = Path(settings.google_sheets_credentials_path).exists()
    has_spreadsheet = bool(settings.google_sheets_spreadsheet_id)

    if has_api_key and has_credentials and has_spreadsheet:
        return "python"

    return "none"


def show_config_status():
    """Display the current configuration status."""
    console.print("\n[bold]Estado de configuracion:[/bold]")

    # Apps Script
    has_apps_script = bool(settings.apps_script_deployment_url)
    status = "[green]Configurado[/green]" if has_apps_script else "[red]No configurado[/red]"
    console.print(f"  Apps Script URL: {status}")

    # Places API Key
    has_api_key = bool(
        settings.google_places_api_key
        and settings.google_places_api_key != "TU_GOOGLE_PLACES_API_KEY_AQUI"
    )
    status = "[green]Configurada[/green]" if has_api_key else "[red]No configurada[/red]"
    console.print(f"  Google Places API Key: {status}")

    # Service Account
    has_credentials = Path(settings.google_sheets_credentials_path).exists()
    status = "[green]Encontrado[/green]" if has_credentials else "[red]No encontrado[/red]"
    console.print(f"  Service Account JSON: {status}")

    # Spreadsheet ID
    has_spreadsheet = bool(settings.google_sheets_spreadsheet_id)
    status = "[green]Configurado[/green]" if has_spreadsheet else "[yellow]No configurado (Apps Script no lo necesita)[/yellow]"
    console.print(f"  Spreadsheet ID: {status}")

    console.print()


# ============================================================
# METODO 1: Apps Script (recomendado)
# ============================================================

def search_via_apps_script(
    industry: str,
    location: str,
    max_results: int = 60,
) -> Dict[str, Any]:
    """
    Search businesses via Apps Script deployment URL.

    The Apps Script handles everything: searches Places API, extracts
    details, writes to Sheet, and returns a summary.

    Args:
        industry: Type of business (e.g., "dentist", "plumber")
        location: City/state to search (e.g., "Miami, FL")
        max_results: Maximum businesses to process

    Returns:
        Dict with results from Apps Script
    """
    console.print(f"\n[cyan]Buscando [bold]{industry}[/bold] en [bold]{location}[/bold] via Apps Script...[/cyan]")

    with AppsScriptClient() as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"Buscando {industry} en {location} (puede tardar unos minutos)...",
                total=None,
            )

            result = client.search_businesses(
                industry=industry,
                location=location,
                max_results=max_results,
            )

            progress.update(task, completed=True)

    if result.get("status") == "error":
        console.print(f"[red]Error: {result.get('message', 'Unknown error')}[/red]")
        return result

    total = result.get("total_leads", 0)
    emails = result.get("with_email", 0)
    phones = result.get("with_phone", 0)
    pain = result.get("with_pain", 0)

    console.print(f"\n[bold green]Busqueda completada![/bold green]")
    console.print(f"  Negocios encontrados: [cyan]{total}[/cyan]")
    console.print(f"  Con email: [cyan]{emails}[/cyan]")
    console.print(f"  Con telefono: [cyan]{phones}[/cyan]")
    console.print(f"  Con pain points: [cyan]{pain}[/cyan]")

    if result.get("tab"):
        console.print(f"  Pestana: [cyan]{result['tab']}[/cyan]")

    if result.get("spreadsheet"):
        url = result["spreadsheet"]
        console.print(f"\n  [bold]Sheet:[/bold] [link={url}]{url}[/link]")

    # Show lead preview if available
    leads_data = result.get("leads", [])
    if leads_data:
        preview_leads_data(leads_data)

    return result


def preview_leads_data(leads_data: List[Dict], max_rows: int = 10):
    """Show a preview table of leads from Apps Script response."""
    table = Table(title="Preview de Negocios", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Negocio", style="green", max_width=30)
    table.add_column("Email", style="cyan", max_width=30)
    table.add_column("Telefono", style="yellow", max_width=15)
    table.add_column("Rating", justify="center", width=7)

    for i, lead in enumerate(leads_data[:max_rows], 1):
        table.add_row(
            str(i),
            str(lead.get("name", ""))[:30],
            lead.get("email") or "[dim]-[/dim]",
            lead.get("phone") or "[dim]-[/dim]",
            str(lead.get("rating", "-")),
        )

    console.print(table)

    if len(leads_data) > max_rows:
        console.print(f"[dim]... y {len(leads_data) - max_rows} negocios mas[/dim]")


# ============================================================
# METODO 2: Python scraper + gspread (fallback)
# ============================================================

def search_businesses(industry: str, location: str) -> List[Lead]:
    """
    Search for businesses using the Python Google Maps scraper.

    Args:
        industry: Type of business (e.g., "dentist", "plumber")
        location: City/state to search (e.g., "Miami, FL")

    Returns:
        List of Lead objects with business data
    """
    from src.scrapers.google_maps_scraper import GoogleMapsScraper

    console.print(f"\n[cyan]Buscando [bold]{industry}[/bold] en [bold]{location}[/bold] via Python scraper...[/cyan]")

    with GoogleMapsScraper() as scraper:
        leads = scraper._search_businesses(industry, location)

    # Sort leads: those with email first, then by rating
    leads.sort(key=lambda l: (
        0 if l.email else 1,
        -(l.rating or 0)
    ))

    email_count = sum(1 for l in leads if l.email)
    phone_count = sum(1 for l in leads if l.phone)

    console.print(f"[green]Encontrados: {len(leads)} negocios[/green]")
    console.print(f"  Con email: [cyan]{email_count}[/cyan]")
    console.print(f"  Con telefono: [cyan]{phone_count}[/cyan]")

    return leads


def preview_leads(leads: List[Lead], max_rows: int = 10):
    """Show a preview table of leads."""
    table = Table(title="Preview de Negocios Encontrados", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Negocio", style="green", max_width=30)
    table.add_column("Email", style="cyan", max_width=30)
    table.add_column("Telefono", style="yellow", max_width=15)
    table.add_column("Rating", justify="center", width=7)
    table.add_column("Reviews", justify="center", width=8)

    for i, lead in enumerate(leads[:max_rows], 1):
        table.add_row(
            str(i),
            (lead.title or lead.company or "")[:30],
            lead.email or "[dim]-[/dim]",
            lead.phone or "[dim]-[/dim]",
            f"{lead.rating:.1f}" if lead.rating else "-",
            str(lead.review_count) if lead.review_count else "-",
        )

    console.print(table)

    if len(leads) > max_rows:
        console.print(f"[dim]... y {len(leads) - max_rows} negocios mas[/dim]")


def write_to_sheet(
    leads: List[Lead],
    tab_name: str,
    spreadsheet_id: str,
) -> Optional[str]:
    """
    Write leads to an existing Google Sheet in a new tab (Python path).

    Args:
        leads: List of leads to write
        tab_name: Tab name for the worksheet (e.g., "Dentist - Miami, FL")
        spreadsheet_id: Google Sheets spreadsheet ID

    Returns:
        URL of the spreadsheet, or None on failure
    """
    from src.sheets.google_sheets import GoogleSheetsClient

    credentials_path = settings.google_sheets_credentials_path

    if not Path(credentials_path).exists():
        console.print(f"[red]Error: No se encontro el archivo de credenciales de Google[/red]")
        console.print(f"[yellow]Ruta esperada: {credentials_path}[/yellow]")
        console.print(
            "\n[dim]Para configurar:\n"
            "1. Google Cloud Console -> Crea proyecto (o usa uno existente)\n"
            "2. Habilita: Google Sheets API + Google Drive API\n"
            "3. Crea un Service Account -> Descarga el JSON\n"
            "4. Guarda el JSON en: credentials/google_sheets_sa.json\n"
            "5. En tu Google Sheet -> Compartir con el email del service account\n"
            "6. Pon el ID de la sheet en .env: GOOGLE_SHEETS_SPREADSHEET_ID=...[/dim]"
        )
        return None

    if not spreadsheet_id:
        console.print("[red]Error: No se configuro GOOGLE_SHEETS_SPREADSHEET_ID en .env[/red]")
        console.print("[yellow]Copia el ID de tu sheet desde la URL:[/yellow]")
        console.print("[dim]https://docs.google.com/spreadsheets/d/[bold]ESTE_ES_EL_ID[/bold]/edit[/dim]")
        return None

    try:
        with GoogleSheetsClient(credentials_path) as sheets:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Escribiendo {len(leads)} negocios en la sheet...", total=None)

                result = sheets.write_leads_to_tab(
                    spreadsheet_id=spreadsheet_id,
                    tab_name=tab_name,
                    leads=leads,
                )

                progress.update(task, completed=True)

            if result["rows_written"] > 0:
                console.print(f"\n[bold green]Sheet actualizada![/bold green]")
                console.print(f"  Pestana: [cyan]{result['tab']}[/cyan]")
                console.print(f"  Filas escritas: [cyan]{result['rows_written']}[/cyan]")
                console.print(f"  Total en pestana: [cyan]{result['total_rows']}[/cyan]")
                console.print(f"\n  [bold]URL:[/bold] [link={result['spreadsheet_url']}]{result['spreadsheet_url']}[/link]")
                return result["spreadsheet_url"]
            else:
                console.print("[yellow]No se escribieron filas[/yellow]")
                return None

    except Exception as e:
        console.print(f"[red]Error escribiendo a Google Sheets: {e}[/red]")
        logger.exception("Google Sheets write error")
        return None


# ============================================================
# MODOS DE EJECUCION
# ============================================================

def interactive_mode(force_method: Optional[str] = None):
    """Run in interactive mode, asking the user for input."""
    display_banner()

    method = force_method or get_available_method()

    if method == "none":
        show_config_status()
        console.print("[red]No hay metodo configurado para buscar negocios.[/red]")
        console.print(
            "\n[yellow]Opcion 1 (recomendada): Configura APPS_SCRIPT_DEPLOYMENT_URL en .env[/yellow]"
            "\n[yellow]Opcion 2: Configura GOOGLE_PLACES_API_KEY + Service Account JSON[/yellow]"
        )
        return

    if method == "apps-script":
        console.print("[dim]Metodo: Apps Script (busca y escribe directo en la Sheet)[/dim]")
    else:
        console.print("[dim]Metodo: Python scraper + gspread[/dim]")
        spreadsheet_id = settings.google_sheets_spreadsheet_id
        if not spreadsheet_id:
            console.print("[red]Falta GOOGLE_SHEETS_SPREADSHEET_ID en .env[/red]")
            return
        console.print(f"[dim]Sheet destino ID: {spreadsheet_id[:20]}...[/dim]")

    while True:
        console.print("\n[bold cyan]--- Nueva Busqueda ---[/bold cyan]")

        # Get industry
        console.print("\n[bold]Industrias disponibles:[/bold]")
        for i, btype in enumerate(settings.google_maps_business_types, 1):
            console.print(f"  [{i}] {btype}")
        console.print(f"  [0] Escribir manualmente")

        industry_choice = Prompt.ask(
            "Selecciona industria",
            default="0"
        )

        if industry_choice.isdigit() and 1 <= int(industry_choice) <= len(settings.google_maps_business_types):
            industry = settings.google_maps_business_types[int(industry_choice) - 1]
        else:
            industry = Prompt.ask("Escribe la industria (ej: dentist, plumber, lawyer)")

        if not industry:
            console.print("[yellow]Industria no puede estar vacia[/yellow]")
            continue

        # Get location
        console.print("\n[bold]Ubicaciones guardadas:[/bold]")
        for i, loc in enumerate(settings.google_maps_locations, 1):
            console.print(f"  [{i}] {loc}")
        console.print(f"  [0] Escribir manualmente")

        location_choice = Prompt.ask(
            "Selecciona ubicacion",
            default="0"
        )

        if location_choice.isdigit() and 1 <= int(location_choice) <= len(settings.google_maps_locations):
            location = settings.google_maps_locations[int(location_choice) - 1]
        else:
            location = Prompt.ask("Escribe la ciudad/estado (ej: Miami, FL)")

        if not location:
            console.print("[yellow]Ubicacion no puede estar vacia[/yellow]")
            continue

        # Execute search based on method
        if method == "apps-script":
            search_via_apps_script(industry, location)
        else:
            leads = search_businesses(industry, location)
            if not leads:
                console.print("[yellow]No se encontraron negocios. Intenta otra busqueda.[/yellow]")
                continue
            preview_leads(leads)
            tab_name = f"{industry.title()} - {location}"
            write_to_sheet(leads, tab_name, settings.google_sheets_spreadsheet_id)

        # Continue?
        if not Confirm.ask("\nBuscar otra industria/ubicacion?", default=True):
            break

    console.print("\n[bold green]Hasta luego![/bold green]\n")


def cli_mode(args):
    """Run with CLI arguments - fully automatic."""
    display_banner()

    method = args.method or get_available_method()

    if method == "none":
        show_config_status()
        console.print("[red]Error: No hay metodo configurado.[/red]")
        return

    console.print(f"[dim]Metodo: {method}[/dim]")

    # Parse industries (comma-separated)
    industries = [i.strip() for i in args.industry.split(",")]

    for industry in industries:
        console.print(f"\n[bold]{'=' * 50}[/bold]")
        console.print(f"[bold cyan]Industria: {industry} | Ubicacion: {args.location}[/bold cyan]")
        console.print(f"[bold]{'=' * 50}[/bold]")

        if method == "apps-script":
            result = search_via_apps_script(industry, args.location)
            if result.get("status") == "error":
                console.print(f"[yellow]Error buscando '{industry}': {result.get('message')}[/yellow]")
        else:
            spreadsheet_id = args.sheet or settings.google_sheets_spreadsheet_id
            if not spreadsheet_id:
                console.print("[red]Error: Falta el ID de la sheet para el metodo Python[/red]")
                return

            leads = search_businesses(industry, args.location)
            if not leads:
                console.print(f"[yellow]No se encontraron negocios para '{industry}' en '{args.location}'[/yellow]")
                continue

            preview_leads(leads, max_rows=5)
            tab_name = f"{industry.title()} - {args.location}"
            write_to_sheet(leads, tab_name, spreadsheet_id)

        # Small delay between industries
        if len(industries) > 1:
            time.sleep(1)

    console.print(f"\n[bold green]Proceso completado para {len(industries)} industria(s)[/bold green]\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Busca negocios por industria y los inserta en tu Google Sheet"
    )
    parser.add_argument(
        "--industry", "-i",
        help="Industria a buscar (ej: 'dentist'). Multiples separadas por coma: 'dentist,plumber'"
    )
    parser.add_argument(
        "--location", "-l",
        help="Ciudad/estado (ej: 'Miami, FL')"
    )
    parser.add_argument(
        "--sheet", "-s",
        help="ID de la Google Sheet (o URL completa)"
    )
    parser.add_argument(
        "--method", "-m",
        choices=["apps-script", "python"],
        help="Metodo de busqueda: 'apps-script' (recomendado) o 'python' (local)"
    )

    args = parser.parse_args()

    # Load environment
    from dotenv import load_dotenv
    load_dotenv()

    if args.industry and args.location:
        cli_mode(args)
    else:
        interactive_mode(force_method=args.method)


if __name__ == "__main__":
    main()
