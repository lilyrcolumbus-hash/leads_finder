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
from src.utils.scoring import enrich_leads, calculate_pain_score
from src.utils.lead_manager import lead_manager, csv_exporter, email_finder
from src.utils.hunter_enricher import enrich_leads_with_hunter
from src.utils.background_tasks import task_manager, TaskStatus
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
# PREMIUM CSS - Executive Business Design
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
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* ========== EXECUTIVE COLOR PALETTE ========== */
    :root {
        /* Primary - Corporate Blue */
        --primary-50: #EFF6FF;
        --primary-100: #DBEAFE;
        --primary-200: #BFDBFE;
        --primary-400: #60A5FA;
        --primary-500: #3B82F6;
        --primary-600: #2563EB;
        --primary-700: #1D4ED8;

        /* Accent - Emerald Success */
        --accent-50: #ECFDF5;
        --accent-500: #10B981;
        --accent-600: #059669;

        /* Warm Accent - Amber */
        --warm-50: #FFFBEB;
        --warm-500: #F59E0B;
        --warm-600: #D97706;

        /* Neutral - Slate Gray (Professional) */
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

        /* Status Colors */
        --success: #22C55E;
        --warning: #EAB308;
        --error: #EF4444;
        --info: #3B82F6;

        /* Base */
        --white: #FFFFFF;
        --black: #000000;

        /* Borders & Shadows */
        --border-light: #E2E8F0;
        --border-medium: #CBD5E1;

        /* Border Radius */
        --radius-xs: 6px;
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
        --radius-xl: 20px;
        --radius-2xl: 24px;

        /* Shadows - Soft & Professional */
        --shadow-xs: 0 1px 2px rgba(15, 23, 42, 0.04);
        --shadow-sm: 0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04);
        --shadow-md: 0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -1px rgba(15, 23, 42, 0.04);
        --shadow-lg: 0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -2px rgba(15, 23, 42, 0.04);
        --shadow-xl: 0 20px 25px -5px rgba(15, 23, 42, 0.1), 0 10px 10px -5px rgba(15, 23, 42, 0.04);
        --shadow-glow: 0 0 20px rgba(59, 130, 246, 0.15);
    }

    /* ========== GLOBAL TYPOGRAPHY ========== */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        line-height: 1.3 !important;
        color: var(--slate-900) !important;
    }

    p, span, div, label {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        line-height: 1.6 !important;
    }

    /* ========== MAIN APP BACKGROUND ========== */
    .stApp, [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 40%, #F1F5F9 100%) !important;
    }

    .main, [data-testid="stMain"] {
        background: transparent !important;
    }

    .main .block-container {
        padding: 2rem 3rem 3rem 3rem !important;
        max-width: 1400px !important;
        background: transparent !important;
    }

    /* ========== SIDEBAR - EXECUTIVE STYLE ========== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #FAFBFC 100%) !important;
        border-right: 1px solid var(--border-light) !important;
        box-shadow: 2px 0 8px rgba(15, 23, 42, 0.03) !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding: 0 !important;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: var(--slate-600) !important;
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
        border-radius: var(--radius-md) !important;
        padding: 14px 16px !important;
        margin: 0 !important;
        color: var(--slate-600) !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        transition: all 0.2s ease !important;
        border: 1px solid transparent !important;
    }

    [data-testid="stSidebar"] .stRadio > div > label:hover {
        background: var(--slate-50) !important;
        color: var(--slate-800) !important;
        border-color: var(--border-light) !important;
    }

    [data-testid="stSidebar"] .stRadio > div > label[data-checked="true"] {
        background: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-500) 100%) !important;
        color: var(--white) !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25), 0 2px 4px rgba(37, 99, 235, 0.1) !important;
        border-color: transparent !important;
    }

    /* ========== LOGO SECTION ========== */
    .logo-section {
        padding: 28px 24px 24px 24px;
        border-bottom: 1px solid var(--border-light);
        margin-bottom: 8px;
        background: linear-gradient(180deg, #FFFFFF 0%, #FAFBFC 100%);
    }

    .logo-container {
        display: flex;
        align-items: center;
        gap: 14px;
    }

    .logo-icon {
        width: 46px;
        height: 46px;
        background: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-500) 100%);
        border-radius: var(--radius-md);
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3), 0 2px 4px rgba(37, 99, 235, 0.1);
    }

    .logo-icon svg {
        width: 24px;
        height: 24px;
    }

    .logo-text {
        flex: 1;
    }

    .logo-title {
        color: var(--slate-900);
        font-size: 20px;
        font-weight: 800;
        letter-spacing: -0.03em;
        margin: 0;
        line-height: 1.2;
    }

    .logo-subtitle {
        color: var(--slate-400);
        font-size: 11px;
        font-weight: 600;
        margin: 4px 0 0 0;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* ========== USER CARD ========== */
    .user-card {
        margin: 16px;
        padding: 16px;
        background: linear-gradient(135deg, var(--slate-50) 0%, #FFFFFF 100%);
        border-radius: var(--radius-md);
        border: 1px solid var(--border-light);
        transition: all 0.2s ease;
    }

    .user-card:hover {
        border-color: var(--primary-200);
        box-shadow: var(--shadow-sm);
    }

    .user-info {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .user-avatar {
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, var(--primary-500) 0%, var(--primary-400) 100%);
        border-radius: var(--radius-sm);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 15px;
        font-weight: 700;
        color: white;
        box-shadow: 0 4px 8px rgba(59, 130, 246, 0.25);
    }

    .user-details h4 {
        color: var(--slate-800);
        font-size: 14px;
        font-weight: 600;
        margin: 0 0 4px 0;
    }

    .user-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: linear-gradient(135deg, var(--accent-500) 0%, var(--accent-600) 100%);
        color: white;
        font-size: 10px;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 20px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3);
    }

    /* ========== NAV LABEL ========== */
    .nav-label {
        padding: 24px 24px 10px 24px;
        font-size: 11px;
        font-weight: 700;
        color: var(--slate-400);
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    /* ========== SIDEBAR FOOTER ========== */
    .sidebar-footer {
        padding: 20px 24px;
        border-top: 1px solid var(--border-light);
        margin-top: auto;
        background: linear-gradient(180deg, #FAFBFC 0%, #FFFFFF 100%);
    }

    .sidebar-stats {
        display: flex;
        align-items: center;
        gap: 10px;
        color: var(--slate-500);
        font-size: 13px;
        font-weight: 500;
    }

    .status-dot {
        width: 8px;
        height: 8px;
        background: var(--success);
        border-radius: 50%;
        box-shadow: 0 0 8px var(--success);
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.7; transform: scale(0.95); }
    }

    /* ========== PAGE HEADER ========== */
    .page-header {
        margin-bottom: 32px;
        padding-bottom: 20px;
        border-bottom: 1px solid var(--border-light);
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
        font-weight: 500;
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

    /* ========== BUTTONS - EXECUTIVE ========== */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-500) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--radius-md) !important;
        padding: 14px 28px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25), 0 2px 4px rgba(37, 99, 235, 0.1) !important;
        transition: all 0.3s ease !important;
        letter-spacing: -0.01em !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(37, 99, 235, 0.35), 0 4px 8px rgba(37, 99, 235, 0.15) !important;
    }

    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* Secondary button style */
    .stButton > button[kind="secondary"] {
        background: var(--white) !important;
        color: var(--slate-700) !important;
        border: 1px solid var(--border-medium) !important;
        box-shadow: var(--shadow-sm) !important;
    }

    .stButton > button[kind="secondary"]:hover {
        background: var(--slate-50) !important;
        border-color: var(--primary-300) !important;
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

    /* ========== DATA TABLE ========== */
    .stDataFrame {
        border: 1px solid var(--border-light) !important;
        border-radius: var(--radius-lg) !important;
        overflow: hidden !important;
    }

    /* ========== PROGRESS ========== */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--primary-500) 0%, var(--primary-400) 100%) !important;
        border-radius: 10px !important;
    }

    /* ========== ALERTS ========== */
    .stSuccess, .stInfo, .stWarning, .stError {
        border-radius: var(--radius-md) !important;
        font-size: 14px !important;
        border-left-width: 4px !important;
        padding: 16px 20px !important;
    }

    .stSuccess {
        background: linear-gradient(135deg, var(--accent-50) 0%, #D1FAE5 100%) !important;
        border-left-color: var(--success) !important;
    }

    .stInfo {
        background: linear-gradient(135deg, var(--primary-50) 0%, var(--primary-100) 100%) !important;
        border-left-color: var(--info) !important;
    }

    /* ========== EMPTY STATE ========== */
    .empty-state {
        text-align: center;
        padding: 60px 48px;
        background: linear-gradient(180deg, var(--slate-50) 0%, var(--white) 100%);
        border: 2px dashed var(--border-medium);
        border-radius: var(--radius-xl);
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
        letter-spacing: -0.02em;
    }

    .empty-desc {
        color: var(--slate-500);
        font-size: 15px;
        margin: 0 0 24px 0;
    }

    /* ========== API CARDS - EXECUTIVE ========== */
    .api-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
    }

    .api-card {
        background: var(--white) !important;
        border: 1px solid var(--border-light) !important;
        border-radius: var(--radius-xl) !important;
        padding: 28px 24px !important;
        text-align: center !important;
        transition: all 0.3s ease !important;
        display: block !important;
        min-height: 140px !important;
        position: relative !important;
    }

    .api-card:hover {
        box-shadow: var(--shadow-md) !important;
        transform: translateY(-3px) !important;
        border-color: var(--primary-200) !important;
    }

    .api-card.connected {
        border-color: var(--accent-500) !important;
        background: linear-gradient(180deg, #FFFFFF 0%, var(--accent-50) 100%) !important;
    }

    .api-card.connected::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--accent-500), var(--accent-600));
        border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    }

    .api-card.disconnected {
        border-color: var(--border-light) !important;
        background: var(--white) !important;
    }

    .api-icon {
        font-size: 36px !important;
        margin-bottom: 14px !important;
        display: block !important;
    }

    .api-name {
        color: var(--slate-900) !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        margin: 0 0 12px 0 !important;
        letter-spacing: -0.01em !important;
        display: block !important;
    }

    h4.api-name {
        color: var(--slate-900) !important;
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
        background: linear-gradient(135deg, var(--accent-50) 0%, #D1FAE5 100%) !important;
        color: var(--accent-600) !important;
    }

    .api-status.disconnected {
        background: var(--slate-100) !important;
        color: var(--slate-500) !important;
    }

    /* ========== TAGS ========== */
    .tags-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }

    .tag {
        background: linear-gradient(135deg, var(--primary-50) 0%, var(--primary-100) 100%);
        color: var(--primary-700);
        font-size: 13px;
        font-weight: 600;
        padding: 8px 14px;
        border-radius: 20px;
        border: 1px solid var(--primary-200);
        transition: all 0.2s ease;
    }

    .tag:hover {
        background: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-500) 100%);
        color: white;
        border-color: var(--primary-600);
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(37, 99, 235, 0.2);
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
        gap: 32px;
        padding: 24px 28px;
        background: linear-gradient(135deg, var(--accent-50) 0%, #D1FAE5 100%);
        border: 1px solid var(--accent-500);
        border-radius: var(--radius-xl);
        margin: 20px 0;
    }

    .result-item {
        text-align: center;
    }

    .result-value {
        font-size: 32px;
        font-weight: 800;
        line-height: 1;
        letter-spacing: -0.03em;
    }

    .result-value.green { color: var(--accent-600); }
    .result-value.blue { color: var(--primary-600); }
    .result-value.orange { color: var(--warm-600); }

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

    /* ========== EXPANDER ========== */
    .streamlit-expanderHeader {
        font-size: 15px !important;
        font-weight: 600 !important;
        background: var(--white) !important;
        border: 1px solid var(--border-light) !important;
        border-radius: var(--radius-md) !important;
        transition: all 0.2s ease !important;
        padding: 14px 18px !important;
    }

    .streamlit-expanderHeader:hover {
        border-color: var(--primary-300) !important;
        background: var(--primary-50) !important;
    }

    /* ========== SELECT BOX ========== */
    .stSelectbox > div > div {
        background: var(--white) !important;
        border: 1px solid var(--border-light) !important;
        border-radius: var(--radius-md) !important;
        font-size: 15px !important;
        color: var(--slate-800) !important;
        padding: 4px 8px !important;
    }

    .stSelectbox > div > div:hover {
        border-color: var(--primary-300) !important;
    }

    .stSelectbox label, .stTextInput label, .stTextArea label, .stNumberInput label {
        color: var(--slate-700) !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        margin-bottom: 6px !important;
    }

    /* ========== TEXT INPUTS ========== */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {
        background: var(--white) !important;
        border: 1px solid var(--border-light) !important;
        border-radius: var(--radius-md) !important;
        color: var(--slate-800) !important;
        font-size: 15px !important;
        padding: 12px 14px !important;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--primary-400) !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
    }

    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {
        color: var(--slate-400) !important;
    }

    /* ========== MULTISELECT ========== */
    .stMultiSelect > div > div {
        background: var(--white) !important;
        border: 1px solid var(--border-light) !important;
        border-radius: var(--radius-md) !important;
        color: var(--slate-800) !important;
    }

    .stMultiSelect span {
        color: var(--slate-800) !important;
    }

    /* ========== RADIO BUTTONS (main area) ========== */
    .main .stRadio label {
        color: var(--slate-700) !important;
        font-weight: 500 !important;
    }

    /* ========== ALL LABELS AND TEXT ========== */
    .main p, .main span, .main label, .main div {
        color: var(--slate-700);
    }

    .main h1, .main h2, .main h3, .main h4 {
        color: var(--slate-900) !important;
    }

    /* ========== SELECTBOX DROPDOWN ========== */
    [data-baseweb="select"] span,
    [data-baseweb="select"] div {
        color: var(--slate-800) !important;
    }

    [data-baseweb="menu"] {
        background: var(--white) !important;
        border-radius: var(--radius-md) !important;
        border: 1px solid var(--border-light) !important;
        box-shadow: var(--shadow-lg) !important;
    }

    [data-baseweb="menu"] li {
        color: var(--slate-800) !important;
        padding: 12px 16px !important;
    }

    [data-baseweb="menu"] li:hover {
        background: var(--primary-50) !important;
    }

    /* ========== SPINNER ========== */
    .stSpinner > div {
        border-top-color: var(--primary-500) !important;
    }

    /* ========== SCROLLBAR ========== */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }

    ::-webkit-scrollbar-track {
        background: var(--slate-100);
        border-radius: 5px;
    }

    ::-webkit-scrollbar-thumb {
        background: var(--slate-300);
        border-radius: 5px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--slate-400);
    }

    /* ========== ENHANCED CHECKBOX STYLING ========== */
    .stCheckbox > label {
        color: var(--slate-800) !important;
        font-weight: 500 !important;
    }

    .stCheckbox > label > div {
        color: var(--slate-800) !important;
    }

    .stCheckbox > label > div > p,
    .stCheckbox > label > div > span {
        color: var(--slate-800) !important;
        font-weight: 500 !important;
    }

    .stCheckbox [data-testid="stMarkdownContainer"] p {
        color: var(--slate-800) !important;
    }

    /* ========== ENHANCED ALERTS ========== */
    .stAlert {
        border-radius: var(--radius-lg) !important;
        padding: 18px 22px !important;
        border: none !important;
        box-shadow: var(--shadow-sm) !important;
    }

    .stAlert > div {
        color: var(--slate-800) !important;
        font-size: 14px !important;
    }

    [data-testid="stAlert"] {
        border-radius: var(--radius-lg) !important;
        border-left: 4px solid !important;
    }

    [data-baseweb="notification"] {
        border-radius: var(--radius-lg) !important;
        background: linear-gradient(135deg, var(--primary-50) 0%, var(--primary-100) 100%) !important;
        border-left: 4px solid var(--primary-500) !important;
    }

    [data-baseweb="notification"] [data-testid="stMarkdownContainer"] p {
        color: var(--slate-800) !important;
        font-weight: 500 !important;
    }

    /* Info alert styling */
    .element-container:has([data-testid="stAlert"]) [role="alert"] {
        background: linear-gradient(135deg, var(--primary-50) 0%, var(--primary-100) 100%) !important;
        border-left-color: var(--primary-500) !important;
        border-radius: var(--radius-lg) !important;
        padding: 18px 22px !important;
    }

    /* ========== CONTAINERS & CARDS ========== */
    [data-testid="stVerticalBlock"] > div:has(> [data-testid="stHorizontalBlock"]) {
        background: var(--white);
        border-radius: var(--radius-xl);
        padding: 24px;
        border: 1px solid var(--border-light);
        margin: 16px 0;
    }

    /* File uploader styling */
    .stFileUploader {
        background: var(--white) !important;
        border: 2px dashed var(--border-medium) !important;
        border-radius: var(--radius-lg) !important;
        padding: 32px !important;
        transition: all 0.2s ease !important;
    }

    .stFileUploader:hover {
        border-color: var(--primary-400) !important;
        background: var(--primary-50) !important;
    }

    /* Divider styling */
    hr {
        border: none !important;
        border-top: 1px solid var(--border-light) !important;
        margin: 24px 0 !important;
    }

    /* ========== STREAMLIT NATIVE TITLES ========== */
    .main h1 {
        color: var(--slate-900) !important;
        font-size: 32px !important;
        font-weight: 800 !important;
        letter-spacing: -0.03em !important;
        margin-bottom: 8px !important;
    }

    .main h2 {
        color: var(--slate-800) !important;
        font-size: 24px !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }

    .main h3 {
        color: var(--slate-800) !important;
        font-size: 20px !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }

    /* Caption styling */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: var(--slate-500) !important;
        font-size: 15px !important;
        font-weight: 500 !important;
    }

    /* ========== FINAL POLISH ========== */
    .stMarkdown {
        color: var(--slate-700) !important;
    }

    /* Smooth transitions for all interactive elements */
    button, input, select, textarea, a {
        transition: all 0.2s ease !important;
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
if 'nav_page' not in st.session_state:
    st.session_state.nav_page = "Dashboard"


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

        # Nav Label
        st.markdown('<div class="nav-label">Main Menu</div>', unsafe_allow_html=True)

        # Navigation
        pages = ["Dashboard", "Find Leads", "My Leads", "CRM", "Analytics", "Settings"]
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
    # Header
    st.title("📊 Dashboard")
    st.caption("Overview of your prospecting activity")

    st.divider()

    # Quick Actions
    st.subheader("⚡ Quick Actions")

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

    st.divider()

    # Metrics
    leads_count = len(st.session_state.leads)
    qualified_count = len(st.session_state.filtered_leads)
    hot_leads_count = len([l for l in st.session_state.filtered_leads if l.pain_score >= 70])
    keywords_count = len(settings.pain_keywords)
    sources_count = sum([1 for x in [True, True, bool(settings.google_api_key), True] if x])
    conv_rate = int((qualified_count / leads_count * 100)) if leads_count > 0 else 0
    avg_pain_score = sum(l.pain_score for l in st.session_state.filtered_leads) / len(st.session_state.filtered_leads) if st.session_state.filtered_leads else 0

    st.markdown(f"""
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-header">
                <div class="metric-icon primary">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4F46E5" stroke-width="2">
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                        <circle cx="9" cy="7" r="4"/>
                        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                    </svg>
                </div>
            </div>
            <div class="metric-content">
                <div class="metric-label">Leads Found</div>
                <div class="metric-value">{leads_count}</div>
            </div>
            <div class="metric-footer">
                <span class="metric-tag">This session</span>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-header">
                <div class="metric-icon" style="background: var(--error-50);">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2">
                        <path d="M12 2L2 22h20L12 2z"/>
                        <path d="M12 9v4"/>
                        <path d="M12 17h.01"/>
                    </svg>
                </div>
            </div>
            <div class="metric-content">
                <div class="metric-label">Hot Leads</div>
                <div class="metric-value" style="color: var(--error-500);">{hot_leads_count}</div>
            </div>
            <div class="metric-footer">
                <span class="metric-tag" style="background: var(--error-50); color: var(--error-500);">Score 70+</span>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-header">
                <div class="metric-icon success">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                        <polyline points="22 4 12 14.01 9 11.01"/>
                    </svg>
                </div>
                <span class="metric-trend">+{conv_rate}%</span>
            </div>
            <div class="metric-content">
                <div class="metric-label">Qualified</div>
                <div class="metric-value">{qualified_count}</div>
            </div>
            <div class="metric-footer">
                <span class="metric-tag">Ready for CRM</span>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-header">
                <div class="metric-icon accent">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#EA580C" stroke-width="2">
                        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                    </svg>
                </div>
            </div>
            <div class="metric-content">
                <div class="metric-label">Keywords</div>
                <div class="metric-value">{keywords_count}</div>
            </div>
            <div class="metric-footer">
                <span class="metric-tag">Active</span>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-header">
                <div class="metric-icon primary">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4F46E5" stroke-width="2">
                        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
                    </svg>
                </div>
            </div>
            <div class="metric-content">
                <div class="metric-label">Sources</div>
                <div class="metric-value">{sources_count}/4</div>
            </div>
            <div class="metric-footer">
                <span class="metric-tag">Connected</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Features
    st.markdown("""
    <div class="section">
        <div class="section-header">
            <div class="section-title">
                <h2>Data Sources</h2>
                <span class="section-badge">4 Platforms</span>
            </div>
        </div>
        <div class="features-grid">
            <div class="feature-card">
                <div class="feature-icon reddit">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
                        <circle cx="9" cy="12" r="1.5"/>
                        <circle cx="15" cy="12" r="1.5"/>
                        <path d="M12 16c-1.5 0-3-.5-3-1.5s1.5-1 3-1 3 .5 3 1.5-1.5 1-3 1z"/>
                    </svg>
                </div>
                <h3 class="feature-title">Reddit</h3>
                <p class="feature-desc">Business and entrepreneur subreddits</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon hn">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="white">
                        <text x="6" y="18" font-size="16" font-weight="bold">Y</text>
                    </svg>
                </div>
                <h3 class="feature-title">Hacker News</h3>
                <p class="feature-desc">Tech startups and founders</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon google">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5">
                        <circle cx="11" cy="11" r="8"/>
                        <path d="M21 21l-4.35-4.35"/>
                    </svg>
                </div>
                <h3 class="feature-title">Google</h3>
                <p class="feature-desc">Targeted search queries</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon ph">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="white">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h4c1.1 0 2 .9 2 2v2c0 1.1-.9 2-2 2h-2v4z"/>
                    </svg>
                </div>
                <h3 class="feature-title">Product Hunt</h3>
                <p class="feature-desc">Product community</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Steps
    st.markdown("""
    <div class="section">
        <div class="section-header">
            <div class="section-title">
                <h2>How It Works</h2>
                <span class="section-badge">3 Steps</span>
            </div>
        </div>
        <div class="steps-grid">
            <div class="step-card">
                <div class="step-number">1</div>
                <h3 class="step-title">Search</h3>
                <p class="step-desc">Select sources and find prospects automatically</p>
            </div>
            <div class="step-card">
                <div class="step-number">2</div>
                <h3 class="step-title">Qualify</h3>
                <p class="step-desc">AI evaluates and scores each lead by relevance</p>
            </div>
            <div class="step-card">
                <div class="step-number">3</div>
                <h3 class="step-title">Export</h3>
                <p class="step-desc">Send the best leads directly to HubSpot</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def show_search():
    # Page Title
    st.title("🔎 Find Leads")
    st.caption("Find prospects with communication problems")

    st.divider()

    # Active Sources Section
    st.subheader("📡 Active Sources (4 Available)")

    col1, col2 = st.columns(2)
    with col1:
        use_reddit = st.checkbox("🔴 Reddit - Business subreddits", value=True, key="reddit_check")
        use_hn = st.checkbox("🟠 Hacker News - Startups", value=True, key="hn_check")
    with col2:
        use_google = st.checkbox("🔵 Google Search", value=bool(settings.google_api_key), disabled=not settings.google_api_key, key="google_check")
        use_ph = st.checkbox("🟣 Product Hunt", value=True, key="ph_check")

    st.divider()

    # Coming Soon Sources
    st.subheader("🚀 Coming Soon (6 More)")

    coming_cols = st.columns(6)
    coming_sources = [
        ("🔷", "LinkedIn"),
        ("🐦", "Twitter/X"),
        ("⭐", "Yelp"),
        ("📍", "Google Business"),
        ("📘", "Facebook"),
        ("🏆", "G2/Clutch")
    ]
    for i, (icon, name) in enumerate(coming_sources):
        with coming_cols[i]:
            st.markdown(f"**{icon}**")
            st.caption(name)

    st.divider()

    # Time Filter
    st.subheader("📅 Time Range")
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

    st.divider()

    # Industry Filter
    st.subheader("🏢 Filter by Industry (Optional)")
    industries = ["All Industries"] + list(settings.industries.keys())
    selected_industry = st.selectbox("Select industry", industries)

    st.divider()

    # AI Option
    ai_available = bool(settings.openai_api_key or settings.anthropic_api_key)
    st.subheader("🤖 AI Qualification (Recommended)")

    use_ai = st.checkbox("Use AI to qualify leads automatically", value=ai_available, disabled=not ai_available, key="ai_check")

    if not ai_available:
        st.info("Configure OpenAI or Anthropic API key in Settings to enable AI qualification")

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
                    batch = s.scrape(time_filter=selected_time)
                    all_leads.extend(batch.leads)
                    with results:
                        st.success(f"{name}: {len(batch.leads)} leads")
            except Exception as e:
                with results:
                    st.warning(f"{name}: Error")

            progress.progress((i + 1) / len(scrapers))

        # Enrich leads with Pain Score and Industry
        status.markdown("""
        <div class="loading-box">
            <div class="spinner"></div>
            <span class="loading-text">Calculating Pain Scores...</span>
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

        # Auto-save leads to storage
        saved_count = lead_manager.save_leads(all_leads)
        if saved_count > 0:
            with results:
                st.success(f"Auto-saved {saved_count} new leads to database")

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

        st.session_state.scraping_done = True
        progress.progress(1.0)

        # Calculate hot leads (Pain Score >= 70)
        hot_leads = len([l for l in st.session_state.filtered_leads if l.pain_score >= 70])

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
            nav_col1, nav_col2 = st.columns(2)
            with nav_col1:
                if st.button("📋 View in CRM", type="primary", use_container_width=True):
                    st.session_state.nav_page = "CRM"
                    st.rerun()
            with nav_col2:
                if st.button("📊 View All Leads", use_container_width=True):
                    st.session_state.nav_page = "My Leads"
                    st.rerun()

    # Preview
    if st.session_state.scraping_done and st.session_state.filtered_leads:
        st.markdown(f"""
        <div class="section" style="margin-top: 32px;">
            <div class="section-header">
                <div class="section-title">
                    <h2>Results</h2>
                    <span class="section-badge">{len(st.session_state.filtered_leads)} leads</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        for lead in st.session_state.filtered_leads[:5]:
            # Pain Score badge color
            if lead.pain_score >= 70:
                score_color = "var(--error-500)"
                urgency_label = "HOT"
            elif lead.pain_score >= 50:
                score_color = "var(--warning-500)"
                urgency_label = "HIGH"
            elif lead.pain_score >= 25:
                score_color = "var(--primary-500)"
                urgency_label = "MEDIUM"
            else:
                score_color = "var(--neutral-400)"
                urgency_label = "LOW"

            with st.expander(f"[{lead.pain_score}] {lead.title[:60]}..."):
                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 10px; background: {score_color}15; border-radius: 8px;">
                        <div style="font-size: 28px; font-weight: 800; color: {score_color};">{lead.pain_score}</div>
                        <div style="font-size: 10px; font-weight: 600; color: {score_color};">PAIN SCORE</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.write(f"**Source:** {lead.source.value}")
                    st.write(f"**Industry:** {lead.industry or 'Unknown'}")
                with col3:
                    st.write(f"**Urgency:** {urgency_label}")
                    st.write(f"**Keywords:** {len(lead.keywords_matched)}")

                st.write(f"**Matched:** {', '.join(lead.keywords_matched[:5])}")
                st.write(f"[View original]({lead.url})")
                st.write("---")
                st.write(lead.content[:350] + "...")


def show_leads():
    st.title("📋 My Leads")
    st.caption("Manage and export your prospects")

    st.divider()

    # Import Section with Field Mapping
    st.subheader("📤 Import Leads")

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

            data = [{
                "Pain": l.pain_score,
                "Title": l.title[:40] + "..." if len(l.title) > 40 else l.title,
                "Industry": l.industry or "-",
                "Source": l.source.value,
                "Keywords": len(l.keywords_matched),
                "AI": f"{l.ai_score:.2f}" if l.ai_score else "-"
            } for l in filtered]

            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

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

            # Display saved leads
            data = [{
                "Pain": l.get('pain_score', 0),
                "Title": str(l.get('title', ''))[:40] + "..." if len(str(l.get('title', ''))) > 40 else l.get('title', ''),
                "Industry": l.get('industry', '-') or '-',
                "Source": l.get('source', '-'),
                "Saved": l.get('saved_at', '-')[:10] if l.get('saved_at') else '-'
            } for l in saved_leads[:100]]  # Limit to 100 for performance

            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

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
            else:
                stage = st.selectbox("Filter by stage", ["All"] + [s.value for s in LeadStage])

                if st.button("Load", type="primary"):
                    with st.spinner("Loading..."):
                        contacts = crm.get_all_contacts() if stage == "All" else crm.get_contacts_by_stage(LeadStage(stage))

                    if contacts:
                        data = [{
                            "Name": f"{c.firstname or ''} {c.lastname or ''}".strip() or "-",
                            "Email": c.email or "-",
                            "Company": c.company or "-",
                            "Stage": c.lead_stage.value
                        } for c in contacts]
                        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
                    else:
                        st.markdown("""
                        <div style="background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%);
                                    border-left: 4px solid #6366F1;
                                    border-radius: 12px;
                                    padding: 14px 18px;
                                    text-align: center;">
                            <p style="color: #1E293B; font-weight: 500; margin: 0; font-size: 14px;">
                                No contacts found for this filter
                            </p>
                        </div>
                        """, unsafe_allow_html=True)


def show_analytics():
    st.markdown("""
    <div class="page-header">
        <h1>Analytics</h1>
        <p>Metrics and performance</p>
    </div>
    """, unsafe_allow_html=True)

    with HubSpotCRM() as crm:
        if not crm.is_configured():
            rate = (len(st.session_state.filtered_leads) / len(st.session_state.leads) * 100) if st.session_state.leads else 0

            st.markdown(f"""
            <div class="metrics-grid" style="grid-template-columns: repeat(3, 1fr);">
                <div class="metric-card">
                    <div class="metric-header">
                        <div class="metric-icon primary">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4F46E5" stroke-width="2">
                                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                                <circle cx="9" cy="7" r="4"/>
                                <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                                <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                            </svg>
                        </div>
                    </div>
                    <div class="metric-content">
                        <div class="metric-label">Found</div>
                        <div class="metric-value">{len(st.session_state.leads)}</div>
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-header">
                        <div class="metric-icon success">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2">
                                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                                <polyline points="22 4 12 14.01 9 11.01"/>
                            </svg>
                        </div>
                    </div>
                    <div class="metric-content">
                        <div class="metric-label">Qualified</div>
                        <div class="metric-value">{len(st.session_state.filtered_leads)}</div>
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-header">
                        <div class="metric-icon accent">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#EA580C" stroke-width="2">
                                <path d="M18 20V10"/>
                                <path d="M12 20V4"/>
                                <path d="M6 20v-6"/>
                            </svg>
                        </div>
                    </div>
                    <div class="metric-content">
                        <div class="metric-label">Conv. Rate</div>
                        <div class="metric-value">{rate:.0f}%</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.session_state.leads:
                st.markdown("<div style='height: 32px'></div>", unsafe_allow_html=True)
                st.markdown("""
                <div class="section">
                    <div class="section-header">
                        <div class="section-title">
                            <h2>By Source</h2>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                counts = {}
                for l in st.session_state.leads:
                    counts[l.source.value] = counts.get(l.source.value, 0) + 1
                st.bar_chart(counts)

            st.markdown("""
            <div style="background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%);
                        border-left: 4px solid #6366F1;
                        border-radius: 12px;
                        padding: 14px 18px;
                        margin-top: 16px;">
                <p style="color: #1E293B; font-weight: 500; margin: 0; font-size: 14px;">
                    Connect HubSpot in Settings to view complete CRM statistics
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            with st.spinner("Loading..."):
                stats = crm.get_statistics()

            if "error" not in stats:
                st.markdown(f"""
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-header">
                            <div class="metric-icon primary">
                                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4F46E5" stroke-width="2">
                                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                                    <circle cx="9" cy="7" r="4"/>
                                </svg>
                            </div>
                        </div>
                        <div class="metric-content">
                            <div class="metric-label">Total Leads</div>
                            <div class="metric-value">{stats["total_leads"]}</div>
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-header">
                            <div class="metric-icon accent">
                                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#EA580C" stroke-width="2">
                                    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
                                    <polyline points="17 6 23 6 23 12"/>
                                </svg>
                            </div>
                        </div>
                        <div class="metric-content">
                            <div class="metric-label">Conversion</div>
                            <div class="metric-value">{stats['conversion_rate']}%</div>
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-header">
                            <div class="metric-icon success">
                                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2">
                                    <path d="M12 20V10"/>
                                    <path d="M18 20V4"/>
                                    <path d="M6 20v-4"/>
                                </svg>
                            </div>
                        </div>
                        <div class="metric-content">
                            <div class="metric-label">Win Rate</div>
                            <div class="metric-value">{stats['win_rate']}%</div>
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-header">
                            <div class="metric-icon success">
                                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2">
                                    <circle cx="12" cy="8" r="7"/>
                                    <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>
                                </svg>
                            </div>
                        </div>
                        <div class="metric-content">
                            <div class="metric-label">Won</div>
                            <div class="metric-value">{stats["by_stage"].get("closed_won", 0)}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if stats["by_stage"]:
                    st.markdown("<div style='height: 32px'></div>", unsafe_allow_html=True)
                    st.markdown("""
                    <div class="section">
                        <div class="section-header">
                            <div class="section-title">
                                <h2>By Stage</h2>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.bar_chart(stats["by_stage"])


def show_crm():
    """Professional CRM with complete pipeline management."""

    # CRM-specific CSS
    st.markdown("""
    <style>
        /* CRM Dashboard Cards */
        .crm-kpi-card {
            background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
            border: 1px solid #E2E8F0;
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .crm-kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
        }
        .crm-kpi-value {
            font-size: 32px;
            font-weight: 700;
            color: #1E293B;
            margin: 8px 0;
        }
        .crm-kpi-label {
            font-size: 13px;
            color: #64748B;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .crm-kpi-icon {
            font-size: 28px;
            margin-bottom: 8px;
        }

        /* Pipeline Stage Header */
        .pipeline-stage {
            background: linear-gradient(180deg, #F8FAFC 0%, #FFFFFF 100%);
            border-radius: 12px;
            padding: 16px 12px;
            text-align: center;
            margin-bottom: 12px;
            border: 1px solid #E2E8F0;
        }
        .pipeline-stage-title {
            font-weight: 700;
            font-size: 14px;
            margin: 6px 0 2px 0;
        }
        .pipeline-stage-count {
            font-size: 11px;
            color: #64748B;
        }

        /* Lead Card */
        .lead-card {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 14px;
            margin-bottom: 10px;
            transition: all 0.2s ease;
            cursor: pointer;
        }
        .lead-card:hover {
            border-color: #3B82F6;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
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
            color: #1E293B;
            margin: 0;
            line-height: 1.3;
        }
        .lead-card-company {
            font-size: 11px;
            color: #64748B;
            margin: 4px 0 0 0;
        }
        .lead-card-score {
            background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
            color: white;
            font-size: 10px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 12px;
        }
        .lead-card-info {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 10px;
        }
        .lead-card-tag {
            background: #F1F5F9;
            color: #475569;
            font-size: 10px;
            padding: 3px 8px;
            border-radius: 6px;
        }
        .lead-card-actions {
            display: flex;
            gap: 4px;
            margin-top: 12px;
            padding-top: 10px;
            border-top: 1px solid #F1F5F9;
        }
        .lead-action-btn {
            flex: 1;
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            padding: 6px;
            font-size: 12px;
            cursor: pointer;
            text-align: center;
            transition: all 0.2s ease;
        }
        .lead-action-btn:hover {
            background: #3B82F6;
            color: white;
            border-color: #3B82F6;
        }

        /* Contact Detail Card */
        .contact-detail-card {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 16px;
        }
        .contact-header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 1px solid #F1F5F9;
        }
        .contact-avatar {
            width: 64px;
            height: 64px;
            background: linear-gradient(135deg, #3B82F6 0%, #8B5CF6 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            font-weight: 700;
        }
        .contact-name {
            font-size: 20px;
            font-weight: 700;
            color: #1E293B;
            margin: 0;
        }
        .contact-company {
            font-size: 14px;
            color: #64748B;
            margin: 4px 0 0 0;
        }

        /* Activity Timeline */
        .activity-item {
            display: flex;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid #F1F5F9;
        }
        .activity-icon {
            width: 32px;
            height: 32px;
            background: #F1F5F9;
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
            color: #1E293B;
            margin: 0;
        }
        .activity-time {
            font-size: 11px;
            color: #94A3B8;
            margin-top: 4px;
        }

        /* Quick Action Buttons */
        .quick-action-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-top: 16px;
        }
        .quick-action-btn {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .quick-action-btn:hover {
            border-color: #3B82F6;
            background: #EFF6FF;
        }
        .quick-action-icon {
            font-size: 24px;
            margin-bottom: 8px;
        }
        .quick-action-label {
            font-size: 12px;
            font-weight: 500;
            color: #475569;
        }
    </style>
    """, unsafe_allow_html=True)

    # CRM Stage definitions
    CRM_STAGES = {
        'new': {'name': 'New', 'icon': '📥', 'color': '#3B82F6', 'bg': '#EFF6FF'},
        'contacted': {'name': 'Contacted', 'icon': '📧', 'color': '#8B5CF6', 'bg': '#F5F3FF'},
        'demo': {'name': 'Demo', 'icon': '🎯', 'color': '#F59E0B', 'bg': '#FFFBEB'},
        'proposal': {'name': 'Proposal', 'icon': '📋', 'color': '#EC4899', 'bg': '#FDF2F8'},
        'won': {'name': 'Won', 'icon': '✅', 'color': '#10B981', 'bg': '#ECFDF5'},
        'lost': {'name': 'Lost', 'icon': '❌', 'color': '#EF4444', 'bg': '#FEF2F2'}
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

    # Page Header
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
        <div>
            <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #1E293B;">CRM Pipeline</h1>
            <p style="margin: 4px 0 0 0; color: #64748B;">Manage your sales pipeline and track deals</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Empty state
    if not all_leads:
        st.markdown("""
        <div style="text-align: center; padding: 60px 20px; background: #F8FAFC; border-radius: 16px; border: 2px dashed #E2E8F0;">
            <div style="font-size: 48px; margin-bottom: 16px;">📋</div>
            <h3 style="margin: 0 0 8px 0; color: #1E293B; font-size: 20px;">No leads in your CRM</h3>
            <p style="margin: 0; color: #64748B;">Import leads or search for new leads to start building your pipeline</p>
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

    # KPI Dashboard
    st.markdown("### Dashboard")
    kpi_cols = st.columns(6)

    kpi_data = [
        ("📊", "Total Leads", total_leads, "#3B82F6"),
        ("🔥", "Active", active_count, "#F59E0B"),
        ("📈", "Win Rate", f"{win_rate:.0f}%", "#10B981"),
        ("✅", "Won", won_count, "#10B981"),
        ("❌", "Lost", lost_count, "#EF4444"),
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

    # Main CRM Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎯 Pipeline", "👥 All Contacts", "📝 Activities", "⚡ Quick Actions", "🔗 HubSpot"])

    # ==================== TAB 1: PIPELINE VIEW ====================
    with tab1:
        st.markdown("### Sales Pipeline")

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
                stage_leads = [l for l in all_leads if l.get('status', 'new') == stage_key]

                # Show leads
                for idx, lead in enumerate(stage_leads[:8]):
                    lead_hash = lead.get('hash', '')
                    lead_title = lead.get('title', lead.get('company', 'Unknown'))[:30]
                    lead_company = lead.get('company', '')[:20]
                    lead_email = lead.get('email', '')
                    pain_score = lead.get('pain_score', 0)

                    # Lead card
                    st.markdown(f"""
                    <div class="lead-card">
                        <div class="lead-card-header">
                            <div>
                                <p class="lead-card-title">{lead_title}</p>
                                {f'<p class="lead-card-company">{lead_company}</p>' if lead_company else ''}
                            </div>
                            <span class="lead-card-score">{pain_score}</span>
                        </div>
                        <div class="lead-card-info">
                            {f'<span class="lead-card-tag">📧 {lead_email[:20]}</span>' if lead_email else ''}
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
        st.markdown("### Contact Database")

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
                    stage = lead.get('status', 'new')
                    stage_info = CRM_STAGES.get(stage, CRM_STAGES['new'])
                    table_data.append({
                        'Status': f"{stage_info['icon']} {stage_info['name']}",
                        'Name': lead.get('title', '')[:40],
                        'Email': lead.get('email', ''),
                        'Phone': lead.get('phone', ''),
                        'Company': lead.get('company', '')[:30],
                        'Position': lead.get('position', '')[:25],
                        'Location': lead.get('location', ''),
                        'Score': lead.get('pain_score', 0),
                        'Source': lead.get('source', '')[:15],
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
                            st.text_input("👤 Name", value=selected_lead.get('title', ''), key="edit_name", disabled=True)
                            st.text_input("📧 Email", value=selected_lead.get('email', ''), key="edit_email", disabled=True)
                            st.text_input("📱 Phone", value=selected_lead.get('phone', ''), key="edit_phone", disabled=True)
                            st.text_input("🔗 LinkedIn", value=selected_lead.get('linkedin', ''), key="edit_linkedin", disabled=True)

                        with detail_col2:
                            st.markdown("**Business Information**")
                            st.text_input("🏢 Company", value=selected_lead.get('company', ''), key="edit_company", disabled=True)
                            st.text_input("💼 Position", value=selected_lead.get('position', ''), key="edit_position", disabled=True)
                            st.text_input("🏭 Industry", value=selected_lead.get('industry', ''), key="edit_industry", disabled=True)
                            st.text_input("📍 Location", value=selected_lead.get('location', ''), key="edit_location", disabled=True)

                        with detail_col3:
                            st.markdown("**Status & Actions**")

                            current_status = selected_lead.get('status', 'new')
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
                            current_notes = selected_lead.get('notes', '')
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
                        lead_hash = lead.get('hash', '')
                        lead_title = lead.get('title', 'Unknown')
                        lead_email = lead.get('email', 'No email')
                        lead_phone = lead.get('phone', '')
                        lead_company = lead.get('company', '')
                        lead_status = lead.get('status', 'new')
                        pain_score = lead.get('pain_score', 0)

                        stage_info = CRM_STAGES.get(lead_status, CRM_STAGES['new'])

                        with st.container(border=True):
                            # Card header
                            header_col1, header_col2 = st.columns([3, 1])
                            with header_col1:
                                st.markdown(f"**{lead_title[:35]}**")
                                st.caption(f"{lead_company[:25]}" if lead_company else "No company")
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

    # ==================== TAB 3: ACTIVITIES ====================
    with tab3:
        st.markdown("### Activity Feed")

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

    # ==================== TAB 4: QUICK ACTIONS ====================
    with tab4:
        st.markdown("### Quick Actions")

        # Bulk Actions
        st.markdown("#### 📦 Bulk Operations")

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
            if st.button(f"Move {from_count} leads", type="primary", use_container_width=True):
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

        st.markdown("---")

        # Quick Stats
        st.markdown("#### 📊 Pipeline Health")

        health_cols = st.columns(4)

        with health_cols[0]:
            conversion = (won_count / total_leads * 100) if total_leads > 0 else 0
            st.metric("Conversion Rate", f"{conversion:.1f}%", help="Percentage of leads that became customers")

        with health_cols[1]:
            in_progress = status_counts.get('contacted', 0) + status_counts.get('demo', 0) + status_counts.get('proposal', 0)
            st.metric("In Progress", in_progress, help="Leads being actively worked")

        with health_cols[2]:
            new_leads = status_counts.get('new', 0)
            st.metric("Uncontacted", new_leads, help="New leads not yet contacted")

        with health_cols[3]:
            hot_leads = len([l for l in all_leads if l.get('pain_score', 0) >= 70])
            st.metric("Hot Leads", hot_leads, help="Leads with score >= 70")

        st.markdown("---")

        # Stage distribution chart
        st.markdown("#### 📈 Stage Distribution")

        chart_data = {CRM_STAGES[k]['name']: v for k, v in status_counts.items()}
        st.bar_chart(chart_data)

    # ==================== TAB 5: HUBSPOT ====================
    with tab5:
        st.markdown("### HubSpot Integration")

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
    # Page Title
    st.title("⚙️ Settings")
    st.caption("APIs and system parameters")

    st.divider()

    # API Integrations Section
    st.subheader("🔗 API Integrations")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        with st.container(border=True):
            st.markdown("### 📊 HubSpot")
            if settings.hubspot_api_key:
                st.success("✓ Connected")
            else:
                st.warning("Not configured")

    with col2:
        with st.container(border=True):
            st.markdown("### 🔍 Google")
            if settings.google_api_key:
                st.success("✓ Connected")
            else:
                st.warning("Not configured")

    with col3:
        with st.container(border=True):
            st.markdown("### 🤖 OpenAI")
            if settings.openai_api_key:
                st.success("✓ Connected")
            else:
                st.warning("Not configured")

    with col4:
        with st.container(border=True):
            st.markdown("### 🧠 Anthropic")
            if settings.anthropic_api_key:
                st.success("✓ Connected")
            else:
                st.warning("Not configured")

    # Second row of APIs
    col5, col6, col7, col8 = st.columns(4)

    with col5:
        with st.container(border=True):
            st.markdown("### 📧 Hunter.io")
            if settings.hunter_api_key:
                st.success("✓ Connected")
            else:
                st.info("Optional - Email Finder")

    with col6:
        # Storage stats
        with st.container(border=True):
            st.markdown("### 💾 Storage")
            stats = lead_manager.get_stats()
            st.metric("Saved Leads", stats['total'])

    with col7:
        # Deduplication stats
        with st.container(border=True):
            st.markdown("### 🔄 Deduplication")
            st.success("✓ Active")

    with col8:
        # Export status
        with st.container(border=True):
            st.markdown("### 📥 CSV Export")
            st.success("✓ Available")

    st.divider()

    # Industries Section
    st.subheader(f"🏢 Industries Configured ({len(settings.industries)})")

    industry_list = list(settings.industries.keys())
    cols = st.columns(5)
    for i, ind in enumerate(industry_list):
        with cols[i % 5]:
            st.markdown(f"• {ind}")

    st.divider()

    # Subreddits Section
    st.subheader(f"📱 Subreddits ({len(settings.subreddits)} total)")

    with st.expander("View all subreddits"):
        sub_text = ", ".join([f"r/{s}" for s in settings.subreddits])
        st.write(sub_text)

    st.divider()

    # Keywords Section
    st.subheader(f"🔑 Pain Keywords ({len(settings.pain_keywords)} total)")

    with st.expander("View all keywords"):
        kw_text = ", ".join(settings.pain_keywords)
        st.write(kw_text)

    st.divider()

    # Configuration Info
    st.info("**How to configure API keys:** Go to your Streamlit Cloud dashboard → Settings → Secrets to add or update your API credentials securely.")


# ============================================
# MAIN
# ============================================
def main():
    render_sidebar()

    page = st.session_state.nav_page

    if page == "Dashboard":
        show_dashboard()
    elif page == "Find Leads":
        show_search()
    elif page == "My Leads":
        show_leads()
    elif page == "CRM":
        show_crm()
    elif page == "Analytics":
        show_analytics()
    elif page == "Settings":
        show_config()


if __name__ == "__main__":
    main()
