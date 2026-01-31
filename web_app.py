#!/usr/bin/env python3
"""
LeadGen Pro - Premium Web Interface
Modern, Clean, Professional Design

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
from src.utils.models import Lead, LeadSource, LeadUrgency
from src.utils.scoring import enrich_leads, calculate_pain_score, get_lead_grade
from src.utils.lead_manager import lead_manager, csv_exporter, email_finder
from src.utils.hunter_enricher import enrich_leads_with_hunter
from src.enrichment.apollo_enricher import enrich_leads_with_apollo
from src.enrichment.email_verifier import EmailVerifier, get_email_quality_for_scoring
from src.enrichment.job_change_monitor import JobChangeMonitor, JobChange, OpportunityLevel
from src.utils.background_tasks import task_manager, TaskStatus
from src.scrapers import RedditScraper, HackerNewsScraper, GoogleScraper, ProductHuntScraper, IndeedScraper, YelpScraper, LinkedInScraper, GoogleMapsScraper
from src.filters import AILeadFilter
from src.crm import HubSpotCRM, LeadStage

# ============================================
# TRANSLATIONS / TRADUCCIONES
# ============================================
TRANSLATIONS = {
    'en': {
        # Analytics Page
        'analytics_title': 'Analytics',
        'analytics_subtitle': 'Lead generation performance metrics',
        'analytics_tooltip_title': 'What is Analytics?',
        'analytics_tooltip_desc': 'This page shows your lead generation performance:',
        'leads_found': 'Leads Found',
        'total_discovered': 'Total discovered',
        'qualified_leads': 'Qualified Leads',
        'passed_filters': 'Passed filters',
        'conversion_rate': 'Conversion Rate',
        'qualified_total': 'Qualified / Total',
        'hot_leads': 'Hot Leads',
        'leads_by_source': 'Leads by Source',
        'leads_by_source_desc': 'Where your leads come from - identify the best sources',
        'score_distribution': 'Score Distribution',
        'lead_quality_by_score': 'Lead quality by score',
        'ready_to_contact': 'Ready to contact',
        'need_more_nurturing': 'Need more nurturing',
        'low_priority': 'Low priority',
        'no_data_yet': 'No data yet',
        'go_to_find_leads': 'Go to "Find Leads" to start searching and see analytics here',
        'connect_hubspot': 'Connect HubSpot for more statistics',
        'go_to_settings': 'Go to Settings to connect your HubSpot account and view advanced CRM metrics',
        'loading_hubspot': 'Loading HubSpot statistics...',
        'hubspot_statistics': 'HubSpot Statistics',
        'data_synced': 'Data synced from your CRM',
        'won': 'Won',
        'by_stage_hubspot': 'By Stage in HubSpot',
        # Common
        'main_menu': 'Main Menu',
        'search': 'Search',
        'save': 'Save',
        'cancel': 'Cancel',
        'delete': 'Delete',
    },
    'es': {
        # Analytics Page
        'analytics_title': 'Analíticas',
        'analytics_subtitle': 'Métricas de rendimiento de generación de leads',
        'analytics_tooltip_title': '¿Para qué es Analytics?',
        'analytics_tooltip_desc': 'Esta página muestra el rendimiento de tu búsqueda de leads:',
        'leads_found': 'Leads Encontrados',
        'total_discovered': 'Total descubiertos',
        'qualified_leads': 'Leads Calificados',
        'passed_filters': 'Pasaron el filtro',
        'conversion_rate': 'Tasa de Conversión',
        'qualified_total': 'Calificados / Total',
        'hot_leads': 'Leads Calientes',
        'leads_by_source': 'Leads por Fuente',
        'leads_by_source_desc': 'De dónde vienen tus leads - identifica las mejores fuentes',
        'score_distribution': 'Distribución de Puntuación',
        'lead_quality_by_score': 'Calidad de tus leads por score',
        'ready_to_contact': 'Listos para contactar',
        'need_more_nurturing': 'Necesitan más nurturing',
        'low_priority': 'Baja prioridad',
        'no_data_yet': 'No hay datos todavía',
        'go_to_find_leads': 'Ve a "Find Leads" para buscar leads y ver analíticas aquí',
        'connect_hubspot': 'Conecta HubSpot para más estadísticas',
        'go_to_settings': 'Ve a Settings para conectar tu HubSpot y ver métricas avanzadas',
        'loading_hubspot': 'Cargando estadísticas de HubSpot...',
        'hubspot_statistics': 'Estadísticas de HubSpot',
        'data_synced': 'Datos sincronizados de tu CRM',
        'won': 'Ganados',
        'by_stage_hubspot': 'Por Etapa en HubSpot',
        # Common
        'main_menu': 'Menú Principal',
        'search': 'Buscar',
        'save': 'Guardar',
        'cancel': 'Cancelar',
        'delete': 'Eliminar',
    }
}

def t(key):
    """Get translation for current language."""
    lang = st.session_state.get('language', 'en')
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)

# Page config
st.set_page_config(
    page_title="LeadGen Pro",
    page_icon="◇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# FUTURISTIC HOLOGRAPHIC UI - Sci-Fi Design
# ============================================
st.markdown("""
<style>
    /* ========== HIDE STREAMLIT ELEMENTS ========== */
    *[class*="keyboard"], *[id*="keyboard"], *[data-testid*="keyboard"],
    [data-testid="stKeyboardShortcuts"], .stKeyboardShortcut,
    #MainMenu, footer, header, .stDeployButton {
        display: none !important;
        visibility: hidden !important;
    }

    /* ========== FONTS ========== */
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Rajdhani:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

    /* ========== FUTURISTIC COLOR PALETTE ========== */
    /* Paleta: Cian, Plateado, Teal, Gris Metálico, Blanco */
    /* SIN: morado, violeta, magenta, azul eléctrico */
    :root {
        /* Primary - Cyan */
        --cyan: #00FFFF;
        --cyan-glow: rgba(0, 255, 255, 0.5);
        --cyan-dim: rgba(0, 255, 255, 0.2);
        --cyan-subtle: rgba(0, 255, 255, 0.1);

        /* Secondary - Teal (NOT electric blue) */
        --teal: #008B8B;
        --teal-glow: rgba(0, 139, 139, 0.5);
        --teal-dim: rgba(0, 139, 139, 0.2);
        --teal-light: #20B2AA;

        /* Accent - Silver/Metallic */
        --silver: #C0C0C0;
        --silver-light: #E5E5E5;
        --silver-glow: rgba(192, 192, 192, 0.4);
        --metallic-gray: #2C3539;

        /* Background - Graphite/Slate Gradient */
        --bg-dark: #1C1C2E;
        --bg-darker: #2D3748;
        --bg-panel: rgba(28, 28, 46, 0.9);
        --bg-glass: rgba(44, 53, 57, 0.6);
        --bg-glass-light: rgba(45, 55, 72, 0.4);

        /* Text */
        --text-bright: #FFFFFF;
        --text-primary: #E5E5E5;
        --text-secondary: #C0C0C0;
        --text-dim: #708090;

        /* Status */
        --success: #00FF88;
        --success-glow: rgba(0, 255, 136, 0.4);
        --warning: #FFB800;
        --warning-glow: rgba(255, 184, 0, 0.4);
        --error: #FF6B6B;
        --error-glow: rgba(255, 107, 107, 0.4);

        /* Glass & Borders */
        --glass-border: rgba(0, 255, 255, 0.15);
        --glass-border-bright: rgba(0, 255, 255, 0.4);
        --silver-border: rgba(192, 192, 192, 0.3);

        /* Border Radius */
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
        --radius-xl: 20px;

        /* Shadows & Glows */
        --glow-cyan: 0 0 20px rgba(0, 255, 255, 0.3), 0 0 40px rgba(0, 255, 255, 0.1);
        --glow-teal: 0 0 20px rgba(0, 139, 139, 0.3), 0 0 40px rgba(0, 139, 139, 0.1);
        --glow-silver: 0 0 15px rgba(192, 192, 192, 0.3);
        --glow-intense: 0 0 30px rgba(0, 255, 255, 0.5), 0 0 60px rgba(0, 255, 255, 0.2);
        --shadow-dark: 0 10px 40px rgba(0, 0, 0, 0.5);
    }

    /* ========== GLOBAL TYPOGRAPHY ========== */
    html, body, [class*="css"] {
        font-family: 'Rajdhani', 'Segoe UI', sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Orbitron', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: 0.05em !important;
        line-height: 1.3 !important;
        color: var(--text-bright) !important;
        text-shadow: 0 0 10px var(--cyan-dim);
    }

    p, span, div, label {
        font-family: 'Rajdhani', sans-serif !important;
        line-height: 1.6 !important;
        color: var(--text-primary) !important;
    }

    /* ========== MAIN APP BACKGROUND ========== */
    /* Graphite/Slate gradient: #1C1C2E → #2D3748 */
    .stApp, [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #1C1C2E 0%, #2D3748 100%) !important;
        background-attachment: fixed !important;
    }

    /* Subtle grid pattern - data flow visualization */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-image:
            linear-gradient(rgba(0, 255, 255, 0.02) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 255, 255, 0.02) 1px, transparent 1px),
            radial-gradient(ellipse at 20% 30%, rgba(0, 139, 139, 0.08) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 70%, rgba(0, 255, 255, 0.05) 0%, transparent 50%);
        background-size: 40px 40px, 40px 40px, 100% 100%, 100% 100%;
        pointer-events: none;
        z-index: 0;
    }

    .main, [data-testid="stMain"] {
        background: transparent !important;
        position: relative;
        z-index: 1;
    }

    .main .block-container {
        padding: 2rem 3rem 3rem 3rem !important;
        max-width: 1400px !important;
        background: transparent !important;
    }

    /* ========== SIDEBAR - HOLOGRAPHIC PANEL ========== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(28, 28, 46, 0.95) 0%, rgba(5, 10, 25, 0.98) 100%) !important;
        border-right: 1px solid var(--glass-border) !important;
        box-shadow: 5px 0 30px rgba(0, 0, 0, 0.5), inset -1px 0 0 var(--cyan-dim) !important;
    }

    [data-testid="stSidebar"]::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 2px;
        height: 100%;
        background: linear-gradient(180deg, transparent 0%, var(--cyan) 20%, var(--cyan) 80%, transparent 100%);
        opacity: 0.3;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding: 0 !important;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: var(--text-secondary) !important;
    }

    /* Sidebar Radio Navigation - Holographic Buttons */
    [data-testid="stSidebar"] .stRadio > label {
        display: none !important;
    }

    [data-testid="stSidebar"] .stRadio > div {
        gap: 6px !important;
        padding: 0 16px !important;
    }

    [data-testid="stSidebar"] .stRadio > div > label {
        background: var(--bg-glass) !important;
        border-radius: var(--radius-md) !important;
        padding: 14px 16px !important;
        margin: 0 !important;
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        font-family: 'Rajdhani', sans-serif !important;
        transition: all 0.3s ease !important;
        border: 1px solid var(--glass-border) !important;
        backdrop-filter: blur(10px) !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
    }

    [data-testid="stSidebar"] .stRadio > div > label:hover {
        background: var(--bg-glass-light) !important;
        color: var(--cyan) !important;
        border-color: var(--cyan-dim) !important;
        box-shadow: var(--glow-cyan), inset 0 0 20px var(--cyan-subtle) !important;
        text-shadow: 0 0 10px var(--cyan-glow);
    }

    [data-testid="stSidebar"] .stRadio > div > label[data-checked="true"] {
        background: linear-gradient(135deg, rgba(0, 255, 255, 0.15) 0%, rgba(0, 139, 139, 0.15) 100%) !important;
        color: var(--cyan) !important;
        font-weight: 600 !important;
        border-color: var(--cyan) !important;
        box-shadow: var(--glow-intense), inset 0 0 30px var(--cyan-dim) !important;
        text-shadow: 0 0 15px var(--cyan);
    }

    /* ========== LOGO SECTION - HOLOGRAPHIC ========== */
    .logo-section {
        padding: 28px 24px 24px 24px;
        border-bottom: 1px solid var(--glass-border);
        margin-bottom: 8px;
        background: linear-gradient(180deg, rgba(0, 40, 60, 0.3) 0%, transparent 100%);
        position: relative;
    }

    .logo-section::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 20%;
        right: 20%;
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, var(--cyan) 50%, transparent 100%);
    }

    .logo-container {
        display: flex;
        align-items: center;
        gap: 14px;
    }

    .logo-icon {
        width: 46px;
        height: 46px;
        background: linear-gradient(135deg, var(--cyan-dim) 0%, var(--electric-dim) 100%);
        border: 1px solid var(--cyan);
        border-radius: var(--radius-md);
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: var(--glow-cyan);
        position: relative;
    }

    .logo-icon::before {
        content: '';
        position: absolute;
        inset: -2px;
        border-radius: var(--radius-md);
        background: linear-gradient(135deg, var(--cyan), var(--electric-blue));
        opacity: 0.3;
        z-index: -1;
        filter: blur(4px);
    }

    .logo-icon svg {
        width: 24px;
        height: 24px;
        filter: drop-shadow(0 0 5px var(--cyan));
    }

    .logo-text {
        flex: 1;
    }

    .logo-title {
        color: var(--cyan);
        font-size: 20px;
        font-weight: 700;
        font-family: 'Orbitron', sans-serif;
        letter-spacing: 0.1em;
        margin: 0;
        line-height: 1.2;
        text-shadow: 0 0 15px var(--cyan-glow);
    }

    .logo-subtitle {
        color: var(--text-secondary);
        font-size: 11px;
        font-weight: 600;
        margin: 4px 0 0 0;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        font-family: 'Share Tech Mono', monospace;
    }

    /* ========== USER CARD - HOLOGRAPHIC ========== */
    .user-card {
        margin: 16px;
        padding: 16px;
        background: var(--bg-glass);
        border-radius: var(--radius-md);
        border: 1px solid var(--glass-border);
        transition: all 0.3s ease;
        backdrop-filter: blur(10px);
        position: relative;
        overflow: hidden;
    }

    .user-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, var(--cyan) 50%, transparent 100%);
        opacity: 0.5;
    }

    .user-card:hover {
        border-color: var(--cyan-dim);
        box-shadow: var(--glow-cyan);
    }

    .user-info {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .user-avatar {
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, var(--cyan-dim) 0%, var(--electric-dim) 100%);
        border: 1px solid var(--cyan);
        border-radius: var(--radius-sm);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 15px;
        font-weight: 700;
        color: var(--cyan);
        box-shadow: var(--glow-cyan);
        font-family: 'Orbitron', sans-serif;
    }

    .user-details h4 {
        color: var(--text-bright);
        font-size: 14px;
        font-weight: 600;
        margin: 0 0 4px 0;
        font-family: 'Rajdhani', sans-serif;
    }

    .user-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: linear-gradient(135deg, rgba(0, 255, 136, 0.2) 0%, rgba(0, 139, 139, 0.2) 100%);
        color: var(--success);
        font-size: 10px;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 20px;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        border: 1px solid var(--success);
        box-shadow: 0 0 10px var(--success-glow);
        font-family: 'Share Tech Mono', monospace;
    }

    /* ========== NAV LABEL - HOLOGRAPHIC ========== */
    .nav-label {
        padding: 24px 24px 10px 24px;
        font-size: 10px;
        font-weight: 700;
        color: var(--text-dim);
        text-transform: uppercase;
        letter-spacing: 0.2em;
        font-family: 'Share Tech Mono', monospace;
    }

    /* ========== SIDEBAR FOOTER - HOLOGRAPHIC ========== */
    .sidebar-footer {
        padding: 20px 24px;
        border-top: 1px solid var(--glass-border);
        margin-top: auto;
        background: linear-gradient(180deg, transparent 0%, rgba(0, 40, 60, 0.3) 100%);
        position: relative;
    }

    .sidebar-footer::before {
        content: '';
        position: absolute;
        top: 0;
        left: 20%;
        right: 20%;
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, var(--cyan) 50%, transparent 100%);
        opacity: 0.3;
    }

    .sidebar-stats {
        display: flex;
        align-items: center;
        gap: 10px;
        color: var(--text-secondary);
        font-size: 12px;
        font-weight: 500;
        font-family: 'Share Tech Mono', monospace;
        letter-spacing: 0.05em;
    }

    .status-dot {
        width: 8px;
        height: 8px;
        background: var(--cyan);
        border-radius: 50%;
        box-shadow: 0 0 10px var(--cyan), 0 0 20px var(--cyan-glow);
        animation: holo-pulse 2s infinite;
    }

    @keyframes holo-pulse {
        0%, 100% { opacity: 1; transform: scale(1); box-shadow: 0 0 10px var(--cyan), 0 0 20px var(--cyan-glow); }
        50% { opacity: 0.7; transform: scale(0.9); box-shadow: 0 0 15px var(--cyan), 0 0 30px var(--cyan-glow); }
    }

    /* Scan line animation */
    @keyframes scanline {
        0% { transform: translateY(-100%); }
        100% { transform: translateY(100vh); }
    }

    /* ========== PAGE HEADER - HOLOGRAPHIC ========== */
    .page-header {
        margin-bottom: 32px;
        padding-bottom: 20px;
        border-bottom: 1px solid var(--glass-border);
        position: relative;
    }

    .page-header::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, var(--cyan) 0%, var(--electric-blue) 50%, transparent 100%);
        opacity: 0.5;
    }

    .page-header h1 {
        color: var(--text-bright);
        font-size: 32px;
        font-weight: 700;
        margin: 0 0 8px 0;
        letter-spacing: 0.05em;
        font-family: 'Orbitron', sans-serif;
        text-shadow: 0 0 20px var(--cyan-dim);
    }

    .page-header p {
        color: var(--text-secondary);
        font-size: 16px;
        margin: 0;
        font-weight: 500;
        font-family: 'Rajdhani', sans-serif;
        letter-spacing: 0.03em;
    }

    /* ========== METRIC CARDS - EXECUTIVE STYLE ========== */
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 20px;
        margin-bottom: 40px;
    }

    .metric-card {
        background: var(--white);
        border-radius: var(--radius-xl);
        padding: 24px;
        border: 1px solid var(--border-light);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--primary-500), var(--primary-400));
        opacity: 0;
        transition: opacity 0.3s ease;
    }

    .metric-card:hover {
        border-color: var(--primary-200);
        box-shadow: var(--shadow-lg), var(--shadow-glow);
        transform: translateY(-4px);
    }

    .metric-card:hover::before {
        opacity: 1;
    }

    .metric-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        margin-bottom: 18px;
    }

    .metric-icon {
        width: 48px;
        height: 48px;
        border-radius: var(--radius-md);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
    }

    .metric-icon.primary { background: linear-gradient(135deg, var(--primary-50) 0%, var(--primary-100) 100%); }
    .metric-icon.accent { background: linear-gradient(135deg, var(--warm-50) 0%, #FEF3C7 100%); }
    .metric-icon.success { background: linear-gradient(135deg, var(--accent-50) 0%, #D1FAE5 100%); }

    .metric-trend {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 5px 10px;
        background: linear-gradient(135deg, var(--accent-50) 0%, #D1FAE5 100%);
        color: var(--accent-600);
        font-size: 12px;
        font-weight: 700;
        border-radius: 20px;
    }

    .metric-content {
        margin-top: 4px;
    }

    .metric-label {
        color: var(--slate-500);
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }

    .metric-value {
        color: var(--slate-900);
        font-size: 36px;
        font-weight: 800;
        letter-spacing: -0.03em;
        line-height: 1;
    }

    .metric-footer {
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid var(--border-light);
    }

    .metric-tag {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 5px 12px;
        background: var(--slate-100);
        color: var(--slate-600);
        font-size: 12px;
        font-weight: 600;
        border-radius: 20px;
    }

    /* ========== METRIC TOOLTIPS ========== */
    .metric-card-wrapper {
        position: relative;
    }

    .metric-tooltip {
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
        color: white;
        padding: 12px 16px;
        border-radius: 12px;
        font-size: 13px;
        line-height: 1.5;
        width: 280px;
        opacity: 0;
        visibility: hidden;
        transition: all 0.3s ease;
        z-index: 1000;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        pointer-events: none;
        margin-bottom: 10px;
    }

    .metric-tooltip::after {
        content: '';
        position: absolute;
        top: 100%;
        left: 50%;
        transform: translateX(-50%);
        border: 8px solid transparent;
        border-top-color: #334155;
    }

    .metric-tooltip-title {
        font-weight: 700;
        font-size: 14px;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .metric-tooltip-text {
        opacity: 0.9;
        font-weight: 400;
    }

    .metric-card:hover .metric-tooltip {
        opacity: 1;
        visibility: visible;
        transform: translateX(-50%) translateY(-5px);
    }

    .metric-help-icon {
        position: absolute;
        top: 12px;
        right: 12px;
        width: 20px;
        height: 20px;
        background: var(--slate-100);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        color: var(--slate-400);
        cursor: help;
        transition: all 0.2s ease;
    }

    .metric-card:hover .metric-help-icon {
        background: var(--primary-100);
        color: var(--primary-600);
    }

    /* ========== SECTION ========== */
    .section {
        margin-bottom: 40px;
    }

    .section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 24px;
    }

    .section-title {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .section-title h2 {
        color: var(--slate-900);
        font-size: 20px;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.02em;
    }

    .section-badge {
        background: linear-gradient(135deg, var(--primary-50) 0%, var(--primary-100) 100%);
        color: var(--primary-700);
        font-size: 12px;
        font-weight: 700;
        padding: 5px 12px;
        border-radius: 20px;
        letter-spacing: 0.02em;
    }

    /* ========== FEATURE CARDS ========== */
    .features-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
    }

    .feature-card {
        background: var(--white);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-xl);
        padding: 24px;
        transition: all 0.3s ease;
        position: relative;
    }

    .feature-card:hover {
        border-color: var(--primary-200);
        box-shadow: var(--shadow-md);
        transform: translateY(-3px);
    }

    .feature-icon {
        width: 52px;
        height: 52px;
        border-radius: var(--radius-md);
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 16px;
        font-size: 24px;
    }

    .feature-icon.reddit { background: linear-gradient(135deg, #FF4500 0%, #FF6B35 100%); color: white; }
    .feature-icon.hn { background: linear-gradient(135deg, #FF6600 0%, #FF8533 100%); color: white; }
    .feature-icon.google { background: linear-gradient(135deg, #4285F4 0%, #5B9CF4 100%); color: white; }
    .feature-icon.ph { background: linear-gradient(135deg, #DA552F 0%, #E06B4D 100%); color: white; }

    .feature-title {
        color: var(--slate-900);
        font-size: 16px;
        font-weight: 700;
        margin: 0 0 6px 0;
        letter-spacing: -0.02em;
    }

    .feature-desc {
        color: var(--slate-500);
        font-size: 14px;
        line-height: 1.6;
        margin: 0;
    }

    /* ========== STEPS ========== */
    .steps-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 20px;
    }

    .step-card {
        background: var(--white);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-xl);
        padding: 32px 24px;
        text-align: center;
        transition: all 0.3s ease;
        position: relative;
    }

    .step-card:hover {
        border-color: var(--primary-200);
        box-shadow: var(--shadow-md);
        transform: translateY(-4px);
    }

    .step-number {
        width: 52px;
        height: 52px;
        background: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-500) 100%);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 20px auto;
        color: white;
        font-size: 22px;
        font-weight: 800;
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.3);
    }

    .step-title {
        color: var(--slate-900);
        font-size: 17px;
        font-weight: 700;
        margin: 0 0 8px 0;
        letter-spacing: -0.02em;
    }

    .step-desc {
        color: var(--slate-500);
        font-size: 14px;
        line-height: 1.6;
        margin: 0;
    }

    /* ========== BUTTONS - HOLOGRAPHIC NEON DESIGN ========== */

    /* Base button reset and foundation */
    .stButton > button {
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
        padding: 12px 24px !important;
        border-radius: 8px !important;
        cursor: pointer !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative !important;
        overflow: hidden !important;
        border: 1px solid var(--cyan) !important;
        outline: none !important;
    }

    /* Primary Button - Cyan Neon Glow */
    .stButton > button[kind="primary"],
    .stButton > button:not([kind]) {
        background: linear-gradient(135deg, rgba(0, 255, 255, 0.15) 0%, rgba(0, 139, 139, 0.15) 100%) !important;
        color: var(--cyan) !important;
        border: 1px solid var(--cyan) !important;
        box-shadow: var(--glow-cyan), inset 0 0 20px rgba(0, 255, 255, 0.1) !important;
        text-shadow: 0 0 10px var(--cyan-glow) !important;
    }

    .stButton > button[kind="primary"]:hover,
    .stButton > button:not([kind]):hover {
        background: linear-gradient(135deg, rgba(0, 255, 255, 0.25) 0%, rgba(0, 139, 139, 0.25) 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: var(--glow-intense), inset 0 0 30px rgba(0, 255, 255, 0.2) !important;
        text-shadow: 0 0 15px var(--cyan) !important;
    }

    .stButton > button[kind="primary"]:active,
    .stButton > button:not([kind]):active {
        transform: translateY(0) !important;
        box-shadow: var(--glow-cyan) !important;
    }

    /* Secondary Button - Glass Effect */
    .stButton > button[kind="secondary"] {
        background: var(--bg-glass) !important;
        color: var(--text-secondary) !important;
        border: 1px solid var(--glass-border) !important;
        box-shadow: none !important;
        backdrop-filter: blur(10px) !important;
    }

    .stButton > button[kind="secondary"]:hover {
        background: var(--bg-glass-light) !important;
        color: var(--cyan) !important;
        border-color: var(--cyan-dim) !important;
        box-shadow: var(--glow-cyan) !important;
        text-shadow: 0 0 10px var(--cyan-glow) !important;
    }

    .stButton > button[kind="secondary"]:active {
        transform: translateY(0) !important;
    }

    /* Tertiary/Ghost Button - Minimal Holographic */
    .stButton > button[kind="tertiary"] {
        background: transparent !important;
        color: var(--text-secondary) !important;
        border: 1px solid transparent !important;
        box-shadow: none !important;
        padding: 10px 16px !important;
    }

    .stButton > button[kind="tertiary"]:hover {
        background: rgba(0, 255, 255, 0.05) !important;
        color: var(--cyan) !important;
        border-color: var(--cyan-dim) !important;
    }

    /* Icon-only buttons */
    .stButton > button:has(span:only-child) {
        padding: 10px 12px !important;
        min-width: 40px !important;
    }

    /* Download buttons - Success Neon */
    .stDownloadButton > button {
        background: linear-gradient(135deg, rgba(0, 255, 136, 0.15) 0%, rgba(0, 139, 139, 0.15) 100%) !important;
        color: var(--success) !important;
        border: 1px solid var(--success) !important;
        border-radius: 8px !important;
        padding: 12px 24px !important;
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
        box-shadow: 0 0 20px var(--success-glow), inset 0 0 20px rgba(0, 255, 136, 0.1) !important;
        text-shadow: 0 0 10px var(--success-glow) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, rgba(0, 255, 136, 0.25) 0%, rgba(0, 139, 139, 0.25) 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 0 30px var(--success-glow), 0 0 60px rgba(0, 255, 136, 0.2), inset 0 0 30px rgba(0, 255, 136, 0.2) !important;
    }

    /* Link buttons - Holographic */
    .stLinkButton > a {
        background: var(--bg-glass) !important;
        color: var(--electric-blue) !important;
        border: 1px solid var(--electric-blue) !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
        text-decoration: none !important;
        transition: all 0.3s ease !important;
        box-shadow: var(--glow-blue) !important;
        text-shadow: 0 0 10px var(--electric-glow) !important;
    }

    .stLinkButton > a:hover {
        background: linear-gradient(135deg, rgba(0, 139, 139, 0.2) 0%, rgba(0, 255, 255, 0.2) 100%) !important;
        color: var(--cyan) !important;
        border-color: var(--cyan) !important;
        transform: translateY(-2px) !important;
        box-shadow: var(--glow-intense) !important;
    }

    /* Button with emoji icon - better alignment */
    .stButton > button {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
    }

    /* Disabled button state */
    .stButton > button:disabled {
        background: rgba(30, 40, 60, 0.5) !important;
        color: var(--text-dim) !important;
        border-color: rgba(100, 120, 140, 0.3) !important;
        cursor: not-allowed !important;
        transform: none !important;
        box-shadow: none !important;
        opacity: 0.5 !important;
        text-shadow: none !important;
    }

    /* Full width button refinement */
    .stButton > button[data-testid="baseButton-secondary"],
    .stButton > button[data-testid="baseButton-primary"] {
        width: 100% !important;
    }

    /* Button scan line effect */
    .stButton > button::before {
        content: '' !important;
        position: absolute !important;
        top: 0 !important;
        left: -100% !important;
        width: 100% !important;
        height: 100% !important;
        background: linear-gradient(90deg, transparent 0%, rgba(0, 255, 255, 0.1) 50%, transparent 100%) !important;
        transition: left 0.5s ease !important;
    }

    .stButton > button:hover::before {
        left: 100% !important;
    }

    /* ========== BUTTON TYPE CLASSES ========== */

    /* Success buttons - Green Neon */
    .btn-success button,
    [data-testid*="success"] button {
        background: linear-gradient(135deg, rgba(0, 255, 136, 0.15) 0%, rgba(0, 139, 139, 0.15) 100%) !important;
        color: var(--success) !important;
        border-color: var(--success) !important;
        box-shadow: 0 0 20px var(--success-glow) !important;
    }

    .btn-success button:hover,
    [data-testid*="success"] button:hover {
        background: linear-gradient(135deg, #047857 0%, #059669 50%, #10B981 100%) !important;
        box-shadow: 0 8px 25px rgba(16, 185, 129, 0.5) !important;
    }

    /* Danger buttons - Red */
    .btn-danger button,
    [data-testid*="danger"] button,
    [data-testid*="delete"] button,
    [data-testid*="clear"] button {
        background: linear-gradient(135deg, #DC2626 0%, #EF4444 50%, #F87171 100%) !important;
        box-shadow: 0 4px 15px rgba(220, 38, 38, 0.4) !important;
    }

    .btn-danger button:hover,
    [data-testid*="danger"] button:hover,
    [data-testid*="delete"] button:hover,
    [data-testid*="clear"] button:hover {
        background: linear-gradient(135deg, #B91C1C 0%, #DC2626 50%, #EF4444 100%) !important;
        box-shadow: 0 8px 25px rgba(220, 38, 38, 0.5) !important;
    }

    /* Warning buttons - Amber/Orange */
    .btn-warning button,
    [data-testid*="warning"] button {
        background: linear-gradient(135deg, #F59E0B 0%, #FBBF24 50%, #FCD34D 100%) !important;
        color: #1E293B !important;
        box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4) !important;
    }

    .btn-warning button:hover,
    [data-testid*="warning"] button:hover {
        background: linear-gradient(135deg, #D97706 0%, #F59E0B 50%, #FBBF24 100%) !important;
        box-shadow: 0 8px 25px rgba(245, 158, 11, 0.5) !important;
    }

    /* Info buttons - Cyan/Blue */
    .btn-info button,
    [data-testid*="sync"] button,
    [data-testid*="refresh"] button {
        background: linear-gradient(135deg, #0EA5E9 0%, #38BDF8 50%, #7DD3FC 100%) !important;
        box-shadow: 0 4px 15px rgba(14, 165, 233, 0.4) !important;
    }

    .btn-info button:hover,
    [data-testid*="sync"] button:hover,
    [data-testid*="refresh"] button:hover {
        background: linear-gradient(135deg, #0284C7 0%, #0EA5E9 50%, #38BDF8 100%) !important;
        box-shadow: 0 8px 25px rgba(14, 165, 233, 0.5) !important;
    }

    /* Purple/Violet buttons - Import/Export */
    .btn-purple button,
    [data-testid*="import"] button,
    [data-testid*="export"] button {
        background: linear-gradient(135deg, #8B5CF6 0%, #A78BFA 50%, #C4B5FD 100%) !important;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4) !important;
    }

    .btn-purple button:hover,
    [data-testid*="import"] button:hover,
    [data-testid*="export"] button:hover {
        background: linear-gradient(135deg, #7C3AED 0%, #8B5CF6 50%, #A78BFA 100%) !important;
        box-shadow: 0 8px 25px rgba(139, 92, 246, 0.5) !important;
    }

    /* Mini/Icon buttons */
    .btn-mini button,
    [data-testid*="mini"] button,
    [data-testid*="arrow"] button,
    [data-testid*="prev"] button,
    [data-testid*="next"] button {
        padding: 8px 12px !important;
        min-width: 42px !important;
        background: linear-gradient(135deg, #F8FAFC 0%, #FFFFFF 100%) !important;
        color: #475569 !important;
        border: 1.5px solid #E2E8F0 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
    }

    .btn-mini button:hover,
    [data-testid*="mini"] button:hover,
    [data-testid*="arrow"] button:hover,
    [data-testid*="prev"] button:hover,
    [data-testid*="next"] button:hover {
        background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%) !important;
        color: white !important;
        border-color: #4F46E5 !important;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3) !important;
    }

    /* ========== CHECKBOXES ========== */
    .stCheckbox {
        background: var(--white) !important;
        border: 1px solid var(--border-light) !important;
        border-radius: var(--radius-md) !important;
        padding: 16px 20px !important;
        margin: 6px 0 !important;
        transition: all 0.2s ease !important;
    }

    .stCheckbox:hover {
        border-color: var(--primary-300) !important;
        background: var(--primary-50) !important;
    }

    .stCheckbox label {
        font-size: 15px !important;
        font-weight: 500 !important;
        color: var(--slate-700) !important;
    }

    /* ========== TABS ========== */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--slate-100) !important;
        border-radius: var(--radius-md) !important;
        padding: 5px !important;
        gap: 4px !important;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: var(--radius-sm) !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        padding: 12px 20px !important;
        color: var(--slate-600) !important;
        transition: all 0.2s ease !important;
    }

    .stTabs [aria-selected="true"] {
        background: var(--white) !important;
        color: var(--primary-600) !important;
        font-weight: 600 !important;
        box-shadow: var(--shadow-sm) !important;
    }

    /* ========== DATA TABLE - SILVER METALLIC ========== */
    .stDataFrame {
        border: 2px solid rgba(192, 192, 192, 0.4) !important;
        border-radius: var(--radius-lg) !important;
        overflow: hidden !important;
        background: linear-gradient(135deg, rgba(55, 65, 85, 0.95) 0%, rgba(40, 50, 70, 0.95) 100%) !important;
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.1) !important;
    }

    .stDataFrame [data-testid="stDataFrameResizable"] {
        background: transparent !important;
    }

    /* ========== PROGRESS - SILVER METALLIC ========== */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #C0C0C0 0%, #808080 100%) !important;
        border-radius: 10px !important;
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.4) !important;
    }

    .stProgress > div > div {
        background: rgba(28, 28, 46, 0.8) !important;
    }

    /* ========== ALERTS - HOLOGRAPHIC ========== */
    .stSuccess, .stInfo, .stWarning, .stError {
        border-radius: var(--radius-md) !important;
        font-size: 14px !important;
        border-left-width: 4px !important;
        padding: 16px 20px !important;
        background: linear-gradient(135deg, rgba(60, 70, 90, 0.95) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        color: #E5E5E5 !important;
    }

    .stSuccess {
        background: linear-gradient(135deg, rgba(0, 80, 50, 0.5) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        border-left-color: #00FF88 !important;
    }

    .stInfo {
        background: linear-gradient(135deg, rgba(70, 80, 100, 0.5) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        border-left-color: #C0C0C0 !important;
    }

    .stWarning {
        background: linear-gradient(135deg, rgba(80, 60, 0, 0.5) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        border-left-color: #FFB800 !important;
    }

    .stError {
        background: linear-gradient(135deg, rgba(80, 30, 30, 0.5) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        border-left-color: #FF6B6B !important;
    }

    /* ========== EMPTY STATE - SILVER METALLIC ========== */
    .empty-state {
        text-align: center;
        padding: 60px 48px;
        background: linear-gradient(135deg, rgba(55, 65, 85, 0.95) 0%, rgba(40, 50, 70, 0.95) 100%);
        border: 2px dashed rgba(192, 192, 192, 0.4);
        border-radius: var(--radius-xl);
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.1);
    }

    .empty-icon {
        font-size: 56px;
        margin-bottom: 20px;
        opacity: 0.8;
        filter: drop-shadow(0 0 10px rgba(192, 192, 192, 0.3));
    }

    .empty-title {
        color: #FFFFFF;
        font-size: 20px;
        font-weight: 700;
        margin: 0 0 8px 0;
        letter-spacing: -0.02em;
        text-shadow: 0 0 15px rgba(192, 192, 192, 0.2);
    }

    .empty-desc {
        color: #C0C0C0;
        font-size: 15px;
        margin: 0 0 24px 0;
    }

    /* ========== API CARDS - SILVER METALLIC ========== */
    .api-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
    }

    .api-card {
        background: linear-gradient(135deg, rgba(55, 65, 85, 0.95) 0%, rgba(40, 50, 70, 0.95) 100%) !important;
        border: 2px solid rgba(192, 192, 192, 0.4) !important;
        border-radius: var(--radius-xl) !important;
        padding: 28px 24px !important;
        text-align: center !important;
        transition: all 0.3s ease !important;
        display: block !important;
        min-height: 140px !important;
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
        position: relative !important;
    }

    .api-card:hover {
        box-shadow: 0 0 25px rgba(192, 192, 192, 0.2), 0 8px 24px rgba(0, 0, 0, 0.4) !important;
        transform: translateY(-3px) !important;
        border-color: #C0C0C0 !important;
    }

    .api-card.connected {
        border-color: #00FF88 !important;
        background: linear-gradient(135deg, rgba(0, 80, 50, 0.4) 0%, rgba(40, 50, 70, 0.95) 100%) !important;
    }

    .api-card.connected::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #00FF88, #00CC66);
        border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    }

    .api-card.disconnected {
        border-color: rgba(192, 192, 192, 0.3) !important;
        background: linear-gradient(135deg, rgba(55, 65, 85, 0.95) 0%, rgba(40, 50, 70, 0.95) 100%) !important;
    }

    .api-icon {
        font-size: 36px !important;
        margin-bottom: 14px !important;
        display: block !important;
        filter: drop-shadow(0 0 8px rgba(192, 192, 192, 0.3)) !important;
    }

    .api-name {
        color: #FFFFFF !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        margin: 0 0 12px 0 !important;
        letter-spacing: -0.01em !important;
        display: block !important;
        text-shadow: 0 0 10px rgba(0, 255, 255, 0.2) !important;
    }

    h4.api-name {
        color: #FFFFFF !important;
        font-size: 16px !important;
        font-weight: 700 !important;
    }

    .api-status {
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        padding: 6px 14px !important;
        border-radius: 20px !important;
    }

    .api-status.connected {
        background: linear-gradient(135deg, rgba(0, 255, 136, 0.3) 0%, rgba(0, 139, 139, 0.3) 100%) !important;
        color: #00FF88 !important;
        border: 1px solid rgba(0, 255, 136, 0.5) !important;
        box-shadow: 0 0 10px rgba(0, 255, 136, 0.3) !important;
    }

    .api-status.disconnected {
        background: rgba(60, 70, 90, 0.8) !important;
        color: #A0A0A0 !important;
        border: 1px solid rgba(160, 160, 160, 0.3) !important;
    }

    /* ========== TAGS - HOLOGRAPHIC ========== */
    .tags-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }

    .tag {
        background: linear-gradient(135deg, rgba(0, 255, 255, 0.2) 0%, rgba(0, 139, 139, 0.3) 100%);
        color: #00FFFF;
        font-size: 13px;
        font-weight: 600;
        padding: 8px 14px;
        border-radius: 20px;
        border: 1px solid rgba(0, 255, 255, 0.4);
        transition: all 0.2s ease;
        box-shadow: 0 0 10px rgba(0, 255, 255, 0.15);
    }

    .tag:hover {
        background: linear-gradient(135deg, rgba(0, 255, 255, 0.4) 0%, rgba(0, 139, 139, 0.5) 100%);
        color: #FFFFFF;
        border-color: #00FFFF;
        transform: translateY(-2px);
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
    }

    /* ========== LOADING ========== */
    .loading-box {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 18px 20px;
        background: var(--slate-50);
        border-radius: var(--radius-md);
        border: 1px solid var(--border-light);
        margin: 10px 0;
    }

    .spinner {
        width: 22px;
        height: 22px;
        border: 2px solid var(--border-light);
        border-top-color: var(--primary-500);
        border-radius: 50%;
        animation: spin 0.7s linear infinite;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    .loading-text {
        color: var(--slate-700);
        font-size: 15px;
        font-weight: 500;
    }

    /* ========== RESULTS ========== */
    .results-box {
        display: flex;
        gap: 24px;
        padding: 20px 24px;
        background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        margin: 20px 0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }

    .result-item {
        text-align: center;
        padding: 12px 20px;
        background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%);
        border-radius: 12px;
        min-width: 100px;
    }

    .result-value {
        font-size: 32px;
        font-weight: 800;
        line-height: 1;
        letter-spacing: -0.03em;
    }

    .result-value.green { color: #059669; }
    .result-value.blue { color: #2563EB; }
    .result-value.orange { color: #EA580C; }

    .result-label {
        color: #475569;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 6px;
    }

    /* ========== MODERN LEAD CARDS ========== */
    .lead-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 0;
        margin: 16px 0;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        transition: all 0.3s ease;
    }

    .lead-card:hover {
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
        transform: translateY(-2px);
    }

    .lead-card-header {
        background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%);
        padding: 16px 20px;
        border-bottom: 1px solid #E2E8F0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
    }

    .lead-card-grade {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 56px;
        height: 56px;
        border-radius: 12px;
        font-size: 24px;
        font-weight: 800;
        flex-shrink: 0;
    }

    .lead-card-title-area {
        flex: 1;
        min-width: 0;
    }

    .lead-card-title {
        font-size: 15px;
        font-weight: 700;
        color: #1E293B;
        margin: 0 0 4px 0;
        line-height: 1.3;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .lead-card-meta {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
    }

    .lead-source-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.02em;
    }

    .lead-source-badge.reddit { background: #FF45000D; color: #FF4500; border: 1px solid #FF450033; }
    .lead-source-badge.hackernews { background: #FF66000D; color: #FF6600; border: 1px solid #FF660033; }
    .lead-source-badge.google { background: #4285F40D; color: #4285F4; border: 1px solid #4285F433; }
    .lead-source-badge.indeed { background: #2164F30D; color: #2164F3; border: 1px solid #2164F333; }
    .lead-source-badge.yelp { background: #D324150D; color: #D32415; border: 1px solid #D3241533; }
    .lead-source-badge.maps { background: #34A8530D; color: #34A853; border: 1px solid #34A85333; }

    .lead-industry-tag {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 10px;
        background: #8B5CF60D;
        color: #7C3AED;
        border: 1px solid #8B5CF633;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
    }

    .lead-card-body {
        padding: 20px;
    }

    .lead-scores-row {
        display: flex;
        gap: 12px;
        margin-bottom: 16px;
    }

    .lead-score-mini {
        flex: 1;
        padding: 12px;
        border-radius: 10px;
        text-align: center;
    }

    .lead-score-mini.pain { background: linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%); }
    .lead-score-mini.intent { background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%); }
    .lead-score-mini.fit { background: linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%); }

    .lead-score-mini-icon {
        font-size: 18px;
        margin-bottom: 4px;
    }

    .lead-score-mini-value {
        font-size: 20px;
        font-weight: 800;
        line-height: 1;
    }

    .lead-score-mini.pain .lead-score-mini-value { color: #DC2626; }
    .lead-score-mini.intent .lead-score-mini-value { color: #D97706; }
    .lead-score-mini.fit .lead-score-mini-value { color: #2563EB; }

    .lead-score-mini-label {
        font-size: 9px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 4px;
    }

    .lead-score-mini.pain .lead-score-mini-label { color: #991B1B; }
    .lead-score-mini.intent .lead-score-mini-label { color: #92400E; }
    .lead-score-mini.fit .lead-score-mini-label { color: #1E40AF; }

    .lead-keywords-section {
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid #E2E8F0;
    }

    .lead-keywords-title {
        font-size: 10px;
        font-weight: 700;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }

    .lead-keyword-tag {
        display: inline-block;
        padding: 4px 10px;
        background: #F1F5F9;
        color: #475569;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 500;
        margin: 2px 4px 2px 0;
    }

    .lead-content-preview {
        margin-top: 16px;
        padding: 16px;
        background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%);
        border-radius: 10px;
        border-left: 3px solid #3B82F6;
    }

    .lead-content-text {
        font-size: 13px;
        line-height: 1.6;
        color: #334155;
        margin: 0;
    }

    .lead-card-footer {
        padding: 16px 20px;
        background: #F8FAFC;
        border-top: 1px solid #E2E8F0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
    }

    .lead-action-text {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        font-weight: 600;
    }

    .lead-view-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        color: white !important;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        text-decoration: none !important;
        transition: all 0.2s ease;
    }

    .lead-view-btn:hover {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }

    /* Results Section Header */
    .results-section-header {
        background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 20px 24px;
        margin: 32px 0 16px 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .results-section-title {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .results-section-title h2 {
        margin: 0;
        font-size: 22px;
        font-weight: 700;
        color: #1E293B;
    }

    .results-count-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        color: white;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
    }

    /* ========== STATS BAR ========== */
    .stats-bar {
        display: flex;
        gap: 40px;
        padding: 20px 0;
        margin-bottom: 28px;
        border-bottom: 1px solid var(--border-light);
    }

    .stat-item {
        display: flex;
        align-items: baseline;
        gap: 8px;
    }

    .stat-value {
        font-size: 28px;
        font-weight: 800;
        color: var(--slate-900);
        letter-spacing: -0.03em;
    }

    .stat-label {
        font-size: 15px;
        color: var(--slate-500);
        font-weight: 500;
    }

    /* ========== EXPANDER - DIGITAL SILVER METALLIC ========== */
    .streamlit-expanderHeader {
        font-size: 15px !important;
        font-weight: 600 !important;
        background: linear-gradient(135deg, rgba(60, 70, 90, 0.95) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        border: 2px solid rgba(192, 192, 192, 0.5) !important;
        border-radius: var(--radius-md) !important;
        transition: all 0.2s ease !important;
        padding: 14px 18px !important;
        color: #E5E5E5 !important;
        backdrop-filter: blur(10px) !important;
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
    }

    .streamlit-expanderHeader:hover {
        border-color: #C0C0C0 !important;
        background: linear-gradient(135deg, rgba(100, 110, 130, 0.6) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        box-shadow: 0 0 20px rgba(192, 192, 192, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
        color: #FFFFFF !important;
    }

    [data-testid="stExpander"] {
        background: transparent !important;
        border: none !important;
    }

    [data-testid="stExpander"] > div:first-child {
        background: linear-gradient(135deg, rgba(60, 70, 90, 0.95) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        border: 2px solid rgba(192, 192, 192, 0.5) !important;
        border-radius: 12px !important;
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.1) !important;
    }

    [data-testid="stExpander"] > div > div {
        background: linear-gradient(135deg, rgba(50, 60, 80, 0.95) 0%, rgba(35, 45, 65, 0.95) 100%) !important;
        border-color: rgba(192, 192, 192, 0.3) !important;
    }

    /* ========== FORM INPUTS - DIGITAL SILVER METALLIC ========== */
    /* Windows/cards use SILVER borders instead of cyan */

    /* Labels - Silver digital */
    .stSelectbox label, .stTextInput label, .stTextArea label, .stNumberInput label, .stMultiSelect label {
        color: #E5E5E5 !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        margin-bottom: 8px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        text-shadow: 0 0 10px rgba(192, 192, 192, 0.3) !important;
    }

    /* SELECT BOX - Silver metallic border */
    .stSelectbox > div > div {
        background: linear-gradient(135deg, rgba(60, 70, 90, 0.95) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        border: 2px solid rgba(192, 192, 192, 0.6) !important;
        border-radius: var(--radius-md) !important;
        font-size: 15px !important;
        color: #FFFFFF !important;
        padding: 6px 10px !important;
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
    }

    .stSelectbox > div > div:hover {
        border-color: #E5E5E5 !important;
        box-shadow: 0 0 20px rgba(192, 192, 192, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
    }

    /* Text Input - Silver metallic */
    .stTextInput > div > div > input {
        background: linear-gradient(135deg, rgba(60, 70, 90, 0.95) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        border: 2px solid rgba(192, 192, 192, 0.6) !important;
        color: #FFFFFF !important;
        border-radius: var(--radius-md) !important;
        padding: 12px 14px !important;
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #E5E5E5 !important;
        box-shadow: 0 0 20px rgba(192, 192, 192, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
        outline: none !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: rgba(192, 192, 192, 0.7) !important;
    }

    /* Text Area - Silver metallic */
    .stTextArea > div > div > textarea {
        background: linear-gradient(135deg, rgba(60, 70, 90, 0.95) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        border: 2px solid rgba(192, 192, 192, 0.6) !important;
        color: #FFFFFF !important;
        border-radius: var(--radius-md) !important;
        padding: 12px 14px !important;
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
    }

    .stTextArea > div > div > textarea:focus {
        border-color: #E5E5E5 !important;
        box-shadow: 0 0 20px rgba(192, 192, 192, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
    }

    .stTextArea > div > div > textarea::placeholder {
        color: rgba(192, 192, 192, 0.7) !important;
    }

    /* Number Input - Silver metallic */
    .stNumberInput > div > div > input {
        background: linear-gradient(135deg, rgba(60, 70, 90, 0.95) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        border: 2px solid rgba(192, 192, 192, 0.6) !important;
        color: #FFFFFF !important;
        border-radius: var(--radius-md) !important;
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.1) !important;
    }

    .stNumberInput > div > div > input:focus {
        border-color: #E5E5E5 !important;
        box-shadow: 0 0 20px rgba(192, 192, 192, 0.25) !important;
    }

    /* Multiselect - Silver metallic */
    .stMultiSelect > div > div {
        background: linear-gradient(135deg, rgba(60, 70, 90, 0.95) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        border: 2px solid rgba(192, 192, 192, 0.6) !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.1) !important;
    }

    .stMultiSelect [data-baseweb="tag"] {
        background: linear-gradient(135deg, rgba(192, 192, 192, 0.2) 0%, rgba(128, 128, 128, 0.3) 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(192, 192, 192, 0.5) !important;
        box-shadow: 0 0 10px rgba(192, 192, 192, 0.2) !important;
    }

    /* Checkbox - Silver metallic */
    .stCheckbox > label {
        color: #E5E5E5 !important;
        font-weight: 500 !important;
    }

    .stCheckbox > label > div[data-testid="stCheckbox"] > div {
        background: linear-gradient(135deg, rgba(60, 70, 90, 0.95) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        border: 2px solid rgba(192, 192, 192, 0.6) !important;
    }

    .stCheckbox > label > div[data-testid="stCheckbox"] > div:hover {
        border-color: #E5E5E5 !important;
    }

    /* Radio - Silver metallic */
    .stRadio > div {
        background: transparent !important;
    }

    .stRadio > div > label {
        color: #E5E5E5 !important;
        background: linear-gradient(135deg, rgba(60, 70, 90, 0.9) 0%, rgba(45, 55, 75, 0.9) 100%) !important;
        border: 2px solid rgba(192, 192, 192, 0.5) !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        margin: 4px 0 !important;
        box-shadow: 0 0 10px rgba(192, 192, 192, 0.08) !important;
    }

    .stRadio > div > label:hover {
        border-color: #C0C0C0 !important;
        background: linear-gradient(135deg, rgba(100, 110, 130, 0.9) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.15) !important;
    }

    .stRadio > div > label[data-checked="true"] {
        border-color: #E5E5E5 !important;
        background: linear-gradient(135deg, rgba(120, 130, 150, 0.5) 0%, rgba(80, 90, 110, 0.6) 100%) !important;
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.2) !important;
    }

    /* Date Input - Silver metallic */
    .stDateInput > div > div > input {
        background: linear-gradient(135deg, rgba(60, 70, 90, 0.95) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        border: 2px solid rgba(192, 192, 192, 0.6) !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.1) !important;
    }

    .stDateInput > div > div > input:focus {
        border-color: #E5E5E5 !important;
        box-shadow: 0 0 20px rgba(192, 192, 192, 0.25) !important;
    }

    /* Slider - Silver metallic */
    .stSlider > div > div > div {
        background: rgba(192, 192, 192, 0.3) !important;
    }

    .stSlider > div > div > div > div {
        background: #C0C0C0 !important;
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.5) !important;
    }

    /* ========== SELECTBOX DROPDOWN - SILVER METALLIC ========== */
    [data-baseweb="select"] span,
    [data-baseweb="select"] div {
        color: #FFFFFF !important;
    }

    [data-baseweb="menu"] {
        background: linear-gradient(135deg, rgba(45, 55, 75, 0.98) 0%, rgba(28, 28, 46, 0.98) 100%) !important;
        border-radius: var(--radius-md) !important;
        border: 2px solid rgba(192, 192, 192, 0.5) !important;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5), 0 0 20px rgba(192, 192, 192, 0.1) !important;
        backdrop-filter: blur(20px) !important;
    }

    [data-baseweb="menu"] li {
        color: #E5E5E5 !important;
        padding: 12px 16px !important;
        transition: all 0.2s ease !important;
    }

    [data-baseweb="menu"] li:hover {
        background: linear-gradient(135deg, rgba(120, 130, 150, 0.4) 0%, rgba(80, 90, 110, 0.5) 100%) !important;
        color: #FFFFFF !important;
    }

    /* ========== MAIN AREA TEXT - HOLOGRAPHIC ========== */
    .main p, .main span, .main label, .main div {
        color: #C0C0C0;
    }

    .main h1, .main h2, .main h3, .main h4 {
        color: #FFFFFF !important;
        text-shadow: 0 0 15px rgba(192, 192, 192, 0.2) !important;
    }

    /* ========== SPINNER ========== */
    .stSpinner > div {
        border-top-color: #C0C0C0 !important;
    }

    /* ========== SCROLLBAR - SILVER METALLIC ========== */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }

    ::-webkit-scrollbar-track {
        background: rgba(28, 28, 46, 0.8);
        border-radius: 5px;
    }

    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, rgba(192, 192, 192, 0.4) 0%, rgba(128, 128, 128, 0.4) 100%);
        border-radius: 5px;
        border: 1px solid rgba(192, 192, 192, 0.3);
    }

    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, rgba(192, 192, 192, 0.6) 0%, rgba(128, 128, 128, 0.6) 100%);
    }

    /* ========== ENHANCED CHECKBOX STYLING - HOLOGRAPHIC ========== */
    .stCheckbox > label {
        color: #E5E5E5 !important;
        font-weight: 500 !important;
    }

    .stCheckbox > label > div {
        color: #E5E5E5 !important;
    }

    .stCheckbox > label > div > p,
    .stCheckbox > label > div > span {
        color: #E5E5E5 !important;
        font-weight: 500 !important;
    }

    .stCheckbox [data-testid="stMarkdownContainer"] p {
        color: #E5E5E5 !important;
    }

    /* ========== ENHANCED ALERTS - SILVER METALLIC ========== */
    .stAlert {
        border-radius: var(--radius-lg) !important;
        padding: 18px 22px !important;
        border: 2px solid rgba(192, 192, 192, 0.4) !important;
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.1) !important;
        background: linear-gradient(135deg, rgba(60, 70, 90, 0.95) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
    }

    .stAlert > div {
        color: #E5E5E5 !important;
        font-size: 14px !important;
    }

    [data-testid="stAlert"] {
        border-radius: var(--radius-lg) !important;
        border-left: 4px solid #C0C0C0 !important;
        background: linear-gradient(135deg, rgba(60, 70, 90, 0.95) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
    }

    [data-baseweb="notification"] {
        border-radius: var(--radius-lg) !important;
        background: linear-gradient(135deg, rgba(100, 110, 130, 0.3) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        border-left: 4px solid #C0C0C0 !important;
    }

    [data-baseweb="notification"] [data-testid="stMarkdownContainer"] p {
        color: #E5E5E5 !important;
        font-weight: 500 !important;
    }

    /* Info alert styling */
    .element-container:has([data-testid="stAlert"]) [role="alert"] {
        background: linear-gradient(135deg, rgba(60, 70, 90, 0.95) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        border-left-color: #C0C0C0 !important;
        border-radius: var(--radius-lg) !important;
        padding: 18px 22px !important;
    }

    /* ========== CONTAINERS & CARDS - SILVER METALLIC ========== */
    [data-testid="stVerticalBlock"] > div:has(> [data-testid="stHorizontalBlock"]) {
        background: linear-gradient(135deg, rgba(55, 65, 85, 0.95) 0%, rgba(40, 50, 70, 0.95) 100%);
        border-radius: var(--radius-xl);
        padding: 24px;
        border: 2px solid rgba(192, 192, 192, 0.4);
        margin: 16px 0;
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.1);
    }

    /* File uploader styling */
    .stFileUploader {
        background: linear-gradient(135deg, rgba(60, 70, 90, 0.95) 0%, rgba(45, 55, 75, 0.95) 100%) !important;
        border: 2px dashed rgba(192, 192, 192, 0.5) !important;
        border-radius: var(--radius-lg) !important;
        padding: 32px !important;
        transition: all 0.2s ease !important;
    }

    .stFileUploader:hover {
        border-color: #C0C0C0 !important;
        background: linear-gradient(135deg, rgba(100, 110, 130, 0.3) 0%, rgba(60, 70, 90, 0.95) 100%) !important;
        box-shadow: 0 0 20px rgba(192, 192, 192, 0.15) !important;
    }

    /* Divider styling */
    hr {
        border: none !important;
        border-top: 1px solid rgba(192, 192, 192, 0.3) !important;
        margin: 24px 0 !important;
    }

    /* ========== STREAMLIT NATIVE TITLES - HOLOGRAPHIC ========== */
    .main h1 {
        color: #FFFFFF !important;
        font-size: 32px !important;
        font-weight: 800 !important;
        letter-spacing: -0.03em !important;
        margin-bottom: 8px !important;
        text-shadow: 0 0 20px rgba(0, 255, 255, 0.3) !important;
    }

    .main h2 {
        color: #E5E5E5 !important;
        font-size: 24px !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        text-shadow: 0 0 15px rgba(0, 255, 255, 0.2) !important;
    }

    .main h3 {
        color: #E5E5E5 !important;
        font-size: 20px !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        text-shadow: 0 0 10px rgba(0, 255, 255, 0.2) !important;
    }

    /* Caption styling */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: #A0A0A0 !important;
        font-size: 15px !important;
        font-weight: 500 !important;
    }

    /* ========== FINAL POLISH - HOLOGRAPHIC ========== */
    .stMarkdown {
        color: #C0C0C0 !important;
    }

    /* Smooth transitions for all interactive elements */
    button, input, select, textarea, a {
        transition: all 0.2s ease !important;
    }

    /* ========================================================================
       MOBILE RESPONSIVE DESIGN - Premium Mobile Experience
       Complete rewrite for stability and visual perfection
       ======================================================================== */

    /* ===== MOBILE FIRST - BASE FIXES ===== */
    * {
        -webkit-tap-highlight-color: transparent;
        -webkit-touch-callout: none;
    }

    /* Prevent horizontal scroll on all devices */
    html, body {
        overflow-x: hidden !important;
        width: 100% !important;
        max-width: 100vw !important;
    }

    .stApp {
        overflow-x: hidden !important;
    }

    /* ===== TABLET (max-width: 1024px) ===== */
    @media screen and (max-width: 1024px) {
        .main .block-container {
            padding: 1rem 1rem !important;
            max-width: 100% !important;
        }

        /* Force 2 columns max on tablet */
        div[style*="grid-template-columns"] {
            grid-template-columns: repeat(2, 1fr) !important;
        }
    }

    /* ===== MOBILE (max-width: 768px) ===== */
    @media screen and (max-width: 768px) {
        /* Hide unnecessary Streamlit elements */
        #MainMenu, footer, header, .stDeployButton,
        [data-testid="collapsedControl"],
        .viewerBadge_container__1QSob {
            display: none !important;
            visibility: hidden !important;
        }

        /* MAIN CONTAINER - Full width, no overflow */
        html, body {
            overflow-x: hidden !important;
            width: 100% !important;
            max-width: 100vw !important;
        }

        .main, [data-testid="stMain"] {
            width: 100% !important;
            max-width: 100vw !important;
            overflow-x: hidden !important;
            padding: 0 !important;
        }

        .main .block-container {
            padding: 10px 12px !important;
            max-width: 100% !important;
            width: 100% !important;
            overflow-x: hidden !important;
            box-sizing: border-box !important;
        }

        /* Remove grid pattern on mobile for performance */
        .stApp::before {
            display: none !important;
        }

        /* SIDEBAR - Clean mobile drawer */
        [data-testid="stSidebar"] {
            width: 85vw !important;
            min-width: 280px !important;
            max-width: 320px !important;
            background: linear-gradient(180deg, #1C1C2E 0%, #0A0A14 100%) !important;
            border-right: 1px solid rgba(0, 255, 255, 0.2) !important;
        }

        [data-testid="stSidebar"] > div {
            width: 100% !important;
            padding: 12px 10px !important;
        }

        /* TYPOGRAPHY - Mobile optimized */
        h1, .stMarkdown h1, [data-testid="stMarkdownContainer"] h1 {
            font-size: 20px !important;
            line-height: 1.3 !important;
            word-wrap: break-word !important;
            margin-bottom: 8px !important;
        }

        h2, .stMarkdown h2, [data-testid="stMarkdownContainer"] h2 {
            font-size: 17px !important;
            margin-bottom: 6px !important;
        }

        h3, .stMarkdown h3, [data-testid="stMarkdownContainer"] h3 {
            font-size: 15px !important;
            margin-bottom: 4px !important;
        }

        p, span, label, div, li {
            font-size: 14px !important;
            line-height: 1.5 !important;
        }

        /* FORCE ALL GRIDS TO STACK - Critical for mobile */
        div[style*="grid-template-columns"],
        div[style*="display: grid"] {
            display: flex !important;
            flex-direction: column !important;
            gap: 10px !important;
            width: 100% !important;
        }

        /* ALL COLUMNS STACK */
        [data-testid="column"],
        .stColumn,
        div[data-testid="stHorizontalBlock"] > div {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            max-width: 100% !important;
        }

        .stHorizontalBlock,
        [data-testid="stHorizontalBlock"],
        div[data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 10px !important;
            width: 100% !important;
        }

        /* METRIC CARDS - Full width */
        .holo-metric-card,
        div[style*="background: rgba"][style*="border-radius"] {
            width: 100% !important;
            min-width: 0 !important;
            max-width: 100% !important;
            padding: 14px !important;
            margin: 0 0 10px 0 !important;
            box-sizing: border-box !important;
            transform: none !important;
            transition: none !important;
        }

        /* HOLOGRAPHIC HEADERS - Mobile optimized */
        div[style*="padding: 32px"] {
            padding: 16px !important;
        }

        div[style*="font-size: 32px"],
        div[style*="font-size: 28px"] {
            font-size: 20px !important;
        }

        /* TOOLTIPS - Hide on mobile */
        .holo-tooltip,
        div[style*="position: absolute"][style*="opacity"] {
            display: none !important;
            visibility: hidden !important;
        }

        /* BUTTONS - Full width, touch friendly */
        .stButton {
            width: 100% !important;
        }

        .stButton > button,
        .stDownloadButton > button,
        button[kind="primary"],
        button[kind="secondary"] {
            width: 100% !important;
            min-height: 48px !important;
            font-size: 14px !important;
            padding: 12px 16px !important;
            border-radius: 10px !important;
            touch-action: manipulation !important;
            -webkit-tap-highlight-color: transparent !important;
        }

        /* Link buttons */
        .stLinkButton > a {
            width: 100% !important;
            min-height: 48px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        /* INPUT FIELDS - Mobile optimized, prevent zoom */
        .stTextInput > div > div > input,
        .stSelectbox > div > div,
        .stSelectbox > div > div > div,
        .stMultiSelect > div > div,
        .stTextArea > div > div > textarea,
        .stNumberInput > div > div > input,
        input, select, textarea {
            min-height: 48px !important;
            font-size: 16px !important;
            padding: 12px !important;
            border-radius: 10px !important;
            width: 100% !important;
            box-sizing: border-box !important;
            -webkit-appearance: none !important;
        }

        /* Select box dropdown */
        .stSelectbox > div,
        .stMultiSelect > div {
            width: 100% !important;
        }

        /* SLIDER - Touch friendly */
        .stSlider > div {
            padding: 10px 0 !important;
        }

        .stSlider [data-baseweb="slider"] {
            height: 40px !important;
        }

        /* TABS - Horizontal scroll */
        .stTabs [data-baseweb="tab-list"] {
            display: flex !important;
            overflow-x: auto !important;
            overflow-y: hidden !important;
            -webkit-overflow-scrolling: touch !important;
            scrollbar-width: none !important;
            flex-wrap: nowrap !important;
            gap: 4px !important;
            padding-bottom: 8px !important;
        }

        .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
            display: none !important;
        }

        .stTabs [data-baseweb="tab"] {
            flex-shrink: 0 !important;
            padding: 10px 14px !important;
            font-size: 12px !important;
            white-space: nowrap !important;
            min-height: 44px !important;
        }

        /* RADIO buttons horizontal - scroll */
        .stRadio > div[role="radiogroup"] {
            flex-wrap: nowrap !important;
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important;
            padding-bottom: 8px !important;
        }

        .stRadio > div[role="radiogroup"]::-webkit-scrollbar {
            display: none !important;
        }

        /* EXPANDERS */
        .streamlit-expanderHeader {
            padding: 14px !important;
            font-size: 14px !important;
        }

        [data-testid="stExpander"] {
            width: 100% !important;
        }

        /* DATA FRAMES/TABLES */
        .stDataFrame,
        [data-testid="stDataFrame"] {
            width: 100% !important;
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important;
        }

        /* CHECKBOXES & RADIO - Touch targets */
        .stCheckbox > label,
        .stRadio > div > label {
            min-height: 44px !important;
            padding: 10px 8px !important;
            display: flex !important;
            align-items: center !important;
        }

        /* ALERTS */
        .stAlert, [data-testid="stAlert"] {
            padding: 12px !important;
            font-size: 13px !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }

        /* ALL INLINE STYLE CARDS */
        div[style*="border-radius: 16px"],
        div[style*="border-radius: 12px"],
        div[style*="border-radius: 20px"] {
            width: 100% !important;
            max-width: 100% !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
            margin-left: 0 !important;
            margin-right: 0 !important;
        }

        /* FLEX CONTAINERS - Force column */
        div[style*="display: flex"][style*="justify-content: space-between"],
        div[style*="display: flex"][style*="gap: 24px"],
        div[style*="display: flex"][style*="gap: 16px"],
        div[style*="display: flex"][style*="gap: 12px"] {
            flex-direction: column !important;
            align-items: stretch !important;
            gap: 10px !important;
            width: 100% !important;
        }

        /* Job Changes cards specific */
        .job-change-card,
        div[class*="job-change"] {
            width: 100% !important;
            padding: 14px !important;
        }

        .job-change-card div[style*="grid-template-columns"] {
            display: flex !important;
            flex-direction: column !important;
        }

        /* Opportunity badges */
        .opp-gold, .opp-silver, .opp-bronze,
        .days-badge {
            font-size: 11px !important;
            padding: 4px 10px !important;
        }

        /* STAT CARDS */
        div[style*="text-align: center"][style*="border-radius"] {
            padding: 12px !important;
        }

        div[style*="font-family: 'Orbitron'"][style*="font-size: 28px"] {
            font-size: 22px !important;
        }

        /* METRICS DISPLAY */
        [data-testid="stMetric"] {
            padding: 10px !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 20px !important;
        }

        [data-testid="stMetricLabel"] {
            font-size: 11px !important;
        }

        /* IMAGES */
        img {
            max-width: 100% !important;
            height: auto !important;
        }

        /* CODE BLOCKS */
        pre, code {
            white-space: pre-wrap !important;
            word-break: break-word !important;
            max-width: 100% !important;
            overflow-x: auto !important;
            font-size: 12px !important;
        }

        /* DIVIDERS */
        hr, .stDivider {
            margin: 12px 0 !important;
        }

        /* LOGO in sidebar - smaller */
        .logo-section {
            padding: 16px !important;
        }

        .logo-title {
            font-size: 16px !important;
        }

        .logo-icon {
            width: 36px !important;
            height: 36px !important;
        }

        /* User card smaller */
        .user-card {
            margin: 10px !important;
            padding: 12px !important;
        }

        /* Nav label */
        .nav-label {
            padding: 16px 16px 8px 16px !important;
            font-size: 9px !important;
        }

        /* Sidebar navigation items */
        [data-testid="stSidebar"] .stRadio > div > label {
            padding: 12px 14px !important;
            font-size: 13px !important;
        }
    }

    /* ===== SMALL MOBILE (max-width: 480px) ===== */
    @media screen and (max-width: 480px) {
        .main .block-container {
            padding: 8px !important;
        }

        h1, .stMarkdown h1 {
            font-size: 18px !important;
        }

        h2, .stMarkdown h2 {
            font-size: 15px !important;
        }

        h3, .stMarkdown h3 {
            font-size: 13px !important;
        }

        p, span, label, div {
            font-size: 13px !important;
        }

        .stButton > button {
            min-height: 44px !important;
            font-size: 13px !important;
            padding: 10px 12px !important;
        }

        .stTabs [data-baseweb="tab"] {
            padding: 8px 10px !important;
            font-size: 11px !important;
        }

        [data-testid="stSidebar"] {
            width: 100vw !important;
            min-width: 100vw !important;
            max-width: 100vw !important;
        }

        /* Even smaller fonts for stats */
        div[style*="font-family: 'Orbitron'"][style*="font-size"] {
            font-size: 18px !important;
        }

        /* Holographic headers */
        div[style*="padding: 32px"],
        div[style*="padding: 24px"] {
            padding: 12px !important;
        }
    }

    /* ===== TOUCH DEVICES ===== */
    @media (hover: none) and (pointer: coarse) {
        /* Disable all hover transforms */
        *:hover {
            transform: none !important;
        }

        /* Remove animations */
        .holo-metric-card,
        .stButton > button,
        [data-testid="stExpander"],
        .job-change-card,
        .warming-card {
            transition: none !important;
            transform: none !important;
        }

        /* Disable glow animations */
        @keyframes gold-pulse { }
        @keyframes urgent-pulse { }
        @keyframes scanline { }

        /* Larger touch targets */
        button, a, input, select, textarea,
        [role="button"], [role="tab"], [role="checkbox"],
        [role="radio"], [role="link"] {
            min-height: 44px !important;
            min-width: 44px !important;
        }

        /* No sticky hover states */
        .stButton > button:hover,
        .stButton > button:focus {
            transform: none !important;
            box-shadow: none !important;
        }
    }

    /* ===== LANDSCAPE MOBILE ===== */
    @media screen and (max-width: 900px) and (orientation: landscape) {
        .main .block-container {
            padding: 8px 16px !important;
        }

        [data-testid="stSidebar"] {
            width: 220px !important;
            min-width: 220px !important;
        }

        /* Allow 2 columns in landscape */
        div[style*="display: grid"],
        [data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns: repeat(2, 1fr) !important;
            flex-direction: row !important;
        }

        [data-testid="column"] {
            width: auto !important;
            min-width: 0 !important;
            max-width: none !important;
        }
    }

    /* ===== SAFE AREA (iPhone notch) ===== */
    @supports (padding: env(safe-area-inset-bottom)) {
        .main .block-container {
            padding-bottom: calc(12px + env(safe-area-inset-bottom)) !important;
            padding-left: calc(12px + env(safe-area-inset-left)) !important;
            padding-right: calc(12px + env(safe-area-inset-right)) !important;
        }

        [data-testid="stSidebar"] {
            padding-top: env(safe-area-inset-top) !important;
            padding-left: env(safe-area-inset-left) !important;
        }
    }

    /* ===== PREVENT ZOOM ON INPUT FOCUS (iOS) ===== */
    @media screen and (max-width: 768px) {
        input, select, textarea {
            font-size: 16px !important;
        }

        /* Prevent double-tap zoom */
        * {
            touch-action: manipulation !important;
        }
    }

    /* ===== REDUCED MOTION ===== */
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation: none !important;
            transition: none !important;
            transform: none !important;
        }
    }

    /* ===== HIGH CONTRAST MODE ===== */
    @media (prefers-contrast: high) {
        .holo-metric-card,
        .holo-tooltip,
        [data-testid="stSidebar"] {
            border-width: 2px !important;
        }

        .tooltip-content,
        p, span {
            color: #FFFFFF !important;
        }
    }

    /* ===== PRINT STYLES ===== */
    @media print {
        [data-testid="stSidebar"],
        .stButton,
        .stTabs [data-baseweb="tab-list"] {
            display: none !important;
        }

        .main .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }

        .holo-metric-card {
            border: 1px solid #000 !important;
            background: #fff !important;
            color: #000 !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }
    }
</style>

<script>
// Dynamic button styling based on content
function styleButtons() {
    const buttons = document.querySelectorAll('.stButton > button');

    buttons.forEach(btn => {
        const text = btn.textContent.toLowerCase();
        const parent = btn.closest('.stButton');

        // Remove existing style classes
        parent.classList.remove('btn-success', 'btn-danger', 'btn-warning', 'btn-info', 'btn-purple', 'btn-mini');

        // Success buttons (green)
        if (text.includes('save') || text.includes('keep') || text.includes('✓') || text.includes('💾') ||
            text.includes('update') || text.includes('confirm')) {
            parent.classList.add('btn-success');
        }
        // Danger buttons (red)
        else if (text.includes('delete') || text.includes('clear') || text.includes('remove') ||
                 text.includes('🗑')) {
            parent.classList.add('btn-danger');
        }
        // Warning buttons (amber)
        else if (text.includes('view') || text.includes('crm') || text.includes('results') ||
                 text.includes('👁')) {
            parent.classList.add('btn-warning');
        }
        // Info buttons (cyan)
        else if (text.includes('sync') || text.includes('refresh') || text.includes('load') ||
                 text.includes('🔄')) {
            parent.classList.add('btn-info');
        }
        // Purple buttons
        else if (text.includes('import') || text.includes('export') || text.includes('📥') ||
                 text.includes('📤')) {
            parent.classList.add('btn-purple');
        }
        // Mini/Icon buttons
        else if (text === '⬅️' || text === '➡️' || text === '👁️' || text === '🔄' ||
                 text.length <= 3) {
            parent.classList.add('btn-mini');
        }
    });
}

// Run on load and periodically to catch dynamically added buttons
styleButtons();
const observer = new MutationObserver(styleButtons);
observer.observe(document.body, { childList: true, subtree: true });

// ========== MOBILE ENHANCEMENTS ==========

// Add viewport meta for proper mobile scaling
(function() {
    // Viewport meta
    if (!document.querySelector('meta[name="viewport"]')) {
        const viewport = document.createElement('meta');
        viewport.name = 'viewport';
        viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes, viewport-fit=cover';
        document.head.appendChild(viewport);
    }

    // Theme color for mobile browser chrome
    if (!document.querySelector('meta[name="theme-color"]')) {
        const themeColor = document.createElement('meta');
        themeColor.name = 'theme-color';
        themeColor.content = '#1C1C2E';
        document.head.appendChild(themeColor);
    }

    // iOS PWA support
    if (!document.querySelector('meta[name="apple-mobile-web-app-capable"]')) {
        const appleMeta = document.createElement('meta');
        appleMeta.name = 'apple-mobile-web-app-capable';
        appleMeta.content = 'yes';
        document.head.appendChild(appleMeta);

        const appleStatus = document.createElement('meta');
        appleStatus.name = 'apple-mobile-web-app-status-bar-style';
        appleStatus.content = 'black-translucent';
        document.head.appendChild(appleStatus);
    }

    // Prevent overscroll bounce on iOS
    document.body.style.overscrollBehavior = 'none';

    // Fix iOS 100vh issue
    function setVH() {
        const vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty('--vh', vh + 'px');
    }
    setVH();
    window.addEventListener('resize', setVH);
    window.addEventListener('orientationchange', function() {
        setTimeout(setVH, 100);
    });
})();
</script>
""", unsafe_allow_html=True)

# ============================================
# SESSION STATE
# ============================================
if 'leads' not in st.session_state:
    st.session_state.leads = []
if 'filtered_leads' not in st.session_state:
    st.session_state.filtered_leads = []
if 'raw_leads' not in st.session_state:
    st.session_state.raw_leads = []  # All leads before AI filter
if 'scraping_done' not in st.session_state:
    st.session_state.scraping_done = False
if 'nav_page' not in st.session_state:
    st.session_state.nav_page = "Dashboard"
if 'last_search_results' not in st.session_state:
    st.session_state.last_search_results = None  # Store search summary

# Lead Warming session state
if 'warming_activities' not in st.session_state:
    st.session_state.warming_activities = []  # List of warming activities performed
if 'warming_queue' not in st.session_state:
    st.session_state.warming_queue = []  # Leads queued for warming
if 'warming_schedule' not in st.session_state:
    st.session_state.warming_schedule = {}  # Scheduled warming activities by lead

# Language setting
if 'language' not in st.session_state:
    st.session_state.language = 'en'  # 'en' for English, 'es' for Spanish

# Error notification system
if 'error_notifications' not in st.session_state:
    st.session_state.error_notifications = []  # List of error notifications

def add_error_notification(title: str, message: str, error_type: str = "error", source: str = "System"):
    """Add an error notification to the queue.

    Args:
        title: Short error title
        message: Detailed error message
        error_type: 'error', 'warning', 'api_error', 'network_error'
        source: Where the error originated (e.g., 'Reddit API', 'HubSpot', 'Search')
    """
    from datetime import datetime
    notification = {
        'id': datetime.now().timestamp(),
        'title': title,
        'message': message,
        'type': error_type,
        'source': source,
        'timestamp': datetime.now().isoformat(),
        'dismissed': False
    }
    st.session_state.error_notifications.append(notification)

def dismiss_notification(notification_id):
    """Mark a notification as dismissed."""
    for notif in st.session_state.error_notifications:
        if notif['id'] == notification_id:
            notif['dismissed'] = True

def clear_all_notifications():
    """Clear all notifications."""
    st.session_state.error_notifications = []

def render_error_notifications():
    """Render the error notification panel if there are active notifications."""
    active_notifications = [n for n in st.session_state.error_notifications if not n.get('dismissed')]

    if not active_notifications:
        return

    # Error notification styles
    st.markdown("""
    <style>
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
            50% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
        }
        .error-panel {
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
            animation: slideIn 0.3s ease-out;
        }
        .error-notification {
            background: linear-gradient(135deg, #FFFFFF 0%, #FEF2F2 100%);
            border: 1px solid #FECACA;
            border-left: 4px solid #EF4444;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: 0 10px 40px rgba(239, 68, 68, 0.2);
            animation: slideIn 0.3s ease-out;
        }
        .error-notification.warning {
            background: linear-gradient(135deg, #FFFFFF 0%, #FFFBEB 100%);
            border-color: #FDE68A;
            border-left-color: #F59E0B;
            box-shadow: 0 10px 40px rgba(245, 158, 11, 0.2);
        }
        .error-notification.api-error {
            background: linear-gradient(135deg, #FFFFFF 0%, #EFF6FF 100%);
            border-color: #BFDBFE;
            border-left-color: #3B82F6;
            box-shadow: 0 10px 40px rgba(59, 130, 246, 0.2);
        }
        .error-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        .error-icon {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            margin-right: 12px;
        }
        .error-icon.error { background: #FEE2E2; }
        .error-icon.warning { background: #FEF3C7; }
        .error-icon.api-error { background: #DBEAFE; }
        .error-title {
            font-weight: 600;
            font-size: 14px;
            color: #1E293B;
            flex: 1;
        }
        .error-source {
            font-size: 10px;
            color: #64748B;
            background: #F1F5F9;
            padding: 2px 8px;
            border-radius: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .error-message {
            font-size: 13px;
            color: #475569;
            line-height: 1.5;
            margin-top: 8px;
            padding-left: 44px;
        }
        .error-time {
            font-size: 11px;
            color: #94A3B8;
            padding-left: 44px;
            margin-top: 8px;
        }
        .error-actions {
            display: flex;
            gap: 8px;
            margin-top: 12px;
            padding-left: 44px;
        }
        .notification-badge {
            position: fixed;
            top: 85px;
            right: 25px;
            background: #EF4444;
            color: white;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
            z-index: 10000;
            animation: pulse 2s infinite;
        }
    </style>
    """, unsafe_allow_html=True)

    # Build notifications HTML
    notifications_html = '<div class="error-panel">'

    for notif in active_notifications[-5:]:  # Show last 5 notifications
        error_type = notif.get('type', 'error')
        icon = '⚠️' if error_type == 'warning' else '🔌' if error_type == 'api_error' else '❌'
        css_class = error_type.replace('_', '-')

        # Format timestamp
        try:
            from datetime import datetime
            ts = datetime.fromisoformat(notif['timestamp'])
            time_str = ts.strftime('%H:%M:%S')
        except:
            time_str = 'Just now'

        notifications_html += f"""
        <div class="error-notification {css_class}">
            <div class="error-header">
                <div style="display: flex; align-items: center;">
                    <div class="error-icon {css_class}">{icon}</div>
                    <div class="error-title">{notif['title']}</div>
                </div>
                <span class="error-source">{notif['source']}</span>
            </div>
            <div class="error-message">{notif['message']}</div>
            <div class="error-time">🕐 {time_str}</div>
        </div>
        """

    notifications_html += '</div>'

    # Badge showing count
    if len(active_notifications) > 0:
        notifications_html += f'<div class="notification-badge">{len(active_notifications)}</div>'

    st.markdown(notifications_html, unsafe_allow_html=True)

    # Dismiss button
    if st.button("✕ Dismiss All Notifications", key="dismiss_all_errors"):
        clear_all_notifications()
        st.rerun()


# ============================================
# SIDEBAR
# ============================================
def render_sidebar():
    with st.sidebar:
        # Logo
        st.markdown("""
        <div class="logo-section">
            <div class="logo-container">
                <div class="logo-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                        <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                        <path d="M2 17l10 5 10-5"/>
                        <path d="M2 12l10 5 10-5"/>
                    </svg>
                </div>
                <div class="logo-text">
                    <p class="logo-title">LeadGen Pro</p>
                    <p class="logo-subtitle">Prospecting AI</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # User Card
        st.markdown("""
        <div class="user-card">
            <div class="user-info">
                <div class="user-avatar">U</div>
                <div class="user-details">
                    <h4>User</h4>
                    <span class="user-badge">PRO</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Language Toggle with animated globe
        current_lang = st.session_state.language
        lang_label = "🇺🇸 EN" if current_lang == 'en' else "🇪🇸 ES"

        st.markdown(f"""
        <style>
            @keyframes globe-spin {{
                0% {{ transform: rotateY(0deg); }}
                100% {{ transform: rotateY(360deg); }}
            }}
            .lang-toggle-container {{
                display: flex;
                justify-content: center;
                margin: 12px 0;
            }}
            .lang-toggle {{
                display: flex;
                align-items: center;
                gap: 8px;
                background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
                border: 1px solid #475569;
                border-radius: 20px;
                padding: 6px 14px;
                cursor: pointer;
                transition: all 0.3s ease;
            }}
            .lang-toggle:hover {{
                border-color: #3B82F6;
                box-shadow: 0 0 12px rgba(59, 130, 246, 0.3);
            }}
            .lang-toggle:hover .globe-icon {{
                animation: globe-spin 1s linear infinite;
            }}
            .globe-icon {{
                font-size: 16px;
                display: inline-block;
            }}
            .lang-text {{
                font-size: 12px;
                font-weight: 600;
                color: #E2E8F0;
            }}
        </style>
        <div class="lang-toggle-container">
            <div class="lang-toggle" title="Click to switch language">
                <span class="globe-icon">🌐</span>
                <span class="lang-text">{lang_label}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Language toggle button (actual functionality)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔄" if current_lang == 'en' else "🔄", key="lang_toggle", help="Switch to Spanish" if current_lang == 'en' else "Cambiar a Inglés", use_container_width=True):
                st.session_state.language = 'es' if current_lang == 'en' else 'en'
                st.rerun()

        # Nav Label
        nav_label = "Main Menu" if st.session_state.language == 'en' else "Menú Principal"
        st.markdown(f'<div class="nav-label">{nav_label}</div>', unsafe_allow_html=True)

        # Navigation
        pages = ["Dashboard", "Find Leads", "My Leads", "Lead Warming", "Job Changes", "CRM", "Analytics", "AI Assistant", "Settings"]
        current_index = pages.index(st.session_state.nav_page) if st.session_state.nav_page in pages else 0

        page = st.radio(
            "nav",
            pages,
            index=current_index,
            label_visibility="collapsed"
        )

        # Sync radio selection with session state
        if page != st.session_state.nav_page:
            st.session_state.nav_page = page

        # Background Task Status
        current_task = task_manager.get_current_task()
        if current_task and current_task.status == TaskStatus.RUNNING:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
                        border-radius: 12px; padding: 12px; margin: 16px 0;">
                <div style="display: flex; align-items: center; gap: 8px; color: white;">
                    <div class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></div>
                    <span style="font-size: 13px; font-weight: 500;">Searching...</span>
                </div>
                <div style="margin-top: 8px;">
                    <div style="background: rgba(255,255,255,0.2); border-radius: 4px; height: 6px; overflow: hidden;">
                        <div style="background: white; height: 100%; width: {current_task.progress}%; transition: width 0.3s;"></div>
                    </div>
                    <p style="color: rgba(255,255,255,0.8); font-size: 11px; margin-top: 4px;">{current_task.progress_message}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            # Auto-refresh every 2 seconds while task is running
            st.markdown("""
            <script>
                setTimeout(function() {
                    window.location.reload();
                }, 2000);
            </script>
            """, unsafe_allow_html=True)
        elif current_task and current_task.status == TaskStatus.COMPLETED:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #10B981 0%, #059669 100%);
                        border-radius: 12px; padding: 12px; margin: 16px 0;">
                <div style="display: flex; align-items: center; gap: 8px; color: white;">
                    <span>✓</span>
                    <span style="font-size: 13px; font-weight: 500;">Search Complete!</span>
                </div>
                <p style="color: rgba(255,255,255,0.9); font-size: 12px; margin-top: 4px;">
                    Found {current_task.result_count} leads
                </p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("View Results", key="view_task_results", use_container_width=True):
                task_manager.clear_completed_task()
                st.session_state.nav_page = "My Leads"
                st.rerun()

        # Footer
        st.markdown(f"""
        <div class="sidebar-footer">
            <div class="sidebar-stats">
                <span class="status-dot"></span>
                <span>{len(st.session_state.filtered_leads)} active leads</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ============================================
# PAGES
# ============================================
def show_dashboard():
    # Futuristic Holographic Dashboard Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%);
                border: 1px solid rgba(0, 255, 255, 0.2);
                border-radius: 16px;
                padding: 32px;
                margin-bottom: 32px;
                position: relative;
                overflow: hidden;
                backdrop-filter: blur(10px);
                box-shadow: 0 0 40px rgba(0, 255, 255, 0.1), inset 0 0 60px rgba(0, 255, 255, 0.05);">
        <!-- Scan line effect -->
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent 0%, #00FFFF 50%, transparent 100%); opacity: 0.8;"></div>
        <div style="position: absolute; bottom: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent 0%, #00FFFF 50%, transparent 100%); opacity: 0.5;"></div>

        <div style="display: flex; align-items: center; gap: 24px; position: relative; z-index: 1;">
            <div style="background: linear-gradient(135deg, rgba(0, 255, 255, 0.2) 0%, rgba(0, 139, 139, 0.2) 100%);
                        border: 1px solid #00FFFF;
                        border-radius: 12px;
                        padding: 16px;
                        box-shadow: 0 0 30px rgba(0, 255, 255, 0.3), inset 0 0 20px rgba(0, 255, 255, 0.1);">
                <span style="font-size: 36px; filter: drop-shadow(0 0 10px #00FFFF);">📊</span>
            </div>
            <div>
                <h1 style="margin: 0 0 8px 0; color: #00FFFF; font-size: 28px; font-weight: 700; font-family: 'Orbitron', sans-serif; letter-spacing: 0.1em; text-shadow: 0 0 20px rgba(0, 255, 255, 0.5);">DASHBOARD</h1>
                <p style="margin: 0; color: #C0C0C0; font-size: 15px; font-family: 'Rajdhani', sans-serif; letter-spacing: 0.05em;">SYSTEM OVERVIEW • LEAD GENERATION METRICS • REAL-TIME DATA</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Quick Actions
    st.markdown("""
    <div style="margin-bottom: 24px;">
        <h3 style="margin: 0 0 16px 0; color: #00FFFF; font-size: 16px; font-weight: 600; font-family: 'Orbitron', sans-serif; letter-spacing: 0.15em; text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);">⚡ QUICK ACTIONS</h3>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔎 Start Searching", type="primary", use_container_width=True):
            st.session_state.nav_page = "Find Leads"
            st.rerun()

    with col2:
        if st.button("📋 View My Leads", use_container_width=True):
            st.session_state.nav_page = "My Leads"
            st.rerun()

    with col3:
        if st.button("⚙️ Configure APIs", use_container_width=True):
            st.session_state.nav_page = "Settings"
            st.rerun()

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # Metrics
    leads_count = len(st.session_state.leads)
    qualified_count = len(st.session_state.filtered_leads)
    hot_leads_count = len([l for l in st.session_state.filtered_leads if getattr(l, 'total_score', l.pain_score) >= 80])
    keywords_count = len(settings.pain_keywords)
    sources_count = sum([1 for x in [True, True, bool(settings.google_api_key), True] if x])
    conv_rate = int((qualified_count / leads_count * 100)) if leads_count > 0 else 0

    # Metrics Section Header - Holographic
    st.markdown("""
    <div style="margin-bottom: 24px;">
        <h3 style="margin: 0 0 8px 0; color: #00FFFF; font-size: 16px; font-weight: 600; font-family: 'Orbitron', sans-serif; letter-spacing: 0.15em; text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);">📈 KEY METRICS</h3>
        <p style="margin: 0; color: #C0C0C0; font-size: 13px; font-family: 'Rajdhani', sans-serif; letter-spacing: 0.05em;">Real-time lead generation performance data</p>
    </div>
    """, unsafe_allow_html=True)

    # Holographic Metric Cards with Modern Tooltips
    st.markdown(f"""
    <style>
        .holo-metric-card {{
            background: linear-gradient(135deg, rgba(55, 65, 85, 0.95) 0%, rgba(40, 50, 70, 0.95) 100%);
            border: 2px solid rgba(0, 255, 255, 0.5);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            position: relative;
            overflow: visible;
            box-shadow: 0 0 25px rgba(0, 255, 255, 0.25), 0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
            cursor: pointer;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }}
        .holo-metric-card:hover {{
            transform: translateY(-4px);
            border-color: #00FFFF;
            box-shadow: 0 0 40px rgba(0, 255, 255, 0.4), 0 12px 40px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.15);
        }}
        .holo-tooltip {{
            position: absolute;
            bottom: calc(100% + 15px);
            left: 50%;
            transform: translateX(-50%) scale(0.9);
            background: linear-gradient(135deg, rgba(28, 28, 46, 0.98) 0%, rgba(45, 55, 72, 0.98) 100%);
            border: 1px solid rgba(0, 255, 255, 0.5);
            border-radius: 12px;
            padding: 16px 20px;
            min-width: 220px;
            max-width: 280px;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 9999;
            backdrop-filter: blur(20px);
            box-shadow: 0 0 30px rgba(0, 255, 255, 0.3), 0 20px 40px rgba(0, 0, 0, 0.5);
        }}
        .holo-tooltip::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent 0%, #00FFFF 50%, transparent 100%);
        }}
        .holo-tooltip::after {{
            content: '';
            position: absolute;
            bottom: -8px;
            left: 50%;
            transform: translateX(-50%);
            width: 0;
            height: 0;
            border-left: 8px solid transparent;
            border-right: 8px solid transparent;
            border-top: 8px solid rgba(0, 255, 255, 0.5);
        }}
        .holo-metric-card:hover .holo-tooltip {{
            opacity: 1;
            visibility: visible;
            transform: translateX(-50%) scale(1);
        }}
        .tooltip-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(0, 255, 255, 0.2);
        }}
        .tooltip-icon {{
            width: 28px;
            height: 28px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }}
        .tooltip-title {{
            color: #00FFFF;
            font-size: 13px;
            font-weight: 600;
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 0.1em;
            text-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
        }}
        .tooltip-content {{
            color: #C0C0C0;
            font-size: 12px;
            font-family: 'Rajdhani', sans-serif;
            line-height: 1.5;
        }}
        .tooltip-highlight {{
            color: #00FFFF;
            font-weight: 600;
        }}
    </style>
    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; margin-bottom: 32px;">
        <!-- Leads Found -->
        <div class="holo-metric-card" style="background: linear-gradient(135deg, rgba(55, 70, 85, 0.95) 0%, rgba(0, 70, 70, 0.6) 100%); border-color: #008B8B;">
            <div class="holo-tooltip">
                <div class="tooltip-header">
                    <div class="tooltip-icon" style="background: rgba(0, 139, 139, 0.5); border: 2px solid #008B8B;">👥</div>
                    <div class="tooltip-title">LEADS FOUND</div>
                </div>
                <div class="tooltip-content">
                    Total de <span class="tooltip-highlight">prospectos descubiertos</span> en esta sesión desde todas las fuentes configuradas (Reddit, Indeed, Yelp, Google Maps).
                </div>
            </div>
            <div style="position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent 0%, #008B8B 50%, transparent 100%);"></div>
            <div style="font-size: 28px; margin-bottom: 8px; filter: drop-shadow(0 0 8px #008B8B);">👥</div>
            <div style="font-size: 36px; font-weight: 700; color: #20B2AA; font-family: 'Orbitron', sans-serif; text-shadow: 0 0 20px rgba(0, 139, 139, 0.6);">{leads_count}</div>
            <div style="font-size: 12px; color: #E5E5E5; margin-top: 4px; font-family: 'Share Tech Mono', monospace; letter-spacing: 0.1em;">LEADS FOUND</div>
            <div style="font-size: 10px; color: #A0A0A0; margin-top: 8px; font-family: 'Share Tech Mono', monospace;">THIS SESSION</div>
        </div>
        <!-- Hot Leads -->
        <div class="holo-metric-card" style="background: linear-gradient(135deg, rgba(55, 65, 85, 0.95) 0%, rgba(100, 30, 50, 0.5) 100%); border-color: #FF3366;">
            <div class="holo-tooltip" style="border-color: #FF3366; box-shadow: 0 0 30px rgba(255, 51, 102, 0.3), 0 20px 40px rgba(0, 0, 0, 0.5);">
                <div style="position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent 0%, #FF3366 50%, transparent 100%);"></div>
                <div class="tooltip-header" style="border-color: rgba(255, 51, 102, 0.3);">
                    <div class="tooltip-icon" style="background: rgba(255, 51, 102, 0.5); border: 2px solid #FF3366;">🔥</div>
                    <div class="tooltip-title" style="color: #FF3366; text-shadow: 0 0 10px rgba(255, 51, 102, 0.5);">HOT LEADS</div>
                </div>
                <div class="tooltip-content">
                    Leads con <span class="tooltip-highlight" style="color: #FF3366;">Score 80+</span>. Son prospectos de alta prioridad listos para contactar inmediatamente.
                </div>
            </div>
            <div style="position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent 0%, #FF3366 50%, transparent 100%);"></div>
            <div style="font-size: 28px; margin-bottom: 8px; filter: drop-shadow(0 0 8px #FF3366);">🔥</div>
            <div style="font-size: 36px; font-weight: 700; color: #FF6B8A; font-family: 'Orbitron', sans-serif; text-shadow: 0 0 20px rgba(255, 51, 102, 0.6);">{hot_leads_count}</div>
            <div style="font-size: 12px; color: #E5E5E5; margin-top: 4px; font-family: 'Share Tech Mono', monospace; letter-spacing: 0.1em;">HOT LEADS</div>
            <div style="font-size: 10px; color: #A0A0A0; margin-top: 8px; font-family: 'Share Tech Mono', monospace;">SCORE 80+</div>
        </div>
        <!-- Qualified -->
        <div class="holo-metric-card" style="background: linear-gradient(135deg, rgba(55, 65, 85, 0.95) 0%, rgba(0, 80, 50, 0.5) 100%); border-color: #00FF88;">
            <div class="holo-tooltip" style="border-color: #00FF88; box-shadow: 0 0 30px rgba(0, 255, 136, 0.3), 0 20px 40px rgba(0, 0, 0, 0.5);">
                <div style="position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent 0%, #00FF88 50%, transparent 100%);"></div>
                <div class="tooltip-header" style="border-color: rgba(0, 255, 136, 0.3);">
                    <div class="tooltip-icon" style="background: rgba(0, 255, 136, 0.5); border: 2px solid #00FF88;">✅</div>
                    <div class="tooltip-title" style="color: #00FF88; text-shadow: 0 0 10px rgba(0, 255, 136, 0.5);">QUALIFIED</div>
                </div>
                <div class="tooltip-content">
                    Leads <span class="tooltip-highlight" style="color: #00FF88;">verificados por AI</span> que pasaron los filtros de calificación. Listos para exportar a tu CRM.
                </div>
            </div>
            <div style="position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent 0%, #00FF88 50%, transparent 100%);"></div>
            <div style="font-size: 28px; margin-bottom: 8px; filter: drop-shadow(0 0 8px #00FF88);">✅</div>
            <div style="font-size: 36px; font-weight: 700; color: #50FFB0; font-family: 'Orbitron', sans-serif; text-shadow: 0 0 20px rgba(0, 255, 136, 0.6);">{qualified_count}</div>
            <div style="font-size: 12px; color: #E5E5E5; margin-top: 4px; font-family: 'Share Tech Mono', monospace; letter-spacing: 0.1em;">QUALIFIED</div>
            <div style="font-size: 10px; color: #A0A0A0; margin-top: 8px; font-family: 'Share Tech Mono', monospace;">CRM READY</div>
        </div>
        <!-- Keywords -->
        <div class="holo-metric-card" style="background: linear-gradient(135deg, rgba(55, 65, 85, 0.95) 0%, rgba(80, 60, 0, 0.5) 100%); border-color: #FFB800;">
            <div class="holo-tooltip" style="border-color: #FFB800; box-shadow: 0 0 30px rgba(255, 184, 0, 0.3), 0 20px 40px rgba(0, 0, 0, 0.5);">
                <div style="position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent 0%, #FFB800 50%, transparent 100%);"></div>
                <div class="tooltip-header" style="border-color: rgba(255, 184, 0, 0.3);">
                    <div class="tooltip-icon" style="background: rgba(255, 184, 0, 0.5); border: 2px solid #FFB800;">🔑</div>
                    <div class="tooltip-title" style="color: #FFB800; text-shadow: 0 0 10px rgba(255, 184, 0, 0.5);">KEYWORDS</div>
                </div>
                <div class="tooltip-content">
                    <span class="tooltip-highlight" style="color: #FFB800;">Palabras clave de dolor</span> activas que detectan necesidades en los prospectos (ej: "need help", "looking for").
                </div>
            </div>
            <div style="position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent 0%, #FFB800 50%, transparent 100%);"></div>
            <div style="font-size: 28px; margin-bottom: 8px; filter: drop-shadow(0 0 8px #FFB800);">🔑</div>
            <div style="font-size: 36px; font-weight: 700; color: #FFD040; font-family: 'Orbitron', sans-serif; text-shadow: 0 0 20px rgba(255, 184, 0, 0.6);">{keywords_count}</div>
            <div style="font-size: 12px; color: #E5E5E5; margin-top: 4px; font-family: 'Share Tech Mono', monospace; letter-spacing: 0.1em;">KEYWORDS</div>
            <div style="font-size: 10px; color: #A0A0A0; margin-top: 8px; font-family: 'Share Tech Mono', monospace;">ACTIVE</div>
        </div>
        <!-- Sources -->
        <div class="holo-metric-card" style="background: linear-gradient(135deg, rgba(55, 65, 85, 0.95) 0%, rgba(0, 60, 80, 0.5) 100%); border-color: #00FFFF;">
            <div class="holo-tooltip">
                <div class="tooltip-header">
                    <div class="tooltip-icon" style="background: rgba(0, 255, 255, 0.5); border: 2px solid #00FFFF;">🔗</div>
                    <div class="tooltip-title">SOURCES</div>
                </div>
                <div class="tooltip-content">
                    <span class="tooltip-highlight">Fuentes de datos conectadas</span>: Reddit, Indeed, Yelp, Google Maps. Configura las APIs en Settings para activar más.
                </div>
            </div>
            <div style="position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent 0%, #00FFFF 50%, transparent 100%);"></div>
            <div style="font-size: 28px; margin-bottom: 8px; filter: drop-shadow(0 0 8px #00FFFF);">🔗</div>
            <div style="font-size: 36px; font-weight: 700; color: #60FFFF; font-family: 'Orbitron', sans-serif; text-shadow: 0 0 20px rgba(0, 255, 255, 0.6);">{sources_count}/4</div>
            <div style="font-size: 12px; color: #E5E5E5; margin-top: 4px; font-family: 'Share Tech Mono', monospace; letter-spacing: 0.1em;">SOURCES</div>
            <div style="font-size: 10px; color: #A0A0A0; margin-top: 8px; font-family: 'Share Tech Mono', monospace;">CONNECTED</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


    # Data Sources Section - Holographic
    st.markdown("""
    <div style="margin-bottom: 24px;">
        <h3 style="margin: 0 0 8px 0; color: #00FFFF; font-size: 16px; font-weight: 600; font-family: 'Orbitron', sans-serif; letter-spacing: 0.15em; text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);">🌐 DATA SOURCES</h3>
        <p style="margin: 0; color: #C0C0C0; font-size: 13px; font-family: 'Rajdhani', sans-serif; letter-spacing: 0.05em;">Connected platforms for lead acquisition</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px;">
        <!-- Reddit -->
        <div style="background: linear-gradient(135deg, rgba(0, 30, 50, 0.6) 0%, rgba(0, 15, 30, 0.8) 100%);
                    border: 1px solid rgba(255, 69, 0, 0.3);
                    border-radius: 12px;
                    padding: 20px;
                    text-align: center;
                    transition: all 0.3s ease;
                    backdrop-filter: blur(10px);">
            <div style="width: 48px; height: 48px; border-radius: 10px; display: flex; align-items: center; justify-content: center; margin: 0 auto 12px auto;
                        background: linear-gradient(135deg, rgba(255, 69, 0, 0.2) 0%, rgba(255, 69, 0, 0.1) 100%);
                        border: 1px solid rgba(255, 69, 0, 0.5);
                        box-shadow: 0 0 15px rgba(255, 69, 0, 0.3);">
                <span style="font-size: 24px; filter: drop-shadow(0 0 5px #FF4500);">🔴</span>
            </div>
            <h4 style="margin: 0 0 4px 0; color: #FF4500; font-size: 14px; font-weight: 600; font-family: 'Orbitron', sans-serif; letter-spacing: 0.05em; text-shadow: 0 0 10px rgba(255, 69, 0, 0.3);">REDDIT</h4>
            <p style="margin: 0; color: #C0C0C0; font-size: 11px; font-family: 'Share Tech Mono', monospace;">BUSINESS FEEDS</p>
        </div>
        <!-- Hacker News -->
        <div style="background: linear-gradient(135deg, rgba(0, 30, 50, 0.6) 0%, rgba(0, 15, 30, 0.8) 100%);
                    border: 1px solid rgba(255, 102, 0, 0.3);
                    border-radius: 12px;
                    padding: 20px;
                    text-align: center;
                    transition: all 0.3s ease;
                    backdrop-filter: blur(10px);">
            <div style="width: 48px; height: 48px; border-radius: 10px; display: flex; align-items: center; justify-content: center; margin: 0 auto 12px auto;
                        background: linear-gradient(135deg, rgba(255, 102, 0, 0.2) 0%, rgba(255, 102, 0, 0.1) 100%);
                        border: 1px solid rgba(255, 102, 0, 0.5);
                        box-shadow: 0 0 15px rgba(255, 102, 0, 0.3);">
                <span style="font-size: 24px; filter: drop-shadow(0 0 5px #FF6600);">🟠</span>
            </div>
            <h4 style="margin: 0 0 4px 0; color: #FF6600; font-size: 14px; font-weight: 600; font-family: 'Orbitron', sans-serif; letter-spacing: 0.05em; text-shadow: 0 0 10px rgba(255, 102, 0, 0.3);">HACKER NEWS</h4>
            <p style="margin: 0; color: #C0C0C0; font-size: 11px; font-family: 'Share Tech Mono', monospace;">TECH STARTUPS</p>
        </div>
        <!-- Google -->
        <div style="background: linear-gradient(135deg, rgba(0, 30, 50, 0.6) 0%, rgba(0, 15, 30, 0.8) 100%);
                    border: 1px solid rgba(66, 133, 244, 0.3);
                    border-radius: 12px;
                    padding: 20px;
                    text-align: center;
                    transition: all 0.3s ease;
                    backdrop-filter: blur(10px);">
            <div style="width: 48px; height: 48px; border-radius: 10px; display: flex; align-items: center; justify-content: center; margin: 0 auto 12px auto;
                        background: linear-gradient(135deg, rgba(66, 133, 244, 0.2) 0%, rgba(66, 133, 244, 0.1) 100%);
                        border: 1px solid rgba(66, 133, 244, 0.5);
                        box-shadow: 0 0 15px rgba(66, 133, 244, 0.3);">
                <span style="font-size: 24px; filter: drop-shadow(0 0 5px #4285F4);">🔵</span>
            </div>
            <h4 style="margin: 0 0 4px 0; color: #4285F4; font-size: 14px; font-weight: 600; font-family: 'Orbitron', sans-serif; letter-spacing: 0.05em; text-shadow: 0 0 10px rgba(66, 133, 244, 0.3);">GOOGLE</h4>
            <p style="margin: 0; color: #C0C0C0; font-size: 11px; font-family: 'Share Tech Mono', monospace;">WEB SEARCH</p>
        </div>
        <!-- Indeed -->
        <div style="background: linear-gradient(135deg, rgba(0, 30, 50, 0.6) 0%, rgba(0, 15, 30, 0.8) 100%);
                    border: 1px solid rgba(0, 139, 139, 0.3);
                    border-radius: 12px;
                    padding: 20px;
                    text-align: center;
                    transition: all 0.3s ease;
                    backdrop-filter: blur(10px);">
            <div style="width: 48px; height: 48px; border-radius: 10px; display: flex; align-items: center; justify-content: center; margin: 0 auto 12px auto;
                        background: linear-gradient(135deg, rgba(0, 139, 139, 0.2) 0%, rgba(0, 139, 139, 0.1) 100%);
                        border: 1px solid rgba(0, 139, 139, 0.5);
                        box-shadow: 0 0 15px rgba(0, 139, 139, 0.3);">
                <span style="font-size: 24px; filter: drop-shadow(0 0 5px #008B8B);">💼</span>
            </div>
            <h4 style="margin: 0 0 4px 0; color: #008B8B; font-size: 14px; font-weight: 600; font-family: 'Orbitron', sans-serif; letter-spacing: 0.05em; text-shadow: 0 0 10px rgba(0, 139, 139, 0.3);">INDEED</h4>
            <p style="margin: 0; color: #C0C0C0; font-size: 11px; font-family: 'Share Tech Mono', monospace;">JOB POSTINGS</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # How It Works Section - Holographic
    st.markdown("""
    <div style="margin-bottom: 24px;">
        <h3 style="margin: 0 0 8px 0; color: #00FFFF; font-size: 18px; font-weight: 700; font-family: 'Orbitron', sans-serif; letter-spacing: 0.1em; text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);">🚀 HOW IT WORKS</h3>
        <p style="margin: 0; color: #C0C0C0; font-size: 13px;">Three simple steps to find qualified leads</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
        <!-- Step 1 -->
        <div style="background: linear-gradient(135deg, rgba(0, 139, 139, 0.15) 0%, rgba(45, 55, 72, 0.3) 100%); border: 1px solid rgba(0, 139, 139, 0.4); border-radius: 16px; padding: 24px; text-align: center; backdrop-filter: blur(10px); box-shadow: 0 0 20px rgba(0, 139, 139, 0.1);">
            <div style="background: linear-gradient(135deg, #008B8B 0%, #006666 100%); width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto; color: #00FFFF; font-weight: 700; font-size: 18px; box-shadow: 0 0 15px rgba(0, 255, 255, 0.3);">1</div>
            <h4 style="margin: 0 0 8px 0; color: #00FFFF; font-size: 16px; font-weight: 600; font-family: 'Orbitron', sans-serif;">Search</h4>
            <p style="margin: 0; color: #C0C0C0; font-size: 13px;">Select sources and find prospects automatically</p>
        </div>
        <!-- Step 2 -->
        <div style="background: linear-gradient(135deg, rgba(0, 255, 136, 0.1) 0%, rgba(45, 55, 72, 0.3) 100%); border: 1px solid rgba(0, 255, 136, 0.4); border-radius: 16px; padding: 24px; text-align: center; backdrop-filter: blur(10px); box-shadow: 0 0 20px rgba(0, 255, 136, 0.1);">
            <div style="background: linear-gradient(135deg, #00AA66 0%, #008844 100%); width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto; color: #00FF88; font-weight: 700; font-size: 18px; box-shadow: 0 0 15px rgba(0, 255, 136, 0.3);">2</div>
            <h4 style="margin: 0 0 8px 0; color: #00FF88; font-size: 16px; font-weight: 600; font-family: 'Orbitron', sans-serif;">Qualify</h4>
            <p style="margin: 0; color: #C0C0C0; font-size: 13px;">AI evaluates and scores each lead by relevance</p>
        </div>
        <!-- Step 3 -->
        <div style="background: linear-gradient(135deg, rgba(255, 184, 0, 0.1) 0%, rgba(45, 55, 72, 0.3) 100%); border: 1px solid rgba(255, 184, 0, 0.4); border-radius: 16px; padding: 24px; text-align: center; backdrop-filter: blur(10px); box-shadow: 0 0 20px rgba(255, 184, 0, 0.1);">
            <div style="background: linear-gradient(135deg, #CC9300 0%, #AA7700 100%); width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto; color: #FFB800; font-weight: 700; font-size: 18px; box-shadow: 0 0 15px rgba(255, 184, 0, 0.3);">3</div>
            <h4 style="margin: 0 0 8px 0; color: #FFB800; font-size: 16px; font-weight: 600; font-family: 'Orbitron', sans-serif;">Export</h4>
            <p style="margin: 0; color: #C0C0C0; font-size: 13px;">Send the best leads directly to HubSpot</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def show_search():
    # Holographic Page Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%);
                border: 1px solid rgba(0, 255, 255, 0.3);
                border-radius: 16px;
                padding: 32px;
                margin-bottom: 24px;
                backdrop-filter: blur(10px);
                box-shadow: 0 0 40px rgba(0, 255, 255, 0.1), inset 0 0 60px rgba(0, 255, 255, 0.05);
                position: relative;
                overflow: hidden;">
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent 0%, #00FFFF 50%, transparent 100%); opacity: 0.8;"></div>
        <h1 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 32px; margin: 0 0 8px 0; letter-spacing: 0.1em; text-shadow: 0 0 20px rgba(0, 255, 255, 0.5);">
            🔎 FIND LEADS
        </h1>
        <p style="color: #C0C0C0; font-family: 'Rajdhani', sans-serif; font-size: 16px; margin: 0;">
            Discover prospects with communication problems
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Active Sources Section
    st.markdown("""
    <div style="background: rgba(28, 28, 46, 0.6); border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 12px; padding: 20px; margin-bottom: 20px; backdrop-filter: blur(5px);">
        <h3 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 18px; margin: 0 0 8px 0; letter-spacing: 0.05em;">
            📡 ACTIVE SOURCES
        </h3>
        <p style="color: #708090; font-size: 13px; margin: 0;">8 data sources available for lead discovery</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        use_reddit = st.checkbox("🔴 Reddit - Business subreddits", value=True, key="reddit_check")
        use_hn = st.checkbox("🟠 Hacker News - Startups", value=False, key="hn_check")
        use_linkedin = st.checkbox("🔷 LinkedIn - Decision Makers", value=bool(settings.google_api_key), disabled=not settings.google_api_key, key="linkedin_check")
    with col2:
        use_google = st.checkbox("🔵 Google Search", value=False, disabled=not settings.google_api_key, key="google_check")
        use_ph = st.checkbox("🟣 Product Hunt", value=False, key="ph_check")
        use_indeed = st.checkbox("💼 Indeed - Hiring Receptionists", value=True, key="indeed_check")
    with col3:
        use_yelp = st.checkbox("⭐ Yelp - Service Businesses", value=True, key="yelp_check")
        use_gmaps = st.checkbox("📍 Google Maps - Local Businesses", value=True, key="gmaps_check")

    st.markdown("""
    <div style="background: rgba(0, 139, 139, 0.1); border: 1px solid rgba(0, 139, 139, 0.3); border-radius: 8px; padding: 12px 16px; margin: 16px 0;">
        <span style="color: #008B8B; font-weight: 600;">💡 TIP:</span>
        <span style="color: #C0C0C0;"> Google Maps busca negocios locales (dentistas, HVAC, abogados) y extrae teléfono, website y email. GRATIS - no usa API.</span>
    </div>
    """, unsafe_allow_html=True)

    # Coming Soon Sources
    st.markdown("""
    <div style="background: rgba(28, 28, 46, 0.6); border: 1px solid rgba(0, 139, 139, 0.2); border-radius: 12px; padding: 20px; margin: 20px 0; backdrop-filter: blur(5px);">
        <h3 style="color: #008B8B; font-family: 'Orbitron', sans-serif; font-size: 18px; margin: 0 0 8px 0; letter-spacing: 0.05em;">
            🚀 COMING SOON
        </h3>
        <p style="color: #708090; font-size: 13px; margin: 0;">2 more sources in development</p>
    </div>
    """, unsafe_allow_html=True)

    coming_cols = st.columns(2)
    coming_sources = [
        ("🐦", "Twitter/X"),
        ("📘", "Facebook Groups")
    ]
    for i, (icon, name) in enumerate(coming_sources):
        with coming_cols[i]:
            st.markdown(f"<span style='color: #00FFFF; font-size: 24px;'>{icon}</span>", unsafe_allow_html=True)
            st.markdown(f"<span style='color: #C0C0C0;'>{name}</span>", unsafe_allow_html=True)

    # Time Filter
    st.markdown("""
    <div style="background: rgba(28, 28, 46, 0.6); border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 12px; padding: 20px; margin: 20px 0; backdrop-filter: blur(5px);">
        <h3 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 18px; margin: 0 0 8px 0; letter-spacing: 0.05em;">
            📅 TIME RANGE
        </h3>
        <p style="color: #708090; font-size: 13px; margin: 0;">Filter results by post date</p>
    </div>
    """, unsafe_allow_html=True)
    time_options = {
        "Last 24 hours": "day",
        "Last 7 days": "week",
        "Last 30 days": "month",
        "Last 3 months": "quarter",
        "Last year": "year",
        "All time": "all"
    }
    selected_time_label = st.selectbox("Search posts from:", list(time_options.keys()), index=1)
    selected_time = time_options[selected_time_label]

    # Location Filter
    st.markdown("""
    <div style="background: rgba(28, 28, 46, 0.6); border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 12px; padding: 20px; margin: 20px 0; backdrop-filter: blur(5px);">
        <h3 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 18px; margin: 0 0 8px 0; letter-spacing: 0.05em;">
            📍 LOCATION FILTER
        </h3>
        <p style="color: #708090; font-size: 13px; margin: 0;">Target specific geographic areas (for Indeed, Yelp & Google Maps)</p>
    </div>
    """, unsafe_allow_html=True)

    location_col1, location_col2 = st.columns(2)
    with location_col1:
        search_city = st.text_input("City", placeholder="Miami, Los Angeles, etc.", key="search_city")
    with location_col2:
        us_states = [
            "All States", "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
        ]
        search_state = st.selectbox("State", us_states, key="search_state")

    zip_col1, zip_col2 = st.columns(2)
    with zip_col1:
        search_zip = st.text_input("Zip Code (optional)", placeholder="33101", key="search_zip")
    with zip_col2:
        search_radius = st.selectbox("Radius", ["10 miles", "25 miles", "50 miles", "100 miles"], index=1, key="search_radius")

    # Build location string
    location_parts = []
    if search_city:
        location_parts.append(search_city)
    if search_state and search_state != "All States":
        location_parts.append(search_state)
    if search_zip:
        location_parts.append(search_zip)

    search_location = ", ".join(location_parts) if location_parts else ""

    if search_location:
        st.markdown(f"""
        <div style="background: rgba(0, 255, 136, 0.1); border: 1px solid rgba(0, 255, 136, 0.3); border-radius: 8px; padding: 12px 16px; margin: 16px 0;">
            <span style="color: #00FF88;">📍 Searching in: <strong>{search_location}</strong></span>
        </div>
        """, unsafe_allow_html=True)

    # Industry Filter
    st.markdown("""
    <div style="background: rgba(28, 28, 46, 0.6); border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 12px; padding: 20px; margin: 20px 0; backdrop-filter: blur(5px);">
        <h3 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 18px; margin: 0 0 8px 0; letter-spacing: 0.05em;">
            🏢 INDUSTRY FILTER
        </h3>
        <p style="color: #708090; font-size: 13px; margin: 0;">Optional - Focus on specific business verticals</p>
    </div>
    """, unsafe_allow_html=True)
    industries = ["All Industries"] + list(settings.industries.keys())
    selected_industry = st.selectbox("Select industry", industries)

    # AI Option
    ai_available = bool(settings.openai_api_key or settings.anthropic_api_key)
    st.markdown("""
    <div style="background: rgba(28, 28, 46, 0.6); border: 1px solid rgba(0, 139, 139, 0.2); border-radius: 12px; padding: 20px; margin: 20px 0; backdrop-filter: blur(5px);">
        <h3 style="color: #008B8B; font-family: 'Orbitron', sans-serif; font-size: 18px; margin: 0 0 8px 0; letter-spacing: 0.05em;">
            🤖 AI QUALIFICATION
        </h3>
        <p style="color: #708090; font-size: 13px; margin: 0;">Recommended - Let AI automatically score and qualify leads</p>
    </div>
    """, unsafe_allow_html=True)

    use_ai = st.checkbox("Use AI to qualify leads automatically", value=ai_available, disabled=not ai_available, key="ai_check")

    if not ai_available:
        st.markdown("""
        <div style="background: rgba(0, 139, 139, 0.1); border: 1px solid rgba(0, 139, 139, 0.3); border-radius: 8px; padding: 12px 16px; margin: 16px 0;">
            <span style="color: #008B8B;">ℹ️ Configure OpenAI or Anthropic API key in Settings to enable AI qualification</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)

    # Search Button
    if st.button("Start Search", type="primary", use_container_width=True):
        all_leads = []
        progress = st.progress(0)
        status = st.empty()
        results = st.container()

        scrapers = []
        if use_reddit: scrapers.append(("Reddit", RedditScraper))
        if use_hn: scrapers.append(("Hacker News", HackerNewsScraper))
        if use_google and settings.google_api_key: scrapers.append(("Google", GoogleScraper))
        if use_ph: scrapers.append(("Product Hunt", ProductHuntScraper))
        if use_indeed: scrapers.append(("Indeed", IndeedScraper))
        if use_yelp: scrapers.append(("Yelp", YelpScraper))
        if use_linkedin and settings.google_api_key: scrapers.append(("LinkedIn", LinkedInScraper))
        if use_gmaps: scrapers.append(("Google Maps", GoogleMapsScraper))

        if not scrapers:
            st.warning("Select at least one source")
            return

        for i, (name, Scraper) in enumerate(scrapers):
            status.markdown(f"""
            <div class="loading-box">
                <div class="spinner"></div>
                <span class="loading-text">Searching {name}...</span>
            </div>
            """, unsafe_allow_html=True)

            try:
                with Scraper() as s:
                    # Pass location to location-aware scrapers
                    if name in ["Indeed", "Yelp", "LinkedIn", "Google Maps"] and search_location:
                        batch = s.scrape(time_filter=selected_time, location=search_location)
                    else:
                        batch = s.scrape(time_filter=selected_time)
                    all_leads.extend(batch.leads)
                    with results:
                        st.success(f"{name}: {len(batch.leads)} leads")
            except ConnectionError as e:
                add_error_notification(
                    title=f"Connection Failed: {name}",
                    message=f"Could not connect to {name}. Check your internet connection or try again later.",
                    error_type="api_error",
                    source=name
                )
                with results:
                    st.warning(f"{name}: Connection error")
            except TimeoutError as e:
                add_error_notification(
                    title=f"Timeout: {name}",
                    message=f"{name} took too long to respond. The service might be overloaded.",
                    error_type="api_error",
                    source=name
                )
                with results:
                    st.warning(f"{name}: Timeout")
            except Exception as e:
                error_msg = str(e)[:100]
                add_error_notification(
                    title=f"Search Error: {name}",
                    message=f"Error while searching {name}: {error_msg}",
                    error_type="error",
                    source=name
                )
                with results:
                    st.warning(f"{name}: Error - {str(e)[:50]}")

            progress.progress((i + 1) / len(scrapers))

        # Enrich leads with Pain Score and Industry
        status.markdown("""
        <div class="loading-box">
            <div class="spinner"></div>
            <span class="loading-text">Calculating Lead Scores (Pain + Intent + Fit)...</span>
        </div>
        """, unsafe_allow_html=True)

        all_leads = enrich_leads(all_leads)

        # Deduplicate leads
        status.markdown("""
        <div class="loading-box">
            <div class="spinner"></div>
            <span class="loading-text">Removing duplicates...</span>
        </div>
        """, unsafe_allow_html=True)

        duplicates_count = lead_manager.get_duplicate_count(all_leads)
        all_leads = lead_manager.deduplicate(all_leads)

        if duplicates_count > 0:
            with results:
                st.info(f"Removed {duplicates_count} duplicate leads")

        # Filter by industry if selected
        if selected_industry != "All Industries":
            industry_subreddits = settings.industries.get(selected_industry, [])
            all_leads = [l for l in all_leads if l.subreddit and l.subreddit.lower() in [s.lower() for s in industry_subreddits] or l.industry == selected_industry]

        st.session_state.leads = all_leads
        st.session_state.raw_leads = all_leads.copy()  # Store raw leads before AI filter

        # Auto-save leads to storage
        saved_count = lead_manager.save_leads(all_leads)
        if saved_count > 0:
            with results:
                st.success(f"Auto-saved {saved_count} new leads to database")

        # AUTO-SYNC TO HUBSPOT if configured
        with HubSpotCRM() as crm:
            if crm.is_configured():
                status.markdown("""
                <div class="loading-box">
                    <div class="spinner"></div>
                    <span class="loading-text">Syncing to HubSpot...</span>
                </div>
                """, unsafe_allow_html=True)

                hubspot_synced = 0
                for lead in all_leads:
                    try:
                        result = crm.create_contact(lead)
                        if result:
                            hubspot_synced += 1
                    except Exception as e:
                        pass  # Continue with other leads

                if hubspot_synced > 0:
                    with results:
                        st.success(f"✅ Auto-synced {hubspot_synced} leads to HubSpot!")
                else:
                    with results:
                        st.info("HubSpot: Leads may already exist or sync failed")

        # Store search summary
        st.session_state.last_search_results = {
            'total_found': len(all_leads),
            'sources': {
                'Reddit': len([l for l in all_leads if l.source.value == 'reddit']),
                'Hacker News': len([l for l in all_leads if l.source.value == 'hacker_news']),
                'Google': len([l for l in all_leads if l.source.value == 'google_search']),
                'Product Hunt': len([l for l in all_leads if l.source.value == 'product_hunt']),
                'LinkedIn': len([l for l in all_leads if l.source.value == 'linkedin']),
                'Indeed': len([l for l in all_leads if l.source.value == 'indeed']),
                'Yelp': len([l for l in all_leads if l.source.value == 'yelp']),
                'Google Maps': len([l for l in all_leads if l.source.value == 'google_my_business']),
            }
        }

        # AI Filter
        if use_ai and all_leads:
            status.markdown("""
            <div class="loading-box">
                <div class="spinner"></div>
                <span class="loading-text">Qualifying with AI...</span>
            </div>
            """, unsafe_allow_html=True)

            try:
                ai_filter = AILeadFilter()
                filtered = ai_filter.filter_leads(all_leads)
                qualified = [l for l in filtered if l.is_qualified]
                st.session_state.filtered_leads = qualified
                with results:
                    st.success(f"AI qualified {len(qualified)}/{len(all_leads)} leads")
            except:
                st.session_state.filtered_leads = all_leads
        else:
            st.session_state.filtered_leads = all_leads

        # Hunter.io email enrichment for leads without emails
        if settings.hunter_api_key and all_leads:
            leads_without_email = [l for l in all_leads if not l.email]
            if leads_without_email:
                status.markdown("""
                <div class="loading-box">
                    <div class="spinner"></div>
                    <span class="loading-text">Finding emails with Hunter.io...</span>
                </div>
                """, unsafe_allow_html=True)

                try:
                    enriched_count, _ = enrich_leads_with_hunter(all_leads, max_lookups=15)
                    if enriched_count > 0:
                        with results:
                            st.success(f"Hunter.io found {enriched_count} emails")
                        # Re-save leads with new emails
                        lead_manager.save_leads(all_leads)
                except Exception as e:
                    with results:
                        st.warning(f"Hunter.io: Could not enrich emails")

        # Apollo.io Enrichment (if configured)
        if settings.apollo_api_key and all_leads:
            leads_to_enrich = [l for l in all_leads if not l.email or not l.phone]
            if leads_to_enrich:
                status.markdown("""
                <div class="loading-box">
                    <div class="spinner"></div>
                    <span class="loading-text">Enriching with Apollo.io (email + phone + company data)...</span>
                </div>
                """, unsafe_allow_html=True)

                try:
                    enriched_leads = enrich_leads_with_apollo(
                        all_leads,
                        api_key=settings.apollo_api_key,
                        max_enrichments=10,
                        delay_seconds=0.5
                    )
                    apollo_enriched = len([l for l in all_leads if l.extra_data and l.extra_data.get('apollo_enriched')])
                    if apollo_enriched > 0:
                        with results:
                            st.success(f"Apollo.io enriched {apollo_enriched} leads (email + phone + company)")
                        lead_manager.save_leads(all_leads)
                except Exception as e:
                    with results:
                        st.warning(f"Apollo.io: Could not enrich leads")

        # Email Verification with ZeroBounce (if configured)
        if (settings.zerobounce_api_key or settings.hunter_api_key) and all_leads:
            leads_with_email = [l for l in all_leads if l.email and not (l.extra_data and l.extra_data.get('email_verified'))]
            if leads_with_email:
                status.markdown("""
                <div class="loading-box">
                    <div class="spinner"></div>
                    <span class="loading-text">Verifying email deliverability...</span>
                </div>
                """, unsafe_allow_html=True)

                try:
                    verifier = EmailVerifier(
                        zerobounce_key=settings.zerobounce_api_key,
                        hunter_key=settings.hunter_api_key
                    )
                    verified_count = 0
                    for lead in leads_with_email[:15]:  # Limit to 15 verifications per run
                        if lead.email:
                            quality_data = get_email_quality_for_scoring(lead.email, verifier)
                            if not lead.extra_data:
                                lead.extra_data = {}
                            lead.extra_data['email_verified'] = True
                            lead.extra_data['email_verification'] = quality_data
                            verified_count += 1

                    if verified_count > 0:
                        with results:
                            st.success(f"Verified {verified_count} email addresses")
                        lead_manager.save_leads(all_leads)
                except Exception as e:
                    with results:
                        st.warning(f"Email verification: Could not verify emails")

        st.session_state.scraping_done = True
        progress.progress(1.0)

        # Calculate hot leads (Total Score >= 80)
        hot_leads = len([l for l in st.session_state.filtered_leads if getattr(l, 'total_score', l.pain_score) >= 80])

        status.markdown(f"""
        <div class="results-box">
            <div class="result-item">
                <div class="result-value green">{len(st.session_state.filtered_leads)}</div>
                <div class="result-label">Qualified</div>
            </div>
            <div class="result-item">
                <div class="result-value orange">{hot_leads}</div>
                <div class="result-label">Hot Leads</div>
            </div>
            <div class="result-item">
                <div class="result-value blue">{len(all_leads)}</div>
                <div class="result-label">Found</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Navigation buttons after search
        with results:
            nav_col1, nav_col2, nav_col3 = st.columns(3)
            with nav_col1:
                if st.button("📋 View in CRM", type="primary", use_container_width=True):
                    st.session_state.nav_page = "CRM"
                    st.rerun()
            with nav_col2:
                if st.button("📊 View All Leads", use_container_width=True):
                    st.session_state.nav_page = "My Leads"
                    st.rerun()
            with nav_col3:
                # Manual HubSpot sync button
                with HubSpotCRM() as crm:
                    if crm.is_configured():
                        if st.button("🔗 Sync to HubSpot", use_container_width=True):
                            sync_progress = st.progress(0)
                            synced = 0
                            total = len(all_leads)
                            for i, lead in enumerate(all_leads):
                                try:
                                    result = crm.create_contact(lead)
                                    if result:
                                        synced += 1
                                except:
                                    pass
                                sync_progress.progress((i + 1) / total)
                            st.success(f"Synced {synced}/{total} leads to HubSpot!")
                    else:
                        st.button("🔗 HubSpot (Not configured)", disabled=True, use_container_width=True)

    # Preview - Modern Lead Cards
    if st.session_state.scraping_done and st.session_state.filtered_leads:
        # Results section header
        st.markdown(f"""
        <div class="results-section-header">
            <div class="results-section-title">
                <h2>Qualified Leads</h2>
                <span class="results-count-badge">{len(st.session_state.filtered_leads)} leads found</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        for lead in st.session_state.filtered_leads[:5]:
            # Get lead grade based on total score
            total_score = getattr(lead, 'total_score', lead.pain_score) or lead.pain_score
            pain_score = lead.pain_score or 0
            intent_score = getattr(lead, 'intent_score', 0) or 0
            fit_score = getattr(lead, 'fit_score', 0) or 0

            grade = get_lead_grade(total_score)
            grade_emoji = grade["emoji"]
            grade_label = grade["label"]
            grade_color = grade["color"]
            grade_bg = grade["bg_color"]

            # Determine source badge class
            source_value = lead.source.value.lower()
            source_class = "reddit" if "reddit" in source_value else \
                          "hackernews" if "hacker" in source_value else \
                          "google" if "google" in source_value else \
                          "indeed" if "indeed" in source_value else \
                          "yelp" if "yelp" in source_value else \
                          "maps" if "maps" in source_value else "google"

            # Source icons
            source_icons = {
                "reddit": "🔴",
                "hackernews": "🟠",
                "google": "🔵",
                "indeed": "💼",
                "yelp": "⭐",
                "maps": "📍"
            }
            source_icon = source_icons.get(source_class, "🌐")

            # Keywords tags HTML
            keywords_html = ""
            if lead.keywords_matched:
                keywords_html = "".join([f'<span class="lead-keyword-tag">{kw}</span>' for kw in lead.keywords_matched[:5]])

            # Clean content for preview
            content_preview = lead.content[:300].replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
            if len(lead.content) > 300:
                content_preview += "..."

            # Build the modern lead card HTML
            st.markdown(f"""
            <div class="lead-card">
                <!-- Card Header -->
                <div class="lead-card-header">
                    <div class="lead-card-grade" style="background: {grade_bg}; border: 2px solid {grade_color}; color: {grade_color};">
                        {total_score}
                    </div>
                    <div class="lead-card-title-area">
                        <h3 class="lead-card-title">{lead.title[:80]}{'...' if len(lead.title) > 80 else ''}</h3>
                        <div class="lead-card-meta">
                            <span class="lead-source-badge {source_class}">{source_icon} {lead.source.value}</span>
                            {f'<span class="lead-industry-tag">🏭 {lead.industry}</span>' if lead.industry else ''}
                        </div>
                    </div>
                </div>

                <!-- Card Body -->
                <div class="lead-card-body">
                    <!-- Triple Score Row -->
                    <div class="lead-scores-row">
                        <div class="lead-score-mini pain">
                            <div class="lead-score-mini-icon">😣</div>
                            <div class="lead-score-mini-value">{pain_score}</div>
                            <div class="lead-score-mini-label">Pain</div>
                        </div>
                        <div class="lead-score-mini intent">
                            <div class="lead-score-mini-icon">🎯</div>
                            <div class="lead-score-mini-value">{intent_score}</div>
                            <div class="lead-score-mini-label">Intent</div>
                        </div>
                        <div class="lead-score-mini fit">
                            <div class="lead-score-mini-icon">✅</div>
                            <div class="lead-score-mini-value">{fit_score}</div>
                            <div class="lead-score-mini-label">Fit</div>
                        </div>
                    </div>

                    <!-- Keywords Section -->
                    {f'''<div class="lead-keywords-section">
                        <div class="lead-keywords-title">Matched Keywords</div>
                        <div>{keywords_html}</div>
                    </div>''' if keywords_html else ''}

                    <!-- Content Preview -->
                    <div class="lead-content-preview">
                        <p class="lead-content-text">{content_preview}</p>
                    </div>
                </div>

                <!-- Card Footer -->
                <div class="lead-card-footer">
                    <div class="lead-action-text" style="color: {grade_color};">
                        <span>{grade_emoji}</span>
                        <span>{grade['action']}</span>
                    </div>
                    <a href="{lead.url}" target="_blank" class="lead-view-btn">
                        View Original ↗
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Section to review ALL raw leads (before AI filter)
    if st.session_state.scraping_done and st.session_state.raw_leads:
        st.divider()

        raw_count = len(st.session_state.raw_leads)
        filtered_count = len(st.session_state.filtered_leads)
        rejected_count = raw_count - filtered_count

        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%);
                    border-radius: 12px; padding: 16px; margin: 16px 0; border-left: 4px solid #F59E0B;">
            <h3 style="margin: 0 0 8px 0; color: #92400E;">📋 Review All Results</h3>
            <p style="margin: 0; color: #78350F;">
                Found <strong>{raw_count}</strong> total leads |
                AI Qualified: <strong>{filtered_count}</strong> |
                Rejected: <strong>{rejected_count}</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"👁️ View ALL {raw_count} leads (before AI filter)", expanded=False):
            st.info("These are ALL leads found, including those rejected by AI. Review manually to ensure nothing was missed.")

            for i, lead in enumerate(st.session_state.raw_leads):
                is_qualified = lead in st.session_state.filtered_leads
                status_icon = "✅" if is_qualified else "❌"
                status_text = "AI Qualified" if is_qualified else "AI Rejected"

                with st.container():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"""
                        <div style="padding: 8px; margin: 4px 0; background: {'#D1FAE5' if is_qualified else '#FEE2E2'};
                                    border-radius: 8px; border-left: 3px solid {'#10B981' if is_qualified else '#EF4444'};">
                            <strong>{status_icon} {lead.title[:70]}{'...' if len(lead.title) > 70 else ''}</strong><br>
                            <small style="color: #6B7280;">
                                Source: {lead.source.value} | Score: {lead.pain_score} | {status_text}
                            </small>
                        </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        st.link_button("View", lead.url, use_container_width=True)

        # Clear results button
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Search Results", type="secondary", use_container_width=True):
                st.session_state.raw_leads = []
                st.session_state.filtered_leads = []
                st.session_state.leads = []
                st.session_state.scraping_done = False
                st.session_state.last_search_results = None
                st.rerun()
        with col2:
            if st.button("💾 Keep & Continue", type="primary", use_container_width=True):
                st.success("Results saved! You can view them in My Leads or CRM anytime.")


def show_leads():
    # Holographic Page Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%);
                border: 1px solid rgba(0, 255, 255, 0.3);
                border-radius: 16px;
                padding: 32px;
                margin-bottom: 24px;
                backdrop-filter: blur(10px);
                box-shadow: 0 0 40px rgba(0, 255, 255, 0.1), inset 0 0 60px rgba(0, 255, 255, 0.05);
                position: relative;
                overflow: hidden;">
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent 0%, #00FFFF 50%, transparent 100%); opacity: 0.8;"></div>
        <h1 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 32px; margin: 0 0 8px 0; letter-spacing: 0.1em; text-shadow: 0 0 20px rgba(0, 255, 255, 0.5);">
            📋 MY LEADS
        </h1>
        <p style="color: #C0C0C0; font-family: 'Rajdhani', sans-serif; font-size: 16px; margin: 0;">
            Manage and export your prospects
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Import Section with Field Mapping
    st.markdown("""
    <div style="background: rgba(28, 28, 46, 0.6); border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 12px; padding: 20px; margin-bottom: 20px; backdrop-filter: blur(5px);">
        <h3 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 18px; margin: 0 0 8px 0; letter-spacing: 0.05em;">
            📤 IMPORT LEADS
        </h3>
        <p style="color: #708090; font-size: 13px; margin: 0;">Upload CSV or Excel files to import leads</p>
    </div>
    """, unsafe_allow_html=True)

    # Define standard CRM fields
    CRM_FIELDS = {
        'name': {'label': 'Name / Title', 'icon': '👤', 'required': False},
        'email': {'label': 'Email', 'icon': '📧', 'required': False},
        'phone': {'label': 'Phone', 'icon': '📱', 'required': False},
        'company': {'label': 'Company', 'icon': '🏢', 'required': False},
        'position': {'label': 'Position/Job Title', 'icon': '💼', 'required': False},
        'website': {'label': 'Website', 'icon': '🌐', 'required': False},
        'linkedin': {'label': 'LinkedIn', 'icon': '🔗', 'required': False},
        'location': {'label': 'Location/City', 'icon': '📍', 'required': False},
        'country': {'label': 'Country', 'icon': '🌍', 'required': False},
        'industry': {'label': 'Industry', 'icon': '🏭', 'required': False},
        'notes': {'label': 'Notes', 'icon': '📝', 'required': False},
        'source': {'label': 'Source', 'icon': '📥', 'required': False},
        'status': {'label': 'Status', 'icon': '📊', 'required': False},
    }

    uploaded_file = st.file_uploader(
        "Upload file with leads",
        type=['csv', 'xlsx', 'xls'],
        help="Supports CSV and Excel files (.xlsx, .xls). Excel files can have multiple sheets."
    )

    if uploaded_file is not None:
        file_extension = uploaded_file.name.split('.')[-1].lower()

        if file_extension in ['xlsx', 'xls']:
            # Excel file - show sheet selection and field mapping
            file_content = uploaded_file.getvalue()
            sheets = lead_manager.get_excel_sheets(file_content)

            if sheets:
                st.info(f"📊 Excel file detected with **{len(sheets)} sheet(s)**: {', '.join(sheets)}")

                # Sheet selection
                selected_sheet = st.selectbox("Select sheet to preview", sheets)

                # Read the selected sheet for preview
                try:
                    import pandas as pd
                    import io
                    df_preview = pd.read_excel(io.BytesIO(file_content), sheet_name=selected_sheet, nrows=5)
                    df_full = pd.read_excel(io.BytesIO(file_content), sheet_name=selected_sheet)
                    file_columns = list(df_preview.columns)

                    st.success(f"Found **{len(df_full)}** rows and **{len(file_columns)}** columns")

                    # Data Preview
                    with st.expander("📋 Data Preview (first 5 rows)", expanded=True):
                        st.dataframe(df_preview, use_container_width=True)

                    # Field Mapping Section
                    st.markdown("### 🔗 Field Mapping")
                    st.caption("Match your file columns to CRM fields. Leave as 'Skip' to ignore a column.")

                    # Auto-detect column mappings
                    auto_mappings = {}
                    column_lower_map = {col.lower().strip(): col for col in file_columns}

                    mapping_hints = {
                        'name': ['name', 'nombre', 'title', 'titulo', 'contact', 'contacto', 'full name', 'nombre completo'],
                        'email': ['email', 'correo', 'e-mail', 'mail', 'email address'],
                        'phone': ['phone', 'telefono', 'tel', 'mobile', 'celular', 'whatsapp', 'telephone'],
                        'company': ['company', 'empresa', 'organization', 'business', 'company name'],
                        'position': ['position', 'cargo', 'job', 'title', 'role', 'puesto', 'job title'],
                        'website': ['website', 'web', 'sitio', 'url', 'domain'],
                        'linkedin': ['linkedin', 'linkedin url'],
                        'location': ['location', 'city', 'ciudad', 'ubicacion', 'address'],
                        'country': ['country', 'pais', 'nation'],
                        'industry': ['industry', 'industria', 'sector', 'vertical'],
                        'notes': ['notes', 'notas', 'comments', 'comentarios'],
                        'source': ['source', 'fuente', 'origen'],
                        'status': ['status', 'estado', 'stage'],
                    }

                    for field, hints in mapping_hints.items():
                        for hint in hints:
                            if hint in column_lower_map:
                                auto_mappings[field] = column_lower_map[hint]
                                break

                    # Display mapping interface
                    mapping_cols = st.columns(3)
                    field_mappings = {}

                    for idx, (field_key, field_info) in enumerate(CRM_FIELDS.items()):
                        with mapping_cols[idx % 3]:
                            default_idx = 0
                            options = ['-- Skip --'] + file_columns
                            if field_key in auto_mappings:
                                try:
                                    default_idx = options.index(auto_mappings[field_key])
                                except ValueError:
                                    default_idx = 0

                            selected = st.selectbox(
                                f"{field_info['icon']} {field_info['label']}",
                                options=options,
                                index=default_idx,
                                key=f"map_{field_key}"
                            )
                            if selected != '-- Skip --':
                                field_mappings[field_key] = selected

                    # Import buttons
                    st.markdown("---")
                    import_col1, import_col2, import_col3 = st.columns([2, 2, 1])

                    with import_col1:
                        import_all_sheets = st.checkbox("Import all sheets with same mapping", value=False)

                    with import_col2:
                        st.caption(f"Mapped **{len(field_mappings)}** fields")

                    with import_col3:
                        if st.button("📥 Import", type="primary", use_container_width=True):
                            sheets_to_import = sheets if import_all_sheets else [selected_sheet]

                            with st.spinner(f"Importing {len(sheets_to_import)} sheet(s)..."):
                                result = lead_manager.import_from_excel_mapped(
                                    file_content,
                                    sheets_to_import,
                                    field_mappings
                                )

                            if result.get('error_message'):
                                st.error(f"Error: {result['error_message']}")
                            else:
                                st.success(f"✅ Imported: **{result['imported']}** | Duplicates: {result['duplicates']} | Errors: {result['errors']}")
                                st.rerun()

                except Exception as e:
                    st.error(f"Error reading file: {str(e)}")
                    # Fallback to original import
                    if st.button("📥 Import (Auto-detect fields)", type="primary"):
                        result = lead_manager.import_from_excel(file_content, sheets)
                        if result.get('error_message'):
                            st.error(f"Error: {result['error_message']}")
                        else:
                            st.success(f"✅ Imported: **{result['imported']}**")
                            st.rerun()
            else:
                st.error("Could not read sheets from Excel file.")

        else:
            # CSV file with field mapping
            try:
                import pandas as pd
                import io
                csv_content = uploaded_file.getvalue().decode('utf-8')
                df_preview = pd.read_csv(io.StringIO(csv_content), nrows=5)
                df_full = pd.read_csv(io.StringIO(csv_content))
                file_columns = list(df_preview.columns)

                st.success(f"Found **{len(df_full)}** rows and **{len(file_columns)}** columns")

                # Data Preview
                with st.expander("📋 Data Preview (first 5 rows)", expanded=True):
                    st.dataframe(df_preview, use_container_width=True)

                # Field Mapping
                st.markdown("### 🔗 Field Mapping")
                st.caption("Match your file columns to CRM fields")

                # Auto-detect
                auto_mappings = {}
                column_lower_map = {col.lower().strip(): col for col in file_columns}

                mapping_hints = {
                    'name': ['name', 'nombre', 'title', 'titulo', 'contact'],
                    'email': ['email', 'correo', 'e-mail', 'mail'],
                    'phone': ['phone', 'telefono', 'tel', 'mobile', 'celular'],
                    'company': ['company', 'empresa', 'organization'],
                    'position': ['position', 'cargo', 'job', 'title', 'role'],
                    'website': ['website', 'web', 'url'],
                    'linkedin': ['linkedin'],
                    'location': ['location', 'city', 'ciudad'],
                    'country': ['country', 'pais'],
                    'industry': ['industry', 'industria', 'sector'],
                    'notes': ['notes', 'notas', 'comments'],
                    'source': ['source', 'fuente'],
                    'status': ['status', 'estado'],
                }

                for field, hints in mapping_hints.items():
                    for hint in hints:
                        if hint in column_lower_map:
                            auto_mappings[field] = column_lower_map[hint]
                            break

                mapping_cols = st.columns(3)
                field_mappings = {}

                for idx, (field_key, field_info) in enumerate(CRM_FIELDS.items()):
                    with mapping_cols[idx % 3]:
                        default_idx = 0
                        options = ['-- Skip --'] + file_columns
                        if field_key in auto_mappings:
                            try:
                                default_idx = options.index(auto_mappings[field_key])
                            except ValueError:
                                default_idx = 0

                        selected = st.selectbox(
                            f"{field_info['icon']} {field_info['label']}",
                            options=options,
                            index=default_idx,
                            key=f"csv_map_{field_key}"
                        )
                        if selected != '-- Skip --':
                            field_mappings[field_key] = selected

                st.markdown("---")
                if st.button("📥 Import Leads", type="primary"):
                    result = lead_manager.import_from_csv_mapped(csv_content, field_mappings)

                    if result.get('error_message'):
                        st.error(f"Error: {result['error_message']}")
                    else:
                        st.success(f"✅ Imported: {result['imported']} | Duplicates: {result['duplicates']} | Errors: {result['errors']}")
                        st.rerun()

            except Exception as e:
                st.error(f"Error reading CSV: {str(e)}")
                if st.button("📥 Import (Auto-detect)", type="primary"):
                    csv_content = uploaded_file.getvalue().decode('utf-8')
                    result = lead_manager.import_from_csv(csv_content)
                    if result.get('error_message'):
                        st.error(f"Error: {result['error_message']}")
                    else:
                        st.success(f"✅ Imported: {result['imported']}")
                        st.rerun()

    st.divider()

    # Export and Actions Row
    st.subheader("📥 Export Leads")
    col_exp1, col_exp2, col_exp3, col_exp4 = st.columns(4)

    with col_exp1:
        # CSV Export for session leads
        if st.session_state.filtered_leads:
            csv_data = csv_exporter.export_leads(st.session_state.filtered_leads)
            st.download_button(
                label="📥 Export CSV (Session)",
                data=csv_data,
                file_name=f"leads_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.button("📥 Export CSV (Session)", disabled=True, use_container_width=True)

    with col_exp2:
        # CSV Export for all saved leads
        saved_leads = lead_manager.load_leads()
        if saved_leads:
            csv_all_data = csv_exporter.export_leads_from_dict(saved_leads)
            st.download_button(
                label=f"📦 Export All ({len(saved_leads)})",
                data=csv_all_data,
                file_name=f"all_leads_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.button("📦 Export All (0)", disabled=True, use_container_width=True)

    with col_exp3:
        # Show storage stats
        stats = lead_manager.get_stats()
        st.metric("Total Saved", stats['total'])

    with col_exp4:
        st.metric("Hot Leads", stats.get('hot_leads', 0))

    st.divider()

    tab1, tab2, tab3 = st.tabs(["Session Leads", "Saved Leads", "HubSpot"])

    with tab1:
        if not st.session_state.filtered_leads:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-icon">🔍</div>
                <h3 class="empty-title">No leads yet</h3>
                <p class="empty-desc">Go to Find Leads to find prospects</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            qualified = len([l for l in st.session_state.filtered_leads if l.is_qualified])
            hot_leads = len([l for l in st.session_state.filtered_leads if l.pain_score >= 70])
            avg_score = sum(l.pain_score for l in st.session_state.filtered_leads) / len(st.session_state.filtered_leads)

            st.markdown(f"""
            <div class="stats-bar">
                <div class="stat-item">
                    <span class="stat-value">{len(st.session_state.filtered_leads)}</span>
                    <span class="stat-label">total</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value" style="color: var(--error-500);">{hot_leads}</span>
                    <span class="stat-label">hot leads</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value" style="color: var(--success-600);">{qualified}</span>
                    <span class="stat-label">qualified</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value" style="color: var(--primary-600);">{avg_score:.0f}</span>
                    <span class="stat-label">avg score</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Filters
            col1, col2, col3 = st.columns(3)
            with col1:
                filter_urgency = st.selectbox("Filter by Urgency", ["All", "Hot (70+)", "High (50+)", "Medium (25+)"])
            with col2:
                industries_found = list(set(l.industry for l in st.session_state.filtered_leads if l.industry))
                filter_industry = st.selectbox("Filter by Industry", ["All"] + industries_found)
            with col3:
                sort_by = st.selectbox("Sort by", ["Pain Score", "Date Found", "AI Score"])

            # Apply filters
            filtered = st.session_state.filtered_leads.copy()
            if filter_urgency == "Hot (70+)":
                filtered = [l for l in filtered if l.pain_score >= 70]
            elif filter_urgency == "High (50+)":
                filtered = [l for l in filtered if l.pain_score >= 50]
            elif filter_urgency == "Medium (25+)":
                filtered = [l for l in filtered if l.pain_score >= 25]

            if filter_industry != "All":
                filtered = [l for l in filtered if l.industry == filter_industry]

            if sort_by == "Pain Score":
                filtered = sorted(filtered, key=lambda x: x.pain_score, reverse=True)
            elif sort_by == "AI Score":
                filtered = sorted(filtered, key=lambda x: x.ai_score or 0, reverse=True)
            else:
                filtered = sorted(filtered, key=lambda x: x.found_at, reverse=True)

            st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)

            # Build data with proper None handling
            data = []
            for l in filtered:
                title = l.title or "No title"
                data.append({
                    "Pain": l.pain_score or 0,
                    "Title": title[:40] + "..." if len(title) > 40 else title,
                    "Industry": l.industry or "-",
                    "Source": l.source.value if l.source else "-",
                    "Keywords": len(l.keywords_matched) if l.keywords_matched else 0,
                    "AI": f"{l.ai_score:.2f}" if l.ai_score else "-"
                })

            if data:
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            else:
                st.info("No leads match the current filters")

            st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)

            if st.button("Send to HubSpot", type="primary"):
                with HubSpotCRM() as crm:
                    if not crm.is_configured():
                        st.error("HubSpot not configured")
                    else:
                        with st.spinner("Sending..."):
                            r = crm.send_leads_to_crm(st.session_state.filtered_leads)
                        st.markdown(f"""
                        <div class="results-box">
                            <div class="result-item">
                                <div class="result-value green">{r['created']}</div>
                                <div class="result-label">Created</div>
                            </div>
                            <div class="result-item">
                                <div class="result-value orange">{r['existing']}</div>
                                <div class="result-label">Existing</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

    with tab2:
        # Saved Leads from Database
        saved_leads = lead_manager.load_leads()

        if not saved_leads:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-icon">💾</div>
                <h3 class="empty-title">No saved leads</h3>
                <p class="empty-desc">Leads will be automatically saved when you search</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.success(f"Found {len(saved_leads)} saved leads in database")

            # Display saved leads with proper None handling
            data = []
            for l in saved_leads[:100]:  # Limit to 100 for performance
                title = str(l.get('title', '') or 'No title')
                saved_at = l.get('saved_at', '')
                data.append({
                    "Pain": l.get('pain_score', 0) or 0,
                    "Title": title[:40] + "..." if len(title) > 40 else title,
                    "Industry": l.get('industry', '-') or '-',
                    "Source": l.get('source', '-') or '-',
                    "Saved": saved_at[:10] if saved_at else '-'
                })

            if data:
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            else:
                st.info("No saved leads to display")

            st.divider()

            # Clear storage button
            col_clear1, col_clear2 = st.columns([3, 1])
            with col_clear2:
                if st.button("🗑️ Clear All Saved", type="secondary"):
                    lead_manager.clear_storage()
                    st.success("Storage cleared!")
                    st.rerun()

    with tab3:
        with HubSpotCRM() as crm:
            if not crm.is_configured():
                st.markdown("""
                <div class="empty-state">
                    <div class="empty-icon">☁️</div>
                    <h3 class="empty-title">HubSpot not connected</h3>
                    <p class="empty-desc">Configure your HubSpot API key in Settings to enable CRM integration</p>
                </div>
                """, unsafe_allow_html=True)

                st.info("💡 Ve a Settings y configura tu HubSpot API Key para sincronizar leads automáticamente")

            else:
                st.success("✅ HubSpot está conectado")

                # Sync buttons section
                st.markdown("### 🔄 Sync Leads to HubSpot")

                sync_col1, sync_col2 = st.columns(2)

                with sync_col1:
                    # Sync saved leads
                    saved_leads_for_sync = lead_manager.load_leads()
                    not_synced = [l for l in saved_leads_for_sync if not l.get('hubspot_synced')]

                    st.markdown(f"**Saved Leads:** {len(saved_leads_for_sync)} total, {len(not_synced)} pending sync")

                    if st.button(f"🔄 Sync {len(not_synced)} Pending Leads", type="primary", use_container_width=True, disabled=len(not_synced)==0):
                        sync_progress = st.progress(0)
                        synced_count = 0

                        for i, lead_dict in enumerate(not_synced):
                            try:
                                # Create a Lead object from dict
                                from src.utils.models import Lead as LeadModel, LeadSource
                                lead_obj = LeadModel(
                                    id=lead_dict.get('hash', ''),
                                    source=LeadSource.REDDIT,
                                    title=lead_dict.get('title') or lead_dict.get('author') or '',
                                    content=lead_dict.get('content', ''),
                                    url=lead_dict.get('url', ''),
                                    email=lead_dict.get('email'),
                                    name=lead_dict.get('author') or lead_dict.get('title'),
                                    company=lead_dict.get('company'),
                                    phone=lead_dict.get('phone'),
                                    industry=lead_dict.get('industry'),
                                    pain_score=lead_dict.get('pain_score', 0)
                                )
                                result = crm.create_contact(lead_obj)
                                if result:
                                    lead_dict['hubspot_synced'] = True
                                    lead_dict['hubspot_id'] = result
                                    synced_count += 1
                            except Exception as e:
                                pass
                            sync_progress.progress((i + 1) / len(not_synced))

                        # Save the updated sync status
                        lead_manager._save_leads_direct(saved_leads_for_sync)
                        st.success(f"✅ Synced {synced_count} leads to HubSpot!")
                        st.rerun()

                with sync_col2:
                    # Sync session leads
                    session_leads = st.session_state.filtered_leads if st.session_state.filtered_leads else []
                    st.markdown(f"**Session Leads:** {len(session_leads)} leads from current session")

                    if st.button(f"🔄 Sync {len(session_leads)} Session Leads", use_container_width=True, disabled=len(session_leads)==0):
                        sync_progress2 = st.progress(0)
                        synced_count2 = 0

                        for i, lead in enumerate(session_leads):
                            try:
                                result = crm.create_contact(lead)
                                if result:
                                    synced_count2 += 1
                            except:
                                pass
                            sync_progress2.progress((i + 1) / len(session_leads))

                        st.success(f"✅ Synced {synced_count2} session leads to HubSpot!")

                st.markdown("---")

                # View HubSpot contacts
                st.markdown("### 📋 HubSpot Contacts")
                stage = st.selectbox("Filter by stage", ["All"] + [s.value for s in LeadStage])

                if st.button("🔍 Load from HubSpot", type="primary"):
                    try:
                        with st.spinner("Loading..."):
                            contacts = crm.get_all_contacts() if stage == "All" else crm.get_contacts_by_stage(LeadStage(stage))
                    except Exception as e:
                        add_error_notification(
                            title="HubSpot Connection Error",
                            message=f"Could not load contacts from HubSpot. Please check your API key in Settings. Error: {str(e)[:80]}",
                            error_type="api_error",
                            source="HubSpot"
                        )
                        contacts = []

                    if contacts:
                        st.success(f"Found {len(contacts)} contacts in HubSpot")
                        data = []
                        for c in contacts:
                            data.append({
                                "Name": f"{c.firstname or ''} {c.lastname or ''}".strip() or "-",
                                "Email": c.email or "-",
                                "Company": c.company or "-",
                                "Stage": c.lead_stage.value if c.lead_stage else "-"
                            })
                        if data:
                            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
                    else:
                        st.info("No contacts found in HubSpot for this filter")


def show_analytics():
    """Analytics page with holographic visualizations."""

    # Holographic Page Header
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%);
                border: 1px solid rgba(0, 255, 255, 0.3);
                border-radius: 16px;
                padding: 32px;
                margin-bottom: 24px;
                backdrop-filter: blur(10px);
                box-shadow: 0 0 40px rgba(0, 255, 255, 0.1), inset 0 0 60px rgba(0, 255, 255, 0.05);
                position: relative;
                overflow: hidden;">
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent 0%, #00FFFF 50%, transparent 100%); opacity: 0.8;"></div>
        <h1 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 32px; margin: 0 0 8px 0; letter-spacing: 0.1em; text-shadow: 0 0 20px rgba(0, 255, 255, 0.5);">
            📊 {t('analytics_title').upper()}
        </h1>
        <p style="color: #C0C0C0; font-family: 'Rajdhani', sans-serif; font-size: 16px; margin: 0;">
            {t('analytics_subtitle')}
        </p>
    </div>
    """, unsafe_allow_html=True)

    with HubSpotCRM() as crm:
        total_leads = len(st.session_state.leads)
        qualified_leads = len(st.session_state.filtered_leads)
        rate = (qualified_leads / total_leads * 100) if total_leads > 0 else 0

        # Calculate additional metrics
        hot_leads = len([l for l in st.session_state.leads if getattr(l, 'pain_score', 0) >= 70])
        avg_score = sum(getattr(l, 'pain_score', 0) for l in st.session_state.leads) / total_leads if total_leads > 0 else 0

        # Holographic KPI Cards
        st.markdown(f"""
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 32px;">
            <!-- Leads Found -->
            <div style="background: linear-gradient(135deg, rgba(0, 139, 139, 0.2) 0%, rgba(45, 55, 72, 0.4) 100%);
                        border: 1px solid rgba(0, 139, 139, 0.4);
                        border-radius: 16px;
                        padding: 24px;
                        backdrop-filter: blur(10px);
                        box-shadow: 0 0 30px rgba(0, 139, 139, 0.2), inset 0 0 30px rgba(0, 139, 139, 0.05);
                        position: relative;
                        overflow: hidden;">
                <div style="position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent 0%, #008B8B 50%, transparent 100%);"></div>
                <div style="color: #C0C0C0; font-size: 14px; margin-bottom: 8px;">🔍 {t('leads_found')}</div>
                <div style="color: #008B8B; font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 700; text-shadow: 0 0 20px rgba(0, 139, 139, 0.5);">{total_leads}</div>
                <div style="color: #708090; font-size: 12px; margin-top: 8px;">{t('total_discovered')}</div>
            </div>
            <!-- Qualified Leads -->
            <div style="background: linear-gradient(135deg, rgba(0, 255, 136, 0.2) 0%, rgba(0, 40, 40, 0.4) 100%);
                        border: 1px solid rgba(0, 255, 136, 0.4);
                        border-radius: 16px;
                        padding: 24px;
                        backdrop-filter: blur(10px);
                        box-shadow: 0 0 30px rgba(0, 255, 136, 0.2), inset 0 0 30px rgba(0, 255, 136, 0.05);
                        position: relative;
                        overflow: hidden;">
                <div style="position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent 0%, #00FF88 50%, transparent 100%);"></div>
                <div style="color: #C0C0C0; font-size: 14px; margin-bottom: 8px;">✅ {t('qualified_leads')}</div>
                <div style="color: #00FF88; font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 700; text-shadow: 0 0 20px rgba(0, 255, 136, 0.5);">{qualified_leads}</div>
                <div style="color: #708090; font-size: 12px; margin-top: 8px;">{t('passed_filters')}</div>
            </div>
            <!-- Conversion Rate -->
            <div style="background: linear-gradient(135deg, rgba(255, 184, 0, 0.2) 0%, rgba(40, 30, 0, 0.4) 100%);
                        border: 1px solid rgba(255, 184, 0, 0.4);
                        border-radius: 16px;
                        padding: 24px;
                        backdrop-filter: blur(10px);
                        box-shadow: 0 0 30px rgba(255, 184, 0, 0.2), inset 0 0 30px rgba(255, 184, 0, 0.05);
                        position: relative;
                        overflow: hidden;">
                <div style="position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent 0%, #FFB800 50%, transparent 100%);"></div>
                <div style="color: #C0C0C0; font-size: 14px; margin-bottom: 8px;">📈 {t('conversion_rate')}</div>
                <div style="color: #FFB800; font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 700; text-shadow: 0 0 20px rgba(255, 184, 0, 0.5);">{rate:.1f}%</div>
                <div style="color: #708090; font-size: 12px; margin-top: 8px;">{t('qualified_total')}</div>
            </div>
            <!-- Hot Leads -->
            <div style="background: linear-gradient(135deg, rgba(255, 51, 102, 0.2) 0%, rgba(40, 10, 20, 0.4) 100%);
                        border: 1px solid rgba(255, 51, 102, 0.4);
                        border-radius: 16px;
                        padding: 24px;
                        backdrop-filter: blur(10px);
                        box-shadow: 0 0 30px rgba(255, 51, 102, 0.2), inset 0 0 30px rgba(255, 51, 102, 0.05);
                        position: relative;
                        overflow: hidden;">
                <div style="position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent 0%, #FF3366 50%, transparent 100%);"></div>
                <div style="color: #C0C0C0; font-size: 14px; margin-bottom: 8px;">🔥 {t('hot_leads')}</div>
                <div style="color: #FF3366; font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 700; text-shadow: 0 0 20px rgba(255, 51, 102, 0.5);">{hot_leads}</div>
                <div style="color: #708090; font-size: 12px; margin-top: 8px;">Score 70+</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.leads:
            # Source distribution with holographic visualization
            st.markdown(f"""
            <div style="background: rgba(28, 28, 46, 0.6); border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 12px; padding: 20px; margin-bottom: 20px; backdrop-filter: blur(5px);">
                <h3 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 18px; margin: 0 0 8px 0; letter-spacing: 0.05em;">
                    📊 {t('leads_by_source').upper()}
                </h3>
                <p style="color: #708090; font-size: 13px; margin: 0;">{t('leads_by_source_desc')}</p>
            </div>
            """, unsafe_allow_html=True)

            # Calculate source counts
            source_counts = {}
            for l in st.session_state.leads:
                source_name = l.source.value if hasattr(l.source, 'value') else str(l.source)
                source_counts[source_name] = source_counts.get(source_name, 0) + 1

            # Source styling with neon colors
            source_colors = {
                'reddit': ('#FF4500', '🔴'),
                'google': ('#008B8B', '🔵'),
                'hackernews': ('#FF6600', '🟠'),
                'apollo': ('#008B8B', '🚀'),
                'hunter': ('#FFB800', '🎯'),
                'manual': ('#C0C0C0', '✏️'),
                'producthunt': ('#FF3366', '🟤'),
                'linkedin': ('#008B8B', '🔷')
            }

            # Build holographic bar chart
            max_count = max(source_counts.values()) if source_counts else 1
            chart_html = '<div style="background: rgba(28, 28, 46, 0.6); border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 16px; padding: 24px; backdrop-filter: blur(5px);">'

            for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
                color, icon = source_colors.get(source.lower(), ('#00FFFF', '📊'))
                width_pct = (count / max_count * 100) if max_count > 0 else 0
                pct_of_total = (count / total_leads * 100) if total_leads > 0 else 0

                chart_html += f"""
                <div style="display: flex; align-items: center; margin-bottom: 16px;">
                    <div style="width: 120px; display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 20px;">{icon}</span>
                        <span style="font-size: 14px; font-weight: 600; color: #E5E5E5; text-transform: capitalize;">{source}</span>
                    </div>
                    <div style="flex: 1; margin: 0 20px;">
                        <div style="background: rgba(45, 55, 72, 0.5); border: 1px solid rgba(0, 255, 255, 0.1); border-radius: 8px; height: 28px; overflow: hidden;">
                            <div style="background: linear-gradient(90deg, {color} 0%, {color}99 100%); width: {width_pct}%; height: 100%; border-radius: 8px; display: flex; align-items: center; padding-left: 12px; transition: width 0.5s ease; box-shadow: 0 0 15px {color}40;">
                                <span style="color: white; font-weight: 700; font-size: 13px; text-shadow: 0 0 10px rgba(255,255,255,0.5);">{count}</span>
                            </div>
                        </div>
                    </div>
                    <div style="width: 80px; text-align: right;">
                        <span style="font-size: 14px; font-weight: 600; color: {color}; text-shadow: 0 0 10px {color}80;">{pct_of_total:.1f}%</span>
                    </div>
                </div>
                """

            chart_html += '</div>'
            st.markdown(chart_html, unsafe_allow_html=True)

            # Score Distribution
            st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background: rgba(28, 28, 46, 0.6); border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 12px; padding: 20px; margin-bottom: 20px; backdrop-filter: blur(5px);">
                <h3 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 18px; margin: 0 0 8px 0; letter-spacing: 0.05em;">
                    🎯 {t('score_distribution').upper()}
                </h3>
                <p style="color: #708090; font-size: 13px; margin: 0;">{t('lead_quality_by_score')}</p>
            </div>
            """, unsafe_allow_html=True)

            # Calculate score distribution
            score_ranges = {'🔥 Hot (70-100)': 0, '🟡 Warm (40-69)': 0, '❄️ Cold (0-39)': 0}
            for l in st.session_state.leads:
                score = getattr(l, 'pain_score', 0)
                if score >= 70:
                    score_ranges['🔥 Hot (70-100)'] += 1
                elif score >= 40:
                    score_ranges['🟡 Warm (40-69)'] += 1
                else:
                    score_ranges['❄️ Cold (0-39)'] += 1

            # Holographic Score distribution cards
            st.markdown(f"""
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
                <!-- Hot Leads -->
                <div style="background: linear-gradient(135deg, rgba(255, 51, 102, 0.15) 0%, rgba(40, 10, 20, 0.4) 100%);
                            border: 1px solid rgba(255, 51, 102, 0.4);
                            border-radius: 12px;
                            padding: 20px;
                            text-align: center;
                            backdrop-filter: blur(5px);
                            box-shadow: 0 0 20px rgba(255, 51, 102, 0.15);
                            position: relative;
                            overflow: hidden;">
                    <div style="position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent 0%, #FF3366 50%, transparent 100%);"></div>
                    <div style="font-size: 32px; margin-bottom: 8px;">🔥</div>
                    <div style="font-size: 28px; font-weight: 700; color: #FF3366; font-family: 'Orbitron', sans-serif; text-shadow: 0 0 15px rgba(255, 51, 102, 0.5);">{score_ranges['🔥 Hot (70-100)']}</div>
                    <div style="font-size: 13px; color: #E5E5E5; margin-top: 4px;">Hot Leads (70-100)</div>
                    <div style="font-size: 12px; color: #708090;">{t('ready_to_contact')}</div>
                </div>
                <!-- Warm Leads -->
                <div style="background: linear-gradient(135deg, rgba(255, 184, 0, 0.15) 0%, rgba(40, 30, 0, 0.4) 100%);
                            border: 1px solid rgba(255, 184, 0, 0.4);
                            border-radius: 12px;
                            padding: 20px;
                            text-align: center;
                            backdrop-filter: blur(5px);
                            box-shadow: 0 0 20px rgba(255, 184, 0, 0.15);
                            position: relative;
                            overflow: hidden;">
                    <div style="position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent 0%, #FFB800 50%, transparent 100%);"></div>
                    <div style="font-size: 32px; margin-bottom: 8px;">🟡</div>
                    <div style="font-size: 28px; font-weight: 700; color: #FFB800; font-family: 'Orbitron', sans-serif; text-shadow: 0 0 15px rgba(255, 184, 0, 0.5);">{score_ranges['🟡 Warm (40-69)']}</div>
                    <div style="font-size: 13px; color: #E5E5E5; margin-top: 4px;">Warm Leads (40-69)</div>
                    <div style="font-size: 12px; color: #708090;">{t('need_more_nurturing')}</div>
                </div>
                <!-- Cold Leads -->
                <div style="background: linear-gradient(135deg, rgba(0, 139, 139, 0.15) 0%, rgba(28, 28, 46, 0.4) 100%);
                            border: 1px solid rgba(0, 139, 139, 0.4);
                            border-radius: 12px;
                            padding: 20px;
                            text-align: center;
                            backdrop-filter: blur(5px);
                            box-shadow: 0 0 20px rgba(0, 139, 139, 0.15);
                            position: relative;
                            overflow: hidden;">
                    <div style="position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent 0%, #008B8B 50%, transparent 100%);"></div>
                    <div style="font-size: 32px; margin-bottom: 8px;">❄️</div>
                    <div style="font-size: 28px; font-weight: 700; color: #008B8B; font-family: 'Orbitron', sans-serif; text-shadow: 0 0 15px rgba(0, 139, 139, 0.5);">{score_ranges['❄️ Cold (0-39)']}</div>
                    <div style="font-size: 13px; color: #E5E5E5; margin-top: 4px;">Cold Leads (0-39)</div>
                    <div style="font-size: 12px; color: #708090;">{t('low_priority')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        else:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 100%); border: 1px solid #BAE6FD; border-radius: 16px; padding: 40px; text-align: center; margin-top: 24px;">
                <div style="font-size: 48px; margin-bottom: 16px;">📊</div>
                <h3 style="color: #0369A1; margin: 0 0 8px 0;">{t('no_data_yet')}</h3>
                <p style="color: #0284C7; margin: 0;">{t('go_to_find_leads')}</p>
            </div>
            """, unsafe_allow_html=True)

        # HubSpot connection notice
        if not crm.is_configured():
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%);
                        border-left: 4px solid #6366F1;
                        border-radius: 12px;
                        padding: 16px 20px;
                        margin-top: 32px;">
                <p style="color: #1E293B; font-weight: 600; margin: 0 0 4px 0; font-size: 14px;">
                    🔗 {t('connect_hubspot')}
                </p>
                <p style="color: #475569; margin: 0; font-size: 13px;">
                    {t('go_to_settings')}
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Show HubSpot stats if connected
            try:
                with st.spinner(t('loading_hubspot')):
                    stats = crm.get_statistics()
            except Exception as e:
                add_error_notification(
                    title="HubSpot Statistics Error",
                    message=f"Could not load statistics from HubSpot. Error: {str(e)[:80]}",
                    error_type="api_error",
                    source="HubSpot"
                )
                stats = {"error": str(e)}

            if "error" not in stats:
                st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)
                st.markdown(f"""
                <div style="margin-bottom: 16px;">
                    <h3 style="color: #1E293B; margin: 0 0 8px 0; font-size: 20px;">🔗 {t('hubspot_statistics')}</h3>
                    <p style="color: #64748B; margin: 0; font-size: 13px;">{t('data_synced')}</p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;">
                    <div style="background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 20px; text-align: center;">
                        <div style="font-size: 24px; margin-bottom: 8px;">👥</div>
                        <div style="font-size: 24px; font-weight: 700; color: #1E293B;">{stats.get('total_leads', 0)}</div>
                        <div style="font-size: 13px; color: #6B7280;">Total Leads</div>
                    </div>
                    <div style="background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 20px; text-align: center;">
                        <div style="font-size: 24px; margin-bottom: 8px;">📈</div>
                        <div style="font-size: 24px; font-weight: 700; color: #1E293B;">{stats.get('conversion_rate', 0)}%</div>
                        <div style="font-size: 13px; color: #6B7280;">Conversión</div>
                    </div>
                    <div style="background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 20px; text-align: center;">
                        <div style="font-size: 24px; margin-bottom: 8px;">🏆</div>
                        <div style="font-size: 24px; font-weight: 700; color: #1E293B;">{stats.get('win_rate', 0)}%</div>
                        <div style="font-size: 13px; color: #6B7280;">Win Rate</div>
                    </div>
                    <div style="background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 20px; text-align: center;">
                        <div style="font-size: 24px; margin-bottom: 8px;">✅</div>
                        <div style="font-size: 24px; font-weight: 700; color: #10B981;">{stats.get('by_stage', {{}}).get('closed_won', 0)}</div>
                        <div style="font-size: 13px; color: #6B7280;">{t('won')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # HubSpot stage distribution
                if stats.get("by_stage"):
                    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="margin-bottom: 12px;">
                        <h4 style="color: #1E293B; margin: 0; font-size: 16px;">{t('by_stage_hubspot')}</h4>
                    </div>
                    """, unsafe_allow_html=True)

                    stage_html = '<div style="background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 20px;">'
                    max_stage = max(stats["by_stage"].values()) if stats["by_stage"].values() else 1
                    stage_colors = ['#3B82F6', '#06B6D4', '#8B5CF6', '#F59E0B', '#10B981', '#EF4444']

                    for i, (stage, count) in enumerate(stats["by_stage"].items()):
                        color = stage_colors[i % len(stage_colors)]
                        width = (count / max_stage * 100) if max_stage > 0 else 0

                        stage_html += f"""
                        <div style="display: flex; align-items: center; margin-bottom: 12px;">
                            <div style="width: 120px; font-size: 13px; font-weight: 500; color: #374151; text-transform: capitalize;">{stage.replace('_', ' ')}</div>
                            <div style="flex: 1; margin: 0 16px;">
                                <div style="background: #E5E7EB; border-radius: 6px; height: 24px; overflow: hidden;">
                                    <div style="background: {color}; width: {width}%; height: 100%; border-radius: 6px; display: flex; align-items: center; padding-left: 10px;">
                                        <span style="color: white; font-weight: 600; font-size: 12px;">{count}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        """
                    stage_html += '</div>'
                    st.markdown(stage_html, unsafe_allow_html=True)


def show_crm():
    """Professional CRM with complete pipeline management, deals, tasks, and HubSpot sync."""

    # Holographic CRM-specific CSS
    st.markdown("""
    <style>
        /* CRM Dashboard Cards - Holographic */
        .crm-kpi-card {
            background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%);
            border: 1px solid rgba(0, 255, 255, 0.2);
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            transition: all 0.3s ease;
            box-shadow: 0 0 20px rgba(0, 255, 255, 0.1);
            backdrop-filter: blur(10px);
        }
        .crm-kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 0 30px rgba(0, 255, 255, 0.2);
            border-color: rgba(0, 255, 255, 0.4);
        }
        .crm-kpi-value {
            font-size: 32px;
            font-weight: 700;
            color: #00FFFF;
            margin: 8px 0;
            font-family: 'Orbitron', sans-serif;
            text-shadow: 0 0 15px rgba(0, 255, 255, 0.5);
        }
        .crm-kpi-label {
            font-size: 13px;
            color: #C0C0C0;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .crm-kpi-icon {
            font-size: 28px;
            margin-bottom: 8px;
        }

        /* Revenue Card - Holographic */
        .revenue-card {
            background: linear-gradient(135deg, rgba(0, 255, 136, 0.2) 0%, rgba(0, 40, 40, 0.4) 100%);
            border: 1px solid rgba(0, 255, 136, 0.4);
            border-radius: 16px;
            padding: 24px;
            color: white;
            text-align: center;
            backdrop-filter: blur(10px);
            box-shadow: 0 0 30px rgba(0, 255, 136, 0.2);
        }
        .revenue-value {
            font-size: 36px;
            font-weight: 800;
            margin: 8px 0;
            color: #00FF88;
            font-family: 'Orbitron', sans-serif;
            text-shadow: 0 0 20px rgba(0, 255, 136, 0.5);
        }
        .revenue-label {
            font-size: 14px;
            color: #C0C0C0;
        }

        /* Pipeline Stage Header - Holographic */
        .pipeline-stage {
            background: linear-gradient(180deg, rgba(45, 55, 72, 0.5) 0%, rgba(28, 28, 46, 0.7) 100%);
            border-radius: 12px;
            padding: 16px 12px;
            text-align: center;
            margin-bottom: 12px;
            border: 1px solid rgba(0, 255, 255, 0.2);
            backdrop-filter: blur(5px);
        }
        .pipeline-stage-title {
            font-weight: 700;
            font-size: 14px;
            margin: 6px 0 2px 0;
            color: #00FFFF;
            font-family: 'Orbitron', sans-serif;
        }
        .pipeline-stage-count {
            font-size: 11px;
            color: #708090;
        }

        /* Lead Card - Holographic */
        .lead-card {
            background: rgba(28, 28, 46, 0.6);
            border: 1px solid rgba(0, 255, 255, 0.15);
            border-radius: 10px;
            padding: 14px;
            margin-bottom: 10px;
            transition: all 0.2s ease;
            cursor: pointer;
            backdrop-filter: blur(5px);
        }
        .lead-card:hover {
            border-color: rgba(0, 255, 255, 0.4);
            box-shadow: 0 0 20px rgba(0, 255, 255, 0.15);
        }
        .lead-card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 10px;
        }
        .lead-card-title {
            font-weight: 600;
            font-size: 13px;
            color: #E5E5E5;
            margin: 0;
            line-height: 1.3;
        }
        .lead-card-company {
            font-size: 11px;
            color: #708090;
            margin: 4px 0 0 0;
        }
        .lead-card-score {
            background: linear-gradient(135deg, rgba(0, 139, 139, 0.3) 0%, rgba(45, 55, 72, 0.5) 100%);
            border: 1px solid rgba(0, 139, 139, 0.4);
            color: #008B8B;
            font-size: 10px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 12px;
            text-shadow: 0 0 10px rgba(0, 139, 139, 0.5);
        }
        .lead-card-info {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 10px;
        }
        .lead-card-tag {
            background: rgba(0, 255, 255, 0.1);
            color: #C0C0C0;
            font-size: 10px;
            padding: 3px 8px;
            border-radius: 6px;
            border: 1px solid rgba(0, 255, 255, 0.2);
        }
        .lead-card-actions {
            display: flex;
            gap: 4px;
            margin-top: 12px;
            padding-top: 10px;
            border-top: 1px solid rgba(0, 255, 255, 0.1);
        }
        .lead-action-btn {
            flex: 1;
            background: rgba(45, 55, 72, 0.5);
            border: 1px solid rgba(0, 255, 255, 0.2);
            border-radius: 6px;
            padding: 6px;
            font-size: 12px;
            cursor: pointer;
            text-align: center;
            transition: all 0.2s ease;
            color: #C0C0C0;
        }
        .lead-action-btn:hover {
            background: rgba(0, 255, 255, 0.2);
            color: #00FFFF;
            border-color: rgba(0, 255, 255, 0.5);
        }

        /* Contact Detail Card - Holographic */
        .contact-detail-card {
            background: rgba(28, 28, 46, 0.6);
            border: 1px solid rgba(0, 255, 255, 0.2);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 16px;
            backdrop-filter: blur(10px);
        }
        .contact-header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 1px solid rgba(0, 255, 255, 0.1);
        }
        .contact-avatar {
            width: 64px;
            height: 64px;
            background: linear-gradient(135deg, rgba(0, 255, 255, 0.3) 0%, rgba(0, 139, 139, 0.3) 100%);
            border: 1px solid rgba(0, 255, 255, 0.4);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #00FFFF;
            font-size: 24px;
            font-weight: 700;
            text-shadow: 0 0 15px rgba(0, 255, 255, 0.5);
        }
        .contact-name {
            font-size: 20px;
            font-weight: 700;
            color: #E5E5E5;
            margin: 0;
            font-family: 'Orbitron', sans-serif;
        }
        .contact-company {
            font-size: 14px;
            color: #708090;
            margin: 4px 0 0 0;
        }

        /* Activity Timeline - Holographic */
        .activity-item {
            display: flex;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid rgba(0, 255, 255, 0.1);
        }
        .activity-icon {
            width: 32px;
            height: 32px;
            background: rgba(0, 255, 255, 0.1);
            border: 1px solid rgba(0, 255, 255, 0.2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            flex-shrink: 0;
        }
        .activity-content {
            flex: 1;
        }
        .activity-text {
            font-size: 13px;
            color: #E5E5E5;
            margin: 0;
        }
        .activity-time {
            font-size: 11px;
            color: #708090;
            margin-top: 4px;
        }

        /* Quick Action Buttons - Holographic */
        .quick-action-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-top: 16px;
        }
        .quick-action-btn {
            background: rgba(28, 28, 46, 0.6);
            border: 1px solid rgba(0, 255, 255, 0.2);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s ease;
            backdrop-filter: blur(5px);
        }
        .quick-action-btn:hover {
            border-color: rgba(0, 255, 255, 0.5);
            background: rgba(0, 255, 255, 0.1);
            box-shadow: 0 0 20px rgba(0, 255, 255, 0.15);
        }
        .quick-action-icon {
            font-size: 24px;
            margin-bottom: 8px;
        }
        .quick-action-label {
            font-size: 12px;
            font-weight: 500;
            color: #C0C0C0;
        }

        /* Deal Card - Holographic */
        .deal-card {
            background: rgba(28, 28, 46, 0.6);
            border: 1px solid rgba(0, 255, 255, 0.15);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            transition: all 0.2s ease;
            backdrop-filter: blur(5px);
        }
        .deal-card:hover {
            border-color: #10B981;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.15);
        }
        .deal-value {
            font-size: 20px;
            font-weight: 700;
            color: #10B981;
        }
        .deal-name {
            font-size: 14px;
            font-weight: 600;
            color: #1E293B;
            margin: 4px 0;
        }
        .deal-company {
            font-size: 12px;
            color: #64748B;
        }

        /* Task Card */
        .task-card {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 14px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .task-card.overdue {
            border-left: 3px solid #EF4444;
        }
        .task-card.today {
            border-left: 3px solid #F59E0B;
        }
        .task-card.upcoming {
            border-left: 3px solid #3B82F6;
        }
        .task-card.completed {
            background: #F8FAFC;
            opacity: 0.7;
        }
        .task-checkbox {
            width: 20px;
            height: 20px;
            border: 2px solid #CBD5E1;
            border-radius: 4px;
            cursor: pointer;
        }
        .task-checkbox.checked {
            background: #10B981;
            border-color: #10B981;
        }
        .task-content {
            flex: 1;
        }
        .task-title {
            font-size: 13px;
            font-weight: 500;
            color: #1E293B;
        }
        .task-due {
            font-size: 11px;
            color: #94A3B8;
        }

        /* Email Template Card */
        .template-card {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 16px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .template-card:hover {
            border-color: #8B5CF6;
            background: #FAF5FF;
        }
        .template-name {
            font-weight: 600;
            font-size: 14px;
            color: #1E293B;
            margin-bottom: 4px;
        }
        .template-preview {
            font-size: 12px;
            color: #64748B;
            line-height: 1.4;
        }

        /* Calendar Day */
        .calendar-day {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 8px;
            min-height: 80px;
            font-size: 12px;
        }
        .calendar-day.today {
            border-color: #3B82F6;
            background: #EFF6FF;
        }
        .calendar-day-number {
            font-weight: 600;
            color: #1E293B;
            margin-bottom: 4px;
        }
        .calendar-event {
            background: #3B82F6;
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            margin-bottom: 2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
    </style>
    """, unsafe_allow_html=True)

    # CRM Stage definitions
    CRM_STAGES = {
        'new': {'name': 'New', 'icon': '📥', 'color': '#00FFFF', 'bg': 'linear-gradient(135deg, rgba(0, 255, 255, 0.15) 0%, rgba(28, 28, 46, 0.8) 100%)'},
        'contacted': {'name': 'Contacted', 'icon': '📧', 'color': '#8B5CF6', 'bg': 'linear-gradient(135deg, rgba(139, 92, 246, 0.15) 0%, rgba(28, 28, 46, 0.8) 100%)'},
        'demo': {'name': 'Demo', 'icon': '🎯', 'color': '#FFD700', 'bg': 'linear-gradient(135deg, rgba(255, 215, 0, 0.15) 0%, rgba(28, 28, 46, 0.8) 100%)'},
        'proposal': {'name': 'Proposal', 'icon': '📋', 'color': '#FF6B35', 'bg': 'linear-gradient(135deg, rgba(255, 107, 53, 0.15) 0%, rgba(28, 28, 46, 0.8) 100%)'},
        'won': {'name': 'Won', 'icon': '✅', 'color': '#00FF88', 'bg': 'linear-gradient(135deg, rgba(0, 255, 136, 0.15) 0%, rgba(28, 28, 46, 0.8) 100%)'},
        'lost': {'name': 'Lost', 'icon': '❌', 'color': '#FF4444', 'bg': 'linear-gradient(135deg, rgba(255, 68, 68, 0.15) 0%, rgba(28, 28, 46, 0.8) 100%)'}
    }

    # Initialize session state for CRM
    if 'crm_selected_lead' not in st.session_state:
        st.session_state.crm_selected_lead = None
    if 'crm_view' not in st.session_state:
        st.session_state.crm_view = 'pipeline'

    # Load all saved leads
    all_leads = lead_manager.load_leads()

    # Calculate stats
    status_counts = {stage: len([l for l in all_leads if l.get('status', 'new') == stage]) for stage in CRM_STAGES.keys()}
    total_leads = len(all_leads)
    won_count = status_counts.get('won', 0)
    lost_count = status_counts.get('lost', 0)
    active_count = total_leads - won_count - lost_count
    win_rate = (won_count / (won_count + lost_count) * 100) if (won_count + lost_count) > 0 else 0
    avg_score = sum(l.get('pain_score', 0) for l in all_leads) / total_leads if total_leads > 0 else 0

    # Holographic Page Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%);
                border: 1px solid rgba(0, 255, 255, 0.3);
                border-radius: 16px;
                padding: 32px;
                margin-bottom: 24px;
                backdrop-filter: blur(10px);
                box-shadow: 0 0 40px rgba(0, 255, 255, 0.1), inset 0 0 60px rgba(0, 255, 255, 0.05);
                position: relative;
                overflow: hidden;">
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent 0%, #00FFFF 50%, transparent 100%); opacity: 0.8;"></div>
        <h1 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 32px; margin: 0 0 8px 0; letter-spacing: 0.1em; text-shadow: 0 0 20px rgba(0, 255, 255, 0.5);">
            🎯 CRM PIPELINE
        </h1>
        <p style="color: #C0C0C0; font-family: 'Rajdhani', sans-serif; font-size: 16px; margin: 0;">
            Manage your sales pipeline and track deals through every stage
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Empty state - Holographic
    if not all_leads:
        st.markdown("""
        <div style="text-align: center; padding: 60px 20px; background: linear-gradient(135deg, rgba(45, 55, 72, 0.4) 0%, rgba(28, 28, 46, 0.6) 100%); border-radius: 16px; border: 2px dashed rgba(0, 255, 255, 0.3); backdrop-filter: blur(10px);">
            <div style="font-size: 48px; margin-bottom: 16px; filter: drop-shadow(0 0 10px rgba(0, 255, 255, 0.5));">📋</div>
            <h3 style="margin: 0 0 8px 0; color: #00FFFF; font-size: 20px; font-family: 'Orbitron', sans-serif;">No leads in your CRM</h3>
            <p style="margin: 0; color: #C0C0C0;">Import leads or search for new leads to start building your pipeline</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔍 Find Leads", type="primary", use_container_width=True):
                st.session_state.nav_page = "Find Leads"
                st.rerun()
            if st.button("📥 Import Leads", use_container_width=True):
                st.session_state.nav_page = "My Leads"
                st.rerun()
        return

    # KPI Dashboard - Holographic
    st.markdown("""
    <div style="margin-bottom: 16px;">
        <h3 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 18px; margin: 0; text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);">📊 DASHBOARD METRICS</h3>
    </div>
    """, unsafe_allow_html=True)
    kpi_cols = st.columns(6)

    kpi_data = [
        ("📊", "Total Leads", total_leads, "#00FFFF"),
        ("🔥", "Active", active_count, "#FFD700"),
        ("📈", "Win Rate", f"{win_rate:.0f}%", "#00FF88"),
        ("✅", "Won", won_count, "#00FF88"),
        ("❌", "Lost", lost_count, "#FF4444"),
        ("⭐", "Avg Score", f"{avg_score:.0f}", "#8B5CF6")
    ]

    for i, (icon, label, value, color) in enumerate(kpi_data):
        with kpi_cols[i]:
            st.markdown(f"""
            <div class="crm-kpi-card">
                <div class="crm-kpi-icon">{icon}</div>
                <div class="crm-kpi-value" style="color: {color};">{value}</div>
                <div class="crm-kpi-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # Initialize session state for deals and tasks
    if 'crm_deals' not in st.session_state:
        st.session_state.crm_deals = []
    if 'crm_tasks' not in st.session_state:
        st.session_state.crm_tasks = []
    if 'email_templates' not in st.session_state:
        st.session_state.email_templates = [
            {
                'id': '1',
                'name': 'Initial Outreach',
                'subject': 'Quick question about {{company}}',
                'body': '''Hi {{name}},

I noticed that {{company}} might benefit from an AI receptionist that can handle calls 24/7, schedule appointments, and never miss a lead.

Would you be open to a quick 15-minute call to see if this could help your business?

Best regards'''
            },
            {
                'id': '2',
                'name': 'Follow Up',
                'subject': 'Following up - AI Receptionist for {{company}}',
                'body': '''Hi {{name}},

I wanted to follow up on my previous message about our AI receptionist solution.

Many {{industry}} businesses like yours have seen:
- 40% reduction in missed calls
- 24/7 availability for customers
- Automated appointment scheduling

Would next week work for a quick demo?

Best regards'''
            },
            {
                'id': '3',
                'name': 'Demo Confirmation',
                'subject': 'Demo Confirmed - {{date}}',
                'body': '''Hi {{name}},

Great news! Your demo is confirmed for {{date}}.

During our 15-minute call, I'll show you:
1. How the AI handles real customer calls
2. The appointment scheduling system
3. How leads are captured and organized

Looking forward to speaking with you!

Best regards'''
            },
            {
                'id': '4',
                'name': 'Proposal Follow-up',
                'subject': 'Your AI Receptionist Proposal',
                'body': '''Hi {{name}},

I hope you had a chance to review our proposal for {{company}}.

As a reminder, the solution includes:
- 24/7 AI phone answering
- Appointment scheduling
- Lead capture and qualification
- CRM integration

Do you have any questions? I'm happy to jump on a quick call.

Best regards'''
            },
            {
                'id': '5',
                'name': 'Win-Back / Re-engagement',
                'subject': 'Still missing calls at {{company}}?',
                'body': '''Hi {{name}},

We spoke a while back about improving call handling at {{company}}.

Since then, we've helped dozens of {{industry}} businesses:
- Capture 100% of incoming calls
- Reduce customer wait times by 80%
- Book appointments automatically

Things change - if you're still dealing with missed calls or overwhelmed staff, I'd love to reconnect.

Would 15 minutes this week work?

Best regards'''
            }
        ]

    # Calculate deal metrics
    total_deal_value = sum(d.get('value', 0) for d in st.session_state.crm_deals)
    won_deal_value = sum(d.get('value', 0) for d in st.session_state.crm_deals if d.get('stage') == 'won')
    pipeline_value = sum(d.get('value', 0) for d in st.session_state.crm_deals if d.get('stage') not in ['won', 'lost'])

    # Main CRM Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "🎯 Pipeline",
        "👥 Contacts",
        "💰 Deals",
        "✅ Tasks",
        "📧 Email",
        "📅 Calendar",
        "📊 Analytics",
        "🔗 HubSpot"
    ])

    # ==================== TAB 1: PIPELINE VIEW ====================
    with tab1:
        st.markdown("""
        <div style="margin-bottom: 20px;">
            <h3 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 20px; margin: 0; text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);">🚀 SALES PIPELINE</h3>
            <p style="color: #708090; font-size: 13px; margin: 4px 0 0 0;">Drag leads through stages to track progress</p>
        </div>
        """, unsafe_allow_html=True)

        # Pipeline columns
        stage_cols = st.columns(6)

        for i, (stage_key, stage_info) in enumerate(CRM_STAGES.items()):
            with stage_cols[i]:
                # Stage header
                st.markdown(f"""
                <div class="pipeline-stage" style="border-top: 3px solid {stage_info['color']}; background: {stage_info['bg']};">
                    <span style="font-size: 24px;">{stage_info['icon']}</span>
                    <p class="pipeline-stage-title" style="color: {stage_info['color']};">{stage_info['name']}</p>
                    <span class="pipeline-stage-count">{status_counts.get(stage_key, 0)} leads</span>
                </div>
                """, unsafe_allow_html=True)

                # Get leads for this stage
                stage_leads = [l for l in all_leads if (l.get('status') or 'new') == stage_key]

                # Show leads
                for idx, lead in enumerate(stage_leads[:8]):
                    lead_hash = lead.get('hash') or ''
                    # Safe string handling
                    lead_title = (lead.get('title') or lead.get('author') or lead.get('company') or 'Unknown Lead')[:30]
                    lead_company = (lead.get('company') or '')[:20]
                    lead_email = lead.get('email') or ''
                    pain_score = lead.get('pain_score') or 0

                    # Lead card
                    email_display = f'<span class="lead-card-tag">📧 {lead_email[:20]}</span>' if lead_email else ''
                    company_display = f'<p class="lead-card-company">{lead_company}</p>' if lead_company else ''

                    st.markdown(f"""
                    <div class="lead-card">
                        <div class="lead-card-header">
                            <div>
                                <p class="lead-card-title">{lead_title}</p>
                                {company_display}
                            </div>
                            <span class="lead-card-score">{pain_score}</span>
                        </div>
                        <div class="lead-card-info">
                            {email_display}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Quick action buttons for each lead
                    btn_cols = st.columns(3)

                    # Get next stage
                    stages_list = list(CRM_STAGES.keys())
                    current_idx = stages_list.index(stage_key) if stage_key in stages_list else 0

                    with btn_cols[0]:
                        if current_idx > 0:
                            if st.button("⬅️", key=f"prev_{lead_hash}_{idx}", help="Move to previous stage"):
                                prev_stage = stages_list[current_idx - 1]
                                lead_manager.update_lead_status(lead_hash, prev_stage)
                                st.rerun()

                    with btn_cols[1]:
                        if st.button("👁️", key=f"view_{lead_hash}_{idx}", help="View details"):
                            st.session_state.crm_selected_lead = lead_hash
                            st.session_state.crm_view = 'detail'

                    with btn_cols[2]:
                        if current_idx < len(stages_list) - 1 and stage_key not in ['won', 'lost']:
                            if st.button("➡️", key=f"next_{lead_hash}_{idx}", help="Move to next stage"):
                                next_stage = stages_list[current_idx + 1]
                                lead_manager.update_lead_status(lead_hash, next_stage)
                                st.rerun()

                if len(stage_leads) > 8:
                    st.caption(f"+{len(stage_leads) - 8} more leads")

    # ==================== TAB 2: ALL CONTACTS (DATA TABLE) ====================
    with tab2:
        st.markdown("""
        <div style="margin-bottom: 20px;">
            <h3 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 20px; margin: 0; text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);">📇 CONTACT DATABASE</h3>
            <p style="color: #708090; font-size: 13px; margin: 4px 0 0 0;">Search, filter and manage all your contacts</p>
        </div>
        """, unsafe_allow_html=True)

        # Top toolbar
        toolbar_col1, toolbar_col2, toolbar_col3, toolbar_col4, toolbar_col5 = st.columns([3, 2, 2, 2, 1])

        with toolbar_col1:
            search_term = st.text_input("🔍 Search contacts", placeholder="Name, email, company, phone...", key="crm_search", label_visibility="collapsed")

        with toolbar_col2:
            filter_stage = st.selectbox(
                "Stage",
                ["All Stages"] + list(CRM_STAGES.keys()),
                format_func=lambda x: f"{CRM_STAGES[x]['icon']} {CRM_STAGES[x]['name']}" if x in CRM_STAGES else "All Stages",
                key="crm_filter_stage",
                label_visibility="collapsed"
            )

        with toolbar_col3:
            sort_options = {
                "recent": "Most Recent",
                "score_high": "Score (High to Low)",
                "score_low": "Score (Low to High)",
                "name_az": "Name A-Z",
                "company": "Company A-Z"
            }
            sort_by = st.selectbox("Sort", list(sort_options.keys()), format_func=lambda x: sort_options[x], key="crm_sort", label_visibility="collapsed")

        with toolbar_col4:
            view_mode = st.selectbox("View", ["Table View", "Card View"], key="crm_view_mode", label_visibility="collapsed")

        with toolbar_col5:
            if st.button("🔄", key="refresh_contacts", help="Refresh", use_container_width=True):
                st.rerun()

        # Apply filters
        filtered_leads = all_leads.copy()

        if search_term:
            search_lower = search_term.lower()
            filtered_leads = [l for l in filtered_leads if
                            search_lower in str(l.get('title', '')).lower() or
                            search_lower in str(l.get('email', '')).lower() or
                            search_lower in str(l.get('company', '')).lower() or
                            search_lower in str(l.get('phone', '')).lower() or
                            search_lower in str(l.get('author', '')).lower()]

        if filter_stage != "All Stages":
            filtered_leads = [l for l in filtered_leads if l.get('status', 'new') == filter_stage]

        # Sort
        if sort_by == "score_high":
            filtered_leads.sort(key=lambda x: x.get('pain_score', 0), reverse=True)
        elif sort_by == "score_low":
            filtered_leads.sort(key=lambda x: x.get('pain_score', 0))
        elif sort_by == "name_az":
            filtered_leads.sort(key=lambda x: str(x.get('title', '')).lower())
        elif sort_by == "company":
            filtered_leads.sort(key=lambda x: str(x.get('company', '')).lower())
        elif sort_by == "recent":
            filtered_leads.sort(key=lambda x: x.get('saved_at', ''), reverse=True)

        # Results count and bulk actions
        result_col1, result_col2 = st.columns([3, 1])
        with result_col1:
            st.caption(f"📊 **{len(filtered_leads)}** contacts found")
        with result_col2:
            if filtered_leads:
                csv_data = csv_exporter.export_leads_from_dict(filtered_leads)
                st.download_button("📥 Export", csv_data, f"contacts_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)

        st.markdown("---")

        if view_mode == "Table View":
            # Professional Data Table View
            if filtered_leads:
                # Create DataFrame for display
                table_data = []
                for lead in filtered_leads:
                    stage = lead.get('status', 'new') or 'new'
                    stage_info = CRM_STAGES.get(stage, CRM_STAGES['new'])
                    # Safe string handling - convert None to empty string
                    name = (lead.get('title') or lead.get('author') or lead.get('company') or 'Unknown')[:40]
                    email = lead.get('email') or ''
                    phone = lead.get('phone') or ''
                    company = (lead.get('company') or '')[:30]
                    position = (lead.get('position') or '')[:25]
                    location = lead.get('location') or ''
                    source = (lead.get('source') or '')[:15]
                    score = lead.get('pain_score') or 0

                    table_data.append({
                        'Status': f"{stage_info['icon']} {stage_info['name']}",
                        'Name': name,
                        'Email': email,
                        'Phone': phone,
                        'Company': company,
                        'Position': position,
                        'Location': location,
                        'Score': score,
                        'Source': source,
                        '_hash': lead.get('hash', '')
                    })

                df = pd.DataFrame(table_data)

                # Display table with selection
                st.dataframe(
                    df.drop(columns=['_hash']),
                    use_container_width=True,
                    height=400,
                    column_config={
                        "Status": st.column_config.TextColumn("Status", width="small"),
                        "Name": st.column_config.TextColumn("Name", width="medium"),
                        "Email": st.column_config.TextColumn("Email", width="medium"),
                        "Phone": st.column_config.TextColumn("Phone", width="small"),
                        "Company": st.column_config.TextColumn("Company", width="medium"),
                        "Position": st.column_config.TextColumn("Position", width="small"),
                        "Location": st.column_config.TextColumn("Location", width="small"),
                        "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
                        "Source": st.column_config.TextColumn("Source", width="small"),
                    }
                )

                # Contact detail section below table
                st.markdown("### Contact Details")
                st.caption("Select a contact below to view and edit details")

                # Contact selector
                contact_options = {lead.get('hash', ''): f"{lead.get('title', 'Unknown')} - {lead.get('email', 'No email')}" for lead in filtered_leads[:50]}

                if contact_options:
                    selected_hash = st.selectbox(
                        "Select Contact",
                        list(contact_options.keys()),
                        format_func=lambda x: contact_options.get(x, "Unknown"),
                        key="selected_contact"
                    )

                    # Find the selected lead
                    selected_lead = next((l for l in filtered_leads if l.get('hash') == selected_hash), None)

                    if selected_lead:
                        # Contact detail card
                        detail_col1, detail_col2, detail_col3 = st.columns([2, 2, 1])

                        with detail_col1:
                            st.markdown("**Contact Information**")
                            st.text_input("👤 Name", value=selected_lead.get('title') or selected_lead.get('author') or '', key="edit_name", disabled=True)
                            st.text_input("📧 Email", value=selected_lead.get('email') or '', key="edit_email", disabled=True)
                            st.text_input("📱 Phone", value=selected_lead.get('phone') or '', key="edit_phone", disabled=True)
                            st.text_input("🔗 LinkedIn", value=selected_lead.get('linkedin') or selected_lead.get('url') or '', key="edit_linkedin", disabled=True)

                        with detail_col2:
                            st.markdown("**Business Information**")
                            st.text_input("🏢 Company", value=selected_lead.get('company') or '', key="edit_company", disabled=True)
                            st.text_input("💼 Position", value=selected_lead.get('position') or '', key="edit_position", disabled=True)
                            st.text_input("🏭 Industry", value=selected_lead.get('industry') or '', key="edit_industry", disabled=True)
                            st.text_input("📍 Location", value=selected_lead.get('location') or '', key="edit_location", disabled=True)

                        with detail_col3:
                            st.markdown("**Status & Actions**")

                            current_status = selected_lead.get('status') or 'new'
                            new_status = st.selectbox(
                                "Pipeline Stage",
                                list(CRM_STAGES.keys()),
                                index=list(CRM_STAGES.keys()).index(current_status) if current_status in CRM_STAGES else 0,
                                format_func=lambda x: f"{CRM_STAGES[x]['icon']} {CRM_STAGES[x]['name']}",
                                key="detail_status"
                            )

                            if st.button("✓ Update Status", type="primary", use_container_width=True):
                                if lead_manager.update_lead_status(selected_hash, new_status):
                                    st.success("Status updated!")
                                    st.rerun()

                            st.markdown("---")

                            if st.button("🗑️ Delete Contact", use_container_width=True):
                                if lead_manager.delete_lead(selected_hash):
                                    st.success("Contact deleted!")
                                    st.rerun()

                        # Notes section
                        st.markdown("---")
                        notes_col1, notes_col2 = st.columns([2, 1])

                        with notes_col1:
                            st.markdown("**Notes**")
                            current_notes = selected_lead.get('notes') or ''
                            if current_notes:
                                st.info(current_notes)
                            new_note = st.text_area("Add a new note...", key="new_note_detail", height=100)
                            if st.button("💾 Save Note", key="save_note_detail"):
                                if new_note:
                                    if lead_manager.add_note_to_lead(selected_hash, new_note):
                                        st.success("Note saved!")
                                        st.rerun()

                        with notes_col2:
                            st.markdown("**Activity History**")
                            activity_log = selected_lead.get('activity_log', [])
                            if activity_log:
                                for activity in activity_log[-5:][::-1]:
                                    if activity.get('type') == 'status_change':
                                        st.caption(f"📌 {activity.get('from')} → {activity.get('to')}")
                                    elif activity.get('type') == 'note':
                                        st.caption(f"📝 Note added")
                            else:
                                st.caption("No activity yet")

            else:
                st.info("No contacts match your filters")

        else:
            # Card View (original expandable view but improved)
            if filtered_leads:
                # Display in a grid of cards
                card_cols = st.columns(2)

                for idx, lead in enumerate(filtered_leads[:20]):
                    with card_cols[idx % 2]:
                        # Safe string handling for all fields
                        lead_hash = lead.get('hash') or ''
                        lead_title = (lead.get('title') or lead.get('author') or lead.get('company') or 'Unknown')[:35]
                        lead_email = lead.get('email') or 'No email'
                        lead_phone = lead.get('phone') or ''
                        lead_company = (lead.get('company') or '')[:25]
                        lead_status = lead.get('status') or 'new'
                        pain_score = lead.get('pain_score') or 0

                        stage_info = CRM_STAGES.get(lead_status, CRM_STAGES['new'])

                        with st.container(border=True):
                            # Card header
                            header_col1, header_col2 = st.columns([3, 1])
                            with header_col1:
                                st.markdown(f"**{lead_title}**")
                                st.caption(lead_company if lead_company else "No company")
                            with header_col2:
                                st.markdown(f"""
                                <div style="background: {stage_info['bg']}; border-radius: 6px; padding: 4px 8px; text-align: center;">
                                    <span style="font-size: 12px; color: {stage_info['color']}; font-weight: 600;">{stage_info['name']}</span>
                                </div>
                                """, unsafe_allow_html=True)

                            # Contact info
                            st.caption(f"📧 {lead_email}")
                            if lead_phone:
                                st.caption(f"📱 {lead_phone}")

                            # Actions
                            btn_col1, btn_col2, btn_col3 = st.columns(3)
                            with btn_col1:
                                if st.button("👁️ View", key=f"view_card_{lead_hash}", use_container_width=True):
                                    st.session_state.selected_contact = lead_hash
                            with btn_col2:
                                stages_list = list(CRM_STAGES.keys())
                                current_idx = stages_list.index(lead_status) if lead_status in stages_list else 0
                                if current_idx < len(stages_list) - 1 and lead_status not in ['won', 'lost']:
                                    if st.button("➡️ Next", key=f"next_card_{lead_hash}", use_container_width=True):
                                        lead_manager.update_lead_status(lead_hash, stages_list[current_idx + 1])
                                        st.rerun()
                            with btn_col3:
                                if st.button("🗑️", key=f"del_card_{lead_hash}", use_container_width=True):
                                    lead_manager.delete_lead(lead_hash)
                                    st.rerun()

                if len(filtered_leads) > 20:
                    st.info(f"Showing 20 of {len(filtered_leads)} contacts. Use filters to narrow results.")
            else:
                st.info("No contacts match your filters")

    # ==================== TAB 3: DEALS/OPPORTUNITIES ====================
    with tab3:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
            <h3 style="margin: 0; color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 20px; text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);">💰 DEALS & OPPORTUNITIES</h3>
            <div class="metric-tooltip-wrapper" style="position: relative; display: inline-block;">
                <span style="cursor: help; background: linear-gradient(135deg, rgba(0, 255, 255, 0.3) 0%, rgba(0, 139, 139, 0.5) 100%); color: #00FFFF; border-radius: 50%; width: 20px; height: 20px; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; border: 1px solid rgba(0, 255, 255, 0.4);">?</span>
                <div class="metric-tooltip" style="position: absolute; bottom: 130%; left: 50%; transform: translateX(-50%); background: linear-gradient(135deg, rgba(28, 28, 46, 0.95) 0%, rgba(45, 55, 72, 0.95) 100%); color: #E5E5E5; padding: 12px 16px; border-radius: 8px; font-size: 12px; width: 280px; z-index: 1000; opacity: 0; visibility: hidden; transition: all 0.2s ease; box-shadow: 0 0 20px rgba(0, 255, 255, 0.2); border: 1px solid rgba(0, 255, 255, 0.3);">
                    <strong style="color: #00FF88;">What are Deals?</strong><br><br>
                    Deals track potential revenue from your leads. Use them to:<br><br>
                    • <strong style="color: #00FFFF;">Track Value:</strong> Set the $ amount each opportunity is worth<br>
                    • <strong style="color: #00FFFF;">Monitor Progress:</strong> Move deals through stages<br>
                    • <strong style="color: #00FFFF;">Forecast Revenue:</strong> See your total pipeline value<br>
                    • <strong style="color: #00FFFF;">Set Close Dates:</strong> Track when deals should close<br><br>
                    <em style="color: #708090;">Create deals for leads showing buying intent!</em>
                    <div style="position: absolute; bottom: -8px; left: 50%; transform: translateX(-50%); width: 0; height: 0; border-left: 8px solid transparent; border-right: 8px solid transparent; border-top: 8px solid rgba(28, 28, 46, 0.95);"></div>
                </div>
            </div>
        </div>
        <p style="color: #708090; font-size: 13px; margin: -12px 0 16px 0;">Track revenue opportunities and deal progress</p>
        <style>
            .metric-tooltip-wrapper:hover .metric-tooltip {
                opacity: 1 !important;
                visibility: visible !important;
            }
        </style>
        """, unsafe_allow_html=True)

        # Deal stats cards
        deal_col1, deal_col2, deal_col3, deal_col4 = st.columns(4)

        with deal_col1:
            st.markdown(f"""
            <div class="revenue-card">
                <div class="revenue-label">Pipeline Value</div>
                <div class="revenue-value">${pipeline_value:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)

        with deal_col2:
            st.markdown(f"""
            <div class="crm-kpi-card" style="background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: white;">
                <div class="crm-kpi-icon">💰</div>
                <div class="crm-kpi-value" style="color: white;">${won_deal_value:,.0f}</div>
                <div class="crm-kpi-label" style="color: rgba(255,255,255,0.9);">Won Revenue</div>
            </div>
            """, unsafe_allow_html=True)

        with deal_col3:
            deal_count = len(st.session_state.crm_deals)
            st.markdown(f"""
            <div class="crm-kpi-card">
                <div class="crm-kpi-icon">📋</div>
                <div class="crm-kpi-value" style="color: #3B82F6;">{deal_count}</div>
                <div class="crm-kpi-label">Total Deals</div>
            </div>
            """, unsafe_allow_html=True)

        with deal_col4:
            avg_deal = pipeline_value / deal_count if deal_count > 0 else 0
            st.markdown(f"""
            <div class="crm-kpi-card">
                <div class="crm-kpi-icon">📊</div>
                <div class="crm-kpi-value" style="color: #8B5CF6;">${avg_deal:,.0f}</div>
                <div class="crm-kpi-label">Avg Deal Size</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        # Create new deal section
        st.markdown("#### Create New Deal")
        with st.expander("➕ Add New Deal", expanded=False):
            deal_form_col1, deal_form_col2 = st.columns(2)

            with deal_form_col1:
                deal_name = st.text_input("Deal Name", placeholder="e.g., AI Receptionist for ABC Dental")
                deal_value = st.number_input("Deal Value ($)", min_value=0, value=1500, step=100)
                deal_contact = st.selectbox(
                    "Associated Contact",
                    ["Select a contact..."] + [f"{l.get('title', 'Unknown')} - {l.get('email', 'No email')}" for l in all_leads[:50]],
                    key="deal_contact"
                )

            with deal_form_col2:
                deal_stage = st.selectbox(
                    "Stage",
                    ['new', 'contacted', 'demo', 'proposal', 'won', 'lost'],
                    format_func=lambda x: CRM_STAGES[x]['name'],
                    key="deal_stage_new"
                )
                deal_close_date = st.date_input("Expected Close Date", value=datetime.now())
                deal_probability = st.slider("Win Probability (%)", 0, 100, 50)

            if st.button("💾 Create Deal", type="primary", use_container_width=True):
                if deal_name:
                    import uuid
                    new_deal = {
                        'id': str(uuid.uuid4())[:8],
                        'name': deal_name,
                        'value': deal_value,
                        'stage': deal_stage,
                        'contact': deal_contact if deal_contact != "Select a contact..." else None,
                        'close_date': deal_close_date.isoformat(),
                        'probability': deal_probability,
                        'created_at': datetime.now().isoformat()
                    }
                    st.session_state.crm_deals.append(new_deal)
                    st.success(f"Deal '{deal_name}' created!")
                    st.rerun()
                else:
                    st.warning("Please enter a deal name")

        # Deal list
        st.markdown("#### Active Deals")

        if st.session_state.crm_deals:
            for deal in st.session_state.crm_deals:
                deal_stage = deal.get('stage') or 'new'
                stage_info = CRM_STAGES.get(deal_stage, CRM_STAGES['new'])
                deal_name = deal.get('name') or 'Unnamed Deal'
                deal_contact = deal.get('contact') or 'None'
                deal_close = (deal.get('close_date') or 'Not set')[:10]
                deal_value = deal.get('value') or 0
                deal_prob = deal.get('probability') or 50
                deal_id = deal.get('id') or 'unknown'

                with st.container(border=True):
                    d_col1, d_col2, d_col3, d_col4 = st.columns([3, 2, 2, 1])

                    with d_col1:
                        st.markdown(f"**{deal_name}**")
                        st.caption(f"Contact: {deal_contact[:30] if deal_contact != 'None' else 'None'}")

                    with d_col2:
                        st.markdown(f"""
                        <div style="background: {stage_info['bg']}; padding: 4px 12px; border-radius: 20px; display: inline-block;">
                            <span style="color: {stage_info['color']}; font-weight: 600; font-size: 12px;">{stage_info['icon']} {stage_info['name']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        st.caption(f"Close: {deal_close}")

                    with d_col3:
                        st.markdown(f"<div class='deal-value'>${deal_value:,.0f}</div>", unsafe_allow_html=True)
                        st.caption(f"Probability: {deal_prob}%")

                    with d_col4:
                        new_stage = st.selectbox(
                            "Move",
                            list(CRM_STAGES.keys()),
                            index=list(CRM_STAGES.keys()).index(deal_stage) if deal_stage in CRM_STAGES else 0,
                            key=f"deal_stage_{deal_id}",
                            label_visibility="collapsed"
                        )
                        if new_stage != deal_stage:
                            deal['stage'] = new_stage
                            st.rerun()
        else:
            st.info("No deals yet. Create your first deal above!")

    # ==================== TAB 4: TASKS ====================
    with tab4:
        # Holographic Task Management Header
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(255, 215, 0, 0.1) 0%, rgba(28, 28, 46, 0.8) 100%); border-radius: 16px; padding: 24px; margin-bottom: 24px; border: 1px solid rgba(255, 215, 0, 0.3); backdrop-filter: blur(10px); box-shadow: 0 0 30px rgba(255, 215, 0, 0.1);">
            <div style="display: flex; align-items: flex-start; gap: 16px;">
                <div style="background: linear-gradient(135deg, rgba(255, 215, 0, 0.3) 0%, rgba(255, 215, 0, 0.1) 100%); border-radius: 12px; padding: 12px; display: flex; align-items: center; justify-content: center; border: 1px solid rgba(255, 215, 0, 0.4);">
                    <span style="font-size: 28px; filter: drop-shadow(0 0 8px rgba(255, 215, 0, 0.5));">📋</span>
                </div>
                <div style="flex: 1;">
                    <h3 style="margin: 0 0 8px 0; color: #FFD700; font-size: 20px; font-weight: 700; font-family: 'Orbitron', sans-serif; text-shadow: 0 0 10px rgba(255, 215, 0, 0.3);">TASK MANAGEMENT</h3>
                    <p style="margin: 0; color: #C0C0C0; font-size: 14px; line-height: 1.5;">
                        Organize your daily follow-up activities and never miss an opportunity. Create tasks for calls, emails, meetings, and notes to stay on top of your sales pipeline.
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Task quick stats with explanations
        today = datetime.now().date()
        overdue_tasks = [t for t in st.session_state.crm_tasks if not t.get('completed') and t.get('due_date') and datetime.fromisoformat(t.get('due_date')).date() < today]
        today_tasks = [t for t in st.session_state.crm_tasks if not t.get('completed') and t.get('due_date') and datetime.fromisoformat(t.get('due_date')).date() == today]
        upcoming_tasks = [t for t in st.session_state.crm_tasks if not t.get('completed') and t.get('due_date') and datetime.fromisoformat(t.get('due_date')).date() > today]
        completed_tasks = [t for t in st.session_state.crm_tasks if t.get('completed')]

        # Stats cards with holographic design
        st.markdown(f"""
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
            <div style="background: linear-gradient(135deg, rgba(255, 68, 68, 0.15) 0%, rgba(28, 28, 46, 0.8) 100%); border-radius: 12px; padding: 16px; text-align: center; border: 1px solid rgba(255, 68, 68, 0.4); backdrop-filter: blur(5px);">
                <div style="font-size: 32px; font-weight: 800; color: #FF4444; font-family: 'Orbitron', sans-serif; text-shadow: 0 0 15px rgba(255, 68, 68, 0.5);">{len(overdue_tasks)}</div>
                <div style="font-size: 12px; font-weight: 600; color: #FF6666; text-transform: uppercase; letter-spacing: 0.05em;">Overdue</div>
                <div style="font-size: 10px; color: #708090; margin-top: 4px;">Need attention now</div>
            </div>
            <div style="background: linear-gradient(135deg, rgba(255, 215, 0, 0.15) 0%, rgba(28, 28, 46, 0.8) 100%); border-radius: 12px; padding: 16px; text-align: center; border: 1px solid rgba(255, 215, 0, 0.4); backdrop-filter: blur(5px);">
                <div style="font-size: 32px; font-weight: 800; color: #FFD700; font-family: 'Orbitron', sans-serif; text-shadow: 0 0 15px rgba(255, 215, 0, 0.5);">{len(today_tasks)}</div>
                <div style="font-size: 12px; font-weight: 600; color: #FFD700; text-transform: uppercase; letter-spacing: 0.05em;">Due Today</div>
                <div style="font-size: 10px; color: #708090; margin-top: 4px;">Complete before EOD</div>
            </div>
            <div style="background: linear-gradient(135deg, rgba(0, 255, 255, 0.15) 0%, rgba(28, 28, 46, 0.8) 100%); border-radius: 12px; padding: 16px; text-align: center; border: 1px solid rgba(0, 255, 255, 0.4); backdrop-filter: blur(5px);">
                <div style="font-size: 32px; font-weight: 800; color: #00FFFF; font-family: 'Orbitron', sans-serif; text-shadow: 0 0 15px rgba(0, 255, 255, 0.5);">{len(upcoming_tasks)}</div>
                <div style="font-size: 12px; font-weight: 600; color: #00FFFF; text-transform: uppercase; letter-spacing: 0.05em;">Upcoming</div>
                <div style="font-size: 10px; color: #708090; margin-top: 4px;">Scheduled for later</div>
            </div>
            <div style="background: linear-gradient(135deg, rgba(0, 255, 136, 0.15) 0%, rgba(28, 28, 46, 0.8) 100%); border-radius: 12px; padding: 16px; text-align: center; border: 1px solid rgba(0, 255, 136, 0.4); backdrop-filter: blur(5px);">
                <div style="font-size: 32px; font-weight: 800; color: #00FF88; font-family: 'Orbitron', sans-serif; text-shadow: 0 0 15px rgba(0, 255, 136, 0.5);">{len(completed_tasks)}</div>
                <div style="font-size: 12px; font-weight: 600; color: #00FF88; text-transform: uppercase; letter-spacing: 0.05em;">Completed</div>
                <div style="font-size: 10px; color: #708090; margin-top: 4px;">Successfully done</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Create new task - Holographic Design
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%); border-radius: 16px; padding: 20px; margin-bottom: 24px; border: 1px solid rgba(0, 255, 255, 0.2); backdrop-filter: blur(10px);">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                <div style="background: rgba(0, 139, 139, 0.3); border: 1px solid #008B8B; border-radius: 8px; padding: 8px 12px;">
                    <span style="color: #00FFFF; font-size: 16px; filter: drop-shadow(0 0 5px #00FFFF);">+</span>
                </div>
                <div>
                    <h4 style="margin: 0; color: #00FFFF; font-size: 16px; font-weight: 700; font-family: 'Orbitron', sans-serif;">CREATE NEW TASK</h4>
                    <p style="margin: 0; color: #C0C0C0; font-size: 12px;">Schedule a follow-up activity for a lead</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Click here to add a new task", expanded=False):
            # Explanation inside the form - Holographic
            st.markdown("""
            <div style="background: rgba(0, 139, 139, 0.1); border-radius: 8px; padding: 12px; margin-bottom: 16px; border-left: 3px solid #008B8B;">
                <p style="margin: 0; color: #C0C0C0; font-size: 13px;">
                    <strong style="color: #00FFFF;">How to create a task:</strong> Fill in the title, select task type (call, email, meeting, etc.), set a due date, and optionally link it to a contact.
                </p>
            </div>
            """, unsafe_allow_html=True)

            task_col1, task_col2 = st.columns(2)

            with task_col1:
                task_title = st.text_input("Task Title", placeholder="e.g., Follow up with John about demo", help="Short description of what you need to do")
                task_description = st.text_area("Description (optional)", placeholder="Add any notes or context for this task...", height=80, help="Additional details to remember")

            with task_col2:
                task_type = st.selectbox("Task Type", ["📞 Call", "📧 Email", "📅 Meeting", "📝 Note", "✅ Other"], help="What kind of activity is this?")
                task_due = st.date_input("Due Date", value=datetime.now(), key="task_due_date", help="When should this task be completed?")
                task_priority = st.selectbox("Priority", ["🔴 High", "🟡 Medium", "🟢 Low"], help="How urgent is this task?")
                task_contact = st.selectbox(
                    "Link to Contact (optional)",
                    ["None"] + [f"{(l.get('title') or l.get('author') or l.get('company') or 'Unknown')[:25]}" for l in all_leads[:30]],
                    key="task_contact",
                    help="Associate this task with a specific lead"
                )

            if st.button("Create Task", type="primary", use_container_width=True, key="create_task_btn"):
                if task_title:
                    import uuid
                    new_task = {
                        'id': str(uuid.uuid4())[:8],
                        'title': task_title,
                        'description': task_description,
                        'type': task_type,
                        'due_date': task_due.isoformat(),
                        'priority': task_priority,
                        'contact': task_contact if task_contact != "None" else None,
                        'completed': False,
                        'created_at': datetime.now().isoformat()
                    }
                    st.session_state.crm_tasks.append(new_task)
                    st.success(f"Task '{task_title}' created successfully!")
                    st.rerun()
                else:
                    st.warning("Please enter a task title")

        # Task list with holographic header
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%); border-radius: 16px; padding: 20px; margin-bottom: 16px; border: 1px solid rgba(0, 255, 255, 0.2); backdrop-filter: blur(10px);">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                <div>
                    <h4 style="margin: 0; color: #00FFFF; font-size: 16px; font-weight: 700; font-family: 'Orbitron', sans-serif;">YOUR TASK LIST</h4>
                    <p style="margin: 4px 0 0 0; color: #C0C0C0; font-size: 12px;">Check the box to mark a task as complete</p>
                </div>
            </div>
            <div style="background: rgba(0, 139, 139, 0.1); border-radius: 8px; padding: 12px; margin-top: 12px; border: 1px solid rgba(0, 139, 139, 0.2);">
                <p style="margin: 0; color: #C0C0C0; font-size: 12px;">
                    <strong style="color: #00FFFF;">Filter Options:</strong>
                    <span style="color: #FF6B6B;">All</span> = View all tasks |
                    <span style="color: #FF6B6B;">Overdue</span> = Past due date |
                    <span style="color: #FFB800;">Today</span> = Due today |
                    <span style="color: #00FFFF;">Upcoming</span> = Future tasks |
                    <span style="color: #00FF88;">Completed</span> = Done tasks
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        task_filter = st.radio("Filter tasks by status:", ["All", "Overdue", "Today", "Upcoming", "Completed"], horizontal=True, key="task_filter", help="Select a filter to view specific tasks")

        if task_filter == "Overdue":
            display_tasks = overdue_tasks
        elif task_filter == "Today":
            display_tasks = today_tasks
        elif task_filter == "Upcoming":
            display_tasks = upcoming_tasks
        elif task_filter == "Completed":
            display_tasks = completed_tasks
        else:
            display_tasks = st.session_state.crm_tasks

        if display_tasks:
            for task in display_tasks:
                task_status = "completed" if task.get('completed') else ""
                if not task.get('completed') and task.get('due_date'):
                    task_date = datetime.fromisoformat(task.get('due_date')).date()
                    if task_date < today:
                        task_status = "overdue"
                    elif task_date == today:
                        task_status = "today"
                    else:
                        task_status = "upcoming"

                # Status colors and backgrounds
                status_styles = {
                    "overdue": {"bg": "#FEE2E2", "border": "#FCA5A5", "color": "#DC2626"},
                    "today": {"bg": "#FEF3C7", "border": "#FCD34D", "color": "#D97706"},
                    "upcoming": {"bg": "#DBEAFE", "border": "#93C5FD", "color": "#2563EB"},
                    "completed": {"bg": "#F1F5F9", "border": "#CBD5E1", "color": "#64748B"}
                }
                style = status_styles.get(task_status, {"bg": "#FFFFFF", "border": "#E2E8F0", "color": "#475569"})

                # Modern task card
                st.markdown(f"""
                <div style="background: {style['bg']}; border: 1px solid {style['border']}; border-radius: 12px; padding: 16px; margin-bottom: 12px;">
                    <div style="display: flex; align-items: center; gap: 16px;">
                        <div style="flex: 1;">
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                                <span style="font-size: 16px;">{task.get('type', '📝').split()[0]}</span>
                                <span style="font-weight: 600; color: #1E293B; {'text-decoration: line-through; color: #94A3B8;' if task.get('completed') else ''}">{task.get('title', 'Untitled')}</span>
                                <span style="background: {style['color']}20; color: {style['color']}; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 600; text-transform: uppercase;">{task_status or 'pending'}</span>
                            </div>
                            <div style="display: flex; align-items: center; gap: 16px; font-size: 12px; color: #64748B;">
                                <span>📅 {task.get('due_date', 'No date')[:10]}</span>
                                <span>{task.get('priority', '🟡 Medium')}</span>
                                {f"<span>👤 {task.get('contact')}</span>" if task.get('contact') else ""}
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Actions row
                act_col1, act_col2, act_col3 = st.columns([2, 1, 1])
                with act_col1:
                    is_done = st.checkbox(
                        "Mark as complete" if not task.get('completed') else "Completed",
                        value=task.get('completed', False),
                        key=f"task_done_{task.get('id')}"
                    )
                    if is_done != task.get('completed', False):
                        task['completed'] = is_done
                        st.rerun()
                with act_col3:
                    if st.button("Delete", key=f"del_task_{task.get('id')}", type="secondary"):
                        st.session_state.crm_tasks.remove(task)
                        st.rerun()
        else:
            st.markdown("""
            <div style="background: #F8FAFC; border-radius: 12px; padding: 32px; text-align: center; border: 2px dashed #CBD5E1;">
                <span style="font-size: 48px;">📋</span>
                <h4 style="margin: 16px 0 8px 0; color: #475569;">No tasks found</h4>
                <p style="margin: 0; color: #64748B; font-size: 14px;">No tasks match the selected filter. Create a new task above to get started!</p>
            </div>
            """, unsafe_allow_html=True)

    # ==================== TAB 5: EMAIL TEMPLATES ====================
    with tab5:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
            <h3 style="margin: 0; color: #1E293B;">Email Templates & Composer</h3>
            <div class="metric-tooltip-wrapper" style="position: relative; display: inline-block;">
                <span style="cursor: help; background: #EC4899; color: white; border-radius: 50%; width: 20px; height: 20px; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600;">?</span>
                <div class="metric-tooltip" style="position: absolute; bottom: 130%; left: 50%; transform: translateX(-50%); background: #1E293B; color: white; padding: 12px 16px; border-radius: 8px; font-size: 12px; width: 300px; z-index: 1000; opacity: 0; visibility: hidden; transition: all 0.2s ease; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                    <strong style="color: #EC4899;">Email Templates</strong><br><br>
                    Pre-written email templates for faster outreach:<br><br>
                    • <strong>Initial Outreach:</strong> First contact with new leads<br>
                    • <strong>Follow Up:</strong> Second touch after no response<br>
                    • <strong>Demo Confirmation:</strong> Confirm scheduled demos<br>
                    • <strong>Proposal Follow-up:</strong> After sending pricing<br>
                    • <strong>Win-Back:</strong> Re-engage cold leads<br><br>
                    <em style="color: #94A3B8;">Use placeholders like {{name}}, {{company}}</em>
                    <div style="position: absolute; bottom: -8px; left: 50%; transform: translateX(-50%); width: 0; height: 0; border-left: 8px solid transparent; border-right: 8px solid transparent; border-top: 8px solid #1E293B;"></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        email_subtab1, email_subtab2 = st.tabs(["📝 Compose Email", "📋 Templates"])

        with email_subtab1:
            st.markdown("#### Compose Email")

            # Select recipient
            recipient_options = ["Select recipient..."] + [f"{l.get('email', 'No email')} - {l.get('title', 'Unknown')[:30]}" for l in all_leads if l.get('email')]
            selected_recipient = st.selectbox("To:", recipient_options, key="email_recipient")

            # Template selection
            template_names = ["No template"] + [t.get('name') for t in st.session_state.email_templates]
            selected_template = st.selectbox("Use Template:", template_names, key="email_template_select")

            # Get template content if selected
            template_subject = ""
            template_body = ""
            if selected_template != "No template":
                for t in st.session_state.email_templates:
                    if t.get('name') == selected_template:
                        template_subject = t.get('subject', '')
                        template_body = t.get('body', '')
                        break

            email_subject = st.text_input("Subject:", value=template_subject, key="email_subject")
            email_body = st.text_area("Message:", value=template_body, height=250, key="email_body")

            st.caption("💡 Use {{name}}, {{company}}, {{industry}}, {{date}} as placeholders")

            col_send1, col_send2 = st.columns(2)
            with col_send1:
                if st.button("📧 Send Email", type="primary", use_container_width=True):
                    if selected_recipient != "Select recipient..." and email_subject and email_body:
                        st.success("Email sent successfully! (Simulated)")
                        # In production, integrate with email service
                    else:
                        st.warning("Please fill in all fields")
            with col_send2:
                if st.button("💾 Save as Draft", use_container_width=True):
                    st.info("Draft saved!")

        with email_subtab2:
            st.markdown("#### Email Templates")

            # Display existing templates
            for template in st.session_state.email_templates:
                with st.expander(f"📧 {template.get('name')}", expanded=False):
                    st.text_input("Subject:", value=template.get('subject', ''), key=f"tmpl_subj_{template.get('id')}", disabled=True)
                    st.text_area("Body:", value=template.get('body', ''), key=f"tmpl_body_{template.get('id')}", disabled=True, height=150)

            # Create new template
            st.markdown("---")
            st.markdown("#### Create New Template")
            with st.expander("➕ Add Template", expanded=False):
                new_tmpl_name = st.text_input("Template Name", key="new_tmpl_name")
                new_tmpl_subject = st.text_input("Subject Line", key="new_tmpl_subject")
                new_tmpl_body = st.text_area("Email Body", height=200, key="new_tmpl_body")

                if st.button("💾 Save Template", type="primary"):
                    if new_tmpl_name and new_tmpl_subject and new_tmpl_body:
                        import uuid
                        new_template = {
                            'id': str(uuid.uuid4())[:8],
                            'name': new_tmpl_name,
                            'subject': new_tmpl_subject,
                            'body': new_tmpl_body
                        }
                        st.session_state.email_templates.append(new_template)
                        st.success("Template saved!")
                        st.rerun()

    # ==================== TAB 6: CALENDAR ====================
    with tab6:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
            <h3 style="margin: 0; color: #1E293B;">Calendar View</h3>
            <div class="metric-tooltip-wrapper" style="position: relative; display: inline-block;">
                <span style="cursor: help; background: #8B5CF6; color: white; border-radius: 50%; width: 20px; height: 20px; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600;">?</span>
                <div class="metric-tooltip" style="position: absolute; bottom: 130%; left: 50%; transform: translateX(-50%); background: #1E293B; color: white; padding: 12px 16px; border-radius: 8px; font-size: 12px; width: 300px; z-index: 1000; opacity: 0; visibility: hidden; transition: all 0.2s ease; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                    <strong style="color: #8B5CF6;">Calendar Overview</strong><br><br>
                    This calendar shows all your scheduled activities:<br><br>
                    • <strong>📞 Tasks:</strong> Calls, emails, and meetings appear on their due dates<br>
                    • <strong>💰 Deals:</strong> Deal close dates are highlighted<br>
                    • <strong>📋 Overview:</strong> See your busiest days at a glance<br><br>
                    <em style="color: #94A3B8;">Pro tip: Create tasks in the Tasks tab and they'll appear here automatically!</em>
                    <div style="position: absolute; bottom: -8px; left: 50%; transform: translateX(-50%); width: 0; height: 0; border-left: 8px solid transparent; border-right: 8px solid transparent; border-top: 8px solid #1E293B;"></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Calendar controls
        cal_col1, cal_col2, cal_col3 = st.columns([1, 2, 1])
        with cal_col2:
            import calendar
            current_date = datetime.now()
            selected_month = st.selectbox(
                "Month",
                list(range(1, 13)),
                index=current_date.month - 1,
                format_func=lambda x: calendar.month_name[x],
                key="cal_month",
                label_visibility="collapsed"
            )
            selected_year = current_date.year

        # Generate calendar
        cal = calendar.Calendar(firstweekday=6)  # Sunday first
        month_days = cal.monthdayscalendar(selected_year, selected_month)

        # Day headers
        day_headers = st.columns(7)
        for i, day_name in enumerate(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
            with day_headers[i]:
                st.markdown(f"<div style='text-align: center; font-weight: 600; color: #64748B; padding: 8px;'>{day_name}</div>", unsafe_allow_html=True)

        # Calendar grid
        for week in month_days:
            week_cols = st.columns(7)
            for i, day in enumerate(week):
                with week_cols[i]:
                    if day == 0:
                        st.markdown("<div style='min-height: 80px;'></div>", unsafe_allow_html=True)
                    else:
                        day_date = f"{selected_year}-{selected_month:02d}-{day:02d}"
                        is_today = (day == current_date.day and selected_month == current_date.month and selected_year == current_date.year)

                        # Get tasks for this day
                        day_tasks = [t for t in st.session_state.crm_tasks if t.get('due_date', '')[:10] == day_date]

                        # Get deals closing this day
                        day_deals = [d for d in st.session_state.crm_deals if d.get('close_date', '')[:10] == day_date]

                        today_class = "today" if is_today else ""
                        events_html = ""

                        for task in day_tasks[:2]:
                            task_type = task.get('type', '📝').split()[0]
                            events_html += f"<div class='calendar-event' style='background: #3B82F6;'>{task_type} {task.get('title', '')[:15]}</div>"

                        for deal in day_deals[:1]:
                            events_html += f"<div class='calendar-event' style='background: #10B981;'>💰 {deal.get('name', '')[:15]}</div>"

                        if len(day_tasks) > 2:
                            events_html += f"<div style='font-size: 10px; color: #64748B;'>+{len(day_tasks) - 2} more</div>"

                        st.markdown(f"""
                        <div class="calendar-day {today_class}">
                            <div class="calendar-day-number">{day}</div>
                            {events_html}
                        </div>
                        """, unsafe_allow_html=True)

        # Upcoming events summary
        st.markdown("---")
        st.markdown("#### Upcoming Events")

        upcoming_events = []
        for task in st.session_state.crm_tasks:
            if not task.get('completed') and task.get('due_date'):
                upcoming_events.append({
                    'type': 'task',
                    'date': task.get('due_date'),
                    'title': task.get('title'),
                    'icon': task.get('type', '📝').split()[0]
                })
        for deal in st.session_state.crm_deals:
            if deal.get('close_date') and deal.get('stage') not in ['won', 'lost']:
                upcoming_events.append({
                    'type': 'deal',
                    'date': deal.get('close_date'),
                    'title': deal.get('name'),
                    'icon': '💰'
                })

        upcoming_events.sort(key=lambda x: x.get('date', ''))

        if upcoming_events[:10]:
            for event in upcoming_events[:10]:
                event_col1, event_col2 = st.columns([1, 4])
                with event_col1:
                    st.caption(event.get('date', '')[:10])
                with event_col2:
                    st.markdown(f"{event.get('icon')} {event.get('title')}")
        else:
            st.info("No upcoming events")

    # ==================== TAB 7: ANALYTICS ====================
    with tab7:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
            <h3 style="margin: 0; color: #1E293B;">Pipeline Analytics</h3>
            <div class="metric-tooltip-wrapper" style="position: relative; display: inline-block;">
                <span style="cursor: help; background: #06B6D4; color: white; border-radius: 50%; width: 20px; height: 20px; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600;">?</span>
                <div class="metric-tooltip" style="position: absolute; bottom: 130%; left: 50%; transform: translateX(-50%); background: #1E293B; color: white; padding: 12px 16px; border-radius: 8px; font-size: 12px; width: 280px; z-index: 1000; opacity: 0; visibility: hidden; transition: all 0.2s ease; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                    <strong style="color: #06B6D4;">Analytics Dashboard</strong><br><br>
                    Track your sales performance:<br><br>
                    • <strong>Funnel:</strong> See how leads progress through stages<br>
                    • <strong>Conversion:</strong> Your win rate percentage<br>
                    • <strong>Sources:</strong> Which channels bring the best leads<br>
                    • <strong>Activity:</strong> Recent actions and updates<br><br>
                    <em style="color: #94A3B8;">Use this to optimize your sales process!</em>
                    <div style="position: absolute; bottom: -8px; left: 50%; transform: translateX(-50%); width: 0; height: 0; border-left: 8px solid transparent; border-right: 8px solid transparent; border-top: 8px solid #1E293B;"></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        analytics_subtab1, analytics_subtab2, analytics_subtab3 = st.tabs(["📊 Dashboard", "📝 Activity Feed", "⚡ Quick Actions"])

        with analytics_subtab1:
            # Performance metrics cards at top
            st.markdown("""
            <div style="margin-bottom: 24px;">
                <h4 style="color: #1E293B; margin-bottom: 16px; font-size: 18px;">Key Performance Indicators</h4>
            </div>
            """, unsafe_allow_html=True)

            perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)

            conversion = (won_count / total_leads * 100) if total_leads > 0 else 0
            in_progress = status_counts.get('contacted', 0) + status_counts.get('demo', 0) + status_counts.get('proposal', 0)
            new_leads = status_counts.get('new', 0)
            hot_leads = len([l for l in all_leads if l.get('pain_score', 0) >= 70])

            with perf_col1:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #10B981 0%, #059669 100%); border-radius: 16px; padding: 20px; text-align: center; color: white;">
                    <div style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">Conversion Rate</div>
                    <div style="font-size: 32px; font-weight: 700;">{conversion:.1f}%</div>
                    <div style="font-size: 12px; margin-top: 8px; opacity: 0.8;">Won / Total Leads</div>
                </div>
                """, unsafe_allow_html=True)

            with perf_col2:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%); border-radius: 16px; padding: 20px; text-align: center; color: white;">
                    <div style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">In Progress</div>
                    <div style="font-size: 32px; font-weight: 700;">{in_progress}</div>
                    <div style="font-size: 12px; margin-top: 8px; opacity: 0.8;">Active Opportunities</div>
                </div>
                """, unsafe_allow_html=True)

            with perf_col3:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%); border-radius: 16px; padding: 20px; text-align: center; color: white;">
                    <div style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">Uncontacted</div>
                    <div style="font-size: 32px; font-weight: 700;">{new_leads}</div>
                    <div style="font-size: 12px; margin-top: 8px; opacity: 0.8;">Need Follow-up</div>
                </div>
                """, unsafe_allow_html=True)

            with perf_col4:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%); border-radius: 16px; padding: 20px; text-align: center; color: white;">
                    <div style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">Hot Leads</div>
                    <div style="font-size: 32px; font-weight: 700;">{hot_leads}</div>
                    <div style="font-size: 12px; margin-top: 8px; opacity: 0.8;">Score 70+</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

            # Modern Funnel Visualization
            st.markdown("""
            <div style="margin-bottom: 16px;">
                <h4 style="color: #1E293B; margin-bottom: 8px; font-size: 18px;">Sales Funnel</h4>
                <p style="color: #64748B; font-size: 13px; margin: 0;">How leads progress through your pipeline</p>
            </div>
            """, unsafe_allow_html=True)

            # Build funnel HTML
            max_count = max(status_counts.values()) if status_counts.values() else 1
            funnel_html = ""
            colors = ['#3B82F6', '#06B6D4', '#8B5CF6', '#F59E0B', '#10B981', '#EF4444']

            for i, (stage_key, stage_info) in enumerate(CRM_STAGES.items()):
                count = status_counts.get(stage_key, 0)
                width_pct = max(20, (count / max_count * 100)) if max_count > 0 else 20
                color = colors[i % len(colors)]

                funnel_html += f"""
                <div style="display: flex; align-items: center; margin-bottom: 12px;">
                    <div style="width: 120px; font-size: 13px; font-weight: 600; color: #374151;">
                        {stage_info['icon']} {stage_info['name']}
                    </div>
                    <div style="flex: 1; margin: 0 16px;">
                        <div style="background: #E5E7EB; border-radius: 8px; height: 32px; overflow: hidden;">
                            <div style="background: linear-gradient(90deg, {color} 0%, {color}CC 100%); width: {width_pct}%; height: 100%; border-radius: 8px; display: flex; align-items: center; justify-content: flex-end; padding-right: 12px; transition: width 0.3s ease;">
                                <span style="color: white; font-weight: 700; font-size: 14px;">{count}</span>
                            </div>
                        </div>
                    </div>
                    <div style="width: 60px; text-align: right; font-size: 13px; color: #6B7280;">
                        {(count / total_leads * 100):.0f}% of total
                    </div>
                </div>
                """ if total_leads > 0 else f"""
                <div style="display: flex; align-items: center; margin-bottom: 12px;">
                    <div style="width: 120px; font-size: 13px; font-weight: 600; color: #374151;">
                        {stage_info['icon']} {stage_info['name']}
                    </div>
                    <div style="flex: 1; margin: 0 16px;">
                        <div style="background: #E5E7EB; border-radius: 8px; height: 32px; overflow: hidden;">
                            <div style="background: linear-gradient(90deg, {color} 0%, {color}CC 100%); width: 20%; height: 100%; border-radius: 8px; display: flex; align-items: center; justify-content: flex-end; padding-right: 12px;">
                                <span style="color: white; font-weight: 700; font-size: 14px;">{count}</span>
                            </div>
                        </div>
                    </div>
                    <div style="width: 60px; text-align: right; font-size: 13px; color: #6B7280;">
                        0%
                    </div>
                </div>
                """

            st.markdown(f"""
            <div style="background: white; border: 1px solid #E5E7EB; border-radius: 16px; padding: 24px;">
                {funnel_html}
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

            # Source distribution with modern cards
            st.markdown("""
            <div style="margin-bottom: 16px;">
                <h4 style="color: #1E293B; margin-bottom: 8px; font-size: 18px;">Lead Sources</h4>
                <p style="color: #64748B; font-size: 13px; margin: 0;">Where your leads are coming from</p>
            </div>
            """, unsafe_allow_html=True)

            source_counts = {}
            for lead in all_leads:
                source = lead.get('source', 'Unknown')
                source_counts[source] = source_counts.get(source, 0) + 1

            if source_counts:
                source_colors = {'reddit': '#FF4500', 'google': '#4285F4', 'hackernews': '#FF6600', 'apollo': '#5B5FC7', 'hunter': '#F5A623', 'manual': '#6B7280'}
                source_icons = {'reddit': '🔴', 'google': '🔵', 'hackernews': '🟠', 'apollo': '🚀', 'hunter': '🎯', 'manual': '✏️'}

                source_html = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px;">'
                for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
                    color = source_colors.get(source.lower(), '#6B7280')
                    icon = source_icons.get(source.lower(), '📊')
                    pct = (count / total_leads * 100) if total_leads > 0 else 0

                    source_html += f"""
                    <div style="background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 16px; text-align: center; border-left: 4px solid {color};">
                        <div style="font-size: 24px; margin-bottom: 8px;">{icon}</div>
                        <div style="font-size: 24px; font-weight: 700; color: #1E293B;">{count}</div>
                        <div style="font-size: 13px; color: #6B7280; text-transform: capitalize;">{source}</div>
                        <div style="font-size: 11px; color: #9CA3AF; margin-top: 4px;">{pct:.1f}% of total</div>
                    </div>
                    """
                source_html += '</div>'

                st.markdown(source_html, unsafe_allow_html=True)
            else:
                st.info("No lead sources to display yet. Start finding leads!")

        with analytics_subtab2:
            st.markdown("#### Activity Feed")

            # Collect all activities
            all_activities = []
            for lead in all_leads:
                lead_title = lead.get('title', lead.get('company', 'Unknown'))
                for activity in lead.get('activity_log', []):
                    activity['lead_title'] = lead_title
                    activity['lead_hash'] = lead.get('hash')
                    all_activities.append(activity)

            # Sort by timestamp
            all_activities.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            if all_activities:
                for activity in all_activities[:50]:
                    icon = "📌" if activity.get('type') == 'status_change' else "📝"
                    lead_title = activity.get('lead_title', 'Unknown')
                    timestamp = activity.get('timestamp', '')[:16].replace('T', ' ')

                    if activity.get('type') == 'status_change':
                        from_stage = CRM_STAGES.get(activity.get('from'), {}).get('name', activity.get('from'))
                        to_stage = CRM_STAGES.get(activity.get('to'), {}).get('name', activity.get('to'))
                        text = f"**{lead_title}** moved from {from_stage} to {to_stage}"
                    else:
                        content = activity.get('content', '')[:100]
                        text = f"Note added to **{lead_title}**: {content}"

                    st.markdown(f"""
                    <div class="activity-item">
                        <div class="activity-icon">{icon}</div>
                        <div class="activity-content">
                            <p class="activity-text">{text}</p>
                            <p class="activity-time">{timestamp}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No activities yet. Start moving leads through stages or adding notes to see activity here.")

        with analytics_subtab3:
            st.markdown("#### Quick Actions")

            # Bulk Actions
            st.markdown("##### Bulk Operations")

            bulk_col1, bulk_col2, bulk_col3 = st.columns(3)

            with bulk_col1:
                from_stage = st.selectbox(
                    "Move from",
                    list(CRM_STAGES.keys()),
                    format_func=lambda x: f"{CRM_STAGES[x]['icon']} {CRM_STAGES[x]['name']}",
                    key="bulk_from_stage"
                )

            with bulk_col2:
                to_stage = st.selectbox(
                    "Move to",
                    list(CRM_STAGES.keys()),
                    format_func=lambda x: f"{CRM_STAGES[x]['icon']} {CRM_STAGES[x]['name']}",
                    key="bulk_to_stage"
                )

            with bulk_col3:
                from_count = status_counts.get(from_stage, 0)
                st.write("")
                if st.button(f"Move {from_count} leads", type="primary", use_container_width=True, key="bulk_move_btn"):
                    if from_count > 0:
                        moved = 0
                        for lead in all_leads:
                            if lead.get('status', 'new') == from_stage:
                                if lead_manager.update_lead_status(lead.get('hash'), to_stage):
                                    moved += 1
                        st.success(f"Moved {moved} leads!")
                        st.rerun()
                    else:
                        st.warning("No leads to move")

    # ==================== TAB 8: HUBSPOT ====================
    with tab8:
        st.markdown("""
        <div style="margin-bottom: 20px;">
            <h3 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 20px; margin: 0; text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);">🔗 HUBSPOT INTEGRATION</h3>
            <p style="color: #708090; font-size: 13px; margin: 4px 0 0 0;">Sync leads and contacts with your HubSpot CRM</p>
        </div>
        """, unsafe_allow_html=True)

        with HubSpotCRM() as crm:
            if crm.is_configured():
                st.success("✓ HubSpot is connected and ready")

                hubspot_col1, hubspot_col2 = st.columns(2)

                with hubspot_col1:
                    st.markdown("#### Sync Leads to HubSpot")

                    sync_stage = st.selectbox(
                        "Select stage to sync",
                        list(CRM_STAGES.keys()),
                        format_func=lambda x: f"{CRM_STAGES[x]['icon']} {CRM_STAGES[x]['name']}",
                        key="hubspot_sync_stage"
                    )

                    leads_to_sync = [l for l in all_leads if l.get('status', 'new') == sync_stage and not l.get('hubspot_synced')]
                    st.info(f"{len(leads_to_sync)} leads ready to sync")

                    if st.button(f"🔄 Sync {len(leads_to_sync)} leads", type="primary", use_container_width=True):
                        if leads_to_sync:
                            progress = st.progress(0)
                            synced = 0

                            for i, lead_dict in enumerate(leads_to_sync):
                                try:
                                    from src.utils.models import Lead as LeadModel, LeadSource
                                    lead_obj = LeadModel(
                                        id=lead_dict.get('hash', ''),
                                        source=LeadSource.REDDIT,
                                        title=lead_dict.get('title', ''),
                                        content=lead_dict.get('content', ''),
                                        url=lead_dict.get('url', ''),
                                        email=lead_dict.get('email'),
                                        name=lead_dict.get('author'),
                                        company=lead_dict.get('company'),
                                        phone=lead_dict.get('phone'),
                                        industry=lead_dict.get('industry'),
                                        pain_score=lead_dict.get('pain_score', 0)
                                    )
                                    result = crm.create_contact(lead_obj)
                                    if result:
                                        lead_manager.update_lead(lead_dict.get('hash'), {
                                            'hubspot_synced': True,
                                            'hubspot_id': result
                                        })
                                        synced += 1
                                except Exception as e:
                                    st.warning(f"Error: {str(e)[:50]}")

                                progress.progress((i + 1) / len(leads_to_sync))

                            st.success(f"✓ Synced {synced} leads to HubSpot!")
                            st.rerun()
                        else:
                            st.info("No leads to sync in this stage")

                with hubspot_col2:
                    st.markdown("#### Sync Statistics")

                    synced_count = len([l for l in all_leads if l.get('hubspot_synced')])
                    not_synced = total_leads - synced_count

                    stat_col1, stat_col2 = st.columns(2)
                    with stat_col1:
                        st.metric("Synced", synced_count, delta=None)
                    with stat_col2:
                        st.metric("Pending", not_synced, delta=None)

                    # Progress bar
                    sync_pct = (synced_count / total_leads * 100) if total_leads > 0 else 0
                    st.progress(sync_pct / 100)
                    st.caption(f"{sync_pct:.0f}% synced")

                st.markdown("---")

                # View HubSpot contacts
                st.markdown("#### HubSpot Contacts")
                if st.button("📋 Load HubSpot Contacts", use_container_width=True):
                    with st.spinner("Loading..."):
                        try:
                            contacts = crm.get_all_contacts(limit=20)
                            if contacts:
                                st.write(f"Found {len(contacts)} contacts:")
                                for c in contacts[:10]:
                                    name = f"{c.firstname or ''} {c.lastname or ''}".strip() or "No name"
                                    st.caption(f"• {name} - {c.email or 'No email'}")
                            else:
                                st.info("No contacts found in HubSpot")
                        except Exception as e:
                            st.error(f"Error loading contacts: {str(e)}")

            else:
                st.warning("⚠️ HubSpot is not configured")

                st.markdown("""
                ### How to Connect HubSpot

                1. **Create a HubSpot account** at [hubspot.com](https://www.hubspot.com) (free tier available)

                2. **Create a Private App:**
                   - Go to Settings → Integrations → Private Apps
                   - Click "Create a private app"
                   - Give it a name (e.g., "LeadGen Pro")
                   - Under Scopes, enable: `crm.objects.contacts.read` and `crm.objects.contacts.write`
                   - Click "Create app" and copy the Access Token

                3. **Add to your `.env` file:**
                   ```
                   HUBSPOT_API_KEY=your_access_token_here
                   ```

                4. **Restart the application**
                """)

                st.info("💡 You can use the internal CRM without HubSpot. Your data is saved locally.")


def show_config():
    # Holographic Settings Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%);
                border: 1px solid rgba(0, 255, 255, 0.3);
                border-radius: 16px;
                padding: 32px;
                margin-bottom: 24px;
                backdrop-filter: blur(10px);
                box-shadow: 0 0 40px rgba(0, 255, 255, 0.1), inset 0 0 60px rgba(0, 255, 255, 0.05);
                position: relative;
                overflow: hidden;">
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent 0%, #00FFFF 50%, transparent 100%); opacity: 0.8;"></div>
        <div style="display: flex; align-items: center; gap: 20px;">
            <div style="background: linear-gradient(135deg, rgba(0, 255, 255, 0.2) 0%, rgba(0, 139, 139, 0.2) 100%);
                        border: 1px solid rgba(0, 255, 255, 0.4);
                        border-radius: 16px;
                        padding: 16px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        box-shadow: 0 0 20px rgba(0, 255, 255, 0.2);">
                <span style="font-size: 36px;">⚙️</span>
            </div>
            <div>
                <h1 style="margin: 0 0 8px 0; color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 32px; letter-spacing: 0.1em; text-shadow: 0 0 20px rgba(0, 255, 255, 0.5);">SETTINGS</h1>
                <p style="margin: 0; color: #C0C0C0; font-size: 15px;">Configure your API integrations, system parameters, and platform preferences</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # API Integrations Section
    st.markdown("""
    <div style="background: rgba(28, 28, 46, 0.6); border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 12px; padding: 20px; margin-bottom: 20px; backdrop-filter: blur(5px);">
        <h3 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 18px; margin: 0 0 8px 0; letter-spacing: 0.05em;">
            🔗 API INTEGRATIONS
        </h3>
        <p style="color: #708090; font-size: 13px; margin: 0;">Connect your external services to unlock full platform functionality</p>
    </div>
    """, unsafe_allow_html=True)

    # API Cards - Row 1 (Main APIs)
    st.markdown("""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
    """, unsafe_allow_html=True)

    # HubSpot - Holographic status colors
    hubspot_icon = "✓" if settings.hubspot_api_key else "○"
    hubspot_color = "#00FF88" if settings.hubspot_api_key else "#FFB800"
    hubspot_border = "rgba(0, 255, 136, 0.4)" if settings.hubspot_api_key else "rgba(255, 184, 0, 0.4)"
    hubspot_bg = "rgba(0, 255, 136, 0.15)" if settings.hubspot_api_key else "rgba(255, 184, 0, 0.15)"
    hubspot_text = "Connected" if settings.hubspot_api_key else "Not configured"

    # Google
    google_icon = "✓" if settings.google_api_key else "○"
    google_color = "#00FF88" if settings.google_api_key else "#FFB800"
    google_border = "rgba(0, 255, 136, 0.4)" if settings.google_api_key else "rgba(255, 184, 0, 0.4)"
    google_bg = "rgba(0, 255, 136, 0.15)" if settings.google_api_key else "rgba(255, 184, 0, 0.15)"
    google_text = "Connected" if settings.google_api_key else "Not configured"

    # OpenAI
    openai_icon = "✓" if settings.openai_api_key else "○"
    openai_color = "#00FF88" if settings.openai_api_key else "#FFB800"
    openai_border = "rgba(0, 255, 136, 0.4)" if settings.openai_api_key else "rgba(255, 184, 0, 0.4)"
    openai_bg = "rgba(0, 255, 136, 0.15)" if settings.openai_api_key else "rgba(255, 184, 0, 0.15)"
    openai_text = "Connected" if settings.openai_api_key else "Not configured"

    # Anthropic
    anthropic_icon = "✓" if settings.anthropic_api_key else "○"
    anthropic_color = "#00FF88" if settings.anthropic_api_key else "#FFB800"
    anthropic_border = "rgba(0, 255, 136, 0.4)" if settings.anthropic_api_key else "rgba(255, 184, 0, 0.4)"
    anthropic_bg = "rgba(0, 255, 136, 0.15)" if settings.anthropic_api_key else "rgba(255, 184, 0, 0.15)"
    anthropic_text = "Connected" if settings.anthropic_api_key else "Not configured"

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
        <!-- HubSpot -->
        <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%);
                    border: 1px solid rgba(0, 255, 255, 0.2);
                    border-radius: 16px;
                    padding: 20px;
                    text-align: center;
                    backdrop-filter: blur(5px);
                    box-shadow: 0 0 20px rgba(0, 255, 255, 0.05);">
            <div style="font-size: 32px; margin-bottom: 12px;">📊</div>
            <h4 style="margin: 0 0 8px 0; color: #E5E5E5; font-size: 16px; font-weight: 600; font-family: 'Rajdhani', sans-serif;">HubSpot CRM</h4>
            <div style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; background: {hubspot_bg}; border: 1px solid {hubspot_border}; color: {hubspot_color}; border-radius: 20px; font-size: 12px; font-weight: 600;">
                <span>{hubspot_icon}</span> {hubspot_text}
            </div>
            <p style="margin: 12px 0 0 0; color: #708090; font-size: 11px;">Sync leads & contacts</p>
        </div>
        <!-- Google -->
        <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%);
                    border: 1px solid rgba(0, 255, 255, 0.2);
                    border-radius: 16px;
                    padding: 20px;
                    text-align: center;
                    backdrop-filter: blur(5px);
                    box-shadow: 0 0 20px rgba(0, 255, 255, 0.05);">
            <div style="font-size: 32px; margin-bottom: 12px;">🔍</div>
            <h4 style="margin: 0 0 8px 0; color: #E5E5E5; font-size: 16px; font-weight: 600; font-family: 'Rajdhani', sans-serif;">Google Search</h4>
            <div style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; background: {google_bg}; border: 1px solid {google_border}; color: {google_color}; border-radius: 20px; font-size: 12px; font-weight: 600;">
                <span>{google_icon}</span> {google_text}
            </div>
            <p style="margin: 12px 0 0 0; color: #708090; font-size: 11px;">Web search for leads</p>
        </div>
        <!-- OpenAI -->
        <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%);
                    border: 1px solid rgba(0, 255, 255, 0.2);
                    border-radius: 16px;
                    padding: 20px;
                    text-align: center;
                    backdrop-filter: blur(5px);
                    box-shadow: 0 0 20px rgba(0, 255, 255, 0.05);">
            <div style="font-size: 32px; margin-bottom: 12px;">🤖</div>
            <h4 style="margin: 0 0 8px 0; color: #E5E5E5; font-size: 16px; font-weight: 600; font-family: 'Rajdhani', sans-serif;">OpenAI</h4>
            <div style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; background: {openai_bg}; border: 1px solid {openai_border}; color: {openai_color}; border-radius: 20px; font-size: 12px; font-weight: 600;">
                <span>{openai_icon}</span> {openai_text}
            </div>
            <p style="margin: 12px 0 0 0; color: #708090; font-size: 11px;">AI lead qualification</p>
        </div>
        <!-- Anthropic -->
        <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%);
                    border: 1px solid rgba(0, 255, 255, 0.2);
                    border-radius: 16px;
                    padding: 20px;
                    text-align: center;
                    backdrop-filter: blur(5px);
                    box-shadow: 0 0 20px rgba(0, 255, 255, 0.05);">
            <div style="font-size: 32px; margin-bottom: 12px;">🧠</div>
            <h4 style="margin: 0 0 8px 0; color: #E5E5E5; font-size: 16px; font-weight: 600; font-family: 'Rajdhani', sans-serif;">Anthropic Claude</h4>
            <div style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; background: {anthropic_bg}; border: 1px solid {anthropic_border}; color: {anthropic_color}; border-radius: 20px; font-size: 12px; font-weight: 600;">
                <span>{anthropic_icon}</span> {anthropic_text}
            </div>
            <p style="margin: 12px 0 0 0; color: #708090; font-size: 11px;">AI assistant</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Row 2 - Enrichment APIs
    hunter_status = "connected" if settings.hunter_api_key else "optional"
    hunter_icon = "✓" if settings.hunter_api_key else "○"
    hunter_color = "#10B981" if settings.hunter_api_key else "#3B82F6"
    hunter_bg = "#D1FAE5" if settings.hunter_api_key else "#DBEAFE"
    hunter_text = "Connected" if settings.hunter_api_key else "Optional"

    apollo_status = "connected" if settings.apollo_api_key else "disconnected"
    apollo_icon = "✓" if settings.apollo_api_key else "○"
    apollo_color = "#10B981" if settings.apollo_api_key else "#F59E0B"
    apollo_bg = "#D1FAE5" if settings.apollo_api_key else "#FEF3C7"
    apollo_text = "Connected" if settings.apollo_api_key else "Not configured"

    # ZeroBounce status
    zerobounce_icon = "✓" if settings.zerobounce_api_key else "○"
    zerobounce_text = "Connected" if settings.zerobounce_api_key else "Optional"

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; margin-bottom: 32px;">
        <!-- Hunter.io -->
        <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%); border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 16px; padding: 20px; text-align: center; backdrop-filter: blur(10px);">
            <div style="font-size: 32px; margin-bottom: 12px; filter: drop-shadow(0 0 5px #00FFFF);">📧</div>
            <h4 style="margin: 0 0 8px 0; color: #00FFFF; font-size: 16px; font-weight: 600; font-family: 'Orbitron', sans-serif;">Hunter.io</h4>
            <div style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; background: {'rgba(0, 255, 136, 0.2)' if settings.hunter_api_key else 'rgba(255, 184, 0, 0.2)'}; color: {'#00FF88' if settings.hunter_api_key else '#FFB800'}; border: 1px solid {'rgba(0, 255, 136, 0.4)' if settings.hunter_api_key else 'rgba(255, 184, 0, 0.4)'}; border-radius: 20px; font-size: 12px; font-weight: 600;">
                <span>{hunter_icon}</span> {hunter_text}
            </div>
            <p style="margin: 12px 0 0 0; color: #708090; font-size: 11px;">Email finder service</p>
        </div>
        <!-- Apollo.io -->
        <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%); border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 16px; padding: 20px; text-align: center; backdrop-filter: blur(10px);">
            <div style="font-size: 32px; margin-bottom: 12px; filter: drop-shadow(0 0 5px #00FFFF);">🚀</div>
            <h4 style="margin: 0 0 8px 0; color: #00FFFF; font-size: 16px; font-weight: 600; font-family: 'Orbitron', sans-serif;">Apollo.io</h4>
            <div style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; background: {'rgba(0, 255, 136, 0.2)' if settings.apollo_api_key else 'rgba(255, 184, 0, 0.2)'}; color: {'#00FF88' if settings.apollo_api_key else '#FFB800'}; border: 1px solid {'rgba(0, 255, 136, 0.4)' if settings.apollo_api_key else 'rgba(255, 184, 0, 0.4)'}; border-radius: 20px; font-size: 12px; font-weight: 600;">
                <span>{apollo_icon}</span> {apollo_text}
            </div>
            <p style="margin: 12px 0 0 0; color: #708090; font-size: 11px;">Email + Phone + Company</p>
        </div>
        <!-- ZeroBounce - Email Verification -->
        <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%); border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 16px; padding: 20px; text-align: center; backdrop-filter: blur(10px);">
            <div style="font-size: 32px; margin-bottom: 12px; filter: drop-shadow(0 0 5px #00FFFF);">✅</div>
            <h4 style="margin: 0 0 8px 0; color: #00FFFF; font-size: 16px; font-weight: 600; font-family: 'Orbitron', sans-serif;">ZeroBounce</h4>
            <div style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; background: {'rgba(0, 255, 136, 0.2)' if settings.zerobounce_api_key else 'rgba(255, 184, 0, 0.2)'}; color: {'#00FF88' if settings.zerobounce_api_key else '#FFB800'}; border: 1px solid {'rgba(0, 255, 136, 0.4)' if settings.zerobounce_api_key else 'rgba(255, 184, 0, 0.4)'}; border-radius: 20px; font-size: 12px; font-weight: 600;">
                <span>{zerobounce_icon}</span> {zerobounce_text}
            </div>
            <p style="margin: 12px 0 0 0; color: #708090; font-size: 11px;">Email verification</p>
        </div>
        <!-- Deduplication -->
        <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%); border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 16px; padding: 20px; text-align: center; backdrop-filter: blur(10px);">
            <div style="font-size: 32px; margin-bottom: 12px; filter: drop-shadow(0 0 5px #00FF88);">🔄</div>
            <h4 style="margin: 0 0 8px 0; color: #00FFFF; font-size: 16px; font-weight: 600; font-family: 'Orbitron', sans-serif;">Deduplication</h4>
            <div style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; background: rgba(0, 255, 136, 0.2); color: #00FF88; border: 1px solid rgba(0, 255, 136, 0.4); border-radius: 20px; font-size: 12px; font-weight: 600;">
                <span>✓</span> Active
            </div>
            <p style="margin: 12px 0 0 0; color: #708090; font-size: 11px;">Remove duplicate leads</p>
        </div>
        <!-- CSV Export -->
        <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%); border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 16px; padding: 20px; text-align: center; backdrop-filter: blur(10px);">
            <div style="font-size: 32px; margin-bottom: 12px; filter: drop-shadow(0 0 5px #00FFFF);">📥</div>
            <h4 style="margin: 0 0 8px 0; color: #00FFFF; font-size: 16px; font-weight: 600; font-family: 'Orbitron', sans-serif;">CSV Export</h4>
            <div style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; background: rgba(0, 255, 136, 0.2); color: #00FF88; border: 1px solid rgba(0, 255, 136, 0.4); border-radius: 20px; font-size: 12px; font-weight: 600;">
                <span>✓</span> Available
            </div>
            <p style="margin: 12px 0 0 0; color: #708090; font-size: 11px;">Export leads to CSV</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # System Status Section - Holographic
    st.markdown("""
    <div style="margin-bottom: 24px;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
            <h2 style="margin: 0; color: #00FFFF; font-size: 20px; font-weight: 700; font-family: 'Orbitron', sans-serif; letter-spacing: 0.1em; text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);">📈 SYSTEM STATUS</h2>
        </div>
        <p style="margin: 0; color: #C0C0C0; font-size: 14px;">Current system features and data statistics</p>
    </div>
    """, unsafe_allow_html=True)

    stats = lead_manager.get_stats()
    ai_ready = settings.openai_api_key or settings.anthropic_api_key

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px;">
        <!-- Storage -->
        <div style="background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%); border-radius: 16px; padding: 20px; text-align: center; color: white;">
            <div style="font-size: 28px; margin-bottom: 8px;">💾</div>
            <div style="font-size: 32px; font-weight: 700;">{stats['total']}</div>
            <div style="font-size: 14px; opacity: 0.9;">Saved Leads</div>
        </div>
        <!-- Triple Score -->
        <div style="background: linear-gradient(135deg, #10B981 0%, #059669 100%); border-radius: 16px; padding: 20px; text-align: center; color: white;">
            <div style="font-size: 28px; margin-bottom: 8px;">📊</div>
            <div style="font-size: 20px; font-weight: 700;">Triple Score</div>
            <div style="font-size: 14px; opacity: 0.9;">Pain + Intent + Fit</div>
        </div>
        <!-- AI Filter -->
        <div style="background: linear-gradient(135deg, {'#8B5CF6' if ai_ready else '#F59E0B'} 0%, {'#7C3AED' if ai_ready else '#D97706'} 100%); border-radius: 16px; padding: 20px; text-align: center; color: white;">
            <div style="font-size: 28px; margin-bottom: 8px;">🎯</div>
            <div style="font-size: 20px; font-weight: 700;">AI Filter</div>
            <div style="font-size: 14px; opacity: 0.9;">{'Ready' if ai_ready else 'No AI Key'}</div>
        </div>
        <!-- Lead Warming -->
        <div style="background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%); border-radius: 16px; padding: 20px; text-align: center; color: white;">
            <div style="font-size: 28px; margin-bottom: 8px;">🔥</div>
            <div style="font-size: 20px; font-weight: 700;">Lead Warming</div>
            <div style="font-size: 14px; opacity: 0.9;">Available</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Industries Section - Holographic
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%); border: 1px solid rgba(0, 255, 255, 0.2); border-radius: 16px; padding: 24px; margin-bottom: 24px; backdrop-filter: blur(10px);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
            <div>
                <h3 style="margin: 0 0 4px 0; color: #00FFFF; font-size: 18px; font-weight: 700; font-family: 'Orbitron', sans-serif;">🏢 INDUSTRIES CONFIGURED</h3>
                <p style="margin: 0; color: #C0C0C0; font-size: 13px;">Target industries for lead generation</p>
            </div>
            <div style="background: rgba(0, 139, 139, 0.3); color: #00FFFF; border: 1px solid rgba(0, 255, 255, 0.4); padding: 6px 16px; border-radius: 20px; font-size: 14px; font-weight: 600;">
                {len(settings.industries)} industries
            </div>
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
    """, unsafe_allow_html=True)

    industry_tags = ""
    for ind in list(settings.industries.keys()):
        industry_tags += f'<span style="background: rgba(0, 139, 139, 0.2); color: #C0C0C0; border: 1px solid rgba(0, 139, 139, 0.3); padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 500;">{ind}</span>'

    st.markdown(f"""
            {industry_tags}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Subreddits Section - Holographic
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%); border: 1px solid rgba(255, 69, 0, 0.3); border-radius: 16px; padding: 24px; margin-bottom: 24px; backdrop-filter: blur(10px);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
            <div>
                <h3 style="margin: 0 0 4px 0; color: #FF4500; font-size: 18px; font-weight: 700; font-family: 'Orbitron', sans-serif;">📱 REDDIT SOURCES</h3>
                <p style="margin: 0; color: #C0C0C0; font-size: 13px;">Subreddits monitored for leads</p>
            </div>
            <div style="background: rgba(255, 69, 0, 0.2); color: #FF4500; border: 1px solid rgba(255, 69, 0, 0.4); padding: 6px 16px; border-radius: 20px; font-size: 14px; font-weight: 600;">
                {len(settings.subreddits)} subreddits
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("View all subreddits"):
        sub_cols = st.columns(5)
        for i, s in enumerate(settings.subreddits):
            with sub_cols[i % 5]:
                st.markdown(f"• r/{s}")

    # Keywords Section - Holographic
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%); border: 1px solid rgba(255, 184, 0, 0.3); border-radius: 16px; padding: 24px; margin-bottom: 24px; backdrop-filter: blur(10px);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
            <div>
                <h3 style="margin: 0 0 4px 0; color: #FFB800; font-size: 18px; font-weight: 700; font-family: 'Orbitron', sans-serif;">🔑 PAIN KEYWORDS</h3>
                <p style="margin: 0; color: #C0C0C0; font-size: 13px;">Keywords that indicate buying intent or pain points</p>
            </div>
            <div style="background: rgba(255, 184, 0, 0.2); color: #FFB800; border: 1px solid rgba(255, 184, 0, 0.4); padding: 6px 16px; border-radius: 20px; font-size: 14px; font-weight: 600;">
                {len(settings.pain_keywords)} keywords
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("View all keywords"):
        kw_cols = st.columns(4)
        for i, kw in enumerate(settings.pain_keywords):
            with kw_cols[i % 4]:
                st.markdown(f"• {kw}")

    # Configuration Help - Holographic
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(0, 139, 139, 0.15) 0%, rgba(28, 28, 46, 0.8) 100%); border: 1px solid rgba(0, 255, 255, 0.3); border-radius: 16px; padding: 24px; margin-top: 24px; backdrop-filter: blur(10px);">
        <div style="display: flex; align-items: flex-start; gap: 16px;">
            <div style="background: rgba(0, 139, 139, 0.3); border: 1px solid #008B8B; border-radius: 12px; padding: 12px; display: flex; align-items: center; justify-content: center;">
                <span style="font-size: 24px; filter: drop-shadow(0 0 5px #00FFFF);">💡</span>
            </div>
            <div>
                <h4 style="margin: 0 0 8px 0; color: #00FFFF; font-size: 16px; font-weight: 700; font-family: 'Orbitron', sans-serif;">HOW TO CONFIGURE API KEYS</h4>
                <p style="margin: 0; color: #C0C0C0; font-size: 14px; line-height: 1.6;">
                    Go to your Streamlit Cloud dashboard → Settings → Secrets to add or update your API credentials securely.
                    Each API key should be added as an environment variable (e.g., HUBSPOT_API_KEY, OPENAI_API_KEY).
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================
# AI ASSISTANT
# ============================================
def show_ai_assistant():
    """AI Lead Generation Assistant - Expert advisor for lead generation."""

    # Holographic CSS for chat interface
    st.markdown("""
    <style>
        .assistant-header {
            background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%);
            border: 1px solid rgba(0, 255, 255, 0.3);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            backdrop-filter: blur(10px);
            box-shadow: 0 0 40px rgba(0, 255, 255, 0.1);
            position: relative;
            overflow: hidden;
        }
        .assistant-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent 0%, #00FFFF 50%, transparent 100%);
        }
        .assistant-title {
            font-size: 28px;
            font-weight: 700;
            margin: 0 0 8px 0;
            color: #00FFFF;
            font-family: 'Orbitron', sans-serif;
            text-shadow: 0 0 20px rgba(0, 255, 255, 0.5);
        }
        .assistant-subtitle {
            font-size: 14px;
            color: #C0C0C0;
            margin: 0;
        }
        .chat-message {
            padding: 16px;
            border-radius: 12px;
            margin-bottom: 12px;
            animation: fadeIn 0.3s ease;
            backdrop-filter: blur(5px);
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .user-message {
            background: linear-gradient(135deg, rgba(0, 139, 139, 0.15) 0%, rgba(45, 55, 72, 0.3) 100%);
            border: 1px solid rgba(0, 139, 139, 0.3);
            border-left: 3px solid #008B8B;
            margin-left: 40px;
        }
        .assistant-message {
            background: linear-gradient(135deg, rgba(0, 255, 136, 0.15) 0%, rgba(0, 40, 40, 0.3) 100%);
            border: 1px solid rgba(0, 255, 136, 0.3);
            border-left: 3px solid #00FF88;
            margin-right: 40px;
        }
        .message-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
            font-weight: 600;
            font-size: 13px;
            color: #E5E5E5;
        }
        .message-content {
            font-size: 14px;
            line-height: 1.6;
            color: #E5E5E5;
        }
        .quick-action-chip {
            display: inline-block;
            background: rgba(28, 28, 46, 0.6);
            border: 1px solid rgba(0, 255, 255, 0.2);
            border-radius: 20px;
            padding: 8px 16px;
            margin: 4px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s ease;
            color: #C0C0C0;
        }
        .quick-action-chip:hover {
            background: rgba(0, 255, 255, 0.15);
            color: #00FFFF;
            border-color: rgba(0, 255, 255, 0.5);
            box-shadow: 0 0 15px rgba(0, 255, 255, 0.2);
        }
        .stats-card {
            background: rgba(28, 28, 46, 0.6);
            border: 1px solid rgba(0, 255, 255, 0.2);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            backdrop-filter: blur(5px);
        }
        .stats-value {
            font-size: 24px;
            font-weight: 700;
            color: #00FFFF;
            font-family: 'Orbitron', sans-serif;
            text-shadow: 0 0 15px rgba(0, 255, 255, 0.5);
        }
        .stats-label {
            font-size: 12px;
            color: #708090;
        }
    </style>
    """, unsafe_allow_html=True)

    # Initialize chat history
    if 'assistant_messages' not in st.session_state:
        st.session_state.assistant_messages = []

    # Header
    st.markdown("""
    <div class="assistant-header">
        <p class="assistant-title">🤖 Lead Generation AI Assistant</p>
        <p class="assistant-subtitle">Tu experto en estrategias de prospección y generación de leads. Pregúntame cualquier cosa sobre la plataforma o cómo conseguir mejores resultados.</p>
    </div>
    """, unsafe_allow_html=True)

    # Two columns: Chat + Tips
    chat_col, tips_col = st.columns([2, 1])

    with tips_col:
        st.markdown("### 💡 Consejos Rápidos")

        # Quick action buttons
        quick_questions = [
            "¿Cómo conseguir más leads?",
            "¿Qué fuentes son mejores?",
            "¿Cómo mejorar mi búsqueda?",
            "¿Cómo usar el filtro de ubicación?",
            "¿Qué industrias buscar?",
            "¿Cómo escribir cold emails?"
        ]

        for q in quick_questions:
            if st.button(q, key=f"quick_{q}", use_container_width=True):
                st.session_state.assistant_pending_question = q
                st.rerun()

        st.markdown("---")

        # Platform stats
        st.markdown("### 📊 Tu Actividad")
        stats = lead_manager.get_stats()

        stat_col1, stat_col2 = st.columns(2)
        with stat_col1:
            st.markdown(f"""
            <div class="stats-card">
                <div class="stats-value">{stats['total']}</div>
                <div class="stats-label">Leads Guardados</div>
            </div>
            """, unsafe_allow_html=True)
        with stat_col2:
            qualified = stats.get('qualified', 0)
            st.markdown(f"""
            <div class="stats-card">
                <div class="stats-value">{qualified}</div>
                <div class="stats-label">Calificados</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Sources status
        st.markdown("### 🔌 Fuentes Activas")
        sources = [
            ("🔴 Reddit", True),
            ("🟠 Hacker News", True),
            ("💼 Indeed", True),
            ("⭐ Yelp", True),
            ("📍 Google Maps", True),
            ("🔷 LinkedIn", bool(settings.google_api_key)),
            ("🔵 Google Search", bool(settings.google_api_key)),
        ]
        for name, active in sources:
            status = "✅" if active else "❌"
            st.caption(f"{status} {name}")

    with chat_col:
        st.markdown("### 💬 Chat con el Asistente")

        # Display chat history
        chat_container = st.container()

        with chat_container:
            # Welcome message if no history
            if not st.session_state.assistant_messages:
                st.markdown("""
                <div class="chat-message assistant-message">
                    <div class="message-header">🤖 Asistente</div>
                    <div class="message-content">
                        ¡Hola! Soy tu asistente de Lead Generation. Puedo ayudarte con:
                        <br><br>
                        • <b>Estrategias de búsqueda</b> - Qué fuentes usar y cómo configurarlas<br>
                        • <b>Mejores prácticas</b> - Cómo encontrar leads de calidad<br>
                        • <b>Cold outreach</b> - Cómo escribir emails que conviertan<br>
                        • <b>Uso de la plataforma</b> - Cualquier función o característica<br>
                        • <b>Tu industria</b> - Consejos específicos para AI receptionist
                        <br><br>
                        ¿En qué puedo ayudarte hoy?
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Display conversation history
            for msg in st.session_state.assistant_messages:
                if msg["role"] == "user":
                    st.markdown(f"""
                    <div class="chat-message user-message">
                        <div class="message-header">👤 Tú</div>
                        <div class="message-content">{msg["content"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="chat-message assistant-message">
                        <div class="message-header">🤖 Asistente</div>
                        <div class="message-content">{msg["content"]}</div>
                    </div>
                    """, unsafe_allow_html=True)

        # Check for pending quick question
        if 'assistant_pending_question' in st.session_state:
            pending = st.session_state.assistant_pending_question
            del st.session_state.assistant_pending_question
            process_assistant_message(pending)
            st.rerun()

        # Chat input
        user_input = st.chat_input("Escribe tu pregunta aquí...")

        if user_input:
            process_assistant_message(user_input)
            st.rerun()

        # Clear chat button
        if st.session_state.assistant_messages:
            if st.button("🗑️ Limpiar conversación", use_container_width=True):
                st.session_state.assistant_messages = []
                st.rerun()


def process_assistant_message(user_message: str):
    """Process user message and generate AI response."""

    # Add user message to history
    st.session_state.assistant_messages.append({
        "role": "user",
        "content": user_message
    })

    # Generate response
    response = generate_assistant_response(user_message)

    # Add assistant response to history
    st.session_state.assistant_messages.append({
        "role": "assistant",
        "content": response
    })


def generate_assistant_response(user_message: str) -> str:
    """Generate AI response using OpenAI or fallback to rule-based."""

    # Try OpenAI first
    if settings.openai_api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=settings.openai_api_key)

            # System prompt with platform knowledge (bilingual)
            system_prompt = """You are an expert in Lead Generation and sales prospecting for LeadGen Pro, a lead generation platform for an AI Receptionist product (AI phone agent that answers calls, schedules appointments, responds to questions).

CRITICAL: Detect the language of the user's message and ALWAYS respond in the SAME language:
- If user writes in Spanish → respond in Spanish
- If user writes in English → respond in English

YOUR PLATFORM KNOWLEDGE:

AVAILABLE SEARCH SOURCES (8 total):
1. Reddit (FREE) - Searches business subreddits like smallbusiness, entrepreneur
2. Hacker News (FREE) - Searches startups and tech companies
3. Product Hunt (FREE) - Finds new products and their makers
4. Indeed (FREE) - Companies hiring receptionists = they need your solution
5. Yelp (FREE) - Local service businesses
6. Google Maps (FREE) - Local businesses with phone, website, email
7. LinkedIn (uses Google API) - Decision makers and business owners
8. Google Search (uses Google API) - Complaints about phones and customer service

TARGET INDUSTRIES for AI Receptionist:
- Dental (dentists, orthodontists) / Dental (dentistas, ortodoncistas)
- HVAC (air conditioning, heating) / HVAC (aire acondicionado, calefacción)
- Legal (lawyers, law firms) / Legal (abogados, bufetes)
- Medical (clinics, doctor offices) / Medical (clínicas, consultorios)
- Beauty (salons, spas) / Beauty (salones, spas)
- Auto (repair shops, dealerships) / Auto (talleres, concesionarios)
- Real Estate (realtors) / Real Estate (inmobiliarias)
- Insurance (agents, brokers) / Insurance (seguros)

SEARCH TIPS:
- Use location filter for Indeed, Yelp, Google Maps, LinkedIn
- Companies hiring receptionists = perfect opportunity
- Businesses with bad reviews about "don't answer the phone" = hot leads
- LinkedIn finds decision makers directly

OUTREACH STRATEGIES:
- Cold email: Personalize with the business's specific pain point
- Use Hormozi's "damaging admission" - acknowledge limitations to gain trust
- LTV (customer lifetime value) determines how much you can pay to acquire leads

Be concise and practical. Give actionable advice."""

            messages = [
                {"role": "system", "content": system_prompt}
            ]

            # Add recent conversation history (last 6 messages)
            for msg in st.session_state.assistant_messages[-6:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

            # Add current message
            messages.append({"role": "user", "content": user_message})

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=800,
                temperature=0.7
            )

            return response.choices[0].message.content

        except Exception as e:
            # Fallback to rule-based if API fails
            return get_fallback_response(user_message)
    else:
        return get_fallback_response(user_message)


def get_fallback_response(user_message: str) -> str:
    """Rule-based fallback responses when AI is not available. Bilingual (ES/EN)."""

    message_lower = user_message.lower()

    # Detect language - Spanish indicators
    spanish_words = ["cómo", "qué", "cuál", "más", "para", "buscar", "mejor", "hola", "gracias", "ayuda", "necesito", "quiero"]
    is_spanish = any(word in message_lower for word in spanish_words)

    # LEADS - How to get more leads
    if any(word in message_lower for word in ["más leads", "conseguir", "encontrar más", "mejorar", "more leads", "get more", "find more", "improve"]):
        if is_spanish:
            return """<b>Para conseguir más leads:</b><br><br>
1. <b>Activa Google Maps</b> - Es gratis y encuentra negocios locales con teléfono y email<br>
2. <b>Usa filtro de ubicación</b> - Enfócate en ciudades específicas (Miami, LA, Houston)<br>
3. <b>Indeed es oro</b> - Empresas contratando recepcionistas = necesitan tu solución<br>
4. <b>LinkedIn</b> - Encuentra dueños de negocios directamente (necesita Google API)<br><br>
💡 <b>Tip:</b> Combina Indeed + Google Maps + Yelp para la misma ciudad = leads locales con datos completos."""
        else:
            return """<b>To get more leads:</b><br><br>
1. <b>Enable Google Maps</b> - It's free and finds local businesses with phone and email<br>
2. <b>Use location filter</b> - Focus on specific cities (Miami, LA, Houston)<br>
3. <b>Indeed is gold</b> - Companies hiring receptionists = they need your solution<br>
4. <b>LinkedIn</b> - Find business owners directly (requires Google API)<br><br>
💡 <b>Tip:</b> Combine Indeed + Google Maps + Yelp for the same city = local leads with complete data."""

    # SOURCES - Best sources
    elif any(word in message_lower for word in ["fuente", "mejor", "cuál usar", "qué fuente", "source", "best", "which", "recommend"]):
        if is_spanish:
            return """<b>Mejores fuentes para AI Receptionist:</b><br><br>
🥇 <b>Indeed</b> - Empresas contratando recepcionistas NECESITAN tu producto<br>
🥈 <b>Google Maps</b> - Dentistas, HVAC, abogados con teléfono directo<br>
🥉 <b>Yelp</b> - Negocios de servicios con reviews<br><br>
<b>Por industria:</b><br>
• Dental → Google Maps + Yelp<br>
• HVAC → Google Maps + Indeed<br>
• Legal → LinkedIn + Google Maps<br><br>
💡 Las fuentes GRATIS (Indeed, Yelp, Google Maps) no gastan créditos de API."""
        else:
            return """<b>Best sources for AI Receptionist:</b><br><br>
🥇 <b>Indeed</b> - Companies hiring receptionists NEED your product<br>
🥈 <b>Google Maps</b> - Dentists, HVAC, lawyers with direct phone<br>
🥉 <b>Yelp</b> - Service businesses with reviews<br><br>
<b>By industry:</b><br>
• Dental → Google Maps + Yelp<br>
• HVAC → Google Maps + Indeed<br>
• Legal → LinkedIn + Google Maps<br><br>
💡 FREE sources (Indeed, Yelp, Google Maps) don't use API credits."""

    # LOCATION - How to use location filter
    elif any(word in message_lower for word in ["ubicación", "location", "ciudad", "filtro", "city", "filter", "area"]):
        if is_spanish:
            return """<b>Cómo usar el filtro de ubicación:</b><br><br>
1. En <b>Find Leads</b>, busca la sección "Location Filter"<br>
2. Ingresa la ciudad (ej: Miami, Los Angeles)<br>
3. Selecciona el estado del dropdown<br>
4. Opcional: agrega código postal para más precisión<br><br>
<b>Fuentes que usan ubicación:</b><br>
✅ Indeed - Busca empleos en esa ciudad<br>
✅ Yelp - Busca negocios en esa área<br>
✅ Google Maps - Busca negocios locales<br>
✅ LinkedIn - Filtra perfiles por ubicación<br><br>
💡 <b>Tip:</b> Empieza con ciudades grandes (Miami, LA, Houston, Dallas) para más resultados."""
        else:
            return """<b>How to use the location filter:</b><br><br>
1. In <b>Find Leads</b>, find the "Location Filter" section<br>
2. Enter the city (e.g., Miami, Los Angeles)<br>
3. Select the state from dropdown<br>
4. Optional: add zip code for more precision<br><br>
<b>Sources that use location:</b><br>
✅ Indeed - Searches jobs in that city<br>
✅ Yelp - Searches businesses in that area<br>
✅ Google Maps - Searches local businesses<br>
✅ LinkedIn - Filters profiles by location<br><br>
💡 <b>Tip:</b> Start with large cities (Miami, LA, Houston, Dallas) for more results."""

    # INDUSTRY - What industries to target
    elif any(word in message_lower for word in ["industria", "sector", "qué buscar", "tipo de negocio", "industry", "target", "business type", "niche"]):
        if is_spanish:
            return """<b>Mejores industrias para AI Receptionist:</b><br><br>
🦷 <b>Dental</b> - Alto volumen de llamadas, muchas citas<br>
❄️ <b>HVAC</b> - Emergencias 24/7, necesitan responder siempre<br>
⚖️ <b>Legal</b> - No pueden perder clientes potenciales<br>
🏥 <b>Medical</b> - Clínicas con muchas citas diarias<br>
💇 <b>Salones/Spas</b> - Reservaciones constantes<br>
🚗 <b>Auto Repair</b> - Clientes llaman para emergencias<br><br>
<b>Señales de que necesitan tu producto:</b><br>
• Contratan recepcionistas (Indeed)<br>
• Reviews quejándose de que "no contestan"<br>
• Negocios pequeños (1-20 empleados)"""
        else:
            return """<b>Best industries for AI Receptionist:</b><br><br>
🦷 <b>Dental</b> - High call volume, many appointments<br>
❄️ <b>HVAC</b> - 24/7 emergencies, need to always answer<br>
⚖️ <b>Legal</b> - Can't afford to lose potential clients<br>
🏥 <b>Medical</b> - Clinics with many daily appointments<br>
💇 <b>Salons/Spas</b> - Constant reservations<br>
🚗 <b>Auto Repair</b> - Customers call for emergencies<br><br>
<b>Signs they need your product:</b><br>
• Hiring receptionists (Indeed)<br>
• Reviews complaining "no one answers"<br>
• Small businesses (1-20 employees)"""

    # EMAIL - Cold outreach
    elif any(word in message_lower for word in ["email", "cold", "outreach", "contactar", "escribir", "write", "reach out", "contact"]):
        if is_spanish:
            return """<b>Cómo escribir cold emails efectivos:</b><br><br>
<b>Estructura ganadora:</b><br>
1. <b>Gancho</b> - "Vi que están contratando recepcionista..."<br>
2. <b>Dolor</b> - "Perder una llamada = perder un cliente de $X"<br>
3. <b>Solución</b> - "Nuestro AI atiende 24/7, agenda citas automáticamente"<br>
4. <b>CTA</b> - "¿15 minutos para una demo esta semana?"<br><br>
<b>Ejemplo:</b><br>
<i>"Hola [Nombre], vi en Indeed que buscan recepcionista para [Empresa]. ¿Sabías que el 67% de los clientes cuelgan si no contestan en 3 rings? Tengo una solución de IA que atiende 24/7. ¿Tienes 15 min para verlo?"</i><br><br>
💡 <b>Hormozi Tip:</b> Usa "admisión dañina" - "No reemplazamos humanos al 100%, pero cubrimos cuando no están"."""
        else:
            return """<b>How to write effective cold emails:</b><br><br>
<b>Winning structure:</b><br>
1. <b>Hook</b> - "I saw you're hiring a receptionist..."<br>
2. <b>Pain</b> - "Missing a call = losing a $X customer"<br>
3. <b>Solution</b> - "Our AI answers 24/7, schedules appointments automatically"<br>
4. <b>CTA</b> - "15 minutes for a demo this week?"<br><br>
<b>Example:</b><br>
<i>"Hi [Name], I saw on Indeed you're hiring a receptionist for [Company]. Did you know 67% of customers hang up if not answered in 3 rings? I have an AI solution that answers 24/7. Do you have 15 min to see it?"</i><br><br>
💡 <b>Hormozi Tip:</b> Use "damaging admission" - "We don't replace humans 100%, but we cover when they're not available"."""

    # COST - API credits
    elif any(word in message_lower for word in ["crédito", "api", "costo", "gratis", "pagar", "credit", "cost", "free", "pay", "price"]):
        if is_spanish:
            return """<b>Costos de la plataforma:</b><br><br>
<b>GRATIS (sin límite):</b><br>
✅ Reddit - RSS feeds<br>
✅ Hacker News - API pública<br>
✅ Product Hunt - RSS feeds<br>
✅ Indeed - Web scraping<br>
✅ Yelp - Web scraping<br>
✅ Google Maps - Web scraping<br><br>
<b>Usan Google API (100 gratis/día):</b><br>
• LinkedIn - ~5 queries por búsqueda<br>
• Google Search - ~15 queries por búsqueda<br><br>
💡 <b>Tip:</b> Usa solo las fuentes gratis para búsquedas ilimitadas."""
        else:
            return """<b>Platform costs:</b><br><br>
<b>FREE (unlimited):</b><br>
✅ Reddit - RSS feeds<br>
✅ Hacker News - Public API<br>
✅ Product Hunt - RSS feeds<br>
✅ Indeed - Web scraping<br>
✅ Yelp - Web scraping<br>
✅ Google Maps - Web scraping<br><br>
<b>Use Google API (100 free/day):</b><br>
• LinkedIn - ~5 queries per search<br>
• Google Search - ~15 queries per search<br><br>
💡 <b>Tip:</b> Use only free sources for unlimited searches."""

    # GREETING
    elif any(word in message_lower for word in ["hola", "hey", "buenos", "qué tal", "hello", "hi", "good morning", "good afternoon"]):
        if is_spanish:
            return """¡Hola! 👋 Soy tu asistente de Lead Generation.<br><br>
Puedo ayudarte con:<br>
• Estrategias para encontrar más leads<br>
• Qué fuentes usar para tu industria<br>
• Cómo escribir cold emails efectivos<br>
• Uso de la plataforma<br><br>
¿Qué necesitas hoy?"""
        else:
            return """Hello! 👋 I'm your Lead Generation assistant.<br><br>
I can help you with:<br>
• Strategies to find more leads<br>
• Which sources to use for your industry<br>
• How to write effective cold emails<br>
• Using the platform<br><br>
What do you need today?"""

    # DEFAULT
    else:
        if is_spanish:
            return """Entiendo tu pregunta. Aquí algunos consejos generales:<br><br>
<b>Para mejores resultados:</b><br>
1. Usa el <b>filtro de ubicación</b> para enfocarte en ciudades específicas<br>
2. Activa <b>Google Maps</b> para obtener teléfonos y emails<br>
3. <b>Indeed</b> encuentra empresas que necesitan tu producto<br>
4. Revisa los leads en <b>My Leads</b> antes de contactar<br><br>
¿Hay algo específico sobre la plataforma o estrategias de lead generation en lo que pueda ayudarte?"""
        else:
            return """I understand your question. Here are some general tips:<br><br>
<b>For better results:</b><br>
1. Use the <b>location filter</b> to focus on specific cities<br>
2. Enable <b>Google Maps</b> to get phones and emails<br>
3. <b>Indeed</b> finds companies that need your product<br>
4. Review leads in <b>My Leads</b> before contacting<br><br>
Is there anything specific about the platform or lead generation strategies I can help you with?"""


# ============================================
# MAIN
# ============================================
def render_floating_assistant():
    """Render a floating AI assistant button accessible from any page."""

    # Don't show floating button on AI Assistant page
    if st.session_state.get('nav_page') == "AI Assistant":
        return

    # Create a container at the bottom of the page for the floating button
    st.markdown("""
    <style>
        /* Floating AI Assistant Button Container */
        .floating-ai-container {
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 9999;
        }
        .floating-ai-btn {
            background: linear-gradient(135deg, #8B5CF6 0%, #6366F1 50%, #4F46E5 100%);
            color: white;
            padding: 14px 24px;
            border-radius: 30px;
            font-size: 14px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 8px 24px rgba(139, 92, 246, 0.4), 0 4px 12px rgba(99, 102, 241, 0.3);
            cursor: pointer;
            transition: all 0.3s ease;
            border: none;
            animation: pulse-glow 2s infinite;
        }
        .floating-ai-btn:hover {
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 12px 32px rgba(139, 92, 246, 0.5), 0 6px 16px rgba(99, 102, 241, 0.4);
        }
        @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 8px 24px rgba(139, 92, 246, 0.4), 0 4px 12px rgba(99, 102, 241, 0.3); }
            50% { box-shadow: 0 8px 32px rgba(139, 92, 246, 0.6), 0 4px 16px rgba(99, 102, 241, 0.5); }
        }
        /* Custom style for the floating button */
        div[data-testid="stVerticalBlock"] > div:has(> div > div > button#floating_ai_assistant) {
            position: fixed !important;
            bottom: 24px !important;
            right: 24px !important;
            z-index: 9999 !important;
        }
        button#floating_ai_assistant {
            background: linear-gradient(135deg, #8B5CF6 0%, #6366F1 50%, #4F46E5 100%) !important;
            color: white !important;
            border: none !important;
            padding: 14px 24px !important;
            border-radius: 30px !important;
            font-weight: 600 !important;
            box-shadow: 0 8px 24px rgba(139, 92, 246, 0.4) !important;
            animation: pulse-glow 2s infinite !important;
        }
        button#floating_ai_assistant:hover {
            transform: translateY(-3px) scale(1.02) !important;
            box-shadow: 0 12px 32px rgba(139, 92, 246, 0.5) !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # Create a floating button using Streamlit's native button with custom positioning
    # We'll use a container at the end of the page
    floating_container = st.container()
    with floating_container:
        col1, col2, col3 = st.columns([6, 2, 1])
        with col3:
            if st.button("🤖 AI Assistant", key="floating_ai_assistant", type="primary"):
                st.session_state.nav_page = "AI Assistant"
                st.rerun()


def show_lead_warming():
    """Lead Warming System - Warm up leads before cold outreach for higher conversion rates."""

    # Holographic Lead Warming CSS
    st.markdown("""
    <style>
        /* Temperature Indicators - Holographic */
        .temp-cold {
            background: linear-gradient(135deg, rgba(0, 139, 139, 0.3) 0%, rgba(45, 55, 72, 0.5) 100%);
            border: 1px solid rgba(0, 139, 139, 0.4);
            color: #008B8B;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-shadow: 0 0 10px rgba(0, 139, 139, 0.5);
        }
        .temp-warm {
            background: linear-gradient(135deg, rgba(255, 184, 0, 0.3) 0%, rgba(40, 30, 0, 0.5) 100%);
            border: 1px solid rgba(255, 184, 0, 0.4);
            color: #FFB800;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-shadow: 0 0 10px rgba(255, 184, 0, 0.5);
        }
        .temp-hot {
            background: linear-gradient(135deg, rgba(255, 51, 102, 0.3) 0%, rgba(40, 10, 20, 0.5) 100%);
            border: 1px solid rgba(255, 51, 102, 0.4);
            color: #FF3366;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-shadow: 0 0 10px rgba(255, 51, 102, 0.5);
        }

        /* Warming Card - Holographic */
        .warming-card {
            background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%);
            border: 1px solid rgba(0, 255, 255, 0.2);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 16px;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        .warming-card:hover {
            box-shadow: 0 0 30px rgba(0, 255, 255, 0.15);
            transform: translateY(-2px);
            border-color: rgba(0, 255, 255, 0.4);
        }

        /* Activity Timeline - Holographic */
        .activity-timeline {
            border-left: 3px solid rgba(0, 255, 255, 0.3);
            padding-left: 20px;
            margin-left: 10px;
        }
        .activity-item {
            position: relative;
            padding-bottom: 16px;
        }
        .activity-item::before {
            content: '';
            position: absolute;
            left: -26px;
            top: 4px;
            width: 12px;
            height: 12px;
            background: #008B8B;
            border-radius: 50%;
            border: 2px solid rgba(28, 28, 46, 0.8);
            box-shadow: 0 0 10px rgba(0, 139, 139, 0.5);
        }
        .activity-completed::before {
            background: #00FF88;
            box-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
        }
        .activity-pending::before {
            background: #708090;
        }

        /* Warming Stats - Holographic */
        .warming-stat-card {
            background: rgba(28, 28, 46, 0.6);
            border: 1px solid rgba(0, 255, 255, 0.2);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            backdrop-filter: blur(5px);
        }
        .warming-stat-value {
            font-size: 28px;
            font-weight: 700;
            color: #00FFFF;
            font-family: 'Orbitron', sans-serif;
            text-shadow: 0 0 15px rgba(0, 255, 255, 0.5);
        }
        .warming-stat-label {
            font-size: 12px;
            color: #708090;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* Progress Ring */
        .progress-ring {
            width: 80px;
            height: 80px;
            margin: 0 auto;
        }

        /* Warming Actions - Holographic */
        .warming-action-btn {
            background: linear-gradient(135deg, rgba(0, 255, 255, 0.2) 0%, rgba(45, 55, 72, 0.4) 100%);
            border: 1px solid rgba(0, 255, 255, 0.4);
            color: #00FFFF;
            padding: 10px 16px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            text-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
        }
        .warming-action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
            background: rgba(0, 255, 255, 0.25);
        }
    </style>
    """, unsafe_allow_html=True)

    # Holographic Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%);
                border: 1px solid rgba(0, 255, 255, 0.3);
                border-radius: 16px;
                padding: 32px;
                margin-bottom: 24px;
                backdrop-filter: blur(10px);
                box-shadow: 0 0 40px rgba(0, 255, 255, 0.1), inset 0 0 60px rgba(0, 255, 255, 0.05);
                position: relative;
                overflow: hidden;">
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent 0%, #00FFFF 50%, transparent 100%); opacity: 0.8;"></div>
        <h1 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 32px; margin: 0 0 8px 0; letter-spacing: 0.1em; text-shadow: 0 0 20px rgba(0, 255, 255, 0.5);">
            🔥 LEAD WARMING
        </h1>
        <p style="color: #C0C0C0; font-family: 'Rajdhani', sans-serif; font-size: 16px; margin: 0;">
            Warm up leads before cold outreach for +300% higher response rates
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Load saved leads
    all_leads = lead_manager.load_leads()

    # Calculate warming stats
    warming_queue = st.session_state.warming_queue
    warming_activities = st.session_state.warming_activities

    # Count leads by temperature
    cold_leads = [l for l in all_leads if l.get('temperature', 'cold') == 'cold']
    warm_leads = [l for l in all_leads if l.get('temperature') == 'warm']
    hot_leads = [l for l in all_leads if l.get('temperature') == 'hot']

    # Stats Row with Tooltips
    st.markdown("""
    <style>
        .warming-stat-wrapper {
            position: relative;
        }
        .warming-stat-card {
            position: relative;
            cursor: help;
        }
        .warming-tooltip {
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
            color: white;
            padding: 12px 16px;
            border-radius: 12px;
            font-size: 13px;
            line-height: 1.5;
            width: 260px;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s ease;
            z-index: 1000;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            pointer-events: none;
            margin-bottom: 10px;
        }
        .warming-tooltip::after {
            content: '';
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%);
            border: 8px solid transparent;
            border-top-color: #334155;
        }
        .warming-stat-card:hover .warming-tooltip {
            opacity: 1;
            visibility: visible;
            transform: translateX(-50%) translateY(-5px);
        }
        .warming-help {
            position: absolute;
            top: 8px;
            right: 8px;
            width: 18px;
            height: 18px;
            background: #E2E8F0;
            border-radius: 50%;
            font-size: 11px;
            color: #64748B;
            display: flex;
            align-items: center;
            justify-content: center;
        }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="warming-stat-card">
            <div class="warming-tooltip">
                <strong>❄️ Cold Leads</strong><br>
                New leads you haven't contacted or engaged with on LinkedIn yet. They need 7 days of "warming" before cold email outreach.
            </div>
            <div class="warming-help">?</div>
            <div style="font-size: 24px; margin-bottom: 8px;">❄️</div>
            <div class="warming-stat-value">{len(cold_leads)}</div>
            <div class="warming-stat-label">Cold Leads</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="warming-stat-card">
            <div class="warming-tooltip">
                <strong>🌡️ Warm Leads</strong><br>
                Leads in warming process (day 3-6). They've seen your profile, received likes/comments. Not ready for direct contact yet.
            </div>
            <div class="warming-help">?</div>
            <div style="font-size: 24px; margin-bottom: 8px;">🌡️</div>
            <div class="warming-stat-value">{len(warm_leads)}</div>
            <div class="warming-stat-label">Warm Leads</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="warming-stat-card">
            <div class="warming-tooltip">
                <strong>🔥 Hot Leads</strong><br>
                <strong>Ready to contact!</strong> Completed 7 days of warming. They already know you from LinkedIn. Send personalized email now for +300% response rate.
            </div>
            <div class="warming-help">?</div>
            <div style="font-size: 24px; margin-bottom: 8px;">🔥</div>
            <div class="warming-stat-value">{len(hot_leads)}</div>
            <div class="warming-stat-label">Hot Leads</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="warming-stat-card">
            <div class="warming-tooltip">
                <strong>✅ Activities Done</strong><br>
                Total warming actions completed: profile views, likes, comments, connection requests. More activity = warmer leads.
            </div>
            <div class="warming-help">?</div>
            <div style="font-size: 24px; margin-bottom: 8px;">✅</div>
            <div class="warming-stat-value">{len([a for a in warming_activities if a.get('completed')])}</div>
            <div class="warming-stat-label">Activities Done</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Warming Queue", "📅 Today's Actions", "📊 Pipeline", "💬 Engagement Tools", "⚙️ Settings"])

    with tab1:
        st.markdown("### Add Leads to Warming Queue")
        st.caption("Select leads to start the warming process before cold outreach")

        # Filter to show only cold leads not in queue
        leads_not_in_queue = [l for l in all_leads if l.get('hash') not in [q.get('hash') for q in warming_queue]]

        if leads_not_in_queue:
            # Select leads to add
            selected_leads = st.multiselect(
                "Select leads to warm up",
                options=range(len(leads_not_in_queue)),
                format_func=lambda x: f"{leads_not_in_queue[x].get('name', leads_not_in_queue[x].get('title', 'Unknown'))} - {leads_not_in_queue[x].get('company', leads_not_in_queue[x].get('business_name', 'N/A'))}",
                key="warming_lead_select"
            )

            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("➕ Add to Warming Queue", type="primary", use_container_width=True):
                    for idx in selected_leads:
                        lead = leads_not_in_queue[idx].copy()
                        lead['warming_started'] = datetime.now().isoformat()
                        lead['warming_day'] = 1
                        lead['temperature'] = 'cold'
                        lead['warming_actions'] = []
                        st.session_state.warming_queue.append(lead)
                    st.success(f"Added {len(selected_leads)} leads to warming queue!")
                    st.rerun()
        else:
            if not all_leads:
                st.info("No leads found. Go to 'Find Leads' to search for leads first.")
            else:
                st.info("All leads are already in the warming queue!")

        st.divider()

        # Show current warming queue
        st.markdown("### Current Warming Queue")

        if warming_queue:
            for i, lead in enumerate(warming_queue):
                temp = lead.get('temperature', 'cold')
                temp_class = f"temp-{temp}"
                temp_emoji = "❄️" if temp == "cold" else ("🌡️" if temp == "warm" else "🔥")
                warming_day = lead.get('warming_day', 1)
                lead_name = lead.get('name', lead.get('title', 'Unknown'))
                company = lead.get('company', lead.get('business_name', 'N/A'))
                linkedin = lead.get('linkedin', lead.get('url', ''))

                with st.expander(f"{temp_emoji} {lead_name} - Day {warming_day}/7", expanded=False):
                    col1, col2, col3 = st.columns([2, 2, 1])

                    with col1:
                        st.markdown(f"**Company:** {company}")
                        st.markdown(f"**Temperature:** <span class='{temp_class}'>{temp.upper()}</span>", unsafe_allow_html=True)
                        if linkedin:
                            st.markdown(f"**LinkedIn:** [{linkedin[:40]}...]({linkedin})")

                    with col2:
                        st.markdown("**Warming Progress:**")
                        progress = min(warming_day / 7, 1.0)
                        st.progress(progress)
                        st.caption(f"Day {warming_day} of 7 - {int(progress * 100)}% complete")

                    with col3:
                        if temp == "hot":
                            st.success("✅ Ready to contact!")
                            if st.button("📧 Send Email", key=f"email_{i}"):
                                st.session_state.nav_page = "CRM"
                                st.rerun()
                        else:
                            if st.button("⏭️ Next Action", key=f"next_{i}"):
                                st.session_state[f"show_actions_{i}"] = True
                                st.rerun()

                    # Show warming timeline
                    st.markdown("---")
                    st.markdown("**Warming Timeline:**")
                    actions = lead.get('warming_actions', [])

                    warming_steps = [
                        {"day": 1, "action": "View LinkedIn Profile", "icon": "👁️"},
                        {"day": 2, "action": "Like 2-3 Posts", "icon": "👍"},
                        {"day": 3, "action": "Comment on Post", "icon": "💬"},
                        {"day": 4, "action": "Send Connection Request", "icon": "🤝"},
                        {"day": 5, "action": "Engage with Content", "icon": "📝"},
                        {"day": 6, "action": "Share Their Content", "icon": "🔄"},
                        {"day": 7, "action": "Ready for Outreach!", "icon": "🚀"},
                    ]

                    for step in warming_steps:
                        completed = step['day'] < warming_day or any(a.get('day') == step['day'] for a in actions)
                        status = "✅" if completed else ("🔄" if step['day'] == warming_day else "⬜")
                        st.markdown(f"{status} **Day {step['day']}:** {step['icon']} {step['action']}")

                    # Action buttons
                    if warming_day <= 7:
                        st.markdown("---")
                        action_col1, action_col2 = st.columns(2)
                        with action_col1:
                            if st.button(f"✅ Mark Day {warming_day} Complete", key=f"complete_{i}", type="primary"):
                                # Update the lead
                                lead['warming_actions'].append({
                                    'day': warming_day,
                                    'completed_at': datetime.now().isoformat(),
                                    'action': warming_steps[warming_day-1]['action']
                                })
                                lead['warming_day'] = warming_day + 1

                                # Update temperature based on progress
                                if warming_day >= 7:
                                    lead['temperature'] = 'hot'
                                elif warming_day >= 4:
                                    lead['temperature'] = 'warm'

                                # Add to activities log
                                st.session_state.warming_activities.append({
                                    'lead_name': lead_name,
                                    'action': warming_steps[warming_day-1]['action'],
                                    'completed_at': datetime.now().isoformat(),
                                    'completed': True
                                })

                                st.success(f"Day {warming_day} marked complete!")
                                st.rerun()

                        with action_col2:
                            if st.button("🗑️ Remove from Queue", key=f"remove_{i}"):
                                st.session_state.warming_queue.pop(i)
                                st.rerun()
        else:
            st.info("No leads in warming queue. Add leads above to start warming them up!")

    with tab2:
        st.markdown("### Today's Warming Actions")
        st.caption("Actions scheduled for today based on your warming queue")

        if warming_queue:
            today_actions = []
            for lead in warming_queue:
                warming_day = lead.get('warming_day', 1)
                if warming_day <= 7:
                    warming_steps = [
                        {"day": 1, "action": "View LinkedIn Profile", "icon": "👁️", "description": "Visit their LinkedIn profile so they see you viewed them"},
                        {"day": 2, "action": "Like 2-3 Posts", "icon": "👍", "description": "Like their recent posts to increase visibility"},
                        {"day": 3, "action": "Comment on Post", "icon": "💬", "description": "Leave a thoughtful comment on a relevant post"},
                        {"day": 4, "action": "Send Connection Request", "icon": "🤝", "description": "Send a personalized connection request"},
                        {"day": 5, "action": "Engage with Content", "icon": "📝", "description": "Continue engaging with their content"},
                        {"day": 6, "action": "Share Their Content", "icon": "🔄", "description": "Share one of their posts with your network"},
                        {"day": 7, "action": "Ready for Outreach!", "icon": "🚀", "description": "Lead is warmed up - send your personalized email"},
                    ]
                    step = warming_steps[warming_day - 1]
                    today_actions.append({
                        'lead': lead,
                        'step': step,
                        'warming_day': warming_day
                    })

            if today_actions:
                for i, action in enumerate(today_actions):
                    lead = action['lead']
                    step = action['step']
                    lead_name = lead.get('name', lead.get('title', 'Unknown'))
                    company = lead.get('company', lead.get('business_name', 'N/A'))
                    linkedin = lead.get('linkedin', lead.get('url', ''))

                    st.markdown(f"""
                    <div class="warming-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <h4 style="margin: 0; color: #1E293B;">{step['icon']} {step['action']}</h4>
                                <p style="margin: 8px 0 0 0; color: #64748B;">{step['description']}</p>
                            </div>
                            <div style="text-align: right;">
                                <p style="margin: 0; font-weight: 600; color: #1E293B;">{lead_name}</p>
                                <p style="margin: 4px 0 0 0; color: #64748B; font-size: 13px;">{company}</p>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        if linkedin and 'linkedin' in linkedin.lower():
                            st.link_button("🔗 Open LinkedIn Profile", linkedin, use_container_width=True)
                        else:
                            st.caption("No LinkedIn URL available")
                    with col2:
                        if st.button("✅ Done", key=f"today_done_{i}", type="primary", use_container_width=True):
                            # Find and update the lead in warming queue
                            for j, q_lead in enumerate(st.session_state.warming_queue):
                                if q_lead.get('hash') == lead.get('hash'):
                                    q_lead['warming_actions'].append({
                                        'day': action['warming_day'],
                                        'completed_at': datetime.now().isoformat(),
                                        'action': step['action']
                                    })
                                    q_lead['warming_day'] = action['warming_day'] + 1
                                    if action['warming_day'] >= 7:
                                        q_lead['temperature'] = 'hot'
                                    elif action['warming_day'] >= 4:
                                        q_lead['temperature'] = 'warm'
                                    break

                            st.session_state.warming_activities.append({
                                'lead_name': lead_name,
                                'action': step['action'],
                                'completed_at': datetime.now().isoformat(),
                                'completed': True
                            })
                            st.success(f"Marked '{step['action']}' as complete!")
                            st.rerun()
                    with col3:
                        if st.button("⏭️ Skip", key=f"today_skip_{i}", use_container_width=True):
                            for j, q_lead in enumerate(st.session_state.warming_queue):
                                if q_lead.get('hash') == lead.get('hash'):
                                    q_lead['warming_day'] = action['warming_day'] + 1
                                    break
                            st.rerun()

                    st.markdown("---")
            else:
                st.success("All warming actions for today are complete!")
        else:
            st.info("No leads in warming queue. Add leads from the 'Warming Queue' tab to see today's actions.")

    with tab3:
        st.markdown("### Warming Pipeline")
        st.caption("Visual overview of leads at each warming stage")

        # Pipeline columns
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #60A5FA 0%, #3B82F6 100%); padding: 16px; border-radius: 12px; text-align: center; color: white; margin-bottom: 16px;">
                <div style="font-size: 24px;">❄️</div>
                <div style="font-size: 20px; font-weight: 700;">COLD</div>
                <div style="font-size: 13px; opacity: 0.9;">Day 1-2</div>
            </div>
            """, unsafe_allow_html=True)

            cold_in_queue = [l for l in warming_queue if l.get('warming_day', 1) <= 2]
            for lead in cold_in_queue:
                lead_name = (lead.get('name') or lead.get('title') or 'Unknown')[:20]
                st.markdown(f"""
                <div style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                    <div style="font-weight: 600; font-size: 13px; color: #1E293B;">{lead_name}</div>
                    <div style="font-size: 11px; color: #64748B;">Day {lead.get('warming_day', 1)}/7</div>
                </div>
                """, unsafe_allow_html=True)

            if not cold_in_queue:
                st.caption("No leads at this stage")

        with col2:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #FCD34D 0%, #FBBF24 100%); padding: 16px; border-radius: 12px; text-align: center; color: #1E293B; margin-bottom: 16px;">
                <div style="font-size: 24px;">🌡️</div>
                <div style="font-size: 20px; font-weight: 700;">WARMING</div>
                <div style="font-size: 13px; opacity: 0.8;">Day 3-4</div>
            </div>
            """, unsafe_allow_html=True)

            warming_in_queue = [l for l in warming_queue if 3 <= l.get('warming_day', 1) <= 4]
            for lead in warming_in_queue:
                lead_name = (lead.get('name') or lead.get('title') or 'Unknown')[:20]
                st.markdown(f"""
                <div style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                    <div style="font-weight: 600; font-size: 13px; color: #1E293B;">{lead_name}</div>
                    <div style="font-size: 11px; color: #64748B;">Day {lead.get('warming_day', 1)}/7</div>
                </div>
                """, unsafe_allow_html=True)

            if not warming_in_queue:
                st.caption("No leads at this stage")

        with col3:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #FB923C 0%, #F97316 100%); padding: 16px; border-radius: 12px; text-align: center; color: white; margin-bottom: 16px;">
                <div style="font-size: 24px;">🔥</div>
                <div style="font-size: 20px; font-weight: 700;">WARM</div>
                <div style="font-size: 13px; opacity: 0.9;">Day 5-6</div>
            </div>
            """, unsafe_allow_html=True)

            warm_in_queue = [l for l in warming_queue if 5 <= l.get('warming_day', 1) <= 6]
            for lead in warm_in_queue:
                lead_name = (lead.get('name') or lead.get('title') or 'Unknown')[:20]
                st.markdown(f"""
                <div style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                    <div style="font-weight: 600; font-size: 13px; color: #1E293B;">{lead_name}</div>
                    <div style="font-size: 11px; color: #64748B;">Day {lead.get('warming_day', 1)}/7</div>
                </div>
                """, unsafe_allow_html=True)

            if not warm_in_queue:
                st.caption("No leads at this stage")

        with col4:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%); padding: 16px; border-radius: 12px; text-align: center; color: white; margin-bottom: 16px;">
                <div style="font-size: 24px;">🚀</div>
                <div style="font-size: 20px; font-weight: 700;">HOT</div>
                <div style="font-size: 13px; opacity: 0.9;">Ready!</div>
            </div>
            """, unsafe_allow_html=True)

            hot_in_queue = [l for l in warming_queue if l.get('warming_day', 1) >= 7]
            for lead in hot_in_queue:
                lead_name = (lead.get('name') or lead.get('title') or 'Unknown')[:20]
                st.markdown(f"""
                <div style="background: #FEF2F2; border: 2px solid #EF4444; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                    <div style="font-weight: 600; font-size: 13px; color: #1E293B;">{lead_name}</div>
                    <div style="font-size: 11px; color: #10B981; font-weight: 600;">Ready to contact!</div>
                </div>
                """, unsafe_allow_html=True)

            if not hot_in_queue:
                st.caption("No leads ready yet")

    with tab4:
        st.markdown("""
        <div style="margin-bottom: 20px;">
            <h3 style="margin: 0; color: #1E293B;">💬 Engagement Tools</h3>
            <p style="margin: 8px 0 0 0; color: #64748B; font-size: 14px;">Templates and tools to help you warm up leads effectively</p>
        </div>
        """, unsafe_allow_html=True)

        # Modern template card styles
        st.markdown("""
        <style>
            .template-card {
                background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 12px;
                transition: all 0.2s ease;
            }
            .template-card:hover {
                border-color: #3B82F6;
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
            }
            .template-header {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 12px;
            }
            .template-badge {
                background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
                color: white;
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
            }
            .template-text {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px 16px;
                font-family: 'Inter', sans-serif;
                font-size: 13px;
                line-height: 1.6;
                color: #334155;
            }
            .template-text strong {
                color: #3B82F6;
            }
        </style>
        """, unsafe_allow_html=True)

        tool_col1, tool_col2 = st.columns(2)

        with tool_col1:
            st.markdown("""
            <div style="margin-bottom: 16px;">
                <h4 style="margin: 0; color: #1E293B; font-size: 16px;">💬 Comment Templates</h4>
                <p style="margin: 4px 0 0 0; color: #64748B; font-size: 12px;">Copy these templates for LinkedIn comments</p>
            </div>
            """, unsafe_allow_html=True)

            comment_templates = [
                {"type": "Agreement", "icon": "👍", "color": "#10B981", "template": "Great insight! I've seen this in my work too - <strong>[specific example]</strong>. Thanks for sharing."},
                {"type": "Question", "icon": "❓", "color": "#F59E0B", "template": "Interesting perspective. Have you found that <strong>[related question]</strong>? I'd love to hear your thoughts."},
                {"type": "Value Add", "icon": "💡", "color": "#3B82F6", "template": "This resonates with me. I'd add that <strong>[additional point]</strong> can also help. What do you think?"},
                {"type": "Industry", "icon": "🏢", "color": "#8B5CF6", "template": "As someone in <strong>[industry]</strong>, I appreciate this take. We're seeing <strong>[relevant trend]</strong> as well."},
            ]

            for i, template in enumerate(comment_templates):
                st.markdown(f"""
                <div class="template-card">
                    <div class="template-header">
                        <span style="font-size: 18px;">{template['icon']}</span>
                        <span style="background: {template['color']}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">{template['type']}</span>
                    </div>
                    <div class="template-text">{template['template']}</div>
                </div>
                """, unsafe_allow_html=True)

        with tool_col2:
            st.markdown("""
            <div style="margin-bottom: 16px;">
                <h4 style="margin: 0; color: #1E293B; font-size: 16px;">🤝 Connection Request Templates</h4>
                <p style="margin: 4px 0 0 0; color: #64748B; font-size: 12px;">Personalized connection request messages</p>
            </div>
            """, unsafe_allow_html=True)

            connection_templates = [
                {"type": "Mutual Interest", "icon": "🎯", "color": "#EF4444", "template": "Hi <strong>[Name]</strong>, I noticed we're both interested in <strong>[topic]</strong>. I'd love to connect and exchange insights. Looking forward to learning from your experience in <strong>[industry]</strong>."},
                {"type": "Content Fan", "icon": "⭐", "color": "#F59E0B", "template": "Hi <strong>[Name]</strong>, I've been following your posts about <strong>[topic]</strong> and find them really valuable. Would love to connect and stay updated on your insights."},
                {"type": "Industry Peer", "icon": "🏆", "color": "#10B981", "template": "Hi <strong>[Name]</strong>, As a fellow professional in <strong>[industry]</strong>, I'd love to connect. Your work at <strong>[Company]</strong> looks impressive. Let's stay in touch!"},
            ]

            for template in connection_templates:
                st.markdown(f"""
                <div class="template-card">
                    <div class="template-header">
                        <span style="font-size: 18px;">{template['icon']}</span>
                        <span style="background: {template['color']}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">{template['type']}</span>
                    </div>
                    <div class="template-text">{template['template']}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

        # Email template with modern design
        st.markdown("""
        <div style="margin-bottom: 16px;">
            <h4 style="margin: 0; color: #1E293B; font-size: 16px;">📧 Follow-up Email Template (After Warming)</h4>
            <p style="margin: 4px 0 0 0; color: #64748B; font-size: 12px;">Use this after completing the 7-day warming process</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background: linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 100%); border: 1px solid #BAE6FD; border-radius: 12px; padding: 20px;">
            <div style="background: white; border-radius: 8px; padding: 20px; font-family: 'Georgia', serif;">
                <div style="border-bottom: 1px solid #E2E8F0; padding-bottom: 12px; margin-bottom: 16px;">
                    <span style="background: #3B82F6; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 600;">SUBJECT</span>
                    <span style="margin-left: 12px; color: #1E293B; font-weight: 500;">Following up on our LinkedIn connection</span>
                </div>
                <div style="color: #334155; font-size: 14px; line-height: 1.8;">
                    Hi <strong style="color: #3B82F6;">[Name]</strong>,<br><br>

                    I hope this message finds you well! We connected on LinkedIn recently, and I've really enjoyed your insights on <strong style="color: #3B82F6;">[topic they posted about]</strong>.<br><br>

                    I noticed that <strong style="color: #3B82F6;">[Company]</strong> is in the <strong style="color: #3B82F6;">[industry]</strong> space, and I wanted to reach out because we help businesses like yours <strong style="color: #3B82F6;">[value proposition]</strong>.<br><br>

                    <span style="background: #FEF3C7; padding: 2px 6px; border-radius: 4px;">[Specific observation about their company/role that shows you've done your research]</span><br><br>

                    Would you be open to a quick 15-minute call to explore if there might be a fit? I'd love to learn more about your current priorities and see if we can help.<br><br>

                    Best regards,<br>
                    <strong style="color: #3B82F6;">[Your Name]</strong><br><br>

                    <em style="color: #64748B;">P.S. [Reference something specific from their recent LinkedIn activity]</em>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with tab5:
        st.markdown("### Warming Settings")
        st.caption("Configure your lead warming preferences")

        st.markdown("#### Warming Schedule")

        col1, col2 = st.columns(2)

        with col1:
            warming_duration = st.slider(
                "Warming Duration (days)",
                min_value=3,
                max_value=14,
                value=7,
                help="Number of days to warm a lead before outreach"
            )

            daily_actions = st.number_input(
                "Max Actions Per Day",
                min_value=1,
                max_value=50,
                value=20,
                help="Maximum number of warming actions per day"
            )

        with col2:
            st.markdown("#### Default Warming Sequence")

            sequence_options = st.multiselect(
                "Actions to include",
                options=[
                    "View LinkedIn Profile",
                    "Like Posts",
                    "Comment on Posts",
                    "Send Connection Request",
                    "Share Content",
                    "Send InMail",
                    "Follow Company Page"
                ],
                default=[
                    "View LinkedIn Profile",
                    "Like Posts",
                    "Comment on Posts",
                    "Send Connection Request",
                    "Share Content"
                ]
            )

        st.divider()

        st.markdown("#### Activity Log")

        if warming_activities:
            activity_df = pd.DataFrame(warming_activities)
            st.dataframe(
                activity_df,
                column_config={
                    "lead_name": st.column_config.TextColumn("Lead"),
                    "action": st.column_config.TextColumn("Action"),
                    "completed_at": st.column_config.DatetimeColumn("Completed", format="DD/MM/YY HH:mm"),
                    "completed": st.column_config.CheckboxColumn("Done")
                },
                use_container_width=True,
                hide_index=True
            )

            if st.button("🗑️ Clear Activity Log"):
                st.session_state.warming_activities = []
                st.success("Activity log cleared!")
                st.rerun()
        else:
            st.info("No warming activities recorded yet.")

        st.divider()

        # Reset button
        st.markdown("#### Danger Zone")
        if st.button("🗑️ Clear All Warming Data", type="secondary"):
            st.session_state.warming_queue = []
            st.session_state.warming_activities = []
            st.session_state.warming_schedule = {}
            st.success("All warming data cleared!")
            st.rerun()


def show_job_changes():
    """Job Change Monitor - Detect leadership changes for sales opportunities."""

    # Initialize session state for job changes
    if 'job_changes' not in st.session_state:
        st.session_state.job_changes = []
    if 'job_change_monitor' not in st.session_state:
        st.session_state.job_change_monitor = JobChangeMonitor()

    # Holographic CSS for Job Changes
    st.markdown("""
    <style>
        /* Opportunity Level Badges */
        .opp-gold {
            background: linear-gradient(135deg, rgba(255, 215, 0, 0.3) 0%, rgba(255, 184, 0, 0.2) 100%);
            border: 1px solid rgba(255, 215, 0, 0.6);
            color: #FFD700;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
            animation: gold-pulse 2s ease-in-out infinite;
        }
        @keyframes gold-pulse {
            0%, 100% { box-shadow: 0 0 5px rgba(255, 215, 0, 0.3); }
            50% { box-shadow: 0 0 20px rgba(255, 215, 0, 0.6); }
        }
        .opp-silver {
            background: linear-gradient(135deg, rgba(192, 192, 192, 0.3) 0%, rgba(169, 169, 169, 0.2) 100%);
            border: 1px solid rgba(192, 192, 192, 0.5);
            color: #C0C0C0;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-shadow: 0 0 10px rgba(192, 192, 192, 0.4);
        }
        .opp-bronze {
            background: linear-gradient(135deg, rgba(205, 127, 50, 0.3) 0%, rgba(180, 100, 30, 0.2) 100%);
            border: 1px solid rgba(205, 127, 50, 0.4);
            color: #CD7F32;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }

        /* Job Change Card */
        .job-change-card {
            background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%);
            border: 1px solid rgba(0, 255, 255, 0.2);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 16px;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        .job-change-card:hover {
            box-shadow: 0 0 30px rgba(0, 255, 255, 0.15);
            transform: translateY(-2px);
            border-color: rgba(0, 255, 255, 0.4);
        }
        .job-change-card.gold {
            border-color: rgba(255, 215, 0, 0.4);
        }
        .job-change-card.gold:hover {
            box-shadow: 0 0 30px rgba(255, 215, 0, 0.2);
        }

        /* Days Badge */
        .days-badge {
            background: rgba(0, 255, 255, 0.15);
            border: 1px solid rgba(0, 255, 255, 0.3);
            color: #00FFFF;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }
        .days-badge.urgent {
            background: rgba(255, 107, 107, 0.15);
            border-color: rgba(255, 107, 107, 0.4);
            color: #FF6B6B;
            animation: urgent-pulse 1.5s ease-in-out infinite;
        }
        @keyframes urgent-pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }

        /* Score Display */
        .opportunity-score {
            font-family: 'Orbitron', sans-serif;
            font-size: 24px;
            font-weight: 700;
            color: #00FFFF;
            text-shadow: 0 0 15px rgba(0, 255, 255, 0.5);
        }

        /* Industry Select */
        .industry-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 12px;
            margin: 16px 0;
        }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(45, 55, 72, 0.6) 0%, rgba(28, 28, 46, 0.8) 100%);
                border: 1px solid rgba(0, 255, 255, 0.3);
                border-radius: 16px;
                padding: 32px;
                margin-bottom: 24px;
                backdrop-filter: blur(10px);
                box-shadow: 0 0 40px rgba(0, 255, 255, 0.1), inset 0 0 60px rgba(0, 255, 255, 0.05);
                position: relative;
                overflow: hidden;">
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent 0%, #00FFFF 50%, transparent 100%); opacity: 0.8;"></div>
        <h1 style="color: #00FFFF; font-family: 'Orbitron', sans-serif; font-size: 32px; margin: 0 0 8px 0; letter-spacing: 0.1em; text-shadow: 0 0 20px rgba(0, 255, 255, 0.5);">
            🚀 JOB CHANGES
        </h1>
        <p style="color: #C0C0C0; font-family: 'Rajdhani', sans-serif; font-size: 16px; margin: 0;">
            Detect when decision-makers change jobs = 3x higher conversion window
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Check if Apollo is configured
    monitor = st.session_state.job_change_monitor
    api_configured = monitor.is_configured()

    if not api_configured:
        st.warning("⚠️ Apollo API key not configured. Go to Settings to add your APOLLO_API_KEY.")

    # Search Section
    st.markdown("### 🔍 Find New Leaders")

    col1, col2 = st.columns(2)

    with col1:
        # Industry selection - Phase 1 industries
        phase1_industries = {
            "🔧 HVAC": "hvac heating cooling",
            "🚿 Plumbing": "plumbing plumber",
            "🏠 Roofing": "roofing contractor",
            "⚡ Electrical": "electrical electrician contractor",
            "🦷 Dental": "dental practice dentist",
            "🏡 Real Estate": "real estate agency broker",
            "⚖️ Legal": "law firm attorney legal",
            "🏥 Medical": "medical practice clinic doctor"
        }

        selected_industry = st.selectbox(
            "Select Industry",
            options=list(phase1_industries.keys()),
            index=0
        )

        industry_query = phase1_industries[selected_industry]

    with col2:
        # Title filters
        title_options = st.multiselect(
            "Target Titles",
            options=["Owner", "Founder", "CEO", "President", "Director", "Manager", "VP", "Partner"],
            default=["Owner", "Director", "Manager"]
        )

        max_days = st.slider(
            "Max Days in New Role",
            min_value=30,
            max_value=180,
            value=90,
            step=30,
            help="First 90 days = highest opportunity window"
        )

    col3, col4 = st.columns(2)

    with col3:
        location = st.text_input(
            "Location (optional)",
            value="United States",
            placeholder="e.g., California, New York"
        )

    with col4:
        company_size = st.select_slider(
            "Company Size (employees)",
            options=["1-10", "10-50", "50-200", "200-500"],
            value="10-50"
        )
        size_map = {"1-10": (1, 10), "10-50": (10, 50), "50-200": (50, 200), "200-500": (200, 500)}
        min_emp, max_emp = size_map[company_size]

    # Search button
    search_col1, search_col2, search_col3 = st.columns([1, 2, 1])
    with search_col2:
        search_clicked = st.button(
            "🔍 Find Job Changes",
            use_container_width=True,
            disabled=not api_configured,
            type="primary"
        )

    if search_clicked and api_configured:
        with st.spinner(f"Searching for new leaders in {selected_industry}..."):
            try:
                changes = monitor.find_new_leaders_in_industry(
                    industry=industry_query,
                    titles=[t.lower() for t in title_options],
                    max_days_in_role=max_days,
                    location=location if location else None,
                    company_size_min=min_emp,
                    company_size_max=max_emp,
                    limit=50
                )
                st.session_state.job_changes = changes

                if changes:
                    st.success(f"✅ Found {len(changes)} job changes!")
                else:
                    st.info("No job changes found with current filters. Try adjusting the criteria.")

            except Exception as e:
                st.error(f"Error searching: {str(e)}")

    # Display Results
    if st.session_state.job_changes:
        changes = st.session_state.job_changes

        # Summary stats
        st.markdown("### 📊 Opportunities Found")

        gold = [c for c in changes if c.opportunity_level == OpportunityLevel.GOLD]
        silver = [c for c in changes if c.opportunity_level == OpportunityLevel.SILVER]
        bronze = [c for c in changes if c.opportunity_level == OpportunityLevel.BRONZE]
        urgent = [c for c in changes if c.days_in_role <= 30]

        stat_cols = st.columns(4)
        with stat_cols[0]:
            st.markdown(f"""
            <div style="background: rgba(255, 215, 0, 0.1); border: 1px solid rgba(255, 215, 0, 0.3);
                        border-radius: 12px; padding: 16px; text-align: center;">
                <div style="font-size: 28px; font-weight: 700; color: #FFD700; font-family: 'Orbitron';">
                    {len(gold)}
                </div>
                <div style="font-size: 12px; color: #C0C0C0;">🥇 GOLD</div>
            </div>
            """, unsafe_allow_html=True)

        with stat_cols[1]:
            st.markdown(f"""
            <div style="background: rgba(192, 192, 192, 0.1); border: 1px solid rgba(192, 192, 192, 0.3);
                        border-radius: 12px; padding: 16px; text-align: center;">
                <div style="font-size: 28px; font-weight: 700; color: #C0C0C0; font-family: 'Orbitron';">
                    {len(silver)}
                </div>
                <div style="font-size: 12px; color: #C0C0C0;">🥈 SILVER</div>
            </div>
            """, unsafe_allow_html=True)

        with stat_cols[2]:
            st.markdown(f"""
            <div style="background: rgba(205, 127, 50, 0.1); border: 1px solid rgba(205, 127, 50, 0.3);
                        border-radius: 12px; padding: 16px; text-align: center;">
                <div style="font-size: 28px; font-weight: 700; color: #CD7F32; font-family: 'Orbitron';">
                    {len(bronze)}
                </div>
                <div style="font-size: 12px; color: #C0C0C0;">🥉 BRONZE</div>
            </div>
            """, unsafe_allow_html=True)

        with stat_cols[3]:
            st.markdown(f"""
            <div style="background: rgba(255, 107, 107, 0.1); border: 1px solid rgba(255, 107, 107, 0.3);
                        border-radius: 12px; padding: 16px; text-align: center;">
                <div style="font-size: 28px; font-weight: 700; color: #FF6B6B; font-family: 'Orbitron';">
                    {len(urgent)}
                </div>
                <div style="font-size: 12px; color: #C0C0C0;">🔥 URGENT (&lt;30d)</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Filter tabs
        filter_tab = st.radio(
            "Filter by level",
            ["All", "🥇 Gold Only", "🥈 Silver Only", "🔥 Urgent (<30 days)"],
            horizontal=True
        )

        if filter_tab == "🥇 Gold Only":
            display_changes = gold
        elif filter_tab == "🥈 Silver Only":
            display_changes = silver
        elif filter_tab == "🔥 Urgent (<30 days)":
            display_changes = urgent
        else:
            display_changes = changes

        # Display cards
        for change in display_changes:
            level_class = change.opportunity_level.value
            level_badge = {
                "gold": '<span class="opp-gold">🥇 GOLD</span>',
                "silver": '<span class="opp-silver">🥈 SILVER</span>',
                "bronze": '<span class="opp-bronze">🥉 BRONZE</span>'
            }.get(level_class, '')

            days_class = "urgent" if change.days_in_role <= 30 else ""

            st.markdown(f"""
            <div class="job-change-card {level_class}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                    <div>
                        <h3 style="color: #FFFFFF; margin: 0 0 4px 0; font-size: 18px;">
                            {change.full_name or 'Unknown'}
                        </h3>
                        <p style="color: #00FFFF; margin: 0; font-size: 14px; font-weight: 600;">
                            {change.current_title or 'N/A'} @ {change.current_company or 'N/A'}
                        </p>
                    </div>
                    <div style="text-align: right;">
                        {level_badge}
                        <div style="margin-top: 8px;">
                            <span class="days-badge {days_class}">{change.days_in_role} days in role</span>
                        </div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px;">
                    <div style="background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px;">
                        <span style="color: #708090; font-size: 11px;">PREVIOUS</span>
                        <p style="color: #C0C0C0; margin: 4px 0 0 0; font-size: 13px;">
                            {change.previous_title or 'N/A'}<br/>
                            <span style="color: #708090;">{change.previous_company or 'N/A'}</span>
                        </p>
                    </div>
                    <div style="background: rgba(0,255,255,0.05); padding: 10px; border-radius: 8px; border: 1px solid rgba(0,255,255,0.1);">
                        <span style="color: #00FFFF; font-size: 11px;">CURRENT</span>
                        <p style="color: #FFFFFF; margin: 4px 0 0 0; font-size: 13px;">
                            {change.current_title or 'N/A'}<br/>
                            <span style="color: #00FFFF;">{change.current_company or 'N/A'}</span>
                        </p>
                    </div>
                </div>
                <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.1);">
                    <span style="color: #708090; font-size: 12px;">💡 {change.opportunity_reason}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Action buttons
            btn_cols = st.columns([1, 1, 1, 3])
            with btn_cols[0]:
                if change.linkedin_url:
                    st.link_button("🔗 LinkedIn", change.linkedin_url, use_container_width=True)
            with btn_cols[1]:
                if st.button("📥 Add to Leads", key=f"add_{change.person_id}", use_container_width=True):
                    lead = change.to_lead()
                    st.session_state.filtered_leads.append(lead)
                    st.success(f"Added {change.full_name} to leads!")
            with btn_cols[2]:
                if change.email:
                    st.button(f"📧 {change.email[:20]}...", key=f"email_{change.person_id}", use_container_width=True)

            st.markdown("<br/>", unsafe_allow_html=True)

        # Export section
        st.markdown("---")
        st.markdown("### 📤 Export Options")

        export_cols = st.columns(3)
        with export_cols[0]:
            if st.button("📥 Add All to Leads", use_container_width=True):
                added = 0
                for change in display_changes:
                    lead = change.to_lead()
                    if lead.id not in [l.id for l in st.session_state.filtered_leads]:
                        st.session_state.filtered_leads.append(lead)
                        added += 1
                st.success(f"Added {added} leads to your pipeline!")

        with export_cols[1]:
            if st.button("📋 Export to CSV", use_container_width=True):
                # Create DataFrame for export
                export_data = []
                for c in display_changes:
                    export_data.append({
                        "Name": c.full_name,
                        "Current Title": c.current_title,
                        "Current Company": c.current_company,
                        "Previous Title": c.previous_title,
                        "Previous Company": c.previous_company,
                        "Days in Role": c.days_in_role,
                        "Opportunity Level": c.opportunity_level.value.upper(),
                        "Score": c.opportunity_score,
                        "Email": c.email or "",
                        "LinkedIn": c.linkedin_url or "",
                        "Reason": c.opportunity_reason
                    })
                df = pd.DataFrame(export_data)
                csv = df.to_csv(index=False)
                st.download_button(
                    "⬇️ Download CSV",
                    csv,
                    "job_changes.csv",
                    "text/csv",
                    use_container_width=True
                )

        with export_cols[2]:
            if st.button("🔄 Send to HubSpot", use_container_width=True):
                st.info("Coming soon: Direct HubSpot integration")

    else:
        # Empty state
        st.markdown("""
        <div style="text-align: center; padding: 60px 20px; background: rgba(45, 55, 72, 0.3);
                    border: 1px dashed rgba(0, 255, 255, 0.3); border-radius: 16px; margin-top: 24px;">
            <div style="font-size: 48px; margin-bottom: 16px;">🔍</div>
            <h3 style="color: #C0C0C0; margin-bottom: 8px;">No Job Changes Found Yet</h3>
            <p style="color: #708090;">Select an industry and search to find new decision-makers</p>
        </div>
        """, unsafe_allow_html=True)

    # Info section
    with st.expander("ℹ️ How Job Change Detection Works"):
        st.markdown("""
        ### Why Job Changes Matter

        When someone takes a new leadership role, they're in a **90-day opportunity window**:

        | Timeframe | Opportunity Level | Why |
        |-----------|------------------|-----|
        | **0-30 days** | 🔥 Critical | Evaluating all vendors, building processes |
        | **31-60 days** | 🟡 High | Implementing changes, open to new solutions |
        | **61-90 days** | 🟢 Medium | Still flexible, establishing relationships |
        | **90+ days** | ⚪ Low | Settled into role, harder to change |

        ### Opportunity Levels

        - **🥇 GOLD**: C-level, VP, Owner in first 30 days = Contact immediately
        - **🥈 SILVER**: Director/Manager or 31-60 days = Contact this week
        - **🥉 BRONZE**: Other changes = Add to nurture sequence

        ### Best Practices

        1. **Personalize outreach** - Reference their new role
        2. **Offer value first** - Share relevant industry insights
        3. **Time it right** - Don't wait more than a week for GOLD opportunities
        """)


def main():
    render_sidebar()

    # Render error notifications (floating panel)
    render_error_notifications()

    # Render floating AI assistant on all pages
    render_floating_assistant()

    page = st.session_state.nav_page

    if page == "Dashboard":
        show_dashboard()
    elif page == "Find Leads":
        show_search()
    elif page == "My Leads":
        show_leads()
    elif page == "Lead Warming":
        show_lead_warming()
    elif page == "Job Changes":
        show_job_changes()
    elif page == "CRM":
        show_crm()
    elif page == "Analytics":
        show_analytics()
    elif page == "AI Assistant":
        show_ai_assistant()
    elif page == "Settings":
        show_config()


if __name__ == "__main__":
    main()
