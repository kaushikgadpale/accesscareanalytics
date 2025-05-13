import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import threading
import asyncio

from config import (
    LOCAL_TZ,
    LOGO_PATH,
    DATE_PRESETS,
    THEME_CONFIG,
    WEBHOOK_PUBLIC_URL
)
from auth import get_auth_headers
from data_fetcher import fetch_businesses, fetch_appointments
from webhook import run_webhook
from analytics import analyze_patients, analyze_service_mix, analyze_clients
from phone_formatter import (
    format_phone_strict, 
    create_phone_analysis, 
    format_phone_dataframe,
    prepare_outlook_contacts
)
from visualizations import (
    create_patient_analysis_charts,
    create_service_mix_charts,
    create_client_analysis_charts,
    display_cancellation_insights
)
from ms_integrations import (
    render_calendar_tab,
    render_forms_tab
)

# ─── Helper Functions ──────────────────────────────────────────────────────────
def filter_appointments(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.subheader("Live Filters")
    status_filter = st.sidebar.multiselect(
        "Status Filter", df["Status"].unique(), df["Status"].unique()
    )
    service_filter = st.sidebar.multiselect(
        "Service Filter", df["Service"].unique(), df["Service"].unique()
    )
    return df[
        df["Status"].isin(status_filter) &
        df["Service"].isin(service_filter)
    ]


def display_appointment_metrics(df: pd.DataFrame) -> None:
    cols = st.columns(4)
    metrics = {
        "Total": len(df),
        "Scheduled": (df["Status"] == "Scheduled").sum(),
        "Completed": (df["Status"] == "Completed").sum(),
        "Cancelled": (df["Status"] == "Cancelled").sum()
    }
    for col, (label, value) in zip(cols, metrics.items()):
        col.metric(label, value)


def display_appointment_table(df: pd.DataFrame) -> None:
    st.dataframe(df, use_container_width=True)


# ─── Session State Initialization ─────────────────────────────────────────────
if 'appointment_data' not in st.session_state:
    st.session_state.appointment_data = pd.DataFrame()
if 'fetch_complete' not in st.session_state:
    st.session_state.fetch_complete = False
if 'webhook_thread' not in st.session_state:
    st.session_state.webhook_thread = None


# ─── Start Webhook Listener ───────────────────────────────────────────────────
def start_webhook_thread():
    """Start the webhook server in a background thread"""
    try:
        if st.session_state.webhook_thread is None or not st.session_state.webhook_thread.is_alive():
            thread = threading.Thread(target=run_webhook, daemon=True)
            thread.start()
            st.session_state.webhook_thread = thread
            return thread
        return st.session_state.webhook_thread
    except Exception as e:
        st.error(f"Failed to start webhook server: {str(e)}")
        return None


# ─── Page Configuration & Theme ───────────────────────────────────────────────
st.set_page_config(
    page_title="Access Care Analytics",
    layout="wide",
    page_icon="🏥",
    initial_sidebar_state="expanded"
)

st.markdown(f"""
<style>
    .main {{
        background-color: {THEME_CONFIG['BACKGROUND_COLOR']};
        color: {THEME_CONFIG['TEXT_COLOR']};
    }}
    .stDataFrame {{
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    h1, h2, h3 {{
        color: {THEME_CONFIG['PRIMARY_COLOR']} !important;
    }}
</style>
""", unsafe_allow_html=True)


# ─── Sidebar Controls ─────────────────────────────────────────────────────────
with st.sidebar:
    if LOGO_PATH:
        st.image(LOGO_PATH, width=120)
    st.title("Filters & Settings")

    # Businesses
    try:
        businesses = asyncio.run(fetch_businesses())
        selected_businesses = []
        if businesses:
            all_selected = st.checkbox("Select All Businesses", True, key="select_all_businesses")
            for idx, biz in enumerate(businesses):
                checkbox_key = f"business_checkbox_{biz['name']}_{idx}"
                if st.checkbox(biz["name"], all_selected, key=checkbox_key):
                    selected_businesses.append(biz["name"])
        else:
            st.warning("No businesses found. Please check your Microsoft Bookings permissions.")
    except Exception as e:
        st.error(f"Error fetching businesses: {str(e)}")
        businesses = []
        selected_businesses = []

    # Date Range
    today = datetime.now(LOCAL_TZ).date()
    default_start = today - timedelta(days=30)
    default_end = today
    
    start_date = st.date_input("Start Date", default_start, max_value=today)
    end_date = st.date_input("End Date", default_end, max_value=today)
    
    if start_date > end_date:
        st.error("Start date must be before end date")
        st.stop()

    # Advanced Settings
    with st.expander("Advanced Settings"):
        max_records = st.slider("Max Records per Business", 100, 5000, 500)
        realtime_updates = st.checkbox("Enable Real-time Updates", False, key="realtime_updates")

    fetch_button = st.button("🔄 Fetch Data")


# ─── Main Layout ───────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 6])
with col1:
    if LOGO_PATH:
        st.image(LOGO_PATH, width=80)
with col2:
    st.title("Access Care Analytics Dashboard")
    if st.session_state.get("last_updated"):
        st.caption(f"Last Updated: {st.session_state.last_updated}")


# ─── Data Fetching Logic ─────────────────────────────────────────────────────
if fetch_button:
    with st.spinner("Collecting data from multiple sources..."):
        try:
            # core appointments
            appointments = asyncio.run(fetch_appointments(
                selected_businesses, start_date, end_date, max_records
            ))

            if appointments:
                # Filter out None values
                appointments = [a for a in appointments if a is not None]
                
                # Convert to DataFrame
                df = pd.DataFrame(appointments)
                
                # Convert datetime columns
                datetime_columns = ['Start Date', 'End Date', 'Created Date', 'Last Updated', 'Cancellation DateTime']
                for col in datetime_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col])
                
                # Add date columns for analysis
                df['Created Date Only'] = df['Created Date'].dt.date
                df['Start Date Only'] = df['Start Date'].dt.date
                df['Hour of Day'] = df['Created Date'].dt.hour
                df['Day of Week'] = df['Created Date'].dt.day_name()
                
                # Store in session state (both new and old variables for compatibility)
                st.session_state['appointments_df'] = df
                st.session_state['appointment_data'] = df.set_index("ID") if "ID" in df.columns else df
                st.session_state['last_fetch'] = datetime.now()
                st.session_state['fetch_complete'] = True
                st.session_state['last_updated'] = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")
                
                # Display success message
                st.success(f"Successfully fetched {len(df)} appointments")
                
                # Display booking trends
                st.subheader("📈 Booking Trends")
                col1, col2 = st.columns(2)
                
                with col1:
                    # Daily booking creation trend
                    daily_bookings = df.groupby('Created Date Only').size().reset_index(name='count')
                    fig_daily = px.line(
                        daily_bookings,
                        x='Created Date Only',
                        y='count',
                        title='Daily Booking Creation Trend',
                        labels={'Created Date Only': 'Date', 'count': 'Number of Bookings'}
                    )
                    st.plotly_chart(fig_daily, use_container_width=True)
                
                with col2:
                    # Hourly booking distribution
                    hourly_bookings = df.groupby('Hour of Day').size().reset_index(name='count')
                    fig_hourly = px.bar(
                        hourly_bookings,
                        x='Hour of Day',
                        y='count',
                        title='Hourly Booking Distribution',
                        labels={'Hour of Day': 'Hour', 'count': 'Number of Bookings'}
                    )
                    st.plotly_chart(fig_hourly, use_container_width=True)
                
                # Status changes and cancellations
                st.subheader("🔄 Appointment Status Changes")
                col3, col4 = st.columns(2)
                
                with col3:
                    # Status distribution
                    status_counts = df['Status'].value_counts().reset_index()
                    status_counts.columns = ['Status', 'Count']
                    fig_status = px.pie(
                        status_counts,
                        values='Count',
                        names='Status',
                        title='Appointment Status Distribution'
                    )
                    st.plotly_chart(fig_status, use_container_width=True)
                
                with col4:
                    # Cancellation reasons
                    if 'Cancellation Reason' in df.columns:
                        cancellation_reasons = df[df['Cancellation Reason'].notna()]['Cancellation Reason'].value_counts().reset_index()
                        cancellation_reasons.columns = ['Reason', 'Count']
                        fig_cancellations = px.bar(
                            cancellation_reasons,
                            x='Reason',
                            y='Count',
                            title='Cancellation Reasons',
                            labels={'Reason': 'Cancellation Reason', 'Count': 'Number of Cancellations'}
                        )
                        st.plotly_chart(fig_cancellations, use_container_width=True)
                
                # Business performance metrics
                st.subheader("📊 Business Performance")
                col5, col6 = st.columns(2)
                
                with col5:
                    # Bookings by business
                    business_bookings = df.groupby('Business').size().reset_index(name='count')
                    fig_business = px.bar(
                        business_bookings,
                        x='Business',
                        y='count',
                        title='Bookings by Business',
                        labels={'Business': 'Business Name', 'count': 'Number of Bookings'}
                    )
                    st.plotly_chart(fig_business, use_container_width=True)
                
                with col6:
                    # Service popularity
                    service_bookings = df.groupby('Service').size().reset_index(name='count')
                    service_bookings = service_bookings.sort_values('count', ascending=False).head(10)
                    fig_service = px.bar(
                        service_bookings,
                        x='Service',
                        y='count',
                        title='Top 10 Most Popular Services',
                        labels={'Service': 'Service Name', 'count': 'Number of Bookings'}
                    )
                    st.plotly_chart(fig_service, use_container_width=True)
                
                # Display the data table
                st.subheader("📋 Appointment Data")
                st.dataframe(df)
                
            else:
                st.warning("No appointments found in the selected date range")
                
        except Exception as e:
            st.error(f"Error fetching appointments: {str(e)}")


# ─── Display Tabs ────────────────────────────────────────────────────────────
if st.session_state.get('fetch_complete', False) and not st.session_state.get('appointment_data', pd.DataFrame()).empty:
    st.markdown("---")
    st.subheader("📋 Detailed Analysis")
    
    df = st.session_state.appointment_data.copy()

    tabs = st.tabs([
        "📋 Appointments",
        "👥 Patient Analysis",
        "🏢 Client Overview",
        "📞 Phone Validation",
        "🧩 Service Mix",
        "🚨 Cancellations",
        "📇 Contact Export",
        "📊 YoY Comparison",
        "📅 Calendar",
        "📝 MS Forms"
    ])

    # — Appointments —
    with tabs[0]:
        st.header("Appointments Overview")
        filtered_df = filter_appointments(df)
        display_appointment_metrics(filtered_df)
        display_appointment_table(filtered_df)

    # — Patient Analysis —
    with tabs[1]:
        st.header("Patient Analysis")
        unique_patients, booking_freq, service_usage, service_counts_dist = analyze_patients(df)
        create_patient_analysis_charts(unique_patients, booking_freq, service_usage, service_counts_dist)

    # — Client Overview —
    with tabs[2]:
        st.header("Client Overview")
        client_analysis = analyze_clients(df)
        create_client_analysis_charts(client_analysis)

    # — Phone Validation —
    with tabs[3]:
        st.header("Phone Number Validation")
        
        # Get phone analysis with unique numbers
        phone_status_df = format_phone_dataframe(df)
        phone_pie, phone_tree = create_phone_analysis(phone_status_df)
        
        # Show phone status distribution
        col1, col2 = st.columns(2)
        with col1:
            if phone_pie:
                st.plotly_chart(phone_pie, use_container_width=True, key="validation_phone_pie")
        with col2:
            if phone_tree:
                st.plotly_chart(phone_tree, use_container_width=True, key="validation_phone_tree")
        
        # Show detailed phone status
        st.write("#### Phone Status Details")
        st.write("Showing unique phone numbers with their validation status:")
        
        # Add color coding based on status
        def highlight_status(row):
            if row["Phone Status"].startswith("Valid"):
                return ["background-color: #e6ffe6"] * len(row)
            elif row["Phone Status"] in ["Missing", "Too Short", "Too Long", "Invalid Format"]:
                return ["background-color: #ffe6e6"] * len(row)
            return ["background-color: #fff2e6"] * len(row)
        
        # Style the dataframe
        styled_df = phone_status_df.style.apply(highlight_status, axis=1)
        st.dataframe(styled_df, use_container_width=True, key="phone_status_table")
        
        st.info("""
        Phone numbers are validated and formatted according to these rules:
        - Ireland (IE): +353 format
        - UK: +44 format
        - US/Canada: +1 (XXX) XXX-XXXX format
        - UAE: +971 format
        - Philippines: +63 format
        - Denmark: +45 format
        - Other: International format with country code
        
        Color coding:
        🟢 Green: Valid phone numbers (will be included in export)
        🔴 Red: Invalid numbers (missing, too short/long)
        🟡 Yellow: Unknown format
        
        Only valid phone numbers will be included in the contact export.
        """)

    # — Service Mix —
    with tabs[4]:
        st.header("Service Mix Analysis")
        service_counts, duration_analysis = analyze_service_mix(df)
        create_service_mix_charts(service_counts, duration_analysis)

    # — Cancellations —
    with tabs[5]:
        st.header("Cancellation Analysis")
        display_cancellation_insights(df)

    # — Contact Export —
    with tabs[6]:
        st.header("Contact Export")
        
        # Create two columns for the export and validation sections
        export_col, validation_col = st.columns(2)
        
        with export_col:
            st.write("### Export Contacts")
            st.write("Export patient contacts in Microsoft Outlook format")
            
            # Prepare contacts data with proper Outlook fields
            outlook_contacts = prepare_outlook_contacts(df)
            
            if not outlook_contacts.empty:
                # Show statistics
                st.write("#### Export Statistics")
                total_contacts = len(outlook_contacts)
                total_with_phone = len(outlook_contacts[outlook_contacts["Business Phone"] != ""])
                
                stats_col1, stats_col2 = st.columns(2)
                with stats_col1:
                    st.metric("Total Contacts", total_contacts)
                with stats_col2:
                    st.metric("With Valid Phone", total_with_phone)
                
                # Show preview of contacts
                st.write("#### Preview")
                st.dataframe(
                    outlook_contacts[["First Name", "Last Name", "E-mail Address", "Business Phone"]].head(),
                    use_container_width=True,
                    key="contact_preview"
                )
                
                # Download button
                csv = outlook_contacts.to_csv(index=False)
                st.download_button(
                    "📥 Download Outlook Contacts CSV",
                    csv,
                    "access_care_contacts.csv",
                    "text/csv",
                    key="download-contacts"
                )
                
                st.info("""
                To import contacts into Outlook:
                1. Open Outlook
                2. Go to File > Open & Export > Import/Export
                3. Choose 'Import from another program or file'
                4. Select 'Comma Separated Values'
                5. Browse to the downloaded CSV file
                6. Choose the Contacts folder as destination
                7. Click Finish
                
                Note: Duplicate phone numbers have been removed, keeping the first occurrence.
                """)
            else:
                st.warning("No contacts available for export")
        
        with validation_col:
            st.write("### Phone Number Distribution")
            if phone_pie:
                st.plotly_chart(phone_pie, use_container_width=True, key="export_phone_pie")
            
            # Show country distribution
            st.write("### Country Distribution")
            if phone_tree:
                st.plotly_chart(phone_tree, use_container_width=True, key="export_phone_tree")
                
    # — Year over Year Comparison —
    with tabs[7]:
        st.header("Year over Year Comparison: 2024 vs 2025")
        
        # Make sure the dataframe has a datetime column
        if 'Start Date' in df.columns:
            df['Year'] = df['Start Date'].dt.year
            df['Month'] = df['Start Date'].dt.month
            df['Month Name'] = df['Start Date'].dt.strftime('%B')
            
            # Filter for 2024 and 2025 data
            comparison_df = df[df['Year'].isin([2024, 2025])]
            
            if not comparison_df.empty:
                # Create monthly comparison data
                monthly_comparison = comparison_df.groupby(['Year', 'Month', 'Month Name']).size().reset_index(name='Appointments')
                monthly_comparison = monthly_comparison.sort_values(['Year', 'Month'])
                
                # Create status breakdown by month and year
                status_comparison = comparison_df.groupby(['Year', 'Month', 'Month Name', 'Status']).size().reset_index(name='Count')
                status_comparison = status_comparison.sort_values(['Year', 'Month'])
                
                # Display metrics for both years
                col1, col2 = st.columns(2)
                with col1:
                    total_2024 = len(comparison_df[comparison_df['Year'] == 2024])
                    total_2025 = len(comparison_df[comparison_df['Year'] == 2025])
                    
                    # Calculate growth
                    if total_2024 > 0:
                        growth = ((total_2025 - total_2024) / total_2024) * 100
                        growth_label = f"{growth:.1f}%"
                    else:
                        growth_label = "N/A"
                    
                    st.subheader("Total Appointments")
                    st.metric("2024", total_2024)
                    st.metric("2025", total_2025, delta=growth_label)
                
                with col2:
                    # Calculate completed appointment rates
                    completed_2024 = comparison_df[(comparison_df['Year'] == 2024) & (comparison_df['Status'] == 'Completed')].shape[0]
                    completed_2025 = comparison_df[(comparison_df['Year'] == 2025) & (comparison_df['Status'] == 'Completed')].shape[0]
                    
                    if total_2024 > 0:
                        rate_2024 = (completed_2024 / total_2024) * 100
                    else:
                        rate_2024 = 0
                        
                    if total_2025 > 0:
                        rate_2025 = (completed_2025 / total_2025) * 100
                    else:
                        rate_2025 = 0
                    
                    st.subheader("Completion Rate")
                    st.metric("2024", f"{rate_2024:.1f}%")
                    st.metric("2025", f"{rate_2025:.1f}%", delta=f"{rate_2025 - rate_2024:.1f}%")
                
                # Monthly trend charts
                st.subheader("Monthly Appointment Trends")
                
                # Bar chart comparison
                monthly_fig = px.bar(
                    monthly_comparison,
                    x='Month Name',
                    y='Appointments',
                    color='Year',
                    barmode='group',
                    title='Monthly Appointments: 2024 vs 2025',
                    labels={'Appointments': 'Number of Appointments', 'Month Name': 'Month'},
                    color_discrete_map={2024: '#1f77b4', 2025: '#ff7f0e'}
                )
                
                # Customize x-axis order (January to December)
                month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                              'July', 'August', 'September', 'October', 'November', 'December']
                monthly_fig.update_layout(xaxis={'categoryorder': 'array', 'categoryarray': month_order})
                
                st.plotly_chart(monthly_fig, use_container_width=True)
                
                # Status breakdown
                st.subheader("Appointment Status by Month")
                
                # Let user select to view 2024 or 2025 data
                year_to_view = st.radio("Select Year to View", [2024, 2025], horizontal=True)
                
                # Filter data for selected year
                year_status_data = status_comparison[status_comparison['Year'] == year_to_view]
                
                if not year_status_data.empty:
                    # Create stacked bar chart for status breakdown
                    status_fig = px.bar(
                        year_status_data,
                        x='Month Name',
                        y='Count',
                        color='Status',
                        title=f'Appointment Status Breakdown by Month ({year_to_view})',
                        labels={'Count': 'Number of Appointments', 'Month Name': 'Month'},
                        color_discrete_map={
                            'Scheduled': '#2ca02c',
                            'Completed': '#1f77b4',
                            'Cancelled': '#d62728'
                        }
                    )
                    
                    # Customize x-axis order (January to December)
                    status_fig.update_layout(xaxis={'categoryorder': 'array', 'categoryarray': month_order})
                    
                    st.plotly_chart(status_fig, use_container_width=True)
                    
                    # Show data table
                    st.subheader(f"Monthly Data ({year_to_view})")
                    
                    # Pivot the data for better display
                    pivot_df = year_status_data.pivot_table(
                        index=['Month Name'], 
                        columns='Status', 
                        values='Count', 
                        aggfunc='sum'
                    ).reset_index()
                    
                    # Add a Total column
                    pivot_df['Total'] = pivot_df.sum(axis=1, numeric_only=True)
                    
                    # Sort by month
                    month_mapping = {month: i for i, month in enumerate(month_order)}
                    pivot_df['month_idx'] = pivot_df['Month Name'].map(month_mapping)
                    pivot_df = pivot_df.sort_values('month_idx').drop('month_idx', axis=1)
                    
                    # Display the table
                    st.dataframe(pivot_df, use_container_width=True)
                else:
                    st.warning(f"No appointment data available for {year_to_view}")
            else:
                st.warning("No data available for 2024-2025 comparison. Please ensure your date range includes data from both years.")
        else:
            st.error("Required date columns are missing in the appointment data.")

    # — Calendar —
    with tabs[8]:
        render_calendar_tab(df)

    # — MS Forms —
    with tabs[9]:
        render_forms_tab()

else:
    st.info("Select filters and click 'Fetch Data' to begin analysis")

# Start webhook thread if realtime updates are enabled
if st.session_state.get("realtime_updates", False):
    webhook_thread = start_webhook_thread()
    if webhook_thread is None:
        st.warning("Real-time updates are disabled due to webhook server startup failure")
