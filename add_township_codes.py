#!/usr/bin/env python3
"""
Add township codes to existing constituencies in the database
This enables boundary-based coordinate improvements
"""

import json
import os
import sys
import psycopg2
from pathlib import Path
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

def add_township_codes():
    """Add township codes to existing constituencies"""
    print("🏷️ Adding Township Codes to Existing Constituencies\n")
    
    # Load the processed data with township codes
    print("1️⃣ Loading processed constituency data...")
    json_path = Path("data/processed/myanmar_election_2025.json")
    
    if not json_path.exists():
        print(f"❌ Processed data not found: {json_path}")
        return False
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    constituencies_data = data.get('constituencies', [])
    print(f"   📊 Loaded {len(constituencies_data)} constituencies from JSON")
    
    # Create mapping by constituency name
    tsp_pcode_mapping = {}
    for const in constituencies_data:
        name_mm = const.get('constituency_name_mm', '').strip()
        tsp_pcode = const.get('tsp_pcode', '').strip()
        if name_mm and tsp_pcode:
            tsp_pcode_mapping[name_mm] = tsp_pcode
    
    print(f"   🗺️ Created mapping for {len(tsp_pcode_mapping)} constituencies")
    
    # Connect to database
    print("\n2️⃣ Connecting to database...")
    connection_string = get_database_url()
    conn = psycopg2.connect(connection_string)
    cursor = conn.cursor()
    
    # Get existing constituencies
    print("\n3️⃣ Loading constituencies from database...")
    cursor.execute("""
        SELECT id, constituency_mm, tsp_pcode
        FROM constituencies 
        WHERE election_year = 2025 
        ORDER BY id
    """)
    
    db_constituencies = cursor.fetchall()
    print(f"   📊 Found {len(db_constituencies)} constituencies in database")
    
    # Update township codes
    print("\n4️⃣ Adding township codes...")
    
    updated_count = 0
    matched_count = 0
    
    for const_id, name_mm, existing_pcode in db_constituencies:
        if name_mm in tsp_pcode_mapping:
            new_pcode = tsp_pcode_mapping[name_mm]
            
            # Update if different or empty
            if existing_pcode != new_pcode:
                cursor.execute("""
                    UPDATE constituencies 
                    SET tsp_pcode = %s
                    WHERE id = %s
                """, (new_pcode, const_id))
                updated_count += 1
                
                if updated_count % 50 == 0:
                    print(f"   🏷️ Updated {updated_count} township codes...")
            
            matched_count += 1
    
    # Commit changes
    conn.commit()
    
    print(f"\n✅ Township code update completed:")
    print(f"   🗺️ Matched constituencies: {matched_count}")
    print(f"   🏷️ Updated township codes: {updated_count}")
    
    # Verify results
    print("\n5️⃣ Verifying township code updates...")
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN tsp_pcode IS NOT NULL AND tsp_pcode != '' THEN 1 END) as with_pcode
        FROM constituencies 
        WHERE election_year = 2025
    """)
    
    total, with_pcode = cursor.fetchone()
    print(f"   📊 Total constituencies: {total}")
    print(f"   🏷️ With township codes: {with_pcode}")
    print(f"   📈 Coverage: {(with_pcode/total)*100:.1f}%")
    
    conn.close()
    
    print("\n✅ Township code addition completed successfully!")
    
    return True

def main():
    """Main function"""
    try:
        success = add_township_codes()
        return success
    except Exception as e:
        logger.error(f"Error adding township codes: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)