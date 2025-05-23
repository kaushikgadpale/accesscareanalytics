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
    """Render the Outlook Contact Import Preparation Tool"""
    from outlook_contact_import import (
        format_phone_number, 
        process_contacts_file, 
        create_status_chart, 
        create_country_chart,
        create_duplicate_chart,
        prepare_outlook_contacts
    )
    
    st.header("Outlook Contact Import Preparation Tool")
    
    st.markdown("""
    <div class="card">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
            <i class="bi bi-person-lines-fill" style="font-size: 1.5rem; color: var(--color-primary-action);"></i>
            <h3 style="margin:0;">Prepare Contacts for Outlook</h3>
        </div>
        <p>This tool helps you prepare contact lists for import into Microsoft Outlook. 
        It can detect duplicates and format phone numbers correctly for US, UK, Ireland, Denmark, and Philippines.</p>
        <ul>
            <li>Validate and format phone numbers for selected countries</li>
            <li>Detect duplicate contacts by phone, email, and name</li>
            <li>Find similar names using fuzzy matching</li>
            <li>Export in Outlook-compatible format</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Add fuzzy matching options
    col1, col2 = st.columns(2)
    with col1:
        enable_fuzzy = st.checkbox("Enable fuzzy name matching", value=True, 
                                  help="Find potential duplicates with similar but not identical names")
    with col2:
        if enable_fuzzy:
            fuzzy_threshold = st.slider("Fuzzy matching threshold", min_value=70, max_value=95, value=85,
                                       help="Higher values require names to be more similar to be considered a match")
        else:
            fuzzy_threshold = 85
    
    uploaded_file = st.file_uploader("Choose a contacts file", type=["csv", "xlsx", "xls"],
                                    key="outlook_import_file_uploader",
                                    help="Upload a CSV or Excel file with your contacts")
    
    if uploaded_file is not None:
        with st.spinner("Processing your file..."):
            result, error = process_contacts_file(uploaded_file, fuzzy_match=enable_fuzzy, fuzzy_threshold=fuzzy_threshold)
        
        if error:
            st.error(error)
        elif result:
            # Display statistics
            st.success("File processed successfully!")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Total Contacts", result['stats']['total'])
            col2.metric("Valid Phone Numbers", result['stats']['valid'])
            col3.metric("Invalid Numbers", result['stats']['invalid'])
            col4.metric("Duplicates", result['stats']['duplicates'])
            col5.metric("Unique Valid Contacts", result['stats']['unique_valid'])
            
            # Create tabs for different views
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Valid Contacts", "Invalid Contacts", "Duplicates", "All Contacts"])
            
            with tab1:
                st.subheader("Phone Number Analysis")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    status_chart = create_status_chart(result['all'])
                    if status_chart:
                        st.plotly_chart(status_chart, use_container_width=True)
                
                with col2:
                    valid_phones = result['all'][result['all']['Phone Status'].str.startswith('Valid')]
                    if not valid_phones.empty:
                        country_chart = create_country_chart(valid_phones)
                        if country_chart:
                            st.plotly_chart(country_chart, use_container_width=True)
                
                # Add duplicate analysis chart
                if result['duplicate_counts']['total'] > 0:
                    st.subheader("Duplicate Analysis")
                    duplicate_chart = create_duplicate_chart(result['duplicate_counts'])
                    if duplicate_chart:
                        st.plotly_chart(duplicate_chart, use_container_width=True)
                
                st.subheader("Actions")
                
                # Generate Outlook-compatible CSV
                if not result['valid'].empty:
                    outlook_contacts = prepare_outlook_contacts(result['valid'])
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.download_button(
                            label="Download All Valid Contacts for Outlook",
                            data=outlook_contacts.to_csv(index=False),
                            file_name="outlook_contacts_all.csv",
                            mime="text/csv"
                        )
                        st.caption("File is formatted for direct import into Outlook")
                    
                    with col2:
                        # Download only unique valid contacts
                        unique_valid = result['valid'][~result['valid']['Is Duplicate']]
                        if not unique_valid.empty:
                            unique_outlook_contacts = prepare_outlook_contacts(unique_valid)
                            st.download_button(
                                label="Download Unique Valid Contacts for Outlook",
                                data=unique_outlook_contacts.to_csv(index=False),
                                file_name="outlook_contacts_unique.csv",
                                mime="text/csv"
                            )
                            st.caption("Contains only unique contacts, removes duplicates")
            
            with tab2:
                if result['valid'].empty:
                    st.warning("No valid phone numbers found.")
                else:
                    st.write(f"Found {len(result['valid'])} valid phone numbers")
                    st.dataframe(result['valid'], use_container_width=True)
                    
                    st.download_button(
                        label="Download Valid Contacts CSV",
                        data=result['valid'].to_csv(index=False),
                        file_name="valid_contacts.csv",
                        mime="text/csv"
                    )
            
            with tab3:
                if result['invalid'].empty:
                    st.success("No invalid phone numbers found.")
                else:
                    st.write(f"Found {len(result['invalid'])} invalid phone numbers")
                    st.dataframe(result['invalid'], use_container_width=True)
                    
                    st.download_button(
                        label="Download Invalid Contacts CSV",
                        data=result['invalid'].to_csv(index=False),
                        file_name="invalid_contacts.csv",
                        mime="text/csv"
                    )
                    
                    st.info("These numbers need manual correction. Common issues include:")
                    st.markdown("""
                    - Missing country code
                    - Incorrect number of digits
                    - Unsupported country format (only US, UK, Ireland, Denmark, and Philippines are supported)
                    """)
            
            with tab4:
                if result['duplicates'].empty:
                    st.success("No duplicate contacts found.")
                else:
                    st.write(f"Found {len(result['duplicates'])} duplicate contacts")
                    
                    # Show duplicate type information
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Phone Duplicates", result['duplicate_counts'].get('phone', 0))
                    col2.metric("Email Duplicates", result['duplicate_counts'].get('email', 0))
                    col3.metric("Exact Name Duplicates", result['duplicate_counts'].get('exact_name', 0))
                    col4.metric("Fuzzy Name Duplicates", result['duplicate_counts'].get('fuzzy_name', 0))
                    
                    st.dataframe(result['duplicates'], use_container_width=True)
                    
                    st.download_button(
                        label="Download Duplicates CSV",
                        data=result['duplicates'].to_csv(index=False),
                        file_name="duplicate_contacts.csv",
                        mime="text/csv"
                    )
            
            with tab5:
                st.write("All processed contacts")
                st.dataframe(result['all'], use_container_width=True)
                
                st.download_button(
                    label="Download All Contacts CSV",
                    data=result['all'].to_csv(index=False),
                    file_name="all_contacts.csv",
                    mime="text/csv"
                )

# Call the main function
if __name__ == "__main__":
    main()
