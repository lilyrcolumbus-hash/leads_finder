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
from src.utils.background_tasks import task_manager, TaskStatus
from src.scrapers import RedditScraper, HackerNewsScraper, GoogleScraper, ProductHuntScraper, IndeedScraper, YelpScraper, LinkedInScraper, GoogleMapsScraper
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

    /* ========== BUTTONS - MODERN PREMIUM DESIGN ========== */

    /* Base button reset and foundation */
    .stButton > button {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        letter-spacing: 0.02em !important;
        padding: 12px 24px !important;
        border-radius: 10px !important;
        cursor: pointer !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative !important;
        overflow: hidden !important;
        border: none !important;
        outline: none !important;
    }

    /* Primary Button - Vibrant Blue Gradient */
    .stButton > button[kind="primary"],
    .stButton > button:not([kind]) {
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #6366F1 100%) !important;
        color: white !important;
        box-shadow:
            0 4px 15px rgba(79, 70, 229, 0.4),
            0 2px 6px rgba(79, 70, 229, 0.2),
            inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
    }

    .stButton > button[kind="primary"]:hover,
    .stButton > button:not([kind]):hover {
        background: linear-gradient(135deg, #4338CA 0%, #6D28D9 50%, #4F46E5 100%) !important;
        transform: translateY(-3px) scale(1.02) !important;
        box-shadow:
            0 8px 25px rgba(79, 70, 229, 0.5),
            0 4px 12px rgba(79, 70, 229, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
    }

    .stButton > button[kind="primary"]:active,
    .stButton > button:not([kind]):active {
        transform: translateY(-1px) scale(1) !important;
        box-shadow:
            0 4px 12px rgba(79, 70, 229, 0.4),
            0 2px 4px rgba(79, 70, 229, 0.2) !important;
    }

    /* Secondary Button - Elegant Glass Effect */
    .stButton > button[kind="secondary"] {
        background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(248,250,252,0.95) 100%) !important;
        color: #334155 !important;
        border: 1.5px solid #E2E8F0 !important;
        box-shadow:
            0 2px 8px rgba(15, 23, 42, 0.06),
            0 1px 3px rgba(15, 23, 42, 0.04),
            inset 0 1px 0 rgba(255, 255, 255, 0.8) !important;
        backdrop-filter: blur(8px) !important;
    }

    .stButton > button[kind="secondary"]:hover {
        background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%) !important;
        color: #4F46E5 !important;
        border-color: #C7D2FE !important;
        transform: translateY(-2px) !important;
        box-shadow:
            0 6px 20px rgba(79, 70, 229, 0.15),
            0 3px 8px rgba(79, 70, 229, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 1) !important;
    }

    .stButton > button[kind="secondary"]:active {
        transform: translateY(0) !important;
    }

    /* Tertiary/Ghost Button - Minimal Style */
    .stButton > button[kind="tertiary"] {
        background: transparent !important;
        color: #64748B !important;
        border: none !important;
        box-shadow: none !important;
        padding: 10px 16px !important;
    }

    .stButton > button[kind="tertiary"]:hover {
        background: rgba(79, 70, 229, 0.08) !important;
        color: #4F46E5 !important;
    }

    /* Icon-only buttons (small square buttons) */
    .stButton > button:has(span:only-child) {
        padding: 10px 12px !important;
        min-width: 40px !important;
    }

    /* Download buttons - Special Style */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #059669 0%, #10B981 50%, #34D399 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px 24px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        box-shadow:
            0 4px 15px rgba(16, 185, 129, 0.35),
            0 2px 6px rgba(16, 185, 129, 0.2),
            inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #047857 0%, #059669 50%, #10B981 100%) !important;
        transform: translateY(-2px) scale(1.02) !important;
        box-shadow:
            0 8px 25px rgba(16, 185, 129, 0.45),
            0 4px 12px rgba(16, 185, 129, 0.25) !important;
    }

    /* Link buttons */
    .stLinkButton > a {
        background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(248,250,252,0.9) 100%) !important;
        color: #4F46E5 !important;
        border: 1.5px solid #C7D2FE !important;
        border-radius: 10px !important;
        padding: 10px 20px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        text-decoration: none !important;
        transition: all 0.25s ease !important;
        box-shadow: 0 2px 8px rgba(79, 70, 229, 0.1) !important;
    }

    .stLinkButton > a:hover {
        background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%) !important;
        color: white !important;
        border-color: #4F46E5 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(79, 70, 229, 0.3) !important;
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
        background: linear-gradient(135deg, #CBD5E1 0%, #E2E8F0 100%) !important;
        color: #94A3B8 !important;
        cursor: not-allowed !important;
        transform: none !important;
        box-shadow: none !important;
        opacity: 0.7 !important;
    }

    /* Full width button refinement */
    .stButton > button[data-testid="baseButton-secondary"],
    .stButton > button[data-testid="baseButton-primary"] {
        width: 100% !important;
    }

    /* Button ripple effect on click */
    .stButton > button::after {
        content: '' !important;
        position: absolute !important;
        top: 50% !important;
        left: 50% !important;
        width: 0 !important;
        height: 0 !important;
        background: rgba(255, 255, 255, 0.3) !important;
        border-radius: 50% !important;
        transform: translate(-50%, -50%) !important;
        transition: width 0.4s ease, height 0.4s ease !important;
    }

    .stButton > button:active::after {
        width: 200px !important;
        height: 200px !important;
    }

    /* ========== BUTTON TYPE CLASSES ========== */

    /* Success buttons - Green */
    .btn-success button,
    [data-testid*="success"] button {
        background: linear-gradient(135deg, #059669 0%, #10B981 50%, #34D399 100%) !important;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4) !important;
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
        pages = ["Dashboard", "Find Leads", "My Leads", "Lead Warming", "CRM", "Analytics", "AI Assistant", "Settings"]
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
    hot_leads_count = len([l for l in st.session_state.filtered_leads if getattr(l, 'total_score', l.pain_score) >= 80])
    keywords_count = len(settings.pain_keywords)
    sources_count = sum([1 for x in [True, True, bool(settings.google_api_key), True] if x])
    conv_rate = int((qualified_count / leads_count * 100)) if leads_count > 0 else 0
    avg_total_score = sum(getattr(l, 'total_score', l.pain_score) for l in st.session_state.filtered_leads) / len(st.session_state.filtered_leads) if st.session_state.filtered_leads else 0

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
                <span class="metric-tag" style="background: var(--error-50); color: var(--error-500);">Total Score 80+</span>
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
    st.subheader("📡 Active Sources (8 Available)")

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

    st.info("💡 **Google Maps** busca negocios locales (dentistas, HVAC, abogados) y extrae teléfono, website y email. **GRATIS** - no usa API.")

    st.divider()

    # Coming Soon Sources
    st.subheader("🚀 Coming Soon (2 More)")

    coming_cols = st.columns(2)
    coming_sources = [
        ("🐦", "Twitter/X"),
        ("📘", "Facebook Groups")
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

    # Location Filter
    st.subheader("📍 Location Filter (for Indeed & Yelp)")

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
        st.success(f"📍 Searching in: **{search_location}**")

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
            except Exception as e:
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

            with st.expander(f"{grade_emoji} [{total_score}] {lead.title[:55]}..."):
                # Triple Score Display
                st.markdown(f"""
                <div style="display: flex; gap: 12px; margin-bottom: 16px;">
                    <!-- Total Score (Large) -->
                    <div style="flex: 1; text-align: center; padding: 16px; background: {grade_bg}; border-radius: 12px; border: 2px solid {grade_color};">
                        <div style="font-size: 36px; font-weight: 800; color: {grade_color};">{total_score}</div>
                        <div style="font-size: 11px; font-weight: 700; color: {grade_color}; letter-spacing: 0.5px;">{grade_emoji} {grade_label}</div>
                        <div style="font-size: 10px; color: #64748B; margin-top: 4px;">TOTAL SCORE</div>
                    </div>
                    <!-- Individual Scores -->
                    <div style="flex: 2; display: flex; flex-direction: column; gap: 8px;">
                        <div style="display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #FEE2E2; border-radius: 8px;">
                            <span style="font-size: 16px;">😣</span>
                            <div style="flex: 1;">
                                <div style="font-size: 10px; color: #991B1B; font-weight: 600;">PAIN</div>
                                <div style="height: 6px; background: #FECACA; border-radius: 3px; overflow: hidden;">
                                    <div style="width: {pain_score}%; height: 100%; background: #EF4444;"></div>
                                </div>
                            </div>
                            <span style="font-size: 14px; font-weight: 700; color: #DC2626;">{pain_score}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #FEF3C7; border-radius: 8px;">
                            <span style="font-size: 16px;">🎯</span>
                            <div style="flex: 1;">
                                <div style="font-size: 10px; color: #92400E; font-weight: 600;">INTENT</div>
                                <div style="height: 6px; background: #FDE68A; border-radius: 3px; overflow: hidden;">
                                    <div style="width: {intent_score}%; height: 100%; background: #F59E0B;"></div>
                                </div>
                            </div>
                            <span style="font-size: 14px; font-weight: 700; color: #D97706;">{intent_score}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #DBEAFE; border-radius: 8px;">
                            <span style="font-size: 16px;">✅</span>
                            <div style="flex: 1;">
                                <div style="font-size: 10px; color: #1E40AF; font-weight: 600;">FIT</div>
                                <div style="height: 6px; background: #BFDBFE; border-radius: 3px; overflow: hidden;">
                                    <div style="width: {fit_score}%; height: 100%; background: #3B82F6;"></div>
                                </div>
                            </div>
                            <span style="font-size: 14px; font-weight: 700; color: #2563EB;">{fit_score}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Lead Details
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Source:** {lead.source.value}")
                    st.write(f"**Industry:** {lead.industry or 'Unknown'}")
                with col2:
                    st.write(f"**Action:** {grade['action']}")
                    st.write(f"**Keywords:** {len(lead.keywords_matched)}")

                if lead.keywords_matched:
                    st.write(f"**Matched:** {', '.join(lead.keywords_matched[:5])}")
                st.link_button("View Original", lead.url)
                st.write("---")
                st.caption(lead.content[:350] + "...")

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
                    with st.spinner("Loading..."):
                        contacts = crm.get_all_contacts() if stage == "All" else crm.get_contacts_by_stage(LeadStage(stage))

                    if contacts:
                        st.success(f"Found {len(contacts)} contacts in HubSpot")
                        data = [{
                            "Name": f"{c.firstname or ''} {c.lastname or ''}".strip() or "-",
                            "Email": c.email or "-",
                            "Company": c.company or "-",
                            "Stage": c.lead_stage.value
                        } for c in contacts]
                        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
                    else:
                        st.info("No contacts found in HubSpot for this filter")


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
    """Professional CRM with complete pipeline management, deals, tasks, and HubSpot sync."""

    # Enhanced CRM-specific CSS
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

        /* Revenue Card */
        .revenue-card {
            background: linear-gradient(135deg, #10B981 0%, #059669 100%);
            border-radius: 16px;
            padding: 24px;
            color: white;
            text-align: center;
        }
        .revenue-value {
            font-size: 36px;
            font-weight: 800;
            margin: 8px 0;
        }
        .revenue-label {
            font-size: 14px;
            opacity: 0.9;
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

        /* Deal Card */
        .deal-card {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            transition: all 0.2s ease;
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
        st.markdown("### Deals & Opportunities")

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
        st.markdown("### Task Management")

        # Task quick stats
        today = datetime.now().date()
        overdue_tasks = [t for t in st.session_state.crm_tasks if not t.get('completed') and t.get('due_date') and datetime.fromisoformat(t.get('due_date')).date() < today]
        today_tasks = [t for t in st.session_state.crm_tasks if not t.get('completed') and t.get('due_date') and datetime.fromisoformat(t.get('due_date')).date() == today]
        upcoming_tasks = [t for t in st.session_state.crm_tasks if not t.get('completed') and t.get('due_date') and datetime.fromisoformat(t.get('due_date')).date() > today]
        completed_tasks = [t for t in st.session_state.crm_tasks if t.get('completed')]

        task_stat_cols = st.columns(4)
        with task_stat_cols[0]:
            st.metric("Overdue", len(overdue_tasks), delta=None, delta_color="inverse")
        with task_stat_cols[1]:
            st.metric("Due Today", len(today_tasks))
        with task_stat_cols[2]:
            st.metric("Upcoming", len(upcoming_tasks))
        with task_stat_cols[3]:
            st.metric("Completed", len(completed_tasks))

        st.markdown("---")

        # Create new task
        st.markdown("#### Create New Task")
        with st.expander("➕ Add New Task", expanded=False):
            task_col1, task_col2 = st.columns(2)

            with task_col1:
                task_title = st.text_input("Task Title", placeholder="e.g., Follow up with John")
                task_description = st.text_area("Description", placeholder="Optional notes...", height=80)

            with task_col2:
                task_type = st.selectbox("Type", ["📞 Call", "📧 Email", "📅 Meeting", "📝 Note", "✅ Other"])
                task_due = st.date_input("Due Date", value=datetime.now(), key="task_due_date")
                task_priority = st.selectbox("Priority", ["🔴 High", "🟡 Medium", "🟢 Low"])
                task_contact = st.selectbox(
                    "Associated Contact",
                    ["None"] + [f"{(l.get('title') or l.get('author') or l.get('company') or 'Unknown')[:25]}" for l in all_leads[:30]],
                    key="task_contact"
                )

            if st.button("💾 Create Task", type="primary", use_container_width=True, key="create_task_btn"):
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
                    st.success(f"Task '{task_title}' created!")
                    st.rerun()
                else:
                    st.warning("Please enter a task title")

        # Task list
        st.markdown("#### Task List")

        task_filter = st.radio("Filter", ["All", "Overdue", "Today", "Upcoming", "Completed"], horizontal=True, key="task_filter")

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

                with st.container(border=True):
                    t_col1, t_col2, t_col3, t_col4 = st.columns([0.5, 3, 2, 1])

                    with t_col1:
                        is_done = st.checkbox("", value=task.get('completed', False), key=f"task_done_{task.get('id')}", label_visibility="collapsed")
                        if is_done != task.get('completed', False):
                            task['completed'] = is_done
                            st.rerun()

                    with t_col2:
                        title_style = "text-decoration: line-through; color: #94A3B8;" if task.get('completed') else ""
                        st.markdown(f"<span style='{title_style}'>{task.get('type', '📝')} **{task.get('title', 'Untitled')}**</span>", unsafe_allow_html=True)
                        if task.get('contact'):
                            st.caption(f"Contact: {task.get('contact')}")

                    with t_col3:
                        due_color = {"overdue": "#EF4444", "today": "#F59E0B", "upcoming": "#3B82F6", "completed": "#94A3B8"}.get(task_status, "#64748B")
                        st.markdown(f"<span style='color: {due_color}; font-size: 12px;'>📅 {task.get('due_date', 'No date')[:10]}</span>", unsafe_allow_html=True)
                        st.caption(task.get('priority', '🟡 Medium'))

                    with t_col4:
                        if st.button("🗑️", key=f"del_task_{task.get('id')}", help="Delete task"):
                            st.session_state.crm_tasks.remove(task)
                            st.rerun()
        else:
            st.info("No tasks match the selected filter.")

    # ==================== TAB 5: EMAIL TEMPLATES ====================
    with tab5:
        st.markdown("### Email Templates & Composer")

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
        st.markdown("### Calendar View")

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
        st.markdown("### Analytics & Activity Feed")

        analytics_subtab1, analytics_subtab2, analytics_subtab3 = st.tabs(["📊 Dashboard", "📝 Activity Feed", "⚡ Quick Actions"])

        with analytics_subtab1:
            st.markdown("#### Pipeline Analytics")

            # Conversion funnel
            st.markdown("##### Conversion Funnel")
            funnel_data = {CRM_STAGES[k]['name']: v for k, v in status_counts.items()}
            st.bar_chart(funnel_data)

            st.markdown("---")

            # Performance metrics
            st.markdown("##### Performance Metrics")
            perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)

            with perf_col1:
                conversion = (won_count / total_leads * 100) if total_leads > 0 else 0
                st.metric("Conversion Rate", f"{conversion:.1f}%")

            with perf_col2:
                in_progress = status_counts.get('contacted', 0) + status_counts.get('demo', 0) + status_counts.get('proposal', 0)
                st.metric("In Progress", in_progress)

            with perf_col3:
                new_leads = status_counts.get('new', 0)
                st.metric("Uncontacted", new_leads)

            with perf_col4:
                hot_leads = len([l for l in all_leads if l.get('pain_score', 0) >= 70])
                st.metric("Hot Leads (70+)", hot_leads)

            st.markdown("---")

            # Source distribution
            st.markdown("##### Lead Sources")
            source_counts = {}
            for lead in all_leads:
                source = lead.get('source', 'Unknown')
                source_counts[source] = source_counts.get(source, 0) + 1

            if source_counts:
                st.bar_chart(source_counts)

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
# AI ASSISTANT
# ============================================
def show_ai_assistant():
    """AI Lead Generation Assistant - Expert advisor for lead generation."""

    # Custom CSS for chat interface
    st.markdown("""
    <style>
        .assistant-header {
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #EC4899 100%);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            color: white;
        }
        .assistant-title {
            font-size: 28px;
            font-weight: 700;
            margin: 0 0 8px 0;
        }
        .assistant-subtitle {
            font-size: 14px;
            opacity: 0.9;
            margin: 0;
        }
        .chat-message {
            padding: 16px;
            border-radius: 12px;
            margin-bottom: 12px;
            animation: fadeIn 0.3s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .user-message {
            background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%);
            border-left: 4px solid #4F46E5;
            margin-left: 40px;
        }
        .assistant-message {
            background: linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%);
            border-left: 4px solid #10B981;
            margin-right: 40px;
        }
        .message-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
            font-weight: 600;
            font-size: 13px;
        }
        .message-content {
            font-size: 14px;
            line-height: 1.6;
            color: #1E293B;
        }
        .quick-action-chip {
            display: inline-block;
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 20px;
            padding: 8px 16px;
            margin: 4px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .quick-action-chip:hover {
            background: #4F46E5;
            color: white;
            border-color: #4F46E5;
        }
        .stats-card {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        }
        .stats-value {
            font-size: 24px;
            font-weight: 700;
            color: #4F46E5;
        }
        .stats-label {
            font-size: 12px;
            color: #64748B;
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

    # Lead Warming CSS
    st.markdown("""
    <style>
        /* Temperature Indicators */
        .temp-cold {
            background: linear-gradient(135deg, #60A5FA 0%, #3B82F6 100%);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .temp-warm {
            background: linear-gradient(135deg, #FBBF24 0%, #F59E0B 100%);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .temp-hot {
            background: linear-gradient(135deg, #F87171 0%, #EF4444 100%);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }

        /* Warming Card */
        .warming-card {
            background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
            border: 1px solid #E2E8F0;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 16px;
            transition: all 0.3s ease;
        }
        .warming-card:hover {
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
            transform: translateY(-2px);
        }

        /* Activity Timeline */
        .activity-timeline {
            border-left: 3px solid #E2E8F0;
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
            background: #3B82F6;
            border-radius: 50%;
            border: 2px solid white;
        }
        .activity-completed::before {
            background: #10B981;
        }
        .activity-pending::before {
            background: #94A3B8;
        }

        /* Warming Stats */
        .warming-stat-card {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        }
        .warming-stat-value {
            font-size: 28px;
            font-weight: 700;
            color: #1E293B;
        }
        .warming-stat-label {
            font-size: 12px;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* Progress Ring */
        .progress-ring {
            width: 80px;
            height: 80px;
            margin: 0 auto;
        }

        /* Warming Actions */
        .warming-action-btn {
            background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
            color: white;
            border: none;
            padding: 10px 16px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .warming-action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown("""
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;">
        <div>
            <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #1E293B;">🔥 Lead Warming</h1>
            <p style="margin: 8px 0 0 0; color: #64748B;">Warm up leads before cold outreach for +300% higher response rates</p>
        </div>
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

    # Stats Row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="warming-stat-card">
            <div style="font-size: 24px; margin-bottom: 8px;">❄️</div>
            <div class="warming-stat-value">{len(cold_leads)}</div>
            <div class="warming-stat-label">Cold Leads</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="warming-stat-card">
            <div style="font-size: 24px; margin-bottom: 8px;">🌡️</div>
            <div class="warming-stat-value">{len(warm_leads)}</div>
            <div class="warming-stat-label">Warm Leads</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="warming-stat-card">
            <div style="font-size: 24px; margin-bottom: 8px;">🔥</div>
            <div class="warming-stat-value">{len(hot_leads)}</div>
            <div class="warming-stat-label">Hot Leads</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="warming-stat-card">
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
        st.markdown("### Engagement Tools")
        st.caption("Templates and tools to help you warm up leads effectively")

        tool_col1, tool_col2 = st.columns(2)

        with tool_col1:
            st.markdown("#### 💬 Comment Templates")
            st.caption("Copy these templates for LinkedIn comments")

            comment_templates = [
                {
                    "type": "Agreement",
                    "template": "Great insight! I've seen this in my work too - [specific example]. Thanks for sharing.",
                },
                {
                    "type": "Question",
                    "template": "Interesting perspective. Have you found that [related question]? I'd love to hear your thoughts.",
                },
                {
                    "type": "Value Add",
                    "template": "This resonates with me. I'd add that [additional point] can also help. What do you think?",
                },
                {
                    "type": "Industry Specific",
                    "template": "As someone in [industry], I appreciate this take. We're seeing [relevant trend] as well.",
                },
            ]

            for template in comment_templates:
                with st.expander(f"📝 {template['type']}"):
                    st.code(template['template'], language=None)
                    if st.button(f"Copy", key=f"copy_{template['type']}"):
                        st.toast("Template copied!")

        with tool_col2:
            st.markdown("#### 🤝 Connection Request Templates")
            st.caption("Personalized connection request messages")

            connection_templates = [
                {
                    "type": "Mutual Interest",
                    "template": "Hi [Name], I noticed we're both interested in [topic]. I'd love to connect and exchange insights. Looking forward to learning from your experience in [industry].",
                },
                {
                    "type": "Content Appreciation",
                    "template": "Hi [Name], I've been following your posts about [topic] and find them really valuable. Would love to connect and stay updated on your insights.",
                },
                {
                    "type": "Industry Peer",
                    "template": "Hi [Name], As a fellow professional in [industry], I'd love to connect. Your work at [Company] looks impressive. Let's stay in touch!",
                },
            ]

            for template in connection_templates:
                with st.expander(f"📝 {template['type']}"):
                    st.code(template['template'], language=None)
                    if st.button(f"Copy", key=f"copy_conn_{template['type']}"):
                        st.toast("Template copied!")

        st.divider()

        st.markdown("#### 📧 Follow-up Email Template (After Warming)")
        st.caption("Use this after completing the 7-day warming process")

        email_template = """Subject: Following up on our LinkedIn connection

Hi [Name],

I hope this message finds you well! We connected on LinkedIn recently, and I've really enjoyed your insights on [topic they posted about].

I noticed that [Company] is in the [industry] space, and I wanted to reach out because we help businesses like yours [value proposition].

[Specific observation about their company/role that shows you've done your research]

Would you be open to a quick 15-minute call to explore if there might be a fit? I'd love to learn more about your current priorities and see if we can help.

Best regards,
[Your Name]

P.S. [Reference something specific from their recent LinkedIn activity]"""

        st.code(email_template, language=None)

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


def main():
    render_sidebar()

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
