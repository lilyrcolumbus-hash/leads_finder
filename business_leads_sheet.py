#!/usr/bin/env python3
"""
Business Leads to Google Sheet

Busca negocios por industria y ciudad usando Google Maps/Places API
y los exporta a una Google Sheet con una pestana por cada industria.

Datos exportados:
- Nombre del negocio
- Email (prioridad)
- Telefono
- Direccion
- Website
- Rating y cantidad de reviews
- Pain score y resumen

Uso:
    # Modo interactivo
    python business_leads_sheet.py

    # Con argumentos
    python business_leads_sheet.py --industry "dentist" --location "Miami, FL"
    python business_leads_sheet.py --industry "plumber" --location "Houston, TX" --radius 10
    python business_leads_sheet.py --industry "lawyer" --location "Los Angeles, CA" --sheet "My Leads Sheet"

    # Multiples industrias de una vez
    python business_leads_sheet.py --industry "dentist,plumber,hvac" --location "Miami, FL"
"""

import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings
from src.utils.logger import setup_logger
from src.utils.models import Lead
from src.scrapers.google_maps_scraper import GoogleMapsScraper
from src.sheets.google_sheets import GoogleSheetsClient

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


def search_businesses(industry: str, location: str, radius: Optional[int] = None) -> List[Lead]:
    """
    Search for businesses of a given industry in a location.

    Args:
        industry: Type of business (e.g., "dentist", "plumber")
        location: City/state to search (e.g., "Miami, FL")
        radius: Optional search radius in miles (not directly supported by Places text search,
                but included in query for better targeting)

    Returns:
        List of Lead objects with business data
    """
    console.print(f"\n[cyan]Buscando [bold]{industry}[/bold] en [bold]{location}[/bold]...[/cyan]")

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
    industry: str,
    spreadsheet_name: str,
    share_email: Optional[str] = None,
) -> Optional[str]:
    """
    Write leads to Google Sheet.

    Args:
        leads: List of leads to write
        industry: Industry name (used as tab name)
        spreadsheet_name: Name of the Google Spreadsheet
        share_email: Optional email to share the sheet with

    Returns:
        URL of the spreadsheet, or None on failure
    """
    credentials_path = settings.google_sheets_credentials_path

    if not Path(credentials_path).exists():
        console.print(f"[red]Error: No se encontro el archivo de credenciales[/red]")
        console.print(f"[yellow]Ruta esperada: {credentials_path}[/yellow]")
        console.print(
            "\n[dim]Para configurar Google Sheets:\n"
            "1. Crea un Service Account en Google Cloud Console\n"
            "2. Habilita Google Sheets API y Google Drive API\n"
            "3. Descarga el JSON de credenciales\n"
            "4. Guardalo en: credentials/google_sheets_sa.json\n"
            "5. O configura GOOGLE_SHEETS_CREDENTIALS_PATH en .env[/dim]"
        )
        return None

    try:
        with GoogleSheetsClient(credentials_path) as sheets:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Escribiendo {len(leads)} negocios en la sheet...", total=None)

                result = sheets.write_leads_to_sheet(
                    spreadsheet_name=spreadsheet_name,
                    industry=industry,
                    leads=leads,
                )

                progress.update(task, completed=True)

            if result["rows_written"] > 0:
                console.print(f"\n[bold green]Sheet actualizada exitosamente![/bold green]")
                console.print(f"  Pestana: [cyan]{result['tab']}[/cyan]")
                console.print(f"  Filas escritas: [cyan]{result['rows_written']}[/cyan]")
                console.print(f"  Total en pestana: [cyan]{result['total_rows']}[/cyan]")
                console.print(f"\n  [bold]URL:[/bold] [link={result['spreadsheet_url']}]{result['spreadsheet_url']}[/link]")

                # Share if email provided
                if share_email:
                    try:
                        sheets.share_spreadsheet(spreadsheet_name, share_email)
                        console.print(f"  [green]Compartida con: {share_email}[/green]")
                    except Exception as e:
                        console.print(f"  [yellow]No se pudo compartir: {e}[/yellow]")

                return result["spreadsheet_url"]
            else:
                console.print("[yellow]No se escribieron filas[/yellow]")
                return None

    except Exception as e:
        console.print(f"[red]Error escribiendo a Google Sheets: {e}[/red]")
        logger.exception("Google Sheets write error")
        return None


def interactive_mode():
    """Run in interactive mode, asking the user for input."""
    display_banner()

    spreadsheet_name = settings.google_sheets_spreadsheet_name
    console.print(f"[dim]Sheet destino: {spreadsheet_name}[/dim]")
    console.print(f"[dim](Configura GOOGLE_SHEETS_SPREADSHEET_NAME en .env para cambiar)[/dim]\n")

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

        # Search businesses
        leads = search_businesses(industry, location)

        if not leads:
            console.print("[yellow]No se encontraron negocios. Intenta otra busqueda.[/yellow]")
            continue

        # Preview
        preview_leads(leads)

        # Write to sheet automatically
        tab_name = f"{industry.title()} - {location}"
        url = write_to_sheet(leads, tab_name, spreadsheet_name)

        # Continue?
        if not Confirm.ask("\nBuscar otra industria/ubicacion?", default=True):
            break

    console.print("\n[bold green]Hasta luego![/bold green]\n")


def cli_mode(args):
    """Run with CLI arguments."""
    display_banner()

    spreadsheet_name = args.sheet or settings.google_sheets_spreadsheet_name
    share_email = args.share or settings.google_sheets_share_email

    # Parse industries (comma-separated)
    industries = [i.strip() for i in args.industry.split(",")]

    for industry in industries:
        console.print(f"\n[bold]{'=' * 50}[/bold]")
        console.print(f"[bold cyan]Industria: {industry} | Ubicacion: {args.location}[/bold cyan]")
        console.print(f"[bold]{'=' * 50}[/bold]")

        leads = search_businesses(industry, args.location)

        if not leads:
            console.print(f"[yellow]No se encontraron negocios para '{industry}' en '{args.location}'[/yellow]")
            continue

        preview_leads(leads, max_rows=5)

        # Tab name
        tab_name = f"{industry.title()} - {args.location}"
        write_to_sheet(leads, tab_name, spreadsheet_name, share_email or None)

        # Small delay between industries
        if len(industries) > 1:
            time.sleep(1)

    console.print(f"\n[bold green]Proceso completado para {len(industries)} industria(s)[/bold green]\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Busca negocios por industria y los exporta a Google Sheets"
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
        help=f"Nombre de la Google Sheet (default: {settings.google_sheets_spreadsheet_name})"
    )
    parser.add_argument(
        "--share",
        help="Email para compartir la sheet"
    )

    args = parser.parse_args()

    # Load environment
    from dotenv import load_dotenv
    load_dotenv()

    if args.industry and args.location:
        cli_mode(args)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
