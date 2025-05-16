import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
import re

def airtable_to_dataframe(airtable_data, verbose=False):
    """
    Convert Airtable API response to a Pandas DataFrame with robust error handling
    
    Args:
        airtable_data: API response from Airtable
        verbose: Whether to show detailed processing information
        
    Returns:
        Pandas DataFrame with cleaned data
    """
    if not airtable_data or 'records' not in airtable_data:
        if verbose:
            st.warning("⚠️ No records found in Airtable data")
        return pd.DataFrame()
    
    try:
        records = []
        record_errors = 0
        
        for record in airtable_data['records']:
            try:
                # Extract fields and add record ID
                row = record.get('fields', {}).copy()
                row['id'] = record.get('id', '')
                row['createdTime'] = record.get('createdTime', '')
                records.append(row)
            except Exception as e:
                record_errors += 1
                if verbose:
                    st.warning(f"⚠️ Error processing record: {str(e)}")
                continue
        
        if record_errors > 0 and verbose:
            st.warning(f"⚠️ Encountered errors in {record_errors} records")
            
        # Create DataFrame from records
        df = pd.DataFrame(records)
        
        if verbose:
            st.success(f"✅ Successfully converted {len(df)} records to DataFrame")
            
            if not df.empty:
                with st.expander("🔍 DataFrame Info", expanded=False):
                    buffer = []
                    buffer.append(f"**Columns ({len(df.columns)}):** {', '.join(df.columns.tolist())}")
                    buffer.append(f"**Shape:** {df.shape[0]} rows × {df.shape[1]} columns")
                    buffer.append(f"**Memory Usage:** {df.memory_usage(deep=True).sum() / (1024 * 1024):.2f} MB")
                    st.markdown("\n".join(buffer))
        
        return df
        
    except Exception as e:
        if verbose:
            st.error(f"❌ Error converting Airtable data to DataFrame: {str(e)}")
        return pd.DataFrame()

def clean_dataframe(df, date_cols=None, numeric_cols=None, text_cols=None, boolean_cols=None, verbose=False):
    """
    Clean and standardize a DataFrame for analysis
    
    Args:
        df: DataFrame to clean
        date_cols: List of columns to convert to datetime
        numeric_cols: List of columns to convert to numeric
        text_cols: List of columns to clean as text
        boolean_cols: List of columns to convert to boolean
        verbose: Whether to show detailed processing information
        
    Returns:
        Cleaned DataFrame
    """
    if df.empty:
        return df
    
    cleaned_df = df.copy()
    
    try:
        # Basic cleaning for all columns
        for col in cleaned_df.columns:
            # Replace empty strings with NaN
            if cleaned_df[col].dtype == 'object':
                cleaned_df[col] = cleaned_df[col].replace('', np.nan)
        
        # Convert date columns
        if date_cols:
            for col in date_cols:
                if col in cleaned_df.columns:
                    try:
                        cleaned_df[col] = pd.to_datetime(cleaned_df[col], errors='coerce')
                    except Exception as e:
                        if verbose:
                            st.warning(f"⚠️ Error converting column '{col}' to datetime: {str(e)}")
        
        # Convert numeric columns
        if numeric_cols:
            for col in numeric_cols:
                if col in cleaned_df.columns:
                    try:
                        # If the column contains currency symbols, remove them first
                        if cleaned_df[col].dtype == 'object':
                            # Remove currency symbols and commas
                            cleaned_df[col] = cleaned_df[col].astype(str).str.replace(r'[$,]', '', regex=True)
                        cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')
                    except Exception as e:
                        if verbose:
                            st.warning(f"⚠️ Error converting column '{col}' to numeric: {str(e)}")
        
        # Clean text columns
        if text_cols:
            for col in text_cols:
                if col in cleaned_df.columns:
                    try:
                        # Convert to string and standardize whitespace
                        cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
                        # Replace multiple spaces with a single space
                        cleaned_df[col] = cleaned_df[col].str.replace(r'\s+', ' ', regex=True)
                        # Handle 'nan' and 'None' strings
                        cleaned_df[col] = cleaned_df[col].replace(['nan', 'None', 'NaN', 'none'], np.nan)
                    except Exception as e:
                        if verbose:
                            st.warning(f"⚠️ Error cleaning text column '{col}': {str(e)}")
        
        # Convert boolean columns
        if boolean_cols:
            for col in boolean_cols:
                if col in cleaned_df.columns:
                    try:
                        # Standardize boolean values
                        true_values = ['yes', 'true', 't', '1', 'y', 'on']
                        false_values = ['no', 'false', 'f', '0', 'n', 'off']
                        
                        def to_bool(x):
                            if pd.isna(x):
                                return np.nan
                            if isinstance(x, bool):
                                return x
                            if isinstance(x, (int, float)):
                                return bool(x)
                            if isinstance(x, str):
                                x = x.lower().strip()
                                if x in true_values:
                                    return True
                                if x in false_values:
                                    return False
                            return np.nan
                        
                        cleaned_df[col] = cleaned_df[col].apply(to_bool)
                    except Exception as e:
                        if verbose:
                            st.warning(f"⚠️ Error converting column '{col}' to boolean: {str(e)}")
        
        if verbose:
            st.success("✅ DataFrame cleaning completed successfully")
            
        return cleaned_df
        
    except Exception as e:
        if verbose:
            st.error(f"❌ Error cleaning DataFrame: {str(e)}")
        return df  # Return original DataFrame on error

def apply_filters(df, filters, verbose=False):
    """
    Apply filters to a DataFrame with enhanced functionality and error handling
    
    Args:
        df: DataFrame to filter
        filters: Dictionary of filter parameters
        verbose: Whether to show detailed filtering information
        
    Returns:
        Filtered DataFrame
    """
    if not filters or df.empty:
        return df.copy()
    
    filtered_df = df.copy()
    applied_filters = []
    
    try:
        # Apply column filters
        for column, value in filters.items():
            if column in filtered_df.columns and value:
                original_count = len(filtered_df)
                
                # List filter (multi-select)
                if isinstance(value, list):
                    if value and value[0] != "All":  # Skip if "All" is selected
                        # Handle case where column might contain lists
                        if any(isinstance(x, list) for x in filtered_df[column].dropna()):
                            # For columns containing lists, check if filter value is in the list
                            mask = filtered_df[column].apply(
                                lambda x: any(str(v) in [str(i) for i in x] for v in value) if isinstance(x, list) 
                                else str(x) in [str(v) for v in value] if x is not None else False
                            )
                            filtered_df = filtered_df[mask]
                            filter_desc = f"{column} in [{', '.join(str(v) for v in value[:3])}{'...' if len(value) > 3 else ''}]"
                        else:
                            # Convert both sides to strings for comparison to handle mixed types
                            value_str = [str(v) for v in value]
                            filtered_df = filtered_df[filtered_df[column].astype(str).isin(value_str)]
                            filter_desc = f"{column} in [{', '.join(str(v) for v in value[:3])}{'...' if len(value) > 3 else ''}]"
                
                # Date range filter
                elif isinstance(value, tuple) and len(value) == 2:
                    start_date, end_date = value
                    if pd.api.types.is_datetime64_dtype(filtered_df[column]):
                        filtered_df = filtered_df[(filtered_df[column] >= start_date) & 
                                                (filtered_df[column] <= end_date)]
                        filter_desc = f"{column} between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}"
                    else:
                        # Try to convert to datetime if not already
                        try:
                            temp_col = pd.to_datetime(filtered_df[column], errors='coerce')
                            filtered_df = filtered_df[(temp_col >= start_date) & (temp_col <= end_date)]
                            filter_desc = f"{column} between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}"
                        except:
                            # Skip if conversion fails
                            if verbose:
                                st.warning(f"⚠️ Could not apply date filter to column '{column}'")
                            continue
                
                # Numeric range filter
                elif isinstance(value, tuple) and len(value) > 2 and value[0] == 'range':
                    min_val, max_val = value[1], value[2]
                    try:
                        if pd.api.types.is_numeric_dtype(filtered_df[column]):
                            filtered_df = filtered_df[(filtered_df[column] >= min_val) & 
                                                    (filtered_df[column] <= max_val)]
                        else:
                            # Try to convert to numeric
                            temp_col = pd.to_numeric(filtered_df[column], errors='coerce')
                            filtered_df = filtered_df[(temp_col >= min_val) & (temp_col <= max_val)]
                        filter_desc = f"{column} between {min_val} and {max_val}"
                    except:
                        if verbose:
                            st.warning(f"⚠️ Could not apply numeric range filter to column '{column}'")
                        continue
                
                # Text search filter
                elif isinstance(value, str) and value.lower() != "all":
                    # Case-insensitive text search on string representation of values
                    filtered_df = filtered_df[filtered_df[column].astype(str).str.contains(value, case=False, na=False)]
                    filter_desc = f"{column} contains '{value}'"
                
                # Boolean filter
                elif isinstance(value, bool):
                    try:
                        # Try direct comparison first
                        filtered_df = filtered_df[filtered_df[column] == value]
                        filter_desc = f"{column} is {value}"
                    except:
                        # Fall back to string comparison for mixed types
                        filtered_df = filtered_df[filtered_df[column].astype(str).str.lower() == str(value).lower()]
                        filter_desc = f"{column} is {value}"
                
                # Record the effect of this filter
                filtered_count = len(filtered_df)
                reduction = original_count - filtered_count
                reduction_pct = (reduction / original_count * 100) if original_count > 0 else 0
                
                applied_filters.append({
                    'column': column,
                    'description': filter_desc,
                    'records_before': original_count,
                    'records_after': filtered_count,
                    'reduction': reduction,
                    'reduction_pct': reduction_pct
                })
        
        if verbose and applied_filters:
            with st.expander("🔍 Filter Details", expanded=False):
                st.write(f"**Applied {len(applied_filters)} filters:**")
                for f in applied_filters:
                    st.write(f"- {f['description']}: reduced records by {f['reduction']} ({f['reduction_pct']:.1f}%)")
                
                # Show the overall reduction
                if applied_filters:
                    initial_count = df.shape[0]
                    final_count = filtered_df.shape[0]
                    overall_reduction = initial_count - final_count
                    overall_pct = (overall_reduction / initial_count * 100) if initial_count > 0 else 0
                    
                    st.write(f"**Overall:** {initial_count:,} → {final_count:,} records ({overall_pct:.1f}% reduction)")
        
        return filtered_df
        
    except Exception as e:
        if verbose:
            st.error(f"❌ Error applying filters: {str(e)}")
        return df  # Return original DataFrame on error

def calculate_metrics(df, metrics_config, groupby=None, verbose=False):
    """
    Calculate multiple metrics from a DataFrame with support for grouping
    
    Args:
        df: DataFrame to analyze
        metrics_config: List of dictionaries with metric configurations
            Each metric dict should have:
            - 'name': Display name for the metric
            - 'column': Column to calculate from
            - 'function': Function to apply ('sum', 'mean', 'median', 'min', 'max', 'count', 'nunique', etc.)
            - 'format': (optional) Format string (e.g., '${:,.2f}', '{:.1%}')
            - 'suffix': (optional) Suffix to append (e.g., '%', '$')
        groupby: Column or list of columns to group by before calculating metrics
        verbose: Whether to show detailed processing information
        
    Returns:
        DataFrame with calculated metrics, or a dictionary if no groupby is provided
    """
    if df.empty:
        if verbose:
            st.warning("⚠️ Empty DataFrame, cannot calculate metrics")
        return {} if groupby is None else pd.DataFrame()
    
    try:
        # If groupby is provided, calculate metrics for each group
        if groupby is not None:
            result = pd.DataFrame()
            
            for metric in metrics_config:
                col = metric.get('column')
                func = metric.get('function', 'sum')
                name = metric.get('name', f"{func}({col})")
                
                if col not in df.columns:
                    if verbose:
                        st.warning(f"⚠️ Column '{col}' not found in DataFrame, skipping metric '{name}'")
                    continue
                
                # Use groupby and aggregate
                if func == 'sum':
                    grouped = df.groupby(groupby)[col].sum()
                elif func == 'mean':
                    grouped = df.groupby(groupby)[col].mean()
                elif func == 'median':
                    grouped = df.groupby(groupby)[col].median()
                elif func == 'min':
                    grouped = df.groupby(groupby)[col].min()
                elif func == 'max':
                    grouped = df.groupby(groupby)[col].max()
                elif func == 'count':
                    grouped = df.groupby(groupby)[col].count()
                elif func == 'nunique':
                    grouped = df.groupby(groupby)[col].nunique()
                else:
                    if verbose:
                        st.warning(f"⚠️ Unknown function '{func}', skipping metric '{name}'")
                    continue
                
                # Add to result DataFrame
                result[name] = grouped
            
            return result.reset_index()
        
        # If no groupby, calculate metrics for the entire DataFrame
        else:
            result = {}
            
            for metric in metrics_config:
                col = metric.get('column')
                func = metric.get('function', 'sum')
                name = metric.get('name', f"{func}({col})")
                format_str = metric.get('format')
                suffix = metric.get('suffix', '')
                
                if col not in df.columns:
                    if verbose:
                        st.warning(f"⚠️ Column '{col}' not found in DataFrame, skipping metric '{name}'")
                    continue
                
                # Calculate the metric
                if func == 'sum':
                    value = df[col].sum()
                elif func == 'mean':
                    value = df[col].mean()
                elif func == 'median':
                    value = df[col].median()
                elif func == 'min':
                    value = df[col].min()
                elif func == 'max':
                    value = df[col].max()
                elif func == 'count':
                    value = df[col].count()
                elif func == 'nunique':
                    value = df[col].nunique()
                else:
                    if verbose:
                        st.warning(f"⚠️ Unknown function '{func}', skipping metric '{name}'")
                    continue
                
                # Format the value if a format string is provided
                if format_str:
                    try:
                        formatted_value = format_str.format(value)
                    except:
                        formatted_value = f"{value}{suffix}"
                else:
                    formatted_value = f"{value}{suffix}"
                
                # Add to result dictionary
                result[name] = {
                    'raw_value': value,
                    'formatted_value': formatted_value
                }
            
            return result
    
    except Exception as e:
        if verbose:
            st.error(f"❌ Error calculating metrics: {str(e)}")
        return {} if groupby is None else pd.DataFrame() 