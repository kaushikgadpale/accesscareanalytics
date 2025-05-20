import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from config import AIRTABLE_BASES, AIRTABLE_CONFIG, THEME_CONFIG

# Import from modular structure
from modules.airtable import get_utilization_data, get_pnl_data, get_sow_data
from modules.utils import apply_filters
from modules.visualization import create_utilization_dashboard

# Functions that haven't been modularized yet
def create_pnl_dashboard(df):
    """
    Create visualizations for PnL data
    
    Args:
        df: DataFrame containing PnL data
        
    Returns:
        None (displays visualizations in Streamlit)
    """
    if df.empty:
        st.warning("No PnL data available to display")
        return
    
    st.subheader("Financial Performance Overview")
    
    # Add descriptive text
    st.markdown("""
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <h4 style="margin-top: 0;">💰 Financial Performance Dashboard</h4>
        <p>This dashboard provides insights into financial performance metrics across different clients, locations, and time periods.
        Key metrics include revenue, expenses, net profit, and profit margins.</p>
        <p><strong>Key Metrics:</strong></p>
        <ul>
            <li><strong>Revenue</strong>: Total income from all sources</li>
            <li><strong>Expenses</strong>: Total cost of goods sold (COGS)</li>
            <li><strong>Net Profit</strong>: Revenue minus expenses</li>
            <li><strong>Profit Margin</strong>: Net profit as a percentage of revenue</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_revenue = df['Revenue_Total'].sum() if 'Revenue_Total' in df.columns else 0
        st.metric("Total Revenue", f"${total_revenue:,.2f}")
    
    with col2:
        total_expenses = df['Expense_COGS_Total'].sum() if 'Expense_COGS_Total' in df.columns else 0
        st.metric("Total Expenses", f"${total_expenses:,.2f}")
    
    with col3:
        net_profit = df['Net_Profit'].sum() if 'Net_Profit' in df.columns else 0
        st.metric("Net Profit", f"${net_profit:,.2f}")
    
    with col4:
        if 'Net_Profit' in df.columns and 'Revenue_Total' in df.columns:
            overall_profit_margin = (df['Net_Profit'].sum() / df['Revenue_Total'].sum()) if df['Revenue_Total'].sum() > 0 else 0
            st.metric("Overall Profit Margin", f"{overall_profit_margin:.1%}")
        else:
            st.metric("Overall Profit Margin", "N/A")
    
    # Revenue Composition
    if all(col in df.columns for col in ['Revenue_WellnessFund', 'Revenue_DentalClaim', 'Revenue_MedicalClaim_InclCancelled', 'Revenue_MissedAppointments']):
        st.subheader("Revenue Composition")
        
        # Add explanation for revenue composition
        st.markdown("""
        <div style="background-color: #e8f4f8; padding: 10px; border-left: 4px solid #4dabf7; border-radius: 3px; margin-bottom: 15px;">
            This chart shows the breakdown of revenue by source. Understanding your revenue mix helps identify your most valuable 
            service offerings and potential areas for growth or optimization.
        </div>
        """, unsafe_allow_html=True)
        
        revenue_data = pd.DataFrame({
            'Source': ['Wellness Fund', 'Dental Claims', 'Medical Claims', 'Missed Appointments'],
            'Amount': [
                df['Revenue_WellnessFund'].sum(),
                df['Revenue_DentalClaim'].sum(),
                df['Revenue_MedicalClaim_InclCancelled'].sum(),
                df['Revenue_MissedAppointments'].sum()
            ]
        })
        
        revenue_data = revenue_data[revenue_data['Amount'] > 0]
        
        fig = px.pie(
            revenue_data,
            values='Amount',
            names='Source',
            title='Revenue Sources',
            color_discrete_sequence=px.colors.sequential.Viridis
        )
        
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(
            margin=dict(t=50, b=50, l=20, r=20),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add insights about revenue composition
        top_source = revenue_data.sort_values('Amount', ascending=False).iloc[0]
        st.markdown(f"""
        <div style="background-color: #fff3bf; padding: 10px; border-radius: 3px; margin-top: 10px;">
            <strong>📊 Insight:</strong> {top_source['Source']} is your primary revenue driver, accounting for 
            {(top_source['Amount'] / revenue_data['Amount'].sum()):.1%} of total revenue.
        </div>
        """, unsafe_allow_html=True)
    
    # Client Performance
    if 'Client' in df.columns and 'Net_Profit' in df.columns:
        st.subheader("Client Profitability")
        
        # Add explanation for client profitability
        st.markdown("""
        <div style="background-color: #e6fcf5; padding: 10px; border-left: 4px solid #12b886; border-radius: 3px; margin-bottom: 15px;">
            This chart ranks clients by net profit. Understanding which clients generate the most profit helps prioritize 
            client relationships and identify opportunities for expansion or improvement.
        </div>
        """, unsafe_allow_html=True)
        
        client_profit = df.groupby('Client').agg({
            'Revenue_Total': 'sum',
            'Expense_COGS_Total': 'sum',
            'Net_Profit': 'sum',
            'Service_Days': 'sum'
        }).reset_index()
        
        client_profit['Profit_Per_Day'] = client_profit['Net_Profit'] / client_profit['Service_Days']
        
        fig = px.bar(
            client_profit.sort_values('Net_Profit', ascending=False).head(10),
            x='Client',
            y='Net_Profit',
            title='Top 10 Clients by Net Profit',
            color='Profit_Per_Day',
            color_continuous_scale='RdYlGn',
            text_auto='$.2s'
        )
        
        fig.update_traces(texttemplate='${text:,.2f}', textposition='outside')
        fig.update_layout(
            xaxis_title="Client",
            yaxis_title="Net Profit ($)",
            coloraxis_colorbar=dict(title="Profit Per Day"),
            margin=dict(t=50, b=100, l=20, r=20),
            height=450
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add insights about client profitability
        top_client = client_profit.sort_values('Net_Profit', ascending=False).iloc[0]
        bottom_client = client_profit[client_profit['Net_Profit'] < 0].sort_values('Net_Profit').iloc[0] if len(client_profit[client_profit['Net_Profit'] < 0]) > 0 else None
        
        st.markdown("""
        <div style="background-color: #fff3bf; padding: 10px; border-radius: 3px; margin-top: 10px;">
            <strong>📊 Insights:</strong>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        - Most profitable client: **{top_client['Client']}** with ${top_client['Net_Profit']:,.2f} net profit per day
        """)
        
        if bottom_client is not None:
            st.markdown(f"""
            - Attention needed: **{bottom_client['Client']}** is showing a loss of ${abs(bottom_client['Net_Profit']):,.2f} per day
            """)
        
        st.markdown("</div>", unsafe_allow_html=True)

        # Add detailed analysis button
        if st.button("Get Detailed Analysis"):
            st.markdown("""
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-top: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <h3 style="color: #2c3e50; margin-top: 0; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px;">📊 Financial Analysis Report</h3>
            """, unsafe_allow_html=True)

            # 1. Overall Financial Health
            st.markdown("### 1. Overall Financial Health")
            total_revenue = df['Revenue_Total'].sum()
            total_expenses = df['Expense_COGS_Total'].sum()
            total_profit = df['Net_Profit'].sum()
            overall_margin = total_profit / total_revenue if total_revenue > 0 else 0

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div style="background-color: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <h4 style="color: #6b7280; margin: 0 0 10px 0; font-size: 0.9rem;">Total Revenue</h4>
                    <p style="color: #1f2937; margin: 0; font-size: 1.5rem; font-weight: 600;">${total_revenue:,.2f}</p>
        </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div style="background-color: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <h4 style="color: #6b7280; margin: 0 0 10px 0; font-size: 0.9rem;">Total Expenses</h4>
                    <p style="color: #1f2937; margin: 0; font-size: 1.5rem; font-weight: 600;">${total_expenses:,.2f}</p>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div style="background-color: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <h4 style="color: #6b7280; margin: 0 0 10px 0; font-size: 0.9rem;">Overall Profit Margin</h4>
                    <p style="color: #1f2937; margin: 0; font-size: 1.5rem; font-weight: 600;">{overall_margin:.1%}</p>
                </div>
                """, unsafe_allow_html=True)

            # 2. Client Portfolio Analysis
            st.markdown("### 2. Client Portfolio Analysis")
            client_metrics = df.groupby('Client').agg({
                'Revenue_Total': 'sum',
                'Expense_COGS_Total': 'sum',
                'Net_Profit': 'sum'
            }).reset_index()
            
            client_metrics['Revenue_Share'] = client_metrics['Revenue_Total'] / total_revenue
            
            # Sort by revenue share
            client_metrics = client_metrics.sort_values('Revenue_Share', ascending=False)
            
            # Display top 5 clients by revenue
            st.markdown("#### Top 5 Clients by Revenue")
            for _, client in client_metrics.head().iterrows():
                st.markdown(f"""
                <div style="background-color: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <h4 style="color: #1f2937; margin: 0 0 10px 0;">{client['Client']}</h4>
                    <div style="display: flex; justify-content: space-between; color: #6b7280; font-size: 0.9rem;">
                        <span>Revenue: ${client['Revenue_Total']:,.2f} ({client['Revenue_Share']:.1%} of total)</span>
                        <span>Profit: ${client['Net_Profit']:,.2f} ({client['Profit_Per_Day']:.2f} per day)</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # 3. Revenue Stream Analysis
            st.markdown("### 3. Revenue Stream Analysis")
            revenue_streams = {
                'Wellness Fund': df['Revenue_WellnessFund'].sum() if 'Revenue_WellnessFund' in df.columns else 0,
                'Dental Claims': df['Revenue_DentalClaim'].sum() if 'Revenue_DentalClaim' in df.columns else 0,
                'Medical Claims': df['Revenue_MedicalClaim_InclCancelled'].sum() if 'Revenue_MedicalClaim_InclCancelled' in df.columns else 0,
                'Missed Appointments': df['Revenue_MissedAppointments'].sum() if 'Revenue_MissedAppointments' in df.columns else 0
            }
            
            # Calculate percentages
            total_stream_revenue = sum(revenue_streams.values())
            revenue_streams = {k: (v, v/total_stream_revenue if total_stream_revenue > 0 else 0) 
                             for k, v in revenue_streams.items() if v > 0}
            
            st.markdown("#### Revenue Distribution by Stream")
            for stream, (amount, percentage) in revenue_streams.items():
                st.markdown(f"""
                <div style="background-color: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="color: #1f2937; margin: 0;">{stream}</h4>
                        <span style="color: #6b7280; font-size: 0.9rem;">{percentage:.1%} of total</span>
                    </div>
                    <p style="color: #1f2937; margin: 10px 0 0 0; font-size: 1.2rem; font-weight: 600;">${amount:,.2f}</p>
                </div>
                """, unsafe_allow_html=True)

            # 4. Trend Analysis
            st.markdown("### 4. Trend Analysis")
            if 'Service_Month' in df.columns:
                monthly_trends = df.groupby(pd.Grouper(key='Service_Month', freq='ME')).agg({
                    'Revenue_Total': 'sum',
                    'Expense_COGS_Total': 'sum',
                    'Net_Profit': 'sum'
                }).reset_index()
                
                # Calculate month-over-month changes
                monthly_trends['Revenue_Change'] = monthly_trends['Revenue_Total'].pct_change()
                monthly_trends['Profit_Change'] = monthly_trends['Net_Profit'].pct_change()
                
                # Get latest month's data
                latest_month = monthly_trends.iloc[-1]
                previous_month = monthly_trends.iloc[-2] if len(monthly_trends) > 1 else None
                
                st.markdown("#### Latest Month Performance")
                st.markdown(f"""
                <div style="background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
                        <div>
                            <h4 style="color: #6b7280; margin: 0 0 10px 0; font-size: 0.9rem;">Revenue</h4>
                            <p style="color: #1f2937; margin: 0; font-size: 1.2rem; font-weight: 600;">${latest_month['Revenue_Total']:,.2f}</p>
                            {f"<p style='color: #10b981; margin: 5px 0 0 0; font-size: 0.9rem;'>↑ {latest_month['Revenue_Change']:.1%} vs previous month</p>" if previous_month is not None else ""}
                        </div>
                        <div>
                            <h4 style="color: #6b7280; margin: 0 0 10px 0; font-size: 0.9rem;">Profit</h4>
                            <p style="color: #1f2937; margin: 0; font-size: 1.2rem; font-weight: 600;">${latest_month['Net_Profit']:,.2f}</p>
                            {f"<p style='color: #10b981; margin: 5px 0 0 0; font-size: 0.9rem;'>↑ {latest_month['Profit_Change']:.1%} vs previous month</p>" if previous_month is not None else ""}
                        </div>
                        <div>
                            <h4 style="color: #6b7280; margin: 0 0 10px 0; font-size: 0.9rem;">Profit Margin</h4>
                            <p style="color: #1f2937; margin: 0; font-size: 1.2rem; font-weight: 600;">{latest_month['Net_Profit'] / latest_month['Revenue_Total']:.1%}</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # 5. Recommendations
            st.markdown("### 5. Strategic Recommendations")
            
            # Analyze client concentration
            top_3_revenue_share = client_metrics.head(3)['Revenue_Share'].sum()
            if top_3_revenue_share > 0.5:
                st.markdown("""
                <div style="background-color: #fff7ed; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #f59e0b;">
                    <h4 style="color: #92400e; margin: 0 0 10px 0;">⚠️ Client Concentration Risk</h4>
                    <p style="color: #78350f; margin: 0;">Top 3 clients account for more than 50% of revenue. Consider diversifying client base to reduce dependency.</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Analyze profit margins
            low_margin_clients = client_metrics[client_metrics['Net_Profit'] < 0]
            if not low_margin_clients.empty:
                st.markdown("""
                <div style="background-color: #f0fdf4; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #10b981;">
                    <h4 style="color: #065f46; margin: 0 0 10px 0;">💡 Margin Improvement Opportunities</h4>
                    <p style="color: #064e3b; margin: 0;">Several clients show low profit margins. Consider reviewing pricing strategy or cost structure.</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Analyze revenue streams
            if revenue_streams:
                dominant_stream = max(revenue_streams.items(), key=lambda x: x[1][1])
                if dominant_stream[1][1] > 0.4:
                    st.markdown(f"""
                    <div style="background-color: #eff6ff; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #3b82f6;">
                        <h4 style="color: #1e40af; margin: 0 0 10px 0;">🔄 Revenue Stream Diversification</h4>
                        <p style="color: #1e3a8a; margin: 0;">{dominant_stream[0]} accounts for more than 40% of revenue. Consider expanding other revenue streams.</p>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

def create_sow_dashboard(df):
    """
    Create visualizations for SOW data
    
    Args:
        df: DataFrame containing SOW data
        
    Returns:
        None (displays visualizations in Streamlit)
    """
    if df.empty:
        st.warning("No SOW data available to display")
        return
    
    st.subheader("Statement of Work Analytics")
    
    # Add descriptive text
    st.markdown("""
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <h4 style="margin-top: 0;">📄 Statement of Work Dashboard</h4>
        <p>This dashboard provides insights into your Statements of Work (SOWs), including project timelines, 
        client distribution, and project status tracking.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_sows = len(df)
        st.metric("Total SOWs", total_sows)
    
    with col2:
        total_clients = df['ClientCompanyName'].nunique() if 'ClientCompanyName' in df.columns else 0
        st.metric("Total Clients", total_clients)
    
    with col3:
        # Calculate active projects (those not yet completed)
        if 'ActualEndDate' in df.columns:
            active_projects = df[df['ActualEndDate'].isna()].shape[0]
        else:
            active_projects = "N/A"
        st.metric("Active Projects", active_projects)
    
    with col4:
        # Calculate average project duration in days
        if 'ScheduledPlanningStartDate' in df.columns and 'ScheduledEndDate' in df.columns:
            df['PlannedDuration'] = (df['ScheduledEndDate'] - df['ScheduledPlanningStartDate']).dt.days
            avg_duration = df['PlannedDuration'].mean()
            st.metric("Avg. Project Duration", f"{avg_duration:.1f} days")
        else:
            st.metric("Avg. Project Duration", "N/A")
    
    # Client Distribution
    if 'ClientCompanyName' in df.columns:
        st.subheader("Client Distribution")
        
        # Add explanation for client distribution
        st.markdown("""
        <div style="background-color: #e8f4f8; padding: 10px; border-left: 4px solid #4dabf7; border-radius: 3px; margin-bottom: 15px;">
            This chart shows the distribution of SOWs by client. Understanding which clients have the most projects helps
            identify key business relationships and potential account expansion opportunities.
        </div>
        """, unsafe_allow_html=True)
        
        client_counts = df['ClientCompanyName'].value_counts().reset_index()
        client_counts.columns = ['Client', 'SOW Count']
        
        fig = px.bar(
            client_counts.sort_values('SOW Count', ascending=False).head(10),
            x='Client',
            y='SOW Count',
            title='Top 10 Clients by Number of SOWs',
            color='SOW Count',
            color_continuous_scale='Viridis'
        )
        
        fig.update_layout(
            xaxis_title="Client",
            yaxis_title="Number of SOWs",
            xaxis={'categoryorder': 'total descending'},
            margin=dict(t=50, b=100, l=20, r=20),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Project Timeline
    if 'ScheduledPlanningStartDate' in df.columns and 'ScheduledEndDate' in df.columns and 'ProjectName' in df.columns:
        st.subheader("Project Timeline")
        
        # Add explanation for project timeline
        st.markdown("""
        <div style="background-color: #f3f0ff; padding: 10px; border-left: 4px solid #7950f2; border-radius: 3px; margin-bottom: 15px;">
            This Gantt chart shows the timeline for your projects. Use this to visualize project overlaps, 
            identify resource allocation needs, and track project durations.
        </div>
        """, unsafe_allow_html=True)
        
        # Prepare data for Gantt chart
        timeline_df = df[['ProjectName', 'ScheduledPlanningStartDate', 'ScheduledEndDate', 'ClientCompanyName']].copy()
        
        # Sort by start date
        timeline_df = timeline_df.sort_values('ScheduledPlanningStartDate')
        
        # Limit to most recent 15 projects for readability
        timeline_df = timeline_df.tail(15)
        
        # Create Gantt chart
        fig = px.timeline(
            timeline_df,
            x_start='ScheduledPlanningStartDate',
            x_end='ScheduledEndDate',
            y='ProjectName',
            color='ClientCompanyName',
            title='Project Timeline (15 Most Recent Projects)',
            labels={
                'ScheduledPlanningStartDate': 'Start Date',
                'ScheduledEndDate': 'End Date',
                'ProjectName': 'Project',
                'ClientCompanyName': 'Client'
            }
        )
        
        fig.update_layout(
            xaxis_title="Timeline",
            yaxis_title="Project",
            yaxis={'categoryorder': 'trace'},
            margin=dict(t=50, b=50, l=20, r=20),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Project Status
    if 'ActualPlanningStartDate' in df.columns and 'ActualEndDate' in df.columns and 'ScheduledEndDate' in df.columns:
        st.subheader("Project Status")
        
        # Add explanation for project status
        st.markdown("""
        <div style="background-color: #e6fcf5; padding: 10px; border-left: 4px solid #12b886; border-radius: 3px; margin-bottom: 15px;">
            This chart shows the status of your projects. Track which projects are on time, delayed, or completed early
            to improve project management and client satisfaction.
        </div>
        """, unsafe_allow_html=True)
        
        # Calculate project status
        df['Status'] = 'Not Started'
        
        # Projects that have started
        started_mask = ~df['ActualPlanningStartDate'].isna()
        df.loc[started_mask, 'Status'] = 'In Progress'
        
        # Projects that have ended
        ended_mask = ~df['ActualEndDate'].isna()
        df.loc[ended_mask, 'Status'] = 'Completed'
        
        # Calculate if projects were completed on time
        df.loc[ended_mask, 'OnTime'] = df.loc[ended_mask, 'ActualEndDate'] <= df.loc[ended_mask, 'ScheduledEndDate']
        
        # Update status for completed projects
        df.loc[(df['Status'] == 'Completed') & (df['OnTime']), 'Status'] = 'Completed On Time'
        df.loc[(df['Status'] == 'Completed') & (~df['OnTime']), 'Status'] = 'Completed Late'
        
        # Create status counts
        status_counts = df['Status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        
        # Define colors for status
        status_colors = {
            'Not Started': '#6c757d',
            'In Progress': '#007bff',
            'Completed On Time': '#28a745',
            'Completed Late': '#dc3545'
        }
        
        # Create pie chart
        fig = px.pie(
            status_counts,
            values='Count',
            names='Status',
            title='Project Status Distribution',
            color='Status',
            color_discrete_map=status_colors
        )
        
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(
            margin=dict(t=50, b=50, l=20, r=20),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add insights about project status
        on_time_rate = df[df['Status'] == 'Completed On Time'].shape[0] / df[df['Status'].str.startswith('Completed')].shape[0] if df[df['Status'].str.startswith('Completed')].shape[0] > 0 else 0
        
        st.markdown(f"""
        <div style="background-color: #fff3bf; padding: 10px; border-radius: 3px; margin-top: 10px;">
            <strong>📊 Project Insights:</strong>
            <ul>
                <li>On-time completion rate: <strong>{on_time_rate:.1%}</strong></li>
                <li>Active projects: <strong>{df[df['Status'] == 'In Progress'].shape[0]}</strong></li>
                <li>Projects not yet started: <strong>{df[df['Status'] == 'Not Started'].shape[0]}</strong></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # SOW Data Table with search and filters
    st.subheader("SOW Data Explorer")
    
    # Add explanation for data explorer
    st.markdown("""
    <div style="background-color: #fff4e6; padding: 10px; border-left: 4px solid #fd7e14; border-radius: 3px; margin-bottom: 15px;">
        Use the filters below to search and explore your SOW data. You can filter by client, project name, or date range.
    </div>
    """, unsafe_allow_html=True)
    
    # Add filters
    col1, col2 = st.columns(2)
    
    with col1:
        if 'ClientCompanyName' in df.columns:
            client_options = ["All"] + sorted(df['ClientCompanyName'].unique().tolist())
            selected_client = st.selectbox("Filter by Client", client_options)
        else:
            selected_client = "All"
    
    with col2:
        if 'ProjectName' in df.columns:
            search_term = st.text_input("Search by Project Name")
        else:
            search_term = ""
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_client != "All" and 'ClientCompanyName' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['ClientCompanyName'] == selected_client]
    
    if search_term and 'ProjectName' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['ProjectName'].str.contains(search_term, case=False, na=False)]
    
    # Display filtered dataframe
    st.dataframe(filtered_df, use_container_width=True)
    
    # Add download option
    if not filtered_df.empty:
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Filtered SOW Data",
            data=csv,
            file_name="sow_data.csv",
            mime="text/csv"
        )

def render_analytics_dashboard():
    """Render the main analytics dashboard with tabs for different data types"""
    st.title("Access Care Analytics Dashboard")
    
    st.markdown("""
    <div style="background-color: white; padding: 1rem; border-radius: 10px; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
        <h4 style="margin-top: 0; color: #2c3e50;">📊 Airtable Analytics Dashboard</h4>
        <p style="margin-bottom: 0;">Visualize and analyze data from Airtable bases for utilization tracking, financial performance, and statements of work.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state variables if they don't exist
    if 'utilization_data' not in st.session_state:
        st.session_state.utilization_data = None
        
    if 'pnl_data' not in st.session_state:
        st.session_state.pnl_data = None
        
    if 'sow_data' not in st.session_state:
        st.session_state.sow_data = None
        
    # Initialize column mappings if they don't exist
    if 'column_mappings' not in st.session_state:
        st.session_state.column_mappings = {
            'UTILIZATION': {},
            'PNL': {},
            'SOW': {}
        }
    
    # Display button to refresh all data
    if st.button("Refresh All Data"):
        with st.spinner("Loading data from all Airtable bases..."):
            # Fetch data from all three bases
            st.session_state.utilization_data = get_utilization_data()
            st.session_state.pnl_data = get_pnl_data()
            st.session_state.sow_data = get_sow_data()
            st.success("Data loaded successfully!")
    
    # Create tabs for different analytics views
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Common Filters", "Utilization Analytics", "Financial Performance", "SOW Analytics", "Column Mappings"])
    
    # Common filters tab
    with tab1:
        st.header("Common Dashboard Filters")
        
        st.markdown("""
        <div style="background-color: white; padding: 1rem; border-radius: 10px; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
            <h4 style="margin-top: 0; color: #2c3e50;">🔍 Filter Dashboard Data</h4>
            <p style="margin-bottom: 0;">Set filters that will apply across all dashboard tabs. These filters will be applied to all visualizations.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize common filters in session state if they don't exist
        if 'common_filters' not in st.session_state:
            st.session_state.common_filters = {}
        
        # Client filter (common across all data types)
        client_filter = None
        if st.session_state.utilization_data is not None and not st.session_state.utilization_data.empty and 'Client' in st.session_state.utilization_data.columns:
            client_options = sorted(st.session_state.utilization_data['Client'].unique().tolist())
            default_clients = st.session_state.common_filters.get('Client', []) if isinstance(st.session_state.common_filters.get('Client', []), list) else []
            client_filter = st.multiselect("Client", client_options, 
                                         default=default_clients)
        elif st.session_state.pnl_data is not None and not st.session_state.pnl_data.empty and 'Client' in st.session_state.pnl_data.columns:
            client_options = sorted(st.session_state.pnl_data['Client'].unique().tolist())
            default_clients = st.session_state.common_filters.get('Client', []) if isinstance(st.session_state.common_filters.get('Client', []), list) else []
            client_filter = st.multiselect("Client", client_options,
                                         default=default_clients)
        else:
            client_filter = st.text_input("Client (enter name)", value=st.session_state.common_filters.get('Client', ''))
        
        # Date range filter
        date_col1, date_col2 = st.columns(2)
        
        with date_col1:
            # Set default start date to January 1st, 2025
            default_start_date = datetime(2025, 1, 1).date()
            start_date = st.date_input("Start Date", 
                                       value=st.session_state.common_filters.get('date_range', (default_start_date, datetime.now()))[0])
        with date_col2:
            end_date = st.date_input("End Date", 
                                     value=st.session_state.common_filters.get('date_range', (default_start_date, datetime.now()))[1])
        
        # Year filter
        year_options = ["All"]
        current_year = datetime.now().year
        year_options.extend(range(current_year - 5, current_year + 2))  # Include next year
        selected_year = st.selectbox("Year", year_options, 
                                     index=year_options.index(st.session_state.common_filters.get('Year', 'All')) if st.session_state.common_filters.get('Year', 'All') in year_options else 0)
        
        # Site filter - changed to multiselect
        site_filter = None
        site_options = []
        
        if st.session_state.utilization_data is not None and not st.session_state.utilization_data.empty and 'Site' in st.session_state.utilization_data.columns:
            # Convert all values to strings before sorting
            site_values = [str(x) for x in st.session_state.utilization_data['Site'].unique()]
            site_options = sorted(site_values)
            default_sites = st.session_state.common_filters.get('Site', []) if isinstance(st.session_state.common_filters.get('Site', []), list) else []
            site_filter = st.multiselect("Site", site_options, default=default_sites)
        elif st.session_state.pnl_data is not None and not st.session_state.pnl_data.empty and 'Site_Location' in st.session_state.pnl_data.columns:
            # Convert all values to strings before sorting
            site_values = [str(x) for x in st.session_state.pnl_data['Site_Location'].unique()]
            site_options = sorted(site_values)
            default_sites = st.session_state.common_filters.get('Site', []) if isinstance(st.session_state.common_filters.get('Site', []), list) else []
            site_filter = st.multiselect("Site", site_options, default=default_sites)
        else:
            site_filter = st.text_input("Site (enter name)", value=st.session_state.common_filters.get('Site', ''))
        
        # Save filters to session state when apply button is clicked
        if st.button("Apply Filters"):
            st.session_state.common_filters = {
                'Client': client_filter if client_filter else None,
                'date_range': (start_date, end_date),
                'Year': selected_year if selected_year != "All" else None,
                'Site': site_filter if site_filter else None
            }
            
            # Remove None values
            st.session_state.common_filters = {k: v for k, v in st.session_state.common_filters.items() if v is not None}
            
            st.success("Filters applied! The visualizations in all tabs will be updated.")
            
        # Clear filters button
        if st.button("Clear All Filters"):
            st.session_state.common_filters = {}
            st.success("All filters cleared!")
            st.rerun()
    
    # Utilization Analytics tab
    with tab2:
        st.header("Utilization Analytics")
        
        # Add tab-specific filters
        with st.expander("Utilization Filters", expanded=True):
            # Date filters for utilization data
            col1, col2 = st.columns(2)
            with col1:
                year_options = ["All"] + list(range(2023, datetime.now().year + 1))
                tab_year = st.selectbox("Filter by Year", year_options, key="util_year")
            
            with col2:
                tab_client = st.text_input("Filter by Client (leave empty for all)", key="util_client")
            
            # Create filters dictionary based on selections
            tab_filters = {}
            if tab_year != "All":
                tab_filters['year'] = tab_year
            if tab_client:
                tab_filters['client'] = tab_client
        
        # Fetch button to get utilization data
        if st.button("Load Utilization Data"):
            with st.spinner("Loading utilization data..."):
                utilization_df = get_utilization_data(tab_filters)
                st.session_state.utilization_data = utilization_df
                
                # Display column information for debugging
                if not utilization_df.empty:
                    st.success(f"Successfully loaded utilization data with {len(utilization_df)} records")
                    with st.expander("View Column Information"):
                        st.write("Available columns in the data:", utilization_df.columns.tolist())
                else:
                    st.warning("No utilization data found. Please check your filters or Airtable connection.")
        
        # Display utilization data if available
        if st.session_state.utilization_data is not None and not st.session_state.utilization_data.empty:
            # Apply common filters
            filtered_df = apply_filters(st.session_state.utilization_data, st.session_state.common_filters)
            
            # Show filter summary
            if st.session_state.common_filters:
                st.info(f"Showing data with applied filters: {', '.join([f'{k}: {v}' for k, v in st.session_state.common_filters.items()])}")
                st.write(f"Filtered data: {len(filtered_df)} records (from {len(st.session_state.utilization_data)} total)")
            
            # Pass interactive=True parameter to always show expanded visualization options
            create_utilization_dashboard(filtered_df, interactive=True)
        else:
            st.info("No utilization data loaded. Please use the 'Load Utilization Data' button above.")
    
    # Financial Performance tab
    with tab3:
        st.header("Financial Performance")
        
        # Add tab-specific filters
        with st.expander("Financial Filters", expanded=True):
            # Filters for PnL data
            col1, col2 = st.columns(2)
            with col1:
                tab_client_pnl = st.text_input("Filter by Client (leave empty for all)", key="client_filter_pnl_tab")
            
            with col2:
                if st.session_state.pnl_data is not None and not st.session_state.pnl_data.empty and 'Service_Month' in st.session_state.pnl_data.columns:
                    month_options = ["All"] + sorted(st.session_state.pnl_data['Service_Month'].unique().tolist())
                    tab_month = st.selectbox("Service Month", month_options, key="pnl_month")
                else:
                    tab_month = "All"
            
            # Create filters dictionary based on selections
            tab_filters = {}
            if tab_client_pnl:
                tab_filters['client'] = tab_client_pnl
            if tab_month != "All":
                tab_filters['month'] = tab_month
        
        # Fetch button for PnL data
        if st.button("Load Financial Data"):
            with st.spinner("Loading financial data..."):
                pnl_df = get_pnl_data(tab_filters)
                st.session_state.pnl_data = pnl_df
                
                # Display column information for debugging
                if not pnl_df.empty:
                    st.success(f"Successfully loaded financial data with {len(pnl_df)} records")
                    with st.expander("View Column Information"):
                        st.write("Available columns in the data:", pnl_df.columns.tolist())
                else:
                    st.warning("No financial data found. Please check your filters or Airtable connection.")
        
        # Display PnL data if available
        if st.session_state.pnl_data is not None and not st.session_state.pnl_data.empty:
            # Apply common filters
            filtered_df = apply_filters(st.session_state.pnl_data, st.session_state.common_filters)
            
            # Show filter summary
            if st.session_state.common_filters:
                st.info(f"Showing data with applied filters: {', '.join([f'{k}: {v}' for k, v in st.session_state.common_filters.items()])}")
                st.write(f"Filtered data: {len(filtered_df)} records (from {len(st.session_state.pnl_data)} total)")
            
            create_pnl_dashboard(filtered_df)
        else:
            st.info("No financial data loaded. Please use the 'Load Financial Data' button above.")
    
    # SOW Analytics tab
    with tab4:
        st.header("SOW Analytics")
        
        # Add tab-specific filters
        with st.expander("SOW Filters", expanded=True):
            # Filters for SOW data
            col1, col2 = st.columns(2)
            with col1:
                tab_client_sow = st.text_input("Filter by Client (leave empty for all)", key="client_filter_sow_tab")
            
            with col2:
                if st.session_state.sow_data is not None and not st.session_state.sow_data.empty and 'ProjectName' in st.session_state.sow_data.columns:
                    project_options = ["All"] + sorted(st.session_state.sow_data['ProjectName'].unique().tolist())
                    tab_project = st.selectbox("Project", project_options, key="sow_project")
                else:
                    tab_project = "All"
            
            # Create filters dictionary based on selections
            tab_filters = {}
            if tab_client_sow:
                tab_filters['client'] = tab_client_sow
            if tab_project != "All":
                tab_filters['project'] = tab_project
        
        # Fetch button for SOW data
        if st.button("Load SOW Data"):
            with st.spinner("Loading SOW data..."):
                sow_df = get_sow_data(tab_filters)
                st.session_state.sow_data = sow_df
                
                # Display column information for debugging
                if not sow_df.empty:
                    st.success(f"Successfully loaded SOW data with {len(sow_df)} records")
                    with st.expander("View Column Information"):
                        st.write("Available columns in the data:", sow_df.columns.tolist())
                else:
                    st.warning("No SOW data found. Please check your Airtable connection.")
        
        # Display SOW data if available
        if st.session_state.sow_data is not None and not st.session_state.sow_data.empty:
            # Apply common filters
            filtered_df = apply_filters(st.session_state.sow_data, st.session_state.common_filters)
            
            # Show filter summary
            if st.session_state.common_filters:
                st.info(f"Showing data with applied filters: {', '.join([f'{k}: {v}' for k, v in st.session_state.common_filters.items()])}")
                st.write(f"Filtered data: {len(filtered_df)} records (from {len(st.session_state.sow_data)} total)")
            
            create_sow_dashboard(filtered_df)
        else:
            st.info("No SOW data loaded. Please use the 'Load SOW Data' button above.")
    
    # Column Mappings tab
    with tab5:
        st.header("Column Mappings Configuration")
        st.markdown("""
        <div style="background-color: white; padding: 1rem; border-radius: 10px; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
            <h4 style="margin-top: 0; color: #2c3e50;">⚙️ Configure Data Column Mappings</h4>
            <p style="margin-bottom: 0;">If the dashboard cannot automatically detect your Airtable column names, you can manually map them here.</p>
        </div>
        """, unsafe_allow_html=True)
        
        mapping_tables = ["UTILIZATION", "PNL", "SOW"]
        mapping_tab1, mapping_tab2, mapping_tab3 = st.tabs(mapping_tables)
        
        # Required fields for each table
        required_fields = {
            "UTILIZATION": ['CLIENT', 'SITE', 'DATE_OF_SERVICE', 'YEAR', 'HEADCOUNT', 
                           'TOTAL_BOOKING_APPTS', 'TOTAL_COMPLETED_APPTS'],
            "PNL": ['CLIENT', 'SITE_LOCATION', 'SERVICE_MONTH', 'REVENUE_TOTAL', 
                    'EXPENSE_COGS_TOTAL', 'NET_PROFIT'],
            "SOW": ['ClientCompanyName', 'ProjectName', 'SOWQuoteNumber', 
                   'ScheduledPlanningStartDate', 'ScheduledEndDate']
        }
        
        with mapping_tab1:
            st.subheader("Utilization Data Mappings")
            
            # Show actual columns if data exists
            if st.session_state.utilization_data is not None and not st.session_state.utilization_data.empty:
                st.write("Available columns in the data:", st.session_state.utilization_data.columns.tolist())
                
                st.write("Map required fields to your actual column names:")
                for field in required_fields["UTILIZATION"]:
                    col_options = [""] + st.session_state.utilization_data.columns.tolist()
                    selected_col = st.selectbox(
                        f"Map {field} to:", 
                        options=col_options,
                        index=col_options.index(st.session_state.column_mappings["UTILIZATION"].get(field, "")) if st.session_state.column_mappings["UTILIZATION"].get(field, "") in col_options else 0,
                        key=f"util_{field}"
                    )
                    if selected_col:
                        st.session_state.column_mappings["UTILIZATION"][field] = selected_col
            else:
                st.info("Load Utilization Data first to configure column mappings")
                
        with mapping_tab2:
            st.subheader("PnL Data Mappings")
            
            # Show actual columns if data exists
            if st.session_state.pnl_data is not None and not st.session_state.pnl_data.empty:
                st.write("Available columns in the data:", st.session_state.pnl_data.columns.tolist())
                
                st.write("Map required fields to your actual column names:")
                for field in required_fields["PNL"]:
                    col_options = [""] + st.session_state.pnl_data.columns.tolist()
                    selected_col = st.selectbox(
                        f"Map {field} to:", 
                        options=col_options,
                        index=col_options.index(st.session_state.column_mappings["PNL"].get(field, "")) if st.session_state.column_mappings["PNL"].get(field, "") in col_options else 0,
                        key=f"pnl_{field}"
                    )
                    if selected_col:
                        st.session_state.column_mappings["PNL"][field] = selected_col
            else:
                st.info("Load Financial Data first to configure column mappings")
                
        with mapping_tab3:
            st.subheader("SOW Data Mappings")
            
            # Show actual columns if data exists
            if st.session_state.sow_data is not None and not st.session_state.sow_data.empty:
                st.write("Available columns in the data:", st.session_state.sow_data.columns.tolist())
                
                st.write("Map required fields to your actual column names:")
                for field in required_fields["SOW"]:
                    col_options = [""] + st.session_state.sow_data.columns.tolist()
                    selected_col = st.selectbox(
                        f"Map {field} to:", 
                        options=col_options,
                        index=col_options.index(st.session_state.column_mappings["SOW"].get(field, "")) if st.session_state.column_mappings["SOW"].get(field, "") in col_options else 0,
                        key=f"sow_{field}"
                    )
                    if selected_col:
                        st.session_state.column_mappings["SOW"][field] = selected_col
            else:
                st.info("Load SOW Data first to configure column mappings")
        
        # Add button to apply mappings
        if st.button("Apply Column Mappings"):
            st.success("Column mappings saved! The mappings will be used when loading data.")
            # The mappings are already saved in session_state, we just show confirmation

if __name__ == "__main__":
    render_analytics_dashboard() 