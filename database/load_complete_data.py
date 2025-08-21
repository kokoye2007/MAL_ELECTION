#!/usr/bin/env python3
"""
Load Complete Myanmar Election Data to Database
Loads all assembly types from the extracted comprehensive data
"""

import os
import sys
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / 'src'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment."""
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Heroku provides postgres:// but psycopg2 needs postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return database_url
    else:
        # Local development fallback
        return os.getenv(
            'DATABASE_URL', 
            'postgresql://election_user:dev_password_2025@postgres:5432/myanmar_election'
        )

def clean_database(connection_string):
    """Clean all existing constituency data."""
    try:
        conn = psycopg2.connect(connection_string)
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM constituencies WHERE election_year = 2025")
            conn.commit()
            logger.info("🧹 Cleaned existing constituency data")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Error cleaning database: {e}")
        return False

def load_complete_constituencies(connection_string):
    """Load all constituency data from comprehensive CSV."""
    try:
        # Read comprehensive CSV data
        csv_path = Path(__file__).parent.parent / 'data' / 'processed' / 'myanmar_election_2025_complete.csv'
        if not csv_path.exists():
            logger.error(f"❌ CSV file not found: {csv_path}")
            return False
        
        df = pd.read_csv(csv_path)
        logger.info(f"📊 Loaded {len(df)} constituencies from comprehensive CSV")
        
        # Connect to database
        conn = psycopg2.connect(connection_string)
        
        inserted = 0
        with conn.cursor() as cursor:
            for _, row in df.iterrows():
                try:
                    # Generate constituency code if missing
                    constituency_code = row.get('constituency_code')
                    if pd.isna(constituency_code) or constituency_code == 'nan':
                        state_abbrev = ''.join([word[0].upper() for word in str(row['state_region_en']).split()[:2]])
                        constituency_code = f"{state_abbrev}-{row['id']:03d}"
                    
                    # Check if constituency already exists
                    cursor.execute("""
                        SELECT COUNT(*) FROM constituencies 
                        WHERE constituency_code = %s AND assembly_type = %s AND election_year = %s
                    """, (constituency_code, row['assembly_type'], 2025))
                    
                    if cursor.fetchone()[0] == 0:  # Doesn't exist, safe to insert
                        cursor.execute("""
                            INSERT INTO constituencies (
                                constituency_code, constituency_en, constituency_mm,
                                state_region_en, state_region_mm, assembly_type,
                                areas_included_en, areas_included_mm, representatives,
                                electoral_system, lat, lng, coordinate_source,
                                validation_status, election_year
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            constituency_code,
                            str(row['constituency_en']),
                            str(row['constituency_mm']),
                            str(row['state_region_en']),
                            str(row['state_region_mm']),
                            str(row['assembly_type']),
                            str(row['areas_included_en']),
                            str(row['areas_included_mm']),
                            int(row['representatives']),
                            str(row['electoral_system_en']),
                            None,  # lat - will be populated from MIMU
                            None,  # lng - will be populated from MIMU
                            'mimu_pending',
                            'verified',
                            2025
                        ))
                        inserted += 1
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error inserting row {row['id']}: {e}")
                    continue
            
            conn.commit()
            logger.info(f"✅ Successfully inserted {inserted} constituencies")
            
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error loading constituency data: {e}")
        return False

def main():
    """Main function to load complete data."""
    logger.info("🚀 Starting Complete Myanmar Election Data Loading...")
    
    connection_string = get_database_url()
    logger.info(f"📡 Using database: {connection_string.split('@')[1] if '@' in connection_string else 'local'}")
    
    # Clean existing data
    if not clean_database(connection_string):
        logger.error("❌ Failed to clean database")
        return False
    
    # Load comprehensive constituencies
    if not load_complete_constituencies(connection_string):
        logger.error("❌ Failed to load constituency data")
        return False
    
    # Final verification
    try:
        conn = psycopg2.connect(connection_string)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT assembly_type, COUNT(*) as count 
                FROM constituencies 
                WHERE election_year = 2025 
                GROUP BY assembly_type 
                ORDER BY assembly_type
            """)
            results = cursor.fetchall()
            
            logger.info("📊 Final Database Statistics:")
            total = 0
            for assembly_type, count in results:
                logger.info(f"  {assembly_type}: {count} constituencies")
                total += count
            logger.info(f"  TOTAL: {total} constituencies")
            
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error getting final statistics: {e}")
    
    logger.info("🎉 Complete data loading finished successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)