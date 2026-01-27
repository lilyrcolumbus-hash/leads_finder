#!/usr/bin/env python3
"""
Lead Generation App - Web Interface (Streamlit)

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

# Page config
st.set_page_config(
    page_title="Lead Generation App",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .lead-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .success-msg {
        color: #28a745;
        font-weight: bold;
    }
    .error-msg {
        color: #dc3545;
        font-weight: bold;
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


def main():
    """Main app entry point."""

    # Sidebar navigation
    st.sidebar.title("🎯 Lead Generation")

    page = st.sidebar.radio(
        "Navegación",
        ["🏠 Inicio", "🔍 Buscar Leads", "📋 Mis Leads", "📊 Estadísticas", "⚙️ Configuración"]
    )

    if page == "🏠 Inicio":
        show_home()
    elif page == "🔍 Buscar Leads":
        show_search()
    elif page == "📋 Mis Leads":
        show_leads()
    elif page == "📊 Estadísticas":
        show_statistics()
    elif page == "⚙️ Configuración":
        show_config()


def show_home():
    """Home page."""
    st.markdown('<h1 class="main-header">🎯 Lead Generation App</h1>', unsafe_allow_html=True)

    st.markdown("""
    ### Encuentra dueños de negocios con problemas de comunicación

    Esta app busca leads en múltiples fuentes:
    - **Reddit** - Subreddits de pequeños negocios
    - **Hacker News** - Discusiones de startups
    - **Google Search** - Búsquedas específicas
    - **Product Hunt** - Founders con problemas

    ---

    #### 🚀 Comenzar
    1. Ve a **Buscar Leads** para encontrar nuevos prospectos
    2. Revisa los resultados en **Mis Leads**
    3. Envía los leads calificados a **HubSpot CRM**
    """)

    # Quick stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Leads Encontrados", len(st.session_state.leads))
    with col2:
        st.metric("Leads Calificados", len(st.session_state.filtered_leads))
    with col3:
        st.metric("Keywords Activos", len(settings.pain_keywords))


def show_search():
    """Search for new leads."""
    st.header("🔍 Buscar Nuevos Leads")

    # Source selection
    st.subheader("Selecciona las fuentes")

    col1, col2 = st.columns(2)
    with col1:
        use_reddit = st.checkbox("Reddit", value=True)
        use_hn = st.checkbox("Hacker News", value=True)
    with col2:
        use_google = st.checkbox("Google Search", value=bool(settings.google_api_key))
        use_ph = st.checkbox("Product Hunt", value=True)

    # AI filtering option
    use_ai = st.checkbox("🤖 Filtrar con AI", value=bool(settings.openai_api_key or settings.anthropic_api_key))

    if st.button("🚀 Iniciar Búsqueda", type="primary", use_container_width=True):
        all_leads = []

        progress_bar = st.progress(0)
        status_text = st.empty()

        scrapers = []
        if use_reddit:
            scrapers.append(("Reddit", RedditScraper))
        if use_hn:
            scrapers.append(("Hacker News", HackerNewsScraper))
        if use_google:
            scrapers.append(("Google Search", GoogleScraper))
        if use_ph:
            scrapers.append(("Product Hunt", ProductHuntScraper))

        for i, (name, ScraperClass) in enumerate(scrapers):
            status_text.text(f"Buscando en {name}...")
            try:
                with ScraperClass() as scraper:
                    batch = scraper.scrape()
                    all_leads.extend(batch.leads)
                    st.success(f"✅ {name}: {len(batch.leads)} leads encontrados")
            except Exception as e:
                st.warning(f"⚠️ {name}: Error - {str(e)[:50]}")

            progress_bar.progress((i + 1) / len(scrapers))

        st.session_state.leads = all_leads
        status_text.text(f"Total: {len(all_leads)} leads encontrados")

        # AI Filtering
        if use_ai and all_leads:
            status_text.text("Filtrando con AI...")
            try:
                ai_filter = AILeadFilter()
                filtered = ai_filter.filter_leads(all_leads)
                qualified = [l for l in filtered if l.is_qualified]
                st.session_state.filtered_leads = qualified
                st.success(f"🤖 AI calificó {len(qualified)}/{len(all_leads)} leads")
            except Exception as e:
                st.warning(f"⚠️ AI filtering failed: {e}")
                st.session_state.filtered_leads = all_leads
        else:
            st.session_state.filtered_leads = all_leads

        st.session_state.scraping_done = True
        progress_bar.progress(1.0)
        status_text.text("✅ Búsqueda completada")

    # Show results preview
    if st.session_state.scraping_done and st.session_state.filtered_leads:
        st.subheader(f"📋 Preview ({len(st.session_state.filtered_leads)} leads)")

        for lead in st.session_state.filtered_leads[:5]:
            with st.expander(f"**{lead.title[:60]}...** - {lead.source.value}"):
                st.write(f"**Keywords:** {', '.join(lead.keywords_matched[:5])}")
                st.write(f"**URL:** {lead.url}")
                if lead.ai_score:
                    st.write(f"**AI Score:** {lead.ai_score:.2f}")
                st.write(f"**Contenido:** {lead.content[:300]}...")


def show_leads():
    """Show and manage leads."""
    st.header("📋 Mis Leads")

    tab1, tab2 = st.tabs(["Leads Locales", "Leads en HubSpot"])

    with tab1:
        if not st.session_state.filtered_leads:
            st.info("No hay leads. Ve a 'Buscar Leads' para encontrar nuevos prospectos.")
        else:
            # Convert to DataFrame
            leads_data = []
            for lead in st.session_state.filtered_leads:
                leads_data.append({
                    "ID": lead.id[:8],
                    "Título": lead.title[:50],
                    "Fuente": lead.source.value,
                    "Keywords": ", ".join(lead.keywords_matched[:3]),
                    "Score": f"{lead.ai_score:.2f}" if lead.ai_score else "-",
                    "URL": lead.url
                })

            df = pd.DataFrame(leads_data)
            st.dataframe(df, use_container_width=True)

            # Send to HubSpot
            st.subheader("Enviar a HubSpot")
            if st.button("📤 Enviar leads a HubSpot", type="primary"):
                with HubSpotCRM() as crm:
                    if not crm.is_configured():
                        st.error("❌ HubSpot no está configurado. Agrega HUBSPOT_API_KEY en .env")
                    else:
                        with st.spinner("Enviando leads..."):
                            results = crm.send_leads_to_crm(st.session_state.filtered_leads)
                        st.success(f"✅ Creados: {results['created']} | Existentes: {results['existing']} | Fallidos: {results['failed']}")

    with tab2:
        with HubSpotCRM() as crm:
            if not crm.is_configured():
                st.warning("⚠️ HubSpot no está configurado")
            else:
                # Stage filter
                stage_filter = st.selectbox(
                    "Filtrar por etapa",
                    ["Todos"] + [s.value for s in LeadStage]
                )

                if st.button("🔄 Cargar leads de HubSpot"):
                    with st.spinner("Cargando..."):
                        if stage_filter == "Todos":
                            contacts = crm.get_all_contacts()
                        else:
                            contacts = crm.get_contacts_by_stage(LeadStage(stage_filter))

                    if contacts:
                        contacts_data = []
                        for c in contacts:
                            contacts_data.append({
                                "ID": c.id,
                                "Nombre": f"{c.firstname or ''} {c.lastname or ''}".strip() or "-",
                                "Email": c.email or "-",
                                "Empresa": c.company or "-",
                                "Etapa": c.lead_stage.value,
                                "Fuente": c.source or "-"
                            })
                        st.dataframe(pd.DataFrame(contacts_data), use_container_width=True)
                    else:
                        st.info("No se encontraron contactos")


def show_statistics():
    """Show statistics dashboard."""
    st.header("📊 Estadísticas")

    with HubSpotCRM() as crm:
        if not crm.is_configured():
            st.warning("⚠️ HubSpot no está configurado. Mostrando estadísticas locales.")

            # Local stats
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Leads encontrados", len(st.session_state.leads))
            with col2:
                st.metric("Leads calificados", len(st.session_state.filtered_leads))

            # By source
            if st.session_state.leads:
                source_counts = {}
                for lead in st.session_state.leads:
                    source_counts[lead.source.value] = source_counts.get(lead.source.value, 0) + 1

                st.subheader("Por fuente")
                st.bar_chart(source_counts)
        else:
            with st.spinner("Cargando estadísticas..."):
                stats = crm.get_statistics()

            if "error" in stats:
                st.error(stats["error"])
            else:
                # Main metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Leads", stats["total_leads"])
                with col2:
                    st.metric("Tasa de Conversión", f"{stats['conversion_rate']}%")
                with col3:
                    st.metric("Tasa de Cierre", f"{stats['win_rate']}%")
                with col4:
                    st.metric("Ganados", stats["by_stage"].get("closed_won", 0))

                # By stage chart
                st.subheader("Leads por Etapa")
                if stats["by_stage"]:
                    st.bar_chart(stats["by_stage"])

                # By source chart
                st.subheader("Leads por Fuente")
                if stats["by_source"]:
                    st.bar_chart(stats["by_source"])


def show_config():
    """Show configuration page."""
    st.header("⚙️ Configuración")

    st.subheader("Estado de APIs")

    col1, col2 = st.columns(2)
    with col1:
        if settings.hubspot_api_key:
            st.success("✅ HubSpot configurado")
        else:
            st.error("❌ HubSpot no configurado")

        if settings.google_api_key:
            st.success("✅ Google configurado")
        else:
            st.warning("⚠️ Google no configurado")

    with col2:
        if settings.openai_api_key:
            st.success("✅ OpenAI configurado")
        else:
            st.warning("⚠️ OpenAI no configurado")

        if settings.anthropic_api_key:
            st.success("✅ Anthropic configurado")
        else:
            st.warning("⚠️ Anthropic no configurado")

    st.subheader("Subreddits monitoreados")
    st.write(", ".join(settings.subreddits))

    st.subheader("Keywords de dolor")
    cols = st.columns(3)
    for i, kw in enumerate(settings.pain_keywords):
        with cols[i % 3]:
            st.write(f"• {kw}")

    st.info("💡 Edita el archivo `.env` para cambiar la configuración")


if __name__ == "__main__":
    main()
