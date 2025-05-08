import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from config import (
    LOCAL_TZ,
    LOGO_PATH,
    DATE_PRESETS,
    THEME_CONFIG,
    BOOKINGS_MAILBOXES,
    WEBHOOK_PUBLIC_URL
)
from auth import get_auth_headers
from data_fetcher import fetch_businesses, fetch_appointments
from email_integration import fetch_cancelled_emails
from webhook import start_webhook_thread
from analytics import analyze_patients, analyze_service_mix, analyze_clients
from phone_formatter import format_phone_strict, create_phone_analysis
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


# ─── Start Webhook Listener ───────────────────────────────────────────────────
start_webhook_thread(WEBHOOK_PUBLIC_URL)


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
    st.image(LOGO_PATH, width=120)
    st.title("Filters & Settings")

    # Businesses
    businesses = fetch_businesses()
    selected_businesses = []
    if businesses:
        all_selected = st.checkbox("Select All Businesses", True)
        for biz in businesses:
            if st.checkbox(biz["name"], all_selected):
                selected_businesses.append(biz["name"])

    # Date Range
    date_preset = st.selectbox("Date Preset", list(DATE_PRESETS.keys()))
    if date_preset != "Custom":
        from_date, to_date = DATE_PRESETS[date_preset]
    else:
        from_date = st.date_input("Start Date")
        to_date = st.date_input("End Date")

    # Advanced Settings
    with st.expander("Advanced Settings"):
        max_records = st.slider("Max Records per Business", 100, 5000, 500)
        include_emails = st.checkbox("Include Email Cancellations", True)
        realtime_updates = st.checkbox("Enable Real-time Updates", False)

        if realtime_updates:
            st.write("Subscribed Mailboxes:")
            for mailbox in BOOKINGS_MAILBOXES:
                st.write(f"- {mailbox}")

    fetch_button = st.button("🔄 Fetch Data")


# ─── Main Layout ───────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 6])
with col1:
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
                selected_businesses, from_date, to_date, max_records
            )

            # email cancellations
            if include_emails:
                for mailbox in BOOKINGS_MAILBOXES:
                    appointments += fetch_cancelled_emails(mailbox, max_records)

            if appointments:
                df = pd.DataFrame(appointments)
                df.set_index("ID", inplace=True)
                st.session_state.appointment_data = df
                st.session_state.fetch_complete = True
                st.session_state.last_updated = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")
                st.success("Data loaded successfully!")
            else:
                st.warning("No appointments found with current filters.")

        except Exception as e:
            st.error(f"Data fetch failed: {e}")


# ─── Display Tabs ────────────────────────────────────────────────────────────
if st.session_state.fetch_complete and not st.session_state.appointment_data.empty:
    df = st.session_state.appointment_data.copy()

    tabs = st.tabs([
        "📋 Appointments",
        "👥 Patient Analysis",
        "🏢 Client Overview",
        "📞 Phone Validation",
        "🧩 Service Mix",
        "🚨 Cancellations"
    ])

    # — Appointments —
    with tabs[0]:
        st.header("Appointment Details")
        filtered = filter_appointments(df)
        display_appointment_metrics(filtered)
        display_appointment_table(filtered)

    # — Patient Analysis —
    with tabs[1]:
        st.header("Patient Insights")
        _, booking_freq, service_usage = analyze_patients(df)
        create_patient_analysis_charts(booking_freq, service_usage)

    # — Client Overview —
    with tabs[2]:
        st.header("Client Performance")
        client_analysis = analyze_clients(df)
        create_client_analysis_charts(client_analysis)

    # — Phone Validation —
    with tabs[3]:
        st.header("Phone Number Analysis")
        cleaned = format_phone_strict(df)
        pie, tree = create_phone_analysis(cleaned)
        st.plotly_chart(pie, use_container_width=True)
        st.plotly_chart(tree, use_container_width=True)

    # — Service Mix —
    with tabs[4]:
        st.header("Service Analysis")
        service_counts, service_duration = analyze_service_mix(df)
        create_service_mix_charts(service_counts, service_duration)

    # — Cancellations —
    with tabs[5]:
        st.header("Cancellation Analysis")
        display_cancellation_insights(df)

else:
    st.info("Select filters and click 'Fetch Data' to begin analysis")
