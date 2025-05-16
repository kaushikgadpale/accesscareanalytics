import streamlit as st
import requests
import time
from datetime import datetime
from config import AIRTABLE_BASES, AIRTABLE_CONFIG

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_from_airtable(base_key, query_params=None, retry_attempts=3, cache_key=None):
    """
    Fetch data from a specific Airtable base defined in AIRTABLE_BASES
    
    Args:
        base_key: Key of the base in AIRTABLE_BASES (e.g., 'SOW', 'UTILIZATION', 'PNL')
        query_params: Dictionary of query parameters to include in the request
        retry_attempts: Number of retry attempts for failed requests
        cache_key: Optional custom cache key for fine-grained cache control
        
    Returns:
        Dictionary containing the API response
    """
    # Record start time for performance tracking
    start_time = time.time()
    
    if base_key not in AIRTABLE_BASES:
        st.error(f"❌ Base key '{base_key}' not found in AIRTABLE_BASES configuration")
        return None
        
    base_info = AIRTABLE_BASES[base_key]
    base_id = base_info['BASE_ID']
    table_id = base_info['TABLE_ID']
    table_name = base_info.get('TABLE_NAME', 'Unknown Table')
    
    # Get API credentials
    api_key = st.session_state.get('airtable_api_key', AIRTABLE_CONFIG['API_KEY'])
    
    if not api_key or not base_id:
        st.error("❌ Airtable credentials not configured. Please set them up in the integration settings.")
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

    try:
        # Create a progress bar for fetching
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Initialize records list and offset
        all_records = []
        offset = None
        page = 1
        total_pages_est = 1  # Initial estimate, will be updated
        
        # Use pagination to fetch all records
        with st.spinner(f"📊 Fetching data from {table_name}..."):
            while True:
                # Add offset to params if we have one
                if offset:
                    params['offset'] = offset
                
                # Retry logic
                for attempt in range(retry_attempts):
                    try:
                        # Update status
                        status_text.text(f"Fetching page {page} (attempt {attempt+1}/{retry_attempts})...")
                        
                        # Make the request
                        response = requests.get(url, headers=headers, params=params, timeout=30)
                        
                        # Break if successful
                        if response.status_code == 200:
                            break
                        
                        # Wait before retrying (exponential backoff)
                        time.sleep(2 ** attempt)
                    except requests.exceptions.RequestException as e:
                        if attempt == retry_attempts - 1:  # Last attempt
                            raise
                        time.sleep(2 ** attempt)  # Wait before retrying
                
                # Check if the request was successful
                if response.status_code == 200:
                    data = response.json()
                    
                    # Add records to our list
                    if 'records' in data:
                        records_count = len(data.get('records', []))
                        all_records.extend(data['records'])
                        
                        # Estimate total pages based on first page
                        if page == 1 and records_count > 0:
                            # If we got the max records per page, there might be more pages
                            if records_count == params['maxRecords']:
                                # Rough estimate based on first page size
                                total_pages_est = max(5, total_pages_est)  # At least 5 pages as a conservative estimate
                        
                        # Update progress
                        progress = min(0.9, page / total_pages_est) if total_pages_est > 0 else 0.5
                        progress_bar.progress(progress)
                        status_text.text(f"Fetched page {page} with {records_count} records...")
                        
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
                    error_msg = f"Error fetching data from Airtable: Status code {response.status_code}"
                    st.error(f"❌ {error_msg}")
                    return None
        
        # Clear the temporary status message
        status_text.empty()
        progress_bar.progress(1.0)
        
        # Create a complete response with all records
        complete_response = {'records': all_records}
        
        # Calculate and show timing
        end_time = time.time()
        duration = end_time - start_time
        
        # Format record count with commas for readability
        record_count = len(all_records)
        formatted_count = f"{record_count:,}"
        
        if record_count > 0:
            st.success(f"✅ Successfully fetched {formatted_count} records from {table_name} ({duration:.2f} seconds)")
        else:
            st.warning(f"⚠️ No records found in {table_name}. Check your filters or Airtable configuration.")
            
        return complete_response
        
    except requests.exceptions.RequestException as e:
        # Handle network errors
        st.error(f"❌ Network error when fetching from Airtable: {str(e)}")
        return None
    except Exception as e:
        # Handle other unexpected errors
        st.error(f"❌ Unexpected error when fetching from Airtable: {str(e)}")
        return None 