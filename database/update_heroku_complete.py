#!/usr/bin/env python3
"""
Update Heroku Database with Comprehensive Data
Updates Heroku database with complete election data including MIMU coordinates
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

def get_heroku_database_url():
    """Get Heroku database URL from environment."""
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Heroku provides postgres:// but psycopg2 needs postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return database_url
    else:
        logger.error("❌ No DATABASE_URL environment variable found")
        return None

def load_mimu_coordinates():
    """Load MIMU coordinate lookup from GeoJSON."""
    try:
        # Load MIMU boundary data
        mimu_path = Path(__file__).parent.parent / 'data' / 'geojson' / 'myanmar_townships_mimu.geojson'
        if not mimu_path.exists():
            logger.warning(f"⚠️ MIMU GeoJSON not found: {mimu_path}")
            return {}
        
        with open(mimu_path, 'r', encoding='utf-8') as f:
            mimu_data = json.load(f)
        
        mimu_coords = {}
        for feature in mimu_data.get('features', []):
            props = feature.get('properties', {})
            tsp_pcode = props.get('TS_PCODE')
            
            if tsp_pcode and feature.get('geometry'):
                # Calculate centroid from geometry
                geom = feature['geometry']
                if geom['type'] == 'MultiPolygon' and geom.get('coordinates'):
                    # For MultiPolygon, use the first polygon's outer ring
                    coords = geom['coordinates'][0][0]  # First polygon's outer ring
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
                elif geom['type'] == 'Polygon' and geom.get('coordinates'):
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

def calculate_multi_township_coordinates(tsp_pcode_string, mimu_coords):
    """Calculate coordinates for multi-township constituencies.
    
    Args:
        tsp_pcode_string: String containing township codes separated by + (e.g., "MMR001001+MMR001003")
        mimu_coords: Dictionary of township coordinates
        
    Returns:
        Tuple of (lat, lng, source) or (None, None, source) if calculation fails
    """
    if not tsp_pcode_string or '+' not in str(tsp_pcode_string):
        # Single township - use regular lookup
        if tsp_pcode_string in mimu_coords:
            lat, lng = mimu_coords[tsp_pcode_string]
            return lat, lng, 'mimu_boundary_centroid'
        return None, None, 'mimu_pending'
    
    # Multi-township - calculate average of all township centroids
    tsp_codes = str(tsp_pcode_string).split('+')
    valid_coords = []
    
    for tsp_code in tsp_codes:
        tsp_code = tsp_code.strip()
        if tsp_code in mimu_coords:
            valid_coords.append(mimu_coords[tsp_code])
    
    if len(valid_coords) == 0:
        return None, None, 'mimu_pending'
    elif len(valid_coords) < len(tsp_codes):
        # Some townships found, some missing
        sum_lat = sum(coord[0] for coord in valid_coords)
        sum_lng = sum(coord[1] for coord in valid_coords)
        avg_lat = sum_lat / len(valid_coords)
        avg_lng = sum_lng / len(valid_coords)
        return avg_lat, avg_lng, f'mimu_partial_{len(valid_coords)}of{len(tsp_codes)}'
    else:
        # All townships found
        sum_lat = sum(coord[0] for coord in valid_coords)
        sum_lng = sum(coord[1] for coord in valid_coords)
        avg_lat = sum_lat / len(valid_coords)
        avg_lng = sum_lng / len(valid_coords)
        return avg_lat, avg_lng, 'mimu_multi_township_centroid'

def update_heroku_with_mimu_coordinates(connection_string):
    """Update existing Heroku database constituencies with MIMU coordinates."""
    try:
        # Load MIMU coordinates
        mimu_coords = load_mimu_coordinates()
        if not mimu_coords:
            logger.error("❌ No MIMU coordinates available")
            return False
        
        # Connect to Heroku database
        conn = psycopg2.connect(connection_string)
        
        updated = 0
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get all constituencies without coordinates or with approximate coordinates
            cursor.execute("""
                SELECT id, constituency_en, tsp_pcode, lat, lng, coordinate_source
                FROM constituencies 
                WHERE election_year = 2025 
                AND (lat IS NULL OR coordinate_source = 'approximate' OR coordinate_source = 'mimu_pending')
                ORDER BY id
            """)
            
            constituencies = cursor.fetchall()
            logger.info(f"📊 Found {len(constituencies)} constituencies needing MIMU coordinates")
            
            for row in constituencies:
                tsp_pcode = row['tsp_pcode']
                if tsp_pcode and tsp_pcode in mimu_coords:
                    lat, lng = mimu_coords[tsp_pcode]
                    
                    # Update with MIMU coordinates
                    cursor.execute("""
                        UPDATE constituencies 
                        SET lat = %s, lng = %s, coordinate_source = 'mimu_boundary_centroid', updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (lat, lng, row['id']))
                    
                    updated += 1
                    logger.info(f"📍 Updated {row['constituency_en']}: {lat:.4f}, {lng:.4f}")
                    
            conn.commit()
            logger.info(f"✅ Successfully updated {updated} constituencies with MIMU coordinates")
            
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error updating Heroku database: {e}")
        return False

def add_comprehensive_data_to_heroku(connection_string):
    """Add comprehensive constituency data to Heroku database."""
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
        
        # Connect to Heroku database
        conn = psycopg2.connect(connection_string)
        
        # Filter to only non-PTHT assemblies (since PTHT already exists)
        non_ptht_df = df[df['assembly_type'] != 'PTHT']
        logger.info(f"📊 Adding {len(non_ptht_df)} non-PTHT constituencies to Heroku")
        
        inserted = 0
        with conn.cursor() as cursor:
            for _, row in non_ptht_df.iterrows():
                try:
                    # Generate constituency code if missing
                    constituency_code = row.get('constituency_code')
                    if pd.isna(constituency_code) or constituency_code == 'nan':
                        state_abbrev = ''.join([word[0].upper() for word in str(row['state_region_en']).split()[:2]])[0:2]
                        constituency_code = f"{state_abbrev}{row['assembly_type']}-{row['id']:03d}"
                    
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
                        
                        if lat and lng:
                            logger.info(f"📍 Added {row['constituency_en']} ({row['assembly_type']}) with MIMU coords: {lat:.4f}, {lng:.4f}")
                        else:
                            logger.info(f"📍 Added {row['constituency_en']} ({row['assembly_type']}) without coordinates")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error inserting row {row['id']}: {e}")
                    continue
            
            conn.commit()
            logger.info(f"✅ Successfully inserted {inserted} new constituencies to Heroku")
            
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error adding comprehensive data: {e}")
        return False

def main():
    """Main function to update Heroku database."""
    logger.info("🚀 Starting Heroku Database Update with Comprehensive Data...")
    
    connection_string = get_heroku_database_url()
    if not connection_string:
        return False
    
    logger.info("📡 Connected to Heroku database")
    
    # Step 1: Update existing PTHT constituencies with MIMU coordinates
    logger.info("📍 Step 1: Updating existing constituencies with MIMU coordinates...")
    if not update_heroku_with_mimu_coordinates(connection_string):
        logger.error("❌ Failed to update existing constituencies")
        return False
    
    # Step 2: Add comprehensive non-PTHT data
    logger.info("📊 Step 2: Adding comprehensive constituency data...")
    if not add_comprehensive_data_to_heroku(connection_string):
        logger.error("❌ Failed to add comprehensive data")
        return False
    
    # Final verification
    try:
        conn = psycopg2.connect(connection_string)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    assembly_type, 
                    COUNT(*) as count,
                    COUNT(CASE WHEN lat IS NOT NULL THEN 1 END) as mapped_count,
                    COUNT(CASE WHEN coordinate_source = 'mimu_boundary_centroid' THEN 1 END) as mimu_count
                FROM constituencies 
                WHERE election_year = 2025 
                GROUP BY assembly_type 
                ORDER BY assembly_type
            """)
            results = cursor.fetchall()
            
            logger.info("📊 Final Heroku Database Statistics:")
            total = 0
            total_mapped = 0
            total_mimu = 0
            for assembly_type, count, mapped_count, mimu_count in results:
                logger.info(f"  {assembly_type}: {count} constituencies ({mapped_count} mapped, {mimu_count} MIMU)")
                total += count
                total_mapped += mapped_count
                total_mimu += mimu_count
            
            logger.info(f"  TOTAL: {total} constituencies ({total_mapped} mapped, {total_mimu} MIMU-enhanced)")
            
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error getting final statistics: {e}")
    
    logger.info("🎉 Heroku database update finished successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)