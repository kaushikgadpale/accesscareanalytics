import streamlit as st
import pandas as pd
from datetime import datetime
from modules.airtable.fetch import fetch_from_airtable
from config import AIRTABLE_CONFIG

# Add the KPI table to the AIRTABLE_BASES in config.py if needed
KPI_TABLE_ID = "tblzlzDIB1HuNIdgw"
KPI_BASE_ID = "appenAXVtP86f4M9z"  # Base ID for 'Onsite Reporting' Base
KPI_FIELDS = {
    'ID': 'fldnPvdlg1ofaNImG',
    'QUESTION': 'fldhPGfw6egYpp4Rx',
    'SELECT': 'fldAtqKvshgDb1kYr',
    'TAGS': 'fld5Ec2UWY9Y1eHr7',
    'DATE': 'fldYnyaTAf9vM9SIO',
    'PICTURES_POD_SETUP': 'fldQYS7eSLqjlS4ED',
    'EARGYM_PROMOTION': 'fldcptj6a0EHtsnMv',
    'CROSSBOOKING': 'fldPHIRIZm77Puwy0',
    'BOTD_EOD_FILLED': 'fldC73HUBZK5XKr3E',
    'PHOTOS_VIDEOS_TESTIMONIALS': 'fldpNQsUV59WsAFK5',
    'XRAYS_DENTAL_NOTES_UPLOADED': 'fldEpdMFzJIEXFERD',
    'IF_NO_WHY': 'fldtUCvGpspiqmSWz'
}

@st.cache_data(ttl=3600, show_spinner=False)
def get_kpi_data(date_range=None, leader=None, site=None):
    """
    Fetch KPI data from Airtable
    
    Args:
        date_range: Tuple containing (start_date, end_date)
        leader: Filter by specific leader name
        site: Filter by specific site name
        
    Returns:
        DataFrame containing KPI data
    """
    # Create a cache key based on filters including a timestamp for cache busting
    cache_key = f"kpi_data_{date_range}_{leader}_{site}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Fetch data from Airtable using a custom fetch method since we have a different base ID
    query_params = {}  # Add any query parameters if needed
    
    # Get API credentials
    api_key = st.session_state.get('airtable_api_key', AIRTABLE_CONFIG['API_KEY'])
    
    if not api_key:
        st.error("❌ Airtable API key not configured. Please set it up in the integration settings.")
        return pd.DataFrame()
    
    # Prepare headers
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # Create URL with the right base ID and table ID 
    url = f"{AIRTABLE_CONFIG['API_URL']}/{KPI_BASE_ID}/{KPI_TABLE_ID}"
    
    try:
        # Use existing fetch_from_airtable function but with overridden base info
        base_info = {
            'KPI': {
                'BASE_ID': KPI_BASE_ID,
                'TABLE_ID': KPI_TABLE_ID,
                'TABLE_NAME': 'Daily KPI',
                'FIELDS': KPI_FIELDS
            }
        }
        
        # Override the AIRTABLE_BASES in config temporarily
        from config import AIRTABLE_BASES
        original_kpi_base = AIRTABLE_BASES.get('KPI', {})
        AIRTABLE_BASES['KPI'] = base_info['KPI']
        
        # Now fetch the data
        response = fetch_from_airtable('KPI', cache_key=cache_key)
        
        # Restore the original base config
        if original_kpi_base:
            AIRTABLE_BASES['KPI'] = original_kpi_base
        else:
            AIRTABLE_BASES.pop('KPI', None)
            
        if not response or 'records' not in response:
            st.warning("No KPI data available. Please check your Airtable connection.")
            return pd.DataFrame()
        
        # Process the records
        records = []
        for i, record in enumerate(response['records']):
            field_data = record['fields']
            
            # --- Temporary Debug Print for Site Name Field ---
            actual_site_field_name = "Sites (from Tags)" # Actual name of the lookup field
            raw_tags_value = field_data.get(actual_site_field_name) 
            if i < 5: # Print for the first 5 records
                print(f"Debug Record {i}: Raw '{actual_site_field_name}' (ID {KPI_FIELDS['TAGS']}) value: {raw_tags_value}, Type: {type(raw_tags_value)}")
            # --- End Temporary Debug Print ---
            
            site_name = 'Unknown Site' # Default
            if isinstance(raw_tags_value, list) and len(raw_tags_value) > 0:
                # If it's a list, assume the first item is the site name string
                if isinstance(raw_tags_value[0], str):
                    site_name = raw_tags_value[0].strip()
                elif raw_tags_value[0] is not None:
                    site_name = str(raw_tags_value[0]).strip() # Attempt to convert
            elif isinstance(raw_tags_value, str) and raw_tags_value.strip():
                site_name = raw_tags_value.strip()
            
            row = {
                'id': record['id'],
                'Leader': field_data.get('Select', ''),
                'Site': site_name,
                'Date': field_data.get('Date', ''),
                'EargymPromotion': _parse_numeric(field_data.get('# of Eargym Promotion', 0)),
                'Crossbooking': _parse_numeric(field_data.get('# of crossbooking', 0)),
                'BOTDandEODFilled': _parse_yes_no(field_data.get('Are BOTD and EOD already filled?', '')),
                'PhotosVideosTestimonials': _parse_numeric(field_data.get('Number of photos/Videos/Testimonials posted at the Teams channel', 0)),
                'XraysAndDentalNotesUploaded': _parse_yes_no(field_data.get('Are all Xray\'s and Dental Notes uploaded to the right platforms?', '')),
                'IfNoWhy': field_data.get('If No, Why?', '')
            }
            records.append(row)
        
        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        # Apply filters if provided
        if date_range and date_range[0] is not None and date_range[1] is not None:
            start_date, end_date = date_range
            
            # Ensure date field is not empty
            df = df[df['Date'].notna() & (df['Date'] != '')]
            
            # Convert date column to datetime
            df['Date'] = pd.to_datetime(df['Date'])
            
            # Apply date filter
            df = df[(df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)]
        
        if leader:
            df = df[df['Leader'] == leader]
        
        if site:
            df = df[df['Site'] == site]
        
        return df
        
    except Exception as e:
        st.error(f"❌ Error fetching KPI data: {str(e)}")
        return pd.DataFrame()

def _parse_numeric(value):
    """Parse a numeric value, handling various formats"""
    if pd.isna(value) or value == '':
        return 0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0

def _parse_yes_no(value):
    """Convert Yes/No to 1/0 for scoring"""
    if isinstance(value, str):
        return 1 if value.lower() == 'yes' else 0
    return 0

def calculate_performance_score(df, weights=None):
    """
    Calculate performance scores for each leader
    
    Args:
        df: DataFrame containing KPI data
        weights: Dictionary of weights for each KPI category
        
    Returns:
        DataFrame with performance scores
    """
    if df.empty:
        return pd.DataFrame()
    
    # Default weights if not provided
    if weights is None:
        weights = {
            'EargymPromotion': 1,
            'Crossbooking': 1,
            'BOTDandEODFilled': 1,
            'PhotosVideosTestimonials': 1,
            'XraysAndDentalNotesUploaded': 1
        }
    
    # Set minimum requirements
    MINIMUM_EARGYM = 1  # 100% of all audio exams
    MINIMUM_CROSSBOOKING = 2  # Minimum 2 crossbookings
    MINIMUM_PHOTOS = 3  # Minimum 3 photos/videos/testimonials
    
    # Make a copy of the dataframe to avoid modifying the original
    score_df = df.copy()
    
    # Calculate if minimums are met (1 for met, partial credit for partial)
    score_df['EargymMinMet'] = score_df['EargymPromotion'].apply(
        lambda x: min(x / MINIMUM_EARGYM, 1.0) if MINIMUM_EARGYM > 0 else 1.0
    )
    
    score_df['CrossbookingMinMet'] = score_df['Crossbooking'].apply(
        lambda x: min(x / MINIMUM_CROSSBOOKING, 1.0) if MINIMUM_CROSSBOOKING > 0 else 1.0
    )
    
    score_df['PhotosMinMet'] = score_df['PhotosVideosTestimonials'].apply(
        lambda x: min(x / MINIMUM_PHOTOS, 1.0) if MINIMUM_PHOTOS > 0 else 1.0
    )
    
    # Aggregate data by leader
    scores = score_df.groupby('Leader').agg({
        'EargymPromotion': 'mean',
        'Crossbooking': 'mean',
        'BOTDandEODFilled': 'mean',
        'PhotosVideosTestimonials': 'mean',
        'XraysAndDentalNotesUploaded': 'mean',
        'EargymMinMet': 'mean',  # Average of whether minimum was met across all events
        'CrossbookingMinMet': 'mean',
        'PhotosMinMet': 'mean',
        'id': 'count'  # Count of records for this leader
    }).rename(columns={'id': 'EventCount'})
    
    # Get max values for normalization
    max_eargym = df['EargymPromotion'].max() if df['EargymPromotion'].max() > 0 else 1
    max_crossbooking = df['Crossbooking'].max() if df['Crossbooking'].max() > 0 else 1
    max_photos = df['PhotosVideosTestimonials'].max() if df['PhotosVideosTestimonials'].max() > 0 else 1
    
    # Normalize numeric scores (0-1 scale) with bonus for exceeding minimums
    # Base score is minimum met (0-1) plus bonus for exceeding minimum
    scores['NormalizedEargymPromotion'] = scores['EargymMinMet'] * 0.7 + (scores['EargymPromotion'] / max_eargym) * 0.3
    scores['NormalizedCrossbooking'] = scores['CrossbookingMinMet'] * 0.7 + (scores['Crossbooking'] / max_crossbooking) * 0.3
    scores['NormalizedPhotosVideosTestimonials'] = scores['PhotosMinMet'] * 0.7 + (scores['PhotosVideosTestimonials'] / max_photos) * 0.3
    
    # Create weighted score
    # Normalize weights to sum to 1
    total_weight = sum(weights.values())
    normalized_weights = {k: v/total_weight for k, v in weights.items()}
    
    scores['WeightedScore'] = (
        scores['NormalizedEargymPromotion'] * normalized_weights['EargymPromotion'] +
        scores['NormalizedCrossbooking'] * normalized_weights['Crossbooking'] +
        scores['BOTDandEODFilled'] * normalized_weights['BOTDandEODFilled'] +
        scores['NormalizedPhotosVideosTestimonials'] * normalized_weights['PhotosVideosTestimonials'] +
        scores['XraysAndDentalNotesUploaded'] * normalized_weights['XraysAndDentalNotesUploaded']
    )
    
    # Convert to 100-point scale for display
    scores['PerformanceScore'] = scores['WeightedScore'] * 100
    
    # Calculate ranks
    scores['Rank'] = scores['PerformanceScore'].rank(ascending=False, method='min')
    
    # Calculate percentage of events where all minimums were met
    scores['MinimumsMet'] = score_df.groupby('Leader').apply(
        lambda x: (
            (x['EargymPromotion'] >= MINIMUM_EARGYM) & 
            (x['Crossbooking'] >= MINIMUM_CROSSBOOKING) & 
            (x['PhotosVideosTestimonials'] >= MINIMUM_PHOTOS) &
            (x['BOTDandEODFilled'] == 1) &
            (x['XraysAndDentalNotesUploaded'] == 1)
        ).mean() * 100
    )
    
    return scores 