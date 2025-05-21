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
from thefuzz import fuzz # For fuzzy matching
import traceback

# Import custom modules
from config import THEME_CONFIG, DATE_PRESETS, APP_TAGLINE, LOGO_PATH, AIRTABLE_CONFIG
from ms_integrations import fetch_bookings_data, fetch_calendar_events, fetch_businesses_for_appointments, track_booking_cancellations, fetch_cancellation_emails
from phone_formatter import format_phone_strict, create_phone_analysis, format_phone_dataframe, prepare_outlook_contacts, create_appointments_flow, process_uploaded_phone_list
from airtable_integration import render_airtable_tabs, get_airtable_credentials, fetch_airtable_table
from icons import render_logo, render_tab_bar, render_icon, render_empty_state, render_info_box
from sow_creator import render_sow_creator
from airtable_export import render_export_options, export_bookings_to_airtable, export_patients_to_airtable, analyze_airtable_data

# Ensure thefuzz is properly imported
try:
    from thefuzz import fuzz
except ImportError:
    # If thefuzz is not available, provide a stub implementation
    print("WARNING: thefuzz module not found. Fuzzy matching will not work.")
    class DummyFuzz:
        @staticmethod
        def ratio(str1, str2):
            print(f"WARNING: Using dummy fuzz.ratio for {str1} and {str2}")
            return 0
    fuzz = DummyFuzz

# Page configuration
st.set_page_config(
    page_title="MS Booking",
    page_icon="🏠",
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
    # Use pandas Timestamp to ensure consistent datetime handling
    today = pd.Timestamp.now().date()
    thirty_days_ago = (pd.Timestamp.now() - pd.Timedelta(days=30)).date()
    st.session_state.date_range = (thirty_days_ago, today)
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
                st.markdown('<div style="display: flex; justify-content: center; align-items: center; height: 100%;">', unsafe_allow_html=True)
                st.image(big_logo_path, width=120, output_format="PNG", use_column_width="never", clamp=True)
                st.markdown('</div>', unsafe_allow_html=True)
                logo_displayed = True
            except Exception as e:
                logo_displayed = False
        
        if not logo_displayed and os.path.exists(logo_path) and os.path.getsize(logo_path) > 100:
            try:
                st.markdown('<div style="display: flex; justify-content: center; align-items: center; height: 100%;">', unsafe_allow_html=True)
                st.image(logo_path, width=80, output_format="PNG", use_column_width="never", clamp=True)
                st.markdown('</div>', unsafe_allow_html=True)
                logo_displayed = True
            except Exception as e:
                logo_displayed = False
        
        if not logo_displayed:
            st.markdown('<div style="display: flex; justify-content: center; align-items: center; height: 100%;">', unsafe_allow_html=True)
            st.markdown(render_logo(width="80px"), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <h1 class="app-title">Access Care Analytics Dashboard</h1>
        <p class="app-subtitle">{APP_TAGLINE}</p>
        """, unsafe_allow_html=True)

# Tab definitions for the main navigation
MAIN_TABS = {
    "dashboard": {"icon": "analytics", "label": "MS Booking"},
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
        "outlook_prep": {"icon": "bi-person-lines-fill", "label": "Outlook Import Prep"}, # New Sub-tab
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
        # Remove logo section and just start with navigation
        st.markdown("---")
        
        # Navigation section
        st.markdown("""
        <style>
        .sidebar-nav {
            padding: 8px 0;
        }
        .nav-link {
            padding: 6px 12px;
            margin: 3px 0;
            border-radius: var(--border-radius);
            background-color: transparent;
            transition: var(--transition);
            display: flex;
            align-items: center;
            text-decoration: none;
            color: var(--color-text);
        }
        .nav-link:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
        .nav-link.active {
            background-color: rgba(62, 147, 236, 0.2);
            font-weight: 500;
        }
        .nav-icon {
            margin-right: 8px;
            width: 18px;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .sidebar-title {
            font-family: var(--font-primary);
            font-weight: 500;
            color: var(--color-accent);
            margin-bottom: 8px;
            font-size: 0.875rem;
            text-align: left;
            padding-left: 8px;
        }
        .version-info {
            position: absolute;
            bottom: 8px;
            left: 8px;
            font-size: 0.6875rem;
            color: var(--color-secondary);
            opacity: 0.7;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("<div class='sidebar-title'>Navigation</div>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-nav'>", unsafe_allow_html=True)
        
        # Navigation items with Bootstrap Icons
        nav_items = {
            "dashboard": {"icon": "bi-house", "label": "Main"},
            "tools": {"icon": "bi-tools", "label": "Tools"},
            "integrations": {"icon": "bi-link", "label": "Integrations"},
            "content": {"icon": "bi-file-text", "label": "Content Creator"}
        }
        
        for key, item in nav_items.items():
            active_class = "active" if st.session_state.active_tab == key else ""
            col1, col2 = st.columns([1, 4])
            with col1:
                st.markdown(f"<div class='nav-icon'><i class='{item['icon']}' style='font-size: 0.875rem;'></i></div>", unsafe_allow_html=True)
            with col2:
                if st.button(item["label"], key=f"nav_{key}", use_container_width=True):
                    st.session_state.active_tab = key
                    st.rerun()
        
        # Add settings section at the bottom with small margin
        st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("<div class='sidebar-title'><i class='bi bi-gear'></i> Settings</div>", unsafe_allow_html=True)
        with st.expander(""):
            st.checkbox("Dark Mode", key="dark_mode")
            st.selectbox("Theme", ["Default", "Light", "Dark"])
        
        # Add version info
        st.markdown("<div class='version-info'>v1.0.0</div>", unsafe_allow_html=True)
    
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
                            customer_search = st.text_input("Search Customer", key="data_table_customer_search")
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
                                customer_search = st.text_input("Search Customer", key="cancellations_customer_search")
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
                            # Make sure the Date column is datetime type before using .dt accessor
                            if not pd.api.types.is_datetime64_dtype(timeline_df['Date']):
                                try:
                                    # Try to convert to datetime if it's not already
                                    timeline_df['Date'] = pd.to_datetime(timeline_df['Date'], errors='coerce')
                                    # Drop any rows where conversion failed
                                    timeline_df = timeline_df.dropna(subset=['Date'])
                                except Exception as e:
                                    st.error(f"Error converting dates: {str(e)}")
                                    st.info("Unable to create timeline visualization due to date format issues.")
                                    return
                            
                            # Now safely extract the date component
                            if not timeline_df.empty and pd.api.types.is_datetime64_dtype(timeline_df['Date']):
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
                
                # Add Patient Analysis Section
                st.subheader("Patient Analysis")
                
                # Analyze unique patients
                unique_patients, service_distribution = analyze_unique_patients(filtered_df)
                
                if not unique_patients.empty:
                    # Create two columns
                    patient_cols = st.columns(2)
                    
                    with patient_cols[0]:
                        # Display unique patient count
                        st.metric("Unique Patients", len(unique_patients))
                        
                        # Display unique patients table
                        st.write("#### Unique Patients by Email")
                        st.dataframe(
                            unique_patients[["Email", "Customer", "Phone"]],
                            use_container_width=True
                        )
                    
                    with patient_cols[1]:
                        if not service_distribution.empty:
                            # Create pie chart of service distribution
                            st.write("#### Services per Patient")
                            fig = px.pie(
                                service_distribution,
                                values="Patient_Count",
                                names="Number_of_Services",
                                title="Number of Services per Patient",
                                hover_data=["Percentage"],
                                labels={
                                    "Number_of_Services": "Number of Services",
                                    "Patient_Count": "Number of Patients",
                                    "Percentage": "Percentage of Patients"
                                }
                            )
                            
                            # Customize pie chart
                            fig.update_traces(
                                textinfo="value+percent",
                                textposition="inside",
                                insidetextorientation="radial"
                            )
                            
                            # Add annotations to explain the chart
                            fig.add_annotation(
                                text="Shows how many services each patient has used",
                                xref="paper", yref="paper",
                                x=0.5, y=-0.15,
                                showarrow=False
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Add insights about service usage
                            single_service = service_distribution[service_distribution['Number_of_Services'] == 1]['Patient_Count'].values[0] if 1 in service_distribution['Number_of_Services'].values else 0
                            multi_service = sum(service_distribution[service_distribution['Number_of_Services'] > 1]['Patient_Count']) if not service_distribution.empty else 0
                            
                            st.markdown(f"""
                            <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 10px;">
                                <strong>Insights:</strong>
                                <ul>
                                    <li>{single_service} patients ({single_service/len(unique_patients)*100:.1f}%) used only 1 service</li>
                                    <li>{multi_service} patients ({multi_service/len(unique_patients)*100:.1f}%) used multiple services</li>
                                </ul>
                            </div>
                            """, unsafe_allow_html=True)
                
                # Add more detailed patient analysis if there's enough data
                if len(unique_patients) > 0:
                    with st.expander("📊 Detailed Patient Service Analysis"):
                        st.write("#### Most Popular Services by Patient Count")
                        
                        # Count patients per service
                        if 'Service' in filtered_df.columns:
                            # Get unique patient-service combinations
                            patient_services = filtered_df[['Email', 'Service']].drop_duplicates()
                            
                            # Count patients per service
                            service_patient_counts = patient_services.groupby('Service')['Email'].nunique().reset_index()
                            service_patient_counts.columns = ['Service', 'Patient_Count']
                            service_patient_counts = service_patient_counts.sort_values('Patient_Count', ascending=False)
                            
                            # Create bar chart of top services by patient count
                            fig = px.bar(
                                service_patient_counts.head(10),
                                x='Service',
                                y='Patient_Count',
                                title='Top 10 Services by Number of Patients',
                                text='Patient_Count',  # Use the column directly
                                color='Patient_Count',
                                color_continuous_scale='Viridis'
                            )
                            
                            # Add proper text formatting
                            fig.update_traces(texttemplate='%{text:,}', textposition='outside')
                            
                            fig.update_layout(
                                xaxis_title='Service',
                                yaxis_title='Number of Patients',
                                xaxis={'categoryorder': 'total descending'},
                                height=400
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Patient visit frequency analysis
                        st.write("#### Patient Visit Frequency")
                        
                        # Count appointments per patient
                        visit_frequency = filtered_df.groupby('Email').size().reset_index(name='Visit_Count')
                        
                        # Create frequency categories
                        visit_frequency['Frequency_Category'] = pd.cut(
                            visit_frequency['Visit_Count'],
                            bins=[0, 1, 2, 3, 5, 10, float('inf')],
                            labels=['1 visit', '2 visits', '3 visits', '4-5 visits', '6-10 visits', '10+ visits'],
                            right=False
                        )
                        
                        # Count patients per frequency category
                        frequency_counts = visit_frequency['Frequency_Category'].value_counts().reset_index()
                        frequency_counts.columns = ['Frequency', 'Patient_Count']
                        frequency_counts = frequency_counts.sort_values('Frequency')
                        
                        # Create bar chart of visit frequency
                        fig = px.bar(
                            frequency_counts,
                            x='Frequency',
                            y='Patient_Count',
                            title='Patient Visit Frequency Distribution',
                            text='Patient_Count',  # Use the column directly
                            color='Patient_Count',
                            color_continuous_scale='Viridis'
                        )
                        
                        # Add proper text formatting
                        fig.update_traces(texttemplate='%{text:,}', textposition='outside')
                        
                        fig.update_layout(
                            xaxis_title='Visit Frequency',
                            yaxis_title='Number of Patients',
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No patient data available for analysis.")
                
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
                    
                    # Filter by date range using timestamps for comparison
                    try:
                        # Make copy of filtered_df
                        creation_df = filtered_df.copy()
                        
                        # Convert the Created Date column to datetime if not already
                        if not pd.api.types.is_datetime64_dtype(creation_df['Created Date']):
                            creation_df['Created Date'] = pd.to_datetime(creation_df['Created Date'])
                        
                        # Convert analysis_start_date and analysis_end_date to Timestamps
                        start_ts = pd.Timestamp(analysis_start_date)
                        end_ts = pd.Timestamp(analysis_end_date).replace(hour=23, minute=59, second=59) # Ensure end_ts includes the whole day

                        # Ensure 'Created Date' is timezone-naive for comparison if start_ts/end_ts are naive
                        if creation_df['Created Date'].dt.tz is not None and start_ts.tz is None:
                            creation_df['Created Date'] = creation_df['Created Date'].dt.tz_localize(None)
                        elif creation_df['Created Date'].dt.tz is None and start_ts.tz is not None:
                            # This case is less likely if analysis_start_date is from st.date_input, but handle defensively
                            start_ts = start_ts.tz_localize(None)
                            end_ts = end_ts.tz_localize(None)
                        elif creation_df['Created Date'].dt.tz is not None and start_ts.tz is not None and creation_df['Created Date'].dt.tz != start_ts.tz:
                            # If both have timezones but they are different, convert 'Created Date' to UTC (a common standard) 
                            # and make sure start_ts/end_ts are also UTC or naive.
                            # For simplicity here, we'll make 'Created Date' naive. A more robust solution might involve converting all to UTC.
                            creation_df['Created Date'] = creation_df['Created Date'].dt.tz_localize(None)
                            start_ts = start_ts.tz_localize(None) # Assuming start_ts/end_ts should also be naive if we do this
                            end_ts = end_ts.tz_localize(None)

                        creation_df = creation_df[
                            (creation_df['Created Date'] >= start_ts) &
                            (creation_df['Created Date'] <= end_ts)
                        ]
                        
                        if not creation_df.empty:
                            # Rest of the code remains the same
                            # Convert timestamps to naive datetime to avoid timezone warnings
                            if 'Created Date' in creation_df.columns and pd.api.types.is_datetime64_dtype(creation_df['Created Date']):
                                # Make a copy to avoid warnings
                                creation_df = creation_df.copy()
                                # Remove timezone info properly
                                if hasattr(creation_df['Created Date'].dtype, 'tz') and creation_df['Created Date'].dtype.tz is not None:
                                    creation_df['Created Date'] = creation_df['Created Date'].dt.tz_localize(None)
                            
                            # Group by selected frequency - using a different approach to avoid period warnings
                            # Instead of using to_period, use date components directly
                            if freq_map[date_level] == 'D':
                                # Daily - just use the date component
                                creation_df['Period'] = creation_df['Created Date'].dt.date
                            elif freq_map[date_level] == 'W':
                                # Weekly - use start of week
                                creation_df['Period'] = creation_df['Created Date'].dt.to_period('W').dt.start_time.dt.date
                            elif freq_map[date_level] == 'M':
                                # Monthly - use year-month
                                creation_df['Period'] = creation_df['Created Date'].dt.strftime('%Y-%m')
                            elif freq_map[date_level] == 'Q':
                                # Quarterly - use year-quarter
                                creation_df['Period'] = creation_df['Created Date'].dt.to_period('Q').astype(str)
                            elif freq_map[date_level] == 'Y':
                                # Yearly - use year
                                creation_df['Period'] = creation_df['Created Date'].dt.year.astype(str)
                            else:
                                # Default to daily
                                creation_df['Period'] = creation_df['Created Date'].dt.date
                            
                            # Group by Period
                            creation_counts = creation_df.groupby('Period').size().reset_index(name='Count')
                            
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
                    except Exception as e:
                        st.error(f"Error processing booking creation analysis: {str(e)}")
                        # Add traceback for better error detection
                        st.code(traceback.format_exc(), language="python")
                        # Also print to terminal for easier debugging
                        print(f"ERROR in booking creation analysis: {str(e)}")
                        print(traceback.format_exc())
                
                # Analysis based on booking date
                if 'Start Date' in filtered_df.columns:
                    st.subheader("Booking Date Analysis")
                    
                    
                    # Filter by date range using timestamps for comparison
                    try:
                        # Make copy of filtered_df
                        booking_df = filtered_df.copy()
                        
                        # Convert the Start Date column to datetime if not already
                        if not pd.api.types.is_datetime64_dtype(booking_df['Start Date']):
                            booking_df['Start Date'] = pd.to_datetime(booking_df['Start Date'])

                        # Convert analysis_start_date and analysis_end_date to Timestamps
                        start_ts = pd.Timestamp(analysis_start_date)
                        end_ts = pd.Timestamp(analysis_end_date).replace(hour=23, minute=59, second=59)

                        # Ensure 'Start Date' is timezone-naive for comparison similar to 'Created Date' logic above
                        if booking_df['Start Date'].dt.tz is not None and start_ts.tz is None:
                            booking_df['Start Date'] = booking_df['Start Date'].dt.tz_localize(None)
                        elif booking_df['Start Date'].dt.tz is None and start_ts.tz is not None:
                            start_ts = start_ts.tz_localize(None)
                            end_ts = end_ts.tz_localize(None)
                        elif booking_df['Start Date'].dt.tz is not None and start_ts.tz is not None and booking_df['Start Date'].dt.tz != start_ts.tz:
                            booking_df['Start Date'] = booking_df['Start Date'].dt.tz_localize(None)
                            start_ts = start_ts.tz_localize(None)
                            end_ts = end_ts.tz_localize(None)

                        booking_df = booking_df[
                            (booking_df['Start Date'] >= start_ts) &
                            (booking_df['Start Date'] <= end_ts)
                        ]
                        
                        if not booking_df.empty:
                            # Rest of the code remains the same
                            # Convert timestamps to naive datetime to avoid timezone warnings
                            if 'Start Date' in booking_df.columns and pd.api.types.is_datetime64_dtype(booking_df['Start Date']):
                                # Make a copy to avoid warnings
                                booking_df = booking_df.copy()
                                # Remove timezone info properly
                                if hasattr(booking_df['Start Date'].dtype, 'tz') and booking_df['Start Date'].dtype.tz is not None:
                                    booking_df['Start Date'] = booking_df['Start Date'].dt.tz_localize(None)
                            
                            # Group by selected frequency - using a different approach to avoid period warnings
                            # Instead of using to_period, use date components directly
                            if freq_map[date_level] == 'D':
                                # Daily - just use the date component
                                booking_df['Period'] = booking_df['Start Date'].dt.date
                            elif freq_map[date_level] == 'W':
                                # Weekly - use start of week
                                booking_df['Period'] = booking_df['Start Date'].dt.to_period('W').dt.start_time.dt.date
                            elif freq_map[date_level] == 'M':
                                # Monthly - use year-month
                                booking_df['Period'] = booking_df['Start Date'].dt.strftime('%Y-%m')
                            elif freq_map[date_level] == 'Q':
                                # Quarterly - use year-quarter
                                booking_df['Period'] = booking_df['Start Date'].dt.to_period('Q').astype(str)
                            elif freq_map[date_level] == 'Y':
                                # Yearly - use year
                                booking_df['Period'] = booking_df['Start Date'].dt.year.astype(str)
                            else:
                                # Default to daily
                                booking_df['Period'] = booking_df['Start Date'].dt.date
                            
                            if 'Business' in booking_df.columns:
                                # Group by business and period
                                business_counts = booking_df.groupby(['Business', 'Period']).size().reset_index(name='Count')
                                
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
                    except Exception as e:
                        st.error(f"Error processing booking date analysis: {str(e)}")
                
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
                                    text='Total Appointments'  # Use the column directly
                                )
                                
                                # Add proper text formatting
                                fig_yearly_totals.update_traces(texttemplate='%{text:,}', textposition='outside')

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
                    <div class="metric-label">Revenue Per Appointment</div>
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
        
        # Radio button to select data source
        source_choice = st.radio(
            "Select Data Source for Phone Validation:",
            ("Validate from Fetched Appointments", "Upload New File"),
            horizontal=True,
            key="phone_validation_source_choice"
        )
        st.markdown("<hr style='margin-top: 0.5rem; margin-bottom: 1rem;'>", unsafe_allow_html=True)

        if source_choice == "Validate from Fetched Appointments":
            st.markdown("#### Validate Phones from Fetched Appointment Data")
            if 'bookings_data' in st.session_state and st.session_state.bookings_data is not None and not st.session_state.bookings_data.empty:
                df_bookings = st.session_state.bookings_data
                if 'Phone' in df_bookings.columns:
                    st.info(f"Found {len(df_bookings)} records in fetched appointments. The 'Phone' column will be used for validation.")
                    
                    # Use a different session state key for results from bookings data to avoid clashes
                    if 'phone_validation_results_bookings' not in st.session_state:
                        st.session_state.phone_validation_results_bookings = None
                    if 'phone_validation_summary_bookings' not in st.session_state:
                        st.session_state.phone_validation_summary_bookings = None

                    if st.button("Validate Phones from Appointments", type="primary", use_container_width=True, key="validate_phones_from_bookings_btn"):
                        with st.spinner("Validating phone numbers from appointments..."):
                            # --- Replicate validation logic --- 
                            results = []
                            valid_count = 0
                            invalid_count = 0
                            empty_count = 0
                            for index, row in df_bookings.iterrows():
                                original_phone = str(row['Phone']) if pd.notna(row['Phone']) else ""
                                formatted_phone, is_valid = format_phone_strict(original_phone)
                                status = "Empty" if not original_phone else ("Valid" if is_valid else "Invalid")
                                if status == "Valid": valid_count += 1
                                elif status == "Invalid": invalid_count += 1
                                else: empty_count += 1
                                
                                result_row = row.to_dict()
                                result_row['Original Phone Value'] = original_phone
                                result_row['Formatted Phone'] = formatted_phone
                                result_row['Validation Status'] = status
                                results.append(result_row)
                            # --- End Replicated Logic ---
                            results_df_bookings = pd.DataFrame(results)
                            st.session_state.phone_validation_results_bookings = results_df_bookings
                            st.session_state.phone_validation_summary_bookings = {
                                "total_processed": len(results_df_bookings),
                                "valid": valid_count, "invalid": invalid_count, "empty": empty_count
                            }
                            st.success(f"Processed {len(results_df_bookings)} phone numbers from appointments.")
                    
                    # Display results if available (for bookings data)
                    if st.session_state.phone_validation_results_bookings is not None:
                        results_df_to_display = st.session_state.phone_validation_results_bookings
                        summary_to_display = st.session_state.phone_validation_summary_bookings
                        # Call a helper to display results (to avoid code duplication)
                        display_phone_validation_output(results_df_to_display, summary_to_display, results_type="bookings")

                else:
                    st.warning("No 'Phone' column found in the fetched appointments data.")
            else:
                st.warning("No appointments data has been fetched yet. Please go to Dashboard > Appointments to fetch data first.")
        
        elif source_choice == "Upload New File":
            st.markdown("#### Validate Phones from Uploaded File")
            # Existing file upload and validation logic starts here
            # Initialize session state for phone validation results (for uploaded file)
            if 'phone_validation_results_upload' not in st.session_state:
                st.session_state.phone_validation_results_upload = None
            if 'phone_validation_summary_upload' not in st.session_state:
                st.session_state.phone_validation_summary_upload = None
            # Ensure the introduction/card for this section is present
            st.markdown("""
            <div class="card">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
                    <i class="bi bi-upload" style="font-size: 1.5rem; color: var(--color-primary-action);"></i>
                    <h3 style="margin:0;">Upload Contact File</h3>
                </div>
                <p>Upload a CSV or Excel file with contact data to validate phone numbers.</p>
            </div>
            """, unsafe_allow_html=True)

            uploaded_file = st.file_uploader(
                "Upload CSV or Excel file", 
                type=["csv", "xlsx"], 
                key="phone_file_uploader",
                help="Ensure your file has a header row. You'll be asked to select the phone number column after upload."
            )
            
            if uploaded_file is not None:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df_upload = pd.read_csv(uploaded_file)
                    else:
                        df_upload = pd.read_excel(uploaded_file)
                    
                    st.success(f"File '{uploaded_file.name}' uploaded successfully with {len(df_upload)} rows.")
                    st.session_state.uploaded_phone_df = df_upload

                except Exception as e:
                    st.error(f"Error reading file: {e}")
                    st.session_state.uploaded_phone_df = None

                # This is the block that was duplicated. We want to keep only one instance of it.
                if "uploaded_phone_df" in st.session_state and st.session_state.uploaded_phone_df is not None:
                    df_upload = st.session_state.uploaded_phone_df
                    if not df_upload.empty:
                        st.markdown("#### Select Phone Number Column")
                        column_options = [""] + df_upload.columns.tolist()
                        phone_column = st.selectbox(
                            "Which column contains the phone numbers?", 
                            column_options,
                            index=0,
                            key="phone_column_selector_unique", # Changed key to avoid conflict if GUI renders faster than state updates
                            help="Choose the column from your uploaded file that has the phone numbers to validate."
                        )

                        if phone_column:
                            if st.button("Validate Phone Numbers", type="primary", use_container_width=True, key="validate_phones_button_unique"): # Changed key
                                with st.spinner(f"Validating phone numbers in column '{phone_column}'... Please wait."):
                                    results = []
                                    valid_count = 0
                                    invalid_count = 0
                                    empty_count = 0
                                    
                                    for index, row in df_upload.iterrows():
                                        original_phone = str(row[phone_column]) if pd.notna(row[phone_column]) else ""
                                        formatted_phone, is_valid = format_phone_strict(original_phone)
                                        
                                        status = ""
                                        if not original_phone:
                                            status = "Empty"
                                            empty_count += 1
                                        elif is_valid:
                                            status = "Valid"
                                            valid_count +=1
                                        else:
                                            status = "Invalid"
                                            invalid_count +=1
                                        
                                        result_row = row.to_dict()
                                        result_row['Original Phone Value'] = original_phone
                                        result_row['Formatted Phone'] = formatted_phone
                                        result_row['Validation Status'] = status
                                        results.append(result_row)
                                    
                                    results_df_upload = pd.DataFrame(results) # Use a different df name
                                    st.session_state.phone_validation_results_upload = results_df_upload
                                    
                                    st.session_state.phone_validation_summary_upload = {
                                        "total_processed": len(results_df_upload),
                                        "valid": valid_count,
                                        "invalid": invalid_count,
                                        "empty": empty_count
                                    }
                                    st.success(f"Processed {len(results_df_upload)} phone numbers from uploaded file.")
            
            # Display results if available (for uploaded file)
            if st.session_state.phone_validation_results_upload is not None:
                results_df_to_display = st.session_state.phone_validation_results_upload
                summary_to_display = st.session_state.phone_validation_summary_upload
                display_phone_validation_output(results_df_to_display, summary_to_display, results_type="upload")

    elif active_subtab == "outlook_prep": # New sub-tab handler
        render_outlook_import_prep_tool()

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
            st.text_input("Client ID", value="12345abcde67890fghij", type="password", key="graph_client_id")
            st.text_input("Client Secret", value="************", type="password", key="graph_client_secret")
            st.text_input("Tenant ID", value="your-tenant.onmicrosoft.com", key="graph_tenant_id")
            
            # API endpoints
            api_methods = ["GET /me", "GET /me/calendar/events", "GET /me/contacts", "POST /me/sendMail"]
            selected_method = st.selectbox("API Method", api_methods)
            
            # Additional parameters
            if selected_method == "GET /me/calendar/events":
                st.text_input("Start DateTime", value="2023-01-01T00:00:00Z", key="graph_start_datetime")
                st.text_input("End DateTime", value="2023-12-31T23:59:59Z", key="graph_end_datetime")
                
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
            st.text_input("API Key", value="key************", type="password", key="airtable_api_key")
            st.text_input("Base ID", value="app***************", key="airtable_base_id")
            
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
                
                # Create a function to display business names instead of IDs
                def format_business_option(business_id):
                    for id, name in business_options:
                        if id == business_id:
                            return name
                    return business_id
                
                # Use the multiselect widget with the format function
                selected_ids = st.multiselect(
                    "Select Booking Pages",
                    options=[id for id, _ in business_options],
                    format_func=format_business_option,
                    default=st.session_state.selected_businesses,
                    key="business_multiselect"
                )
                
                # Update session state with selected businesses
                if selected_ids != st.session_state.selected_businesses:
                    st.session_state.selected_businesses = selected_ids
                    st.rerun()  # Force a rerun to update the display
            else:
                st.warning("No booking pages found. Please check your Microsoft Bookings integration.")
            
            # Maximum results
            max_results = st.slider("Maximum Results", min_value=10, max_value=1000, value=500, step=10)
            
            # Fetch button
            if st.button("Fetch Bookings Data"):
                if not st.session_state.selected_businesses:
                    st.warning("Please select at least one booking page before fetching data.")
                else:
                    with st.spinner("Fetching bookings data..."):
                        # Run the asynchronous function with the selected business IDs
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
        st.text_input("Webhook URL", placeholder="https://your-service.com/webhook", key="webhook_url")
        
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

def analyze_unique_patients(df):
    """
    Analyze unique patients grouped by email and return unique patient counts and service distribution
    
    Args:
        df: DataFrame containing appointment data
        
    Returns:
        unique_patients_df: DataFrame with unique patients
        service_distribution: DataFrame with service count distribution
    """
    if df.empty or 'Email' not in df.columns:
        return pd.DataFrame(), pd.DataFrame()
    
    # Get unique patients with their most recent appointment
    unique_patients = (df[["Email", "Customer", "Phone", "Start Date"]]
                      .sort_values("Start Date", ascending=False)
                      .groupby("Email")
                      .first()
                      .reset_index())
    
    # Count total unique patients
    total_unique_patients = len(unique_patients)
    
    # Analyze service distribution per patient
    # Count how many unique services each patient has used
    if 'Service' in df.columns:
        # Group by email and count unique services
        services_per_patient = df.groupby('Email')['Service'].nunique().reset_index()
        services_per_patient.columns = ['Email', 'Service_Count']
        
        # Create distribution of service counts
        service_distribution = services_per_patient['Service_Count'].value_counts().reset_index()
        service_distribution.columns = ['Number_of_Services', 'Patient_Count']
        
        # Sort by number of services
        service_distribution = service_distribution.sort_values('Number_of_Services')
        
        # Calculate percentage
        service_distribution['Percentage'] = service_distribution['Patient_Count'] / total_unique_patients * 100
        
        return unique_patients, service_distribution
    
    return unique_patients, pd.DataFrame()

# Helper function to display phone validation output (to reduce duplication)
def display_phone_validation_output(results_df, summary, results_type="general"):
    st.markdown("---")
    st.markdown("#### Validation Results")
    st.dataframe(results_df, use_container_width=True, height=400)

    if summary:
        st.markdown("##### Validation Summary")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Total Processed", summary.get('total_processed', 0))
        valid_pct = (summary.get('valid',0)/summary.get('total_processed',1)) if summary.get('total_processed',0) > 0 else 0
        invalid_pct = (summary.get('invalid',0)/summary.get('total_processed',1)) if summary.get('total_processed',0) > 0 else 0
        empty_pct = (summary.get('empty',0)/summary.get('total_processed',1)) if summary.get('total_processed',0) > 0 else 0

        m_col2.metric("Valid Numbers", summary.get('valid',0), f"{valid_pct:.1%}")
        m_col3.metric("Invalid Numbers", summary.get('invalid',0), f"{invalid_pct:.1%}")
        m_col4.metric("Empty Fields", summary.get('empty',0), f"{empty_pct:.1%}")

        if summary.get('total_processed',0) > 0:
            status_data = pd.DataFrame({
                'Status': ['Valid', 'Invalid', 'Empty'],
                'Count': [summary.get('valid',0), summary.get('invalid',0), summary.get('empty',0)]
            })
            status_data = status_data[status_data['Count'] > 0]

            if not status_data.empty:
                fig_status_pie = px.pie(status_data, 
                             values='Count', 
                             names='Status', 
                             title='Phone Number Validation Status',
                             color='Status',
                             color_discrete_map={'Valid': '#28a745', 'Invalid': '#dc3545', 'Empty': '#6c757d'})
                fig_status_pie.update_traces(textposition='inside', textinfo='percent+label+value')
                st.plotly_chart(fig_status_pie, use_container_width=True)
            else:
                st.info("No data to display in the validation status chart.")
        
        if summary.get('valid', 0) > 0:
            st.markdown("##### Country Analysis of Valid Numbers")
            valid_numbers_df = results_df[results_df['Validation Status'] == 'Valid'].copy()
            
            if not valid_numbers_df.empty:
                # Extract country information from the "Validation Status" column directly
                # This ensures we use only the countries actually identified in the data
                
                # First, check if we have a "Validation Status" column with values like "Valid (Country)"
                if "Validation Status" in valid_numbers_df.columns and valid_numbers_df["Validation Status"].str.contains(r"Valid \(.*\)").any():
                    # Extract country names from status like "Valid (US)"
                    valid_numbers_df['Country'] = valid_numbers_df['Validation Status'].str.extract(r'Valid \((.*?)\)', expand=False)
                    
                    # Handle any rows where extraction failed
                    valid_numbers_df.loc[valid_numbers_df['Country'].isna(), 'Country'] = "Other"
                    
                    # Count countries
                    country_counts = valid_numbers_df['Country'].value_counts().reset_index()
                    country_counts.columns = ['Country', 'Count']
                    
                    # Only proceed if we have country data
                    if not country_counts.empty:
                        # Sort by count in descending order
                        display_counts = country_counts.sort_values(by='Count', ascending=False)
                        
                        fig_country_bar = px.bar(
                            display_counts,
                            x='Country',
                            y='Count',
                            title=f'Phone Numbers by Country ({len(display_counts)} countries found)',
                            labels={'Count': 'Number of Valid Phones', 'Country': 'Country'},
                            color='Country'
                        )
                        fig_country_bar.update_layout(
                            xaxis_title="Country", 
                            yaxis_title="Number of Valid Phones", 
                            height=500,
                            xaxis={'tickangle': -45} # Angled labels for better readability
                        )
                        st.plotly_chart(fig_country_bar, use_container_width=True)
                        st.caption("Country identification is based on phone number formats in your data.")
                    else:
                        st.info("No country information found in the valid phone numbers.")
                else:
                    # Fall back to extracting country codes from formatted phone numbers if status doesn't contain country info
                    def extract_country_code(phone_str):
                        if pd.isna(phone_str) or not isinstance(phone_str, str):
                            return "Unknown"
                        
                        # More robust country code extraction
                        match = re.match(r"^\+(\d{1,3})(?:\s*\(?)", phone_str)
                        if match:
                            # Map country codes to proper country names
                            country_code = match.group(1)
                            country_map = {
                                "1": "US/CA",      # United States/Canada
                                "44": "UK",        # United Kingdom
                                "353": "IE",       # Ireland
                                "971": "UAE",      # UAE/Dubai
                                "45": "DK",        # Denmark
                                "63": "PH",        # Philippines
                                "91": "IN",        # India
                                "61": "AU",        # Australia
                                "52": "MX",        # Mexico
                                "55": "BR",        # Brazil
                                "49": "DE",        # Germany
                                "33": "FR",        # France
                                "34": "ES",        # Spain
                                "86": "CN",        # China
                                "81": "JP",        # Japan
                                "82": "KR",        # South Korea
                                "39": "IT",        # Italy
                                "31": "NL",        # Netherlands
                                "64": "NZ",        # New Zealand
                                "54": "AR",        # Argentina
                                "27": "ZA"         # South Africa
                            }
                            # Return the country name or use the code if not in our map
                            return country_map.get(country_code, f"Country +{country_code}")
                        return "Unknown"

                    valid_numbers_df.loc[:, 'Country'] = valid_numbers_df['Formatted Phone'].apply(extract_country_code)
                    
                    # Count countries
                    country_counts = valid_numbers_df['Country'].value_counts().reset_index()
                    country_counts.columns = ['Country', 'Count']
                    
                    # Remove unknown countries
                    known_country_counts = country_counts[country_counts['Country'] != "Unknown"]
                    
                    if not known_country_counts.empty:
                        # Sort by count in descending order
                        display_counts = known_country_counts.sort_values(by='Count', ascending=False)
                        
                        fig_country_bar = px.bar(
                            display_counts,
                            x='Country',
                            y='Count',
                            title=f'Phone Numbers by Country ({len(display_counts)} countries found)',
                            labels={'Count': 'Number of Valid Phones', 'Country': 'Country'},
                            color='Country'
                        )
                        fig_country_bar.update_layout(
                            xaxis_title="Country", 
                            yaxis_title="Number of Valid Phones", 
                            height=500,
                            xaxis={'tickangle': -45} # Angled labels for better readability
                        )
                        st.plotly_chart(fig_country_bar, use_container_width=True)
                        st.caption("Country identification is based on phone number formats in your data.")
                    else:
                        st.info("No country information found in the valid phone numbers.")
            else:
                st.info("No valid numbers found for country analysis.")
    else:
        st.info("Validation summary data is not available.")

    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        csv_all = results_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download All Results (CSV)",
            data=csv_all,
            file_name=f"phone_validation_all_results_{results_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True,
            key=f"download_phone_all_results_{results_type}"
        )
    with dl_col2:
        valid_df = results_df[results_df['Validation Status'] == 'Valid']
        if not valid_df.empty:
            csv_valid = valid_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Valid Numbers Only (CSV)",
                data=csv_valid,
                file_name=f"phone_validation_valid_only_{results_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                type="secondary",
                use_container_width=True,
                key=f"download_phone_valid_only_{results_type}"
            )
        else:
            st.button("Download Valid Numbers Only (CSV)", disabled=True, use_container_width=True, help="No valid phone numbers found to download.", key=f"download_phone_valid_disabled_{results_type}")

# --- Outlook Import Prep Tool --- 
def render_outlook_import_prep_tool():
    st.header("Outlook Contact Import Preparation Tool")
    
    # Add debugging panel
    with st.expander("⚠️ Debug Information", expanded=False):
        st.markdown("### Session State Debugging")
        st.write("Current step:", st.session_state.get("outlook_prep_step", "No step set"))
        st.write("Has uploaded data:", "outlook_prep_uploaded_df" in st.session_state)
        st.write("Has column mapping:", "outlook_prep_column_mapping" in st.session_state)
        st.write("Has analysis results:", "outlook_prep_analysis_results" in st.session_state)
        
        if "outlook_prep_analysis_results" in st.session_state and st.session_state.outlook_prep_analysis_results:
            st.write("Analysis results keys:", list(st.session_state.outlook_prep_analysis_results.keys()))
            
        if st.button("Reset Tool State"):
            for key in list(st.session_state.keys()):
                if key.startswith("outlook_prep_"):
                    del st.session_state[key]
            st.success("Tool state has been reset")
            st.rerun()

    # Add the introduction card
    st.markdown("""
    <div class="card">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
            <i class="bi bi-person-check-fill" style="font-size: 1.5rem; color: var(--color-primary-action);"></i>
            <h3 style="margin:0;">Prepare Contacts for Outlook Import</h3>
        </div>
        <p>This tool helps you analyze and clean a CSV file (typically an Outlook export) before re-importing to Outlook. 
        It identifies potential duplicates, validates phone numbers, and flags common issues.</p>
        <ul>
            <li>Upload your CSV file (e.g., an export from Outlook).</li>
            <li>Map your file's columns to standard contact fields.</li>
            <li>Configure duplicate detection criteria.</li>
            <li>Review the analysis and (soon) download a cleaned/annotated file.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    # Initialize session state for this tool
    if 'outlook_prep_uploaded_df' not in st.session_state:
        st.session_state.outlook_prep_uploaded_df = None
    if 'outlook_prep_column_mapping' not in st.session_state:
        st.session_state.outlook_prep_column_mapping = {}
    if 'outlook_prep_analysis_results' not in st.session_state:
        st.session_state.outlook_prep_analysis_results = None

    # Define target internal fields (keys) and their typical Outlook export names (values for default mapping)
    TARGET_FIELDS = {
        "FirstName": "First Name",
        "MiddleName": "Middle Name",
        "LastName": "Last Name",
        "Email1": "E-mail Address",
        "Email2": "E-mail 2 Address",
        "Email3": "E-mail 3 Address",
        "MobilePhone": "Mobile Phone",
        "HomePhone": "Home Phone",
        "BusinessPhone": "Business Phone",
        # Add other fields as needed, e.g., Company, JobTitle, Addresses
    }

    uploaded_file_outlook = st.file_uploader(
        "Upload Outlook Export CSV File",
        type=["csv"],
        key="outlook_prep_uploader",
        help="Upload the CSV file you exported from Outlook or intend to import."
    )

    if uploaded_file_outlook is not None:
        try:
            df = pd.read_csv(uploaded_file_outlook)
            st.session_state.outlook_prep_uploaded_df = df
            st.success(f"Successfully uploaded '{uploaded_file_outlook.name}' with {len(df)} rows and {len(df.columns)} columns.")
            # Reset previous mapping and results if a new file is uploaded
            st.session_state.outlook_prep_column_mapping = {}
            st.session_state.outlook_prep_analysis_results = None 
        except Exception as e:
            st.error(f"Error reading CSV file: {e}")
            st.session_state.outlook_prep_uploaded_df = None

    if st.session_state.outlook_prep_uploaded_df is not None:
        df = st.session_state.outlook_prep_uploaded_df
        st.markdown("---")
        st.markdown("#### 1. Map Your CSV Columns")
        st.markdown("""Match the columns from your uploaded CSV to the standard contact fields. 
                    The tool will try to guess based on common Outlook export names.""", unsafe_allow_html=False) # Explicitly set unsafe_allow_html=False as it's not HTML

        available_csv_columns = ["<Not Mapped>"] + df.columns.tolist()
        current_mapping = st.session_state.outlook_prep_column_mapping.copy()

        cols_per_row = 3
        field_keys = list(TARGET_FIELDS.keys())
        
        for i in range(0, len(field_keys), cols_per_row):
            row_field_keys = field_keys[i:i+cols_per_row]
            map_cols = st.columns(cols_per_row)
            for idx, field_key in enumerate(row_field_keys):
                with map_cols[idx]:
                    # Attempt default mapping
                    default_outlook_name = TARGET_FIELDS[field_key]
                    default_index = 0
                    if default_outlook_name in available_csv_columns:
                        default_index = available_csv_columns.index(default_outlook_name)
                    elif field_key in available_csv_columns: # Fallback to internal key name if it exists as a header
                        default_index = available_csv_columns.index(field_key)
                    
                    # If already mapped, use that, otherwise use default
                    selected_column = current_mapping.get(field_key, available_csv_columns[default_index])
                    if selected_column not in available_csv_columns: # handle case where previously mapped col no longer exists
                        selected_column = "<Not Mapped>"
                        current_mapping[field_key] = "<Not Mapped>"
                    else:
                         current_mapping[field_key] = selected_column # ensure it is in current_mapping for the selectbox

                    mapped_col = st.selectbox(
                        f"Map: **{field_key}** (Standard Field)",
                        options=available_csv_columns,
                        index=available_csv_columns.index(selected_column),
                        key=f"map_{field_key}"
                    )
                    current_mapping[field_key] = mapped_col if mapped_col != "<Not Mapped>" else None
        
        st.session_state.outlook_prep_column_mapping = {k: v for k, v in current_mapping.items() if v is not None}

        if st.button("Proceed to Duplicate Detection Setup", type="primary"):
            # Basic check: Ensure at least one critical field is mapped for duplicate checking
            mapped_fields_for_dup_check = [
                st.session_state.outlook_prep_column_mapping.get("Email1"),
                st.session_state.outlook_prep_column_mapping.get("MobilePhone"),
                (st.session_state.outlook_prep_column_mapping.get("FirstName") and st.session_state.outlook_prep_column_mapping.get("LastName"))
            ]
            if not any(mapped_fields_for_dup_check):
                st.error("Please map at least one of: E-mail Address, Mobile Phone, or both First and Last Name before proceeding.")
            else:
                st.session_state.outlook_prep_step = "deduplication_setup" # Fictional state to move to next UI part
                st.rerun() # To update UI based on new step

        # Placeholder for next steps (Deduplication setup, Analysis)
        if st.session_state.get("outlook_prep_step") == "deduplication_setup":
            st.markdown("---")
            st.markdown("#### 2. Configure Duplicate Detection")
            
            mapped_columns = st.session_state.outlook_prep_column_mapping
            # Filter available fields for duplicate checking to those actually mapped by the user
            available_fields_for_exact_match = [mf_key for mf_key, mf_val in TARGET_FIELDS.items() if mapped_columns.get(mf_key)]
            # Add a conceptual "FullName" if both FirstName and LastName are mapped
            if mapped_columns.get("FirstName") and mapped_columns.get("LastName"):
                available_fields_for_exact_match.append("FullName (First + Last)") # Conceptual field

            if not any(available_fields_for_exact_match):
                st.warning("No fields suitable for duplicate detection have been mapped. Please map fields like Email, Phone, or Name in Step 1.")
                st.stop()

            # Initialize duplicate_check_fields in session state if not present
            if 'outlook_prep_duplicate_check_fields' not in st.session_state:
                st.session_state.outlook_prep_duplicate_check_fields = []

            selected_exact_match_fields = st.multiselect(
                "Select field(s) for **exact** duplicate checking:",
                options=available_fields_for_exact_match,
                default=[f for f in st.session_state.outlook_prep_duplicate_check_fields if f in available_fields_for_exact_match],
                help="Contacts will be considered exact duplicates if ALL selected fields match."
            )
            st.session_state.outlook_prep_duplicate_check_fields = selected_exact_match_fields

            # Fuzzy matching options (only if FirstName and LastName are mapped)
            can_do_fuzzy = mapped_columns.get("FirstName") and mapped_columns.get("LastName")
            if 'outlook_prep_enable_fuzzy_matching' not in st.session_state:
                 st.session_state.outlook_prep_enable_fuzzy_matching = False # Default to False
            if 'outlook_prep_fuzzy_threshold' not in st.session_state:
                 st.session_state.outlook_prep_fuzzy_threshold = 85 # Default threshold

            if can_do_fuzzy:
                st.session_state.outlook_prep_enable_fuzzy_matching = st.checkbox(
                    "Enable Fuzzy Name Matching (for First + Last Name)", 
                    value=st.session_state.outlook_prep_enable_fuzzy_matching,
                    help="Uses string similarity to find non-exact name matches. Slower on very large files."
                )
                if st.session_state.outlook_prep_enable_fuzzy_matching:
                    st.session_state.outlook_prep_fuzzy_threshold = st.slider(
                        "Fuzzy Match Similarity Threshold (%):", 
                        min_value=50, 
                        max_value=100, 
                        value=st.session_state.outlook_prep_fuzzy_threshold, 
                        help="Higher means names must be more similar to be considered a fuzzy match."
                    )
            else:
                st.session_state.outlook_prep_enable_fuzzy_matching = False # Ensure it's off if names not mapped
                st.info("Map both 'FirstName' and 'LastName' in Step 1 to enable Fuzzy Name Matching.")

            if st.button("Run Analysis", type="primary", key="run_outlook_prep_analysis"):
                if not selected_exact_match_fields and not st.session_state.outlook_prep_enable_fuzzy_matching:
                    st.error("Please select at least one field for exact duplicate checking or enable fuzzy name matching.")
                else:
                    # Add debug info
                    st.info(f"Starting analysis with {len(st.session_state.outlook_prep_uploaded_df)} records and {len(selected_exact_match_fields)} selected fields.")
                    
                    # Perform the actual analysis rather than just moving to the placeholder
                    with st.spinner("Analyzing your contact data..."):
                        try:
                            # Add debug output
                            st.write("Debug: Starting analysis process")
                            
                            # Get our data and settings
                            df = st.session_state.outlook_prep_uploaded_df
                            mapping = st.session_state.outlook_prep_column_mapping
                            
                            # Show key variables
                            st.write(f"Debug: Mapping keys: {list(mapping.keys())}")
                            st.write(f"Debug: DataFrame columns: {list(df.columns)}")
                            st.write(f"Debug: Selected fields: {selected_exact_match_fields}")
                            
                            # Create a results structure to store analysis findings
                            analysis_results = {
                                "total_records": len(df),
                                "exact_duplicates": [],
                                "fuzzy_duplicates": [],
                                "invalid_phones": [],
                                "empty_required": [],  # Add this field to avoid KeyError
                                "metrics": {
                                    "total_contacts": len(df),
                                    "exact_duplicate_count": 0,
                                    "fuzzy_duplicate_count": 0,
                                    "invalid_phone_count": 0,
                                    "empty_required_fields_count": 0,
                                },
                                "error": None
                            }
                            
                            # EXACT DUPLICATE CHECK
                            if selected_exact_match_fields:
                                st.write("Checking for exact duplicates...")
                                # Convert Outlook field names to actual columns in the dataframe
                                field_to_col = {}
                                for field in selected_exact_match_fields:
                                    if field == "FullName (First + Last)":
                                        if mapping.get("FirstName") and mapping.get("LastName"):
                                            # Create a temporary full name column by concatenating first and last
                                            df["_temp_fullname"] = df[mapping["FirstName"]].fillna("") + " " + df[mapping["LastName"]].fillna("")
                                            df["_temp_fullname"] = df["_temp_fullname"].str.strip()
                                            field_to_col[field] = "_temp_fullname"
                                    else:
                                        # Map the field to its corresponding column in the dataframe
                                        if mapping.get(field):
                                            field_to_col[field] = mapping[field]
                            
                                # Only proceed if we have valid column mappings
                                check_cols = [col for col in field_to_col.values() if col in df.columns]
                                if check_cols:
                                    # Find duplicates based on the selected fields
                                    duplicate_mask = df.duplicated(subset=check_cols, keep=False)
                                    duplicates = df[duplicate_mask].copy()
                                    
                                    if not duplicates.empty:
                                        # Group by duplicate values
                                        for _, group in duplicates.groupby(check_cols):
                                            if len(group) > 1:  # Ensure it's actually a duplicate group
                                                analysis_results["exact_duplicates"].append({
                                                    "fields": [field for field, col in field_to_col.items() if col in check_cols],
                                                    "count": len(group),
                                                    "records": group.to_dict('records')
                                                })
                                        
                                        # Update metrics
                                        analysis_results["metrics"]["exact_duplicate_count"] = sum(len(g["records"]) for g in analysis_results["exact_duplicates"])

                            # Store results in session state before trying other steps (in case they fail)
                            st.session_state.outlook_prep_analysis_results = analysis_results
                            
                            # Debug info
                            st.write(f"Found {analysis_results['metrics']['exact_duplicate_count']} exact duplicates.")
                            
                            # FUZZY DUPLICATE CHECK
                            if st.session_state.outlook_prep_enable_fuzzy_matching:
                                st.write("Checking for fuzzy name matches...")
                                # Only proceed if both first and last name are mapped
                                if mapping.get("FirstName") and mapping.get("LastName"):
                                    try:
                                        # Create a full name for comparison
                                        df["_fullname"] = df[mapping["FirstName"]].fillna("") + " " + df[mapping["LastName"]].fillna("")
                                        df["_fullname"] = df["_fullname"].str.strip()
                                        
                                        # If there are not many records, do a complete comparison
                                        # For large datasets, we might want to optimize this with blocking
                                        if len(df) <= 1000:  # Only do complete comparison for reasonably sized datasets
                                            fuzzy_threshold = st.session_state.outlook_prep_fuzzy_threshold
                                            
                                            # Compare each name with every other name
                                            for i, row in df.iterrows():
                                                if not pd.isna(row["_fullname"]) and row["_fullname"].strip():
                                                    name1 = row["_fullname"]
                                                    matches = []
                                                    matched_indices = []
                                                    
                                                    # Compare with all other names
                                                    for j, other_row in df.iterrows():
                                                        if i != j:  # Don't compare with self
                                                            if not pd.isna(other_row["_fullname"]) and other_row["_fullname"].strip():
                                                                name2 = other_row["_fullname"]
                                                                
                                                                # Calculate similarity
                                                                similarity = fuzz.ratio(name1.lower(), name2.lower())
                                                                
                                                                # If similar enough but not exact
                                                                if similarity >= fuzzy_threshold and similarity < 100:
                                                                    matches.append({
                                                                        "name": name2,
                                                                        "similarity": similarity,
                                                                        "index": j
                                                                    })
                                                                    matched_indices.append(j)
                                                    
                                                    # If matches found, create a fuzzy duplicate group
                                                    if matches:
                                                        # Add this record and all matches to the group
                                                        group_records = [row.to_dict()]
                                                        for idx in matched_indices:
                                                            group_records.append(df.loc[idx].to_dict())
                                                        
                                                        # Add to results
                                                        analysis_results["fuzzy_duplicates"].append({
                                                            "original": {"name": name1, "index": i},
                                                            "matches": matches,
                                                            "records": group_records
                                                        })
                                            
                                            # Update metrics for fuzzy duplicates
                                            fuzzy_records_count = sum(len(g["records"]) for g in analysis_results["fuzzy_duplicates"])
                                            analysis_results["metrics"]["fuzzy_duplicate_count"] = fuzzy_records_count
                                            
                                            # Debug info
                                            st.write(f"Found {len(analysis_results['fuzzy_duplicates'])} fuzzy match groups with {fuzzy_records_count} records.")
                                        else:
                                            st.warning("Dataset too large for fuzzy matching. Try using a smaller sample.")
                                    except Exception as e:
                                        st.error(f"Error in fuzzy matching: {str(e)}")
                                        analysis_results["error"] = f"Fuzzy matching error: {str(e)}"
                            
                            # Update session state with fuzzy results
                            st.session_state.outlook_prep_analysis_results = analysis_results
                            
                            # PHONE VALIDATION
                            st.write("Validating phone numbers...")
                            phone_fields = [field for field in ["MobilePhone", "HomePhone", "BusinessPhone"] 
                                            if mapping.get(field) and mapping[field] in df.columns]
                            
                            invalid_phones = []
                            if phone_fields:
                                for field in phone_fields:
                                    col = mapping[field]
                                    if col in df.columns:
                                        # Check each phone number
                                        for idx, row in df.iterrows():
                                            phone = row[col]
                                            if pd.notna(phone) and phone:  # Not empty
                                                try:
                                                    # Use safer way to call format_phone_strict that won't crash if import fails
                                                    # First check if function exists in current namespace
                                                    if 'format_phone_strict' in globals():
                                                        formatted, status = format_phone_strict(str(phone))
                                                        if not status.startswith("Valid"):
                                                            invalid_phones.append({
                                                                "field": field,
                                                                "original_value": phone,
                                                                "status": status,
                                                                "record": row.to_dict()
                                                            })
                                                except Exception as e:
                                                    st.error(f"Phone validation error: {str(e)}")
                                                    analysis_results["error"] = f"Phone validation error: {str(e)}"
                                
                                # Update metrics
                                analysis_results["invalid_phones"] = invalid_phones
                                analysis_results["metrics"]["invalid_phone_count"] = len(invalid_phones)
                            
                            # Store results again with phone validation results
                            st.session_state.outlook_prep_analysis_results = analysis_results
                            
                            # CHECK FOR EMPTY REQUIRED FIELDS
                            st.write("Checking field completeness...")
                            required_fields = ["FirstName", "LastName", "Email1", "MobilePhone"]
                            empty_required = []
                            
                            for field in required_fields:
                                if field in mapping and mapping[field] in df.columns:
                                    col = mapping[field]
                                    empty_count = df[col].isna().sum() + (df[col] == "").sum()
                                    
                                    if empty_count > 0:
                                        # Calculate percentage
                                        percentage = (empty_count / len(df)) * 100
                                        
                                        empty_required.append({
                                            "field": field,
                                            "column": col,
                                            "count": int(empty_count),
                                            "percentage": percentage
                                        })
                            
                            # Update results
                            analysis_results["empty_required"] = empty_required
                            analysis_results["metrics"]["empty_required_fields_count"] = len(empty_required)
                                
                            # Finally update session state with complete results
                            st.session_state.outlook_prep_analysis_results = analysis_results
                            st.session_state.outlook_prep_step = "analysis_results"
                            
                            # Debug info
                            st.success("Analysis completed successfully! Navigating to results...")
                            
                        except Exception as e:
                            st.error(f"Error during analysis: {str(e)}")
                            # Add traceback for better error detection
                            st.code(traceback.format_exc(), language="python")
                            # Also print to terminal for easier debugging
                            print(f"ERROR in analysis: {str(e)}")
                            print(traceback.format_exc())
                            # Still update step to show results, but mark error
                            if 'outlook_prep_analysis_results' not in st.session_state:
                                st.session_state.outlook_prep_analysis_results = {"error": str(e)}
                            st.session_state.outlook_prep_step = "analysis_results"
                    
                    # Force rerun to show results
                    st.rerun()

        if st.session_state.get("outlook_prep_step") == "analysis_results":
            st.markdown("---")
            st.markdown("#### 3. Analysis Results")
            
            # Display results if they exist
            if st.session_state.outlook_prep_analysis_results:
                results = st.session_state.outlook_prep_analysis_results
                
                # Overview metrics
                st.markdown("##### Contact Data Overview")
                metrics_cols = st.columns(4)
                
                with metrics_cols[0]:
                    st.metric("Total Contacts", results["metrics"]["total_contacts"])
                
                with metrics_cols[1]:
                    exact_dup_count = results["metrics"]["exact_duplicate_count"]
                    pct = f"({(exact_dup_count / results['metrics']['total_contacts'] * 100):.1f}%)" if results["metrics"]["total_contacts"] > 0 else ""
                    st.metric("Exact Duplicates", f"{exact_dup_count} {pct}")
                
                with metrics_cols[2]:
                    fuzzy_dup_count = results["metrics"]["fuzzy_duplicate_count"]
                    pct = f"({(fuzzy_dup_count / results['metrics']['total_contacts'] * 100):.1f}%)" if results["metrics"]["total_contacts"] > 0 else ""
                    st.metric("Fuzzy Duplicates", f"{fuzzy_dup_count} {pct}")
                
                with metrics_cols[3]:
                    invalid_count = results["metrics"]["invalid_phone_count"]
                    pct = f"({(invalid_count / results['metrics']['total_contacts'] * 100):.1f}%)" if results["metrics"]["total_contacts"] > 0 else ""
                    st.metric("Invalid Phones", f"{invalid_count} {pct}")
                
                # Create tabs for different result sections
                result_tabs = st.tabs([
                    "Exact Duplicates", 
                    "Fuzzy Matches", 
                    "Phone Issues",
                    "Field Completeness"
                ])
                
                # Exact Duplicates Tab
                with result_tabs[0]:
                    if results["exact_duplicates"]:
                        st.markdown(f"##### Found {len(results['exact_duplicates'])} groups of exact duplicates")
                        
                        for i, group in enumerate(results["exact_duplicates"]):
                            with st.expander(f"Duplicate Group #{i+1}: {group['count']} records matching on {', '.join(group['fields'])}"):
                                if group["records"]:
                                    st.dataframe(pd.DataFrame(group["records"]))
                    else:
                        st.info("No exact duplicates found based on your selected criteria.")
                
                # Fuzzy Matches Tab
                with result_tabs[1]:
                    if results["fuzzy_duplicates"]:
                        st.markdown(f"##### Found {len(results['fuzzy_duplicates'])} groups with similar names")
                        
                        for i, group in enumerate(results["fuzzy_duplicates"]):
                            matches_info = [f"{m['name']} ({m['similarity']}% similar)" for m in group["matches"]]
                            with st.expander(f"Similar Name Group #{i+1}: '{group['original']['name']}' matches {len(matches_info)} others"):
                                # Display original and matched names with similarity scores
                                st.markdown("**Original Name:** " + group["original"]["name"])
                                st.markdown("**Similar to:**")
                                for match_info in matches_info:
                                    st.markdown(f"- {match_info}")
                                
                                # Display the full records
                                st.markdown("**Full Records:**")
                                st.dataframe(pd.DataFrame(group["records"]))
                    else:
                        if st.session_state.outlook_prep_enable_fuzzy_matching:
                            st.info("No similar names found with the current threshold setting.")
                        else:
                            st.info("Fuzzy name matching was not enabled.")
                
                # Phone Issues Tab
                with result_tabs[2]:
                    if results["invalid_phones"]:
                        st.markdown(f"##### Found {len(results['invalid_phones'])} phone numbers with issues")
                        
                        # Convert to DataFrame for easier display
                        phone_issues_df = pd.DataFrame([
                            {
                                "Field": issue["field"],
                                "Original Value": issue["original_value"],
                                "Status": issue["status"]
                            }
                            for issue in results["invalid_phones"]
                        ])
                        
                        st.dataframe(phone_issues_df)
                    else:
                        st.info("No phone number issues detected.")
                
                # Field Completeness Tab
                with result_tabs[3]:
                    if "empty_required" in results and results["empty_required"]:
                        st.markdown("##### Required Fields Missing Data")
                        
                        # Create a DataFrame for better display
                        empty_fields_df = pd.DataFrame([
                            {
                                "Field": empty["field"],
                                "Records Missing": empty["count"],
                                "Percentage": f"{empty['percentage']:.1f}%"
                            }
                            for empty in results["empty_required"]
                        ])
                        
                        st.dataframe(empty_fields_df)
                        
                        # Create a bar chart to visualize completeness
                        if not empty_fields_df.empty:
                            fig = px.bar(
                                empty_fields_df,
                                x="Field",
                                y="Records Missing",
                                text="Percentage",
                                title="Required Fields Missing Data",
                                color="Records Missing"
                            )
                            
                            fig.update_layout(height=400)
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("All required fields have data in all records, or no required fields were defined.")
                
                # Download cleaned file option (placeholder for now)
                st.markdown("---")
                st.markdown("##### Download Options")
                
                download_cols = st.columns(2)
                
                with download_cols[0]:
                    st.button("Download Analysis Report (CSV)", disabled=True, 
                             help="This feature is coming soon.")
                
                with download_cols[1]:
                    st.button("Download Cleaned Contacts (CSV)", disabled=True,
                             help="This feature is coming soon.")
            else:
                st.info("No analysis results available. Please run the analysis first.")
                # Add button to return to previous step if needed
                if st.button("Return to Duplicate Detection Setup"):
                    st.session_state.outlook_prep_step = "deduplication_setup"
                    st.rerun()

# Call the main function
if __name__ == "__main__":
    main()
