# Database Setup Guide

This document explains the simplified database initialization approach for the Myanmar Election Visualization project.

## 🏗️ Architecture Overview

The database setup has been consolidated into a clean, automated initialization process:

```
database/
├── init/                           # PostgreSQL auto-initialization
│   ├── 00_init.sql                # Basic user/database setup
│   ├── 01_schema.sql              # Complete schema with PostGIS
│   └── 02_data_migration.sql      # Migration helper functions
├── init_complete.py               # Consolidated data migration
├── migrate_csv_to_db.py          # PTHT base data (330 constituencies)
├── expand_constituencies.py      # TPHT + TPTYT expansion
├── add_amyotha_hluttaw.py        # AMTHT data (116 constituencies)
└── geocode_constituencies.py     # Coordinate mapping
```

## 🚀 Quick Start Options

### Option 1: Automatic Initialization (Recommended)
```bash
# Single command setup with full database
./quick-start.sh
```

This will:
1. Start PostgreSQL with schema auto-initialization
2. Start the Streamlit application
3. Run complete data migration (835 constituencies)
4. Verify data completeness

### Option 2: Manual Step-by-Step
```bash
# 1. Start containers with schema only
docker-compose -f docker-compose.dev.yml up -d

# 2. Initialize complete database
docker-compose -f docker-compose.dev.yml exec myanmar-election-viz python database/init_complete.py

# 3. Verify setup
curl http://localhost:8501
```

### Option 3: Individual Migration Steps
```bash
# Start with empty schema
docker-compose -f docker-compose.dev.yml up -d

# Run migrations individually
docker-compose -f docker-compose.dev.yml exec myanmar-election-viz python database/migrate_csv_to_db.py
docker-compose -f docker-compose.dev.yml exec myanmar-election-viz python database/expand_constituencies.py
docker-compose -f docker-compose.dev.yml exec myanmar-election-viz python database/add_amyotha_hluttaw.py
docker-compose -f docker-compose.dev.yml exec myanmar-election-viz python database/geocode_constituencies.py
```

## 📊 Data Structure

### Automatic Schema Initialization
When PostgreSQL starts, it automatically runs:
- `00_init.sql` - Creates users and database
- `01_schema.sql` - Creates complete schema with PostGIS
- `02_data_migration.sql` - Helper functions for data loading

### Data Migration Process
The `init_complete.py` script orchestrates:

1. **PTHT Base Data** (330 constituencies)
   - Source: `data/processed/myanmar_constituencies.csv`
   - Assembly: Pyithu Hluttaw (Lower House)

2. **Assembly Expansion** (360 + 29 = 389 additional)
   - TPHT: State/Regional assemblies (360)
   - TPTYT: Ethnic Affairs constituencies (29)
   - Source: Excel analysis with constituency detection

3. **AMTHT Addition** (116 constituencies)
   - Assembly: Amyotha Hluttaw (Upper House)
   - Generated based on constitutional allocation

4. **Geocoding** (98.8% coverage)
   - Coordinates for 826/835 constituencies
   - Sources: township centers, state centers, manual mapping

## 🔧 Database Configuration

### Development Environment
```yaml
# docker-compose.dev.yml
postgres:
  image: postgis/postgis:15-3.4
  environment:
    POSTGRES_DB: myanmar_election
    POSTGRES_USER: election_user
    POSTGRES_PASSWORD: election_dev_2025
  volumes:
    - ./database/init:/docker-entrypoint-initdb.d:ro
  tmpfs:
    - /var/lib/postgresql/data  # Non-persistent for development
```

### Production Environment
```yaml
# docker-compose.yml
postgres:
  volumes:
    - postgres_data:/var/lib/postgresql/data  # Persistent storage
    - ./database/init:/docker-entrypoint-initdb.d:ro
```

## 📋 Verification

### Check Data Completeness
```bash
# Quick verification
docker exec myanmar-election-db-dev psql -U election_user -d myanmar_election -c "
SELECT 
    assembly_type,
    COUNT(*) as constituencies,
    COUNT(CASE WHEN lat IS NOT NULL THEN 1 END) as mapped
FROM constituencies 
WHERE election_year = 2025
GROUP BY assembly_type
ORDER BY assembly_type;
"
```

Expected output:
```
assembly_type | constituencies | mapped
--------------+----------------+--------
AMTHT         |            116 |    116
PTHT          |            330 |    330
TPHT          |            360 |    351
TPTYT         |             29 |     29
```

### Application Health Check
```bash
curl http://localhost:8501/_stcore/health
# Should return: {"status": "ok"}
```

## 🔄 Reset and Rebuild

### Reset Development Database
```bash
# Stop containers
docker-compose -f docker-compose.dev.yml down

# Remove volumes (development uses tmpfs, so just restart)
docker-compose -f docker-compose.dev.yml up -d

# Re-initialize data
docker-compose -f docker-compose.dev.yml exec myanmar-election-viz python database/init_complete.py
```

### Reset Production Database
```bash
# Stop and remove persistent data
docker-compose down
docker volume rm myanmar-election-viz_postgres_data

# Restart (will auto-initialize)
docker-compose up -d
```

## 🛠️ Troubleshooting

### Common Issues

1. **PostgreSQL fails to start**
   ```bash
   # Check logs
   docker-compose logs postgres
   
   # Verify initialization scripts
   ls -la database/init/
   ```

2. **Data migration fails**
   ```bash
   # Check migration logs
   docker-compose exec myanmar-election-viz python database/init_complete.py
   
   # Verify CSV data exists
   ls -la data/processed/
   ```

3. **Application can't connect to database**
   ```bash
   # Test database connectivity
   docker exec myanmar-election-db-dev pg_isready -U election_user -d myanmar_election
   
   # Check environment variables
   docker-compose exec myanmar-election-viz env | grep DATABASE
   ```

### Performance Issues

For large dataset operations:
- Use `docker-compose.dev.yml` with tmpfs for faster I/O
- Monitor migration progress with verbose logging
- Consider running geocoding separately if timeout occurs

## 📚 Migration Scripts Reference

| Script | Purpose | Expected Output |
|--------|---------|-----------------|
| `migrate_csv_to_db.py` | Load PTHT base data | 330 constituencies |
| `expand_constituencies.py` | Add TPHT + TPTYT | +389 constituencies |
| `add_amyotha_hluttaw.py` | Add AMTHT data | +116 constituencies |
| `geocode_constituencies.py` | Map coordinates | 98.8% geocoded |
| `init_complete.py` | Run all migrations | 835 total constituencies |

## 🎯 Best Practices

1. **Always use the consolidated `init_complete.py`** for new setups
2. **Use `quick-start.sh`** for development environment setup
3. **Verify data completeness** after any migration
4. **Keep `database/init/` files** for automatic schema setup
5. **Use development environment** for testing migration changes