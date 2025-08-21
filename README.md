# Myanmar Election Data Visualization

A comprehensive data visualization platform for Myanmar's 2025 electoral system, featuring interactive maps, statistical charts, and bilingual support.

## Overview

This project visualizes Myanmar's 2025 electoral constituencies with authentic data from the Myanmar Election Commission:
- **Pyithu Hluttaw** (Lower House): 330 constituencies (real official data)
- **Geographic Coverage**: 100% mapping coverage with verified coordinates
- **Data Integrity**: Only verified, official constituency data (no synthetic data)

## Features

### Current Features
- 📊 **Statistical Dashboard**: Real-time constituency statistics and regional distribution
- 🗺️ **Interactive Maps**: Zoom-adaptive rendering with constituency pin points
- 🏛️ **Assembly Selection**: Prominent sidebar dropdown with real-time filtering
- 🔍 **Search Functionality**: Find constituencies by name or region
- 🌐 **Bilingual Support**: Myanmar/English language switching
- 📱 **Responsive Design**: Mobile-optimized interface
- 🐳 **Docker Deployment**: Full containerization for development and production
- ☁️ **Heroku Integration**: Production deployment with PostgreSQL database

## Tech Stack

### Technology Stack
- **Framework**: Streamlit (Enhanced Multi-page Application)
- **Database**: PostgreSQL with PostGIS (local + Heroku)
- **Visualization**: Plotly (charts), Folium (interactive maps)
- **Data Processing**: Pandas, GeoPandas
- **Containerization**: Docker + Docker Compose
- **Production**: Heroku with release phase database initialization
- **Development**: Local Docker environment with data persistence

## Quick Start

### Production Application
Visit the live application: **[myanmar-election-2025-df34bedd7e69.herokuapp.com](https://myanmar-election-2025-df34bedd7e69.herokuapp.com)**

### Local Development
```bash
# 1. Clone the repository
git clone [repository-url]
cd myanmar-election-viz

# 2. Start Docker environment
docker-compose up -d postgres myanmar-election-viz

# 3. Load clean data (if needed)
source venv/bin/activate
DATABASE_URL='postgresql://election_user:election_pass_2025@localhost:5432/myanmar_election' python database/load_clean_data.py

# 4. Access application
open http://localhost:8501
```

### Current Data Status
- **Total Constituencies**: 330 (all PTHT - Pyithu Hluttaw)
- **Assembly Selection**: Default shows PTHT only (real data available)
- **Mapping Coverage**: 100% with verified coordinates
- **Data Source**: Official Myanmar Election Commission CSV

## Data Structure

The project processes Myanmar electoral data with the following structure:

```json
{
  "constituencies": [
    {
      "id": "number",
      "state_region_mm": "string (Myanmar)",
      "state_region_en": "string (English)",
      "constituency_mm": "string (Myanmar)",
      "constituency_en": "string (English)",
      "assembly_type": "pyithu|amyotha|state_regional",
      "areas_included": "string",
      "representatives": "number",
      "electoral_system": "FPTP"
    }
  ]
}
```

## Quick Start

### Prerequisites
- Python 3.8+
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd myanmar-election-viz
   ```

2. **Set up virtual environment**
   ```bash
   python3 -m venv myanmar-election-env
   source myanmar-election-env/bin/activate  # Linux/Mac
   # or
   myanmar-election-env\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   streamlit run src/app.py
   ```

## Project Structure

```
myanmar-election-viz/
├── README.md
├── requirements.txt
├── src/
│   ├── app.py                 # Main Streamlit application
│   ├── data_processor.py      # Data cleaning and processing
│   ├── visualizations.py     # Chart and map components
│   └── config.py             # Configuration settings
├── data/
│   ├── raw/                  # Original Excel files
│   ├── processed/            # Cleaned JSON/CSV files
│   └── geojson/             # Myanmar geographic boundaries
├── assets/
│   ├── fonts/               # Myanmar fonts (Padauk, Pyidaungsu)
│   └── images/              # Static images and icons
├── docs/
│   ├── DATA_DICTIONARY.md   # Data field descriptions
│   ├── DEPLOYMENT.md        # Deployment instructions
│   └── CULTURAL_GUIDE.md    # Myanmar cultural considerations
└── tests/
    ├── test_data_processor.py
    └── test_visualizations.py
```

## Development Roadmap

### Week 1-3: Python MVP ✅
- [x] Data analysis and cleaning pipeline
- [x] Basic statistical visualizations
- [x] Interactive maps with Folium
- [x] Streamlit web interface
- [x] Search and filter functionality

### Week 4-6: React Platform
- [ ] React + TypeScript setup
- [ ] D3.js interactive visualizations
- [ ] Leaflet map integration
- [ ] Component-based architecture

### Week 7-8: Enhancement & Deployment
- [ ] Bilingual implementation (Myanmar/English)
- [ ] Accessibility features (WCAG 2.1 AA)
- [ ] Export functionality
- [ ] Production deployment
- [ ] Performance optimization

## Cultural Considerations

### Typography
- **Myanmar Fonts**: Padauk, Pyidaungsu for proper Unicode rendering
- **Bilingual Support**: Seamless toggle between Myanmar and English
- **Text Direction**: Proper handling of Myanmar script rendering

### Design Principles
- **Political Neutrality**: Non-partisan color schemes and terminology
- **Cultural Sensitivity**: Appropriate use of Myanmar flag colors (yellow, green, red)
- **Accessibility**: Colorblind-friendly palettes and screen reader support

## Data Sources

- **Electoral Data**: Myanmar Election Commission constituency plans
- **Geographic Boundaries**: GADM database for Myanmar administrative boundaries
- **Cultural References**: Native Myanmar speaker consultation for accuracy

## Contributing

### Code Standards
- **Python**: Follow PEP 8 guidelines
- **React**: ESLint + Prettier configuration
- **Commits**: Conventional commit format
- **Testing**: Minimum 80% code coverage

### Cultural Guidelines
- Ensure political neutrality in all content
- Verify Myanmar language accuracy with native speakers
- Test accessibility with screen readers
- Validate mobile responsiveness on various devices

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Myanmar Election Commission for electoral data
- GADM project for geographic boundaries
- Myanmar Unicode community for font resources
- Contributors to open-source mapping libraries

## Support

For questions or support, please:
- Open an issue on GitHub
- Contact the development team
- Refer to the documentation in `/docs`

---

**Note**: This project aims to provide factual, non-partisan visualization of Myanmar's electoral system for educational and civic engagement purposes.