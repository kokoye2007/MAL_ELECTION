#!/usr/bin/env python3
"""
Configuration settings for Myanmar Election Data Visualization
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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

# API Configuration
API_KEYS = {
    "TOMTOM_API_KEY": os.getenv("TOMTOM_API_KEY"),
    "MAPBOX_API_KEY": os.getenv("MAPBOX_API_KEY"), 
    "HERE_API_KEY": os.getenv("HERE_API_KEY")
}

# Map Configuration from Environment
MAP_CONFIG = {
    "DEFAULT_ZOOM_LEVEL": int(os.getenv("DEFAULT_ZOOM_LEVEL", "6")),
    "DEFAULT_MAP_PROVIDER": os.getenv("DEFAULT_MAP_PROVIDER", "auto"),
    "HEAT_MAP_RADIUS": int(os.getenv("HEAT_MAP_RADIUS", "20")),
    "HEAT_MAP_BLUR": int(os.getenv("HEAT_MAP_BLUR", "10")),
    "HEAT_MAP_MIN_OPACITY": float(os.getenv("HEAT_MAP_MIN_OPACITY", "0.15")),
    "HEAT_MAP_INTENSITY_SCALE": float(os.getenv("HEAT_MAP_INTENSITY_SCALE", "0.8")),
    "CUSTOM_MAP_SERVER_URL": os.getenv("CUSTOM_MAP_SERVER_URL")
}

# Application Settings
APP_CONFIG = {
    "DEBUG_MODE": os.getenv("DEBUG_MODE", "false").lower() == "true",
    "ENABLE_PERFORMANCE_MONITORING": os.getenv("ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true",
    "ENABLE_CACHING": os.getenv("ENABLE_CACHING", "true").lower() == "true",
    "CACHE_TTL_SECONDS": int(os.getenv("CACHE_TTL_SECONDS", "3600"))
}

def get_api_key(service: str) -> str:
    """Get API key for a specific service with validation."""
    key = API_KEYS.get(f"{service.upper()}_API_KEY")
    if not key:
        print(f"Warning: {service} API key not found in environment variables")
    return key

def has_api_key(service: str) -> bool:
    """Check if API key is available for a service."""
    return bool(API_KEYS.get(f"{service.upper()}_API_KEY"))