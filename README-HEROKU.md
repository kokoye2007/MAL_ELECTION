# Myanmar Election Visualization 2025 - Heroku Deployment

🗳️ **Interactive web application for visualizing Myanmar's 2025 electoral constituencies across all assemblies with bilingual support and historical data.**

## 🚀 Quick Deploy to Heroku

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

## 📋 Prerequisites

- [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) installed
- Heroku account created
- Git repository initialized

## 🎯 Automated Deployment

### Option 1: One-Click Deploy (Recommended)
1. Click the "Deploy to Heroku" button above
2. Fill in the app name and region
3. Click "Deploy app"
4. Wait for deployment to complete

### Option 2: Script-Based Deploy
```bash
# Run the automated deployment script
./deploy-heroku.sh
```

### Option 3: Manual Deploy
```bash
# Create Heroku app
heroku create your-app-name

# Add PostgreSQL addon
heroku addons:create heroku-postgresql:essential-0

# Set environment variables
heroku config:set ENVIRONMENT=production
heroku config:set DEBUG_MODE=false
heroku config:set ENABLE_CACHING=true

# Deploy code
git push heroku heroku-deploy:main

# Initialize database
heroku run python database/init_heroku_db.py
```

## 🏗️ Architecture

### **Stack Components**
- **Frontend**: Streamlit web framework
- **Backend**: Python with PostgreSQL database
- **Maps**: Folium with interactive visualization
- **Charts**: Plotly for statistical analysis
- **Deployment**: Heroku with PostgreSQL addon

### **Key Features**
- 📊 **Multi-Assembly Support**: All 4 Myanmar assemblies (PTHT, AMTHT, TPHT, TPTYT)
- 🗺️ **Interactive Maps**: Zoom-adaptive rendering with 835+ constituencies
- 🌐 **Bilingual Interface**: English and Myanmar language support
- 📜 **Historical Data**: 2020 election documents and references
- ⬇️ **Document Downloads**: Direct access to official election materials

## 🔧 Configuration

### **Environment Variables**
```bash
ENVIRONMENT=production
DEBUG_MODE=false
ENABLE_CACHING=true
DEFAULT_MAP_PROVIDER=cartodb
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
```

### **Database Schema**
- `constituencies`: 2025 election data (835 constituencies)
- `historical_constituencies`: 2020 historical data
- `cached_statistics`: Performance optimization cache

### **File Structure**
```
myanmar-election-viz/
├── src/
│   ├── app_enhanced.py          # Main Streamlit application
│   ├── database.py              # PostgreSQL connector
│   └── languages.json           # Bilingual translations
├── 2020/                        # Historical documents
│   ├── idea.int/               # IDEA reports
│   ├── merin.org.mm/           # MERIN analysis
│   ├── themimu.info/           # MIMU maps
│   └── uec.org.mm/             # UEC documents
├── database/
│   └── init_heroku_db.py       # Database initialization
├── Procfile                    # Heroku process definition
├── requirements.txt            # Python dependencies
└── app.json                    # Heroku app metadata
```

## 📊 Performance Optimization

### **Caching Strategy**
- 5-minute TTL for database queries
- Streamlit native caching for expensive operations
- Session state management for user preferences

### **Map Optimization**
- Zoom-adaptive rendering (heatmap → cluster → individual)
- Performance modes: fast, balanced, quality
- Lazy loading for large datasets

### **Resource Management**
- Essential-0 PostgreSQL plan (10,000 rows, 20 connections)
- Basic dyno tier (512MB RAM, 1x CPU)
- Automatic scaling based on traffic

## 🗄️ Database Management

### **Sample Data**
The deployment includes sample constituency data for immediate testing.

### **Data Migration**
```bash
# Check database status
heroku pg:info

# Run database shell
heroku pg:psql

# View constituency count
heroku run python -c "
from src.database import get_database
db = get_database()
print(f'Total constituencies: {len(db.get_constituencies())}')
"
```

### **Backup & Restore**
```bash
# Create backup
heroku pg:backups:capture

# Download backup
heroku pg:backups:download

# Restore from backup
heroku pg:backups:restore b001
```

## 🔍 Monitoring & Debugging

### **Application Logs**
```bash
# View real-time logs
heroku logs --tail

# Filter Streamlit logs
heroku logs --tail --source app

# View specific log lines
heroku logs --num 500
```

### **Database Monitoring**
```bash
# Check database stats
heroku pg:info

# Monitor active connections
heroku pg:diagnose

# View slow queries
heroku pg:outliers
```

### **Performance Metrics**
```bash
# View app metrics
heroku apps:info

# Check dyno usage
heroku ps

# Scale dynos if needed
heroku ps:scale web=1
```

## 🔒 Security & Compliance

### **Data Protection**
- Environment variables for sensitive configuration
- PostgreSQL with SSL encryption
- No sensitive data in code repository
- Secure file handling for document downloads

### **Access Control**
- Heroku app-level access management
- Database connection pooling with limits
- Rate limiting for API endpoints

## 🆙 Scaling & Updates

### **Vertical Scaling**
```bash
# Upgrade to Standard-1X dyno
heroku ps:resize web=standard-1x

# Upgrade database plan
heroku addons:upgrade heroku-postgresql:standard-0
```

### **Application Updates**
```bash
# Deploy updates
git push heroku heroku-deploy:main

# Restart dynos
heroku restart

# Check deployment status
heroku releases
```

## 🎨 Customization

### **Themes**
- Light/Dark mode toggle
- Myanmar cultural color scheme
- Responsive design for mobile devices

### **Languages**
- English/Myanmar bilingual support
- Unicode Myanmar text rendering
- Cultural sensitivity in terminology

### **Data Sources**
- Official UEC constituency definitions
- MIMU geographic boundary data
- Historical 2020 election references

## 🔗 External Dependencies

- **Mapbox**: Optional enhanced mapping (requires API key)
- **PostgreSQL**: Required database (included with addon)
- **GitHub**: Source code repository
- **Heroku**: Platform-as-a-Service hosting

## 📈 Usage Analytics

The application includes optional usage analytics:
- Page view tracking
- Feature usage statistics  
- Performance monitoring
- Error logging

## 🆘 Support & Troubleshooting

### **Common Issues**

**Database Connection Errors**
```bash
# Check DATABASE_URL
heroku config:get DATABASE_URL

# Restart database connections
heroku restart
```

**Memory Limit Exceeded**
```bash
# Check memory usage
heroku logs --tail | grep "R14"

# Upgrade dyno tier
heroku ps:resize web=standard-1x
```

**Build Failures**
```bash
# Check buildpack
heroku buildpacks

# Clear build cache
heroku plugins:install heroku-builds
heroku builds:cache:purge
```

## 👨‍💻 Development Team

- **Clean Text | Nyi Lynn Seck** - System design, development & implementation
- **Data Sources**: UEC, MIMU, MERIN, IDEA
- **Geographic Data**: Myanmar Information Management Unit
- **Historical Research**: Multiple election monitoring organizations

## 📄 License

This project uses data from multiple sources with appropriate attribution:
- **Creative Commons Attribution 4.0** for application code
- **UEC Official Data** with proper attribution
- **MIMU Geographic Data** under academic use terms
- **Historical Documents** remain property of original organizations

---

**📱 Live Application**: https://your-app-name.herokuapp.com  
**📊 Status Page**: https://status.heroku.com  
**📚 Documentation**: https://devcenter.heroku.com