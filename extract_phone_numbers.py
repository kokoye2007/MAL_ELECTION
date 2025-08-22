#!/usr/bin/env python3
"""
Extract Phone Numbers from Party Address Data
Split address and phone number into separate columns
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Tuple

def extract_phone_from_address(address: str) -> Tuple[str, str]:
    """
    Extract phone number from address field and return cleaned address and phone.
    
    Args:
        address: Original address string
        
    Returns:
        Tuple of (cleaned_address, phone_number)
    """
    if not address:
        return "", ""
    
    # Split by phone number pattern
    if "ဖုန်းနံပါတ်" in address:
        parts = address.split("ဖုန်းနံပါတ်")
        cleaned_address = parts[0].strip()
        
        # Extract phone number (everything after "ဖုန်းနံပါတ်-")
        phone_part = parts[1] if len(parts) > 1 else ""
        phone_number = phone_part.replace("-", "").strip()
        
        # Remove trailing dots and newlines from address
        cleaned_address = re.sub(r'[.\s\\n]+$', '', cleaned_address)
        
        return cleaned_address, phone_number
    
    return address, ""

def process_party_data(party_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process all party data to extract phone numbers."""
    
    updated_data = party_data.copy()
    phone_extraction_stats = {
        'total_processed': 0,
        'addresses_with_phone_pattern': 0,
        'addresses_with_actual_numbers': 0,
        'addresses_cleaned': 0
    }
    
    for category in ['existing', 'allowed_to_register', 'canceled']:
        if category not in updated_data['parties']:
            continue
            
        for party in updated_data['parties'][category]:
            phone_extraction_stats['total_processed'] += 1
            
            address = party.get('address', '')
            if address:
                cleaned_address, phone_number = extract_phone_from_address(address)
                
                # Update party data
                party['address'] = cleaned_address
                party['phone'] = phone_number
                
                # Track statistics
                if "ဖုန်းနံပါတ်" in address:
                    phone_extraction_stats['addresses_with_phone_pattern'] += 1
                    phone_extraction_stats['addresses_cleaned'] += 1
                    
                    if phone_number:
                        phone_extraction_stats['addresses_with_actual_numbers'] += 1
            else:
                # Add empty phone field for consistency
                party['phone'] = ""
    
    return updated_data, phone_extraction_stats

def main():
    """Main function to process phone number extraction."""
    print("📞 Processing party data to extract phone numbers...")
    
    # Load current party data
    data_path = Path('data/processed/myanmar_2025_political_parties.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        party_data = json.load(f)
    
    print(f"📊 Original data loaded: {party_data['summary']['total_all_parties']} parties")
    
    # Process phone number extraction
    updated_data, stats = process_party_data(party_data)
    
    # Display statistics
    print("\n📊 Phone Number Extraction Statistics:")
    print(f"  Total parties processed: {stats['total_processed']}")
    print(f"  Addresses with phone pattern (ဖုန်းနံပါတ်): {stats['addresses_with_phone_pattern']}")
    print(f"  Addresses with actual phone numbers: {stats['addresses_with_actual_numbers']}")
    print(f"  Addresses cleaned: {stats['addresses_cleaned']}")
    
    # Show examples of cleaned data
    print("\n🔍 Examples of cleaned addresses:")
    for category in ['existing', 'allowed_to_register', 'canceled']:
        parties = updated_data['parties'].get(category, [])
        for party in parties[:3]:
            if party.get('address') and "phone" in party:
                original_has_phone = "ဖုန်းနံပါတ်" in str(party.get('address', ''))
                print(f"  📋 {party['name_mm'][:50]}...")
                print(f"     Address: {party['address'][:80]}...")
                print(f"     Phone: '{party['phone']}'")
                break
    
    # Save updated data
    output_path = Path('data/processed/myanmar_2025_political_parties_with_phone.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(updated_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Saved updated data with phone extraction to {output_path}")
    
    # Check if we should replace the original
    if stats['addresses_with_phone_pattern'] > 0:
        print(f"\n✅ Found {stats['addresses_with_phone_pattern']} addresses with phone patterns")
        print("📞 Phone numbers extracted and addresses cleaned")
        
        # Replace original file
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, indent=2, ensure_ascii=False)
        print(f"🔄 Updated original file: {data_path}")
    else:
        print("\n❌ No phone patterns found to extract")

if __name__ == "__main__":
    main()