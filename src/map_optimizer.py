#!/usr/bin/env python3
"""
Map Rendering Optimizer for Myanmar Election Visualization
Optimizes map performance for rendering 835+ constituencies with various strategies.
"""

import folium
from folium.plugins import MarkerCluster, HeatMap
import pandas as pd
import numpy as np
import streamlit as st
from typing import Dict, List, Optional, Tuple
import json
import math

class MapRenderingOptimizer:
    """Optimize map rendering for large numbers of constituencies."""
    
    def __init__(self):
        """Initialize the map optimizer."""
        self.assembly_colors = {
            'PTHT': '#2E86AB',
            'AMTHT': '#A23B72',
            'TPHT': '#F18F01',
            'TPTYT': '#C73E1D'
        }
        
        # Performance thresholds
        self.CLUSTER_THRESHOLD = 100  # Use clustering above this number
        self.HEATMAP_THRESHOLD = 300  # Use heatmap above this number
        self.SIMPLIFY_THRESHOLD = 500  # Simplify markers above this number
        
    def create_optimized_map(
        self, 
        data: pd.DataFrame, 
        assembly_types: List[str], 
        zoom_level: int = 6,
        render_mode: str = "auto",
        performance_mode: str = "balanced"
    ) -> folium.Map:
        """Create an optimized map based on data size and performance requirements.
        
        Args:
            data: Constituency data
            assembly_types: Selected assembly types
            zoom_level: Initial zoom level
            render_mode: Rendering strategy (auto, cluster, heatmap, simplified, full)
            performance_mode: Performance optimization (fast, balanced, quality)
            
        Returns:
            Optimized folium map
        """
        
        # Filter and prepare data
        filtered_data = self._prepare_data(data, assembly_types)
        
        if filtered_data.empty:
            return self._create_empty_map()
        
        # Determine optimal rendering strategy
        optimal_mode = self._determine_render_mode(filtered_data, render_mode, performance_mode)
        
        # Calculate map bounds and center
        center_lat, center_lng, bounds = self._calculate_map_bounds(filtered_data)
        print(f"🗺️  Map center calculated: lat={center_lat:.4f}, lng={center_lng:.4f}")
        print(f"📊 Filtered data size: {len(filtered_data)}, Valid coords: {(filtered_data['lat'].notna() & filtered_data['lng'].notna()).sum()}")
        
        # Create base map with optimized tile layer
        base_map = self._create_base_map(
            center_lat, center_lng, zoom_level, performance_mode
        )
        
        # Apply rendering strategy
        if optimal_mode == "heatmap":
            self._add_heatmap_layer(base_map, filtered_data)
        elif optimal_mode == "cluster":
            self._add_clustered_markers(base_map, filtered_data, assembly_types)
        elif optimal_mode == "simplified":
            self._add_simplified_markers(base_map, filtered_data, assembly_types)
        else:  # full rendering
            self._add_full_markers(base_map, filtered_data, assembly_types)
        
        # Add performance info
        self._add_performance_info(base_map, filtered_data, optimal_mode)
        
        return base_map
    
    def _prepare_data(self, data: pd.DataFrame, assembly_types: List[str]) -> pd.DataFrame:
        """Prepare and filter data for mapping."""
        if data.empty:
            return data
        
        # Filter by assembly types
        if assembly_types:
            data = data[data['assembly_type'].isin(assembly_types)]
        
        # Remove entries without coordinates
        data = data[data['lat'].notna() & data['lng'].notna()].copy()
        
        # Add cluster groups for performance
        if len(data) > self.CLUSTER_THRESHOLD:
            data['cluster_group'] = self._create_cluster_groups(data)
        
        return data
    
    def _create_cluster_groups(self, data: pd.DataFrame) -> pd.Series:
        """Create spatial cluster groups for better performance."""
        # Simple grid-based clustering
        lat_bins = np.linspace(data['lat'].min(), data['lat'].max(), 10)
        lng_bins = np.linspace(data['lng'].min(), data['lng'].max(), 10)
        
        lat_groups = pd.cut(data['lat'], lat_bins, labels=False)
        lng_groups = pd.cut(data['lng'], lng_bins, labels=False)
        
        return lat_groups * 10 + lng_groups
    
    def _determine_render_mode(
        self, 
        data: pd.DataFrame, 
        render_mode: str, 
        performance_mode: str
    ) -> str:
        """Determine optimal rendering mode based on data size and performance settings."""
        
        data_size = len(data)
        
        if render_mode != "auto":
            return render_mode
        
        # Auto-determine based on data size and performance mode
        if performance_mode == "fast":
            if data_size > self.HEATMAP_THRESHOLD:
                return "heatmap"
            elif data_size > self.CLUSTER_THRESHOLD:
                return "cluster"
            else:
                return "simplified"
        
        elif performance_mode == "balanced":
            if data_size > self.SIMPLIFY_THRESHOLD:
                return "heatmap"
            elif data_size > self.CLUSTER_THRESHOLD:
                return "cluster"
            else:
                return "full"
        
        else:  # quality mode
            if data_size > self.SIMPLIFY_THRESHOLD:
                return "cluster"
            else:
                return "full"
    
    def _calculate_map_bounds(self, data: pd.DataFrame) -> Tuple[float, float, List]:
        """Calculate optimal map center and bounds."""
        # Filter out invalid coordinates
        valid_data = data[data['lat'].notna() & data['lng'].notna()]
        
        if valid_data.empty:
            # Fallback to Myanmar center
            center_lat, center_lng = 21.9162, 95.9560
            bounds = [[10.0, 92.0], [29.0, 102.0]]  # Myanmar approximate bounds
        else:
            # Calculate center from valid coordinates
            center_lat = valid_data['lat'].median()
            center_lng = valid_data['lng'].median()
            
            # Validate coordinates are within Myanmar bounds (approximate)
            if not (10.0 <= center_lat <= 29.0) or not (92.0 <= center_lng <= 102.0):
                print(f"⚠️  Invalid coordinates detected: {center_lat}, {center_lng} - using Myanmar fallback")
                center_lat, center_lng = 21.9162, 95.9560
                bounds = [[10.0, 92.0], [29.0, 102.0]]
            else:
                # Calculate bounds for zoom optimization
                bounds = [
                    [valid_data['lat'].min(), valid_data['lng'].min()],
                    [valid_data['lat'].max(), valid_data['lng'].max()]
                ]
        
        return center_lat, center_lng, bounds
    
    def _create_base_map(
        self, 
        center_lat: float, 
        center_lng: float, 
        zoom_level: int, 
        performance_mode: str
    ) -> folium.Map:
        """Create optimized base map."""
        
        # Choose tile layer based on performance mode
        if performance_mode == "fast":
            tiles = "OpenStreetMap"
            tile_attr = None
        else:
            tiles = "CartoDB Positron"
            tile_attr = "© CartoDB, © OpenStreetMap contributors"
        
        # Ensure coordinates are valid for Myanmar
        if not (10.0 <= center_lat <= 29.0) or not (92.0 <= center_lng <= 102.0):
            print(f"⚠️  Invalid map center detected: {center_lat}, {center_lng} - using Myanmar fallback")
            center_lat, center_lng = 21.9162, 95.9560
            
        base_map = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=zoom_level,
            tiles=tiles,
            attr=tile_attr,
            prefer_canvas=True,  # Use canvas for better performance
            max_zoom=18,
            zoom_control=True,
            scrollWheelZoom=True
        )
        
        return base_map
    
    def _add_heatmap_layer(self, map_obj: folium.Map, data: pd.DataFrame):
        """Add optimized heatmap layer for large datasets."""
        
        # Create weight data based on representatives
        heat_data = []
        for _, row in data.iterrows():
            weight = row.get('representatives', 1)
            heat_data.append([row['lat'], row['lng'], weight])
        
        # Optimized heatmap settings for performance
        heatmap = HeatMap(
            heat_data,
            name="Constituency Density",
            min_opacity=0.3,
            max_zoom=15,  # Limit max zoom for performance
            radius=25,  # Larger radius for better visibility
            blur=15,
            gradient={
                0.0: '#440154',
                0.2: '#31688e',
                0.4: '#35b779',
                0.6: '#fde725',
                0.8: '#f0746e',
                1.0: '#dc143c'
            }
        )
        
        heatmap.add_to(map_obj)
        
        # Add legend
        legend_html = self._create_heatmap_legend(data)
        map_obj.get_root().html.add_child(folium.Element(legend_html))
    
    def _add_clustered_markers(
        self, 
        map_obj: folium.Map, 
        data: pd.DataFrame, 
        assembly_types: List[str]
    ):
        """Add clustered markers for medium-sized datasets."""
        
        # Use FastMarkerCluster for better performance
        for assembly in assembly_types:
            assembly_data = data[data['assembly_type'] == assembly]
            if assembly_data.empty:
                continue
            
            color = self.assembly_colors.get(assembly, '#666666')
            
            # Create optimized marker cluster
            marker_cluster = MarkerCluster(
                name=f"{assembly} Constituencies",
                show_coverage_on_hover=False,  # Disable for performance
                max_cluster_radius=50,  # Optimize cluster radius
                disable_clustering_at_zoom=12  # Show individual markers at high zoom
            ).add_to(map_obj)
            
            # Add simplified markers
            for _, row in assembly_data.iterrows():
                popup_html = self._create_simple_popup(row, assembly, color)
                
                folium.CircleMarker(
                    location=[row['lat'], row['lng']],
                    radius=5,  # Smaller radius for performance
                    popup=folium.Popup(popup_html, max_width=250),
                    color=color,
                    fillColor=color,
                    weight=1,  # Thinner border
                    fillOpacity=0.7
                ).add_to(marker_cluster)
        
        folium.LayerControl().add_to(map_obj)
    
    def _add_simplified_markers(
        self, 
        map_obj: folium.Map, 
        data: pd.DataFrame, 
        assembly_types: List[str]
    ):
        """Add simplified markers for performance."""
        
        for assembly in assembly_types:
            assembly_data = data[data['assembly_type'] == assembly]
            if assembly_data.empty:
                continue
            
            color = self.assembly_colors.get(assembly, '#666666')
            
            # Create feature group instead of individual markers for better performance
            feature_group = folium.FeatureGroup(name=f"{assembly} Constituencies")
            
            # Add points as GeoJSON for better performance
            geojson_data = {
                "type": "FeatureCollection",
                "features": []
            }
            
            for _, row in assembly_data.iterrows():
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [row['lng'], row['lat']]
                    },
                    "properties": {
                        "name": row['constituency_en'],
                        "assembly": assembly,
                        "representatives": row.get('representatives', 1),
                        "state_region": row['state_region_en'],
                        "popup": self._create_simple_popup_text(row, assembly)
                    }
                }
                geojson_data["features"].append(feature)
            
            # Add GeoJSON layer
            folium.GeoJson(
                geojson_data,
                marker=folium.CircleMarker(
                    radius=4,
                    color=color,
                    fillColor=color,
                    weight=1,
                    fillOpacity=0.6
                ),
                popup=folium.GeoJsonPopup(fields=["popup"], labels=False),
                tooltip=folium.GeoJsonTooltip(fields=["name"], labels=False)
            ).add_to(feature_group)
            
            feature_group.add_to(map_obj)
        
        folium.LayerControl().add_to(map_obj)
    
    def _add_full_markers(
        self, 
        map_obj: folium.Map, 
        data: pd.DataFrame, 
        assembly_types: List[str]
    ):
        """Add full-featured markers for small datasets."""
        
        for assembly in assembly_types:
            assembly_data = data[data['assembly_type'] == assembly]
            if assembly_data.empty:
                continue
            
            color = self.assembly_colors.get(assembly, '#666666')
            
            for _, row in assembly_data.iterrows():
                popup_html = self._create_detailed_popup(row, assembly, color)
                
                folium.CircleMarker(
                    location=[row['lat'], row['lng']],
                    radius=6,
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=row['constituency_en'],
                    color=color,
                    fillColor=color,
                    weight=2,
                    fillOpacity=0.7
                ).add_to(map_obj)
    
    def _create_simple_popup(self, row: pd.Series, assembly: str, color: str) -> str:
        """Create simplified popup for performance."""
        return f"""
        <div style="font-family: Arial; width: 200px;">
            <h4 style="margin: 0; color: {color};">{assembly}</h4>
            <hr style="margin: 5px 0;">
            <b>{row['constituency_en']}</b><br>
            <b>Region:</b> {row['state_region_en']}<br>
            <b>Reps:</b> {row.get('representatives', 1)}
        </div>
        """
    
    def _create_simple_popup_text(self, row: pd.Series, assembly: str) -> str:
        """Create simple popup text for GeoJSON."""
        return f"<b>{row['constituency_en']}</b><br>{row['state_region_en']}<br>Assembly: {assembly}"
    
    def _create_detailed_popup(self, row: pd.Series, assembly: str, color: str) -> str:
        """Create detailed popup for full rendering."""
        return f"""
        <div style="font-family: Arial; width: 250px;">
            <h4 style="margin: 0; color: {color};">{assembly}</h4>
            <hr style="margin: 5px 0;">
            <b>English:</b> {row['constituency_en']}<br>
            <b>Myanmar:</b> {row.get('constituency_mm', 'N/A')}<br>
            <b>State/Region:</b> {row['state_region_en']}<br>
            <b>Electoral System:</b> {row.get('electoral_system', 'N/A')}<br>
            <b>Representatives:</b> {row.get('representatives', 1)}<br>
            <b>Code:</b> {row.get('constituency_code', 'N/A')}
        </div>
        """
    
    def _create_heatmap_legend(self, data: pd.DataFrame) -> str:
        """Create legend for heatmap visualization."""
        total_constituencies = len(data)
        assembly_counts = data['assembly_type'].value_counts().to_dict()
        
        legend_items = []
        for assembly, count in assembly_counts.items():
            color = self.assembly_colors.get(assembly, '#666666')
            legend_items.append(f"""
                <div style='display: flex; align-items: center; margin: 5px 0;'>
                    <div style='width: 15px; height: 15px; background: {color}; 
                         margin-right: 8px; border-radius: 3px; border: 1px solid #333;'></div>
                    <span style='color: #333; font-weight: 500;'>{assembly}: {count} constituencies</span>
                </div>
            """)
        
        return f"""
        <div style='position: fixed; 
                    top: 10px; right: 10px; width: 280px; height: auto; 
                    background-color: rgba(255, 255, 255, 0.95); 
                    border: 2px solid #333; z-index: 9999; 
                    font-size: 12px; padding: 15px; border-radius: 8px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.2);'>
            <h4 style='margin: 0 0 12px 0; color: #1a1a1a; font-size: 14px; font-weight: bold;'>
                Constituency Heatmap ({total_constituencies} total)
            </h4>
            {''.join(legend_items)}
            <div style='margin-top: 10px; font-size: 10px; color: #555; font-weight: normal;'>
                Density visualization optimized for performance
            </div>
        </div>
        """
    
    def _add_performance_info(self, map_obj: folium.Map, data: pd.DataFrame, render_mode: str):
        """Add performance information overlay."""
        data_size = len(data)
        
        performance_html = f"""
        <div style='position: fixed; 
                    bottom: 10px; left: 10px; width: 200px; height: auto; 
                    background-color: rgba(255,255,255,0.95); 
                    border: 2px solid #333; z-index:9999; 
                    font-size:11px; padding: 10px; border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
            <div style='color: #1a1a1a; font-weight: bold; margin-bottom: 4px;'>Map Performance:</div>
            <div style='color: #333;'>Mode: {render_mode.title()}</div>
            <div style='color: #333;'>Constituencies: {data_size:,}</div>
            <div style='color: #27ae60;'>Optimized: ✅</div>
        </div>
        """
        
        map_obj.get_root().html.add_child(folium.Element(performance_html))
    
    def _create_empty_map(self) -> folium.Map:
        """Create empty map when no data available."""
        return folium.Map(
            location=[21.9162, 95.9560],  # Myanmar center
            zoom_start=6,
            tiles="CartoDB Positron"
        )

def create_performance_optimized_map(
    data: pd.DataFrame,
    assembly_types: List[str],
    zoom_level: int = 6,
    performance_mode: str = "balanced"
) -> folium.Map:
    """Create a performance-optimized map for large constituency datasets.
    
    Args:
        data: Constituency dataframe
        assembly_types: List of assembly types to display
        zoom_level: Initial zoom level
        performance_mode: Performance optimization level (fast, balanced, quality)
        
    Returns:
        Optimized folium map object
    """
    optimizer = MapRenderingOptimizer()
    return optimizer.create_optimized_map(
        data, assembly_types, zoom_level, "auto", performance_mode
    )