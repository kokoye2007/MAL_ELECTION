#!/usr/bin/env python3
"""
Political Parties Page for Myanmar Election 2025
Displays UEC party data with filtering, search, and color coding
"""

import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from typing import Dict, List, Any

def load_party_data() -> Dict[str, Any]:
    """Load political parties data from JSON."""
    try:
        data_path = Path(__file__).parent.parent / 'data' / 'processed' / 'myanmar_2025_political_parties.json'
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Party data not found. Please run convert_uec_parties.py first.")
        return {}

def get_party_color(party_type: str) -> str:
    """Get color for party type."""
    colors = {
        'existing': '#2E86AB',  # Blue - active parties
        'allowed_to_register': '#F18F01',  # Orange - registered for 2025
        'canceled': '#C73E1D'  # Red - canceled parties
    }
    return colors.get(party_type, '#666666')

def create_parties_overview(party_data: Dict[str, Any]) -> None:
    """Create overview section with summary statistics."""
    st.subheader("🏛️ Political Parties Overview")
    
    if not party_data or 'summary' not in party_data:
        st.warning("No party data available")
        return
    
    summary = party_data['summary']
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📋 Existing Parties",
            value=summary['total_existing'],
            help="Currently active political parties"
        )
    
    with col2:
        st.metric(
            label="📝 Allowed to Register",
            value=summary['total_allowed_to_register'],
            help="Parties allowed to register for 2025 election"
        )
    
    with col3:
        st.metric(
            label="❌ Canceled Parties",
            value=summary['total_canceled'],
            help="Previously registered but canceled parties"
        )
    
    with col4:
        st.metric(
            label="📊 Total Parties",
            value=summary['total_all_parties'],
            help="All parties across all categories"
        )

def create_party_distribution_chart(party_data: Dict[str, Any]) -> None:
    """Create party distribution visualization."""
    if not party_data or 'summary' not in party_data:
        return
    
    summary = party_data['summary']
    
    # Pie chart of party distribution
    fig = go.Figure(data=[go.Pie(
        labels=['Existing', 'Allowed to Register', 'Canceled'],
        values=[
            summary['total_existing'],
            summary['total_allowed_to_register'],
            summary['total_canceled']
        ],
        marker_colors=['#2E86AB', '#F18F01', '#C73E1D'],
        textinfo='label+percent+value',
        hole=0.3
    )])
    
    fig.update_layout(
        title="Party Distribution by Status",
        height=400,
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_party_search_and_filter(party_data: Dict[str, Any]) -> pd.DataFrame:
    """Create search and filter interface, return filtered dataframe."""
    if not party_data or 'parties' not in party_data:
        return pd.DataFrame()
    
    st.subheader("🔍 Search & Filter Parties")
    
    # Create combined dataframe
    all_parties = []
    for party_type, parties in party_data['parties'].items():
        for party in parties:
            party_info = party.copy()
            party_info['type'] = party_type
            all_parties.append(party_info)
    
    if not all_parties:
        st.warning("No party data available")
        return pd.DataFrame()
    
    df = pd.DataFrame(all_parties)
    
    # Search and filter controls
    col1, col2 = st.columns(2)
    
    with col1:
        search_term = st.text_input(
            "Search parties (Myanmar or English)",
            placeholder="Enter party name...",
            help="Search by party name in Myanmar or English"
        )
    
    with col2:
        party_types = st.multiselect(
            "Filter by status",
            options=['existing', 'allowed_to_register', 'canceled'],
            default=['existing', 'allowed_to_register'],
            format_func=lambda x: {
                'existing': '📋 Existing',
                'allowed_to_register': '📝 Allowed to Register', 
                'canceled': '❌ Canceled'
            }[x]
        )
    
    # Apply filters
    filtered_df = df[df['type'].isin(party_types)].copy()
    
    # Apply search
    if search_term:
        search_mask = (
            filtered_df['name_mm'].str.contains(search_term, case=False, na=False) |
            filtered_df['name_en'].str.contains(search_term, case=False, na=False)
        )
        filtered_df = filtered_df[search_mask]
    
    # Display filter results
    st.info(f"📊 Showing {len(filtered_df)} parties out of {len(df)} total")
    
    return filtered_df

def display_party_table(df: pd.DataFrame) -> None:
    """Display parties in a formatted table."""
    if df.empty:
        st.warning("No parties found matching your criteria")
        return
    
    st.subheader("📋 Party Details")
    
    # Prepare display dataframe
    display_df = df.copy()
    
    # Add status badges
    status_map = {
        'existing': '🟢 Existing',
        'allowed_to_register': '🟡 Allowed to Register',
        'canceled': '🔴 Canceled'
    }
    display_df['Status'] = display_df['type'].map(status_map)
    
    # Select and rename columns for display
    columns_to_show = ['name_mm', 'name_en', 'Status']
    column_names = ['Party Name (Myanmar)', 'Party Name (English)', 'Status']
    
    # Add additional columns based on party type
    if 'address' in display_df.columns:
        columns_to_show.append('address')
        column_names.append('Address')
    
    if 'registration_date' in display_df.columns:
        columns_to_show.append('registration_date')
        column_names.append('Registration Date')
    
    # Show the table
    display_subset = display_df[columns_to_show].copy()
    display_subset.columns = column_names
    
    # Color code rows by status
    def highlight_party_type(row):
        if 'Existing' in str(row['Status']):
            return ['background-color: rgba(46, 134, 171, 0.1)'] * len(row)
        elif 'Allowed' in str(row['Status']):
            return ['background-color: rgba(241, 143, 1, 0.1)'] * len(row)
        elif 'Canceled' in str(row['Status']):
            return ['background-color: rgba(199, 62, 29, 0.1)'] * len(row)
        return [''] * len(row)
    
    styled_df = display_subset.style.apply(highlight_party_type, axis=1)
    st.dataframe(styled_df, use_container_width=True, height=600)

def create_parties_page():
    """Main function to create the parties page."""
    st.title("🏛️ Myanmar 2025 Political Parties")
    st.markdown("*Data from Union Election Commission (UEC)*")
    
    # Load party data
    party_data = load_party_data()
    
    if not party_data:
        st.error("Unable to load party data")
        return
    
    # Overview section
    create_parties_overview(party_data)
    
    # Distribution chart
    st.subheader("📊 Party Distribution")
    create_party_distribution_chart(party_data)
    
    # Search and filter
    filtered_df = create_party_search_and_filter(party_data)
    
    # Display table
    display_party_table(filtered_df)
    
    # Data source note
    st.markdown("---")
    st.markdown("**Data Source:** Union Election Commission (UEC) Myanmar")
    st.markdown("**Categories:**")
    st.markdown("- 🟢 **Existing**: Currently active political parties")
    st.markdown("- 🟡 **Allowed to Register**: Parties permitted to register for 2025 election")
    st.markdown("- 🔴 **Canceled**: Previously registered but canceled parties")

if __name__ == "__main__":
    create_parties_page()