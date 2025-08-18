#!/usr/bin/env python3
"""
Myanmar Election Data Visualization - Historical Comparison App

A comprehensive web application for comparing Myanmar's 2020 and 2025 electoral constituencies
with historical analysis, trend visualization, and bilingual support.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import sys

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent))

from database import get_database
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster
import numpy as np

def configure_page():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="Myanmar Election Historical Analysis",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'About': '''
            # Myanmar Election Historical Analysis
            
            This application provides comprehensive historical comparison between
            Myanmar's 2020 and 2025 electoral constituencies.
            
            **Features:**
            - Historical vs Current constituency comparison
            - Trend analysis and change detection
            - Regional redistribution analysis
            - Assembly expansion tracking
            - Bilingual support (Myanmar/English)
            
            **Elections Covered:**
            - 2020: 330 Pyithu Hluttaw constituencies
            - 2025: 835+ constituencies across 4 assemblies
            
            **Data Source:** Myanmar Election Commission + Historical Records
            '''
        }
    )

def add_custom_css():
    """Add custom CSS styling."""
    st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .historical-card { border-left-color: #2E86AB; }
    .current-card { border-left-color: #F18F01; }
    .change-positive { color: #28a745; font-weight: bold; }
    .change-negative { color: #dc3545; font-weight: bold; }
    .change-neutral { color: #6c757d; }
    
    .stSelectbox > div > div > select {
        background-color: white;
    }
    </style>
    """, unsafe_allow_html=True)

def create_sidebar(db):
    """Create enhanced sidebar with historical controls."""
    
    st.sidebar.title("📊 Historical Analysis")
    
    # Page navigation
    page = st.sidebar.selectbox(
        "Select Analysis",
        [
            "📈 Historical Overview", 
            "🔄 Election Comparison", 
            "🗺️ Historical Maps", 
            "📋 Change Analysis",
            "📊 Trend Visualization"
        ],
        index=0
    )
    
    st.sidebar.markdown("---")
    
    # Election year comparison controls
    st.sidebar.subheader("🗳️ Election Years")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        base_year = st.selectbox("Base Year", [2020], index=0)
    with col2:
        compare_year = st.selectbox("Compare Year", [2025], index=0)
    
    # Historical filters
    st.sidebar.subheader("🔍 Historical Filters")
    
    show_changes_only = st.sidebar.checkbox(
        "Show Only Changed Regions",
        value=False,
        help="Filter to show only regions with constituency changes"
    )
    
    change_threshold = st.sidebar.slider(
        "Change Threshold",
        min_value=0,
        max_value=50,
        value=5,
        help="Minimum change in constituencies to highlight"
    )
    
    # Assembly type filter for 2025
    if compare_year == 2025:
        assembly_filter = st.sidebar.multiselect(
            "2025 Assembly Types",
            ["PTHT", "AMTHT", "TPHT", "TPTYT"],
            default=["PTHT"],
            help="Filter 2025 data by assembly type"
        )
    else:
        assembly_filter = ["PTHT"]  # 2020 only had PTHT
    
    st.sidebar.markdown("---")
    
    # Database status
    with st.sidebar.expander("🔌 Database Status"):
        if st.button("Test Historical Data"):
            test_historical_connection(db)
    
    # Information panel
    with st.sidebar.expander("ℹ️ Historical Data Coverage"):
        st.markdown("""
        **2020 Election:**
        - 330 Pyithu Hluttaw constituencies
        - Single assembly election
        - FPTP electoral system
        
        **2025 Election:**
        - 835+ total constituencies
        - 4 assembly types (PTHT, AMTHT, TPHT, TPTYT)
        - Mixed electoral systems
        """)
        
        st.markdown("**Last Updated:** Real-time PostgreSQL")
        st.markdown("**Source:** Myanmar Election Commission + Historical Records")
    
    return page, base_year, compare_year, show_changes_only, change_threshold, assembly_filter

def test_historical_connection(db):
    """Test historical database connection."""
    try:
        historical_stats = db.get_historical_statistics(2020)
        if historical_stats:
            st.success(f"✅ Historical data connected! Found {historical_stats.get('total_constituencies', 0)} constituencies for 2020")
        else:
            st.warning("⚠️ No historical data found for 2020")
    except Exception as e:
        st.error(f"❌ Historical connection failed: {e}")

def display_historical_overview(db):
    """Display historical overview page."""
    st.title("📈 Myanmar Election Historical Overview")
    st.markdown("*Comprehensive comparison between 2020 and 2025 electoral structures*")
    
    # Get statistics for both years
    stats_2020 = db.get_historical_statistics(2020)
    stats_2025 = db.get_assembly_statistics()
    
    if not stats_2020 or not stats_2025:
        st.warning("Historical data not available. Please run the historical migration first.")
        return
    
    # Main metrics comparison
    st.subheader("📊 Election Comparison Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        constituencies_2020 = stats_2020.get('total_constituencies', 0)
        constituencies_2025 = stats_2025.get('total_constituencies', 0)
        change = constituencies_2025 - constituencies_2020
        
        st.metric(
            "Total Constituencies",
            f"{constituencies_2025:,}",
            delta=f"+{change:,}" if change > 0 else f"{change:,}",
            help="Total number of electoral constituencies"
        )
    
    with col2:
        reps_2020 = stats_2020.get('total_representatives', 0)
        reps_2025 = stats_2025.get('total_representatives', 0)
        rep_change = reps_2025 - reps_2020
        
        st.metric(
            "Total Representatives",
            f"{reps_2025:,}",
            delta=f"+{rep_change:,}" if rep_change > 0 else f"{rep_change:,}",
            help="Total number of elected representatives"
        )
    
    with col3:
        assemblies_2020 = len(stats_2020.get('assembly_breakdown', []))
        assemblies_2025 = len(stats_2025.get('assembly_breakdown', []))
        assembly_change = assemblies_2025 - assemblies_2020
        
        st.metric(
            "Assembly Types",
            assemblies_2025,
            delta=f"+{assembly_change}" if assembly_change > 0 else f"{assembly_change}",
            help="Number of different assembly types"
        )
    
    with col4:
        mapped_2020 = stats_2020.get('mapped_constituencies', 0)
        mapped_2025 = stats_2025.get('mapped_constituencies', 0)
        
        coverage_2020 = (mapped_2020 / constituencies_2020 * 100) if constituencies_2020 > 0 else 0
        coverage_2025 = (mapped_2025 / constituencies_2025 * 100) if constituencies_2025 > 0 else 0
        
        st.metric(
            "Mapping Coverage",
            f"{coverage_2025:.1f}%",
            delta=f"{coverage_2025 - coverage_2020:+.1f}%",
            help="Percentage of constituencies with geographic coordinates"
        )
    
    # Historical timeline chart
    st.subheader("🗳️ Electoral System Evolution")
    
    timeline_data = pd.DataFrame([
        {
            'Year': 2020,
            'Constituencies': constituencies_2020,
            'Representatives': reps_2020,
            'Assemblies': assemblies_2020,
            'Electoral_System': 'Single Assembly (PTHT only)'
        },
        {
            'Year': 2025,
            'Constituencies': constituencies_2025,
            'Representatives': reps_2025,
            'Assemblies': assemblies_2025,
            'Electoral_System': 'Multi-Assembly System'
        }
    ])
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Constituencies Over Time', 'Representatives Over Time'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Constituencies chart
    fig.add_trace(
        go.Scatter(
            x=timeline_data['Year'],
            y=timeline_data['Constituencies'],
            mode='lines+markers',
            name='Constituencies',
            line=dict(color='#2E86AB', width=4),
            marker=dict(size=12)
        ),
        row=1, col=1
    )
    
    # Representatives chart
    fig.add_trace(
        go.Scatter(
            x=timeline_data['Year'],
            y=timeline_data['Representatives'],
            mode='lines+markers',
            name='Representatives',
            line=dict(color='#F18F01', width=4),
            marker=dict(size=12)
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        title="Myanmar Electoral System Evolution (2020-2025)",
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Assembly breakdown comparison
    st.subheader("🏛️ Assembly Structure Comparison")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 2020 Election Structure")
        assembly_2020 = pd.DataFrame(stats_2020.get('assembly_breakdown', []))
        if not assembly_2020.empty:
            fig_2020 = px.pie(
                assembly_2020,
                values='constituencies',
                names='assembly_type',
                title="2020: Single Assembly Election",
                color_discrete_map={'PTHT': '#2E86AB'}
            )
            st.plotly_chart(fig_2020, use_container_width=True)
        else:
            st.info("No 2020 assembly data available")
    
    with col2:
        st.markdown("#### 2025 Election Structure")
        assembly_2025 = pd.DataFrame(stats_2025.get('assembly_breakdown', []))
        if not assembly_2025.empty:
            # Group by assembly type for cleaner display
            assembly_grouped = assembly_2025.groupby('assembly_type')['constituencies'].sum().reset_index()
            
            fig_2025 = px.pie(
                assembly_grouped,
                values='constituencies',
                names='assembly_type',
                title="2025: Multi-Assembly System",
                color_discrete_map={
                    'PTHT': '#2E86AB',
                    'AMTHT': '#A23B72',
                    'TPHT': '#F18F01',
                    'TPTYT': '#C73E1D'
                }
            )
            st.plotly_chart(fig_2025, use_container_width=True)
        else:
            st.info("No 2025 assembly data available")

def display_election_comparison(db, base_year, compare_year, show_changes_only, change_threshold):
    """Display detailed election comparison."""
    st.title("🔄 Detailed Election Comparison")
    st.markdown(f"*Comparing {base_year} vs {compare_year} electoral constituencies*")
    
    # Get comparison data
    comparison = db.compare_elections(base_year, compare_year)
    
    if not comparison or not comparison.get('regional_comparison'):
        st.warning("Comparison data not available. Please ensure both datasets are loaded.")
        return
    
    # Summary metrics
    summary = comparison.get('summary', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        constituency_change = summary.get('total_constituencies_change', 0)
        st.metric(
            "Total Constituency Change",
            f"{constituency_change:+,}",
            help=f"Net change in constituencies from {base_year} to {compare_year}"
        )
    
    with col2:
        rep_change = summary.get('total_representatives_change', 0)
        st.metric(
            "Total Representative Change",
            f"{rep_change:+,}",
            help=f"Net change in representatives from {base_year} to {compare_year}"
        )
    
    # Regional comparison table
    st.subheader("📋 Regional Constituency Changes")
    
    comparison_df = pd.DataFrame(comparison['regional_comparison'])
    
    # Apply filters
    if show_changes_only:
        comparison_df = comparison_df[comparison_df['constituencies_change'] != 0]
    
    if change_threshold > 0:
        comparison_df = comparison_df[
            abs(comparison_df['constituencies_change']) >= change_threshold
        ]
    
    if comparison_df.empty:
        st.info("No regions meet the current filter criteria.")
        return
    
    # Style the dataframe
    def style_changes(val):
        if val > 0:
            return 'color: #28a745; font-weight: bold'
        elif val < 0:
            return 'color: #dc3545; font-weight: bold'
        else:
            return 'color: #6c757d'
    
    styled_df = comparison_df.style.applymap(
        style_changes, 
        subset=['constituencies_change', 'representatives_change']
    )
    
    st.dataframe(styled_df, use_container_width=True)
    
    # Regional change visualization
    st.subheader("📊 Regional Change Visualization")
    
    # Sort by absolute change for better visualization
    comparison_df_sorted = comparison_df.reindex(
        comparison_df['constituencies_change'].abs().sort_values(ascending=True).index
    )
    
    fig = go.Figure()
    
    # Add bars with conditional coloring
    colors = ['#28a745' if x >= 0 else '#dc3545' for x in comparison_df_sorted['constituencies_change']]
    
    fig.add_trace(go.Bar(
        x=comparison_df_sorted['constituencies_change'],
        y=comparison_df_sorted['state_region_en'],
        orientation='h',
        marker_color=colors,
        text=comparison_df_sorted['constituencies_change'],
        textposition='outside',
        name='Constituency Change'
    ))
    
    fig.update_layout(
        title=f"Constituency Changes by Region ({base_year} → {compare_year})",
        xaxis_title="Change in Number of Constituencies",
        yaxis_title="State/Region",
        height=max(400, len(comparison_df_sorted) * 30),
        showlegend=False
    )
    
    # Add vertical line at x=0
    fig.add_vline(x=0, line_dash="dash", line_color="gray")
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Top changers
    st.subheader("🔝 Largest Changes")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Largest Increases")
        increases = comparison_df[comparison_df['constituencies_change'] > 0].nlargest(5, 'constituencies_change')
        if not increases.empty:
            for _, row in increases.iterrows():
                st.markdown(f"• **{row['state_region_en']}**: +{row['constituencies_change']} constituencies")
        else:
            st.info("No regions with constituency increases")
    
    with col2:
        st.markdown("#### Largest Decreases")
        decreases = comparison_df[comparison_df['constituencies_change'] < 0].nsmallest(5, 'constituencies_change')
        if not decreases.empty:
            for _, row in decreases.iterrows():
                st.markdown(f"• **{row['state_region_en']}**: {row['constituencies_change']} constituencies")
        else:
            st.info("No regions with constituency decreases")

def display_historical_maps(db, base_year, compare_year, assembly_filter):
    """Display historical map comparison."""
    st.title("🗺️ Historical Map Comparison")
    st.markdown(f"*Geographic comparison of {base_year} vs {compare_year} constituencies*")
    
    # Load data
    historical_data = db.get_historical_constituencies(base_year)
    current_data = db.get_constituencies(assembly_filter)
    
    if historical_data.empty and current_data.empty:
        st.warning("No map data available for the selected years.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"📍 {base_year} Election Map")
        if not historical_data.empty:
            map_2020 = create_historical_map(historical_data, f"{base_year} Constituencies")
            st_folium(map_2020, width=700, height=400)
            st.markdown(f"**Mapped:** {historical_data['lat'].notna().sum()}/{len(historical_data)} constituencies")
        else:
            st.info(f"No {base_year} map data available")
    
    with col2:
        st.subheader(f"📍 {compare_year} Election Map")
        if not current_data.empty:
            map_2025 = create_current_map(current_data, f"{compare_year} Constituencies", assembly_filter)
            st_folium(map_2025, width=700, height=400)
            st.markdown(f"**Mapped:** {current_data['lat'].notna().sum()}/{len(current_data)} constituencies")
        else:
            st.info(f"No {compare_year} map data available")
    
    # Combined statistics
    if not historical_data.empty and not current_data.empty:
        st.subheader("📊 Geographic Coverage Comparison")
        
        coverage_data = pd.DataFrame([
            {
                'Election Year': base_year,
                'Total Constituencies': len(historical_data),
                'Mapped Constituencies': historical_data['lat'].notna().sum(),
                'Coverage %': round(historical_data['lat'].notna().sum() / len(historical_data) * 100, 1)
            },
            {
                'Election Year': compare_year,
                'Total Constituencies': len(current_data),
                'Mapped Constituencies': current_data['lat'].notna().sum(),
                'Coverage %': round(current_data['lat'].notna().sum() / len(current_data) * 100, 1)
            }
        ])
        
        st.dataframe(coverage_data, use_container_width=True)

def create_historical_map(data, title):
    """Create map for historical data."""
    # Filter mapped data
    mapped_data = data[data['lat'].notna() & data['lng'].notna()]
    
    if mapped_data.empty:
        # Return empty map centered on Myanmar
        return folium.Map(location=[21.9162, 95.9560], zoom_start=6)
    
    # Calculate center
    center_lat = mapped_data['lat'].median()
    center_lng = mapped_data['lng'].median()
    
    # Create map
    m = folium.Map(location=[center_lat, center_lng], zoom_start=6, tiles='OpenStreetMap')
    
    # Add markers
    marker_cluster = MarkerCluster(name=title).add_to(m)
    
    for _, row in mapped_data.iterrows():
        popup_html = f"""
        <div style="font-family: Arial; width: 250px;">
            <h4 style="margin: 0; color: #2E86AB;">2020 Constituency</h4>
            <hr style="margin: 5px 0;">
            <b>English:</b> {row['constituency_en']}<br>
            <b>Myanmar:</b> {row.get('constituency_mm', 'N/A')}<br>
            <b>State/Region:</b> {row['state_region_en']}<br>
            <b>Assembly:</b> {row['assembly_type']}<br>
            <b>Representatives:</b> {row['representatives']}<br>
            <b>Code:</b> {row['constituency_code']}
        </div>
        """
        
        folium.CircleMarker(
            location=[row['lat'], row['lng']],
            radius=6,
            popup=folium.Popup(popup_html, max_width=300),
            color='#2E86AB',
            fillColor='#2E86AB',
            weight=2,
            fillOpacity=0.7
        ).add_to(marker_cluster)
    
    folium.LayerControl().add_to(m)
    return m

def create_current_map(data, title, assembly_filter):
    """Create map for current data with assembly colors."""
    # Filter mapped data
    mapped_data = data[data['lat'].notna() & data['lng'].notna()]
    
    if mapped_data.empty:
        return folium.Map(location=[21.9162, 95.9560], zoom_start=6)
    
    # Calculate center
    center_lat = mapped_data['lat'].median()
    center_lng = mapped_data['lng'].median()
    
    # Create map
    m = folium.Map(location=[center_lat, center_lng], zoom_start=6, tiles='OpenStreetMap')
    
    # Assembly colors
    assembly_colors = {
        'PTHT': '#2E86AB',
        'AMTHT': '#A23B72',
        'TPHT': '#F18F01',
        'TPTYT': '#C73E1D'
    }
    
    # Add markers by assembly type
    for assembly in assembly_filter:
        assembly_data = mapped_data[mapped_data['assembly_type'] == assembly]
        if assembly_data.empty:
            continue
            
        color = assembly_colors.get(assembly, '#666666')
        marker_cluster = MarkerCluster(name=f"{assembly} Constituencies").add_to(m)
        
        for _, row in assembly_data.iterrows():
            popup_html = f"""
            <div style="font-family: Arial; width: 250px;">
                <h4 style="margin: 0; color: {color};">2025 {assembly}</h4>
                <hr style="margin: 5px 0;">
                <b>English:</b> {row['constituency_en']}<br>
                <b>Myanmar:</b> {row.get('constituency_mm', 'N/A')}<br>
                <b>State/Region:</b> {row['state_region_en']}<br>
                <b>Assembly:</b> {row['assembly_type']}<br>
                <b>Electoral System:</b> {row.get('electoral_system', 'N/A')}<br>
                <b>Representatives:</b> {row['representatives']}<br>
                <b>Code:</b> {row['constituency_code']}
            </div>
            """
            
            folium.CircleMarker(
                location=[row['lat'], row['lng']],
                radius=6,
                popup=folium.Popup(popup_html, max_width=300),
                color=color,
                fillColor=color,
                weight=2,
                fillOpacity=0.7
            ).add_to(marker_cluster)
    
    folium.LayerControl().add_to(m)
    return m

def main():
    """Main application function."""
    configure_page()
    add_custom_css()
    
    # Initialize database
    db = get_database()
    
    # Create sidebar
    page, base_year, compare_year, show_changes_only, change_threshold, assembly_filter = create_sidebar(db)
    
    # Main content routing
    if page == "📈 Historical Overview":
        display_historical_overview(db)
    elif page == "🔄 Election Comparison":
        display_election_comparison(db, base_year, compare_year, show_changes_only, change_threshold)
    elif page == "🗺️ Historical Maps":
        display_historical_maps(db, base_year, compare_year, assembly_filter)
    elif page == "📋 Change Analysis":
        st.title("📋 Change Analysis")
        st.info("Detailed change analysis feature coming soon!")
    elif page == "📊 Trend Visualization":
        st.title("📊 Trend Visualization")
        st.info("Advanced trend visualization feature coming soon!")

if __name__ == "__main__":
    main()