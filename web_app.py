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
from src.scrapers import RedditScraper, HackerNewsScraper, GoogleScraper, ProductHuntScraper
from src.filters import AILeadFilter
from src.crm import HubSpotCRM, LeadStage

# Page config - centered layout works better on mobile
st.set_page_config(
    page_title="Lead Generation",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed"  # Collapsed by default for mobile
)

# Mobile-optimized CSS with enhanced animations
st.markdown("""
<style>
    /* ========== CSS VARIABLES ========== */
    :root {
        --primary: #667eea;
        --primary-dark: #5a67d8;
        --secondary: #764ba2;
        --success: #10b981;
        --warning: #f59e0b;
        --error: #ef4444;
        --info: #3b82f6;
        --text-primary: #1e293b;
        --text-secondary: #64748b;
        --bg-card: #ffffff;
        --bg-hover: #f8fafc;
        --border: #e2e8f0;
        --shadow: rgba(0,0,0,0.1);
        --shadow-lg: rgba(0,0,0,0.15);
    }

    /* ========== ANIMATIONS ========== */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translateX(-30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }

    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }

    @keyframes statusPulse {
        0%, 100% {
            transform: scale(1);
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4);
        }
        50% {
            transform: scale(1.1);
            box-shadow: 0 0 0 8px rgba(16, 185, 129, 0);
        }
    }

    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    /* ========== BASE STYLES ========== */
    .stApp {
        max-width: 100%;
    }

    /* Smooth scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #f1f5f9;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, var(--primary), var(--secondary));
        border-radius: 4px;
    }

    /* ========== MOBILE-FIRST RESPONSIVE ========== */
    @media (max-width: 768px) {
        .stApp {
            padding: 0.5rem;
            padding-bottom: 80px !important; /* Space for bottom nav */
        }

        .stButton > button {
            width: 100% !important;
            min-height: 3rem !important;
            font-size: 1.1rem !important;
            margin: 0.5rem 0 !important;
            transition: all 0.3s ease !important;
        }

        .stButton > button:active {
            transform: scale(0.98) !important;
        }

        .stCheckbox {
            padding: 0.75rem 0 !important;
        }

        .stCheckbox label {
            font-size: 1.1rem !important;
        }

        [data-testid="metric-container"] {
            padding: 0.75rem !important;
            margin: 0.25rem 0 !important;
            animation: fadeInUp 0.4s ease-out;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
        }

        .streamlit-expanderHeader {
            font-size: 1rem !important;
            padding: 1rem !important;
        }

        [data-testid="stSidebar"] {
            min-width: 280px !important;
        }

        .stTabs [data-baseweb="tab"] {
            padding: 0.75rem 1rem !important;
            font-size: 1rem !important;
        }

        .stSelectbox {
            margin: 0.5rem 0 !important;
        }

        .stProgress {
            margin: 1rem 0 !important;
        }

        .stAlert {
            padding: 1rem !important;
            font-size: 1rem !important;
        }

        h1 { font-size: 1.75rem !important; }
        h2 { font-size: 1.5rem !important; }
        h3 { font-size: 1.25rem !important; }

        /* Show mobile bottom nav */
        .mobile-bottom-nav {
            display: flex !important;
        }
    }

    /* ========== MAIN HEADER ========== */
    .main-header {
        font-size: 1.75rem;
        font-weight: bold;
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 1.5rem;
        padding: 1rem;
        animation: fadeIn 0.6s ease-out;
    }

    /* ========== CARD STYLING ========== */
    .lead-card {
        background-color: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.25rem;
        margin: 0.75rem 0;
        box-shadow: 0 4px 15px var(--shadow);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        animation: fadeInUp 0.5s ease-out;
        position: relative;
        overflow: hidden;
    }

    .lead-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--primary), var(--secondary));
        transform: scaleX(0);
        transform-origin: left;
        transition: transform 0.3s ease;
    }

    .lead-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 25px var(--shadow-lg);
        border-color: var(--primary);
    }

    .lead-card:hover::before {
        transform: scaleX(1);
    }

    /* ========== STATUS BADGES ========== */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 0.35rem 0.85rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    .status-success {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.15));
        color: var(--success);
        border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .status-warning {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(217, 119, 6, 0.15));
        color: var(--warning);
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    .status-error {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.15));
        color: var(--error);
        border: 1px solid rgba(239, 68, 68, 0.3);
    }

    .status-info {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(37, 99, 235, 0.15));
        color: var(--info);
        border: 1px solid rgba(59, 130, 246, 0.3);
    }

    /* Status dot with pulse */
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }

    .status-dot.active {
        background: var(--success);
        animation: statusPulse 2s infinite;
    }

    .status-dot.inactive {
        background: #94a3b8;
    }

    /* ========== NAVIGATION ========== */
    .nav-link {
        display: block;
        padding: 1rem;
        margin: 0.5rem 0;
        background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
        color: white !important;
        text-decoration: none;
        border-radius: 12px;
        text-align: center;
        font-weight: 600;
        font-size: 1.1rem;
        transition: all 0.3s ease;
    }

    .nav-link:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
    }

    /* ========== MOBILE BOTTOM NAVIGATION ========== */
    .mobile-bottom-nav {
        display: none;
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        height: 65px;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border-top: 1px solid var(--border);
        box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.1);
        z-index: 99999;
        justify-content: space-around;
        align-items: center;
        padding: 0 8px;
        padding-bottom: env(safe-area-inset-bottom);
    }

    .mobile-nav-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 8px 12px;
        cursor: pointer;
        transition: all 0.3s ease;
        border-radius: 12px;
        min-width: 60px;
    }

    .mobile-nav-item:active {
        transform: scale(0.95);
    }

    .mobile-nav-item.active {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
    }

    .mobile-nav-icon {
        font-size: 22px;
        margin-bottom: 4px;
        transition: all 0.3s ease;
    }

    .mobile-nav-item.active .mobile-nav-icon {
        transform: scale(1.1);
    }

    .mobile-nav-label {
        font-size: 10px;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .mobile-nav-item.active .mobile-nav-label {
        color: var(--primary);
    }

    /* ========== PROGRESS INDICATOR ========== */
    .progress-container {
        background: #e2e8f0;
        border-radius: 10px;
        height: 10px;
        overflow: hidden;
        margin: 1rem 0;
    }

    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--primary), var(--secondary));
        border-radius: 10px;
        transition: width 0.5s ease;
        position: relative;
    }

    .progress-fill::after {
        content: '';
        position: absolute;
        inset: 0;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
        animation: shimmer 2s infinite;
        background-size: 200% 100%;
    }

    /* ========== LOADING SKELETON ========== */
    .skeleton {
        background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        border-radius: 8px;
    }

    .skeleton-text {
        height: 16px;
        margin-bottom: 8px;
    }

    .skeleton-card {
        height: 100px;
        margin: 0.75rem 0;
    }

    /* ========== SCORE INDICATOR ========== */
    .score-indicator {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 700;
    }

    .score-high {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.15));
        color: var(--success);
    }

    .score-medium {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(217, 119, 6, 0.15));
        color: var(--warning);
    }

    .score-low {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.15));
        color: var(--error);
    }

    /* ========== SYNC STATUS ========== */
    .sync-status {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 12px;
        background: #f8fafc;
        border: 1px solid var(--border);
        border-radius: 8px;
        font-size: 0.85rem;
    }

    .sync-status.syncing .sync-icon {
        animation: spin 1s linear infinite;
    }

    /* ========== UTILITIES ========== */
    .dataframe-container {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }

    input, select, textarea {
        font-size: 16px !important;
    }

    /* Animation classes */
    .animate-in {
        animation: fadeInUp 0.5s ease-out;
    }

    .animate-slide-left {
        animation: slideInLeft 0.5s ease-out;
    }

    .hover-lift {
        transition: all 0.3s ease;
    }

    .hover-lift:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 25px var(--shadow-lg);
    }

    /* Staggered animation delays */
    .stagger-1 { animation-delay: 0.05s; }
    .stagger-2 { animation-delay: 0.1s; }
    .stagger-3 { animation-delay: 0.15s; }
    .stagger-4 { animation-delay: 0.2s; }
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
        ("🚀 Product Hunt", "Founders activos")
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


def render_mobile_bottom_nav():
    """Render mobile bottom navigation bar."""
    current_page = st.session_state.current_page

    # Map pages to icons and labels
    nav_items = [
        ("inicio", "🏠", "Inicio"),
        ("buscar", "🔍", "Buscar"),
        ("leads", "📋", "Leads"),
        ("stats", "📊", "Stats"),
        ("config", "⚙️", "Config"),
    ]

    nav_html = '<div class="mobile-bottom-nav">'

    for page, icon, label in nav_items:
        is_active = "active" if current_page == page else ""
        nav_html += f'''
        <div class="mobile-nav-item {is_active}" onclick="navigateTo('{page}')" data-page="{page}">
            <span class="mobile-nav-icon">{icon}</span>
            <span class="mobile-nav-label">{label}</span>
        </div>
        '''

    nav_html += '</div>'

    # Add JavaScript for navigation
    nav_html += '''
    <script>
    function navigateTo(page) {
        // Find the sidebar buttons and click the matching one
        const buttons = document.querySelectorAll('[data-testid="stSidebar"] button');
        const pageMap = {
            'inicio': '🏠 Inicio',
            'buscar': '🔍 Buscar Leads',
            'leads': '📋 Mis Leads',
            'stats': '📊 Estadísticas',
            'config': '⚙️ Configuración'
        };
        buttons.forEach(btn => {
            if (btn.textContent.includes(pageMap[page].substring(2))) {
                btn.click();
            }
        });
    }

    // Update active state for visual feedback
    document.querySelectorAll('.mobile-nav-item').forEach(item => {
        item.addEventListener('click', function() {
            document.querySelectorAll('.mobile-nav-item').forEach(i => i.classList.remove('active'));
            this.classList.add('active');
        });
    });
    </script>
    '''

    st.markdown(nav_html, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
    # Render mobile bottom navigation after main content
    render_mobile_bottom_nav()
