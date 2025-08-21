#!/usr/bin/env python3
"""
Test coordinate updating using boundary data
Demonstrates improved constituency coordinate calculation
"""

import json
from pathlib import Path
from typing import Dict, Tuple, Optional

def calculate_centroid(geometry: Dict) -> Tuple[Optional[float], Optional[float]]:
    """Calculate centroid of a geometry (simplified version)"""
    if geometry.get("type") == "Point":
        coords = geometry.get("coordinates", [])
        return coords[0], coords[1]
    
    elif geometry.get("type") == "Polygon":
        # Simple centroid calculation
        coords = geometry.get("coordinates", [[]])[0]
        if not coords:
            return None, None
            
        lngs = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        
        return sum(lngs) / len(lngs), sum(lats) / len(lats)
    
    elif geometry.get("type") == "MultiPolygon":
        # Average of polygon centroids
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

def test_coordinate_updating():
    """Test coordinate updating using boundary data"""
    print("📍 Testing Coordinate Update Capability\n")
    
    # Load boundary data
    print("1️⃣ Loading boundary data...")
    geojson_path = Path("data/geojson/myanmar_townships_mimu.geojson")
    
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
    print("\n2️⃣ Loading constituency data...")
    processed_path = Path("data/processed/myanmar_election_2025.json")
    
    with open(processed_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    constituencies = data.get('constituencies', [])
    constituencies_with_pcode = [c for c in constituencies if c.get('tsp_pcode')]
    
    print(f"   📊 Found {len(constituencies_with_pcode)} constituencies with Pcode")
    
    # Test coordinate updating
    print("\n3️⃣ Testing coordinate updates...")
    
    updated_count = 0
    coordinate_improvements = []
    
    # Test first 20 constituencies
    for constituency in constituencies_with_pcode[:20]:
        tsp_pcode = constituency.get('tsp_pcode')
        current_lat = constituency.get('lat')
        current_lng = constituency.get('lng')
        
        # Find boundary
        boundary_feature = boundary_index.get(tsp_pcode)
        
        if boundary_feature:
            # Calculate centroid from boundary
            geometry = boundary_feature.get('geometry')
            if geometry:
                new_lng, new_lat = calculate_centroid(geometry)
                
                if new_lng and new_lat:
                    # Calculate improvement (distance difference)
                    if current_lat and current_lng:
                        lat_diff = abs(new_lat - current_lat)
                        lng_diff = abs(new_lng - current_lng)
                        distance_change = (lat_diff**2 + lng_diff**2)**0.5
                        
                        coordinate_improvements.append({
                            'constituency': constituency.get('constituency_name_mm', 'N/A')[:30],
                            'tsp_pcode': tsp_pcode,
                            'old_coords': f"{current_lat:.6f}, {current_lng:.6f}",
                            'new_coords': f"{new_lat:.6f}, {new_lng:.6f}",
                            'improvement': distance_change
                        })
                    else:
                        coordinate_improvements.append({
                            'constituency': constituency.get('constituency_name_mm', 'N/A')[:30],
                            'tsp_pcode': tsp_pcode,
                            'old_coords': "No coordinates",
                            'new_coords': f"{new_lat:.6f}, {new_lng:.6f}",
                            'improvement': "New coordinates"
                        })
                    
                    updated_count += 1
    
    print(f"   ✅ Successfully calculated new coordinates for {updated_count} constituencies")
    
    # Show results
    if coordinate_improvements:
        print("\n4️⃣ Coordinate Update Results:")
        print("   📊 Sample improvements:")
        
        for i, improvement in enumerate(coordinate_improvements[:5]):
            print(f"      {i+1}. {improvement['constituency']}...")
            print(f"         Pcode: {improvement['tsp_pcode']}")
            print(f"         Old: {improvement['old_coords']}")
            print(f"         New: {improvement['new_coords']}")
            if isinstance(improvement['improvement'], float):
                print(f"         Distance change: {improvement['improvement']:.6f} degrees")
            else:
                print(f"         Status: {improvement['improvement']}")
            print()
    
    # Calculate statistics
    print("5️⃣ Integration Statistics:")
    total_constituencies = len(constituencies)
    with_pcode = len(constituencies_with_pcode)
    potential_updates = updated_count
    coverage_percent = (with_pcode / total_constituencies) * 100
    
    print(f"   📈 Total constituencies: {total_constituencies}")
    print(f"   🏷️ Constituencies with Pcode: {with_pcode} ({coverage_percent:.1f}%)")
    print(f"   🎯 Successful boundary matches: {potential_updates}")
    print(f"   📍 Coordinate update success rate: {(potential_updates/with_pcode)*100:.1f}%")
    
    # Show boundary data coverage by state
    print("\n6️⃣ Coverage by Assembly Type:")
    assembly_stats = {}
    for const in constituencies_with_pcode:
        assembly = const.get('assembly_type', 'Unknown')
        assembly_stats[assembly] = assembly_stats.get(assembly, 0) + 1
    
    for assembly, count in sorted(assembly_stats.items()):
        print(f"   • {assembly}: {count} constituencies")
    
    print("\n✅ Coordinate updating test completed!")
    print(f"🎯 Boundary integration will improve coordinates for {potential_updates} constituencies")
    
    return True

def main():
    """Run coordinate update test"""
    return test_coordinate_updating()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)