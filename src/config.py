#!/usr/bin/env python3
"""
Configuration settings for Myanmar Election Data Visualization
"""

from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
RAW_DATA_DIR = DATA_DIR / "raw"
GEOJSON_DIR = DATA_DIR / "geojson"

# Data files
CONSTITUENCIES_JSON = PROCESSED_DATA_DIR / "myanmar_constituencies.json"
CONSTITUENCIES_CSV = PROCESSED_DATA_DIR / "myanmar_constituencies.csv"
STATISTICS_JSON = PROCESSED_DATA_DIR / "summary_statistics.json"

# Streamlit configuration
STREAMLIT_CONFIG = {
    "page_title": "Myanmar Election Data Visualization",
    "page_icon": "🗳️",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Myanmar language settings
MYANMAR_FONTS = ["Padauk", "Pyidaungsu", "Myanmar Text"]

# Map settings
MAP_CENTER = {
    "lat": 21.9162,
    "lng": 95.9560
}
MAP_ZOOM = 6

# Color schemes
COLORS = {
    "primary": "#1e3a8a",
    "secondary": "#3b82f6", 
    "accent": "#0d9488",
    "success": "#10b981",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "neutral": "#6b7280"
}

# Chart themes
CHART_THEME = "plotly_white"

# Assembly information
ASSEMBLIES = {
    "pyithu": {
        "name_en": "Pyithu Hluttaw",
        "name_mm": "ပြည်သူ့လွှတ်တော်",
        "seats": 330,
        "description": "House of Representatives (Lower House)"
    },
    "amyotha": {
        "name_en": "Amyotha Hluttaw", 
        "name_mm": "အမျိုးသားလွှတ်တော်",
        "seats": 110,
        "description": "House of Nationalities (Upper House)"
    },
    "state_regional": {
        "name_en": "State/Regional Assemblies",
        "name_mm": "တိုင်း/ပြည်နယ်လွှတ်တော်များ",
        "seats": 398,
        "description": "Local legislative assemblies"
    }
}

# Data validation rules
VALIDATION_RULES = {
    "max_constituencies_per_region": 50,
    "min_constituencies_per_region": 1,
    "representatives_per_constituency": 1,
    "required_fields": ["id", "state_region_mm", "constituency_mm", "representatives"]
}