#!/usr/bin/env python3
"""
Migration script to convert CSV data to PostgreSQL database.
Handles the migration from current CSV-based storage to Docker PostgreSQL setup.
"""

import pandas as pd
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import sys
from pathlib import Path
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CSVToDatabaseMigrator:
    """Migrates Myanmar election data from CSV files to PostgreSQL database."""
    
    def __init__(self, database_url=None):
        """Initialize migrator with database connection."""
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable must be set")
        
        self.data_dir = Path(__file__).parent.parent / "data"
        self.processed_dir = self.data_dir / "processed"
        self.raw_dir = self.data_dir / "raw"
        
        self.conn = None
        
    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(self.database_url)
            logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
            
    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def load_csv_data(self):
        """Load existing CSV data."""
        logger.info("Loading CSV data...")
        
        # Load main constituency data
        csv_file = self.processed_dir / "myanmar_constituencies.csv"
        if not csv_file.exists():
            # Try to load from JSON if CSV doesn't exist
            json_file = self.processed_dir / "myanmar_constituencies.json"
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    return pd.DataFrame(json_data['constituencies'])
            else:
                raise FileNotFoundError(f"No constituency data found at {csv_file} or {json_file}")
        
        return pd.read_csv(csv_file)
    
    def prepare_constituency_data(self, df):
        """Prepare constituency data for database insertion."""
        logger.info(f"Preparing {len(df)} constituency records...")
        
        prepared_data = []
        for _, row in df.iterrows():
            # Generate constituency code if not present
            constituency_code = f"PTHT_{row.get('id', row.name):03d}"
            
            record = {
                'constituency_code': constituency_code,
                'constituency_en': row.get('constituency_en', ''),
                'constituency_mm': row.get('constituency_mm', ''),
                'state_region_en': row.get('state_region_en', ''),
                'state_region_mm': row.get('state_region_mm', ''),
                'assembly_type': 'PTHT',  # Current data is all Pyithu Hluttaw
                'electoral_system': 'FPTP',
                'representatives': int(row.get('representatives', 1)),
                'lat': float(row['lat']) if pd.notna(row.get('lat')) else None,
                'lng': float(row['lng']) if pd.notna(row.get('lng')) else None,
                'coordinate_source': 'geocoded' if pd.notna(row.get('lat')) else None,
                'validation_status': 'verified' if pd.notna(row.get('lat')) else 'pending',
                'areas_included_en': row.get('areas_included_en', ''),
                'areas_included_mm': row.get('areas_included_mm', ''),
                'election_year': 2025
            }
            prepared_data.append(record)
            
        return prepared_data
    
    def insert_constituencies(self, data):
        """Insert constituency data into database."""
        logger.info(f"Inserting {len(data)} constituencies...")
        
        with self.conn.cursor() as cursor:
            # Clear existing data
            cursor.execute("DELETE FROM constituencies WHERE election_year = 2025")
            
            # Insert new data
            insert_query = """
            INSERT INTO constituencies (
                constituency_code, constituency_en, constituency_mm,
                state_region_en, state_region_mm, assembly_type, electoral_system,
                representatives, lat, lng, coordinate_source, validation_status,
                areas_included_en, areas_included_mm, election_year
            ) VALUES (
                %(constituency_code)s, %(constituency_en)s, %(constituency_mm)s,
                %(state_region_en)s, %(state_region_mm)s, %(assembly_type)s, %(electoral_system)s,
                %(representatives)s, %(lat)s, %(lng)s, %(coordinate_source)s, %(validation_status)s,
                %(areas_included_en)s, %(areas_included_mm)s, %(election_year)s
            )
            """
            
            cursor.executemany(insert_query, data)
            self.conn.commit()
            
        logger.info(f"Successfully inserted {len(data)} constituencies")
    
    def load_and_insert_mimu_data(self):
        """Load and insert MIMU boundary data if available."""
        mimu_file = self.data_dir / "2020" / "mmr_polbnda_adm3_250k_mimu_1.csv"
        
        if not mimu_file.exists():
            logger.warning(f"MIMU file not found at {mimu_file}")
            return
            
        logger.info("Loading MIMU boundary data...")
        mimu_df = pd.read_csv(mimu_file)
        
        with self.conn.cursor() as cursor:
            # Clear existing MIMU data
            cursor.execute("DELETE FROM mimu_boundaries")
            
            for _, row in mimu_df.iterrows():
                # Parse geometry if available (simplified for now)
                insert_query = """
                INSERT INTO mimu_boundaries (
                    fid, st_pcode, ts_pcode, township_name_en, state_region_en
                ) VALUES (%s, %s, %s, %s, %s)
                """
                
                cursor.execute(insert_query, (
                    row.get('FID'),
                    row.get('ST_PCODE'),
                    row.get('TS_PCODE'),
                    row.get('TS_NAME_EN', ''),
                    row.get('ST_NAME_EN', '')
                ))
            
            self.conn.commit()
            
        logger.info(f"Successfully inserted {len(mimu_df)} MIMU boundary records")
    
    def create_initial_cache(self):
        """Create initial cached statistics."""
        logger.info("Creating initial cached statistics...")
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Calculate summary statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_constituencies,
                    SUM(representatives) as total_representatives,
                    COUNT(DISTINCT state_region_en) as total_regions,
                    COUNT(CASE WHEN lat IS NOT NULL THEN 1 END) as mapped_constituencies
                FROM constituencies 
                WHERE election_year = 2025
            """)
            summary = cursor.fetchone()
            
            # Regional breakdown
            cursor.execute("""
                SELECT 
                    state_region_en,
                    COUNT(*) as constituencies,
                    SUM(representatives) as representatives
                FROM constituencies 
                WHERE election_year = 2025
                GROUP BY state_region_en
                ORDER BY state_region_en
            """)
            regional_breakdown = cursor.fetchall()
            
            # Assembly breakdown
            cursor.execute("""
                SELECT 
                    assembly_type,
                    COUNT(*) as constituencies,
                    SUM(representatives) as representatives
                FROM constituencies 
                WHERE election_year = 2025
                GROUP BY assembly_type
            """)
            assembly_breakdown = cursor.fetchall()
            
            # Create cache entries
            cache_entries = [
                {
                    'cache_key': 'summary_statistics_2025',
                    'data': json.dumps(dict(summary)),
                    'expires_at': None  # No expiration for migration data
                },
                {
                    'cache_key': 'regional_breakdown_2025',
                    'data': json.dumps([dict(row) for row in regional_breakdown]),
                    'expires_at': None
                },
                {
                    'cache_key': 'assembly_breakdown_2025',
                    'data': json.dumps([dict(row) for row in assembly_breakdown]),
                    'expires_at': None
                }
            ]
            
            # Insert cache entries
            for entry in cache_entries:
                cursor.execute("""
                    INSERT INTO cached_statistics (cache_key, data, expires_at, election_year)
                    VALUES (%(cache_key)s, %(data)s, %(expires_at)s, 2025)
                    ON CONFLICT (cache_key) DO UPDATE SET
                        data = EXCLUDED.data,
                        created_at = CURRENT_TIMESTAMP
                """, entry)
            
            self.conn.commit()
            
        logger.info("Initial cache created successfully")
    
    def validate_migration(self):
        """Validate the migration was successful."""
        logger.info("Validating migration...")
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check total record count
            cursor.execute("SELECT COUNT(*) as count FROM constituencies WHERE election_year = 2025")
            db_count = cursor.fetchone()['count']
            
            # Check geographic data
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN lat IS NOT NULL AND lng IS NOT NULL THEN 1 END) as with_coords
                FROM constituencies WHERE election_year = 2025
            """)
            geo_stats = cursor.fetchone()
            
            logger.info(f"Database contains {db_count} constituencies")
            logger.info(f"Geographic data: {geo_stats['with_coords']}/{geo_stats['total']} have coordinates")
            
            # Verify we have the expected 330 Pyithu Hluttaw constituencies
            if db_count == 330:
                logger.info("✅ Migration validation successful: 330 constituencies imported")
                return True
            else:
                logger.error(f"❌ Migration validation failed: Expected 330, got {db_count}")
                return False
    
    def run_migration(self):
        """Execute the complete migration process."""
        logger.info("Starting CSV to PostgreSQL migration...")
        
        try:
            # Connect to database
            self.connect()
            
            # Load CSV data
            csv_data = self.load_csv_data()
            
            # Prepare and insert constituency data
            prepared_data = self.prepare_constituency_data(csv_data)
            self.insert_constituencies(prepared_data)
            
            # Load MIMU data if available
            self.load_and_insert_mimu_data()
            
            # Create initial cache
            self.create_initial_cache()
            
            # Refresh materialized views
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT refresh_statistics()")
                self.conn.commit()
            
            # Validate migration
            if self.validate_migration():
                logger.info("🎉 Migration completed successfully!")
                return True
            else:
                logger.error("❌ Migration validation failed")
                return False
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.disconnect()

def main():
    """Main migration function."""
    # Check environment
    if not os.getenv('DATABASE_URL'):
        print("Error: DATABASE_URL environment variable not set")
        print("Example: DATABASE_URL=postgresql://election_user:password@localhost:5432/myanmar_election")
        sys.exit(1)
    
    # Run migration
    migrator = CSVToDatabaseMigrator()
    success = migrator.run_migration()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("Your Myanmar Election Visualization data is now in PostgreSQL.")
        print("You can start the Docker containers with: docker-compose up -d")
    else:
        print("\n❌ Migration failed. Check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()