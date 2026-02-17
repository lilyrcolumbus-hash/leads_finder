#!/usr/bin/env python3
"""Test script: scrape 5 real businesses, enrich emails, send to Google Sheet.

Usage:
    python test_sheets.py                           # Default: plumber in Miami FL
    python test_sheets.py dentist "Austin, TX"      # Custom industry + city
    python test_sheets.py electrician "Lima, OH" 25  # With radius in miles
"""

import sys
import time
from typing import List

from rich.console import Console
from rich.table import Table

from src.config import settings
from src.scrapers.google_maps_scraper import GoogleMapsScraper
from src.sheets.google_sheets import GoogleSheetsSync
from src.database.sqlite_db import LeadDatabase
from src.utils.models import Lead

console = Console()


def show_results_table(leads: List[Lead], title: str):
    """Display leads in a compact results table."""
    table = Table(title=title, show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Negocio", style="green", max_width=28)
    table.add_column("Telefono", style="cyan", width=16)
    table.add_column("Email", style="yellow", max_width=30)
    table.add_column("Website", style="blue", max_width=25)
    table.add_column("Rating", justify="center", width=6)
    table.add_column("Dolor", justify="center", width=6)

    for i, lead in enumerate(leads, 1):
        pain = "[red]SI[/red]" if lead.has_pain else "[green]NO[/green]"
        rating = f"{lead.rating:.1f}" if lead.rating else "-"
        website = (lead.website or "-")[:25]
        email = lead.email or "[dim]-[/dim]"
        table.add_row(
            str(i),
            (lead.company or lead.title or "")[:28],
            lead.phone or "-",
            email,
            website,
            rating,
            pain,
        )

    console.print(table)


def main():
    # Parse args
    business_type = sys.argv[1] if len(sys.argv) > 1 else "plumber"
    city = sys.argv[2] if len(sys.argv) > 2 else "Miami, FL"
    radius_miles = float(sys.argv[3]) if len(sys.argv) > 3 else None

    console.print("\n[bold cyan]═══ TEST: 5 Leads con Enriquecimiento de Emails ═══[/bold cyan]\n")
    console.print(f"  Industria: [bold]{business_type}[/bold]")
    console.print(f"  Ciudad:    [bold]{city}[/bold]")
    if radius_miles:
        console.print(f"  Radio:     [bold]{radius_miles} millas[/bold]")
    console.print()

    # ── Step 1: Check API keys ──────────────────────────────
    console.print("[bold]1. Verificando configuracion...[/bold]")
    api_key = settings.google_places_api_key or settings.google_api_key
    if not api_key:
        console.print("[red]  ERROR: No hay Google API key configurada[/red]")
        console.print("  Configura GOOGLE_PLACES_API_KEY o GOOGLE_API_KEY en .env")
        sys.exit(1)
    console.print(f"  Google Places API: [green]OK[/green]")

    sheets = GoogleSheetsSync()
    has_sheets = sheets.is_configured()
    console.print(f"  Google Sheets:     {'[green]OK[/green]' if has_sheets else '[yellow]No configurado[/yellow]'}")

    has_hunter = bool(settings.hunter_api_key)
    console.print(f"  Hunter.io:         {'[green]OK[/green]' if has_hunter else '[dim]No configurado (opcional)[/dim]'}")
    console.print()

    # ── Step 2: Scrape 5 businesses ─────────────────────────
    console.print("[bold]2. Buscando 5 negocios en Google Maps...[/bold]")
    start = time.time()

    try:
        with GoogleMapsScraper() as scraper:
            # Limit results to 5
            scraper.max_results = 5
            batch = scraper.scrape(
                location=city,
                category=business_type,
                radius_miles=radius_miles,
            )
    except Exception as e:
        console.print(f"[red]  Error: {e}[/red]")
        sys.exit(1)

    elapsed = time.time() - start
    leads = batch.leads[:5]  # extra safety: cap at 5

    if not leads:
        console.print("[yellow]  No se encontraron negocios.[/yellow]")
        if batch.errors:
            for err in batch.errors[:3]:
                console.print(f"  [red]{err}[/red]")
        sys.exit(1)

    console.print(f"  Encontrados: [green]{len(leads)}[/green] negocios ({elapsed:.1f}s)")

    # Show initial state (before enrichment)
    with_email = sum(1 for l in leads if l.email)
    with_website = sum(1 for l in leads if l.website)
    console.print(f"  Con email:   [cyan]{with_email}[/cyan]")
    console.print(f"  Con website: [cyan]{with_website}[/cyan]")
    console.print()

    # ── Step 3: Email enrichment pipeline ───────────────────
    console.print("[bold]3. Enriquecimiento de emails...[/bold]")

    # Step 3a: Website crawling (free)
    needs_crawl = [l for l in leads if l.website and not l.email]
    if needs_crawl:
        console.print(f"\n  [cyan]3a. Rastreando {len(needs_crawl)} websites...[/cyan]")
        from src.scrapers.base_scraper import BaseScraper

        class _Crawler(BaseScraper):
            source = leads[0].source
            def scrape(self):
                pass

        crawler = _Crawler()
        crawl_found = 0
        try:
            for lead in needs_crawl:
                try:
                    email = crawler.extract_email_from_website(lead.website)
                    if email:
                        lead.email = email
                        crawl_found += 1
                        console.print(f"    [green]{(lead.company or '')[:30]}[/green] -> {email}")
                    else:
                        console.print(f"    [dim]{(lead.company or '')[:30]}[/dim] -> no encontrado")
                except Exception:
                    console.print(f"    [dim]{(lead.company or '')[:30]}[/dim] -> error")
                time.sleep(0.3)
        finally:
            crawler.close()
        console.print(f"  Emails via website: [green]{crawl_found}[/green]")
    else:
        console.print("  [dim]3a. Todos los leads ya tienen email o no tienen website[/dim]")

    # Step 3b: Hunter.io (if configured)
    if has_hunter:
        needs_hunter = [l for l in leads if not l.email]
        if needs_hunter:
            console.print(f"\n  [cyan]3b. Buscando con Hunter.io ({len(needs_hunter)} leads)...[/cyan]")
            from src.enrichment.hunter import HunterClient
            hunter_found = 0
            with HunterClient() as hunter:
                for lead in needs_hunter:
                    try:
                        result = hunter.find_email_for_lead(
                            url=lead.website or lead.url,
                            company=lead.company,
                            name=lead.name,
                        )
                        if result:
                            lead.email = result.email
                            hunter_found += 1
                            console.print(f"    [green]{(lead.company or '')[:30]}[/green] -> {result.email} ({result.confidence}%)")
                        else:
                            console.print(f"    [dim]{(lead.company or '')[:30]}[/dim] -> no encontrado")
                    except Exception as e:
                        console.print(f"    [dim]{(lead.company or '')[:30]}[/dim] -> error")
            console.print(f"  Emails via Hunter: [green]{hunter_found}[/green]")
        else:
            console.print("  [dim]3b. Hunter.io: todos los leads ya tienen email[/dim]")

        # Step 3c: Verify emails
        with_email_now = [l for l in leads if l.email]
        if with_email_now:
            console.print(f"\n  [cyan]3c. Verificando {len(with_email_now)} emails...[/cyan]")
            from src.enrichment.hunter import HunterClient
            verified = 0
            invalid = 0
            with HunterClient() as hunter:
                for lead in with_email_now:
                    try:
                        result = hunter.verify_email(lead.email)
                        status = result.get("status", "unknown")
                        if status == "valid":
                            verified += 1
                        elif status in ("invalid", "disposable"):
                            console.print(f"    [red]{lead.email} -> INVALIDO ({status})[/red]")
                            lead.email = None
                            invalid += 1
                    except Exception:
                        pass
            console.print(f"  Verificados: [green]{verified}[/green] | Invalidos: [red]{invalid}[/red]")
    else:
        console.print("  [dim]3b. Hunter.io no configurado (omitido)[/dim]")
        console.print("  [dim]3c. Verificacion de emails omitida (requiere Hunter.io)[/dim]")

    console.print()

    # ── Step 4: Results ─────────────────────────────────────
    final_with_email = sum(1 for l in leads if l.email)
    console.print(f"[bold]4. Resultados finales: {final_with_email}/{len(leads)} leads con email[/bold]\n")
    show_results_table(leads, f"{business_type.title()} en {city}")

    # ── Step 5: Save to DB ──────────────────────────────────
    console.print("\n[bold]5. Guardando en base de datos local...[/bold]")
    db = LeadDatabase()
    result = db.save_leads(leads)
    console.print(f"  Guardados: [green]{result['saved']}[/green] nuevos, {result['duplicates']} duplicados")

    # ── Step 6: Send to Google Sheets ───────────────────────
    if has_sheets:
        console.print("\n[bold]6. Enviando a Google Sheets...[/bold]")
        check = sheets.verify_connection()
        if check["ok"]:
            console.print(f"  Conexion: [green]{check['message']}[/green]")
        else:
            console.print(f"  Conexion: [yellow]{check['message']}[/yellow]")

        try:
            result = sheets.send_leads(leads)
            if result["sent"] > 0:
                console.print(f"  [bold green]Enviados: {result['sent']} leads a Google Sheets![/bold green]")
            else:
                console.print(f"  [red]Fallidos: {result['failed']}[/red]")
        except Exception as e:
            console.print(f"  [red]Error: {e}[/red]")
        finally:
            sheets.client.close()
    else:
        console.print("\n[dim]6. Google Sheets no configurado (omitido)[/dim]")

    # ── Step 7: Export CSV (always works) ───────────────────
    csv_path = f"leads_{business_type}_{city.replace(', ', '_').replace(' ', '_')}.csv"
    console.print(f"\n[bold]7. Exportando CSV...[/bold]")
    import csv
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Negocio", "Email", "Telefono", "Website", "Direccion", "Rating", "Reviews", "Industria", "Dolor"])
        for lead in leads:
            writer.writerow([
                lead.company or lead.title or "",
                lead.email or "",
                lead.phone or "",
                lead.website or "",
                lead.address or lead.location or "",
                lead.rating or "",
                lead.review_count or "",
                lead.industry or lead.business_type or "",
                "SI" if lead.has_pain else "NO",
            ])
    console.print(f"  [bold green]CSV guardado: {csv_path}[/bold green]")

    # ── Summary ─────────────────────────────────────────────
    console.print(f"\n[bold cyan]{'═' * 50}[/bold cyan]")
    console.print(f"  Negocios encontrados:  [bold]{len(leads)}[/bold]")
    console.print(f"  Con telefono:          [bold]{sum(1 for l in leads if l.phone)}[/bold]")
    console.print(f"  Con email:             [bold]{final_with_email}[/bold]")
    console.print(f"  Con dolor detectado:   [bold]{sum(1 for l in leads if l.has_pain)}[/bold]")
    console.print(f"[bold cyan]{'═' * 50}[/bold cyan]\n")


if __name__ == "__main__":
    main()
