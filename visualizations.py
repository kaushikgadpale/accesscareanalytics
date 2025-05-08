import streamlit as st
import plotly.express as px
import pandas as pd


def create_patient_analysis_charts(unique_patients, booking_freq, service_usage, service_counts_dist):
    """Generate patient analysis visualizations"""
    # First row - Appointments and Services
    col1, col2 = st.columns(2)

    with col1:
        st.write("#### Top Patients by Appointments")
        fig = px.bar(
            booking_freq.head(10),
            x="Customer",
            y="Total_Appointments",
            title="Top 10 Patients by Total Appointments",
            color="Total_Appointments"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.write("#### Service Count Distribution")
        fig = px.pie(
            service_counts_dist,
            values="Patient_Count",
            names="Number_of_Services",
            title="Number of Services per Patient",
            hole=0.3,
            labels={"Number_of_Services": "Number of Services", "Patient_Count": "Number of Patients"}
        )
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    # Second row - Visit Patterns and Cancellations
    col3, col4 = st.columns(2)

    with col3:
        st.write("#### Visit Frequency Analysis")
        fig = px.histogram(
            booking_freq,
            x="Days_Between_Visits",
            title="Days Between Patient Visits",
            nbins=20
        )
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        st.write("#### Cancellation Rates")
        fig = px.box(
            booking_freq,
            y="Cancellation_Rate",
            title="Patient Cancellation Rate Distribution",
            points="all"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Display detailed patient metrics
    st.write("### Detailed Patient Metrics")
    metrics = pd.merge(booking_freq, service_usage[["Email", "Services", "Preferred_Business"]], on="Email")
    st.dataframe(metrics, use_container_width=True)


def create_service_mix_charts(service_counts, service_duration):
    """Generate service mix visualizations"""
    col1, col2 = st.columns(2)

    with col1:
        fig = px.pie(
            service_counts,
            names="Service",
            values="Count",
            title="Service Distribution",
            hole=0.3
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            service_duration.head(10),
            x="Service",
            y="Avg_Duration",
            title="Average Service Duration",
            color="Appointment_Count"
        )
        st.plotly_chart(fig, use_container_width=True)


def create_client_analysis_charts(client_analysis):
    """Generate client analysis visualizations"""
    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            client_analysis.sort_values("Total_Appointments", ascending=False).head(10),
            x="Business",
            y="Total_Appointments",
            title="Top Clients by Appointments",
            color="Total_Appointments"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            client_analysis.sort_values("Cancellation_Rate", ascending=False).head(10),
            x="Business",
            y="Cancellation_Rate",
            title="Cancellation Rate by Client",
            color="Cancellation_Rate"
        )
        st.plotly_chart(fig, use_container_width=True)


def display_cancellation_insights(df):
    """Show cancellation-specific analytics"""
    cancellations = df[df["Status"] == "Cancelled"]
    col1, col2 = st.columns(2)

    with col1:
        fig = px.histogram(
            cancellations,
            x="Start Date",
            title="Cancellation Timeline",
            nbins=20
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.sunburst(
            cancellations,
            path=["Business", "Service"],
            title="Cancellation Breakdown"
        )
        st.plotly_chart(fig, use_container_width=True)
