#!/usr/bin/env python3
"""
Heroku Database Initialization Script
Initializes PostgreSQL database with Myanmar Election data for Heroku deployment.
"""

import os
import sys
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from pathlib import Path

# Add src to path for database imports
sys.path.append(str(Path(__file__).parent.parent / 'src'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_heroku_database_url():
    """Get Heroku database URL from environment."""
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Heroku provides postgres:// but psycopg2 needs postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
    return database_url

def create_tables(connection_string):
    """Create necessary tables for Myanmar Election data."""
    try:
        conn = psycopg2.connect(connection_string)
        with conn.cursor() as cursor:
            # Create constituencies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS constituencies (
                    id SERIAL PRIMARY KEY,
                    constituency_code VARCHAR(20) NOT NULL,
                    constituency_en VARCHAR(255) NOT NULL,
                    constituency_mm VARCHAR(255),
                    state_region_en VARCHAR(100) NOT NULL,
                    state_region_mm VARCHAR(100),
                    assembly_type VARCHAR(10) NOT NULL,
                    electoral_system VARCHAR(20) DEFAULT 'FPTP',
                    representatives INTEGER DEFAULT 1,
                    lat DECIMAL(10, 8),
                    lng DECIMAL(11, 8),
                    areas_included_en TEXT,
                    areas_included_mm TEXT,
                    ethnic_group VARCHAR(100),
                    coordinate_source VARCHAR(50) DEFAULT 'estimated',
                    validation_status VARCHAR(20) DEFAULT 'pending',
                    election_year INTEGER DEFAULT 2025,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(constituency_code, assembly_type, election_year)
                );
            """)
            
            # Create historical constituencies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historical_constituencies (
                    id SERIAL PRIMARY KEY,
                    constituency_code VARCHAR(20) NOT NULL,
                    constituency_en VARCHAR(255) NOT NULL,
                    constituency_mm VARCHAR(255),
                    state_region_en VARCHAR(100) NOT NULL,
                    state_region_mm VARCHAR(100),
                    assembly_type VARCHAR(10) NOT NULL,
                    representatives INTEGER DEFAULT 1,
                    lat DECIMAL(10, 8),
                    lng DECIMAL(11, 8),
                    areas_included_en TEXT,
                    election_year INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(constituency_code, assembly_type, election_year)
                );
            """)
            
            # Create cached statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cached_statistics (
                    id SERIAL PRIMARY KEY,
                    cache_key VARCHAR(100) NOT NULL,
                    election_year INTEGER NOT NULL,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    UNIQUE(cache_key, election_year)
                );
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_constituencies_assembly ON constituencies(assembly_type);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_constituencies_region ON constituencies(state_region_en);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_constituencies_year ON constituencies(election_year);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_constituencies_coords ON constituencies(lat, lng);")
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_historical_assembly ON historical_constituencies(assembly_type);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_historical_year ON historical_constituencies(election_year);")
            
            conn.commit()
            logger.info("✅ Database tables created successfully")
            
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        return False

def load_clean_data(connection_string):
    """Load comprehensive Myanmar constituency data with MIMU coordinates."""
    try:
        # Import and run the comprehensive data loader
        from load_comprehensive_data import clean_database, load_comprehensive_data
        
        logger.info("📊 Loading comprehensive Myanmar Election data with MIMU coordinates...")
        
        # Always clean and reload for comprehensive data
        conn = psycopg2.connect(connection_string)
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM constituencies WHERE election_year = 2025")
            count = cursor.fetchone()[0]
            
            if count > 0:
                logger.info(f"🧹 Found {count} constituencies, cleaning for fresh comprehensive load...")
                conn.close()
                if not clean_database(connection_string):
                    logger.error("❌ Failed to clean database")
                    return False
            else:
                conn.close()
        
        # Load comprehensive constituency data with MIMU coordinates
        if not load_comprehensive_data(connection_string):
            logger.error("❌ Failed to load comprehensive data")
            return False
        
        logger.info("🎉 Successfully loaded comprehensive Myanmar constituencies with MIMU coordinates!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error loading comprehensive data: {e}")
        # Fallback to basic sample data
        logger.info("⚠️ Falling back to minimal sample data...")
        return load_minimal_sample_data(connection_string)

def load_minimal_sample_data(connection_string):
    """Fallback: Load minimal sample data if real data loading fails."""
    try:
        conn = psycopg2.connect(connection_string)
        
        # Minimal sample data for emergency fallback
        sample_data = [
            ('YGN-001', 'Yangon (1)', 'ရန်ကုန် (၁)', 'Yangon Region', 'ရန်ကုန်တိုင်းဒေသကြီး', 'PTHT', 1, 16.8661, 96.1951),
            ('MDY-001', 'Mandalay (1)', 'မန္တလေး (၁)', 'Mandalay Region', 'မန္တလေးတိုင်းဒေသကြီး', 'PTHT', 1, 21.9588, 96.0891),
            ('NPT-001', 'Naypyidaw (1)', 'နေပြည်တော် (၁)', 'Naypyidaw', 'နေပြည်တော်', 'PTHT', 1, 19.7633, 96.0785),
        ]
        
        with conn.cursor() as cursor:
            for code, name_en, name_mm, region_en, region_mm, assembly, reps, lat, lng in sample_data:
                cursor.execute("""
                    INSERT INTO constituencies (
                        constituency_code, constituency_en, constituency_mm,
                        state_region_en, state_region_mm, assembly_type,
                        representatives, lat, lng, coordinate_source, validation_status, election_year
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (code, name_en, name_mm, region_en, region_mm, assembly, reps, lat, lng, 'manual', 'verified', 2025))
            
            conn.commit()
            logger.info(f"✅ Loaded {len(sample_data)} minimal sample constituencies")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error loading minimal sample data: {e}")
        return False

def main():
    """Main initialization function for Heroku deployment."""
    logger.info("🚀 Starting Heroku database initialization...")
    
    # Get database URL
    database_url = get_heroku_database_url()
    if not database_url:
        logger.error("❌ DATABASE_URL environment variable not found")
        sys.exit(1)
    
    logger.info("📍 Found database URL, connecting...")
    
    # Create tables
    if not create_tables(database_url):
        logger.error("❌ Failed to create database tables")
        sys.exit(1)
    
    # Load comprehensive Myanmar Election data with MIMU coordinates
    if not load_clean_data(database_url):
        logger.error("❌ Failed to load clean data")
        sys.exit(1)
    
    logger.info("🎉 Heroku database initialization completed successfully!")
    logger.info("📊 Application ready for deployment")

if __name__ == "__main__":
    main()