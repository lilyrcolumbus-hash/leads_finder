#!/usr/bin/env python3
"""
Lead Generation App - Web Interface (Streamlit)
Optimized for mobile and desktop
v2.0 - 10 sources, Ollama/Gemini AI, CSV export

Run with: streamlit run web_app.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings
from src.utils.logger import setup_logger
from src.utils.models import Lead, LeadSource
from src.scrapers import (
    RedditScraper, HackerNewsScraper, GoogleScraper, ProductHuntScraper,
    GoogleMapsScraper, YelpScraper, IndeedScraper, YellowPagesScraper,
    BBBScraper, CraigslistScraper, EmailExtractor,
)
from src.filters import AILeadFilter, OllamaGeminiFilter
from src.crm import HubSpotCRM, LeadStage
from src.utils.csv_export import export_leads_to_csv, export_leads_for_google_sheets

# Page config
st.set_page_config(
    page_title="Lead Generation v2.0",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Mobile-optimized CSS
st.markdown("""
<style>
    .stApp { max-width: 100%; }
    @media (max-width: 768px) {
        .stApp { padding: 0.5rem; }
        .stButton > button { width: 100% !important; min-height: 3rem !important; font-size: 1.1rem !important; margin: 0.5rem 0 !important; }
        .stCheckbox { padding: 0.75rem 0 !important; }
        .stCheckbox label { font-size: 1.1rem !important; }
        [data-testid="metric-container"] { padding: 0.75rem !important; margin: 0.25rem 0 !important; }
        [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
        .streamlit-expanderHeader { font-size: 1rem !important; padding: 1rem !important; }
        [data-testid="stSidebar"] { min-width: 280px !important; }
        .stTabs [data-baseweb="tab"] { padding: 0.75rem 1rem !important; font-size: 1rem !important; }
        h1 { font-size: 1.75rem !important; }
        h2 { font-size: 1.5rem !important; }
        h3 { font-size: 1.25rem !important; }
    }
    .main-header { font-size: 1.75rem; font-weight: bold; color: #1f77b4; text-align: center; margin-bottom: 1.5rem; padding: 1rem; }
    .lead-card { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 1rem; margin: 0.75rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .status-badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.875rem; font-weight: 500; }
    .status-success { background-color: #d4edda; color: #155724; }
    .status-warning { background-color: #fff3cd; color: #856404; }
    input, select, textarea { font-size: 16px !important; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'leads' not in st.session_state:
    st.session_state.leads = []
if 'filtered_leads' not in st.session_state:
    st.session_state.filtered_leads = []
if 'scraping_done' not in st.session_state:
    st.session_state.scraping_done = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = "inicio"


def main():
    """Main app entry point."""

    with st.sidebar:
        st.markdown("## 🎯 LeadGen v2.0")
        st.markdown("---")

        if st.button("🏠 Inicio", use_container_width=True):
            st.session_state.current_page = "inicio"
            st.rerun()
        if st.button("🔍 Buscar Leads", use_container_width=True):
            st.session_state.current_page = "buscar"
            st.rerun()
        if st.button("📋 Mis Leads", use_container_width=True):
            st.session_state.current_page = "leads"
            st.rerun()
        if st.button("📧 Extraer Emails", use_container_width=True):
            st.session_state.current_page = "emails"
            st.rerun()
        if st.button("✉️ Mensajes AI", use_container_width=True):
            st.session_state.current_page = "messages"
            st.rerun()
        if st.button("📊 Estadísticas", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()
        if st.button("💾 Exportar CSV", use_container_width=True):
            st.session_state.current_page = "export"
            st.rerun()
        if st.button("⚙️ Configuración", use_container_width=True):
            st.session_state.current_page = "config"
            st.rerun()

        st.markdown("---")
        st.caption("v2.0 | 10 Fuentes | Ollama/Gemini AI")

    page = st.session_state.current_page

    if page == "inicio":
        show_home()
    elif page == "buscar":
        show_search()
    elif page == "leads":
        show_leads()
    elif page == "emails":
        show_email_extraction()
    elif page == "messages":
        show_message_generation()
    elif page == "stats":
        show_statistics()
    elif page == "export":
        show_export()
    elif page == "config":
        show_config()


def show_home():
    """Home page."""
    st.markdown('<h1 class="main-header">🎯 Lead Generation App v2.0</h1>', unsafe_allow_html=True)
    st.markdown("### Encuentra leads de 10 fuentes diferentes")

    sources = [
        ("📱 Reddit", "Subreddits de negocios"),
        ("💻 Hacker News", "Discusiones de startups"),
        ("🔍 Google Search", "Búsquedas específicas"),
        ("🚀 Product Hunt", "Founders activos"),
        ("📍 Google Maps", "Negocios locales por nicho"),
        ("⭐ Yelp", "Directorios de negocios"),
        ("💼 Indeed", "Empresas contratando"),
        ("📒 Yellow Pages", "Páginas amarillas"),
        ("🏢 BBB", "Better Business Bureau"),
        ("📰 Craigslist", "Servicios y empleos"),
    ]

    col1, col2 = st.columns(2)
    for i, (icon_name, desc) in enumerate(sources):
        target = col1 if i % 2 == 0 else col2
        with target:
            st.markdown(f"""
            <div class="lead-card">
                <strong>{icon_name}</strong><br>
                <small>{desc}</small>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Leads", len(st.session_state.leads))
    with col2:
        st.metric("Calificados", len(st.session_state.filtered_leads))
    with col3:
        emails = sum(1 for l in st.session_state.leads if l.email)
        st.metric("Con Email", emails)

    st.markdown("---")

    if st.button("🚀 Comenzar Búsqueda", type="primary", use_container_width=True):
        st.session_state.current_page = "buscar"
        st.rerun()


def show_search():
    """Search for new leads."""
    st.header("🔍 Buscar Leads")

    st.markdown("### Grupos de fuentes")
    source_group = st.radio(
        "Selecciona grupo",
        ["Todas (10)", "Foros", "Directorios", "Empleo", "Manual"],
        horizontal=True
    )

    scrapers = []

    if source_group == "Todas (10)":
        scrapers = [
            ("Reddit", RedditScraper), ("Hacker News", HackerNewsScraper),
            ("Google Search", GoogleScraper), ("Product Hunt", ProductHuntScraper),
            ("Google Maps", GoogleMapsScraper), ("Yelp", YelpScraper),
            ("Indeed", IndeedScraper), ("Yellow Pages", YellowPagesScraper),
            ("BBB", BBBScraper), ("Craigslist", CraigslistScraper),
        ]
    elif source_group == "Foros":
        scrapers = [
            ("Reddit", RedditScraper), ("Hacker News", HackerNewsScraper),
            ("Product Hunt", ProductHuntScraper),
        ]
    elif source_group == "Directorios":
        scrapers = [
            ("Google Maps", GoogleMapsScraper), ("Yelp", YelpScraper),
            ("Yellow Pages", YellowPagesScraper), ("BBB", BBBScraper),
        ]
    elif source_group == "Empleo":
        scrapers = [("Indeed", IndeedScraper), ("Craigslist", CraigslistScraper)]
    else:
        st.markdown("### Selecciona fuentes")
        all_sources = {
            "Reddit": RedditScraper, "Hacker News": HackerNewsScraper,
            "Google Search": GoogleScraper, "Product Hunt": ProductHuntScraper,
            "Google Maps": GoogleMapsScraper, "Yelp": YelpScraper,
            "Indeed": IndeedScraper, "Yellow Pages": YellowPagesScraper,
            "BBB": BBBScraper, "Craigslist": CraigslistScraper,
        }
        for name, cls in all_sources.items():
            if st.checkbox(name, value=True):
                scrapers.append((name, cls))

    st.markdown("---")

    # AI options
    st.markdown("### AI Filtering")
    ollama_filter = OllamaGeminiFilter()
    ai_backend = "none"

    ai_options = ["Sin AI"]
    if ollama_filter.ollama_available:
        ai_options.append(f"Ollama ({settings.ollama_model})")
    if ollama_filter.gemini_available:
        ai_options.append("Gemini (gratis)")
    if settings.openai_api_key:
        ai_options.append("OpenAI (pago)")
    if settings.anthropic_api_key:
        ai_options.append("Anthropic (pago)")

    ai_choice = st.selectbox("Motor de AI", ai_options, index=1 if len(ai_options) > 1 else 0)
    if "Ollama" in ai_choice:
        ai_backend = "ollama"
    elif "Gemini" in ai_choice:
        ai_backend = "gemini"
    elif "OpenAI" in ai_choice:
        ai_backend = "openai"
    elif "Anthropic" in ai_choice:
        ai_backend = "anthropic"

    st.markdown("")

    if st.button("🚀 INICIAR BÚSQUEDA", type="primary", use_container_width=True):
        if not scrapers:
            st.warning("⚠️ Selecciona al menos una fuente")
            return

        all_leads = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()

        for i, (name, ScraperClass) in enumerate(scrapers):
            status_text.text(f"🔄 Buscando en {name}...")
            try:
                with ScraperClass() as scraper:
                    batch = scraper.scrape()
                    all_leads.extend(batch.leads)
                    with results_container:
                        st.success(f"✅ {name}: {len(batch.leads)} leads")
            except Exception as e:
                with results_container:
                    st.warning(f"⚠️ {name}: {str(e)[:50]}")
            progress_bar.progress((i + 1) / len(scrapers))

        st.session_state.leads = all_leads

        # AI Filtering
        if ai_backend != "none" and all_leads:
            status_text.text("🤖 Filtrando con AI...")
            try:
                if ai_backend in ("ollama", "gemini"):
                    filtered = ollama_filter.filter_leads(all_leads)
                else:
                    ai_filter = AILeadFilter()
                    filtered = ai_filter.filter_leads(all_leads)
                qualified = [l for l in filtered if l.is_qualified]
                st.session_state.filtered_leads = qualified
                with results_container:
                    st.success(f"🤖 AI: {len(qualified)}/{len(all_leads)} calificados")
            except Exception:
                st.session_state.filtered_leads = all_leads
        else:
            st.session_state.filtered_leads = all_leads

        st.session_state.scraping_done = True
        progress_bar.progress(1.0)
        status_text.text(f"✅ ¡Listo! {len(all_leads)} leads encontrados")

    # Show results
    if st.session_state.scraping_done and st.session_state.filtered_leads:
        st.markdown("---")
        st.subheader(f"📋 Resultados ({len(st.session_state.filtered_leads)})")

        for lead in st.session_state.filtered_leads[:15]:
            title_short = lead.title[:50] + "..." if len(lead.title) > 50 else lead.title
            with st.expander(f"📌 {title_short}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Fuente:** {lead.source.value}")
                    st.markdown(f"**Empresa:** {lead.company or '-'}")
                    st.markdown(f"**Email:** {lead.email or '-'}")
                with col2:
                    st.markdown(f"**Teléfono:** {lead.phone or '-'}")
                    st.markdown(f"**Ubicación:** {lead.location or '-'}")
                    if lead.ai_score:
                        st.markdown(f"**Score AI:** {int(lead.ai_score * 100)}%")
                if lead.website:
                    st.markdown(f"**Web:** {lead.website}")
                st.markdown(f"**URL:** [{lead.url[:40]}...]({lead.url})")


def show_leads():
    """Show and manage leads."""
    st.header("📋 Mis Leads")

    tab1, tab2 = st.tabs(["📱 Locales", "☁️ HubSpot"])

    with tab1:
        if not st.session_state.filtered_leads:
            st.info("📭 No hay leads. Ve a 'Buscar Leads' para encontrar prospectos.")
            if st.button("🔍 Ir a Buscar", use_container_width=True):
                st.session_state.current_page = "buscar"
                st.rerun()
        else:
            leads = st.session_state.filtered_leads
            st.markdown(f"**Total:** {len(leads)} leads")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Con Email", sum(1 for l in leads if l.email))
            with col2:
                st.metric("Con Teléfono", sum(1 for l in leads if l.phone))
            with col3:
                st.metric("Con Web", sum(1 for l in leads if l.website))

            for i, lead in enumerate(leads[:20]):
                company = (lead.company or lead.title)[:40]
                parts = []
                if lead.email:
                    parts.append(f"📧 {lead.email}")
                if lead.phone:
                    parts.append(f"📞 {lead.phone}")
                if lead.location:
                    parts.append(f"📍 {lead.location}")
                info = " | ".join(parts) if parts else "Sin datos de contacto"

                st.markdown(f"""
                <div class="lead-card">
                    <strong>#{i+1} {company}</strong><br>
                    <small>🏷️ {lead.source.value} | {info}</small>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📤 ENVIAR A HUBSPOT", type="primary", use_container_width=True):
                    with HubSpotCRM() as crm:
                        if not crm.is_configured():
                            st.error("❌ HubSpot no configurado")
                        else:
                            with st.spinner("Enviando..."):
                                results = crm.send_leads_to_crm(leads)
                            st.success(f"✅ Enviados: {results['created']}")
            with col2:
                if st.button("💾 EXPORTAR CSV", use_container_width=True):
                    st.session_state.current_page = "export"
                    st.rerun()

    with tab2:
        with HubSpotCRM() as crm:
            if not crm.is_configured():
                st.warning("⚠️ Configura HUBSPOT_API_KEY en .env")
            else:
                stage_filter = st.selectbox("Filtrar por etapa", ["Todos"] + [s.value for s in LeadStage])
                if st.button("🔄 Cargar de HubSpot", use_container_width=True):
                    with st.spinner("Cargando..."):
                        if stage_filter == "Todos":
                            contacts = crm.get_all_contacts()
                        else:
                            contacts = crm.get_contacts_by_stage(LeadStage(stage_filter))
                    if contacts:
                        for c in contacts[:15]:
                            name = f"{c.firstname or ''} {c.lastname or ''}".strip() or "Sin nombre"
                            st.markdown(f"""
                            <div class="lead-card">
                                <strong>{name}</strong><br>
                                📧 {c.email or '-'} | 🏢 {c.company or '-'}<br>
                                <span class="status-badge status-success">{c.lead_stage.value}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No hay contactos")


def show_email_extraction():
    """Email extraction page."""
    st.header("📧 Extraer Emails de Websites")

    leads = st.session_state.leads
    if not leads:
        st.info("📭 No hay leads. Busca leads primero.")
        if st.button("🔍 Ir a Buscar", use_container_width=True):
            st.session_state.current_page = "buscar"
            st.rerun()
        return

    websites = [l for l in leads if l.website and not l.email]
    already_have = sum(1 for l in leads if l.email)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Sitios web pendientes", len(websites))
    with col2:
        st.metric("Ya tienen email", already_have)

    if not websites:
        st.success("✅ No hay sitios web pendientes.")
        return

    st.markdown("---")

    if st.button("🚀 EXTRAER EMAILS", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status = st.empty()

        with EmailExtractor() as extractor:
            found = 0
            for i, lead in enumerate(websites):
                status.text(f"🔄 Extrayendo de {lead.website[:40]}...")
                try:
                    emails = extractor.extract_from_website(lead.website)
                    if emails:
                        lead.email = emails[0]
                        found += 1
                except Exception:
                    pass
                progress_bar.progress((i + 1) / len(websites))

        progress_bar.progress(1.0)
        status.text(f"✅ ¡Listo! {found} emails encontrados de {len(websites)} sitios")
        st.session_state.leads = leads
        st.session_state.filtered_leads = [l for l in leads if l.is_qualified] or leads


def show_message_generation():
    """AI message generation page."""
    st.header("✉️ Generar Mensajes Personalizados")

    leads = st.session_state.filtered_leads
    if not leads:
        st.info("📭 No hay leads calificados. Busca y filtra leads primero.")
        return

    without_msg = [l for l in leads if not l.personalized_message]
    with_msg = [l for l in leads if l.personalized_message]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Sin mensaje", len(without_msg))
    with col2:
        st.metric("Con mensaje", len(with_msg))

    ollama_filter = OllamaGeminiFilter()
    if not ollama_filter.is_available():
        st.error("❌ Se necesita Ollama o Gemini para generar mensajes.")
        st.info("Instala Ollama o configura GEMINI_API_KEY en .env")
        return

    st.info(f"🤖 Usando: {ollama_filter.get_backend_name()}")

    if without_msg and st.button("🚀 GENERAR MENSAJES", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status = st.empty()
        generated = 0
        total = min(len(without_msg), 20)

        for i, lead in enumerate(without_msg[:20]):
            status.text(f"🔄 Generando para {(lead.company or lead.title)[:30]}...")
            try:
                msg = ollama_filter.generate_message(lead)
                if msg:
                    generated += 1
            except Exception:
                pass
            progress_bar.progress((i + 1) / total)

        progress_bar.progress(1.0)
        status.text(f"✅ {generated} mensajes generados")
        st.session_state.filtered_leads = leads

    if with_msg:
        st.markdown("---")
        st.subheader("Mensajes generados")
        for lead in with_msg[:10]:
            with st.expander(f"✉️ {(lead.company or lead.title)[:40]}"):
                st.markdown(f"**Para:** {lead.email or 'Sin email'}")
                st.markdown("---")
                st.markdown(lead.personalized_message)


def show_statistics():
    """Show statistics dashboard."""
    st.header("📊 Estadísticas")

    leads = st.session_state.leads
    filtered = st.session_state.filtered_leads

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📥 Encontrados", len(leads))
    with col2:
        st.metric("✅ Calificados", len(filtered))
    with col3:
        st.metric("📧 Con Email", sum(1 for l in leads if l.email))

    if leads:
        st.markdown("---")
        st.subheader("Por Fuente")

        source_data = {}
        for lead in leads:
            src = lead.source.value
            if src not in source_data:
                source_data[src] = {"total": 0, "email": 0, "phone": 0}
            source_data[src]["total"] += 1
            if lead.email:
                source_data[src]["email"] += 1
            if lead.phone:
                source_data[src]["phone"] += 1

        df = pd.DataFrame([
            {"Fuente": src, "Total": d["total"], "Con Email": d["email"], "Con Teléfono": d["phone"]}
            for src, d in sorted(source_data.items(), key=lambda x: x[1]["total"], reverse=True)
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)

    with HubSpotCRM() as crm:
        if crm.is_configured():
            st.markdown("---")
            if st.button("🔄 Cargar Stats de HubSpot", use_container_width=True):
                with st.spinner("Cargando..."):
                    stats = crm.get_statistics()
                if "error" not in stats:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("📊 Total HubSpot", stats["total_leads"])
                        st.metric("📈 Conversión", f"{stats['conversion_rate']}%")
                    with col2:
                        st.metric("🏆 Ganados", stats["by_stage"].get("closed_won", 0))
                        st.metric("📉 Win Rate", f"{stats['win_rate']}%")


def show_export():
    """CSV export page."""
    st.header("💾 Exportar Leads")

    leads = st.session_state.filtered_leads or st.session_state.leads
    if not leads:
        st.info("📭 No hay leads para exportar. Busca leads primero.")
        return

    st.markdown(f"**{len(leads)} leads disponibles para exportar**")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Con Email", sum(1 for l in leads if l.email))
    with col2:
        st.metric("Con Teléfono", sum(1 for l in leads if l.phone))

    st.markdown("---")
    export_format = st.radio("Formato", ["CSV estándar", "Google Sheets (TSV)"], horizontal=True)

    if st.button("💾 EXPORTAR", type="primary", use_container_width=True):
        try:
            if export_format == "CSV estándar":
                filepath = export_leads_to_csv(leads)
            else:
                filepath = export_leads_for_google_sheets(leads)

            st.success(f"✅ Exportado: {filepath}")
            st.info(f"📁 {len(leads)} leads exportados")

            with open(filepath, "r") as f:
                content = f.read()
            st.download_button(
                "⬇️ Descargar archivo",
                data=content,
                file_name=Path(filepath).name,
                mime="text/csv",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"❌ Error: {e}")


def show_config():
    """Show configuration page."""
    st.header("⚙️ Configuración")

    st.subheader("🤖 Estado de AI")
    ollama_filter = OllamaGeminiFilter()

    ai_status = [
        ("Ollama", ollama_filter.ollama_available, f"Local ({settings.ollama_model})", "Gratis"),
        ("Gemini", bool(settings.gemini_api_key), "Google AI", "Gratis"),
        ("OpenAI", bool(settings.openai_api_key), "GPT-4o-mini", "Pago"),
        ("Anthropic", bool(settings.anthropic_api_key), "Claude Haiku", "Pago"),
    ]

    for name, active, desc, cost in ai_status:
        badge = "status-success" if active else "status-warning"
        status = "✅ Activo" if active else "⚠️ No configurado"
        st.markdown(f"""
        <div class="lead-card">
            <span class="status-badge {badge}">{status}</span>
            <strong> {name}</strong> ({cost})<br>
            <small>{desc}</small>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("🔌 APIs")
    apis = [
        ("HubSpot", settings.hubspot_api_key, "CRM"),
        ("Google Search", settings.google_api_key, "100 búsquedas/día gratis"),
    ]
    for name, key, purpose in apis:
        status = "✅ Activo" if key else "⚠️ No configurado"
        badge = "status-success" if key else "status-warning"
        st.markdown(f"""
        <div class="lead-card">
            <span class="status-badge {badge}">{status}</span>
            <strong> {name}</strong><br>
            <small>{purpose}</small>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🎯 Fuentes (10)")
    st.markdown("Reddit, Hacker News, Google Search, Product Hunt, Google Maps, Yelp, Indeed, Yellow Pages, BBB, Craigslist")

    st.markdown("---")
    st.subheader("🏷️ Nichos")
    st.markdown(", ".join(settings.maps_niches))

    st.subheader("📍 Ubicaciones")
    st.markdown(", ".join(settings.maps_locations))

    st.markdown("---")
    st.info("💡 Edita `.env` para cambiar la configuración")


if __name__ == "__main__":
    main()
