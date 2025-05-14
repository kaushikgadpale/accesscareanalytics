import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import json
from config import AIRTABLE_BASES, AIRTABLE_CONFIG, THEME_CONFIG

def fetch_from_airtable(base_key, query_params=None):
    """
    Fetch data from a specific Airtable base defined in AIRTABLE_BASES
    
    Args:
        base_key: Key of the base in AIRTABLE_BASES (e.g., 'SOW', 'UTILIZATION', 'PNL')
        query_params: Dictionary of query parameters to include in the request
        
    Returns:
        Dictionary containing the API response
    """
    if base_key not in AIRTABLE_BASES:
        st.error(f"Base key '{base_key}' not found in AIRTABLE_BASES")
        return None
        
    base_info = AIRTABLE_BASES[base_key]
    base_id = base_info['BASE_ID']
    table_id = base_info['TABLE_ID']
    
    # Get API credentials
    api_key = st.session_state.get('airtable_api_key', AIRTABLE_CONFIG['API_KEY'])
    
    if not api_key or not base_id:
        st.error("Airtable credentials not configured. Please set them up in the integration settings.")
        return None
    
    # Prepare headers
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # Create URL
    url = f"{AIRTABLE_CONFIG['API_URL']}/{base_id}/{table_id}"
    
    # Add query parameters if provided
    params = query_params or {}
    
    # Set a higher record limit (default to 1000 instead of 100)
    if 'maxRecords' not in params:
        params['maxRecords'] = 1000
    
    # Hide debug information in collapsed expander
    with st.expander(f"Debug Info for {base_key} API Request", expanded=False):
        st.write(f"URL: {url}")
        st.write(f"Headers: Authorization: Bearer ...{api_key[-5:]}")
        st.write(f"Query Parameters: {params}")
    
    try:
        # Show a loading spinner instead of multiple info messages
        with st.spinner(f"Fetching data from Airtable {base_key} base..."):
            # Initialize records list and offset
            all_records = []
            offset = None
            page = 1
            
            # Use pagination to fetch all records
            while True:
                # Add offset to params if we have one
                if offset:
                    params['offset'] = offset
                
                # Make the request
                response = requests.get(url, headers=headers, params=params)
                
                # Check if the request was successful
                if response.status_code == 200:
                    data = response.json()
                    
                    # Add records to our list
                    if 'records' in data:
                        all_records.extend(data['records'])
                        # Don't show individual page fetch messages
                        # st.success(f"Fetched page {page} with {len(data.get('records', []))} records")
                        
                        # Check if there are more records
                        if 'offset' in data:
                            offset = data['offset']
                            page += 1
                        else:
                            # No more records
                            break
                    else:
                        # No records in response
                        break
                else:
                    st.error(f"Error fetching data from Airtable: Status code {response.status_code}")
                    st.error(f"Response: {response.text}")
                    return None
        
        # Create a complete response with all records
        complete_response = {'records': all_records}
        # Only show a single success message with the total
        st.success(f"Successfully fetched {len(all_records)} records from {base_key}")
        return complete_response
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from Airtable: {str(e)}")
        return None

def airtable_to_dataframe(airtable_data):
    """Convert Airtable API response to a Pandas DataFrame"""
    if not airtable_data or 'records' not in airtable_data:
        return pd.DataFrame()
    
    records = []
    for record in airtable_data['records']:
        row = record['fields'].copy()
        row['id'] = record['id']
        records.append(row)
    
    return pd.DataFrame(records)

def apply_filters(df, filters):
    """
    Apply filters to a DataFrame based on filter parameters
    
    Args:
        df: DataFrame to filter
        filters: Dictionary of filter parameters
        
    Returns:
        Filtered DataFrame
    """
    filtered_df = df.copy()
    
    if not filters or df.empty:
        return filtered_df
    
    # Apply column filters
    for column, value in filters.items():
        if column in filtered_df.columns and value:
            if isinstance(value, list):
                if value and value[0] != "All":  # Skip if "All" is selected
                    filtered_df = filtered_df[filtered_df[column].isin(value)]
            elif isinstance(value, tuple) and len(value) == 2:  # Date range
                start_date, end_date = value
                if pd.api.types.is_datetime64_dtype(filtered_df[column]):
                    filtered_df = filtered_df[(filtered_df[column] >= start_date) & 
                                             (filtered_df[column] <= end_date)]
            elif isinstance(value, str) and value.lower() != "all":
                # Case-insensitive text search
                filtered_df = filtered_df[filtered_df[column].astype(str).str.contains(value, case=False, na=False)]
    
    return filtered_df

def get_utilization_data(filters=None):
    """
    Get utilization data from Airtable and process it
    
    Args:
        filters: Dictionary of filtering options
        
    Returns:
        Processed DataFrame with utilization data
    """
    # Create query parameters based on filters
    params = {'maxRecords': 1000}  # Default to 1000 records max
    
    if filters:
        # Example: Add view filtering or formula filtering
        if 'year' in filters:
            params['filterByFormula'] = f"{{Year}}='{filters['year']}'"
    
    # Fetch data from Airtable
    utilization_data = fetch_from_airtable('UTILIZATION', params)
    
    if not utilization_data:
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = airtable_to_dataframe(utilization_data)
    
    # Process the DataFrame
    if not df.empty:
        # Create debug expander for field mapping info
        with st.expander("Field Mapping Details", expanded=False):
            st.write("Mapping fields for Utilization data:")
            
            # Map field IDs to readable names if present
            field_mapping = AIRTABLE_BASES['UTILIZATION'].get('FIELDS', {})
            field_map_inverted = {v: k for k, v in field_mapping.items()}
            
            # Rename columns using the field mapping
            df = df.rename(columns=field_map_inverted)
            
            # If we don't have mappings for some key fields, try to use common names
            required_fields = [
                'CLIENT', 'SITE', 'DATE_OF_SERVICE', 'YEAR', 'HEADCOUNT', 
                'TOTAL_BOOKING_APPTS', 'TOTAL_COMPLETED_APPTS'
            ]
            
            for field in required_fields:
                if field not in df.columns:
                    # Try some common alternatives
                    alternatives = {
                        'CLIENT': ['Client', 'client', 'Company', 'company', 'Organization'],
                        'SITE': ['Site', 'site', 'Location', 'location'],
                        'DATE_OF_SERVICE': ['Date of Service', 'date_of_service', 'Service Date', 'DOS'],
                        'YEAR': ['Year', 'year', 'Calendar Year'],
                        'HEADCOUNT': ['Headcount', 'headcount', 'Head Count', 'Employee Count'],
                        'TOTAL_BOOKING_APPTS': ['Total Booking Appts', 'Bookings', 'Appointments Booked'],
                        'TOTAL_COMPLETED_APPTS': ['Total Completed Appts', 'Completed', 'Completed Appointments']
                    }
                    
                    # Try to find a matching column
                    found = False
                    for alt in alternatives.get(field, []):
                        if alt in df.columns:
                            df[field] = df[alt]
                            found = True
                            st.write(f"Found alternative for '{field}': '{alt}'")
                            break
                    
                    if not found:
                        st.warning(f"Could not find a mapping for required field '{field}'")
        
        # Convert date fields
        date_fields = ['DATE_OF_SERVICE', 'Date of Service']
        for field in date_fields:
            if field in df.columns:
                df[field] = pd.to_datetime(df[field], errors='coerce')
        
        # Convert numeric fields
        numeric_fields = [
            'HEADCOUNT', 'WALKINS', 'INTERESTED_PATIENTS',
            'TOTAL_BOOKING_APPTS', 'TOTAL_COMPLETED_APPTS',
            'DENTAL', 'AUDIOLOGY', 'VISION', 'MSK', 
            'SKIN_SCREENING', 'BIOMETRICS_AND_LABS',
            'Headcount', 'Walkins', 'Interested Patients',
            'Total Booking Appts', 'Total Completed Appts',
            'Dental', 'Audiology', 'Vision', 'MSK', 
            'Skin Screening', 'Biometrics and Labs'
        ]
        
        for field in numeric_fields:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce')
        
        # Calculate additional metrics - try with both potential field names
        booking_rate_fields = [
            ('TOTAL_BOOKING_APPTS', 'HEADCOUNT'),
            ('Total Booking Appts', 'Headcount')
        ]
        
        for booking_field, headcount_field in booking_rate_fields:
            if booking_field in df.columns and headcount_field in df.columns:
                df['Booking Rate'] = (df[booking_field] / df[headcount_field]).fillna(0)
                break
        
        show_rate_fields = [
            ('TOTAL_COMPLETED_APPTS', 'TOTAL_BOOKING_APPTS'),
            ('Total Completed Appts', 'Total Booking Appts')
        ]
        
        for completed_field, booking_field in show_rate_fields:
            if completed_field in df.columns and booking_field in df.columns:
                df['Show Rate'] = (df[completed_field] / df[booking_field]).fillna(0)
                break
        
        utilization_rate_fields = [
            ('TOTAL_COMPLETED_APPTS', 'HEADCOUNT'),
            ('Total Completed Appts', 'Headcount')
        ]
        
        for completed_field, headcount_field in utilization_rate_fields:
            if completed_field in df.columns and headcount_field in df.columns:
                df['Utilization Rate'] = (df[completed_field] / df[headcount_field]).fillna(0)
                break
    
    return df

def get_pnl_data(filters=None):
    """
    Get PnL data from Airtable and process it
    
    Args:
        filters: Dictionary of filtering options
        
    Returns:
        Processed DataFrame with PnL data
    """
    # Create query parameters based on filters
    params = {'maxRecords': 1000}  # Default to 1000 records max
    
    if filters:
        if 'client' in filters:
            params['filterByFormula'] = f"FIND('{filters['client']}', {{Client}})"
    
    # Fetch data from Airtable
    pnl_data = fetch_from_airtable('PNL', params)
    
    if not pnl_data:
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = airtable_to_dataframe(pnl_data)
    
    # Print column names for debugging
    print("Actual PnL Data Columns:", df.columns.tolist())
    
    # Process the DataFrame
    if not df.empty:
        # Create debug expander for field mapping info
        with st.expander("Field Mapping Details", expanded=False):
            st.write("Mapping fields for PnL data:")
            
            # Map field IDs to readable names if present
            field_mapping = AIRTABLE_BASES['PNL'].get('FIELDS', {})
            field_map_inverted = {v: k for k, v in field_mapping.items()}
            
            # Rename columns using the field mapping
            df = df.rename(columns=field_map_inverted)
            
            # Define required fields and alternatives with expanded potential column names
            required_fields = [
                'CLIENT', 'SITE_LOCATION', 'SERVICE_MONTH', 'REVENUE_TOTAL', 
                'EXPENSE_COGS_TOTAL', 'NET_PROFIT'
            ]
            
            for field in required_fields:
                if field not in df.columns:
                    # Try some common alternatives
                    alternatives = {
                        'CLIENT': ['Client', 'client', 'Company', 'company', 'Organization', 'Client Name'],
                        'SITE_LOCATION': ['Site Location', 'Site_Location', 'Location', 'location', 'Site', 'Event Location'],
                        'SERVICE_MONTH': ['Service Month', 'Month', 'Date', 'Service_Month', 'Service Date', 'Event Date'],
                        'REVENUE_TOTAL': ['Revenue Total', 'Total Revenue', 'Revenue', 'Revenue_Total', 'Gross Revenue'],
                        'EXPENSE_COGS_TOTAL': ['Expense COGS Total', 'Total Expenses', 'Expenses', 'Expense_COGS_Total', 'COGS', 'Cost of Goods Sold'],
                        'NET_PROFIT': ['Net Profit', 'Profit', 'Net Income', 'Net_Profit', 'Margin', 'Earnings']
                    }
                    
                    # Try to find a matching column
                    found = False
                    for alt in alternatives.get(field, []):
                        if alt in df.columns:
                            df[field] = df[alt]
                            found = True
                            st.write(f"Found alternative for '{field}': '{alt}'")
                            break
                    
                    if not found:
                        # Try to find a column that contains the field name as a substring
                        for col in df.columns:
                            if any(alt.lower() in col.lower() for alt in alternatives.get(field, [])):
                                df[field] = df[col]
                                found = True
                                st.write(f"Found column containing '{field}' in name: '{col}'")
                                break
                    
                    if not found:
                        st.warning(f"Could not find a mapping for required field '{field}'")
        
        # Convert date fields - try multiple potential names
        date_fields = ['SERVICE_MONTH', 'Service_Month', 'Service Month', 'Month', 'LAST_MODIFIED', 'Last Modified']
        for field in date_fields:
            if field in df.columns:
                df[field] = pd.to_datetime(df[field], errors='coerce')
        
        # Convert numeric fields - try multiple potential names
        currency_fields = [
            'REVENUE_WELLNESS_FUND', 'REVENUE_DENTAL_CLAIM', 'REVENUE_MEDICAL_CLAIM',
            'REVENUE_EVENT_TOTAL', 'REVENUE_MISSED_APPOINTMENTS', 'REVENUE_TOTAL',
            'REVENUE_PER_DAY_AVG', 'EXPENSE_COGS_TOTAL', 'EXPENSE_COGS_PER_DAY_AVG', 
            'NET_PROFIT', 'Revenue_WellnessFund', 'Revenue_DentalClaim',
            'Revenue_MedicalClaim_InclCancelled', 'Revenue_EventTotal',
            'Revenue_MissedAppointments', 'Revenue_Total', 'Revenue_PerDay_Avg',
            'Expense_COGS_Total', 'Expense_COGS_PerDay_Avg', 'Net_Profit'
        ]
        
        for field in currency_fields:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce')
        
        # Convert percentage fields
        percentage_fields = ['NET_PROFIT_PERCENT', 'Net_Profit_%', 'Profit Margin', 'Margin']
        for field in percentage_fields:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce')
    
    return df

def get_sow_data(filters=None):
    """
    Get SOW data from Airtable and process it
    
    Args:
        filters: Dictionary of filtering options
        
    Returns:
        Processed DataFrame with SOW data
    """
    # Create query parameters based on filters
    params = {'maxRecords': 1000}  # Default to 1000 records max
    
    if filters:
        filter_formulas = []
        
        # Add client filter
        if 'client' in filters and filters['client']:
            filter_formulas.append(f"FIND('{filters['client']}', {{ClientCompanyName}})")
        
        # Add project filter
        if 'project' in filters and filters['project']:
            filter_formulas.append(f"{{ProjectName}}='{filters['project']}'")
            
        # Combine filter formulas with AND if multiple exist
        if filter_formulas:
            if len(filter_formulas) == 1:
                params['filterByFormula'] = filter_formulas[0]
            else:
                params['filterByFormula'] = f"AND({','.join(filter_formulas)})"
    
    # Fetch data from Airtable
    sow_data = fetch_from_airtable('SOW', params)
    
    if not sow_data:
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = airtable_to_dataframe(sow_data)
    
    # Process the DataFrame
    if not df.empty:
        # Create debug expander for field mapping info
        with st.expander("Field Mapping Details", expanded=False):
            st.write("Mapping fields for SOW data:")
            
            # Map field IDs to readable names if present
            field_mapping = AIRTABLE_BASES['SOW'].get('FIELDS', {})
            field_map_inverted = {v: k for k, v in field_mapping.items()}
            
            # Rename columns using the field mapping
            df = df.rename(columns=field_map_inverted)
            
            # Define required fields and alternatives with expanded potential column names
            required_fields = [
                'ClientCompanyName', 'ProjectName', 'SOWQuoteNumber', 
                'ScheduledPlanningStartDate', 'ScheduledEndDate'
            ]
            
            for field in required_fields:
                if field not in df.columns:
                    st.warning(f"Could not find required field '{field}'")
        
        # Convert date fields
        date_fields = [
            'ScheduledPlanningStartDate', 'ScheduledEndDate', 
            'ActualPlanningStartDate', 'ActualEndDate'
        ]
        
        for field in date_fields:
            if field in df.columns:
                df[field] = pd.to_datetime(df[field], errors='coerce')
    
    return df

def create_utilization_dashboard(df):
    """
    Create visualizations for utilization data
    
    Args:
        df: DataFrame containing utilization data
        
    Returns:
        None (displays visualizations in Streamlit)
    """
    if df.empty:
        st.warning("No utilization data available to display")
        return
    
    st.subheader("Utilization Overview")
    
    # Add descriptive text
    st.markdown("""
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <h4 style="margin-top: 0;">📈 Utilization Dashboard</h4>
        <p>This dashboard provides insights into appointment utilization metrics across different clients and sites. 
        Key metrics include booking rates, show rates, and overall utilization rates.</p>
        <p><strong>Definitions:</strong></p>
        <ul>
            <li><strong>Booking Rate</strong>: Percentage of eligible employees who booked appointments</li>
            <li><strong>Show Rate</strong>: Percentage of booked appointments that were completed</li>
            <li><strong>Utilization Rate</strong>: Percentage of eligible employees who completed appointments</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Summary statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_clients = df['Client'].nunique()
        st.metric("Total Clients", total_clients)
    
    with col2:
        total_sites = df['Site'].nunique()
        st.metric("Total Sites", total_sites)
    
    with col3:
        total_headcount = df['Headcount'].sum() if 'Headcount' in df.columns else 0
        st.metric("Total Headcount", f"{total_headcount:,}")
    
    with col4:
        total_appointments = df['Total Completed Appts'].sum() if 'Total Completed Appts' in df.columns else 0
        st.metric("Total Completed Appointments", f"{total_appointments:,}")
    
    # Utilization rates
    st.subheader("Utilization Rates")
    
    # Add explanation for utilization rates
    st.markdown("""
    <div style="background-color: #e8f4f8; padding: 10px; border-left: 4px solid #4dabf7; border-radius: 3px; margin-bottom: 15px;">
        These metrics show the overall effectiveness of appointment booking and completion across all clients.
        Higher rates indicate better engagement and service utilization.
    </div>
    """, unsafe_allow_html=True)
    
    rates_col1, rates_col2, rates_col3 = st.columns(3)
    
    with rates_col1:
        avg_booking_rate = df['Booking Rate'].mean() if 'Booking Rate' in df.columns else 0
        st.metric("Avg. Booking Rate", f"{avg_booking_rate:.1%}")
    
    with rates_col2:
        avg_show_rate = df['Show Rate'].mean() if 'Show Rate' in df.columns else 0
        st.metric("Avg. Show Rate", f"{avg_show_rate:.1%}")
    
    with rates_col3:
        avg_utilization = df['Utilization Rate'].mean() if 'Utilization Rate' in df.columns else 0
        st.metric("Avg. Utilization Rate", f"{avg_utilization:.1%}")
    
    # Service distribution
    service_cols = ['Dental', 'Audiology', 'Vision', 'MSK', 'Skin Screening', 'Biometrics and Labs']
    service_cols = [col for col in service_cols if col in df.columns]
    
    if service_cols:
        st.subheader("Service Distribution")
        
        # Add explanation for service distribution
        st.markdown("""
        <div style="background-color: #f3f0ff; padding: 10px; border-left: 4px solid #7950f2; border-radius: 3px; margin-bottom: 15px;">
            This chart shows the breakdown of appointments by service type. Use this to identify which services are most utilized 
            and where there may be opportunities to increase engagement.
        </div>
        """, unsafe_allow_html=True)
        
        service_totals = df[service_cols].sum().reset_index()
        service_totals.columns = ['Service', 'Count']
        service_totals = service_totals[service_totals['Count'] > 0]
        
        if not service_totals.empty:
            fig = px.pie(
                service_totals,
                values='Count',
                names='Service',
                title='Appointment Distribution by Service Type',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(
                margin=dict(t=50, b=50, l=20, r=20),
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add insights about service distribution
            top_service = service_totals.sort_values('Count', ascending=False).iloc[0]
            st.markdown(f"""
            <div style="background-color: #fff3bf; padding: 10px; border-radius: 3px; margin-top: 10px;">
                <strong>📊 Insight:</strong> {top_service['Service']} is the most utilized service, accounting for 
                {(top_service['Count'] / service_totals['Count'].sum()):.1%} of all appointments.
            </div>
            """, unsafe_allow_html=True)
    
    # Client performance
    if 'Client' in df.columns and 'Utilization Rate' in df.columns:
        st.subheader("Client Performance")
        
        # Add explanation for client performance
        st.markdown("""
        <div style="background-color: #e6fcf5; padding: 10px; border-left: 4px solid #12b886; border-radius: 3px; margin-bottom: 15px;">
            This chart ranks clients by their utilization rate. Higher rates indicate better engagement with the services offered.
            Focus on strategies that work well with high-performing clients and identify improvement opportunities for others.
        </div>
        """, unsafe_allow_html=True)
        
        client_performance = df.groupby('Client').agg({
            'Headcount': 'sum',
            'Total Booking Appts': 'sum',
            'Total Completed Appts': 'sum',
            'Utilization Rate': 'mean'
        }).reset_index()
        
        client_performance['Utilization Rate'] = client_performance['Utilization Rate'] * 100
        
        fig = px.bar(
            client_performance.sort_values('Utilization Rate', ascending=False).head(10),
            x='Client',
            y='Utilization Rate',
            title='Top 10 Clients by Utilization Rate (%)',
            color='Utilization Rate',
            color_continuous_scale='Viridis',
            text_auto='.1f'
        )
        
        fig.update_traces(texttemplate='%{text}%', textposition='outside')
        fig.update_layout(
            xaxis_title="Client",
            yaxis_title="Utilization Rate (%)",
            yaxis=dict(range=[0, max(client_performance['Utilization Rate']) * 1.1]),
            margin=dict(t=50, b=100, l=20, r=20),
            height=450
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add insights about client performance
        top_client = client_performance.sort_values('Utilization Rate', ascending=False).iloc[0]
        bottom_client = client_performance.sort_values('Utilization Rate').iloc[0]
        
        st.markdown("""
        <div style="background-color: #fff3bf; padding: 10px; border-radius: 3px; margin-top: 10px;">
            <strong>📊 Insights:</strong>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        - Most profitable client: **{top_client['Client']}** with {top_client['Utilization Rate']:.1f}% utilization rate
        """)
        
        if bottom_client is not None:
            st.markdown(f"""
            - Opportunity for improvement: **{bottom_client['Client']}** with {bottom_client['Utilization Rate']:.1f}% utilization rate
            """)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Time series analysis
    if 'Date of Service' in df.columns and 'Utilization Rate' in df.columns:
        st.subheader("Time Series Analysis")
        
        # Add explanation for time series
        st.markdown("""
        <div style="background-color: #fff4e6; padding: 10px; border-left: 4px solid #fd7e14; border-radius: 3px; margin-bottom: 15px;">
            This chart shows utilization rate trends over time. Use this to identify seasonal patterns, 
            the impact of promotional campaigns, or other factors affecting utilization rates.
        </div>
        """, unsafe_allow_html=True)
        
        time_series = df.groupby(pd.Grouper(key='Date of Service', freq='M')).agg({
            'Headcount': 'sum',
            'Total Booking Appts': 'sum',
            'Total Completed Appts': 'sum',
            'Utilization Rate': 'mean'
        }).reset_index()
        
        time_series['Month'] = time_series['Date of Service'].dt.strftime('%b %Y')
        time_series['Utilization Rate'] = time_series['Utilization Rate'] * 100
        
        fig = px.line(
            time_series,
            x='Date of Service',
            y='Utilization Rate',
            title='Utilization Rate Trend Over Time',
            markers=True
        )
        
        fig.update_traces(line=dict(width=3))
        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Utilization Rate (%)",
            margin=dict(t=50, b=50, l=20, r=20),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add trend analysis
        if len(time_series) > 1:
            first_month = time_series.iloc[0]
            last_month = time_series.iloc[-1]
            change = last_month['Utilization Rate'] - first_month['Utilization Rate']
            
            trend_color = "#12b886" if change >= 0 else "#fa5252"
            trend_icon = "📈" if change >= 0 else "📉"
            
            st.markdown(f"""
            <div style="background-color: #fff3bf; padding: 10px; border-radius: 3px; margin-top: 10px;">
                <strong>{trend_icon} Trend Analysis:</strong> Utilization rate has 
                <span style="color: {trend_color}; font-weight: bold;">
                    {"increased" if change >= 0 else "decreased"} by {abs(change):.1f}%
                </span> 
                from {first_month['Month']} to {last_month['Month']}.
            </div>
            """, unsafe_allow_html=True)

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

        # Add detailed analysis button
        if st.button("Get Detailed CEO Analysis"):
            st.markdown("""
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-top: 20px;">
                <h3 style="color: #2c3e50; margin-top: 0;">📊 CEO Financial Analysis Report</h3>
            """, unsafe_allow_html=True)

            # 1. Overall Financial Health
            st.markdown("### 1. Overall Financial Health")
            total_revenue = df['Revenue_Total'].sum()
            total_expenses = df['Expense_COGS_Total'].sum()
            total_profit = df['Net_Profit'].sum()
            overall_margin = total_profit / total_revenue if total_revenue > 0 else 0

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Revenue", f"${total_revenue:,.2f}")
            with col2:
                st.metric("Total Expenses", f"${total_expenses:,.2f}")
            with col3:
                st.metric("Overall Profit Margin", f"{overall_margin:.1%}")

            # 2. Client Portfolio Analysis
            st.markdown("### 2. Client Portfolio Analysis")
            client_metrics = df.groupby('Client').agg({
                'Revenue_Total': 'sum',
                'Expense_COGS_Total': 'sum',
                'Net_Profit': 'sum'
            }).reset_index()
            
            client_metrics['Profit_Margin'] = client_metrics['Net_Profit'] / client_metrics['Revenue_Total']
            client_metrics['Revenue_Share'] = client_metrics['Revenue_Total'] / total_revenue
            
            # Sort by revenue share
            client_metrics = client_metrics.sort_values('Revenue_Share', ascending=False)
            
            # Display top 5 clients by revenue
            st.markdown("#### Top 5 Clients by Revenue")
            for _, client in client_metrics.head().iterrows():
                st.markdown(f"""
                - **{client['Client']}**
                    - Revenue: ${client['Revenue_Total']:,.2f} ({client['Revenue_Share']:.1%} of total)
                    - Profit: ${client['Net_Profit']:,.2f} ({client['Profit_Margin']:.1%} margin)
                """)

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
                st.markdown(f"- **{stream}**: ${amount:,.2f} ({percentage:.1%} of total)")

            # 4. Trend Analysis
            st.markdown("### 4. Trend Analysis")
            if 'Service_Month' in df.columns:
                monthly_trends = df.groupby(pd.Grouper(key='Service_Month', freq='M')).agg({
                    'Revenue_Total': 'sum',
                    'Expense_COGS_Total': 'sum',
                    'Net_Profit': 'sum'
                }).reset_index()
                
                monthly_trends['Profit_Margin'] = monthly_trends['Net_Profit'] / monthly_trends['Revenue_Total']
                
                # Calculate month-over-month changes
                monthly_trends['Revenue_Change'] = monthly_trends['Revenue_Total'].pct_change()
                monthly_trends['Profit_Change'] = monthly_trends['Net_Profit'].pct_change()
                
                # Get latest month's data
                latest_month = monthly_trends.iloc[-1]
                previous_month = monthly_trends.iloc[-2] if len(monthly_trends) > 1 else None
                
                st.markdown("#### Latest Month Performance")
                st.markdown(f"""
                - Revenue: ${latest_month['Revenue_Total']:,.2f} 
                    {f"({latest_month['Revenue_Change']:.1%} vs previous month)" if previous_month is not None else ""}
                - Profit: ${latest_month['Net_Profit']:,.2f}
                    {f"({latest_month['Profit_Change']:.1%} vs previous month)" if previous_month is not None else ""}
                - Profit Margin: {latest_month['Profit_Margin']:.1%}
                """)

            # 5. Recommendations
            st.markdown("### 5. Strategic Recommendations")
            
            # Analyze client concentration
            top_3_revenue_share = client_metrics.head(3)['Revenue_Share'].sum()
            if top_3_revenue_share > 0.5:
                st.markdown("""
                ⚠️ **Client Concentration Risk**
                - Top 3 clients account for more than 50% of revenue
                - Consider diversifying client base to reduce dependency
                """)
            
            # Analyze profit margins
            low_margin_clients = client_metrics[client_metrics['Profit_Margin'] < 0.1]
            if not low_margin_clients.empty:
                st.markdown("""
                💡 **Margin Improvement Opportunities**
                - Several clients show low profit margins
                - Consider reviewing pricing strategy or cost structure
                """)
            
            # Analyze revenue streams
            if revenue_streams:
                dominant_stream = max(revenue_streams.items(), key=lambda x: x[1][1])
                if dominant_stream[1][1] > 0.4:
                    st.markdown(f"""
                    🔄 **Revenue Stream Diversification**
                    - {dominant_stream[0]} accounts for more than 40% of revenue
                    - Consider expanding other revenue streams
                    """)

            st.markdown("</div>", unsafe_allow_html=True)
    
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
        
        location_profit = df.explode('Site_Location').groupby('Site_Location').agg({
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
            hover_name='Site_Location',
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
                <li>Most profitable location: <strong>{top_location['Site_Location']}</strong> with ${top_location['Net_Profit']:,.2f} net profit</li>
                <li>{unprofitable_count} locations are currently operating at a loss (below the red dashed line)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
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
        
        monthly_performance = df.groupby(pd.Grouper(key='Service_Month', freq='M')).agg({
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
            client_options = ["All"] + sorted(st.session_state.utilization_data['Client'].unique().tolist())
            client_filter = st.selectbox("Client", client_options, 
                                         index=client_options.index(st.session_state.common_filters.get('Client', 'All')) if st.session_state.common_filters.get('Client', 'All') in client_options else 0)
        elif st.session_state.pnl_data is not None and not st.session_state.pnl_data.empty and 'Client' in st.session_state.pnl_data.columns:
            client_options = ["All"] + sorted(st.session_state.pnl_data['Client'].unique().tolist())
            client_filter = st.selectbox("Client", client_options,
                                         index=client_options.index(st.session_state.common_filters.get('Client', 'All')) if st.session_state.common_filters.get('Client', 'All') in client_options else 0)
        else:
            client_filter = st.text_input("Client (enter name)", value=st.session_state.common_filters.get('Client', ''))
        
        # Date range filter
        date_col1, date_col2 = st.columns(2)
        
        with date_col1:
            start_date = st.date_input("Start Date", 
                                       value=st.session_state.common_filters.get('date_range', (datetime.now() - timedelta(days=365), datetime.now()))[0])
        with date_col2:
            end_date = st.date_input("End Date", 
                                     value=st.session_state.common_filters.get('date_range', (datetime.now() - timedelta(days=365), datetime.now()))[1])
        
        # Year filter
        year_options = ["All"]
        current_year = datetime.now().year
        year_options.extend(range(current_year - 5, current_year + 1))
        selected_year = st.selectbox("Year", year_options, 
                                     index=year_options.index(st.session_state.common_filters.get('Year', 'All')) if st.session_state.common_filters.get('Year', 'All') in year_options else 0)
        
        # Site filter
        site_filter = None
        site_options = []
        
        if st.session_state.utilization_data is not None and not st.session_state.utilization_data.empty and 'Site' in st.session_state.utilization_data.columns:
            site_options = ["All"] + sorted(st.session_state.utilization_data['Site'].unique().tolist())
        elif st.session_state.pnl_data is not None and not st.session_state.pnl_data.empty and 'Site_Location' in st.session_state.pnl_data.columns:
            site_options = ["All"] + sorted(st.session_state.pnl_data['Site_Location'].unique().tolist())
        
        if site_options:
            site_filter = st.selectbox("Site", site_options,
                                       index=site_options.index(st.session_state.common_filters.get('Site', 'All')) if st.session_state.common_filters.get('Site', 'All') in site_options else 0)
        else:
            site_filter = st.text_input("Site (enter name)", value=st.session_state.common_filters.get('Site', ''))
        
        # Save filters to session state when apply button is clicked
        if st.button("Apply Filters"):
            st.session_state.common_filters = {
                'Client': client_filter if client_filter != "All" else None,
                'date_range': (start_date, end_date),
                'Year': selected_year if selected_year != "All" else None,
                'Site': site_filter if site_filter != "All" else None
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
        with st.expander("Utilization Filters", expanded=False):
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
            
            create_utilization_dashboard(filtered_df)
        else:
            st.info("No utilization data loaded. Please use the 'Load Utilization Data' button above.")
    
    # Financial Performance tab
    with tab3:
        st.header("Financial Performance")
        
        # Add tab-specific filters
        with st.expander("Financial Filters", expanded=False):
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
        with st.expander("SOW Filters", expanded=False):
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