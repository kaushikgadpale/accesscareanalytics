import streamlit as st
import pandas as pd
from config import AIRTABLE_BASES
from modules.airtable.fetch import fetch_from_airtable
from modules.utils.data_processing import airtable_to_dataframe

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