import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import threading

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
        businesses = fetch_businesses()
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
            appointments = fetch_appointments(
                selected_businesses, start_date, end_date, max_records
            )

            if appointments:
                # Filter out None values
                appointments = [apt for apt in appointments if apt is not None]
                if appointments:
                    df = pd.DataFrame(appointments)
                    df.set_index("ID", inplace=True)
                    st.session_state.appointment_data = df
                    st.session_state.fetch_complete = True
                    st.session_state.last_updated = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")
                    st.success("Data loaded successfully!")
                else:
                    st.warning("No valid appointments found with current filters.")
            else:
                st.warning("No appointments found with current filters.")

        except Exception as e:
            st.error(f"Data fetch failed: {str(e)}")


# ─── Display Tabs ────────────────────────────────────────────────────────────
if st.session_state.fetch_complete and not st.session_state.appointment_data.empty:
    df = st.session_state.appointment_data.copy()

    tabs = st.tabs([
        "📋 Appointments",
        "👥 Patient Analysis",
        "🏢 Client Overview",
        "📞 Phone Validation",
        "🧩 Service Mix",
        "🚨 Cancellations",
        "📇 Contact Export"
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

else:
    st.info("Select filters and click 'Fetch Data' to begin analysis")

# Start webhook thread if realtime updates are enabled
if st.session_state.get("realtime_updates", False):
    webhook_thread = start_webhook_thread()
    if webhook_thread is None:
        st.warning("Real-time updates are disabled due to webhook server startup failure")
