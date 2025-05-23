import streamlit as st
import sys
import os
from datetime import datetime, timedelta
import pandas as pd

# Add parent directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import required modules
from modules.airtable import get_kpi_data, calculate_performance_score
from modules.visualization.leader_performance import create_leader_performance_dashboard

# Page configuration
st.set_page_config(
    page_title="Onsite Leader Performance",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
try:
    with open('styles.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    st.warning("Styles file not found. Some visual elements may not display correctly.")

def render_leader_performance_dashboard():
    """Render the leader performance dashboard"""
    
    # Page header
    st.title("Onsite Leader Performance")
    
    # Add refresh data button at the top
    col_refresh, col_spacer = st.columns([1, 5])
    
    with col_refresh:
        if st.button("🔄 Refresh Data", use_container_width=True, type="primary"):
            # Clear cache to force data refresh
            get_kpi_data.clear()
            st.success("✅ Data refreshed from Daily KPI table!")
            # Force page to reload to show the updated data
            st.rerun()
    
    # Filters
    st.subheader("Filters")
    
    col1, col2, col3 = st.columns(3)
    
    # Default dates (last 90 days)
    default_end_date = datetime.now().date()
    default_start_date = datetime(2025, 1, 1).date()
    
    with col1:
        start_date = st.date_input("Start Date", value=default_start_date)
    
    with col2:
        end_date = st.date_input("End Date", value=default_end_date)
    
    # Set up date range filter
    date_range = (start_date, end_date)
    
    # Add preset date ranges
    with col3:
        preset_ranges = {
            "2025 Data": (datetime(2025, 1, 1).date(), datetime(2025, 12, 31).date()),
            "Last 30 days": (default_end_date - timedelta(days=30), default_end_date),
            "Last 90 days": (default_end_date - timedelta(days=90), default_end_date),
            "Last 6 months": (default_end_date - timedelta(days=180), default_end_date),
            "Year to date": (datetime(default_end_date.year, 1, 1).date(), default_end_date),
            "All time": (None, None)
        }
        
        selected_preset = st.selectbox("Preset Date Range", list(preset_ranges.keys()), index=0)
        
        if st.button("Apply Preset"):
            start_date, end_date = preset_ranges[selected_preset]
            if start_date is not None and end_date is not None:
                # Update the date range based on the selected preset
                date_range = (start_date, end_date)
                st.success(f"Date range updated: {start_date} to {end_date}")
            else:
                # Set to all time
                date_range = (None, None)
                st.success(f"Date range set to all time")
    
    # Info about the data source
    st.info("Data is fetched from the 'Daily KPI' table in the 'Onsite Reporting' Airtable base.")
    
    # Fetch KPI data
    with st.spinner("Loading KPI data..."):
        try:
            kpi_data = get_kpi_data(date_range=date_range)
            
            if kpi_data.empty:
                st.warning("No KPI data available for the selected date range. Try selecting a different range or check if data exists in the Airtable table.")
                
                # Show example data format
                st.subheader("Expected Data Format")
                st.markdown("""
                The dashboard expects data from the Daily KPI form with the following fields:
                - **Leader**: The name of the onsite leader
                - **Site**: The location where the event was held
                - **Date**: The date of the event
                - **EargymPromotion**: Number of Eargym promotions
                - **Crossbooking**: Number of cross-bookings
                - **BOTDandEODFilled**: Whether Beginning/End of Day forms were completed (Yes/No)
                - **PhotosVideosTestimonials**: Number of photos/videos/testimonials posted
                - **XraysAndDentalNotesUploaded**: Whether all documentation was uploaded (Yes/No)
                """)
                return
        except Exception as e:
            st.error(f"Error loading KPI data: {str(e)}")
            st.info("Check that your Airtable API key is set correctly and that you have access to the 'Onsite Reporting' base.")
            return
    
    # Display data overview
    st.subheader("Data Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Records", len(kpi_data))
    with col2:
        st.metric("Leaders", len(kpi_data['Leader'].unique()))
    with col3:
        st.metric("Sites", len(kpi_data['Site'].unique()))
    with col4:
        date_range_str = f"{kpi_data['Date'].min().strftime('%b %d, %Y')} to {kpi_data['Date'].max().strftime('%b %d, %Y')}" if not kpi_data.empty else "N/A"
        st.metric("Date Range", date_range_str)
    
    # Get weights from session state or use defaults
    weights = st.session_state.get('kpi_weights', {
        'EargymPromotion': 1,
        'Crossbooking': 1,
        'BOTDandEODFilled': 1,
        'PhotosVideosTestimonials': 1,
        'XraysAndDentalNotesUploaded': 1
    })
    
    # Calculate performance scores
    leader_scores = calculate_performance_score(kpi_data, weights=weights)
    
    # Create the dashboard
    create_leader_performance_dashboard(kpi_data, leader_scores, weights=weights)

# Run the dashboard
render_leader_performance_dashboard() 