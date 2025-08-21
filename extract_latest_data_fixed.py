#!/usr/bin/env python3
"""
Extract Latest Election Data from Excel to JSON/YAML
Processes the official 2025-ELECTION-PLAN-DATA-FINAL.xlsx file
"""

import pandas as pd
import json
import yaml
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_get(row, key, default=''):
    """Safely get value from row with fallback"""
    try:
        val = row.get(key, default)
        return str(val) if pd.notna(val) else default
    except:
        return default

def safe_int(row, key, default=1):
    """Safely get integer value from row"""
    try:
        val = row.get(key, default)
        return int(val) if pd.notna(val) else default
    except:
        return default

def create_state_region_mapping():
    """Create state/region mapping for English names"""
    mapping = {
        'ကချင်ပြည်နယ်': 'Kachin State',
        'ကယားပြည်နယ်': 'Kayah State', 
        'ကရင်ပြည်နယ်': 'Kayin State',
        'ချင်းပြည်နယ်': 'Chin State',
        'စစ်ကိုင်းတိုင်းဒေသကြီး': 'Sagaing Region',
        'တနင်္သာရီတိုင်းဒေသကြီး': 'Tanintharyi Region',
        'ပဲခူးတိုင်းဒေသကြီး': 'Bago Region',
        'မကွေးတိုင်းဒေသကြီး': 'Magway Region',
        'မန္တလေးတိုင်းဒေသကြီး': 'Mandalay Region',
        'မွန်ပြည်နယ်': 'Mon State',
        'ရခိုင်ပြည်နယ်': 'Rakhine State',
        'ရန်ကုန်တိုင်းဒေသကြီး': 'Yangon Region',
        'ရှမ်းပြည်နယ်': 'Shan State',
        'ဧရာဝတီတိုင်းဒေသကြီး': 'Ayeyarwady Region',
        'နေပြည်တော်ပြည်နယ်': 'Naypyidaw Union Territory'
    }
    return mapping

def process_all_sheets(xlsx_path):
    """Process all sheets in the Excel file"""
    all_constituencies = []
    state_mapping = create_state_region_mapping()
    
    # 1. Pyithu Hluttaw (ပြည်သူ့လွှတ်တော်)
    logger.info("📊 Processing Pyithu Hluttaw...")
    df = pd.read_excel(xlsx_path, sheet_name='ပြည်သူ့လွှတ်တော် (FPTP)')
    for _, row in df.iterrows():
        constituency = {
            'id': safe_int(row, 'Unnamed: 0'),
            'township_name_en': safe_get(row, 'Township_Name_Eng'),
            'constituency_mm': safe_get(row, 'မြို့နယ်.1'),
            'constituency_en': f"{safe_get(row, 'Township_Name_Eng')} Township",
            'areas_included_mm': safe_get(row, 'မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ'),
            'areas_included_en': f"{safe_get(row, 'Township_Name_Eng')} Township (entire)",
            'township_mm': safe_get(row, 'မြို့နယ်'),
            'state_region_mm': safe_get(row, 'တိုင်း/ပြည်နယ်'),
            'state_region_en': state_mapping.get(safe_get(row, 'တိုင်း/ပြည်နယ်'), safe_get(row, 'တিုန်း/ပြည်နယ်')),
            'tsp_pcode': safe_get(row, 'Tsp_Pcode'),
            'representatives': safe_int(row, 'ကိုယ်စားလှယ်'),
            'electoral_system_mm': safe_get(row, 'မဲစနစ်'),
            'electoral_system_en': 'First Past The Post (FPTP)',
            'assembly_type': 'PTHT',
            'assembly_name_mm': 'ပြည်သူ့လွှတ်တော်',
            'assembly_name_en': 'Pyithu Hluttaw'
        }
        all_constituencies.append(constituency)
    logger.info(f"✅ Processed {len(df)} Pyithu constituencies")
    
    # 2. Amyotha Hluttaw FPTP
    logger.info("📊 Processing Amyotha Hluttaw FPTP...")
    df = pd.read_excel(xlsx_path, sheet_name='အမျိုးသားလွှတ်တော် (FPTP)')
    for index, row in df.iterrows():
        constituency = {
            'id': safe_int(row, 'Unnamed: 0', index + 1000),  # Offset to avoid ID conflicts
            'constituency_mm': safe_get(row, 'မဲဆန္ဒနယ်'),
            'constituency_en': f"Amyotha Hluttaw FPTP Constituency No.{safe_int(row, 'Unnamed: 0', index + 1)}",
            'areas_included_mm': safe_get(row, 'မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ'),
            'areas_included_en': f"Multiple townships in {safe_get(row, 'တိုင်း/ပြည်နယ်')}",
            'state_region_mm': safe_get(row, 'တိုင်း/ပြည်နယ်'),
            'state_region_en': state_mapping.get(safe_get(row, 'တিုန်း/ပြည်နယ်'), safe_get(row, 'တိုင်း/ပြည်နယ်')),
            'tsp_pcode_list': safe_get(row, 'ပါဝင်သည့်နယ်မြေများ'),
            'representatives': safe_int(row, 'ကိုယ်စားလှယ်'),
            'electoral_system_mm': safe_get(row, 'မဲစနစ်'),
            'electoral_system_en': 'First Past The Post (FPTP)',
            'assembly_type': 'AMTHT',
            'assembly_name_mm': 'အမျိုးသားလွှတ်တော်',
            'assembly_name_en': 'Amyotha Hluttaw'
        }
        all_constituencies.append(constituency)
    logger.info(f"✅ Processed {len(df)} Amyotha FPTP constituencies")
    
    # 3. Amyotha Hluttaw PR
    logger.info("📊 Processing Amyotha Hluttaw PR...")
    df = pd.read_excel(xlsx_path, sheet_name='အမျိုးသားလွှတ်တော်(PR)')
    for index, row in df.iterrows():
        constituency = {
            'id': safe_int(row, 'Unnamed: 0', index + 2000),  # Offset to avoid ID conflicts
            'constituency_code': safe_get(row, 'အတိုမှတ်'),
            'constituency_mm': safe_get(row, 'မဲဆန္ဒနယ်အမှတ်'),
            'constituency_en': f"Amyotha Hluttaw PR {safe_get(row, 'အတိုမှတ်')}",
            'areas_included_mm': safe_get(row, 'မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ'),
            'areas_included_en': f"Multiple townships in {safe_get(row, 'တိုင်း/ပြည်နယ်')}",
            'state_region_mm': safe_get(row, 'တိုင်း/ပြည်နယ်'),
            'state_region_en': state_mapping.get(safe_get(row, 'တိုင်း/ပြည်နယ်'), safe_get(row, 'တိုင်း/ပြည်နယ်')),
            'tsp_pcode_list': safe_get(row, 'ပါဝင်သည့်နယ်မြေများ'),
            'representatives': safe_int(row, 'ကိုယ်စားလှယ်'),
            'electoral_system_mm': safe_get(row, 'မဲစနစ်'),
            'electoral_system_en': 'Proportional Representation (PR)',
            'assembly_type': 'AMPR',
            'assembly_name_mm': 'အမျိုးသားလွှတ်တော်(အချိုးကျ)',
            'assembly_name_en': 'Amyotha Hluttaw (PR)'
        }
        all_constituencies.append(constituency)
    logger.info(f"✅ Processed {len(df)} Amyotha PR constituencies")
    
    # 4. State/Regional FPTP
    logger.info("📊 Processing State/Regional FPTP...")
    df = pd.read_excel(xlsx_path, sheet_name='တိုင်းပြည်နယ်လွှတ်တော်(FPTP)')
    for index, row in df.iterrows():
        constituency = {
            'id': safe_int(row, 'Unnamed: 0', index + 3000),  # Offset to avoid ID conflicts
            'township_name_en': safe_get(row, 'Township_Name_Eng'),
            'constituency_mm': safe_get(row, 'မဲဆန္ဒနယ်'),
            'constituency_en': f"{safe_get(row, 'Township_Name_Eng')} Township",
            'areas_included_mm': safe_get(row, 'မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ'),
            'areas_included_en': f"{safe_get(row, 'Township_Name_Eng')} Township area",
            'township_mm': safe_get(row, 'မြို့နယ်'),
            'state_region_mm': safe_get(row, 'တိုင်း/ပြည်နယ်'),
            'state_region_en': state_mapping.get(safe_get(row, 'တိုင်း/ပြည်နယ်'), safe_get(row, 'တိုင်း/ပြည်နယ်')),
            'tsp_pcode': safe_get(row, 'ပါဝင်သည့်နယ်မြေများ'),
            'representatives': safe_int(row, 'ကိုယ်စားလှယ်'),
            'electoral_system_mm': safe_get(row, 'မဲစနစ်'),
            'electoral_system_en': 'First Past The Post (FPTP)',
            'assembly_type': 'TPHT',
            'assembly_name_mm': 'တိုင်းပြည်နယ်လွှတ်တော်',
            'assembly_name_en': 'State/Regional Hluttaw'
        }
        all_constituencies.append(constituency)
    logger.info(f"✅ Processed {len(df)} State/Regional FPTP constituencies")
    
    # 5. State/Regional PR
    logger.info("📊 Processing State/Regional PR...")
    df = pd.read_excel(xlsx_path, sheet_name='တိုင်းပြည်နယ်လွှတ်တော်(PR)')
    for index, row in df.iterrows():
        constituency = {
            'id': safe_int(row, 'Unnamed: 0', index + 4000),  # Offset to avoid ID conflicts
            'constituency_code': safe_get(row, 'အတိုမှတ်'),
            'constituency_mm': safe_get(row, 'မဲဆန္ဒနယ်.1'),
            'constituency_en': f"State/Regional PR {safe_get(row, 'အတိုမှတ်')}",
            'areas_included_mm': safe_get(row, 'မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ'),
            'areas_included_en': f"Multiple townships in {safe_get(row, 'တိုင်း/ပြည်နယ်')}",
            'state_region_mm': safe_get(row, 'တိုင်း/ပြည်နယ်'),
            'state_region_en': state_mapping.get(safe_get(row, 'တိုင်း/ပြည်နယ်'), safe_get(row, 'တিုန်း/ပြည်နယ်')),
            'tsp_pcode_list': safe_get(row, 'ပါဝင်သည့်နယ်မြေများ'),
            'representatives': safe_int(row, 'ကိုယ်စားလှယ်'),
            'electoral_system_mm': safe_get(row, 'မဲစနစ်'),
            'electoral_system_en': 'Proportional Representation (PR)',
            'assembly_type': 'TPPR',
            'assembly_name_mm': 'တိုင်းပြည်နယ်လွှတ်တော်(အချိုးကျ)',
            'assembly_name_en': 'State/Regional Hluttaw (PR)'
        }
        all_constituencies.append(constituency)
    logger.info(f"✅ Processed {len(df)} State/Regional PR constituencies")
    
    # 6. Ethnic FPTP
    logger.info("📊 Processing Ethnic FPTP...")
    df = pd.read_excel(xlsx_path, sheet_name='တိုင်းရင်းသား(FPTP)')
    for index, row in df.iterrows():
        constituency = {
            'id': safe_int(row, 'Unnamed: 0', index + 5000),  # Offset to avoid ID conflicts
            'constituency_mm': safe_get(row, 'မဲဆန္ဒနယ်'),
            'constituency_en': f"Ethnic Constituency No.{safe_int(row, 'Unnamed: 0', index + 1)}",
            'areas_included_mm': safe_get(row, 'မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ'),
            'areas_included_en': f"Ethnic areas in {safe_get(row, 'တိုင်း/ပြည်နယ်')}",
            'state_region_mm': safe_get(row, 'တိုင်း/ပြည်နယ်'),
            'state_region_en': state_mapping.get(safe_get(row, 'တိုင်း/ပြည်နယ်'), safe_get(row, 'တိုင်း/ပြည်နယ်')),
            'tsp_pcode_list': safe_get(row, 'ပါဝင်သည့်နယ်မြေများ'),
            'representatives': safe_int(row, 'ကိုယ်စားလှယ်'),
            'electoral_system_mm': safe_get(row, 'မဲစနစ်'),
            'electoral_system_en': 'First Past The Post (FPTP)',
            'assembly_type': 'TPTYT',
            'assembly_name_mm': 'တိုင်းရင်းသားကိုယ်စားလှယ်',
            'assembly_name_en': 'Ethnic Representatives'
        }
        all_constituencies.append(constituency)
    logger.info(f"✅ Processed {len(df)} Ethnic constituencies")
    
    return all_constituencies

def main():
    """Main extraction function"""
    xlsx_path = 'data/2025-ELECTION-PLAN-DATA-FINAL.xlsx'
    output_dir = Path('data/processed')
    
    logger.info(f"🚀 Extracting data from {xlsx_path}")
    
    # Process all sheets
    all_constituencies = process_all_sheets(xlsx_path)
    
    # Count by assembly type
    assembly_counts = {}
    for constituency in all_constituencies:
        assembly_type = constituency['assembly_type']
        assembly_counts[assembly_type] = assembly_counts.get(assembly_type, 0) + 1
    
    # Create comprehensive dataset
    complete_dataset = {
        'metadata': {
            'source': '2025-ELECTION-PLAN-DATA-FINAL.xlsx',
            'extraction_date': '2025-08-21',
            'total_constituencies': len(all_constituencies),
            'assembly_breakdown': assembly_counts,
            'description': 'Complete Myanmar 2025 Election constituency data extracted from official planning documents'
        },
        'constituencies': all_constituencies
    }
    
    # Output to JSON
    json_path = output_dir / 'myanmar_election_2025_complete.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(complete_dataset, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 Saved JSON: {json_path}")
    
    # Output to YAML
    yaml_path = output_dir / 'myanmar_election_2025_complete.yaml'
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(complete_dataset, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    logger.info(f"💾 Saved YAML: {yaml_path}")
    
    # Create CSV for compatibility
    df_all = pd.DataFrame(all_constituencies)
    csv_path = output_dir / 'myanmar_election_2025_complete.csv'
    df_all.to_csv(csv_path, index=False, encoding='utf-8')
    logger.info(f"💾 Saved CSV: {csv_path}")
    
    # Summary statistics
    logger.info(f"🎉 Extraction complete!")
    logger.info(f"📊 Total constituencies: {len(all_constituencies)}")
    for assembly_type, count in assembly_counts.items():
        logger.info(f"   {assembly_type}: {count}")

if __name__ == "__main__":
    main()