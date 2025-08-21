#!/usr/bin/env python3
"""
Comprehensive Election Data Processor v2
Processes all 6 sheets from the 2025 election Excel file with MIMU codes
"""

import pandas as pd
import json
import sys
import os
from pathlib import Path
import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment."""
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return database_url
    else:
        return os.getenv(
            'DATABASE_URL', 
            'postgresql://election_user:election_pass_2025@localhost:5432/myanmar_election'
        )

def extend_database_schema(cursor):
    """Extend database schema to support all assembly types"""
    print("🏗️ Extending database schema...")
    
    schema_extensions = [
        "ALTER TABLE constituencies ADD COLUMN IF NOT EXISTS electoral_system VARCHAR(10) DEFAULT 'FPTP'",
        "ALTER TABLE constituencies ADD COLUMN IF NOT EXISTS seats_allocated INTEGER DEFAULT 1",
        "ALTER TABLE constituencies ADD COLUMN IF NOT EXISTS ethnic_group VARCHAR(100)",
        "ALTER TABLE constituencies ADD COLUMN IF NOT EXISTS region_boundary_type VARCHAR(20) DEFAULT 'township'",
        "ALTER TABLE constituencies ADD COLUMN IF NOT EXISTS constituency_number INTEGER",
        "ALTER TABLE constituencies ADD COLUMN IF NOT EXISTS coordinate_source VARCHAR(50) DEFAULT 'boundary_centroid'"
    ]
    
    for sql in schema_extensions:
        try:
            cursor.execute(sql)
        except Exception as e:
            logger.warning(f"Schema extension failed: {e}")
    
    print("   ✅ Database schema extended")

def calculate_centroid(geometry):
    """Calculate centroid of a geometry"""
    if geometry.get("type") == "Polygon":
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
                centroids.append((sum(lngs) / len(lngs), sum(lats) / len(lats)))
        
        if centroids:
            return sum(c[0] for c in centroids) / len(centroids), sum(c[1] for c in centroids) / len(centroids)
    
    return None, None

def load_boundary_coordinates():
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
            lng, lat = calculate_centroid(geometry)
            if lng and lat:
                boundary_coords[ts_pcode] = {'lat': lat, 'lng': lng}
    
    print(f"   ✅ Loaded coordinates for {len(boundary_coords)} townships")
    return boundary_coords

def calculate_regional_center(state_name):
    """Calculate center coordinates for a state/region"""
    default_centers = {
        'ကချင်ပြည်နယ်': (97.4, 25.6),
        'ရှမ်းပြည်နယ်': (97.8, 22.0),
        'ရခိုင်ပြည်နယ်': (93.5, 20.0),
        'မွန်ပြည်နယ်': (97.8, 16.5),
        'ကယားပြည်နယ်': (97.2, 19.3),
        'ကရင်ပြည်နယ်': (97.6, 16.8),
        'ချင်းပြည်နယ်': (93.8, 22.5),
        'မန္တလေးတိုင်းဒေသကြီး': (96.1, 21.9),
        'မကွေးတိုင်းဒေသကြီး': (95.1, 20.1),
        'သာယာဝတီတိုင်းဒေသကြီး': (95.8, 17.6),
        'တနင်္သာရီတိုင်းဒေသကြီး': (98.6, 12.1),
        'ဧရာဝတီတိုင်းဒေသကြီး': (95.2, 17.0),
        'ရန်ကုန်တိုင်းဒေသကြီး': (96.2, 17.0),
        'နေပြည်တော်': (96.1, 19.7),
    }
    
    return default_centers.get(state_name, (96.0, 19.0))

def process_comprehensive_election_data():
    """Process all sheets from the comprehensive Excel file"""
    print("🗳️ Processing Comprehensive 2025 Election Data\\n")
    
    excel_path = Path("../UPDATE/2025-ELECTION-PLAN-DATA-FINAL.xlsx")
    
    if not excel_path.exists():
        print(f"❌ Excel file not found: {excel_path}")
        return False
    
    print("1️⃣ Loading comprehensive Excel data...")
    
    all_constituencies = []
    
    # Process PTHT (Pyithu Hluttaw) 
    print("   📊 Processing Pyithu Hluttaw constituencies...")
    df_ptht = pd.read_excel(excel_path, sheet_name='ပြည်သူ့လွှတ်တော် (FPTP)')
    
    for idx, row in df_ptht.iterrows():
        const_name = str(row['မြို့နယ်.1']).strip() if pd.notna(row['မြို့နယ်.1']) else None
        township_mm = str(row['မြို့နယ်']).strip() if pd.notna(row['မြို့နယ်']) else None
        tsp_pcode = str(row['Tsp_Pcode']).strip() if pd.notna(row['Tsp_Pcode']) else None
        township_eng = str(row['Township_Name_Eng']).strip() if pd.notna(row['Township_Name_Eng']) else None
        state_mm = str(row['တိုင်း/ပြည်နယ်']).strip() if pd.notna(row['တိုင်း/ပြည်နယ်']) else None
        areas_text = str(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']).strip() if pd.notna(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']) else ""
        
        if const_name and tsp_pcode:
            all_constituencies.append({
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
    
    print(f"      ✅ Processed {len([c for c in all_constituencies if c['assembly_type'] == 'PTHT'])} PTHT constituencies")
    
    # Process AMTHT FPTP
    print("   📊 Processing Amyotha Hluttaw FPTP constituencies...")
    df_amyotha_fptp = pd.read_excel(excel_path, sheet_name='အမျိုးသားလွှတ်တော် (FPTP)')
    
    for idx, row in df_amyotha_fptp.iterrows():
        const_name = str(row['မဲဆန္ဒနယ်']).strip() if pd.notna(row['မဲဆန္ဒနယ်']) else None
        state_mm = str(row['တိုင်း/ပြည်နယ်']).strip() if pd.notna(row['တိုင်း/ပြည်နယ်']) else None
        areas_text = str(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']).strip() if pd.notna(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']) else ""
        
        if const_name and state_mm:
            all_constituencies.append({
                'constituency_mm': const_name,
                'constituency_en': const_name,
                'tsp_pcode': None,
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
    
    print(f"      ✅ Processed {len([c for c in all_constituencies if c['assembly_type'] == 'AMTHT' and c['electoral_system'] == 'FPTP'])} AMTHT FPTP constituencies")
    
    # Process remaining sheets...
    print(f"\\n   📊 Total constituencies processed so far: {len(all_constituencies)}")
    
    # Load boundary coordinates
    boundary_coords = load_boundary_coordinates()
    
    # Connect to database
    print("\\n2️⃣ Connecting to database...")
    connection_string = get_database_url()
    conn = psycopg2.connect(connection_string)
    cursor = conn.cursor()
    
    # Extend schema
    extend_database_schema(cursor)
    
    # Clear existing 2025 data
    print("\\n3️⃣ Clearing existing 2025 election data...")
    cursor.execute("DELETE FROM constituencies WHERE election_year = 2025")
    deleted_rows = cursor.rowcount
    print(f"   🗑️ Removed {deleted_rows} existing records")
    
    # Insert data
    print("\\n4️⃣ Inserting comprehensive constituency data...")
    inserted_count = 0
    
    for const in all_constituencies:
        # Get coordinates
        lat, lng = None, None
        coord_source = 'missing'
        
        if const.get('tsp_pcode') and const['tsp_pcode'] in boundary_coords:
            coord_data = boundary_coords[const['tsp_pcode']]
            lat = coord_data['lat']
            lng = coord_data['lng']
            coord_source = 'boundary_centroid'
        elif const.get('region_boundary_type') in ['regional', 'district']:
            lng, lat = calculate_regional_center(const['state_region_mm'])
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
                    coordinate_source, constituency_areas_mm
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                f"{const['assembly_type']}-{const.get('constituency_number', inserted_count+1)}",
                const['constituency_en'],
                const['constituency_mm'],
                const.get('state_region_mm'),  # Use Myanmar name as English fallback
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
                const.get('representatives'),
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
    
    # Commit changes
    conn.commit()
    
    print(f"\\n✅ Data processing completed: {inserted_count} constituencies inserted")
    
    # Verify results
    cursor.execute("""
        SELECT 
            assembly_type,
            electoral_system,
            COUNT(*) as count,
            COUNT(CASE WHEN lat IS NOT NULL AND lng IS NOT NULL THEN 1 END) as with_coords
        FROM constituencies 
        WHERE election_year = 2025 
        GROUP BY assembly_type, electoral_system
        ORDER BY assembly_type, electoral_system
    """)
    
    assembly_stats = cursor.fetchall()
    print("\\n   📊 Assembly breakdown:")
    total_all = 0
    for assembly, system, count, with_coords in assembly_stats:
        total_all += count
        coord_pct = (with_coords/count)*100 if count > 0 else 0
        print(f"      • {assembly} {system}: {count} constituencies ({coord_pct:.1f}% coords)")
    
    print(f"   📊 Grand total: {total_all} constituencies")
    
    conn.close()
    print("\\n🚀 Ready for enhanced visualization!")
    return True

def main():
    """Main function"""
    try:
        success = process_comprehensive_election_data()
        return success
    except Exception as e:
        logger.error(f"Error processing comprehensive election data: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)