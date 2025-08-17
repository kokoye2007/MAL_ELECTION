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
    
    # Performance monitoring section
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚡ Performance")
    
    cache_info = visualizer.get_cache_info()
    if cache_info["data_loaded"]:
        st.sidebar.success(f"✅ Data: {cache_info['total_constituencies']} constituencies")
    else:
        st.sidebar.error("❌ Data not loaded")
    
    # Cache management
    if st.sidebar.button("🧹 Clear Cache"):
        visualizer.clear_cache()
        st.rerun()
    
    # Performance tips
    with st.sidebar.expander("💡 Performance Tips"):
        st.markdown("""
        **For optimal performance:**
        - Use 'Auto' render mode on maps
        - Clear cache if experiencing slow loading
        - Regional filters reduce processing time
        - PDF generation may take 10-15 seconds
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
    """Display enhanced interactive map page with zoom-adaptive rendering."""
    
    display_bilingual_title(
        "Enhanced Interactive Constituency Map", 
        "အပြန်အလှန်တုံ့ပြန်သော မဲဆန္ဒနယ် မြေပုံ"
    )
    
    # Map configuration sidebar
    with st.sidebar:
        st.markdown("### 🗺️ Map Settings")
        
        # Zoom level selector
        zoom_level = st.select_slider(
            "Initial Zoom Level",
            options=[4, 5, 6, 7, 8, 9, 10, 11, 12],
            value=6,
            help="Lower values show country-wide view, higher values show detailed local view"
        )
        
        # Rendering mode selector
        render_mode = st.radio(
            "Map Display Mode",
            options=["auto", "regional_counts", "heat_map", "clustered", "individual"],
            index=0,
            help="""
            - Auto: Automatically choose based on zoom level and view mode
            - Regional Counts: Show constituency count per state/region
            - Heat Map: Show constituency density as heat overlay
            - Clustered: Group nearby constituencies 
            - Individual: Show all constituencies separately
            """
        )
        
        # Info about Auto mode progression
        if render_mode == "auto":
            st.info("""
            **Auto Mode Progression:**
            - Zoom ≤6: Heat Map (density visualization)
            - Zoom 7-8: Regional Count Badges  
            - Zoom 9-10: Clustered Markers
            - Zoom 11+: Individual Markers
            """)
        
        # Base map provider selection
        st.markdown("### 🎨 Base Map Provider")
        base_map_provider = st.selectbox(
            "Choose Base Map",
            options=["auto", "cartodb", "osm"],
            index=0,
            help="""
            - Auto: Automatically choose based on zoom level
            - CartoDB: Clean, minimal style (best for country view)
            - OSM: OpenStreetMap with detailed streets
            """
        )
        
        # Map provider info
        if base_map_provider == "auto":
            st.info("**Auto Mode**: Uses CartoDB for country view (≤6), OSM for detailed view (7+)")
        elif base_map_provider == "cartodb":
            st.info("**CartoDB**: Clean, minimal design ideal for data visualization")
        elif base_map_provider == "osm":
            st.info("**OpenStreetMap**: Detailed street-level mapping with community data")
    
    # Map usage instructions  
    st.markdown("""
    📍 **Map Features:**
    - **Zoom Out (Country View)**: Shows density patterns across Myanmar with heat map visualization
    - **Zoom In (Regional View)**: Displays regional counts and groupings for better overview
    - **Zoom In (Local View)**: Shows individual constituencies with detailed information
    - **Interactive**: Click on any area for detailed constituency information and statistics
    - **Heat Map Colors**: Purple indicates fewer constituencies, red indicates more constituencies per region
    """)
    
    # Initialize session state for dynamic zoom tracking
    if 'map_zoom_level' not in st.session_state:
        st.session_state.map_zoom_level = zoom_level
    if 'map_render_mode' not in st.session_state:
        st.session_state.map_render_mode = render_mode
    
    # Auto mode logic: determine actual render mode based on zoom
    actual_render_mode = render_mode
    current_zoom_for_map = zoom_level
    
    if render_mode == "auto":
        # Check if we have a detected zoom from previous interaction
        if 'detected_zoom' in st.session_state and st.session_state.detected_zoom:
            current_zoom_for_map = st.session_state.detected_zoom
        
        # Determine render mode based on current zoom
        if current_zoom_for_map <= 6:
            actual_render_mode = "heat_map"
            mode_name = "Heat Map"
        elif current_zoom_for_map <= 8:
            actual_render_mode = "regional_counts"
            mode_name = "Regional Count Badges" 
        elif current_zoom_for_map <= 10:
            actual_render_mode = "clustered"
            mode_name = "Clustered Markers"
        else:
            actual_render_mode = "individual"
            mode_name = "Individual Markers"
        
        st.caption(f"📍 **Auto Mode Active**: {mode_name} (Zoom {current_zoom_for_map})")
    
    # Create and display map with determined mode
    try:
        constituency_map = visualizer.create_interactive_map(
            selected_regions=selected_regions,
            zoom_level=current_zoom_for_map,
            render_mode=actual_render_mode,  # Use the determined mode, not "auto"
            base_map_provider=base_map_provider,
            heat_map_mode=False
        )
        
        # Display map with zoom detection
        map_data = st_folium(
            constituency_map, 
            width=None, 
            height=600,
            returned_objects=["last_object_clicked", "zoom", "bounds"],
            key=f"map_{actual_render_mode}_{current_zoom_for_map}"  # Dynamic key for re-rendering
        )
        
        # Handle zoom changes for Auto mode
        if map_data and 'zoom' in map_data and map_data['zoom'] and render_mode == "auto":
            detected_zoom = map_data['zoom']
            
            # Determine what mode should be at detected zoom
            if detected_zoom <= 6:
                target_mode = "heat_map"
                target_name = "Heat Map"
            elif detected_zoom <= 8:
                target_mode = "regional_counts"
                target_name = "Regional Count Badges"
            elif detected_zoom <= 10:
                target_mode = "clustered"
                target_name = "Clustered Markers"
            else:
                target_mode = "individual"
                target_name = "Individual Markers"
            
            # Check if mode needs to change
            if target_mode != actual_render_mode:
                st.info(f"🔄 **Auto Mode**: Detected zoom change to {detected_zoom} - Switching to {target_name}")
                st.session_state.detected_zoom = detected_zoom
                st.rerun()  # Trigger re-run to regenerate map with new mode
        
        # Enhanced details when a marker is clicked
        if map_data['last_object_clicked']:
            st.markdown("### 📋 Selected Area Details")
            
            # Try to extract details from clicked object
            clicked_coords = map_data['last_object_clicked'].get('lat'), map_data['last_object_clicked'].get('lng')
            if clicked_coords[0] and clicked_coords[1]:
                # Find nearest constituency
                data_to_search = visualizer.data[visualizer.data['state_region_en'].isin(selected_regions)] if selected_regions else visualizer.data
                
                if len(data_to_search) > 0:
                    # Calculate distances and find closest
                    distances = ((data_to_search['lat'] - clicked_coords[0])**2 + 
                               (data_to_search['lng'] - clicked_coords[1])**2)**0.5
                    closest_idx = distances.idxmin()
                    closest_constituency = data_to_search.loc[closest_idx]
                    
                    # Display detailed information
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**{closest_constituency['constituency_en']}**")
                        st.markdown(f"*{closest_constituency['constituency_mm']}*")
                        st.markdown(f"**State/Region:** {closest_constituency['state_region_en']}")
                        st.markdown(f"**Representatives:** {closest_constituency['representatives']}")
                    
                    with col2:
                        st.markdown(f"**Areas Included:**")
                        st.markdown(f"{closest_constituency['areas_included_en']}")
                        st.markdown(f"**ID:** {closest_constituency['id']}")
                        st.markdown(f"**Assembly:** Pyithu Hluttaw")
        
    except Exception as e:
        st.error(f"Error loading enhanced map: {str(e)}")
        st.markdown("Please ensure all required dependencies are installed and data files are available.")
        
        # Show basic error info for debugging
        with st.expander("🔧 Technical Details"):
            st.code(str(e))
    
    # Enhanced map statistics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if selected_regions:
            filtered_data = visualizer.data[visualizer.data['state_region_en'].isin(selected_regions)]
            st.metric("Constituencies Shown", len(filtered_data))
        else:
            st.metric("Total Constituencies", len(visualizer.data))
    
    with col2:
        # Display current rendering mode
        if render_mode == "auto":
            if zoom_level <= 6:
                display_mode = "Auto (Heat Map)"
            elif zoom_level <= 8:
                display_mode = "Auto (Regional Counts)"
            elif zoom_level <= 10:
                display_mode = "Auto (Clustered)"
            else:
                display_mode = "Auto (Individual)"
        else:
            render_mode_display = {
                "regional_counts": "Regional Counts",
                "heat_map": "Heat Map",
                "clustered": "Clustered View", 
                "individual": "Individual Markers"
            }
            display_mode = render_mode_display.get(render_mode, render_mode)
        
        st.metric("Rendering Mode", display_mode)
    
    with col3:
        zoom_level_desc = {
            4: "Country", 5: "Country", 6: "Country",
            7: "Regional", 8: "Regional", 9: "Regional", 
            10: "Local", 11: "Local", 12: "Local"
        }
        st.metric("Zoom Level", f"{zoom_level} ({zoom_level_desc.get(zoom_level, 'Custom')})")
    
    # Performance tip
    if render_mode == "individual" and zoom_level <= 6:
        st.warning("💡 **Performance Tip**: Individual marker mode at low zoom levels may be slow. Consider using 'Auto' mode for better performance.")
    
    # Region statistics
    if selected_regions:
        st.markdown(f"**Filtered View**: {', '.join(selected_regions)}")
    else:
        st.markdown("**View**: All 15 states and regions across Myanmar")


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
    col1, col2, col3 = st.columns(3)
    
    with col1:
        csv = filtered_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Download as CSV",
            data=csv,
            file_name="myanmar_constituencies.csv",
            mime="text/csv"
        )
    
    with col2:
        # PDF Export functionality
        try:
            if st.button("📑 Generate PDF Report"):
                with st.spinner("Generating PDF report..."):
                    pdf_data = visualizer.generate_pdf_report(
                        title="Myanmar Constituency Report",
                        selected_regions=selected_regions
                    )
                    
                    # Create download button for PDF
                    region_suffix = f"_{'+'.join(selected_regions)}" if selected_regions else "_all_regions"
                    filename = f"myanmar_constituencies{region_suffix}.pdf"
                    
                    st.download_button(
                        label="⬇️ Download PDF Report",
                        data=pdf_data,
                        file_name=filename,
                        mime="application/pdf"
                    )
                    st.success("PDF report generated successfully!")
        except Exception as e:
            st.error(f"Error generating PDF: {str(e)}")
            with st.expander("🔧 Technical Details"):
                st.code(str(e))
    
    with col3:
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