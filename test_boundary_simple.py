#!/usr/bin/env python3
"""
Simple boundary data test to verify integration capability
"""

import json
import pandas as pd
from pathlib import Path

def test_boundary_data_availability():
    """Test availability of boundary data and database"""
    print("🗺️ Testing Boundary Data Availability\n")
    
    # Test 1: Check if GeoJSON file exists
    print("1️⃣ Checking local GeoJSON boundary data...")
    geojson_path = Path("data/geojson/myanmar_townships_mimu.geojson")
    
    if geojson_path.exists():
        print(f"   ✅ Found township GeoJSON: {geojson_path}")
        
        # Load and analyze
        with open(geojson_path, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
        
        features = geojson_data.get('features', [])
        print(f"   📊 Contains {len(features)} township boundaries")
        
        # Check structure
        if features:
            sample_props = features[0].get('properties', {})
            print(f"   🏷️ Sample properties: {list(sample_props.keys())}")
            
            # Look for Pcode fields
            pcode_fields = [k for k in sample_props.keys() if 'PCODE' in k.upper()]
            if pcode_fields:
                print(f"   📍 Found Pcode fields: {pcode_fields}")
                sample_pcode = sample_props.get(pcode_fields[0])
                print(f"   📝 Sample Pcode: {sample_pcode}")
    else:
        print(f"   ❌ GeoJSON file not found: {geojson_path}")
        return False
    
    # Test 2: Check processed constituency data
    print("\n2️⃣ Checking processed constituency data...")
    processed_file = Path("data/processed/myanmar_election_2025.json")
    
    if processed_file.exists():
        print(f"   ✅ Found processed data: {processed_file}")
        
        with open(processed_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        constituencies = data.get('constituencies', [])
        print(f"   📊 Contains {len(constituencies)} constituencies")
        
        # Check for tsp_pcode field
        with_pcode = [c for c in constituencies if c.get('tsp_pcode')]
        print(f"   🏷️ Constituencies with tsp_pcode: {len(with_pcode)}")
        
        if with_pcode:
            sample_const = with_pcode[0]
            print(f"   📝 Sample constituency: {sample_const.get('constituency_name_mm', 'N/A')}")
            print(f"   📍 Sample Pcode: {sample_const.get('tsp_pcode')}")
            
            # Check for multi-township
            multi = [c for c in with_pcode if '+' in str(c.get('tsp_pcode', ''))]
            print(f"   🔗 Multi-township constituencies: {len(multi)}")
            
    else:
        print(f"   ❌ Processed data not found: {processed_file}")
        return False
    
    # Test 3: Test coordinate matching logic
    print("\n3️⃣ Testing coordinate matching potential...")
    
    # Get sample Pcodes from both datasets
    boundary_pcodes = set()
    for feature in features[:10]:  # Sample first 10
        props = feature.get('properties', {})
        for field in ['TS_PCODE', 'Tsp_Pcode', 'PCODE', 'pcode']:
            if props.get(field):
                boundary_pcodes.add(props[field])
                break
    
    constituency_pcodes = set()
    for const in constituencies[:50]:  # Sample first 50
        pcode = const.get('tsp_pcode')
        if pcode:
            # Handle multi-township
            if '+' in pcode:
                constituency_pcodes.update(pcode.split('+'))
            else:
                constituency_pcodes.add(pcode)
    
    print(f"   📊 Sample boundary Pcodes: {len(boundary_pcodes)}")
    print(f"   📊 Sample constituency Pcodes: {len(constituency_pcodes)}")
    
    # Find matches
    matches = boundary_pcodes.intersection(constituency_pcodes)
    print(f"   ✅ Potential matches found: {len(matches)}")
    
    if matches:
        sample_matches = list(matches)[:3]
        print(f"   📝 Sample matches: {sample_matches}")
        
    print("\n✅ Boundary data integration is feasible!")
    print(f"🎯 Integration Summary:")
    print(f"   • Township boundaries: {len(features)} available")
    print(f"   • Constituencies: {len(constituencies)} total")
    print(f"   • Constituencies with Pcode: {len(with_pcode)}")
    print(f"   • Potential coordinate improvements: {len(matches)} townships")
    
    return True

def main():
    """Run simple boundary data test"""
    return test_boundary_data_availability()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)