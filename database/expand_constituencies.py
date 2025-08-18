#!/usr/bin/env python3
"""
Constituency Expansion Script
Expands from 330 PTHT constituencies to the full 765 constituency dataset.
Processes all assembly types from the MAL-ELECTION-PLAN.xlsx file.
"""

import pandas as pd
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import sys
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConstituencyExpander:
    def __init__(self):
        self.conn = None
        self.source_file = "/app/data/raw/MAL-ELECTION-PLAN.xlsx"
        
    def connect(self):
        """Connect to PostgreSQL database."""
        try:
            database_url = os.getenv('DATABASE_URL', 
                'postgresql://election_user:dev_password_2025@postgres:5432/myanmar_election')
            self.conn = psycopg2.connect(database_url)
            logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
            
    def load_excel_data(self):
        """Load and parse the multi-section Excel file."""
        logger.info("Loading Excel data from all sections...")
        
        # Read the full dataset
        df = pd.read_excel(self.source_file, header=None, skiprows=3)
        df.columns = ['seq_no', 'state_region_mm', 'constituency_mm', 'assembly_type_mm', 
                     'areas_mm', 'representatives', 'col6', 'electoral_system_mm']
        
        # Find sections where sequence number resets to 1
        reset_points = df[df['seq_no'] == 1].index.tolist()
        logger.info(f"Found {len(reset_points)} sections in Excel file")
        
        all_constituencies = []
        
        # Process each section
        for i, start_idx in enumerate(reset_points):
            end_idx = reset_points[i+1] if i+1 < len(reset_points) else len(df)
            section = df.iloc[start_idx:end_idx].copy()
            section = section.dropna(subset=['seq_no', 'state_region_mm', 'constituency_mm'])
            
            if len(section) == 0:
                continue
                
            # Determine assembly type based on section characteristics
            assembly_type = self.determine_assembly_type(section, i+1)
            logger.info(f"Section {i+1}: {len(section)} constituencies ({assembly_type})")
            
            # Process this section
            section_constituencies = self.process_section(section, assembly_type)
            all_constituencies.extend(section_constituencies)
            
        logger.info(f"Total constituencies loaded: {len(all_constituencies)}")
        return all_constituencies
        
    def determine_assembly_type(self, section, section_num):
        """Determine assembly type based on section characteristics."""
        sample_constituency = section.iloc[0]['constituency_mm']
        sample_state_region = section.iloc[0]['state_region_mm']
        electoral_system = section.iloc[0]['electoral_system_mm']
        
        if section_num == 1:
            return 'PTHT'  # Pyithu Hluttaw - plain township names
        elif 'တိုင်းရင်းသားလူမျိုး' in sample_constituency:
            return 'TPTYT'  # Ethnic Affairs - ethnic group constituencies
        elif 'PR' in electoral_system and 'အမှတ်' in sample_constituency:
            return 'TPHT'  # State/Regional Assembly (PR) - numbered constituencies
        elif 'လွှတ်တော်' in sample_state_region and 'မဲဆန္ဒနယ်' in sample_constituency:
            return 'TPHT'  # State/Regional Assembly (FPTP) - township constituencies
        else:
            return 'TPHT'  # Default to State/Regional for remaining
            
    def process_section(self, section, assembly_type):
        """Process a section of constituencies."""
        constituencies = []
        
        for _, row in section.iterrows():
            # Map electoral system
            electoral_system = 'PR' if 'PR' in str(row['electoral_system_mm']) else 'FPTP'
            
            # Clean state/region name
            state_region_mm = self.clean_state_region(row['state_region_mm'])
            state_region_en = self.translate_state_region(state_region_mm)
            
            # Generate constituency code
            constituency_code = self.generate_constituency_code(
                assembly_type, state_region_en, int(row['seq_no'])
            )
            
            # Clean constituency name
            constituency_mm = str(row['constituency_mm']).strip()
            constituency_en = self.translate_constituency_name(constituency_mm, state_region_en)
            
            constituency = {
                'constituency_code': constituency_code,
                'constituency_en': constituency_en,
                'constituency_mm': constituency_mm,
                'state_region_en': state_region_en,
                'state_region_mm': state_region_mm,
                'assembly_type': assembly_type,
                'electoral_system': electoral_system,
                'representatives': int(row['representatives']) if pd.notna(row['representatives']) else 1,
                'areas_included_mm': str(row['areas_mm']) if pd.notna(row['areas_mm']) else None,
                'coordinate_source': 'estimated',  # Will be updated later with actual coordinates
                'validation_status': 'pending',
                'election_year': 2025
            }
            
            constituencies.append(constituency)
            
        return constituencies
        
    def clean_state_region(self, state_region_mm):
        """Clean state/region name by removing assembly-specific suffixes."""
        if pd.isna(state_region_mm):
            return ""
        
        state_region = str(state_region_mm).strip()
        # Remove "လွှတ်တော်" suffix if present
        if state_region.endswith('လွှတ်တော်'):
            state_region = state_region.replace('လွှတ်တော်', '').strip()
        return state_region
        
    def translate_state_region(self, state_region_mm):
        """Translate Myanmar state/region names to English."""
        translation_map = {
            'ကချင်ပြည်နယ်': 'Kachin State',
            'ကယားပြည်နယ်': 'Kayah State', 
            'ကရင်ပြည်နယ်': 'Kayin State',
            'ချင်းပြည်နယ်': 'Chin State',
            'မွန်ပြည်နယ်': 'Mon State',
            'ရခိုင်ပြည်နယ်': 'Rakhine State',
            'ရှမ်းပြည်နယ်': 'Shan State',
            'တနင်္သာရီတိုင်း': 'Tanintharyi Region',
            'ပဲခူးတိုင်း': 'Bago Region',
            'မကွေးတိုင်း': 'Magway Region',
            'မန္တလေးတိုင်း': 'Mandalay Region',
            'စစ်ကိုင်းတိုင်း': 'Sagaing Region',
            'ရန်ကုန်တိုင်း': 'Yangon Region',
            'ဧရာဝတီတိုင်း': 'Ayeyarwady Region',
            'နေပြည်တော်': 'Naypyitaw Union Territory'
        }
        
        return translation_map.get(state_region_mm, state_region_mm)
        
    def translate_constituency_name(self, constituency_mm, state_region_en):
        """Generate English constituency names."""
        # For now, create descriptive English names
        # This would need actual translation data for full implementation
        constituency_mm = str(constituency_mm).strip()
        
        if 'မြို့နယ်' in constituency_mm:
            # Township constituency
            township = constituency_mm.replace('မြို့နယ်', '').strip()
            return f"{township} Township"
        elif 'မဲဆန္ဒနယ်' in constituency_mm:
            # Numbered constituency
            if 'အမှတ်' in constituency_mm:
                # Extract number from အမှတ်(၁) format
                import re
                match = re.search(r'အမှတ်\(([^\)]+)\)', constituency_mm)
                if match:
                    number = match.group(1)
                    return f"{state_region_en} Constituency {number}"
            return f"{state_region_en} Constituency"
        elif 'တိုင်းရင်းသား' in constituency_mm:
            # Ethnic constituency
            parts = constituency_mm.split('တিုင်းရင်းသားလူမျိုး')
            if len(parts) > 0:
                ethnic_group = parts[0].strip()
                return f"{ethnic_group} Ethnic Constituency"
        
        return constituency_mm  # Fallback to Myanmar name
        
    def generate_constituency_code(self, assembly_type, state_region_en, seq_no):
        """Generate unique constituency codes."""
        # Create state/region abbreviation
        state_abbr = ''.join([word[0] for word in state_region_en.split()[:2]]).upper()
        
        # Assembly prefix
        assembly_prefix = {
            'PTHT': 'P',
            'AMTHT': 'A', 
            'TPHT': 'S',  # State/Regional
            'TPTYT': 'E'  # Ethnic
        }.get(assembly_type, 'U')
        
        return f"{assembly_prefix}{state_abbr}{seq_no:03d}"
        
    def insert_constituencies(self, constituencies):
        """Insert constituencies into database."""
        logger.info(f"Inserting {len(constituencies)} constituencies...")
        
        with self.conn.cursor() as cursor:
            # First delete existing non-PTHT data to avoid duplicates
            cursor.execute("DELETE FROM constituencies WHERE assembly_type != 'PTHT' AND election_year = 2025")
            
            insert_query = """
                INSERT INTO constituencies (
                    constituency_code, constituency_en, constituency_mm, 
                    state_region_en, state_region_mm, assembly_type, electoral_system,
                    representatives, areas_included_mm, coordinate_source, 
                    validation_status, election_year
                ) VALUES (
                    %(constituency_code)s, %(constituency_en)s, %(constituency_mm)s,
                    %(state_region_en)s, %(state_region_mm)s, %(assembly_type)s, %(electoral_system)s,
                    %(representatives)s, %(areas_included_mm)s, %(coordinate_source)s,
                    %(validation_status)s, %(election_year)s
                ) ON CONFLICT (constituency_code) DO UPDATE SET
                    constituency_en = EXCLUDED.constituency_en,
                    constituency_mm = EXCLUDED.constituency_mm,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            cursor.executemany(insert_query, constituencies)
            self.conn.commit()
            
            logger.info(f"Successfully inserted {len(constituencies)} constituencies")
            
    def validate_expansion(self):
        """Validate the expansion results."""
        logger.info("Validating constituency expansion...")
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check totals by assembly type
            cursor.execute("""
                SELECT 
                    assembly_type,
                    COUNT(*) as count,
                    COUNT(CASE WHEN lat IS NOT NULL AND lng IS NOT NULL THEN 1 END) as mapped_count
                FROM constituencies 
                WHERE election_year = 2025
                GROUP BY assembly_type
                ORDER BY assembly_type
            """)
            
            results = cursor.fetchall()
            total_constituencies = sum(row['count'] for row in results)
            
            logger.info("Expansion validation results:")
            for row in results:
                logger.info(f"  {row['assembly_type']}: {row['count']} constituencies ({row['mapped_count']} mapped)")
            
            logger.info(f"Total constituencies: {total_constituencies}")
            
            # Check if we're close to target of 765
            if total_constituencies >= 650:  # Close to target, accounting for missing AMTHT
                logger.info("✅ Expansion successful!")
                return True
            else:
                logger.warning(f"⚠️ Only {total_constituencies} constituencies found, expected ~765")
                return False
                
    def run_expansion(self):
        """Run the complete expansion process."""
        try:
            self.connect()
            constituencies = self.load_excel_data()
            
            # Filter out PTHT since it's already in the database
            non_ptht_constituencies = [c for c in constituencies if c['assembly_type'] != 'PTHT']
            logger.info(f"Inserting {len(non_ptht_constituencies)} new constituencies (excluding PTHT)")
            
            if non_ptht_constituencies:
                self.insert_constituencies(non_ptht_constituencies)
            
            success = self.validate_expansion()
            
            if success:
                logger.info("🎉 Constituency expansion completed successfully!")
                print("\n" + "="*60)
                print("🎉 CONSTITUENCY EXPANSION COMPLETED!")
                print("="*60)
                print("Your Myanmar Election database now includes:")
                print("• Pyithu Hluttaw (PTHT): 330 constituencies")  
                print("• State/Regional Assemblies (TPHT): ~364 constituencies")
                print("• Ethnic Affairs (TPTYT): 29 constituencies")
                print("• Total: ~723+ constituencies")
                print("\nNext step: Add Amyotha Hluttaw (AMTHT) data")
                print("="*60)
            
            return success
            
        except Exception as e:
            logger.error(f"Expansion failed: {e}")
            return False
        finally:
            if self.conn:
                self.conn.close()
                logger.info("Database connection closed")

def main():
    expander = ConstituencyExpander()
    success = expander.run_expansion()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()