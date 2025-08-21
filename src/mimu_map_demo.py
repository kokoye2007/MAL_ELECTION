#!/usr/bin/env python3
"""
MIMU Multi-Layer Map Demo

This script demonstrates the enhanced multi-layer mapping capabilities 
with MIMU township boundaries and constituency pinpoint markers.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent))

from layered_visualizations import MyanmarElectionLayeredVisualizer


def load_comprehensive_data():
    """Load comprehensive constituency data with MIMU coordinates."""
    # Try multiple possible paths
    possible_paths = [
        Path(__file__).parent.parent / 'data' / 'processed' / 'myanmar_election_2025_comprehensive_with_coordinates.csv',
        Path('data/processed/myanmar_election_2025_comprehensive_with_coordinates.csv'),
        Path('../data/processed/myanmar_election_2025_comprehensive_with_coordinates.csv'),
    ]
    
    for csv_path in possible_paths:
        if csv_path.exists():
            st.success(f"✅ Found data at: {csv_path}")
            return pd.read_csv(csv_path)
    
    st.error(f"❌ Comprehensive data not found. Tried paths: {[str(p) for p in possible_paths]}")
    return pd.DataFrame()


def main():
    """Main demo application."""
    st.set_page_config(
        page_title="MIMU Multi-Layer Election Map Demo",
        page_icon="🗺️",
        layout="wide"
    )
    
    st.title("🗺️ MIMU Multi-Layer Election Map Demo")
    st.markdown("""
    This demo showcases the enhanced multi-layer mapping system with:
    - **Pinpoint Markers**: Constituency locations from MIMU coordinate calculations
    - **Township Boundaries**: MIMU administrative boundaries
    - **Interactive Layers**: Toggle-able layer controls
    - **Multi-Assembly Support**: Different assembly types with color coding
    """)
    
    # Load data
    data = load_comprehensive_data()
    
    if data.empty:
        st.warning("⚠️ No data available for visualization")
        return
    
    st.success(f"✅ Loaded {len(data)} constituencies with MIMU coordinate mapping")
    
    # Initialize visualizer
    visualizer = MyanmarElectionLayeredVisualizer()
    
    # Sidebar controls
    st.sidebar.header("🎛️ Map Controls")
    
    # Assembly type filter
    available_assemblies = data['assembly_type'].unique().tolist()
    selected_assemblies = st.sidebar.multiselect(
        "Select Assembly Types",
        options=available_assemblies,
        default=available_assemblies[:3],  # First 3 by default
        help="Choose which assembly types to display"
    )
    
    # Layer controls
    st.sidebar.subheader("Layer Options")
    show_boundaries = st.sidebar.checkbox("Show MIMU Township Boundaries (Colored)", value=True, 
                                          help="Township boundaries colored by constituency assembly type")
    show_pinpoints = st.sidebar.checkbox("Show Constituency Pinpoints", value=True)
    show_selection_boxes = False  # Deprecated - we're coloring boundaries instead
    area_radius = 3  # Not used anymore
    
    # Map settings
    st.sidebar.subheader("Map Settings")
    zoom_level = st.sidebar.slider("Zoom Level", min_value=5, max_value=12, value=7)
    
    # Filter data
    filtered_data = data[data['assembly_type'].isin(selected_assemblies)] if selected_assemblies else pd.DataFrame()
    
    if not filtered_data.empty:
        st.markdown(f"### 🎯 Displaying {len(filtered_data)} constituencies from {len(selected_assemblies)} assembly types")
        
        # Create multi-layer map
        try:
            multi_layer_map = visualizer.create_multi_layer_map(
                constituencies_data=filtered_data,
                zoom_level=zoom_level,
                show_boundaries=show_boundaries,
                show_pinpoints=show_pinpoints,
                show_selection_boxes=show_selection_boxes,
                area_radius_km=area_radius,
                assembly_filter=selected_assemblies
            )
            
            # Display the map
            st.components.v1.html(
                multi_layer_map._repr_html_(),
                height=600,
                scrolling=True
            )
            
        except Exception as e:
            st.error(f"❌ Error creating map: {e}")
            st.info("📝 This may be due to missing MIMU boundary data. Please check that myanmar_townships_mimu.geojson is available.")
    
    else:
        st.warning("⚠️ No data to display with current filters")
    
    # Data summary
    if not data.empty:
        st.markdown("### 📊 Data Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Constituencies", len(data))
        
        with col2:
            mapped_count = data['lat'].notna().sum()
            st.metric("MIMU Mapped", mapped_count)
        
        with col3:
            multi_township_count = (data['coordinate_source'] == 'mimu_multi_township_centroid').sum()
            st.metric("Multi-Township", multi_township_count)
        
        # Assembly breakdown
        st.markdown("#### Assembly Type Breakdown")
        assembly_summary = data.groupby('assembly_type').agg({
            'id': 'count',
            'representatives': 'sum',
            'lat': lambda x: x.notna().sum()
        }).rename(columns={'id': 'constituencies', 'lat': 'mapped'})
        
        st.dataframe(assembly_summary, use_container_width=True)
        
        # Coordinate source breakdown
        st.markdown("#### Coordinate Source Analysis")
        coord_summary = data['coordinate_source'].value_counts()
        st.dataframe(coord_summary, use_container_width=True)
    
    # Technical notes
    with st.expander("🔍 Technical Implementation Details"):
        st.markdown("""
        **Multi-Layer Architecture:**
        - **Layer 1**: MIMU Township Boundaries (GeoJSON polygons) - Colored by assembly type
        - **Layer 2**: Constituency Pinpoints (CircleMarkers)
        - **Layer Control**: Interactive toggling of layers
        
        **Boundary Coloring:**
        - Township boundaries are automatically colored based on their constituency's assembly type
        - Red boundaries: PTHT constituencies
        - Blue boundaries: AMTHT constituencies
        - Green boundaries: TPHT constituencies
        - Gray boundaries: Townships without constituencies
        
        **Coordinate Mapping:**
        - `mimu_boundary_centroid`: Single township constituencies
        - `mimu_multi_township_centroid`: Average of multiple township centroids
        - `mimu_partial_NofM`: Partial township matches with averaging
        
        **Assembly Types:**
        - **PTHT**: Pyithu Hluttaw (House of Representatives) - Red markers
        - **AMTHT**: Amyotha Hluttaw (House of Nationalities) - Blue markers
        - **AMTHT_PR**: Amyotha Hluttaw Proportional Representation - Dark Blue
        - **TPHT**: State/Regional Hluttaw - Green markers
        - **TPHT_PR**: State/Regional Proportional Representation - Dark Green
        - **TPTYT**: Ethnic constituencies - Brown markers
        
        **Data Integration:**
        - MIMU (Myanmar Information Management Unit) administrative boundaries
        - Multi-township constituency coordinate averaging
        - Real-time layer switching and filtering
        """)


if __name__ == "__main__":
    main()