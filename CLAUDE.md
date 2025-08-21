# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Installation
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application (main enhanced version)
streamlit run src/app_enhanced.py

# Run Docker environment (recommended)
docker-compose up -d postgres myanmar-election-viz
```

### Development Workflow
```bash
# Run with specific port
streamlit run src/app_enhanced.py --server.port 8502

# Run in headless mode for testing
streamlit run src/app_enhanced.py --server.headless true --server.port 8502

# Docker development workflow
docker-compose up -d  # Start all services
docker-compose down   # Stop all services
docker-compose logs -f myanmar-election-viz  # View app logs

# Check for linting issues
black src/
flake8 src/

# Run tests
pytest tests/
```

### Database Management
```bash
# Load clean real constituency data (330 PTHT constituencies)
python database/load_clean_data.py

# Initialize Heroku database
python database/init_heroku_db.py

# Test assembly filtering functionality
python test_assembly_fix.py

# Check database contents
docker exec myanmar-election-db psql -U election_user -d myanmar_election -c "SELECT assembly_type, COUNT(*) FROM constituencies WHERE election_year = 2025 GROUP BY assembly_type;"
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

**src/app_enhanced.py** - Main Streamlit application with multiple pages:
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

**src/database.py** - Database connectivity and operations:
- PostgreSQL connection management for both local and Heroku
- Assembly filtering functionality
- Statistical analysis and data aggregation
- Caching for performance optimization

### Database Architecture

**Current Data Status (2025)**:
- **Real Constituencies**: 330 PTHT (Pyithu Hluttaw) constituencies from official Myanmar Election Commission data
- **Data Source**: `data/processed/myanmar_constituencies.csv` (derived from official Excel files)
- **Geographic Coverage**: 100% mapping coverage with verified coordinates
- **Assembly Types**: Only PTHT available (real data), other assemblies require official data sources

**Database Scripts**:
- **`database/load_clean_data.py`**: Loads only real constituency data (330 PTHT)
- **`database/init_heroku_db.py`**: Heroku database initialization with clean data
- **`database/load_real_data.py`**: Legacy script (includes synthetic data generation)

**Key Database Tables**:
```sql
constituencies (
    id SERIAL PRIMARY KEY,
    constituency_code VARCHAR(20),
    constituency_en VARCHAR(255),
    constituency_mm VARCHAR(255),
    state_region_en VARCHAR(100),
    state_region_mm VARCHAR(100),
    assembly_type VARCHAR(10), -- PTHT, AMTHT, TPHT, TPTYT
    representatives INTEGER,
    lat DECIMAL(10, 8),
    lng DECIMAL(11, 8),
    election_year INTEGER DEFAULT 2025
);
```

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

### Assembly Selection System
**IMPORTANT**: The Assembly Selection dropdown has been completely restructured for better UX:

**Location**: Prominent sidebar position (lines 1026-1052 in `src/app_enhanced.py`)
```python
# Assembly Selection is now prominently displayed in sidebar
selected_assemblies = st.sidebar.multiselect(
    "Assemblies to Display",
    options=list(assembly_options.keys()),
    default=["PTHT"],  # Only real data available
    format_func=lambda x: assembly_options[x],
    help="Select one or more assemblies to view their constituencies"
)
```

**Key Features**:
- **Real-time Filtering**: Overview page respects assembly selection (lines 1851-1889)
- **Constituency Counter**: Shows selected constituency count in sidebar
- **Default Selection**: PTHT only (real data available)
- **User Feedback**: Immediate visual feedback when selections change

**Testing**: Use `test_assembly_fix.py` to verify assembly filtering works correctly.

### Data Processing
- Myanmar state/region names require careful mapping between Myanmar and English
- Excel source data has specific column structure that must be maintained
- Geographic coordinates are essential for map functionality
- **Data Integrity**: Only use real constituency data from official sources

### Development Principles
- Maintain bilingual support throughout all features
- Ensure cultural sensitivity in design and content
- Test accessibility with various screen readers
- Validate mobile responsiveness across devices
- Follow political neutrality in all visualizations
- **Data Authenticity**: Only use verified, official Myanmar Election Commission data

## Deployment

### Heroku Production Environment
- **URL**: `myanmar-election-2025-df34bedd7e69.herokuapp.com`
- **Database**: PostgreSQL with 330 real constituencies
- **Auto-deployment**: Via `heroku-deploy` branch
- **Release Command**: `python database/init_heroku_db.py` (ensures clean data)

### Local Development Environment  
- **Requirements**: Docker and Docker Compose
- **Database**: PostgreSQL container with same schema as production
- **Port**: Application runs on `localhost:8501`
- **Data Sync**: Use `load_clean_data.py` to match production data

### Deployment Commands
```bash
# Deploy to Heroku
git push heroku heroku-deploy:main

# Check Heroku status
heroku ps
heroku logs --tail

# Local environment
docker-compose up -d postgres myanmar-election-viz
```

### Data Consistency Verification
Both environments should show identical statistics:
- **Total Constituencies**: 330
- **Assembly Type**: PTHT only  
- **Mapping Coverage**: 100%
- **Representatives**: 330