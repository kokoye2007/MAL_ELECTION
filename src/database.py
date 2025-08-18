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
                    representatives, lat, lng, areas_included_en, areas_included_mm,
                    ethnic_group, coordinate_source, validation_status, election_year,
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
            
            return df
            
        except Exception as e:
            st.error(f"Database connection error: {e}")
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
                
                # Regional breakdown
                cursor.execute("""
                    SELECT 
                        state_region_en,
                        assembly_type,
                        COUNT(*) as constituencies,
                        SUM(representatives) as representatives
                    FROM constituencies 
                    WHERE election_year = 2025
                    GROUP BY state_region_en, assembly_type
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
            df = pd.read_sql_query("""
                SELECT DISTINCT state_region_en 
                FROM constituencies 
                WHERE election_year = 2025 
                ORDER BY state_region_en
            """, _self.engine)
            return df['state_region_en'].tolist()
            
        except Exception as e:
            st.error(f"Database regions error: {e}")
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
                
                # Current data
                cursor.execute("""
                    SELECT 
                        state_region_en,
                        COUNT(*) as constituencies_current,
                        SUM(representatives) as representatives_current
                    FROM constituencies 
                    WHERE election_year = %s
                    GROUP BY state_region_en
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