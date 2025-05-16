import streamlit as st
import pandas as pd
from config import AIRTABLE_BASES
from modules.airtable.fetch import fetch_from_airtable
from modules.utils.data_processing import airtable_to_dataframe

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