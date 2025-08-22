#!/usr/bin/env python3
"""
Convert UEC Party Data from Markdown to JSON
Processes the 3 party categories: existing, allowed to register, and canceled
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any

def parse_party_table(content: str, party_type: str) -> List[Dict[str, Any]]:
    """Parse markdown table and extract party data."""
    parties = []
    lines = content.split('\n')
    
    # Find table data rows (skip header and separator)
    table_started = False
    for line in lines:
        line = line.strip()
        if not line or not line.startswith('|'):
            continue
            
        # Skip header and separator lines
        if '---' in line or ('စဉ်' in line and 'နိုင်ငံရေးပါတီအမည်' in line):
            table_started = True
            continue
            
        if not table_started:
            continue
            
        # Parse table row
        cols = [col.strip() for col in line.split('|')[1:-1]]  # Remove empty first/last
        if len(cols) < 3:
            continue
            
        try:
            party_data = {
                'id': int(cols[0]) if cols[0].isdigit() else cols[0],
                'name_mm': cols[1] if len(cols) > 1 else '',
                'type': party_type
            }
            
            # Extract additional fields based on party type
            if party_type == 'existing':
                party_data.update({
                    'chairman': cols[2] if len(cols) > 2 else '',
                    'secretary_general': cols[3] if len(cols) > 3 else '',
                    'address': cols[4] if len(cols) > 4 else ''
                })
            elif party_type == 'allowed_to_register':
                party_data.update({
                    'registration_date': cols[2] if len(cols) > 2 else '',
                    'announcement_number': cols[3] if len(cols) > 3 else '',
                    'notes': cols[4] if len(cols) > 4 else ''
                })
            elif party_type == 'canceled':
                party_data.update({
                    'registration_date': cols[2] if len(cols) > 2 else '',
                    'announcement_number': cols[3] if len(cols) > 3 else '',
                    'cancellation_date': cols[4] if len(cols) > 4 else '',
                    'cancellation_announcement': cols[5] if len(cols) > 5 else '',
                    'notes': cols[6] if len(cols) > 6 else ''
                })
            
            # Extract English name if available
            english_match = re.search(r'\[(.*?)\]', party_data['name_mm'])
            if english_match:
                party_data['name_en'] = english_match.group(1)
                party_data['name_mm'] = re.sub(r'\s*\[.*?\]', '', party_data['name_mm']).strip()
            else:
                party_data['name_en'] = ''
                
            parties.append(party_data)
            
        except (ValueError, IndexError) as e:
            print(f"Error parsing row: {line[:50]}... Error: {e}")
            continue
    
    return parties

def convert_uec_data():
    """Convert all UEC party data to JSON format."""
    base_path = Path('UEC')
    
    # File mappings
    files = {
        'existing': base_path / 'existing_parties.md',
        'allowed_to_register': base_path / 'allowed_to_register_parties.md', 
        'canceled': base_path / 'canceled_parties.md'
    }
    
    all_parties = {
        'metadata': {
            'source': 'Union Election Commission (UEC) Myanmar',
            'extraction_date': '2025-01-22',
            'description': 'Political parties data for Myanmar 2025 Election',
            'categories': {
                'existing': 'Currently existing political parties',
                'allowed_to_register': 'Parties allowed to register for 2025 election',
                'canceled': 'Previously registered but canceled parties'
            }
        },
        'parties': {
            'existing': [],
            'allowed_to_register': [],
            'canceled': []
        },
        'summary': {}
    }
    
    # Process each file
    for party_type, file_path in files.items():
        if not file_path.exists():
            print(f"Warning: {file_path} not found")
            continue
            
        print(f"Processing {party_type} parties from {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        parties = parse_party_table(content, party_type)
        all_parties['parties'][party_type] = parties
        
        print(f"  Found {len(parties)} {party_type} parties")
    
    # Generate summary statistics
    all_parties['summary'] = {
        'total_existing': len(all_parties['parties']['existing']),
        'total_allowed_to_register': len(all_parties['parties']['allowed_to_register']),
        'total_canceled': len(all_parties['parties']['canceled']),
        'total_all_parties': sum([
            len(all_parties['parties']['existing']),
            len(all_parties['parties']['allowed_to_register']),
            len(all_parties['parties']['canceled'])
        ])
    }
    
    # Save to JSON
    output_path = Path('data/processed/myanmar_2025_political_parties.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_parties, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Successfully converted UEC party data to {output_path}")
    print(f"📊 Summary:")
    print(f"  • Existing parties: {all_parties['summary']['total_existing']}")
    print(f"  • Allowed to register: {all_parties['summary']['total_allowed_to_register']}")
    print(f"  • Canceled parties: {all_parties['summary']['total_canceled']}")
    print(f"  • Total parties: {all_parties['summary']['total_all_parties']}")
    
    return output_path

if __name__ == "__main__":
    convert_uec_data()