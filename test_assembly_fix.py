#!/usr/bin/env python3
"""
Test Assembly Selection Fix
Verify that assembly filtering works correctly for Overview page.
"""

import os
import sys

# Add src to path
sys.path.append('src')

def test_assembly_filtering():
    """Test assembly selection filtering."""
    
    # Set database URL for local Docker
    os.environ['DATABASE_URL'] = 'postgresql://election_user:dev_password_2025@localhost:5432/myanmar_election'
    
    from database import get_database
    
    print("🧪 Testing Assembly Selection Filtering...")
    
    db = get_database()
    
    # Test individual assemblies
    assemblies = ['PTHT', 'AMTHT', 'TPHT', 'TPTYT']
    expected_counts = {'PTHT': 330, 'AMTHT': 116, 'TPHT': 360, 'TPTYT': 29}
    
    for assembly in assemblies:
        df = db.get_constituencies([assembly])
        expected = expected_counts[assembly]
        actual = len(df)
        status = "✅" if actual == expected else "❌"
        print(f"  {status} {assembly}: Expected {expected}, Got {actual}")
    
    # Test all assemblies combined
    df_all = db.get_constituencies(assemblies)
    total_expected = sum(expected_counts.values())  # 835
    total_actual = len(df_all)
    status = "✅" if total_actual == total_expected else "❌"
    print(f"  {status} ALL: Expected {total_expected}, Got {total_actual}")
    
    # Test empty selection
    df_empty = db.get_constituencies([])
    empty_actual = len(df_empty)
    status = "✅" if empty_actual == total_expected else "❌"  # Should return all when empty
    print(f"  {status} EMPTY: Expected {total_expected}, Got {empty_actual}")
    
    # Test the new Overview page logic (simulate)
    print("\n📊 Testing Overview Page Statistics Logic...")
    
    # Simulate what the Overview page does now
    for assembly_list in [['PTHT'], ['PTHT', 'AMTHT'], assemblies]:
        df = db.get_constituencies(assembly_list)
        stats = {
            'total_constituencies': len(df),
            'total_representatives': df['representatives'].sum() if not df.empty else 0,
            'mapped_constituencies': df['lat'].notna().sum() if not df.empty else 0,
        }
        
        print(f"  Assemblies {assembly_list}:")
        print(f"    Constituencies: {stats['total_constituencies']}")
        print(f"    Representatives: {stats['total_representatives']}")
        print(f"    Mapped: {stats['mapped_constituencies']}")
        print()

if __name__ == "__main__":
    try:
        test_assembly_filtering()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    
    print("🎉 Assembly filtering test completed!")