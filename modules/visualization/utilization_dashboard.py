import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import calendar

def format_metric(value, is_percentage=True):
    """Format metric values without decimals"""
    if is_percentage:
        return f"{int(round(value * 100))}%"
    return f"{int(round(value))}"

def create_utilization_dashboard(df, interactive=True, dark_mode=False):
    """
    Create interactive visualizations for utilization data with enhanced analytics
    
    Args:
        df: DataFrame containing utilization data
        interactive: Whether to include interactive elements (toggles, filters)
        dark_mode: Whether to use dark mode for visualizations
        
    Returns:
        None (displays visualizations in Streamlit)
    """
    if df.empty:
        st.warning("⚠️ No utilization data available to display")
        return
    
    # Set color theme based on mode
    if dark_mode:
        color_theme = {
            'bg': '#1e1e1e',
            'text': '#ffffff',
            'accent': '#4dabf7',
            'chart_colors': px.colors.sequential.Plasma,
            'success': '#00b894',
            'warning': '#fdcb6e',
            'error': '#d63031'
        }
    else:
        color_theme = {
            'bg': '#ffffff',
            'text': '#333333',
            'accent': '#3498db',
            'chart_colors': px.colors.sequential.Viridis,
            'success': '#00b894',
            'warning': '#fdcb6e',
            'error': '#e74c3c'
        }
    
    # Title with custom styling
    st.markdown(f"""
    <div style="background-color: {color_theme['bg']}; padding: 20px; border-radius: 10px; 
         margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="color: {color_theme['accent']}; margin: 0; font-weight: 600;">
            <span style="margin-right: 10px;">📊</span> 
            Utilization Analytics Dashboard
        </h2>
        <p style="color: {color_theme['text']}; margin-top: 10px; margin-bottom: 0;">
            Detailed metrics and visualizations to track appointment utilization across clients, 
            services, and locations. Current data shows {df['Client'].nunique()} clients across {df['Site'].nunique()} sites.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Interactive controls for visualization options
    if interactive:
        with st.expander("🔧 Visualization Options", expanded=True):
            view_options_col1, view_options_col2 = st.columns(2)
            
            with view_options_col1:
                chart_type = st.selectbox(
                    "Chart Type for Client Performance",
                    options=["Bar Chart", "Treemap", "Scatter Plot"],
                    index=0
                )
                
                time_grouping = st.selectbox(
                    "Time Series Grouping",
                    options=["Monthly", "Quarterly", "Yearly"],
                    index=0
                )
            
            with view_options_col2:
                top_n_clients = st.slider(
                    "Number of Top Clients to Show",
                    min_value=5,
                    max_value=20,
                    value=10,
                    step=1
                )
                
                show_trends = st.checkbox("Show Trend Lines", value=True)
    else:
        chart_type = "Bar Chart"
        time_grouping = "Monthly"
        top_n_clients = 10
        show_trends = True
    
    # Prepare data for metrics
    # Calculate key metrics even if they don't exist in the DataFrame
    if 'Booking Rate' not in df.columns and 'Total Booking Appts' in df.columns and 'Headcount' in df.columns:
        df['Booking Rate'] = df['Total Booking Appts'] / df['Headcount']
        
    if 'Show Rate' not in df.columns and 'Total Completed Appts' in df.columns and 'Total Booking Appts' in df.columns:
        df['Show Rate'] = df['Total Completed Appts'] / df['Total Booking Appts']
        
    if 'Utilization Rate' not in df.columns and 'Total Completed Appts' in df.columns and 'Headcount' in df.columns:
        df['Utilization Rate'] = df['Total Completed Appts'] / df['Headcount']
    
    # Enhanced metric cards with visual indicators
    st.markdown("### 📌 Key Performance Indicators")
    
    metrics_container = st.container()
    
    with metrics_container:
        kpi_cols = st.columns(4)
        
        with kpi_cols[0]:
            st.markdown(f"""
            <div class="card metric-card">
                <div class="metric-value">{format_metric(df['Show Rate'].mean())}</div>
                <div class="metric-label">Show Rate</div>
            </div>
            """, unsafe_allow_html=True)
        
        with kpi_cols[1]:
            st.markdown(f"""
            <div class="card metric-card">
                <div class="metric-value">{format_metric(df['Booking Rate'].mean())}</div>
                <div class="metric-label">Booking Rate</div>
            </div>
            """, unsafe_allow_html=True)
        
        with kpi_cols[2]:
            st.markdown(f"""
            <div class="card metric-card">
                <div class="metric-value">{format_metric(df['Utilization Rate'].mean())}</div>
                <div class="metric-label">Utilization</div>
            </div>
            """, unsafe_allow_html=True)
        
        with kpi_cols[3]:
            st.markdown(f"""
            <div class="card metric-card">
                <div class="metric-value">{format_metric(df['Utilization Rate'].mean())}</div>
                <div class="metric-label">Efficiency</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Utilization rates with enhanced visualization
    st.markdown("### 📊 Utilization Metrics")
    
    # Add explanation for utilization rates
    st.markdown("""
    <div style="background-color: #e8f4f8; padding: 15px; border-left: 4px solid #4dabf7; border-radius: 5px; margin-bottom: 20px;">
        <h4 style="margin-top: 0; margin-bottom: 10px; color: #0c63e4;">Understanding Utilization Metrics</h4>
        <p style="margin-bottom: 8px;">These metrics show the effectiveness of your appointment scheduling and completion process:</p>
        <ul style="margin-bottom: 0;">
            <li><strong>Booking Rate</strong>: Percentage of eligible employees who booked appointments - measures marketing effectiveness</li>
            <li><strong>Show Rate</strong>: Percentage of booked appointments that were completed - measures attendance reliability</li>
            <li><strong>Utilization Rate</strong>: Percentage of eligible employees who completed appointments - measures overall program success</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Create a combined gauge chart for the three key rates
    rates_fig = make_subplots(
        rows=1, cols=3,
        specs=[[{'type': 'indicator'}, {'type': 'indicator'}, {'type': 'indicator'}]],
        subplot_titles=("Booking Rate", "Show Rate", "Utilization Rate")
    )
    
    # Calculate rates with error handling
    avg_booking_rate = df['Booking Rate'].mean() if 'Booking Rate' in df.columns else 0
    avg_show_rate = df['Show Rate'].mean() if 'Show Rate' in df.columns else 0
    avg_utilization = df['Utilization Rate'].mean() if 'Utilization Rate' in df.columns else 0
    
    # Add traces for each gauge
    rates_fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=avg_booking_rate * 100,  # Convert to percentage
            number={'suffix': "%", 'font': {'size': 26}},
            delta={'reference': 50, 'increasing': {'color': "#009933"}},
            gauge={
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "#4dabf7"},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 25], 'color': '#ffcccc'},
                    {'range': [25, 50], 'color': '#ffebcc'},
                    {'range': [50, 75], 'color': '#e6ffcc'},
                    {'range': [75, 100], 'color': '#ccffcc'}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 50
                }
            }
        ),
        row=1, col=1
    )
    
    rates_fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=avg_show_rate * 100,  # Convert to percentage
            number={'suffix': "%", 'font': {'size': 26}},
            delta={'reference': 70, 'increasing': {'color': "#009933"}},
            gauge={
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "#7950f2"},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 25], 'color': '#ffcccc'},
                    {'range': [25, 50], 'color': '#ffebcc'},
                    {'range': [50, 75], 'color': '#e6ffcc'},
                    {'range': [75, 100], 'color': '#ccffcc'}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 70
                }
            }
        ),
        row=1, col=2
    )
    
    rates_fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=avg_utilization * 100,  # Convert to percentage
            number={'suffix': "%", 'font': {'size': 26}},
            delta={'reference': 40, 'increasing': {'color': "#009933"}},
            gauge={
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "#00b894"},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 25], 'color': '#ffcccc'},
                    {'range': [25, 50], 'color': '#ffebcc'},
                    {'range': [50, 75], 'color': '#e6ffcc'},
                    {'range': [75, 100], 'color': '#ccffcc'}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 40
                }
            }
        ),
        row=1, col=3
    )
    
    # Update layout
    rates_fig.update_layout(
        height=250,
        margin=dict(l=30, r=30, t=50, b=30),
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font={'color': '#333333', 'size': 12}
    )
    
    st.plotly_chart(rates_fig, use_container_width=True)
    
    # Additional metrics and comparisons
    metrics_col1, metrics_col2 = st.columns(2)
    
    with metrics_col1:
        # Calculate min, max, and variability for rates
        if 'Utilization Rate' in df.columns:
            client_util_rates = df.groupby('Client')['Utilization Rate'].mean().sort_values(ascending=False)
            max_util_client = client_util_rates.index[0] if not client_util_rates.empty else "N/A"
            max_util_rate = client_util_rates.iloc[0] * 100 if not client_util_rates.empty else 0
            
            # Convert to DataFrame for better display
            client_table = pd.DataFrame({
                'Client': client_util_rates.index,
                'Utilization Rate (%)': client_util_rates.values * 100,
            }).reset_index(drop=True)
            
            # Add a performance category column
            def get_performance_category(rate):
                rate_pct = rate
                if rate_pct >= 75:
                    return "Excellent"
                elif rate_pct >= 50:
                    return "Good"
                elif rate_pct >= 25:
                    return "Average"
                else:
                    return "Needs Improvement"
            
            client_table['Performance'] = client_table['Utilization Rate (%)'].apply(get_performance_category)
            
            # Display with header and styled dataframe
            st.markdown("<h4 style='margin-top: 0;'>⭐ Utilization Leaders & Opportunities</h4>", unsafe_allow_html=True)
            
            # Style the dataframe
            def highlight_performance(val):
                if val == "Excellent":
                    return 'background-color: #28a745; color: white'
                elif val == "Good":
                    return 'background-color: #17a2b8; color: white'
                elif val == "Average":
                    return 'background-color: #ffc107; color: white'
                else:
                    return 'background-color: #dc3545; color: white'
            
            # Format the utilization rate column
            client_table['Utilization Rate (%)'] = client_table['Utilization Rate (%)'].map('{:.1f}%'.format)
            
            # Apply styling
            styled_table = client_table.style.applymap(
                highlight_performance, 
                subset=['Performance']
            ).set_properties(**{
                'text-align': 'center',
                'border': '1px solid #f0f0f0',
                'padding': '0.5rem'
            }, subset=['Performance'])
            
            # Display the table
            st.dataframe(styled_table, use_container_width=True, height=300)
    
    with metrics_col2:
        # Enhanced Improvement Potential section
        if all(col in df.columns for col in ['Headcount', 'Utilization Rate']):
            current_appointments = df['Total Completed Appts'].sum() if 'Total Completed Appts' in df.columns else 0
            total_potential = df['Headcount'].sum()
            avg_utilization = df['Utilization Rate'].mean() if 'Utilization Rate' in df.columns else 0
            
            # Get maximum values for comparison
            max_client_util = client_util_rates.iloc[0] if not client_util_rates.empty else 0
            
            # Get service type with highest utilization if service columns exist
            service_cols = ['Dental', 'Audiology', 'Vision', 'MSK', 'Skin Screening', 'Biometrics and Labs']
            service_cols = [col for col in service_cols if col in df.columns]
            
            max_service_util = 0
            max_service_name = "N/A"
            
            if service_cols:
                service_util = {}
                for service in service_cols:
                    service_data = df[df[service] > 0]
                    if not service_data.empty and 'Utilization Rate' in service_data.columns:
                        service_util[service] = service_data['Utilization Rate'].mean()
                
                if service_util:
                    max_service_name = max(service_util, key=service_util.get)
                    max_service_util = service_util[max_service_name]
            
            # Calculate potential increases
            potential_increase_10pct = total_potential * (avg_utilization + 0.1) - current_appointments
            potential_increase_to_top_client = total_potential * max_client_util - current_appointments
            potential_increase_to_top_service = total_potential * max_service_util - current_appointments
            
            # Create dataframes for better display
            improvement_data = pd.DataFrame({
                'Metric': [
                    'Current Appointments',
                    'With 10% Utilization Increase',
                    f'If All Matched Top Client ({max_util_client})',
                    f'If All Matched Best Service ({max_service_name})'
                ],
                'Value': [
                    f"{current_appointments:,.0f}",
                    f"+{potential_increase_10pct:,.0f} appointments",
                    f"+{potential_increase_to_top_client:,.0f} appointments",
                    f"+{potential_increase_to_top_service:,.0f} appointments"
                ]
            })
            
            outcomes_data = pd.DataFrame({
                'Metric': [
                    'Maximum Potential (All Clients)',
                    'Current Utilization',
                    'Unrealized Opportunity'
                ],
                'Value': [
                    f"{total_potential:,.0f} appointments",
                    f"{avg_utilization*100:.1f}%",
                    f"{total_potential - current_appointments:,.0f} appointments"
                ]
            })
            
            # Display with headers and styled dataframes
            st.markdown("<h4 style='margin-top: 0;'>🚀 Improvement Potential</h4>", unsafe_allow_html=True)
            st.dataframe(improvement_data, use_container_width=True, hide_index=True)
            
            st.markdown("<h5 style='margin-top: 15px; margin-bottom: 5px;'>Potential Outcomes</h5>", unsafe_allow_html=True)
            st.dataframe(outcomes_data, use_container_width=True, hide_index=True)
    
    # Service distribution with enhanced visualization
    service_cols = ['Dental', 'Audiology', 'Vision', 'MSK', 'Skin Screening', 'Biometrics and Labs']
    service_cols = [col for col in service_cols if col in df.columns]
    
    if service_cols:
        st.markdown("### 📋 Service Analysis")
        
        # Add explanation with enhanced styling
        st.markdown("""
        <div style="background-color: #f3f0ff; padding: 15px; border-left: 4px solid #7950f2; border-radius: 5px; margin-bottom: 20px;">
            <h4 style="margin-top: 0; margin-bottom: 10px; color: #7950f2;">Service Mix Insights</h4>
            <p style="margin-bottom: 8px;">Analyzing service distribution helps identify which services are most popular and where there may be growth opportunities:</p>
            <ul style="margin-bottom: 0;">
                <li>Identify most and least utilized services to optimize resources</li>
                <li>Spot services with growth potential based on client demographics</li>
                <li>Analyze service preferences by client type for targeted marketing</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        service_totals = df[service_cols].sum().reset_index()
        service_totals.columns = ['Service', 'Count']
        service_totals = service_totals[service_totals['Count'] > 0]
        
        if not service_totals.empty:
            # Create tabs for different visualizations
            service_tab1, service_tab2, service_tab3 = st.tabs(["Distribution", "By Client", "Trends"])
            
            with service_tab1:
                # Calculate additional metrics
                total_appointments = service_totals['Count'].sum()
                service_totals['Percentage'] = service_totals['Count'] / total_appointments * 100
                
                # Sort by count descending
                service_totals = service_totals.sort_values('Count', ascending=False)
                
                # Create two columns for different views
                col1, col2 = st.columns(2)
                
                with col1:
                    # Pie chart
                    fig_pie = px.pie(
                        service_totals,
                        values='Count',
                        names='Service',
                        title='Service Distribution',
                        color_discrete_sequence=px.colors.qualitative.Bold,
                        hole=0.4
                    )
                    
                    fig_pie.update_traces(
                        textposition='inside', 
                        textinfo='percent+label',
                        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}'
                    )
                    
                    fig_pie.update_layout(
                        margin=dict(t=50, b=20, l=20, r=20),
                        height=380,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.2,
                            xanchor="center",
                            x=0.5
                        )
                    )
                    
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    # Bar chart showing actual counts for comparison
                    fig_bar = px.bar(
                        service_totals,
                        x='Service',
                        y='Count',
                        title='Appointment Count by Service',
                        color='Service',
                        text='Count',
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
                    
                    fig_bar.update_traces(
                        texttemplate='%{text:,}', 
                        textposition='outside',
                        hovertemplate='<b>%{x}</b><br>Count: %{y:,}<br>Percentage: %{customdata[0]:.1f}%',
                        customdata=service_totals[['Percentage']]
                    )
                    
                    fig_bar.update_layout(
                        xaxis_title="",
                        yaxis_title="Number of Appointments",
                        xaxis={'categoryorder': 'total descending'},
                        showlegend=False,
                        margin=dict(t=50, b=20, l=20, r=20),
                        height=380
                    )
                    
                    st.plotly_chart(fig_bar, use_container_width=True)
                
                # Add service metrics with proper display
                st.markdown("#### Service Metrics")
                
                # Format the service metrics dataframe
                if 'service_totals' in locals() and not service_totals.empty:
                    # Rename and format columns for display
                    service_metrics_df = service_totals.copy()
                    service_metrics_df.columns = ['Service', 'Count', 'Percentage']
                    
                    # Add rank column
                    service_metrics_df['Rank'] = range(1, len(service_metrics_df) + 1)
                    service_metrics_df['Rank'] = service_metrics_df['Rank'].apply(lambda x: f"#{x}")
                    
                    # Format the percentage column
                    service_metrics_df['Percentage'] = service_metrics_df['Percentage'].apply(lambda x: f"{x:.1f}%")
                    
                    # Format the count column
                    service_metrics_df['Count'] = service_metrics_df['Count'].apply(lambda x: f"{x:,.0f}")
                    
                    # Display the formatted dataframe
                    st.dataframe(service_metrics_df, use_container_width=True, hide_index=True)
            
            with service_tab2:
                # Top clients by service utilization
                if 'Client' in df.columns:
                    st.subheader("Service Utilization by Client")
                    
                    # Get top 5 clients by total appointments
                    top_clients = df.groupby('Client')['Total Completed Appts'].sum().nlargest(5).index.tolist()
                    
                    # Filter for top clients and prepare data
                    top_client_data = df[df['Client'].isin(top_clients)]
                    
                    # Aggregate service data by client
                    client_service_data = []
                    
                    for client in top_clients:
                        client_df = top_client_data[top_client_data['Client'] == client]
                        for service in service_cols:
                            if service in client_df.columns:
                                service_count = client_df[service].sum()
                                if service_count > 0:
                                    client_service_data.append({
                                        'Client': client,
                                        'Service': service,
                                        'Count': service_count
                                    })
                    
                    # Convert to DataFrame
                    if client_service_data:
                        client_service_df = pd.DataFrame(client_service_data)
                        
                        # Create grouped bar chart
                        fig = px.bar(
                            client_service_df,
                            x='Client',
                            y='Count',
                            color='Service',
                            title='Service Mix for Top 5 Clients',
                            barmode='group',
                            color_discrete_sequence=px.colors.qualitative.Bold
                        )
                        
                        fig.update_layout(
                            xaxis_title="",
                            yaxis_title="Number of Appointments",
                            legend_title="Service",
                            height=450,
                            margin=dict(t=50, b=50, l=20, r=20)
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
            
            with service_tab3:
                # Service trends over time
                if 'Date of Service' in df.columns:
                    st.subheader("Service Trends Over Time")
                    
                    # Choose time grouping
                    time_groups = {
                        'Monthly': 'ME',
                        'Quarterly': 'Q',
                        'Yearly': 'Y'
                    }
                    
                    freq = time_groups.get(time_grouping, 'ME')
                    
                    # Prepare data
                    time_series_data = []
                    
                    for service in service_cols:
                        if service in df.columns:
                            # Group by time period
                            service_time = df.groupby(pd.Grouper(key='Date of Service', freq=freq))[service].sum().reset_index()
                            service_time['Service'] = service
                            service_time = service_time.rename(columns={service: 'Count'})
                            time_series_data.append(service_time)
                    
                    if time_series_data:
                        # Combine all services
                        all_services_time = pd.concat(time_series_data)
                        
                        # Format date for display
                        if freq == 'ME':
                            all_services_time['Period'] = all_services_time['Date of Service'].dt.strftime('%b %Y')
                        elif freq == 'Q':
                            all_services_time['Period'] = all_services_time['Date of Service'].apply(
                                lambda x: f"Q{pd.Timestamp(x).quarter} {pd.Timestamp(x).year}"
                            )
                        else:
                            all_services_time['Period'] = all_services_time['Date of Service'].dt.strftime('%Y')
                        
                        # Create area chart for trends
                        fig = px.area(
                            all_services_time,
                            x='Date of Service',
                            y='Count',
                            color='Service',
                            title=f'Service Utilization Trends ({time_grouping})',
                            color_discrete_sequence=px.colors.qualitative.Bold
                        )
                        
                        fig.update_layout(
                            xaxis_title="Time Period",
                            yaxis_title="Number of Appointments",
                            legend_title="Service",
                            height=450,
                            margin=dict(t=50, b=50, l=20, r=20),
                            hovermode="x unified"
                        )
                        
                        fig.update_traces(
                            hovertemplate='<b>%{x}</b><br>%{y:,} appointments<extra>%{fullData.name}</extra>'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Add service growth analysis
                        st.markdown("#### 📈 Service Growth Analysis")
                        
                        # Calculate growth rates
                        growth_data = []
                        
                        for service in service_cols:
                            service_df = all_services_time[all_services_time['Service'] == service]
                            if len(service_df) > 1:
                                first_period = service_df.iloc[0]['Count']
                                last_period = service_df.iloc[-1]['Count'] 
                                
                                if first_period > 0:
                                    growth_pct = (last_period - first_period) / first_period * 100
                                    growth_data.append({
                                        'Service': service,
                                        'First Period': first_period,
                                        'Last Period': last_period,
                                        'Change': last_period - first_period,
                                        'Growth %': growth_pct
                                    })
                        
                        if growth_data:
                            growth_df = pd.DataFrame(growth_data)
                            
                            # Sort by growth percentage
                            growth_df = growth_df.sort_values('Growth %', ascending=False)
                            
                            # Create horizontal bar chart for growth
                            fig_growth = px.bar(
                                growth_df,
                                y='Service',
                                x='Growth %',
                                color='Growth %',
                                orientation='h',
                                title='Service Growth Rate',
                                color_continuous_scale='RdYlGn',
                                text='Growth %'
                            )
                            
                            fig_growth.update_traces(
                                texttemplate='%{x:.1f}%', 
                                textposition='outside',
                                hovertemplate='<b>%{y}</b><br>Growth: %{x:.1f}%<br>From: %{customdata[0]:,} to %{customdata[1]:,}<extra></extra>',
                                customdata=growth_df[['First Period', 'Last Period']]
                            )
                            
                            fig_growth.update_layout(
                                xaxis_title="Growth Percentage",
                                yaxis_title="",
                                height=350,
                                margin=dict(t=50, b=20, l=20, r=20)
                            )
                            
                            st.plotly_chart(fig_growth, use_container_width=True)
            
            # Add insights about service distribution
            top_service = service_totals.iloc[0]
            bottom_service = service_totals.iloc[-1]
            
            st.markdown(f"""
            <div style="background-color: #fff3bf; padding: 15px; border-radius: 5px; margin-top: 20px; border-left: 4px solid #ffd43b;">
                <h4 style="margin-top: 0; color: #856404;">📊 Key Service Insights</h4>
                <ul style="margin-bottom: 0;">
                    <li><strong>{top_service['Service']}</strong> is the most utilized service, accounting for 
                    {top_service['Percentage']:.1f}% of all appointments.</li>
                    <li>The least utilized service is <strong>{bottom_service['Service']}</strong> at only 
                    {bottom_service['Percentage']:.1f}% of appointments, representing a potential growth opportunity.</li>
                    <li>The top 2 services account for {service_totals.iloc[:2]['Percentage'].sum():.1f}% of all appointments.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
    
    # Client performance with enhanced visualization
    if 'Client' in df.columns and 'Utilization Rate' in df.columns:
        st.markdown("### 🏢 Client Performance Analysis")
        
        # Add explanation for client performance
        st.markdown("""
        <div style="background-color: #e6fcf5; padding: 15px; border-left: 4px solid #12b886; border-radius: 5px; margin-bottom: 20px;">
            <h4 style="margin-top: 0; margin-bottom: 10px; color: #12b886;">Client Performance Insights</h4>
            <p style="margin-bottom: 8px;">This analysis ranks clients by their utilization metrics and provides actionable insights:</p>
            <ul style="margin-bottom: 0;">
                <li>Identify high and low-performing clients to understand success factors</li>
                <li>Discover best practices from top performers to implement with others</li>
                <li>Target improvement opportunities for specific clients or segments</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Calculate client metrics
        client_performance = df.groupby('Client').agg({
            'Headcount': 'sum',
            'Total Booking Appts': 'sum',
            'Total Completed Appts': 'sum',
            'Booking Rate': 'mean',
            'Show Rate': 'mean',
            'Utilization Rate': 'mean',
            'Site': 'nunique'
        }).reset_index()
        
        # Add a site count column
        client_performance.rename(columns={'Site': 'Site Count'}, inplace=True)
        
        # Calculate additional metrics
        client_performance['Booking Rate %'] = client_performance['Booking Rate'] * 100
        client_performance['Show Rate %'] = client_performance['Show Rate'] * 100
        client_performance['Utilization Rate %'] = client_performance['Utilization Rate'] * 100
        
        # Create tabs for different views
        client_tab1, client_tab2 = st.tabs(["Rankings", "Details"])
        
        with client_tab1:
            # Choose visualization type based on interactive option
            if chart_type == "Bar Chart" or not interactive:
                # Create enhanced bar chart
                fig = px.bar(
                    client_performance.sort_values('Utilization Rate', ascending=False).head(top_n_clients),
                    x='Client',
                    y='Utilization Rate %',
                    title=f'Top {top_n_clients} Clients by Utilization Rate',
                    color='Utilization Rate %',
                    color_continuous_scale='Viridis',
                    text='Utilization Rate %',
                    hover_data=['Headcount', 'Total Completed Appts', 'Site Count']
                )
                
                fig.update_traces(
                    texttemplate='%{text:.1f}%', 
                    textposition='outside'
                )
                
                fig.update_layout(
                    xaxis_title="Client",
                    yaxis_title="Utilization Rate (%)",
                    yaxis=dict(range=[0, max(client_performance['Utilization Rate %']) * 1.15]),
                    margin=dict(t=50, b=100, l=20, r=20),
                    height=450,
                    coloraxis_colorbar=dict(title="Utilization Rate (%)")
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
            elif chart_type == "Treemap":
                # Create treemap visualization
                fig = px.treemap(
                    client_performance.sort_values('Utilization Rate', ascending=False).head(top_n_clients),
                    path=['Client'],
                    values='Total Completed Appts',
                    color='Utilization Rate %',
                    color_continuous_scale='Viridis',
                    title=f'Top {top_n_clients} Clients by Utilization Rate',
                    hover_data=['Headcount', 'Booking Rate %', 'Show Rate %']
                )
                
                fig.update_traces(
                    texttemplate='<b>%{label}</b><br>%{customdata[2]:.1f}%',
                    hovertemplate='<b>%{label}</b><br>Utilization: %{color:.1f}%<br>Appointments: %{value:,}<br>Headcount: %{customdata[0]:,}<br>Booking Rate: %{customdata[1]:.1f}%<br>Show Rate: %{customdata[2]:.1f}%'
                )
                
                fig.update_layout(
                    margin=dict(t=50, b=20, l=20, r=20),
                    height=450,
                    coloraxis_colorbar=dict(title="Utilization Rate (%)")
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
            elif chart_type == "Scatter Plot":
                # Create scatter plot visualization showing relationship between metrics
                fig = px.scatter(
                    client_performance.head(top_n_clients),
                    x='Booking Rate %',
                    y='Show Rate %',
                    size='Headcount',
                    color='Utilization Rate %',
                    hover_name='Client',
                    color_continuous_scale='Viridis',
                    title='Client Performance Metrics Relationship',
                    size_max=50,
                    hover_data=['Total Completed Appts', 'Site Count']
                )
                
                # Add diagonal reference line (booking rate * show rate = utilization rate)
                # This is an approximation for visual reference
                x_ref = [0, 100]
                fig.add_trace(
                    go.Scatter(
                        x=x_ref, 
                        y=x_ref,
                        mode='lines',
                        line=dict(color='rgba(255,0,0,0.3)', width=2, dash='dash'),
                        name='Booking Rate = Show Rate',
                        hoverinfo='skip'
                    )
                )
                
                fig.update_layout(
                    xaxis_title="Booking Rate (%)",
                    yaxis_title="Show Rate (%)",
                    xaxis=dict(range=[0, 100]),
                    yaxis=dict(range=[0, 100]),
                    margin=dict(t=50, b=50, l=20, r=20),
                    height=500,
                    coloraxis_colorbar=dict(title="Utilization Rate (%)")
                )
                
                # Add annotations for quadrants
                fig.add_annotation(
                    x=25, y=75,
                    text="High Show / Low Booking",
                    showarrow=False,
                    font=dict(size=10, color="gray")
                )
                
                fig.add_annotation(
                    x=75, y=75,
                    text="High Performance",
                    showarrow=False,
                    font=dict(size=10, color="gray")
                )
                
                fig.add_annotation(
                    x=25, y=25,
                    text="Improvement Needed",
                    showarrow=False,
                    font=dict(size=10, color="gray")
                )
                
                fig.add_annotation(
                    x=75, y=25,
                    text="High Booking / Low Show",
                    showarrow=False,
                    font=dict(size=10, color="gray")
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Add explanation for the quadrant chart
                st.markdown("""
                <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; font-size: 0.9em;">
                    <p style="margin: 0;"><strong>Chart Interpretation:</strong> 
                    Each bubble represents a client, with size indicating headcount. The position shows booking rate (x-axis) 
                    and show rate (y-axis), while color indicates overall utilization rate. Clients in the top-right quadrant 
                    are high performers in both metrics.</p>
                </div>
                """, unsafe_allow_html=True)
        
        with client_tab2:
            st.subheader("Client Details")
            
            # Create sortable client data table
            client_table = client_performance.copy()
            
            # Round percentage columns for display
            for col in ['Booking Rate %', 'Show Rate %', 'Utilization Rate %']:
                client_table[col] = client_table[col].round(1)
            
            # Format the table columns
            display_cols = ['Client', 'Headcount', 'Total Completed Appts', 
                            'Booking Rate %', 'Show Rate %', 'Utilization Rate %', 'Site Count']
            
            # Allow sorting by column
            sort_column = st.selectbox(
                "Sort by:",
                options=display_cols,
                index=display_cols.index('Utilization Rate %')
            )
            
            # Sort and display
            st.dataframe(
                client_table[display_cols].sort_values(sort_column, ascending=False),
                use_container_width=True,
                height=400
            )
            
            # Add download option
            csv = client_table[display_cols].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Client Data",
                data=csv,
                file_name="client_performance.csv",
                mime="text/csv"
            )
        
        # Add insights about client performance
        top_client = client_performance.sort_values('Utilization Rate', ascending=False).iloc[0]
        bottom_client = client_performance.sort_values('Utilization Rate').iloc[0]
        
        st.markdown(f"""
        <div style="background-color: #fff3bf; padding: 15px; border-radius: 5px; margin-top: 20px; border-left: 4px solid #ffd43b;">
            <h4 style="margin-top: 0; color: #856404;">🔍 Client Performance Summary</h4>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid rgba(0,0,0,0.1);">
                    <td style="padding: 8px 5px; width: 30%;"><strong>Top Performer:</strong></td>
                    <td style="padding: 8px 5px;"><strong>{top_client['Client']}</strong> with {top_client['Utilization Rate %']:.1f}% utilization rate</td>
                </tr>
                <tr style="border-bottom: 1px solid rgba(0,0,0,0.1);">
                    <td style="padding: 8px 5px;"><strong>Improvement Opportunity:</strong></td>
                    <td style="padding: 8px 5px;"><strong>{bottom_client['Client']}</strong> with {bottom_client['Utilization Rate %']:.1f}% utilization rate</td>
                </tr>
                <tr style="border-bottom: 1px solid rgba(0,0,0,0.1);">
                    <td style="padding: 8px 5px;"><strong>Performance Gap:</strong></td>
                    <td style="padding: 8px 5px;">
                        {(top_client['Utilization Rate %'] - bottom_client['Utilization Rate %']):.1f} percentage points 
                        ({(top_client['Utilization Rate']/bottom_client['Utilization Rate']):.1f}x difference)
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 5px;"><strong>Average Utilization:</strong></td>
                    <td style="padding: 8px 5px;">
                        {client_performance['Utilization Rate %'].mean():.1f}% across {len(client_performance)} clients
                    </td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
    
    # Time series analysis
    if 'Date of Service' in df.columns and 'Utilization Rate' in df.columns:
        st.markdown("### 📅 Temporal Analysis")
        
        # Add explanation for time series
        st.markdown("""
        <div style="background-color: #fff4e6; padding: 15px; border-left: 4px solid #fd7e14; border-radius: 5px; margin-bottom: 20px;">
            <h4 style="margin-top: 0; margin-bottom: 10px; color: #fd7e14;">Trend Analysis Insights</h4>
            <p style="margin-bottom: 8px;">Analyzing trends over time helps identify patterns and opportunities:</p>
            <ul style="margin-bottom: 0;">
                <li>Track changes in utilization metrics to identify growth or decline</li>
                <li>Discover seasonal patterns and plan resources accordingly</li>
                <li>Measure the impact of marketing campaigns or operational changes</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Determine time grouping frequency
        time_groups = {
            "Monthly": "ME",
            "Quarterly": "Q",
            "Yearly": "Y"
        }
        
        freq = time_groups.get(time_grouping, "ME")
        
        # Prepare time series data
        time_series = df.groupby(pd.Grouper(key='Date of Service', freq=freq)).agg({
            'Headcount': 'sum',
            'Total Booking Appts': 'sum',
            'Total Completed Appts': 'sum',
            'Booking Rate': 'mean',
            'Show Rate': 'mean',
            'Utilization Rate': 'mean'
        }).reset_index()
        
        # Format date for display
        time_series['Month'] = time_series['Date of Service'].dt.strftime('%b %Y')
        
        # Convert rates to percentages
        time_series['Booking Rate %'] = time_series['Booking Rate'] * 100
        time_series['Show Rate %'] = time_series['Show Rate'] * 100
        time_series['Utilization Rate %'] = time_series['Utilization Rate'] * 100
        
        # Create tabs for different time series views
        time_tab1, time_tab2 = st.tabs(["Utilization Trends", "Volume Analysis"])
        
        with time_tab1:
            # Create a more advanced line chart with annotations
            fig = go.Figure()
            
            # Add line for utilization rate
            fig.add_trace(go.Scatter(
                x=time_series['Date of Service'],
                y=time_series['Utilization Rate %'],
                mode='lines+markers',
                name='Utilization Rate',
                line=dict(color='#00b894', width=3),
                marker=dict(size=8)
            ))
            
            # Add a moving average if there are enough data points
            if len(time_series) >= 3:
                time_series['MA_3'] = time_series['Utilization Rate %'].rolling(window=3).mean()
                
                if show_trends:
                    fig.add_trace(go.Scatter(
                        x=time_series['Date of Service'],
                        y=time_series['MA_3'],
                        mode='lines',
                        name='3-Period Moving Avg',
                        line=dict(color='rgba(0, 184, 148, 0.5)', width=2, dash='dot')
                    ))
            
            # Add annotations for highest and lowest points
            if not time_series.empty:
                max_point = time_series.loc[time_series['Utilization Rate %'].idxmax()]
                min_point = time_series.loc[time_series['Utilization Rate %'].idxmin()]
                
                # Add annotation for max point
                fig.add_annotation(
                    x=max_point['Date of Service'],
                    y=max_point['Utilization Rate %'],
                    text=f"Peak: {max_point['Utilization Rate %']:.1f}%",
                    showarrow=True,
                    arrowhead=7,
                    ax=0,
                    ay=-40
                )
                
                # Add annotation for min point
                fig.add_annotation(
                    x=min_point['Date of Service'],
                    y=min_point['Utilization Rate %'],
                    text=f"Low: {min_point['Utilization Rate %']:.1f}%",
                    showarrow=True,
                    arrowhead=7,
                    ax=0,
                    ay=40
                )
            
            fig.update_layout(
                title=f'Utilization Rate Trend Over Time ({time_grouping})',
                xaxis_title="Time Period",
                yaxis_title="Utilization Rate (%)",
                margin=dict(t=50, b=50, l=20, r=20),
                height=450,
                hovermode="x unified",
                yaxis=dict(range=[0, max(time_series['Utilization Rate %']) * 1.2])
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add trend analysis summary
            if len(time_series) > 1:
                first_month = time_series.iloc[0]
                last_month = time_series.iloc[-1]
                change = last_month['Utilization Rate %'] - first_month['Utilization Rate %']
                
                # Calculate compound growth rate
                periods = len(time_series) - 1
                if periods > 0 and first_month['Utilization Rate'] > 0:
                    cagr = ((last_month['Utilization Rate'] / first_month['Utilization Rate']) ** (1/periods) - 1) * 100
                else:
                    cagr = 0
                
                trend_color = "#12b886" if change >= 0 else "#fa5252"
                trend_icon = "📈" if change >= 0 else "📉"
                
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 15px;">
                    <h4 style="margin-top: 0;">{trend_icon} Trend Analysis</h4>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 5px; width: 40%;"><strong>Change in Utilization Rate:</strong></td>
                            <td style="padding: 8px 5px;">
                                <span style="color: {trend_color}; font-weight: bold;">
                                    {change:.1f} percentage points ({change/first_month['Utilization Rate %']*100:.1f}%)
                                </span>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 5px;"><strong>Time Period:</strong></td>
                            <td style="padding: 8px 5px;">
                                {first_month['Month']} to {last_month['Month']} ({periods+1} {time_grouping.lower()} periods)
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 5px;"><strong>Average Period-to-Period Change:</strong></td>
                            <td style="padding: 8px 5px;">{cagr:.2f}% per period</td>
                        </tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)
        
        with time_tab2:
            # Create a chart showing volume metrics
            fig = go.Figure()
            
            # Add bar for headcount (capacity)
            fig.add_trace(go.Bar(
                x=time_series['Date of Service'],
                y=time_series['Headcount'],
                name='Eligible Headcount',
                marker_color='rgba(200, 200, 200, 0.6)'
            ))
            
            # Add bar for bookings
            fig.add_trace(go.Bar(
                x=time_series['Date of Service'],
                y=time_series['Total Booking Appts'],
                name='Booked Appointments',
                marker_color='rgba(77, 171, 247, 0.8)'
            ))
            
            # Add bar for completed
            fig.add_trace(go.Bar(
                x=time_series['Date of Service'],
                y=time_series['Total Completed Appts'],
                name='Completed Appointments',
                marker_color='rgba(0, 184, 148, 0.8)'
            ))
            
            fig.update_layout(
                title=f'Appointment Volumes Over Time ({time_grouping})',
                xaxis_title="Time Period",
                yaxis_title="Count",
                barmode='group',
                margin=dict(t=50, b=50, l=20, r=20),
                height=450,
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Calculate and display volume metrics
            if len(time_series) > 1:
                first_period = time_series.iloc[0]
                last_period = time_series.iloc[-1]
                
                # Calculate changes
                headcount_change = last_period['Headcount'] - first_period['Headcount']
                headcount_pct = (headcount_change / first_period['Headcount'] * 100) if first_period['Headcount'] > 0 else 0
                
                bookings_change = last_period['Total Booking Appts'] - first_period['Total Booking Appts']
                bookings_pct = (bookings_change / first_period['Total Booking Appts'] * 100) if first_period['Total Booking Appts'] > 0 else 0
                
                completed_change = last_period['Total Completed Appts'] - first_period['Total Completed Appts']
                completed_pct = (completed_change / first_period['Total Completed Appts'] * 100) if first_period['Total Completed Appts'] > 0 else 0
                
                # Format colors
                hc_color = "#12b886" if headcount_change >= 0 else "#fa5252"
                book_color = "#12b886" if bookings_change >= 0 else "#fa5252"
                comp_color = "#12b886" if completed_change >= 0 else "#fa5252"
                
                # Create metrics table
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 15px;">
                    <h4 style="margin-top: 0;">Volume Change Analysis</h4>
                    <p style="margin-bottom: 10px;">Changes from {first_period['Month']} to {last_period['Month']}:</p>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="border-bottom: 1px solid rgba(0,0,0,0.1);">
                            <td style="padding: 8px 5px; width: 40%;"><strong>Eligible Headcount:</strong></td>
                            <td style="padding: 8px 5px;">
                                <span style="color: {hc_color}; font-weight: bold;">
                                    {headcount_change:+,.0f} ({headcount_pct:+.1f}%)
                                </span>
                                from {first_period['Headcount']:,.0f} to {last_period['Headcount']:,.0f}
                            </td>
                        </tr>
                        <tr style="border-bottom: 1px solid rgba(0,0,0,0.1);">
                            <td style="padding: 8px 5px;"><strong>Booked Appointments:</strong></td>
                            <td style="padding: 8px 5px;">
                                <span style="color: {book_color}; font-weight: bold;">
                                    {bookings_change:+,.0f} ({bookings_pct:+.1f}%)
                                </span>
                                from {first_period['Total Booking Appts']:,.0f} to {last_period['Total Booking Appts']:,.0f}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 5px;"><strong>Completed Appointments:</strong></td>
                            <td style="padding: 8px 5px;">
                                <span style="color: {comp_color}; font-weight: bold;">
                                    {completed_change:+,.0f} ({completed_pct:+.1f}%)
                                </span>
                                from {first_period['Total Completed Appts']:,.0f} to {last_period['Total Completed Appts']:,.0f}
                            </td>
                        </tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)
        
        # Add seasonal analysis if enough data
        if len(time_series) >= 4:
            st.subheader("Seasonal Patterns")
            
            # Determine if we have enough data for meaningful seasonality
            has_multiple_years = (time_series['Date of Service'].dt.year.max() - 
                                 time_series['Date of Service'].dt.year.min()) >= 1
            
            if has_multiple_years:
                # Extract month for monthly analysis
                time_series['Month_Num'] = time_series['Date of Service'].dt.month
                
                # Group by month and calculate average metrics for each month
                monthly_pattern = time_series.groupby('Month_Num').agg({
                    'Booking Rate %': 'mean',
                    'Show Rate %': 'mean',
                    'Utilization Rate %': 'mean'
                }).reset_index()
                
                # Add month names
                monthly_pattern['Month_Name'] = monthly_pattern['Month_Num'].apply(
                    lambda x: calendar.month_name[x]
                )
                
                # Sort by month
                monthly_pattern = monthly_pattern.sort_values('Month_Num')
                
                # Create seasonal chart
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=monthly_pattern['Month_Name'],
                    y=monthly_pattern['Utilization Rate %'],
                    mode='lines+markers',
                    name='Utilization Rate',
                    line=dict(color='#00b894', width=3),
                    marker=dict(size=8)
                ))
                
                fig.update_layout(
                    title='Seasonal Utilization Rate Pattern',
                    xaxis_title="Month",
                    yaxis_title="Average Utilization Rate (%)",
                    margin=dict(t=50, b=50, l=20, r=20),
                    height=350
                )
                
                # Find peak and low months
                peak_month = monthly_pattern.loc[monthly_pattern['Utilization Rate %'].idxmax()]
                low_month = monthly_pattern.loc[monthly_pattern['Utilization Rate %'].idxmin()]
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Add seasonal insights
                st.markdown(f"""
                <div style="background-color: #fff3bf; padding: 15px; border-radius: 5px; margin-top: 15px; border-left: 4px solid #ffd43b;">
                    <h4 style="margin-top: 0; color: #856404;">🗓️ Seasonal Pattern Insights</h4>
                    <ul style="margin-bottom: 0;">
                        <li>Peak utilization occurs in <strong>{peak_month['Month_Name']}</strong> with an average of {peak_month['Utilization Rate %']:.1f}%</li>
                        <li>Lowest utilization occurs in <strong>{low_month['Month_Name']}</strong> with an average of {low_month['Utilization Rate %']:.1f}%</li>
                        <li>Seasonal difference of {(peak_month['Utilization Rate %'] - low_month['Utilization Rate %']):.1f} percentage points</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("More data needed for meaningful seasonal analysis. At least one full year of data is recommended.")
                
    # Return from the function
    return 