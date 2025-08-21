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

def extract_pyithu_hluttaw(xlsx_path):
    """Extract Pyithu Hluttaw (House of Representatives) data"""
    df = pd.read_excel(xlsx_path, sheet_name='ပြည်သူ့လွှတ်တော် (FPTP)')
    
    constituencies = []
    for _, row in df.iterrows():
        constituency = {
            'id': int(row['Unnamed: 0']),
            'township_name_en': str(row['Township_Name_Eng']),
            'constituency_mm': str(row['မြို့နယ်.1']),
            'constituency_en': f"{row['Township_Name_Eng']} Township",
            'areas_included_mm': str(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']),
            'areas_included_en': f"{row['Township_Name_Eng']} Township (entire)",
            'township_mm': str(row['မြို့နယ်']),
            'state_region_mm': str(row['တိုင်း/ပြည်နယ်']),
            'tsp_pcode': str(row['Tsp_Pcode']),
            'representatives': int(row['ကိုယ်စားလှယ်']),
            'electoral_system_mm': str(row['မဲစနစ်']),
            'electoral_system_en': 'First Past The Post (FPTP)',
            'assembly_type': 'PTHT',
            'assembly_name_mm': 'ပြည်သူ့လွှတ်တော်',
            'assembly_name_en': 'Pyithu Hluttaw'
        }
        constituencies.append(constituency)
    
    return constituencies

def extract_amyotha_hluttaw_fptp(xlsx_path):
    """Extract Amyotha Hluttaw FPTP data"""
    df = pd.read_excel(xlsx_path, sheet_name='အမျိုးသားလွှတ်တော် (FPTP)')
    
    constituencies = []
    for index, row in df.iterrows():
        constituency = {
            'id': int(row['Unnamed: 0']) if pd.notna(row['Unnamed: 0']) else index + 1,
            'constituency_mm': str(row['မဲဆန္ဒနယ်']),
            'constituency_en': f"Amyotha Hluttaw Constituency No.{int(row['Unnamed: 0']) if pd.notna(row['Unnamed: 0']) else index + 1}",
            'areas_included_mm': str(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']),
            'areas_included_en': f"Multiple townships in {row['တိုင်း/ပြည်နယ်']}",
            'state_region_mm': str(row['တိုင်း/ပြည်နယ်']),
            'tsp_pcode_list': str(row['ပါဝင်သည့်နယ်မြေများ']),
            'representatives': int(row['ကိုယ်စားလှယ်']) if pd.notna(row['ကိုယ်စားလှယ်']) else 1,
            'electoral_system_mm': str(row['မဲစနစ်']),
            'electoral_system_en': 'First Past The Post (FPTP)',
            'assembly_type': 'AMTHT',
            'assembly_name_mm': 'အမျိုးသားလွှတ်တော်',
            'assembly_name_en': 'Amyotha Hluttaw'
        }
        constituencies.append(constituency)
    
    return constituencies

def extract_amyotha_hluttaw_pr(xlsx_path):
    """Extract Amyotha Hluttaw PR data"""
    df = pd.read_excel(xlsx_path, sheet_name='အမျိုးသားလွှတ်တော်(PR)')
    
    constituencies = []
    for index, row in df.iterrows():
        constituency = {
            'id': int(row['Unnamed: 0']) if pd.notna(row['Unnamed: 0']) else index + 1,
            'constituency_code': str(row['အတိုမှတ်']) if pd.notna(row['အတိုမှတ်']) else f"AMPR-{index+1:02d}",
            'constituency_mm': str(row['မဲဆန္ဒနယ်.1']) if 'မဲဆန္ဒနယ်.1' in row else str(row['မဲဆန္ဒနယ်']),
            'constituency_en': f"Amyotha Hluttaw PR Constituency {row['အတိုမှတ်'] if pd.notna(row['အတိုမှတ်']) else index + 1}",
            'areas_included_mm': str(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']),
            'areas_included_en': f"Multiple townships in {row['တိုင်း/ပြည်နယ်']}",
            'state_region_mm': str(row['တိုင်း/ပြည်နယ်']),
            'tsp_pcode_list': str(row['ပါဝင်သည့်နယ်မြေများ']),
            'representatives': int(row['ကိုယ်စားလှယ်']) if pd.notna(row['ကိုယ်စားလှယ်']) else 1,
            'electoral_system_mm': str(row['မဲစနစ်']),
            'electoral_system_en': 'Proportional Representation (PR)',
            'assembly_type': 'AMPR',
            'assembly_name_mm': 'အမျိုးသားလွှတ်တော်(အချိုးကျ)',
            'assembly_name_en': 'Amyotha Hluttaw (PR)'
        }
        constituencies.append(constituency)
    
    return constituencies

def extract_state_regional_fptp(xlsx_path):
    """Extract State/Regional Hluttaw FPTP data"""
    df = pd.read_excel(xlsx_path, sheet_name='တိုင်းပြည်နယ်လွှတ်တော်(FPTP)')
    
    constituencies = []
    for index, row in df.iterrows():
        constituency = {
            'id': int(row['Unnamed: 0']) if pd.notna(row['Unnamed: 0']) else index + 1,
            'township_name_en': str(row['Township_Name_Eng']) if pd.notna(row['Township_Name_Eng']) else '',
            'constituency_mm': str(row['မဲဆန္ဒနယ်']),
            'constituency_en': f"{row['Township_Name_Eng']} Township" if pd.notna(row['Township_Name_Eng']) else f"Constituency {index + 1}",
            'areas_included_mm': str(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']),
            'areas_included_en': f"{row['Township_Name_Eng']} Township area",
            'township_mm': str(row['မြို့နယ်']),
            'state_region_mm': str(row['တိုင်း/ပြည်နယ်']),
            'tsp_pcode': str(row['ပါဝင်သည့်နယ်မြေများ']),
            'representatives': int(row['ကိုယ်စားလှယ်']) if pd.notna(row['ကိုယ်စားလှယ်']) else 1,
            'electoral_system_mm': str(row['မဲစနစ်']),
            'electoral_system_en': 'First Past The Post (FPTP)',
            'assembly_type': 'TPHT',
            'assembly_name_mm': 'တိုင်းပြည်နယ်လွှတ်တော်',
            'assembly_name_en': 'State/Regional Hluttaw'
        }
        constituencies.append(constituency)
    
    return constituencies

def extract_state_regional_pr(xlsx_path):
    """Extract State/Regional Hluttaw PR data"""
    df = pd.read_excel(xlsx_path, sheet_name='တိုင်းပြည်နယ်လွှတ်တော်(PR)')
    
    constituencies = []
    for index, row in df.iterrows():
        constituency = {
            'id': int(row['Unnamed: 0']) if pd.notna(row['Unnamed: 0']) else index + 1,
            'constituency_code': str(row['အတိုမှတ်']) if pd.notna(row['အတိုမှတ်']) else f"SRPR-{index+1:02d}",
            'constituency_mm': str(row['မဲဆန္ဒနယ်.1']) if 'မဲဆန္ဒနယ်.1' in row else str(row['မဲဆန္ဒနယ်']),
            'constituency_en': f"State/Regional PR Constituency {row['အတိုမှတ်'] if pd.notna(row['အတိုမှတ်']) else index + 1}",
            'areas_included_mm': str(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']),
            'areas_included_en': f"Multiple townships in {row['တိုင်း/ပြည်နယ်']}",
            'state_region_mm': str(row['တিোន်း/ပြည်နယ်']),
            'tsp_pcode_list': str(row['ပါဝင်သည့်နယ်မြေများ']),
            'representatives': int(row['ကိုယ်စားလှယ်']) if pd.notna(row['ကိုယ်စားလှယ်']) else 1,
            'electoral_system_mm': str(row['မဲစနစ်']),
            'electoral_system_en': 'Proportional Representation (PR)',
            'assembly_type': 'TPPR',
            'assembly_name_mm': 'တိုင်းပြည်နယ်လွှတ်တော်(အချိုးကျ)',
            'assembly_name_en': 'State/Regional Hluttaw (PR)'
        }
        constituencies.append(constituency)
    
    return constituencies

def extract_ethnic_fptp(xlsx_path):
    """Extract Ethnic FPTP data"""
    df = pd.read_excel(xlsx_path, sheet_name='တိုင်းရင်းသား(FPTP)')
    
    constituencies = []
    for index, row in df.iterrows():
        constituency = {
            'id': int(row['Unnamed: 0']) if pd.notna(row['Unnamed: 0']) else index + 1,
            'constituency_mm': str(row['မဲဆန္ဒနယ်']),
            'constituency_en': f"Ethnic Constituency No.{index + 1}",
            'areas_included_mm': str(row['မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ']),
            'areas_included_en': f"Ethnic areas in {row['တိုင်း/ပြည်နယ်']}",
            'state_region_mm': str(row['တိုင်း/ပြည်နယ်']),
            'tsp_pcode_list': str(row['ပါဝင်သည့်နယ်မြေများ']),
            'representatives': int(row['ကိုယ်စားလှယ်']) if pd.notna(row['ကိုယ်စားလှယ်']) else 1,
            'electoral_system_mm': str(row['မဲစနစ်']),
            'electoral_system_en': 'First Past The Post (FPTP)',
            'assembly_type': 'TPTYT',
            'assembly_name_mm': 'တိုင်းရင်းသားကိုယ်စားလှယ်',
            'assembly_name_en': 'Ethnic Representatives'
        }
        constituencies.append(constituency)
    
    return constituencies

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

def main():
    """Main extraction function"""
    xlsx_path = 'data/2025-ELECTION-PLAN-DATA-FINAL.xlsx'
    output_dir = Path('data/processed')
    
    logger.info(f"🚀 Extracting data from {xlsx_path}")
    
    # Create state mapping
    state_mapping = create_state_region_mapping()
    
    # Extract all assembly data
    all_constituencies = []
    
    # 1. Pyithu Hluttaw (330 constituencies)
    logger.info("📊 Extracting Pyithu Hluttaw data...")
    pyithu_data = extract_pyithu_hluttaw(xlsx_path)
    all_constituencies.extend(pyithu_data)
    logger.info(f"✅ Extracted {len(pyithu_data)} Pyithu constituencies")
    
    # 2. Amyotha Hluttaw FPTP (86 constituencies)
    logger.info("📊 Extracting Amyotha Hluttaw FPTP data...")
    amyotha_fptp_data = extract_amyotha_hluttaw_fptp(xlsx_path)
    all_constituencies.extend(amyotha_fptp_data)
    logger.info(f"✅ Extracted {len(amyotha_fptp_data)} Amyotha FPTP constituencies")
    
    # 3. Amyotha Hluttaw PR (28 constituencies)
    logger.info("📊 Extracting Amyotha Hluttaw PR data...")
    amyotha_pr_data = extract_amyotha_hluttaw_pr(xlsx_path)
    all_constituencies.extend(amyotha_pr_data)
    logger.info(f"✅ Extracted {len(amyotha_pr_data)} Amyotha PR constituencies")
    
    # 4. State/Regional FPTP (324 constituencies)
    logger.info("📊 Extracting State/Regional FPTP data...")
    state_fptp_data = extract_state_regional_fptp(xlsx_path)
    all_constituencies.extend(state_fptp_data)
    logger.info(f"✅ Extracted {len(state_fptp_data)} State/Regional FPTP constituencies")
    
    # 5. State/Regional PR (44 constituencies)
    logger.info("📊 Extracting State/Regional PR data...")
    state_pr_data = extract_state_regional_pr(xlsx_path)
    all_constituencies.extend(state_pr_data)
    logger.info(f"✅ Extracted {len(state_pr_data)} State/Regional PR constituencies")
    
    # 6. Ethnic FPTP (31 constituencies)
    logger.info("📊 Extracting Ethnic FPTP data...")
    ethnic_data = extract_ethnic_fptp(xlsx_path)
    all_constituencies.extend(ethnic_data)
    logger.info(f"✅ Extracted {len(ethnic_data)} Ethnic constituencies")
    
    # Add English state names
    for constituency in all_constituencies:
        mm_state = constituency.get('state_region_mm', '')
        constituency['state_region_en'] = state_mapping.get(mm_state, mm_state)
    
    # Create comprehensive dataset
    complete_dataset = {
        'metadata': {
            'source': '2025-ELECTION-PLAN-DATA-FINAL.xlsx',
            'extraction_date': '2025-08-21',
            'total_constituencies': len(all_constituencies),
            'assembly_breakdown': {
                'PTHT': len(pyithu_data),
                'AMTHT': len(amyotha_fptp_data),
                'AMPR': len(amyotha_pr_data),
                'TPHT': len(state_fptp_data),
                'TPPR': len(state_pr_data),
                'TPTYT': len(ethnic_data)
            }
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
    for assembly_type, count in complete_dataset['metadata']['assembly_breakdown'].items():
        logger.info(f"   {assembly_type}: {count}")

if __name__ == "__main__":
    main()