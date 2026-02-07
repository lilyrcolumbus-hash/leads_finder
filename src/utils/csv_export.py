"""CSV export utility for leads."""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import List

from src.config import settings
from src.utils.logger import get_logger
from src.utils.models import Lead

logger = get_logger("CSVExport")


def export_leads_to_csv(leads: List[Lead], filename: str = None) -> str:
    """
    Export leads to a CSV file.

    Args:
        leads: List of leads to export
        filename: Optional custom filename

    Returns:
        Path to the exported CSV file
    """
    if not leads:
        raise ValueError("No leads to export")

    # Create export directory
    export_dir = Path(settings.csv_export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leads_{timestamp}.csv"

    filepath = export_dir / filename

    # CSV columns
    fieldnames = [
        "id",
        "source",
        "company",
        "name",
        "email",
        "phone",
        "website",
        "address",
        "niche",
        "location",
        "title",
        "content",
        "url",
        "ai_score",
        "is_qualified",
        "ai_reasoning",
        "personalized_message",
        "keywords_matched",
        "found_at",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for lead in leads:
            writer.writerow({
                "id": lead.id,
                "source": lead.source.value,
                "company": lead.company or "",
                "name": lead.name or "",
                "email": lead.email or "",
                "phone": lead.phone or "",
                "website": lead.website or "",
                "address": lead.address or "",
                "niche": lead.niche or "",
                "location": lead.location or "",
                "title": lead.title,
                "content": lead.content[:500],
                "url": lead.url,
                "ai_score": f"{lead.ai_score:.2f}" if lead.ai_score else "",
                "is_qualified": lead.is_qualified,
                "ai_reasoning": lead.ai_reasoning or "",
                "personalized_message": lead.personalized_message or "",
                "keywords_matched": "; ".join(lead.keywords_matched),
                "found_at": lead.found_at.isoformat(),
            })

    logger.info(f"Exported {len(leads)} leads to {filepath}")
    return str(filepath)


def export_leads_for_google_sheets(leads: List[Lead], filename: str = None) -> str:
    """
    Export leads in a format optimized for Google Sheets import.
    Uses tab-separated values for easier pasting.

    Args:
        leads: List of leads to export
        filename: Optional custom filename

    Returns:
        Path to the exported file
    """
    if not leads:
        raise ValueError("No leads to export")

    export_dir = Path(settings.csv_export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leads_gsheets_{timestamp}.tsv"

    filepath = export_dir / filename

    # Simplified columns for Google Sheets
    fieldnames = [
        "Company",
        "Email",
        "Phone",
        "Website",
        "Location",
        "Niche",
        "Score",
        "Qualified",
        "Source",
        "Message",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()

        for lead in leads:
            writer.writerow({
                "Company": lead.company or lead.title[:50],
                "Email": lead.email or "",
                "Phone": lead.phone or "",
                "Website": lead.website or "",
                "Location": lead.location or "",
                "Niche": lead.niche or "",
                "Score": f"{lead.ai_score:.0%}" if lead.ai_score else "",
                "Qualified": "Yes" if lead.is_qualified else "No",
                "Source": lead.source.value,
                "Message": lead.personalized_message or "",
            })

    logger.info(f"Exported {len(leads)} leads for Google Sheets to {filepath}")
    return str(filepath)
