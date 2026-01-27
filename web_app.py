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
from src.utils.models import Lead, LeadSource
from src.scrapers import RedditScraper, HackerNewsScraper, GoogleScraper, ProductHuntScraper
from src.filters import AILeadFilter
from src.crm import HubSpotCRM, LeadStage

# Page config
st.set_page_config(
    page_title="LeadGen Pro",
    page_icon="◇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# PREMIUM CSS - Clean & Modern Design
# ============================================
st.markdown("""
<style>
    /* ========== FONTS ========== */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    /* ========== CSS VARIABLES ========== */
    :root {
        --blue-50: #EFF6FF;
        --blue-100: #DBEAFE;
        --blue-500: #3B82F6;
        --blue-600: #2563EB;
        --blue-700: #1D4ED8;
        --blue-900: #1E3A8A;

        --orange-50: #FFF7ED;
        --orange-100: #FFEDD5;
        --orange-500: #F97316;
        --orange-600: #EA580C;

        --slate-50: #F8FAFC;
        --slate-100: #F1F5F9;
        --slate-200: #E2E8F0;
        --slate-300: #CBD5E1;
        --slate-400: #94A3B8;
        --slate-500: #64748B;
        --slate-600: #475569;
        --slate-700: #334155;
        --slate-800: #1E293B;
        --slate-900: #0F172A;

        --green-50: #F0FDF4;
        --green-500: #22C55E;
        --green-600: #16A34A;

        --red-50: #FEF2F2;
        --red-500: #EF4444;

        --white: #FFFFFF;
        --radius: 16px;
        --radius-sm: 12px;
        --radius-xs: 8px;
    }

    /* ========== GLOBAL ========== */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        -webkit-font-smoothing: antialiased;
    }

    .main .block-container {
        padding: 2rem 3rem 4rem 3rem !important;
        max-width: 1200px !important;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }

    p, span, div, label {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* Hide Streamlit elements */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}

    /* ========== SIDEBAR ========== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--slate-900) 0%, var(--slate-800) 100%) !important;
        padding: 0 !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding: 0 !important;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: var(--slate-300) !important;
    }

    /* Sidebar Radio Navigation */
    [data-testid="stSidebar"] .stRadio > label {
        display: none !important;
    }

    [data-testid="stSidebar"] .stRadio > div {
        gap: 4px !important;
        padding: 0 16px !important;
    }

    [data-testid="stSidebar"] .stRadio > div > label {
        background: transparent !important;
        border-radius: var(--radius-sm) !important;
        padding: 14px 16px !important;
        margin: 0 !important;
        color: var(--slate-400) !important;
        font-weight: 500 !important;
        font-size: 15px !important;
        transition: all 0.15s ease !important;
        border: none !important;
    }

    [data-testid="stSidebar"] .stRadio > div > label:hover {
        background: rgba(255,255,255,0.05) !important;
        color: var(--white) !important;
    }

    [data-testid="stSidebar"] .stRadio > div > label[data-checked="true"] {
        background: rgba(59, 130, 246, 0.15) !important;
        color: var(--white) !important;
        font-weight: 600 !important;
    }

    /* ========== LOGO SECTION ========== */
    .logo-section {
        padding: 28px 24px 20px 24px;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        margin-bottom: 8px;
    }

    .logo-container {
        display: flex;
        align-items: center;
        gap: 14px;
    }

    .logo-icon {
        width: 44px;
        height: 44px;
        background: linear-gradient(135deg, var(--blue-600) 0%, var(--blue-500) 100%);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }

    .logo-icon svg {
        width: 24px;
        height: 24px;
    }

    .logo-text {
        flex: 1;
    }

    .logo-title {
        color: var(--white);
        font-size: 20px;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0;
        line-height: 1.2;
    }

    .logo-subtitle {
        color: var(--slate-500);
        font-size: 12px;
        font-weight: 500;
        margin: 2px 0 0 0;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* ========== USER CARD ========== */
    .user-card {
        margin: 16px;
        padding: 16px;
        background: rgba(255,255,255,0.03);
        border-radius: var(--radius-sm);
        border: 1px solid rgba(255,255,255,0.06);
    }

    .user-info {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .user-avatar {
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, var(--orange-500) 0%, var(--orange-600) 100%);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        font-weight: 700;
        color: white;
    }

    .user-details h4 {
        color: var(--white);
        font-size: 14px;
        font-weight: 600;
        margin: 0 0 2px 0;
    }

    .user-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: linear-gradient(135deg, var(--green-500) 0%, var(--green-600) 100%);
        color: white;
        font-size: 10px;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 20px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ========== SIDEBAR FOOTER ========== */
    .sidebar-footer {
        padding: 20px 24px;
        border-top: 1px solid rgba(255,255,255,0.06);
        margin-top: auto;
    }

    .sidebar-stats {
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--slate-500);
        font-size: 13px;
    }

    .status-dot {
        width: 8px;
        height: 8px;
        background: var(--green-500);
        border-radius: 50%;
        box-shadow: 0 0 8px var(--green-500);
    }

    /* ========== PAGE HEADER ========== */
    .page-header {
        margin-bottom: 32px;
    }

    .page-header h1 {
        color: var(--slate-900);
        font-size: 32px;
        font-weight: 800;
        margin: 0 0 8px 0;
        letter-spacing: -0.03em;
    }

    .page-header p {
        color: var(--slate-500);
        font-size: 16px;
        margin: 0;
        font-weight: 400;
    }

    /* ========== METRIC CARDS ========== */
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 20px;
        margin-bottom: 40px;
    }

    @media (max-width: 1000px) {
        .metrics-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }

    .metric-card {
        background: var(--white);
        border-radius: var(--radius);
        padding: 24px;
        border: 1px solid var(--slate-200);
        transition: all 0.2s ease;
        position: relative;
        overflow: hidden;
    }

    .metric-card:hover {
        border-color: var(--blue-500);
        box-shadow: 0 8px 24px rgba(59, 130, 246, 0.1);
        transform: translateY(-2px);
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--blue-500) 0%, var(--orange-500) 100%);
    }

    .metric-icon {
        width: 48px;
        height: 48px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 16px;
        font-size: 22px;
    }

    .metric-icon.blue { background: var(--blue-50); }
    .metric-icon.orange { background: var(--orange-50); }
    .metric-icon.green { background: var(--green-50); }

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

    .metric-tag {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        margin-top: 12px;
        padding: 4px 10px;
        background: var(--green-50);
        color: var(--green-600);
        font-size: 12px;
        font-weight: 600;
        border-radius: 20px;
    }

    /* ========== SECTION ========== */
    .section {
        margin-bottom: 40px;
    }

    .section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 20px;
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
    }

    .section-badge {
        background: var(--blue-50);
        color: var(--blue-600);
        font-size: 12px;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 20px;
    }

    /* ========== FEATURE CARDS ========== */
    .features-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
    }

    @media (max-width: 900px) {
        .features-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }

    .feature-card {
        background: var(--white);
        border: 1px solid var(--slate-200);
        border-radius: var(--radius);
        padding: 24px;
        transition: all 0.2s ease;
    }

    .feature-card:hover {
        border-color: var(--blue-300);
        box-shadow: 0 4px 16px rgba(0,0,0,0.06);
    }

    .feature-icon {
        width: 52px;
        height: 52px;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 16px;
        font-size: 26px;
    }

    .feature-icon.reddit { background: #FF45001A; }
    .feature-icon.hn { background: #FF66001A; }
    .feature-icon.google { background: #4285F41A; }
    .feature-icon.ph { background: #DA552F1A; }

    .feature-title {
        color: var(--slate-900);
        font-size: 16px;
        font-weight: 700;
        margin: 0 0 6px 0;
    }

    .feature-desc {
        color: var(--slate-500);
        font-size: 14px;
        line-height: 1.5;
        margin: 0;
    }

    /* ========== STEPS ========== */
    .steps-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 20px;
    }

    .step-card {
        background: var(--white);
        border: 1px solid var(--slate-200);
        border-radius: var(--radius);
        padding: 32px 24px;
        text-align: center;
        transition: all 0.2s ease;
    }

    .step-card:hover {
        border-color: var(--blue-300);
        transform: translateY(-2px);
    }

    .step-number {
        width: 52px;
        height: 52px;
        background: linear-gradient(135deg, var(--blue-600) 0%, var(--blue-500) 100%);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 20px auto;
        color: white;
        font-size: 22px;
        font-weight: 800;
        box-shadow: 0 4px 14px rgba(59, 130, 246, 0.35);
    }

    .step-title {
        color: var(--slate-900);
        font-size: 17px;
        font-weight: 700;
        margin: 0 0 8px 0;
    }

    .step-desc {
        color: var(--slate-500);
        font-size: 14px;
        line-height: 1.5;
        margin: 0;
    }

    /* ========== BUTTONS ========== */
    .stButton > button {
        background: linear-gradient(135deg, var(--orange-500) 0%, var(--orange-600) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        padding: 14px 28px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 14px rgba(249, 115, 22, 0.35) !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(249, 115, 22, 0.45) !important;
    }

    /* ========== CHECKBOXES ========== */
    .stCheckbox {
        background: var(--white) !important;
        border: 1px solid var(--slate-200) !important;
        border-radius: var(--radius-sm) !important;
        padding: 16px 20px !important;
        margin: 6px 0 !important;
        transition: all 0.15s ease !important;
    }

    .stCheckbox:hover {
        border-color: var(--blue-400) !important;
        background: var(--blue-50) !important;
    }

    .stCheckbox label {
        font-size: 15px !important;
        font-weight: 500 !important;
        color: var(--slate-700) !important;
    }

    /* ========== TABS ========== */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--slate-100) !important;
        border-radius: var(--radius-sm) !important;
        padding: 4px !important;
        gap: 4px !important;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: var(--radius-xs) !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        padding: 12px 20px !important;
        color: var(--slate-600) !important;
    }

    .stTabs [aria-selected="true"] {
        background: var(--white) !important;
        color: var(--blue-600) !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
    }

    /* ========== DATA TABLE ========== */
    .stDataFrame {
        border: 1px solid var(--slate-200) !important;
        border-radius: var(--radius-sm) !important;
        overflow: hidden !important;
    }

    /* ========== PROGRESS ========== */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--blue-500) 0%, var(--orange-500) 100%) !important;
    }

    /* ========== ALERTS ========== */
    .stSuccess, .stInfo, .stWarning, .stError {
        border-radius: var(--radius-sm) !important;
        font-size: 14px !important;
    }

    .stSuccess {
        background: var(--green-50) !important;
        border-left: 4px solid var(--green-500) !important;
    }

    .stInfo {
        background: var(--blue-50) !important;
        border-left: 4px solid var(--blue-500) !important;
    }

    /* ========== EMPTY STATE ========== */
    .empty-state {
        text-align: center;
        padding: 60px 40px;
        background: var(--slate-50);
        border: 2px dashed var(--slate-200);
        border-radius: var(--radius);
    }

    .empty-icon {
        font-size: 56px;
        margin-bottom: 20px;
        opacity: 0.6;
    }

    .empty-title {
        color: var(--slate-900);
        font-size: 20px;
        font-weight: 700;
        margin: 0 0 8px 0;
    }

    .empty-desc {
        color: var(--slate-500);
        font-size: 15px;
        margin: 0 0 24px 0;
    }

    /* ========== API CARDS ========== */
    .api-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
    }

    .api-card {
        background: var(--white);
        border: 1px solid var(--slate-200);
        border-radius: var(--radius);
        padding: 24px;
        text-align: center;
        transition: all 0.2s ease;
    }

    .api-card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.06);
    }

    .api-card.connected {
        border-color: var(--green-500);
        background: linear-gradient(180deg, var(--white) 0%, var(--green-50) 100%);
    }

    .api-card.disconnected {
        border-color: var(--slate-300);
    }

    .api-icon {
        font-size: 32px;
        margin-bottom: 12px;
    }

    .api-name {
        color: var(--slate-900);
        font-size: 15px;
        font-weight: 600;
        margin: 0 0 8px 0;
    }

    .api-status {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 20px;
    }

    .api-status.connected {
        background: var(--green-50);
        color: var(--green-600);
    }

    .api-status.disconnected {
        background: var(--slate-100);
        color: var(--slate-500);
    }

    /* ========== TAGS ========== */
    .tags-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }

    .tag {
        background: var(--blue-50);
        color: var(--blue-700);
        font-size: 13px;
        font-weight: 500;
        padding: 8px 14px;
        border-radius: 20px;
        border: 1px solid var(--blue-100);
        transition: all 0.15s ease;
    }

    .tag:hover {
        background: var(--blue-600);
        color: white;
        border-color: var(--blue-600);
    }

    /* ========== LOADING ========== */
    .loading-box {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 18px 20px;
        background: var(--slate-50);
        border-radius: var(--radius-sm);
        margin: 8px 0;
    }

    .spinner {
        width: 22px;
        height: 22px;
        border: 3px solid var(--slate-200);
        border-top-color: var(--blue-500);
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
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
        gap: 32px;
        padding: 24px;
        background: var(--green-50);
        border: 1px solid var(--green-500);
        border-radius: var(--radius);
        margin: 16px 0;
    }

    .result-item {
        text-align: center;
    }

    .result-value {
        font-size: 32px;
        font-weight: 800;
        line-height: 1;
    }

    .result-value.green { color: var(--green-600); }
    .result-value.blue { color: var(--blue-600); }
    .result-value.orange { color: var(--orange-600); }

    .result-label {
        color: var(--slate-600);
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 6px;
    }

    /* ========== STATS BAR ========== */
    .stats-bar {
        display: flex;
        gap: 40px;
        padding: 20px 0;
        margin-bottom: 24px;
        border-bottom: 1px solid var(--slate-200);
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
    }

    .stat-label {
        font-size: 15px;
        color: var(--slate-500);
    }

    /* ========== EXPANDER ========== */
    .streamlit-expanderHeader {
        font-size: 15px !important;
        font-weight: 600 !important;
        background: var(--white) !important;
        border: 1px solid var(--slate-200) !important;
        border-radius: var(--radius-sm) !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# SESSION STATE
# ============================================
if 'leads' not in st.session_state:
    st.session_state.leads = []
if 'filtered_leads' not in st.session_state:
    st.session_state.filtered_leads = []
if 'scraping_done' not in st.session_state:
    st.session_state.scraping_done = False


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
                    <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5">
                        <polygon points="12,2 22,8.5 22,15.5 12,22 2,15.5 2,8.5"/>
                        <line x1="12" y1="22" x2="12" y2="15.5"/>
                        <polyline points="22,8.5 12,15.5 2,8.5"/>
                    </svg>
                </div>
                <div class="logo-text">
                    <p class="logo-title">LeadGen Pro</p>
                    <p class="logo-subtitle">Smart Prospecting</p>
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
                    <h4>Usuario</h4>
                    <span class="user-badge">PRO</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Navigation
        page = st.radio(
            "nav",
            ["Dashboard", "Buscar Leads", "Mis Leads", "Analytics", "Configuracion"],
            label_visibility="collapsed"
        )

        # Footer
        st.markdown(f"""
        <div class="sidebar-footer">
            <div class="sidebar-stats">
                <span class="status-dot"></span>
                <span>{len(st.session_state.filtered_leads)} leads activos</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        return page


# ============================================
# PAGES
# ============================================
def show_dashboard():
    # Header
    st.markdown("""
    <div class="page-header">
        <h1>Dashboard</h1>
        <p>Resumen de tu actividad de prospeccion</p>
    </div>
    """, unsafe_allow_html=True)

    # Metrics
    leads_count = len(st.session_state.leads)
    qualified_count = len(st.session_state.filtered_leads)
    keywords_count = len(settings.pain_keywords)
    sources_count = sum([1 for x in [True, True, bool(settings.google_api_key), True] if x])

    st.markdown(f"""
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-icon blue">👥</div>
            <div class="metric-label">Leads Encontrados</div>
            <div class="metric-value">{leads_count}</div>
            <div class="metric-tag">Esta sesion</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon green">✓</div>
            <div class="metric-label">Calificados</div>
            <div class="metric-value">{qualified_count}</div>
            <div class="metric-tag">Listos para CRM</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon orange">⚡</div>
            <div class="metric-label">Keywords</div>
            <div class="metric-value">{keywords_count}</div>
            <div class="metric-tag">Activos</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon blue">🔗</div>
            <div class="metric-label">Fuentes</div>
            <div class="metric-value">{sources_count}/4</div>
            <div class="metric-tag">Conectadas</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Features
    st.markdown("""
    <div class="section">
        <div class="section-header">
            <div class="section-title">
                <h2>Fuentes de Datos</h2>
                <span class="section-badge">4 Plataformas</span>
            </div>
        </div>
        <div class="features-grid">
            <div class="feature-card">
                <div class="feature-icon reddit">📱</div>
                <h3 class="feature-title">Reddit</h3>
                <p class="feature-desc">Subreddits de negocios y emprendedores</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon hn">🔥</div>
                <h3 class="feature-title">Hacker News</h3>
                <p class="feature-desc">Startups y founders tech</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon google">🔍</div>
                <h3 class="feature-title">Google</h3>
                <p class="feature-desc">Busquedas especificas</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon ph">🚀</div>
                <h3 class="feature-title">Product Hunt</h3>
                <p class="feature-desc">Comunidad de productos</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Steps
    st.markdown("""
    <div class="section">
        <div class="section-header">
            <div class="section-title">
                <h2>Como Funciona</h2>
                <span class="section-badge">3 Pasos</span>
            </div>
        </div>
        <div class="steps-grid">
            <div class="step-card">
                <div class="step-number">1</div>
                <h3 class="step-title">Buscar</h3>
                <p class="step-desc">Selecciona fuentes y encuentra prospectos automaticamente</p>
            </div>
            <div class="step-card">
                <div class="step-number">2</div>
                <h3 class="step-title">Calificar</h3>
                <p class="step-desc">La IA evalua y puntua cada lead por relevancia</p>
            </div>
            <div class="step-card">
                <div class="step-number">3</div>
                <h3 class="step-title">Exportar</h3>
                <p class="step-desc">Envia los mejores leads directo a HubSpot</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def show_search():
    st.markdown("""
    <div class="page-header">
        <h1>Buscar Leads</h1>
        <p>Encuentra prospectos con problemas de comunicacion</p>
    </div>
    """, unsafe_allow_html=True)

    # Sources
    st.markdown("""
    <div class="section">
        <div class="section-header">
            <div class="section-title">
                <h2>Fuentes</h2>
                <span class="section-badge">Selecciona</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        use_reddit = st.checkbox("Reddit - Subreddits de negocios", value=True)
        use_hn = st.checkbox("Hacker News - Startups", value=True)
    with col2:
        use_google = st.checkbox("Google Search", value=bool(settings.google_api_key), disabled=not settings.google_api_key)
        use_ph = st.checkbox("Product Hunt", value=True)

    st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)

    # AI Option
    ai_available = bool(settings.openai_api_key or settings.anthropic_api_key)

    st.markdown("""
    <div class="section">
        <div class="section-header">
            <div class="section-title">
                <h2>Calificacion AI</h2>
                <span class="section-badge">Recomendado</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    use_ai = st.checkbox("Usar IA para calificar leads", value=ai_available, disabled=not ai_available)

    if not ai_available:
        st.info("Configura OpenAI o Anthropic API key para usar calificacion con IA")

    st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)

    # Search Button
    if st.button("Iniciar Busqueda", type="primary", use_container_width=True):
        all_leads = []
        progress = st.progress(0)
        status = st.empty()
        results = st.container()

        scrapers = []
        if use_reddit: scrapers.append(("Reddit", RedditScraper))
        if use_hn: scrapers.append(("Hacker News", HackerNewsScraper))
        if use_google and settings.google_api_key: scrapers.append(("Google", GoogleScraper))
        if use_ph: scrapers.append(("Product Hunt", ProductHuntScraper))

        if not scrapers:
            st.warning("Selecciona al menos una fuente")
            return

        for i, (name, Scraper) in enumerate(scrapers):
            status.markdown(f"""
            <div class="loading-box">
                <div class="spinner"></div>
                <span class="loading-text">Buscando en {name}...</span>
            </div>
            """, unsafe_allow_html=True)

            try:
                with Scraper() as s:
                    batch = s.scrape()
                    all_leads.extend(batch.leads)
                    with results:
                        st.success(f"{name}: {len(batch.leads)} leads")
            except Exception as e:
                with results:
                    st.warning(f"{name}: Error")

            progress.progress((i + 1) / len(scrapers))

        st.session_state.leads = all_leads

        # AI Filter
        if use_ai and all_leads:
            status.markdown("""
            <div class="loading-box">
                <div class="spinner"></div>
                <span class="loading-text">Calificando con IA...</span>
            </div>
            """, unsafe_allow_html=True)

            try:
                ai_filter = AILeadFilter()
                filtered = ai_filter.filter_leads(all_leads)
                qualified = [l for l in filtered if l.is_qualified]
                st.session_state.filtered_leads = qualified
                with results:
                    st.success(f"IA califico {len(qualified)}/{len(all_leads)} leads")
            except:
                st.session_state.filtered_leads = all_leads
        else:
            st.session_state.filtered_leads = all_leads

        st.session_state.scraping_done = True
        progress.progress(1.0)

        status.markdown(f"""
        <div class="results-box">
            <div class="result-item">
                <div class="result-value green">{len(st.session_state.filtered_leads)}</div>
                <div class="result-label">Calificados</div>
            </div>
            <div class="result-item">
                <div class="result-value blue">{len(all_leads)}</div>
                <div class="result-label">Encontrados</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Preview
    if st.session_state.scraping_done and st.session_state.filtered_leads:
        st.markdown(f"""
        <div class="section" style="margin-top: 32px;">
            <div class="section-header">
                <div class="section-title">
                    <h2>Resultados</h2>
                    <span class="section-badge">{len(st.session_state.filtered_leads)} leads</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        for lead in st.session_state.filtered_leads[:5]:
            with st.expander(f"{lead.title[:65]}..."):
                st.write(f"**Fuente:** {lead.source.value}")
                st.write(f"**Keywords:** {', '.join(lead.keywords_matched[:4])}")
                if lead.ai_score:
                    st.write(f"**Score:** {lead.ai_score:.2f}")
                st.write(f"[Ver original]({lead.url})")
                st.write("---")
                st.write(lead.content[:350] + "...")


def show_leads():
    st.markdown("""
    <div class="page-header">
        <h1>Mis Leads</h1>
        <p>Gestiona y exporta tus prospectos</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Leads Locales", "HubSpot"])

    with tab1:
        if not st.session_state.filtered_leads:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-icon">🔍</div>
                <h3 class="empty-title">Sin leads todavia</h3>
                <p class="empty-desc">Ve a Buscar Leads para encontrar prospectos</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            qualified = len([l for l in st.session_state.filtered_leads if l.is_qualified])
            st.markdown(f"""
            <div class="stats-bar">
                <div class="stat-item">
                    <span class="stat-value">{len(st.session_state.filtered_leads)}</span>
                    <span class="stat-label">totales</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value" style="color: var(--green-600);">{qualified}</span>
                    <span class="stat-label">calificados</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            data = [{
                "ID": l.id[:8],
                "Titulo": l.title[:45] + "..." if len(l.title) > 45 else l.title,
                "Fuente": l.source.value,
                "Keywords": ", ".join(l.keywords_matched[:3]),
                "Score": f"{l.ai_score:.2f}" if l.ai_score else "-"
            } for l in st.session_state.filtered_leads]

            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

            st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)

            if st.button("Enviar a HubSpot", type="primary"):
                with HubSpotCRM() as crm:
                    if not crm.is_configured():
                        st.error("HubSpot no configurado")
                    else:
                        with st.spinner("Enviando..."):
                            r = crm.send_leads_to_crm(st.session_state.filtered_leads)
                        st.markdown(f"""
                        <div class="results-box">
                            <div class="result-item">
                                <div class="result-value green">{r['created']}</div>
                                <div class="result-label">Creados</div>
                            </div>
                            <div class="result-item">
                                <div class="result-value orange">{r['existing']}</div>
                                <div class="result-label">Existentes</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

    with tab2:
        with HubSpotCRM() as crm:
            if not crm.is_configured():
                st.markdown("""
                <div class="empty-state">
                    <div class="empty-icon">☁️</div>
                    <h3 class="empty-title">HubSpot no conectado</h3>
                    <p class="empty-desc">Agrega HUBSPOT_API_KEY en .env</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                stage = st.selectbox("Filtrar etapa", ["Todos"] + [s.value for s in LeadStage])

                if st.button("Cargar", type="primary"):
                    with st.spinner("Cargando..."):
                        contacts = crm.get_all_contacts() if stage == "Todos" else crm.get_contacts_by_stage(LeadStage(stage))

                    if contacts:
                        data = [{
                            "Nombre": f"{c.firstname or ''} {c.lastname or ''}".strip() or "-",
                            "Email": c.email or "-",
                            "Empresa": c.company or "-",
                            "Etapa": c.lead_stage.value
                        } for c in contacts]
                        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
                    else:
                        st.info("Sin contactos")


def show_analytics():
    st.markdown("""
    <div class="page-header">
        <h1>Analytics</h1>
        <p>Metricas y rendimiento</p>
    </div>
    """, unsafe_allow_html=True)

    with HubSpotCRM() as crm:
        if not crm.is_configured():
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon blue">👥</div>
                    <div class="metric-label">Encontrados</div>
                    <div class="metric-value">{len(st.session_state.leads)}</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon green">✓</div>
                    <div class="metric-label">Calificados</div>
                    <div class="metric-value">{len(st.session_state.filtered_leads)}</div>
                </div>
                """, unsafe_allow_html=True)

            with col3:
                rate = (len(st.session_state.filtered_leads) / len(st.session_state.leads) * 100) if st.session_state.leads else 0
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon orange">📊</div>
                    <div class="metric-label">Tasa</div>
                    <div class="metric-value">{rate:.0f}%</div>
                </div>
                """, unsafe_allow_html=True)

            if st.session_state.leads:
                st.markdown("<div style='height: 32px'></div>", unsafe_allow_html=True)
                counts = {}
                for l in st.session_state.leads:
                    counts[l.source.value] = counts.get(l.source.value, 0) + 1
                st.bar_chart(counts)

            st.info("Conecta HubSpot para ver estadisticas completas")
        else:
            with st.spinner("Cargando..."):
                stats = crm.get_statistics()

            if "error" not in stats:
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Total Leads", stats["total_leads"])
                with col2:
                    st.metric("Conversion", f"{stats['conversion_rate']}%")
                with col3:
                    st.metric("Win Rate", f"{stats['win_rate']}%")
                with col4:
                    st.metric("Ganados", stats["by_stage"].get("closed_won", 0))

                if stats["by_stage"]:
                    st.bar_chart(stats["by_stage"])


def show_config():
    st.markdown("""
    <div class="page-header">
        <h1>Configuracion</h1>
        <p>APIs y parametros del sistema</p>
    </div>
    """, unsafe_allow_html=True)

    # APIs
    st.markdown("""
    <div class="section">
        <div class="section-header">
            <div class="section-title">
                <h2>Integraciones</h2>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    apis = [
        ("📊", "HubSpot", settings.hubspot_api_key),
        ("🔍", "Google", settings.google_api_key),
        ("🤖", "OpenAI", settings.openai_api_key),
        ("🧠", "Anthropic", settings.anthropic_api_key),
    ]

    html = '<div class="api-grid">'
    for icon, name, key in apis:
        status = "connected" if key else "disconnected"
        label = "Conectado" if key else "No configurado"
        html += f"""
        <div class="api-card {status}">
            <div class="api-icon">{icon}</div>
            <h4 class="api-name">{name}</h4>
            <span class="api-status {status}">{label}</span>
        </div>
        """
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

    # Subreddits
    st.markdown("""
    <div class="section" style="margin-top: 40px;">
        <div class="section-header">
            <div class="section-title">
                <h2>Subreddits</h2>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tags = "".join([f'<span class="tag">r/{s}</span>' for s in settings.subreddits])
    st.markdown(f'<div class="tags-container">{tags}</div>', unsafe_allow_html=True)

    # Keywords
    st.markdown("""
    <div class="section" style="margin-top: 40px;">
        <div class="section-header">
            <div class="section-title">
                <h2>Keywords</h2>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tags = "".join([f'<span class="tag">{k}</span>' for k in settings.pain_keywords])
    st.markdown(f'<div class="tags-container">{tags}</div>', unsafe_allow_html=True)

    st.markdown("<div style='height: 32px'></div>", unsafe_allow_html=True)
    st.info("Edita el archivo .env para cambiar la configuracion")


# ============================================
# MAIN
# ============================================
def main():
    page = render_sidebar()

    if page == "Dashboard":
        show_dashboard()
    elif page == "Buscar Leads":
        show_search()
    elif page == "Mis Leads":
        show_leads()
    elif page == "Analytics":
        show_analytics()
    elif page == "Configuracion":
        show_config()


if __name__ == "__main__":
    main()
