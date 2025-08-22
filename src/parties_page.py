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

def create_context_cards() -> None:
    """Create context cards explaining party categories."""
    st.markdown("### 📖 Understanding Party Categories")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background-color: rgba(46, 134, 171, 0.1); padding: 15px; border-radius: 10px; border-left: 5px solid #2E86AB;">
        <h4 style="color: #2E86AB; margin-top: 0;">📋 Currently Registered (61)</h4>
        <p style="margin-bottom: 0;">Parties already active from previous elections and continuing their registration for 2025.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background-color: rgba(241, 143, 1, 0.1); padding: 15px; border-radius: 10px; border-left: 5px solid #F18F01;">
        <h4 style="color: #F18F01; margin-top: 0;">📝 Newly Allowed to Register (4)</h4>
        <p style="margin-bottom: 0;">Genuinely NEW parties that have received permission to register specifically for the 2025 election (duplicates merged).</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background-color: rgba(199, 62, 29, 0.1); padding: 15px; border-radius: 10px; border-left: 5px solid #C73E1D;">
        <h4 style="color: #C73E1D; margin-top: 0;">❌ Canceled/Historical (75)</h4>
        <p style="margin-bottom: 0;">Previously registered parties that have been canceled, dissolved, or rejected (duplicates merged).</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.info("💡 **Key Point**: These are three distinct, non-overlapping categories representing different registration statuses, not stages in a transformation process.")

def get_parties_by_type(party_data: Dict[str, Any], party_types: List[str]) -> pd.DataFrame:
    """Get parties filtered by type(s)."""
    if not party_data or 'parties' not in party_data:
        return pd.DataFrame()
    
    parties = []
    for party_type in party_types:
        if party_type in party_data['parties']:
            for party in party_data['parties'][party_type]:
                party_info = party.copy()
                party_info['type'] = party_type
                parties.append(party_info)
    
    return pd.DataFrame(parties) if parties else pd.DataFrame()

def create_party_search(df: pd.DataFrame, search_key: str) -> pd.DataFrame:
    """Create search interface and return filtered dataframe."""
    search_term = st.text_input(
        "🔍 Search parties (Myanmar or English)",
        placeholder="Enter party name...",
        help="Search by party name in Myanmar or English",
        key=search_key
    )
    
    if search_term and not df.empty:
        search_mask = (
            df['name_mm'].str.contains(search_term, case=False, na=False) |
            df['name_en'].str.contains(search_term, case=False, na=False)
        )
        filtered_df = df[search_mask]
        st.info(f"🔍 Found {len(filtered_df)} parties matching '{search_term}'")
        return filtered_df
    
    return df

def display_party_table(df: pd.DataFrame, show_status: bool = False) -> None:
    """Display parties in a formatted table."""
    if df.empty:
        st.warning("No parties found matching your criteria")
        return
    
    # Prepare display dataframe
    display_df = df.copy()
    
    # Select columns for display
    columns_to_show = ['name_mm', 'name_en']
    column_names = ['Party Name (Myanmar)', 'Party Name (English)']
    
    # Add status column if requested
    if show_status:
        status_map = {
            'existing': '🟢 Currently Registered',
            'allowed_to_register': '🟡 Newly Allowed to Register',
            'canceled': '🔴 Canceled/Historical'
        }
        display_df['Status'] = display_df['type'].map(status_map)
        columns_to_show.append('Status')
        column_names.append('Status')
    
    # Add additional columns based on available data
    if 'address' in display_df.columns and not display_df['address'].isna().all():
        columns_to_show.append('address')
        column_names.append('Address')
    
    if 'registration_date' in display_df.columns and not display_df['registration_date'].isna().all():
        columns_to_show.append('registration_date')
        column_names.append('Registration Date')
    
    # Create display subset
    display_subset = display_df[columns_to_show].copy()
    display_subset.columns = column_names
    
    # Color code rows by status if showing status
    if show_status:
        def highlight_party_type(row):
            if 'Currently Registered' in str(row.get('Status', '')):
                return ['background-color: rgba(46, 134, 171, 0.1)'] * len(row)
            elif 'Newly Allowed' in str(row.get('Status', '')):
                return ['background-color: rgba(241, 143, 1, 0.1)'] * len(row)
            elif 'Canceled' in str(row.get('Status', '')):
                return ['background-color: rgba(199, 62, 29, 0.1)'] * len(row)
            return [''] * len(row)
        
        styled_df = display_subset.style.apply(highlight_party_type, axis=1)
        st.dataframe(styled_df, use_container_width=True, height=500)
    else:
        st.dataframe(display_subset, use_container_width=True, height=500)

def create_tabbed_party_interface(party_data: Dict[str, Any]) -> None:
    """Create tabbed interface for different party categories."""
    if not party_data or 'parties' not in party_data:
        st.error("No party data available")
        return
    
    summary = party_data.get('summary', {})
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        f"🗳️ 2025 Election Eligible ({summary.get('total_existing', 0) + summary.get('total_allowed_to_register', 0)})",
        f"📋 Currently Registered ({summary.get('total_existing', 0)})",
        f"📝 Newly Allowed to Register ({summary.get('total_allowed_to_register', 0)})",
        f"📜 Historical/Canceled ({summary.get('total_canceled', 0)})"
    ])
    
    # Tab 1: 2025 Election Eligible (Combined)
    with tab1:
        st.markdown("### 🗳️ Parties Eligible for 2025 Election")
        st.info("This tab shows all parties that can participate in the 2025 election: both currently registered parties and newly allowed parties.")
        
        eligible_df = get_parties_by_type(party_data, ['existing', 'allowed_to_register'])
        filtered_df = create_party_search(eligible_df, "search_eligible")
        
        if not filtered_df.empty:
            st.markdown(f"**📊 Total: {len(filtered_df)} parties eligible for 2025 election**")
            display_party_table(filtered_df, show_status=True)
        else:
            st.warning("No parties found")
    
    # Tab 2: Currently Registered
    with tab2:
        st.markdown("### 📋 Currently Registered Parties")
        st.info("Parties that were already registered from previous elections and continue to be active for 2025.")
        
        existing_df = get_parties_by_type(party_data, ['existing'])
        filtered_df = create_party_search(existing_df, "search_existing")
        
        if not filtered_df.empty:
            st.markdown(f"**📊 Total: {len(filtered_df)} currently registered parties**")
            display_party_table(filtered_df)
        else:
            st.warning("No currently registered parties found")
    
    # Tab 3: Newly Allowed to Register
    with tab3:
        st.markdown("### 📝 Newly Allowed to Register")
        st.info("NEW parties that have received permission to register specifically for the 2025 election. These are not previously existing parties.")
        
        new_df = get_parties_by_type(party_data, ['allowed_to_register'])
        filtered_df = create_party_search(new_df, "search_new")
        
        if not filtered_df.empty:
            st.markdown(f"**📊 Total: {len(filtered_df)} newly allowed parties**")
            display_party_table(filtered_df)
        else:
            st.warning("No newly allowed parties found")
    
    # Tab 4: Historical/Canceled
    with tab4:
        st.markdown("### 📜 Historical/Canceled Parties")
        st.warning("These parties are no longer active and cannot participate in the 2025 election.")
        
        canceled_df = get_parties_by_type(party_data, ['canceled'])
        filtered_df = create_party_search(canceled_df, "search_canceled")
        
        if not filtered_df.empty:
            st.markdown(f"**📊 Total: {len(filtered_df)} canceled/historical parties**")
            display_party_table(filtered_df)
        else:
            st.warning("No canceled parties found")

def create_parties_page():
    """Main function to create the parties page."""
    st.title("🏛️ Myanmar 2025 Political Parties")
    st.markdown("*Data from Union Election Commission (UEC)*")
    
    # Load party data
    party_data = load_party_data()
    
    if not party_data:
        st.error("Unable to load party data")
        return
    
    # Context cards explaining categories
    create_context_cards()
    
    # Overview section
    create_parties_overview(party_data)
    
    # Distribution chart
    st.subheader("📊 Party Distribution by Registration Status")
    create_party_distribution_chart(party_data)
    
    st.markdown("---")
    
    # Tabbed interface for party categories
    create_tabbed_party_interface(party_data)
    
    # Data source note
    st.markdown("---")
    st.markdown("**Data Source:** Union Election Commission (UEC) Myanmar")
    st.markdown("**Important Notes:**")
    st.markdown("- These three categories are **distinct and non-overlapping**")
    st.markdown("- 'Newly Allowed to Register' parties are **NEW** applications, not existing parties changing status")
    st.markdown("- Only parties in 'Currently Registered' and 'Newly Allowed to Register' categories can participate in 2025")
    st.markdown("- Data represents official UEC registration statuses as of the extraction date")

if __name__ == "__main__":
    create_parties_page()