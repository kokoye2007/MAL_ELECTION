#!/usr/bin/env python3
"""
Myanmar Election Data Visualizations

This module contains visualization components for Myanmar election data,
including charts, maps, and interactive elements for Streamlit.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import pandas as pd
import json
from typing import Dict, List, Optional
from pathlib import Path


class MyanmarElectionVisualizer:
    """Create visualizations for Myanmar election data."""
    
    def __init__(self, data_path: str = "data/processed"):
        """Initialize with processed data.
        
        Args:
            data_path: Path to processed data directory
        """
        self.data_path = Path(data_path)
        self.data = self._load_data()
        self.stats = self._load_statistics()
        
    def _load_data(self) -> pd.DataFrame:
        """Load processed constituency data."""
        json_path = self.data_path / "myanmar_constituencies.json"
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return pd.DataFrame(data['constituencies'])
        
    def _load_statistics(self) -> Dict:
        """Load summary statistics."""
        stats_path = self.data_path / "summary_statistics.json"
        
        with open(stats_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def create_parliament_composition_chart(self) -> go.Figure:
        """Create parliament composition overview chart."""
        
        # For now, we only have Pyithu Hluttaw data
        # In future, this would include all three assemblies
        parliament_data = {
            "Assembly": ["Pyithu Hluttaw", "Amyotha Hluttaw", "State/Regional"],
            "Seats": [330, 110, 398],
            "Available Data": [330, 0, 0]  # Only Pyithu data available
        }
        
        df_parliament = pd.DataFrame(parliament_data)
        
        fig = go.Figure()
        
        # Total seats (planned)
        fig.add_trace(go.Bar(
            name='Total Seats (Planned)',
            x=df_parliament['Assembly'],
            y=df_parliament['Seats'],
            marker_color='lightblue',
            text=df_parliament['Seats'],
            textposition='inside'
        ))
        
        # Available data
        fig.add_trace(go.Bar(
            name='Data Available',
            x=df_parliament['Assembly'],
            y=df_parliament['Available Data'],
            marker_color='darkblue',
            text=df_parliament['Available Data'],
            textposition='inside'
        ))
        
        fig.update_layout(
            title="Myanmar Parliament Structure - Electoral Constituencies",
            xaxis_title="Assembly Type",
            yaxis_title="Number of Seats",
            barmode='overlay',
            height=400,
            showlegend=True
        )
        
        return fig
    
    def create_regional_distribution_chart(self) -> go.Figure:
        """Create regional constituency distribution chart."""
        
        regional_data = []
        for region, data in self.stats['states_regions']['breakdown'].items():
            regional_data.append({
                'Region': region,
                'Constituencies': data['constituencies'],
                'Representatives': data['representatives']
            })
        
        df_regional = pd.DataFrame(regional_data).sort_values('Constituencies', ascending=True)
        
        fig = px.bar(
            df_regional,
            x='Constituencies',
            y='Region',
            title='Constituency Distribution by State/Region',
            labels={'Constituencies': 'Number of Constituencies', 'Region': 'State/Region'},
            orientation='h',
            height=600,
            color='Constituencies',
            color_continuous_scale='Blues'
        )
        
        # Add text annotations
        fig.update_traces(texttemplate='%{x}', textposition='inside')
        
        fig.update_layout(
            showlegend=False,
            xaxis_title="Number of Constituencies",
            yaxis_title="State/Region"
        )
        
        return fig
    
    def create_state_type_distribution(self) -> go.Figure:
        """Create pie chart showing state vs region distribution."""
        
        state_type_data = {'States': 0, 'Regions': 0, 'Union Territory': 0}
        
        for region in self.stats['states_regions']['breakdown'].keys():
            if 'State' in region:
                state_type_data['States'] += self.stats['states_regions']['breakdown'][region]['constituencies']
            elif 'Region' in region:
                state_type_data['Regions'] += self.stats['states_regions']['breakdown'][region]['constituencies']
            elif 'Territory' in region:
                state_type_data['Union Territory'] += self.stats['states_regions']['breakdown'][region]['constituencies']
        
        labels = list(state_type_data.keys())
        values = list(state_type_data.values())
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker_colors=['#FF9999', '#66B2FF', '#99FF99']
        )])
        
        fig.update_layout(
            title="Constituency Distribution: States vs Regions vs Territory",
            annotations=[dict(text='330<br>Total', x=0.5, y=0.5, font_size=16, showarrow=False)],
            height=400
        )
        
        return fig
    
    def create_interactive_map(self, selected_regions: Optional[List[str]] = None) -> folium.Map:
        """Create interactive map of Myanmar constituencies."""
        
        # Filter data if regions are selected
        if selected_regions:
            map_data = self.data[self.data['state_region_en'].isin(selected_regions)]
        else:
            map_data = self.data
        
        # Center map on Myanmar
        center_lat = map_data['lat'].mean()
        center_lng = map_data['lng'].mean()
        
        # Create base map
        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=6,
            tiles='OpenStreetMap'
        )
        
        # Add markers for each constituency
        for _, row in map_data.iterrows():
            if pd.notna(row['lat']) and pd.notna(row['lng']):
                
                # Create popup content
                popup_html = f"""
                <div style="font-family: Arial; font-size: 12px; width: 200px;">
                    <h4>{row['constituency_en']}</h4>
                    <p><strong>Myanmar:</strong> {row['constituency_mm']}</p>
                    <p><strong>State/Region:</strong> {row['state_region_en']}</p>
                    <p><strong>Representatives:</strong> {row['representatives']}</p>
                    <p><strong>Areas:</strong> {row['areas_included_en']}</p>
                </div>
                """
                
                # Color code by region
                color = self._get_region_color(row['state_region_en'])
                
                folium.CircleMarker(
                    location=[row['lat'], row['lng']],
                    radius=6,
                    popup=folium.Popup(popup_html, max_width=300),
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7,
                    weight=2
                ).add_to(m)
        
        return m
    
    def _get_region_color(self, region: str) -> str:
        """Get color for region based on type."""
        color_map = {
            'State': '#FF6B6B',      # Red for states
            'Region': '#4ECDC4',     # Teal for regions  
            'Territory': '#45B7D1'   # Blue for territory
        }
        
        for region_type, color in color_map.items():
            if region_type in region:
                return color
        
        return '#95A5A6'  # Default gray
    
    def create_constituency_search_table(self, search_term: str = "", 
                                       selected_regions: List[str] = None) -> pd.DataFrame:
        """Create searchable and filterable constituency table."""
        
        # Start with full data
        filtered_data = self.data.copy()
        
        # Apply region filter
        if selected_regions:
            filtered_data = filtered_data[filtered_data['state_region_en'].isin(selected_regions)]
        
        # Apply search filter
        if search_term:
            search_columns = ['constituency_en', 'constituency_mm', 'state_region_en']
            mask = filtered_data[search_columns].apply(
                lambda x: x.str.contains(search_term, case=False, na=False)
            ).any(axis=1)
            filtered_data = filtered_data[mask]
        
        # Select and rename columns for display
        display_columns = {
            'id': 'ID',
            'constituency_en': 'Constituency (English)',
            'constituency_mm': 'Constituency (မြန်မာ)',
            'state_region_en': 'State/Region',
            'representatives': 'Representatives',
            'areas_included_en': 'Areas Included'
        }
        
        display_data = filtered_data[list(display_columns.keys())].rename(columns=display_columns)
        
        return display_data.sort_values('ID')
    
    def create_summary_cards(self) -> Dict[str, int]:
        """Create summary statistics cards."""
        return {
            "Total Constituencies": self.stats['total_constituencies'],
            "Total Representatives": self.stats['total_representatives'], 
            "States & Regions": self.stats['states_regions']['total'],
            "Assembly Types": len(self.stats['assembly_types'])
        }
    
    def get_region_list(self) -> List[str]:
        """Get list of all states/regions for filtering."""
        return sorted(self.data['state_region_en'].unique())
    
    def create_detailed_regional_breakdown(self, region: str) -> Dict:
        """Create detailed breakdown for a specific region."""
        
        region_data = self.data[self.data['state_region_en'] == region]
        
        return {
            'total_constituencies': len(region_data),
            'total_representatives': region_data['representatives'].sum(),
            'constituencies': region_data[['constituency_en', 'constituency_mm', 'representatives']].to_dict('records')
        }


def display_summary_cards(cards_data: Dict[str, int]):
    """Display summary statistics as cards."""
    
    cols = st.columns(len(cards_data))
    
    for i, (title, value) in enumerate(cards_data.items()):
        with cols[i]:
            st.metric(
                label=title,
                value=f"{value:,}"
            )


def display_bilingual_title(english: str, myanmar: str):
    """Display bilingual title."""
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.title(english)
    
    with col2:
        st.markdown(f"### {myanmar}")


def add_custom_css():
    """Add custom CSS for Myanmar fonts and styling."""
    
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Padauk:wght@400;700&display=swap');
    
    .myanmar-text {
        font-family: 'Padauk', sans-serif;
        font-size: 16px;
        line-height: 1.6;
    }
    
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    
    .region-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)