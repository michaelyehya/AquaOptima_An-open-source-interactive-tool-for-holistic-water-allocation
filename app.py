# app.py — Streamlit GUI for the Water Allocation Model
# Run: streamlit run app.py
# ============================================================
# Enhanced visual design: investor-grade dashboard with custom
# theming, premium typography, unified Plotly templates, and
# refined information architecture.
# ============================================================

from water_model import (DataManager, WaterAllocationModel,
                         DATA_FILE, OUTPUT_FILE)
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
import pandas as pd
import numpy as np
import os
import sys
import io
import time

# ── Path setup ───────────────────────────────────────────────
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)


# ─────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='Aquivo — Water Allocation Intelligence',
    page_icon='💧',
    layout='wide',
    initial_sidebar_state='expanded',
)

# ─────────────────────────────────────────────────────────────
# DESIGN SYSTEM — Color palette & typography
# ─────────────────────────────────────────────────────────────
# Primary palette: deep navy (trust/data) + cyan (water) + teal accents
PALETTE = {
    'navy_900':   '#0A1628',  # deepest — body text, headers
    'navy_800':   '#13243D',  # surfaces
    'navy_700':   '#1E3A5F',  # secondary surfaces
    'navy_600':   '#2D5080',  # borders
    'cyan_500':   '#06B6D4',  # primary accent
    'cyan_400':   '#22D3EE',  # hover/highlight
    'cyan_300':   '#67E8F9',  # soft accent
    'teal_500':   '#0D9488',  # secondary accent
    'amber_500':  '#F59E0B',  # warning / cost
    'rose_500':   '#E11D48',  # critical / shortage
    'emerald_500': '#10B981',  # success / equity
    'slate_50':   '#F8FAFC',  # page bg
    'slate_100':  '#F1F5F9',  # card bg
    'slate_200':  '#E2E8F0',  # subtle borders
    'slate_400':  '#94A3B8',  # muted text
    'slate_600':  '#475569',  # body text
    'white':      '#FFFFFF',
}

# Diverging color scale used across all "performance" charts (red→amber→green)
PERF_SCALE = [
    [0.0, '#E11D48'],
    [0.25, '#F59E0B'],
    [0.5, '#FCD34D'],
    [0.75, '#84CC16'],
    [1.0, '#10B981'],
]

# Sequential blues for cost/volume (water-themed)
WATER_SCALE = [
    [0.0, '#E0F7FA'],
    [0.25, '#67E8F9'],
    [0.5, '#22D3EE'],
    [0.75, '#06B6D4'],
    [1.0, '#0E7490'],
]

# Categorical palette for source-mix/multi-series
CATEGORICAL = ['#06B6D4', '#0D9488', '#0EA5E9',
               '#8B5CF6', '#F59E0B', '#EC4899', '#84CC16']

# ─────────────────────────────────────────────────────────────
# Unified Plotly template
# ─────────────────────────────────────────────────────────────
pio.templates['aqua'] = go.layout.Template(
    layout=go.Layout(
        font=dict(
            family='"IBM Plex Sans", "Inter", -apple-system, sans-serif',
            size=14,
            color=PALETTE['navy_900'],
        ),
        title=dict(
            font=dict(
                family='"Space Grotesk", "Inter", sans-serif',
                size=19,
                color=PALETTE['navy_900'],
            ),
            x=0.02, xanchor='left', y=0.96,
        ),
        plot_bgcolor='rgba(248,250,252,0.4)',
        paper_bgcolor='rgba(0,0,0,0)',
        colorway=CATEGORICAL,
        xaxis=dict(
            gridcolor='#E2E8F0',
            linecolor='#94A3B8',
            zerolinecolor='#CBD5E1',
            tickfont=dict(size=13, color=PALETTE['navy_700'],
                          family='"IBM Plex Sans", sans-serif'),
            title=dict(font=dict(
                size=14, color=PALETTE['navy_900'],
                family='"IBM Plex Sans", sans-serif')),
        ),
        yaxis=dict(
            gridcolor='#E2E8F0',
            linecolor='#94A3B8',
            zerolinecolor='#CBD5E1',
            tickfont=dict(size=13, color=PALETTE['navy_700'],
                          family='"IBM Plex Sans", sans-serif'),
            title=dict(font=dict(
                size=14, color=PALETTE['navy_900'],
                family='"IBM Plex Sans", sans-serif')),
        ),
        legend=dict(
            font=dict(size=13, color=PALETTE['navy_900'],
                      family='"IBM Plex Sans", sans-serif'),
            bgcolor='rgba(255,255,255,0.92)',
            bordercolor='#CBD5E1',
            borderwidth=1,
        ),
        margin=dict(l=70, r=30, t=70, b=60),
        hoverlabel=dict(
            bgcolor='white',
            bordercolor=PALETTE['cyan_500'],
            font=dict(size=13, family='"IBM Plex Sans", sans-serif',
                      color=PALETTE['navy_900']),
        ),
    )
)
pio.templates.default = 'aqua'

# ─────────────────────────────────────────────────────────────
# Global CSS — typography, layout, components
# ─────────────────────────────────────────────────────────────
st.markdown(f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
/* ════════════════════════════════════════════════════════════
   GLOBAL TYPOGRAPHY
   ════════════════════════════════════════════════════════════ */
html, body, [class*="css"] {{
    font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: {PALETTE['navy_900']};
}}

h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
    font-family: 'Space Grotesk', 'IBM Plex Sans', sans-serif !important;
    color: {PALETTE['navy_900']};
    letter-spacing: -0.015em;
    font-weight: 600;
}}

.stMarkdown h1 {{ font-size: 2.4rem; font-weight: 700; letter-spacing: -0.025em; }}
.stMarkdown h2 {{ font-size: 1.7rem; font-weight: 600; margin-top: 1.5rem; }}
.stMarkdown h3 {{ font-size: 1.25rem; font-weight: 600; margin-top: 1.2rem; }}
.stMarkdown h4 {{ font-size: 1.05rem; font-weight: 600; }}

p, li, .stMarkdown p {{
    color: {PALETTE['slate_600']};
    line-height: 1.65;
    font-size: 0.95rem;
}}

code, pre, .stCodeBlock {{
    font-family: 'IBM Plex Mono', 'SF Mono', Monaco, monospace !important;
    font-size: 0.88rem;
}}

/* ════════════════════════════════════════════════════════════
   APP BACKGROUND
   ════════════════════════════════════════════════════════════ */
.stApp {{
    background:
        radial-gradient(circle at 0% 0%, rgba(6,182,212,0.04) 0%, transparent 40%),
        radial-gradient(circle at 100% 100%, rgba(13,148,136,0.04) 0%, transparent 40%),
        {PALETTE['slate_50']};
}}

.block-container {{
    padding-top: 2rem;
    padding-bottom: 4rem;
    max-width: 1400px;
}}

/* ════════════════════════════════════════════════════════════
   SIDEBAR — premium dark navy
   ════════════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {PALETTE['navy_900']} 0%, {PALETTE['navy_800']} 100%);
    border-right: 1px solid {PALETTE['navy_700']};
}}

section[data-testid="stSidebar"] * {{
    color: #E2E8F0 !important;
}}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] .stMarkdown strong {{
    color: #FFFFFF !important;
}}

section[data-testid="stSidebar"] hr {{
    border-color: {PALETTE['navy_700']};
    margin: 1.2rem 0;
}}

/* Sidebar caption / subtle text */
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
section[data-testid="stSidebar"] small {{
    color: #94A3B8 !important;
    font-size: 0.82rem !important;
}}

/* Sidebar file uploader */
section[data-testid="stSidebar"] [data-testid="stFileUploader"] {{
    background: rgba(255,255,255,0.04);
    border: 1px dashed {PALETTE['navy_600']};
    border-radius: 10px;
    padding: 12px;
}}

section[data-testid="stSidebar"] [data-testid="stFileUploader"]:hover {{
    border-color: {PALETTE['cyan_400']};
    background: rgba(6,182,212,0.06);
}}

/* Sidebar slider track */
section[data-testid="stSidebar"] [data-baseweb="slider"] [role="slider"] {{
    background: {PALETTE['cyan_400']} !important;
    box-shadow: 0 0 0 4px rgba(34,211,238,0.18) !important;
}}

/* Sidebar primary button — premium gradient */
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {PALETTE['cyan_500']} 0%, {PALETTE['teal_500']} 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    font-weight: 600 !important;
    font-size: 0.98rem !important;
    padding: 0.75rem 1rem !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 14px rgba(6,182,212,0.35), inset 0 1px 0 rgba(255,255,255,0.18) !important;
    letter-spacing: 0.01em !important;
    transition: all 0.2s ease;
}}

section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {{
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(6,182,212,0.45), inset 0 1px 0 rgba(255,255,255,0.22) !important;
}}

/* ════════════════════════════════════════════════════════════
   TABS — pill-style with gradient active state
   ════════════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {{
    gap: 4px;
    background: transparent;
    border-bottom: 2px solid {PALETTE['slate_200']};
    padding-bottom: 0;
    margin-bottom: 1.5rem;
}}

.stTabs [data-baseweb="tab-list"] button {{
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    padding: 12px 22px !important;
    background: transparent !important;
    border: none !important;
    border-radius: 8px 8px 0 0 !important;
    color: {PALETTE['slate_400']} !important;
    transition: all 0.2s ease;
    letter-spacing: 0.005em;
    margin-bottom: -2px;
    border-bottom: 2px solid transparent !important;
}}

.stTabs [data-baseweb="tab-list"] button:hover {{
    color: {PALETTE['navy_700']} !important;
    background: {PALETTE['slate_100']} !important;
}}

.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
    color: {PALETTE['cyan_500']} !important;
    background: transparent !important;
    border-bottom: 2px solid {PALETTE['cyan_500']} !important;
}}

.stTabs [data-baseweb="tab-highlight"] {{
    display: none !important;
}}

/* ════════════════════════════════════════════════════════════
   METRICS — refined cards with subtle gradients
   ════════════════════════════════════════════════════════════ */
[data-testid="stMetric"] {{
    background: linear-gradient(135deg, #FFFFFF 0%, {PALETTE['slate_50']} 100%);
    border: 1px solid {PALETTE['slate_200']};
    border-radius: 12px;
    padding: 18px 20px;
    box-shadow: 0 1px 3px rgba(10,22,40,0.04), 0 1px 2px rgba(10,22,40,0.06);
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
}}

[data-testid="stMetric"]::before {{
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: linear-gradient(180deg, {PALETTE['cyan_500']}, {PALETTE['teal_500']});
}}

[data-testid="stMetric"]:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(10,22,40,0.08), 0 2px 4px rgba(10,22,40,0.06);
    border-color: {PALETTE['cyan_300']};
}}

[data-testid="stMetric"] [data-testid="stMetricLabel"] {{
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: {PALETTE['slate_400']} !important;
    margin-bottom: 6px;
}}

[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: {PALETTE['navy_900']} !important;
    line-height: 1.2;
}}

/* ════════════════════════════════════════════════════════════
   BUTTONS — body
   ════════════════════════════════════════════════════════════ */
.stButton > button {{
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-weight: 500 !important;
    border-radius: 8px !important;
    border: 1px solid {PALETTE['slate_200']} !important;
    transition: all 0.15s ease;
}}

.stButton > button:hover {{
    border-color: {PALETTE['cyan_500']} !important;
    color: {PALETTE['cyan_500']} !important;
}}

/* ════════════════════════════════════════════════════════════
   ALERTS / INFO BOXES
   ════════════════════════════════════════════════════════════ */
[data-testid="stAlert"] {{
    border-radius: 10px;
    border: none;
    padding: 14px 18px;
    box-shadow: 0 1px 2px rgba(10,22,40,0.04);
}}

[data-testid="stAlert"][kind="info"] {{
    background: linear-gradient(135deg, rgba(6,182,212,0.08) 0%, rgba(6,182,212,0.04) 100%);
    border-left: 3px solid {PALETTE['cyan_500']};
}}

[data-testid="stAlert"][kind="success"] {{
    background: linear-gradient(135deg, rgba(16,185,129,0.08) 0%, rgba(16,185,129,0.04) 100%);
    border-left: 3px solid {PALETTE['emerald_500']};
}}

[data-testid="stAlert"][kind="warning"] {{
    background: linear-gradient(135deg, rgba(245,158,11,0.08) 0%, rgba(245,158,11,0.04) 100%);
    border-left: 3px solid {PALETTE['amber_500']};
}}

[data-testid="stAlert"][kind="error"] {{
    background: linear-gradient(135deg, rgba(225,29,72,0.08) 0%, rgba(225,29,72,0.04) 100%);
    border-left: 3px solid {PALETTE['rose_500']};
}}

/* ════════════════════════════════════════════════════════════
   DATAFRAMES
   ════════════════════════════════════════════════════════════ */
[data-testid="stDataFrame"] {{
    border-radius: 10px;
    border: 1px solid {PALETTE['slate_200']};
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(10,22,40,0.04);
}}

/* ════════════════════════════════════════════════════════════
   SLIDERS (main page)
   ════════════════════════════════════════════════════════════ */
.main [data-baseweb="slider"] [role="slider"] {{
    background: {PALETTE['cyan_500']} !important;
    box-shadow: 0 0 0 4px rgba(6,182,212,0.18) !important;
}}

/* ════════════════════════════════════════════════════════════
   EXPANDERS
   ════════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {{
    border: 1px solid {PALETTE['slate_200']};
    border-radius: 10px;
    background: #FFFFFF;
    box-shadow: 0 1px 2px rgba(10,22,40,0.03);
}}

[data-testid="stExpander"] summary {{
    font-weight: 600;
    color: {PALETTE['navy_900']};
}}

/* ════════════════════════════════════════════════════════════
   PROGRESS BAR
   ════════════════════════════════════════════════════════════ */
[data-testid="stProgressBar"] > div > div {{
    background: linear-gradient(90deg, {PALETTE['cyan_500']}, {PALETTE['teal_500']}) !important;
}}

/* ════════════════════════════════════════════════════════════
   CUSTOM HERO & CARDS
   ════════════════════════════════════════════════════════════ */
.aqua-hero {{
    position: relative;
    padding: 56px 48px 48px 48px;
    border-radius: 20px;
    margin-bottom: 2rem;
    background:
        radial-gradient(circle at 85% 15%, rgba(34,211,238,0.18) 0%, transparent 45%),
        radial-gradient(circle at 15% 85%, rgba(13,148,136,0.18) 0%, transparent 45%),
        linear-gradient(135deg, {PALETTE['navy_900']} 0%, {PALETTE['navy_800']} 60%, {PALETTE['navy_700']} 100%);
    color: white;
    overflow: hidden;
    box-shadow: 0 20px 50px rgba(10,22,40,0.18), 0 6px 16px rgba(10,22,40,0.12);
}}

.aqua-hero::before {{
    content: '';
    position: absolute;
    top: 0; right: 0; bottom: 0; left: 0;
    background-image:
        linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
    background-size: 32px 32px;
    pointer-events: none;
}}

.aqua-hero-content {{ position: relative; z-index: 1; }}

.aqua-eyebrow {{
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    font-weight: 500;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: {PALETTE['cyan_300']};
    padding: 5px 12px;
    border: 1px solid rgba(103,232,249,0.35);
    border-radius: 999px;
    margin-bottom: 18px;
    background: rgba(103,232,249,0.08);
}}

.aqua-hero h1 {{
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 3.4rem !important;
    font-weight: 700 !important;
    line-height: 1.05 !important;
    letter-spacing: -0.03em !important;
    color: #FFFFFF !important;
    margin: 0 0 14px 0 !important;
}}

.aqua-hero h1 .accent {{
    background: linear-gradient(135deg, {PALETTE['cyan_300']}, {PALETTE['cyan_400']});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

.aqua-hero p.lede {{
    font-size: 1.1rem !important;
    line-height: 1.55 !important;
    max-width: 720px;
    color: #CBD5E1 !important;
    margin: 0 0 28px 0 !important;
}}

.aqua-stats {{
    display: flex;
    gap: 36px;
    flex-wrap: wrap;
    padding-top: 24px;
    border-top: 1px solid rgba(255,255,255,0.08);
}}

.aqua-stat .num {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.7rem;
    font-weight: 700;
    color: #FFFFFF;
    display: block;
    line-height: 1;
}}

.aqua-stat .lbl {{
    font-size: 0.78rem;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 6px;
    display: block;
}}

/* Feature cards on landing */
.aqua-card {{
    background: #FFFFFF;
    border: 1px solid {PALETTE['slate_200']};
    border-radius: 14px;
    padding: 22px 22px 20px 22px;
    height: 100%;
    transition: all 0.2s ease;
    box-shadow: 0 1px 3px rgba(10,22,40,0.04);
    position: relative;
    overflow: hidden;
}}

.aqua-card:hover {{
    transform: translateY(-3px);
    box-shadow: 0 12px 28px rgba(10,22,40,0.08), 0 4px 8px rgba(10,22,40,0.06);
    border-color: {PALETTE['cyan_300']};
}}

.aqua-card .icon-pill {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 10px;
    background: linear-gradient(135deg, rgba(6,182,212,0.12), rgba(13,148,136,0.12));
    border: 1px solid rgba(6,182,212,0.25);
    font-size: 1.3rem;
    margin-bottom: 14px;
}}

.aqua-card h4 {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.05rem;
    font-weight: 600;
    color: {PALETTE['navy_900']};
    margin: 0 0 8px 0;
}}

.aqua-card p {{
    font-size: 0.88rem;
    color: {PALETTE['slate_600']};
    line-height: 1.55;
    margin: 0;
}}

/* Objective callout cards */
.aqua-obj {{
    background: linear-gradient(135deg, #FFFFFF 0%, {PALETTE['slate_50']} 100%);
    border: 1px solid {PALETTE['slate_200']};
    border-left: 4px solid var(--obj-color, {PALETTE['cyan_500']});
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 12px;
    transition: all 0.2s ease;
}}

.aqua-obj:hover {{
    box-shadow: 0 4px 12px rgba(10,22,40,0.06);
}}

.aqua-obj .obj-tag {{
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--obj-color, {PALETTE['cyan_500']});
    background: rgba(6,182,212,0.08);
    padding: 3px 8px;
    border-radius: 4px;
    margin-bottom: 8px;
}}

.aqua-obj h4 {{
    font-size: 1.05rem;
    margin: 0 0 6px 0;
    color: {PALETTE['navy_900']};
}}

.aqua-obj p {{
    margin: 0;
    font-size: 0.88rem;
    color: {PALETTE['slate_600']};
    line-height: 1.55;
}}

/* Page section header */
.aqua-section-head {{
    border-bottom: 1px solid {PALETTE['slate_200']};
    padding-bottom: 14px;
    margin: 0 0 1.5rem 0;
}}

.aqua-section-head .eyebrow {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: {PALETTE['cyan_500']};
    display: block;
    margin-bottom: 6px;
}}

.aqua-section-head h2 {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.85rem;
    font-weight: 700;
    color: {PALETTE['navy_900']};
    margin: 0;
    letter-spacing: -0.02em;
}}

.aqua-section-head .sub {{
    color: {PALETTE['slate_600']};
    font-size: 0.95rem;
    line-height: 1.5;
    margin-top: 8px;
    max-width: 880px;
}}

/* Status pill */
.status-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 999px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.74rem;
    font-weight: 500;
    letter-spacing: 0.05em;
}}

.status-pill.live {{
    background: rgba(16,185,129,0.12);
    color: {PALETTE['emerald_500']};
    border: 1px solid rgba(16,185,129,0.3);
}}

.status-pill.live::before {{
    content: '';
    width: 6px; height: 6px;
    border-radius: 50%;
    background: {PALETTE['emerald_500']};
    animation: pulse 1.8s infinite;
}}

@keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.4; }}
}}

/* Insight callout — used at top of analytical sections */
.aqua-insight {{
    background: linear-gradient(135deg, rgba(6,182,212,0.06) 0%, rgba(13,148,136,0.04) 100%);
    border: 1px solid rgba(6,182,212,0.18);
    border-radius: 12px;
    padding: 16px 20px;
    margin: 12px 0 20px 0;
    display: flex;
    gap: 14px;
    align-items: flex-start;
}}

.aqua-insight .ico {{
    flex-shrink: 0;
    width: 32px; height: 32px;
    border-radius: 8px;
    background: linear-gradient(135deg, {PALETTE['cyan_500']}, {PALETTE['teal_500']});
    color: white;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem;
    box-shadow: 0 2px 6px rgba(6,182,212,0.25);
}}

.aqua-insight .body {{
    flex: 1;
    font-size: 0.92rem;
    line-height: 1.55;
    color: {PALETTE['navy_900']};
}}

.aqua-insight .body strong {{
    color: {PALETTE['navy_900']};
}}

/* Scoreboard — used for top-of-tab summary */
.scoreboard {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 14px;
    margin-bottom: 1.5rem;
}}

.scoreboard .cell {{
    background: white;
    border: 1px solid {PALETTE['slate_200']};
    border-radius: 12px;
    padding: 16px 18px;
    box-shadow: 0 1px 2px rgba(10,22,40,0.03);
    position: relative;
    overflow: hidden;
}}

.scoreboard .cell .lbl {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.74rem;
    font-weight: 600;
    color: {PALETTE['slate_400']};
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}

.scoreboard .cell .val {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: {PALETTE['navy_900']};
    margin-top: 4px;
    line-height: 1.2;
}}

.scoreboard .cell .delta {{
    font-size: 0.78rem;
    color: {PALETTE['slate_400']};
    margin-top: 2px;
}}

/* hide streamlit chrome */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header[data-testid="stHeader"] {{ background: transparent; }}

</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Session state initialization
# ─────────────────────────────────────────────────────────────
for key, default in [
    ('pareto',        None),
    ('all_sols',      None),
    ('bounds',        None),
    ('ws_df',         None),
    ('social_params', None),
    ('regional_mode', False),
    ('run_log',       ''),
    ('data_path',     os.path.join(APP_DIR, DATA_FILE)),
    ('active_tab',    0),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def topsis(df, weights, benefit_flags):
    X = df.values.astype(float)
    norms = np.sqrt((X ** 2).sum(axis=0))
    norms = np.where(norms < 1e-12, 1.0, norms)
    R = X / norms
    W = np.array(weights, dtype=float)
    V = R * W
    Aplus = np.where(benefit_flags, V.max(axis=0), V.min(axis=0))
    Aminus = np.where(benefit_flags, V.min(axis=0), V.max(axis=0))
    d_plus = np.sqrt(((V - Aplus) ** 2).sum(axis=1))
    d_minus = np.sqrt(((V - Aminus) ** 2).sum(axis=1))
    denom = d_plus + d_minus
    scores = np.where(denom < 1e-12, 0.5, d_minus / denom)
    ranks = scores.argsort()[::-1].argsort() + 1
    return scores, ranks


def fmt_large(val):
    try:
        return f'{float(val):,.0f}'
    except Exception:
        return str(val)


def _color_from_scale(t):
    """Linear interpolation across PERF_SCALE for t∈[0,1].
    Returns a hex color suitable for inline SVG fills.
    """
    t = max(0.0, min(1.0, float(t)))
    # PERF_SCALE stops are at 0, 0.25, 0.5, 0.75, 1.0
    stops = [(0.0,   (225, 29, 72)),    # rose
             (0.25,  (245, 158, 11)),   # amber
             (0.5,   (252, 211, 77)),   # yellow
             (0.75,  (132, 204, 22)),   # lime
             (1.0,   (16, 185, 129))]   # emerald
    for i in range(len(stops) - 1):
        s0, c0 = stops[i]
        s1, c1 = stops[i + 1]
        if s0 <= t <= s1:
            f = (t - s0) / (s1 - s0) if s1 > s0 else 0.0
            r = int(c0[0] + (c1[0] - c0[0]) * f)
            g = int(c0[1] + (c1[1] - c0[1]) * f)
            b = int(c0[2] + (c1[2] - c0[2]) * f)
            return f'#{r:02X}{g:02X}{b:02X}'
    return '#10B981'


def heat_style(df, columns, palette='cyan', invert=False):
    """Apply a column-wise heatmap background WITHOUT requiring matplotlib.

    Returns a Styler with per-cell background-color set by min/max linear
    scaling within each column. `palette` picks the hue family; `invert`
    flips so that lower values get darker shading (useful for cost/energy
    where small is good).
    """
    palettes = {
        'cyan':   [(240, 253, 255), (6, 182, 212)],     # light → cyan
        'green':  [(236, 253, 245), (16, 185, 129)],    # light → emerald
        'orange': [(255, 247, 237), (245, 158, 11)],    # light → amber
        'blue':   [(239, 246, 255), (37, 99, 235)],     # light → blue
        'rose':   [(255, 241, 242), (225, 29, 72)],     # light → rose
    }
    lo_rgb, hi_rgb = palettes.get(palette, palettes['cyan'])

    def _col_styler(s):
        vals = s.astype(float)
        vmin, vmax = vals.min(), vals.max()
        rng = vmax - vmin if vmax > vmin else 1.0
        styles = []
        for v in vals:
            t = (v - vmin) / rng
            if invert:
                t = 1 - t
            r = int(lo_rgb[0] + (hi_rgb[0] - lo_rgb[0]) * t)
            g = int(lo_rgb[1] + (hi_rgb[1] - lo_rgb[1]) * t)
            b = int(lo_rgb[2] + (hi_rgb[2] - lo_rgb[2]) * t)
            # darker text on light cells, white text on dark cells
            text = '#0A1628' if t < 0.55 else '#FFFFFF'
            styles.append(
                f'background-color: rgb({r},{g},{b}); color: {text};')
        return styles

    valid_cols = [c for c in columns if c in df.columns]
    return df.style.apply(_col_styler, subset=valid_cols, axis=0)


def section_head(eyebrow, title, sub=''):
    """Render a styled section header."""
    sub_html = f'<div class="sub">{sub}</div>' if sub else ''
    st.markdown(f"""
    <div class="aqua-section-head">
        <span class="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


def insight(text, icon='💡'):
    """Render a key-insight callout."""
    st.markdown(f"""
    <div class="aqua-insight">
        <div class="ico">{icon}</div>
        <div class="body">{text}</div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    # Brand block
    st.markdown(f"""
    <div style="padding: 8px 0 4px 0;">
        <div style="display:flex; align-items:center; gap:12px;">
            <div style="width:42px; height:42px; border-radius:11px;
                        background: linear-gradient(135deg, {PALETTE['cyan_400']}, {PALETTE['teal_500']});
                        display:flex; align-items:center; justify-content:center;
                        font-size:1.5rem; box-shadow: 0 4px 12px rgba(6,182,212,0.4);">💧</div>
            <div>
                <div style="font-family:'Space Grotesk',sans-serif; font-size:1.25rem;
                            font-weight:700; color:#FFFFFF; line-height:1;
                            letter-spacing:-0.02em;">Aquivo</div>
                <div style="font-family:'IBM Plex Mono',monospace; font-size:0.7rem;
                            color:#67E8F9; letter-spacing:0.12em; margin-top:3px;">
                    WATER ALLOCATION
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <p style="color:#94A3B8 !important; font-size:0.85rem; margin: 14px 0 0 0;
              line-height:1.5;">
        Multi-objective optimization for sustainable water resource planning.
    </p>
    """, unsafe_allow_html=True)

    st.divider()

    # Data section
    st.markdown(f"""
    <div style="font-family:'IBM Plex Mono',monospace; font-size:0.72rem;
                color:#67E8F9; letter-spacing:0.15em; margin-bottom:10px;">
        ◆ DATA INPUT
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        'Upload WaterAllocationData.xlsx',
        type=['xlsx'],
        help='Leave blank to use (or auto-generate) the placeholder data file.',
        label_visibility='collapsed',
    )
    if uploaded is not None:
        save_path = os.path.join(APP_DIR, 'uploaded_data.xlsx')
        with open(save_path, 'wb') as f:
            f.write(uploaded.read())
        st.session_state['data_path'] = save_path
        st.success('Custom data file loaded.')

    if not os.path.exists(st.session_state['data_path']):
        st.warning(
            f'Input file not found. Upload an `.xlsx` to proceed.')
    else:
        st.markdown(
            '<div style="margin-top:8px;"><span class="status-pill live">'
            'DATA READY</span></div>',
            unsafe_allow_html=True)

    st.divider()

    # Solver section
    st.markdown(f"""
    <div style="font-family:'IBM Plex Mono',monospace; font-size:0.72rem;
                color:#67E8F9; letter-spacing:0.15em; margin-bottom:10px;">
        ◆ SOLVER CONFIG
    </div>
    """, unsafe_allow_html=True)

    n_eps = st.slider(
        'Pareto density (n_eps)',
        min_value=3, max_value=15, value=5, step=1,
        help='Total sub-problems = n_eps². Higher = denser Pareto front.',
    )
    st.caption(f'≈ {n_eps**2} sub-problem solves')

    verbose_solver = st.checkbox('Verbose solver output', value=False)

    st.divider()

    run_btn = st.button('▶  RUN OPTIMIZATION', type='primary',
                        use_container_width=True)

    st.markdown(f"""
    <div style="margin-top: 24px; padding: 12px; background: rgba(255,255,255,0.03);
                border-radius: 8px; border: 1px solid {PALETTE['navy_700']};">
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.7rem;
                    color:#67E8F9; letter-spacing:0.15em; margin-bottom:6px;">
            ◆ ENGINE
        </div>
        <div style="font-size:0.78rem; color:#CBD5E1; line-height:1.5;">
            scipy HiGHS LP solver<br>
            ε-constraint method<br>
            Pareto front + TOPSIS MCDM
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Run model
# ─────────────────────────────────────────────────────────────
if run_btn:
    data_path = st.session_state['data_path']
    if not os.path.exists(data_path):
        st.error('Data file not found. Create the placeholder data first.')
        st.stop()

    log_buf = io.StringIO()
    progress = st.progress(0, text='Loading data...')
    status = st.empty()

    try:
        dm = DataManager(data_path)
        dm.load_all()

        model = WaterAllocationModel(dm)
        progress.progress(
            5, text='Computing normalization bounds (Phase 1)...')

        model.precompute_bounds(verbose=True)
        progress.progress(40, text='Generating Pareto front (Phase 2)...')

        pareto = model.generate_pareto_front(
            n_eps=n_eps, verbose=verbose_solver)
        progress.progress(95, text='Saving results...')

        out_path = os.path.join(APP_DIR, OUTPUT_FILE)
        model.save_results_to_excel(out_path)
        progress.progress(100, text='Done.')

        st.session_state['pareto'] = pareto
        st.session_state['all_sols'] = model.all_solutions
        st.session_state['bounds'] = model.bounds
        st.session_state['ws_df'] = dm.water_sources
        st.session_state['social_params'] = dm.social_params
        st.session_state['regional_mode'] = dm.regional_mode

        if pareto:
            status.success(
                f'✓ Optimization complete — {len(pareto)} non-dominated solutions found.')
        else:
            status.warning(
                'Model complete but no non-dominated solutions found.')

    except Exception as exc:
        progress.empty()
        st.error(f'Model error: {exc}')
        st.stop()


# ─────────────────────────────────────────────────────────────
# Main dashboard
# ─────────────────────────────────────────────────────────────
pareto = st.session_state.get('pareto')
all_sols = st.session_state.get('all_sols')
ws_df = st.session_state.get('ws_df')
social_params = st.session_state.get('social_params')
regional_mode = st.session_state.get('regional_mode', False)


if not pareto:
    # ══════════════════════════════════════════════════════════
    # LANDING PAGE — investor-grade hero
    # ══════════════════════════════════════════════════════════
    st.markdown(f"""
    <div class="aqua-hero">
        <div class="aqua-hero-content">
            <span class="aqua-eyebrow">◆ DECISION INTELLIGENCE FOR WATER PLANNING</span>
            <h1>Optimize the trade-offs.<br>
                <span class="accent">Allocate water with confidence.</span></h1>
            <p class="lede">
                A multi-objective optimization platform that simultaneously balances
                economic cost, environmental footprint, and social equity, surfacing
                the full Pareto frontier of viable strategies for water utilities,
                regulators, and infrastructure planners.
            </p>
            <div class="aqua-stats">
                <div class="aqua-stat">
                    <span class="num">3</span>
                    <span class="lbl">Competing Objectives</span>
                </div>
                <div class="aqua-stat">
                    <span class="num">5</span>
                    <span class="lbl">Equity Sub-Indicators</span>
                </div>
                <div class="aqua-stat">
                    <span class="num">N²</span>
                    <span class="lbl">ε-Constraint Grid Solves</span>
                </div>
                <div class="aqua-stat">
                    <span class="num">∞</span>
                    <span class="lbl">Trade-off Scenarios</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Two-column intro
    intro_col, obj_col = st.columns([1.2, 1], gap='large')

    with intro_col:
        section_head('◆ THE PROBLEM',
                     'Water planning has no single best answer.')
        st.markdown("""
        Water resource planning involves **competing goals** — keeping costs
        contained, reducing environmental impact, and ensuring fair access for all
        communities. There is rarely a single "best" strategy; instead, planners
        face a spectrum of trade-offs.

        Aquivo runs a rigorous **multi-objective optimization** that
        simultaneously solves all three goals and produces the **Pareto front** —
        the set of solutions where you cannot improve any one objective without
        making at least one other worse.

        Decision-makers then use the built-in **TOPSIS ranking engine** to weight
        their priorities and surface the solution that best fits their decision
        context.
        """)

        # Workflow chevrons
        st.markdown(f"""
        <div style="display:flex; gap:0; margin-top:1.2rem;
                    background: white; border-radius: 12px;
                    border: 1px solid {PALETTE['slate_200']};
                    overflow: hidden;
                    box-shadow: 0 1px 3px rgba(10,22,40,0.04);">
        """, unsafe_allow_html=True)

        steps = [
            ('01', 'Upload', 'Load your water allocation data'),
            ('02', 'Configure', 'Tune solver density'),
            ('03', 'Optimize', 'Run the Pareto solver'),
            ('04', 'Decide', 'Rank with TOPSIS'),
        ]
        cols = st.columns(4)
        for col, (num, title, desc) in zip(cols, steps):
            with col:
                st.markdown(f"""
                <div style="padding:16px; text-align:left;
                            border-right: 1px solid {PALETTE['slate_200']};">
                    <div style="font-family:'IBM Plex Mono',monospace; font-size:0.75rem;
                                color:{PALETTE['cyan_500']}; font-weight:600;
                                letter-spacing:0.1em;">{num}</div>
                    <div style="font-family:'Space Grotesk',sans-serif; font-size:1rem;
                                font-weight:600; color:{PALETTE['navy_900']};
                                margin-top:4px;">{title}</div>
                    <div style="font-size:0.8rem; color:{PALETTE['slate_400']};
                                margin-top:4px; line-height:1.4;">{desc}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with obj_col:
        section_head('◆ THE OBJECTIVES',
                     'Three competing objective functions.')
        st.markdown(f"""
        <div class="aqua-obj" style="--obj-color:{PALETTE['amber_500']};">
            <span class="obj-tag" style="color:{PALETTE['amber_500']};
                  background:rgba(245,158,11,0.08);">OF1 · MINIMIZE</span>
            <h4>💰 Economic Cost</h4>
            <p>Total annual water supply cost across all source-technology
            pathways (USD/yr).</p>
        </div>
        <div class="aqua-obj" style="--obj-color:{PALETTE['emerald_500']};">
            <span class="obj-tag" style="color:{PALETTE['emerald_500']};
                  background:rgba(16,185,129,0.08);">OF2 · MINIMIZE</span>
            <h4>🌿 Energy & Environmental Footprint</h4>
            <p>Total electricity consumption (kWh/yr) — environmental proxy
            via grid CO₂ intensity.</p>
        </div>
        <div class="aqua-obj" style="--obj-color:{PALETTE['cyan_500']};">
            <span class="obj-tag" style="color:{PALETTE['cyan_500']};
                  background:rgba(6,182,212,0.08);">OF3 · MAXIMIZE</span>
            <h4>⚖️ Social Equity (WE)</h4>
            <p>Composite of <em>Labour Intensity, Gini Coefficient, Shortage
            Variance, Williamson Coefficient</em>, and <em>Guarantee Rate</em>.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

    # Page navigation cards
    section_head('◆ INSIDE THE DASHBOARD',
                 'Four analytical surfaces for full insight.')

    page_info = [
        ('📊', 'Pareto Front',
         'Interactive 3-D and 2-D projections of every non-dominated solution. '
         'Rotate, zoom, and inspect the full trade-off surface.'),
        ('🏆', 'MCDM / TOPSIS',
         'Weight your priorities and rank solutions by closeness to the ideal. '
         'Radar plots compare the top candidates side-by-side.'),
        ('🔍', 'Solution Detail',
         'Drill into any solution to inspect every source-tech-end-use pathway, '
         'with cost, energy, CO₂, and unit-economics breakdowns.'),
        ('🗺️', 'Regional Analysis',
         'Geographic equity view: supply vs demand, shortage rates, and '
         'source-mix per hydrologic region.'),
    ]

    cols = st.columns(4, gap='medium')
    for col, (icon, title, desc) in zip(cols, page_info):
        with col:
            st.markdown(f"""
            <div class="aqua-card">
                <div class="icon-pill">{icon}</div>
                <h4>{title}</h4>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)

    st.info(
        '**Ready to begin?** Configure the solver in the sidebar and click '
        '**▶ RUN OPTIMIZATION** to generate the Pareto front. If no data file '
        'is loaded, the model will auto-generate placeholder data on first run.'
    )
    st.stop()


# ─────────────────────────────────────────────────────────────
# Build main dataframe
# ─────────────────────────────────────────────────────────────
df_pareto = pd.DataFrame([{
    'Point':       k + 1,
    'OF1_Cost':    s['OF1'],
    'OF2b_Energy': s['OF2b'],
    'OF3_Social':  s['OF3'],
    'LI':          s['LI'],
    'WGC':         s['WGC'],
    'WSRV':        s['WSRV'],
    'WC':          s['WC'],
    'WSGR':        s['WSGR'],
} for k, s in enumerate(pareto)])


# ─────────────────────────────────────────────────────────────
# Top-of-app summary banner (post-run)
# ─────────────────────────────────────────────────────────────
best_cost = df_pareto['OF1_Cost'].min()
best_eq = df_pareto['OF3_Social'].max()
best_eng = df_pareto['OF2b_Energy'].min()
total_feasible = len(all_sols) if all_sols else len(pareto)

st.markdown(f"""
<div class="aqua-hero" style="padding: 28px 36px; margin-bottom: 1.5rem;">
    <div class="aqua-hero-content"
         style="display:flex; align-items:center; justify-content:space-between;
                flex-wrap: wrap; gap: 24px;">
        <div>
            <span class="aqua-eyebrow">◆ OPTIMIZATION RESULTS</span>
            <h1 style="font-size: 2rem !important; margin: 8px 0 0 0 !important;">
                Pareto frontier <span class="accent">resolved.</span>
            </h1>
            <p style="color:#CBD5E1; font-size:0.95rem; margin: 6px 0 0 0;">
                {len(pareto)} non-dominated solutions from {total_feasible} feasible solves.
            </p>
        </div>
        <div style="display:flex; gap:24px; flex-wrap:wrap;">
            <div class="aqua-stat" style="text-align:right;">
                <span class="num">${best_cost/1e6:,.1f}M<span style="font-size:0.95rem; opacity:0.7;">/yr</span></span>
                <span class="lbl">Lowest Cost</span>
            </div>
            <div class="aqua-stat" style="text-align:right;">
                <span class="num">{best_eng/1e9:.2f}<span style="font-size:0.95rem; opacity:0.7;"> GWh/yr</span></span>
                <span class="lbl">Lowest Energy Use</span>
            </div>
            <div class="aqua-stat" style="text-align:right;">
                <span class="num">{best_eq:.3f}</span>
                <span class="lbl">Top Equity Score</span>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────
TAB_LABELS = [
    '📊  Pareto Front',
    '🏆  MCDM · TOPSIS',
    '🔍  Solution Detail',
    '🗺️  Regional Analysis',
]
tab_pareto, tab_topsis, tab_detail, tab_regional = st.tabs(TAB_LABELS)

_active = st.session_state.get('active_tab', 0)
st.components.v1.html(f"""
<script>
(function() {{
    const idx = {_active};
    function clickTab() {{
        const tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
        if (tabs.length > idx) {{
            tabs[idx].click();
        }} else {{
            setTimeout(clickTab, 80);
        }}
    }}
    setTimeout(clickTab, 80);
}})();
</script>
""", height=0)


# ═══════════════════════════════════════════════════════════
# TAB 1 — PARETO FRONT
# ═══════════════════════════════════════════════════════════
with tab_pareto:
    section_head(
        '◆ TRADE-OFF SURFACE',
        'The Pareto Frontier',
        'Each point is a strategy where no objective can be improved without '
        'sacrificing another. The shape of the frontier reveals how competing '
        'goals conflict and where the sweet spots lie.'
    )

    # Top metrics row — built as custom HTML so all four cards have
    # identical formatting. (st.metric mis-parses ranges like "9,972M to
    # 15,542M" as a delta and tints the first number green, which broke
    # the visual symmetry across the row.)
    def _kpi_card(label, value):
        return f"""
        <div style="
            background: linear-gradient(135deg, #FFFFFF 0%, {PALETTE['slate_50']} 100%);
            border: 1px solid {PALETTE['slate_200']};
            border-radius: 12px;
            padding: 18px 20px;
            box-shadow: 0 1px 3px rgba(10,22,40,0.04), 0 1px 2px rgba(10,22,40,0.06);
            position: relative;
            overflow: hidden;
            min-height: 92px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        ">
            <div style="position:absolute; top:0; left:0; width:3px;
                        height:100%;
                        background: linear-gradient(180deg, {PALETTE['cyan_500']}, {PALETTE['teal_500']});">
            </div>
            <div style="font-family:'IBM Plex Sans',sans-serif;
                        font-size:0.78rem; font-weight:600;
                        text-transform:uppercase; letter-spacing:0.06em;
                        color:{PALETTE['slate_400']}; margin-bottom:6px;
                        white-space:nowrap;">{label}</div>
            <div style="font-family:'Space Grotesk',sans-serif;
                        font-size:1.4rem; font-weight:700;
                        color:{PALETTE['navy_900']}; line-height:1.2;
                        white-space:nowrap;">{value}</div>
        </div>
        """

    pcol1, pcol2, pcol3, pcol4 = st.columns(4)
    with pcol1:
        st.markdown(_kpi_card(
            'Solutions on Frontier', f'{len(pareto)}'
        ), unsafe_allow_html=True)
    with pcol2:
        st.markdown(_kpi_card(
            'Cost Range (USD/yr)',
            f'${df_pareto["OF1_Cost"].min()/1e6:,.1f}M – '
            f'${df_pareto["OF1_Cost"].max()/1e6:,.1f}M',
        ), unsafe_allow_html=True)
    with pcol3:
        st.markdown(_kpi_card(
            'Energy Range (GWh/yr)',
            f'{df_pareto["OF2b_Energy"].min()/1e9:,.2f} – '
            f'{df_pareto["OF2b_Energy"].max()/1e9:,.2f}',
        ), unsafe_allow_html=True)
    with pcol4:
        st.markdown(_kpi_card(
            'Equity Score Range',
            f'{df_pareto["OF3_Social"].min():,.3f} – '
            f'{df_pareto["OF3_Social"].max():,.3f}',
        ), unsafe_allow_html=True)

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    # Color dimension selector
    color_choice = st.selectbox(
        'Color the frontier by:',
        options=['OF3_Social', 'OF1_Cost', 'OF2b_Energy'],
        format_func=lambda c: {
            'OF3_Social':  '⚖️  Social Equity (WE)',
            'OF1_Cost':    '💰  Economic Cost (USD/yr)',
            'OF2b_Energy': '🌿  Total Energy (kWh/yr)',
        }[c],
        help='Choose which objective drives the color scale on the 3-D chart.',
    )
    color_labels = {
        'OF3_Social':  'OF3 Social Equity',
        'OF1_Cost':    'OF1 Cost (USD/yr)',
        'OF2b_Energy': 'OF2b Energy (kWh/yr)',
    }

    # When coloring by "lower is better" objectives (cost, energy),
    # invert the perf scale so green = low (good) and red = high (bad).
    # OF3 (equity) stays as-is: green = high (good), red = low (bad).
    minimize_objectives = {'OF1_Cost', 'OF2b_Energy'}
    if color_choice in minimize_objectives:
        # Reverse colors but keep the [0..1] stop positions ascending
        stops = [s[0] for s in PERF_SCALE]
        colors = [s[1] for s in reversed(PERF_SCALE)]
        active_colorscale = [[stops[i], colors[i]]
                             for i in range(len(PERF_SCALE))]
    else:
        active_colorscale = PERF_SCALE

    # ── 3-D scatter (hero chart) ──────────────────────────────
    fig3d = go.Figure(go.Scatter3d(
        x=df_pareto['OF1_Cost'],
        y=df_pareto['OF2b_Energy'],
        z=df_pareto['OF3_Social'],
        mode='markers+text',
        text=df_pareto['Point'].astype(str),
        textposition='top center',
        textfont=dict(size=12, color=PALETTE['navy_900'],
                      family='"IBM Plex Sans", sans-serif'),
        marker=dict(
            size=9,
            color=df_pareto[color_choice],
            colorscale=active_colorscale,
            colorbar=dict(
                title=dict(text=color_labels[color_choice],
                           font=dict(size=13, color=PALETTE['navy_900'])),
                thickness=14, len=0.75,
                tickfont=dict(size=12, color=PALETTE['navy_700']),
                outlinewidth=0,
            ),
            showscale=True,
            line=dict(color='white', width=1),
            opacity=0.92,
        ),
        hovertemplate=(
            '<b>Solution %{text}</b><br>'
            'Cost: $%{x:,.0f}/yr<br>'
            'Energy: %{y:,.0f} kWh/yr<br>'
            'Equity: %{z:.4f}<extra></extra>'
        ),
    ))
    fig3d.update_layout(
        scene=dict(
            xaxis=dict(title=dict(text='Cost (USD/yr)',
                                  font=dict(size=14, color=PALETTE['navy_900'])),
                       backgroundcolor='rgba(248,250,252,0.5)',
                       gridcolor='#E2E8F0', zerolinecolor='#94A3B8',
                       tickfont=dict(size=12, color=PALETTE['navy_700'])),
            yaxis=dict(title=dict(text='Energy (kWh/yr)',
                                  font=dict(size=14, color=PALETTE['navy_900'])),
                       backgroundcolor='rgba(248,250,252,0.5)',
                       gridcolor='#E2E8F0', zerolinecolor='#94A3B8',
                       tickfont=dict(size=12, color=PALETTE['navy_700'])),
            zaxis=dict(title=dict(text='Social Equity (WE)',
                                  font=dict(size=14, color=PALETTE['navy_900'])),
                       backgroundcolor='rgba(248,250,252,0.5)',
                       gridcolor='#E2E8F0', zerolinecolor='#94A3B8',
                       tickfont=dict(size=12, color=PALETTE['navy_700'])),
            camera=dict(eye=dict(x=1.6, y=1.6, z=1.0)),
        ),
        height=620,
        margin=dict(l=0, r=0, b=0, t=60),
        title=dict(text='<b>3-D Pareto Frontier</b>  ·  drag to rotate, scroll to zoom',
                   font=dict(size=18, color=PALETTE['navy_900'])),
    )
    st.plotly_chart(fig3d, use_container_width=True)

    # ── 2-D projections ───────────────────────────────────────
    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
    section_head('◆ PAIRWISE VIEWS',
                 '2-D Projections',
                 'Slicing the trade-off cube into pairwise planes. The shaded '
                 'corner of each chart marks the <b>ideal zone</b> — where '
                 'both objectives perform best.')

    insight(
        'The connecting line traces the Pareto front in sorted order — a '
        '<strong>curved arc</strong> means objectives genuinely trade off, '
        'while a <strong>flat line</strong> means improving one barely '
        'costs the other.'
    )

    def pareto2d(x_col, y_col, xlabel, ylabel, title,
                 line_color, ideal_corner, ideal_label):
        """
        Pareto pairwise scatter with connecting line and quadrant shading.

        ideal_corner: one of 'NE', 'NW', 'SE', 'SW' indicating which
                      corner is "best". Drives quadrant shading + label.
        """
        df = df_pareto.sort_values(x_col).reset_index(drop=True)
        x = df[x_col]
        y = df[y_col]

        # Ranges with padding
        x_min, x_max = x.min(), x.max()
        y_min, y_max = y.min(), y.max()
        x_pad = (x_max - x_min) * 0.10 if x_max > x_min else x_max * 0.05
        y_pad = (y_max - y_min) * 0.15 if y_max > y_min else y_max * 0.05
        x_lo, x_hi = x_min - x_pad, x_max + x_pad
        y_lo, y_hi = y_min - y_pad, y_max + y_pad

        # Quadrant shading rectangle (covers the ideal corner half)
        if ideal_corner == 'NW':
            q_x0, q_x1 = x_lo, (x_lo + x_hi) / 2
            q_y0, q_y1 = (y_lo + y_hi) / 2, y_hi
            badge_x, badge_y = 0.04, 0.95
            badge_anchor_x, badge_anchor_y = 'left', 'top'
        elif ideal_corner == 'NE':
            q_x0, q_x1 = (x_lo + x_hi) / 2, x_hi
            q_y0, q_y1 = (y_lo + y_hi) / 2, y_hi
            badge_x, badge_y = 0.96, 0.95
            badge_anchor_x, badge_anchor_y = 'right', 'top'
        elif ideal_corner == 'SE':
            q_x0, q_x1 = (x_lo + x_hi) / 2, x_hi
            q_y0, q_y1 = y_lo, (y_lo + y_hi) / 2
            badge_x, badge_y = 0.96, 0.05
            badge_anchor_x, badge_anchor_y = 'right', 'bottom'
        else:  # 'SW'
            q_x0, q_x1 = x_lo, (x_lo + x_hi) / 2
            q_y0, q_y1 = y_lo, (y_lo + y_hi) / 2
            badge_x, badge_y = 0.04, 0.05
            badge_anchor_x, badge_anchor_y = 'left', 'bottom'

        fig = go.Figure()

        # Pareto curve (connecting line — drawn first, sits behind markers)
        fig.add_trace(go.Scatter(
            x=x, y=y,
            mode='lines',
            line=dict(color=line_color, width=2.5,
                      shape='spline', smoothing=0.6),
            opacity=0.45,
            hoverinfo='skip',
            showlegend=False,
        ))

        # Markers + point labels
        fig.add_trace(go.Scatter(
            x=df[x_col], y=df[y_col],
            mode='markers+text',
            text=df['Point'].astype(str),
            textposition='top center',
            textfont=dict(size=12, color=PALETTE['navy_900'],
                          family='"Space Grotesk", sans-serif',
                          weight=700),
            marker=dict(
                size=18,
                color=line_color,
                line=dict(color='white', width=2.5),
                opacity=0.95,
            ),
            customdata=df[['Point', x_col, y_col]],
            hovertemplate=(
                f'<b>Solution %{{customdata[0]}}</b><br>'
                f'{xlabel}: %{{customdata[1]:,.2f}}<br>'
                f'{ylabel}: %{{customdata[2]:,.4f}}<extra></extra>'
            ),
            showlegend=False,
        ))

        fig.update_layout(
            title=dict(text=f'<b>{title}</b>',
                       font=dict(size=17, color=PALETTE['navy_900']),
                       x=0.0, xanchor='left', y=0.97, yanchor='top'),
            height=420,
            margin=dict(l=70, r=30, t=70, b=70),
            xaxis=dict(
                title=dict(text=xlabel,
                           font=dict(size=13, color=PALETTE['navy_900'])),
                range=[x_lo, x_hi],
                tickfont=dict(size=12, color=PALETTE['navy_700']),
                gridcolor='#E2E8F0',
                zeroline=False,
            ),
            yaxis=dict(
                title=dict(text=ylabel,
                           font=dict(size=13, color=PALETTE['navy_900'])),
                range=[y_lo, y_hi],
                tickfont=dict(size=12, color=PALETTE['navy_700']),
                gridcolor='#E2E8F0',
                zeroline=False,
            ),
            shapes=[
                # Ideal-zone shading
                dict(
                    type='rect',
                    x0=q_x0, x1=q_x1, y0=q_y0, y1=q_y1,
                    fillcolor=line_color,
                    opacity=0.07,
                    line=dict(width=0),
                    layer='below',
                ),
            ],
            annotations=[
                # Ideal-corner callout badge
                dict(
                    x=badge_x, y=badge_y, xref='paper', yref='paper',
                    xanchor=badge_anchor_x, yanchor=badge_anchor_y,
                    text=f'<b>✓ {ideal_label}</b>',
                    showarrow=False,
                    font=dict(size=11, color=line_color,
                              family='"IBM Plex Sans", sans-serif'),
                    bgcolor='rgba(255,255,255,0.92)',
                    bordercolor=line_color,
                    borderwidth=1.5,
                    borderpad=6,
                ),
            ],
        )
        return fig

    c1, c2, c3 = st.columns(3, gap='medium')

    with c1:
        st.plotly_chart(
            pareto2d(
                'OF1_Cost', 'OF2b_Energy',
                'Cost (USD/yr)', 'Energy (kWh/yr)',
                'Cost × Energy',
                PALETTE['amber_500'],
                ideal_corner='SW',
                ideal_label='Ideal: low cost · low energy',
            ),
            use_container_width=True,
        )
        st.caption(
            'The Pareto curve here shows whether cutting cost forces '
            'higher energy — a steep slope means yes.'
        )
    with c2:
        st.plotly_chart(
            pareto2d(
                'OF1_Cost', 'OF3_Social',
                'Cost (USD/yr)', 'Social Equity (WE)',
                'Cost × Social Equity',
                PALETTE['cyan_500'],
                ideal_corner='NW',
                ideal_label='Ideal: low cost · high equity',
            ),
            use_container_width=True,
        )
        st.caption(
            'The most desirable corner: cheap and equitable. Solutions '
            'closest to the upper-left are the strongest all-rounders.'
        )
    with c3:
        st.plotly_chart(
            pareto2d(
                'OF2b_Energy', 'OF3_Social',
                'Energy (kWh/yr)', 'Social Equity (WE)',
                'Energy × Social Equity',
                PALETTE['emerald_500'],
                ideal_corner='NW',
                ideal_label='Ideal: low energy · high equity',
            ),
            use_container_width=True,
        )
        st.caption(
            'A flat curve here means equity and energy are largely '
            'independent — you can have both.'
        )

    # Raw table — collapsed
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    with st.expander('📋  Raw Pareto front data', expanded=False):
        styled = heat_style(
            df_pareto,
            columns=['OF3_Social'],
            palette='green',
        )
        # Layer a second heatmap on cost/energy with inverted scale (low=dark)

        def _orange_invert(s):
            vmin, vmax = s.min(), s.max()
            rng = vmax - vmin if vmax > vmin else 1.0
            out = []
            for v in s:
                t = 1 - (v - vmin) / rng  # invert: low values become dark
                r = int(255 + (245 - 255) * t)
                g = int(247 + (158 - 247) * t)
                b = int(237 + (11 - 237) * t)
                text = '#0A1628' if t < 0.55 else '#FFFFFF'
                out.append(
                    f'background-color: rgb({r},{g},{b}); color: {text};')
            return out

        styled = styled.apply(
            _orange_invert, subset=['OF1_Cost', 'OF2b_Energy'], axis=0
        ).format({
            'OF1_Cost':    '{:,.0f}',
            'OF2b_Energy': '{:,.0f}',
            'OF3_Social':  '{:.4f}',
            'LI':   '{:.6f}', 'WGC':  '{:.6f}',
            'WSRV': '{:.6f}', 'WC':   '{:.6f}', 'WSGR': '{:.6f}',
        })
        st.dataframe(styled, use_container_width=True, height=400)


# ═══════════════════════════════════════════════════════════
# TAB 2 — MCDM / TOPSIS
# ═══════════════════════════════════════════════════════════
with tab_topsis:
    section_head(
        '◆ MULTI-CRITERIA DECISION ANALYSIS',
        'TOPSIS · Pick your priorities.',
        'TOPSIS ranks each Pareto solution by its closeness to the hypothetical '
        'ideal point (best value on every objective). Adjust the weights below to '
        'match your decision context — the rankings update in real time.'
    )

    # ── Weight sliders ────────────────────────────────────────
    for key, val in [('w1_raw', 33), ('w2_raw', 33), ('w3_raw', 34)]:
        if key not in st.session_state:
            st.session_state[key] = val

    def rebalance(changed: str):
        keys = ['w1_raw', 'w2_raw', 'w3_raw']
        fixed_val = st.session_state[changed]
        others = [k for k in keys if k != changed]
        remaining = 100 - fixed_val
        if remaining < 0:
            remaining = 0
            st.session_state[changed] = 100
        other_sum = st.session_state[others[0]] + st.session_state[others[1]]
        if other_sum == 0:
            st.session_state[others[0]] = remaining // 2
            st.session_state[others[1]] = remaining - remaining // 2
        else:
            st.session_state[others[0]] = round(
                remaining * st.session_state[others[0]] / other_sum)
            st.session_state[others[1]] = 100 - \
                fixed_val - st.session_state[others[0]]

    def _w1_changed():
        rebalance('w1_raw')
        st.session_state['active_tab'] = 1

    def _w2_changed():
        rebalance('w2_raw')
        st.session_state['active_tab'] = 1

    def _w3_changed():
        rebalance('w3_raw')
        st.session_state['active_tab'] = 1

    st.markdown(f"""
    <div style="background: white; border: 1px solid {PALETTE['slate_200']};
                border-radius: 12px; padding: 24px;
                box-shadow: 0 1px 3px rgba(10,22,40,0.04);
                margin-bottom: 1.5rem;">
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.72rem;
                    color:{PALETTE['cyan_500']}; letter-spacing:0.15em;
                    margin-bottom:12px;">
            ◆ PREFERENCE WEIGHTS
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_w1, col_w2, col_w3 = st.columns(3, gap='medium')
    with col_w1:
        st.slider('💰  w₁ — Economic (OF1)', 0, 100,
                  key='w1_raw', on_change=_w1_changed,
                  help='Weight for OF1 (cost). Higher = prioritise cost reduction.')
    with col_w2:
        st.slider('🌿  w₂ — Environmental (OF2)', 0, 100,
                  key='w2_raw', on_change=_w2_changed,
                  help='Weight for OF2 (env). Higher = prioritise environmental performance.')
    with col_w3:
        st.slider('⚖️  w₃ — Social Equity (OF3)', 0, 100,
                  key='w3_raw', on_change=_w3_changed,
                  help='Weight for OF3 (social). Higher = prioritise equity.')

    w1_raw = st.session_state['w1_raw']
    w2_raw = st.session_state['w2_raw']
    w3_raw = st.session_state['w3_raw']

    total_w = w1_raw + w2_raw + w3_raw
    if total_w == 0:
        st.error('All weights are zero. Set at least one weight > 0.')
        st.stop()

    w1 = w1_raw / total_w
    w2 = w2_raw / total_w
    w3 = w3_raw / total_w

    # Visual weight bar
    st.markdown(f"""
    <div style="display:flex; height: 40px; border-radius: 10px; overflow:hidden;
                margin: 6px 0 24px 0; border: 1px solid {PALETTE['slate_200']};
                box-shadow: inset 0 1px 2px rgba(10,22,40,0.06);">
        <div style="width:{w1*100}%; background:linear-gradient(135deg,#F59E0B,#D97706);
                    display:flex; align-items:center; justify-content:center;
                    color:white; font-family:'Space Grotesk',sans-serif;
                    font-weight:600; font-size:0.85rem; padding: 0 8px;
                    text-shadow: 0 1px 2px rgba(0,0,0,0.15);
                    transition: width 0.3s ease;">
            {w1:.0%} Cost
        </div>
        <div style="width:{w2*100}%; background:linear-gradient(135deg,#10B981,#059669);
                    display:flex; align-items:center; justify-content:center;
                    color:white; font-family:'Space Grotesk',sans-serif;
                    font-weight:600; font-size:0.85rem; padding: 0 8px;
                    text-shadow: 0 1px 2px rgba(0,0,0,0.15);
                    transition: width 0.3s ease;">
            {w2:.0%} Env
        </div>
        <div style="width:{w3*100}%; background:linear-gradient(135deg,#06B6D4,#0891B2);
                    display:flex; align-items:center; justify-content:center;
                    color:white; font-family:'Space Grotesk',sans-serif;
                    font-weight:600; font-size:0.85rem; padding: 0 8px;
                    text-shadow: 0 1px 2px rgba(0,0,0,0.15);
                    transition: width 0.3s ease;">
            {w3:.0%} Equity
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Run TOPSIS ─────────────────────────────────────────────
    criteria_df = df_pareto[['OF1_Cost', 'OF2b_Energy', 'OF3_Social']].copy()
    weights = [w1, w2, w3]
    benefit_flag = [False, False, True]
    scores, ranks = topsis(criteria_df, weights, benefit_flag)

    df_topsis = df_pareto.copy()
    df_topsis['TOPSIS_Score'] = scores
    df_topsis['Rank'] = ranks
    df_topsis = df_topsis.sort_values('Rank')

    # ── Best solution highlight (premium card) ─────────────────
    best = df_topsis.iloc[0]
    runner_up = df_topsis.iloc[1] if len(df_topsis) > 1 else None
    third = df_topsis.iloc[2] if len(df_topsis) > 2 else None

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {PALETTE['navy_900']} 0%,
                {PALETTE['navy_700']} 100%);
                border-radius: 16px; padding: 28px 32px;
                color: white;
                box-shadow: 0 12px 32px rgba(10,22,40,0.18);
                margin-bottom: 1.5rem;
                position: relative; overflow: hidden;">
        <div style="position:absolute; top:-40px; right:-40px;
                    width:200px; height:200px; border-radius:50%;
                    background:radial-gradient(circle, rgba(34,211,238,0.15), transparent 70%);"></div>
        <div style="position:relative; z-index:1;
                    display:flex; align-items:center; justify-content:space-between;
                    flex-wrap:wrap; gap:24px;">
            <div>
                <div style="font-family:'IBM Plex Mono',monospace; font-size:0.72rem;
                            color:{PALETTE['cyan_300']}; letter-spacing:0.15em;
                            margin-bottom:6px;">
                    🏆  TOP-RANKED SOLUTION
                </div>
                <div style="font-family:'Space Grotesk',sans-serif;
                            font-size:2.4rem; font-weight:700;
                            line-height:1.1; letter-spacing:-0.02em;">
                    Solution #{int(best["Point"])}
                </div>
                <div style="font-size:0.92rem; color:#CBD5E1; margin-top:8px;">
                    Closeness score: <strong style="color:{PALETTE['cyan_300']};">
                    {best["TOPSIS_Score"]:.4f}</strong> — best fit for your weights
                </div>
            </div>
            <div style="display:flex; gap:32px; flex-wrap:wrap;">
                <div>
                    <div style="font-size:0.72rem; color:#94A3B8;
                                text-transform:uppercase; letter-spacing:0.08em;">Cost</div>
                    <div style="font-family:'Space Grotesk',sans-serif; font-size:1.4rem;
                                font-weight:700; margin-top:2px;">
                        ${best["OF1_Cost"]/1e6:,.1f}M<span style="font-size:0.85rem; opacity:0.6;">/yr</span>
                    </div>
                </div>
                <div>
                    <div style="font-size:0.72rem; color:#94A3B8;
                                text-transform:uppercase; letter-spacing:0.08em;">Energy</div>
                    <div style="font-family:'Space Grotesk',sans-serif; font-size:1.4rem;
                                font-weight:700; margin-top:2px;">
                        {best["OF2b_Energy"]/1e9:.2f}<span style="font-size:0.85rem; opacity:0.6;"> GWh</span>
                    </div>
                </div>
                <div>
                    <div style="font-size:0.72rem; color:#94A3B8;
                                text-transform:uppercase; letter-spacing:0.08em;">Equity</div>
                    <div style="font-family:'Space Grotesk',sans-serif; font-size:1.4rem;
                                font-weight:700; margin-top:2px;
                                color:{PALETTE['cyan_300']};">
                        {best["OF3_Social"]:.4f}
                    </div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Closeness score chart
    section_head('◆ CLOSENESS SCORES',
                 'How every solution ranks',
                 '0 = matches the worst case, 1 = matches the ideal. '
                 'Bars are sorted by rank.')

    fig_bar = go.Figure(go.Bar(
        x=df_topsis['Point'].astype(str),
        y=df_topsis['TOPSIS_Score'],
        marker=dict(
            color=df_topsis['TOPSIS_Score'],
            colorscale=PERF_SCALE,
            showscale=False,
            line=dict(color='white', width=1),
        ),
        text=[f'{s:.3f}' for s in df_topsis['TOPSIS_Score']],
        textposition='outside',
        textfont=dict(size=13, color=PALETTE['navy_900'],
                      family='"IBM Plex Sans", sans-serif'),
        hovertemplate=(
            '<b>Solution %{x}</b><br>'
            'Closeness: %{y:.4f}<extra></extra>'
        ),
    ))
    fig_bar.update_layout(
        title=dict(
            text=f'<b>Closeness Coefficient by Solution</b>  ·  '
            f'w₁={w1:.2f} · w₂={w2:.2f} · w₃={w3:.2f}',
            font=dict(size=17, color=PALETTE['navy_900']),
        ),
        height=400,
        showlegend=False,
        yaxis=dict(range=[0, 1.12], title='Closeness (0–1)'),
        xaxis=dict(title='Pareto Solution', type='category'),
        bargap=0.35,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # Radar + table side-by-side
    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    radar_col, info_col = st.columns([1.4, 1], gap='large')

    with radar_col:
        section_head('◆ TOP 3 COMPARISON',
                     'Multi-criteria radar',
                     'Outer edge = best on each dimension. Look for shape — '
                     'spiky polygons excel on specific axes, balanced '
                     'polygons perform consistently.')

        top3 = df_topsis.head(3)
        cats = ['OF1 Cost', 'OF2b Energy', 'OF3 Social',
                'LI', 'WGC (inv)', 'WSRV (inv)', 'WC (inv)', 'WSGR']

        def radar_norm(col, minimize=True):
            mn, mx = df_pareto[col].min(), df_pareto[col].max()
            rng = mx - mn
            if abs(rng) < 1e-12:
                return [0.5] * len(df_pareto)
            if minimize:
                return ((mx - df_pareto[col]) / rng).values
            return ((df_pareto[col] - mn) / rng).values

        norm_data = {
            'OF1 Cost':    radar_norm('OF1_Cost', minimize=True),
            'OF2b Energy': radar_norm('OF2b_Energy', minimize=True),
            'OF3 Social':  radar_norm('OF3_Social', minimize=False),
            'LI':          radar_norm('LI', minimize=False),
            'WGC (inv)':   radar_norm('WGC', minimize=True),
            'WSRV (inv)':  radar_norm('WSRV', minimize=True),
            'WC (inv)':    radar_norm('WC', minimize=True),
            'WSGR':        radar_norm('WSGR', minimize=False),
        }

        fig_radar = go.Figure()
        radar_colors = [PALETTE['cyan_500'],
                        PALETTE['amber_500'], PALETTE['teal_500']]

        for idx_row, (_, row) in enumerate(top3.iterrows()):
            pt_idx = int(row['Point']) - 1
            vals = [norm_data[c][pt_idx] for c in cats]
            vals += [vals[0]]
            fig_radar.add_trace(go.Scatterpolar(
                r=vals,
                theta=cats + [cats[0]],
                fill='toself',
                name=f'#{int(row["Point"])}  ·  rank {int(row["Rank"])}',
                line=dict(color=radar_colors[idx_row], width=2.5),
                fillcolor=radar_colors[idx_row],
                opacity=0.35,
                hovertemplate=(
                    f'<b>Solution {int(row["Point"])}</b><br>'
                    '%{theta}: %{r:.3f}<extra></extra>'
                ),
            ))
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True, range=[0, 1],
                    tickvals=[0, 0.25, 0.5, 0.75, 1.0],
                    ticktext=['worst', '', '', '', 'best'],
                    tickfont=dict(size=11, color=PALETTE['slate_600'],
                                  family='"IBM Plex Sans", sans-serif'),
                    gridcolor='#E2E8F0',
                ),
                angularaxis=dict(
                    tickfont=dict(size=13, color=PALETTE['navy_900'],
                                  family='"IBM Plex Sans", sans-serif'),
                    gridcolor='#CBD5E1',
                ),
                bgcolor='rgba(248,250,252,0.5)',
            ),
            height=500,
            legend=dict(orientation='h', yanchor='bottom', y=-0.15,
                        xanchor='center', x=0.5,
                        font=dict(size=13, color=PALETTE['navy_900'])),
            margin=dict(t=40, b=80, l=60, r=60),
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with info_col:
        section_head('◆ TOP 3 BREAKDOWN',
                     'The contenders', '')

        for idx_row, (_, row) in enumerate(top3.iterrows()):
            color = radar_colors[idx_row]
            rank_emoji = ['🥇', '🥈', '🥉'][idx_row]
            st.markdown(f"""
            <div style="background:white; border:1px solid {PALETTE['slate_200']};
                        border-left: 4px solid {color};
                        border-radius:10px; padding:14px 16px; margin-bottom:10px;
                        box-shadow:0 1px 3px rgba(10,22,40,0.04);">
                <div style="display:flex; justify-content:space-between;
                            align-items:flex-start;">
                    <div>
                        <div style="font-family:'IBM Plex Mono',monospace;
                                    font-size:0.7rem; color:{color};
                                    letter-spacing:0.1em; font-weight:600;">
                            {rank_emoji}  RANK {int(row['Rank'])}
                        </div>
                        <div style="font-family:'Space Grotesk',sans-serif;
                                    font-size:1.15rem; font-weight:700;
                                    color:{PALETTE['navy_900']}; margin-top:2px;">
                            Solution #{int(row['Point'])}
                        </div>
                    </div>
                    <div style="font-family:'Space Grotesk',sans-serif;
                                font-size:1.1rem; font-weight:700;
                                color:{color};">
                        {row['TOPSIS_Score']:.3f}
                    </div>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr 1fr;
                            gap:8px; margin-top:10px; font-size:0.8rem;">
                    <div>
                        <div style="color:{PALETTE['slate_400']};
                                    text-transform:uppercase; letter-spacing:0.06em;
                                    font-size:0.66rem;">Cost</div>
                        <div style="color:{PALETTE['navy_900']}; font-weight:600;">
                            ${row['OF1_Cost']/1e6:.1f}M
                        </div>
                    </div>
                    <div>
                        <div style="color:{PALETTE['slate_400']};
                                    text-transform:uppercase; letter-spacing:0.06em;
                                    font-size:0.66rem;">Energy</div>
                        <div style="color:{PALETTE['navy_900']}; font-weight:600;">
                            {row['OF2b_Energy']/1e9:.2f} GWh
                        </div>
                    </div>
                    <div>
                        <div style="color:{PALETTE['slate_400']};
                                    text-transform:uppercase; letter-spacing:0.06em;
                                    font-size:0.66rem;">Equity</div>
                        <div style="color:{PALETTE['navy_900']}; font-weight:600;">
                            {row['OF3_Social']:.4f}
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Full ranked table
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    with st.expander('📋  Full ranked table (all solutions)', expanded=False):
        st.dataframe(
            df_topsis[['Rank', 'Point', 'OF1_Cost', 'OF2b_Energy', 'OF3_Social',
                       'LI', 'WGC', 'WSRV', 'WC', 'WSGR', 'TOPSIS_Score']]
            .style
            .format({
                'OF1_Cost':     '{:,.0f}',
                'OF2b_Energy':  '{:,.0f}',
                'OF3_Social':   '{:.4f}',
                'LI':   '{:.5f}', 'WGC':  '{:.5f}',
                'WSRV': '{:.5f}', 'WC':   '{:.5f}', 'WSGR': '{:.5f}',
                'TOPSIS_Score': '{:.4f}',
            })
            .apply(
                lambda row: ['background-color: #ECFDF5' if row['Rank'] == 1 else ''
                             for _ in row],
                axis=1,
            ),
            use_container_width=True,
            height=400,
        )


# ═══════════════════════════════════════════════════════════
# TAB 3 — SOLUTION DETAIL
# ═══════════════════════════════════════════════════════════
with tab_detail:
    section_head(
        '◆ ALLOCATION INSPECTOR',
        'Drill into any solution',
        'Examine the full water allocation across every source-technology-end-use '
        'pathway, with cost, energy, and CO₂ breakdowns.'
    )

    if ws_df is None or pareto is None:
        st.info('Run the model first.')
        st.stop()

    # ── Point selector ─────────────────────────────────────────
    point_labels = [
        f'Solution {k+1}  ·  ${s["OF1"]/1e6:,.1f}M  ·  '
        f'{s["OF2b"]/1e9:.2f} GWh  ·  Equity {s["OF3"]:.4f}'
        for k, s in enumerate(pareto)
    ]
    sel = st.selectbox(
        '🔍  Select a solution to inspect:',
        options=range(len(pareto)),
        format_func=lambda i: point_labels[i])
    sol = pareto[sel]

    # KPI row — premium scorecard
    k1, k2, k3, k4 = st.columns(4)
    k1.metric('Annual Cost', f'${sol["OF1"]/1e6:,.1f}M',
              help=f'${sol["OF1"]:,.0f}/yr')
    k2.metric('Annual Energy', f'{sol["OF2b"]/1e9:,.2f} GWh',
              help=f'{sol["OF2b"]:,.0f} kWh/yr')
    k3.metric('Equity Score', f'{sol["OF3"]:.4f}')
    k4.metric('Guarantee Rate', f'{sol["WSGR"]:.4f}')

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

    # Social sub-indicators in styled card
    section_head('◆ EQUITY SUB-INDICATORS',
                 'The five components of OF3', '')

    si_cols = st.columns(5, gap='small')
    indicators = [
        ('LI', 'Labour Intensity', '👷', PALETTE['cyan_500']),
        ('WGC', 'Gini Coefficient', '📊', PALETTE['amber_500']),
        ('WSRV', 'Shortage Variance', '📉', PALETTE['rose_500']),
        ('WC', 'Williamson Coeff.', '📐', PALETTE['teal_500']),
        ('WSGR', 'Guarantee Rate', '✓', PALETTE['emerald_500']),
    ]
    for ci, (key, label, icon, color) in enumerate(indicators):
        with si_cols[ci]:
            st.markdown(f"""
            <div style="background:white; border:1px solid {PALETTE['slate_200']};
                        border-radius:10px; padding:14px 16px;
                        box-shadow:0 1px 3px rgba(10,22,40,0.04);">
                <div style="font-size:1.3rem;">{icon}</div>
                <div style="font-family:'IBM Plex Sans',sans-serif;
                            font-size:0.7rem; color:{PALETTE['slate_400']};
                            text-transform:uppercase; letter-spacing:0.08em;
                            margin-top:6px;">{label}</div>
                <div style="font-family:'Space Grotesk',sans-serif;
                            font-size:1.2rem; font-weight:700;
                            color:{color}; margin-top:4px;">
                    {sol[key]:.5f}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)

    # ── Allocation table ───────────────────────────────────────
    alloc = ws_df.copy()
    alloc['P_m3yr'] = sol['P']
    alloc['Cost_USD_yr'] = alloc['cost_uvw'] * alloc['P_m3yr']
    alloc['Energy_kWh_yr'] = alloc['energy_uvw'] * alloc['P_m3yr']
    alloc['CO2_ton_yr'] = alloc['co2_uvw'] * alloc['P_m3yr']
    alloc['Share_pct'] = 100.0 * alloc['P_m3yr'] / \
        max(alloc['P_m3yr'].sum(), 1e-12)

    active = alloc[alloc['P_m3yr'] > 1e4].sort_values(
        'P_m3yr', ascending=False)

    if not active.empty:
        # ── Allocation charts (side by side) ───────────────────
        section_head('◆ PATHWAY DECOMPOSITION',
                     'Where the water goes',
                     'Each pathway = a unique source → technology → end-use combination.')

        chart_col1, chart_col2 = st.columns([1, 1], gap='medium')

        with chart_col1:
            active_sorted = active.copy()
            active_sorted['Label'] = (
                active_sorted['source_name'] + ' → ' +
                active_sorted['technology'] + ' → ' +
                active_sorted['end_use']
            )
            fig_bar_alloc = px.bar(
                active_sorted.sort_values('P_m3yr'),
                x='P_m3yr',
                y='Label',
                orientation='h',
                color='Cost_USD_yr',
                color_continuous_scale=WATER_SCALE,
                labels={
                    'P_m3yr': 'Allocation (m³/yr)',
                    'Label': '',
                    'Cost_USD_yr': 'Cost (USD/yr)',
                },
            )
            fig_bar_alloc.update_layout(
                title=dict(text='<b>Volume Allocated</b>  ·  by pathway',
                           font=dict(size=17, color=PALETTE['navy_900'])),
                height=max(420, len(active_sorted) * 40 + 120),
                margin=dict(l=10, r=20, t=60, b=50),
                yaxis=dict(
                    tickfont=dict(size=13, color=PALETTE['navy_900'],
                                  family='"IBM Plex Sans", sans-serif'),
                    automargin=True,
                ),
                xaxis=dict(
                    tickfont=dict(size=13, color=PALETTE['navy_700']),
                ),
                coloraxis_colorbar=dict(
                    title=dict(text='Cost (USD/yr)',
                               font=dict(size=13, color=PALETTE['navy_900'])),
                    thickness=14,
                    len=0.7,
                    tickfont=dict(size=12, color=PALETTE['navy_700']),
                    outlinewidth=0,
                ),
            )
            fig_bar_alloc.update_traces(
                hovertemplate='<b>%{y}</b><br>Allocation: %{x:,.0f} m³/yr<extra></extra>'
            )
            st.plotly_chart(fig_bar_alloc, use_container_width=True)

        with chart_col2:
            fig_tree = px.treemap(
                active,
                path=['source_name', 'technology', 'end_use'],
                values='P_m3yr',
                color='Cost_USD_yr',
                color_continuous_scale=WATER_SCALE,
                hover_data={'P_m3yr': ':,.0f', 'Cost_USD_yr': ':,.0f'},
            )
            fig_tree.update_traces(
                texttemplate='<b>%{label}</b><br>%{value:,.0f}',
                textfont=dict(family='"IBM Plex Sans", sans-serif',
                              size=13, color='white'),
                hovertemplate=(
                    '<b>%{label}</b><br>'
                    'Allocation: %{value:,.0f} m³/yr<br>'
                    'Cost: $%{color:,.0f}/yr<extra></extra>'
                ),
                marker=dict(line=dict(color='white', width=2)),
            )
            fig_tree.update_layout(
                title=dict(text='<b>Hierarchical Share</b>  ·  area = volume, color = cost',
                           font=dict(size=17, color=PALETTE['navy_900'])),
                height=max(420, len(active_sorted) * 40 + 120),
                margin=dict(l=10, r=10, t=60, b=10),
                coloraxis_colorbar=dict(
                    title=dict(text='Cost (USD/yr)',
                               font=dict(size=13, color=PALETTE['navy_900'])),
                    thickness=14, len=0.7,
                    tickfont=dict(size=12, color=PALETTE['navy_700']),
                    outlinewidth=0,
                ),
            )
            st.plotly_chart(fig_tree, use_container_width=True)

        # ── Cost efficiency chart ──────────────────────────────
        st.markdown('<div style="height:24px;"></div>',
                    unsafe_allow_html=True)
        section_head(
            '◆ UNIT ECONOMICS',
            'Cost vs. volume — find the costly small pathways',
            'Each bubble is a single pathway. <b>Bubble size</b> shows its '
            'total annual cost contribution. Pathways high on the chart '
            '(expensive per m³) but small in size are the prime targets '
            'for re-optimization — they drain the budget without moving '
            'much water.',
        )

        active_eff = active.copy()
        active_eff['CostPerM3'] = active_eff['Cost_USD_yr'] / \
            active_eff['P_m3yr'].replace(0, np.nan)
        active_eff['Label'] = (
            active_eff['source_name'] + ' → ' +
            active_eff['technology'] + ' → ' +
            active_eff['end_use']
        )

        # Categorical color by source — instantly recognizable
        source_colors = {
            'Surface Water':  PALETTE['cyan_500'],
            'Groundwater':    PALETTE['amber_500'],
            'Brackish Water': '#8B5CF6',
            'Seawater':       PALETTE['teal_500'],
            'Wastewater':     PALETTE['emerald_500'],
        }

        fig_eff = go.Figure()
        for src in active_eff['source_name'].unique():
            sub = active_eff[active_eff['source_name'] == src]
            # Bubble size: scale total cost into a sensible pixel range
            max_cost = active_eff['Cost_USD_yr'].max()
            sizes = (sub['Cost_USD_yr'] / max_cost) * 60 + 12
            fig_eff.add_trace(go.Scatter(
                x=sub['P_m3yr'],
                y=sub['CostPerM3'],
                mode='markers',  # NO text labels — hover handles detail
                marker=dict(
                    size=sizes,
                    color=source_colors.get(src, '#94A3B8'),
                    line=dict(color='white', width=2),
                    opacity=0.82,
                    sizemode='diameter',
                ),
                name=src,
                customdata=np.stack([
                    sub['source_name'], sub['technology'], sub['end_use'],
                    sub['Cost_USD_yr']
                ], axis=-1),
                hovertemplate=(
                    '<b>%{customdata[0]} → %{customdata[1]} → %{customdata[2]}</b><br>'
                    'Volume: %{x:,.0f} m³/yr<br>'
                    'Unit cost: $%{y:,.2f}/m³<br>'
                    'Annual cost: $%{customdata[3]:,.0f}<extra></extra>'
                ),
            ))

        # Median guide lines
        x_range_log = [
            np.log10(max(active_eff['P_m3yr'].min(), 1e3)),
            np.log10(active_eff['P_m3yr'].max() * 1.2),
        ]
        y_max = active_eff['CostPerM3'].max() * 1.15

        fig_eff.update_layout(
            title=dict(
                text='<b>Pathway Cost vs Volume</b>  ·  bubble size = total annual cost',
                font=dict(size=17, color=PALETTE['navy_900']),
                x=0.0, xanchor='left',
                y=0.97, yanchor='top',
            ),
            xaxis=dict(
                title='Volume Allocated (m³/yr)  ·  log scale',
                type='log',
                tickfont=dict(size=13, color=PALETTE['navy_700']),
            ),
            yaxis=dict(
                title='Unit Cost (USD per m³)',
                tickfont=dict(size=13, color=PALETTE['navy_700']),
                rangemode='tozero',
            ),
            height=560,
            # top margin holds title + legend
            margin=dict(l=85, r=40, t=130, b=70),
            legend=dict(
                title=dict(text='<b>Source</b>',
                           font=dict(size=13, color=PALETTE['navy_900'])),
                orientation='h',
                yanchor='top', y=1.10,
                xanchor='left', x=0.0,
                bgcolor='rgba(255,255,255,0.85)',
                bordercolor=PALETTE['slate_200'],
                borderwidth=1,
            ),
            shapes=[
                # Subtle vertical guide at median volume
                dict(
                    type='line',
                    x0=active_eff['P_m3yr'].median(),
                    x1=active_eff['P_m3yr'].median(),
                    y0=0, y1=y_max, yref='y',
                    line=dict(color='#CBD5E1', width=1, dash='dot'),
                ),
                # Subtle horizontal guide at median unit cost
                dict(
                    type='line',
                    x0=10**x_range_log[0], x1=10**x_range_log[1],
                    y0=active_eff['CostPerM3'].median(),
                    y1=active_eff['CostPerM3'].median(),
                    line=dict(color='#CBD5E1', width=1, dash='dot'),
                ),
            ],
            annotations=[
                # Upper-left "optimization targets" callout — pushed right
                # of y-axis labels and given a solid white backdrop so it
                # always sits cleanly on top of any data points underneath.
                dict(
                    x=0.06, y=0.93, xref='paper', yref='paper',
                    text=('<b style="color:#E11D48;">⚠ Low volume · High unit cost</b>'
                          '<br><span style="font-size:10px;color:#475569;">'
                          'optimization targets</span>'),
                    showarrow=False,
                    align='left', xanchor='left', yanchor='top',
                    font=dict(size=12, family='"IBM Plex Sans", sans-serif'),
                    bgcolor='rgba(255,255,255,0.96)',
                    bordercolor=PALETTE['rose_500'],
                    borderwidth=1.5,
                    borderpad=8,
                ),
                # Lower-right "workhorse" callout
                dict(
                    x=0.98, y=0.06, xref='paper', yref='paper',
                    text=('<b style="color:#10B981;">✓ High volume · Low unit cost</b>'
                          '<br><span style="font-size:10px;color:#475569;">'
                          'workhorse pathways</span>'),
                    showarrow=False,
                    align='right', xanchor='right', yanchor='bottom',
                    font=dict(size=12, family='"IBM Plex Sans", sans-serif'),
                    bgcolor='rgba(255,255,255,0.96)',
                    bordercolor=PALETTE['emerald_500'],
                    borderwidth=1.5,
                    borderpad=8,
                ),
            ],
        )
        st.plotly_chart(fig_eff, use_container_width=True)

    # Allocation table (collapsed)
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    with st.expander(f'📋  Full pathway table ({len(active)} active pathways)',
                     expanded=False):
        renamed = active[['source_name', 'technology', 'end_use',
                          'P_m3yr', 'Share_pct', 'Cost_USD_yr',
                          'Energy_kWh_yr', 'CO2_ton_yr']].rename(columns={
                              'source_name': 'Source', 'technology': 'Technology',
                              'end_use': 'End Use',
                              'P_m3yr': 'Allocation (m³/yr)', 'Share_pct': 'Share (%)',
                              'Cost_USD_yr': 'Cost (USD/yr)',
                              'Energy_kWh_yr': 'Energy (kWh/yr)',
                              'CO2_ton_yr': 'CO₂ (t/yr)',
                          })

        styled = heat_style(
            renamed,
            columns=['Allocation (m³/yr)'],
            palette='cyan',
        ).format({
            'Allocation (m³/yr)': '{:,.0f}',
            'Share (%)':          '{:.1f}',
            'Cost (USD/yr)':      '{:,.0f}',
            'Energy (kWh/yr)':    '{:,.0f}',
            'CO₂ (t/yr)':         '{:,.2f}',
        })
        st.dataframe(styled, use_container_width=True, height=400)


# ═══════════════════════════════════════════════════════════
# TAB 4 — REGIONAL ANALYSIS
# ═══════════════════════════════════════════════════════════
with tab_regional:
    section_head(
        '◆ GEOGRAPHIC EQUITY',
        'Regional water distribution',
        'How the allocated supply gets distributed across regions in each '
        'Pareto solution. The "Shortage Variance" shown here is one of the '
        'five sub-indicators that feed into the social equity score (OF3): '
        'it captures how evenly — or unevenly — water shortages are spread '
        'across regions.'
    )

    if not regional_mode:
        st.info(
            '🗺️  Regional analysis requires data with regional supply caps '
            '(`region_id` column in WaterSources). Upload a regional Excel '
            'file (e.g. `WaterAllocationData_Synthetic.xlsx`), then click '
            '**▶ RUN OPTIMIZATION**.'
        )
    elif pareto is None or social_params is None:
        st.info('Run the model first.')
    else:
        # ── Solution selector ──────────────────────────────────
        point_labels_r = [
            f'Solution {k+1}  ·  ${s["OF1"]/1e6:,.1f}M  ·  '
            f'Equity {s["OF3"]:.4f}  ·  WSRV {s["WSRV"]:.4f}'
            for k, s in enumerate(pareto)
        ]
        sel_r = st.selectbox(
            '🗺️  Select a solution to inspect:',
            options=range(len(pareto)),
            format_func=lambda i: point_labels_r[i],
            key='regional_point_sel',
        )
        sol_r = pareto[sel_r]

        # Build per-region table
        reg_alloc = sol_r.get('regional_allocations', {})
        sp = social_params.copy()
        sp['supply_m3yr'] = sp['region_name'].map(reg_alloc).fillna(0.0)
        sp['demand_m3yr'] = (
            sp['demand_municipal'] + sp['demand_agricultural'] +
            sp['demand_industrial']
        )
        sp['shortage_m3yr'] = (sp['demand_m3yr'] -
                               sp['supply_m3yr']).clip(lower=0)
        sp['surplus_m3yr'] = (sp['supply_m3yr'] -
                              sp['demand_m3yr']).clip(lower=0)
        sp['shortage_rate'] = sp['shortage_m3yr'] / \
            sp['demand_m3yr'].replace(0, np.nan)
        sp['coverage_pct'] = (
            sp['supply_m3yr'] / sp['demand_m3yr'].replace(0, np.nan) * 100
        ).clip(upper=200)

        # ── KPI row ────────────────────────────────────────────
        k1, k2, k3, k4 = st.columns(4)
        k1.metric('Equity Score (OF3)', f'{sol_r["OF3"]:.4f}')
        k2.metric('Shortage Variance', f'{sol_r["WSRV"]:.6f}')
        k3.metric('Regions in Shortage',
                  f'{int((sp["shortage_m3yr"] > 1e6).sum())}')
        k4.metric('Total Shortage',
                  f'{sp["shortage_m3yr"].sum() / 1e6:,.1f} Mm³')

        st.markdown('<div style="height:24px;"></div>',
                    unsafe_allow_html=True)

        # ── Regional Schematic (bubble illustration) ──────────
        section_head(
            '◆ COVERAGE OVERVIEW',
            'Coverage by region',
            'Each region is shown as a bubble — size scales with '
            'population, color shows the share of local demand met by '
            'the allocated supply (red = severe shortage, green = fully '
            'covered). The number inside each bubble is the coverage '
            'percentage.',
        )

        # Schematic bubble layout — region-agnostic. Each region is
        # rendered as a sized circle (radius scales with population),
        # filled with its coverage color, with a coverage % pill overlaid.
        # No geographic pretense — purely a coverage schematic.

        # Build per-region data from the optimization results
        positioned = []
        for _, row in sp.iterrows():
            cov_raw = row['coverage_pct'] if pd.notna(
                row['coverage_pct']) else 0.0
            # Color is driven by clipped coverage (red→green at 100%);
            # the displayed % shows the actual uncapped value, so a
            # heavily over-supplied region reads as 200% (not flat 100%).
            cov_clip = max(0.0, min(100.0, cov_raw))
            positioned.append({
                'name':         row['region_name'],
                'population':   float(row['population']),
                'cov_pct':      int(round(cov_raw)),
                'cov_full':     cov_raw,
                'cov_color':    _color_from_scale(cov_clip / 100.0),
                'supply_b':     row['supply_m3yr'] / 1e9,
                'demand_b':     row['demand_m3yr'] / 1e9,
                'short_b':      row['shortage_m3yr'] / 1e9,
            })

        # Layout: distribute circles horizontally, evenly spaced, with
        # radius scaled by sqrt(population) so visual area ∝ population.
        VBW, VBH = 700, 540              # SVG viewBox
        n = len(positioned)
        if n == 0:
            st.info('No regional data available to display.')
            st.stop()

        # Radius scaling — clamp so smallest is still readable, largest
        # doesn't overlap its neighbor.
        pops = np.array([p['population'] for p in positioned])
        max_r = min(85, (VBW - 80) / max(n, 1) / 2.4)
        min_r = max(45, max_r * 0.55)
        r_scale = np.sqrt(pops / pops.max())
        radii = min_r + (max_r - min_r) * r_scale

        # X positions: evenly distributed across the viewBox
        x_positions = np.linspace(VBW / (n + 1), VBW * n / (n + 1), n)
        cy = 260  # vertical center of the bubble row

        # Pre-compute pixel positions for each region
        for i, p in enumerate(positioned):
            p['cx'] = float(x_positions[i])
            p['cy'] = cy
            p['r']  = float(radii[i])

        # Build SVG fragments
        bubbles_svg = ''
        for p in positioned:
            cx, cy, r = p['cx'], p['cy'], p['r']
            bubbles_svg += f'''
            <g>
                <!-- subtle outer ring -->
                <circle cx="{cx}" cy="{cy}" r="{r+8}"
                        fill="none"
                        stroke="rgba(255,255,255,0.08)" stroke-width="1"/>
                <!-- main bubble (coverage colored) -->
                <circle cx="{cx}" cy="{cy}" r="{r}"
                        fill="{p['cov_color']}" fill-opacity="0.85"
                        stroke="white" stroke-width="2.5">
                    <title>{p['name']}: {p['supply_b']:.2f} Bm³ supply, \
{p['demand_b']:.2f} Bm³ demand, {p['cov_full']:.1f}% coverage</title>
                </circle>
                <!-- coverage % at the center of the bubble -->
                <text x="{cx}" y="{cy+8}" text-anchor="middle"
                      font-family="Space Grotesk, sans-serif"
                      font-weight="700" font-size="26"
                      fill="white"
                      stroke="rgba(10,22,40,0.4)" stroke-width="3"
                      paint-order="stroke">
                    {p['cov_pct']}%
                </text>
            </g>'''

        # Region name labels above each bubble (with room for the
        # population badge that sits between name and bubble)
        labels_svg = ''
        for p in positioned:
            cx = p['cx']
            top_y = p['cy'] - p['r'] - 44
            labels_svg += f'''
            <text x="{cx}" y="{top_y}" text-anchor="middle"
                  font-family="Space Grotesk, sans-serif"
                  font-weight="700" font-size="16"
                  fill="white"
                  style="letter-spacing: 0.04em; text-transform: uppercase;">
                {p['name']}
            </text>'''

        # Stats panels below each bubble — supply / demand / shortage
        stats_svg = ''
        for p in positioned:
            cx = p['cx']
            base_y = p['cy'] + p['r'] + 32
            stats_svg += f'''
            <g font-family="IBM Plex Mono, monospace" font-size="11">
                <text x="{cx}" y="{base_y}" text-anchor="middle"
                      fill="rgba(255,255,255,0.55)"
                      letter-spacing="0.12em">SUPPLY</text>
                <text x="{cx}" y="{base_y+16}" text-anchor="middle"
                      font-family="Space Grotesk, sans-serif"
                      font-size="14" font-weight="600" fill="white">
                    {p['supply_b']:.2f} Bm³
                </text>
                <text x="{cx}" y="{base_y+38}" text-anchor="middle"
                      fill="rgba(255,255,255,0.55)"
                      letter-spacing="0.12em">DEMAND</text>
                <text x="{cx}" y="{base_y+54}" text-anchor="middle"
                      font-family="Space Grotesk, sans-serif"
                      font-size="14" font-weight="600" fill="white">
                    {p['demand_b']:.2f} Bm³
                </text>
                <text x="{cx}" y="{base_y+76}" text-anchor="middle"
                      fill="rgba(255,255,255,0.55)"
                      letter-spacing="0.12em">SHORTAGE</text>
                <text x="{cx}" y="{base_y+92}" text-anchor="middle"
                      font-family="Space Grotesk, sans-serif"
                      font-size="14" font-weight="600"
                      fill="{p['cov_color']}">
                    {p['short_b']:.2f} Bm³
                </text>
            </g>'''

        # Population badges — sit just below the region name label,
        # above the bubble. Cleaner than inside the bubble (avoids
        # overlap) and pairs naturally with the name.
        pop_svg = ''
        for p in positioned:
            cx = p['cx']
            badge_y = p['cy'] - p['r'] - 10
            pop_m = p['population'] / 1e6
            pop_str = (f'POP {pop_m:.1f}M' if pop_m >= 1
                       else f'POP {p["population"]/1e3:.0f}K')
            pop_svg += f'''
            <g transform="translate({cx}, {badge_y})">
                <rect x="-34" y="-9" width="68" height="18" rx="9"
                      fill="rgba(10,22,40,0.55)"
                      stroke="rgba(255,255,255,0.18)" stroke-width="0.5"/>
                <text x="0" y="4" text-anchor="middle"
                      font-family="IBM Plex Mono, monospace"
                      font-size="10" font-weight="600"
                      letter-spacing="0.05em"
                      fill="rgba(255,255,255,0.85)">
                    {pop_str}
                </text>
            </g>'''

        # No "unmapped regions" possible — every region is rendered
        unmapped_regions = []

        # Assemble the SVG
        svg_html = f'''
        <svg viewBox="0 0 {VBW} {VBH}"
             width="100%" height="100%"
             preserveAspectRatio="xMidYMid meet"
             style="max-width: {VBW}px; max-height: {VBH}px;
                    font-family: 'IBM Plex Sans', sans-serif;
                    display: block; margin: 0 auto;">
            <defs>
                <linearGradient id="bgGradient"
                                x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#0F2942"/>
                    <stop offset="100%" stop-color="#1E3A5F"/>
                </linearGradient>
                <pattern id="schemDots" x="0" y="0" width="6" height="6"
                         patternUnits="userSpaceOnUse">
                    <circle cx="3" cy="3" r="0.5"
                            fill="rgba(255,255,255,0.10)"/>
                </pattern>
                <linearGradient id="legendGrad" x1="0%" x2="100%">
                    <stop offset="0%"   stop-color="#E11D48"/>
                    <stop offset="25%"  stop-color="#F59E0B"/>
                    <stop offset="50%"  stop-color="#FCD34D"/>
                    <stop offset="75%"  stop-color="#84CC16"/>
                    <stop offset="100%" stop-color="#10B981"/>
                </linearGradient>
            </defs>

            <!-- Background -->
            <rect width="{VBW}" height="{VBH}" fill="url(#bgGradient)"/>
            <rect width="{VBW}" height="{VBH}" fill="url(#schemDots)"
                  opacity="0.7"/>

            <!-- Title -->
            <text x="30" y="42"
                  font-family="Space Grotesk, sans-serif"
                  font-size="20" font-weight="700"
                  fill="white">
                Regional Coverage · Schematic View
            </text>
            <text x="30" y="62"
                  font-family="IBM Plex Mono, monospace"
                  font-size="10" font-weight="500"
                  letter-spacing="0.18em"
                  fill="#67E8F9">
                BUBBLE SIZE = POPULATION · COLOR = COVERAGE
            </text>

            <!-- Region name labels (above bubbles) -->
            {labels_svg}

            <!-- Bubbles -->
            {bubbles_svg}

            <!-- Population badges -->
            {pop_svg}

            <!-- Stats panels (below bubbles) -->
            {stats_svg}

            <!-- Coverage legend at bottom -->
            <g transform="translate(30, {VBH-30})">
                <text x="0" y="0"
                      font-family="IBM Plex Sans, sans-serif"
                      font-size="11" font-weight="600" fill="white">
                    Coverage:
                </text>
                <rect x="80" y="-9" width="160" height="11" rx="5"
                      fill="url(#legendGrad)"
                      stroke="rgba(255,255,255,0.3)" stroke-width="1"/>
                <text x="80" y="14"
                      font-family="IBM Plex Sans, sans-serif"
                      font-size="10"
                      fill="rgba(255,255,255,0.7)">0%</text>
                <text x="240" y="14"
                      font-family="IBM Plex Sans, sans-serif"
                      font-size="10" text-anchor="end"
                      fill="rgba(255,255,255,0.7)">100%</text>
            </g>
        </svg>
        '''

        # Render via components.v1.html (st.markdown sanitizes SVG tags
        # like <defs>, <linearGradient>, breaking the SVG).
        full_html = f'''<!DOCTYPE html>
<html><head>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
<style>
  body {{ margin: 0; padding: 0; background: transparent;
         font-family: 'IBM Plex Sans', sans-serif; }}
</style>
</head>
<body>{svg_html}</body>
</html>'''

        st.components.v1.html(full_html, height=560, scrolling=False)

        if unmapped_regions:
            st.caption(
                f'ℹ️  {len(unmapped_regions)} region(s) — '
                f'{", ".join(unmapped_regions[:3])}'
                f'{"..." if len(unmapped_regions) > 3 else ""} '
                f'— not in canonical region list and were skipped on '
                f'the map.'
            )

        # ── Shortage rates + Source mix side by side ───────────
        st.markdown('<div style="height:16px;"></div>',
                    unsafe_allow_html=True)

        sr_col, smix_col = st.columns(2, gap='medium')

        with sr_col:
            section_head(
                '◆ SHORTAGE RATES',
                'How much demand each region had to go without',
                'For each region, this is the share of water demand that was '
                '<b>not</b> covered by the allocated supply (capped at 0% '
                'for surplus regions). WSRV measures how unevenly these '
                'shortages are spread across regions — a low WSRV means '
                'the burden is shared equitably, a high WSRV means a few '
                'regions are bearing most of the pain.'
            )

            colors_sr = [
                PALETTE['rose_500'] if r > 0.3
                else PALETTE['amber_500'] if r > 0.1
                else PALETTE['emerald_500']
                for r in sp['shortage_rate'].fillna(0)
            ]
            fig_sr = go.Figure(go.Bar(
                x=sp['region_name'],
                y=sp['shortage_rate'].fillna(0) * 100,
                marker=dict(color=colors_sr,
                            line=dict(color='white', width=1.5)),
                text=(sp['shortage_rate'].fillna(0) *
                      100).round(1).astype(str) + '%',
                textposition='outside',
                textfont=dict(size=13, color=PALETTE['navy_900'],
                              family='"IBM Plex Sans", sans-serif'),
            ))
            fig_sr.update_layout(
                title=dict(text='<b>Shortage Rate by Region</b>',
                           font=dict(size=16, color=PALETTE['navy_900'])),
                yaxis=dict(
                    title='Shortage Rate (%)',
                    range=[0, max(sp['shortage_rate'].fillna(0).max() *
                                  120, 10)]),
                xaxis=dict(title='', tickfont=dict(size=13,
                                                   color=PALETTE['navy_900'])),
                height=420,
                margin=dict(t=70, b=70),
                bargap=0.35,
            )
            st.plotly_chart(fig_sr, use_container_width=True)

        with smix_col:
            if ws_df is not None and 'region_id' in ws_df.columns:
                section_head('◆ SOURCE MIX',
                             'By region',
                             'Inland regions cannot use Seawater; '
                             'supply-constrained regions diversify.')

                alloc_detail = ws_df.copy()
                alloc_detail['P_m3yr'] = sol_r['P']
                alloc_detail = alloc_detail[alloc_detail['P_m3yr'] > 1e6]

                if not alloc_detail.empty:
                    src_region = (
                        alloc_detail.groupby(
                            ['region_id', 'source_name'])['P_m3yr']
                        .sum().reset_index()
                    )
                    rid_map = dict(zip(
                        social_params['region_id'],
                        social_params['region_name']
                    ))
                    src_region['region_name'] = src_region['region_id'].map(
                        rid_map)
                    src_region['P_Bm3yr'] = src_region['P_m3yr'] / 1e9

                    source_colors = {
                        'Surface Water':  PALETTE['cyan_500'],
                        'Groundwater':    PALETTE['amber_500'],
                        'Brackish Water': '#8B5CF6',
                        'Seawater':       PALETTE['teal_500'],
                        'Wastewater':     PALETTE['emerald_500'],
                    }
                    fig_mix = go.Figure()
                    for src in src_region['source_name'].unique():
                        sub = src_region[src_region['source_name'] == src]
                        fig_mix.add_trace(go.Bar(
                            name=src,
                            x=sub['region_name'],
                            y=sub['P_Bm3yr'],
                            marker=dict(
                                color=source_colors.get(src, '#94A3B8'),
                                line=dict(color='white', width=1)),
                        ))
                    fig_mix.update_layout(
                        barmode='stack',
                        title=dict(text='<b>Allocated Supply by Source</b>',
                                   font=dict(size=16, color=PALETTE['navy_900'])),
                        yaxis=dict(title='Volume (Bm³/yr)'),
                        xaxis=dict(title='',
                                   tickfont=dict(size=13,
                                                 color=PALETTE['navy_900'])),
                        height=420,
                        legend=dict(orientation='h', yanchor='bottom',
                                    y=1.02, x=0.5, xanchor='center'),
                        margin=dict(t=80, b=60),
                    )
                    st.plotly_chart(fig_mix, use_container_width=True)

        # ── Regional summary table ─────────────────────────────
        st.markdown('<div style="height:16px;"></div>',
                    unsafe_allow_html=True)

        with st.expander('📋  Regional summary table', expanded=True):
            disp_cols = {
                'region_name':   'Region',
                'population':    'Population',
                'demand_m3yr':   'Demand (m³/yr)',
                'supply_m3yr':   'Supply (m³/yr)',
                'shortage_m3yr': 'Shortage (m³/yr)',
                'shortage_rate': 'Shortage Rate',
                'coverage_pct':  'Coverage (%)',
            }
            st.dataframe(
                sp[list(disp_cols.keys())].rename(columns=disp_cols)
                .style.format({
                    'Population':       '{:,.0f}',
                    'Demand (m³/yr)':   '{:,.0f}',
                    'Supply (m³/yr)':   '{:,.0f}',
                    'Shortage (m³/yr)': '{:,.0f}',
                    'Shortage Rate':    '{:.3f}',
                    'Coverage (%)':     '{:.1f}',
                })
                .apply(
                    lambda row: [
                        'background-color: #FEE2E2'
                        if row['Shortage Rate'] > 0.1 else ''
                        for _ in row
                    ],
                    axis=1,
                ),
                use_container_width=True,
            )

        # ── WSRV across all Pareto solutions ──────────────────
        st.markdown('<div style="height:24px;"></div>',
                    unsafe_allow_html=True)
        section_head('◆ EQUITY ACROSS THE FRONTIER',
                     'WSRV vs Social Equity',
                     'Each bubble is a Pareto solution. Upper-left = most '
                     'equitable. Bubble size encodes annual cost. Selected '
                     'solution highlighted.')

        df_wsrv = pd.DataFrame([{
            'Point':      k + 1,
            'WSRV':       s['WSRV'],
            'OF3_Social': s['OF3'],
            'OF1_Cost':   s['OF1'],
            'Selected':   (k == sel_r),
        } for k, s in enumerate(pareto)])

        fig_wsrv = go.Figure()
        # Non-selected
        non_sel = df_wsrv[~df_wsrv['Selected']]
        fig_wsrv.add_trace(go.Scatter(
            x=non_sel['WSRV'], y=non_sel['OF3_Social'],
            mode='markers+text',
            text=non_sel['Point'].astype(str),
            textposition='top center',
            textfont=dict(size=12, color=PALETTE['navy_700'],
                          family='"IBM Plex Sans", sans-serif'),
            marker=dict(
                size=non_sel['OF1_Cost'] / df_wsrv['OF1_Cost'].max() * 30 + 10,
                color=PALETTE['cyan_500'],
                opacity=0.6,
                line=dict(color='white', width=1.5),
            ),
            name='Pareto solutions',
            hovertemplate=(
                '<b>Solution %{text}</b><br>'
                'WSRV: %{x:.4f}<br>'
                'Equity: %{y:.4f}<extra></extra>'
            ),
        ))
        # Selected
        sel_row = df_wsrv[df_wsrv['Selected']]
        fig_wsrv.add_trace(go.Scatter(
            x=sel_row['WSRV'], y=sel_row['OF3_Social'],
            mode='markers+text',
            text=sel_row['Point'].astype(str),
            textposition='top center',
            textfont=dict(size=14, color=PALETTE['rose_500'],
                          family='"Space Grotesk", sans-serif'),
            marker=dict(
                size=sel_row['OF1_Cost'] / df_wsrv['OF1_Cost'].max() * 30 + 14,
                color=PALETTE['rose_500'],
                line=dict(color='white', width=2.5),
            ),
            name='Selected',
            hovertemplate=(
                '<b>Solution %{text}</b> (selected)<br>'
                'WSRV: %{x:.4f}<br>'
                'Equity: %{y:.4f}<extra></extra>'
            ),
        ))
        fig_wsrv.update_layout(
            title=dict(text='<b>WSRV × Social Equity</b>  ·  bubble size = cost',
                       font=dict(size=17, color=PALETTE['navy_900'])),
            xaxis=dict(title='WSRV  (lower = more equitable →)'),
            yaxis=dict(title='OF3 Social Equity  (higher = better →)'),
            height=480,
            showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=1.02,
                        x=0.5, xanchor='center'),
            margin=dict(t=80, b=60),
        )
        st.plotly_chart(fig_wsrv, use_container_width=True)
