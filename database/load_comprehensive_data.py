#!/usr/bin/env python3
"""
Load comprehensive Myanmar Election data with MIMU coordinates.
This loads the correct data from extract_comprehensive_with_coordinates.py output.
"""

import os
import sys
import logging
import psycopg2
import pandas as pd
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_database(connection_string):
    """Clean existing data from database."""
    try:
        conn = psycopg2.connect(connection_string)
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM constituencies WHERE election_year = 2025")
            deleted = cursor.rowcount
            conn.commit()
            logger.info(f"🧹 Cleaned {deleted} existing records")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Error cleaning database: {e}")
        return False

def load_comprehensive_data(connection_string):
    """Load comprehensive data with MIMU coordinates."""
    try:
        # Load the comprehensive CSV with coordinates
        csv_path = Path(__file__).parent.parent / 'data' / 'processed' / 'myanmar_election_2025_comprehensive_with_coordinates.csv'
        
        if not csv_path.exists():
            logger.error(f"❌ CSV file not found: {csv_path}")
            return False
        
        df = pd.read_csv(csv_path)
        logger.info(f"📊 Loaded {len(df)} constituencies from CSV")
        
        # Connect to database
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        loaded = 0
        skipped = 0
        
        for _, row in df.iterrows():
            try:
                # Prepare data with proper handling of NaN values
                lat = row['lat'] if pd.notna(row['lat']) else None
                lng = row['lng'] if pd.notna(row['lng']) else None
                coord_source = row.get('coordinate_source', 'unknown') if pd.notna(row.get('coordinate_source')) else 'unknown'
                
                cursor.execute("""
                    INSERT INTO constituencies (
                        constituency_code, 
                        constituency_en, 
                        constituency_mm,
                        state_region_en, 
                        state_region_mm, 
                        assembly_type,
                        electoral_system,
                        representatives, 
                        lat, 
                        lng,
                        areas_included_en,
                        areas_included_mm,
                        coordinate_source,
                        validation_status,
                        election_year
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (constituency_code, assembly_type, election_year) 
                    DO UPDATE SET
                        constituency_en = EXCLUDED.constituency_en,
                        constituency_mm = EXCLUDED.constituency_mm,
                        state_region_en = EXCLUDED.state_region_en,
                        state_region_mm = EXCLUDED.state_region_mm,
                        electoral_system = EXCLUDED.electoral_system,
                        representatives = EXCLUDED.representatives,
                        lat = EXCLUDED.lat,
                        lng = EXCLUDED.lng,
                        areas_included_en = EXCLUDED.areas_included_en,
                        areas_included_mm = EXCLUDED.areas_included_mm,
                        coordinate_source = EXCLUDED.coordinate_source,
                        validation_status = EXCLUDED.validation_status,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    row.get('id', f"{row.get('state_region_en', 'UNK')}-{loaded+1:03d}"),
                    row.get('constituency_en', 'Unknown'),
                    row.get('constituency_mm', ''),
                    row.get('state_region_en', 'Unknown'),
                    row.get('state_region_mm', ''),
                    row.get('assembly_type', 'UNKNOWN'),
                    row.get('electoral_system', 'FPTP'),
                    int(row.get('representatives', 1)) if pd.notna(row.get('representatives')) else 1,
                    lat,
                    lng,
                    row.get('areas_included_en', ''),
                    row.get('areas_included_mm', ''),
                    coord_source,
                    'verified' if lat and lng else 'pending',
                    2025
                ))
                loaded += 1
                
            except Exception as e:
                logger.warning(f"⚠️ Skipped row: {e}")
                skipped += 1
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Successfully loaded {loaded} constituencies")
        if skipped > 0:
            logger.info(f"⚠️ Skipped {skipped} problematic rows")
        
        # Verify the load
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        # Count by assembly type
        cursor.execute("""
            SELECT assembly_type, COUNT(*) 
            FROM constituencies 
            WHERE election_year = 2025 
            GROUP BY assembly_type 
            ORDER BY assembly_type
        """)
        
        logger.info("📊 Loaded constituencies by assembly type:")
        for assembly, count in cursor.fetchall():
            logger.info(f"  {assembly}: {count}")
        
        # Count mapped coordinates
        cursor.execute("""
            SELECT COUNT(*) 
            FROM constituencies 
            WHERE election_year = 2025 AND lat IS NOT NULL AND lng IS NOT NULL
        """)
        mapped = cursor.fetchone()[0]
        logger.info(f"📍 Constituencies with coordinates: {mapped}/{loaded}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error loading comprehensive data: {e}")
        return False

def main():
    """Main function to load comprehensive data."""
    # Get database URL (local or Heroku)
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        # Try local database
        database_url = "postgresql://election_user:election2025@localhost:5432/myanmar_election"
        logger.info("📍 Using local database")
    else:
        # Heroku provides postgres:// but psycopg2 needs postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        logger.info("📍 Using Heroku database")
    
    # Clean existing data
    logger.info("🧹 Cleaning existing data...")
    if not clean_database(database_url):
        logger.error("Failed to clean database")
        sys.exit(1)
    
    # Load comprehensive data
    logger.info("📊 Loading comprehensive data with MIMU coordinates...")
    if not load_comprehensive_data(database_url):
        logger.error("Failed to load comprehensive data")
        sys.exit(1)
    
    logger.info("🎉 Successfully loaded comprehensive Myanmar Election data!")

if __name__ == "__main__":
    main()