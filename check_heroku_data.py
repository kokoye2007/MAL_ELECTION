#!/usr/bin/env python3
"""
Check Heroku database data to compare with local
"""
import os
import psycopg2

def main():
    database_url = os.environ.get('DATABASE_URL')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    conn = psycopg2.connect(database_url)
    with conn.cursor() as cursor:
        # Check total counts
        cursor.execute("SELECT assembly_type, COUNT(*) FROM constituencies GROUP BY assembly_type ORDER BY assembly_type")
        print("Assembly counts in Heroku:")
        for assembly, count in cursor.fetchall():
            print(f"  {assembly}: {count}")
        
        print("\nSample PTHT constituency data:")
        cursor.execute("""
            SELECT constituency_en, constituency_mm, state_region_en, state_region_mm, 
                   areas_included_en, areas_included_mm, coordinate_source
            FROM constituencies 
            WHERE assembly_type = 'PTHT' 
            LIMIT 3
        """)
        
        for i, row in enumerate(cursor.fetchall(), 1):
            en_name, mm_name, state_en, state_mm, areas_en, areas_mm, coord_source = row
            print(f"\n{i}. EN Name: {en_name}")
            print(f"   MM Name: {mm_name}")
            print(f"   State EN: {state_en}")
            print(f"   State MM: {state_mm}")
            print(f"   Areas EN: {areas_en}")
            print(f"   Areas MM: {areas_mm}")
            print(f"   Coord Source: {coord_source}")
    
    conn.close()

if __name__ == "__main__":
    main()