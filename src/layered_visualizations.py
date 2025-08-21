#!/usr/bin/env python3
"""
Enhanced Myanmar Election Multi-Layer Visualizations

This module provides advanced multi-layer mapping capabilities with:
1. Pinpoint constituency markers (from MIMU coordinate data)
2. MIMU township boundary layers
3. Interactive layer control
4. Zoom-adaptive rendering
"""

import folium
import pandas as pd
import json
import geopandas as gpd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np


class MyanmarElectionLayeredVisualizer:
    """Create multi-layer visualizations for Myanmar election data with MIMU integration."""
    
    def __init__(self, data_path: str = "data/processed"):
        """Initialize with processed data and MIMU boundaries.
        
        Args:
            data_path: Path to processed data directory
        """
        self.data_path = Path(data_path)
        self.mimu_boundaries = self._load_mimu_boundaries()
        
    def _load_mimu_boundaries(self) -> Optional[Dict]:
        """Load MIMU township boundary data."""
        try:
            # Try multiple possible paths
            possible_paths = [
                self.data_path.parent / 'data' / 'geojson' / 'myanmar_townships_mimu.geojson',
                Path('data/geojson/myanmar_townships_mimu.geojson'),
                Path('../data/geojson/myanmar_townships_mimu.geojson'),
                self.data_path.parent / 'data' / 'geojson' / 'mimu_township_boundaries.geojson',
                Path('data/geojson/mimu_township_boundaries.geojson')
            ]
            
            for mimu_path in possible_paths:
                if mimu_path.exists():
                    with open(mimu_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
            
            # If no boundaries found, continue without them (graceful degradation)
            print(f"⚠️ MIMU boundaries not found in any of these paths: {[str(p) for p in possible_paths]}")
            return None
        except Exception as e:
            print(f"❌ Error loading MIMU boundaries: {e}")
            return None
    
    def create_multi_layer_map(
        self, 
        constituencies_data: pd.DataFrame,
        center_coords: Tuple[float, float] = (21.9162, 95.9560),
        zoom_level: int = 7,
        show_boundaries: bool = True,
        show_pinpoints: bool = True,
        show_selection_boxes: bool = True,
        area_radius_km: float = 3,
        assembly_filter: List[str] = None,
        boundary_style: Dict = None,
        pinpoint_style: Dict = None
    ) -> folium.Map:
        """Create multi-layer interactive map with boundaries and constituency pinpoints.
        
        Args:
            constituencies_data: DataFrame with constituency data
            center_coords: (lat, lng) for map center
            zoom_level: Initial zoom level
            show_boundaries: Whether to show MIMU township boundaries
            show_pinpoints: Whether to show constituency pinpoint markers
            show_selection_boxes: Whether to show transparent circular constituency areas
            area_radius_km: Radius in kilometers for constituency areas
            assembly_filter: List of assembly types to display
            boundary_style: Custom styling for boundary layer
            pinpoint_style: Custom styling for pinpoint markers
            
        Returns:
            Folium map with multi-layer visualization
        """
        # Initialize map
        m = folium.Map(
            location=center_coords,
            zoom_start=zoom_level,
            tiles='OpenStreetMap'
        )
        
        # Filter data by assembly type if specified
        if assembly_filter:
            filtered_data = constituencies_data[
                constituencies_data['assembly_type'].isin(assembly_filter)
            ]
        else:
            filtered_data = constituencies_data
        
        # Layer 1: MIMU Township Boundaries (colored by assembly types)
        if show_boundaries and self.mimu_boundaries:
            self._add_mimu_boundaries_layer(m, boundary_style or {}, filtered_data)
        
        # Layer 2: Constituency Pinpoint Markers
        if show_pinpoints and len(filtered_data) > 0:
            self._add_constituency_pinpoints_layer(m, filtered_data, pinpoint_style or {}, show_selection_boxes, area_radius_km)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        return m
    
    def _add_mimu_boundaries_layer(self, map_obj: folium.Map, style: Dict, constituencies_data: pd.DataFrame = None):
        """Add MIMU township boundaries as a separate layer, colored by constituency assembly types."""
        # Create boundary feature group
        boundary_group = folium.FeatureGroup(name="Township Boundaries (MIMU)")
        
        # Create a mapping of township codes to assembly types
        tsp_assembly_map = {}
        if constituencies_data is not None and not constituencies_data.empty:
            for _, row in constituencies_data.iterrows():
                tsp_codes = str(row.get('tsp_pcode', '')).split('+') if row.get('tsp_pcode') else []
                assembly_type = row.get('assembly_type', '')
                for code in tsp_codes:
                    code = code.strip()
                    if code and assembly_type:
                        # If multiple assemblies in same township, prioritize PTHT > AMTHT > TPHT
                        if code not in tsp_assembly_map or assembly_type == 'PTHT':
                            tsp_assembly_map[code] = assembly_type
        
        # Add each township boundary
        for feature in self.mimu_boundaries.get('features', []):
            props = feature.get('properties', {})
            tsp_pcode = props.get('TS_PCODE', 'Unknown')
            tsp_name_en = props.get('TS', 'Unknown Township')
            tsp_name_mm = props.get('TS_MMR', 'အမည်မသိမြို့နယ်')
            state_name = props.get('ST', 'Unknown State')
            
            # Get assembly type for this township
            assembly_type = tsp_assembly_map.get(tsp_pcode, None)
            
            # Determine boundary color based on assembly type
            if assembly_type:
                boundary_color = self._get_assembly_color(assembly_type)
                fill_opacity = 0.3  # More visible when colored
                border_opacity = 0.6
            else:
                boundary_color = 'gray'
                fill_opacity = 0.05  # Very light for non-constituency townships
                border_opacity = 0.2
            
            # Create boundary styling
            boundary_style = {
                'fillColor': boundary_color,
                'color': boundary_color,
                'weight': 2 if assembly_type else 1,
                'fillOpacity': fill_opacity,
                'opacity': border_opacity
            }
            
            # Create popup content for township
            assembly_info = f"<p style='margin: 3px 0;'><strong>Assembly:</strong> {assembly_type}</p>" if assembly_type else ""
            popup_content = f"""
            <div style="font-family: Arial; font-size: 12px; width: 200px;">
                <h4 style="color: {boundary_color if assembly_type else '#1e40af'}; margin: 5px 0;">{tsp_name_en}</h4>
                <p style="margin: 3px 0;"><strong>မြန်မာ:</strong> {tsp_name_mm}</p>
                <p style="margin: 3px 0;"><strong>MIMU Code:</strong> {tsp_pcode}</p>
                <p style="margin: 3px 0;"><strong>State/Region:</strong> {state_name}</p>
                {assembly_info}
                <hr style="margin: 5px 0;">
                <p style="font-size: 10px; color: #666;">MIMU Township Boundary</p>
            </div>
            """
            
            # Add boundary to feature group
            folium.GeoJson(
                feature,
                style_function=lambda x, style=boundary_style: style,
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=f"{tsp_name_en} ({tsp_pcode})"
            ).add_to(boundary_group)
        
        boundary_group.add_to(map_obj)
    
    def _add_constituency_pinpoints_layer(self, map_obj: folium.Map, data: pd.DataFrame, style: Dict, show_selection_boxes: bool = True, area_radius_km: float = 3):
        """Add constituency pinpoint markers as a separate layer."""
        # Default pinpoint styling
        default_style = {
            'radius': 6,
            'weight': 2,
            'opacity': 0.8,
            'fill_opacity': 0.7
        }
        pinpoint_style = {**default_style, **style}
        
        # Create separate feature groups for each assembly type
        assembly_groups = {}
        
        for _, row in data.iterrows():
            if pd.notna(row.get('lat')) and pd.notna(row.get('lng')):
                assembly_type = row.get('assembly_type', 'Unknown')
                
                # Create feature group for this assembly type if not exists
                if assembly_type not in assembly_groups:
                    assembly_groups[assembly_type] = folium.FeatureGroup(
                        name=f"Constituencies - {assembly_type}"
                    )
                
                # Get assembly-specific color
                color = self._get_assembly_color(assembly_type)
                
                # Create constituency popup content
                popup_content = f"""
                <div style="font-family: Arial; font-size: 13px; width: 280px;">
                    <h4 style="color: {color}; margin: 8px 0;">{row.get('constituency_en', 'Unknown')}</h4>
                    <p style="margin: 4px 0;"><strong>မြန်မာ:</strong> {row.get('constituency_mm', '')}</p>
                    <p style="margin: 4px 0;"><strong>Assembly:</strong> {assembly_type}</p>
                    <p style="margin: 4px 0;"><strong>State/Region:</strong> {row.get('state_region_en', 'Unknown')}</p>
                    <p style="margin: 4px 0;"><strong>Representatives:</strong> {row.get('representatives', 1)}</p>
                    <p style="margin: 4px 0;"><strong>Township Areas:</strong> {row.get('areas_included_en', '')}</p>
                    <p style="margin: 4px 0;"><strong>MIMU Code:</strong> {row.get('tsp_pcode', '')}</p>
                    <hr style="margin: 8px 0;">
                    <p style="font-size: 11px; color: #666;">
                        Coordinates: {row.get('lat', 0):.4f}, {row.get('lng', 0):.4f}<br>
                        Source: {row.get('coordinate_source', 'Unknown')}
                    </p>
                </div>
                """
                
                # Add pinpoint marker
                marker = folium.CircleMarker(
                    location=[row['lat'], row['lng']],
                    radius=pinpoint_style['radius'],
                    color=color,
                    weight=pinpoint_style['weight'],
                    opacity=pinpoint_style['opacity'],
                    fillColor=color,
                    fillOpacity=pinpoint_style['fill_opacity'],
                    popup=folium.Popup(popup_content, max_width=400),
                    tooltip=f"{row.get('constituency_en', 'Unknown')} ({assembly_type})"
                )
                
                marker.add_to(assembly_groups[assembly_type])
        
        # Add all assembly groups to map
        for group in assembly_groups.values():
            group.add_to(map_obj)
    
    def _get_assembly_color(self, assembly_type: str) -> str:
        """Get color coding for different assembly types."""
        color_mapping = {
            'PTHT': '#dc2626',     # Red for Pyithu Hluttaw
            'AMTHT': '#2563eb',    # Blue for Amyotha Hluttaw
            'AMTHT_PR': '#1d4ed8', # Dark Blue for Amyotha PR
            'TPHT': '#059669',     # Green for State/Regional Hluttaw
            'TPHT_PR': '#047857',  # Dark Green for State/Regional PR
            'TPTYT': '#7c2d12'     # Brown for Ethnic constituencies
        }
        return color_mapping.get(assembly_type, '#6b7280')  # Default gray
    
    def _create_selection_area(self, lat: float, lng: float, color: str, radius_km: float = 5) -> folium.Circle:
        """Create a transparent circular area around a constituency marker."""
        # Convert radius from km to meters for folium
        radius_meters = radius_km * 1000
        
        # Create transparent circle with assembly color
        selection_area = folium.Circle(
            location=[lat, lng],
            radius=radius_meters,
            color=color,
            weight=2,
            opacity=0.6,  # Border opacity
            fillColor=color,
            fillOpacity=0.2,  # Transparent fill similar to boundaries
            popup=None,
            tooltip="Constituency area"
        )
        
        return selection_area
    
    def create_assembly_comparison_map(
        self,
        constituencies_data: pd.DataFrame,
        assembly_types: List[str],
        center_coords: Tuple[float, float] = (21.9162, 95.9560),
        zoom_level: int = 7
    ) -> folium.Map:
        """Create a map comparing different assembly types with color-coded layers.
        
        Args:
            constituencies_data: DataFrame with constituency data
            assembly_types: List of assembly types to compare
            center_coords: (lat, lng) for map center
            zoom_level: Initial zoom level
            
        Returns:
            Folium map with assembly comparison layers
        """
        m = folium.Map(
            location=center_coords,
            zoom_start=zoom_level,
            tiles='CartoDB positron'
        )
        
        # Create separate layer for each assembly type
        for assembly_type in assembly_types:
            assembly_data = constituencies_data[
                constituencies_data['assembly_type'] == assembly_type
            ]
            
            if len(assembly_data) > 0:
                assembly_group = folium.FeatureGroup(
                    name=f"{assembly_type} ({len(assembly_data)} constituencies)"
                )
                
                color = self._get_assembly_color(assembly_type)
                
                # Add markers for this assembly type
                for _, row in assembly_data.iterrows():
                    if pd.notna(row.get('lat')) and pd.notna(row.get('lng')):
                        # Add marker
                        folium.CircleMarker(
                            location=[row['lat'], row['lng']],
                            radius=5,
                            color=color,
                            weight=1,
                            opacity=0.8,
                            fillColor=color,
                            fillOpacity=0.6,
                            popup=f"{row.get('constituency_en', 'Unknown')} ({assembly_type})",
                            tooltip=row.get('constituency_en', 'Unknown')
                        ).add_to(assembly_group)
                
                assembly_group.add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        return m
    
    def create_mimu_enhanced_map(
        self,
        constituencies_data: pd.DataFrame,
        highlight_tsp_codes: List[str] = None,
        center_coords: Tuple[float, float] = (21.9162, 95.9560),
        zoom_level: int = 7
    ) -> folium.Map:
        """Create a map with MIMU integration highlighting specific townships.
        
        Args:
            constituencies_data: DataFrame with constituency data
            highlight_tsp_codes: List of MIMU township codes to highlight
            center_coords: (lat, lng) for map center
            zoom_level: Initial zoom level
            
        Returns:
            Folium map with MIMU-enhanced visualization
        """
        m = folium.Map(
            location=center_coords,
            zoom_start=zoom_level,
            tiles='OpenStreetMap'
        )
        
        if self.mimu_boundaries:
            # Add all township boundaries (light style)
            normal_style = {
                'fillColor': 'lightgray',
                'color': 'gray',
                'weight': 1,
                'fillOpacity': 0.05,
                'opacity': 0.2
            }
            
            # Highlighted style for specific townships
            highlight_style = {
                'fillColor': 'yellow',
                'color': 'orange',
                'weight': 2,
                'fillOpacity': 0.3,
                'opacity': 0.8
            }
            
            for feature in self.mimu_boundaries.get('features', []):
                props = feature.get('properties', {})
                tsp_pcode = props.get('TS_PCODE', '')
                
                # Choose style based on whether township is highlighted
                style = highlight_style if (highlight_tsp_codes and tsp_pcode in highlight_tsp_codes) else normal_style
                
                folium.GeoJson(
                    feature,
                    style_function=lambda x, style=style: style,
                    tooltip=f"{props.get('TS', 'Unknown')} ({tsp_pcode})"
                ).add_to(m)
        
        # Add constituency pinpoints
        self._add_constituency_pinpoints_layer(m, constituencies_data, {}, True, 3)
        
        return m