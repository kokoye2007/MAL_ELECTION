#!/usr/bin/env python3
"""
Update database coordinates using boundary data
Updates the PostgreSQL database directly with boundary-based coordinates
"""

import json
import os
import sys
import psycopg2
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging

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

def calculate_centroid(geometry: Dict) -> Tuple[Optional[float], Optional[float]]:
    """Calculate centroid of a geometry"""
    if geometry.get("type") == "Point":
        coords = geometry.get("coordinates", [])
        return coords[0], coords[1]
    
    elif geometry.get("type") == "Polygon":
        coords = geometry.get("coordinates", [[]])[0]
        if not coords:
            return None, None
            
        lngs = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        
        return sum(lngs) / len(lngs), sum(lats) / len(lats)
    
    elif geometry.get("type") == "MultiPolygon":
        centroids = []
        for polygon in geometry.get("coordinates", []):
            if polygon and polygon[0]:
                lngs = [c[0] for c in polygon[0]]
                lats = [c[1] for c in polygon[0]]
                centroids.append((
                    sum(lngs) / len(lngs),
                    sum(lats) / len(lats)
                ))
        
        if centroids:
            avg_lng = sum(c[0] for c in centroids) / len(centroids)
            avg_lat = sum(c[1] for c in centroids) / len(centroids)
            return avg_lng, avg_lat
    
    return None, None

def update_database_coordinates():
    """Update constituency coordinates in the database using boundary data"""
    print("🗺️ Updating Database Coordinates from Boundary Data\n")
    
    # Load boundary data
    print("1️⃣ Loading township boundary data...")
    geojson_path = Path("data/geojson/myanmar_townships_mimu.geojson")
    
    if not geojson_path.exists():
        print(f"❌ Boundary data not found: {geojson_path}")
        return False
    
    with open(geojson_path, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)
    
    # Index boundaries by TS_PCODE
    boundary_index = {}
    for feature in geojson_data.get('features', []):
        props = feature.get('properties', {})
        ts_pcode = props.get('TS_PCODE')
        if ts_pcode:
            boundary_index[ts_pcode] = feature
    
    print(f"   ✅ Indexed {len(boundary_index)} township boundaries")
    
    # Connect to database
    print("\n2️⃣ Connecting to database...")
    connection_string = get_database_url()
    conn = psycopg2.connect(connection_string)
    cursor = conn.cursor()
    
    # Get constituencies with township codes
    print("\n3️⃣ Loading constituencies from database...")
    cursor.execute("""
        SELECT id, constituency_mm, tsp_pcode, lat, lng, coordinate_source
        FROM constituencies 
        WHERE election_year = 2025 
        ORDER BY id
    """)
    
    constituencies = cursor.fetchall()
    print(f"   📊 Found {len(constituencies)} constituencies")
    
    # Update coordinates
    print("\n4️⃣ Updating coordinates...")
    
    updated_count = 0
    improved_count = 0
    new_coordinates_count = 0
    failed_count = 0
    
    for const_id, name, tsp_pcode, current_lat, current_lng, coord_source in constituencies:
        
        if not tsp_pcode:
            continue
            
        # Handle multi-township constituencies
        pcodes_to_check = tsp_pcode.split('+') if '+' in tsp_pcode else [tsp_pcode]
        
        # Find boundary for first matching Pcode
        boundary_feature = None
        for pcode in pcodes_to_check:
            if pcode in boundary_index:
                boundary_feature = boundary_index[pcode]
                break
        
        if boundary_feature:
            geometry = boundary_feature.get('geometry')
            if geometry:
                new_lng, new_lat = calculate_centroid(geometry)
                
                if new_lng and new_lat:
                    # Update coordinates in database
                    cursor.execute("""
                        UPDATE constituencies 
                        SET lat = %s, lng = %s, coordinate_source = 'boundary_centroid'
                        WHERE id = %s
                    """, (new_lat, new_lng, const_id))
                    
                    if current_lat and current_lng:
                        # Calculate improvement (convert Decimal to float for calculation)
                        lat_diff = float(new_lat) - float(current_lat)
                        lng_diff = float(new_lng) - float(current_lng)
                        distance_change = (lat_diff**2 + lng_diff**2)**0.5
                        if distance_change > 0.01:  # Significant improvement (>0.01 degrees ≈ 1km)
                            improved_count += 1
                    else:
                        new_coordinates_count += 1
                    
                    updated_count += 1
                    
                    if updated_count % 50 == 0:
                        print(f"   📍 Updated {updated_count} constituencies...")
                else:
                    failed_count += 1
            else:
                failed_count += 1
        else:
            # No boundary found for this Pcode
            pass
    
    # Commit changes
    conn.commit()
    
    print(f"\n✅ Database update completed:")
    print(f"   📍 Updated coordinates: {updated_count}")
    print(f"   📈 Significant improvements: {improved_count}")
    print(f"   🆕 New coordinates: {new_coordinates_count}")
    print(f"   ⚠️ Failed updates: {failed_count}")
    
    # Verify results
    print("\n5️⃣ Verifying database updates...")
    cursor.execute("""
        SELECT coordinate_source, COUNT(*) 
        FROM constituencies 
        WHERE election_year = 2025 
        GROUP BY coordinate_source
        ORDER BY COUNT(*) DESC
    """)
    
    coord_stats = cursor.fetchall()
    print("   📊 Coordinate sources after update:")
    for source, count in coord_stats:
        print(f"      • {source}: {count}")
    
    conn.close()
    
    print("\n✅ Database coordinate update completed successfully!")
    
    return True

def main():
    """Main function"""
    try:
        success = update_database_coordinates()
        return success
    except Exception as e:
        logger.error(f"Error updating database coordinates: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)