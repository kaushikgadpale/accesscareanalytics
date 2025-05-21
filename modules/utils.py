import pandas as pd
import streamlit as st

def apply_filters(df, filters):
    """
    Apply common filters to dataframe
    
    Args:
        df: DataFrame to filter
        filters: Dictionary of filters to apply
        
    Returns:
        Filtered DataFrame
    """
    if not filters or df.empty:
        return df
    
    filtered_df = df.copy()
    
    # Apply Client filter
    if 'Client' in filters and filters['Client'] and 'Client' in filtered_df.columns:
        if isinstance(filters['Client'], list):
            # Handle list filter values
            # For columns that may contain lists, use a custom filter
            if filtered_df['Client'].apply(lambda x: isinstance(x, list)).any():
                # For rows where Client is a list, check if any item in the list is in filters['Client']
                list_mask = filtered_df['Client'].apply(
                    lambda x: isinstance(x, list) and any(str(item) in filters['Client'] for item in x)
                )
                # For rows where Client is not a list, check if it matches any in filters['Client']
                non_list_mask = filtered_df['Client'].apply(
                    lambda x: not isinstance(x, list) and str(x) in filters['Client']
                )
                # Combine the masks
                filtered_df = filtered_df[list_mask | non_list_mask]
            else:
                # Standard case for non-list columns
                filtered_df = filtered_df[filtered_df['Client'].isin(filters['Client'])]
        else:
            # Single string filter
            filtered_df = filtered_df[filtered_df['Client'] == filters['Client']]
    
    # Apply Site filter
    if 'Site' in filters and filters['Site']:
        # Check if we have 'Site' or 'Site_Location' column
        site_col = None
        if 'Site' in filtered_df.columns:
            site_col = 'Site'
        elif 'Site_Location' in filtered_df.columns:
            site_col = 'Site_Location'
            
        if site_col:
            if isinstance(filters['Site'], list):
                # For columns that may contain lists, use a custom filter
                if filtered_df[site_col].apply(lambda x: isinstance(x, list)).any():
                    # For rows where Site is a list, check if any item in the list is in filters['Site']
                    list_mask = filtered_df[site_col].apply(
                        lambda x: isinstance(x, list) and any(str(item) in filters['Site'] for item in x)
                    )
                    # For rows where Site is not a list, check if it matches any in filters['Site']
                    non_list_mask = filtered_df[site_col].apply(
                        lambda x: not isinstance(x, list) and str(x) in filters['Site']
                    )
                    # Combine the masks
                    filtered_df = filtered_df[list_mask | non_list_mask]
                else:
                    # Standard case for non-list columns
                    filtered_df = filtered_df[filtered_df[site_col].isin(filters['Site'])]
            else:
                # Single string filter
                filtered_df = filtered_df[filtered_df[site_col] == filters['Site']]
    
    # Apply date range filter
    date_col = None
    if 'date_range' in filters and filters['date_range']:
        # Check for date columns
        if 'Service_Month' in filtered_df.columns:
            date_col = 'Service_Month'
        elif 'Date_of_Service' in filtered_df.columns:
            date_col = 'Date_of_Service'
        elif 'ScheduledPlanningStartDate' in filtered_df.columns:
            date_col = 'ScheduledPlanningStartDate'
            
        if date_col:
            try:
                start_date, end_date = filters['date_range']
                filtered_df = filtered_df[(filtered_df[date_col] >= pd.Timestamp(start_date)) & 
                                        (filtered_df[date_col] <= pd.Timestamp(end_date))]
            except Exception as e:
                st.warning(f"Date filtering error: {str(e)}")
    
    # Apply year filter
    if 'Year' in filters and filters['Year']:
        try:
            year = int(filters['Year'])
            
            # Check for date columns
            if date_col is None:
                if 'Service_Month' in filtered_df.columns:
                    date_col = 'Service_Month'
                elif 'Date_of_Service' in filtered_df.columns:
                    date_col = 'Date_of_Service'
                elif 'ScheduledPlanningStartDate' in filtered_df.columns:
                    date_col = 'ScheduledPlanningStartDate'
            
            if date_col:
                filtered_df = filtered_df[filtered_df[date_col].dt.year == year]
            elif 'Year' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Year'] == year]
        except Exception as e:
            st.warning(f"Year filtering error: {str(e)}")
            
    return filtered_df 