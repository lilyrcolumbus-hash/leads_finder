#!/usr/bin/env python3
"""
Lead Generation App - Web Interface (Streamlit)
Optimized for mobile and desktop

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
from src.scrapers import RedditScraper, HackerNewsScraper, GoogleScraper, ProductHuntScraper, IndeedScraper
from src.filters import AILeadFilter
from src.crm import HubSpotCRM, LeadStage

# Page config - centered layout works better on mobile
st.set_page_config(
    page_title="Lead Generation",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed"  # Collapsed by default for mobile
)

# Mobile-optimized CSS
st.markdown("""
<style>
    /* Base styles */
    .stApp {
        max-width: 100%;
    }

    /* Mobile-first responsive design */
    @media (max-width: 768px) {
        .stApp {
            padding: 0.5rem;
        }

        /* Make buttons full width and larger */
        .stButton > button {
            width: 100% !important;
            min-height: 3rem !important;
            font-size: 1.1rem !important;
            margin: 0.5rem 0 !important;
        }

        /* Larger touch targets for checkboxes */
        .stCheckbox {
            padding: 0.75rem 0 !important;
        }

        .stCheckbox label {
            font-size: 1.1rem !important;
        }

        /* Better spacing for metrics */
        [data-testid="metric-container"] {
            padding: 0.75rem !important;
            margin: 0.25rem 0 !important;
        }

        /* Larger text in metrics */
        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
        }

        /* Make expanders easier to tap */
        .streamlit-expanderHeader {
            font-size: 1rem !important;
            padding: 1rem !important;
        }

        /* Sidebar adjustments */
        [data-testid="stSidebar"] {
            min-width: 280px !important;
        }

        /* Tab styling */
        .stTabs [data-baseweb="tab"] {
            padding: 0.75rem 1rem !important;
            font-size: 1rem !important;
        }

        /* Select box */
        .stSelectbox {
            margin: 0.5rem 0 !important;
        }

        /* Progress bar */
        .stProgress {
            margin: 1rem 0 !important;
        }

        /* Info/Warning/Success boxes */
        .stAlert {
            padding: 1rem !important;
            font-size: 1rem !important;
        }

        /* Headers */
        h1 {
            font-size: 1.75rem !important;
        }

        h2 {
            font-size: 1.5rem !important;
        }

        h3 {
            font-size: 1.25rem !important;
        }
    }

    /* Main header styling */
    .main-header {
        font-size: 1.75rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1.5rem;
        padding: 1rem;
    }

    /* Card styling */
    .lead-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.75rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 500;
    }

    .status-success {
        background-color: #d4edda;
        color: #155724;
    }

    .status-warning {
        background-color: #fff3cd;
        color: #856404;
    }

    .status-error {
        background-color: #f8d7da;
        color: #721c24;
    }

    /* Navigation menu styling */
    .nav-link {
        display: block;
        padding: 1rem;
        margin: 0.5rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        text-decoration: none;
        border-radius: 10px;
        text-align: center;
        font-weight: 500;
        font-size: 1.1rem;
    }

    /* Mobile table scroll */
    .dataframe-container {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }

    /* Fix for iOS input zoom */
    input, select, textarea {
        font-size: 16px !important;
    }
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

    # Mobile-friendly navigation in sidebar
    with st.sidebar:
        st.markdown("## 🎯 Lead Generation")
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

        if st.button("📊 Estadísticas", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

        if st.button("⚙️ Configuración", use_container_width=True):
            st.session_state.current_page = "config"
            st.rerun()

        st.markdown("---")
        st.caption("v1.0 | Mobile Ready 📱")

    # Route to pages
    page = st.session_state.current_page

    if page == "inicio":
        show_home()
    elif page == "buscar":
        show_search()
    elif page == "leads":
        show_leads()
    elif page == "stats":
        show_statistics()
    elif page == "config":
        show_config()


def show_home():
    """Home page."""
    st.markdown('<h1 class="main-header">🎯 Lead Generation App</h1>', unsafe_allow_html=True)

    st.markdown("""
    ### Encuentra leads con problemas de comunicación

    Busca en múltiples fuentes:
    """)

    # Sources as cards - stacked for mobile
    sources = [
        ("📱 Reddit", "Subreddits de negocios"),
        ("💻 Hacker News", "Discusiones de startups"),
        ("🔍 Google", "Búsquedas específicas"),
        ("🚀 Product Hunt", "Founders activos"),
        ("💼 Indeed", "Empresas contratando recepcionistas"),
    ]

    for icon_name, desc in sources:
        st.markdown(f"""
        <div class="lead-card">
            <strong>{icon_name}</strong><br>
            <small>{desc}</small>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Quick stats - 2 columns max for mobile
    st.subheader("📊 Resumen Rápido")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Leads", len(st.session_state.leads))
    with col2:
        st.metric("Calificados", len(st.session_state.filtered_leads))

    st.markdown("---")

    # Quick action button
    if st.button("🚀 Comenzar Búsqueda", type="primary", use_container_width=True):
        st.session_state.current_page = "buscar"
        st.rerun()


def show_search():
    """Search for new leads."""
    st.header("🔍 Buscar Leads")

    st.markdown("### Selecciona fuentes")

    # Stacked checkboxes for mobile (easier to tap)
    use_reddit = st.checkbox("📱 Reddit", value=True)
    use_hn = st.checkbox("💻 Hacker News", value=True)
    use_google = st.checkbox("🔍 Google Search", value=bool(settings.google_api_key))
    use_ph = st.checkbox("🚀 Product Hunt", value=True)
    use_indeed = st.checkbox("💼 Indeed (Empresas contratando recepcionistas)", value=True)

    st.markdown("---")

    # AI filtering option
    use_ai = st.checkbox(
        "🤖 Filtrar con AI",
        value=bool(settings.openai_api_key or settings.anthropic_api_key),
        help="Usa inteligencia artificial para calificar leads"
    )

    st.markdown("")

    if st.button("🚀 INICIAR BÚSQUEDA", type="primary", use_container_width=True):
        all_leads = []

        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()

        scrapers = []
        if use_reddit:
            scrapers.append(("Reddit", RedditScraper))
        if use_hn:
            scrapers.append(("Hacker News", HackerNewsScraper))
        if use_google:
            scrapers.append(("Google Search", GoogleScraper))
        if use_ph:
            scrapers.append(("Product Hunt", ProductHuntScraper))
        if use_indeed:
            scrapers.append(("Indeed", IndeedScraper))

        if not scrapers:
            st.warning("⚠️ Selecciona al menos una fuente")
            return

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
                    st.warning(f"⚠️ {name}: Error")

            progress_bar.progress((i + 1) / len(scrapers))

        st.session_state.leads = all_leads

        # AI Filtering
        if use_ai and all_leads:
            status_text.text("🤖 Filtrando con AI...")
            try:
                ai_filter = AILeadFilter()
                filtered = ai_filter.filter_leads(all_leads)
                qualified = [l for l in filtered if l.is_qualified]
                st.session_state.filtered_leads = qualified
                with results_container:
                    st.success(f"🤖 AI: {len(qualified)}/{len(all_leads)} calificados")
            except Exception as e:
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

        for lead in st.session_state.filtered_leads[:10]:
            title_short = lead.title[:50] + "..." if len(lead.title) > 50 else lead.title
            with st.expander(f"📌 {title_short}"):
                st.markdown(f"**Fuente:** {lead.source.value}")
                st.markdown(f"**Keywords:** {', '.join(lead.keywords_matched[:3])}")
                if lead.ai_score:
                    score_pct = int(lead.ai_score * 100)
                    st.markdown(f"**Score AI:** {score_pct}%")
                st.markdown(f"**URL:** [{lead.url[:40]}...]({lead.url})")
                st.markdown(f"**Contenido:**\n{lead.content[:200]}...")


def show_leads():
    """Show and manage leads."""
    st.header("📋 Mis Leads")

    tab1, tab2 = st.tabs(["📱 Locales", "☁️ HubSpot"])

    with tab1:
        if not st.session_state.filtered_leads:
            st.info("📭 No hay leads.\n\nVe a 'Buscar Leads' para encontrar prospectos.")

            if st.button("🔍 Ir a Buscar", use_container_width=True):
                st.session_state.current_page = "buscar"
                st.rerun()
        else:
            st.markdown(f"**Total:** {len(st.session_state.filtered_leads)} leads")

            # Mobile-friendly card view instead of table
            for i, lead in enumerate(st.session_state.filtered_leads[:20]):
                with st.container():
                    st.markdown(f"""
                    <div class="lead-card">
                        <strong>#{i+1}</strong> {lead.title[:40]}...<br>
                        <small>📍 {lead.source.value} | 🏷️ {', '.join(lead.keywords_matched[:2])}</small>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("---")

            # Send to HubSpot
            if st.button("📤 ENVIAR A HUBSPOT", type="primary", use_container_width=True):
                with HubSpotCRM() as crm:
                    if not crm.is_configured():
                        st.error("❌ HubSpot no configurado")
                    else:
                        with st.spinner("Enviando..."):
                            results = crm.send_leads_to_crm(st.session_state.filtered_leads)
                        st.success(f"✅ Enviados: {results['created']}")
                        if results['failed'] > 0:
                            st.warning(f"⚠️ Fallidos: {results['failed']}")

    with tab2:
        with HubSpotCRM() as crm:
            if not crm.is_configured():
                st.warning("⚠️ Configura HUBSPOT_API_KEY en .env")
            else:
                stage_filter = st.selectbox(
                    "Filtrar por etapa",
                    ["Todos"] + [s.value for s in LeadStage]
                )

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
                                📧 {c.email or '-'}<br>
                                🏢 {c.company or '-'}<br>
                                <span class="status-badge status-success">{c.lead_stage.value}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No hay contactos")


def show_statistics():
    """Show statistics dashboard."""
    st.header("📊 Estadísticas")

    with HubSpotCRM() as crm:
        if not crm.is_configured():
            st.info("📊 Estadísticas locales")

            col1, col2 = st.columns(2)
            with col1:
                st.metric("📥 Encontrados", len(st.session_state.leads))
            with col2:
                st.metric("✅ Calificados", len(st.session_state.filtered_leads))

            # By source
            if st.session_state.leads:
                st.markdown("---")
                st.subheader("Por Fuente")

                source_counts = {}
                for lead in st.session_state.leads:
                    source_counts[lead.source.value] = source_counts.get(lead.source.value, 0) + 1

                for source, count in source_counts.items():
                    st.markdown(f"""
                    <div class="lead-card">
                        <strong>{source}</strong>: {count} leads
                    </div>
                    """, unsafe_allow_html=True)
        else:
            if st.button("🔄 Cargar Estadísticas", use_container_width=True):
                with st.spinner("Cargando..."):
                    stats = crm.get_statistics()

                if "error" in stats:
                    st.error(stats["error"])
                else:
                    # Main metrics - 2 columns for mobile
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("📊 Total", stats["total_leads"])
                        st.metric("📈 Conversión", f"{stats['conversion_rate']}%")
                    with col2:
                        st.metric("🏆 Ganados", stats["by_stage"].get("closed_won", 0))
                        st.metric("📉 Win Rate", f"{stats['win_rate']}%")

                    # Pipeline
                    st.markdown("---")
                    st.subheader("Pipeline")

                    stages = [
                        ("🆕 Nuevo", "new"),
                        ("📞 Contactado", "contacted"),
                        ("🎯 Demo", "demo"),
                        ("📝 Propuesta", "proposal"),
                        ("✅ Ganado", "closed_won"),
                        ("❌ Perdido", "closed_lost")
                    ]

                    for label, key in stages:
                        count = stats["by_stage"].get(key, 0)
                        st.markdown(f"{label}: **{count}**")


def show_config():
    """Show configuration page."""
    st.header("⚙️ Configuración")

    st.subheader("Estado de APIs")

    # API Status cards
    apis = [
        ("HubSpot", settings.hubspot_api_key, "CRM"),
        ("Google", settings.google_api_key, "Búsquedas"),
        ("OpenAI", settings.openai_api_key, "AI Filter"),
        ("Anthropic", settings.anthropic_api_key, "AI Filter"),
    ]

    for name, key, purpose in apis:
        if key:
            st.markdown(f"""
            <div class="lead-card">
                <span class="status-badge status-success">✅ Activo</span>
                <strong> {name}</strong><br>
                <small>{purpose}</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="lead-card">
                <span class="status-badge status-warning">⚠️ No configurado</span>
                <strong> {name}</strong><br>
                <small>{purpose}</small>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Subreddits
    st.subheader("📱 Subreddits")
    subreddits_text = ", ".join(settings.subreddits)
    st.markdown(f"<small>{subreddits_text}</small>", unsafe_allow_html=True)

    st.markdown("---")

    # Keywords
    st.subheader("🔑 Keywords de Dolor")
    for kw in settings.pain_keywords[:8]:
        st.markdown(f"• {kw}")
    if len(settings.pain_keywords) > 8:
        st.markdown(f"*... y {len(settings.pain_keywords) - 8} más*")

    st.markdown("---")
    st.info("💡 Edita `.env` para cambiar la configuración")


if __name__ == "__main__":
    main()
