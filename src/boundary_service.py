#!/usr/bin/env python3
"""
Myanmar Boundary Service
Integrates with GeoNode API to fetch administrative boundary data
"""

import json
import logging
import requests
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from functools import lru_cache
import time

logger = logging.getLogger(__name__)


class GeoNodeBoundaryService:
    """Service for fetching boundary data from Myanmar GeoNode"""
    
    def __init__(self, cache_dir: Path = None):
        """Initialize the boundary service
        
        Args:
            cache_dir: Directory to cache boundary data
        """
        self.base_url = "https://geonode.themimu.info"
        self.api_url = f"{self.base_url}/api/v2"
        self.cache_dir = cache_dir or Path("data/boundaries")
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        
        # Cache for loaded boundaries
        self._boundary_cache = {}
        
    def search_boundaries(self, 
                         category: str = "boundaries",
                         limit: int = 100) -> List[Dict]:
        """Search for boundary datasets
        
        Args:
            category: Category to filter (e.g., 'boundaries')
            limit: Maximum results to return
            
        Returns:
            List of boundary datasets
        """
        try:
            # Check cache first
            cache_file = self.cache_dir / f"boundary_list_{category}.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    return json.load(f)
            
            # Fetch from API
            params = {
                "limit": limit,
                "offset": 0,
                "category__identifier__in": category
            }
            
            response = requests.get(
                f"{self.api_url}/layers",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            layers = data.get("objects", [])
            
            # Cache the results
            with open(cache_file, 'w') as f:
                json.dump(layers, f, indent=2)
                
            logger.info(f"Found {len(layers)} boundary layers")
            return layers
            
        except Exception as e:
            logger.error(f"Error searching boundaries: {e}")
            return []
    
    def get_township_boundaries(self) -> Optional[Dict]:
        """Get Myanmar township boundaries
        
        Returns:
            GeoJSON with township boundaries
        """
        # Look for township boundary layers
        layers = self.search_boundaries()
        
        township_layers = [
            layer for layer in layers
            if "township" in layer.get("title", "").lower() or
               "tsp" in layer.get("title", "").lower()
        ]
        
        if not township_layers:
            logger.warning("No township boundary layers found")
            return None
            
        # Use the first matching layer
        layer = township_layers[0]
        layer_id = layer.get("id")
        
        return self.get_layer_data(layer_id)
    
    def get_layer_data(self, layer_id: int) -> Optional[Dict]:
        """Fetch actual GeoJSON data for a layer
        
        Args:
            layer_id: ID of the layer
            
        Returns:
            GeoJSON data
        """
        try:
            # Check cache
            cache_file = self.cache_dir / f"layer_{layer_id}.geojson"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    return json.load(f)
            
            # Get layer details
            response = requests.get(
                f"{self.api_url}/layers/{layer_id}",
                timeout=30
            )
            response.raise_for_status()
            
            layer_data = response.json()
            
            # Get download links
            links = layer_data.get("links", [])
            geojson_link = None
            
            for link in links:
                if link.get("mime") == "application/json" or \
                   link.get("link_type") == "geojson":
                    geojson_link = link.get("url")
                    break
            
            if not geojson_link:
                logger.warning(f"No GeoJSON link found for layer {layer_id}")
                return None
            
            # Download GeoJSON
            response = requests.get(geojson_link, timeout=60)
            response.raise_for_status()
            
            geojson_data = response.json()
            
            # Cache the data
            with open(cache_file, 'w') as f:
                json.dump(geojson_data, f)
                
            logger.info(f"Downloaded layer {layer_id} with {len(geojson_data.get('features', []))} features")
            return geojson_data
            
        except Exception as e:
            logger.error(f"Error fetching layer {layer_id}: {e}")
            return None
    
    @lru_cache(maxsize=1000)
    def get_boundary_for_pcode(self, pcode: str) -> Optional[Dict]:
        """Get boundary geometry for a specific Pcode
        
        Args:
            pcode: Township Pcode (e.g., MMR001005)
            
        Returns:
            GeoJSON feature for the township
        """
        # Load township boundaries if not cached
        if "townships" not in self._boundary_cache:
            township_data = self.get_township_boundaries()
            if township_data:
                # Index by Pcode
                pcode_index = {}
                for feature in township_data.get("features", []):
                    props = feature.get("properties", {})
                    # Try different Pcode field names
                    for field in ["TS_PCODE", "Tsp_Pcode", "PCODE", "pcode"]:
                        if field in props:
                            pcode_index[props[field]] = feature
                            break
                            
                self._boundary_cache["townships"] = pcode_index
                logger.info(f"Indexed {len(pcode_index)} townships by Pcode")
        
        # Return boundary for specific Pcode
        townships = self._boundary_cache.get("townships", {})
        return townships.get(pcode)
    
    def merge_boundaries(self, pcodes: List[str]) -> Optional[Dict]:
        """Merge multiple township boundaries
        
        Args:
            pcodes: List of township Pcodes
            
        Returns:
            Merged GeoJSON feature
        """
        features = []
        for pcode in pcodes:
            feature = self.get_boundary_for_pcode(pcode)
            if feature:
                features.append(feature)
        
        if not features:
            return None
        
        if len(features) == 1:
            return features[0]
        
        # Simple merge - combine all features into a FeatureCollection
        # In production, you'd want to merge the actual geometries
        merged = {
            "type": "FeatureCollection",
            "features": features
        }
        
        return merged
    
    def get_state_boundaries(self) -> Optional[Dict]:
        """Get Myanmar state/region boundaries
        
        Returns:
            GeoJSON with state boundaries
        """
        # Look for state/region boundary layers
        layers = self.search_boundaries()
        
        state_layers = [
            layer for layer in layers
            if ("state" in layer.get("title", "").lower() or
                "region" in layer.get("title", "").lower()) and
               "township" not in layer.get("title", "").lower()
        ]
        
        if not state_layers:
            logger.warning("No state boundary layers found")
            return None
        
        layer = state_layers[0]
        return self.get_layer_data(layer.get("id"))
    
    def download_all_boundaries(self) -> Dict[str, int]:
        """Download all available boundary layers
        
        Returns:
            Dictionary with download statistics
        """
        stats = {
            "total_layers": 0,
            "downloaded": 0,
            "failed": 0
        }
        
        layers = self.search_boundaries()
        stats["total_layers"] = len(layers)
        
        for layer in layers:
            layer_id = layer.get("id")
            title = layer.get("title", "Unknown")
            
            logger.info(f"Downloading: {title}")
            
            try:
                data = self.get_layer_data(layer_id)
                if data:
                    stats["downloaded"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                logger.error(f"Failed to download {title}: {e}")
                stats["failed"] += 1
            
            # Be polite to the server
            time.sleep(1)
        
        return stats


class BoundaryMatcher:
    """Matches constituencies to boundary geometries"""
    
    def __init__(self, boundary_service: GeoNodeBoundaryService):
        self.boundary_service = boundary_service
        self.match_cache = {}
        
    def match_constituency(self, 
                          tsp_pcode: str,
                          constituency_name: str = None) -> Optional[Dict]:
        """Match a constituency to its boundary
        
        Args:
            tsp_pcode: Township Pcode
            constituency_name: Optional constituency name for verification
            
        Returns:
            Matched boundary feature
        """
        # Check cache
        cache_key = f"{tsp_pcode}_{constituency_name}"
        if cache_key in self.match_cache:
            return self.match_cache[cache_key]
        
        # Handle multiple Pcodes (constituencies spanning multiple townships)
        if "+" in tsp_pcode:
            pcodes = tsp_pcode.split("+")
            boundary = self.boundary_service.merge_boundaries(pcodes)
        else:
            boundary = self.boundary_service.get_boundary_for_pcode(tsp_pcode)
        
        # Cache result
        self.match_cache[cache_key] = boundary
        
        return boundary
    
    def calculate_centroid(self, geometry: Dict) -> Tuple[float, float]:
        """Calculate centroid of a geometry
        
        Args:
            geometry: GeoJSON geometry
            
        Returns:
            Tuple of (longitude, latitude)
        """
        if geometry.get("type") == "Point":
            coords = geometry.get("coordinates", [])
            return coords[0], coords[1]
        
        elif geometry.get("type") == "Polygon":
            # Simple centroid calculation
            coords = geometry.get("coordinates", [[]])[0]
            if not coords:
                return None, None
                
            lngs = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            
            return sum(lngs) / len(lngs), sum(lats) / len(lats)
        
        elif geometry.get("type") == "MultiPolygon":
            # Average of polygon centroids
            centroids = []
            for polygon in geometry.get("coordinates", []):
                if polygon and polygon[0]:
                    lngs = [c[0] for c in polygon[0]]
                    lats = [c[1] for c in polygon[0]]
                    centroids.append((
                        sum(lngs) / len(lngs),
                        sum(lats) / len(lats)
                    ))
            
            if centroids:
                avg_lng = sum(c[0] for c in centroids) / len(centroids)
                avg_lat = sum(c[1] for c in centroids) / len(centroids)
                return avg_lng, avg_lat
        
        return None, None


def main():
    """Test the boundary service"""
    service = GeoNodeBoundaryService()
    
    # Search for boundaries
    print("Searching for boundary layers...")
    layers = service.search_boundaries()
    
    print(f"\nFound {len(layers)} boundary layers:")
    for layer in layers[:5]:  # Show first 5
        print(f"  - {layer.get('title')}")
    
    # Get township boundaries
    print("\nFetching township boundaries...")
    townships = service.get_township_boundaries()
    if townships:
        features = townships.get("features", [])
        print(f"  Loaded {len(features)} township features")
        
        # Test Pcode lookup
        if features:
            first_feature = features[0]
            props = first_feature.get("properties", {})
            print(f"  Sample township: {props}")
    
    # Test boundary matching
    matcher = BoundaryMatcher(service)
    
    # Test with a sample Pcode
    test_pcode = "MMR001005"
    print(f"\nTesting boundary match for {test_pcode}...")
    boundary = matcher.match_constituency(test_pcode)
    if boundary:
        print(f"  Found boundary for {test_pcode}")
        geometry = boundary.get("geometry")
        if geometry:
            lng, lat = matcher.calculate_centroid(geometry)
            print(f"  Centroid: {lng:.4f}, {lat:.4f}")


if __name__ == "__main__":
    main()