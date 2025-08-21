#!/usr/bin/env python3
"""
Update constituency coordinates using boundary data
Production script to improve coordinate accuracy using GeoJSON boundary centroids
"""

import json
import sys
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def update_constituency_coordinates():
    """Update constituency coordinates using boundary data"""
    print("🗺️ Updating Constituency Coordinates from Boundary Data\\n")
    
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
    
    # Load constituency data
    print("\\n2️⃣ Loading constituency data...")
    processed_path = Path("data/processed/myanmar_election_2025.json")
    
    if not processed_path.exists():
        print(f"❌ Constituency data not found: {processed_path}")
        return False
    
    with open(processed_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    constituencies = data.get('constituencies', [])
    print(f"   📊 Loaded {len(constituencies)} constituencies")
    
    # Update coordinates
    print("\\n3️⃣ Updating coordinates...")
    
    updated_count = 0
    improved_count = 0
    new_coordinates_count = 0
    failed_count = 0
    
    for constituency in constituencies:
        tsp_pcode = constituency.get('tsp_pcode')
        
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
                    old_lat = constituency.get('lat')
                    old_lng = constituency.get('lng')
                    
                    # Update coordinates
                    constituency['lat'] = new_lat
                    constituency['lng'] = new_lng
                    constituency['coordinate_source'] = 'boundary_centroid'
                    
                    if old_lat and old_lng:
                        # Calculate improvement
                        distance_change = ((new_lat - old_lat)**2 + (new_lng - old_lng)**2)**0.5
                        if distance_change > 0.01:  # Significant improvement (>0.01 degrees ≈ 1km)
                            improved_count += 1
                    else:
                        new_coordinates_count += 1
                    
                    updated_count += 1
                else:
                    failed_count += 1
            else:
                failed_count += 1
        else:
            # No boundary found for this Pcode
            pass
    
    print(f"   ✅ Updated coordinates for {updated_count} constituencies")
    print(f"   📈 Significant improvements: {improved_count}")
    print(f"   🆕 New coordinates added: {new_coordinates_count}")
    print(f"   ⚠️ Failed updates: {failed_count}")
    
    # Update metadata
    if 'metadata' in data:
        data['metadata']['coordinate_update'] = {
            'boundary_source': 'myanmar_townships_mimu.geojson',
            'updated_constituencies': updated_count,
            'improved_coordinates': improved_count,
            'new_coordinates': new_coordinates_count
        }
    
    # Save updated data
    print("\\n4️⃣ Saving updated data...")
    
    # Backup original
    backup_path = processed_path.with_suffix('.backup.json')
    if not backup_path.exists():
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        print(f"   💾 Created backup: {backup_path}")
    
    # Save updated version
    with open(processed_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"   ✅ Updated data saved to: {processed_path}")
    
    # Generate summary
    print("\\n5️⃣ Update Summary:")
    total_with_pcode = len([c for c in constituencies if c.get('tsp_pcode')])
    success_rate = (updated_count / total_with_pcode) * 100 if total_with_pcode > 0 else 0
    
    print(f"   📊 Constituencies with Pcode: {total_with_pcode}")
    print(f"   ✅ Successfully updated: {updated_count} ({success_rate:.1f}%)")
    print(f"   📍 Coordinates significantly improved: {improved_count}")
    print(f"   🆕 New coordinates assigned: {new_coordinates_count}")
    
    # Show coordinate source breakdown
    coordinate_sources = {}
    for const in constituencies:
        source = const.get('coordinate_source', 'unknown')
        coordinate_sources[source] = coordinate_sources.get(source, 0) + 1
    
    print("\\n   📈 Coordinate sources after update:")
    for source, count in sorted(coordinate_sources.items()):
        print(f"      • {source}: {count}")
    
    print("\\n✅ Coordinate update completed successfully!")
    
    return True

def main():
    """Main function"""
    try:
        success = update_constituency_coordinates()
        return success
    except Exception as e:
        logger.error(f"Error updating coordinates: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)