# Deployment Guide - Myanmar Election Data Visualization

## Overview

This guide covers deploying the Myanmar Election Data Visualization platform across different environments, from local development to production deployment on Streamlit Cloud.

## Local Development Setup

### Prerequisites
- Python 3.8 or higher
- Git
- 4GB+ RAM (for processing large datasets)
- Internet connection (for map tiles and dependencies)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd myanmar-election-viz
   ```

2. **Create virtual environment**
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

4. **Process data** (if not already done)
   ```bash
   python src/data_processor.py
   ```

5. **Run application**
   ```bash
   streamlit run src/app.py
   ```

6. **Access application**
   - Open browser to `http://localhost:8501`
   - The application should load with the overview page

### Development Workflow

```bash
# Activate environment
source myanmar-election-env/bin/activate

# Run with auto-reload
streamlit run src/app.py --server.runOnSave true

# Run on custom port
streamlit run src/app.py --server.port 8502

# Run with debug mode
streamlit run src/app.py --logger.level debug
```

## Streamlit Cloud Deployment

### Preparation Steps

1. **Prepare repository**
   ```bash
   # Ensure all files are committed
   git add .
   git commit -m "Prepare for Streamlit Cloud deployment"
   git push origin main
   ```

2. **Verify file structure**
   ```
   myanmar-election-viz/
   ├── src/
   │   ├── app.py              # Main Streamlit app
   │   ├── visualizations.py   # Visualization components  
   │   ├── data_processor.py   # Data processing
   │   └── config.py          # Configuration
   ├── data/
   │   ├── processed/         # Processed JSON/CSV files
   │   └── geojson/          # Geographic boundary data
   ├── requirements.txt       # Python dependencies
   └── README.md
   ```

### Streamlit Cloud Setup

1. **Access Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub account

2. **Create new app**
   - Click "New app"
   - Select your repository
   - Set main file path: `src/app.py`
   - Choose branch: `main`

3. **Configure advanced settings**
   ```toml
   # .streamlit/config.toml (optional)
   [theme]
   primaryColor = "#1e3a8a"
   backgroundColor = "#ffffff"
   secondaryBackgroundColor = "#f0f2f6"
   textColor = "#262730"
   font = "sans serif"
   
   [server]
   maxUploadSize = 200
   maxMessageSize = 200
   enableCORS = false
   enableXsrfProtection = true
   ```

4. **Environment variables** (if needed)
   - No special environment variables required for basic deployment
   - Add any API keys or secrets through Streamlit Cloud interface

5. **Deploy**
   - Click "Deploy" 
   - Monitor deployment logs for any issues
   - App will be available at `https://share.streamlit.io/[username]/[repo-name]/main/src/app.py`

### Deployment Checklist

- [ ] All code committed and pushed to GitHub
- [ ] `requirements.txt` includes all dependencies
- [ ] Data files are included in repository (processed JSON/CSV)
- [ ] No hardcoded file paths (use relative paths)
- [ ] Error handling for missing files
- [ ] File sizes under GitHub limits (100MB per file)
- [ ] No sensitive data or API keys in code

## Alternative Deployment Options

### Heroku Deployment

1. **Create Heroku app**
   ```bash
   heroku create myanmar-election-viz
   ```

2. **Add buildpack**
   ```bash
   heroku buildpacks:add heroku/python
   ```

3. **Create Procfile**
   ```
   web: sh setup.sh && streamlit run src/app.py --server.port=$PORT --server.address=0.0.0.0
   ```

4. **Create setup.sh**
   ```bash
   mkdir -p ~/.streamlit/
   echo "\
   [server]\n\
   headless = true\n\
   port = $PORT\n\
   enableCORS = false\n\
   \n\
   " > ~/.streamlit/config.toml
   ```

5. **Deploy**
   ```bash
   git push heroku main
   ```

### Docker Deployment

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.9-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY . .
   
   EXPOSE 8501
   
   HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
   
   ENTRYPOINT ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
   ```

2. **Build and run**
   ```bash
   docker build -t myanmar-election-viz .
   docker run -p 8501:8501 myanmar-election-viz
   ```

### AWS/GCP/Azure Deployment

For cloud deployment, consider:
- **AWS**: Elastic Beanstalk or ECS
- **GCP**: Cloud Run or App Engine
- **Azure**: Container Instances or App Service

## Performance Optimization

### Data Optimization
- Compress large JSON files with gzip
- Use parquet format for large datasets
- Implement data caching with `@st.cache_data`

### Streamlit Optimization
```python
import streamlit as st

# Cache data loading
@st.cache_data
def load_data():
    return pd.read_json("data/processed/myanmar_constituencies.json")

# Cache expensive computations
@st.cache_data
def create_visualization(data):
    return create_complex_chart(data)
```

### Map Performance
- Use simplified GeoJSON boundaries
- Implement map clustering for large datasets
- Cache map tiles locally if possible

## Monitoring and Maintenance

### Health Checks
```python
# Add to app.py
def health_check():
    """Basic health check for monitoring."""
    try:
        # Check data availability
        assert Path("data/processed/myanmar_constituencies.json").exists()
        return {"status": "healthy", "timestamp": pd.Timestamp.now()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Logging
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
```

### Analytics
Consider adding:
- Google Analytics for usage tracking
- Error tracking with Sentry
- Performance monitoring with New Relic

## Troubleshooting

### Common Issues

1. **Memory errors**
   - Reduce data file sizes
   - Implement data pagination
   - Use more efficient data structures

2. **Slow loading**
   - Add loading spinners
   - Implement progressive data loading
   - Cache expensive operations

3. **Map not loading**
   - Check internet connectivity
   - Verify GeoJSON file structure
   - Use fallback map tiles

4. **Myanmar fonts not rendering**
   - Ensure font files are accessible
   - Add font fallbacks in CSS
   - Test on different browsers

### Debugging Commands
```bash
# Check Streamlit installation
streamlit version

# Run with debug logging
streamlit run src/app.py --logger.level debug

# Check memory usage
python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"

# Validate data files
python src/data_processor.py --validate-only
```

### Support Resources
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Streamlit Community Forum](https://discuss.streamlit.io/)
- [Myanmar Unicode Guide](https://www.unicode.org/charts/PDF/U1000.pdf)
- [Folium Documentation](https://python-visualization.github.io/folium/)

## Security Considerations

### Data Protection
- No sensitive personal data in public repository
- Use environment variables for API keys
- Implement rate limiting if needed
- Regular security updates for dependencies

### Access Control
- Consider authentication for internal use
- Implement role-based access if needed
- Use HTTPS in production
- Monitor for unusual usage patterns

## Future Enhancements

### Planned Improvements
- React frontend migration
- Real-time data updates
- Enhanced mobile experience
- Multi-language support expansion
- API endpoint development

### Scaling Considerations
- Database backend for large datasets
- CDN for static assets
- Load balancing for high traffic
- Microservices architecture

---

**Note**: This deployment guide assumes familiarity with basic web deployment concepts. For production deployments, consult with a systems administrator or DevOps engineer for security and performance optimization.