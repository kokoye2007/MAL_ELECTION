#!/usr/bin/env python3
"""
Database connectivity for Myanmar Election Visualization
Handles PostgreSQL database operations and data loading.
"""

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine
import os
import streamlit as st
import json
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseConnector:
    """Database connection and data loading for Myanmar Election data."""
    
    def __init__(self):
        """Initialize database connection."""
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            # Heroku provides postgres:// but psycopg2 needs postgresql://
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            self.connection_string = database_url
            self.engine = create_engine(database_url)
        else:
            # Local development fallback
            self.connection_string = os.getenv(
                'DATABASE_URL', 
                'postgresql://election_user:dev_password_2025@postgres:5432/myanmar_election'
            )
            # Create SQLAlchemy engine for pandas compatibility
            password = os.getenv('POSTGRES_PASSWORD', 'election_dev_2025')
            self.engine = create_engine(f'postgresql://election_user:{password}@postgres:5432/myanmar_election')
        
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_constituencies(_self, assembly_types: Optional[List[str]] = None) -> pd.DataFrame:
        """Get constituency data from database.
        
        Args:
            assembly_types: List of assembly types to filter by (PTHT, AMTHT, TPHT, TPTYT)
            
        Returns:
            DataFrame with constituency data
        """
        try:
            # Build query
            query = """
                SELECT 
                    id, constituency_code, constituency_en, constituency_mm,
                    state_region_en, state_region_mm, assembly_type, electoral_system,
                    representatives, lat, lng, township_name_eng, township_name_mm,
                    constituency_areas_mm, tsp_pcode, boundary_codes,
                    coordinate_source, validation_status, election_year,
                    created_at, updated_at
                FROM constituencies 
                WHERE election_year = 2025
            """
            
            # For IN clauses, build query directly (SQLAlchemy has issues with list params)
            if assembly_types:
                # Safely escape assembly type values
                safe_types = [f"'{t}'" for t in assembly_types]
                query += f" AND assembly_type IN ({','.join(safe_types)})"
                
            query += " ORDER BY assembly_type, state_region_en, constituency_code"
            
            # No parameters needed since we're building the query directly
            df = pd.read_sql_query(query, _self.engine)
            
            # Post-process to ensure Naypyitaw constituencies have proper state regions
            df = _self._fix_naypyitaw_regions(df)
            
            return df
            
        except Exception as e:
            st.warning(f"Database connection error, using CSV fallback: {e}")
            return _self._load_csv_fallback(assembly_types)
    
    @st.cache_data(ttl=300)        
    def _load_csv_fallback(_self, assembly_types: Optional[List[str]] = None) -> pd.DataFrame:
        """Load data from CSV when database is unavailable."""
        try:
            # Try comprehensive data first (new), then legacy CSV
            csv_path = "/app/data/processed/myanmar_election_2025_complete.csv"
            if not os.path.exists(csv_path):
                csv_path = "data/processed/myanmar_election_2025_complete.csv"
            
            if not os.path.exists(csv_path):
                # Fallback to legacy CSV
                csv_path = "/app/data/processed/myanmar_constituencies.csv"
                if not os.path.exists(csv_path):
                    csv_path = "data/processed/myanmar_constituencies.csv"
            
            if not os.path.exists(csv_path):
                st.error("❌ No CSV data files found")
                return pd.DataFrame()
            
            df = pd.read_csv(csv_path)
            print(f"📊 Loaded {len(df)} constituencies from CSV fallback: {csv_path}")
            
            # Handle legacy CSV format if needed
            if 'assembly_type' in df.columns and df['assembly_type'].iloc[0] == 'pyithu':
                # This is legacy format, apply mapping
                assembly_mapping = {
                    'pyithu': 'PTHT',
                    'amyotha': 'AMTHT', 
                    'state_regional': 'TPHT'
                }
                df['assembly_type'] = df['assembly_type'].map(assembly_mapping).fillna(df['assembly_type'])
                print("🔄 Applied legacy assembly type mapping")
            
            # Add missing coordinate columns if not present
            if 'lat' not in df.columns and 'lng' not in df.columns:
                # This means we're using the new comprehensive data, need to add coordinates
                df['lat'] = None
                df['lng'] = None
                print("⚠️ New data format detected, coordinates will be populated from MIMU")
            
            # Filter by assembly types if specified
            if assembly_types:
                df = df[df['assembly_type'].isin(assembly_types)]
            
            # Post-process to ensure Naypyitaw constituencies have proper state regions
            df = _self._fix_naypyitaw_regions(df)
            
            st.info(f"📁 Using CSV data: {len(df)} constituencies loaded from {csv_path.split('/')[-1]}")
            return df
            
        except Exception as e:
            st.error(f"CSV fallback failed: {e}")
            return pd.DataFrame()
            
    @st.cache_data(ttl=300)
    def get_assembly_statistics(_self) -> Dict:
        """Get assembly statistics from database."""
        try:
            conn = psycopg2.connect(_self.connection_string)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Overall statistics
                cursor.execute("""
                    SELECT 
                        assembly_type,
                        electoral_system,
                        COUNT(*) as constituencies,
                        SUM(representatives) as total_representatives,
                        COUNT(CASE WHEN lat IS NOT NULL THEN 1 END) as mapped_count,
                        COUNT(CASE WHEN validation_status = 'verified' THEN 1 END) as verified_count
                    FROM constituencies 
                    WHERE election_year = 2025
                    GROUP BY assembly_type, electoral_system
                    ORDER BY assembly_type, electoral_system
                """)
                
                assembly_stats = cursor.fetchall()
                
                # Regional breakdown - with Naypyitaw fix
                cursor.execute("""
                    SELECT 
                        CASE 
                            WHEN state_region_en IS NULL OR state_region_en = '' OR state_region_en = 'Unknown State' THEN 'Naypyitaw Union Territory'
                            ELSE state_region_en
                        END as state_region_en,
                        assembly_type,
                        COUNT(*) as constituencies,
                        SUM(representatives) as representatives
                    FROM constituencies 
                    WHERE election_year = 2025
                    GROUP BY 
                        CASE 
                            WHEN state_region_en IS NULL OR state_region_en = '' OR state_region_en = 'Unknown State' THEN 'Naypyitaw Union Territory'
                            ELSE state_region_en
                        END,
                        assembly_type
                    ORDER BY state_region_en, assembly_type
                """)
                
                regional_stats = cursor.fetchall()
                
                # Coordinate source breakdown
                cursor.execute("""
                    SELECT 
                        coordinate_source,
                        COUNT(*) as count
                    FROM constituencies 
                    WHERE election_year = 2025 AND lat IS NOT NULL
                    GROUP BY coordinate_source
                    ORDER BY count DESC
                """)
                
                coordinate_stats = cursor.fetchall()
                
            conn.close()
            
            return {
                'assembly_breakdown': [dict(row) for row in assembly_stats],
                'regional_breakdown': [dict(row) for row in regional_stats],
                'coordinate_breakdown': [dict(row) for row in coordinate_stats],
                'total_constituencies': sum(row['constituencies'] for row in assembly_stats),
                'total_representatives': sum(row['total_representatives'] for row in assembly_stats),
                'mapped_constituencies': sum(row['mapped_count'] for row in assembly_stats)
            }
            
        except Exception as e:
            st.error(f"Database statistics error: {e}")
            return {}
            
    @st.cache_data(ttl=300)
    def get_states_regions(_self) -> List[str]:
        """Get list of all states and regions."""
        try:
            # Get all regions from database using raw SQL to avoid SQLAlchemy issues
            conn = psycopg2.connect(_self.connection_string)
            cursor = conn.cursor()
            
            # First get all valid regions
            cursor.execute("""
                SELECT DISTINCT state_region_en 
                FROM constituencies 
                WHERE election_year = 2025 
                    AND state_region_en IS NOT NULL 
                    AND state_region_en != ''
                    AND state_region_en != 'Unknown State'
                ORDER BY state_region_en
            """)
            
            regions = [row[0] for row in cursor.fetchall() if row[0] and row[0].strip()]
            
            # Check for Naypyitaw constituencies and ensure they're properly labeled
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM constituencies 
                WHERE election_year = 2025 
                    AND (LOWER(constituency_en) LIKE '%naypyitaw%' 
                         OR constituency_en LIKE '%သီရိ%' OR constituency_en LIKE '%တပ်ကုန်း%' OR constituency_en LIKE '%လယ်ဝေး%' 
                         OR constituency_mm LIKE '%သီရိ%' OR constituency_mm LIKE '%တပ်ကုန်း%' OR constituency_mm LIKE '%လယ်ဝေး%'
                         OR constituency_mm LIKE '%ပုဗ္ဗ%' OR constituency_mm LIKE '%ဇေယျာ%' OR constituency_mm LIKE '%ဇမ္ဗူ%'
                         OR constituency_mm LIKE '%ဒက္ခိဏ%' OR constituency_mm LIKE '%ဥတ္တရ%' OR constituency_mm LIKE '%ပျဉ်းမနား%'
                         OR constituency_mm LIKE '%တက္ကုန်း%')
            """)
            
            naypyitaw_count = cursor.fetchone()[0]
            
            if naypyitaw_count > 0 and 'Naypyitaw Union Territory' not in regions:
                regions.append('Naypyitaw Union Territory')
            
            cursor.close()
            conn.close()
            
            # Sort the regions and ensure no None/empty values
            regions = sorted([r for r in regions if r and r.strip()])
            return regions
            
        except Exception as e:
            st.warning(f"Database regions error, using CSV fallback: {e}")
            return _self._get_states_regions_from_csv()
    
    def _fix_naypyitaw_regions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fix Naypyitaw constituencies that have missing or incorrect state regions."""
        if df.empty:
            return df
        
        # Comprehensive Naypyitaw indicators
        naypyitaw_indicators = [
            'naypyitaw', 'ပြည်ထောင်စု', 'သီရိ', 'တပ်ကုန်း', 'တက္ကုန်း', 'လယ်ဝေး', 
            'ပုဗ္ဗ', 'ဇေယျာ', 'ဇမ္ဗူ', 'ဒက္ခိဏ', 'ဥတ္တရ', 'ပျဉ်းမနား',
            'tatkon', 'ottara', 'thiri', 'pyinmana', 'dakkhin', 'zabbu', 'zeyya', 'pobba', 'lewe'
        ]
        
        # Find Naypyitaw constituencies
        for idx, row in df.iterrows():
            constituency_en = str(row.get('constituency_en', '')).lower()
            constituency_mm = str(row.get('constituency_mm', ''))
            state_region = row.get('state_region_en', '')
            
            # Check if this is a Naypyitaw constituency
            is_naypyitaw = (
                any(indicator in constituency_en for indicator in naypyitaw_indicators) or
                any(indicator in constituency_mm for indicator in naypyitaw_indicators)
            )
            
            # If it's a Naypyitaw constituency but doesn't have proper state region, fix it
            if is_naypyitaw and (pd.isna(state_region) or not str(state_region).strip() or state_region == 'Unknown State'):
                df.at[idx, 'state_region_en'] = 'Naypyitaw Union Territory'
                df.at[idx, 'state_region_mm'] = 'ပြည်ထောင်စုနယ်မြေ'
        
        return df
    
    def _get_states_regions_from_csv(self) -> List[str]:
        """Get states/regions from CSV when database is unavailable."""
        try:
            # Load data from CSV using the same logic as get_constituencies
            csv_path = "/app/data/processed/myanmar_election_2025_complete.csv"
            if not os.path.exists(csv_path):
                csv_path = "data/processed/myanmar_election_2025_complete.csv"
            
            if not os.path.exists(csv_path):
                # Fallback to legacy CSV
                csv_path = "/app/data/processed/myanmar_constituencies.csv"
                if not os.path.exists(csv_path):
                    csv_path = "data/processed/myanmar_constituencies.csv"
            
            if not os.path.exists(csv_path):
                return []
            
            df = pd.read_csv(csv_path)
            
            # Apply the same Naypyitaw fix
            df = self._fix_naypyitaw_regions(df)
            
            # Get unique regions, excluding NaN/empty values
            regions = df['state_region_en'].dropna().unique().tolist()
            regions = [r for r in regions if r and str(r).strip() and str(r) != 'Unknown State']
            
            # Sort and return
            return sorted(regions)
            
        except Exception as e:
            st.error(f"CSV regions fallback error: {e}")
            return []
            
    @st.cache_data(ttl=300)
    def get_historical_constituencies(_self, election_year: int = 2020, assembly_types: Optional[List[str]] = None) -> pd.DataFrame:
        """Get historical constituency data from database.
        
        Args:
            election_year: Election year to fetch (default 2020)
            assembly_types: List of assembly types to filter by
            
        Returns:
            DataFrame with historical constituency data
        """
        try:
            conn = psycopg2.connect(_self.connection_string)
            
            # Build query
            query = """
                SELECT 
                    id, constituency_code, constituency_en, constituency_mm,
                    state_region_en, state_region_mm, assembly_type,
                    representatives, lat, lng, areas_included_en, election_year,
                    created_at
                FROM historical_constituencies 
                WHERE election_year = %s
            """
            
            # Use SQLAlchemy parameter binding
            params = {'year': election_year}
            query = query.replace('%s', ':year')
            
            if assembly_types:
                # Create named parameters for SQLAlchemy
                placeholders = ','.join([f':type{i}' for i in range(len(assembly_types))])
                query += f" AND assembly_type IN ({placeholders})"
                
                # Add assembly type parameters
                for i, assembly_type in enumerate(assembly_types):
                    params[f'type{i}'] = assembly_type
                
            query += " ORDER BY assembly_type, state_region_en, constituency_code"
            
            df = pd.read_sql_query(query, _self.engine, params=params)
            return df
            
        except Exception as e:
            st.error(f"Historical data connection error: {e}")
            return pd.DataFrame()
    
    @st.cache_data(ttl=300)
    def get_historical_statistics(_self, election_year: int = 2020) -> Dict:
        """Get historical election statistics.
        
        Args:
            election_year: Election year to analyze
            
        Returns:
            Dictionary with historical statistics
        """
        try:
            conn = psycopg2.connect(_self.connection_string)
            
            # Check for cached statistics first
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT data FROM cached_statistics 
                    WHERE cache_key = %s AND election_year = %s
                """, (f'historical_summary_{election_year}', election_year))
                
                cached_result = cursor.fetchone()
                if cached_result:
                    conn.close()
                    return cached_result['data']
                
                # Calculate statistics if not cached
                cursor.execute("""
                    SELECT 
                        assembly_type,
                        COUNT(*) as constituencies,
                        SUM(representatives) as total_representatives,
                        COUNT(CASE WHEN lat IS NOT NULL THEN 1 END) as mapped_count
                    FROM historical_constituencies 
                    WHERE election_year = %s
                    GROUP BY assembly_type
                    ORDER BY assembly_type
                """, (election_year,))
                
                assembly_stats = cursor.fetchall()
                
                # Regional breakdown
                cursor.execute("""
                    SELECT 
                        state_region_en,
                        state_region_mm,
                        assembly_type,
                        COUNT(*) as constituencies,
                        SUM(representatives) as representatives
                    FROM historical_constituencies 
                    WHERE election_year = %s
                    GROUP BY state_region_en, state_region_mm, assembly_type
                    ORDER BY state_region_en, assembly_type
                """, (election_year,))
                
                regional_stats = cursor.fetchall()
                
            conn.close()
            
            return {
                'election_year': election_year,
                'assembly_breakdown': [dict(row) for row in assembly_stats],
                'regional_breakdown': [dict(row) for row in regional_stats],
                'total_constituencies': sum(row['constituencies'] for row in assembly_stats),
                'total_representatives': sum(row['total_representatives'] for row in assembly_stats),
                'mapped_constituencies': sum(row['mapped_count'] for row in assembly_stats)
            }
            
        except Exception as e:
            st.error(f"Historical statistics error: {e}")
            return {}
    
    @st.cache_data(ttl=300)
    def compare_elections(_self, base_year: int = 2020, compare_year: int = 2025) -> Dict:
        """Compare constituency data between two elections.
        
        Args:
            base_year: Base election year for comparison
            compare_year: Comparison election year
            
        Returns:
            Dictionary with comparison data
        """
        try:
            conn = psycopg2.connect(_self.connection_string)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Historical data
                cursor.execute("""
                    SELECT 
                        state_region_en,
                        COUNT(*) as constituencies_historical,
                        SUM(representatives) as representatives_historical
                    FROM historical_constituencies 
                    WHERE election_year = %s
                    GROUP BY state_region_en
                    ORDER BY state_region_en
                """, (base_year,))
                
                historical_data = {row['state_region_en']: dict(row) for row in cursor.fetchall()}
                
                # Current data - with Naypyitaw fix
                cursor.execute("""
                    SELECT 
                        CASE 
                            WHEN state_region_en IS NULL OR state_region_en = '' OR state_region_en = 'Unknown State' THEN 'Naypyitaw Union Territory'
                            ELSE state_region_en
                        END as state_region_en,
                        COUNT(*) as constituencies_current,
                        SUM(representatives) as representatives_current
                    FROM constituencies 
                    WHERE election_year = %s
                    GROUP BY 
                        CASE 
                            WHEN state_region_en IS NULL OR state_region_en = '' OR state_region_en = 'Unknown State' THEN 'Naypyitaw Union Territory'
                            ELSE state_region_en
                        END
                    ORDER BY state_region_en
                """, (compare_year,))
                
                current_data = {row['state_region_en']: dict(row) for row in cursor.fetchall()}
                
            conn.close()
            
            # Merge and calculate differences
            comparison = []
            all_regions = set(historical_data.keys()) | set(current_data.keys())
            
            for region in sorted(all_regions):
                hist = historical_data.get(region, {'constituencies_historical': 0, 'representatives_historical': 0})
                curr = current_data.get(region, {'constituencies_current': 0, 'representatives_current': 0})
                
                comparison.append({
                    'state_region_en': region,
                    'constituencies_2020': hist['constituencies_historical'],
                    'constituencies_2025': curr['constituencies_current'],
                    'constituencies_change': curr['constituencies_current'] - hist['constituencies_historical'],
                    'representatives_2020': hist['representatives_historical'],
                    'representatives_2025': curr['representatives_current'],
                    'representatives_change': curr['representatives_current'] - hist['representatives_historical']
                })
            
            return {
                'base_year': base_year,
                'compare_year': compare_year,
                'regional_comparison': comparison,
                'summary': {
                    'total_constituencies_change': sum(c['constituencies_change'] for c in comparison),
                    'total_representatives_change': sum(c['representatives_change'] for c in comparison)
                }
            }
            
        except Exception as e:
            st.error(f"Election comparison error: {e}")
            return {}
    
    @st.cache_data(ttl=300)
    def search_constituencies(_self, search_term: str) -> pd.DataFrame:
        """Search constituencies by name or region.
        
        Args:
            search_term: Search term in English or Myanmar
            
        Returns:
            DataFrame with matching constituencies
        """
        try:
            query = """
                SELECT 
                    constituency_code, constituency_en, constituency_mm,
                    state_region_en, state_region_mm, assembly_type,
                    electoral_system, representatives, lat, lng
                FROM constituencies 
                WHERE election_year = 2025
                AND (
                    constituency_en ILIKE %(pattern)s OR 
                    constituency_mm LIKE %(pattern)s OR
                    state_region_en ILIKE %(pattern)s OR
                    state_region_mm LIKE %(pattern)s OR
                    areas_included_en ILIKE %(pattern)s OR
                    areas_included_mm LIKE %(pattern)s
                )
                ORDER BY assembly_type, state_region_en, constituency_en
            """
            
            search_pattern = f"%{search_term}%"
            params = {'pattern': search_pattern}
            
            df = pd.read_sql_query(query, _self.engine, params=params)
            return df
            
        except Exception as e:
            st.error(f"Database search error: {e}")
            return pd.DataFrame()
            
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            conn = psycopg2.connect(self.connection_string)
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM constituencies WHERE election_year = 2025")
                count = cursor.fetchone()[0]
            conn.close()
            
            st.success(f"✅ Database connected successfully! Found {count} constituencies.")
            return True
            
        except Exception as e:
            st.error(f"❌ Database connection failed: {e}")
            return False

# Global database instance
@st.cache_resource
def get_database():
    """Get cached database connector instance."""
    return DatabaseConnector()