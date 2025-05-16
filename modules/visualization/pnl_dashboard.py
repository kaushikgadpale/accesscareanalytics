import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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
        
        client_profit['Profit_Margin'] = client_profit['Net_Profit'] / client_profit['Revenue_Total']
        client_profit['Profit_Per_Day'] = client_profit['Net_Profit'] / client_profit['Service_Days']
        
        fig = px.bar(
            client_profit.sort_values('Net_Profit', ascending=False).head(10),
            x='Client',
            y='Net_Profit',
            title='Top 10 Clients by Net Profit',
            color='Profit_Margin',
            color_continuous_scale='RdYlGn',
            text_auto='$.2s'
        )
        
        fig.update_traces(texttemplate='${text:,.2f}', textposition='outside')
        fig.update_layout(
            xaxis_title="Client",
            yaxis_title="Net Profit ($)",
            coloraxis_colorbar=dict(title="Profit Margin"),
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
        - Most profitable client: **{top_client['Client']}** with ${top_client['Net_Profit']:,.2f} net profit ({top_client['Profit_Margin']:.1%} margin)
        """)
        
        if bottom_client is not None:
            st.markdown(f"""
            - Attention needed: **{bottom_client['Client']}** is showing a loss of ${abs(bottom_client['Net_Profit']):,.2f}
            """)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Time Series
    if 'Service_Month' in df.columns:
        st.subheader("Monthly Financial Performance")
        
        # Add explanation for monthly performance
        st.markdown("""
        <div style="background-color: #fff4e6; padding: 10px; border-left: 4px solid #fd7e14; border-radius: 3px; margin-bottom: 15px;">
            This chart shows your financial performance over time. Track revenue, expenses, and profit trends to identify 
            seasonal patterns and business growth. The line represents net profit, while bars show revenue and expenses.
        </div>
        """, unsafe_allow_html=True)
        
        monthly_performance = df.groupby(pd.Grouper(key='Service_Month', freq='ME')).agg({
            'Revenue_Total': 'sum',
            'Expense_COGS_Total': 'sum',
            'Net_Profit': 'sum'
        }).reset_index()
        
        monthly_performance['Month'] = monthly_performance['Service_Month'].dt.strftime('%b %Y')
        monthly_performance['Profit_Margin'] = monthly_performance['Net_Profit'] / monthly_performance['Revenue_Total']
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=monthly_performance['Month'],
            y=monthly_performance['Revenue_Total'],
            name='Revenue',
            marker_color='rgb(55, 83, 109)'
        ))
        
        fig.add_trace(go.Bar(
            x=monthly_performance['Month'],
            y=monthly_performance['Expense_COGS_Total'],
            name='Expenses',
            marker_color='rgb(219, 64, 82)'
        ))
        
        fig.add_trace(go.Scatter(
            x=monthly_performance['Month'],
            y=monthly_performance['Net_Profit'],
            name='Net Profit',
            line=dict(color='rgb(26, 118, 255)', width=4)
        ))
        
        fig.update_layout(
            title='Monthly Financial Performance',
            barmode='group',
            xaxis_title="Month",
            yaxis_title="Amount ($)",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(t=50, b=100, l=20, r=20),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add trend analysis
        if len(monthly_performance) > 1:
            first_month = monthly_performance.iloc[0]
            last_month = monthly_performance.iloc[-1]
            profit_change = last_month['Net_Profit'] - first_month['Net_Profit']
            revenue_change = last_month['Revenue_Total'] - first_month['Revenue_Total']
            
            profit_trend_color = "#12b886" if profit_change >= 0 else "#fa5252"
            revenue_trend_color = "#12b886" if revenue_change >= 0 else "#fa5252"
            
            st.markdown(f"""
            <div style="background-color: #fff3bf; padding: 10px; border-radius: 3px; margin-top: 10px;">
                <strong>📈 Trend Analysis:</strong>
                <ul>
                    <li>Net Profit has <span style="color: {profit_trend_color}; font-weight: bold;">
                        {"increased" if profit_change >= 0 else "decreased"} by ${abs(profit_change):,.2f}
                    </span> from {first_month['Month']} to {last_month['Month']}.</li>
                    <li>Revenue has <span style="color: {revenue_trend_color}; font-weight: bold;">
                        {"increased" if revenue_change >= 0 else "decreased"} by ${abs(revenue_change):,.2f}
                    </span> over the same period.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
    
    # Location Performance
    if 'Site_Location' in df.columns and 'Net_Profit' in df.columns:
        st.subheader("Location Profitability")
        
        # Add explanation for location profitability
        st.markdown("""
        <div style="background-color: #f3f0ff; padding: 10px; border-left: 4px solid #7950f2; border-radius: 3px; margin-bottom: 15px;">
            This scatter plot shows the relationship between revenue and profit across different locations. 
            The size of each bubble represents expenses, and the color indicates profit margin. 
            Locations in the upper right quadrant with green coloring are your best performers.
        </div>
        """, unsafe_allow_html=True)
        
        # Debug information for Site_Location
        with st.expander("Debug Site_Location", expanded=False):
            st.write("Site_Location values types:", [type(x) for x in df['Site_Location'].head(10)])
            st.write("First few Site_Location values:", df['Site_Location'].head(10).tolist())
        
        # Ensure Site_Location is properly formatted for explode
        # If it's not already a list type, convert single values to lists
        df['Site_Location_List'] = df['Site_Location'].apply(
            lambda x: x if isinstance(x, list) else [str(x) if x is not None else "Unknown"]
        )
        
        # Now safely explode the list column
        try:
            location_profit = df.explode('Site_Location_List').groupby('Site_Location_List').agg({
                'Revenue_Total': 'sum',
                'Expense_COGS_Total': 'sum',
                'Net_Profit': 'sum'
            }).reset_index()
            
            location_profit['Profit_Margin'] = location_profit['Net_Profit'] / location_profit['Revenue_Total']
            
            fig = px.scatter(
                location_profit,
                x='Revenue_Total',
                y='Net_Profit',
                size='Expense_COGS_Total',
                color='Profit_Margin',
                hover_name='Site_Location_List',
                color_continuous_scale='RdYlGn',
                title='Location Profitability Analysis'
            )
            
            fig.update_layout(
                xaxis_title="Total Revenue ($)",
                yaxis_title="Net Profit ($)",
                coloraxis_colorbar=dict(title="Profit Margin"),
                margin=dict(t=50, b=50, l=20, r=20),
                height=500
            )
            
            # Add reference line for breakeven
            fig.add_shape(
                type='line',
                x0=0,
                y0=0,
                x1=location_profit['Revenue_Total'].max() * 1.1,
                y1=0,
                line=dict(color='red', dash='dash')
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add insights about location profitability
            top_location = location_profit.sort_values('Net_Profit', ascending=False).iloc[0]
            unprofitable_count = len(location_profit[location_profit['Net_Profit'] < 0])
            
            st.markdown(f"""
            <div style="background-color: #fff3bf; padding: 10px; border-radius: 3px; margin-top: 10px;">
                <strong>📊 Insights:</strong>
                <ul>
                    <li>Most profitable location: <strong>{top_location['Site_Location_List']}</strong> with ${top_location['Net_Profit']:,.2f} net profit</li>
                    <li>{unprofitable_count} locations are currently operating at a loss (below the red dashed line)</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error processing location data: {str(e)}")
            st.write("Please check the format of your Site_Location data.") 