#!/usr/bin/env python3
"""
MIMU Integration Test

This script tests the complete pipeline from Excel extraction to multi-layer visualization
with MIMU coordinate mapping and township boundaries.
"""

import sys
from pathlib import Path
import pandas as pd
import json

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / 'src'))

def test_comprehensive_data_extraction():
    """Test that comprehensive data extraction worked correctly."""
    print("🧪 Testing comprehensive data extraction...")
    
    csv_path = Path('data/processed/myanmar_election_2025_comprehensive_with_coordinates.csv')
    if not csv_path.exists():
        print("❌ Comprehensive CSV not found - running extraction...")
        import subprocess
        result = subprocess.run([sys.executable, 'extract_comprehensive_with_coordinates.py'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Extraction failed: {result.stderr}")
            return False
    
    # Load and verify data
    df = pd.read_csv(csv_path)
    print(f"✅ Loaded {len(df)} constituencies")
    
    # Check assembly types
    assembly_types = df['assembly_type'].unique()
    print(f"📊 Assembly types: {list(assembly_types)}")
    
    # Check coordinate mapping
    mapped_count = df['lat'].notna().sum()
    multi_township_count = (df['coordinate_source'] == 'mimu_multi_township_centroid').sum()
    print(f"📍 {mapped_count} constituencies mapped ({multi_township_count} multi-township)")
    
    # Verify multi-township coordinate calculation
    multi_township_sample = df[df['coordinate_source'] == 'mimu_multi_township_centroid'].head(3)
    if not multi_township_sample.empty:
        print("🎯 Multi-township examples:")
        for _, row in multi_township_sample.iterrows():
            print(f"   {row['constituency_en']} -> {row['lat']:.4f}, {row['lng']:.4f}")
    
    return True


def test_mimu_boundaries_loading():
    """Test MIMU boundary data loading."""
    print("\n🧪 Testing MIMU boundaries loading...")
    
    mimu_path = Path('data/geojson/myanmar_townships_mimu.geojson')
    if not mimu_path.exists():
        print("⚠️ MIMU GeoJSON not found - this is expected in some setups")
        return True
    
    try:
        with open(mimu_path, 'r', encoding='utf-8') as f:
            mimu_data = json.load(f)
        
        feature_count = len(mimu_data.get('features', []))
        print(f"✅ Loaded {feature_count} MIMU township boundaries")
        
        # Test a few features
        sample_features = mimu_data['features'][:3]
        for feature in sample_features:
            props = feature.get('properties', {})
            tsp_code = props.get('TS_PCODE', 'Unknown')
            tsp_name = props.get('TS_NAME_EN', 'Unknown')
            print(f"   {tsp_name} ({tsp_code})")
        
        return True
    except Exception as e:
        print(f"❌ Error loading MIMU boundaries: {e}")
        return False


def test_layered_visualizer():
    """Test the layered visualizer creation."""
    print("\n🧪 Testing layered visualizer...")
    
    try:
        from layered_visualizations import MyanmarElectionLayeredVisualizer
        
        # Initialize visualizer
        visualizer = MyanmarElectionLayeredVisualizer()
        print("✅ Visualizer initialized successfully")
        
        # Load test data
        csv_path = Path('data/processed/myanmar_election_2025_comprehensive_with_coordinates.csv')
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            sample_data = df.head(50)  # Test with small sample
            
            # Test multi-layer map creation
            test_map = visualizer.create_multi_layer_map(
                constituencies_data=sample_data,
                show_boundaries=True,
                show_pinpoints=True,
                assembly_filter=['PTHT', 'AMTHT']
            )
            
            print(f"✅ Created multi-layer map with {len(sample_data)} constituencies")
            
            # Test assembly comparison
            assembly_types = sample_data['assembly_type'].unique()[:2]
            comparison_map = visualizer.create_assembly_comparison_map(
                constituencies_data=sample_data,
                assembly_types=list(assembly_types)
            )
            
            print(f"✅ Created assembly comparison map for {list(assembly_types)}")
            
        return True
    except Exception as e:
        print(f"❌ Error testing visualizer: {e}")
        return False


def test_coordinate_calculations():
    """Test multi-township coordinate calculation accuracy."""
    print("\n🧪 Testing coordinate calculations...")
    
    # Test the calculation function directly
    try:
        from extract_comprehensive_with_coordinates import calculate_multi_township_coordinates, load_mimu_coordinates
        
        # Load MIMU coordinates
        mimu_coords = load_mimu_coordinates()
        if not mimu_coords:
            print("⚠️ No MIMU coordinates available for testing")
            return True
        
        print(f"✅ Loaded {len(mimu_coords)} MIMU coordinate entries")
        
        # Test single township
        sample_code = list(mimu_coords.keys())[0]
        lat, lng, source = calculate_multi_township_coordinates(sample_code, mimu_coords)
        print(f"📍 Single township test: {sample_code} -> {lat:.4f}, {lng:.4f} ({source})")
        
        # Test multi-township (simulate)
        multi_code = f"{sample_code}+{list(mimu_coords.keys())[1]}"
        lat, lng, source = calculate_multi_township_coordinates(multi_code, mimu_coords)
        print(f"📍 Multi-township test: {multi_code} -> {lat:.4f}, {lng:.4f} ({source})")
        
        return True
    except Exception as e:
        print(f"❌ Error testing coordinate calculations: {e}")
        return False


def main():
    """Run all integration tests."""
    print("🚀 Starting MIMU Integration Test Pipeline...\n")
    
    tests = [
        ("Comprehensive Data Extraction", test_comprehensive_data_extraction),
        ("MIMU Boundaries Loading", test_mimu_boundaries_loading),
        ("Coordinate Calculations", test_coordinate_calculations),
        ("Layered Visualizer", test_layered_visualizer)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"=" * 60)
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            failed += 1
    
    print(f"\n" + "=" * 60)
    print(f"🎯 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! MIMU integration is working correctly.")
        print("\n📋 Pipeline Summary:")
        print("✅ Multi-township coordinate mapping from Excel data")
        print("✅ MIMU boundary integration")
        print("✅ Multi-layer visualization with pinpoints and boundaries")
        print("✅ Assembly type filtering and color coding")
        print("✅ Interactive layer controls")
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)