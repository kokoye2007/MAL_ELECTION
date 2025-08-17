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
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import numpy as np

# Enhanced mapping imports
from folium.plugins import MarkerCluster, HeatMap
import geojson
import requests

# PDF export imports
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import io
import base64
from config import MAP_CONFIG


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
        
    @st.cache_data
    def _load_data(_self) -> pd.DataFrame:
        """Load processed constituency data with caching."""
        json_path = _self.data_path / "myanmar_constituencies.json"
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return pd.DataFrame(data['constituencies'])
        
    @st.cache_data
    def _load_statistics(_self) -> Dict:
        """Load summary statistics with caching."""
        stats_path = _self.data_path / "summary_statistics.json"
        
        with open(stats_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @st.cache_data
    def create_parliament_composition_chart(_self) -> go.Figure:
        """Create parliament composition overview chart with caching."""
        
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
    
    @st.cache_data
    def create_regional_distribution_chart(_self) -> go.Figure:
        """Create regional constituency distribution chart with caching."""
        
        regional_data = []
        for region, data in _self.stats['states_regions']['breakdown'].items():
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
    
    @st.cache_data 
    def create_state_type_distribution(_self) -> go.Figure:
        """Create pie chart showing state vs region distribution with caching."""
        
        state_type_data = {'States': 0, 'Regions': 0, 'Union Territory': 0}
        
        for region in _self.stats['states_regions']['breakdown'].keys():
            if 'State' in region:
                state_type_data['States'] += _self.stats['states_regions']['breakdown'][region]['constituencies']
            elif 'Region' in region:
                state_type_data['Regions'] += _self.stats['states_regions']['breakdown'][region]['constituencies']
            elif 'Territory' in region:
                state_type_data['Union Territory'] += _self.stats['states_regions']['breakdown'][region]['constituencies']
        
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
    
    def create_interactive_map(self, selected_regions: Optional[List[str]] = None, 
                             zoom_level: int = 6, render_mode: str = "auto", 
                             base_map_provider: str = "cartodb", heat_map_mode: bool = False) -> folium.Map:
        """Create zoom-adaptive interactive map of Myanmar constituencies.
        
        Args:
            selected_regions: Optional list of regions to filter
            zoom_level: Initial zoom level (affects rendering mode)
            render_mode: 'auto', 'regional_counts', 'clustered', 'individual', 'heat_map'
            base_map_provider: 'cartodb', 'osm', 'google', 'mapbox'
            heat_map_mode: Use heat map instead of count badges for country view
        """
        
        # Filter data if regions are selected
        if selected_regions:
            map_data = self.data[self.data['state_region_en'].isin(selected_regions)]
        else:
            map_data = self.data
        
        # Center map based on selected data
        if len(map_data) > 0:
            center_lat = map_data['lat'].mean()
            center_lng = map_data['lng'].mean()
            
            # Calculate bounds for filtered regions to adjust zoom
            if selected_regions and len(selected_regions) > 0:
                # Calculate bounding box for selected regions
                lat_range = map_data['lat'].max() - map_data['lat'].min()
                lng_range = map_data['lng'].max() - map_data['lng'].min()
                
                # Adjust zoom level based on geographic spread
                max_range = max(lat_range, lng_range)
                if max_range < 1.0:  # Very small area
                    zoom_level = min(10, zoom_level + 2)
                elif max_range < 3.0:  # Medium area  
                    zoom_level = min(9, zoom_level + 1)
                elif max_range < 6.0:  # Large area
                    zoom_level = max(7, zoom_level)
                # For very large areas, keep original zoom
        else:
            # Default Myanmar center
            center_lat = 21.9162
            center_lng = 95.9560
        
        # Determine rendering mode based on zoom level for Auto mode
        if render_mode == "auto":
            if zoom_level <= 6:
                render_mode = "heat_map"  # Default to heat map for country view
            elif zoom_level <= 8:
                render_mode = "regional_counts"  # Regional count badges
            elif zoom_level <= 10:
                render_mode = "clustered"  # Clustered markers
            else:
                render_mode = "individual"  # Individual markers
            
        
        # Get enhanced base map tiles based on provider and zoom level
        tiles_config = self._get_base_map_tiles(base_map_provider, zoom_level)
        
        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=zoom_level,
            tiles=tiles_config["tiles"],
            attr=tiles_config.get("attr", "")
        )
        
        # Add alternative tile layers if available
        if "alternatives" in tiles_config:
            for alt_layer in tiles_config["alternatives"]:
                alt_layer["layer"].add_to(m)
                
        # Add layer control if multiple layers available
        if "alternatives" in tiles_config:
            folium.LayerControl().add_to(m)
        
        # Render based on mode
        if render_mode == "regional_counts":
            self._add_regional_count_badges(m, map_data)
        elif render_mode == "heat_map":
            self._add_heat_map(m, map_data)
        elif render_mode == "clustered":
            self._add_clustered_markers(m, map_data)
        else:  # individual
            self._add_individual_markers(m, map_data)
        
        return m
    
    def _add_regional_count_badges(self, map_obj: folium.Map, data: pd.DataFrame):
        """Add regional count badges for zoomed out view."""
        
        # Group by state/region
        regional_data = data.groupby('state_region_en').agg({
            'id': 'count',
            'representatives': 'sum',
            'lat': 'mean',
            'lng': 'mean',
            'state_region_mm': 'first'
        }).rename(columns={'id': 'constituencies'})
        
        for region, row in regional_data.iterrows():
            if pd.notna(row['lat']) and pd.notna(row['lng']):
                
                # Create badge popup content
                popup_html = f"""
                <div style="font-family: Arial; font-size: 14px; width: 250px;">
                    <h3 style="color: #1e3a8a; margin-bottom: 10px;">{region}</h3>
                    <p style="margin: 5px 0;"><strong>Myanmar:</strong> {row['state_region_mm']}</p>
                    <p style="margin: 5px 0;"><strong>Constituencies:</strong> {row['constituencies']}</p>
                    <p style="margin: 5px 0;"><strong>Representatives:</strong> {row['representatives']}</p>
                    <hr style="margin: 10px 0;">
                    <p style="font-size: 12px; color: #666;">Click to zoom in for detailed view</p>
                </div>
                """
                
                # Color based on region type
                region_color = self._get_region_color(region)
                
                # Create larger badge marker
                folium.CircleMarker(
                    location=[row['lat'], row['lng']],
                    radius=15 + (row['constituencies'] / 10),  # Size based on constituency count
                    popup=folium.Popup(popup_html, max_width=300),
                    color=region_color,
                    fill=True,
                    fillColor=region_color,
                    fillOpacity=0.8,
                    weight=3
                ).add_to(map_obj)
                
                # Add count label
                folium.Marker(
                    location=[row['lat'], row['lng']],
                    icon=folium.DivIcon(
                        html=f"""
                        <div style="
                            background-color: white;
                            border: 2px solid {region_color};
                            border-radius: 50%;
                            width: 30px;
                            height: 30px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-weight: bold;
                            font-size: 12px;
                            color: {region_color};
                        ">{row['constituencies']}</div>
                        """,
                        icon_size=(30, 30),
                        icon_anchor=(15, 15),
                    )
                ).add_to(map_obj)
    
    def _add_heat_map(self, map_obj: folium.Map, data: pd.DataFrame):
        """Add heat map layer for constituency density visualization with proper scaling."""
        
        # Validate input data
        if data.empty or len(data) == 0:
            return  # Skip heatmap if no data
        
        # Filter out rows with invalid coordinates
        valid_data = data.dropna(subset=['lat', 'lng', 'state_region_en'])
        if valid_data.empty:
            return  # Skip heatmap if no valid coordinates
        
        # Calculate regional constituency counts for meaningful weights
        regional_counts = valid_data.groupby('state_region_en').size()
        
        # Calculate weight statistics for proper scaling
        min_count = regional_counts.min()
        max_count = regional_counts.max()
        median_count = regional_counts.median()
        
        # Create weight mapping for each constituency
        region_weight_map = {}
        for region, count in regional_counts.items():
            # Normalize to 0.1-1.0 range for better color distribution
            # Handle case where max_count == min_count (single region or all regions have same count)
            if max_count == min_count:
                normalized_weight = 0.6  # Use middle value when no variation
            else:
                normalized_weight = 0.1 + (count - min_count) / (max_count - min_count) * 0.9
            region_weight_map[region] = normalized_weight * MAP_CONFIG["HEAT_MAP_INTENSITY_SCALE"]
        
        # Prepare heat map data with proper weights using cleaned data
        heat_data = []
        for _, row in valid_data.iterrows():
            # Use regional density as weight
            weight = region_weight_map.get(row['state_region_en'], 0.1)
            # Ensure weight is not NaN and is a valid number
            if pd.notna(weight) and weight > 0:
                heat_data.append([row['lat'], row['lng'], weight])
        
        if heat_data and len(heat_data) > 0:
            # Create perceptually uniform color gradient
            heat_map = HeatMap(
                heat_data,
                name="Constituency Density",
                min_opacity=MAP_CONFIG["HEAT_MAP_MIN_OPACITY"],
                max_zoom=18,
                radius=MAP_CONFIG["HEAT_MAP_RADIUS"],
                blur=MAP_CONFIG["HEAT_MAP_BLUR"],
                gradient={
                    0.0: '#440154',    # Dark purple (lowest density)
                    0.1: '#31688e',    # Dark blue  
                    0.2: '#26828e',    # Teal
                    0.3: '#1f9e89',    # Green-teal
                    0.4: '#35b779',    # Green
                    0.5: '#6ece58',    # Light green
                    0.6: '#b5de2b',    # Yellow-green
                    0.7: '#fde725',    # Yellow
                    0.8: '#fca636',    # Orange
                    0.9: '#f0746e',    # Light red
                    1.0: '#dc143c'     # Deep red (highest density)
                }
            )
            heat_map.add_to(map_obj)
            
            # Add enhanced info box with actual data ranges
            info_html = f"""
            <div style='position: fixed; 
                        top: 10px; right: 10px; width: 320px; height: 180px; 
                        background-color: white; border:2px solid grey; z-index:9999; 
                        font-size:12px; padding: 15px; border-radius: 8px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                <h4 style='margin:0 0 12px 0; color: #2c3e50; font-size:14px;'>Heat Map: Regional Density</h4>
                <div style='display: flex; align-items: center; margin: 10px 0; line-height: 1.4;'>
                    <div style='width: 15px; height: 15px; background: #440154; margin-right: 10px; border-radius: 3px; flex-shrink: 0;'></div>
                    <span><strong>Low:</strong> {min_count} constituencies<br/><small>(Kayah, Kayin)</small></span>
                </div>
                <div style='display: flex; align-items: center; margin: 10px 0; line-height: 1.4;'>
                    <div style='width: 15px; height: 15px; background: #35b779; margin-right: 10px; border-radius: 3px; flex-shrink: 0;'></div>
                    <span><strong>Medium:</strong> ~{median_count:.0f} constituencies<br/><small>(Average regions)</small></span>
                </div>
                <div style='display: flex; align-items: center; margin: 10px 0; line-height: 1.4;'>
                    <div style='width: 15px; height: 15px; background: #dc143c; margin-right: 10px; border-radius: 3px; flex-shrink: 0;'></div>
                    <span><strong>High:</strong> {max_count} constituencies<br/><small>(Shan, Yangon)</small></span>
                </div>
            </div>
            """
            map_obj.get_root().html.add_child(folium.Element(info_html))
    
    def _add_clustered_markers(self, map_obj: folium.Map, data: pd.DataFrame):
        """Add clustered township boundaries for medium zoom view."""
        
        # For clustered view, we'll show simplified boundaries without clustering
        # since polygon clustering is complex - instead show smaller polygons
        for _, row in data.iterrows():
            if pd.notna(row['lat']) and pd.notna(row['lng']):
                
                popup_html = f"""
                <div style="font-family: Arial; font-size: 12px; width: 200px;">
                    <h4>{row['constituency_en']}</h4>
                    <p><strong>Myanmar:</strong> {row['constituency_mm']}</p>
                    <p><strong>State/Region:</strong> {row['state_region_en']}</p>
                    <p><strong>Representatives:</strong> {row['representatives']}</p>
                    <p><strong>Areas:</strong> {row['areas_included_en']}</p>
                    <hr style="margin: 8px 0;">
                    <p style="font-size: 11px; color: #666;">Constituency Pin Point</p>
                </div>
                """
                
                color = self._get_region_color(row['state_region_en'])
                
                # Create pin point marker for constituency location 
                folium.CircleMarker(
                    location=[row['lat'], row['lng']],
                    radius=6,
                    popup=folium.Popup(popup_html, max_width=300),
                    color=color,
                    weight=1,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.6,
                    opacity=0.8
                ).add_to(map_obj)
    
    def _add_individual_markers(self, map_obj: folium.Map, data: pd.DataFrame):
        """Add individual pin point markers for zoomed in view."""
        
        for _, row in data.iterrows():
            if pd.notna(row['lat']) and pd.notna(row['lng']):
                
                popup_html = f"""
                <div style="font-family: Arial; font-size: 12px; width: 200px;">
                    <h4>{row['constituency_en']}</h4>
                    <p><strong>Myanmar:</strong> {row['constituency_mm']}</p>
                    <p><strong>State/Region:</strong> {row['state_region_en']}</p>
                    <p><strong>Representatives:</strong> {row['representatives']}</p>
                    <p><strong>Areas:</strong> {row['areas_included_en']}</p>
                    <hr style="margin: 8px 0;">
                    <p style="font-size: 11px; color: #666;">Constituency Location</p>
                </div>
                """
                
                color = self._get_region_color(row['state_region_en'])
                
                # Create pin point marker for constituency location
                folium.CircleMarker(
                    location=[row['lat'], row['lng']],
                    radius=8,
                    popup=folium.Popup(popup_html, max_width=300),
                    color=color,
                    weight=2,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7,
                    opacity=1.0
                ).add_to(map_obj)
    
    
    def _get_base_map_tiles(self, provider: str, zoom_level: int) -> Dict:
        """Get base map tile configuration based on provider.
        
        Args:
            provider: Map provider ('cartodb', 'osm', 'google', 'mapbox')
            zoom_level: Current zoom level (unused, kept for compatibility)
            
        Returns:
            Dictionary with tiles configuration
        """
        
        # Provider-specific configurations
        tiles_configs = {
            "cartodb": {
                "tiles": "CartoDB Positron",
                "attr": "© CartoDB, © OpenStreetMap contributors"
            },
            "osm": {
                "tiles": "OpenStreetMap", 
                "attr": "© OpenStreetMap contributors"
            },
            "google": {
                "tiles": "https://mt1.google.com/vt/lyrs=r&x={x}&y={y}&z={z}",
                "attr": "© Google Maps"
            }
        }
        
        # Return configuration with fallback to cartodb
        return tiles_configs.get(provider, tiles_configs["cartodb"])
    
    
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
    
    def generate_pdf_report(self, title: str = "Myanmar Election Constituency Report", 
                          selected_regions: Optional[List[str]] = None) -> bytes:
        """Generate PDF report of constituency data.
        
        Args:
            title: Report title
            selected_regions: Optional list of regions to include
            
        Returns:
            PDF report as bytes
        """
        
        # Filter data if regions selected
        if selected_regions:
            report_data = self.data[self.data['state_region_en'].isin(selected_regions)]
            subtitle = f"Regions: {', '.join(selected_regions)}"
        else:
            report_data = self.data
            subtitle = "All States and Regions"
        
        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            textColor=colors.HexColor('#1e3a8a'),
            alignment=1  # Center alignment
        )
        
        # Build content
        content = []
        
        # Title
        content.append(Paragraph(title, title_style))
        content.append(Paragraph(subtitle, styles['Heading2']))
        content.append(Spacer(1, 20))
        
        # Summary statistics
        summary_stats = self._generate_summary_statistics_for_pdf(report_data)
        content.append(Paragraph("Summary Statistics", styles['Heading2']))
        
        # Summary table
        summary_data = [
            ['Metric', 'Value'],
            ['Total Constituencies', str(summary_stats['total_constituencies'])],
            ['Total Representatives', str(summary_stats['total_representatives'])],
            ['States & Regions', str(summary_stats['states_regions'])],
            ['Assembly Type', 'Pyithu Hluttaw (House of Representatives)'],
            ['Electoral System', 'First Past The Post (FPTP)']
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(summary_table)
        content.append(Spacer(1, 20))
        
        # Regional breakdown
        content.append(Paragraph("Regional Breakdown", styles['Heading2']))
        
        regional_data = report_data.groupby('state_region_en').agg({
            'id': 'count',
            'representatives': 'sum'
        }).rename(columns={'id': 'constituencies'}).reset_index()
        
        regional_table_data = [['State/Region', 'Constituencies', 'Representatives']]
        for _, row in regional_data.iterrows():
            regional_table_data.append([
                row['state_region_en'],
                str(row['constituencies']),
                str(row['representatives'])
            ])
        
        regional_table = Table(regional_table_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
        regional_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(regional_table)
        content.append(Spacer(1, 20))
        
        # Add chart image
        chart_image = self._create_chart_for_pdf(report_data)
        if chart_image:
            content.append(Paragraph("Constituency Distribution Chart", styles['Heading2']))
            content.append(chart_image)
        
        # Footer
        content.append(Spacer(1, 20))
        footer_text = f"""
        <para align="center">
        <font size="10" color="#666666">
        Generated by Myanmar Election Data Visualization Platform<br/>
        Data Source: Myanmar Election Commission<br/>
        Translation Services: National Language Services (NLS)<br/>
        Data Processing: Clean Text & MIMU Boundary Integration<br/>
        Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
        </font>
        </para>
        """
        content.append(Paragraph(footer_text, styles['Normal']))
        
        # Build PDF
        doc.build(content)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _generate_summary_statistics_for_pdf(self, data: pd.DataFrame) -> Dict:
        """Generate summary statistics for PDF report."""
        return {
            'total_constituencies': len(data),
            'total_representatives': data['representatives'].sum(),
            'states_regions': data['state_region_en'].nunique()
        }
    
    def _create_chart_for_pdf(self, data: pd.DataFrame) -> Optional[Image]:
        """Create chart image for PDF report."""
        try:
            # Create regional distribution chart
            regional_data = data.groupby('state_region_en').size().sort_values(ascending=True)
            
            plt.figure(figsize=(10, 6))
            regional_data.plot(kind='barh', color='#3b82f6')
            plt.title('Constituency Distribution by State/Region', fontsize=14, fontweight='bold')
            plt.xlabel('Number of Constituencies')
            plt.ylabel('State/Region')
            plt.tight_layout()
            
            # Save to buffer
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close()
            
            # Create reportlab Image
            img = Image(img_buffer, width=6*inch, height=3.6*inch)
            return img
            
        except Exception as e:
            st.error(f"Error creating chart for PDF: {e}")
            return None
    
    @staticmethod
    def clear_cache():
        """Clear all cached data for memory management."""
        st.cache_data.clear()
        st.success("Cache cleared successfully!")
    
    def get_cache_info(self) -> Dict:
        """Get information about cached data for performance monitoring."""
        cache_info = {
            "data_loaded": hasattr(self, 'data') and len(self.data) > 0,
            "stats_loaded": hasattr(self, 'stats') and bool(self.stats),
            "total_constituencies": len(self.data) if hasattr(self, 'data') else 0,
            "cache_hits": "Cache statistics available via Streamlit"
        }
        return cache_info


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