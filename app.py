import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from config import (
    LOCAL_TZ, LOGO_PATH, DATE_PRESETS, THEME_CONFIG,
    BOOKINGS_MAILBOXES, WEBHOOK_PUBLIC_URL
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
    create_client_analysis_charts
)

# Initialize session state
if 'appointment_data' not in st.session_state:
    st.session_state.appointment_data = pd.DataFrame()
if 'fetch_complete' not in st.session_state:
    st.session_state.fetch_complete = False
if 'subscriptions' not in st.session_state:
    st.session_state.subscriptions = {}

# Start webhook thread
start_webhook_thread()

# Configure page
st.set_page_config(
    page_title="Access Care Analytics",
    layout="wide",
    page_icon="🏥",
    initial_sidebar_state="expanded"
)

# Apply theme
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

# Sidebar Controls
with st.sidebar:
    st.image(LOGO_PATH, width=120)
    st.title("Filters & Settings")
    
    # Business selection
    businesses = fetch_businesses()
    selected_businesses = []
    if businesses:
        all_selected = st.checkbox("Select All Businesses", True)
        for biz in businesses:
            if st.checkbox(biz["name"], all_selected):
                selected_businesses.append(biz)
    
    # Date selection
    date_preset = st.selectbox("Date Preset", list(DATE_PRESETS.keys()))
    if date_preset != "Custom":
        from_date, to_date = DATE_PRESETS[date_preset]
    else:
        from_date = st.date_input("Start Date")
        to_date = st.date_input("End Date")
    
    # Advanced settings
    with st.expander("Advanced Settings"):
        max_records = st.slider("Max Records per Business", 100, 5000, 500)
        include_emails = st.checkbox("Include Email Cancellations", True)
        realtime_updates = st.checkbox("Enable Real-time Updates", False)
        
        if realtime_updates:
            st.write("Subscribed Mailboxes:")
            for mailbox in BOOKINGS_MAILBOXES:
                st.write(f"- {mailbox}")

# Main Interface
col1, col2 = st.columns([1, 6])
with col1:
    st.image(LOGO_PATH, width=80)
with col2:
    st.title("Access Care Analytics Dashboard")
    if st.session_state.get("last_updated"):
        st.caption(f"Last Updated: {st.session_state.last_updated}")

# Data Fetching
if st.sidebar.button("🔄 Fetch Data"):
    with st.spinner("Collecting data from multiple sources..."):
        try:
            # Fetch core appointments
            appointments = fetch_appointments(
                selected_businesses, from_date, to_date, max_records
            )
            
            # Add email cancellations
            if include_emails and BOOKINGS_MAILBOXES:
                for mailbox in BOOKINGS_MAILBOXES:
                    appointments += fetch_cancelled_emails(mailbox, max_records)
            
            # Update session state
            if appointments:
                df = pd.DataFrame(appointments)
                df.set_index("ID", inplace=True)
                st.session_state.appointment_data = df
                st.session_state.fetch_complete = True
                st.session_state.last_updated = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")
                st.success("Data loaded successfully!")
            else:
                st.warning("No appointments found with current filters")
        
        except Exception as e:
            st.error(f"Data fetch failed: {str(e)}")

# Main Display Tabs
if st.session_state.fetch_complete and not st.session_state.appointment_data.empty:
    df = st.session_state.appointment_data
    tabs = st.tabs([
        "📋 Appointments", "👥 Patient Analysis",
        "🏢 Client Overview", "📞 Phone Validation",
        "🧩 Service Mix", "🚨 Cancellations"
    ])
    
    with tabs[0]:  # Appointments Tab
        st.header("Appointment Details")
        filtered_df = filter_appointments(df)
        display_appointment_metrics(filtered_df)
        display_appointment_table(filtered_df)
    
    with tabs[1]:  # Patient Analysis
        st.header("Patient Insights")
        up, bf, sp = analyze_patients(df)
        create_patient_analysis_charts(bf, sp)
    
    with tabs[2]:  # Client Overview
        st.header("Client Performance")
        ca = analyze_clients(df)
        create_client_analysis_charts(ca)
    
    with tabs[3]:  # Phone Validation
        st.header("Phone Number Analysis")
        pie, tree = create_phone_analysis(df)
        st.plotly_chart(pie, use_container_width=True)
        st.plotly_chart(tree, use_container_width=True)
    
    with tabs[4]:  # Service Mix
        st.header("Service Analysis")
        sc, sd = analyze_service_mix(df)
        create_service_mix_charts(sc, sd)
    
    with tabs[5]:  # Cancellations
        st.header("Cancellation Analysis")
        display_cancellation_insights(df)

else:
    st.info("Select filters and click 'Fetch Data' to begin analysis")

# Helper functions for UI components
def filter_appointments(df):
    st.sidebar.subheader("Live Filters")
    status_filter = st.sidebar.multiselect(
        "Status Filter", df["Status"].unique(), df["Status"].unique()
    )
    service_filter = st.sidebar.multiselect(
        "Service Filter", df["Service"].unique(), df["Service"].unique()
    )
    return df[
        (df["Status"].isin(status_filter)) &
        (df["Service"].isin(service_filter))
    ]

def display_appointment_metrics(df):
    cols = st.columns(4)
    metrics = {
        "Total": len(df),
        "Scheduled": (df["Status"] == "Scheduled").sum(),
        "Completed": (df["Status"] == "Completed").sum(),
        "Cancelled": (df["Status"] == "Cancelled").sum()
    }
    for col, (label, value) in zip(cols, metrics.items()):
        col.metric(label, value)