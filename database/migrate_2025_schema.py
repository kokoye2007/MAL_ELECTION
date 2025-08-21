#!/usr/bin/env python3
"""
Database Migration for 2025 Election Data
Adds new fields and updates schema for the refactored data structure
"""

import os
import sys
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / 'src'))

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


def create_updated_schema(connection_string):
    """Create updated database schema with new fields"""
    try:
        conn = psycopg2.connect(connection_string)
        with conn.cursor() as cursor:
            # Check if tables exist first
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'constituencies'
                );
            """)
            
            constituencies_exists = cursor.fetchone()[0]
            
            if not constituencies_exists:
                # Create updated table with new fields
                cursor.execute("""
                    CREATE TABLE constituencies (
                        id SERIAL PRIMARY KEY,
                        constituency_code VARCHAR(20) UNIQUE NOT NULL,
                        constituency_en VARCHAR(255),
                        constituency_mm VARCHAR(255) NOT NULL,
                        township_name_eng VARCHAR(255),
                        township_name_mm VARCHAR(255),
                        constituency_areas_mm TEXT,
                        constituency_areas_en TEXT,
                        state_region_en VARCHAR(100) NOT NULL,
                        state_region_mm VARCHAR(100) NOT NULL,
                        assembly_type VARCHAR(10) NOT NULL, -- PTHT, AMTHT, TPHT, ETHNIC
                        electoral_system VARCHAR(10) DEFAULT 'FPTP', -- FPTP, PR
                        representatives INTEGER DEFAULT 1,
                        lat DECIMAL(10, 8),
                        lng DECIMAL(11, 8),
                        tsp_pcode VARCHAR(50), -- Township boundary code
                        boundary_codes TEXT[], -- Array of boundary codes for multi-township constituencies
                        coordinate_source VARCHAR(50) DEFAULT 'approximate',
                        validation_status VARCHAR(20) DEFAULT 'pending',
                        election_year INTEGER DEFAULT 2025,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX idx_constituencies_assembly ON constituencies(assembly_type);")
                cursor.execute("CREATE INDEX idx_constituencies_state ON constituencies(state_region_en);")
                cursor.execute("CREATE INDEX idx_constituencies_year ON constituencies(election_year);")
                cursor.execute("CREATE INDEX idx_constituencies_pcode ON constituencies(tsp_pcode);")
                cursor.execute("CREATE INDEX idx_constituencies_electoral ON constituencies(electoral_system);")
                
                logger.info("✅ Created constituencies table")
            else:
                logger.info("✅ Constituencies table already exists")
            
            # Check for political_parties table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'political_parties'
                );
            """)
            
            parties_exists = cursor.fetchone()[0]
            
            if not parties_exists:
                # Create parties table for political party data
                cursor.execute("""
                    CREATE TABLE political_parties (
                        id SERIAL PRIMARY KEY,
                        party_name_mm VARCHAR(500) NOT NULL,
                        party_name_en VARCHAR(500),
                        registration_status VARCHAR(20) NOT NULL, -- 'registered', 'rejected'
                        registration_date VARCHAR(50),
                        announcement_number VARCHAR(50),
                        rejection_date VARCHAR(50),
                        rejection_reason TEXT,
                        notes TEXT,
                        election_year INTEGER DEFAULT 2025,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                cursor.execute("CREATE INDEX idx_parties_status ON political_parties(registration_status);")
                cursor.execute("CREATE INDEX idx_parties_year ON political_parties(election_year);")
                
                logger.info("✅ Created political_parties table")
            else:
                logger.info("✅ Political parties table already exists")
            
            # Check for constituency_boundaries table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'constituency_boundaries'
                );
            """)
            
            boundaries_exists = cursor.fetchone()[0]
            
            if not boundaries_exists:
                # Create constituency_boundaries table for caching boundary data
                cursor.execute("""
                    CREATE TABLE constituency_boundaries (
                        id SERIAL PRIMARY KEY,
                        constituency_id INTEGER REFERENCES constituencies(id) ON DELETE CASCADE,
                        tsp_pcode VARCHAR(50) NOT NULL,
                        boundary_geojson JSONB,
                        centroid_lat DECIMAL(10, 8),
                        centroid_lng DECIMAL(11, 8),
                        area_km2 DECIMAL(10, 3),
                        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        source VARCHAR(100) DEFAULT 'geonode'
                    );
                """)
                
                cursor.execute("CREATE INDEX idx_boundaries_pcode ON constituency_boundaries(tsp_pcode);")
                cursor.execute("CREATE INDEX idx_boundaries_constituency ON constituency_boundaries(constituency_id);")
                
                logger.info("✅ Created constituency_boundaries table")
            else:
                logger.info("✅ Constituency boundaries table already exists")
            
            conn.commit()
            logger.info("✅ Database schema verification completed")
            
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Error creating schema: {e}")
        return False


def load_2025_data(connection_string):
    """Load 2025 election data from the new processor output"""
    try:
        # Read the new processed data
        json_file = Path(__file__).parent.parent / 'data' / 'processed' / 'myanmar_election_2025.json'
        if not json_file.exists():
            logger.error(f"❌ 2025 data file not found: {json_file}")
            logger.info("💡 Run: python src/data_processor_2025.py first")
            return False
        
        import json
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        constituencies = data.get('constituencies', [])
        parties = data.get('parties', {})
        
        logger.info(f"📊 Loading {len(constituencies)} constituencies")
        
        # Connect to database
        conn = psycopg2.connect(connection_string)
        
        # Load constituencies
        loaded_constituencies = 0
        with conn.cursor() as cursor:
            for const in constituencies:
                try:
                    # Generate constituency code
                    state_abbrev = ''.join([word[0].upper() for word in const.get('state_region_mm', '').split()[:2]])
                    if not state_abbrev:
                        state_abbrev = 'UNK'
                    code = f"{const.get('assembly_type', 'PTHT')}-{state_abbrev}-{const.get('id', 0):03d}"
                    
                    # Handle boundary codes array
                    boundary_codes = const.get('boundary_codes')
                    if boundary_codes and isinstance(boundary_codes, list):
                        boundary_codes_array = boundary_codes
                    else:
                        boundary_codes_array = None
                    
                    cursor.execute("""
                        INSERT INTO constituencies (
                            constituency_code, constituency_mm, township_name_eng,
                            township_name_mm, constituency_areas_mm, state_region_mm,
                            state_region_en, assembly_type, electoral_system, representatives,
                            lat, lng, tsp_pcode, boundary_codes, coordinate_source, election_year
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (constituency_code) DO UPDATE SET
                            constituency_mm = EXCLUDED.constituency_mm,
                            township_name_eng = EXCLUDED.township_name_eng,
                            township_name_mm = EXCLUDED.township_name_mm,
                            state_region_en = EXCLUDED.state_region_en,
                            lat = EXCLUDED.lat,
                            lng = EXCLUDED.lng,
                            coordinate_source = EXCLUDED.coordinate_source,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        code,
                        const.get('constituency_name_mm', ''),
                        const.get('township_name_eng', ''),
                        const.get('township_name_mm', ''),
                        const.get('constituency_areas_mm', ''),
                        const.get('state_region_mm', ''),
                        const.get('state_region_en', ''),
                        const.get('assembly_type', 'PTHT'),
                        const.get('electoral_system', 'FPTP'),
                        const.get('representatives', 1),
                        const.get('lat'),
                        const.get('lng'),
                        const.get('tsp_pcode', ''),
                        boundary_codes_array,
                        const.get('coordinate_source', 'approximate'),
                        2025
                    ))
                    
                    loaded_constituencies += 1
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error loading constituency {const.get('id')}: {e}")
                    continue
        
        # Load political parties
        loaded_parties = 0
        registered_parties = parties.get('registered', [])
        rejected_parties = parties.get('rejected', [])
        
        with conn.cursor() as cursor:
            # Load registered parties
            for party in registered_parties:
                try:
                    cursor.execute("""
                        INSERT INTO political_parties (
                            party_name_mm, registration_status, registration_date,
                            announcement_number, notes, election_year
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        party.get('name_mm', ''),
                        'registered',
                        party.get('registration_date', ''),
                        party.get('announcement_number', ''),
                        party.get('notes', ''),
                        2025
                    ))
                    loaded_parties += 1
                except Exception as e:
                    logger.warning(f"⚠️ Error loading registered party: {e}")
            
            # Load rejected parties
            for party in rejected_parties:
                try:
                    cursor.execute("""
                        INSERT INTO political_parties (
                            party_name_mm, registration_status, registration_date,
                            announcement_number, rejection_reason, notes, election_year
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        party.get('name_mm', ''),
                        'rejected',
                        party.get('registration_date', ''),
                        party.get('announcement_number', ''),
                        party.get('notes', ''),  # Rejection reason is in notes for rejected parties
                        '',
                        2025
                    ))
                    loaded_parties += 1
                except Exception as e:
                    logger.warning(f"⚠️ Error loading rejected party: {e}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Successfully loaded:")
        logger.info(f"   📍 {loaded_constituencies} constituencies")
        logger.info(f"   🎉 {loaded_parties} political parties")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error loading 2025 data: {e}")
        return False


def verify_data(connection_string):
    """Verify the loaded data"""
    try:
        conn = psycopg2.connect(connection_string)
        with conn.cursor() as cursor:
            # Check constituencies by assembly type
            cursor.execute("""
                SELECT assembly_type, electoral_system, COUNT(*) as count
                FROM constituencies 
                WHERE election_year = 2025
                GROUP BY assembly_type, electoral_system
                ORDER BY assembly_type, electoral_system
            """)
            
            constituency_stats = cursor.fetchall()
            
            # Check parties by status
            cursor.execute("""
                SELECT registration_status, COUNT(*) as count
                FROM political_parties
                WHERE election_year = 2025
                GROUP BY registration_status
            """)
            
            party_stats = cursor.fetchall()
            
            print("\n📊 Data Verification Results:")
            print("\n🏛️ Constituencies by Assembly & Electoral System:")
            total_constituencies = 0
            for assembly, electoral, count in constituency_stats:
                print(f"   • {assembly} ({electoral}): {count}")
                total_constituencies += count
            
            print(f"\n   📍 Total: {total_constituencies} constituencies")
            
            print("\n🎭 Political Parties by Status:")
            total_parties = 0
            for status, count in party_stats:
                print(f"   • {status.title()}: {count}")
                total_parties += count
            
            print(f"\n   🎉 Total: {total_parties} parties")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error verifying data: {e}")
        return False


def main():
    """Main migration process"""
    print("🚀 Starting Myanmar 2025 Election Data Migration")
    
    connection_string = get_database_url()
    logger.info(f"Connecting to database...")
    
    # Step 1: Create updated schema
    print("\n1️⃣ Creating updated database schema...")
    if not create_updated_schema(connection_string):
        print("❌ Schema creation failed")
        return False
    
    # Step 2: Load 2025 data
    print("\n2️⃣ Loading 2025 election data...")
    if not load_2025_data(connection_string):
        print("❌ Data loading failed")
        return False
    
    # Step 3: Verify data
    print("\n3️⃣ Verifying loaded data...")
    if not verify_data(connection_string):
        print("❌ Data verification failed")
        return False
    
    print("\n✅ Migration completed successfully!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)