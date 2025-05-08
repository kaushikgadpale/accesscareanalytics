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
from phone_formatter import format_phone_strict, create_phone_analysis, format_phone_dataframe
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
        unique_patients, booking_freq, service_usage = analyze_patients(df)
        create_patient_analysis_charts(unique_patients, booking_freq, service_usage)

    # — Client Overview —
    with tabs[2]:
        st.header("Client Overview")
        client_analysis = analyze_clients(df)
        create_client_analysis_charts(client_analysis)

    # — Phone Validation —
    with tabs[3]:
        st.header("Phone Number Validation")
        cleaned_phones = format_phone_dataframe(df)
        create_phone_analysis(cleaned_phones)

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
        st.write("Export patient contacts for Microsoft Outlook")
        
        # Prepare contacts data
        contacts_df = df[["Customer", "Email", "Phone"]].drop_duplicates()
        contacts_df = contacts_df[contacts_df["Email"].notna()]  # Remove rows without email
        
        # Add export options
        st.write("#### Export Options")
        include_phone = st.checkbox("Include phone numbers", True)
        
        # Create CSV content
        if include_phone:
            export_df = contacts_df
        else:
            export_df = contacts_df[["Customer", "Email"]]
            
        # Download button
        if not export_df.empty:
            csv = export_df.to_csv(index=False)
            st.download_button(
                "📥 Download Contacts CSV",
                csv,
                "access_care_contacts.csv",
                "text/csv",
                key="download-contacts"
            )
            
            st.info("""
            To import contacts into Outlook:
            1. Download the CSV file
            2. Open Outlook
            3. Go to People (Contacts)
            4. Click 'Import Contacts' or 'Import from file'
            5. Select the downloaded CSV file
            6. Map the columns to Outlook contact fields
            7. Complete the import
            """)
        else:
            st.warning("No contacts available for export")

else:
    st.info("Select filters and click 'Fetch Data' to begin analysis")

# Start webhook thread if realtime updates are enabled
if st.session_state.get("realtime_updates", False):
    webhook_thread = start_webhook_thread()
    if webhook_thread is None:
        st.warning("Real-time updates are disabled due to webhook server startup failure")
