#!/usr/bin/env python3
"""
Boundary Renderer for Myanmar Election Maps
Handles GeoJSON boundary loading, styling, and performance optimization
"""

import streamlit as st
import folium
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import gc

logger = logging.getLogger(__name__)


class BoundaryRenderer:
    """Handles boundary polygon rendering for Myanmar election maps"""
    
    def __init__(self, geojson_dir: Path = None):
        """Initialize boundary renderer
        
        Args:
            geojson_dir: Directory containing GeoJSON boundary files
        """
        self.geojson_dir = geojson_dir or Path("data/geojson")
        self.township_boundaries_path = self.geojson_dir / "myanmar_townships_mimu.geojson"
        self.state_boundaries_path = self.geojson_dir / "myanmar_gadm.json"
        
        # Boundary styling configuration
        self.boundary_styles = {
            'township': {
                'color': '#2E86AB',
                'weight': 1,
                'fillOpacity': 0.1,
                'opacity': 0.6
            },
            'state': {
                'color': '#A23B72', 
                'weight': 2,
                'fillOpacity': 0.05,
                'opacity': 0.8
            }
        }
    
    @st.cache_data(ttl=600)  # Cache for 10 minutes
    def load_township_boundaries(_self) -> Dict:
        """Load township boundary GeoJSON with caching
        
        Returns:
            Dictionary containing GeoJSON data
        """
        try:
            if not _self.township_boundaries_path.exists():
                logger.warning(f"Township boundaries not found: {_self.township_boundaries_path}")
                return {}
                
            with open(_self.township_boundaries_path, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
            
            logger.info(f"Loaded {len(geojson_data.get('features', []))} township boundaries")
            return geojson_data
            
        except Exception as e:
            logger.error(f"Failed to load township boundaries: {e}")
            return {}
    
    @st.cache_data(ttl=600)
    def load_state_boundaries(_self) -> Dict:
        """Load state/region boundary GeoJSON with caching
        
        Returns:
            Dictionary containing GeoJSON data
        """
        try:
            if not _self.state_boundaries_path.exists():
                logger.warning(f"State boundaries not found: {_self.state_boundaries_path}")
                return {}
                
            with open(_self.state_boundaries_path, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
            
            logger.info(f"Loaded {len(geojson_data.get('features', []))} state boundaries")
            return geojson_data
            
        except Exception as e:
            logger.error(f"Failed to load state boundaries: {e}")
            return {}
    
    def optimize_geojson_for_zoom(self, geojson_data: Dict, zoom_level: int) -> Dict:
        """Optimize GeoJSON based on zoom level to improve performance
        
        Args:
            geojson_data: Original GeoJSON data
            zoom_level: Current map zoom level
            
        Returns:
            Optimized GeoJSON data
        """
        if not geojson_data or zoom_level < 8:
            # Don't show detailed boundaries at country/regional level
            return {}
        
        # For zoom levels 8-12, show simplified boundaries
        if zoom_level < 12:
            return self._simplify_geojson(geojson_data, tolerance=0.01)
        elif zoom_level < 15:
            return self._simplify_geojson(geojson_data, tolerance=0.005)
            
        return geojson_data
    
    def _simplify_geojson(self, geojson_data: Dict, tolerance: float = 0.01) -> Dict:
        """Simplify GeoJSON coordinates to reduce file size
        
        Args:
            geojson_data: Original GeoJSON
            tolerance: Simplification tolerance (higher = more simplified)
            
        Returns:
            Simplified GeoJSON
        """
        if not geojson_data or not geojson_data.get('features'):
            return geojson_data
            
        simplified_features = []
        
        for feature in geojson_data['features']:
            geometry = feature.get('geometry', {})
            if geometry.get('type') == 'Polygon':
                # Simplify polygon coordinates
                coords = geometry.get('coordinates', [])
                if coords:
                    simplified_coords = [
                        self._douglas_peucker(ring, tolerance) 
                        for ring in coords
                    ]
                    feature = feature.copy()
                    feature['geometry'] = {
                        'type': 'Polygon',
                        'coordinates': simplified_coords
                    }
            elif geometry.get('type') == 'MultiPolygon':
                # Simplify multipolygon coordinates
                coords = geometry.get('coordinates', [])
                if coords:
                    simplified_coords = [
                        [self._douglas_peucker(ring, tolerance) for ring in polygon]
                        for polygon in coords
                    ]
                    feature = feature.copy()
                    feature['geometry'] = {
                        'type': 'MultiPolygon', 
                        'coordinates': simplified_coords
                    }
            
            simplified_features.append(feature)
        
        return {
            'type': 'FeatureCollection',
            'features': simplified_features
        }
    
    def _douglas_peucker(self, points: List, tolerance: float) -> List:
        """Douglas-Peucker line simplification algorithm
        
        Args:
            points: List of [lng, lat] coordinate pairs
            tolerance: Simplification tolerance
            
        Returns:
            Simplified coordinate list
        """
        if len(points) <= 2:
            return points
        
        # Find the point with maximum distance from line
        max_dist = 0
        index = 0
        
        for i in range(1, len(points) - 1):
            dist = self._perpendicular_distance(points[i], points[0], points[-1])
            if dist > max_dist:
                max_dist = dist
                index = i
        
        # If max distance is greater than tolerance, recursively simplify
        if max_dist > tolerance:
            # Recursive call
            left = self._douglas_peucker(points[:index + 1], tolerance)
            right = self._douglas_peucker(points[index:], tolerance)
            
            # Merge results, removing duplicate point
            return left[:-1] + right
        else:
            # If within tolerance, return just endpoints
            return [points[0], points[-1]]
    
    def _perpendicular_distance(self, point: List, line_start: List, line_end: List) -> float:
        """Calculate perpendicular distance from point to line
        
        Args:
            point: [lng, lat] coordinate
            line_start: Line start [lng, lat]
            line_end: Line end [lng, lat]
            
        Returns:
            Perpendicular distance
        """
        if line_start[0] == line_end[0] and line_start[1] == line_end[1]:
            # Line is actually a point
            return ((point[0] - line_start[0]) ** 2 + (point[1] - line_start[1]) ** 2) ** 0.5
        
        # Calculate perpendicular distance using cross product
        x0, y0 = point[0], point[1]
        x1, y1 = line_start[0], line_start[1] 
        x2, y2 = line_end[0], line_end[1]
        
        # Distance formula
        numerator = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
        denominator = ((y2 - y1) ** 2 + (x2 - x1) ** 2) ** 0.5
        
        return numerator / denominator if denominator > 0 else 0
    
    def add_township_boundaries(self, 
                               map_obj: folium.Map, 
                               zoom_level: int = 10,
                               constituency_data: pd.DataFrame = None,
                               opacity: float = 0.6) -> None:
        """Add township boundary layer to map
        
        Args:
            map_obj: Folium map object to add boundaries to
            zoom_level: Current zoom level for optimization
            constituency_data: Constituency data for matching
        """
        # Only show township boundaries at appropriate zoom levels
        if zoom_level < 8:
            return
            
        boundaries = self.load_township_boundaries()
        if not boundaries:
            return
            
        # Optimize for zoom level and memory usage
        optimized_boundaries = self.optimize_geojson_for_zoom(boundaries, zoom_level)
        if not optimized_boundaries:
            return
        
        # Free original boundaries from memory
        del boundaries
        gc.collect()
        
        # Create boundary feature group
        boundary_group = folium.FeatureGroup(name="Township Boundaries", show=False)
        
        try:
            # Add GeoJSON layer with styling
            township_style = self.boundary_styles['township'].copy()
            township_style['opacity'] = opacity
            
            folium.GeoJson(
                optimized_boundaries,
                style_function=lambda feature: township_style,
                popup=folium.GeoJsonPopup(
                    fields=['TS', 'TS_MMR', 'DT', 'ST'],
                    aliases=['Township (EN)', 'Township (MM)', 'District', 'State/Region'],
                    labels=True,
                    max_width=300
                ),
                tooltip=folium.GeoJsonTooltip(
                    fields=['TS', 'TS_MMR'],
                    aliases=['Township:', 'မြို့နယ်:'],
                    labels=True
                ),
                show=False  # Start hidden to avoid conflicts
            ).add_to(boundary_group)
            
            # Add to map (layer control managed centrally)
            boundary_group.add_to(map_obj)
            logger.info(f"Added township boundaries at zoom level {zoom_level}")
            
        except Exception as e:
            logger.error(f"Failed to add township boundaries: {e}")
    
    def add_state_boundaries(self, 
                            map_obj: folium.Map,
                            zoom_level: int = 6) -> None:
        """Add state/region boundary layer to map
        
        Args:
            map_obj: Folium map object to add boundaries to
            zoom_level: Current zoom level for optimization
        """
        boundaries = self.load_state_boundaries()
        if not boundaries:
            return
        
        # Create boundary feature group
        boundary_group = folium.FeatureGroup(name="State/Region Boundaries", show=True)
        
        try:
            # Add GeoJSON layer with styling
            folium.GeoJson(
                boundaries,
                style_function=lambda feature: self.boundary_styles['state'],
                popup=folium.GeoJsonPopup(
                    fields=['NAME_1'],
                    aliases=['State/Region'], 
                    labels=True,
                    max_width=250
                ),
                tooltip=folium.GeoJsonTooltip(
                    fields=['NAME_1'],
                    aliases=['State/Region:'],
                    labels=True
                ),
                show=True  # Show state boundaries by default
            ).add_to(boundary_group)
            
            # Add to map (layer control managed centrally)
            boundary_group.add_to(map_obj)
            logger.info(f"Added state boundaries at zoom level {zoom_level}")
            
        except Exception as e:
            logger.error(f"Failed to add state boundaries: {e}")
    
    def get_constituency_boundary(self, tsp_pcode: str) -> Optional[Dict]:
        """Get specific boundary for a constituency by township code
        
        Args:
            tsp_pcode: Township PCODE to match
            
        Returns:
            Boundary feature if found
        """
        boundaries = self.load_township_boundaries()
        if not boundaries:
            return None
            
        # Find matching township boundary
        for feature in boundaries.get('features', []):
            properties = feature.get('properties', {})
            if properties.get('TS_PCODE') == tsp_pcode:
                return feature
                
        return None
    
    def add_constituency_highlight(self, 
                                  map_obj: folium.Map,
                                  tsp_pcode: str,
                                  highlight_color: str = '#FF6B6B') -> bool:
        """Highlight specific constituency boundary
        
        Args:
            map_obj: Folium map object
            tsp_pcode: Township code to highlight
            highlight_color: Color for highlighting
            
        Returns:
            True if boundary was found and highlighted
        """
        boundary = self.get_constituency_boundary(tsp_pcode)
        if not boundary:
            return False
            
        # Add highlighted boundary
        folium.GeoJson(
            boundary,
            style_function=lambda feature: {
                'color': highlight_color,
                'weight': 3,
                'fillOpacity': 0.3,
                'opacity': 1.0
            }
        ).add_to(map_obj)
        
        return True