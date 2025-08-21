#!/usr/bin/env python3
"""
Comprehensive Election Data Processor
Processes all 6 sheets from the 2025 election Excel file with MIMU codes
Extends database schema and loads all assembly types
"""

import pandas as pd
import json
import sys
import os
from pathlib import Path
import psycopg2
import logging
from typing import Dict, List, Optional
import re

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

def extend_database_schema(cursor):
    """Extend database schema to support all assembly types"""
    print("🏗️ Extending database schema...")
    
    # Add new columns for comprehensive data
    schema_extensions = [
        "ALTER TABLE constituencies ADD COLUMN IF NOT EXISTS electoral_system VARCHAR(10) DEFAULT 'FPTP'",
        "ALTER TABLE constituencies ADD COLUMN IF NOT EXISTS state_region_code VARCHAR(20)",
        "ALTER TABLE constituencies ADD COLUMN IF NOT EXISTS seats_allocated INTEGER DEFAULT 1",
        "ALTER TABLE constituencies ADD COLUMN IF NOT EXISTS ethnic_group VARCHAR(100)",
        "ALTER TABLE constituencies ADD COLUMN IF NOT EXISTS region_boundary_type VARCHAR(20) DEFAULT 'township'",
        "ALTER TABLE constituencies ADD COLUMN IF NOT EXISTS constituency_number INTEGER",
        "ALTER TABLE constituencies ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE constituencies ADD COLUMN IF NOT EXISTS coordinate_source VARCHAR(50) DEFAULT 'boundary_centroid'"
    ]
    
    for sql in schema_extensions:
        try:
            cursor.execute(sql)
            logger.info(f"✅ Schema extended: {sql.split('ADD COLUMN IF NOT EXISTS')[1].split()[0] if 'ADD COLUMN' in sql else 'Updated'}")
        except Exception as e:
            logger.warning(f"⚠️ Schema extension failed: {e}")
    
    print("   ✅ Database schema extended for multi-assembly support")

def extract_tsp_pcodes_from_text(area_text: str) -> List[str]:
    """Extract township codes from descriptive text by matching with known townships"""
    # This would require a mapping from township names to codes
    # For now, return empty list - will be enhanced with boundary matching
    return []

def process_ptht_constituencies(df: pd.DataFrame) -> List[Dict]:
    """Process Pyithu Hluttaw (PTHT) constituencies"""
    constituencies = []
    
    for idx, row in df.iterrows():
        const_name = str(row['မြို့နယ်.1']).strip() if pd.notna(row['မြို့နယ်.1']) else None
        township_mm = str(row['မြို့နယ်']).strip() if pd.notna(row['မြို့နယ်']) else None
        tsp_pcode = str(row['Tsp_Pcode']).strip() if pd.notna(row['Tsp_Pcode']) else None
        township_eng = str(row['Township_Name_Eng']).strip() if pd.notna(row['Township_Name_Eng']) else None
        state_mm = str(row['တိုင်း/ပြည်နယ်']).strip() if pd.notna(row['တিုন်း/ပြည်နယ်']) else None
        areas_text = str(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']).strip() if pd.notna(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']) else ""
        
        if const_name and tsp_pcode:
            constituencies.append({
                'constituency_mm': const_name,
                'constituency_en': township_eng if township_eng else const_name,
                'tsp_pcode': tsp_pcode,
                'township_name_eng': township_eng,
                'township_name_mm': township_mm,
                'state_region_mm': state_mm,
                'assembly_type': 'PTHT',
                'electoral_system': 'FPTP',
                'representatives': 1,
                'constituency_number': idx + 1,
                'region_boundary_type': 'township',
                'constituency_areas_mm': areas_text
            })
    
    return constituencies

def process_amyotha_fptp(df: pd.DataFrame) -> List[Dict]:
    """Process Amyotha Hluttaw FPTP constituencies"""
    constituencies = []
    
    for idx, row in df.iterrows():
        const_name = str(row['မဲဆန္ဒနယ်']).strip() if pd.notna(row['မဲဆန္ဒနယ်']) else None
        state_mm = str(row['တိုင်း/ပြည်နယ်']).strip() if pd.notna(row['တိုင်း/ပြည်နယ်']) else None
        areas_text = str(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']).strip() if pd.notna(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']) else ""
        
        if const_name and state_mm:
            constituencies.append({
                'constituency_mm': const_name,
                'constituency_en': const_name,
                'tsp_pcode': None,  # Multi-district constituencies
                'township_name_eng': None,
                'township_name_mm': None,
                'state_region_mm': state_mm,
                'assembly_type': 'AMTHT',
                'electoral_system': 'FPTP',
                'representatives': 1,
                'constituency_number': idx + 1,
                'region_boundary_type': 'district',
                'constituency_areas_mm': areas_text
            })
    
    return constituencies

def process_amyotha_pr(df: pd.DataFrame) -> List[Dict]:
    """Process Amyotha Hluttaw PR constituencies"""
    constituencies = []
    
    for idx, row in df.iterrows():
        if pd.isna(row['တိုင်း/ပြည်နယ်']):
            continue
            
        const_name = str(row['မဲဆန္ဒနယ်အမှတ်']).strip() if pd.notna(row['မဲဆန္ဒနယ်အမှတ်']) else f"PR-{idx+1}"
        state_mm = str(row['တিုန်း/ပြည်နယ်']).strip() if pd.notna(row['တিုန်း/ပြည်နယ်']) else None
        areas_text = str(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']).strip() if pd.notna(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']) else ""
        seats = int(row['ကိုယ်စားလှယ်']) if pd.notna(row['ကိုယ်စားလှယ်']) else 1
        
        if state_mm:
            constituencies.append({
                'constituency_mm': const_name,
                'constituency_en': const_name,
                'tsp_pcode': None,  # PR spans entire state/region
                'township_name_eng': None,
                'township_name_mm': None,
                'state_region_mm': state_mm,
                'assembly_type': 'AMTHT',
                'electoral_system': 'PR',
                'representatives': seats,
                'constituency_number': idx + 1,
                'region_boundary_type': 'regional',
                'constituency_areas_mm': areas_text
            })
    
    return constituencies

def process_state_region_fptp(df: pd.DataFrame) -> List[Dict]:
    """Process State/Region FPTP constituencies"""
    constituencies = []
    
    for idx, row in df.iterrows():
        const_name = str(row['မဲဆန္ဒနယ်']).strip() if pd.notna(row['မဲဆန္ဒနယ်']) else None
        township_mm = str(row['မြို့နယ်']).strip() if pd.notna(row['မြို့နယ်']) else None
        township_eng = str(row['Township_Name_Eng']).strip() if pd.notna(row['Township_Name_Eng']) else None
        state_mm = str(row['တိုင်း/ပြည်နယ်']).strip() if pd.notna(row['တিုင်း/ပြည်နယ်']) else None
        areas_text = str(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']).strip() if pd.notna(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']) else ""
        
        if const_name and state_mm:
            # Try to extract TSP_PCODE from township name matching
            tsp_pcode = None
            if township_eng:
                # This would need to be matched against boundary data
                pass
            
            constituencies.append({
                'constituency_mm': const_name,
                'constituency_en': township_eng if township_eng else const_name,
                'tsp_pcode': tsp_pcode,
                'township_name_eng': township_eng,
                'township_name_mm': township_mm,
                'state_region_mm': state_mm,
                'assembly_type': 'TPHT',
                'electoral_system': 'FPTP',
                'representatives': 1,
                'constituency_number': idx + 1,
                'region_boundary_type': 'township',
                'constituency_areas_mm': areas_text
            })
    
    return constituencies

def process_state_region_pr(df: pd.DataFrame) -> List[Dict]:
    """Process State/Region PR constituencies"""
    constituencies = []
    
    for idx, row in df.iterrows():
        const_name = str(row['မဲဆန္ဒနယ်']).strip() if pd.notna(row['မဲဆန္ဒနယ်']) else None
        state_mm = str(row['တိုင်း/ပြည်နယ်']).strip() if pd.notna(row['တိုင်း/ပြည်နယ်']) else None
        areas_text = str(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']).strip() if pd.notna(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']) else ""
        seats = int(row['ကိုယ်စားလှယ်']) if pd.notna(row['ကိုယ်စားလှယ်']) else 1
        
        if const_name and state_mm:
            constituencies.append({
                'constituency_mm': const_name,
                'constituency_en': const_name,
                'tsp_pcode': None,  # PR spans multiple townships
                'township_name_eng': None,
                'township_name_mm': None,
                'state_region_mm': state_mm,
                'assembly_type': 'TPHT',
                'electoral_system': 'PR',
                'representatives': seats,
                'constituency_number': idx + 1,
                'region_boundary_type': 'regional',
                'constituency_areas_mm': areas_text
            })
    
    return constituencies

def process_ethnic_constituencies(df: pd.DataFrame) -> List[Dict]:
    """Process Ethnic constituencies"""
    constituencies = []
    
    for idx, row in df.iterrows():
        const_name = str(row['မဲဆန္ဒနယ်']).strip() if pd.notna(row['မဲဆန္ဒနယ်']) else None
        state_mm = str(row['တိုင်း/ပြည်နယ်']).strip() if pd.notna(row['တိုင်း/ပြည်နယ်']) else None
        areas_text = str(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']).strip() if pd.notna(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']) else ""
        
        # Extract ethnic group from constituency name
        ethnic_group = None
        if const_name:
            # Extract ethnic group name from constituency name
            if 'တိုင်းရင်းသားလူမျိုး' in const_name:
                ethnic_group = const_name.replace('တိုင်းရင်းသားလူမျိုးမဲဆန္ဒနယ်', '').replace('မဲဆန္ဒနယ်', '').strip()
        
        if const_name and state_mm:
            constituencies.append({
                'constituency_mm': const_name,
                'constituency_en': const_name,
                'tsp_pcode': None,  # Ethnic constituencies span various areas
                'township_name_eng': None,
                'township_name_mm': None,
                'state_region_mm': state_mm,
                'assembly_type': 'TPTYT',  # Ethnic representatives
                'electoral_system': 'FPTP',
                'representatives': 1,
                'constituency_number': idx + 1,
                'region_boundary_type': 'ethnic',
                'constituency_areas_mm': areas_text,
                'ethnic_group': ethnic_group
            })
    
    return constituencies

def load_boundary_coordinates() -> Dict[str, Dict]:
    """Load boundary data for coordinate calculation"""
    print("📍 Loading boundary coordinate data...")
    geojson_path = Path("data/geojson/myanmar_townships_mimu.geojson")
    
    if not geojson_path.exists():
        print(f"   ⚠️ Boundary data not found: {geojson_path}")
        return {}
    
    with open(geojson_path, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)
    
    boundary_coords = {}
    for feature in geojson_data.get('features', []):
        props = feature.get('properties', {})
        ts_pcode = props.get('TS_PCODE')
        geometry = feature.get('geometry')
        
        if ts_pcode and geometry:
            # Calculate centroid
            lng, lat = calculate_centroid(geometry)
            if lng and lat:
                boundary_coords[ts_pcode] = {
                    'lat': lat,
                    'lng': lng,
                    'township_eng': props.get('TS_NAME_EN'),
                    'township_mm': props.get('TS_NAME_MM')
                }
    
    print(f"   ✅ Loaded coordinates for {len(boundary_coords)} townships")
    return boundary_coords

def calculate_centroid(geometry: Dict) -> tuple:
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

def calculate_regional_center(state_name: str, boundary_coords: Dict) -> tuple:
    """Calculate center coordinates for a state/region"""
    # For PR constituencies that span entire states, calculate regional center
    # This is a placeholder - would need proper regional boundary aggregation
    default_centers = {
        'ကချင်ပြည်နယ်': (97.4, 25.6),
        'ရှမ်းပြည်နယ်': (97.8, 22.0),
        'ရခိုင်ပြည်နယ်': (93.5, 20.0),
        'မွန်ပြည်နယ်': (97.8, 16.5),
        # Add more as needed
    }
    
    return default_centers.get(state_name, (96.0, 19.0))  # Myanmar center as fallback

def insert_constituencies(cursor, constituencies: List[Dict], boundary_coords: Dict):
    """Insert constituencies into database"""
    inserted_count = 0
    
    for const in constituencies:
        # Get coordinates
        lat, lng = None, None
        coord_source = 'missing'
        
        if const.get('tsp_pcode') and const['tsp_pcode'] in boundary_coords:
            coord_data = boundary_coords[const['tsp_pcode']]
            lat = coord_data['lat']
            lng = coord_data['lng']
            coord_source = 'boundary_centroid'
        elif const.get('region_boundary_type') in ['regional', 'district', 'ethnic']:
            # Calculate regional center for PR constituencies
            lng, lat = calculate_regional_center(const['state_region_mm'], boundary_coords)
            coord_source = 'regional_center'
        
        try:
            cursor.execute("""
                INSERT INTO constituencies (
                    constituency_code, constituency_en, constituency_mm,
                    state_region_en, state_region_mm, assembly_type,
                    representatives, lat, lng, election_year,
                    tsp_pcode, township_name_eng, township_name_mm,
                    electoral_system, seats_allocated, ethnic_group,
                    region_boundary_type, constituency_number,
                    coordinate_source, constituency_areas_mm, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
                )
            """, (
                f"{const['assembly_type']}-{const.get('constituency_number', inserted_count+1)}",
                const['constituency_en'],
                const['constituency_mm'],
                const.get('state_region_en', const.get('state_region_mm')),
                const['state_region_mm'],
                const['assembly_type'],
                const['representatives'],
                lat,
                lng,
                2025,
                const.get('tsp_pcode'),
                const.get('township_name_eng'),
                const.get('township_name_mm'),
                const['electoral_system'],
                const.get('seats_allocated', const['representatives']),
                const.get('ethnic_group'),
                const['region_boundary_type'],
                const.get('constituency_number'),
                coord_source,
                const.get('constituency_areas_mm'),
            ))
            inserted_count += 1
            
            if inserted_count % 100 == 0:
                print(f"   📊 Inserted {inserted_count} constituencies...")
                
        except Exception as e:
            logger.error(f"Failed to insert constituency {const['constituency_mm']}: {e}")
    
    return inserted_count

def process_comprehensive_election_data():
    """Process all sheets from the comprehensive Excel file"""
    print("🗳️ Processing Comprehensive 2025 Election Data\\n")
    
    # Read the Excel file with all assembly data
    excel_path = Path("../UPDATE/2025-ELECTION-PLAN-DATA-FINAL.xlsx")
    
    if not excel_path.exists():
        print(f"❌ Excel file not found: {excel_path}")
        return False
    
    print("1️⃣ Loading comprehensive Excel data...")
    
    # Load all sheets with correct names
    sheets = {
        'ptht': 'ပြည်သူ့လွှတ်တော် (FPTP)',
        'amyotha_fptp': 'အမျိုးသားလွှတ်တော် (FPTP)',
        'amyotha_pr': 'အမျိုးသားလွှတ်တော်(PR)',
        'state_fptp': 'တိုင်းပြည်နယ်လွှတ်တော်(FPTP)',
        'state_pr': 'တိုင်းပြည်နယ်လွှတ်တော်(PR)',
        'ethnic': 'တိုင်းရင်းသား(FPTP)'
    }
    
    all_constituencies = []
    
    # Process PTHT (Pyithu Hluttaw)
    print("   📊 Processing Pyithu Hluttaw constituencies...")
    df_ptht = pd.read_excel(excel_path, sheet_name=sheets['ptht'])
    ptht_constituencies = process_ptht_constituencies(df_ptht)
    all_constituencies.extend(ptht_constituencies)
    print(f"      ✅ Processed {len(ptht_constituencies)} PTHT constituencies")
    
    # Process AMTHT FPTP
    print("   📊 Processing Amyotha Hluttaw FPTP constituencies...")
    df_amyotha_fptp = pd.read_excel(excel_path, sheet_name=sheets['amyotha_fptp'])
    amyotha_fptp = process_amyotha_fptp(df_amyotha_fptp)
    all_constituencies.extend(amyotha_fptp)
    print(f"      ✅ Processed {len(amyotha_fptp)} AMTHT FPTP constituencies")
    
    # Process AMTHT PR
    print("   📊 Processing Amyotha Hluttaw PR constituencies...")
    df_amyotha_pr = pd.read_excel(excel_path, sheet_name=sheets['amyotha_pr'])
    amyotha_pr = process_amyotha_pr(df_amyotha_pr)
    all_constituencies.extend(amyotha_pr)
    print(f"      ✅ Processed {len(amyotha_pr)} AMTHT PR constituencies")
    
    # Process State/Region FPTP
    print("   📊 Processing State/Region FPTP constituencies...")
    df_state_fptp = pd.read_excel(excel_path, sheet_name=sheets['state_fptp'])
    state_fptp = process_state_region_fptp(df_state_fptp)
    all_constituencies.extend(state_fptp)
    print(f"      ✅ Processed {len(state_fptp)} State/Region FPTP constituencies")
    
    # Process State/Region PR
    print("   📊 Processing State/Region PR constituencies...")
    df_state_pr = pd.read_excel(excel_path, sheet_name=sheets['state_pr'])
    state_pr = process_state_region_pr(df_state_pr)
    all_constituencies.extend(state_pr)
    print(f"      ✅ Processed {len(state_pr)} State/Region PR constituencies")
    
    # Process Ethnic constituencies
    print("   📊 Processing Ethnic constituencies...")
    df_ethnic = pd.read_excel(excel_path, sheet_name=sheets['ethnic'])
    ethnic_constituencies = process_ethnic_constituencies(df_ethnic)
    all_constituencies.extend(ethnic_constituencies)
    print(f"      ✅ Processed {len(ethnic_constituencies)} Ethnic constituencies")
    
    print(f"\\n   📊 Total constituencies to process: {len(all_constituencies)}")
    
    # Load boundary coordinates
    boundary_coords = load_boundary_coordinates()
    
    # Connect to database
    print("\\n2️⃣ Connecting to database...")
    connection_string = get_database_url()
    conn = psycopg2.connect(connection_string)
    cursor = conn.cursor()
    
    # Extend schema
    extend_database_schema(cursor)
    
    # Clear existing 2025 data to avoid duplicates
    print("\\n3️⃣ Clearing existing 2025 election data...")
    cursor.execute("DELETE FROM constituencies WHERE election_year = 2025")
    deleted_rows = cursor.rowcount
    print(f"   🗑️ Removed {deleted_rows} existing records")
    
    # Insert comprehensive data
    print("\\n4️⃣ Inserting comprehensive constituency data...")
    total_inserted = insert_constituencies(cursor, all_constituencies, boundary_coords)
    
    # Commit changes
    conn.commit()
    
    print(f"\\n✅ Comprehensive data processing completed:")
    print(f"   📊 Total constituencies inserted: {total_inserted}")
    
    # Verify results by assembly type
    print("\\n5️⃣ Verifying comprehensive data by assembly type...")
    cursor.execute("""
        SELECT 
            assembly_type,
            electoral_system,
            COUNT(*) as count,
            COUNT(CASE WHEN lat IS NOT NULL AND lng IS NOT NULL THEN 1 END) as with_coords,
            COUNT(CASE WHEN tsp_pcode IS NOT NULL THEN 1 END) as with_pcode
        FROM constituencies 
        WHERE election_year = 2025 
        GROUP BY assembly_type, electoral_system
        ORDER BY assembly_type, electoral_system
    """)
    
    assembly_stats = cursor.fetchall()
    print("   📊 Assembly breakdown:")
    total_all = 0
    for assembly, system, count, with_coords, with_pcode in assembly_stats:
        total_all += count
        coord_pct = (with_coords/count)*100 if count > 0 else 0
        pcode_pct = (with_pcode/count)*100 if count > 0 else 0
        print(f"      • {assembly} {system}: {count} constituencies ({coord_pct:.1f}% coords, {pcode_pct:.1f}% pcodes)")
    
    print(f"   📊 Grand total: {total_all} constituencies")
    
    # Verify coordinate sources
    cursor.execute("""
        SELECT coordinate_source, COUNT(*) 
        FROM constituencies 
        WHERE election_year = 2025 
        GROUP BY coordinate_source
        ORDER BY COUNT(*) DESC
    """)
    
    coord_sources = cursor.fetchall()
    print("\\n   📍 Coordinate sources:")
    for source, count in coord_sources:
        print(f"      • {source}: {count}")
    
    conn.close()
    
    print("\\n✅ Comprehensive election data processing completed successfully!")
    print("\\n🚀 Ready for enhanced visualization with all assembly types!")
    
    return True

def main():
    """Main function"""
    try:
        success = process_comprehensive_election_data()
        return success
    except Exception as e:
        logger.error(f"Error processing comprehensive election data: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)