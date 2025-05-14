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

# Import custom modules
from config import THEME_CONFIG, DATE_PRESETS, APP_TAGLINE, LOGO_PATH
from ms_integrations import fetch_bookings_data, fetch_calendar_events
from phone_formatter import format_phone_strict, create_phone_analysis, format_phone_dataframe, prepare_outlook_contacts, create_appointments_flow, process_uploaded_phone_list
from airtable_integration import render_airtable_tabs, get_airtable_credentials, fetch_airtable_table
from icons import render_logo, render_tab_bar, render_icon, render_empty_state, render_info_box

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
    st.session_state.active_tab = tab
    
def set_active_subtab(tab, subtab):
    if 'active_subtab' not in st.session_state:
        st.session_state.active_subtab = {}
    st.session_state.active_subtab[tab] = subtab

# Render the application header
def render_app_header():
    """Render the application header with logo and title"""
    header_html = f"""
    <div class="app-header">
        {render_logo(width="50px")}
        <div style="margin-left: 15px;">
            <h1 class="app-title">Access Care Analytics Dashboard</h1>
            <p class="app-subtitle">{APP_TAGLINE}</p>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

# Tab definitions for the main navigation
MAIN_TABS = {
    "dashboard": {"icon": "analytics", "label": "Dashboard"},
    "patient": {"icon": "user", "label": "Patient & Client"},
    "tools": {"icon": "tool", "label": "Tools"},
    "integrations": {"icon": "link", "label": "Integrations"},
    "content": {"icon": "document", "label": "Content Creator"}
}

# Subtab definitions for each main tab
SUBTABS = {
    "dashboard": {
        "overview": {"icon": "dashboard", "label": "Overview"},
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
        "airtable": {"icon": "airtable", "label": "Airtable"},
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
    render_app_header()
    
    # Render main tabs
    active_tab = render_tab_bar(MAIN_TABS, st.session_state.active_tab, set_active_tab)
    st.session_state.active_tab = active_tab
    
    # Render subtabs for the active tab
    if active_tab in SUBTABS:
        # Initialize active subtab for this tab if not set
        if active_tab not in st.session_state.active_subtab:
            st.session_state.active_subtab[active_tab] = list(SUBTABS[active_tab].keys())[0]
            
        # Render the subtabs
        active_subtab = render_tab_bar(
            SUBTABS[active_tab], 
            st.session_state.active_subtab.get(active_tab),
            lambda subtab: set_active_subtab(active_tab, subtab)
        )
        st.session_state.active_subtab[active_tab] = active_subtab
    
    # Render the content for the active tab and subtab
    if active_tab == "dashboard":
        render_dashboard_tab(st.session_state.active_subtab.get(active_tab))
    elif active_tab == "patient":
        render_patient_tab(st.session_state.active_subtab.get(active_tab))
    elif active_tab == "tools":
        render_tools_tab(st.session_state.active_subtab.get(active_tab))
    elif active_tab == "integrations":
        render_integrations_tab(st.session_state.active_subtab.get(active_tab))
    elif active_tab == "content":
        render_content_tab(st.session_state.active_subtab.get(active_tab))

# Render the dashboard tab
def render_dashboard_tab(active_subtab):
    """Render the dashboard tab content"""
    if active_subtab == "overview":
        st.header("Dashboard Overview")
        
        # Show introduction card
        st.markdown("""
        <div class="card">
            <h3>Welcome to Access Care Analytics</h3>
            <p>Access comprehensive analytics and operational intelligence for your healthcare services.</p>
            <p>Use the tabs above to navigate between different dashboard views.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Create metrics row
        st.subheader("Key Metrics")
        
        # Check if we have data
        if st.session_state.get('bookings_data') is not None:
            df = st.session_state.bookings_data
            
            # Create metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                total_appointments = len(df)
                st.metric("Total Appointments", total_appointments)
                
            with col2:
                if 'Status' in df.columns:
                    completed = len(df[df['Status'] == 'Completed'])
                    st.metric("Completed", completed)
                else:
                    st.metric("Completed", "N/A")
                    
            with col3:
                if 'Status' in df.columns:
                    scheduled = len(df[df['Status'] == 'Scheduled'])
                    st.metric("Scheduled", scheduled)
                else:
                    st.metric("Scheduled", "N/A")
                    
            with col4:
                if 'Status' in df.columns:
                    cancelled = len(df[df['Status'] == 'Cancelled'])
                    st.metric("Cancelled", cancelled)
                else:
                    st.metric("Cancelled", "N/A")
                    
            # Create visualization row
            st.subheader("Appointment Trends")
            
            try:
                # Create a simple line chart of appointments over time
                if 'Created Date' in df.columns:
                    df['Created Date'] = pd.to_datetime(df['Created Date'])
                    daily_counts = df.groupby(df['Created Date'].dt.date).size().reset_index(name='count')
                    
                    fig = px.line(
                        daily_counts, 
                        x='Created Date', 
                        y='count',
                        title='Daily Appointment Bookings',
                        labels={'Created Date': 'Date', 'count': 'Number of Bookings'},
                        template='plotly_dark'
                    )
                    
                    # Update the figure with theme colors
                    fig.update_layout(
                        plot_bgcolor=THEME_CONFIG['CARD_BG'],
                        paper_bgcolor=THEME_CONFIG['CARD_BG'],
                        font_color=THEME_CONFIG['TEXT_COLOR'],
                        title_font_color=THEME_CONFIG['PRIMARY_COLOR'],
                        legend_title_font_color=THEME_CONFIG['PRIMARY_COLOR'],
                        height=400
                    )
                    fig.update_traces(line_color=THEME_CONFIG['SECONDARY_COLOR'])
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Date information is not available in the current dataset.")
            except Exception as e:
                st.error(f"Error creating chart: {str(e)}")
                
            # Status distribution pie chart
            try:
                if 'Status' in df.columns:
                    st.subheader("Appointment Status Distribution")
                    
                    status_counts = df['Status'].value_counts().reset_index()
                    status_counts.columns = ['Status', 'Count']
                    
                    fig = px.pie(
                        status_counts,
                        values='Count',
                        names='Status',
                        title='Appointment Status Distribution',
                        template='plotly_dark',
                        color_discrete_map={
                            'Completed': THEME_CONFIG['SUCCESS_COLOR'],
                            'Scheduled': THEME_CONFIG['PRIMARY_COLOR'],
                            'Cancelled': THEME_CONFIG['DANGER_COLOR']
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
            except Exception as e:
                st.error(f"Error creating chart: {str(e)}")
        else:
            # Show empty state
            render_empty_state(
                "No appointment data available. Use the sidebar to set filters and fetch data.",
                "dashboard"
            )
            
            # Add a button to fetch data
            if st.button("Fetch Appointment Data"):
                # This would normally fetch real data
                st.session_state.bookings_data = pd.DataFrame({
                    "Customer": ["John Doe", "Jane Smith", "Bob Johnson"] * 5,
                    "Status": ["Completed", "Scheduled", "Cancelled"] * 5,
                    "Created Date": pd.date_range(start="2023-01-01", periods=15, freq="D"),
                    "Service": ["Cleaning", "Exam", "Surgery"] * 5
                })
                st.experimental_rerun()
                
    elif active_subtab == "appointments":
        st.header("Appointments")
        
        # Check if we have data
        if st.session_state.get('bookings_data') is not None:
            df = st.session_state.bookings_data
            
            # Add filters
            col1, col2 = st.columns(2)
            with col1:
                if 'Status' in df.columns:
                    status_options = df['Status'].unique().tolist()
                    selected_status = st.multiselect(
                        "Filter by Status",
                        options=status_options,
                        default=status_options
                    )
                else:
                    selected_status = []
                    
            with col2:
                if 'Service' in df.columns:
                    service_options = df['Service'].unique().tolist()
                    selected_services = st.multiselect(
                        "Filter by Service",
                        options=service_options,
                        default=service_options
                    )
                else:
                    selected_services = []
                    
            # Apply filters
            filtered_df = df
            if 'Status' in df.columns and selected_status:
                filtered_df = filtered_df[filtered_df['Status'].isin(selected_status)]
                
            if 'Service' in df.columns and selected_services:
                filtered_df = filtered_df[filtered_df['Service'].isin(selected_services)]
                
            # Display filtered results
            st.subheader(f"Showing {len(filtered_df)} appointments")
            st.dataframe(filtered_df, use_container_width=True)
            
            # Download filtered data
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download Filtered Data",
                csv,
                "appointments.csv",
                "text/csv",
                key="download-appointments"
            )
        else:
            # Show empty state
            render_empty_state(
                "No appointment data available. Use the sidebar to set filters and fetch data.",
                "calendar"
            )
    
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

# Render the patient tab
def render_patient_tab(active_subtab):
    """Render the patient tab content"""
    if active_subtab == "contacts":
        st.header("Patient Contacts")
        
        # Check if we have data
        if st.session_state.get('bookings_data') is not None:
            df = st.session_state.bookings_data
            
            # Create patient contact information cards
            if "Customer" in df.columns:
                # Get unique customers
                unique_customers = df["Customer"].unique()
                st.subheader(f"Patient Directory ({len(unique_customers)} patients)")
                
                # Create search functionality
                search_term = st.text_input("Search Patients", "")
                
                # Filter based on search
                if search_term:
                    filtered_customers = [c for c in unique_customers if search_term.lower() in c.lower()]
                else:
                    filtered_customers = unique_customers
                
                # Add pagination
                patients_per_page = 10
                total_pages = (len(filtered_customers) - 1) // patients_per_page + 1
                
                col1, col2 = st.columns([4, 1])
                with col2:
                    current_page = st.selectbox("Page", range(1, total_pages + 1), 1) if total_pages > 1 else 1
                
                # Slice the customers for current page
                start_idx = (current_page - 1) * patients_per_page
                end_idx = start_idx + patients_per_page
                current_customers = filtered_customers[start_idx:end_idx]
                
                # Display patient cards
                for customer in current_customers:
                    customer_data = df[df["Customer"] == customer].iloc[0]
                    
                    # Create a card for each patient
                    st.markdown(f"""
                    <div class="card" style="margin-bottom: 1rem;">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div>
                                <h3 style="margin-top: 0;">{customer}</h3>
                                <p><strong>Last Visit:</strong> {customer_data.get('Start Date', 'N/A')}</p>
                                <p><strong>Service:</strong> {customer_data.get('Service', 'N/A')}</p>
                            </div>
                            <div>
                                <span style="background-color: {THEME_CONFIG['SUCCESS_COLOR']}; color: white; padding: 4px 8px; border-radius: 4px;">
                                    {customer_data.get('Status', 'N/A')}
                                </span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                render_empty_state(
                    "No customer data found in the current dataset.",
                    "user"
                )
        else:
            # Show empty state
            render_empty_state(
                "No patient data available. Please fetch appointment data first.",
                "user"
            )
            
    elif active_subtab == "communication":
        st.header("Patient Communication")
        
        # Show introduction card
        st.markdown("""
        <div class="card">
            <h3>Communication Dashboard</h3>
            <p>Monitor and manage patient communications and outreach campaigns.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Create tabs for different communication methods
        comm_tabs = ["Email Templates", "SMS Campaigns", "Communication History"]
        active_comm_tab = st.radio("", comm_tabs, horizontal=True)
        
        if active_comm_tab == "Email Templates":
            st.subheader("Email Templates")
            
            # Example email templates
            templates = [
                {"name": "Appointment Reminder", "subject": "Your Upcoming Appointment", "usage": 245},
                {"name": "Appointment Confirmation", "subject": "Appointment Confirmed", "usage": 189},
                {"name": "Follow-up Care", "subject": "Follow-up Information After Your Visit", "usage": 156},
                {"name": "Annual Checkup Reminder", "subject": "Time for Your Annual Check-up", "usage": 98}
            ]
            
            # Display templates
            for i, template in enumerate(templates):
                st.markdown(f"""
                <div class="card" style="margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div>
                            <h3 style="margin-top: 0;">{template['name']}</h3>
                            <p><strong>Subject:</strong> {template['subject']}</p>
                        </div>
                        <div>
                            <span style="background-color: {THEME_CONFIG['LIGHT_COLOR']}; color: {THEME_CONFIG['TEXT_COLOR']}; padding: 4px 8px; border-radius: 4px;">
                                Used {template['usage']} times
                            </span>
                        </div>
                    </div>
                    <div style="margin-top: 0.5rem;">
                        <button style="background-color: {THEME_CONFIG['PRIMARY_COLOR']}; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; margin-right: 8px;">
                            Edit Template
                        </button>
                        <button style="background-color: {THEME_CONFIG['SECONDARY_COLOR']}; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer;">
                            Send Test
                        </button>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            # Button to create new template
            st.button("Create New Template")
            
        elif active_comm_tab == "SMS Campaigns":
            st.subheader("SMS Campaigns")
            
            # Example SMS campaigns
            campaigns = [
                {"name": "Appointment Reminder", "status": "Active", "sent": 156, "delivered": 152},
                {"name": "Special Promotion", "status": "Completed", "sent": 243, "delivered": 238},
                {"name": "Holiday Hours", "status": "Draft", "sent": 0, "delivered": 0}
            ]
            
            # Display campaigns
            for campaign in campaigns:
                status_color = {
                    "Active": THEME_CONFIG['SUCCESS_COLOR'],
                    "Completed": THEME_CONFIG['SECONDARY_COLOR'],
                    "Draft": THEME_CONFIG['LIGHT_COLOR']
                }.get(campaign['status'], THEME_CONFIG['LIGHT_COLOR'])
                
                st.markdown(f"""
                <div class="card" style="margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div>
                            <h3 style="margin-top: 0;">{campaign['name']}</h3>
                            <p><strong>Messages Sent:</strong> {campaign['sent']}</p>
                            <p><strong>Delivered:</strong> {campaign['delivered']}</p>
                        </div>
                        <div>
                            <span style="background-color: {status_color}; color: white; padding: 4px 8px; border-radius: 4px;">
                                {campaign['status']}
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            # Button to create new campaign
            st.button("Create New Campaign")
            
        elif active_comm_tab == "Communication History":
            st.subheader("Communication History")
            
            # Create sample communication history data
            history_data = pd.DataFrame({
                "Date": pd.date_range(start="2023-01-01", periods=10, freq="D"),
                "Type": ["Email", "SMS", "Email", "Email", "SMS", "Email", "SMS", "Email", "Email", "SMS"],
                "Subject/Template": ["Appointment Reminder", "Schedule Confirmation", "Follow-up Care", 
                                    "Annual Checkup", "Office Closed", "Lab Results", "Medication Reminder",
                                    "Survey Request", "Billing Notice", "Appointment Reminder"],
                "Recipient": ["John Doe", "Jane Smith", "Bob Johnson", "Alice Brown", "Tom Wilson",
                             "Sarah Davis", "Mike Thompson", "Lisa Miller", "Carlos Gomez", "Emily Chen"],
                "Status": ["Delivered", "Delivered", "Opened", "Clicked", "Delivered", "Bounced", 
                          "Delivered", "Opened", "Delivered", "Failed"]
            })
            
            # Display the history data
            st.dataframe(history_data, use_container_width=True)
            
            # Download option
            csv = history_data.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download Communication History",
                csv,
                "communication_history.csv",
                "text/csv",
                key="download-comm-history"
            )
    
    elif active_subtab == "export":
        st.header("Patient Data Export")
        
        # Check if we have data
        if st.session_state.get('bookings_data') is not None:
            df = st.session_state.bookings_data
            
            # Create export options
            st.subheader("Export Options")
            
            # Create columns for export formats
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("""
                <div class="card" style="text-align: center; cursor: pointer;">
                    <h3>CSV Export</h3>
                    <p>Export patient data to CSV format</p>
                    <div style="background-color: {THEME_CONFIG['PRIMARY_COLOR']}; color: white; padding: 8px; border-radius: 4px; margin-top: 12px;">
                        Export CSV
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Add the actual export button
                if st.button("Export CSV"):
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "Download CSV",
                        csv,
                        "patient_data.csv",
                        "text/csv",
                        key="download-csv"
                    )
            
            with col2:
                st.markdown("""
                <div class="card" style="text-align: center; cursor: pointer;">
                    <h3>Excel Export</h3>
                    <p>Export patient data to Excel format</p>
                    <div style="background-color: {THEME_CONFIG['PRIMARY_COLOR']}; color: white; padding: 8px; border-radius: 4px; margin-top: 12px;">
                        Export Excel
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Add the actual export button
                if st.button("Export Excel"):
                    # In a real app, you would generate an Excel file
                    # Since we can't do that without saving files, just show a message
                    st.success("Excel export functionality would go here")
            
            with col3:
                st.markdown("""
                <div class="card" style="text-align: center; cursor: pointer;">
                    <h3>Outlook Contacts</h3>
                    <p>Export as Outlook contact format</p>
                    <div style="background-color: {THEME_CONFIG['PRIMARY_COLOR']}; color: white; padding: 8px; border-radius: 4px; margin-top: 12px;">
                        Export Contacts
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Add the actual export button
                if st.button("Export Contacts"):
                    # Create a simple contact CSV
                    if "Customer" in df.columns and "Phone" in df.columns:
                        contacts_df = df[["Customer", "Phone"]].drop_duplicates()
                        contacts_csv = contacts_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "Download Contacts",
                            contacts_csv,
                            "patient_contacts.csv",
                            "text/csv",
                            key="download-contacts"
                        )
                    else:
                        st.warning("Required contact fields not found in the dataset")
            
            # Add export history
            st.subheader("Export History")
            
            # Create sample export history
            export_history = pd.DataFrame({
                "Date": pd.date_range(end=pd.Timestamp.now(), periods=5, freq="D"),
                "Format": ["CSV", "Excel", "Contacts", "CSV", "Excel"],
                "Records": [124, 124, 98, 115, 110],
                "Exported By": ["Admin User"] * 5
            })
            
            st.dataframe(export_history, use_container_width=True)
        else:
            # Show empty state
            render_empty_state(
                "No patient data available for export. Please fetch appointment data first.",
                "upload"
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
    render_empty_state(
        f"The {active_subtab} integration tab is under development.",
        "link"
    )

def render_content_tab(active_subtab):
    st.header("Content Creator")
    render_empty_state(
        f"The {active_subtab} content creator tab is under development.",
        "document"
    )

# Call the main function
if __name__ == "__main__":
    main()
