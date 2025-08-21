#!/usr/bin/env python3
"""
Myanmar Election Data Processor 2025
Refactored version to handle new multi-sheet Excel format with boundary codes
"""

import pandas as pd
import json
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import logging
from dataclasses import dataclass, asdict
from enum import Enum

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AssemblyType(Enum):
    """Parliament assembly types"""
    PTHT = "ပြည်သူ့လွှတ်တော်"  # Pyithu Hluttaw (Lower House)
    AMTHT = "အမျိုးသားလွှတ်တော်"  # Amyotha Hluttaw (Upper House)
    TPHT = "တိုင်းပြည်နယ်လွှတ်တော်"  # State/Regional Hluttaw
    ETHNIC = "တိုင်းရင်းသား"  # Ethnic Affairs


class ElectoralSystem(Enum):
    """Electoral systems"""
    FPTP = "FPTP"  # First Past the Post
    PR = "PR"  # Proportional Representation


@dataclass
class Constituency:
    """Data class for constituency information"""
    id: int
    township_name_eng: str
    township_name_mm: str
    constituency_name_mm: str
    constituency_areas_mm: str
    state_region_mm: str
    state_region_en: str
    tsp_pcode: str
    assembly_type: str
    electoral_system: str
    representatives: int
    lat: Optional[float] = None
    lng: Optional[float] = None
    boundary_codes: Optional[List[str]] = None


class DataLoader:
    """Handles loading data from various sources"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.raw_dir = data_dir / "raw"
        
    def load_excel_sheets(self, filename: str = "2025-ELECTION-PLAN-DATA-FINAL.xlsx") -> Dict[str, pd.DataFrame]:
        """Load all sheets from Excel file"""
        file_path = Path("../UPDATE") / filename if not (self.raw_dir / filename).exists() else self.raw_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")
            
        logger.info(f"Loading Excel file from {file_path}")
        
        # Read all sheets
        xl = pd.ExcelFile(file_path)
        sheets = {}
        
        for sheet_name in xl.sheet_names:
            logger.info(f"Loading sheet: {sheet_name}")
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            sheets[sheet_name] = df
            
        return sheets


class DataCleaner:
    """Handles data cleaning and standardization"""
    
    def __init__(self):
        # Myanmar to English state/region mapping
        self.state_region_mapping = {
            # States
            "ကချင်ပြည်နယ်": "Kachin State",
            "ကယားပြည်နယ်": "Kayah State",
            "ကရင်ပြည်နယ်": "Kayin State",
            "ချင်းပြည်နယ်": "Chin State",
            "မွန်ပြည်နယ်": "Mon State",
            "ရခိုင်ပြည်နယ်": "Rakhine State",
            "ရှမ်းပြည်နယ်": "Shan State",
            # Regions
            "စစ်ကိုင်းတိုင်းဒေသကြီး": "Sagaing Region",
            "တနင်္သာရီတိုင်းဒေသကြီး": "Tanintharyi Region",
            "ပဲခူးတိုင်းဒေသကြီး": "Bago Region",
            "မကွေးတိုင်းဒေသကြီး": "Magway Region",
            "မန္တလေးတိုင်းဒေသကြီး": "Mandalay Region",
            "ရန်ကုန်တိုင်းဒေသကြီး": "Yangon Region",
            "ဧရာဝတီတိုင်းဒေသကြီး": "Ayeyarwady Region",
            # Union Territory
            "နေပြည်တော်ပြည်ထောင်စုနယ်မြေ": "Naypyitaw Union Territory"
        }
        
    def clean_sheet(self, df: pd.DataFrame, assembly_type: str) -> List[Constituency]:
        """Clean and standardize a single sheet"""
        constituencies = []
        
        # Standardize column names
        if 'Tsp_Pcode' in df.columns:
            df['tsp_pcode'] = df['Tsp_Pcode']
        if 'Township_Name_Eng' in df.columns:
            df['township_name_eng'] = df['Township_Name_Eng']
            
        # Determine electoral system
        electoral_system = ElectoralSystem.PR.value if "(PR)" in assembly_type else ElectoralSystem.FPTP.value
        
        # Process each row
        for idx, row in df.iterrows():
            try:
                # Skip if no valid ID
                if pd.isna(row.get('Unnamed: 0')):
                    continue
                    
                state_region_mm = str(row.get('တိုင်း/ပြည်နယ်', ''))
                
                constituency = Constituency(
                    id=int(row.get('Unnamed: 0', idx)),
                    township_name_eng=str(row.get('township_name_eng', '')),
                    township_name_mm=str(row.get('မြို့နယ်', '')),
                    constituency_name_mm=str(row.get('မဲဆန္ဒနယ်', '')),
                    constituency_areas_mm=str(row.get('မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ', '')),
                    state_region_mm=state_region_mm,
                    state_region_en=self.state_region_mapping.get(state_region_mm, state_region_mm),
                    tsp_pcode=str(row.get('tsp_pcode', '')),
                    assembly_type=self._map_assembly_type(assembly_type),
                    electoral_system=electoral_system,
                    representatives=int(row.get('ကိုယ်စားလှယ်', 1))
                )
                
                # Parse boundary codes if contains +
                if '+' in constituency.tsp_pcode:
                    constituency.boundary_codes = constituency.tsp_pcode.split('+')
                    
                constituencies.append(constituency)
                
            except Exception as e:
                logger.warning(f"Error processing row {idx}: {e}")
                continue
                
        return constituencies
    
    def _map_assembly_type(self, sheet_name: str) -> str:
        """Map sheet name to assembly type code"""
        if "ပြည်သူ့လွှတ်တော်" in sheet_name:
            return "PTHT"
        elif "အမျိုးသားလွှတ်တော်" in sheet_name:
            return "AMTHT"
        elif "တိုင်းပြည်နယ်လွှတ်တော်" in sheet_name:
            return "TPHT"
        elif "တိုင်းရင်းသား" in sheet_name:
            return "ETHNIC"
        else:
            return "UNKNOWN"


class BoundaryCodeMapper:
    """Maps township codes to boundary geometries"""
    
    def __init__(self):
        self.geonode_base_url = "https://geonode.themimu.info"
        self.boundary_cache = {}
        
    def get_boundary_for_code(self, tsp_pcode: str) -> Optional[Dict]:
        """Fetch boundary geometry for a township code"""
        # This would connect to GeoNode API
        # For now, return placeholder
        if tsp_pcode in self.boundary_cache:
            return self.boundary_cache[tsp_pcode]
            
        # TODO: Implement actual GeoNode API call
        logger.info(f"Would fetch boundary for: {tsp_pcode}")
        return None
        
    def process_multiple_codes(self, codes: List[str]) -> Optional[Dict]:
        """Process constituencies spanning multiple townships"""
        # Merge multiple boundary polygons
        boundaries = []
        for code in codes:
            boundary = self.get_boundary_for_code(code)
            if boundary:
                boundaries.append(boundary)
                
        # TODO: Merge geometries
        return boundaries[0] if boundaries else None


class CoordinateService:
    """Handles coordinate assignment and geocoding"""
    
    def __init__(self):
        # Basic coordinate mapping for states/regions
        self.state_coordinates = {
            "Kachin State": {"lat": 25.3848, "lng": 97.3962},
            "Kayah State": {"lat": 19.3000, "lng": 97.2000},
            "Kayin State": {"lat": 16.8000, "lng": 98.0000},
            "Chin State": {"lat": 22.5000, "lng": 93.5000},
            "Mon State": {"lat": 15.5000, "lng": 97.6000},
            "Rakhine State": {"lat": 20.1500, "lng": 94.1000},
            "Shan State": {"lat": 21.0000, "lng": 98.0000},
            "Sagaing Region": {"lat": 22.0000, "lng": 95.0000},
            "Tanintharyi Region": {"lat": 12.1000, "lng": 98.6000},
            "Bago Region": {"lat": 17.3000, "lng": 96.5000},
            "Magway Region": {"lat": 20.1500, "lng": 94.9000},
            "Mandalay Region": {"lat": 21.9588, "lng": 96.0891},
            "Yangon Region": {"lat": 16.8661, "lng": 96.1951},
            "Ayeyarwady Region": {"lat": 16.9000, "lng": 95.2000},
            "Naypyitaw Union Territory": {"lat": 19.7451, "lng": 96.1297}
        }
        
    def assign_coordinates(self, constituencies: List[Constituency], 
                          state_region_mapping: Dict[str, str]) -> List[Constituency]:
        """Assign coordinates to constituencies"""
        np.random.seed(42)  # For reproducible offsets
        
        for const in constituencies:
            # Get English state name
            state_en = state_region_mapping.get(const.state_region_mm, const.state_region_mm)
            
            # Get base coordinates
            if state_en in self.state_coordinates:
                base_coords = self.state_coordinates[state_en]
                # Add small random offset to prevent overlapping
                const.lat = base_coords["lat"] + np.random.normal(0, 0.1)
                const.lng = base_coords["lng"] + np.random.normal(0, 0.1)
            else:
                logger.warning(f"No coordinates for: {state_en}")
                
        return constituencies


class PartyDataProcessor:
    """Processes political party registration data"""
    
    def __init__(self):
        self.registered_parties = []
        self.rejected_parties = []
        
    def load_party_data(self, reg_file: Path, rej_file: Path) -> Tuple[List[Dict], List[Dict]]:
        """Load party data from markdown files"""
        # Parse registered parties
        if reg_file.exists():
            with open(reg_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self.registered_parties = self._parse_party_table(content)
                
        # Parse rejected parties
        if rej_file.exists():
            with open(rej_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self.rejected_parties = self._parse_party_table(content)
                
        logger.info(f"Loaded {len(self.registered_parties)} registered parties")
        logger.info(f"Loaded {len(self.rejected_parties)} rejected parties")
        
        return self.registered_parties, self.rejected_parties
        
    def _parse_party_table(self, markdown_content: str) -> List[Dict]:
        """Parse markdown table to extract party data"""
        parties = []
        lines = markdown_content.split('\n')
        
        for line in lines:
            if line.startswith('|') and not line.startswith('| ---'):
                parts = [p.strip() for p in line.split('|')[1:-1]]
                
                if len(parts) >= 4 and parts[0].isdigit():
                    party = {
                        'id': int(parts[0]),
                        'name_mm': parts[1],
                        'registration_date': parts[2],
                        'announcement_number': parts[3],
                        'notes': parts[4] if len(parts) > 4 else ''
                    }
                    parties.append(party)
                    
        return parties


class DataExporter:
    """Handles exporting processed data to various formats"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        
    def export_to_json(self, constituencies: List[Constituency], 
                      parties: Dict[str, List], 
                      filename: str = "myanmar_election_2025.json") -> None:
        """Export data to JSON format"""
        output_data = {
            "metadata": {
                "total_constituencies": len(constituencies),
                "last_updated": pd.Timestamp.now().isoformat(),
                "data_source": "Myanmar Election Commission 2025"
            },
            "constituencies": [asdict(c) for c in constituencies],
            "parties": parties,
            "statistics": self._generate_statistics(constituencies)
        }
        
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
            
        logger.info(f"Exported JSON to: {output_path}")
        
    def export_to_csv(self, constituencies: List[Constituency], 
                     filename: str = "myanmar_constituencies_2025.csv") -> None:
        """Export constituencies to CSV"""
        df = pd.DataFrame([asdict(c) for c in constituencies])
        
        output_path = self.output_dir / filename
        df.to_csv(output_path, index=False, encoding='utf-8')
        
        logger.info(f"Exported CSV to: {output_path}")
        
    def _generate_statistics(self, constituencies: List[Constituency]) -> Dict:
        """Generate summary statistics"""
        df = pd.DataFrame([asdict(c) for c in constituencies])
        
        return {
            "by_assembly": df.groupby('assembly_type').size().to_dict(),
            "by_electoral_system": df.groupby('electoral_system').size().to_dict(),
            "total_representatives": int(df['representatives'].sum()),
            "constituencies_with_boundaries": int(df['tsp_pcode'].notna().sum())
        }


class Myanmar2025ElectionProcessor:
    """Main processor orchestrating all components"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.loader = DataLoader(self.data_dir)
        self.cleaner = DataCleaner()
        self.boundary_mapper = BoundaryCodeMapper()
        self.coordinate_service = CoordinateService()
        self.party_processor = PartyDataProcessor()
        self.exporter = DataExporter(self.data_dir / "processed")
        
    def process_all(self) -> None:
        """Run complete processing pipeline"""
        logger.info("Starting Myanmar 2025 Election Data Processing")
        
        # Load Excel sheets
        sheets = self.loader.load_excel_sheets()
        
        # Process all constituencies
        all_constituencies = []
        for sheet_name, df in sheets.items():
            logger.info(f"Processing sheet: {sheet_name}")
            constituencies = self.cleaner.clean_sheet(df, sheet_name)
            
            # Assign coordinates
            constituencies = self.coordinate_service.assign_coordinates(
                constituencies, 
                self.cleaner.state_region_mapping
            )
            
            all_constituencies.extend(constituencies)
            
        logger.info(f"Processed {len(all_constituencies)} total constituencies")
        
        # Load party data
        reg_file = Path("../UPDATE/reg.md")
        rej_file = Path("../UPDATE/rej.md")
        registered, rejected = self.party_processor.load_party_data(reg_file, rej_file)
        
        parties = {
            "registered": registered,
            "rejected": rejected
        }
        
        # Export results
        self.exporter.export_to_json(all_constituencies, parties)
        self.exporter.export_to_csv(all_constituencies)
        
        # Print summary
        print(f"\n✅ Processing completed successfully!")
        print(f"📊 Total constituencies: {len(all_constituencies)}")
        
        # Count by assembly
        assembly_counts = {}
        for c in all_constituencies:
            assembly_counts[c.assembly_type] = assembly_counts.get(c.assembly_type, 0) + 1
            
        print(f"\n🏛️ By Assembly Type:")
        for assembly, count in assembly_counts.items():
            print(f"   • {assembly}: {count} constituencies")
            
        print(f"\n🎉 Registered parties: {len(registered)}")
        print(f"❌ Rejected parties: {len(rejected)}")
        
        print(f"\n📁 Files created:")
        print(f"   • data/processed/myanmar_election_2025.json")
        print(f"   • data/processed/myanmar_constituencies_2025.csv")


def main():
    """Main entry point"""
    processor = Myanmar2025ElectionProcessor()
    processor.process_all()


if __name__ == "__main__":
    main()