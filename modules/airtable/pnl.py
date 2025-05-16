import streamlit as st
import pandas as pd
from config import AIRTABLE_BASES
from modules.airtable.fetch import fetch_from_airtable
from modules.utils.data_processing import airtable_to_dataframe

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