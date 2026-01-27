#!/usr/bin/env python3
"""
LeadGen Pro - Premium Web Interface (Streamlit)

A modern, professional lead generation platform with
sophisticated UI/UX design for business owners.

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

# Page config with custom favicon
st.set_page_config(
    page_title="LeadGen Pro | Intelligent Lead Generation",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect fill='%231E40AF' rx='20' width='100' height='100'/><path fill='%23F97316' d='M50 20L70 50L50 80L30 50Z'/></svg>",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# SVG ASSETS
# ============================================

LOGO_SVG = """
<svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="40" height="40" rx="10" fill="url(#logo_gradient)"/>
    <path d="M20 10L28 20L20 30L12 20L20 10Z" fill="#F97316"/>
    <path d="M20 14L24 20L20 26L16 20L20 14Z" fill="white" fill-opacity="0.9"/>
    <defs>
        <linearGradient id="logo_gradient" x1="0" y1="0" x2="40" y2="40">
            <stop offset="0%" stop-color="#1E40AF"/>
            <stop offset="100%" stop-color="#3B82F6"/>
        </linearGradient>
    </defs>
</svg>
"""

EMPTY_STATE_SVG = """
<svg width="120" height="120" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="60" cy="60" r="50" fill="#F1F5F9" stroke="#E2E8F0" stroke-width="2"/>
    <circle cx="60" cy="45" r="15" fill="#CBD5E1"/>
    <path d="M35 85C35 71.193 46.193 60 60 60C73.807 60 85 71.193 85 85" stroke="#CBD5E1" stroke-width="8" stroke-linecap="round"/>
    <circle cx="85" cy="35" r="12" fill="#F97316"/>
    <path d="M81 35L84 38L89 32" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

SEARCH_EMPTY_SVG = """
<svg width="120" height="120" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="50" cy="50" r="30" fill="#F1F5F9" stroke="#1E40AF" stroke-width="3"/>
    <line x1="72" y1="72" x2="95" y2="95" stroke="#1E40AF" stroke-width="4" stroke-linecap="round"/>
    <circle cx="50" cy="50" r="15" fill="#E2E8F0"/>
    <path d="M45 45L55 55M55 45L45 55" stroke="#94A3B8" stroke-width="2" stroke-linecap="round"/>
</svg>
"""

CHART_EMPTY_SVG = """
<svg width="120" height="120" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="15" y="80" width="20" height="25" rx="4" fill="#E2E8F0"/>
    <rect x="45" y="55" width="20" height="50" rx="4" fill="#CBD5E1"/>
    <rect x="75" y="35" width="20" height="70" rx="4" fill="#1E40AF"/>
    <path d="M20 30L50 45L80 25" stroke="#F97316" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="20" cy="30" r="4" fill="#F97316"/>
    <circle cx="50" cy="45" r="4" fill="#F97316"/>
    <circle cx="80" cy="25" r="4" fill="#F97316"/>
</svg>
"""

# Service Logos (simplified SVG versions)
HUBSPOT_LOGO = """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="10" fill="#FF7A59"/>
    <path d="M12 6V12L16 14" stroke="white" stroke-width="2" stroke-linecap="round"/>
</svg>
"""

GOOGLE_LOGO = """
<svg width="24" height="24" viewBox="0 0 24 24">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
</svg>
"""

OPENAI_LOGO = """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="10" fill="#10A37F"/>
    <path d="M12 6L12 12M12 12L17 9M12 12L7 9M12 12L12 18M12 18L17 15M12 18L7 15" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
</svg>
"""

ANTHROPIC_LOGO = """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="10" fill="#D4A574"/>
    <path d="M8 16L12 8L16 16" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M9.5 14H14.5" stroke="white" stroke-width="2" stroke-linecap="round"/>
</svg>
"""

REDDIT_LOGO = """
<svg width="32" height="32" viewBox="0 0 32 32" fill="none">
    <circle cx="16" cy="16" r="14" fill="#FF4500"/>
    <circle cx="11" cy="14" r="2" fill="white"/>
    <circle cx="21" cy="14" r="2" fill="white"/>
    <path d="M11 20C11 20 13 23 16 23C19 23 21 20 21 20" stroke="white" stroke-width="2" stroke-linecap="round"/>
</svg>
"""

HN_LOGO = """
<svg width="32" height="32" viewBox="0 0 32 32" fill="none">
    <rect width="32" height="32" rx="4" fill="#FF6600"/>
    <text x="16" y="22" font-family="Arial" font-size="16" font-weight="bold" fill="white" text-anchor="middle">Y</text>
</svg>
"""

PRODUCTHUNT_LOGO = """
<svg width="32" height="32" viewBox="0 0 32 32" fill="none">
    <circle cx="16" cy="16" r="14" fill="#DA552F"/>
    <text x="16" y="21" font-family="Arial" font-size="14" font-weight="bold" fill="white" text-anchor="middle">P</text>
</svg>
"""

# Mini sparkline SVG for metrics
SPARKLINE_UP = """
<svg width="60" height="24" viewBox="0 0 60 24" fill="none">
    <path d="M2 18L12 14L22 16L32 10L42 12L52 6L58 4" stroke="#10B981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="58" cy="4" r="3" fill="#10B981"/>
</svg>
"""

SPARKLINE_NEUTRAL = """
<svg width="60" height="24" viewBox="0 0 60 24" fill="none">
    <path d="M2 12L12 14L22 10L32 12L42 11L52 13L58 12" stroke="#F97316" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="58" cy="12" r="3" fill="#F97316"/>
</svg>
"""

# Premium CSS Design System - Blue + Orange Theme
st.markdown("""
<style>
    /* ============================================
       LEADGEN PRO - PREMIUM DESIGN SYSTEM
       Blue (Trust) + Orange (Action) Theme
    ============================================ */

    /* Import Modern Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* CSS Variables - Blue + Orange Professional Palette */
    :root {
        /* Primary Blue - Trust & Professionalism */
        --primary: #1E40AF;
        --primary-dark: #1E3A8A;
        --primary-light: #3B82F6;
        --primary-lighter: #60A5FA;
        --primary-bg: #EFF6FF;

        /* Accent Orange - Action & Urgency */
        --accent: #F97316;
        --accent-dark: #EA580C;
        --accent-light: #FB923C;
        --accent-bg: #FFF7ED;

        /* Neutrals */
        --secondary: #0F172A;
        --surface: #FFFFFF;
        --surface-secondary: #F8FAFC;
        --surface-tertiary: #F1F5F9;

        /* Semantic */
        --success: #10B981;
        --success-bg: #ECFDF5;
        --warning: #F59E0B;
        --warning-bg: #FFFBEB;
        --danger: #EF4444;
        --danger-bg: #FEF2F2;

        /* Text */
        --text-primary: #0F172A;
        --text-secondary: #475569;
        --text-muted: #94A3B8;
        --text-inverse: #FFFFFF;

        /* Borders & Shadows */
        --border: #E2E8F0;
        --border-light: #F1F5F9;
        --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
        --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        --shadow-md: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
        --shadow-lg: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
        --shadow-accent: 0 4px 14px rgba(249, 115, 22, 0.25);
        --shadow-primary: 0 4px 14px rgba(30, 64, 175, 0.25);

        /* Radius */
        --radius-sm: 8px;
        --radius: 12px;
        --radius-lg: 16px;
        --radius-xl: 24px;
        --radius-full: 9999px;
    }

    /* Global Styles */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    .main .block-container {
        padding: 1.5rem 2.5rem 3rem 2.5rem;
        max-width: 1400px;
    }

    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ============================================
       SIDEBAR - Dark Professional Style
    ============================================ */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%);
        border-right: none;
        padding-top: 0;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #F8FAFC;
    }

    [data-testid="stSidebar"] .stRadio > label {
        color: #64748B !important;
        font-size: 0.6875rem;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }

    [data-testid="stSidebar"] .stRadio > div {
        gap: 0.375rem;
    }

    [data-testid="stSidebar"] .stRadio > div > label {
        background: transparent;
        border-radius: var(--radius);
        padding: 0.875rem 1rem;
        color: #94A3B8 !important;
        transition: all 0.2s ease;
        border: 1px solid transparent;
        margin: 0;
        font-weight: 500;
    }

    [data-testid="stSidebar"] .stRadio > div > label:hover {
        background: rgba(255, 255, 255, 0.05);
        color: #F1F5F9 !important;
        border-color: rgba(255, 255, 255, 0.1);
    }

    [data-testid="stSidebar"] .stRadio > div > label[data-checked="true"] {
        background: linear-gradient(135deg, rgba(30, 64, 175, 0.3) 0%, rgba(59, 130, 246, 0.15) 100%);
        border: 1px solid rgba(59, 130, 246, 0.4);
        color: #FFFFFF !important;
        font-weight: 600;
    }

    /* ============================================
       USER PROFILE IN SIDEBAR
    ============================================ */
    .user-profile {
        display: flex;
        align-items: center;
        gap: 0.875rem;
        padding: 1.25rem;
        margin: 1rem 0.75rem;
        background: rgba(255, 255, 255, 0.05);
        border-radius: var(--radius);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    .user-avatar {
        width: 42px;
        height: 42px;
        border-radius: var(--radius);
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.125rem;
        font-weight: 700;
        color: white;
    }

    .user-info {
        flex: 1;
        min-width: 0;
    }

    .user-name {
        color: #F8FAFC;
        font-size: 0.875rem;
        font-weight: 600;
        margin: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .user-plan {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dark) 100%);
        color: white;
        padding: 0.125rem 0.5rem;
        border-radius: var(--radius-full);
        font-size: 0.625rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.25rem;
    }

    /* ============================================
       BRAND & LOGO
    ============================================ */
    .brand-container {
        display: flex;
        align-items: center;
        gap: 0.875rem;
        padding: 1.5rem 1rem 1.25rem 1rem;
    }

    .brand-text {
        flex: 1;
    }

    .brand-name {
        color: #FFFFFF;
        font-size: 1.25rem;
        font-weight: 700;
        letter-spacing: -0.025em;
        margin: 0;
    }

    .brand-tagline {
        color: #64748B;
        font-size: 0.6875rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 0.125rem;
    }

    /* ============================================
       GLOBAL TOP HEADER
    ============================================ */
    .top-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 0 1.5rem 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 1.5rem;
    }

    .breadcrumb {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: var(--text-muted);
        font-size: 0.875rem;
    }

    .breadcrumb-current {
        color: var(--text-primary);
        font-weight: 600;
    }

    .header-actions {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .notification-btn {
        width: 40px;
        height: 40px;
        border-radius: var(--radius);
        background: var(--surface-secondary);
        border: 1px solid var(--border);
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.2s ease;
        position: relative;
    }

    .notification-btn:hover {
        background: var(--surface);
        border-color: var(--primary-light);
        box-shadow: var(--shadow);
    }

    .notification-badge {
        position: absolute;
        top: -4px;
        right: -4px;
        width: 18px;
        height: 18px;
        background: var(--accent);
        border-radius: 50%;
        font-size: 0.625rem;
        font-weight: 700;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .header-user {
        display: flex;
        align-items: center;
        gap: 0.625rem;
        padding: 0.5rem 0.875rem 0.5rem 0.5rem;
        background: var(--surface-secondary);
        border: 1px solid var(--border);
        border-radius: var(--radius-full);
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .header-user:hover {
        background: var(--surface);
        border-color: var(--primary-light);
        box-shadow: var(--shadow);
    }

    .header-avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        font-weight: 700;
        color: white;
    }

    .header-username {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text-primary);
    }

    /* ============================================
       PAGE HEADER - Hero Style
    ============================================ */
    .page-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #334155 100%);
        border-radius: var(--radius-xl);
        padding: 2.5rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }

    .page-header::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 50%;
        height: 100%;
        background: linear-gradient(135deg, rgba(30, 64, 175, 0.15) 0%, rgba(249, 115, 22, 0.08) 100%);
        border-radius: 0 var(--radius-xl) var(--radius-xl) 0;
    }

    .page-header::after {
        content: '';
        position: absolute;
        top: 50%;
        right: 10%;
        width: 200px;
        height: 200px;
        background: radial-gradient(circle, rgba(249, 115, 22, 0.1) 0%, transparent 70%);
        transform: translateY(-50%);
    }

    .page-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dark) 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: var(--radius-full);
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 1rem;
        box-shadow: var(--shadow-accent);
    }

    .page-header h1 {
        color: #FFFFFF;
        font-size: 2rem;
        font-weight: 700;
        margin: 0 0 0.5rem 0;
        letter-spacing: -0.025em;
        position: relative;
        z-index: 1;
    }

    .page-header p {
        color: #94A3B8;
        font-size: 1rem;
        margin: 0;
        font-weight: 400;
        position: relative;
        z-index: 1;
    }

    /* ============================================
       METRIC CARDS - Premium Style with Icons
    ============================================ */
    .metric-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-md);
        border-color: var(--primary-light);
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--primary) 0%, var(--accent) 100%);
        border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    }

    .metric-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        margin-bottom: 1rem;
    }

    .metric-icon {
        width: 44px;
        height: 44px;
        border-radius: var(--radius);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
    }

    .metric-icon.blue {
        background: linear-gradient(135deg, var(--primary-bg) 0%, #DBEAFE 100%);
        color: var(--primary);
    }

    .metric-icon.orange {
        background: linear-gradient(135deg, var(--accent-bg) 0%, #FED7AA 100%);
        color: var(--accent);
    }

    .metric-icon.green {
        background: linear-gradient(135deg, var(--success-bg) 0%, #A7F3D0 100%);
        color: var(--success);
    }

    .metric-sparkline {
        opacity: 0.8;
    }

    .metric-label {
        color: var(--text-secondary);
        font-size: 0.8125rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }

    .metric-value {
        color: var(--text-primary);
        font-size: 2.25rem;
        font-weight: 700;
        letter-spacing: -0.025em;
        line-height: 1;
    }

    .metric-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid var(--border-light);
    }

    .metric-change {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.25rem 0.625rem;
        border-radius: var(--radius-full);
    }

    .metric-change.up {
        color: var(--success);
        background: var(--success-bg);
    }

    .metric-change.neutral {
        color: var(--accent);
        background: var(--accent-bg);
    }

    /* ============================================
       SECTION HEADERS
    ============================================ */
    .section-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin: 2.5rem 0 1.25rem 0;
    }

    .section-header h2 {
        color: var(--text-primary);
        font-size: 1.25rem;
        font-weight: 600;
        margin: 0;
        letter-spacing: -0.025em;
    }

    .section-badge {
        background: var(--primary-bg);
        color: var(--primary);
        padding: 0.25rem 0.75rem;
        border-radius: var(--radius-full);
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* ============================================
       SOURCE CARDS - Selectable Cards
    ============================================ */
    .source-card {
        background: var(--surface);
        border: 2px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.25rem;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .source-card:hover {
        border-color: var(--primary-light);
        background: var(--primary-bg);
    }

    .source-card.selected {
        border-color: var(--primary);
        background: var(--primary-bg);
        box-shadow: 0 0 0 3px rgba(30, 64, 175, 0.1);
    }

    .source-card.disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .source-icon {
        width: 48px;
        height: 48px;
        border-radius: var(--radius);
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }

    .source-info {
        flex: 1;
    }

    .source-name {
        font-weight: 600;
        color: var(--text-primary);
        font-size: 0.9375rem;
        margin-bottom: 0.25rem;
    }

    .source-desc {
        color: var(--text-secondary);
        font-size: 0.8125rem;
    }

    .source-check {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        border: 2px solid var(--border);
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s ease;
    }

    .source-card.selected .source-check {
        background: var(--primary);
        border-color: var(--primary);
        color: white;
    }

    /* ============================================
       FEATURE CARDS
    ============================================ */
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 1.25rem;
        margin: 1.5rem 0;
    }

    .feature-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.75rem;
        transition: all 0.3s ease;
    }

    .feature-card:hover {
        border-color: var(--primary-light);
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }

    .feature-icon {
        width: 52px;
        height: 52px;
        border-radius: var(--radius);
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 1rem;
    }

    .feature-title {
        color: var(--text-primary);
        font-size: 1.0625rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }

    .feature-desc {
        color: var(--text-secondary);
        font-size: 0.875rem;
        line-height: 1.6;
    }

    /* ============================================
       API STATUS CARDS - With Service Logos
    ============================================ */
    .api-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        text-align: center;
        transition: all 0.2s ease;
    }

    .api-card:hover {
        box-shadow: var(--shadow);
    }

    .api-card.active {
        border-color: rgba(16, 185, 129, 0.3);
        background: linear-gradient(180deg, var(--surface) 0%, var(--success-bg) 100%);
    }

    .api-card.inactive {
        border-color: rgba(245, 158, 11, 0.3);
        background: linear-gradient(180deg, var(--surface) 0%, var(--warning-bg) 100%);
    }

    .api-logo {
        width: 48px;
        height: 48px;
        margin: 0 auto 0.75rem auto;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .api-name {
        font-weight: 600;
        color: var(--text-primary);
        font-size: 0.9375rem;
        margin-bottom: 0.5rem;
    }

    .api-status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.375rem 0.75rem;
        border-radius: var(--radius-full);
        font-size: 0.75rem;
        font-weight: 600;
    }

    .api-status-badge.active {
        background: var(--success-bg);
        color: var(--success);
    }

    .api-status-badge.inactive {
        background: var(--warning-bg);
        color: var(--warning);
    }

    /* ============================================
       BUTTONS
    ============================================ */
    .stButton > button {
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dark) 100%);
        color: white !important;
        border: none;
        border-radius: var(--radius);
        padding: 0.875rem 1.75rem;
        font-weight: 600;
        font-size: 0.9375rem;
        transition: all 0.2s ease;
        box-shadow: var(--shadow-accent);
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(249, 115, 22, 0.4);
    }

    .stButton > button:active {
        transform: translateY(0);
    }

    /* Secondary Button Style */
    .secondary-btn button {
        background: var(--surface) !important;
        color: var(--text-primary) !important;
        border: 2px solid var(--border) !important;
        box-shadow: var(--shadow-sm) !important;
    }

    .secondary-btn button:hover {
        border-color: var(--primary) !important;
        color: var(--primary) !important;
        background: var(--primary-bg) !important;
    }

    /* ============================================
       EMPTY STATES
    ============================================ */
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        background: linear-gradient(180deg, var(--surface) 0%, var(--surface-secondary) 100%);
        border-radius: var(--radius-xl);
        border: 2px dashed var(--border);
    }

    .empty-state-illustration {
        margin-bottom: 1.5rem;
    }

    .empty-state-title {
        color: var(--text-primary);
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }

    .empty-state-desc {
        color: var(--text-secondary);
        font-size: 0.9375rem;
        margin-bottom: 1.5rem;
        max-width: 400px;
        margin-left: auto;
        margin-right: auto;
    }

    .empty-state-cta {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dark) 100%);
        color: white;
        padding: 0.875rem 1.5rem;
        border-radius: var(--radius);
        font-weight: 600;
        font-size: 0.9375rem;
        text-decoration: none;
        box-shadow: var(--shadow-accent);
        transition: all 0.2s ease;
    }

    .empty-state-cta:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(249, 115, 22, 0.4);
    }

    /* ============================================
       KEYWORD TAGS
    ============================================ */
    .keyword-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 1rem 0;
    }

    .keyword-tag {
        background: var(--primary-bg);
        border: 1px solid rgba(30, 64, 175, 0.2);
        color: var(--primary);
        padding: 0.5rem 1rem;
        border-radius: var(--radius-full);
        font-size: 0.8125rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    .keyword-tag:hover {
        background: var(--primary);
        color: white;
        transform: translateY(-1px);
    }

    /* ============================================
       DATA TABLES & FRAMES
    ============================================ */
    .stDataFrame {
        border: 1px solid var(--border);
        border-radius: var(--radius);
        overflow: hidden;
    }

    /* ============================================
       TABS
    ============================================ */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--surface-secondary);
        border-radius: var(--radius);
        padding: 0.375rem;
        gap: 0.375rem;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: var(--radius-sm);
        font-weight: 500;
        color: var(--text-secondary);
        padding: 0.75rem 1.5rem;
    }

    .stTabs [aria-selected="true"] {
        background: var(--surface) !important;
        color: var(--primary) !important;
        box-shadow: var(--shadow);
        font-weight: 600;
    }

    /* ============================================
       CHECKBOXES - Modern Toggle Style
    ============================================ */
    .stCheckbox {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 1rem 1.25rem;
        margin: 0.375rem 0;
        transition: all 0.2s ease;
    }

    .stCheckbox:hover {
        border-color: var(--primary-light);
        background: var(--primary-bg);
    }

    /* ============================================
       PROGRESS BAR
    ============================================ */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--primary) 0%, var(--accent) 100%);
        border-radius: var(--radius-full);
    }

    .stProgress > div > div {
        background: var(--surface-tertiary);
        border-radius: var(--radius-full);
    }

    /* ============================================
       ALERTS / MESSAGES
    ============================================ */
    .stSuccess {
        background: var(--success-bg) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        border-radius: var(--radius) !important;
        color: #065F46 !important;
    }

    .stWarning {
        background: var(--warning-bg) !important;
        border: 1px solid rgba(245, 158, 11, 0.3) !important;
        border-radius: var(--radius) !important;
        color: #92400E !important;
    }

    .stError {
        background: var(--danger-bg) !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
        border-radius: var(--radius) !important;
        color: #991B1B !important;
    }

    .stInfo {
        background: var(--primary-bg) !important;
        border: 1px solid rgba(30, 64, 175, 0.3) !important;
        border-radius: var(--radius) !important;
        color: #1E3A8A !important;
    }

    /* ============================================
       ANIMATIONS
    ============================================ */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .animate-fade-in {
        animation: fadeIn 0.4s ease-out;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    .animate-pulse {
        animation: pulse 2s ease-in-out infinite;
    }

    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    .animate-spin {
        animation: spin 1s linear infinite;
    }

    /* ============================================
       STEP CARDS - Onboarding Style
    ============================================ */
    .step-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 2rem;
        text-align: center;
        transition: all 0.3s ease;
        position: relative;
    }

    .step-card:hover {
        border-color: var(--primary-light);
        box-shadow: var(--shadow-md);
        transform: translateY(-3px);
    }

    .step-number {
        width: 48px;
        height: 48px;
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
        font-weight: 700;
        color: white;
        margin: 0 auto 1rem auto;
        box-shadow: var(--shadow-primary);
    }

    .step-title {
        color: var(--text-primary);
        font-size: 1.0625rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }

    .step-desc {
        color: var(--text-secondary);
        font-size: 0.875rem;
        line-height: 1.6;
    }

    /* ============================================
       LEAD CARDS
    ============================================ */
    .lead-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 1.25rem;
        margin: 0.75rem 0;
        transition: all 0.2s ease;
    }

    .lead-card:hover {
        border-color: var(--primary-light);
        box-shadow: var(--shadow);
    }

    /* ============================================
       RESULTS CARDS
    ============================================ */
    .results-summary {
        display: flex;
        gap: 1.5rem;
        padding: 1.5rem;
        background: var(--success-bg);
        border-radius: var(--radius-lg);
        border: 1px solid rgba(16, 185, 129, 0.3);
        margin: 1rem 0;
    }

    .result-item {
        text-align: center;
    }

    .result-value {
        font-size: 1.75rem;
        font-weight: 700;
    }

    .result-value.success { color: var(--success); }
    .result-value.warning { color: var(--warning); }
    .result-value.danger { color: var(--danger); }

    .result-label {
        font-size: 0.75rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.25rem;
    }

    /* ============================================
       LOADING STATE
    ============================================ */
    .loading-card {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1.25rem;
        background: var(--surface-secondary);
        border-radius: var(--radius);
        margin: 0.5rem 0;
    }

    .loading-spinner {
        width: 24px;
        height: 24px;
        border: 3px solid var(--border);
        border-top-color: var(--primary);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    .loading-text {
        font-weight: 500;
        color: var(--text-primary);
    }

    /* ============================================
       STATS BAR
    ============================================ */
    .stats-bar {
        display: flex;
        gap: 2.5rem;
        padding: 1.25rem 0;
        margin-bottom: 1.5rem;
        border-bottom: 1px solid var(--border);
    }

    .stat-item {
        display: flex;
        align-items: baseline;
        gap: 0.5rem;
    }

    .stat-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--text-primary);
    }

    .stat-label {
        font-size: 0.875rem;
        color: var(--text-secondary);
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


def render_top_header(current_page: str):
    """Render global top header with breadcrumb and user info."""
    st.markdown(f"""
    <div class="top-header">
        <div class="breadcrumb">
            <span>LeadGen Pro</span>
            <span>/</span>
            <span class="breadcrumb-current">{current_page}</span>
        </div>
        <div class="header-actions">
            <div class="notification-btn">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                    <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                </svg>
                <span class="notification-badge">3</span>
            </div>
            <div class="header-user">
                <div class="header-avatar">U</div>
                <span class="header-username">Usuario</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main app entry point."""

    # Sidebar with premium branding
    with st.sidebar:
        # Logo and brand
        st.markdown(f"""
        <div class="brand-container">
            {LOGO_SVG}
            <div class="brand-text">
                <div class="brand-name">LeadGen Pro</div>
                <div class="brand-tagline">Intelligent Prospecting</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # User profile card
        st.markdown("""
        <div class="user-profile">
            <div class="user-avatar">U</div>
            <div class="user-info">
                <div class="user-name">Usuario Demo</div>
                <div class="user-plan">Pro Plan</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height: 0.5rem'></div>", unsafe_allow_html=True)

        page = st.radio(
            "NAVEGACION",
            ["Dashboard", "Buscar Leads", "Mis Leads", "Analytics", "Configuracion"],
            label_visibility="visible"
        )

        # Sidebar footer
        st.markdown("---")
        st.markdown(f"""
        <div style="padding: 0.75rem 0; color: #64748B; font-size: 0.75rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.625rem;">
                <span style="width: 8px; height: 8px; background: #10B981; border-radius: 50%;"></span>
                <span>{len(st.session_state.filtered_leads)} leads activos</span>
            </div>
            <div style="color: #475569; font-size: 0.6875rem;">Version 2.0 Pro</div>
        </div>
        """, unsafe_allow_html=True)

    # Route to pages
    if page == "Dashboard":
        show_home()
    elif page == "Buscar Leads":
        show_search()
    elif page == "Mis Leads":
        show_leads()
    elif page == "Analytics":
        show_statistics()
    elif page == "Configuracion":
        show_config()


def show_home():
    """Premium home/dashboard page."""

    render_top_header("Dashboard")

    # Page Header
    st.markdown(f"""
    <div class="page-header animate-fade-in">
        <div class="page-badge">
            {LOGO_SVG.replace('width="40" height="40"', 'width="16" height="16"')}
            Plataforma Activa
        </div>
        <h1>Bienvenido a LeadGen Pro</h1>
        <p>Tu plataforma inteligente para encontrar y calificar leads de alto valor</p>
    </div>
    """, unsafe_allow_html=True)

    # Metrics Row with Icons and Sparklines
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card animate-fade-in">
            <div class="metric-header">
                <div class="metric-icon blue">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                        <circle cx="9" cy="7" r="4"/>
                        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                    </svg>
                </div>
                <div class="metric-sparkline">{SPARKLINE_UP}</div>
            </div>
            <div class="metric-label">Leads Encontrados</div>
            <div class="metric-value">{len(st.session_state.leads)}</div>
            <div class="metric-footer">
                <span class="metric-change up">En esta sesion</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card animate-fade-in">
            <div class="metric-header">
                <div class="metric-icon green">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                        <polyline points="22 4 12 14.01 9 11.01"/>
                    </svg>
                </div>
                <div class="metric-sparkline">{SPARKLINE_UP}</div>
            </div>
            <div class="metric-label">Leads Calificados</div>
            <div class="metric-value">{len(st.session_state.filtered_leads)}</div>
            <div class="metric-footer">
                <span class="metric-change up">Listos para CRM</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card animate-fade-in">
            <div class="metric-header">
                <div class="metric-icon orange">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                    </svg>
                </div>
                <div class="metric-sparkline">{SPARKLINE_NEUTRAL}</div>
            </div>
            <div class="metric-label">Keywords Activos</div>
            <div class="metric-value">{len(settings.pain_keywords)}</div>
            <div class="metric-footer">
                <span class="metric-change neutral">Configurados</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        sources_active = sum([1 for x in [True, True, bool(settings.google_api_key), True] if x])
        st.markdown(f"""
        <div class="metric-card animate-fade-in">
            <div class="metric-header">
                <div class="metric-icon blue">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                        <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                        <line x1="12" y1="22.08" x2="12" y2="12"/>
                    </svg>
                </div>
                <div class="metric-sparkline">{SPARKLINE_UP}</div>
            </div>
            <div class="metric-label">Fuentes Activas</div>
            <div class="metric-value">{sources_active}/4</div>
            <div class="metric-footer">
                <span class="metric-change up">Conectadas</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Features Section with Platform Icons
    st.markdown("""
    <div class="section-header">
        <h2>Fuentes de Prospeccion</h2>
        <span class="section-badge">4 Integraciones</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="feature-grid">
        <div class="feature-card">
            <div class="feature-icon" style="background: #FF45001A;">
                {REDDIT_LOGO}
            </div>
            <div class="feature-title">Reddit</div>
            <div class="feature-desc">Monitoreo de subreddits de pequenos negocios y emprendedores buscando soluciones.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon" style="background: #FF66001A;">
                {HN_LOGO}
            </div>
            <div class="feature-title">Hacker News</div>
            <div class="feature-desc">Discusiones de startups y founders con problemas de comunicacion empresarial.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon" style="background: #4285F41A;">
                {GOOGLE_LOGO}
            </div>
            <div class="feature-title">Google Search</div>
            <div class="feature-desc">Busquedas especificas de frases que indican necesidad de soluciones.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon" style="background: #DA552F1A;">
                {PRODUCTHUNT_LOGO}
            </div>
            <div class="feature-title">Product Hunt</div>
            <div class="feature-desc">Founders discutiendo retos operacionales y buscando herramientas.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Quick Start Steps
    st.markdown("""
    <div class="section-header">
        <h2>Como Empezar</h2>
        <span class="section-badge">3 Pasos</span>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="step-card">
            <div class="step-number">1</div>
            <div class="step-title">Buscar Leads</div>
            <div class="step-desc">Selecciona las fuentes y ejecuta una busqueda automatizada.</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="step-card">
            <div class="step-number">2</div>
            <div class="step-title">Revisar y Filtrar</div>
            <div class="step-desc">La AI califica automaticamente los leads mas prometedores.</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="step-card">
            <div class="step-number">3</div>
            <div class="step-title">Exportar a CRM</div>
            <div class="step-desc">Envia los leads calificados directamente a HubSpot.</div>
        </div>
        """, unsafe_allow_html=True)


def show_search():
    """Premium search page."""

    render_top_header("Buscar Leads")

    # Page Header
    st.markdown("""
    <div class="page-header animate-fade-in" style="padding: 2rem 2.5rem;">
        <h1 style="font-size: 1.75rem;">Buscar Nuevos Leads</h1>
        <p>Encuentra prospectos con problemas de comunicacion empresarial</p>
    </div>
    """, unsafe_allow_html=True)

    # Source Selection with Cards
    st.markdown("""
    <div class="section-header">
        <h2>Seleccionar Fuentes</h2>
        <span class="section-badge">Multi-canal</span>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        use_reddit = st.checkbox("Reddit - Subreddits de negocios", value=True)
        use_hn = st.checkbox("Hacker News - Startups y founders", value=True)

    with col2:
        use_google = st.checkbox(
            "Google Search - Busquedas especificas",
            value=bool(settings.google_api_key),
            disabled=not settings.google_api_key
        )
        use_ph = st.checkbox("Product Hunt - Comunidad tech", value=True)

    st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)

    # AI Filtering
    ai_available = bool(settings.openai_api_key or settings.anthropic_api_key)

    st.markdown("""
    <div class="section-header">
        <h2>Calificacion Inteligente</h2>
        <span class="section-badge">AI Powered</span>
    </div>
    """, unsafe_allow_html=True)

    use_ai = st.checkbox(
        "Usar AI para calificar leads automaticamente (recomendado)",
        value=ai_available,
        disabled=not ai_available
    )

    if not ai_available:
        st.info("Configura OpenAI o Anthropic API key para habilitar calificacion con AI")

    st.markdown("<div style='height: 1.5rem'></div>", unsafe_allow_html=True)

    # Search Button
    if st.button("Iniciar Busqueda", type="primary", use_container_width=True):
        all_leads = []

        progress_bar = st.progress(0)
        status_container = st.empty()

        scrapers = []
        if use_reddit:
            scrapers.append(("Reddit", RedditScraper, REDDIT_LOGO))
        if use_hn:
            scrapers.append(("Hacker News", HackerNewsScraper, HN_LOGO))
        if use_google and settings.google_api_key:
            scrapers.append(("Google Search", GoogleScraper, GOOGLE_LOGO))
        if use_ph:
            scrapers.append(("Product Hunt", ProductHuntScraper, PRODUCTHUNT_LOGO))

        if not scrapers:
            st.warning("Selecciona al menos una fuente para buscar")
            return

        results_container = st.container()

        for i, (name, ScraperClass, icon) in enumerate(scrapers):
            status_container.markdown(f"""
            <div class="loading-card">
                <div class="loading-spinner"></div>
                <span class="loading-text">Buscando en {name}...</span>
            </div>
            """, unsafe_allow_html=True)

            try:
                with ScraperClass() as scraper:
                    batch = scraper.scrape()
                    all_leads.extend(batch.leads)
                    with results_container:
                        st.success(f"{name}: {len(batch.leads)} leads encontrados")
            except Exception as e:
                with results_container:
                    st.warning(f"{name}: Error - {str(e)[:50]}")

            progress_bar.progress((i + 1) / len(scrapers))

        st.session_state.leads = all_leads

        # AI Filtering
        if use_ai and all_leads:
            status_container.markdown("""
            <div class="loading-card">
                <div class="loading-spinner"></div>
                <span class="loading-text">Calificando leads con AI...</span>
            </div>
            """, unsafe_allow_html=True)

            try:
                ai_filter = AILeadFilter()
                filtered = ai_filter.filter_leads(all_leads)
                qualified = [l for l in filtered if l.is_qualified]
                st.session_state.filtered_leads = qualified
                with results_container:
                    st.success(f"AI califico {len(qualified)}/{len(all_leads)} leads como relevantes")
            except Exception as e:
                with results_container:
                    st.warning(f"AI filtering error: {e}")
                st.session_state.filtered_leads = all_leads
        else:
            st.session_state.filtered_leads = all_leads

        st.session_state.scraping_done = True
        progress_bar.progress(1.0)

        status_container.markdown(f"""
        <div class="results-summary">
            <div class="result-item">
                <div class="result-value success">{len(st.session_state.filtered_leads)}</div>
                <div class="result-label">Leads Calificados</div>
            </div>
            <div class="result-item">
                <div class="result-value" style="color: var(--primary);">{len(all_leads)}</div>
                <div class="result-label">Total Encontrados</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Results Preview
    if st.session_state.scraping_done and st.session_state.filtered_leads:
        st.markdown(f"""
        <div class="section-header">
            <h2>Resultados</h2>
            <span class="section-badge">{len(st.session_state.filtered_leads)} leads</span>
        </div>
        """, unsafe_allow_html=True)

        for lead in st.session_state.filtered_leads[:5]:
            with st.expander(f"**{lead.title[:70]}...**"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**Fuente:** {lead.source.value}")
                    st.markdown(f"**Keywords:** {', '.join(lead.keywords_matched[:5])}")
                    if lead.ai_score:
                        st.markdown(f"**AI Score:** {lead.ai_score:.2f}")
                with col2:
                    st.markdown(f"[Ver original]({lead.url})")

                st.markdown("---")
                st.markdown(f"{lead.content[:400]}...")

        if len(st.session_state.filtered_leads) > 5:
            st.info(f"Mostrando 5 de {len(st.session_state.filtered_leads)} leads. Ve a 'Mis Leads' para ver todos.")


def show_leads():
    """Premium leads management page."""

    render_top_header("Mis Leads")

    st.markdown("""
    <div class="page-header animate-fade-in" style="padding: 2rem 2.5rem;">
        <h1 style="font-size: 1.75rem;">Gestion de Leads</h1>
        <p>Administra y exporta tus prospectos calificados</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Leads Locales", "Leads en HubSpot"])

    with tab1:
        if not st.session_state.filtered_leads:
            st.markdown(f"""
            <div class="empty-state">
                <div class="empty-state-illustration">{SEARCH_EMPTY_SVG}</div>
                <div class="empty-state-title">No hay leads todavia</div>
                <div class="empty-state-desc">Comienza una busqueda para encontrar prospectos calificados con problemas de comunicacion empresarial.</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Ir a Buscar Leads"):
                st.rerun()
        else:
            # Stats bar
            qualified_count = len([l for l in st.session_state.filtered_leads if l.is_qualified])
            st.markdown(f"""
            <div class="stats-bar">
                <div class="stat-item">
                    <span class="stat-value">{len(st.session_state.filtered_leads)}</span>
                    <span class="stat-label">leads totales</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value" style="color: var(--success);">{qualified_count}</span>
                    <span class="stat-label">calificados</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # DataFrame
            leads_data = []
            for lead in st.session_state.filtered_leads:
                leads_data.append({
                    "ID": lead.id[:8],
                    "Titulo": lead.title[:50] + "..." if len(lead.title) > 50 else lead.title,
                    "Fuente": lead.source.value,
                    "Keywords": ", ".join(lead.keywords_matched[:3]),
                    "Score": f"{lead.ai_score:.2f}" if lead.ai_score else "-",
                })

            df = pd.DataFrame(leads_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("<div style='height: 1.5rem'></div>", unsafe_allow_html=True)

            # HubSpot Export
            st.markdown(f"""
            <div class="section-header">
                <h2>Exportar a CRM</h2>
                <span class="section-badge">HubSpot</span>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Enviar leads a HubSpot", type="primary"):
                with HubSpotCRM() as crm:
                    if not crm.is_configured():
                        st.error("HubSpot no esta configurado. Agrega HUBSPOT_API_KEY en .env")
                    else:
                        with st.spinner("Enviando leads a HubSpot..."):
                            results = crm.send_leads_to_crm(st.session_state.filtered_leads)

                        st.markdown(f"""
                        <div class="results-summary">
                            <div class="result-item">
                                <div class="result-value success">{results['created']}</div>
                                <div class="result-label">Creados</div>
                            </div>
                            <div class="result-item">
                                <div class="result-value warning">{results['existing']}</div>
                                <div class="result-label">Existentes</div>
                            </div>
                            <div class="result-item">
                                <div class="result-value danger">{results['failed']}</div>
                                <div class="result-label">Fallidos</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

    with tab2:
        with HubSpotCRM() as crm:
            if not crm.is_configured():
                st.markdown(f"""
                <div class="empty-state">
                    <div class="empty-state-illustration">{EMPTY_STATE_SVG}</div>
                    <div class="empty-state-title">HubSpot no configurado</div>
                    <div class="empty-state-desc">Agrega tu HUBSPOT_API_KEY en el archivo .env para conectar con tu CRM.</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                col1, col2 = st.columns([2, 1])
                with col1:
                    stage_filter = st.selectbox(
                        "Filtrar por etapa",
                        ["Todos"] + [s.value for s in LeadStage]
                    )
                with col2:
                    st.markdown("<div style='height: 1.75rem'></div>", unsafe_allow_html=True)
                    load_btn = st.button("Cargar desde HubSpot", type="primary")

                if load_btn:
                    with st.spinner("Cargando contactos..."):
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
                        st.dataframe(pd.DataFrame(contacts_data), use_container_width=True, hide_index=True)
                    else:
                        st.info("No se encontraron contactos con ese filtro")


def show_statistics():
    """Premium statistics/analytics page."""

    render_top_header("Analytics")

    st.markdown("""
    <div class="page-header animate-fade-in" style="padding: 2rem 2.5rem;">
        <h1 style="font-size: 1.75rem;">Analytics Dashboard</h1>
        <p>Metricas de rendimiento y conversion de tu pipeline</p>
    </div>
    """, unsafe_allow_html=True)

    with HubSpotCRM() as crm:
        if not crm.is_configured():
            # Local Stats
            st.markdown("""
            <div class="section-header">
                <h2>Estadisticas de Sesion</h2>
                <span class="section-badge">Local</span>
            </div>
            """, unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-header">
                        <div class="metric-icon blue">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                                <circle cx="9" cy="7" r="4"/>
                            </svg>
                        </div>
                    </div>
                    <div class="metric-label">Leads Encontrados</div>
                    <div class="metric-value">{len(st.session_state.leads)}</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-header">
                        <div class="metric-icon green">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                                <polyline points="22 4 12 14.01 9 11.01"/>
                            </svg>
                        </div>
                    </div>
                    <div class="metric-label">Leads Calificados</div>
                    <div class="metric-value">{len(st.session_state.filtered_leads)}</div>
                </div>
                """, unsafe_allow_html=True)

            with col3:
                rate = (len(st.session_state.filtered_leads) / len(st.session_state.leads) * 100) if st.session_state.leads else 0
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-header">
                        <div class="metric-icon orange">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="18" y1="20" x2="18" y2="10"/>
                                <line x1="12" y1="20" x2="12" y2="4"/>
                                <line x1="6" y1="20" x2="6" y2="14"/>
                            </svg>
                        </div>
                    </div>
                    <div class="metric-label">Tasa de Calificacion</div>
                    <div class="metric-value">{rate:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)

            # By Source Chart
            if st.session_state.leads:
                st.markdown("""
                <div class="section-header">
                    <h2>Leads por Fuente</h2>
                </div>
                """, unsafe_allow_html=True)

                source_counts = {}
                for lead in st.session_state.leads:
                    source_counts[lead.source.value] = source_counts.get(lead.source.value, 0) + 1

                st.bar_chart(source_counts)
            else:
                st.markdown(f"""
                <div class="empty-state" style="padding: 3rem 2rem;">
                    <div class="empty-state-illustration">{CHART_EMPTY_SVG}</div>
                    <div class="empty-state-title">Sin datos para mostrar</div>
                    <div class="empty-state-desc">Realiza una busqueda de leads para ver estadisticas aqui.</div>
                </div>
                """, unsafe_allow_html=True)

            st.info("Conecta HubSpot para ver estadisticas completas del pipeline")

        else:
            with st.spinner("Cargando metricas..."):
                stats = crm.get_statistics()

            if "error" in stats:
                st.error(stats["error"])
            else:
                # Main KPIs
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Total Leads</div>
                        <div class="metric-value">{stats["total_leads"]}</div>
                        <div class="metric-footer">
                            <span class="metric-change up">En pipeline</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Tasa de Conversion</div>
                        <div class="metric-value">{stats['conversion_rate']}%</div>
                        <div class="metric-footer">
                            <span class="metric-change up">Lead a Oportunidad</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Win Rate</div>
                        <div class="metric-value">{stats['win_rate']}%</div>
                        <div class="metric-footer">
                            <span class="metric-change up">Cierres exitosos</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col4:
                    won = stats["by_stage"].get("closed_won", 0)
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Deals Ganados</div>
                        <div class="metric-value">{won}</div>
                        <div class="metric-footer">
                            <span class="metric-change up">Cerrados</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # Charts
                if stats["by_stage"]:
                    st.markdown("""
                    <div class="section-header">
                        <h2>Pipeline de Ventas</h2>
                        <span class="section-badge">Funnel</span>
                    </div>
                    """, unsafe_allow_html=True)
                    st.bar_chart(stats["by_stage"])

                if stats["by_source"]:
                    st.markdown("""
                    <div class="section-header">
                        <h2>Distribucion por Fuente</h2>
                    </div>
                    """, unsafe_allow_html=True)
                    st.bar_chart(stats["by_source"])


def show_config():
    """Premium configuration page."""

    render_top_header("Configuracion")

    st.markdown("""
    <div class="page-header animate-fade-in" style="padding: 2rem 2.5rem;">
        <h1 style="font-size: 1.75rem;">Configuracion</h1>
        <p>Estado de integraciones y parametros del sistema</p>
    </div>
    """, unsafe_allow_html=True)

    # API Status with Service Logos
    st.markdown("""
    <div class="section-header">
        <h2>Estado de APIs</h2>
        <span class="section-badge">Integraciones</span>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        status = "active" if settings.hubspot_api_key else "inactive"
        st.markdown(f"""
        <div class="api-card {status}">
            <div class="api-logo">{HUBSPOT_LOGO}</div>
            <div class="api-name">HubSpot CRM</div>
            <div class="api-status-badge {status}">
                {"Conectado" if settings.hubspot_api_key else "No configurado"}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        status = "active" if settings.google_api_key else "inactive"
        st.markdown(f"""
        <div class="api-card {status}">
            <div class="api-logo">{GOOGLE_LOGO}</div>
            <div class="api-name">Google Search</div>
            <div class="api-status-badge {status}">
                {"Conectado" if settings.google_api_key else "No configurado"}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        status = "active" if settings.openai_api_key else "inactive"
        st.markdown(f"""
        <div class="api-card {status}">
            <div class="api-logo">{OPENAI_LOGO}</div>
            <div class="api-name">OpenAI</div>
            <div class="api-status-badge {status}">
                {"Conectado" if settings.openai_api_key else "No configurado"}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        status = "active" if settings.anthropic_api_key else "inactive"
        st.markdown(f"""
        <div class="api-card {status}">
            <div class="api-logo">{ANTHROPIC_LOGO}</div>
            <div class="api-name">Anthropic</div>
            <div class="api-status-badge {status}">
                {"Conectado" if settings.anthropic_api_key else "No configurado"}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Subreddits
    st.markdown("""
    <div class="section-header">
        <h2>Subreddits Monitoreados</h2>
        <span class="section-badge">Reddit</span>
    </div>
    """, unsafe_allow_html=True)

    subreddit_html = "".join([f'<span class="keyword-tag">r/{sr}</span>' for sr in settings.subreddits])
    st.markdown(f'<div class="keyword-grid">{subreddit_html}</div>', unsafe_allow_html=True)

    # Keywords
    st.markdown("""
    <div class="section-header">
        <h2>Keywords de Dolor</h2>
        <span class="section-badge">Filtros</span>
    </div>
    """, unsafe_allow_html=True)

    keywords_html = "".join([f'<span class="keyword-tag">{kw}</span>' for kw in settings.pain_keywords])
    st.markdown(f'<div class="keyword-grid">{keywords_html}</div>', unsafe_allow_html=True)

    st.markdown("<div style='height: 2rem'></div>", unsafe_allow_html=True)
    st.info("Para modificar la configuracion, edita el archivo `.env` en la raiz del proyecto")


if __name__ == "__main__":
    main()
