#!/usr/bin/env python3
"""
Process new Excel file with MIMU codes and update database
This integrates the official MIMU township codes from the 2025 election data
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

def process_mimu_codes():
    """Process Excel file with MIMU codes and update database"""
    print("🗺️ Processing MIMU Codes from New Excel Data\n")
    
    # Read the Excel file with MIMU codes
    excel_path = Path("../UPDATE/2025-ELECTION-PLAN-DATA-FINAL.xlsx")
    
    if not excel_path.exists():
        print(f"❌ Excel file not found: {excel_path}")
        return False
    
    print("1️⃣ Loading Excel data with MIMU codes...")
    
    # Read the Pyithu Hluttaw sheet (has Township codes)
    df = pd.read_excel(excel_path, sheet_name='ပြည်သူ့လွှတ်တော် (FPTP)')
    
    print(f"   📊 Loaded {len(df)} constituencies from Excel")
    
    # Create mapping of constituency to MIMU code
    mimu_mapping = {}
    
    for idx, row in df.iterrows():
        # Get constituency name and MIMU code
        constituency_mm = str(row['မဲဆန္ဒနယ်']).strip() if pd.notna(row['မဲဆန္ဒနယ်']) else None
        township_mm = str(row['မြို့နယ်']).strip() if pd.notna(row['မြို့နယ်']) else None
        tsp_pcode = str(row['Tsp_Pcode']).strip() if pd.notna(row['Tsp_Pcode']) else None
        township_eng = str(row['Township_Name_Eng']).strip() if pd.notna(row['Township_Name_Eng']) else None
        
        if constituency_mm and tsp_pcode:
            # Build full constituency name
            if township_mm:
                full_name = f"{township_mm}{constituency_mm}"
            else:
                full_name = constituency_mm
                
            mimu_mapping[full_name] = {
                'tsp_pcode': tsp_pcode,
                'township_eng': township_eng,
                'township_mm': township_mm
            }
    
    print(f"   🗺️ Created mapping for {len(mimu_mapping)} constituencies")
    
    # Connect to database
    print("\n2️⃣ Connecting to database...")
    connection_string = get_database_url()
    conn = psycopg2.connect(connection_string)
    cursor = conn.cursor()
    
    # Get existing constituencies
    print("\n3️⃣ Loading constituencies from database...")
    cursor.execute("""
        SELECT id, constituency_mm, tsp_pcode, township_name_eng
        FROM constituencies 
        WHERE election_year = 2025 
        AND assembly_type = 'PTHT'
        ORDER BY id
    """)
    
    db_constituencies = cursor.fetchall()
    print(f"   📊 Found {len(db_constituencies)} PTHT constituencies in database")
    
    # Update MIMU codes
    print("\n4️⃣ Updating MIMU codes and township names...")
    
    updated_count = 0
    matched_count = 0
    
    for const_id, name_mm, existing_pcode, existing_township_eng in db_constituencies:
        if name_mm and name_mm in mimu_mapping:
            mapping = mimu_mapping[name_mm]
            new_pcode = mapping['tsp_pcode']
            new_township_eng = mapping['township_eng']
            new_township_mm = mapping['township_mm']
            
            # Update database with new information
            cursor.execute("""
                UPDATE constituencies 
                SET tsp_pcode = %s,
                    township_name_eng = %s,
                    township_name_mm = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (new_pcode, new_township_eng, new_township_mm, const_id))
            
            updated_count += 1
            matched_count += 1
            
            if updated_count % 50 == 0:
                print(f"   🏷️ Updated {updated_count} constituencies...")
    
    # Also process other assemblies if needed
    print("\n5️⃣ Processing other assembly types...")
    
    # Read Amyotha Hluttaw sheet
    df_amyotha = pd.read_excel(excel_path, sheet_name='အမျိုးသားလွှတ်တော် (FPTP)')
    print(f"   📊 Loaded {len(df_amyotha)} Amyotha Hluttaw constituencies")
    
    # Read State/Region sheets
    df_state_fptp = pd.read_excel(excel_path, sheet_name='တိုင်းပြည်နယ်လွှတ်တော်(FPTP)')
    df_state_pr = pd.read_excel(excel_path, sheet_name='တိုင်းပြည်နယ်လွှတ်တော်(PR)')
    print(f"   📊 Loaded {len(df_state_fptp)} State/Region FPTP constituencies")
    print(f"   📊 Loaded {len(df_state_pr)} State/Region PR constituencies")
    
    # Commit changes
    conn.commit()
    
    print(f"\n✅ MIMU code update completed:")
    print(f"   🗺️ Matched constituencies: {matched_count}")
    print(f"   🏷️ Updated with MIMU codes: {updated_count}")
    
    # Verify results
    print("\n6️⃣ Verifying MIMU code updates...")
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN tsp_pcode IS NOT NULL AND tsp_pcode != '' THEN 1 END) as with_pcode,
            COUNT(CASE WHEN township_name_eng IS NOT NULL AND township_name_eng != '' THEN 1 END) as with_township_eng
        FROM constituencies 
        WHERE election_year = 2025
        AND assembly_type = 'PTHT'
    """)
    
    total, with_pcode, with_township_eng = cursor.fetchone()
    print(f"   📊 Total PTHT constituencies: {total}")
    print(f"   🏷️ With MIMU codes: {with_pcode} ({(with_pcode/total)*100:.1f}%)")
    print(f"   🌍 With English township names: {with_township_eng} ({(with_township_eng/total)*100:.1f}%)")
    
    # Show sample of updated data
    cursor.execute("""
        SELECT constituency_mm, township_name_eng, tsp_pcode
        FROM constituencies 
        WHERE election_year = 2025
        AND assembly_type = 'PTHT'
        AND tsp_pcode IS NOT NULL
        LIMIT 5
    """)
    
    samples = cursor.fetchall()
    print("\n   📋 Sample updated records:")
    for const_mm, township_eng, pcode in samples:
        print(f"      • {const_mm}: {township_eng} ({pcode})")
    
    conn.close()
    
    print("\n✅ MIMU code processing completed successfully!")
    
    return True

def main():
    """Main function"""
    try:
        success = process_mimu_codes()
        return success
    except Exception as e:
        logger.error(f"Error processing MIMU codes: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)