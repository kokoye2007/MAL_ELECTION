# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Installation
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run src/app.py
```

### Development Workflow
```bash
# Run with specific port
streamlit run src/app.py --server.port 8502

# Run in headless mode for testing
streamlit run src/app.py --server.headless true --server.port 8502

# Check for linting issues
black src/
flake8 src/

# Run tests
pytest tests/
```

### Data Processing
```bash
# Process raw election data (if needed)
python src/data_processor.py

# Test basic functionality
python test_changes.py
python test_app_integration.py
```

## Architecture Overview

### Core Application Structure
The project is a **Streamlit-based web application** for visualizing Myanmar's 2025 electoral constituencies with **bilingual support** (English/Myanmar). The architecture follows a modular design:

**src/app.py** - Main Streamlit application with multiple pages:
- Overview page with statistical charts
- Interactive map page with zoom-adaptive rendering
- Constituency search and directory
- Detailed analysis page

**src/visualizations.py** - Core visualization engine (MyanmarElectionVisualizer class):
- Interactive Folium maps with multiple rendering modes (heat_map, clustered, individual, regional_counts)
- Zoom-adaptive map rendering that automatically switches visualization modes based on zoom level
- Area-based visualization (not point markers) - constituencies are displayed as semi-transparent circles representing township/town areas
- Plotly statistical charts (parliament composition, regional distribution)
- PDF report generation with ReportLab

**src/data_processor.py** - Data cleaning and processing pipeline:
- Processes raw Excel files from Myanmar Election Commission
- Handles Myanmar/English bilingual data mapping
- Normalizes state/region names across languages
- Outputs structured JSON/CSV data

**src/config.py** - Centralized configuration:
- File paths for data directories (raw, processed, geojson)
- Map settings and API configurations
- Myanmar language fonts and cultural settings
- Assembly information (Pyithu Hluttaw, Amyotha Hluttaw, State/Regional)

### Translation System
The application implements an **offline translation system** that doesn't require API calls:
- Static translation dictionaries for electoral terminology
- Myanmar language support with proper Unicode rendering
- Cached translations for performance
- No external API dependencies (removed Gemini API dependency)

### Map Visualization Approach
**Key architectural decision**: Maps display **constituency pin point locations**:
- Uses `folium.CircleMarker` for precise constituency location markers
- Each constituency represented by a circular pin point at its geographic center
- Color-coded by state/region for easy visual grouping
- Two marker sizes: 8px radius for detailed individual view, 6px for clustered view
- Interactive popups provide detailed constituency information on click
- Clean, fast rendering suitable for all zoom levels
- Zoom-adaptive rendering automatically selects appropriate visualization mode

### Data Flow
1. **Raw Data**: Excel files from Myanmar Election Commission in `data/raw/`
2. **Processing**: MyanmarElectionDataProcessor cleans and normalizes data
3. **Structured Data**: JSON/CSV outputs in `data/processed/`
4. **Visualization**: MyanmarElectionVisualizer creates interactive components
5. **Web Interface**: Streamlit app presents data with bilingual support

### Key Dependencies and Integration Points
- **Streamlit + streamlit-folium**: Core web framework with map integration
- **Folium + plugins**: Interactive mapping (HeatMap, MarkerCluster)
- **Plotly**: Statistical chart generation
- **Pandas + GeoPandas**: Data processing and geographic operations
- **ReportLab**: PDF export functionality

### Error Handling Architecture
- Graceful degradation for missing API keys
- Fallback map creation for JavaScript errors
- Comprehensive error logging in data processing
- User-friendly error messages in Streamlit interface

### Performance Optimizations
- Zoom-adaptive rendering reduces processing load
- Data caching for frequently accessed information
- Simplified map configurations to avoid JavaScript errors
- Background processing for PDF generation

### Cultural and Political Considerations
- **Political neutrality**: Non-partisan color schemes and terminology
- **Myanmar Unicode**: Proper handling of Myanmar script with Padauk/Pyidaungsu fonts
- **Bilingual interface**: Seamless switching between English and Myanmar languages
- **Cultural sensitivity**: Appropriate use of Myanmar national colors (yellow, green, red)
- **Credits**: NLS (National Language Services) for translations, Clean Text for data processing, MIMU for boundary data

## Important Implementation Notes

### Map Rendering
- Use `folium.CircleMarker` for constituency pin point visualization
- Pin points are positioned at constituency geographic centers (lat/lng coordinates)
- Two marker sizes: 8px radius for individual view, 6px for clustered view
- Color coding by state/region using `_get_region_color()` method
- Interactive popups show constituency details including name, state, representatives, and areas
- HeatMap plugin should be avoided due to JavaScript compatibility issues
- Always test map rendering after changes to avoid missing maps

### Translation System
- All translations are handled offline via static dictionaries
- No API calls required for translation functionality
- Cache is maintained in `data/processed/translations_cache.json`

### Data Processing
- Myanmar state/region names require careful mapping between Myanmar and English
- Excel source data has specific column structure that must be maintained
- Geographic coordinates are essential for map functionality

### Development Principles
- Maintain bilingual support throughout all features
- Ensure cultural sensitivity in design and content
- Test accessibility with various screen readers
- Validate mobile responsiveness across devices
- Follow political neutrality in all visualizations