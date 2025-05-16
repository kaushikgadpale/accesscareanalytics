import streamlit as st
import plotly.express as px
import pandas as pd


def format_business_name(name, max_length=20):
    """Format business name to a standard length with ellipsis if needed"""
    if len(name) <= max_length:
        return name
    return name[:max_length-3] + "..."


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
    # Format business names
    service_counts = service_counts.copy()
    service_counts["Service"] = service_counts["Service"].apply(format_business_name)
    
    service_duration = service_duration.copy()
    service_duration["Service"] = service_duration["Service"].apply(format_business_name)
    
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
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)


def create_client_analysis_charts(client_analysis):
    """Generate client analysis visualizations"""
    # Create a copy with formatted business names
    client_analysis_formatted = client_analysis.copy()
    client_analysis_formatted["Business_Short"] = client_analysis_formatted["Business"].apply(format_business_name)
    
    # Overall metrics
    st.write("### Overall Business Metrics")
    total_appointments = client_analysis["Total_Appointments"].sum()
    avg_cancellation = client_analysis["Cancellation_Rate"].mean()
    total_patients = client_analysis["Recurring_Patients"].sum()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Appointments", f"{total_appointments:,}")
    with col2:
        st.metric("Average Cancellation Rate", f"{avg_cancellation:.1f}%")
    with col3:
        st.metric("Total Unique Patients", f"{total_patients:,}")
    
    # Detailed client metrics
    st.write("### Detailed Client Metrics")
    
    # Simple styling without background gradient
    def style_dataframe(df):
        return df.style.format({
            'Total_Appointments': '{:,.0f}',
            'Cancellation_Rate': '{:.1f}%',
            'Recurring_Patients': '{:,.0f}',
            'Unique_Services': '{:,.0f}'
        })
    
    styled_df = style_dataframe(client_analysis)
    st.dataframe(
        styled_df,
        use_container_width=True,
        key="client_metrics"
    )
    
    # Visualizations
    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            client_analysis_formatted,
            x="Business_Short",
            y="Total_Appointments",
            title="Appointments by Business",
            color="Total_Appointments"
        )
        fig.update_layout(
            xaxis_tickangle=-45,
            height=500  # Make the graph taller
        )
        st.plotly_chart(fig, use_container_width=True, key="client_appointments")

    with col2:
        fig = px.scatter(
            client_analysis_formatted,
            x="Total_Appointments",
            y="Cancellation_Rate",
            size="Recurring_Patients",
            color="Unique_Services",
            hover_data=["Business"],  # Show full business name on hover
            title="Business Performance Matrix"
        )
        fig.update_layout(height=500)  # Make the graph taller
        st.plotly_chart(fig, use_container_width=True, key="client_matrix")


def create_booking_trends(df):
    """Generate booking trend analysis visualizations"""
    if df.empty:
        return
    
    # Format business names in the dataframe
    df = df.copy()
    df["Business"] = df["Business"].apply(format_business_name)
    
    # Convert to datetime if not already
    df["Start Date"] = pd.to_datetime(df["Start Date"])
    
    # Daily booking counts
    daily_bookings = df.groupby(
        [df["Start Date"].dt.date, "Status"]
    ).size().reset_index(name="Count")
    
    # Weekly booking counts
    weekly_bookings = df.groupby(
        [pd.Grouper(key="Start Date", freq="W"), "Status"]
    ).size().reset_index(name="Count")
    
    # Monthly booking counts
    monthly_bookings = df.groupby(
        [pd.Grouper(key="Start Date", freq="ME"), "Status"]
    ).size().reset_index(name="Count")
    
    # Visualizations
    st.write("### Daily Booking Trends")
    fig_daily = px.line(
        daily_bookings,
        x="Start Date",
        y="Count",
        color="Status",
        title="Daily Booking Volume"
    )
    st.plotly_chart(fig_daily, use_container_width=True, key="daily_trends")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### Weekly Trends")
        fig_weekly = px.line(
            weekly_bookings,
            x="Start Date",
            y="Count",
            color="Status",
            title="Weekly Booking Volume"
        )
        st.plotly_chart(fig_weekly, use_container_width=True, key="weekly_trends")
    
    with col2:
        st.write("### Monthly Trends")
        fig_monthly = px.line(
            monthly_bookings,
            x="Start Date",
            y="Count",
            color="Status",
            title="Monthly Booking Volume"
        )
        st.plotly_chart(fig_monthly, use_container_width=True, key="monthly_trends")
    
    # Business-wise growth
    st.write("### Business Growth Analysis")
    business_growth = df.groupby(
        [pd.Grouper(key="Start Date", freq="ME"), "Business"]
    ).size().reset_index(name="Bookings")
    
    fig_growth = px.line(
        business_growth,
        x="Start Date",
        y="Bookings",
        color="Business",
        title="Business Growth Over Time"
    )
    st.plotly_chart(fig_growth, use_container_width=True, key="business_growth")
    
    # Time of day analysis
    st.write("### Booking Time Analysis")
    df["Hour"] = df["Start Date"].dt.hour
    hourly_bookings = df.groupby("Hour").size().reset_index(name="Count")
    
    fig_hourly = px.bar(
        hourly_bookings,
        x="Hour",
        y="Count",
        title="Popular Booking Hours",
        labels={"Hour": "Hour of Day (24h)", "Count": "Number of Bookings"}
    )
    st.plotly_chart(fig_hourly, use_container_width=True, key="hourly_analysis")


def display_cancellation_insights(df):
    """Show detailed cancellation analytics"""
    # Format business names in the dataframe
    df = df.copy()
    df["Business"] = df["Business"].apply(format_business_name)
    
    st.write("## Cancellation Analysis")
    
    # Filter cancellations
    cancellations = df[df["Status"] == "Cancelled"].copy()
    if cancellations.empty:
        st.info("No cancellations found in the selected date range.")
        return
    
    # Calculate overall metrics
    total_bookings = len(df)
    total_cancellations = len(cancellations)
    cancellation_rate = (total_cancellations / total_bookings) * 100
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Cancellations", f"{total_cancellations:,}")
    with col2:
        st.metric("Overall Cancellation Rate", f"{cancellation_rate:.1f}%")
    with col3:
        st.metric("Total Affected Hours", f"{cancellations['Duration (min)'].sum() / 60:.1f}")
    with col4:
        notifications_sent = cancellations["Cancellation Notification Sent"].sum()
        st.metric("Notifications Sent", f"{notifications_sent:,}")
    
    # Booking Channel Analysis
    st.write("### Booking Channel Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        # Self-service vs. Staff bookings
        self_service_counts = cancellations["Self Service ID"].notna().value_counts()
        fig = px.pie(
            values=self_service_counts.values,
            names=["Staff Booked", "Self Service"],
            title="Cancellations by Booking Channel",
            hole=0.3
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Online vs. In-person appointments
        location_counts = cancellations["Is Online"].value_counts()
        fig = px.pie(
            values=location_counts.values,
            names=["In Person", "Online"],
            title="Cancelled Appointment Types",
            hole=0.3
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Communication Preferences
    st.write("### Communication Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        # SMS and Email preferences
        comm_prefs = pd.DataFrame({
            "Channel": ["SMS Enabled", "Email Opted Out"],
            "Count": [
                cancellations["SMS Enabled"].sum(),
                cancellations["Opt Out of Email"].sum()
            ]
        })
        fig = px.bar(
            comm_prefs,
            x="Channel",
            y="Count",
            title="Communication Preferences",
            color="Count"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Customer management permissions
        mgmt_counts = cancellations["Customer Can Manage"].value_counts()
        fig = px.pie(
            values=mgmt_counts.values,
            names=["No Self-Management", "Can Self-Manage"],
            title="Booking Management Permissions",
            hole=0.3
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Time Analysis
    st.write("### Timing Analysis")
    col1, col2 = st.columns(2)

    with col1:
        # Time from creation to cancellation
        cancellations["Booking Duration (Hours)"] = (
            cancellations["Cancellation DateTime"] - cancellations["Created Date"]
        ).dt.total_seconds() / 3600
        
        fig = px.histogram(
            cancellations,
            x="Booking Duration (Hours)",
            title="Time from Booking to Cancellation",
            nbins=20
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Buffer time analysis
        buffer_data = pd.DataFrame({
            "Type": ["Pre-appointment", "Post-appointment"],
            "Average Minutes": [
                cancellations["Pre Buffer (min)"].mean(),
                cancellations["Post Buffer (min)"].mean()
            ]
        })
        fig = px.bar(
            buffer_data,
            x="Type",
            y="Average Minutes",
            title="Average Buffer Times for Cancelled Appointments",
            color="Type"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Price Analysis
    st.write("### Financial Impact")
    col1, col2 = st.columns(2)
    
    with col1:
        # Total value of cancelled appointments
        total_value = cancellations["Price"].sum()
        avg_value = cancellations["Price"].mean()
        
        value_metrics = pd.DataFrame({
            "Metric": ["Total Value Lost", "Average Appointment Value"],
            "Amount": [total_value, avg_value]
        })
        
        fig = px.bar(
            value_metrics,
            x="Metric",
            y="Amount",
            title="Financial Impact of Cancellations",
            color="Metric"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Price type distribution
        price_type_counts = cancellations["Price Type"].value_counts()
        fig = px.pie(
            values=price_type_counts.values,
            names=price_type_counts.index,
            title="Price Type Distribution",
            hole=0.3
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Staff Impact
    st.write("### Staff Impact")
    staff_cancellations = (
        cancellations["Staff Members"]
        .str.split(", ", expand=True)
        .stack()
        .value_counts()
        .reset_index()
    )
    staff_cancellations.columns = ["Staff ID", "Cancelled Appointments"]
    
    fig = px.bar(
        staff_cancellations.head(10),
        x="Staff ID",
        y="Cancelled Appointments",
        title="Top 10 Staff Members by Cancellations",
        color="Cancelled Appointments"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed Cancellations Table
    st.write("### Detailed Cancellation Records")
    detailed_view = cancellations[[
        "Business", "Customer", "Service", "Price",
        "Start Date", "Created Date", "Cancellation DateTime",
        "Is Online", "SMS Enabled", "Staff Members",
        "Cancellation Reason", "Cancellation Details",
        "Customer Location", "Service Location"
    ]].sort_values("Start Date", ascending=False)
    
    st.dataframe(detailed_view, use_container_width=True)
