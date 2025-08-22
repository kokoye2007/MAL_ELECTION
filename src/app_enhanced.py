#!/usr/bin/env python3
"""
Myanmar Election Data Visualization - Enhanced Multi-Assembly App

A comprehensive web application for visualizing Myanmar's 2025 electoral constituencies
across all assemblies with interactive maps, statistical charts, and bilingual support.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
import json

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent))

from database import get_database
from boundary_renderer import BoundaryRenderer
from parties_page import create_parties_page
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster
import numpy as np

# Initialize session state variables early
if 'language' not in st.session_state:
    st.session_state.language = 'en'
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'
if 'current_date' not in st.session_state:
    from datetime import datetime
    st.session_state.current_date = datetime.now().strftime('%B %d, %Y')

# Import map optimizer with error handling
try:
    from map_optimizer import create_performance_optimized_map
except (ImportError, KeyError) as e:
    print(f"Warning: Could not import map_optimizer: {e}")
    # Fallback function
    def create_performance_optimized_map(data, assembly_types, zoom_level=6, performance_mode="balanced", 
                                       show_township_boundaries=False, show_state_boundaries=True, boundary_opacity=0.6):
        """Fallback map creation function."""
        return create_interactive_map(data, assembly_types, show_township_boundaries, show_state_boundaries, boundary_opacity)

# Load language data
def load_languages():
    """Load language translations from JSON file."""
    try:
        with open(Path(__file__).parent / 'languages.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback to English only
        return {"en": {"app_title": "Myanmar Election Data Visualization"}}

def get_text(key, **kwargs):
    """Get translated text for current language."""
    languages = load_languages()
    current_language = st.session_state.get('language', 'en')
    
    # Navigate through nested keys
    keys = key.split('.')
    text = languages.get(current_language, languages.get('en', {}))
    
    for k in keys:
        if isinstance(text, dict) and k in text:
            text = text[k]
        else:
            # Fallback to English if key not found
            text = languages.get('en', {})
            for k in keys:
                if isinstance(text, dict) and k in text:
                    text = text[k]
                else:
                    return f"Missing: {key}"
            break
    
    # Format text with kwargs if provided
    if isinstance(text, str) and kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    
    return text

def configure_page():
    """Configure Streamlit page settings with enhanced HTML header and favicon."""
    st.set_page_config(
        page_title="Myanmar Election 2025 - Interactive Constituency Visualization",
        page_icon="🗺️",  # Changed to map icon to represent geographic visualization
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'About': '''
            # Myanmar Election 2025 - Interactive Visualization Platform
            ### Version 2025.2.0 - MIMU Enhanced Multi-Layer Edition
            
            This application provides comprehensive visualization of Myanmar's 2025 electoral constituencies
            with MIMU (Myanmar Information Management Unit) integrated mapping system.
            
            **🏛️ Complete Assembly Coverage:**
            - **Pyithu Hluttaw (PTHT):** 330 constituencies
            - **Amyotha Hluttaw (AMTHT):** 85 + 27 PR constituencies  
            - **State/Regional Hluttaw (TPHT):** 323 + 43 PR constituencies
            - **Ethnic Affairs (TPTYT):** 30 constituencies
            - **Total: 838 constituencies with MIMU coordinate mapping**
            
            **🗺️ Advanced Features:**
            - Multi-layer interactive mapping with MIMU township boundaries
            - Pinpoint constituency markers with coordinate verification
            - Assembly-specific color coding and transparency
            - Multi-township constituency coordinate averaging
            - Real-time PostgreSQL database with comprehensive data
            - Bilingual support (Myanmar/English)
            - Performance-optimized rendering for all zoom levels
            
            **📊 Data Integration:**
            - **Geographic:** MIMU administrative boundaries and coordinates
            - **Electoral:** Myanmar Election Commission official data
            - **Technical:** PostGIS-enabled PostgreSQL with spatial indexing
            
            **🎯 Coordinate Mapping:**
            - 804/838 constituencies mapped (96% coverage)
            - Multi-township centroid averaging for complex constituencies
            - Township code mapping with + separator pattern
            - Coordinate source tracking and verification
            
            ---
            **Version:** 2025.2.0 MIMU Enhanced  
            **Build:** Heroku v44+ with comprehensive MIMU integration  
            **Data Source:** Myanmar Election Commission + MIMU Geographic Data  
            **Credits:** NLS translations, Clean Text processing, MIMU boundaries
            '''
        }
    )
    
    # Inject custom HTML header with favicon and meta tags
    st.markdown("""
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="Interactive visualization of Myanmar's 2025 electoral constituencies with MIMU integrated mapping, covering all assemblies: PTHT, AMTHT, TPHT, and TPTYT.">
        <meta name="keywords" content="Myanmar Election 2025, constituencies, MIMU, interactive map, Pyithu Hluttaw, Amyotha Hluttaw, electoral visualization">
        <meta name="author" content="Myanmar Election Visualization Team">
        <meta property="og:title" content="Myanmar Election 2025 - Interactive Constituency Visualization">
        <meta property="og:description" content="Comprehensive visualization of Myanmar's 838 electoral constituencies with MIMU geographic integration">
        <meta property="og:type" content="website">
        <meta property="og:image" content="/assets/icons/favicon.svg">
        <title>Myanmar Election 2025 - Interactive Constituency Visualization</title>
        <link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8Y2lyY2xlIGN4PSIxNiIgY3k9IjE2IiByPSIxNSIgZmlsbD0iI0ZFQ0YzRSIgc3Ryb2tlPSIjMzMzIiBzdHJva2Utd2lkdGg9IjIiLz4KICA8cmVjdCB4PSI4IiB5PSIxMCIgd2lkdGg9IjE2IiBoZWlnaHQ9IjEyIiByeD0iMiIgZmlsbD0iI2ZmZiIgc3Ryb2tlPSIjMzMzIiBzdHJva2Utd2lkdGg9IjEuNSIvPgogIDxyZWN0IHg9IjEwIiB5PSI4IiB3aWR0aD0iMTIiIGhlaWdodD0iMyIgcng9IjEiIGZpbGw9IiMzMzMiLz4KICA8cmVjdCB4PSI4IiB5PSIxNCIgd2lkdGg9IjE2IiBoZWlnaHQ9IjIiIGZpbGw9IiMzNEE4NTMiLz4KICA8cmVjdCB4PSI4IiB5PSIxNyIgd2lkdGg9IjE2IiBoZWlnaHQ9IjIiIGZpbGw9IiNFQTQzMzUiLz4KICA8cGF0aCBkPSJNMTYgMTEgTDE2LjUgMTIuNSBMMTggMTIuNSBMMTYuNzUgMTMuNSBMMTcuMjUgMTUgTDE2IDE0IEwxNC43NSAxNSBMMTUuMjUgMTMuNSBMMTQgMTIuNSBMMTUuNSAxMi41IFoiIGZpbGw9IiNGRUNGM0UiLz4KPC9zdmc+" />
    </head>
    """, unsafe_allow_html=True)

def get_theme_css(theme='light'):
    """Get CSS for specific theme."""
    
    if theme == 'dark':
        return """
    /* Dark Theme - Professional Dark Design */
    .stApp {
        background: linear-gradient(135deg, #0f1419 0%, #1a1d29 100%);
        color: #e8eaed;
    }
    
    .main .block-container {
        background: transparent;
        color: #e8eaed;
    }
    
    /* Typography - All headings and paragraphs */
    h1, h2, h3, h4, h5, h6 {
        color: #f9fafb !important;
    }
    
    p, .stMarkdown p {
        color: #d1d5db !important;
    }
    
    /* Sidebar styling */
    .stSidebar > div {
        background: linear-gradient(180deg, #1f2937 0%, #111827 100%);
        border-right: 1px solid #374151;
    }
    
    /* Reduce sidebar spacing */
    .stSidebar .element-container {
        margin-bottom: 0.5rem !important;
    }
    
    .stSidebar hr {
        margin: 0.5rem 0 !important;
    }
    
    .stSidebar h1, .stSidebar h2, .stSidebar h3, .stSidebar h4 {
        color: #f9fafb !important;
    }
    
    .stSidebar p, .stSidebar .stMarkdown p {
        color: #d1d5db !important;
    }
    
    .stSidebar .stMarkdown {
        color: #d1d5db !important;
    }
    
    .stSidebar .stSelectbox > div > div > select {
        background: linear-gradient(145deg, #6b7280, #4b5563) !important;
        color: #f9fafb !important;
        border: 1px solid #9ca3af;
        border-radius: 8px;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .stSidebar .stMultiSelect > div > div {
        background: linear-gradient(145deg, #6b7280, #4b5563) !important;
        color: #f9fafb !important;
        border: 1px solid #9ca3af;
        border-radius: 8px;
    }
    
    .stSidebar .stTextInput > div > div > input {
        background: linear-gradient(145deg, #374151, #1f2937);
        color: #f9fafb;
        border: 1px solid #6b7280;
        border-radius: 8px;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .stSidebar .stButton > button {
        background: linear-gradient(145deg, #3b82f6, #1d4ed8);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(59, 130, 246, 0.3);
    }
    
    .stSidebar .stButton > button:hover {
        background: linear-gradient(145deg, #2563eb, #1e40af);
        transform: translateY(-1px);
        box-shadow: 0 6px 8px rgba(59, 130, 246, 0.4);
    }
    
    .stExpander {
        background: linear-gradient(145deg, #1f2937, #111827);
        border: 1px solid #374151;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
    }
    
    .stExpander > div > div[data-testid="stExpanderDetails"] > div {
        background: rgba(31, 41, 55, 0.95) !important;
        color: #e5e7eb !important;
        border-radius: 0 0 12px 12px;
    }
    
    /* Expander content text for dark theme */
    .stExpander [data-testid="stExpanderDetails"] p,
    .stExpander [data-testid="stExpanderDetails"] h1,
    .stExpander [data-testid="stExpanderDetails"] h2,
    .stExpander [data-testid="stExpanderDetails"] h3,
    .stExpander [data-testid="stExpanderDetails"] h4 {
        color: #e5e7eb !important;
    }
    
    .stExpander [data-testid="stExpanderDetails"] .stMarkdown {
        color: #e5e7eb !important;
    }
    
    .map-info-section {
        background: linear-gradient(145deg, #1e3a8a, #1e40af);
        color: #dbeafe;
        padding: 16px 20px;
        border-radius: 12px;
        margin-bottom: 16px;
        border-left: 4px solid #60a5fa;
        box-shadow: 0 4px 12px rgba(30, 58, 138, 0.3);
    }
    
    .map-info-section p {
        margin: 8px 0 !important;
        color: #bfdbfe !important;
        font-size: 14px !important;
    }
    
    .map-info-section strong {
        color: #dbeafe !important;
        font-weight: 600 !important;
    }
    
    .stMetric {
        background: linear-gradient(145deg, #1f2937, #111827) !important;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #374151;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        color: #e5e7eb !important;
    }
    
    .stMetric .metric-value, .stMetric [data-testid="metric-value"] {
        color: #60a5fa !important;
        font-weight: 700;
    }
    
    .stMetric .metric-label, .stMetric [data-testid="metric-label"] {
        color: #9ca3af !important;
    }
    
    /* Additional metric selectors */
    .stMetric div {
        color: #e5e7eb !important;
    }
    
    .stMetric div[data-testid="stMetricValue"] {
        color: #60a5fa !important;
    }
    
    .stMetric div[data-testid="stMetricLabel"] {
        color: #9ca3af !important;
    }
    
    .stDataFrame {
        background: linear-gradient(145deg, #1f2937, #111827) !important;
        border-radius: 12px;
        border: 1px solid #374151;
    }
    
    /* Fix Plotly charts background for dark theme */
    .js-plotly-plot {
        background: transparent !important;
    }
    
    .main-svg {
        background: transparent !important;
    }
    
    .plot-container {
        background: transparent !important;
    }
    
    /* DataFrames and tables for dark theme - comprehensive selectors */
    .stDataFrame, .stDataFrame > div, .stDataFrame > div > div {
        background: #1f2937 !important;
        color: #e5e7eb !important;
    }
    
    .stDataFrame table, .dataframe, table.dataframe {
        background: #1f2937 !important;
        color: #e5e7eb !important;
    }
    
    .stDataFrame th, .dataframe th, table.dataframe th {
        background: #374151 !important;
        color: #f9fafb !important;
        border-bottom: 1px solid #4b5563 !important;
    }
    
    .stDataFrame td, .dataframe td, table.dataframe td {
        background: #1f2937 !important;
        color: #e5e7eb !important;
        border-bottom: 1px solid #374151 !important;
    }
    
    /* Pandas dataframe specific */
    .pandas-dataframe {
        background: #1f2937 !important;
        color: #e5e7eb !important;
    }
    
    .pandas-dataframe th {
        background: #374151 !important;
        color: #f9fafb !important;
    }
    
    .pandas-dataframe td {
        background: #1f2937 !important;
        color: #e5e7eb !important;
    }
    
    /* Main content dropdowns and selectors */
    .stSelectbox > div > div > select,
    .stMultiSelect > div > div > div,
    .stMultiSelect > div > div,
    .stSelectbox > div > div > div {
        background: linear-gradient(145deg, #374151, #1f2937) !important;
        color: #f9fafb !important;
        border: 1px solid #6b7280 !important;
        border-radius: 8px;
    }
    
    /* Dropdown options */
    .stSelectbox option,
    .stMultiSelect option {
        background: #1f2937 !important;
        color: #f9fafb !important;
    }
    
    /* Text inputs */
    .stTextInput > div > div > input {
        background: linear-gradient(145deg, #374151, #1f2937) !important;
        color: #f9fafb !important;
        border: 1px solid #6b7280 !important;
        border-radius: 8px;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(145deg, #3b82f6, #1d4ed8) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px;
        font-weight: 500;
    }
    
    /* Info and alert boxes */
    .stAlert, .stInfo {
        background: linear-gradient(145deg, #1e3a8a, #1e40af) !important;
        color: #dbeafe !important;
        border: 1px solid #3b82f6 !important;
        border-radius: 8px;
    }
    
    .stWarning {
        background: linear-gradient(145deg, #92400e, #d97706) !important;
        color: #fef3c7 !important;
        border: 1px solid #f59e0b !important;
        border-radius: 8px;
    }
        """
    else:
        return """
    /* Light Theme - Modern Professional Design */
    .stApp {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        color: #1e293b;
    }
    
    .main .block-container {
        background: transparent;
        color: #1e293b;
    }
    
    /* Typography - All headings and paragraphs */
    h1, h2, h3, h4, h5, h6 {
        color: #1e293b !important;
    }
    
    p, .stMarkdown p {
        color: #475569 !important;
    }
    
    /* Sidebar styling */
    .stSidebar > div {
        background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%);
        border-right: 1px solid #e2e8f0;
        box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
    }
    
    /* Reduce sidebar spacing */
    .stSidebar .element-container {
        margin-bottom: 0.5rem !important;
    }
    
    .stSidebar hr {
        margin: 0.5rem 0 !important;
    }
    
    .stSidebar h1, .stSidebar h2, .stSidebar h3, .stSidebar h4 {
        color: #1e293b !important;
    }
    
    .stSidebar p, .stSidebar .stMarkdown p {
        color: #475569 !important;
    }
    
    .stSidebar .stMarkdown {
        color: #475569 !important;
    }
    
    .stSidebar .stSelectbox > div > div > select {
        background: linear-gradient(145deg, #f1f5f9, #e2e8f0) !important;
        color: #374151 !important;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    
    .stSidebar .stSelectbox > div > div > select:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    .stSidebar .stMultiSelect > div > div {
        background: linear-gradient(145deg, #f1f5f9, #e2e8f0) !important;
        color: #374151 !important;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .stSidebar .stTextInput > div > div > input {
        background: linear-gradient(145deg, #ffffff, #f8fafc);
        color: #374151;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    
    .stSidebar .stTextInput > div > div > input:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    .stSidebar .stButton > button {
        background: linear-gradient(145deg, #3b82f6, #2563eb);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(59, 130, 246, 0.25);
    }
    
    .stSidebar .stButton > button:hover {
        background: linear-gradient(145deg, #2563eb, #1d4ed8);
        transform: translateY(-1px);
        box-shadow: 0 6px 12px rgba(59, 130, 246, 0.35);
    }
    
    .stExpander {
        background: linear-gradient(145deg, #ffffff, #f8fafc);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    
    .stExpander:hover {
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
    }
    
    /* Expander header/title styling for light theme */
    .stExpander > div > div[data-testid="collapsedControl"] {
        background: linear-gradient(145deg, #f8fafc, #ffffff) !important;
        color: #1e293b !important;
        border-radius: 12px 12px 0 0 !important;
    }
    
    .stExpander > div > div[data-testid="collapsedControl"] p {
        color: #1e293b !important;
        font-weight: 600 !important;
    }
    
    .stExpander > div > div[data-testid="stExpanderDetails"] > div {
        background: rgba(248, 250, 252, 0.95) !important;
        color: #374151 !important;
        border-radius: 0 0 12px 12px;
    }
    
    /* Expander content text */
    .stExpander [data-testid="stExpanderDetails"] p,
    .stExpander [data-testid="stExpanderDetails"] h1,
    .stExpander [data-testid="stExpanderDetails"] h2,
    .stExpander [data-testid="stExpanderDetails"] h3,
    .stExpander [data-testid="stExpanderDetails"] h4 {
        color: #374151 !important;
    }
    
    .stExpander [data-testid="stExpanderDetails"] .stMarkdown {
        color: #374151 !important;
    }
    
    .map-info-section {
        background: linear-gradient(145deg, #dbeafe, #bfdbfe);
        color: #1e40af;
        padding: 16px 20px;
        border-radius: 12px;
        margin-bottom: 16px;
        border-left: 4px solid #3b82f6;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
    }
    
    .map-info-section p {
        margin: 8px 0 !important;
        color: #1e40af !important;
        font-size: 14px !important;
        font-weight: 500;
    }
    
    .map-info-section strong {
        color: #1e3a8a !important;
        font-weight: 700 !important;
    }
    
    .metric-card {
        background: linear-gradient(145deg, #ffffff, #f8fafc);
        color: #1e293b;
        border-left: 4px solid #3b82f6;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
    }
    
    .stMetric {
        background: linear-gradient(145deg, #ffffff, #f8fafc) !important;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
        color: #1e293b !important;
    }
    
    .stMetric:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
    }
    
    .stMetric .metric-value, .stMetric [data-testid="metric-value"] {
        color: #1e40af !important;
        font-weight: 700;
    }
    
    .stMetric .metric-label, .stMetric [data-testid="metric-label"] {
        color: #64748b !important;
        font-weight: 500;
    }
    
    /* Additional metric selectors */
    .stMetric div {
        color: #1e293b !important;
    }
    
    .stMetric div[data-testid="stMetricValue"] {
        color: #1e40af !important;
    }
    
    .stMetric div[data-testid="stMetricLabel"] {
        color: #64748b !important;
    }
    
    .stDataFrame {
        background: linear-gradient(145deg, #ffffff, #f8fafc) !important;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    
    /* Fix Plotly charts background */
    .js-plotly-plot {
        background: transparent !important;
    }
    
    .main-svg {
        background: transparent !important;
    }
    
    .plot-container {
        background: transparent !important;
    }
    
    /* DataFrames and tables - comprehensive selectors */
    .stDataFrame, .stDataFrame > div, .stDataFrame > div > div {
        background: #ffffff !important;
        color: #374151 !important;
    }
    
    .stDataFrame table, .dataframe, table.dataframe {
        background: #ffffff !important;
        color: #374151 !important;
    }
    
    .stDataFrame th, .dataframe th, table.dataframe th {
        background: #f8fafc !important;
        color: #1e293b !important;
        border-bottom: 1px solid #e2e8f0 !important;
    }
    
    .stDataFrame td, .dataframe td, table.dataframe td {
        background: #ffffff !important;
        color: #374151 !important;
        border-bottom: 1px solid #f1f5f9 !important;
    }
    
    /* Pandas dataframe specific */
    .pandas-dataframe {
        background: #ffffff !important;
        color: #374151 !important;
    }
    
    .pandas-dataframe th {
        background: #f8fafc !important;
        color: #1e293b !important;
    }
    
    .pandas-dataframe td {
        background: #ffffff !important;
        color: #374151 !important;
    }
    
    /* Main content dropdowns and selectors */
    .stSelectbox > div > div > select,
    .stMultiSelect > div > div > div,
    .stMultiSelect > div > div,
    .stSelectbox > div > div > div {
        background: linear-gradient(145deg, #ffffff, #f8fafc) !important;
        color: #374151 !important;
        border: 1px solid #d1d5db !important;
        border-radius: 8px;
    }
    
    /* Dropdown options */
    .stSelectbox option,
    .stMultiSelect option {
        background: #ffffff !important;
        color: #374151 !important;
    }
    
    /* Text inputs */
    .stTextInput > div > div > input {
        background: linear-gradient(145deg, #ffffff, #f8fafc) !important;
        color: #374151 !important;
        border: 1px solid #d1d5db !important;
        border-radius: 8px;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(145deg, #3b82f6, #2563eb) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px;
        font-weight: 500;
    }
    
    /* Info and alert boxes */
    .stAlert, .stInfo {
        background: linear-gradient(145deg, #dbeafe, #bfdbfe) !important;
        color: #1e40af !important;
        border: 1px solid #3b82f6 !important;
        border-radius: 8px;
    }
    
    .stWarning {
        background: linear-gradient(145deg, #fef3c7, #fde68a) !important;
        color: #92400e !important;
        border: 1px solid #f59e0b !important;
        border-radius: 8px;
    }
        """

def add_custom_css():
    """Add custom CSS styling with theme support."""
    # Get current theme
    current_theme = st.session_state.get('theme', 'light')
    
    # Apply theme CSS
    theme_css = get_theme_css(current_theme)
    
    st.markdown(f"""
    <style>
    /* Base CSS - Enhanced Professional Design */
    html, body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
    }}
    
    .metric-card {{
        padding: 1.25rem;
        border-radius: 12px;
        border-left: 4px solid #3b82f6;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }}
    
    .metric-card::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.3), transparent);
    }}
    
    .assembly-ptht {{ 
        border-left-color: #2E86AB; 
        background: linear-gradient(145deg, rgba(46, 134, 171, 0.05), rgba(46, 134, 171, 0.02));
    }}
    .assembly-amtht {{ 
        border-left-color: #A23B72;
        background: linear-gradient(145deg, rgba(162, 59, 114, 0.05), rgba(162, 59, 114, 0.02));
    }}
    .assembly-tpht {{ 
        border-left-color: #F18F01;
        background: linear-gradient(145deg, rgba(241, 143, 1, 0.05), rgba(241, 143, 1, 0.02));
    }}
    .assembly-tptyt {{ 
        border-left-color: #C73E1D;
        background: linear-gradient(145deg, rgba(199, 62, 29, 0.05), rgba(199, 62, 29, 0.02));
    }}
    
    /* Typography improvements */
    h1, h2, h3 {{
        font-weight: 600;
        letter-spacing: -0.025em;
    }}
    
    h1 {{
        font-size: 2.25rem;
        line-height: 1.2;
        margin-bottom: 0.5rem;
    }}
    
    h2 {{
        font-size: 1.875rem;
        line-height: 1.3;
        margin-bottom: 1rem;
    }}
    
    h3 {{
        font-size: 1.5rem;
        line-height: 1.4;
        margin-bottom: 0.75rem;
    }}
    
    /* Enhanced spacing and layout */
    .stMultiSelect > div > div {{
        margin-bottom: 12px;
    }}
    
    .stSelectbox > div {{
        margin-bottom: 12px;
    }}
    
    /* Premium Folium styling */
    div[data-testid="stElement"] > div > iframe[title="streamlit_folium.st_folium"] {{
        border-radius: 16px !important;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1), 0 4px 10px rgba(0, 0, 0, 0.05) !important;
        margin: 16px 0 !important;
        height: 550px !important;
        width: 100% !important;
        border: 1px solid rgba(0, 0, 0, 0.05);
    }}
    
    /* Grid and layout improvements */
    .stMarkdown div[data-testid="stMarkdownContainer"] {{
        width: 100% !important;
    }}
    
    /* Loading and interaction states */
    .stSpinner {{
        min-height: 80px !important;
        height: 80px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}
    
    .stAlert {{
        min-height: 60px !important;
        margin: 12px 0 !important;
        border-radius: 8px !important;
        border-left-width: 4px !important;
    }}
    
    .element-container {{
        margin: 12px 0 !important;
    }}
    
    /* Clean up empty elements */
    div[data-testid="stEmpty"] {{
        height: 0 !important;
        min-height: 0 !important;
        max-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        display: block !important;
    }}
    
    .stElementContainer {{
        margin-bottom: 0.5rem !important;
    }}
    
    /* Enhanced expander styling */
    .stExpander {{
        border: none;
        border-radius: 12px;
        margin-bottom: 20px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }}
    
    .stExpander > div > div[data-testid="stExpanderDetails"] > div {{
        padding: 20px !important;
        line-height: 1.6 !important;
    }}
    
    .stExpander h4 {{
        font-size: 1.125rem !important;
        font-weight: 600 !important;
        margin: 0 0 16px 0 !important;
        line-height: 1.4 !important;
    }}
    
    .stExpander ul {{
        margin: 0 !important;
        padding-left: 24px !important;
        line-height: 1.6 !important;
    }}
    
    .stExpander li {{
        margin-bottom: 8px !important;
        line-height: 1.5 !important;
    }}
    
    .stExpander strong {{
        font-weight: 600 !important;
    }}
    
    .stExpander p {{
        margin: 16px 0 !important;
        line-height: 1.6 !important;
    }}
    
    /* Button enhancements */
    .stButton > button {{
        transition: all 0.3s ease;
        font-weight: 500;
        border-radius: 8px;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-1px);
    }}
    
    /* Plotly chart styling */
    .js-plotly-plot {{
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }}
    
    /* Data table improvements */
    .stDataFrame {{
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }}
    
    .stDataFrame table {{
        border-collapse: separate;
        border-spacing: 0;
    }}
    
    .stDataFrame th {{
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
    }}
    
    {theme_css}
    </style>
    """, unsafe_allow_html=True)

def show_navigation_guide():
    """Display navigation guidelines."""
    with st.expander(get_text("overview.quick_reference")):
        st.markdown("""
        #### Navigation Guide
        
        - **📊 Overview:** See statistics across all electoral assemblies
        - **🗺️ Interactive Map:** Explore constituencies on a responsive map (select assemblies in sidebar)
        - **📋 Search:** Find specific constituencies by name or region
        - **📈 Comparison:** Compare assembly data between election years
        
        **Tip:** Use the sidebar filters to customize what data you see!
        """)

def create_sidebar(db):
    """Create enhanced sidebar with organized combo boxes."""
    
    # 1. Navigation Combo Box (System Settings + How to Use)
    with st.sidebar.expander("🗳️ Multi-Assembly Navigation", expanded=False):
        
        # System Settings sub-expander
        with st.expander("⚙️ System Settings", expanded=False):
            # Language selector with emoji buttons
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**🌐 Language**")
            with col2:
                current_lang = st.session_state.get('language', 'en')
                lang_cols = st.columns(2)
                with lang_cols[0]:
                    if st.button("🇺🇸", key="lang_en", help="English", 
                               type="primary" if current_lang == 'en' else "secondary"):
                        if st.session_state.language != 'en':
                            st.session_state.language = 'en'
                            st.rerun()
                with lang_cols[1]:
                    if st.button("🇲🇲", key="lang_mm", help="မြန်မာ",
                               type="primary" if current_lang == 'mm' else "secondary"):
                        if st.session_state.language != 'mm':
                            st.session_state.language = 'mm'
                            st.rerun()
            
            # Theme selector with emoji buttons
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**🎨 Theme**")
            with col2:
                current_theme = st.session_state.get('theme', 'light')
                theme_cols = st.columns(2)
                with theme_cols[0]:
                    if st.button("🌞", key="theme_light", help="Light",
                               type="primary" if current_theme == 'light' else "secondary"):
                        if st.session_state.theme != 'light':
                            st.session_state.theme = 'light'
                            st.rerun()
                with theme_cols[1]:
                    if st.button("🌙", key="theme_dark", help="Dark",
                               type="primary" if current_theme == 'dark' else "secondary"):
                        if st.session_state.theme != 'dark':
                            st.session_state.theme = 'dark'
                            st.rerun()
        
        # How to Use Application sub-expander
        with st.expander("📖 How to Use This Application", expanded=False):
            st.markdown("**Quick Reference:**")
            st.markdown(get_text("overview.quick_ref_items.overview"))
            st.markdown(get_text("overview.quick_ref_items.map")) 
            st.markdown(get_text("overview.quick_ref_items.search"))
            st.markdown(get_text("overview.quick_ref_items.comparison"))
    
    st.sidebar.markdown("---")
    
    # 2. Page Selection (standalone)
    page = st.sidebar.selectbox(
        "📄 Select Page",
        [get_text("pages.overview"), get_text("pages.map"), get_text("pages.search"), get_text("pages.comparison"), get_text("pages.parties"), get_text("pages.historical")],
        index=0,
        help="Choose which section of the application to view"
    )
    
    st.sidebar.markdown("---")
    
    # 3. Assembly Selection (prominent placement)
    st.sidebar.markdown("### 🏛️ Assembly Selection")
    st.sidebar.markdown("*Choose which assemblies to analyze*")
    
    assembly_options = {
        "PTHT": get_text("assemblies.PTHT"),
        "AMTHT": get_text("assemblies.AMTHT"), 
        "TPHT": get_text("assemblies.TPHT"),
        "TPTYT": get_text("assemblies.TPTYT")
    }
    
    selected_assemblies = st.sidebar.multiselect(
        "Assemblies to Display",
        options=list(assembly_options.keys()),
        default=["PTHT"],  # Only real data available
        format_func=lambda x: assembly_options[x],
        help="Select one or more assemblies to view their constituencies"
    )
    
    # Show quick constituency count
    if selected_assemblies:
        # Get a quick count from database
        df_preview = db.get_constituencies(selected_assemblies)
        constituency_count = len(df_preview)
        st.sidebar.success(f"📊 {constituency_count} constituencies selected")
    else:
        st.sidebar.warning("⚠️ No assemblies selected")
    
    # Region filter
    if selected_assemblies:
        all_regions = db.get_states_regions()
        selected_regions = st.sidebar.multiselect(
            "States/Regions",
            options=all_regions,
            default=[],
            help="Filter by specific states or regions"
        )
    else:
        selected_regions = []
        
    # Electoral system filter
    electoral_systems = st.sidebar.multiselect(
        "Electoral Systems",
        options=["FPTP", "PR"],
        default=["FPTP", "PR"],
        help="First Past the Post (FPTP) or Proportional Representation (PR)"
    )
    
    st.sidebar.markdown("---")
    
    # 4. Map Display Options
    st.sidebar.markdown("### 🗺️ Map Display")
    
    # Boundary layer toggles
    show_township_boundaries = st.sidebar.checkbox(
        "Show Township Boundaries",
        value=False,
        help="Display township boundary polygons (recommended for zoom level 8+)"
    )
    
    show_state_boundaries = st.sidebar.checkbox(
        "Show State/Region Boundaries", 
        value=False,
        help="Display state and region boundary outlines"
    )
    
    # Map style options
    boundary_opacity = st.sidebar.slider(
        "Boundary Opacity",
        min_value=0.1,
        max_value=1.0,
        value=0.6,
        step=0.1,
        help="Adjust transparency of boundary lines"
    )
    
    st.sidebar.markdown("---")
    
    # 5. Function Combo Box (Map Performance + Search Options)
    with st.sidebar.expander("🔧 Advanced Controls", expanded=False):
        # Map Performance sub-expander
        with st.expander("⚡ Map Performance", expanded=False):
            st.markdown("*Optimize map rendering and performance*")
            
            performance_mode = st.selectbox(
                "Performance Mode",
                options=["fast", "balanced", "quality"],
                index=1,
                help="Fast: Optimized for speed, Quality: Best visuals, Balanced: Good compromise"
            )
            
            render_mode = st.selectbox(
                "Render Mode",
                options=["auto", "heatmap", "cluster", "simplified", "full"],
                index=0,
                help="Auto: Automatically choose based on data size"
            )
        
        # Search Options sub-expander (only for search page)
        search_term = ""
        if page == get_text("pages.search"):
            with st.expander("🔍 Search Options", expanded=False):
                st.markdown("*Find specific constituencies*")
                search_term = st.text_input(
                    "Find Constituencies",
                    placeholder="Enter name in English or Myanmar...",
                    help="Search by constituency name, region, or included areas"
                )
                if search_term:
                    st.success(f"Searching for: '{search_term}'")
    
    st.sidebar.markdown("---")
    
    # 4. Site Status Combo Box (Database Status + Current Data Coverage)
    with st.sidebar.expander("📊 Site Status", expanded=False):
        
        # Database Status sub-expander
        with st.expander("🔌 Database Status", expanded=False):
            if st.button("Test Connection"):
                db.test_connection()
            
        # Current Data Coverage sub-expander
        with st.expander("ℹ️ Current Data Coverage", expanded=False):
            stats = db.get_assembly_statistics()
            if stats:
                st.markdown(f"""
                **Total Constituencies:** {stats.get('total_constituencies', 0)}  
                **Total Representatives:** {stats.get('total_representatives', 0)}  
                **Mapped Locations:** {stats.get('mapped_constituencies', 0)}
                
                **By Assembly:**
                """)
                for assembly in stats.get('assembly_breakdown', []):
                    st.markdown(f"- {assembly['assembly_type']}: {assembly['constituencies']} constituencies")
                    
            st.markdown("**Last Updated:** Real-time PostgreSQL")
            st.markdown("**Source:** Myanmar Election Commission")
    
    st.sidebar.markdown("---")
    
    # 5. Credits Combo Box (Tech Stack + Data Credits + Site Credits)
    with st.sidebar.expander("🏆 Credits & Tech Stack", expanded=False):
        
        # Tech Stack sub-expander
        with st.expander("⚙️ Technology Stack", expanded=False):
            st.markdown("""
            **Frontend & Backend:**
            - 🐍 Python 3.11
            - 🚀 Streamlit (Web Framework)
            - 🗺️ Folium + streamlit-folium (Interactive Maps)
            - 📊 Plotly (Charts & Visualizations)
            - 🐼 Pandas + GeoPandas (Data Processing)
            
            **Database & Infrastructure:**
            - 🐘 PostgreSQL + PostGIS (Spatial Database)
            - 🐳 Docker + Docker Compose (Containerization)
            - ⚡ SQLAlchemy + psycopg2 (Database Connectivity)
            
            **UI & Styling:**
            - 🎨 Custom CSS (Theme System)
            - 🌐 Bilingual Support (EN/MM)
            - 📱 Responsive Design
            """)
        
        # Data Source & Cleaning Credits sub-expander  
        with st.expander("📊 Data Source & Processing", expanded=False):
            st.markdown("""
            **Data Preparation & Cleaning:**
            - 🧹 **Burma Data** - Data cleaning and normalization
            - 🗣️ **Nyi Lynn Seck** - Myanmar language processing
            
            **Data Sources:**
            - 🗳️ **UEC (Union Election Commission)** - Official election data
            - 🗺️ **MIMU (Myanmar Information Management Unit)** - Geographic boundaries
            - 📍 **OpenStreetMap** - Additional geographic coordinates
            
            **Data Coverage:**
            - 835 constituencies across 4 assemblies (PTHT: 330, AMTHT: 116, TPHT: 360, TPTYT: 29)
            - Bilingual constituency names (English/Myanmar)
            - Geographic coordinates and boundary data
            - Electoral system classifications
            """)
        
        # Site Creation Credits sub-expander
        with st.expander("🛠️ Development Credits", expanded=False):
            st.markdown("""
            **Site Development:**
            - 💻 **OSS (Open Source Software)** - Framework and libraries
            - 👨‍💻 **Burma Data | Nyi Lynn Seck** - System design, development & implementation
            
            **Key Features Developed:**
            - Multi-assembly data visualization system
            - Interactive map with performance optimization
            - Bilingual user interface (English/Myanmar)
            - Real-time PostgreSQL database integration
            - Responsive theme system (Light/Dark)
            - Advanced filtering and search capabilities
            
            **Open Source:**
            This project leverages open-source technologies and contributes back to the Myanmar tech community.
            """)
        
        # Usage License & Terms sub-expander
        with st.expander("📜 Usage License & Terms", expanded=False):
            st.markdown("""
            **Website & Application License:**
            - 📖 **Creative Commons Attribution 4.0 (CC BY 4.0)**
            - ✅ **Free to use, share, and adapt** with proper attribution
            - 🔗 **Attribution Required:** Credit to Burma Data | Nyi Lynn Seck and data sources
            - 🌐 **Non-commercial and educational use encouraged**
            
            **Data Usage License:**
            - 📊 **Original Data:** Union Election Commission (UEC) - Myanmar
            - ⚖️ **Public Domain:** Electoral data for transparency purposes
            - 🗺️ **Geographic Data:** MIMU, OpenStreetMap (ODbL License)
            - ⚠️ **Data Accuracy:** Based on official sources as of processing date
            
            **Terms of Use:**
            - 📍 Data visualization for informational purposes only
            - 🚫 Not for official election administration use
            - ⚡ Real-time updates subject to source data availability
            """)
        
        # Original Data Sources & Credits sub-expander  
        with st.expander("🏛️ Original Data & Official Credits", expanded=False):
            st.markdown(f"""
            **Primary Data Source:**
            - 🗳️ **Union Election Commission (UEC)** - Republic of the Union of Myanmar
            - 📋 **Official Election Data** - 2025 General Election Constituencies
            - 🏛️ **Assembly Coverage:** Pyithu Hluttaw, Amyotha Hluttaw, State/Regional, Ethnic Affairs
            
            **Data Processing Timeline:**
            - 📅 **Original Data Collection:** November-December 2024
            - 🔄 **Last Data Processing:** January 2025  
            - ⚡ **Website Last Updated:** {st.session_state.get('current_date', 'January 18, 2025')}
            - 📊 **Database Status:** Live PostgreSQL updates
            
            **Official Disclaimers:**
            - ⚖️ **Data Subject to Change:** UEC may update constituency boundaries
            - 📍 **Coordinates:** Approximate locations for visualization purposes
            - 🔍 **Verification:** Users should verify with official UEC sources for legal matters
            - 📞 **Updates:** Check UEC official website for latest information
            
            **Geographic Data Credits:**
            - 🗺️ **MIMU (Myanmar Information Management Unit)** - Administrative boundaries
            - 🌍 **OpenStreetMap Contributors** - Additional coordinate data
            - 📐 **PostGIS/PostgreSQL** - Spatial data processing
            """)
        
        # Version & Technical License sub-expander
        with st.expander("⚙️ Version & Technical License", expanded=False):
            st.markdown("""
            **Application Version:**
            - 🏷️ **Version:** 2025.2.0 MIMU Enhanced Multi-Layer Edition
            - 📅 **Release Date:** August 2025
            - 🗺️ **Major Features:** MIMU township boundaries + pinpoint markers
            - 🔄 **Update Cycle:** Continuous integration with comprehensive data
            - 💾 **Database Version:** PostgreSQL 15 + PostGIS 3.4 with spatial indexing
            
            **Technical Licensing:**
            - 🐍 **Python Libraries:** Various open-source licenses (MIT, BSD, Apache 2.0)
            - 🚀 **Streamlit:** Apache License 2.0
            - 🗺️ **Folium/Leaflet:** BSD/MIT Licenses  
            - 📊 **Plotly:** MIT License
            - 🐳 **Docker:** Apache License 2.0
            
            **Community & Legal:**
            - 🇲🇲 **Created for Myanmar Election Transparency**
            - 🤝 **Open Source Community Project**
            - 📧 **Contact:** For data corrections or technical issues
            - 🏛️ **Compliance:** Follows Myanmar digital governance guidelines
            """)
    
    st.sidebar.markdown("---")
    
    # Version and Update Information
    st.sidebar.markdown("### ℹ️ Version Info")
    # Dynamic version with git hash and Yangon timezone
    import subprocess
    from datetime import datetime, timezone, timedelta
    
    try:
        git_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip()
    except:
        git_hash = "89cdcc1"  # Fallback
    
    # Yangon timezone (+6:30)
    yangon_tz = timezone(timedelta(hours=6, minutes=30))
    current_time = datetime.now(yangon_tz)
    
    st.sidebar.markdown(f"**Version:** 2025.2.0-v44+{git_hash}")
    st.sidebar.markdown(f"**Last Updated:** {current_time.strftime('%B %d, %Y at %I:%M %p MMT')}")
    st.sidebar.markdown("**Features:** MIMU Multi-Layer + Pinpoint Markers")
    st.sidebar.markdown("**Data:** 838 constituencies with 96% coordinate mapping")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("*🗺️ Myanmar Election 2025 - MIMU Enhanced | Built with ❤️ for electoral transparency*")
    
    return page, selected_assemblies, selected_regions, electoral_systems, search_term, performance_mode, render_mode, show_township_boundaries, show_state_boundaries, boundary_opacity

def display_assembly_metrics(stats):
    """Display assembly overview metrics."""
    if not stats:
        st.warning("No statistics available")
        return
        
    # Main metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Constituencies", 
            stats.get('total_constituencies', 0),
            help="All constituencies across assemblies"
        )
    
    with col2:
        st.metric(
            "Total Representatives", 
            stats.get('total_representatives', 0),
            help="Sum of all elected representatives"
        )
    
    with col3:
        st.metric(
            "Mapped Locations", 
            stats.get('mapped_constituencies', 0),
            help="Constituencies with geographic coordinates"
        )
        
    with col4:
        mapped_pct = 0
        if stats.get('total_constituencies', 0) > 0:
            mapped_pct = round(stats['mapped_constituencies'] * 100 / stats['total_constituencies'], 1)
        st.metric(
            "Mapping Coverage", 
            f"{mapped_pct}%",
            help="Percentage of constituencies with coordinates"
        )

def get_chart_colors():
    """Get theme-aware colors for charts."""
    current_theme = st.session_state.get('theme', 'light')
    
    if current_theme == 'dark':
        return {
            'bg_color': 'rgba(15, 20, 25, 0)',
            'paper_color': 'rgba(15, 20, 25, 0)',
            'text_color': '#e8eaed',
            'grid_color': '#374151',
            'bar_colors': ['#60a5fa', '#f59e0b', '#10b981', '#ef4444'],
            'line_color': '#6b7280'
        }
    else:
        return {
            'bg_color': 'rgba(255, 255, 255, 0)',
            'paper_color': 'rgba(255, 255, 255, 0)',
            'text_color': '#1e293b',
            'grid_color': '#e2e8f0',
            'bar_colors': ['#3b82f6', '#f59e0b', '#10b981', '#ef4444'],
            'line_color': '#d1d5db'
        }

def create_assembly_comparison_chart(stats):
    """Create assembly comparison chart."""
    if not stats or not stats.get('assembly_breakdown'):
        return None
        
    assembly_data = stats['assembly_breakdown']
    df = pd.DataFrame(assembly_data)
    
    # Group by assembly type and sum
    df_grouped = df.groupby('assembly_type').agg({
        'constituencies': 'sum',
        'total_representatives': 'sum',
        'mapped_count': 'sum'
    }).reset_index()
    
    colors = get_chart_colors()
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Constituencies',
        x=df_grouped['assembly_type'],
        y=df_grouped['constituencies'],
        marker_color=colors['bar_colors'][0],
        yaxis='y1'
    ))
    
    fig.add_trace(go.Bar(
        name='Representatives',
        x=df_grouped['assembly_type'],
        y=df_grouped['total_representatives'],
        marker_color=colors['bar_colors'][1],
        yaxis='y1'
    ))
    
    fig.update_layout(
        title="Constituencies and Representatives by Assembly",
        title_font_color=colors['text_color'],
        xaxis_title="Assembly Type",
        yaxis_title="Count",
        barmode='group',
        height=400,
        plot_bgcolor=colors['bg_color'],
        paper_bgcolor=colors['paper_color'],
        font={'color': colors['text_color']},
        xaxis={'gridcolor': colors['grid_color'], 'color': colors['text_color']},
        yaxis={'gridcolor': colors['grid_color'], 'color': colors['text_color']}
    )
    
    return fig

def create_interactive_map(df, assembly_types, show_township_boundaries=False, show_state_boundaries=True, boundary_opacity=0.6):
    """Create interactive map with multi-assembly support and boundary layers."""
    if df.empty:
        st.warning("No data available for selected filters")
        return None
        
    # Filter only mapped constituencies
    mapped_df = df[df['lat'].notna() & df['lng'].notna()].copy()
    
    if mapped_df.empty:
        st.warning("No mapped constituencies found for selected filters")
        return None
    
    # Calculate map center
    center_lat = mapped_df['lat'].median()
    center_lng = mapped_df['lng'].median()
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=6,
        tiles='OpenStreetMap'
    )
    
    # Initialize boundary renderer
    boundary_renderer = BoundaryRenderer()
    
    # Add boundary layers if requested (with error handling for performance)
    try:
        if show_state_boundaries:
            boundary_renderer.add_state_boundaries(m, zoom_level=6)
        
        if show_township_boundaries:
            # Show loading message for large boundary file
            boundary_loading = st.empty()
            boundary_loading.info("🗺️ Loading township boundaries...")
            boundary_renderer.add_township_boundaries(m, zoom_level=8, constituency_data=mapped_df, opacity=boundary_opacity)
            boundary_loading.empty()
    except Exception as e:
        st.warning(f"⚠️ Boundary data loading issue (map will still work without boundaries): {e}")
        logger.warning(f"Boundary loading failed: {e}")
    
    # Assembly colors
    assembly_colors = {
        'PTHT': '#2E86AB',
        'AMTHT': '#A23B72', 
        'TPHT': '#F18F01',
        'TPTYT': '#C73E1D'
    }
    
    # Add markers by assembly type
    for assembly in assembly_types:
        assembly_data = mapped_df[mapped_df['assembly_type'] == assembly]
        if assembly_data.empty:
            continue
            
        color = assembly_colors.get(assembly, '#666666')
        
        # Create marker cluster for each assembly
        marker_cluster = MarkerCluster(name=f"{assembly} Constituencies").add_to(m)
        
        for _, row in assembly_data.iterrows():
            popup_html = f"""
            <div style="font-family: Arial; width: 250px;">
                <h4 style="margin: 0; color: {color};">{assembly}</h4>
                <hr style="margin: 5px 0;">
                <b>English:</b> {row['constituency_en']}<br>
                <b>Myanmar:</b> {row['constituency_mm']}<br>
                <b>State/Region:</b> {row['state_region_en']}<br>
                <b>Electoral System:</b> {row['electoral_system']}<br>
                <b>Representatives:</b> {row['representatives']}<br>
                <b>Code:</b> {row['constituency_code']}
            </div>
            """
            
            folium.CircleMarker(
                location=[row['lat'], row['lng']],
                radius=6 if assembly == 'PTHT' else 8,  # Slightly larger for other assemblies
                popup=folium.Popup(popup_html, max_width=300),
                color=color,
                fillColor=color,
                weight=2,
                fillOpacity=0.7
            ).add_to(marker_cluster)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    return m

def show_historical_data_page():
    """Display historical 2020 election data page with document links and references."""
    st.title("📜 Historical Data (2020)")
    st.markdown("*Comprehensive collection of 2020 Myanmar Election documents and references*")
    
    # Introduction
    st.markdown("""
    ### Overview
    This page provides access to historical documents, maps, and data from Myanmar's 2020 General Election. 
    The documents are organized by source organization and include official reports, boundary maps, and statistical analyses.
    """)
    
    # Data Sources Overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🏛️ IDEA Documents", "1", help="International Institute for Democracy and Electoral Assistance")
    with col2:
        st.metric("🔬 MERIN Reports", "4", help="Myanmar Election Research and Information Network")
    with col3:
        st.metric("🗺️ MIMU Maps", "14", help="Myanmar Information Management Unit")
    with col4:
        st.metric("📋 UEC Materials", "7", help="Union Election Commission Official Documents")
    
    st.markdown("---")
    
    # IDEA Section
    with st.expander("🏛️ **International Institute for Democracy and Electoral Assistance (IDEA)**", expanded=False):
        st.markdown("""
        **Organization:** International IDEA  
        **Website:** [idea.int](https://www.idea.int/)  
        **Focus:** Democracy and electoral assistance worldwide
        
        #### Available Documents:
        """)
        
        docs = [
            {
                "title": "2020 General Election in Myanmar - Fact Sheet",
                "date": "July 14, 2020",
                "file": "2020-General-Election-in-Myanmar-Fact-Sheet_14-July-2020.pdf",
                "description": "Comprehensive fact sheet about Myanmar's 2020 general election processes and procedures"
            }
        ]
        
        for doc in docs:
            col_info, col_download = st.columns([3, 1])
            with col_info:
                st.markdown(f"""
                **📄 {doc['title']}**  
                *Date:* {doc['date']}  
                *Description:* {doc['description']}  
                *File:* `{doc['file']}`
                """)
            with col_download:
                file_path = f"2020/idea.int/{doc['file']}"
                try:
                    with open(file_path, "rb") as file:
                        st.download_button(
                            label="⬇️ Download",
                            data=file.read(),
                            file_name=doc['file'],
                            mime="application/pdf",
                            key=f"idea_{doc['file']}"
                        )
                except FileNotFoundError:
                    st.write("*File not accessible*")
    
    # MERIN Section  
    with st.expander("🔬 **Myanmar Election Research and Information Network (MERIN)**", expanded=False):
        st.markdown("""
        **Organization:** MERIN  
        **Website:** [merin.org.mm](http://merin.org.mm/)  
        **Focus:** Election research and gender participation analysis
        
        #### Available Documents:
        """)
        
        docs = [
            {
                "title": "Gender and Political Participation in Myanmar",
                "date": "October 2020",
                "file": "Report_Gender_and_Political_Participlation_in_Myanmar_EMReF_Oct2020_ENG-MMR.pdf",
                "description": "Bilingual report on gender representation and political participation"
            },
            {
                "title": "Amyotha Hluttaw Constituency Boundaries 2020",
                "date": "August 21, 2020", 
                "file": "mimu1707v01_21_aug_20_ifes_constituency_boundaries_of_amyotha_hluttaw_2020_a3.pdf",
                "description": "Official constituency boundary maps for Upper House"
            },
            {
                "title": "Pyithu Hluttaw Constituency Boundaries 2020",
                "date": "August 21, 2020",
                "file": "mimu1707v01_21_aug_20_ifes_constituency_boundaries_of_pyithu_hluttaw_2020_a3.pdf", 
                "description": "Official constituency boundary maps for Lower House"
            },
            {
                "title": "State and Region Hluttaw Boundaries 2020",
                "date": "August 24, 2020",
                "file": "mimu1707v01_24_aug_20_ifes_constituency_boundaries_of_state_and_region_hluttaw_2020_a3.pdf",
                "description": "Regional assembly constituency boundaries"
            }
        ]
        
        for doc in docs:
            col_info, col_download = st.columns([3, 1])
            with col_info:
                st.markdown(f"""
                **📄 {doc['title']}**  
                *Date:* {doc['date']}  
                *Description:* {doc['description']}  
                *File:* `{doc['file']}`
                """)
            with col_download:
                file_path = f"2020/merin.org.mm/{doc['file']}"
                try:
                    with open(file_path, "rb") as file:
                        st.download_button(
                            label="⬇️ Download",
                            data=file.read(),
                            file_name=doc['file'],
                            mime="application/pdf",
                            key=f"merin_{doc['file'][:20]}"  # Truncate for unique key
                        )
                except FileNotFoundError:
                    st.write("*File not accessible*")
    
    # MIMU Section
    with st.expander("🗺️ **Myanmar Information Management Unit (MIMU)**", expanded=False):
        st.markdown("""
        **Organization:** MIMU  
        **Website:** [themimu.info](https://themimu.info/)  
        **Focus:** Geographic information and mapping support
        
        #### Available Documents:
        """)
        
        docs = [
            {
                "title": "Atlas of Myanmar Election Maps 2010-2018",
                "date": "July 2020",
                "file": "Atlas_of_Myanmar_Election_Maps_2010-2018_IFES-MIMU_Jul2020.pdf",
                "description": "Comprehensive atlas covering multiple election cycles"
            },
            {
                "title": "2020 Election Cancelled Areas (Oct 16)",
                "date": "October 19, 2020",
                "file": "Map_2020 Election Cancelled Areas_As of 16Oct_IFES_MIMU1713v01_19Oct2020_A3.pdf",
                "description": "Areas where 2020 elections were cancelled as of October 16"
            },
            {
                "title": "2020 Election Cancelled Areas (Oct 27)",
                "date": "October 28, 2020",
                "file": "Map_2020_Election_Cancelled_Areas_As_of_27Oct_IFES_MIMU1713v02_28Oct2020_A3.pdf",
                "description": "Updated cancellation areas as of October 27"
            },
            {
                "title": "Pyithu Hluttaw Election Results 2020",
                "date": "November 24, 2020",
                "file": "Map_Pyithu Hluttaw Election Results 2020_IFES_MIMU1707v02_24Nov2020_A3.pdf",
                "description": "Official Lower House election results"
            },
            {
                "title": "Amyotha Hluttaw Election Results 2020",
                "date": "November 24, 2020",
                "file": "Map_Amyotha Hluttaw Election Results 2020_IFES_MIMU1707v02_24Nov2020 A3.pdf",
                "description": "Official Upper House election results"
            },
            {
                "title": "State/Region Election Results 2020",
                "date": "November 24, 2020",
                "file": "Map_St-Rg Election Results 2020_IFES_MIMU1707v02_24Nov2020_A3.pdf",
                "description": "Regional assembly election results"
            },
            {
                "title": "Constituency Boundaries of Pyithu Hluttaw 2020",
                "date": "August 13, 2020",
                "file": "Map_Constituency Boundaries of Pyithu Hluttaw_2020 IFES MIMU1707v01 13Aug2020 A3.pdf",
                "description": "Lower House constituency boundary maps"
            },
            {
                "title": "Constituency Boundaries of Amyotha Hluttaw 2020",
                "date": "August 13, 2020",
                "file": "Map_Constituency Boundaries of Amyotha Hluttaw_2020 IFES MIMU1707v01 13Aug2020 A3.pdf",
                "description": "Upper House constituency boundary maps"
            }
        ]
        
        for idx, doc in enumerate(docs):
            col_info, col_download = st.columns([3, 1])
            with col_info:
                st.markdown(f"""
                **📄 {doc['title']}**  
                *Date:* {doc['date']}  
                *Description:* {doc['description']}  
                *File:* `{doc['file']}`
                """)
            with col_download:
                file_path = f"2020/themimu.info/{doc['file']}"
                try:
                    with open(file_path, "rb") as file:
                        st.download_button(
                            label="⬇️ Download",
                            data=file.read(),
                            file_name=doc['file'],
                            mime="application/pdf",
                            key=f"mimu_{idx}"
                        )
                except FileNotFoundError:
                    st.write("*File not accessible*")
    
    # UEC Section
    with st.expander("📋 **Union Election Commission (UEC) - Official Documents**", expanded=False):
        st.markdown("""
        **Organization:** Union Election Commission of Myanmar  
        **Website:** [uec.org.mm](http://uec.org.mm/)  
        **Focus:** Official election administration and constituency definitions
        
        #### Available Documents:
        """)
        
        docs = [
            {
                "title": "Pyithu Hluttaw Constituencies",
                "date": "2020",
                "file": "ပြည်သူ့လွှတ်တော်မဲဆန္ဒနယ်.pdf",
                "description": "Official constituency list for Lower House (Myanmar language)"
            },
            {
                "title": "Amyotha Hluttaw Constituencies", 
                "date": "2020",
                "file": "အမျိုးသားလွှတ်တော် မဲဆန္ဒနယ်.pdf",
                "description": "Official constituency list for Upper House (Myanmar language)"
            },
            {
                "title": "State/Region Hluttaw Constituencies",
                "date": "2020", 
                "file": "တိုင်းဒေသကြီးလွှတ်တော် သို့မဟုတ် ပြည်နယ်လွှတ်တော် မဲဆန္ဒနယ် .pdf",
                "description": "Regional assembly constituencies (Myanmar language)"
            },
            {
                "title": "Ethnic Constituencies",
                "date": "2020",
                "file": "တိုင်းဒေသကြီးလွှတ်တော် သို့မဟုတ် ပြည်နယ်လွှတ်တော် ( တိုင်းရင်းသားလူမျိုး ) မဲဆန္ဒနယ်.pdf", 
                "description": "Ethnic minority constituencies (Myanmar language)"
            },
            {
                "title": "Approved Candidate Lists",
                "date": "2020",
                "file": "Directory with candidate information",
                "description": "Official approved candidate listings by constituency"
            },
            {
                "title": "Election Results Annulment Declaration",
                "date": "2021",
                "file": "ရွေးကောက်ပွဲရလဒ်များ ပယ်ဖျက်ကြောင်း ကြေညာခြင်း.pdf",
                "description": "Official declaration of election results annulment"
            }
        ]
        
        for idx, doc in enumerate(docs):
            col_info, col_download = st.columns([3, 1])
            with col_info:
                st.markdown(f"""
                **📄 {doc['title']}**  
                *Date:* {doc['date']}  
                *Description:* {doc['description']}  
                *File:* `{doc['file']}`
                """)
            with col_download:
                if doc['file'] == "Directory with candidate information":
                    # For directories, show a browse option
                    if st.button("📁 Browse", key=f"uec_browse_{idx}"):
                        st.info("Candidate information available in 2020/uec.org.mm/ directory")
                else:
                    # Handle Myanmar language file names
                    if doc['file'].endswith('.pdf'):
                        file_path = f"2020/uec.org.mm/မဲဆန္ဒနယ်/{doc['file']}"
                        try:
                            with open(file_path, "rb") as file:
                                st.download_button(
                                    label="⬇️ Download",
                                    data=file.read(),
                                    file_name=doc['file'],
                                    mime="application/pdf",
                                    key=f"uec_{idx}"
                                )
                        except FileNotFoundError:
                            # Try alternative path for annulment document
                            file_path = f"2020/uec.org.mm/{doc['file']}"
                            try:
                                with open(file_path, "rb") as file:
                                    st.download_button(
                                        label="⬇️ Download",
                                        data=file.read(),
                                        file_name=doc['file'],
                                        mime="application/pdf",
                                        key=f"uec_alt_{idx}"
                                    )
                            except FileNotFoundError:
                                st.write("*File not accessible*")
                    else:
                        st.write("*Directory*")
    
    # External References
    with st.expander("🌐 **External References and Links**", expanded=False):
        st.markdown("""
        #### Additional Resources:
        
        **📚 Wikimedia Commons**  
        **Link:** [Election maps of Myanmar](https://commons.wikimedia.org/wiki/Category:Election_maps_of_Myanmar)  
        **Description:** Public domain election maps and visualizations
        
        **🔗 Related Websites:**
        - [International Foundation for Electoral Systems (IFES)](https://www.ifes.org/)
        - [Myanmar Election Commission](http://uec.org.mm/)
        - [Myanmar Information Management Unit](https://themimu.info/)
        """)
    
    # Data Usage and Licensing
    st.markdown("---")
    st.subheader("📋 Data Usage and Attribution")
    
    st.markdown("""
    #### Data Sources Credit:
    - **🏛️ IDEA:** International Institute for Democracy and Electoral Assistance
    - **🔬 MERIN:** Myanmar Election Research and Information Network  
    - **🗺️ MIMU:** Myanmar Information Management Unit
    - **📋 UEC:** Union Election Commission of Myanmar
    - **🌐 Wikimedia:** Public domain election resources
    
    #### Download Information:
    - **⬇️ Direct Downloads:** Click the download buttons to save PDF documents locally
    - **📁 File Access:** All files are stored in the `2020/` directory structure
    - **🔒 File Security:** Downloads are served directly from local storage
    - **📱 Mobile Support:** Downloads work on desktop and mobile devices
    
    #### Usage Guidelines:
    - These documents are provided for research and educational purposes
    - Original copyright belongs to respective organizations
    - When using this data, please provide appropriate attribution
    - Check individual document licenses for specific usage terms
    
    #### Last Updated:
    *Historical data collection: {0}*
    """.format(st.session_state.current_date))
    
    # Technical Notes
    with st.expander("🔧 **Technical Notes**", expanded=False):
        st.markdown("""
        #### File Organization:
        ```
        2020/
        ├── idea.int/           # IDEA documents
        ├── merin.org.mm/       # MERIN reports and maps
        ├── themimu.info/       # MIMU maps and analysis
        ├── uec.org.mm/         # Official UEC documents
        │   └── မဲဆန္ဒနယ်/      # Constituency definitions
        └── wiki.links          # External reference links
        ```
        
        #### File Access:
        - All documents are stored locally in the `2020/` directory
        - PDF documents can be accessed for reference and analysis
        - Myanmar language documents use Unicode encoding
        - Geographic data includes coordinate information where available
        """)

def main():
    """Main application function."""
    configure_page()
    add_custom_css()
    
    # Initialize database
    db = get_database()
    
    # Create sidebar
    page, selected_assemblies, selected_regions, electoral_systems, search_term, performance_mode, render_mode, show_township_boundaries, show_state_boundaries, boundary_opacity = create_sidebar(db)
    
    # Create page mapping to handle translations
    page_mappings = {
        get_text("pages.overview"): "overview",
        get_text("pages.map"): "map", 
        get_text("pages.search"): "search",
        get_text("pages.comparison"): "comparison",
        get_text("pages.parties"): "parties",
        get_text("pages.historical"): "historical"
    }
    
    # Get current page type
    current_page_type = page_mappings.get(page, "overview")
    
    # Main content
    if current_page_type == "overview":
        st.title(get_text("app_title"))
        st.markdown(f"*{get_text('app_subtitle')}*")
        
        # Show navigation guide
        show_navigation_guide()
        
        # Get statistics with assembly filtering
        if selected_assemblies:
            # Get filtered constituency data
            df = db.get_constituencies(selected_assemblies)
            
            # Calculate filtered statistics
            stats = {
                'total_constituencies': len(df),
                'total_representatives': df['representatives'].sum() if not df.empty else 0,
                'mapped_constituencies': df['lat'].notna().sum() if not df.empty else 0,
                'assembly_breakdown': []
            }
            
            # Create assembly breakdown from filtered data
            if not df.empty:
                for assembly_type in df['assembly_type'].unique():
                    assembly_data = df[df['assembly_type'] == assembly_type]
                    stats['assembly_breakdown'].append({
                        'assembly_type': assembly_type,
                        'constituencies': len(assembly_data),
                        'total_representatives': assembly_data['representatives'].sum(),
                        'mapped_count': assembly_data['lat'].notna().sum()
                    })
        else:
            # No assemblies selected - show empty stats
            stats = {
                'total_constituencies': 0,
                'total_representatives': 0,
                'mapped_constituencies': 0,
                'assembly_breakdown': []
            }
        
        # Display metrics with assembly filter info
        st.subheader(get_text("overview.metrics_title"))
        if selected_assemblies:
            st.info(f"📊 Showing statistics for: {', '.join(selected_assemblies)}")
        else:
            st.warning("⚠️ No assemblies selected. Please select assemblies from the sidebar.")
        display_assembly_metrics(stats)
        
        # Assembly comparison chart
        st.subheader(get_text("overview.comparison_title"))
        comparison_fig = create_assembly_comparison_chart(stats)
        if comparison_fig:
            st.plotly_chart(comparison_fig, use_container_width=True)
            
        # Assembly breakdown table
        if stats and stats.get('assembly_breakdown'):
            st.subheader(get_text("overview.breakdown_title"))
            breakdown_df = pd.DataFrame(stats['assembly_breakdown'])
            st.dataframe(breakdown_df, use_container_width=True)
    
    elif current_page_type == "map":
        st.title("🗺️ Interactive Multi-Assembly Map")
        
        # Show map usage guide
        with st.expander("🗺️ Map Usage Guide"):
            st.markdown("""
            #### How to Use the Interactive Map
            
            - **Assembly Filter:** Select which assemblies to display (PTHT, AMTHT, TPHT, TPTYT)
            - **Performance Mode:** Choose map rendering speed (Fast/Balanced/Quality)
            - **Zoom & Pan:** Click and drag to explore different regions
            - **Click Markers:** Get detailed constituency information
            - **Responsive Design:** Map automatically scales to your screen size
            
            **Performance Tips:** Use Fast mode for large datasets, Quality mode for detailed analysis.
            """)
        
        if not selected_assemblies:
            st.warning("⚠️ Please select at least one assembly type from the sidebar to view the map")
            return
            
        # Load constituency data
        df = db.get_constituencies(selected_assemblies)
        
        # Apply filters
        if selected_regions and 'state_region_en' in df.columns:
            df = df[df['state_region_en'].isin(selected_regions)]
            
        if electoral_systems and 'electoral_system' in df.columns:
            df = df[df['electoral_system'].isin(electoral_systems)]
        
        # Display map info with better styling
        if not df.empty:
            mapped_count = df['lat'].notna().sum()
            st.markdown(f"""
            <div class="map-info-section">
                <strong>📍 Displaying:</strong> {len(df)} constituencies | 
                <strong>🗺️ Mapped:</strong> {mapped_count}/{len(df)} | 
                <strong>⚡ Mode:</strong> {performance_mode.title()}
            </div>
            """, unsafe_allow_html=True)
        
        # Create and display responsive map
        if not df.empty:
            # Generate map with stable key based on assemblies and data hash
            data_hash = hash(tuple(sorted(selected_assemblies)) + (len(df), performance_mode))
            map_key = f"interactive_map_{data_hash}"
            
            map_obj = create_performance_optimized_map(
                df, 
                selected_assemblies, 
                zoom_level=6, 
                performance_mode=performance_mode,
                show_township_boundaries=show_township_boundaries,
                show_state_boundaries=show_state_boundaries,
                boundary_opacity=boundary_opacity
            )
            
            if map_obj:
                # Use session state to prevent unnecessary re-renders
                if 'current_map_key' not in st.session_state:
                    st.session_state.current_map_key = None
                
                # Only re-render if map parameters changed
                if st.session_state.current_map_key != map_key:
                    st.session_state.current_map_key = map_key
                    st.session_state.rerun_map = True
                
                # Display the map with stable key
                map_data = st_folium(
                    map_obj, 
                    width="100%", 
                    height=500,
                    key=map_key,
                    returned_objects=["last_object_clicked"]
                )
                
                # Show status information below map (static, no dynamic content)
                st.markdown(f"""
                <div class="map-info-section">
                    <p>{get_text("map.status", mode=performance_mode, count=len(df))}</p>
                    <p>{get_text("map.usage")}</p>
                </div>
                """, unsafe_allow_html=True)
        
        # Display constituency table
        if not df.empty:
            st.subheader("📋 Constituency Details")
            display_df = df[['constituency_code', 'constituency_en', 'state_region_en', 
                           'assembly_type', 'electoral_system', 'representatives']].copy()
            st.dataframe(display_df, use_container_width=True)
    
    elif current_page_type == "search":
        st.title("📋 Constituency Search")
        
        # Show search usage guide
        with st.expander("🔍 Search Guide"):
            st.markdown("""
            #### How to Search Constituencies
            
            - **Language Support:** Search in English or Myanmar script
            - **Search Types:** Constituency names, regions, or included areas  
            - **Examples:** Try "Yangon", "Mandalay", or specific constituency names
            - **Partial Matches:** Supported - try short keywords!
            - **Search Fields:** Name, region, areas included, and assembly types
            
            **Pro Tip:** Use region names like "Yangon" or "Shan" to find all constituencies in that area.
            """)
        
        if search_term:
            with st.spinner(f"Searching for '{search_term}'..."):
                results = db.search_constituencies(search_term)
            
            if not results.empty:
                st.success(f"Found {len(results)} constituencies matching '{search_term}'")
                
                # Display results in a more organized way
                st.subheader("Search Results")
                
                # Group by assembly type for better organization
                for assembly_type in results['assembly_type'].unique():
                    assembly_results = results[results['assembly_type'] == assembly_type]
                    
                    st.markdown(f"### {assembly_type} - {len(assembly_results)} constituencies")
                    
                    for _, row in assembly_results.iterrows():
                        with st.expander(f"{row['constituency_en']} - {row['state_region_en']}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown(f"**English:** {row['constituency_en']}")
                                st.markdown(f"**Myanmar:** {row.get('constituency_mm', 'N/A')}")
                                st.markdown(f"**Code:** {row.get('constituency_code', 'N/A')}")
                                
                            with col2:
                                st.markdown(f"**State/Region:** {row['state_region_en']}")
                                st.markdown(f"**Assembly:** {row['assembly_type']}")
                                st.markdown(f"**Electoral System:** {row.get('electoral_system_en', row.get('electoral_system', 'N/A'))}")
                                st.markdown(f"**Representatives:** {row.get('representatives', 1)}")
                                
                                # Show coordinates if available
                                if pd.notna(row.get('lat')) and pd.notna(row.get('lng')):
                                    st.markdown(f"**Location:** {row['lat']:.4f}, {row['lng']:.4f}")
                                    
            else:
                st.warning(f"No constituencies found matching '{search_term}'")
                st.info("💡 **Search Tips:**\n- Try partial names (e.g., 'Yangon' instead of 'Yangon East')\n- Search works in both English and Myanmar\n- You can search by region, township, or constituency name")
        else:
            st.info("👈 Enter a search term in the sidebar to find constituencies")
            
            # Show sample searches
            st.subheader("Sample Searches")
            sample_col1, sample_col2 = st.columns(2)
            
            with sample_col1:
                st.markdown("**Try searching for:**")
                st.markdown("- Yangon")
                st.markdown("- Mandalay") 
                st.markdown("- Shan")
                
            with sample_col2:
                st.markdown("**Or try Myanmar:**")
                st.markdown("- ရန်ကုန်")
                st.markdown("- မန္တလေး")
                st.markdown("- ရှမ်း")
    
    elif current_page_type == "comparison":
        st.title("📈 Assembly Comparison Analysis")
        
        # Show comparison guide
        with st.expander("📈 Analysis Guide"):
            st.markdown("""
            #### Understanding Assembly Comparisons
            
            - **Regional Distribution:** See how constituencies are distributed across states/regions
            - **Assembly Types:** Compare different electoral assemblies (PTHT, AMTHT, TPHT, TPTYT)
            - **Representatives:** Analyze representation patterns across the country
            - **Interactive Charts:** Click and hover for detailed information
            - **Data Analysis:** Use filters in sidebar to focus on specific areas
            
            **Assembly Types:**
            - **PTHT:** Pyithu Hluttaw (Lower House) - 330 constituencies
            - **AMTHT:** Amyotha Hluttaw (Upper House) - 116 constituencies  
            - **TPHT:** State/Regional Assemblies - 360 constituencies
            - **TPTYT:** Ethnic Affairs - 29 constituencies
            - **Total: 835 constituencies across all assemblies**
            """)
        
        # Load all data for comparison
        all_data = db.get_constituencies()
        stats = db.get_assembly_statistics()
        
        if not all_data.empty:
            # Regional distribution by assembly
            st.subheader("🌍 Regional Distribution by Assembly")
            
            regional_dist = all_data.groupby(['state_region_en', 'assembly_type']).size().reset_index(name='count')
            
            colors = get_chart_colors()
            
            fig = px.bar(
                regional_dist, 
                x='state_region_en', 
                y='count',
                color='assembly_type',
                title="Constituencies by State/Region and Assembly",
                labels={'state_region_en': 'State/Region', 'count': 'Number of Constituencies'}
            )
            fig.update_layout(
                xaxis_tickangle=45,
                plot_bgcolor=colors['bg_color'],
                paper_bgcolor=colors['paper_color'],
                font={'color': colors['text_color']},
                title_font_color=colors['text_color'],
                xaxis={'gridcolor': colors['grid_color'], 'color': colors['text_color']},
                yaxis={'gridcolor': colors['grid_color'], 'color': colors['text_color']}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Electoral system breakdown
            st.subheader("🗳️ Electoral System Distribution")
            
            electoral_dist = all_data.groupby(['assembly_type', 'electoral_system']).size().reset_index(name='count')
            
            fig2 = px.pie(
                electoral_dist,
                values='count',
                names='electoral_system',
                facet_col='assembly_type',
                title="Electoral Systems by Assembly"
            )
            fig2.update_layout(
                plot_bgcolor=colors['bg_color'],
                paper_bgcolor=colors['paper_color'],
                font={'color': colors['text_color']},
                title_font_color=colors['text_color']
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    elif current_page_type == "parties":
        create_parties_page()
    
    elif current_page_type == "historical":
        show_historical_data_page()

if __name__ == "__main__":
    main()