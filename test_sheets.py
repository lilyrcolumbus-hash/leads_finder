"""Test script for Google Sheets integration.

Run this locally to verify the Google Sheets webhook is working:
    python test_sheets.py
"""

import sys
from datetime import datetime

from src.config import settings
from src.sheets.google_sheets import GoogleSheetsSync
from src.utils.models import Lead, LeadSource


def create_test_lead() -> Lead:
    """Create a sample lead for testing the Sheets connection."""
    return Lead(
        id="test_sheets_001",
        source=LeadSource.GOOGLE_MAPS,
        title="Plomeria Express Miami",
        content="Negocio de plomeria con problemas de comunicacion detectados en reviews",
        url="https://maps.google.com/?cid=test123",
        keywords_matched=["phone", "calls", "customers"],
        urgency_keywords_matched=["frustrated"],
        pain_reviews=["Never answers the phone", "Called 3 times, no response"],
        tags=["plumbing", "miami", "test"],
        # Contact info
        name="Plomeria Express Miami",
        company="Plomeria Express",
        email="test@plomeriaexpress.com",
        phone="+1-305-555-0199",
        website="https://plomeriaexpress.example.com",
        address="123 Main St, Miami, FL 33101",
        # Business details
        industry="Plumbing",
        business_type="plumber",
        rating=3.2,
        review_count=47,
        # Pain detection
        has_pain=True,
        pain_score=78.0,
        pain_summary="Multiple reviews mention unanswered calls and poor communication",
        # AI Analysis
        ai_score=0.85,
        ai_reasoning="High pain - communication issues detected in reviews",
        is_qualified=True,
        has_explicit_pain=True,
        # Gemini Analysis
        has_website=True,
        has_social_media=False,
        software_needs="CRM, Call management, Online scheduling",
        gemini_analysis="Business lacks modern communication tools",
        # Timestamp
        found_at=datetime.now(),
    )


def main():
    print("=" * 60)
    print("  TEST DE CONEXION - Google Sheets")
    print("=" * 60)
    print()

    # Check configuration
    webhook_url = settings.google_sheets_webhook_url
    if not webhook_url:
        print("ERROR: GOOGLE_SHEETS_WEBHOOK_URL no esta configurada en .env")
        print("Agrega la URL del Apps Script desplegado a tu archivo .env")
        sys.exit(1)

    print(f"Webhook URL: {webhook_url[:60]}...")
    print()

    # Initialize sync
    sheets = GoogleSheetsSync()

    # Step 1: Verify connection (GET request)
    print("[1/3] Verificando conexion (GET health check)...")
    result = sheets.verify_connection()
    if result["ok"]:
        print(f"  OK: {result['message']}")
    else:
        print(f"  FALLO: {result['message']}")
        print()
        print("  Posibles causas:")
        print("  - El Apps Script no esta desplegado como Web App")
        print("  - El acceso no esta configurado como 'Anyone'")
        print("  - El Deployment ID es incorrecto")
        print("  - Necesitas re-desplegar despues de cambiar el codigo")
        print()
        print("  Quieres intentar enviar un lead de prueba de todas formas? (s/n)")
        resp = input("  > ").strip().lower()
        if resp != "s":
            sheets.client.close()
            sys.exit(1)

    print()

    # Step 2: Send test lead
    print("[2/3] Enviando lead de prueba...")
    test_lead = create_test_lead()

    try:
        result = sheets.send_leads([test_lead])
        print(f"  Resultado: enviados={result['sent']}, fallidos={result['failed']}")
    except Exception as e:
        print(f"  ERROR al enviar: {e}")
        sheets.client.close()
        sys.exit(1)

    print()

    # Step 3: Stats
    print("[3/3] Estadisticas de sync:")
    stats = sheets.get_stats()
    print(f"  Total enviados: {stats['total_sent']}")
    print(f"  Total fallidos: {stats['total_failed']}")
    print(f"  En buffer: {stats['buffered']}")

    sheets.client.close()

    print()
    print("=" * 60)
    if result["sent"] > 0:
        print("  EXITO! Revisa tu Google Sheet para ver el lead de prueba.")
        print("  Columnas esperadas:")
        print("  Nombre | Email | Telefono | Empresa | Website | Direccion |")
        print("  Industria | Rating | Fuente | URL | Pain Score | AI Score |")
        print("  Software Needs | Gemini Analysis | Has Website | Has Social Media | Fecha")
    else:
        print("  FALLO - No se pudo enviar el lead de prueba.")
        print("  Revisa la configuracion del Apps Script (ver instrucciones abajo).")
    print("=" * 60)


if __name__ == "__main__":
    main()
