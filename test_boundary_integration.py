#!/usr/bin/env python3
"""
Test boundary integration with database
Tests the enhanced boundary service integration with constituency data
"""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / 'src'))

from boundary_service import GeoNodeBoundaryService, BoundaryMatcher
from database import get_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_boundary_integration():
    """Test the boundary service integration"""
    print("🗺️ Testing Boundary Service Integration\n")
    
    # Initialize services
    boundary_service = GeoNodeBoundaryService()
    matcher = BoundaryMatcher(boundary_service)
    db = get_database()
    
    # Test 1: Load local township boundaries
    print("1️⃣ Testing local township boundary loading...")
    townships = boundary_service.load_local_township_boundaries()
    
    if townships:
        features = townships.get('features', [])
        print(f"   ✅ Loaded {len(features)} township boundaries from local file")
        
        # Show sample township data
        if features:
            sample = features[0]['properties']
            print(f"   📊 Sample township: {sample}")
    else:
        print("   ❌ Failed to load local township boundaries")
        return False
    
    # Test 2: Test boundary matching for specific Pcode
    print("\n2️⃣ Testing boundary matching...")
    test_pcode = "MMR001005"  # Sample Pcode
    boundary = matcher.match_constituency(test_pcode)
    
    if boundary:
        print(f"   ✅ Found boundary for {test_pcode}")
        geometry = boundary.get('geometry')
        if geometry:
            lng, lat = matcher.calculate_centroid(geometry)
            print(f"   📍 Centroid: {lng:.6f}, {lat:.6f}")
    else:
        print(f"   ⚠️ No boundary found for {test_pcode}")
    
    # Test 3: Load constituency data from database
    print("\n3️⃣ Loading constituency data from database...")
    try:
        constituencies_df = db.get_constituencies()
        constituencies = constituencies_df.to_dict('records')
        print(f"   📊 Loaded {len(constituencies)} constituencies from database")
        
        # Show some that have tsp_pcode
        with_pcode = [c for c in constituencies if c.get('tsp_pcode')]
        print(f"   🏷️ Constituencies with Pcode: {len(with_pcode)}")
        
        if with_pcode:
            # Show first few examples
            print("   📝 Sample constituencies with Pcode:")
            for i, const in enumerate(with_pcode[:3]):
                print(f"      • {const.get('constituency_mm', 'N/A')} - {const.get('tsp_pcode', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Error loading constituencies: {e}")
        return False
    
    # Test 4: Update coordinates for sample constituencies
    print("\n4️⃣ Testing coordinate updating...")
    try:
        # Test with first 10 constituencies that have tsp_pcode
        test_constituencies = [c for c in constituencies if c.get('tsp_pcode')][:10]
        
        if not test_constituencies:
            print("   ⚠️ No constituencies with Pcode found for testing")
            return True
        
        print(f"   🧪 Testing coordinate updates for {len(test_constituencies)} constituencies")
        
        # Update coordinates using boundary data
        updated_constituencies = matcher.update_constituency_coordinates(test_constituencies)
        
        # Show results
        updated_count = sum(1 for c in updated_constituencies if c.get('coordinate_source') == 'boundary_centroid')
        print(f"   ✅ Updated coordinates for {updated_count} constituencies")
        
        # Show examples of updated coordinates
        if updated_count > 0:
            print("   📍 Sample updated coordinates:")
            for const in updated_constituencies:
                if const.get('coordinate_source') == 'boundary_centroid':
                    print(f"      • {const.get('constituency_mm', 'N/A')[:20]}... -> {const.get('lat'):.6f}, {const.get('lng'):.6f}")
                    break
    
    except Exception as e:
        print(f"   ❌ Error in coordinate updating: {e}")
        logger.exception("Coordinate update error:")
        return False
    
    # Test 5: Test multi-township constituencies
    print("\n5️⃣ Testing multi-township constituencies...")
    multi_township = [c for c in constituencies if c.get('tsp_pcode') and '+' in str(c.get('tsp_pcode', ''))]
    
    if multi_township:
        print(f"   📊 Found {len(multi_township)} multi-township constituencies")
        sample_multi = multi_township[0]
        pcode = sample_multi.get('tsp_pcode', '')
        print(f"   🔗 Sample: {sample_multi.get('constituency_mm', 'N/A')[:30]}... -> {pcode}")
        
        # Test matching
        boundary = matcher.match_constituency(pcode)
        if boundary:
            print(f"   ✅ Successfully matched multi-township boundary")
        else:
            print(f"   ⚠️ Could not match multi-township boundary")
    else:
        print("   📊 No multi-township constituencies found")
    
    print("\n✅ Boundary integration test completed successfully!")
    return True

def main():
    """Run boundary integration tests"""
    success = test_boundary_integration()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)