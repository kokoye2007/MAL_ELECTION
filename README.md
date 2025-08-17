# Myanmar Election Data Visualization

A comprehensive data visualization platform for Myanmar's 2025 electoral system, featuring interactive maps, statistical charts, and bilingual support.

## Overview

This project visualizes Myanmar's electoral constituencies across three levels of government:
- **Pyithu Hluttaw** (Lower House): 330 constituencies
- **Amyotha Hluttaw** (Upper House): 110 constituencies  
- **State/Regional Assemblies**: 398+ constituencies

## Features

### Phase 1: Python MVP (Current)
- 📊 Statistical charts (parliament composition, regional distribution)
- 🗺️ Interactive maps with constituency boundaries
- 🔍 Search and filter functionality
- 📱 Responsive design for mobile devices

### Phase 2: React Platform (Planned)
- 🎨 Enhanced interactive visualizations with D3.js
- 🌐 Bilingual support (Myanmar/English)
- 📤 Export functionality (PDF, PNG, SVG)
- ♿ Full accessibility compliance

## Tech Stack

### Current (Python MVP)
- **Framework**: Streamlit
- **Visualization**: Plotly, Folium
- **Data Processing**: Pandas, GeoPandas
- **Deployment**: Streamlit Cloud

### Future (React Platform)
- **Frontend**: React + TypeScript
- **Visualization**: D3.js, Leaflet, Recharts
- **Styling**: Tailwind CSS
- **Deployment**: Vercel

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