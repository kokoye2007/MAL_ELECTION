#!/usr/bin/env python3
"""
Analyze mapping between MIMU township boundaries and election constituency data.
"""

import json
import pandas as pd
from pathlib import Path
import sys

# Add src directory to path
sys.path.append(str(Path(__file__).parent / "src"))

def load_mimu_townships():
    """Load MIMU township boundary data."""
    geojson_path = Path(__file__).parent / "data" / "geojson" / "myanmar_townships_mimu.geojson"
    with open(geojson_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_election_data():
    """Load election constituency data."""
    csv_path = Path(__file__).parent / "data" / "processed" / "myanmar_constituencies.csv"
    return pd.read_csv(csv_path)

def analyze_mapping():
    """Analyze the mapping between MIMU and election data."""
    
    print("🔍 Analyzing MIMU Township Boundaries vs Election Constituencies")
    print("=" * 70)
    
    # Load data
    mimu_data = load_mimu_townships()
    election_df = load_election_data()
    
    print(f"📊 MIMU Townships: {mimu_data['totalFeatures']}")
    print(f"📊 Election Constituencies: {len(election_df)}")
    print()
    
    # Extract MIMU township info
    mimu_townships = []
    for feature in mimu_data['features']:
        props = feature['properties']
        mimu_townships.append({
            'TS_PCODE': props.get('TS_PCODE'),
            'TS': props.get('TS'),
            'TS_MMR': props.get('TS_MMR'),
            'ST': props.get('ST'),
            'DT': props.get('DT'),
            'geometry': feature['geometry']
        })
    
    mimu_df = pd.DataFrame(mimu_townships)
    
    print("🗺️ Sample MIMU Townships:")
    print(mimu_df[['TS_PCODE', 'TS', 'TS_MMR', 'ST', 'DT']].head(10).to_string(index=False))
    print()
    
    print("🗳️ Sample Election Constituencies:")
    print(election_df[['constituency_en', 'constituency_mm', 'state_region_en']].head(10).to_string(index=False))
    print()
    
    # Analyze name matching
    print("🔍 Name Matching Analysis:")
    print("-" * 30)
    
    # Try to match by English township names
    election_townships = set(election_df['constituency_en'].str.replace(' Township', '').str.strip())
    mimu_townships_en = set(mimu_df['TS'].str.strip())
    
    matches = election_townships.intersection(mimu_townships_en)
    election_only = election_townships - mimu_townships_en
    mimu_only = mimu_townships_en - election_townships
    
    print(f"✅ Direct English name matches: {len(matches)}")
    print(f"📋 Election constituencies without MIMU match: {len(election_only)}")
    print(f"🗺️ MIMU townships without election match: {len(mimu_only)}")
    print()
    
    if len(matches) > 0:
        print("✅ Sample matches:")
        for match in sorted(list(matches))[:10]:
            print(f"   - {match}")
        print()
    
    if len(election_only) > 0:
        print("📋 Election constituencies without MIMU match (first 10):")
        for item in sorted(list(election_only))[:10]:
            print(f"   - {item}")
        print()
    
    if len(mimu_only) > 0:
        print("🗺️ MIMU townships without election match (first 10):")
        for item in sorted(list(mimu_only))[:10]:
            print(f"   - {item}")
        print()
    
    # Analysis by state/region
    print("🏛️ State/Region Analysis:")
    print("-" * 25)
    
    election_states = set(election_df['state_region_en'])
    mimu_states = set(mimu_df['ST'])
    
    state_matches = election_states.intersection(mimu_states)
    
    print(f"✅ State/Region matches: {len(state_matches)}")
    print(f"📊 Election states: {sorted(election_states)}")
    print(f"🗺️ MIMU states: {sorted(mimu_states)}")
    print()
    
    # Create mapping recommendations
    print("💡 Mapping Strategy Recommendations:")
    print("-" * 35)
    
    match_rate = (len(matches) / len(election_townships)) * 100
    print(f"📈 Direct name match rate: {match_rate:.1f}%")
    
    if match_rate > 80:
        print("✅ EXCELLENT: High match rate - can use direct name mapping")
    elif match_rate > 60:
        print("⚠️ GOOD: Moderate match rate - needs fuzzy matching for remaining")
    else:
        print("❌ POOR: Low match rate - needs comprehensive mapping table")
    
    print()
    print("🔧 Recommended Implementation Approach:")
    if match_rate > 60:
        print("1. Use direct name matching for matched townships")
        print("2. Create manual mapping table for unmatched townships") 
        print("3. Use MIMU geometries for constituencies with matches")
        print("4. Fall back to generated boundaries for unmatched")
    else:
        print("1. Create comprehensive manual mapping table")
        print("2. Consider alternative matching strategies (Myanmar names, fuzzy matching)")
        print("3. Validate geographic proximity for matches")
    
    return {
        'mimu_df': mimu_df,
        'election_df': election_df,
        'matches': matches,
        'election_only': election_only,
        'mimu_only': mimu_only,
        'match_rate': match_rate
    }

if __name__ == "__main__":
    results = analyze_mapping()