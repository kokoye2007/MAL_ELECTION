#!/usr/bin/env python3
"""
Fix database schema by adding missing columns
"""

import os
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

def fix_schema():
    """Add missing columns to constituencies table"""
    connection_string = get_database_url()
    
    try:
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        # Check existing columns
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'constituencies'
            ORDER BY column_name
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        logger.info(f"Existing columns: {existing_columns}")
        
        # Add missing columns
        missing_columns = []
        
        # Check and add township_name_eng
        if 'township_name_eng' not in existing_columns:
            cursor.execute("ALTER TABLE constituencies ADD COLUMN township_name_eng VARCHAR(255)")
            missing_columns.append('township_name_eng')
            logger.info("Added township_name_eng column")
        
        # Check and add constituency_en
        if 'constituency_en' not in existing_columns:
            cursor.execute("ALTER TABLE constituencies ADD COLUMN constituency_en VARCHAR(255)")
            missing_columns.append('constituency_en')
            logger.info("Added constituency_en column")
        
        # Check and add constituency_areas_mm
        if 'constituency_areas_mm' not in existing_columns:
            cursor.execute("ALTER TABLE constituencies ADD COLUMN constituency_areas_mm TEXT")
            missing_columns.append('constituency_areas_mm')
            logger.info("Added constituency_areas_mm column")
        
        # Check and add boundary_codes
        if 'boundary_codes' not in existing_columns:
            cursor.execute("ALTER TABLE constituencies ADD COLUMN boundary_codes TEXT[]")
            missing_columns.append('boundary_codes')
            logger.info("Added boundary_codes column")
        
        # Check and add tsp_pcode
        if 'tsp_pcode' not in existing_columns:
            cursor.execute("ALTER TABLE constituencies ADD COLUMN tsp_pcode VARCHAR(50)")
            missing_columns.append('tsp_pcode')
            logger.info("Added tsp_pcode column")
        
        # Check and add coordinate_source
        if 'coordinate_source' not in existing_columns:
            cursor.execute("ALTER TABLE constituencies ADD COLUMN coordinate_source VARCHAR(50) DEFAULT 'approximate'")
            missing_columns.append('coordinate_source')
            logger.info("Added coordinate_source column")
        
        # Check and add validation_status
        if 'validation_status' not in existing_columns:
            cursor.execute("ALTER TABLE constituencies ADD COLUMN validation_status VARCHAR(20) DEFAULT 'pending'")
            missing_columns.append('validation_status')
            logger.info("Added validation_status column")
        
        # Check and add constituency_areas_en
        if 'constituency_areas_en' not in existing_columns:
            cursor.execute("ALTER TABLE constituencies ADD COLUMN constituency_areas_en TEXT")
            missing_columns.append('constituency_areas_en')
            logger.info("Added constituency_areas_en column")
        
        # Check and add electoral_system
        if 'electoral_system' not in existing_columns:
            cursor.execute("ALTER TABLE constituencies ADD COLUMN electoral_system VARCHAR(10) DEFAULT 'FPTP'")
            missing_columns.append('electoral_system')
            logger.info("Added electoral_system column")
        
        conn.commit()
        
        if missing_columns:
            logger.info(f"✅ Added missing columns: {missing_columns}")
        else:
            logger.info("✅ All required columns already exist")
        
        # Verify final schema
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'constituencies'
            ORDER BY column_name
        """)
        final_columns = [row[0] for row in cursor.fetchall()]
        logger.info(f"Final schema: {final_columns}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error fixing schema: {e}")
        return False

if __name__ == "__main__":
    success = fix_schema()
    exit(0 if success else 1)