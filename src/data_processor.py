#!/usr/bin/env python3
"""
Myanmar Election Data Processor

This module handles the cleaning, processing, and transformation of Myanmar
election constituency data from Excel format to structured JSON/CSV.
"""

import pandas as pd
import json
import numpy as np
import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MyanmarElectionDataProcessor:
    """Process Myanmar election constituency data."""
    
    def __init__(self, data_dir: str = "data"):
        """Initialize the data processor.
        
        Args:
            data_dir: Base data directory path
        """
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.geojson_dir = self.data_dir / "geojson"
        
        # Create directories if they don't exist
        self.processed_dir.mkdir(exist_ok=True)
        
        # Myanmar state/region name mappings
        self.state_region_mapping = {
            # States
            "ကချင်ပြည်နယ်": "Kachin State",
            "ကယားပြည်နယ်": "Kayah State", 
            "ကရင်ပြည်နယ်": "Kayin State",
            "ချင်းပြည်နယ်": "Chin State",
            "မွန်ပြည်နယ်": "Mon State",
            "ရခိုင်ပြည်နယ်": "Rakhine State",
            "ရှမ်းပြည်နယ်": "Shan State",
            # Regions (with different suffix variations)
            "စစ်ကိုင်းတိုင်း": "Sagaing Region",
            "စစ်ကိုင်းတိုင်းဒေသကြီး": "Sagaing Region",
            "တနင်္သာရီတိုင်း": "Tanintharyi Region",
            "တနင်္သာရီတိုင်းဒေသကြီး": "Tanintharyi Region",
            "ပဲခူးတိုင်း": "Bago Region",
            "ပဲခူးတိုင်းဒေသကြီး": "Bago Region",
            "မကွေးတိုင်း": "Magway Region",
            "မကွေးတိုင်းဒေသကြီး": "Magway Region",
            "မန္တလေးတိုင်း": "Mandalay Region",
            "မန္တလေးတိုင်းဒေသကြီး": "Mandalay Region",
            "ရန်ကုန်တိုင်း": "Yangon Region",
            "ရန်ကုန်တိုင်းဒေသကြီး": "Yangon Region",
            "ဧရာဝတီတိုင်း": "Ayeyarwady Region",
            "ဧရာဝတီတိုင်းဒေသကြီး": "Ayeyarwady Region",
            # Union Territory
            "နေပြည်တော်ပြည်ထောင်စုနယ်မြေ": "Naypyitaw Union Territory",
            "ပြည်ထောင်စုနယ်မြေ": "Naypyitaw Union Territory"
        }
        
    def load_raw_data(self, filename: str = "MAL-ELECTION-PLAN.xlsx") -> pd.DataFrame:
        """Load raw Excel data and perform initial cleaning.
        
        Args:
            filename: Excel file name in raw data directory
            
        Returns:
            DataFrame with raw data
        """
        file_path = self.raw_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")
            
        logger.info(f"Loading raw data from {file_path}")
        
        # Read Excel file, skipping Myanmar headers
        df_raw = pd.read_excel(file_path, header=None)
        
        # Find where actual data starts (first row with numeric ID)
        data_start_row = None
        for i, row in df_raw.iterrows():
            if pd.notna(row.iloc[0]) and str(row.iloc[0]).strip().isdigit():
                data_start_row = i
                break
                
        if data_start_row is None:
            raise ValueError("Could not find data start row")
            
        # Read with proper header
        df = pd.read_excel(file_path, skiprows=data_start_row-1)
        
        logger.info(f"Loaded {len(df)} constituency records")
        return df
        
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize the data.
        
        Args:
            df: Raw DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        logger.info("Cleaning and standardizing data")
        
        # Rename columns to English
        column_mapping = {
            df.columns[0]: "id",
            "တိုင်း/ပြည်နယ်": "state_region_mm",
            "မဲဆန္ဒနယ်": "constituency_mm", 
            df.columns[3]: "assembly_type_mm",
            "မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ": "areas_included_mm",
            "ကိုယ်စားလှယ်": "representatives",
            "မဲစနစ်": "electoral_system_mm"
        }
        
        df_clean = df.rename(columns=column_mapping)
        
        # Remove rows with missing critical data
        df_clean = df_clean.dropna(subset=["id", "state_region_mm", "constituency_mm"])
        
        # Convert ID to integer and ensure uniqueness
        df_clean["id"] = pd.to_numeric(df_clean["id"], errors="coerce")
        df_clean = df_clean.dropna(subset=["id"])
        df_clean["id"] = df_clean["id"].astype(int)
        
        # Remove duplicate IDs (keep first occurrence)
        df_clean = df_clean.drop_duplicates(subset=["id"], keep="first")
        
        # Convert representatives to integer
        df_clean["representatives"] = pd.to_numeric(df_clean["representatives"], errors="coerce").fillna(1).astype(int)
        
        # Add English translations
        df_clean["state_region_en"] = df_clean["state_region_mm"].map(self.state_region_mapping)
        
        # Clean constituency names (remove township suffix for cleaner English names)
        df_clean["constituency_en"] = df_clean["constituency_mm"].str.replace("မြို့နယ်", " Township")
        
        # Standardize assembly type
        df_clean["assembly_type"] = "pyithu"  # All records are Pyithu Hluttaw
        
        # Standardize electoral system
        df_clean["electoral_system"] = "FPTP"
        
        # Clean areas included text
        df_clean["areas_included_en"] = df_clean["areas_included_mm"].str.replace("မြို့နယ်တစ်ခုလုံး", "Entire Township")
        df_clean["areas_included_en"] = df_clean["areas_included_en"].str.replace("။", ".")
        
        # Fill missing areas_included_en
        df_clean["areas_included_en"] = df_clean["areas_included_en"].fillna("Area description not available")
        
        # Remove unnecessary columns
        columns_to_keep = [
            "id", "state_region_mm", "state_region_en", "constituency_mm", 
            "constituency_en", "assembly_type", "areas_included_mm", 
            "areas_included_en", "representatives", "electoral_system"
        ]
        
        df_clean = df_clean[columns_to_keep]
        
        # Reset index
        df_clean = df_clean.reset_index(drop=True)
        
        # Data validation
        self._validate_data(df_clean)
        
        logger.info(f"Data cleaning completed. {len(df_clean)} records processed")
        return df_clean
        
    def _validate_data(self, df: pd.DataFrame) -> None:
        """Validate cleaned data for consistency and completeness.
        
        Args:
            df: Cleaned DataFrame
        """
        logger.info("Validating data quality")
        
        # Check for required fields
        required_fields = ["id", "state_region_mm", "constituency_mm", "representatives"]
        for field in required_fields:
            if df[field].isnull().any():
                logger.warning(f"Missing values found in required field: {field}")
                
        # Check ID uniqueness
        if df["id"].duplicated().any():
            raise ValueError("Duplicate IDs found in data")
            
        # Check representative count (should all be 1)
        if not (df["representatives"] == 1).all():
            logger.warning("Non-standard representative count found")
            
        # Check for unmapped state/regions
        unmapped = df[df["state_region_en"].isnull()]["state_region_mm"].unique()
        if len(unmapped) > 0:
            logger.warning(f"Unmapped state/regions found: {unmapped}")
            
        logger.info("Data validation completed")
        
    def add_coordinates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add approximate coordinates for constituencies.
        
        Note: This is a simplified implementation. In production,
        you would use a proper geocoding service or coordinate database.
        
        Args:
            df: DataFrame with constituency data
            
        Returns:
            DataFrame with added coordinate columns
        """
        logger.info("Adding approximate coordinates")
        
        # Simplified coordinate mapping for major cities/townships
        # In production, this would be more comprehensive
        coordinate_mapping = {
            # States
            "ကချင်ပြည်နယ်": {"lat": 25.3848, "lng": 97.3962},
            "ကယားပြည်နယ်": {"lat": 19.3000, "lng": 97.2000},
            "ကရင်ပြည်နယ်": {"lat": 16.8000, "lng": 98.0000},
            "ချင်းပြည်နယ်": {"lat": 22.5000, "lng": 93.5000},
            "မွန်ပြည်နယ်": {"lat": 15.5000, "lng": 97.6000},
            "ရခိုင်ပြည်နယ်": {"lat": 20.1500, "lng": 94.1000},
            "ရှမ်းပြည်နယ်": {"lat": 21.0000, "lng": 98.0000},
            # Regions (both variations)
            "စစ်ကိုင်းတိုင်း": {"lat": 22.0000, "lng": 95.0000},
            "စစ်ကိုင်းတိုင်းဒေသကြီး": {"lat": 22.0000, "lng": 95.0000},
            "တနင်္သာရီတိုင်း": {"lat": 12.1000, "lng": 98.6000},
            "တနင်္သာရီတိုင်းဒေသကြီး": {"lat": 12.1000, "lng": 98.6000},
            "ပဲခူးတိုင်း": {"lat": 17.3000, "lng": 96.5000},
            "ပဲခူးတိုင်းဒေသကြီး": {"lat": 17.3000, "lng": 96.5000},
            "မကွေးတိုင်း": {"lat": 20.1500, "lng": 94.9000},
            "မကွေးတိုင်းဒေသကြီး": {"lat": 20.1500, "lng": 94.9000},
            "မန္တလေးတိုင်း": {"lat": 21.9588, "lng": 96.0891},
            "မန္တလေးတိုင်းဒေသကြီး": {"lat": 21.9588, "lng": 96.0891},
            "ရန်ကုန်တိုင်း": {"lat": 16.8661, "lng": 96.1951},
            "ရန်ကုန်တိုင်းဒေသကြီး": {"lat": 16.8661, "lng": 96.1951},
            "ဧရာဝတီတိုင်း": {"lat": 16.9000, "lng": 95.2000},
            "ဧရာဝတီတိုင်းဒေသကြီး": {"lat": 16.9000, "lng": 95.2000},
            # Union Territory
            "နေပြည်တော်ပြည်ထောင်စုနယ်မြေ": {"lat": 19.7451, "lng": 96.1297},
            "ပြည်ထောင်စုနယ်မြေ": {"lat": 19.7451, "lng": 96.1297}
        }
        
        # Add coordinates based on state/region
        df["lat"] = df["state_region_mm"].map(lambda x: coordinate_mapping.get(x, {}).get("lat"))
        df["lng"] = df["state_region_mm"].map(lambda x: coordinate_mapping.get(x, {}).get("lng"))
        
        # Add small random offset for constituencies within same state
        # This prevents overlapping points on the map
        np.random.seed(42)  # For reproducible results
        df["lat"] = df["lat"] + np.random.normal(0, 0.1, len(df))
        df["lng"] = df["lng"] + np.random.normal(0, 0.1, len(df))
        
        logger.info("Coordinate assignment completed")
        return df
        
    def generate_summary_statistics(self, df: pd.DataFrame) -> Dict:
        """Generate summary statistics for the dataset.
        
        Args:
            df: Processed DataFrame
            
        Returns:
            Dictionary with summary statistics
        """
        logger.info("Generating summary statistics")
        
        stats = {
            "total_constituencies": len(df),
            "total_representatives": df["representatives"].sum(),
            "states_regions": {
                "total": df["state_region_en"].nunique(),
                "breakdown": df.groupby("state_region_en").agg({
                    "id": "count",
                    "representatives": "sum"
                }).rename(columns={"id": "constituencies"}).to_dict("index")
            },
            "assembly_types": df["assembly_type"].value_counts().to_dict(),
            "electoral_system": df["electoral_system"].value_counts().to_dict()
        }
        
        return stats
        
    def save_processed_data(self, df: pd.DataFrame, stats: Dict) -> None:
        """Save processed data in multiple formats.
        
        Args:
            df: Processed DataFrame
            stats: Summary statistics
        """
        logger.info("Saving processed data")
        
        # Convert numpy/pandas types to Python native types for JSON serialization
        df_json = df.copy()
        for col in df_json.columns:
            if df_json[col].dtype == 'int64':
                df_json[col] = df_json[col].astype(int)
            elif df_json[col].dtype == 'float64':
                df_json[col] = df_json[col].astype(float)
                
        # Save as JSON (for web applications)
        json_data = {
            "metadata": {
                "total_records": int(len(df)),
                "last_updated": pd.Timestamp.now().isoformat(),
                "data_source": "Myanmar Election Commission"
            },
            "statistics": self._convert_to_json_serializable(stats),
            "constituencies": df_json.to_dict("records")
        }
        
        with open(self.processed_dir / "myanmar_constituencies.json", "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
            
        # Save as CSV (for analysis)
        df.to_csv(self.processed_dir / "myanmar_constituencies.csv", index=False, encoding="utf-8")
        
        # Save summary statistics separately
        with open(self.processed_dir / "summary_statistics.json", "w", encoding="utf-8") as f:
            json.dump(self._convert_to_json_serializable(stats), f, ensure_ascii=False, indent=2)
            
        logger.info("Data saved successfully")
        
    def _convert_to_json_serializable(self, obj):
        """Convert numpy/pandas types to JSON serializable types."""
        if isinstance(obj, dict):
            return {k: self._convert_to_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_json_serializable(v) for v in obj]
        elif isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        else:
            return obj
        
    def process_all(self) -> Tuple[pd.DataFrame, Dict]:
        """Run the complete data processing pipeline.
        
        Returns:
            Tuple of (processed DataFrame, summary statistics)
        """
        logger.info("Starting complete data processing pipeline")
        
        # Load and process data
        df_raw = self.load_raw_data()
        df_clean = self.clean_data(df_raw)
        df_with_coords = self.add_coordinates(df_clean)
        
        # Generate statistics
        stats = self.generate_summary_statistics(df_with_coords)
        
        # Save results
        self.save_processed_data(df_with_coords, stats)
        
        logger.info("Data processing pipeline completed successfully")
        return df_with_coords, stats


def main():
    """Main function to run data processing."""
    processor = MyanmarElectionDataProcessor()
    df, stats = processor.process_all()
    
    print(f"\n✅ Processing completed successfully!")
    print(f"📊 Total constituencies: {stats['total_constituencies']}")
    print(f"🏛️ Total representatives: {stats['total_representatives']}")
    print(f"🗺️ States/Regions covered: {stats['states_regions']['total']}")
    
    print(f"\n📁 Files created:")
    print(f"   • data/processed/myanmar_constituencies.json")
    print(f"   • data/processed/myanmar_constituencies.csv") 
    print(f"   • data/processed/summary_statistics.json")


if __name__ == "__main__":
    main()