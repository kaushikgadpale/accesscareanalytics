import plotly.express as px

def create_patient_analysis_charts(booking_freq, service_usage):
    """Generate patient analysis visualizations"""
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(
            booking_freq.head(10),
            x="Customer",
            y="Total_Appointments",
            title="Top Patients by Appointments",
            color="Total_Appointments"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.treemap(
            service_usage.head(15),
            path=["Customer", "Services"],
            values="Service_Count",
            title="Service Utilization by Patient"
        )
        st.plotly_chart(fig, use_container_width=True)

def create_service_mix_charts(service_counts, service_duration):
    """Generate service analysis visualizations"""
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