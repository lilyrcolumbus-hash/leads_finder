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
# PREMIUM CSS - Ultra Modern Design System
# ============================================
st.markdown("""
<style>
    /* ========== HIDE KEYBOARD SHORTCUTS (PRIORITY) ========== */
    *[class*="keyboard"],
    *[id*="keyboard"],
    *[data-testid*="keyboard"],
    *[aria-label*="keyboard"],
    div[class*="Keyboard"],
    button[title*="keyboard"],
    [data-testid="stKeyboardShortcuts"],
    .stKeyboardShortcut {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        height: 0 !important;
        width: 0 !important;
        position: absolute !important;
        left: -9999px !important;
    }

    /* ========== FONTS ========== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* ========== CSS VARIABLES ========== */
    :root {
        --primary-50: #EEF2FF;
        --primary-100: #E0E7FF;
        --primary-200: #C7D2FE;
        --primary-500: #6366F1;
        --primary-600: #4F46E5;
        --primary-700: #4338CA;

        --accent-50: #FFF7ED;
        --accent-100: #FFEDD5;
        --accent-500: #F97316;
        --accent-600: #EA580C;

        --neutral-50: #FAFAFA;
        --neutral-100: #F5F5F5;
        --neutral-200: #E5E5E5;
        --neutral-300: #D4D4D4;
        --neutral-400: #A3A3A3;
        --neutral-500: #737373;
        --neutral-600: #525252;
        --neutral-700: #404040;
        --neutral-800: #262626;
        --neutral-900: #171717;

        --success-50: #ECFDF5;
        --success-500: #10B981;
        --success-600: #059669;

        --warning-50: #FFFBEB;
        --warning-500: #F59E0B;

        --error-50: #FEF2F2;
        --error-500: #EF4444;

        --white: #FFFFFF;
        --radius-xl: 20px;
        --radius-lg: 16px;
        --radius-md: 12px;
        --radius-sm: 8px;
        --radius-xs: 6px;

        --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
        --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
        --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
    }

    /* ========== GLOBAL ========== */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        font-feature-settings: "cv02", "cv03", "cv04", "cv11";
    }

    .main {
        background: linear-gradient(135deg, var(--neutral-50) 0%, #F8FAFC 100%) !important;
    }

    .main .block-container {
        padding: 2.5rem 3.5rem 4rem 3.5rem !important;
        max-width: 1280px !important;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.025em !important;
        line-height: 1.2 !important;
    }

    p, span, div, label {
        font-family: 'Inter', sans-serif !important;
        letter-spacing: -0.011em !important;
    }

    /* Hide Streamlit elements */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}

    /* ========== SIDEBAR - LIGHT THEME ========== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%) !important;
        border-right: 1px solid #E5E7EB !important;
        padding: 0 !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding: 0 !important;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #6B7280 !important;
    }

    /* Sidebar Radio Navigation */
    [data-testid="stSidebar"] .stRadio > label {
        display: none !important;
    }

    [data-testid="stSidebar"] .stRadio > div {
        gap: 2px !important;
        padding: 0 12px !important;
    }

    [data-testid="stSidebar"] .stRadio > div > label {
        background: transparent !important;
        border-radius: var(--radius-sm) !important;
        padding: 12px 14px !important;
        margin: 0 !important;
        color: #6B7280 !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border: none !important;
    }

    [data-testid="stSidebar"] .stRadio > div > label:hover {
        background: #F3F4F6 !important;
        color: #1F2937 !important;
    }

    [data-testid="stSidebar"] .stRadio > div > label[data-checked="true"] {
        background: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-500) 100%) !important;
        color: var(--white) !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4) !important;
    }

    /* ========== LOGO SECTION - LIGHT ========== */
    .logo-section {
        padding: 24px 20px 20px 20px;
        border-bottom: 1px solid #E5E7EB;
        margin-bottom: 4px;
        background: #FFFFFF;
    }

    .logo-container {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .logo-icon {
        width: 42px;
        height: 42px;
        background: linear-gradient(135deg, var(--primary-500) 0%, #818CF8 100%);
        border-radius: var(--radius-sm);
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 8px 20px rgba(99, 102, 241, 0.35);
    }

    .logo-icon svg {
        width: 22px;
        height: 22px;
    }

    .logo-text {
        flex: 1;
    }

    .logo-title {
        color: #1F2937;
        font-size: 18px;
        font-weight: 700;
        letter-spacing: -0.03em;
        margin: 0;
        line-height: 1.2;
    }

    .logo-subtitle {
        color: #9CA3AF;
        font-size: 11px;
        font-weight: 500;
        margin: 2px 0 0 0;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    /* ========== USER CARD - LIGHT ========== */
    .user-card {
        margin: 12px;
        padding: 14px;
        background: #F9FAFB;
        border-radius: var(--radius-sm);
        border: 1px solid #E5E7EB;
        transition: all 0.2s ease;
    }

    .user-card:hover {
        background: #F3F4F6;
        border-color: #D1D5DB;
    }

    .user-info {
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .user-avatar {
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, var(--accent-500) 0%, #FB923C 100%);
        border-radius: var(--radius-xs);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        font-weight: 700;
        color: white;
        box-shadow: 0 4px 12px rgba(249, 115, 22, 0.3);
    }

    .user-details h4 {
        color: #1F2937;
        font-size: 13px;
        font-weight: 600;
        margin: 0 0 2px 0;
    }

    .user-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: linear-gradient(135deg, var(--success-500) 0%, #34D399 100%);
        color: white;
        font-size: 9px;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 20px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    /* ========== NAV LABEL - LIGHT ========== */
    .nav-label {
        padding: 20px 20px 8px 20px;
        font-size: 10px;
        font-weight: 600;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 0.12em;
    }

    /* ========== SIDEBAR FOOTER - LIGHT ========== */
    .sidebar-footer {
        padding: 16px 20px;
        border-top: 1px solid #E5E7EB;
        margin-top: auto;
        background: #FFFFFF;
    }

    .sidebar-stats {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #6B7280;
        font-size: 12px;
    }

    .status-dot {
        width: 7px;
        height: 7px;
        background: var(--success-500);
        border-radius: 50%;
        box-shadow: 0 0 10px var(--success-500);
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    /* ========== PAGE HEADER ========== */
    .page-header {
        margin-bottom: 36px;
        padding-bottom: 24px;
        border-bottom: 1px solid var(--neutral-200);
    }

    .page-header h1 {
        color: var(--neutral-900);
        font-size: 28px;
        font-weight: 800;
        margin: 0 0 6px 0;
        letter-spacing: -0.035em;
    }

    .page-header p {
        color: var(--neutral-500);
        font-size: 15px;
        margin: 0;
        font-weight: 400;
    }

    /* ========== METRIC CARDS ========== */
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 48px;
    }

    @media (max-width: 1000px) {
        .metrics-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }

    .metric-card {
        background: var(--white);
        border-radius: var(--radius-lg);
        padding: 20px 22px;
        border: 1px solid var(--neutral-200);
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }

    .metric-card:hover {
        border-color: var(--primary-200);
        box-shadow: var(--shadow-lg);
        transform: translateY(-4px);
    }

    .metric-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        margin-bottom: 16px;
    }

    .metric-icon {
        width: 44px;
        height: 44px;
        border-radius: var(--radius-sm);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
    }

    .metric-icon.primary { background: var(--primary-50); }
    .metric-icon.accent { background: var(--accent-50); }
    .metric-icon.success { background: var(--success-50); }

    .metric-trend {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 4px 8px;
        background: var(--success-50);
        color: var(--success-600);
        font-size: 11px;
        font-weight: 600;
        border-radius: 20px;
    }

    .metric-content {
        margin-top: 4px;
    }

    .metric-label {
        color: var(--neutral-500);
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 6px;
    }

    .metric-value {
        color: var(--neutral-900);
        font-size: 32px;
        font-weight: 800;
        letter-spacing: -0.04em;
        line-height: 1;
    }

    .metric-footer {
        margin-top: 14px;
        padding-top: 14px;
        border-top: 1px solid var(--neutral-100);
    }

    .metric-tag {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        background: var(--neutral-100);
        color: var(--neutral-600);
        font-size: 11px;
        font-weight: 600;
        border-radius: 20px;
    }

    /* ========== SECTION ========== */
    .section {
        margin-bottom: 48px;
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
        gap: 10px;
    }

    .section-title h2 {
        color: var(--neutral-900);
        font-size: 18px;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.02em;
    }

    .section-badge {
        background: var(--primary-50);
        color: var(--primary-600);
        font-size: 11px;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 20px;
        letter-spacing: 0.02em;
    }

    /* ========== FEATURE CARDS ========== */
    .features-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 14px;
    }

    @media (max-width: 900px) {
        .features-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }

    .feature-card {
        background: var(--white);
        border: 1px solid var(--neutral-200);
        border-radius: var(--radius-lg);
        padding: 20px;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
    }

    .feature-card:hover {
        border-color: var(--primary-200);
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }

    .feature-icon {
        width: 46px;
        height: 46px;
        border-radius: var(--radius-sm);
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 14px;
        font-size: 22px;
    }

    .feature-icon.reddit { background: linear-gradient(135deg, #FF4500 0%, #FF6B35 100%); color: white; font-size: 18px; }
    .feature-icon.hn { background: linear-gradient(135deg, #FF6600 0%, #FF8533 100%); color: white; font-size: 18px; }
    .feature-icon.google { background: linear-gradient(135deg, #4285F4 0%, #5B9CF4 100%); color: white; font-size: 18px; }
    .feature-icon.ph { background: linear-gradient(135deg, #DA552F 0%, #E06B4D 100%); color: white; font-size: 18px; }

    .feature-title {
        color: var(--neutral-900);
        font-size: 15px;
        font-weight: 700;
        margin: 0 0 4px 0;
        letter-spacing: -0.02em;
    }

    .feature-desc {
        color: var(--neutral-500);
        font-size: 13px;
        line-height: 1.5;
        margin: 0;
    }

    /* ========== STEPS ========== */
    .steps-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
    }

    .step-card {
        background: var(--white);
        border: 1px solid var(--neutral-200);
        border-radius: var(--radius-lg);
        padding: 28px 20px;
        text-align: center;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
    }

    .step-card:hover {
        border-color: var(--primary-200);
        box-shadow: var(--shadow-md);
        transform: translateY(-3px);
    }

    .step-number {
        width: 48px;
        height: 48px;
        background: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-500) 100%);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 18px auto;
        color: white;
        font-size: 20px;
        font-weight: 800;
        box-shadow: 0 8px 20px rgba(99, 102, 241, 0.35);
    }

    .step-title {
        color: var(--neutral-900);
        font-size: 16px;
        font-weight: 700;
        margin: 0 0 6px 0;
        letter-spacing: -0.02em;
    }

    .step-desc {
        color: var(--neutral-500);
        font-size: 13px;
        line-height: 1.5;
        margin: 0;
    }

    /* ========== BUTTONS ========== */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-500) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        padding: 13px 26px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        box-shadow: 0 6px 16px rgba(99, 102, 241, 0.35) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        letter-spacing: -0.01em !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 24px rgba(99, 102, 241, 0.45) !important;
    }

    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* ========== CHECKBOXES ========== */
    .stCheckbox {
        background: var(--white) !important;
        border: 1px solid var(--neutral-200) !important;
        border-radius: var(--radius-sm) !important;
        padding: 14px 18px !important;
        margin: 4px 0 !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .stCheckbox:hover {
        border-color: var(--primary-300) !important;
        background: var(--primary-50) !important;
    }

    .stCheckbox label {
        font-size: 14px !important;
        font-weight: 500 !important;
        color: var(--neutral-700) !important;
    }

    /* ========== TABS ========== */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--neutral-100) !important;
        border-radius: var(--radius-sm) !important;
        padding: 4px !important;
        gap: 4px !important;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: var(--radius-xs) !important;
        font-weight: 500 !important;
        font-size: 13px !important;
        padding: 10px 18px !important;
        color: var(--neutral-600) !important;
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
        border: 1px solid var(--neutral-200) !important;
        border-radius: var(--radius-md) !important;
        overflow: hidden !important;
    }

    /* ========== PROGRESS ========== */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--primary-500) 0%, var(--accent-500) 100%) !important;
        border-radius: 10px !important;
    }

    /* ========== ALERTS ========== */
    .stSuccess, .stInfo, .stWarning, .stError {
        border-radius: var(--radius-sm) !important;
        font-size: 13px !important;
        border-left-width: 3px !important;
    }

    .stSuccess {
        background: var(--success-50) !important;
        border-left-color: var(--success-500) !important;
    }

    .stInfo {
        background: var(--primary-50) !important;
        border-left-color: var(--primary-500) !important;
    }

    /* ========== EMPTY STATE ========== */
    .empty-state {
        text-align: center;
        padding: 56px 40px;
        background: linear-gradient(180deg, var(--neutral-50) 0%, var(--white) 100%);
        border: 1px dashed var(--neutral-300);
        border-radius: var(--radius-lg);
    }

    .empty-icon {
        font-size: 52px;
        margin-bottom: 18px;
        opacity: 0.5;
    }

    .empty-title {
        color: var(--neutral-900);
        font-size: 18px;
        font-weight: 700;
        margin: 0 0 6px 0;
        letter-spacing: -0.02em;
    }

    .empty-desc {
        color: var(--neutral-500);
        font-size: 14px;
        margin: 0 0 20px 0;
    }

    /* ========== API CARDS ========== */
    .api-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 14px;
    }

    .api-card {
        background: #FFFFFF !important;
        border: 1px solid #E5E5E5 !important;
        border-radius: 16px !important;
        padding: 24px 20px !important;
        text-align: center !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        display: block !important;
        min-height: 120px !important;
    }

    .api-card:hover {
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1) !important;
        transform: translateY(-2px) !important;
    }

    .api-card.connected {
        border-color: #10B981 !important;
        background: linear-gradient(180deg, #FFFFFF 0%, #ECFDF5 100%) !important;
    }

    .api-card.disconnected {
        border-color: #E5E5E5 !important;
        background: #FFFFFF !important;
    }

    .api-icon {
        font-size: 32px !important;
        margin-bottom: 12px !important;
        display: block !important;
    }

    .api-name {
        color: #171717 !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        margin: 0 0 10px 0 !important;
        letter-spacing: -0.01em !important;
        display: block !important;
    }

    h4.api-name {
        color: #171717 !important;
        font-size: 15px !important;
        font-weight: 700 !important;
    }

    .api-status {
        display: inline-flex !important;
        align-items: center !important;
        gap: 5px !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        padding: 4px 12px !important;
        border-radius: 20px !important;
    }

    .api-status.connected {
        background: #ECFDF5 !important;
        color: #059669 !important;
    }

    .api-status.disconnected {
        background: #F5F5F5 !important;
        color: #737373 !important;
    }

    /* ========== TAGS ========== */
    .tags-container {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }

    .tag {
        background: var(--primary-50);
        color: var(--primary-700);
        font-size: 12px;
        font-weight: 500;
        padding: 6px 12px;
        border-radius: 20px;
        border: 1px solid var(--primary-100);
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .tag:hover {
        background: var(--primary-600);
        color: white;
        border-color: var(--primary-600);
        transform: translateY(-1px);
    }

    /* ========== LOADING ========== */
    .loading-box {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px 18px;
        background: var(--neutral-50);
        border-radius: var(--radius-sm);
        border: 1px solid var(--neutral-200);
        margin: 8px 0;
    }

    .spinner {
        width: 20px;
        height: 20px;
        border: 2px solid var(--neutral-200);
        border-top-color: var(--primary-500);
        border-radius: 50%;
        animation: spin 0.7s linear infinite;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    .loading-text {
        color: var(--neutral-700);
        font-size: 14px;
        font-weight: 500;
    }

    /* ========== RESULTS ========== */
    .results-box {
        display: flex;
        gap: 28px;
        padding: 22px 24px;
        background: linear-gradient(135deg, var(--success-50) 0%, #D1FAE5 100%);
        border: 1px solid var(--success-500);
        border-radius: var(--radius-lg);
        margin: 16px 0;
    }

    .result-item {
        text-align: center;
    }

    .result-value {
        font-size: 28px;
        font-weight: 800;
        line-height: 1;
        letter-spacing: -0.03em;
    }

    .result-value.green { color: var(--success-600); }
    .result-value.blue { color: var(--primary-600); }
    .result-value.orange { color: var(--accent-600); }

    .result-label {
        color: var(--neutral-600);
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-top: 5px;
    }

    /* ========== STATS BAR ========== */
    .stats-bar {
        display: flex;
        gap: 36px;
        padding: 18px 0;
        margin-bottom: 24px;
        border-bottom: 1px solid var(--neutral-200);
    }

    .stat-item {
        display: flex;
        align-items: baseline;
        gap: 6px;
    }

    .stat-value {
        font-size: 26px;
        font-weight: 800;
        color: var(--neutral-900);
        letter-spacing: -0.03em;
    }

    .stat-label {
        font-size: 14px;
        color: var(--neutral-500);
    }

    /* ========== EXPANDER ========== */
    .streamlit-expanderHeader {
        font-size: 14px !important;
        font-weight: 600 !important;
        background: var(--white) !important;
        border: 1px solid var(--neutral-200) !important;
        border-radius: var(--radius-sm) !important;
        transition: all 0.2s ease !important;
    }

    .streamlit-expanderHeader:hover {
        border-color: var(--primary-300) !important;
        background: var(--primary-50) !important;
    }

    /* ========== SELECT BOX ========== */
    .stSelectbox > div > div {
        background: var(--white) !important;
        border: 1px solid var(--neutral-200) !important;
        border-radius: var(--radius-sm) !important;
        font-size: 14px !important;
        color: var(--neutral-800) !important;
    }

    .stSelectbox > div > div:hover {
        border-color: var(--primary-300) !important;
    }

    .stSelectbox label, .stTextInput label, .stTextArea label, .stNumberInput label {
        color: var(--neutral-700) !important;
    }

    /* ========== TEXT INPUTS ========== */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {
        background: var(--white) !important;
        border: 1px solid var(--neutral-200) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--neutral-800) !important;
        font-size: 14px !important;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--primary-400) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
    }

    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {
        color: var(--neutral-400) !important;
    }

    /* ========== MULTISELECT ========== */
    .stMultiSelect > div > div {
        background: var(--white) !important;
        border: 1px solid var(--neutral-200) !important;
        color: var(--neutral-800) !important;
    }

    .stMultiSelect span {
        color: var(--neutral-800) !important;
    }

    /* ========== RADIO BUTTONS (main area) ========== */
    .main .stRadio label {
        color: var(--neutral-700) !important;
    }

    /* ========== ALL LABELS AND TEXT ========== */
    .main p, .main span, .main label, .main div {
        color: var(--neutral-700);
    }

    .main h1, .main h2, .main h3, .main h4 {
        color: var(--neutral-900) !important;
    }

    /* ========== SELECTBOX DROPDOWN ========== */
    [data-baseweb="select"] span,
    [data-baseweb="select"] div {
        color: var(--neutral-800) !important;
    }

    [data-baseweb="menu"] {
        background: var(--white) !important;
    }

    [data-baseweb="menu"] li {
        color: var(--neutral-800) !important;
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
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: var(--neutral-100);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb {
        background: var(--neutral-300);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--neutral-400);
    }

    /* ========== HIDE STREAMLIT KEYBOARD SHORTCUTS ========== */
    [data-testid="stKeyboardShortcuts"],
    [class*="keyboard"],
    .stKeyboardShortcut,
    [aria-label*="keyboard"] {
        display: none !important;
        visibility: hidden !important;
    }

    /* ========== ENHANCED CHECKBOX STYLING ========== */
    .stCheckbox > label {
        color: var(--neutral-800) !important;
        font-weight: 500 !important;
    }

    .stCheckbox > label > div {
        color: var(--neutral-800) !important;
    }

    .stCheckbox > label > div > p,
    .stCheckbox > label > div > span {
        color: var(--neutral-800) !important;
        font-weight: 500 !important;
    }

    .stCheckbox [data-testid="stMarkdownContainer"] p {
        color: var(--neutral-800) !important;
    }

    /* ========== ENHANCED ALERTS ========== */
    .stAlert {
        border-radius: var(--radius-md) !important;
        padding: 16px 20px !important;
        border: none !important;
        box-shadow: var(--shadow-sm) !important;
    }

    .stAlert > div {
        color: var(--neutral-800) !important;
    }

    [data-testid="stAlert"] {
        border-radius: var(--radius-md) !important;
        border-left: 4px solid !important;
    }

    [data-baseweb="notification"] {
        border-radius: var(--radius-md) !important;
        background: var(--primary-50) !important;
        border-left: 4px solid var(--primary-500) !important;
    }

    [data-baseweb="notification"] [data-testid="stMarkdownContainer"] p {
        color: var(--neutral-800) !important;
        font-weight: 500 !important;
    }

    /* Info alert styling */
    .element-container:has([data-testid="stAlert"]) [role="alert"] {
        background: linear-gradient(135deg, var(--primary-50) 0%, #E0E7FF 100%) !important;
        border-left-color: var(--primary-500) !important;
        border-radius: var(--radius-md) !important;
        padding: 16px 20px !important;
    }

    /* ========== ENHANCED PAGE TITLES ========== */
    .page-header h1 {
        color: #0F172A !important;
        font-weight: 800 !important;
        text-shadow: none !important;
    }

    .section-title h2 {
        color: #1E293B !important;
        font-weight: 700 !important;
    }

    /* Ensure all main content has dark text */
    .main h1, .main h2, .main h3 {
        color: #0F172A !important;
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
        pages = ["Dashboard", "Find Leads", "My Leads", "Analytics", "Settings"]
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
                    batch = s.scrape()
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

        # Filter by industry if selected
        if selected_industry != "All Industries":
            industry_subreddits = settings.industries.get(selected_industry, [])
            all_leads = [l for l in all_leads if l.subreddit and l.subreddit.lower() in [s.lower() for s in industry_subreddits] or l.industry == selected_industry]

        st.session_state.leads = all_leads

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
    st.markdown("""
    <div class="page-header">
        <h1>My Leads</h1>
        <p>Manage and export your prospects</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Local Leads", "HubSpot"])

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
    elif page == "Analytics":
        show_analytics()
    elif page == "Settings":
        show_config()


if __name__ == "__main__":
    main()
