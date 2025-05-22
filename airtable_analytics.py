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
        
        # Ensure Service_Days column exists, if not, create it with default value of 1
        if 'Service_Days' not in df.columns:
            df['Service_Days'] = 1  # Default to 1 day if not specified
            
        client_profit = df.groupby('Client').agg({
            'Revenue_Total': 'sum',
            'Expense_COGS_Total': 'sum',
            'Net_Profit': 'sum',
            'Service_Days': 'sum'  # Add Service_Days to the aggregation
        }).reset_index()
        
        # Convert Service_Days to numeric, ensuring it's at least 1 for each client
        client_profit['Service_Days'] = pd.to_numeric(client_profit['Service_Days'], errors='coerce')
        client_profit['Service_Days'] = client_profit['Service_Days'].fillna(1)
        client_profit['Service_Days'] = client_profit['Service_Days'].apply(lambda x: max(x, 1))  # Ensure min value is 1
        
        client_profit['Profit_Margin'] = client_profit['Net_Profit'] / client_profit['Revenue_Total']
        client_profit['Profit_Per_Day'] = client_profit['Net_Profit'] / client_profit['Service_Days']
        
        fig = px.bar(
            client_profit.sort_values('Net_Profit', ascending=False).head(10),
            x='Client',
            y='Net_Profit',
            title='Top 10 Clients by Net Profit',
            color='Profit_Per_Day',
            color_continuous_scale='RdYlGn',
            text='Net_Profit'
        )
        
        fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        
        # Use the safe layout update helper
        safe_update_layout(fig,
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
    
    # Always show detailed analysis (removed the button and condition)
    st.markdown("""
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-top: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
        <h3 style="color: #2c3e50; margin-top: 0; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px;">📊 Enhanced Financial Analysis Report</h3>
    """, unsafe_allow_html=True)

    # 1. Overall Financial Health with KPI trend
    st.markdown("### 1. Overall Financial Health")
    
    # Calculate key financial metrics
    total_revenue = df['Revenue_Total'].sum()
    total_expenses = df['Expense_COGS_Total'].sum()
    total_profit = df['Net_Profit'].sum()
    overall_margin = total_profit / total_revenue if total_revenue > 0 else 0
    
    # Add formula explanations for metrics
    formula_revenue = "Sum of all Revenue_Total values"
    formula_expenses = "Sum of all Expense_COGS_Total values"
    formula_profit = "Sum of all Net_Profit values (or Revenue_Total - Expense_COGS_Total)"
    formula_margin = "Net Profit ÷ Total Revenue"
    
    # Calculate profit growth if temporal data available
    profit_growth = "N/A"
    revenue_growth = "N/A"
    formula_growth = "Formula: (Current Period Value ÷ First Period Value) - 1"
    
    if 'Service_Month' in df.columns:
        valid_months_df = df.dropna(subset=['Service_Month'])
        if not valid_months_df.empty and pd.api.types.is_datetime64_any_dtype(valid_months_df['Service_Month']):
            # Calculate YoY or QoQ growth if possible
            monthly_data = valid_months_df.groupby(pd.Grouper(key='Service_Month', freq='M')).agg({
                'Revenue_Total': 'sum',
                'Net_Profit': 'sum'
            }).reset_index()
            
            if len(monthly_data) >= 2:
                revenue_growth = ((monthly_data['Revenue_Total'].iloc[-1] / monthly_data['Revenue_Total'].iloc[0]) - 1)
                profit_growth = ((monthly_data['Net_Profit'].iloc[-1] / monthly_data['Net_Profit'].iloc[0]) - 1) if monthly_data['Net_Profit'].iloc[0] > 0 else 0

    # Display metrics in a more visually appealing way with growth indicators
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div style="background-color: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <h4 style="color: #6b7280; margin: 0 0 10px 0; font-size: 0.9rem;">Total Revenue</h4>
            <p style="color: #1f2937; margin: 0; font-size: 1.5rem; font-weight: 600;">${total_revenue:,.2f}</p>
            {f"<p style='color: {'#10b981' if revenue_growth > 0 else '#ef4444'}; margin: 5px 0 0 0; font-size: 0.8rem;'>{'↑' if revenue_growth > 0 else '↓'} {abs(revenue_growth):.1%}</p>" if revenue_growth != "N/A" else ""}
            <p style="color: #6b7280; margin: 5px 0 0 0; font-size: 0.7rem;">{formula_revenue}</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div style="background-color: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <h4 style="color: #6b7280; margin: 0 0 10px 0; font-size: 0.9rem;">Total Expenses</h4>
            <p style="color: #1f2937; margin: 0; font-size: 1.5rem; font-weight: 600;">${total_expenses:,.2f}</p>
            <p style="color: #6b7280; margin: 5px 0 0 0; font-size: 0.7rem;">{formula_expenses}</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div style="background-color: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <h4 style="color: #6b7280; margin: 0 0 10px 0; font-size: 0.9rem;">Net Profit</h4>
            <p style="color: #1f2937; margin: 0; font-size: 1.5rem; font-weight: 600;">${total_profit:,.2f}</p>
            {f"<p style='color: {'#10b981' if profit_growth > 0 else '#ef4444'}; margin: 5px 0 0 0; font-size: 0.8rem;'>{'↑' if profit_growth > 0 else '↓'} {abs(profit_growth):.1%}</p>" if profit_growth != "N/A" else ""}
            <p style="color: #6b7280; margin: 5px 0 0 0; font-size: 0.7rem;">{formula_profit}</p>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div style="background-color: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <h4 style="color: #6b7280; margin: 0 0 10px 0; font-size: 0.9rem;">Profit Margin</h4>
            <p style="color: #1f2937; margin: 0; font-size: 1.5rem; font-weight: 600;">{overall_margin:.1%}</p>
            <p style="color: #6b7280; margin: 5px 0 0 0; font-size: 0.7rem;">{formula_margin}</p>
        </div>
        """, unsafe_allow_html=True)
            
    # Add trend visualization if temporal data is available
    if 'Service_Month' in df.columns:
        valid_months_df = df.dropna(subset=['Service_Month'])
        if not valid_months_df.empty and pd.api.types.is_datetime64_any_dtype(valid_months_df['Service_Month']):
            monthly_data = valid_months_df.groupby(pd.Grouper(key='Service_Month', freq='M')).agg({
                'Revenue_Total': 'sum',
                'Expense_COGS_Total': 'sum',
                'Net_Profit': 'sum'
            }).reset_index()
            
            if len(monthly_data) > 1:
                # Create a financial trend chart
                monthly_data['Profit_Margin'] = monthly_data['Net_Profit'] / monthly_data['Revenue_Total']
                
                # Format dates for better display
                monthly_data['Month'] = monthly_data['Service_Month'].dt.strftime('%b %Y')
                
                # Create a line chart with dual y-axis for revenue/profit (left) and margin (right)
                fig = go.Figure()
                
                # Add revenue line
                fig.add_trace(go.Scatter(
                    x=monthly_data['Month'],
                    y=monthly_data['Revenue_Total'],
                    name='Revenue',
                    line=dict(color='#3b82f6', width=3),
                    hovertemplate='Revenue: $%{y:,.2f}<extra></extra>'
                ))
                
                # Add profit line
                fig.add_trace(go.Scatter(
                    x=monthly_data['Month'],
                    y=monthly_data['Net_Profit'],
                    name='Net Profit',
                    line=dict(color='#10b981', width=3),
                    hovertemplate='Profit: $%{y:,.2f}<extra></extra>'
                ))
                
                # Add profit margin line with secondary y-axis
                fig.add_trace(go.Scatter(
                    x=monthly_data['Month'],
                    y=monthly_data['Profit_Margin'],
                    name='Profit Margin',
                    line=dict(color='#f59e0b', width=3, dash='dash'),
                    yaxis='y2',
                    hovertemplate='Margin: %{y:.1%}<extra></extra>'
                ))
                
                # Update layout for dual y-axis
                fig.update_layout(
                    title='Financial Trends Over Time',
                    xaxis=dict(title='Month'),
                    yaxis=dict(
                        title='Amount ($)',
                        titlefont=dict(color='#3b82f6'),
                        tickfont=dict(color='#3b82f6'),
                        gridcolor='#e5e7eb'
                    ),
                    yaxis2=dict(
                        title='Profit Margin (%)',
                        titlefont=dict(color='#f59e0b'),
                        tickfont=dict(color='#f59e0b'),
                        anchor='x',
                        overlaying='y',
                        side='right',
                        tickformat='.0%',
                        range=[0, max(monthly_data['Profit_Margin']) * 1.5]  # Set range with some headroom
                    ),
                    legend=dict(orientation='h', y=1.1),
                    height=400,
                    margin=dict(l=60, r=60, t=50, b=50),
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Calculate trailing indicators
                if len(monthly_data) >= 6:
                    last_6_months = monthly_data.tail(6)
                    avg_margin_6m = last_6_months['Profit_Margin'].mean()
                    margin_trend = last_6_months['Profit_Margin'].iloc[-1] - last_6_months['Profit_Margin'].iloc[0]
                    
                    st.markdown(f"""
                    <div style="background-color: #f1f5f9; padding: 15px; border-radius: 8px; margin-top: 10px;">
                        <strong>📈 Trend Insights:</strong>
                        <ul>
                            <li>6-month average profit margin: <strong>{avg_margin_6m:.1%}</strong></li>
                            <li>Margin trend is <strong>{'improving' if margin_trend > 0 else 'declining'}</strong> over the last 6 months</li>
                            <li>Most profitable month: <strong>{monthly_data.iloc[monthly_data['Net_Profit'].argmax()]['Month']}</strong></li>
                        </ul>
                        <p style="font-size: 0.8rem; color: #6b7280; margin-top: 10px; border-top: 1px solid #e5e7eb; padding-top: 8px;">
                            <strong>Growth Calculation:</strong> {formula_growth}<br>
                            <strong>Margin Calculation:</strong> Net Profit ÷ Revenue for each period
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

    # 2. Client Portfolio Analysis - Enhanced with quadrant analysis
    st.markdown("### 2. Client Portfolio Analysis")
    
    # Add formula explanations for client metrics
    st.markdown("""
    <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #64748b;">
        <h4 style="color: #334155; margin: 0 0 10px 0;">📊 Client Metrics Explained</h4>
        <ul style="font-size: 0.8rem; color: #475569; margin: 0; padding-left: 20px;">
            <li><strong>Revenue Share</strong> = Client Revenue ÷ Total Revenue</li>
            <li><strong>Profit Per Day</strong> = Client Net Profit ÷ Client Service Days</li>
            <li><strong>Profit Margin</strong> = Client Net Profit ÷ Client Revenue</li>
        </ul>
        <p style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">These metrics help identify your most valuable clients and areas for improvement.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Ensure Service_Days column exists, if not, create it with default value of 1
    if 'Service_Days' not in df.columns:
        df['Service_Days'] = 1  # Default to 1 day if not specified
    
    client_metrics = df.groupby('Client').agg({
        'Revenue_Total': 'sum',
        'Expense_COGS_Total': 'sum',
        'Net_Profit': 'sum',
        'Service_Days': 'sum'  # Add Service_Days to the aggregation
    }).reset_index()
    
    # Convert Service_Days to numeric, ensuring it's at least 1 for each client
    client_metrics['Service_Days'] = pd.to_numeric(client_metrics['Service_Days'], errors='coerce')
    client_metrics['Service_Days'] = client_metrics['Service_Days'].fillna(1)
    client_metrics['Service_Days'] = client_metrics['Service_Days'].apply(lambda x: max(x, 1))  # Ensure min value is 1
    
    client_metrics['Revenue_Share'] = client_metrics['Revenue_Total'] / total_revenue
    client_metrics['Profit_Per_Day'] = client_metrics['Net_Profit'] / client_metrics['Service_Days']
    client_metrics['Profit_Margin'] = client_metrics['Net_Profit'] / client_metrics['Revenue_Total']
    
    # Create client quadrant analysis (Revenue vs Profit Margin)
    if len(client_metrics) >= 3:  # Only create if we have enough clients
        # Calculate median values for quadrant thresholds
        median_revenue = client_metrics['Revenue_Total'].median()
        median_margin = client_metrics['Profit_Margin'].median()
        
        # Create scatter plot for quadrant analysis
        fig = px.scatter(
            client_metrics,
            x='Revenue_Total',
            y='Profit_Margin',
            size='Service_Days',  # Bubble size represents service days
            color='Profit_Per_Day',  # Color represents profitability
            hover_name='Client',
            color_continuous_scale='RdYlGn',
            size_max=50,
            labels={
                'Revenue_Total': 'Total Revenue ($)',
                'Profit_Margin': 'Profit Margin (%)',
                'Service_Days': 'Service Days',
                'Profit_Per_Day': 'Profit Per Day ($)'
            },
            title='Client Portfolio Matrix: Revenue vs. Profit Margin',
            text='Client'  # Add client names to the points
        )
        
        # Add quadrant lines
        fig.add_vline(x=median_revenue, line_width=1, line_color='gray', line_dash='dash')
        fig.add_hline(y=median_margin, line_width=1, line_color='gray', line_dash='dash')
        
        # Add quadrant labels
        fig.add_annotation(
            x=median_revenue/2, 
            y=median_margin*1.5, 
            text="Low Revenue, <br>High Margin <br>(Growth Potential)",
            showarrow=False,
            font=dict(color="#1e40af")
        )
        fig.add_annotation(
            x=median_revenue*1.5, 
            y=median_margin*1.5, 
            text="High Revenue, <br>High Margin <br>(Stars)",
            showarrow=False,
            font=dict(color="#047857")
        )
        fig.add_annotation(
            x=median_revenue/2, 
            y=median_margin/2, 
            text="Low Revenue, <br>Low Margin <br>(Evaluate)",
            showarrow=False,
            font=dict(color="#b91c1c")
        )
        fig.add_annotation(
            x=median_revenue*1.5, 
            y=median_margin/2, 
            text="High Revenue, <br>Low Margin <br>(Improve Efficiency)",
            showarrow=False,
            font=dict(color="#92400e")
        )
        
        # Update traces with safer parameters
        fig.update_traces(
            textposition='top center',
            marker=dict(opacity=0.8, line=dict(width=1, color='DarkSlateGrey')),
        )
        
        # Use the safe layout update helper
        safe_update_layout(fig, 
            height=600,
            margin=dict(l=60, r=60, t=50, b=50),
            xaxis=dict(type='log', title_font=dict(size=14)),
            yaxis=dict(tickformat='.0%', title_font=dict(size=14))
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add explanation for quadrant analysis calculation
        st.markdown("""
        <div style="background-color: #f8fafc; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-size: 0.8rem;">
            <strong>How Client Portfolio Matrix is Calculated:</strong><br>
            • X-axis: Total Revenue for each client<br>
            • Y-axis: Profit Margin (Net Profit ÷ Revenue) for each client<br>
            • Bubble Size: Number of service days for each client<br>
            • Color: Profit per day (darker green = higher profit per day)<br>
            • Quadrant Lines: Placed at median values for revenue and profit margin
        </div>
        """, unsafe_allow_html=True)
        
        # Add strategic recommendations based on quadrants
        st.markdown("""
        <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #64748b;">
            <h4 style="color: #334155; margin: 0 0 10px 0;">💼 Portfolio Strategy Recommendations</h4>
            <ul style="margin: 0; padding-left: 20px;">
                <li><strong>Stars (High Revenue, High Margin):</strong> Nurture these relationships and look for expansion opportunities.</li>
                <li><strong>Growth Potential (Low Revenue, High Margin):</strong> Increase allocation of resources to grow these accounts.</li>
                <li><strong>Improve Efficiency (High Revenue, Low Margin):</strong> Review cost structure and pricing strategy to improve profitability.</li>
                <li><strong>Evaluate (Low Revenue, Low Margin):</strong> Consider restructuring contracts or potentially phasing out these clients.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Display top 5 clients with enhanced metrics
    st.markdown("#### Top Client Performance")
    
    # Create table with key metrics for top clients
    top_clients_df = client_metrics.sort_values('Revenue_Total', ascending=False).head(5)
    
    # Create a styled table with conditional formatting
    client_table_data = []
    for _, client in top_clients_df.iterrows():
        client_table_data.append({
            'Client': client['Client'],
            'Revenue': f"${client['Revenue_Total']:,.2f}",
            'Revenue Share': f"{client['Revenue_Share']:.1%}",
            'Profit': f"${client['Net_Profit']:,.2f}",
            'Margin': f"{client['Profit_Margin']:.1%}",
            'Profit/Day': f"${client['Profit_Per_Day']:.2f}"
        })
    
    # Convert to DataFrame for display
    client_table = pd.DataFrame(client_table_data)
    
    # Apply styling with colors based on profit margin
    def color_margin(val):
        # Extract percentage value
        try:
            pct = float(val.strip('%')) / 100
            if pct > 0.20:  # Good margin
                return 'background-color: #d1fae5; color: #065f46'
            elif pct > 0.10:  # Medium margin
                return 'background-color: #e0f2fe; color: #0369a1'
            elif pct > 0:  # Low margin
                return 'background-color: #fff7ed; color: #9a3412'
            else:  # Negative margin
                return 'background-color: #fee2e2; color: #b91c1c'
        except:
            return ''
    
    # Show styled table
    st.dataframe(client_table.style.applymap(color_margin, subset=['Margin']), use_container_width=True)
    
    # Add advanced client analytics
    if len(client_metrics) > 5:
        # Calculate portfolio statistics
        top_3_revenue = client_metrics.head(3)['Revenue_Total'].sum() / total_revenue
        bottom_50_pct = client_metrics[client_metrics['Revenue_Total'].cumsum() > total_revenue * 0.5].shape[0]
        
        st.markdown("#### Client Portfolio Metrics")
        metric1, metric2, metric3, metric4 = st.columns(4)
        
        with metric1:
            st.metric("Top 3 Client %", f"{top_3_revenue:.1%}")
        
        with metric2:
            st.metric("Clients for 50% Revenue", bottom_50_pct)
        
        with metric3:
            positive_margin = client_metrics[client_metrics['Profit_Margin'] > 0].shape[0]
            st.metric("Profitable Clients", f"{positive_margin}/{len(client_metrics)}")
        
        with metric4:
            avg_revenue_per_client = total_revenue / len(client_metrics)
            st.metric("Avg Revenue/Client", f"${avg_revenue_per_client:,.2f}")

    # 3. Revenue Stream Analysis with expanded visualization
    st.markdown("### 3. Enhanced Revenue Analysis")
    
    # Create revenue streams dictionary
    revenue_streams_data = {}
    
    # Check what revenue breakdown columns exist in the data
    potential_revenue_columns = [
        ('Wellness Fund', 'Revenue_WellnessFund'),
        ('Dental Claims', 'Revenue_DentalClaim'),
        ('Medical Claims', 'Revenue_MedicalClaim_InclCancelled'),
        ('Missed Appointments', 'Revenue_MissedAppointments'),
        ('Events', 'Revenue_EventTotal')
    ]
    
    # Add any columns that exist to our revenue streams data
    for stream_name, column in potential_revenue_columns:
        if column in df.columns:
            revenue_streams_data[stream_name] = df[column].sum()
    
    # Calculate total to get percentages
    total_stream_revenue = sum(revenue_streams_data.values())
    
    # Only proceed if we have revenue data
    if total_stream_revenue > 0:
        # Create a DataFrame for better visualization
        revenue_df = pd.DataFrame({
            'Stream': list(revenue_streams_data.keys()),
            'Amount': list(revenue_streams_data.values())
        })
        
        revenue_df['Percentage'] = revenue_df['Amount'] / total_stream_revenue
        revenue_df = revenue_df.sort_values('Amount', ascending=False)
        
        # Create side-by-side charts: pie chart and bar chart
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Create pie chart for distribution
            fig1 = px.pie(
                revenue_df,
                values='Amount',
                names='Stream',
                title='Revenue Stream Distribution',
                color_discrete_sequence=px.colors.qualitative.Bold,
                hole=0.4
            )
            
            fig1.update_traces(
                textposition='inside',
                textinfo='percent+label',
                insidetextfont=dict(color='white')
            )
            
            fig1.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(orientation='h', yanchor='bottom', y=-0.3)
            )
            
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Create bar chart for absolute values
            fig2 = px.bar(
                revenue_df,
                y='Stream',
                x='Amount',
                title='Revenue by Source',
                color='Stream',
                color_discrete_sequence=px.colors.qualitative.Bold,
                text='Percentage'
            )
            
            fig2.update_traces(
                texttemplate='%{text:.1%}',
                textposition='inside',
                insidetextfont=dict(color='white')
            )
            
            fig2.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                xaxis_title='Revenue ($)',
                yaxis_title='',
                height=400,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            
            st.plotly_chart(fig2, use_container_width=True)
        
        # Add revenue stream analysis
        st.markdown("#### Revenue Stream Performance")
        
        # Create a table with revenue metrics
        for i, row in revenue_df.iterrows():
            st.markdown(f"""
            <div style="background-color: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 5px solid {px.colors.qualitative.Bold[i % len(px.colors.qualitative.Bold)]}; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="color: #1f2937; margin: 0;">{row['Stream']}</h4>
                    <span style="color: #6b7280; font-size: 0.9rem; font-weight: bold;">{row['Percentage']:.1%} of revenue</span>
                </div>
                <p style="color: #1f2937; margin: 10px 0 0 0; font-size: 1.2rem;">${row['Amount']:,.2f}</p>
            </div>
            """, unsafe_allow_html=True)

    # 4. Time-based Analysis with enhanced visualizations
    st.markdown("### 4. Financial Trends Analysis")
    if 'Service_Month' in df.columns:
        valid_months_df = df.dropna(subset=['Service_Month'])
        
        if not valid_months_df.empty and pd.api.types.is_datetime64_any_dtype(valid_months_df['Service_Month']):
            # If we have client information, we can do client-based temporal analysis
            if 'Client' in valid_months_df.columns:
                # Get the top clients by revenue
                top_clients = client_metrics.sort_values('Revenue_Total', ascending=False).head(5)['Client'].tolist()
                
                # Prepare data for time series by client
                client_monthly = valid_months_df[valid_months_df['Client'].isin(top_clients)].copy()
                
                if not client_monthly.empty:
                    # Group by month and client
                    client_trends = client_monthly.groupby([pd.Grouper(key='Service_Month', freq='M'), 'Client']).agg({
                        'Revenue_Total': 'sum',
                        'Net_Profit': 'sum'
                    }).reset_index()
                    
                    # Create stacked area chart for revenue trends by client
                    fig = px.area(
                        client_trends,
                        x='Service_Month',
                        y='Revenue_Total',
                        color='Client',
                        title='Revenue Trends by Top Clients',
                        labels={
                            'Service_Month': 'Month',
                            'Revenue_Total': 'Revenue ($)',
                            'Client': 'Client'
                        }
                    )
                    
                    fig.update_layout(
                        xaxis_title='Month',
                        yaxis_title='Revenue ($)',
                        legend_title='Client',
                        height=450,
                        margin=dict(l=40, r=40, t=50, b=50)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Create line chart for profit margin trends by client
                    client_trends['Profit_Margin'] = client_trends['Net_Profit'] / client_trends['Revenue_Total']
                    
                    fig = px.line(
                        client_trends,
                        x='Service_Month',
                        y='Profit_Margin',
                        color='Client',
                        title='Profit Margin Trends by Client',
                        labels={
                            'Service_Month': 'Month',
                            'Profit_Margin': 'Profit Margin',
                            'Client': 'Client'
                        }
                    )
                    
                    fig.update_layout(
                        xaxis_title='Month',
                        yaxis_title='Profit Margin',
                        yaxis_tickformat='.0%',
                        legend_title='Client',
                        height=450,
                        margin=dict(l=40, r=40, t=50, b=50)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
            # Monthly trends analysis
            monthly_trends = valid_months_df.groupby(pd.Grouper(key='Service_Month', freq='M')).agg({
                'Revenue_Total': 'sum',
                'Expense_COGS_Total': 'sum',
                'Net_Profit': 'sum'
            }).reset_index()
            
            if len(monthly_trends) > 1:
                monthly_trends['Month'] = monthly_trends['Service_Month'].dt.strftime('%b %Y')
                monthly_trends['Profit_Margin'] = monthly_trends['Net_Profit'] / monthly_trends['Revenue_Total']
                
                # Create a month-over-month change heatmap
                monthly_trends['Revenue_MoM'] = monthly_trends['Revenue_Total'].pct_change()
                monthly_trends['Profit_MoM'] = monthly_trends['Net_Profit'].pct_change()
                monthly_trends['Margin_MoM'] = monthly_trends['Profit_Margin'].pct_change()
                
                # Drop the first row which has NaN MoM values
                heatmap_data = monthly_trends.iloc[1:].copy()
                
                # Create a pivot table for the heatmap
                heatmap_metrics = ['Revenue_MoM', 'Profit_MoM', 'Margin_MoM']
                heatmap_df = pd.DataFrame({
                    'Month': heatmap_data['Month'].tolist() * len(heatmap_metrics),
                    'Metric': ['Revenue Change'] * len(heatmap_data) + ['Profit Change'] * len(heatmap_data) + ['Margin Change'] * len(heatmap_data),
                    'Value': heatmap_data['Revenue_MoM'].tolist() + heatmap_data['Profit_MoM'].tolist() + heatmap_data['Margin_MoM'].tolist()
                })
                
                # Create heatmap
                if len(heatmap_df) > 0:
                    fig = px.imshow(
                        heatmap_df.pivot(index='Metric', columns='Month', values='Value'),
                        text_auto=False, # Turn off automatic text
                        color_continuous_scale='RdYlGn',
                        title='Month-over-Month Changes',
                        labels=dict(x='Month', y='Metric', color='Change'),
                        aspect='auto'
                    )
                    
                    # Add custom text formatting
                    fig.update_traces(texttemplate='%{z:.1%}', textfont={"size": 12})
                    
                    fig.update_layout(
                        coloraxis_colorbar=dict(
                            title='Change',
                            tickformat='.0%'
                        ),
                        margin=dict(l=40, r=40, t=50, b=100),
                        height=300
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Add explanation for month-over-month calculations
                    st.markdown("""
                    <div style="background-color: #f8fafc; padding: 12px; border-radius: 6px; margin-top: 10px; font-size: 0.8rem;">
                        <strong>How Month-over-Month Changes are Calculated:</strong><br>
                        For each metric in each month: (Current Month Value - Previous Month Value) ÷ Previous Month Value<br>
                        <em>Example: If Revenue was $10,000 in April and $12,000 in May, the MoM change would be +20%</em>
                    </div>
                    """, unsafe_allow_html=True)

    # 5. Enhanced Strategic Recommendations with more detailed insights
    st.markdown("### 5. Business Intelligence & Strategic Recommendations")
    
    # Create actionable insights and recommendations based on the data
    insights = []
    
    # Client concentration insights
    top_3_revenue_share = client_metrics.head(3)['Revenue_Share'].sum()
    if top_3_revenue_share > 0.5:
        insights.append({
            'category': 'Client Concentration',
            'risk_level': 'High' if top_3_revenue_share > 0.7 else 'Medium',
            'insight': f"Top 3 clients account for {top_3_revenue_share:.1%} of revenue",
            'recommendation': "Diversify client base to reduce dependency risk. Consider targeted business development efforts to acquire new mid-size clients.",
            'icon': '⚠️',
            'color': '#f97316' if top_3_revenue_share > 0.7 else '#fbbf24'
        })
    
    # Low margin clients
    low_margin_clients_count = client_metrics[client_metrics['Profit_Margin'] < 0.1].shape[0]
    if low_margin_clients_count > 0:
        insights.append({
            'category': 'Profit Margins',
            'risk_level': 'Medium',
            'insight': f"{low_margin_clients_count} clients have profit margins below 10%",
            'recommendation': "Review pricing strategy and cost structure for low-margin clients. Consider implementing minimum margin thresholds for new contracts.",
            'icon': '💡',
            'color': '#10b981'
        })
    
    # Revenue stream diversification
    if revenue_streams_data:
        dominant_stream = max(revenue_streams_data.items(), key=lambda x: x[1])
        dominant_stream_pct = dominant_stream[1] / total_stream_revenue
        if dominant_stream_pct > 0.4:
            insights.append({
                'category': 'Revenue Mix',
                'risk_level': 'Medium' if dominant_stream_pct > 0.6 else 'Low',
                'insight': f"{dominant_stream[0]} accounts for {dominant_stream_pct:.1%} of revenue",
                'recommendation': f"Expand other revenue streams beyond {dominant_stream[0]}. Develop marketing and sales strategies to promote underrepresented service lines.",
                'icon': '🔄',
                'color': '#3b82f6'
            })
    
    # Seasonal patterns if temporal data is available
    if 'Service_Month' in df.columns and len(monthly_trends) > 6:
        # Look for seasonality in the data
        monthly_trends['Month_Num'] = monthly_trends['Service_Month'].dt.month
        monthly_averages = monthly_trends.groupby('Month_Num')['Revenue_Total'].mean().reset_index()
        max_month = monthly_averages.loc[monthly_averages['Revenue_Total'].idxmax(), 'Month_Num']
        min_month = monthly_averages.loc[monthly_averages['Revenue_Total'].idxmin(), 'Month_Num']
        
        # Convert month numbers to names
        month_names = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
            7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }
        
        insights.append({
            'category': 'Seasonality',
            'risk_level': 'Info',
            'insight': f"Highest revenue month is typically {month_names[max_month]}, lowest is {month_names[min_month]}",
            'recommendation': f"Plan resource allocation accordingly. Consider promotional campaigns during {month_names[min_month]} to boost revenue in the low season.",
            'icon': '📅',
            'color': '#8b5cf6'
        })
    
    # Display insights
    for insight in insights:
        st.markdown(f"""
        <div style="background-color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 5px solid {insight['color']}; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h4 style="color: #1f2937; margin: 0;">{insight['icon']} {insight['category']}</h4>
                <span style="font-size: 0.8rem; padding: 3px 8px; border-radius: 12px; background-color: {insight['color']}; color: white;">{insight['risk_level']}</span>
            </div>
            <p style="color: #4b5563; margin: 0 0 10px 0;"><strong>Finding:</strong> {insight['insight']}</p>
            <p style="color: #4b5563; margin: 0;"><strong>Recommendation:</strong> {insight['recommendation']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Add resource allocation optimization if we have client and revenue data
    if 'Client' in df.columns and client_metrics.shape[0] >= 5:
        st.markdown("### 6. Resource Allocation Optimization")
        
        # Create a table with strategic focus areas
        focus_areas = []
        
        # Stars - high revenue, high margin
        stars = client_metrics[(client_metrics['Revenue_Total'] > client_metrics['Revenue_Total'].median()) & 
                               (client_metrics['Profit_Margin'] > client_metrics['Profit_Margin'].median())]
        if not stars.empty:
            focus_areas.append({
                'category': 'Key Accounts (Stars)',
                'clients': ', '.join(stars.head(3)['Client'].tolist()),
                'strategy': 'Protect and grow these accounts. Assign top account managers and ensure excellent service delivery.',
                'priority': 'High',
                'color': '#15803d'  # Green
            })
        
        # Growth potential - low revenue, high margin
        growth = client_metrics[(client_metrics['Revenue_Total'] <= client_metrics['Revenue_Total'].median()) & 
                              (client_metrics['Profit_Margin'] > client_metrics['Profit_Margin'].median())]
        if not growth.empty:
            focus_areas.append({
                'category': 'Growth Opportunities',
                'clients': ', '.join(growth.head(3)['Client'].tolist()),
                'strategy': 'Invest in expanding these relationships. Identify cross-selling and upselling opportunities.',
                'priority': 'Medium-High',
                'color': '#0284c7'  # Blue
            })
        
        # High revenue, low margin
        improve = client_metrics[(client_metrics['Revenue_Total'] > client_metrics['Revenue_Total'].median()) & 
                               (client_metrics['Profit_Margin'] <= client_metrics['Profit_Margin'].median())]
        if not improve.empty:
            focus_areas.append({
                'category': 'Margin Improvement Targets',
                'clients': ', '.join(improve.head(3)['Client'].tolist()),
                'strategy': 'Review cost structure and pricing. Identify efficiency opportunities or contract renegotiation.',
                'priority': 'Medium',
                'color': '#f59e0b'  # Yellow/Orange
            })
        
        # Low revenue, low margin
        evaluate = client_metrics[(client_metrics['Revenue_Total'] <= client_metrics['Revenue_Total'].median()) & 
                                (client_metrics['Profit_Margin'] <= client_metrics['Profit_Margin'].median())]
        if not evaluate.empty:
            focus_areas.append({
                'category': 'Relationship Evaluation',
                'clients': ', '.join(evaluate.head(3)['Client'].tolist()),
                'strategy': 'Evaluate relationship value. Consider restructuring or potentially phasing out if improvements cannot be made.',
                'priority': 'Low-Medium',
                'color': '#dc2626'  # Red
            })
        
        # Display focus areas
        for area in focus_areas:
            st.markdown(f"""
            <div style="background-color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 5px solid {area['color']}; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <h4 style="color: #1f2937; margin: 0;">{area['category']}</h4>
                    <span style="font-size: 0.8rem; padding: 3px 8px; border-radius: 12px; background-color: {area['color']}; color: white;">{area['priority']} Priority</span>
                </div>
                <p style="color: #4b5563; margin: 0 0 10px 0;"><strong>Key Clients:</strong> {area['clients']}</p>
                <p style="color: #4b5563; margin: 0;"><strong>Strategy:</strong> {area['strategy']}</p>
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
        if 'ClientCompanyName' in df.columns:
            # Handle case where ClientCompanyName might contain lists
            client_values = set()
            for val in df['ClientCompanyName']:
                if isinstance(val, list):
                    # If it's a list, add each item individually
                    for client in val:
                        client_values.add(str(client))
                else:
                    # Otherwise, just add the value as a string
                    client_values.add(str(val))
            total_clients = len(client_values)
        else:
            total_clients = 0
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
            # Handle case where ClientCompanyName might contain lists
            client_values = set()
            for val in df['ClientCompanyName']:
                if isinstance(val, list):
                    # If it's a list, add each item individually
                    for client in val:
                        client_values.add(str(client))
                else:
                    # Otherwise, just add the value as a string
                    client_values.add(str(val))
            # Get unique values and sort
            client_options = ["All"] + sorted(client_values)
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

def safe_update_layout(fig, **kwargs):
    """
    Helper function to safely update plotly figure layout.
    Works around potential compatibility issues between different environments.
    """
    try:
        # Convert all nested dicts to use string keys
        layout_params = {}
        for key, value in kwargs.items():
            if isinstance(value, dict):
                layout_params[key] = {str(k): v for k, v in value.items()}
            else:
                layout_params[key] = value
                
        fig.update_layout(**layout_params)
    except Exception as e:
        st.warning(f"Note: Chart layout couldn't be fully optimized. {str(e)}")
        # Apply minimal safe layout
        fig.update_layout(height=kwargs.get('height', 500))
    
    return fig

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
            # Handle case where Client column might contain lists
            client_values = set()
            for val in st.session_state.pnl_data['Client']:
                if isinstance(val, list):
                    # If it's a list, add each item individually
                    for client in val:
                        client_values.add(str(client))
                else:
                    # Otherwise, just add the value as a string
                    client_values.add(str(val))
            # Get unique values and sort
            client_options = sorted(client_values)
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
            # Handle case where Site_Location contains lists
            site_values = set()
            for val in st.session_state.pnl_data['Site_Location']:
                if isinstance(val, list):
                    # If it's a list, add each item individually
                    for site in val:
                        site_values.add(str(site))
                else:
                    # Otherwise, just add the value as a string
                    site_values.add(str(val))
            # Get unique values and sort
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
                    # Handle case where Service_Month might contain lists
                    month_values = []
                    for val in st.session_state.pnl_data['Service_Month']:
                        if isinstance(val, list):
                            # If it's a list, add each item individually
                            for month in val:
                                month_values.append(month)
                        else:
                            # Otherwise, just add the value
                            month_values.append(val)
                    # Get unique values and sort
                    month_options = ["All"] + sorted(set(month_values))
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
                    # Handle case where ProjectName might contain lists
                    project_values = []
                    for val in st.session_state.sow_data['ProjectName']:
                        if isinstance(val, list):
                            # If it's a list, add each item individually
                            for project in val:
                                project_values.append(str(project))
                        else:
                            # Otherwise, just add the value as a string
                            project_values.append(str(val))
                    # Get unique values and sort
                    project_options = ["All"] + sorted(set(project_values))
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