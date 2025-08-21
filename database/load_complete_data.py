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
import json
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
            'postgresql://election_user:election_pass_2025@localhost:5432/myanmar_election'
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

def load_mimu_coordinates():
    """Load MIMU coordinate lookup from GeoJSON."""
    try:
        # Load MIMU boundary data
        mimu_path = Path(__file__).parent.parent / 'data' / 'geojson' / 'mimu_township_boundaries.geojson'
        if not mimu_path.exists():
            logger.warning(f"⚠️ MIMU GeoJSON not found: {mimu_path}")
            return {}
        
        with open(mimu_path, 'r', encoding='utf-8') as f:
            mimu_data = json.load(f)
        
        mimu_coords = {}
        for feature in mimu_data.get('features', []):
            props = feature.get('properties', {})
            tsp_pcode = props.get('tsp_pcode', props.get('TS_PCODE'))
            
            if tsp_pcode and feature.get('geometry'):
                # Calculate centroid from geometry
                geom = feature['geometry']
                if geom['type'] == 'Polygon' and geom.get('coordinates'):
                    coords = geom['coordinates'][0]  # Outer ring
                    if len(coords) > 0:
                        # Simple centroid calculation
                        sum_lat, sum_lng = 0, 0
                        count = len(coords)
                        for coord in coords:
                            if len(coord) >= 2:
                                sum_lng += coord[0]
                                sum_lat += coord[1]
                        
                        centroid_lat = sum_lat / count
                        centroid_lng = sum_lng / count
                        mimu_coords[tsp_pcode] = (centroid_lat, centroid_lng)
        
        logger.info(f"📍 Loaded {len(mimu_coords)} MIMU coordinate entries")
        return mimu_coords
        
    except Exception as e:
        logger.error(f"❌ Error loading MIMU coordinates: {e}")
        return {}

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
        
        # Load MIMU coordinates for population
        mimu_coords = load_mimu_coordinates()
        
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
                        # Get MIMU coordinates if available
                        lat, lng = None, None
                        coordinate_source = 'mimu_pending'
                        
                        tsp_pcode = row.get('tsp_pcode', '')
                        if tsp_pcode and tsp_pcode in mimu_coords:
                            lat, lng = mimu_coords[tsp_pcode]
                            coordinate_source = 'mimu_boundary_centroid'
                            logger.info(f"📍 MIMU coordinates for {row['constituency_en']}: {lat:.4f}, {lng:.4f}")
                        
                        # Map electoral system to shorter value
                        electoral_system = str(row['electoral_system_en'])
                        if 'FPTP' in electoral_system or 'First Past The Post' in electoral_system:
                            electoral_system = 'FPTP'
                        elif len(electoral_system) > 10:
                            electoral_system = electoral_system[:10]
                        
                        cursor.execute("""
                            INSERT INTO constituencies (
                                constituency_code, constituency_en, constituency_mm,
                                state_region_en, state_region_mm, assembly_type,
                                constituency_areas_en, constituency_areas_mm, representatives,
                                electoral_system, lat, lng, coordinate_source,
                                validation_status, election_year, township_name_eng, township_name_mm,
                                tsp_pcode
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            constituency_code,
                            str(row['constituency_en']),
                            str(row['constituency_mm']),
                            str(row['state_region_en']),
                            str(row['state_region_mm']),
                            str(row['assembly_type']),
                            str(row['areas_included_en']),  # constituency_areas_en
                            str(row['areas_included_mm']),  # constituency_areas_mm
                            int(row['representatives']),
                            electoral_system,
                            lat,  # lat - from MIMU if available
                            lng,  # lng - from MIMU if available
                            coordinate_source,
                            'verified',
                            2025,
                            str(row['township_name_en']),  # township_name_eng
                            str(row.get('township_mm', row.get('state_region_mm', ''))),  # township_name_mm
                            str(row['tsp_pcode'])  # tsp_pcode
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