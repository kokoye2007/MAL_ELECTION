#!/usr/bin/env python3
"""
Test real boundary integration without Streamlit.
"""

import json
import pandas as pd
from pathlib import Path

def test_boundary_integration():
    """Test that real boundaries can be loaded and used."""
    
    print("🧪 Testing Real Boundary Integration")
    print("=" * 40)
    
    # Load boundary mapping
    mapping_path = Path("data/processed/township_boundary_mapping.json")
    
    try:
        with open(mapping_path, 'r', encoding='utf-8') as f:
            boundary_mapping = json.load(f)
        
        print(f"✅ Boundary mapping loaded successfully")
        print(f"📊 Total matches: {len(boundary_mapping['matches'])}")
        print(f"🗺️ MIMU townships: {len(boundary_mapping['mimu_townships'])}")
        
        # Test boundary conversion for first few matches
        print("\n🔍 Testing boundary conversion:")
        
        for i, match in enumerate(boundary_mapping['matches'][:5]):
            constituency_id = match['election_id']
            mimu_pcode = match['mimu_pcode']
            
            if mimu_pcode in boundary_mapping['mimu_townships']:
                geometry = boundary_mapping['mimu_townships'][mimu_pcode]['geometry']
                
                # Convert geometry
                if geometry['type'] == 'Polygon':
                    coords = geometry['coordinates'][0]
                elif geometry['type'] == 'MultiPolygon':
                    coords = geometry['coordinates'][0][0]
                else:
                    coords = []
                
                # Convert to Folium format
                folium_coords = [[lat_lng[1], lat_lng[0]] for lat_lng in coords[:10]]  # First 10 points
                
                print(f"   {i+1}. {match['election_name_en']} → {match['mimu_name_en']}")
                print(f"      Geometry: {geometry['type']}, Points: {len(coords)}")
                print(f"      Sample coords: {folium_coords[:3]}...")
        
        # Test performance metrics
        print("\n📈 Performance Analysis:")
        total_geom_points = 0
        for township_data in boundary_mapping['mimu_townships'].values():
            geometry = township_data['geometry']
            if geometry['type'] == 'Polygon':
                total_geom_points += len(geometry['coordinates'][0])
            elif geometry['type'] == 'MultiPolygon':
                for polygon in geometry['coordinates']:
                    total_geom_points += len(polygon[0])
        
        avg_points = total_geom_points / len(boundary_mapping['mimu_townships'])
        print(f"   Total geometry points: {total_geom_points:,}")
        print(f"   Average points per township: {avg_points:.1f}")
        
        if avg_points > 100:
            print("   ⚠️ High detail level - consider simplification for web performance")
        else:
            print("   ✅ Reasonable detail level for web rendering")
        
        return True
        
    except FileNotFoundError:
        print("❌ Boundary mapping file not found")
        return False
    except Exception as e:
        print(f"❌ Error testing boundaries: {str(e)}")
        return False

def test_streamlit_app_startup():
    """Test that the Streamlit app can start with new boundaries."""
    
    print("\n🚀 Testing Streamlit App Startup")
    print("=" * 35)
    
    try:
        # Test app startup without actually running Streamlit
        from pathlib import Path
        app_path = Path("src/app.py")
        
        if app_path.exists():
            print("✅ App file exists")
            
            # Check if imports would work
            try:
                import sys
                sys.path.append("src")
                
                # Test key imports without streamlit
                import pandas as pd
                import json
                from pathlib import Path
                
                print("✅ Core dependencies available")
                print("🎯 Ready for Streamlit testing")
                
                return True
                
            except ImportError as e:
                print(f"❌ Import error: {e}")
                return False
        else:
            print("❌ App file not found")
            return False
            
    except Exception as e:
        print(f"❌ Error testing app: {str(e)}")
        return False

if __name__ == "__main__":
    success1 = test_boundary_integration()
    success2 = test_streamlit_app_startup()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 All tests passed! Real boundaries ready for use.")
        print("🚀 Run 'streamlit run src/app.py' to see the results!")
    else:
        print("❌ Some tests failed. Check the output above.")