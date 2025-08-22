#!/usr/bin/env python3
"""
Fix Party Data Duplicates and Merge Information
Addresses the issue where parties appear in multiple categories
"""

import json
from pathlib import Path
from typing import Dict, List, Any

def load_party_data() -> Dict[str, Any]:
    """Load the current party data."""
    data_path = Path('data/processed/myanmar_2025_political_parties.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def merge_party_information(parties_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge duplicate parties and determine their current status.
    Priority: existing > allowed_to_register > canceled
    """
    
    # Create a merged parties dictionary
    merged_parties = {}
    all_parties = {}
    
    # Priority order for status (higher number = higher priority)
    status_priority = {
        'canceled': 1,
        'allowed_to_register': 2, 
        'existing': 3
    }
    
    # Collect all parties and merge duplicates
    for category, parties in parties_data['parties'].items():
        for party in parties:
            name = party['name_mm'].strip()
            
            if name in all_parties:
                # Merge with existing entry, keeping higher priority status
                existing_party = all_parties[name]
                current_priority = status_priority.get(existing_party.get('current_status', 'canceled'), 0)
                new_priority = status_priority.get(category, 0)
                
                if new_priority > current_priority:
                    # Update status to higher priority one
                    existing_party['current_status'] = category
                    existing_party['primary_type'] = category
                
                # Merge additional information
                for key, value in party.items():
                    if key == 'type':
                        continue
                    if key not in existing_party or not existing_party[key]:
                        existing_party[key] = value
                    elif key == 'address' and value and value != existing_party.get(key, ''):
                        # Combine addresses if different
                        if existing_party.get(key) and existing_party[key] != value:
                            existing_party[key] = f"{existing_party[key]} | {value}"
                        else:
                            existing_party[key] = value
                
                # Track all statuses this party has appeared in
                if 'all_statuses' not in existing_party:
                    existing_party['all_statuses'] = [existing_party.get('primary_type', category)]
                if category not in existing_party['all_statuses']:
                    existing_party['all_statuses'].append(category)
                    
            else:
                # First time seeing this party
                party_info = party.copy()
                party_info['current_status'] = category
                party_info['primary_type'] = category
                party_info['all_statuses'] = [category]
                all_parties[name] = party_info
    
    # Organize by current status
    organized_parties = {
        'existing': [],
        'allowed_to_register': [],
        'canceled': []
    }
    
    for party in all_parties.values():
        current_status = party['current_status']
        organized_parties[current_status].append(party)
    
    # Calculate new summary
    new_summary = {
        'total_existing': len(organized_parties['existing']),
        'total_allowed_to_register': len(organized_parties['allowed_to_register']),
        'total_canceled': len(organized_parties['canceled']),
        'total_all_parties': len(all_parties),
        'duplicates_resolved': len(parties_data['parties']['existing']) + len(parties_data['parties']['allowed_to_register']) + len(parties_data['parties']['canceled']) - len(all_parties)
    }
    
    return {
        'metadata': parties_data['metadata'].copy(),
        'parties': organized_parties,
        'summary': new_summary
    }

def main():
    """Main function to fix duplicates and save cleaned data."""
    print("🔧 Loading party data...")
    original_data = load_party_data()
    
    print("📊 Original counts:")
    for category, parties in original_data['parties'].items():
        print(f"  {category}: {len(parties)}")
    
    print("\n🔄 Merging duplicate parties...")
    cleaned_data = merge_party_information(original_data)
    
    print("📊 Cleaned counts:")
    for category, parties in cleaned_data['parties'].items():
        print(f"  {category}: {len(parties)}")
    
    print(f"\n✅ Resolved {cleaned_data['summary']['duplicates_resolved']} duplicates")
    
    # Save cleaned data
    output_path = Path('data/processed/myanmar_2025_political_parties_cleaned.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Saved cleaned data to {output_path}")
    
    # Show some examples of merged parties
    print("\n🔍 Examples of merged parties:")
    for category, parties in cleaned_data['parties'].items():
        for party in parties[:2]:
            if len(party.get('all_statuses', [])) > 1:
                print(f"  📋 {party['name_mm']}")
                print(f"     Current Status: {party['current_status']}")
                print(f"     All Statuses: {', '.join(party['all_statuses'])}")
                break

if __name__ == "__main__":
    main()