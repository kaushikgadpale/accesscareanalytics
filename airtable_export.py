import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
from config import AIRTABLE_CONFIG

def export_to_airtable(df, table_name, mapping=None, api_key=None, base_id=None):
    """
    Export a DataFrame to an Airtable table
    
    Args:
        df: DataFrame to export
        table_name: Name of the Airtable table
        mapping: Dictionary mapping DataFrame column names to Airtable field names
        api_key: Airtable API key (optional - will use config if not provided)
        base_id: Airtable Base ID (optional - will use config if not provided)
    
    Returns:
        Tuple of (success_count, error_count, errors)
    """
    # Get API credentials
    api_key = api_key or st.session_state.get('airtable_api_key') or AIRTABLE_CONFIG['API_KEY']
    base_id = base_id or st.session_state.get('airtable_base_id') or AIRTABLE_CONFIG['BASE_ID']
    
    if not api_key or not base_id:
        st.error("Airtable credentials not configured. Please set them up in the integration settings.")
        return (0, 0, ["Missing Airtable credentials"])
    
    # Prepare headers
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # Create URL
    url = f"{AIRTABLE_CONFIG['API_URL']}/{base_id}/{table_name}"
    
    # Apply mapping if provided
    if mapping:
        df = df.rename(columns=mapping)
    
    # Initialize counters
    success_count = 0
    error_count = 0
    errors = []
    
    # Convert DataFrame to records
    records = df.to_dict(orient='records')
    
    # Batch records (Airtable limits to 10 records per request)
    batch_size = 10
    batches = [records[i:i + batch_size] for i in range(0, len(records), batch_size)]
    
    # Process each batch
    with st.spinner(f"Exporting {len(records)} records to Airtable..."):
        for batch in batches:
            # Format the batch for Airtable
            airtable_records = {"records": [{"fields": record} for record in batch]}
            
            try:
                # Send the batch to Airtable
                response = requests.post(url, headers=headers, json=airtable_records)
                
                if response.status_code == 200:
                    success_count += len(batch)
                else:
                    error_count += len(batch)
                    error_message = f"Batch export failed: {response.status_code} - {response.text}"
                    errors.append(error_message)
                    st.warning(error_message)
            except Exception as e:
                error_count += len(batch)
                error_message = f"Error during export: {str(e)}"
                errors.append(error_message)
                st.warning(error_message)
    
    return (success_count, error_count, errors)

def export_bookings_to_airtable(bookings_df):
    """
    Export bookings data to Airtable
    
    Args:
        bookings_df: DataFrame containing bookings data
    
    Returns:
        Tuple of (success_count, error_count, errors)
    """
    if bookings_df is None or bookings_df.empty:
        st.error("No bookings data available to export.")
        return (0, 0, ["No data available"])
    
    # Define mapping between DataFrame columns and Airtable fields
    mapping = {
        "Customer": "Customer Name",
        "Email": "Email",
        "Phone": "Phone",
        "Service": "Service",
        "Start Date": "Appointment Date",
        "End Date": "End Date",
        "Created Date": "Created Date",
        "Modified Date": "Modified Date",
        "Status": "Status",
        "Notes": "Notes",
        "Location": "Location",
        # Add any other fields you want to map
    }
    
    # Filter columns to only include those in the mapping (to avoid extra fields)
    available_columns = [col for col in mapping.keys() if col in bookings_df.columns]
    export_df = bookings_df[available_columns].copy()
    
    # Add export timestamp
    export_df['Export Date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Export to Airtable
    return export_to_airtable(
        export_df, 
        AIRTABLE_CONFIG['BOOKINGS_TABLE'],
        {k: mapping[k] for k in available_columns}  # Only include mappings for available columns
    )

def export_patients_to_airtable(patients_df):
    """
    Export patient data to Airtable
    
    Args:
        patients_df: DataFrame containing patient data
    
    Returns:
        Tuple of (success_count, error_count, errors)
    """
    if patients_df is None or patients_df.empty:
        st.error("No patient data available to export.")
        return (0, 0, ["No data available"])
    
    # Define mapping between DataFrame columns and Airtable fields
    mapping = {
        "Customer": "Patient Name",
        "Email": "Email",
        "Phone": "Phone",
        "Address": "Address",
        "City": "City",
        "State": "State",
        "Zip": "Postal Code",
        "Last Visit": "Last Visit Date",
        "Service": "Last Service",
        # Add any other fields you want to map
    }
    
    # Filter columns to only include those in the mapping (to avoid extra fields)
    available_columns = [col for col in mapping.keys() if col in patients_df.columns]
    export_df = patients_df[available_columns].copy()
    
    # Add export timestamp
    export_df['Export Date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Export to Airtable
    return export_to_airtable(
        export_df, 
        AIRTABLE_CONFIG['PATIENTS_TABLE'],
        {k: mapping[k] for k in available_columns}  # Only include mappings for available columns
    )

def export_sow_to_airtable(sow_data):
    """
    Export SOW data to Airtable
    
    Args:
        sow_data: Dictionary containing SOW data
    
    Returns:
        Tuple of (success_count, error_count, errors)
    """
    if not sow_data:
        st.error("No SOW data available to export.")
        return (0, 0, ["No data available"])
    
    # Convert to DataFrame (with single row)
    sow_df = pd.DataFrame([sow_data])
    
    # Add export timestamp
    sow_df['Export Date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Export to Airtable
    return export_to_airtable(sow_df, AIRTABLE_CONFIG['SOW_TABLE'])

def render_airtable_export_button(df, export_type="bookings", location="dashboard"):
    """
    Render a button to export data to Airtable
    
    Args:
        df: DataFrame to export
        export_type: Type of data to export ('bookings', 'patients', or 'sow')
        location: Where the button is located (for styling)
    
    Returns:
        None
    """
    if df is None or df.empty:
        return
    
    # Choose button style based on location
    if location == "sidebar":
        container = st.sidebar
    else:
        container = st
    
    # Create export button
    if container.button(f"Export to Airtable", key=f"export_{export_type}_{location}"):
        with st.spinner(f"Exporting {export_type} to Airtable..."):
            # Choose export function based on data type
            if export_type == "bookings":
                success, errors, error_msgs = export_bookings_to_airtable(df)
            elif export_type == "patients":
                success, errors, error_msgs = export_patients_to_airtable(df)
            elif export_type == "sow":
                success, errors, error_msgs = export_sow_to_airtable(df)
            else:
                st.error(f"Unknown export type: {export_type}")
                return
            
            # Display results
            if success > 0 and errors == 0:
                st.success(f"Successfully exported {success} records to Airtable!")
            elif success > 0:
                st.warning(f"Partially exported data. Exported {success} records, but {errors} failed.")
            else:
                st.error(f"Failed to export data to Airtable. Check logs for details.")
                if error_msgs:
                    with st.expander("Error Details"):
                        for msg in error_msgs:
                            st.write(msg)

def render_export_options(data_type="bookings", df=None):
    """
    Render export options for different data types
    
    Args:
        data_type: Type of data to export ('bookings', 'patients', 'sow')
        df: DataFrame to export (optional)
    
    Returns:
        None
    """
    st.subheader(f"{data_type.title()} Export Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="card" style="text-align: center; cursor: pointer;">
            <h3>CSV Export</h3>
            <p>Export {data_type} as CSV file</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(f"Export CSV", key=f"csv_{data_type}"):
            if df is not None and not df.empty:
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Download CSV",
                    csv,
                    f"{data_type}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    key=f"download_csv_{data_type}"
                )
            else:
                st.warning(f"No {data_type} data available to export")
    
    with col2:
        st.markdown(f"""
        <div class="card" style="text-align: center; cursor: pointer;">
            <h3>Excel Export</h3>
            <p>Export {data_type} as Excel file</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(f"Export Excel", key=f"excel_{data_type}"):
            st.info(f"Excel export for {data_type} would be implemented here")
    
    with col3:
        st.markdown(f"""
        <div class="card" style="text-align: center; cursor: pointer;">
            <h3>Airtable Export</h3>
            <p>Export {data_type} to Airtable</p>
        </div>
        """, unsafe_allow_html=True)
        
        render_airtable_export_button(df, data_type, "export_page")

# Function to analyze Airtable data
def analyze_airtable_data(table_name, analysis_type="summary"):
    """
    Analyze data from Airtable
    
    Args:
        table_name: Name of the Airtable table
        analysis_type: Type of analysis to perform
        
    Returns:
        DataFrame with analysis results
    """
    from airtable_integration import fetch_airtable_table, convert_airtable_to_dataframe
    
    # Fetch data from Airtable
    airtable_data = fetch_airtable_table(table_name)
    if not airtable_data:
        st.error(f"Could not fetch data from {table_name} table.")
        return None
    
    # Convert to DataFrame
    df = convert_airtable_to_dataframe(airtable_data)
    if df.empty:
        st.warning(f"No records found in the {table_name} table.")
        return None
    
    # Perform analysis based on type
    if analysis_type == "summary":
        # Return basic statistics
        if table_name == AIRTABLE_CONFIG['BOOKINGS_TABLE']:
            # For bookings, analyze by status, service, date, etc.
            analyses = {}
            
            # Status distribution
            if 'Status' in df.columns:
                analyses['status_counts'] = df['Status'].value_counts().reset_index()
                analyses['status_counts'].columns = ['Status', 'Count']
            
            # Service distribution
            if 'Service' in df.columns:
                analyses['service_counts'] = df['Service'].value_counts().reset_index()
                analyses['service_counts'].columns = ['Service', 'Count']
            
            # Date distribution
            date_col = next((col for col in ['Appointment Date', 'Created Date', 'Start Date'] 
                             if col in df.columns), None)
            if date_col:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                analyses['date_counts'] = df.groupby(df[date_col].dt.date).size().reset_index()
                analyses['date_counts'].columns = ['Date', 'Count']
            
            return analyses
        
        elif table_name == AIRTABLE_CONFIG['PATIENTS_TABLE']:
            # For patients, analyze demographics, visit history, etc.
            analyses = {}
            
            # Count by State or City
            for field in ['State', 'City']:
                if field in df.columns:
                    analyses[f'{field.lower()}_counts'] = df[field].value_counts().reset_index()
                    analyses[f'{field.lower()}_counts'].columns = [field, 'Count']
            
            # Visit frequency
            if 'Last Visit Date' in df.columns:
                df['Last Visit Date'] = pd.to_datetime(df['Last Visit Date'], errors='coerce')
                analyses['visit_recency'] = df.groupby(df['Last Visit Date'].dt.month).size().reset_index()
                analyses['visit_recency'].columns = ['Month', 'Count']
            
            # Service distribution
            if 'Last Service' in df.columns:
                analyses['service_counts'] = df['Last Service'].value_counts().reset_index()
                analyses['service_counts'].columns = ['Service', 'Count']
            
            return analyses
    
    # Return the raw data if no specific analysis is performed
    return {"raw_data": df} 