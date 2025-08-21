#!/usr/bin/env python3
"""
Extract Comprehensive Myanmar Election Data with Multi-Township MIMU Coordinates
Handles both single and multi-township constituencies with + separated codes
"""

import pandas as pd
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / 'src'))

def load_mimu_coordinates():
    """Load MIMU coordinate lookup from GeoJSON."""
    try:
        # Load MIMU boundary data
        mimu_path = Path(__file__).parent / 'data' / 'geojson' / 'myanmar_townships_mimu.geojson'
        if not mimu_path.exists():
            print(f"⚠️ MIMU GeoJSON not found: {mimu_path}")
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
        
        print(f"📍 Loaded {len(mimu_coords)} MIMU coordinate entries")
        return mimu_coords
        
    except Exception as e:
        print(f"❌ Error loading MIMU coordinates: {e}")
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

def extract_comprehensive_data():
    """Extract comprehensive election data from all assembly sheets with coordinates."""
    
    excel_file = 'data/2025-ELECTION-PLAN-DATA-FINAL.xlsx'
    output_file = 'data/processed/myanmar_election_2025_comprehensive_with_coordinates.csv'
    
    print("🚀 Starting comprehensive data extraction with multi-township MIMU coordinates...")
    
    # Load MIMU coordinates
    mimu_coords = load_mimu_coordinates()
    
    # Assembly type mapping
    assembly_mapping = {
        'ပြည်သူ့လွှတ်တော် (FPTP)': 'PTHT',
        'အမျိုးသားလွှတ်တော် (FPTP)': 'AMTHT', 
        'အမျိုးသားလွှတ်တော်(PR)': 'AMTHT_PR',
        'တိုင်းပြည်နယ်လွှတ်တော်(FPTP)': 'TPHT',
        'တိုင်းပြည်နယ်လွှတ်တော်(PR)': 'TPHT_PR',
        'တိုင်းရင်းသား(FPTP)': 'TPTYT'
    }
    
    all_constituencies = []
    constituency_id = 1
    
    xl_file = pd.ExcelFile(excel_file)
    
    for sheet_name in xl_file.sheet_names:
        print(f"\n📊 Processing sheet: {sheet_name}")
        
        try:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            assembly_type = assembly_mapping.get(sheet_name, sheet_name)
            
            print(f"   Found {len(df)} constituencies")
            
            # Find the correct column names for this sheet
            areas_col = None
            tsp_code_col = None
            constituency_col = None
            state_col = None
            representatives_col = None
            electoral_system_col = None
            
            for col in df.columns:
                if 'ပါဝင်သည့်နယ်မြေများ' in col and areas_col is None:
                    areas_col = col
                if 'Tsp_Pcode' in col or col == 'Tsp_Pcode':
                    tsp_code_col = col
                if 'မဲဆန္ဒနယ်' in col and col != 'မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ':
                    constituency_col = col
                if 'တိုင်း/ပြည်နယ်' in col:
                    state_col = col
                if 'ကိုယ်စားလှယ်' in col:
                    representatives_col = col
                if 'မဲစနစ်' in col:
                    electoral_system_col = col
            
            print(f"   Columns found - Areas: {areas_col}, TSP: {tsp_code_col}")
            
            for _, row in df.iterrows():
                try:
                    # For PTHT (single township), use Tsp_Pcode column
                    # For other assemblies (multi-township), use ပါဝင်သည့်နယ်မြေများ column
                    if assembly_type == 'PTHT' and tsp_code_col:
                        tsp_pcode_field = row.get(tsp_code_col, '')
                    else:
                        # Look for the multi-township codes column
                        multi_tsp_col = None
                        for col in df.columns:
                            if col == 'ပါဝင်သည့်နယ်မြေများ':
                                multi_tsp_col = col
                                break
                        tsp_pcode_field = row.get(multi_tsp_col, '') if multi_tsp_col else ''
                    
                    # Calculate coordinates using multi-township logic
                    lat, lng, coordinate_source = calculate_multi_township_coordinates(tsp_pcode_field, mimu_coords)
                    
                    # Build constituency record
                    constituency = {
                        'id': constituency_id,
                        'constituency_en': str(row.get(constituency_col, f'{assembly_type} Constituency {constituency_id}')),
                        'constituency_mm': str(row.get(constituency_col, f'{assembly_type} မဲဆန်ဒနယ် {constituency_id}')),
                        'state_region_en': str(row.get(state_col, 'Unknown State')),
                        'state_region_mm': str(row.get(state_col, 'အမည်မသိပြည်နယ်')),
                        'assembly_type': assembly_type,
                        'areas_included_en': str(row.get('မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ', '')),
                        'areas_included_mm': str(row.get('မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ', '')),
                        'representatives': int(row.get(representatives_col, 1)),
                        'electoral_system_en': 'FPTP' if 'FPTP' in sheet_name else 'PR' if 'PR' in sheet_name else 'FPTP',
                        'tsp_pcode': str(tsp_pcode_field) if tsp_pcode_field else '',
                        'lat': lat,
                        'lng': lng,
                        'coordinate_source': coordinate_source,
                        'township_name_en': str(row.get('Township_Name_Eng', '')),
                        'township_mm': str(row.get('မြို့နယ်', ''))
                    }
                    
                    all_constituencies.append(constituency)
                    
                    if lat and lng:
                        coord_info = f"({lat:.4f}, {lng:.4f})"
                        print(f"   ✅ {constituency['constituency_en']} - {coordinate_source} {coord_info}")
                    else:
                        print(f"   ⚠️  {constituency['constituency_en']} - No coordinates")
                    
                    constituency_id += 1
                    
                except Exception as e:
                    print(f"   ❌ Error processing row in {sheet_name}: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error processing sheet {sheet_name}: {e}")
            continue
    
    # Create output dataframe and save
    if all_constituencies:
        final_df = pd.DataFrame(all_constituencies)
        final_df.to_csv(output_file, index=False, encoding='utf-8')
        
        print(f"\n🎉 Successfully extracted {len(all_constituencies)} constituencies!")
        print(f"📄 Saved to: {output_file}")
        
        # Summary statistics
        print("\n📊 Summary by Assembly Type:")
        summary = final_df.groupby('assembly_type').agg({
            'id': 'count',
            'lat': lambda x: x.notna().sum(),
            'coordinate_source': lambda x: (x == 'mimu_multi_township_centroid').sum()
        }).rename(columns={'id': 'total', 'lat': 'mapped', 'coordinate_source': 'multi_township'})
        
        for assembly_type, stats in summary.iterrows():
            print(f"  {assembly_type}: {stats['total']} total, {stats['mapped']} mapped, {stats['multi_township']} multi-township")
        
        print(f"  TOTAL: {len(all_constituencies)} constituencies, {final_df['lat'].notna().sum()} mapped")
        
        return True
    else:
        print("❌ No constituencies extracted")
        return False

if __name__ == "__main__":
    success = extract_comprehensive_data()
    sys.exit(0 if success else 1)