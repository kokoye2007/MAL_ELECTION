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

def load_sample_data(connection_string):
    """Load sample constituency data for demonstration."""
    try:
        conn = psycopg2.connect(connection_string)
        
        # Sample data for demonstration
        sample_data = [
            {
                'constituency_code': 'YGN-001',
                'constituency_en': 'Yangon (1)',
                'constituency_mm': 'ရန်ကုန် (၁)',
                'state_region_en': 'Yangon Region',
                'state_region_mm': 'ရန်ကုန်တိုင်းဒေသကြီး',
                'assembly_type': 'PTHT',
                'representatives': 1,
                'lat': 16.8661,
                'lng': 96.1951,
                'areas_included_en': 'Downtown Yangon',
                'coordinate_source': 'manual'
            },
            {
                'constituency_code': 'MDY-001', 
                'constituency_en': 'Mandalay (1)',
                'constituency_mm': 'မန္တလေး (၁)',
                'state_region_en': 'Mandalay Region',
                'state_region_mm': 'မန္တလေးတိုင်းဒေသကြီး',
                'assembly_type': 'PTHT',
                'representatives': 1,
                'lat': 21.9588,
                'lng': 96.0891,
                'areas_included_en': 'Central Mandalay',
                'coordinate_source': 'manual'
            }
        ]
        
        with conn.cursor() as cursor:
            # Check if data already exists
            cursor.execute("SELECT COUNT(*) FROM constituencies WHERE election_year = 2025")
            count = cursor.fetchone()[0]
            
            if count == 0:
                for data in sample_data:
                    cursor.execute("""
                        INSERT INTO constituencies (
                            constituency_code, constituency_en, constituency_mm,
                            state_region_en, state_region_mm, assembly_type,
                            representatives, lat, lng, areas_included_en, coordinate_source
                        ) VALUES (%(constituency_code)s, %(constituency_en)s, %(constituency_mm)s,
                                %(state_region_en)s, %(state_region_mm)s, %(assembly_type)s,
                                %(representatives)s, %(lat)s, %(lng)s, %(areas_included_en)s, %(coordinate_source)s)
                    """, data)
                
                conn.commit()
                logger.info(f"✅ Loaded {len(sample_data)} sample constituencies")
            else:
                logger.info(f"✅ Database already contains {count} constituencies")
            
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error loading sample data: {e}")
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
    
    # Load sample data
    if not load_sample_data(database_url):
        logger.error("❌ Failed to load sample data")
        sys.exit(1)
    
    logger.info("🎉 Heroku database initialization completed successfully!")
    logger.info("📊 Application ready for deployment")

if __name__ == "__main__":
    main()