#!/usr/bin/env python3
"""
Myanmar Election Data Visualization - Streamlit App

A comprehensive web application for visualizing Myanmar's 2025 electoral constituencies
with interactive maps, statistical charts, and bilingual support.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent))

from visualizations import MyanmarElectionVisualizer, display_summary_cards, display_bilingual_title, add_custom_css
from streamlit_folium import st_folium


def configure_page():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="Myanmar Election Data Visualization",
        page_icon="🗳️",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/your-repo/myanmar-election-viz',
            'Report a bug': 'https://github.com/your-repo/myanmar-election-viz/issues',
            'About': '''
            # Myanmar Election Data Visualization
            
            This application visualizes Myanmar's 2025 electoral constituencies
            across the Pyithu Hluttaw (House of Representatives).
            
            **Features:**
            - Interactive maps with constituency details
            - Statistical charts and breakdowns
            - Bilingual support (Myanmar/English)
            - Search and filter functionality
            
            **Data Source:** Myanmar Election Commission
            '''
        }
    )


def create_sidebar(visualizer: MyanmarElectionVisualizer):
    """Create sidebar with navigation and filters."""
    
    st.sidebar.title("🗳️ Navigation")
    
    # Language toggle (placeholder for future implementation)
    language = st.sidebar.selectbox(
        "Language / ဘာသာစကား",
        ["English", "မြန်မာ"],
        index=0,
        help="Switch between English and Myanmar languages"
    )
    
    # Page navigation
    page = st.sidebar.selectbox(
        "Select Page",
        ["📊 Overview", "🗺️ Interactive Map", "📋 Constituency Search", "📈 Detailed Analysis"],
        index=0
    )
    
    st.sidebar.markdown("---")
    
    # Filters
    st.sidebar.subheader("🔍 Filters")
    
    # Region filter
    all_regions = ["All Regions"] + visualizer.get_region_list()
    selected_regions = st.sidebar.multiselect(
        "Select States/Regions",
        options=visualizer.get_region_list(),
        default=[],
        help="Filter data by specific states or regions"
    )
    
    # Search filter for constituency search page
    search_term = ""
    if page == "📋 Constituency Search":
        search_term = st.sidebar.text_input(
            "Search Constituencies",
            placeholder="Enter constituency or region name...",
            help="Search in English or Myanmar"
        )
    
    st.sidebar.markdown("---")
    
    # Information panel
    with st.sidebar.expander("ℹ️ About This Data"):
        st.markdown("""
        **Data Coverage:**
        - Pyithu Hluttaw: 330 constituencies ✅
        - Amyotha Hluttaw: Coming soon 🔄
        - State/Regional: Coming soon 🔄
        
        **Last Updated:** August 2025
        
        **Source:** Myanmar Election Commission
        """)
    
    return page, selected_regions, search_term, language


def show_overview_page(visualizer: MyanmarElectionVisualizer):
    """Display overview page with key statistics and charts."""
    
    # Bilingual title
    display_bilingual_title(
        "Myanmar Election Data Overview", 
        "မြန်မာနိုင်ငံ ရွေးကောက်ပွဲ ဒေတာ ခြုံငုံသုံးမြင်ကွင်း"
    )
    
    # Summary cards
    st.markdown("## 📊 Key Statistics")
    cards_data = visualizer.create_summary_cards()
    display_summary_cards(cards_data)
    
    st.markdown("---")
    
    # Main charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Parliament Structure")
        parliament_fig = visualizer.create_parliament_composition_chart()
        st.plotly_chart(parliament_fig, use_container_width=True)
        
        with st.expander("ℹ️ About Parliament Structure"):
            st.markdown("""
            Myanmar's parliament consists of three levels:
            
            - **Pyithu Hluttaw** (House of Representatives): 330 seats
            - **Amyotha Hluttaw** (House of Nationalities): 110 seats  
            - **State/Regional Assemblies**: 398 seats total
            
            Currently showing data for Pyithu Hluttaw constituencies only.
            """)
    
    with col2:
        st.markdown("### State vs Region Distribution")
        state_type_fig = visualizer.create_state_type_distribution()
        st.plotly_chart(state_type_fig, use_container_width=True)
        
        with st.expander("ℹ️ About Administrative Divisions"):
            st.markdown("""
            Myanmar is divided into:
            
            - **7 States**: Ethnic minority areas
            - **7 Regions**: Predominantly Bamar areas
            - **1 Union Territory**: Naypyitaw (capital)
            
            Each has different numbers of constituencies based on population and geographic factors.
            """)
    
    # Regional distribution chart
    st.markdown("### 🗺️ Regional Constituency Distribution")
    regional_fig = visualizer.create_regional_distribution_chart()
    st.plotly_chart(regional_fig, use_container_width=True)
    
    # Data quality note
    st.info("""
    **📋 Data Note:** This visualization currently covers the 330 Pyithu Hluttaw (House of Representatives) 
    constituencies for Myanmar's 2025 election plan. Data for Amyotha Hluttaw and State/Regional assemblies 
    will be added in future updates.
    """)


def show_map_page(visualizer: MyanmarElectionVisualizer, selected_regions):
    """Display interactive map page."""
    
    display_bilingual_title(
        "Interactive Constituency Map", 
        "အပြန်အလှန်တုံ့ပြန်သော မဲဆန္ဒနယ် မြေပုံ"
    )
    
    # Map instructions
    st.markdown("""
    📍 **Instructions:** Click on any marker to see constituency details. Use the sidebar filters to focus on specific regions.
    """)
    
    # Create and display map
    try:
        constituency_map = visualizer.create_interactive_map(selected_regions)
        
        # Display map
        map_data = st_folium(
            constituency_map, 
            width=None, 
            height=500,
            returned_objects=["last_object_clicked"]
        )
        
        # Show details when a marker is clicked
        if map_data['last_object_clicked']:
            st.markdown("### 📋 Selected Constituency Details")
            # This would be enhanced to show specific constituency data
            st.info("Click on a constituency marker to see detailed information here.")
        
    except Exception as e:
        st.error(f"Error loading map: {str(e)}")
        st.markdown("Please ensure all required dependencies are installed and data files are available.")
    
    # Map statistics
    if selected_regions:
        filtered_data = visualizer.data[visualizer.data['state_region_en'].isin(selected_regions)]
        st.markdown(f"**Showing {len(filtered_data)} constituencies** from selected regions: {', '.join(selected_regions)}")
    else:
        st.markdown(f"**Showing all {len(visualizer.data)} constituencies** across Myanmar")


def show_search_page(visualizer: MyanmarElectionVisualizer, selected_regions, search_term):
    """Display constituency search and table page."""
    
    display_bilingual_title(
        "Constituency Search & Directory", 
        "မဲဆန္ဒနယ် ရှာဖွေခြင်းနှင့် စာရင်း"
    )
    
    # Search results
    filtered_data = visualizer.create_constituency_search_table(search_term, selected_regions)
    
    # Display search summary
    total_shown = len(filtered_data)
    total_available = len(visualizer.data)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Constituencies Shown", total_shown)
    with col2:
        st.metric("Total Available", total_available)
    with col3:
        st.metric("Filtered Out", total_available - total_shown)
    
    # Export options
    st.markdown("### 📥 Export Options")
    col1, col2 = st.columns(2)
    
    with col1:
        csv = filtered_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Download as CSV",
            data=csv,
            file_name="myanmar_constituencies.csv",
            mime="text/csv"
        )
    
    with col2:
        if st.button("📋 Copy to Clipboard"):
            st.success("Table data would be copied to clipboard (feature to be implemented)")
    
    # Display table
    st.markdown("### 📋 Constituency Directory")
    
    if total_shown > 0:
        # Configure table display
        st.dataframe(
            filtered_data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID", width="small"),
                "Constituency (English)": st.column_config.TextColumn("Constituency (English)", width="medium"),
                "Constituency (မြန်မာ)": st.column_config.TextColumn("Constituency (မြန်မာ)", width="medium"),
                "State/Region": st.column_config.TextColumn("State/Region", width="medium"),
                "Representatives": st.column_config.NumberColumn("Reps", width="small"),
                "Areas Included": st.column_config.TextColumn("Areas Included", width="large")
            }
        )
    else:
        st.warning("No constituencies match your search criteria. Try adjusting your filters or search terms.")


def show_analysis_page(visualizer: MyanmarElectionVisualizer, selected_regions):
    """Display detailed analysis page."""
    
    display_bilingual_title(
        "Detailed Analysis & Insights", 
        "အသေးစိတ် ခွဲခြမ်းစိတ်ဖြာမှုနှင့် ထိုးထွင်းသိမြင်မှု"
    )
    
    # Analysis selector
    analysis_type = st.selectbox(
        "Select Analysis Type",
        ["Regional Comparison", "Constituency Size Analysis", "Geographic Distribution"],
        index=0
    )
    
    if analysis_type == "Regional Comparison":
        st.markdown("### 🏛️ Regional Comparison Analysis")
        
        # Regional breakdown table
        regional_stats = []
        for region in visualizer.get_region_list():
            region_breakdown = visualizer.create_detailed_regional_breakdown(region)
            regional_stats.append({
                'State/Region': region,
                'Total Constituencies': region_breakdown['total_constituencies'],
                'Total Representatives': region_breakdown['total_representatives'],
                'Avg per Constituency': round(region_breakdown['total_representatives'] / region_breakdown['total_constituencies'], 2)
            })
        
        df_comparison = pd.DataFrame(regional_stats).sort_values('Total Constituencies', ascending=False)
        
        st.dataframe(df_comparison, use_container_width=True, hide_index=True)
        
        # Insights
        st.markdown("#### 📈 Key Insights")
        largest_region = df_comparison.iloc[0]['State/Region']
        smallest_region = df_comparison.iloc[-1]['State/Region']
        
        st.markdown(f"""
        - **Largest representation:** {largest_region} with {df_comparison.iloc[0]['Total Constituencies']} constituencies
        - **Smallest representation:** {smallest_region} with {df_comparison.iloc[-1]['Total Constituencies']} constituencies
        - **Total coverage:** {len(visualizer.get_region_list())} states and regions
        - **Representation ratio:** 1 representative per constituency (FPTP system)
        """)
    
    elif analysis_type == "Constituency Size Analysis":
        st.markdown("### 📏 Constituency Size Analysis")
        st.info("Constituency size analysis would require additional geographic and demographic data.")
        
    elif analysis_type == "Geographic Distribution":
        st.markdown("### 🗺️ Geographic Distribution Analysis")
        st.info("Geographic distribution analysis would include population density and area calculations.")


def main():
    """Main application function."""
    
    # Configure page
    configure_page()
    
    # Add custom CSS
    add_custom_css()
    
    # Initialize visualizer
    try:
        visualizer = MyanmarElectionVisualizer()
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.stop()
    
    # Create sidebar and get user inputs
    page, selected_regions, search_term, language = create_sidebar(visualizer)
    
    # Display appropriate page
    if page == "📊 Overview":
        show_overview_page(visualizer)
    elif page == "🗺️ Interactive Map":
        show_map_page(visualizer, selected_regions)
    elif page == "📋 Constituency Search":
        show_search_page(visualizer, selected_regions, search_term)
    elif page == "📈 Detailed Analysis":
        show_analysis_page(visualizer, selected_regions)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <p>Myanmar Election Data Visualization | Data Source: Myanmar Election Commission</p>
        <p>🤖 Built with Streamlit | 📊 Powered by Plotly & Folium</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()