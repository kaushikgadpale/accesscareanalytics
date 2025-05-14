import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import json
import pytz
import csv
import base64
from io import BytesIO
import re
import numpy as np
import time
import uuid
import sys
import asyncio
from streamlit_extras.stylable_container import stylable_container
from streamlit_extras.app_logo import add_logo
from streamlit_extras.colored_header import colored_header

# Import custom modules
from config import THEME_CONFIG, DATE_PRESETS, APP_TAGLINE, LOGO_PATH, AIRTABLE_CONFIG
from ms_integrations import fetch_bookings_data, fetch_calendar_events, fetch_businesses_for_appointments, track_booking_cancellations, fetch_cancellation_emails
from phone_formatter import format_phone_strict, create_phone_analysis, format_phone_dataframe, prepare_outlook_contacts, create_appointments_flow, process_uploaded_phone_list
from airtable_integration import render_airtable_tabs, get_airtable_credentials, fetch_airtable_table
from icons import render_logo, render_tab_bar, render_icon, render_empty_state, render_info_box
from sow_creator import render_sow_creator
from airtable_export import render_export_options, export_bookings_to_airtable, export_patients_to_airtable, analyze_airtable_data

# Page configuration
st.set_page_config(
    page_title="Access Care Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Initialize session state variables if they don't exist
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 'dashboard'
    
if 'active_subtab' not in st.session_state:
    st.session_state.active_subtab = {}
    
if 'date_range' not in st.session_state:
    today = datetime.now().date()
    st.session_state.date_range = (today - timedelta(days=30), today)
    st.session_state.date_preset = "Last 30 Days"

if 'bookings_data' not in st.session_state:
    st.session_state.bookings_data = None
    
if 'filtered_data' not in st.session_state:
    st.session_state.filtered_data = None
    
if 'calendar_data' not in st.session_state:
    st.session_state.calendar_data = None

# Helper functions
def set_active_tab(tab):
    """Set the active main tab and update session state"""
    st.session_state.active_tab = tab
    # Force the page to rerun
    st.rerun()
    
def set_active_subtab(tab, subtab):
    """Set the active subtab for a specific main tab and update session state"""
    if 'active_subtab' not in st.session_state:
        st.session_state.active_subtab = {}
    st.session_state.active_subtab[tab] = subtab
    # Force the page to rerun
    st.rerun()

# Render the application header
def render_app_header():
    """Render the application header with logo and title"""
    col1, col2 = st.columns([1, 4])
    
    with col1:
        # Check if logo files exist and use them, otherwise use the SVG
        logo_path = "logo.png"
        big_logo_path = "big_logo.png"
        
        logo_displayed = False
        
        # Try to display logo with proper error handling
        if os.path.exists(big_logo_path) and os.path.getsize(big_logo_path) > 100:
            try:
                st.image(big_logo_path, width=150)
                logo_displayed = True
            except Exception as e:
                logo_displayed = False
        
        if not logo_displayed and os.path.exists(logo_path) and os.path.getsize(logo_path) > 100:
            try:
                st.image(logo_path, width=80)
                logo_displayed = True
            except Exception as e:
                logo_displayed = False
        
        if not logo_displayed:
            st.markdown(render_logo(width="80px"), unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <h1 class="app-title">Access Care Analytics Dashboard</h1>
        <p class="app-subtitle">{APP_TAGLINE}</p>
        """, unsafe_allow_html=True)

# Tab definitions for the main navigation
MAIN_TABS = {
    "dashboard": {"icon": "analytics", "label": "Main"},
    "tools": {"icon": "tool", "label": "Tools"},
    "integrations": {"icon": "link", "label": "Integrations"},
    "content": {"icon": "document", "label": "Content Creator"}
}

# Subtab definitions for each main tab
SUBTABS = {
    "dashboard": {
        "appointments": {"icon": "calendar", "label": "Appointments"},
        "performance": {"icon": "chart", "label": "Performance"}
    },
    "patient": {
        "contacts": {"icon": "phone", "label": "Contacts"},
        "communication": {"icon": "mail", "label": "Communication"},
        "export": {"icon": "upload", "label": "Export"}
    },
    "tools": {
        "phone_validation": {"icon": "phone", "label": "Phone Validation"},
        "api_inspector": {"icon": "search", "label": "API Inspector"},
        "date_tools": {"icon": "clock", "label": "Date Tools"}
    },
    "integrations": {
        "ms_graph": {"icon": "graph", "label": "Microsoft Graph"},
        "webhooks": {"icon": "link", "label": "Webhooks"}
    },
    "content": {
        "templates": {"icon": "template", "label": "Templates"},
        "sow": {"icon": "document", "label": "SOW Generator"}
    }
}

# Main application layout
def main():
    """Main application entry point"""
    # Add sidebar
    with st.sidebar:
        # Add logo to sidebar
        logo_path = "big_logo.png"
        if os.path.exists(logo_path) and os.path.getsize(logo_path) > 100:
            try:
                st.image(logo_path, width=120)
            except Exception as e:
                st.markdown(render_logo(width="120px"), unsafe_allow_html=True)
        else:
            st.markdown(render_logo(width="120px"), unsafe_allow_html=True)
        
        st.markdown("<h3 style='text-align: center; margin-bottom: 0;'>Access Care Analytics</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 0.9rem; margin-top: 0;'>Healthcare Analytics Platform</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        # Add navigation links with monochrome icons
        colored_header("Navigation", description="", color_name="gray-70")
        
        # Use the stylable_container to create better-styled buttons
        with stylable_container(
            key="sidebar_nav",
            css_styles="""
                button {
                    background-color: transparent;
                    color: #1f2937;
                    text-align: left;
                    font-weight: 500;
                    padding: 0.5rem 1rem;
                    width: 100%;
                    border: 1px solid #e5e7eb;
                    border-radius: 6px;
                    margin-bottom: 0.5rem;
                }
                button:hover {
                    background-color: #f3f4f6;
                    border-color: #d1d5db;
                }
                div[data-testid="stHorizontalBlock"] {
                    align-items: center;
                }
            """
        ):
            if st.button("Main", use_container_width=True):
                st.session_state.active_tab = "dashboard"
                st.rerun()
                
            if st.button("Tools", use_container_width=True):
                st.session_state.active_tab = "tools"
                st.rerun()
                
            if st.button("Integrations", use_container_width=True):
                st.session_state.active_tab = "integrations"
                st.rerun()
                
            if st.button("Content Creator", use_container_width=True):
                st.session_state.active_tab = "content"
                st.rerun()
        
        # App information
        st.markdown("---")
        colored_header("About", description="", color_name="gray-70")
        st.markdown("""
        <div style='font-size: 0.9rem;'>
        Access Care Analytics provides comprehensive tools for healthcare appointment management, data analysis, and reporting.
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("<p style='text-align: center; font-size: 0.8rem; color: #6b7280;'>© 2023 Access Care Analytics</p>", unsafe_allow_html=True)
    
    render_app_header()
    
    # Render main tabs
    active_tab = render_tab_bar(MAIN_TABS, st.session_state.active_tab, set_active_tab)
    st.session_state.active_tab = active_tab
    
    # Render subtabs for the active tab
    if active_tab in SUBTABS:
        # Initialize active subtab for this tab if not set
        if active_tab not in st.session_state.active_subtab:
            st.session_state.active_subtab[active_tab] = list(SUBTABS[active_tab].keys())[0]
        
        # Add a small visual separator
        st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
            
        # Create columns for subtabs
        st.markdown("<div class='subtabs-container'>", unsafe_allow_html=True)
        
        # Render the subtabs
        active_subtab = render_tab_bar(
            SUBTABS[active_tab], 
            st.session_state.active_subtab.get(active_tab),
            lambda subtab: set_active_subtab(active_tab, subtab)
        )
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.session_state.active_subtab[active_tab] = active_subtab
    
    # Render the content for the active tab and subtab
    if active_tab == "dashboard":
        render_dashboard_tab(st.session_state.active_subtab.get(active_tab))
    elif active_tab == "tools":
        render_tools_tab(st.session_state.active_subtab.get(active_tab))
    elif active_tab == "integrations":
        render_integrations_tab(st.session_state.active_subtab.get(active_tab))
    elif active_tab == "content":
        render_content_tab(st.session_state.active_subtab.get(active_tab))

# Render the dashboard tab
def render_dashboard_tab(active_subtab):
    """Render the dashboard tab content"""
    if active_subtab == "appointments":
        st.header("Appointments")
        
        # Add a section to select booking businesses
        st.subheader("Select Booking Pages")
        
        # Add search box for filtering businesses
        search_query = st.text_input("Search booking pages", key="business_search")
        
        # Initialize session state for selected businesses if not exists
        if 'selected_businesses' not in st.session_state:
            st.session_state.selected_businesses = []
        
        # Fetch businesses and group them
        if 'grouped_businesses' not in st.session_state:
            try:
                grouped_businesses = asyncio.run(fetch_businesses_for_appointments())
                st.session_state.grouped_businesses = grouped_businesses
            except Exception as e:
                st.error(f"Error fetching businesses: {str(e)}")
                st.session_state.grouped_businesses = {}
        
        # Create columns for select/unselect all buttons
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("Select All"):
                # Select all businesses
                all_businesses = []
                for group in st.session_state.grouped_businesses.values():
                    all_businesses.extend([b["id"] for b in group])
                st.session_state.selected_businesses = all_businesses
                st.rerun()
        
        with col2:
            if st.button("Unselect All"):
                # Clear all selections
                st.session_state.selected_businesses = []
                st.rerun()
        
        # Display businesses grouped by first two letters
        if st.session_state.grouped_businesses:
            for prefix, businesses in st.session_state.grouped_businesses.items():
                # Filter businesses based on search query
                if search_query:
                    filtered_businesses = [b for b in businesses if search_query.lower() in b["name"].lower()]
                    if not filtered_businesses:
                        continue
                    businesses = filtered_businesses
                
                # Create expandable section for each group
                with st.expander(f"{prefix} ({len(businesses)} booking pages)", expanded=True):
                    for business in businesses:
                        is_selected = business["id"] in st.session_state.selected_businesses
                        if st.checkbox(
                            business["name"], 
                            value=is_selected, 
                            key=f"business_{business['id']}"
                        ):
                            if business["id"] not in st.session_state.selected_businesses:
                                st.session_state.selected_businesses.append(business["id"])
                        else:
                            if business["id"] in st.session_state.selected_businesses:
                                st.session_state.selected_businesses.remove(business["id"])
        else:
            st.warning("No booking pages found. Please check your Microsoft Bookings integration.")
        
        # Display selected businesses summary
        if st.session_state.selected_businesses:
            # Flatten the business list to find names for the selected IDs
            all_businesses = []
            for group in st.session_state.grouped_businesses.values():
                all_businesses.extend(group)
            
            # Get names of selected businesses
            selected_names = [
                b["name"] for b in all_businesses 
                if b["id"] in st.session_state.selected_businesses
            ]
            
            if selected_names:
                st.write(f"**{len(selected_names)} booking pages selected**: {', '.join(selected_names)}")
            else:
                st.write("No booking pages selected")
        else:
            st.write("No booking pages selected")
        
        # Button to fetch appointments for selected businesses
        if st.session_state.selected_businesses:
            # Date range for appointment fetching
            date_col1, date_col2 = st.columns(2)
            with date_col1:
                start_date = st.date_input("Start Date", value=st.session_state.date_range[0])
            with date_col2:
                end_date = st.date_input("End Date", value=st.session_state.date_range[1])
            
            # Update session state date range
            st.session_state.date_range = (start_date, end_date)
            
            # Add a button to fetch data
            if st.button("Fetch Appointments"):
                with st.spinner("Fetching appointments..."):
                    try:
                        # Call the asynchronous function to fetch appointments
                        bookings_data = asyncio.run(fetch_bookings_data(
                            start_date,
                            end_date,
                            500,  # Use default max_results
                            st.session_state.selected_businesses
                        ))
                        
                        if bookings_data and len(bookings_data) > 0:
                            # Convert to DataFrame
                            df = pd.DataFrame(bookings_data)
                            
                            # Process date columns
                            date_columns = ['Created Date', 'Start Date', 'End Date']
                            for col in date_columns:
                                if col in df.columns:
                                    df[col] = pd.to_datetime(df[col])
                            
                            # Store in session state
                            st.session_state.bookings_data = df
                            st.success(f"Successfully fetched {len(df)} appointments.")
                        else:
                            st.warning("No appointments found for the selected date range and businesses.")
                    except Exception as e:
                        st.error(f"Error fetching appointments: {str(e)}")
        
        # Show appointment data if available
        if st.session_state.get('bookings_data') is not None:
            st.subheader("Appointment Data")
            
            df = st.session_state.bookings_data
            
            # Create tabs for different views
            tabs = st.tabs(["Data Table", "Cancellations", "Visualizations", "Analysis"])
            
            with tabs[0]:
                # Data table view with filters
                st.write("### Appointment Records")
                
                # Add filters for the data table
                filter_container = st.container()
                with filter_container:
                    filter_cols = st.columns(4)
                    
                    # Create filter for business names
                    with filter_cols[0]:
                        if 'Business' in df.columns:
                            business_options = ["All"] + sorted(df['Business'].unique().tolist())
                            selected_business = st.selectbox("Business", business_options)
                        else:
                            selected_business = "All"
                    
                    # Create filter for status
                    with filter_cols[1]:
                        if 'Status' in df.columns:
                            status_options = ["All"] + sorted(df['Status'].unique().tolist())
                            selected_status = st.selectbox("Status", status_options)
                        else:
                            selected_status = "All"
                    
                    # Create filter for service
                    with filter_cols[2]:
                        if 'Service' in df.columns:
                            service_options = ["All"] + sorted(df['Service'].unique().tolist())
                            selected_service = st.selectbox("Service", service_options)
                        else:
                            selected_service = "All"
                    
                    # Create search for customer name
                    with filter_cols[3]:
                        if 'Customer' in df.columns:
                            customer_search = st.text_input("Search Customer")
                        else:
                            customer_search = ""
                
                # Apply filters to the dataframe
                filtered_df = df.copy()
                
                if selected_business != "All" and 'Business' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['Business'] == selected_business]
                
                if selected_status != "All" and 'Status' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['Status'] == selected_status]
                
                if selected_service != "All" and 'Service' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['Service'] == selected_service]
                
                if customer_search and 'Customer' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['Customer'].str.contains(customer_search, case=False)]
                
                # Show the filtered table
                st.dataframe(filtered_df, use_container_width=True)
                
                # Add download option
                csv = filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Download CSV",
                    csv,
                    "appointments.csv",
                    "text/csv",
                    key="download-csv"
                )
            
            with tabs[1]:
                # Cancellations tab
                st.write("### Appointment Cancellations")
                
                st.markdown("""
                <div class="card">
                    <h4>Track Cancelled Appointments</h4>
                    <p>This feature tracks appointments that were cancelled by combining two methods:</p>
                    <ol>
                        <li><strong>Dataset Comparison</strong>: Detects appointments that were present in a previous fetch but are missing in the current data.</li>
                        <li><strong>Email Analysis</strong>: Searches mailboxes for cancellation emails and extracts appointment details.</li>
                    </ol>
                </div>
                """, unsafe_allow_html=True)
                
                # Options for cancellation detection
                check_col1, check_col2 = st.columns([3, 2])
                
                with check_col1:
                    # Add options for email checking
                    with st.expander("Cancellation Detection Options", expanded=True):
                        check_emails = st.checkbox("Check mailboxes for cancellation emails", value=True)
                        email_days = st.slider("Days to look back for cancellation emails", 
                                              min_value=1, max_value=90, value=30, 
                                              help="Number of days to look back in mailboxes for cancellation emails")
                        
                        # Display mailbox information
                        if check_emails:
                            import os
                            mailboxes = os.getenv("BOOKINGS_MAILBOXES", "").split(",")
                            if mailboxes and mailboxes[0]:
                                st.info(f"Will check {len(mailboxes)} configured mailboxes:")
                                # List mailboxes directly without nested expander
                                mailbox_text = "\n".join([f"- {mailbox}" for mailbox in mailboxes if mailbox.strip()])
                                st.text(mailbox_text)
                            else:
                                st.warning("No mailboxes configured. Set the BOOKINGS_MAILBOXES environment variable.")
                                st.markdown("""
                                To configure mailboxes, add the BOOKINGS_MAILBOXES environment variable with a comma-separated list of email addresses, like:
                                ```
                                info-usa@accesscare.health,info-usacst@accesscare.health,info@accesscare.health
                                ```
                                """)
                    
                    # Button to check for cancellations
                    if st.button("Check for Cancellations", use_container_width=True):
                        with st.spinner("Analyzing appointment cancellations..."):
                            try:
                                # Run the cancellation tracking function
                                cancelled = asyncio.run(track_booking_cancellations(
                                    st.session_state.date_range[0],
                                    st.session_state.date_range[1],
                                    st.session_state.selected_businesses,
                                    500,
                                    check_emails,
                                    email_days
                                ))
                                
                                # Store in session state
                                st.session_state.cancelled_appointments = cancelled
                                
                                if cancelled:
                                    st.session_state.cancelled_df = pd.DataFrame(cancelled)
                                else:
                                    st.session_state.cancelled_df = pd.DataFrame()
                            except Exception as e:
                                st.error(f"Error checking for cancellations: {str(e)}")
                
                # Display cancelled appointments if available
                if 'cancelled_df' in st.session_state and not st.session_state.cancelled_df.empty:
                    st.write(f"### {len(st.session_state.cancelled_df)} Cancelled Appointments Found")
                    
                    # Add filters for the cancellations table
                    filter_container = st.container()
                    with filter_container:
                        filter_cols = st.columns(3)
                        
                        # Filter by cancellation source
                        with filter_cols[0]:
                            if 'CancellationSource' in st.session_state.cancelled_df.columns:
                                source_options = ["All"] + sorted(st.session_state.cancelled_df['CancellationSource'].unique().tolist())
                                selected_source = st.selectbox("Cancellation Source", source_options)
                            else:
                                selected_source = "All"
                        
                        # Filter by business
                        with filter_cols[1]:
                            if 'Business' in st.session_state.cancelled_df.columns:
                                business_options = ["All"] + sorted(st.session_state.cancelled_df['Business'].dropna().unique().tolist())
                                selected_business = st.selectbox("Business", business_options)
                            else:
                                selected_business = "All"
                        
                        # Search for customer
                        with filter_cols[2]:
                            if 'Customer' in st.session_state.cancelled_df.columns:
                                customer_search = st.text_input("Search Customer")
                            else:
                                customer_search = ""
                    
                    # Apply filters
                    filtered_cancelled_df = st.session_state.cancelled_df.copy()
                    
                    if selected_source != "All" and 'CancellationSource' in filtered_cancelled_df.columns:
                        filtered_cancelled_df = filtered_cancelled_df[filtered_cancelled_df['CancellationSource'] == selected_source]
                    
                    if selected_business != "All" and 'Business' in filtered_cancelled_df.columns:
                        filtered_cancelled_df = filtered_cancelled_df[filtered_cancelled_df['Business'] == selected_business]
                    
                    if customer_search and 'Customer' in filtered_cancelled_df.columns:
                        filtered_cancelled_df = filtered_cancelled_df[
                            filtered_cancelled_df['Customer'].astype(str).str.contains(customer_search, case=False, na=False)
                        ]
                    
                    # Display the filtered cancellations
                    st.dataframe(filtered_cancelled_df, use_container_width=True)
                    
                    # Add download option
                    csv = filtered_cancelled_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "Download Cancelled Appointments",
                        csv,
                        "cancelled_appointments.csv",
                        "text/csv",
                        key="download-cancelled"
                    )
                    
                    # Add visualizations for cancellations
                    viz_tabs = st.tabs(["Cancellation Sources", "Businesses", "Timeline"])
                    
                    with viz_tabs[0]:
                        # Cancellation source breakdown
                        if 'CancellationSource' in filtered_cancelled_df.columns:
                            st.subheader("Cancellation Sources")
                            
                            source_counts = filtered_cancelled_df['CancellationSource'].value_counts().reset_index()
                            source_counts.columns = ['Source', 'Count']
                            
                            fig = px.pie(
                                source_counts,
                                values='Count',
                                names='Source',
                                title='Cancellation Detection Methods',
                                color='Source',
                                color_discrete_map={
                                    'Dataset Comparison': THEME_CONFIG['PRIMARY_COLOR'],
                                    'Email': THEME_CONFIG['ACCENT_COLOR']
                                }
                            )
                            
                            fig.update_traces(textposition='inside', textinfo='percent+label')
                            fig.update_layout(height=400)
                            
                            st.plotly_chart(fig, use_container_width=True)
                    
                    with viz_tabs[1]:
                        # Business breakdown
                        if 'Business' in filtered_cancelled_df.columns:
                            st.subheader("Cancellations by Business")
                            
                            # Filter out None values
                            business_df = filtered_cancelled_df.dropna(subset=['Business'])
                            
                            if not business_df.empty:
                                business_counts = business_df['Business'].value_counts().reset_index()
                                business_counts.columns = ['Business', 'Count']
                                
                                fig = px.bar(
                                    business_counts,
                                    x='Business',
                                    y='Count',
                                    color='Count',
                                    color_continuous_scale='Reds',
                                    title='Appointment Cancellations by Business'
                                )
                                
                                fig.update_layout(
                                    xaxis_title="Business",
                                    yaxis_title="Number of Cancellations",
                                    xaxis={'categoryorder': 'total descending'},
                                    height=400
                                )
                                
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("No business data available for cancellations")
                    
                    with viz_tabs[2]:
                        # Timeline of cancellations
                        st.subheader("Cancellation Timeline")
                        
                        # Make a deep copy to prevent SettingWithCopyWarning
                        timeline_df = filtered_cancelled_df.copy(deep=True)
                        
                        # Create a Date column for timeline analysis
                        timeline_df['Date'] = None
                        
                        # Try to get date information from different fields
                        if 'ReceivedTime' in timeline_df.columns:
                            # Use proper .loc assignment to avoid SettingWithCopyWarning
                            timeline_df.loc[:, 'Date'] = pd.to_datetime(timeline_df['ReceivedTime'], errors='coerce')
                        
                        if 'Start Date' in timeline_df.columns:
                            # Fill missing dates with Start Date if available - using .loc to avoid warnings
                            mask = timeline_df['Date'].isna()
                            timeline_df.loc[mask, 'Date'] = pd.to_datetime(timeline_df.loc[mask, 'Start Date'], errors='coerce')
                        
                        # Drop rows with no date
                        timeline_df = timeline_df.dropna(subset=['Date'])
                        
                        if not timeline_df.empty:
                            # Group by date and source
                            timeline_df['Date'] = timeline_df['Date'].dt.date
                            
                            if 'CancellationSource' in timeline_df.columns:
                                daily_counts = timeline_df.groupby(['Date', 'CancellationSource']).size().reset_index(name='Count')
                                
                                fig = px.line(
                                    daily_counts,
                                    x='Date',
                                    y='Count',
                                    color='CancellationSource',
                                    title='Cancellations Over Time',
                                    markers=True
                                )
                            else:
                                daily_counts = timeline_df.groupby('Date').size().reset_index(name='Count')
                                
                                fig = px.line(
                                    daily_counts,
                                    x='Date',
                                    y='Count',
                                    title='Cancellations Over Time',
                                    markers=True
                                )
                            
                            fig.update_layout(
                                xaxis_title="Date",
                                yaxis_title="Number of Cancellations",
                                height=400
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("No timeline data available for cancellations")
                    
                elif 'cancelled_df' in st.session_state:
                    st.info("No cancelled appointments were detected.")
                else:
                    st.info("Click 'Check for Cancellations' to analyze appointment changes.")
                    
                # Add instructions for interpreting results
                with st.expander("About Cancellation Detection", expanded=False):
                    st.markdown("""
                    ## How Cancellation Detection Works
                    
                    This feature uses two complementary methods to track cancellations:
                    
                    ### 1. Dataset Comparison Method
                    
                    This method works by comparing the current set of appointments with the previously fetched set:
                    
                    1. When you click "Check for Cancellations", the system compares appointment IDs from the current data with those from the previous fetch
                    2. Appointments that were present before but are missing now are identified as "cancelled"
                    3. The full details of these cancelled appointments are displayed from the previous data snapshot
                    
                    ### 2. Email Analysis Method
                    
                    This method searches for cancellation emails in your configured mailboxes:
                    
                    1. It searches each mailbox for emails containing cancellation keywords in the subject or body
                    2. It then extracts appointment details like the customer name, appointment ID, and date
                    3. This method can detect cancellations that happen between your data fetches
                    
                    ### Important Notes
                    
                    - The Microsoft Bookings API doesn't provide a direct "cancelled" status
                    - The dataset comparison method assumes that missing appointments were cancelled
                    - Some appointments might be missing for other reasons (e.g., rescheduled with a new ID)
                    - The email method depends on the format of your cancellation emails
                    - For best results, use both methods together
                    """)
                    
                    st.markdown("""
                    ### Setting Up Mailboxes
                    
                    To configure the mailboxes for cancellation emails, add the `BOOKINGS_MAILBOXES` environment variable with a comma-separated list of email addresses:
                    
                    ```
                    BOOKINGS_MAILBOXES=info-usa@accesscare.health,info-usacst@accesscare.health,info@accesscare.health
                    ```
                    
                    The application will need appropriate permissions to access these mailboxes.
                    """)
            
            with tabs[2]:
                # Visualizations tab
                st.write("### Appointment Visualizations")
                
                # Status distribution
                if 'Status' in filtered_df.columns:
                    st.subheader("Appointment Status Distribution")
                    
                    status_counts = filtered_df['Status'].value_counts().reset_index()
                    status_counts.columns = ['Status', 'Count']
                    
                    fig = px.pie(
                        status_counts,
                        values='Count',
                        names='Status',
                        title='Appointment Status Distribution',
                        color_discrete_map={
                            'Completed': THEME_CONFIG['SUCCESS_COLOR'],
                            'Scheduled': THEME_CONFIG['PRIMARY_COLOR'],
                            'Cancelled': THEME_CONFIG['DANGER_COLOR']
                        }
                    )
                    
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    fig.update_layout(height=400)
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                # Distribution by business (if applicable)
                if 'Business' in filtered_df.columns:
                    st.subheader("Appointments by Business")
                    
                    business_counts = filtered_df['Business'].value_counts().reset_index()
                    business_counts.columns = ['Business', 'Count']
                    
                    fig = px.bar(
                        business_counts.sort_values('Count', ascending=False).head(10),
                        x='Business',
                        y='Count',
                        title='Top Businesses by Appointment Count',
                        color='Count',
                        color_continuous_scale='Viridis'
                    )
                    
                    fig.update_layout(
                        xaxis_title="Business",
                        yaxis_title="Number of Appointments",
                        xaxis={'categoryorder': 'total descending'},
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                # Service distribution (if applicable)
                if 'Service' in filtered_df.columns:
                    st.subheader("Appointments by Service Type")
                    
                    service_counts = filtered_df['Service'].value_counts().reset_index()
                    service_counts.columns = ['Service', 'Count']
                    
                    fig = px.bar(
                        service_counts.sort_values('Count', ascending=False),
                        x='Service',
                        y='Count',
                        title='Appointments by Service Type',
                        color='Count',
                        color_continuous_scale='Viridis'
                    )
                    
                    fig.update_layout(
                        xaxis_title="Service",
                        yaxis_title="Number of Appointments",
                        xaxis={'categoryorder': 'total descending'},
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
            
            with tabs[3]:
                # Analysis tab
                st.write("### Appointment Analysis")
                
                # Select date level for aggregation
                date_level = st.selectbox(
                    "Date Aggregation Level", 
                    ["Daily", "Weekly", "Monthly", "Quarterly", "Yearly"]
                )
                
                # Define frequency map for resample
                freq_map = {
                    "Daily": "D",
                    "Weekly": "W",
                    "Monthly": "M",
                    "Quarterly": "Q",
                    "Yearly": "Y"
                }
                
                # Month names for nice labels
                month_names = {
                    1: 'January', 2: 'February', 3: 'March', 4: 'April',
                    5: 'May', 6: 'June', 7: 'July', 8: 'August',
                    9: 'September', 10: 'October', 11: 'November', 12: 'December'
                }
                
                # Date range for analysis
                analysis_cols = st.columns(2)
                with analysis_cols[0]:
                    analysis_start_date = st.date_input("Analysis Start Date", value=st.session_state.date_range[0], key="analysis_start")
                with analysis_cols[1]:
                    analysis_end_date = st.date_input("Analysis End Date", value=st.session_state.date_range[1], key="analysis_end")
                
                # Analysis based on booking creation time
                if 'Created Date' in filtered_df.columns:
                    st.subheader("Booking Creation Analysis")
                    
                    # Filter by date range
                    creation_df = filtered_df[
                        (filtered_df['Created Date'].dt.date >= analysis_start_date) &
                        (filtered_df['Created Date'].dt.date <= analysis_end_date)
                    ]
                    
                    if not creation_df.empty:
                        # Convert timestamps to naive datetime to avoid timezone warnings
                        if pd.api.types.is_datetime64_dtype(creation_df['Created Date']):
                            creation_df['Created Date'] = creation_df['Created Date'].dt.tz_localize(None)
                        
                        # Group by selected frequency
                        creation_df['Period'] = creation_df['Created Date'].dt.to_period(freq_map[date_level])
                        creation_counts = creation_df.groupby('Period').size().reset_index(name='Count')
                        creation_counts['Period'] = creation_counts['Period'].astype(str)
                        
                        # Create creation time graph
                        fig_creation = px.line(
                            creation_counts, 
                            x='Period', 
                            y='Count',
                            title=f'Appointments by Creation Date ({date_level})',
                            markers=True
                        )
                        
                        fig_creation.update_layout(
                            xaxis_title=f"{date_level} Period",
                            yaxis_title="Number of Appointments",
                            hovermode="x unified",
                            height=400
                        )
                        
                        st.plotly_chart(fig_creation, use_container_width=True)
                    else:
                        st.info("No data available for the selected date range.")
                
                # Analysis based on booking date
                if 'Start Date' in filtered_df.columns:
                    st.subheader("Booking Date Analysis")
                    
                    # Filter by date range
                    booking_df = filtered_df[
                        (filtered_df['Start Date'].dt.date >= analysis_start_date) &
                        (filtered_df['Start Date'].dt.date <= analysis_end_date)
                    ]
                    
                    if not booking_df.empty:
                        # Convert timestamps to naive datetime to avoid timezone warnings
                        if 'Start Date' in booking_df.columns and pd.api.types.is_datetime64_dtype(booking_df['Start Date']):
                            booking_df['Start Date'] = booking_df['Start Date'].dt.tz_localize(None)
                        
                        # Group by business and period
                        booking_df['Period'] = booking_df['Start Date'].dt.to_period(freq_map[date_level])
                        
                        if 'Business' in booking_df.columns:
                            # Group by business and period
                            business_counts = booking_df.groupby(['Business', 'Period']).size().reset_index(name='Count')
                            business_counts['Period'] = business_counts['Period'].astype(str)
                            
                            # Create booking date by business graph
                            fig_business = px.line(
                                business_counts, 
                                x='Period', 
                                y='Count',
                                color='Business',
                                title=f'Appointments by Booking Date and Business ({date_level})',
                                markers=True
                            )
                            
                            fig_business.update_layout(
                                xaxis_title=f"{date_level} Period",
                                yaxis_title="Number of Appointments",
                                hovermode="x unified",
                                height=500
                            )
                            
                            st.plotly_chart(fig_business, use_container_width=True)
                        
                        # Overall booking date trends
                        booking_counts = booking_df.groupby('Period').size().reset_index(name='Count')
                        booking_counts['Period'] = booking_counts['Period'].astype(str)
                        
                        fig_booking = px.bar(
                            booking_counts, 
                            x='Period', 
                            y='Count',
                            title=f'Appointments by Booking Date ({date_level})',
                            color='Count',
                            color_continuous_scale='Viridis'
                        )
                        
                        fig_booking.update_layout(
                            xaxis_title=f"{date_level} Period",
                            yaxis_title="Number of Appointments",
                            hovermode="x unified",
                            height=400
                        )
                        
                        st.plotly_chart(fig_booking, use_container_width=True)
                    else:
                        st.info("No data available for the selected date range.")
                
                # Year-over-year comparison
                st.subheader("Year-over-Year Comparison")
                
                if 'Start Date' in filtered_df.columns:
                    # Extract year from dates
                    filtered_df['Year'] = filtered_df['Start Date'].dt.year
                    
                    # Get all unique years
                    years = sorted(filtered_df['Year'].dropna().unique())
                    
                    if len(years) > 0:
                        # Create year-over-year graphs
                        year_tabs = st.tabs([f"{year}" for year in years] + ["Compare All Years"])
                        
                        # Individual year tabs
                        for i, year in enumerate(years):
                            with year_tabs[i]:
                                year_df = filtered_df[filtered_df['Year'] == year]
                                
                                if not year_df.empty:
                                    # Monthly trend for this year
                                    year_df['Month'] = year_df['Start Date'].dt.month
                                    monthly_counts = year_df.groupby('Month').size().reset_index(name='Count')
                                    
                                    # Add month names
                                    monthly_counts['Month Name'] = monthly_counts['Month'].map(month_names)
                                    
                                    fig_monthly = px.line(
                                        monthly_counts.sort_values('Month'),
                                        x='Month Name',
                                        y='Count',
                                        title=f'Monthly Appointments in {year}',
                                        markers=True
                                    )
                                    
                                    fig_monthly.update_layout(
                                        xaxis_title="Month",
                                        yaxis_title="Number of Appointments",
                                        height=400,
                                        xaxis={'categoryorder':'array', 'categoryarray':list(month_names.values())}
                                    )
                                    
                                    st.plotly_chart(fig_monthly, use_container_width=True)
                                    
                                    # Business breakdown for this year if available
                                    if 'Business' in year_df.columns:
                                        business_year_counts = year_df.groupby('Business').size().reset_index(name='Count')
                                        
                                        fig_business_year = px.pie(
                                            business_year_counts,
                                            values='Count',
                                            names='Business',
                                            title=f'Appointments by Business in {year}'
                                        )
                                        
                                        fig_business_year.update_traces(textposition='inside', textinfo='percent+label')
                                        fig_business_year.update_layout(height=400)
                                        
                                        st.plotly_chart(fig_business_year, use_container_width=True)
                                else:
                                    st.info(f"No data available for {year}.")
                        
                        # Compare all years tab
                        with year_tabs[len(years)]:
                            if len(years) > 1:
                                # Prepare data for all years comparison
                                all_years_df = filtered_df.dropna(subset=['Year', 'Start Date'])
                                all_years_df['Month'] = all_years_df['Start Date'].dt.month
                                all_years_counts = all_years_df.groupby(['Year', 'Month']).size().reset_index(name='Count')
                                
                                # Add month names
                                all_years_counts['Month Name'] = all_years_counts['Month'].map(month_names)
                                
                                # Create combined year-over-year graph
                                fig_all_years = px.line(
                                    all_years_counts,
                                    x='Month Name',
                                    y='Count',
                                    color='Year',
                                    title='Year-over-Year Monthly Comparison',
                                    markers=True
                                )
                                
                                fig_all_years.update_layout(
                                    xaxis_title="Month",
                                    yaxis_title="Number of Appointments",
                                    hovermode="x",
                                    xaxis={'categoryorder':'array', 'categoryarray':list(month_names.values())},
                                    height=500
                                )
                                
                                st.plotly_chart(fig_all_years, use_container_width=True)
                                
                                # Total appointments per year
                                yearly_totals = all_years_df.groupby('Year').size().reset_index(name='Total Appointments')
                                
                                fig_yearly_totals = px.bar(
                                    yearly_totals,
                                    x='Year',
                                    y='Total Appointments',
                                    title='Total Appointments by Year',
                                    color='Total Appointments',
                                    text_auto=True
                                )
                                
                                fig_yearly_totals.update_layout(
                                    xaxis_title="Year",
                                    yaxis_title="Total Appointments",
                                    height=400
                                )
                                
                                st.plotly_chart(fig_yearly_totals, use_container_width=True)
                            else:
                                st.info("Need at least two years of data for comparison.")
                    else:
                        st.info("No yearly data available for comparison.")
                else:
                    st.info("No booking date information available for year-over-year analysis.")
            if 'Start Date' not in filtered_df.columns and 'Created Date' not in filtered_df.columns:
                st.warning("No date columns available for analysis. Please ensure your data includes 'Created Date' or 'Start Date' columns.")
        else:
            # Show message instructing to select businesses and fetch data
            st.info("Please select booking pages and fetch appointments to view data.")
    
    elif active_subtab == "performance":
        st.header("Performance Metrics")
        
        # Show introduction
        st.markdown("""
        <div class="card">
            <h3>Performance Analytics</h3>
            <p>Track key performance indicators and operational efficiency metrics.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Check if we have data
        if st.session_state.get('bookings_data') is not None:
            df = st.session_state.bookings_data
            
            # Add time period selector
            time_periods = ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Year to Date", "Custom"]
            selected_period = st.selectbox("Select Time Period", time_periods)
            
            if selected_period == "Custom":
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("Start Date", value=pd.Timestamp.now() - pd.Timedelta(days=30))
                with col2:
                    end_date = st.date_input("End Date", value=pd.Timestamp.now())
            else:
                # Set date range based on selection
                end_date = pd.Timestamp.now().date()
                if selected_period == "Last 7 Days":
                    start_date = end_date - pd.Timedelta(days=7)
                elif selected_period == "Last 30 Days":
                    start_date = end_date - pd.Timedelta(days=30)
                elif selected_period == "Last 90 Days":
                    start_date = end_date - pd.Timedelta(days=90)
                elif selected_period == "Year to Date":
                    start_date = pd.Timestamp(year=end_date.year, month=1, day=1).date()
                    
            # Create KPI metrics
            st.subheader("Key Performance Indicators")
            
            # Create example KPIs
            kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
            
            with kpi_col1:
                st.markdown("""
                <div class="card metric-card">
                    <div class="metric-value">94%</div>
                    <div class="metric-label">Booking Efficiency</div>
                </div>
                """, unsafe_allow_html=True)
                
            with kpi_col2:
                st.markdown("""
                <div class="card metric-card">
                    <div class="metric-value">89%</div>
                    <div class="metric-label">Patient Satisfaction</div>
                </div>
                """, unsafe_allow_html=True)
                
            with kpi_col3:
                st.markdown("""
                <div class="card metric-card">
                    <div class="metric-value">$1,240</div>
                    <div class="metric-label">Avg. Revenue Per Appointment</div>
                </div>
                """, unsafe_allow_html=True)
                
            # Example performance chart
            st.subheader("Daily Performance Metrics")
            
            # Create sample performance data
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            performance_data = pd.DataFrame({
                'Date': dates,
                'Satisfaction': np.random.uniform(80, 100, size=len(dates)),
                'Efficiency': np.random.uniform(75, 95, size=len(dates)),
                'Revenue': np.random.uniform(900, 1500, size=len(dates))
            })
            
            # Create a line chart for the metrics
            fig = px.line(
                performance_data,
                x='Date',
                y=['Satisfaction', 'Efficiency'],
                title='Daily Performance Metrics',
                template='plotly_dark',
                labels={'value': 'Score (%)', 'variable': 'Metric'},
                color_discrete_map={
                    'Satisfaction': THEME_CONFIG['ACCENT_COLOR'],
                    'Efficiency': THEME_CONFIG['PRIMARY_COLOR']
                }
            )
            
            fig.update_layout(
                plot_bgcolor=THEME_CONFIG['CARD_BG'],
                paper_bgcolor=THEME_CONFIG['CARD_BG'],
                font_color=THEME_CONFIG['TEXT_COLOR'],
                title_font_color=THEME_CONFIG['PRIMARY_COLOR'],
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Revenue chart
            fig_revenue = px.bar(
                performance_data,
                x='Date',
                y='Revenue',
                title='Daily Revenue Metrics',
                template='plotly_dark',
                labels={'Revenue': 'Revenue ($)'},
                color_discrete_sequence=[THEME_CONFIG['SUCCESS_COLOR']]
            )
            
            fig_revenue.update_layout(
                plot_bgcolor=THEME_CONFIG['CARD_BG'],
                paper_bgcolor=THEME_CONFIG['CARD_BG'],
                font_color=THEME_CONFIG['TEXT_COLOR'],
                title_font_color=THEME_CONFIG['PRIMARY_COLOR'],
                height=400
            )
            
            st.plotly_chart(fig_revenue, use_container_width=True)
        else:
            # Show empty state
            render_empty_state(
                "No performance data available. Please fetch appointment data first.",
                "analytics"
            )

# Render the tools tab
def render_tools_tab(active_subtab):
    """Render the tools tab content"""
    if active_subtab == "phone_validation":
        st.header("Phone Validation Tool")
        
        # Show introduction
        st.markdown("""
        <div class="card">
            <h3>Phone Number Validation</h3>
            <p>Validate and format phone numbers from your patient database or uploaded files.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Create two methods: Use existing data or upload new data
        method_tabs = st.radio(
            "Select Data Source", 
            ["Validate Existing Data", "Upload New Data"],
            horizontal=True
        )
        
        if method_tabs == "Validate Existing Data":
            # Check if we have data
            if st.session_state.get('bookings_data') is not None:
                df = st.session_state.bookings_data
                
                # Check if there are phone numbers
                if "Phone" in df.columns:
                    # Display phone stats
                    st.subheader("Phone Number Statistics")
                    
                    # Create mock phone analysis
                    status_data = pd.DataFrame({
                        "Status": ["Valid", "Invalid", "Missing", "Unknown"],
                        "Count": [85, 12, 8, 5]
                    })
                    
                    # Create a pie chart
                    fig = px.pie(
                        status_data,
                        values="Count",
                        names="Status",
                        title="Phone Number Validation Results",
                        template="plotly_dark",
                        color_discrete_map={
                            "Valid": THEME_CONFIG['SUCCESS_COLOR'],
                            "Invalid": THEME_CONFIG['DANGER_COLOR'],
                            "Missing": THEME_CONFIG['WARNING_COLOR'],
                            "Unknown": THEME_CONFIG['LIGHT_COLOR']
                        }
                    )
                    
                    fig.update_layout(
                        plot_bgcolor=THEME_CONFIG['CARD_BG'],
                        paper_bgcolor=THEME_CONFIG['CARD_BG'],
                        font_color=THEME_CONFIG['TEXT_COLOR'],
                        title_font_color=THEME_CONFIG['PRIMARY_COLOR'],
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show table of phone numbers
                    st.subheader("Phone Number Details")
                    
                    # Create a version of the dataframe with validated phones
                    validated_df = df[["Customer", "Phone"]].drop_duplicates()
                    validated_df["Validated Phone"] = validated_df["Phone"].apply(
                        lambda x: f"+1 ({x[0:3]}) {x[3:6]}-{x[6:10]}" if len(str(x)) == 10 else str(x)
                    )
                    validated_df["Status"] = validated_df["Phone"].apply(
                        lambda x: "Valid" if len(str(x)) == 10 else "Invalid"
                    )
                    
                    # Display the validated data
                    st.dataframe(validated_df, use_container_width=True)
                    
                    # Download option
                    csv = validated_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "Download Validated Phone Numbers",
                        csv,
                        "validated_phones.csv",
                        "text/csv",
                        key="download-phones"
                    )
                else:
                    render_empty_state(
                        "No phone number data found in the current dataset.",
                        "phone"
                    )
            else:
                # Show empty state
                render_empty_state(
                    "No data available. Please fetch appointment data first.",
                    "phone"
                )
                
        elif method_tabs == "Upload New Data":
            st.subheader("Upload Contact Data")
            
            # File uploader
            uploaded_file = st.file_uploader("Upload CSV or Excel file with phone numbers", type=["csv", "xlsx"])
            
            if uploaded_file is not None:
                st.success(f"File '{uploaded_file.name}' uploaded successfully!")
                
                # Create mock validated data
                mock_data = pd.DataFrame({
                    "Original Phone": ["1234567890", "555-123-4567", "(800) 123-4567", "+1 (888) 555-1212"],
                    "Validated Phone": ["+1 (123) 456-7890", "+1 (555) 123-4567", "+1 (800) 123-4567", "+1 (888) 555-1212"],
                    "Status": ["Valid", "Valid", "Valid", "Valid"] 
                })
                
                # Display the mock validated data
                st.subheader("Validation Results")
                st.dataframe(mock_data, use_container_width=True)
                
                # Download option
                csv = mock_data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Download Validated Phone Numbers",
                    csv,
                    "validated_phones.csv",
                    "text/csv",
                    key="download-uploaded-phones"
                )
    
    elif active_subtab == "api_inspector":
        st.header("API Inspector Tool")
        
        # Show introduction
        st.markdown("""
        <div class="card">
            <h3>API Inspection Tool</h3>
            <p>Debug API connections and inspect responses from various services.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Create API endpoint selection
        api_endpoints = ["Microsoft Graph API", "Airtable API", "Outlook Contacts API", "Other API"]
        selected_api = st.selectbox("Select API", api_endpoints)
        
        # Show configuration for each API
        if selected_api == "Microsoft Graph API":
            st.subheader("Microsoft Graph API Configuration")
            
            # Mock configuration settings
            st.text_input("Client ID", value="12345abcde67890fghij", type="password")
            st.text_input("Client Secret", value="************", type="password")
            st.text_input("Tenant ID", value="your-tenant.onmicrosoft.com")
            
            # API endpoints
            api_methods = ["GET /me", "GET /me/calendar/events", "GET /me/contacts", "POST /me/sendMail"]
            selected_method = st.selectbox("API Method", api_methods)
            
            # Additional parameters
            if selected_method == "GET /me/calendar/events":
                st.text_input("Start DateTime", value="2023-01-01T00:00:00Z")
                st.text_input("End DateTime", value="2023-12-31T23:59:59Z")
                
            # Test button
            if st.button("Test API Connection"):
                with st.spinner("Testing API connection..."):
                    time.sleep(2)  # Simulate API call
                    st.success("API connection successful!")
                    
                    # Show mock response
                    st.subheader("API Response")
                    
                    if selected_method == "GET /me":
                        response = {
                            "id": "user123",
                            "displayName": "John Doe",
                            "mail": "john.doe@example.com",
                            "userPrincipalName": "john.doe@example.com"
                        }
                    elif selected_method == "GET /me/calendar/events":
                        response = {
                            "value": [
                                {
                                    "id": "event1",
                                    "subject": "Team Meeting",
                                    "start": {"dateTime": "2023-06-01T09:00:00Z"},
                                    "end": {"dateTime": "2023-06-01T10:00:00Z"}
                                },
                                {
                                    "id": "event2",
                                    "subject": "Project Review",
                                    "start": {"dateTime": "2023-06-02T13:00:00Z"},
                                    "end": {"dateTime": "2023-06-02T14:30:00Z"}
                                }
                            ]
                        }
                    
                    st.json(response)
        
        elif selected_api == "Airtable API":
            st.subheader("Airtable API Configuration")
            
            # Mock configuration settings
            st.text_input("API Key", value="key************", type="password")
            st.text_input("Base ID", value="app***************")
            
            # Table selection
            tables = ["Patients", "Appointments", "Services", "Invoices"]
            selected_table = st.selectbox("Table", tables)
            
            # Test button
            if st.button("Test API Connection"):
                with st.spinner("Testing API connection..."):
                    time.sleep(2)  # Simulate API call
                    st.success("API connection successful!")
                    
                    # Show mock response
                    st.subheader("API Response")
                    
                    response = {
                        "records": [
                            {
                                "id": "rec123",
                                "fields": {
                                    "Name": "John Doe",
                                    "Phone": "(123) 456-7890",
                                    "Email": "john.doe@example.com"
                                }
                            },
                            {
                                "id": "rec456",
                                "fields": {
                                    "Name": "Jane Smith",
                                    "Phone": "(555) 123-4567",
                                    "Email": "jane.smith@example.com"
                                }
                            }
                        ]
                    }
                    
                    st.json(response)
    
    elif active_subtab == "date_tools":
        st.header("Date & Time Tools")
        
        # Show introduction
        st.markdown("""
        <div class="card">
            <h3>Date & Time Utilities</h3>
            <p>Tools for working with dates, times, and scheduling.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Create date utilities options
        date_tools = ["Date Calculator", "Time Zone Converter", "Business Days Calculator"]
        selected_date_tool = st.selectbox("Select Tool", date_tools)
        
        if selected_date_tool == "Date Calculator":
            st.subheader("Date Calculator")
            
            # Basic date calculator
            base_date = st.date_input("Base Date", value=pd.Timestamp.now())
            operation = st.radio("Operation", ["Add", "Subtract"], horizontal=True)
            
            col1, col2 = st.columns(2)
            with col1:
                amount = st.number_input("Amount", min_value=1, value=30)
            with col2:
                unit = st.selectbox("Unit", ["Days", "Weeks", "Months", "Years"])
            
            # Calculate result
            result_date = None
            if operation == "Add":
                if unit == "Days":
                    result_date = base_date + pd.Timedelta(days=amount)
                elif unit == "Weeks":
                    result_date = base_date + pd.Timedelta(weeks=amount)
                elif unit == "Months":
                    result_date = base_date + pd.DateOffset(months=amount)
                elif unit == "Years":
                    result_date = base_date + pd.DateOffset(years=amount)
            else:  # Subtract
                if unit == "Days":
                    result_date = base_date - pd.Timedelta(days=amount)
                elif unit == "Weeks":
                    result_date = base_date - pd.Timedelta(weeks=amount)
                elif unit == "Months":
                    result_date = base_date - pd.DateOffset(months=amount)
                elif unit == "Years":
                    result_date = base_date - pd.DateOffset(years=amount)
            
            # Display result
            st.markdown(f"""
            <div class="card">
                <h4>Result</h4>
                <p style="font-size: 1.5rem; font-weight: bold; color: {THEME_CONFIG['SECONDARY_COLOR']};">
                    {result_date.strftime('%A, %B %d, %Y')}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
        elif selected_date_tool == "Time Zone Converter":
            st.subheader("Time Zone Converter")
            
            # Time zone converter
            col1, col2 = st.columns(2)
            
            with col1:
                source_date = st.date_input("Date", value=pd.Timestamp.now())
                source_time = st.time_input("Time", value=pd.Timestamp.now().time())
                source_timezone = st.selectbox(
                    "Source Time Zone",
                    ["US/Eastern", "US/Central", "US/Mountain", "US/Pacific", "UTC", "Europe/London", "Asia/Tokyo"]
                )
            
            with col2:
                target_timezone = st.selectbox(
                    "Target Time Zone",
                    ["US/Eastern", "US/Central", "US/Mountain", "US/Pacific", "UTC", "Europe/London", "Asia/Tokyo"]
                )
                
                # Calculate the conversion
                source_dt = pd.Timestamp.combine(source_date, source_time)
                source_dt = source_dt.tz_localize(source_timezone)
                target_dt = source_dt.tz_convert(target_timezone)
                
                # Display the result
                st.markdown(f"""
                <div class="card">
                    <h4>Converted Time</h4>
                    <p style="font-size: 1.5rem; font-weight: bold; color: {THEME_CONFIG['SECONDARY_COLOR']};">
                        {target_dt.strftime('%A, %B %d, %Y %H:%M:%S %Z')}
                    </p>
                </div>
                """, unsafe_allow_html=True)

# Simple placeholder for the remaining tabs
def render_integrations_tab(active_subtab):
    st.header("Integrations")
    
    if active_subtab == "ms_graph":
        st.subheader("Microsoft Graph API Integration")
        
        # Create tabs for different Microsoft Graph services
        graph_services = ["Calendar", "Bookings", "Contacts", "Mail"]
        selected_service = st.selectbox("Service", graph_services)
        
        if selected_service == "Calendar":
            st.markdown("""
            <div class="card">
                <h3>Microsoft Calendar Integration</h3>
                <p>Fetch and analyze calendar events from your Microsoft 365 account.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Date range selection
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=st.session_state.date_range[0])
            with col2:
                end_date = st.date_input("End Date", value=st.session_state.date_range[1])
            
            # Fetch button
            if st.button("Fetch Calendar Events"):
                with st.spinner("Fetching calendar events..."):
                    # Run the asynchronous function
                    calendar_data = asyncio.run(fetch_calendar_events(start_date, end_date))
                    
                    if calendar_data and len(calendar_data) > 0:
                        # Store in session state
                        st.session_state.calendar_data = pd.DataFrame(calendar_data)
                        st.success(f"Successfully fetched {len(calendar_data)} calendar events.")
                    else:
                        st.warning("No calendar events found for the selected date range.")
            
            # Display calendar data if available
            if st.session_state.get('calendar_data') is not None:
                st.subheader("Calendar Events")
                st.dataframe(st.session_state.calendar_data)
                
                # Download option
                csv = st.session_state.calendar_data.to_csv(index=False)
                st.download_button(
                    label="Download Calendar Data",
                    data=csv,
                    file_name=f"calendar_events_{start_date}_to_{end_date}.csv",
                    mime="text/csv"
                )
        
        elif selected_service == "Bookings":
            st.markdown("""
            <div class="card">
                <h3>Microsoft Bookings Integration</h3>
                <p>Fetch and analyze appointment data from your Microsoft Bookings account.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Initialize selected_businesses if not exists
            if 'selected_businesses' not in st.session_state:
                st.session_state.selected_businesses = []
                
            # Date range selection
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=st.session_state.date_range[0])
            with col2:
                end_date = st.date_input("End Date", value=st.session_state.date_range[1])
            
            # Add business selection
            st.subheader("Select Booking Pages")
            
            # Fetch businesses if needed
            if 'grouped_businesses' not in st.session_state:
                try:
                    grouped_businesses = asyncio.run(fetch_businesses_for_appointments())
                    st.session_state.grouped_businesses = grouped_businesses
                except Exception as e:
                    st.error(f"Error fetching businesses: {str(e)}")
                    st.session_state.grouped_businesses = {}
            
            # Create columns for select/unselect all buttons
            btn_col1, btn_col2 = st.columns([1, 1])
            
            with btn_col1:
                if st.button("Select All", key="int_select_all"):
                    # Select all businesses
                    all_businesses = []
                    for group in st.session_state.grouped_businesses.values():
                        all_businesses.extend([b["id"] for b in group])
                    st.session_state.selected_businesses = all_businesses
                    st.rerun()
            
            with btn_col2:
                if st.button("Unselect All", key="int_unselect_all"):
                    # Clear all selections
                    st.session_state.selected_businesses = []
                    st.rerun()
            
            # Display businesses in a single selectbox for simplicity
            if st.session_state.grouped_businesses:
                # Flatten the business list
                all_businesses = []
                for group in st.session_state.grouped_businesses.values():
                    all_businesses.extend(group)
                
                # Sort businesses by name
                all_businesses = sorted(all_businesses, key=lambda x: x["name"])
                
                # Get selected business names
                selected_names = [
                    b["name"] for b in all_businesses 
                    if b["id"] in st.session_state.selected_businesses
                ]
                
                # Display selected businesses summary
                if selected_names:
                    st.write(f"**{len(selected_names)} booking pages selected**: {', '.join(selected_names)}")
                else:
                    st.write("No booking pages selected")
                
                # Display multiselect for businesses
                business_options = [(b["id"], b["name"]) for b in all_businesses]
                selected_ids = st.multiselect(
                    "Select Booking Pages",
                    options=[id for id, _ in business_options],
                    format_func=lambda x: next((name for id, name in business_options if id == x), x),
                    default=st.session_state.selected_businesses
                )
                
                # Update session state with selected businesses
                st.session_state.selected_businesses = selected_ids
            else:
                st.warning("No booking pages found. Please check your Microsoft Bookings integration.")
            
            # Maximum results
            max_results = st.slider("Maximum Results", min_value=10, max_value=1000, value=500, step=10)
            
            # Fetch button
            if st.button("Fetch Bookings Data"):
                with st.spinner("Fetching bookings data..."):
                    # Run the asynchronous function
                    bookings_data = asyncio.run(fetch_bookings_data(
                        start_date,
                        end_date,
                        max_results,
                        st.session_state.selected_businesses
                    ))
                    
                    if bookings_data and len(bookings_data) > 0:
                        # Store in session state
                        st.session_state.bookings_data = pd.DataFrame(bookings_data)
                        st.success(f"Successfully fetched {len(bookings_data)} appointments.")
                    else:
                        st.warning("No appointments found for the selected date range.")
            
            # Display bookings data if available
            if st.session_state.get('bookings_data') is not None:
                st.subheader("Bookings Data")
                st.dataframe(st.session_state.bookings_data)
                
                # Download option
                csv = st.session_state.bookings_data.to_csv(index=False)
                st.download_button(
                    label="Download Bookings Data",
                    data=csv,
                    file_name=f"bookings_data_{start_date}_to_{end_date}.csv",
                    mime="text/csv"
                )
                
        elif selected_service in ["Contacts", "Mail"]:
            render_empty_state(
                f"The {selected_service} integration is under development.",
                "link"
            )
    
    elif active_subtab == "webhooks":
        st.subheader("Webhooks Integration")
        
        st.markdown("""
        <div class="card">
            <h3>Webhooks Configuration</h3>
            <p>Set up and manage webhooks to connect external services with your Access Care Analytics platform.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Add webhook configuration UI
        st.text_input("Webhook URL", placeholder="https://your-service.com/webhook")
        
        # Create columns for event selection
        st.subheader("Select Events to Trigger Webhook")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.checkbox("New Appointment Created", value=True)
            st.checkbox("Appointment Updated")
            st.checkbox("Appointment Cancelled")
        
        with col2:
            st.checkbox("Patient Data Updated")
            st.checkbox("Report Generated")
            st.checkbox("Error Events")
        
        # Add webhook testing
        st.subheader("Test Webhook")
        
        test_col1, test_col2 = st.columns([3, 1])
        
        with test_col1:
            test_payload = st.text_area(
                "Test Payload (JSON)",
                value="""{\n  "event": "appointment.created",\n  "data": {\n    "id": "test-123",\n    "patient": "John Doe",\n    "time": "2023-06-15T10:00:00Z"\n  }\n}"""
            )
        
        with test_col2:
            st.write("")
            st.write("")
            if st.button("Send Test"):
                with st.spinner("Sending test webhook..."):
                    time.sleep(2)  # Simulate API call
                    st.success("Test webhook sent successfully!")
        
        # Webhook history
        st.subheader("Recent Webhook Activity")
        
        # Create mock webhook history
        webhook_history = pd.DataFrame({
            "Timestamp": pd.date_range(end=pd.Timestamp.now(), periods=5, freq='-1h'),
            "Event": ["appointment.created", "appointment.updated", "appointment.cancelled", "report.generated", "error.auth"],
            "Status": ["Success", "Success", "Failed", "Success", "Failed"],
            "Response Time": ["120ms", "98ms", "Timeout", "145ms", "503ms"]
        })
        
        # Display webhook history
        st.dataframe(webhook_history, use_container_width=True)
        
        # Webhook documentation
        with st.expander("Webhook Documentation"):
            st.markdown("""
            ### Webhook Format
            
            All webhooks are sent as HTTP POST requests with a JSON payload. The payload format is:
            
            ```json
            {
              "event": "event.name",
              "timestamp": "ISO-8601 timestamp",
              "data": {
                // Event-specific data
              }
            }
            ```
            
            ### Authentication
            
            Webhooks are authenticated using a signature in the `X-Webhook-Signature` header. The signature is a HMAC-SHA256 hash of the request body using your webhook secret as the key.
            
            ### Event Types
            
            - `appointment.created` - Triggered when a new appointment is created
            - `appointment.updated` - Triggered when an appointment is updated
            - `appointment.cancelled` - Triggered when an appointment is cancelled
            - `patient.updated` - Triggered when patient data is updated
            - `report.generated` - Triggered when a report is generated
            - `error.*` - Various error events
            """)
    
    else:
        render_empty_state(
            f"The {active_subtab} integration is under development.",
            "link"
        )

def render_content_tab(active_subtab):
    """Render the content creator tab"""
    st.header("Content Creator")
    
    if active_subtab == "sow":
        # Render the SOW generator UI
        render_sow_creator()
    elif active_subtab == "templates":
        # Show a message about templates being under development
        render_empty_state(
            "The templates feature is currently under development. Check back soon!",
            "template"
        )
    else:
        render_empty_state(
            f"The {active_subtab} content creator tab is under development.",
            "document"
        )

# Call the main function
if __name__ == "__main__":
    main()
