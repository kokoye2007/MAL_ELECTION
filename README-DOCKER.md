# Docker Migration Guide

This guide covers migrating from the current CSV-based Streamlit setup to a containerized Docker architecture with PostgreSQL database.

## Overview

**Current Setup:**
- Streamlit app reading CSV files directly
- 330 Pyithu Hluttaw constituencies
- Local file-based data storage

**New Docker Setup:**
- Containerized Streamlit application
- PostgreSQL database with PostGIS for geographic data
- Redis caching for performance
- Nginx reverse proxy for production
- Scalable architecture for 765 constituencies

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │   Streamlit     │    │   PostgreSQL    │
│   (Port 80)     │────│   (Port 8501)   │────│   (Port 5432)   │
│  Reverse Proxy  │    │      App        │    │    Database     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │     Redis       │
                       │   (Port 6379)   │
                       │     Cache       │
                       └─────────────────┘
```

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- Current Myanmar election data in `data/processed/`

### 2. Automated Setup

```bash
# Run the setup script
./scripts/docker-setup.sh
```

This script will:
- Check Docker installation
- Create environment configuration
- Build and start containers
- Migrate CSV data to PostgreSQL
- Verify everything is working

### 3. Manual Setup (Alternative)

If you prefer manual setup:

```bash
# 1. Create environment file
cp .env.example .env
# Edit .env with your settings

# 2. Build and start containers
docker-compose up -d

# 3. Run data migration
docker-compose exec myanmar-election-app python database/migrate_csv_to_db.py
```

## Services

### Myanmar Election App
- **URL**: http://localhost:8501
- **Purpose**: Main Streamlit visualization application
- **Features**: Interactive maps, charts, search, PDF export

### PostgreSQL Database
- **Port**: 5432
- **Database**: myanmar_election
- **User**: election_user
- **Features**: PostGIS for geographic data, optimized indexes

### Redis Cache
- **Port**: 6379
- **Purpose**: Application caching for better performance
- **Configuration**: 256MB memory limit, LRU eviction

### Nginx Proxy
- **Port**: 80
- **Purpose**: Production-ready reverse proxy
- **Features**: Gzip compression, security headers, health checks

## Data Migration

The migration process converts your CSV data to PostgreSQL:

### What Gets Migrated

1. **Constituency Data**
   - All 330 current constituencies
   - Geographic coordinates (lat/lng)
   - Administrative divisions
   - Electoral information

2. **MIMU Boundary Data** (if available)
   - Township boundary polygons
   - Geographic reference data

3. **Cached Statistics**
   - Pre-calculated summaries
   - Regional breakdowns
   - Performance optimizations

### Database Schema

```sql
-- Main table for constituencies
constituencies (
    id, constituency_code, constituency_en, constituency_mm,
    state_region_en, state_region_mm, assembly_type,
    electoral_system, representatives, lat, lng,
    coordinate_source, validation_status, areas_included_en,
    geom -- PostGIS geometry column
)

-- Historical data for comparison
historical_constituencies (...)

-- MIMU boundary data
mimu_boundaries (
    boundary_geom -- MULTIPOLYGON geometries
)

-- Performance caching
cached_statistics (...)
```

## Environment Configuration

Key environment variables in `.env`:

```bash
# Database
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql://election_user:password@postgres:5432/myanmar_election

# Application
ENVIRONMENT=production
DEFAULT_MAP_PROVIDER=cartodb
ENABLE_CACHING=true

# Performance
CACHE_TTL_SECONDS=3600
HEAT_MAP_RADIUS=12

# API Keys (optional)
TOMTOM_API_KEY=your_key
MAPBOX_API_KEY=your_key
```

## Usage

### Starting Services

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d postgres
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f myanmar-election-app
```

### Database Access

```bash
# Access PostgreSQL
docker-compose exec postgres psql -U election_user myanmar_election

# Run queries
\dt  -- List tables
SELECT COUNT(*) FROM constituencies;
```

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (careful!)
docker-compose down -v
```

## Performance Benefits

### Before (CSV):
- File I/O for every query
- No indexing
- Limited filtering capabilities
- No caching

### After (PostgreSQL):
- Optimized database queries
- Spatial indexing for geographic data
- Redis caching layer
- Materialized views for aggregations

### Expected Improvements:
- **Search**: 10x faster with database indexes
- **Map Rendering**: 5x faster with spatial queries
- **Filtering**: 20x faster with optimized queries
- **Scalability**: Ready for 765 constituencies

## Scaling for 765 Constituencies

The new architecture is designed to handle the expansion:

### Database Optimization
- Spatial indexes for geographic queries
- Materialized views for expensive aggregations
- Connection pooling for concurrent users

### Application Caching
- Redis for frequently accessed data
- Streamlit's built-in caching
- Pre-computed statistics

### Container Scaling
```bash
# Scale app instances
docker-compose up -d --scale myanmar-election-app=3

# Load balancing with nginx
# (requires nginx configuration update)
```

## Troubleshooting

### Container Won't Start
```bash
# Check container status
docker-compose ps

# View detailed logs
docker-compose logs myanmar-election-app

# Check resource usage
docker stats
```

### Database Connection Issues
```bash
# Test database connectivity
docker-compose exec postgres pg_isready -U election_user

# Check database logs
docker-compose logs postgres

# Reset database
docker-compose down postgres
docker volume rm myanmar-election-viz_postgres_data
docker-compose up -d postgres
```

### Migration Errors
```bash
# Re-run migration
docker-compose exec myanmar-election-app python database/migrate_csv_to_db.py

# Check data integrity
docker-compose exec postgres psql -U election_user myanmar_election -c "SELECT COUNT(*) FROM constituencies;"
```

### Performance Issues
```bash
# Monitor Redis cache
docker-compose exec redis redis-cli info memory

# Check database performance
docker-compose exec postgres psql -U election_user myanmar_election -c "SELECT * FROM pg_stat_activity;"

# View app resource usage
docker stats myanmar-election-app
```

## Next Steps

1. **Verify Migration**: Ensure all 330 constituencies migrated correctly
2. **Test Features**: Verify maps, search, and export functionality
3. **Performance Testing**: Load test with multiple users
4. **Backup Setup**: Configure automated backups
5. **Monitoring**: Set up application monitoring
6. **Scale Preparation**: Ready for 765-constituency expansion

## Support

If you encounter issues:

1. Check the logs: `docker-compose logs -f`
2. Verify environment configuration in `.env`
3. Ensure all required data files are present
4. Test database connectivity
5. Review container resource usage

The Docker setup provides a solid foundation for scaling to 765 constituencies across all Myanmar electoral assemblies.