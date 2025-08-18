#!/usr/bin/env python3
"""
Create mapping between MIMU township boundaries and election constituency data.
"""

import json
import pandas as pd
from pathlib import Path
import sys
from difflib import SequenceMatcher

# Add src directory to path
sys.path.append(str(Path(__file__).parent / "src"))

def similarity(a, b):
    """Calculate similarity between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def load_data():
    """Load both datasets."""
    # Load MIMU data
    geojson_path = Path(__file__).parent / "data" / "geojson" / "myanmar_townships_mimu.geojson"
    with open(geojson_path, 'r', encoding='utf-8') as f:
        mimu_data = json.load(f)
    
    # Load election data
    csv_path = Path(__file__).parent / "data" / "processed" / "myanmar_constituencies.csv"
    election_df = pd.read_csv(csv_path)
    
    return mimu_data, election_df

def create_mapping():
    """Create mapping between datasets using multiple strategies."""
    
    mimu_data, election_df = load_data()
    
    print("🔗 Creating Township Boundary Mapping")
    print("=" * 50)
    
    # Extract MIMU data into structured format
    mimu_townships = {}
    for feature in mimu_data['features']:
        props = feature['properties']
        township_name = props.get('TS', '')
        township_mmr = props.get('TS_MMR', '')
        
        mimu_townships[props.get('TS_PCODE')] = {
            'name_en': township_name,
            'name_mmr': township_mmr,
            'state': props.get('ST', ''),
            'district': props.get('DT', ''),
            'pcode': props.get('TS_PCODE'),
            'geometry': feature['geometry']
        }
    
    # Clean election constituency names for matching
    election_df['constituency_clean'] = election_df['constituency_en'].str.replace(' Township', '').str.strip()
    
    # Strategy 1: Try Myanmar script matching
    print("🔍 Strategy 1: Myanmar Script Matching")
    myanmar_matches = []
    
    for idx, row in election_df.iterrows():
        election_mmr = row['constituency_mm'].replace('မြို့နယ်', '').strip()
        
        best_match = None
        best_score = 0
        
        for pcode, township in mimu_townships.items():
            if township['name_mmr'] and election_mmr:
                score = similarity(election_mmr, township['name_mmr'])
                if score > best_score and score > 0.8:  # High threshold for Myanmar text
                    best_score = score
                    best_match = pcode
        
        if best_match:
            myanmar_matches.append({
                'election_id': row['id'],
                'election_name_en': row['constituency_en'],
                'election_name_mm': row['constituency_mm'],
                'mimu_pcode': best_match,
                'mimu_name_en': mimu_townships[best_match]['name_en'],
                'mimu_name_mmr': mimu_townships[best_match]['name_mmr'],
                'score': best_score,
                'match_type': 'myanmar_script'
            })
    
    print(f"✅ Myanmar script matches: {len(myanmar_matches)}")
    
    # Strategy 2: Fuzzy English matching for remaining
    print("\n🔍 Strategy 2: Fuzzy English Matching")
    matched_election_ids = set([m['election_id'] for m in myanmar_matches])
    matched_mimu_pcodes = set([m['mimu_pcode'] for m in myanmar_matches])
    
    english_matches = []
    
    for idx, row in election_df.iterrows():
        if row['id'] in matched_election_ids:
            continue
            
        election_clean = row['constituency_clean']
        
        best_match = None
        best_score = 0
        
        for pcode, township in mimu_townships.items():
            if pcode in matched_mimu_pcodes:
                continue
                
            score = similarity(election_clean, township['name_en'])
            if score > best_score and score > 0.7:  # Lower threshold for English fuzzy matching
                best_score = score
                best_match = pcode
        
        if best_match:
            english_matches.append({
                'election_id': row['id'],
                'election_name_en': row['constituency_en'],
                'election_name_mm': row['constituency_mm'],
                'mimu_pcode': best_match,
                'mimu_name_en': mimu_townships[best_match]['name_en'],
                'mimu_name_mmr': mimu_townships[best_match]['name_mmr'],
                'score': best_score,
                'match_type': 'english_fuzzy'
            })
    
    print(f"✅ English fuzzy matches: {len(english_matches)}")
    
    # Combine all matches
    all_matches = myanmar_matches + english_matches
    total_matched = len(all_matches)
    total_constituencies = len(election_df)
    
    print(f"\n📊 Total matches: {total_matched}/{total_constituencies} ({(total_matched/total_constituencies)*100:.1f}%)")
    
    # Show sample matches
    if all_matches:
        print("\n✅ Sample successful matches:")
        for match in all_matches[:10]:
            print(f"   {match['election_name_en']} ↔ {match['mimu_name_en']} (score: {match['score']:.2f}, {match['match_type']})")
    
    # Find unmatched
    unmatched_election = election_df[~election_df['id'].isin([m['election_id'] for m in all_matches])]
    unmatched_mimu = [pcode for pcode in mimu_townships.keys() if pcode not in [m['mimu_pcode'] for m in all_matches]]
    
    if len(unmatched_election) > 0:
        print(f"\n❌ Unmatched election constituencies ({len(unmatched_election)}):")
        for idx, row in unmatched_election.head(10).iterrows():
            print(f"   - {row['constituency_en']} ({row['constituency_mm']})")
    
    if len(unmatched_mimu) > 0:
        print(f"\n❌ Unmatched MIMU townships ({len(unmatched_mimu)}):")
        for pcode in unmatched_mimu[:10]:
            township = mimu_townships[pcode]
            print(f"   - {township['name_en']} ({township['name_mmr']})")
    
    # Create mapping file
    mapping_data = {
        'metadata': {
            'total_constituencies': total_constituencies,
            'total_matched': total_matched,
            'match_rate': (total_matched/total_constituencies)*100,
            'myanmar_script_matches': len(myanmar_matches),
            'english_fuzzy_matches': len(english_matches)
        },
        'matches': all_matches,
        'mimu_townships': mimu_townships
    }
    
    # Save mapping
    mapping_path = Path(__file__).parent / "data" / "processed" / "township_boundary_mapping.json"
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(mapping_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Mapping saved to: {mapping_path}")
    print(f"🎯 Ready to integrate real boundaries for {total_matched} constituencies!")
    
    return mapping_data

if __name__ == "__main__":
    mapping = create_mapping()