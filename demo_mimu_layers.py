#!/usr/bin/env python3
"""
Quick MIMU Multi-Layer Demo

This script creates a simple example of the multi-layer map with 
pinpoint markers and MIMU township boundaries.
"""

import pandas as pd
from pathlib import Path
import sys

# Add src to path
sys.path.append('src')

from layered_visualizations import MyanmarElectionLayeredVisualizer

def main():
    """Create and save a sample multi-layer map."""
    print("🗺️ MIMU Multi-Layer Map Demo")
    print("=" * 50)
    
    # Load comprehensive data
    csv_path = Path('data/processed/myanmar_election_2025_comprehensive_with_coordinates.csv')
    if not csv_path.exists():
        print("❌ Data not found")
        return
    
    df = pd.read_csv(csv_path)
    print(f"📊 Loaded {len(df)} constituencies")
    
    # Filter to a manageable subset for demo
    # Take first 100 constituencies from different assembly types
    demo_data = df.head(100)
    
    print(f"🎯 Demo with {len(demo_data)} constituencies")
    print(f"🏛️ Assembly types: {list(demo_data['assembly_type'].unique())}")
    
    # Initialize visualizer
    visualizer = MyanmarElectionLayeredVisualizer()
    
    # Create multi-layer map
    print("\n🗺️ Creating multi-layer map...")
    
    multi_layer_map = visualizer.create_multi_layer_map(
        constituencies_data=demo_data,
        center_coords=(21.9162, 95.9560),  # Myanmar center
        zoom_level=7,
        show_boundaries=True,  # Township boundaries colored by assembly type
        show_pinpoints=True,
        show_selection_boxes=False,  # Not needed - boundaries are colored instead
        assembly_filter=['PTHT', 'AMTHT', 'TPHT']  # Show main assemblies
    )
    
    # Save the map
    output_path = Path('demo_output/mimu_multi_layer_map.html')
    output_path.parent.mkdir(exist_ok=True)
    
    multi_layer_map.save(str(output_path))
    print(f"✅ Multi-layer map saved to: {output_path}")
    
    # Create assembly comparison map
    print("\n🎨 Creating assembly comparison map...")
    
    comparison_map = visualizer.create_assembly_comparison_map(
        constituencies_data=demo_data,
        assembly_types=['PTHT', 'AMTHT'],
        zoom_level=7
    )
    
    comparison_output = Path('demo_output/assembly_comparison_map.html')
    comparison_map.save(str(comparison_output))
    print(f"✅ Assembly comparison map saved to: {comparison_output}")
    
    # Print summary
    print("\n📋 Demo Summary:")
    print("=" * 50)
    print("✅ Multi-layer map with pinpoint markers and colored MIMU boundaries")
    print("✅ Township boundaries colored by constituency assembly type")
    print("✅ Interactive layer controls for toggling boundaries/pinpoints")
    print("✅ Assembly-specific color coding (Red=PTHT, Blue=AMTHT, Green=TPHT)")
    print("✅ MIMU township boundary integration with transparent fills")
    print("✅ Multi-township coordinate averaging")
    
    mapped_count = demo_data['lat'].notna().sum()
    multi_township_count = (demo_data['coordinate_source'] == 'mimu_multi_township_centroid').sum()
    print(f"\n📍 Coordinates: {mapped_count}/{len(demo_data)} mapped ({multi_township_count} multi-township)")
    
    if visualizer.mimu_boundaries:
        boundary_count = len(visualizer.mimu_boundaries.get('features', []))
        print(f"🗺️ MIMU Boundaries: {boundary_count} township boundaries loaded")
    
    print(f"\n🌐 Open maps in browser:")
    print(f"   - Multi-layer: file://{output_path.absolute()}")
    print(f"   - Comparison: file://{comparison_output.absolute()}")

if __name__ == "__main__":
    main()