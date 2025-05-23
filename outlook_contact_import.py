import streamlit as st
import pandas as pd
import re
import base64
import io
import plotly.express as px
from thefuzz import fuzz  # For fuzzy name matching

def format_phone_number(phone_number):
    """
    Format phone number for specific countries (US, UK, Ireland, Denmark, Philippines)
    Returns a tuple of (formatted_number, status)
    """
    if not phone_number or not isinstance(phone_number, str):
        return ("", "Missing")
    
    # Remove all non-digit characters (including brackets)
    digits = re.sub(r"[^\d+]", "", phone_number)
    
    # If there's already a + in the number, remove all characters before and including it
    if "+" in digits:
        digits = re.sub(r"^.*?\+", "", digits)
    
    # Basic validation - count the digits
    if len(digits) < 8:
        return ("", "Too Short")
    if len(digits) > 15:
        return ("", "Too Long")
    
    # Define patterns for the countries we care about
    country_patterns = [
        # Format: (regex_pattern, country_code, country_name, leading_digits_to_remove)
        # US: +1
        (r"^1\d{10}$", "1", "US", 1),  # US with country code
        (r"^\d{10}$", "1", "US", 0),   # US without country code
        
        # UK: +44
        (r"^44\d{10}$", "44", "UK", 2),         # UK with country code
        (r"^0\d{10}$", "44", "UK", 1),          # UK with leading 0
        (r"^7\d{9}$", "44", "UK", 0),           # UK mobile without leading 0
        
        # Ireland: +353
        (r"^353\d{9}$", "353", "Ireland", 3),   # Ireland with country code
        (r"^0\d{9}$", "353", "Ireland", 1),     # Ireland with leading 0
        
        # Denmark: +45
        (r"^45\d{8}$", "45", "Denmark", 2),     # Denmark with country code
        (r"^\d{8}$", "45", "Denmark", 0),       # Denmark without country code
        
        # Philippines: +63
        (r"^63\d{10}$", "63", "Philippines", 2), # Philippines with country code
        (r"^0\d{10}$", "63", "Philippines", 1),  # Philippines with leading 0
        (r"^9\d{9}$", "63", "Philippines", 0),   # Philippines mobile without leading 0
    ]
    
    # Try to match the digit pattern to identify the country
    matched_country = None
    for pattern, country_code, country_name, digits_to_remove in country_patterns:
        if re.match(pattern, digits):
            matched_country = (country_code, country_name, digits_to_remove)
            break
    
    # Format the phone number based on the detected country
    if matched_country:
        country_code, country_name, digits_to_remove = matched_country
        
        # Remove leading digits that are already part of the country code or leading zeros
        if digits_to_remove > 0:
            formatted_number = digits[digits_to_remove:]
        else:
            formatted_number = digits
        
        # Format with country code
        formatted = f"+{country_code} {formatted_number}"
        
        # Apply country-specific formatting if needed
        if country_code == "1":  # US: +1 (XXX) XXX-XXXX
            if len(formatted_number) == 10:
                area_code = formatted_number[:3]
                prefix = formatted_number[3:6]
                line = formatted_number[6:]
                formatted = f"+1 ({area_code}) {prefix}-{line}"
        elif country_code == "44":  # UK: +44 XXXX XXXXXX
            if len(formatted_number) == 10:
                first_part = formatted_number[:4]
                second_part = formatted_number[4:]
                formatted = f"+44 {first_part} {second_part}"
        elif country_code == "353":  # Ireland: +353 XX XXXXXXX
            if len(formatted_number) == 9:
                first_part = formatted_number[:2]
                second_part = formatted_number[2:]
                formatted = f"+353 {first_part} {second_part}"
        elif country_code == "45":  # Denmark: +45 XXXX XXXX
            if len(formatted_number) == 8:
                first_part = formatted_number[:4]
                second_part = formatted_number[4:]
                formatted = f"+45 {first_part} {second_part}"
        elif country_code == "63":  # Philippines: +63 XXX XXX XXXX
            if len(formatted_number) == 10:
                first_part = formatted_number[:3]
                second_part = formatted_number[3:6]
                third_part = formatted_number[6:]
                formatted = f"+63 {first_part} {second_part} {third_part}"
        
        return (formatted, f"Valid {country_name}")
    
    # Fallback for numbers we couldn't identify
    # Check common country code prefixes
    if digits.startswith('1') and len(digits) == 11:
        return (f"+1 {digits[1:]}", "Valid US")
    elif digits.startswith('44'):
        return (f"+44 {digits[2:]}", "Valid UK")
    elif digits.startswith('353'):
        return (f"+353 {digits[3:]}", "Valid Ireland")
    elif digits.startswith('45') and len(digits) == 10:
        return (f"+45 {digits[2:]}", "Valid Denmark")
    elif digits.startswith('63'):
        return (f"+63 {digits[2:]}", "Valid Philippines")
    else:
        return (f"{digits}", "Unknown Format")

def detect_duplicates(df, columns=None, fuzzy_name_match=False, fuzzy_threshold=85):
    """
    Detect duplicates in the dataframe based on specified columns
    
    Args:
        df: DataFrame to check for duplicates
        columns: Dictionary mapping column types to column names (e.g., {'phone': 'Formatted Phone', 'email': 'Email'})
        fuzzy_name_match: Whether to use fuzzy matching for names
        fuzzy_threshold: Threshold for fuzzy matching (0-100), higher = more strict
    
    Returns:
        DataFrame with duplicate information, dictionary with duplicate counts by type, duplicate groups dictionary
    """
    if df.empty:
        return df, {}, {}, {}
    
    # Initialize results
    df = df.copy()  # Don't modify the original
    df['Is Duplicate'] = False
    df['Duplicate Type'] = ""
    df['Duplicate Group'] = ""
    
    duplicate_counts = {
        'phone': 0,
        'email': 0,
        'exact_name': 0,
        'fuzzy_name': 0,
        'total': 0
    }
    
    duplicate_groups = {}
    group_id = 1
    
    # If no columns specified, use defaults
    if columns is None:
        columns = {}
        if 'Formatted Phone' in df.columns:
            columns['phone'] = 'Formatted Phone'
        if 'Email' in df.columns:
            columns['email'] = 'Email'
        if all(col in df.columns for col in ['First Name', 'Last Name']):
            columns['first_name'] = 'First Name'
            columns['last_name'] = 'Last Name'
    
    # Check for phone duplicates
    if 'phone' in columns and columns['phone'] in df.columns:
        phone_column = columns['phone']
        # Only consider non-empty phone values
        phone_dupes = df[df[phone_column].notna() & (df[phone_column] != "")]
        phone_dupes = phone_dupes[phone_dupes[phone_column].duplicated(keep=False)]
        
        for phone_value in phone_dupes[phone_column].unique():
            matching_indices = df[df[phone_column] == phone_value].index
            df.loc[matching_indices, 'Is Duplicate'] = True
            df.loc[matching_indices, 'Duplicate Type'] = 'Phone'
            df.loc[matching_indices, 'Duplicate Group'] = f"Phone-{group_id}"
            duplicate_groups[f"Phone-{group_id}"] = matching_indices.tolist()
            group_id += 1
            duplicate_counts['phone'] += len(matching_indices)
    
    # Check for email duplicates
    if 'email' in columns and columns['email'] in df.columns:
        email_column = columns['email']
        # Only consider non-empty email values
        email_dupes = df[df[email_column].notna() & (df[email_column] != "")]
        email_dupes = email_dupes[email_dupes[email_column].duplicated(keep=False)]
        
        for email_value in email_dupes[email_column].unique():
            matching_indices = df[df[email_column] == email_value].index
            # Only mark as duplicate if not already marked
            new_dupes = matching_indices[~df.loc[matching_indices, 'Is Duplicate']]
            if len(new_dupes) > 0:
                df.loc[matching_indices, 'Is Duplicate'] = True
                df.loc[matching_indices, 'Duplicate Type'] = df.loc[matching_indices, 'Duplicate Type'].replace('', 'Email')
                df.loc[matching_indices, 'Duplicate Group'] = f"Email-{group_id}"
                duplicate_groups[f"Email-{group_id}"] = matching_indices.tolist()
                group_id += 1
                duplicate_counts['email'] += len(matching_indices)
    
    # Check for exact name duplicates
    if all(key in columns for key in ['first_name', 'last_name']):
        first_name_col = columns['first_name']
        last_name_col = columns['last_name']
        
        # Create a combined full name column
        df['_FullName'] = df[first_name_col].fillna('') + ' ' + df[last_name_col].fillna('')
        df['_FullName'] = df['_FullName'].str.strip().str.lower()
        
        # Find exact name duplicates
        name_dupes = df[df['_FullName'] != '']
        name_dupes = name_dupes[name_dupes['_FullName'].duplicated(keep=False)]
        
        for name_value in name_dupes['_FullName'].unique():
            matching_indices = df[df['_FullName'] == name_value].index
            # Only mark as duplicate if not already marked
            new_dupes = matching_indices[~df.loc[matching_indices, 'Is Duplicate']]
            if len(new_dupes) > 0:
                df.loc[matching_indices, 'Is Duplicate'] = True
                df.loc[matching_indices, 'Duplicate Type'] = df.loc[matching_indices, 'Duplicate Type'].replace('', 'Exact Name')
                df.loc[matching_indices, 'Duplicate Group'] = f"Name-{group_id}"
                duplicate_groups[f"Name-{group_id}"] = matching_indices.tolist()
                group_id += 1
                duplicate_counts['exact_name'] += len(matching_indices)
        
        # Fuzzy name matching if requested
        if fuzzy_name_match and fuzz is not None:
            # Get contacts not already identified as duplicates
            non_dupes = df[~df['Is Duplicate']].copy()
            
            # Compare each name against all other names using fuzzy matching
            processed_pairs = set()
            
            # Process in chunks to avoid memory issues with large datasets
            chunk_size = 500
            for i in range(0, len(non_dupes), chunk_size):
                chunk = non_dupes.iloc[i:i+chunk_size]
                
                for idx1, row1 in chunk.iterrows():
                    name1 = row1['_FullName']
                    if not name1 or name1.strip() == '':
                        continue
                    
                    # Compare with all other names not yet processed
                    for idx2, row2 in non_dupes.iterrows():
                        if idx1 >= idx2:  # Skip self-comparison and already compared pairs
                            continue
                            
                        # Skip if this pair has been processed
                        pair_key = tuple(sorted([idx1, idx2]))
                        if pair_key in processed_pairs:
                            continue
                            
                        processed_pairs.add(pair_key)
                        
                        name2 = row2['_FullName']
                        if not name2 or name2.strip() == '':
                            continue
                        
                        # Calculate fuzzy match score
                        similarity = fuzz.ratio(name1, name2)
                        
                        # If above threshold, mark as fuzzy duplicates
                        if similarity >= fuzzy_threshold:
                            # Create a new duplicate group
                            df.loc[[idx1, idx2], 'Is Duplicate'] = True
                            df.loc[[idx1, idx2], 'Duplicate Type'] = df.loc[[idx1, idx2], 'Duplicate Type'].replace('', 'Fuzzy Name')
                            df.loc[[idx1, idx2], 'Duplicate Group'] = f"Fuzzy-{group_id}"
                            df.loc[[idx1, idx2], 'Matching Name'] = f"{row2['_FullName']}" if idx1 == idx1 else f"{row1['_FullName']}"
                            duplicate_groups[f"Fuzzy-{group_id}"] = [idx1, idx2]
                            
                            # Record the similarity as well
                            if 'Fuzzy Match Score' not in df.columns:
                                df['Fuzzy Match Score'] = None
                            df.loc[[idx1, idx2], 'Fuzzy Match Score'] = similarity
                            
                            # Store the matched name for reference
                            if 'Matched With' not in df.columns:
                                df['Matched With'] = ""
                            df.loc[idx1, 'Matched With'] = row2['_FullName']
                            df.loc[idx2, 'Matched With'] = row1['_FullName']
                            
                            group_id += 1
                            duplicate_counts['fuzzy_name'] += 2
        
        # Clean up the temporary column
        df = df.drop('_FullName', axis=1)
    
    # Calculate total duplicates (may be less than sum of individual counts due to overlaps)
    duplicate_counts['total'] = df['Is Duplicate'].sum()
    
    # Extract only the duplicates
    duplicates_df = df[df['Is Duplicate']].copy()
    
    return df, duplicates_df, duplicate_counts, duplicate_groups

def process_contacts_file(file, phone_column_names=None, fuzzy_match=True, fuzzy_threshold=85):
    """
    Process uploaded contacts file (CSV or Excel)
    """
    if file is None:
        return None, "No file uploaded"
    
    try:
        # Determine file type
        file_type = file.name.split('.')[-1].lower()
        
        if file_type == 'csv':
            df = pd.read_csv(file)
        elif file_type in ['xls', 'xlsx']:
            df = pd.read_excel(file)
        else:
            return None, "Unsupported file format. Please upload a CSV or Excel file."
        
        # Check for required columns
        if phone_column_names is None:
            phone_column_names = ['Phone', 'Mobile', 'Phone Number', 'Mobile Number', 
                                 'Cell', 'Cell Phone', 'Telephone', 'Contact Number',
                                 'Business Phone', 'Home Phone', 'Work Phone']
        
        found_phone_column = None
        for col in phone_column_names:
            if col in df.columns:
                found_phone_column = col
                break
        
        if not found_phone_column:
            return None, "No phone number column found in the file."
        
        # Create a clean dataframe with standardized columns
        processed_df = pd.DataFrame()
        processed_df['Original Phone'] = df[found_phone_column].astype(str)
        
        # Copy over name fields if available
        if 'First Name' in df.columns:
            processed_df['First Name'] = df['First Name']
        if 'Last Name' in df.columns:
            processed_df['Last Name'] = df['Last Name']
        if 'Name' in df.columns and 'First Name' not in df.columns:
            # Split name into first and last
            processed_df['First Name'] = df['Name'].apply(lambda x: str(x).split(' ')[0] if pd.notna(x) else '')
            processed_df['Last Name'] = df['Name'].apply(lambda x: ' '.join(str(x).split(' ')[1:]) if pd.notna(x) and len(str(x).split(' ')) > 1 else '')
        
        # Copy email if available
        for email_col in ['Email', 'E-mail', 'E-mail Address', 'Email Address']:
            if email_col in df.columns:
                processed_df['Email'] = df[email_col]
                break
        
        # Format phone numbers
        formatted_phones = []
        phone_statuses = []
        
        for phone in processed_df['Original Phone']:
            formatted, status = format_phone_number(phone)
            formatted_phones.append(formatted)
            phone_statuses.append(status)
        
        processed_df['Formatted Phone'] = formatted_phones
        processed_df['Phone Status'] = phone_statuses
        
        # Create column mapping for duplicate detection
        columns_map = {'phone': 'Formatted Phone'}
        if 'Email' in processed_df.columns:
            columns_map['email'] = 'Email'
        if 'First Name' in processed_df.columns and 'Last Name' in processed_df.columns:
            columns_map['first_name'] = 'First Name'
            columns_map['last_name'] = 'Last Name'
        
        # Detect duplicates with both exact and fuzzy matching
        processed_df, duplicates_df, duplicate_counts, duplicate_groups = detect_duplicates(
            processed_df, 
            columns=columns_map,
            fuzzy_name_match=fuzzy_match, 
            fuzzy_threshold=fuzzy_threshold
        )
        
        # Separate valid and invalid phone numbers
        valid_df = processed_df[processed_df['Phone Status'].str.startswith('Valid')]
        invalid_df = processed_df[~processed_df['Phone Status'].str.startswith('Valid')]
        
        return {
            'all': processed_df,
            'valid': valid_df,
            'invalid': invalid_df,
            'duplicates': duplicates_df,
            'duplicate_counts': duplicate_counts,
            'duplicate_groups': duplicate_groups,
            'stats': {
                'total': len(processed_df),
                'valid': len(valid_df),
                'invalid': len(invalid_df),
                'duplicates': duplicate_counts['total'],
                'unique_valid': len(valid_df[~valid_df['Is Duplicate']])
            }
        }, None
        
    except Exception as e:
        import traceback
        return None, f"Error processing file: {str(e)}\n{traceback.format_exc()}"

def create_status_chart(df):
    """
    Create a chart showing the distribution of phone statuses
    """
    if df.empty or 'Phone Status' not in df.columns:
        return None
    
    status_counts = df['Phone Status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Count']
    
    fig = px.pie(
        status_counts,
        names='Status',
        values='Count',
        title='Phone Number Status Distribution',
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig

def create_country_chart(df):
    """
    Create a chart showing the distribution of countries
    """
    if df.empty or 'Phone Status' not in df.columns:
        return None
    
    # Extract country from status
    df = df.copy()
    df['Country'] = df['Phone Status'].str.replace('Valid ', '')
    
    country_counts = df['Country'].value_counts().reset_index()
    country_counts.columns = ['Country', 'Count']
    
    fig = px.bar(
        country_counts,
        x='Country',
        y='Count',
        title='Phone Numbers by Country',
        color='Country',
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    
    return fig

def create_duplicate_chart(duplicate_counts):
    """
    Create a chart showing the types of duplicates found
    """
    if not duplicate_counts:
        return None
    
    # Extract relevant counts
    counts_data = {
        'Type': ['Phone', 'Email', 'Exact Name', 'Fuzzy Name'],
        'Count': [
            duplicate_counts.get('phone', 0),
            duplicate_counts.get('email', 0),
            duplicate_counts.get('exact_name', 0),
            duplicate_counts.get('fuzzy_name', 0)
        ]
    }
    
    df_counts = pd.DataFrame(counts_data)
    df_counts = df_counts[df_counts['Count'] > 0]  # Only show non-zero counts
    
    if df_counts.empty:
        return None
    
    fig = px.bar(
        df_counts,
        x='Type',
        y='Count',
        title='Duplicate Types Found',
        color='Type',
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    
    fig.update_layout(xaxis_title='Duplicate Type', yaxis_title='Count')
    
    return fig

def download_csv(df):
    """
    Generate a download link for a dataframe
    """
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'data:file/csv;base64,{b64}'
    return href

def prepare_outlook_contacts(df):
    """
    Prepare contacts for Outlook import using the standard Outlook CSV format
    """
    if df.empty:
        return pd.DataFrame()
    
    # Create a properly formatted Outlook contacts CSV
    outlook_contacts = pd.DataFrame({
        "First Name": df.get('First Name', ''),
        "Middle Name": "",
        "Last Name": df.get('Last Name', ''),
        "Title": "",
        "Suffix": "",
        "Nickname": "",
        "E-mail Address": df.get('Email', ''),
        "E-mail 2 Address": "",
        "E-mail 3 Address": "",
        "Home Phone": "",
        "Home Phone 2": "",
        "Business Phone": df['Formatted Phone'],
        "Business Phone 2": "",
        "Mobile Phone": df['Formatted Phone'],
        "Car Phone": "",
        "Other Phone": "",
        "Primary Phone": df['Formatted Phone'],
        "Pager": "",
        "Business Fax": "",
        "Home Fax": "",
        "Other Fax": "",
        "Company": "",
        "Job Title": "",
        "Department": "",
        "Office Location": "",
        "Categories": "Imported Contacts"
    })
    
    return outlook_contacts

def main():
    st.set_page_config(page_title="Outlook Contact Import Preparation Tool", layout="wide")
    
    st.title("Outlook Contact Import Preparation Tool")
    
    st.markdown("""
    This tool helps you prepare contact lists for import into Microsoft Outlook. 
    It can detect duplicates and format phone numbers correctly for US, UK, Ireland, Denmark, and Philippines.
    
    Upload your CSV or Excel file with contact information to get started.
    """)
    
    # Add fuzzy matching options
    col1, col2 = st.columns(2)
    with col1:
        enable_fuzzy = st.checkbox("Enable fuzzy name matching", value=True, 
                                  help="Find potential duplicates with similar but not identical names")
    with col2:
        if enable_fuzzy:
            fuzzy_threshold = st.slider("Fuzzy matching threshold", min_value=70, max_value=95, value=85,
                                       help="Higher values require names to be more similar to be considered a match")
        else:
            fuzzy_threshold = 85
    
    uploaded_file = st.file_uploader("Choose a contacts file", type=["csv", "xlsx", "xls"])
    
    if uploaded_file is not None:
        with st.spinner("Processing your file..."):
            result, error = process_contacts_file(uploaded_file, fuzzy_match=enable_fuzzy, fuzzy_threshold=fuzzy_threshold)
        
        if error:
            st.error(error)
        elif result:
            # Display statistics
            st.success("File processed successfully!")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Total Contacts", result['stats']['total'])
            col2.metric("Valid Phone Numbers", result['stats']['valid'])
            col3.metric("Invalid Numbers", result['stats']['invalid'])
            col4.metric("Duplicates", result['stats']['duplicates'])
            col5.metric("Unique Valid Contacts", result['stats']['unique_valid'])
            
            # Create tabs for different views
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Valid Contacts", "Invalid Contacts", "Duplicates", "All Contacts"])
            
            with tab1:
                st.subheader("Phone Number Analysis")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    status_chart = create_status_chart(result['all'])
                    if status_chart:
                        st.plotly_chart(status_chart, use_container_width=True)
                
                with col2:
                    country_chart = create_country_chart(result['all'][result['all']['Phone Status'].str.startswith('Valid')])
                    if country_chart:
                        st.plotly_chart(country_chart, use_container_width=True)
                
                # Add duplicate analysis chart
                if result['duplicate_counts']['total'] > 0:
                    st.subheader("Duplicate Analysis")
                    duplicate_chart = create_duplicate_chart(result['duplicate_counts'])
                    if duplicate_chart:
                        st.plotly_chart(duplicate_chart, use_container_width=True)
                
                st.subheader("Actions")
                
                # Generate Outlook-compatible CSV
                if not result['valid'].empty:
                    outlook_contacts = prepare_outlook_contacts(result['valid'])
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.download_button(
                            label="Download All Valid Contacts for Outlook",
                            data=outlook_contacts.to_csv(index=False),
                            file_name="outlook_contacts_all.csv",
                            mime="text/csv"
                        )
                        st.caption("File is formatted for direct import into Outlook")
                    
                    with col2:
                        # Download only unique valid contacts
                        unique_valid = result['valid'][~result['valid']['Is Duplicate']]
                        if not unique_valid.empty:
                            unique_outlook_contacts = prepare_outlook_contacts(unique_valid)
                            st.download_button(
                                label="Download Unique Valid Contacts for Outlook",
                                data=unique_outlook_contacts.to_csv(index=False),
                                file_name="outlook_contacts_unique.csv",
                                mime="text/csv"
                            )
                            st.caption("Contains only unique phone numbers, removes duplicates")
            
            with tab2:
                if result['valid'].empty:
                    st.warning("No valid phone numbers found.")
                else:
                    st.write(f"Found {len(result['valid'])} valid phone numbers")
                    st.dataframe(result['valid'], use_container_width=True)
                    
                    st.download_button(
                        label="Download Valid Contacts CSV",
                        data=result['valid'].to_csv(index=False),
                        file_name="valid_contacts.csv",
                        mime="text/csv"
                    )
            
            with tab3:
                if result['invalid'].empty:
                    st.success("No invalid phone numbers found.")
                else:
                    st.write(f"Found {len(result['invalid'])} invalid phone numbers")
                    st.dataframe(result['invalid'], use_container_width=True)
                    
                    st.download_button(
                        label="Download Invalid Contacts CSV",
                        data=result['invalid'].to_csv(index=False),
                        file_name="invalid_contacts.csv",
                        mime="text/csv"
                    )
                    
                    st.info("These numbers need manual correction. Common issues include:")
                    st.markdown("""
                    - Missing country code
                    - Incorrect number of digits
                    - Unsupported country format (only US, UK, Ireland, Denmark, and Philippines are supported)
                    """)
            
            with tab4:
                if result['duplicates'].empty:
                    st.success("No duplicate contacts found.")
                else:
                    st.write(f"Found {len(result['duplicates'])} duplicate contacts")
                    
                    # Show duplicate type information
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Phone Duplicates", result['duplicate_counts'].get('phone', 0))
                    col2.metric("Email Duplicates", result['duplicate_counts'].get('email', 0))
                    col3.metric("Exact Name Duplicates", result['duplicate_counts'].get('exact_name', 0))
                    col4.metric("Fuzzy Name Duplicates", result['duplicate_counts'].get('fuzzy_name', 0))
                    
                    # Display the duplicates dataframe
                    st.dataframe(result['duplicates'], use_container_width=True)
                    
                    # Display fuzzy match details if there are any
                    if result['duplicate_counts'].get('fuzzy_name', 0) > 0:
                        st.subheader("Fuzzy Matching Details")
                        fuzzy_matches = result['duplicates'][result['duplicates']['Duplicate Type'] == 'Fuzzy Name']
                        
                        # Group by duplicate group
                        fuzzy_groups = {}
                        for _, row in fuzzy_matches.iterrows():
                            group = row['Duplicate Group']
                            if group not in fuzzy_groups:
                                fuzzy_groups[group] = []
                            fuzzy_groups[group].append(row)
                        
                        # Display each fuzzy match pair
                        for group, matches in fuzzy_groups.items():
                            if len(matches) == 2:  # Most fuzzy matches are pairs
                                score = matches[0]['Fuzzy Match Score']
                                st.info(f"**Match Pair (Similarity: {score:.0f}%)**:")
                                
                                # Create a comparison table
                                comparison_data = {
                                    '': ['First Name', 'Last Name', 'Email', 'Formatted Phone']
                                }
                                
                                for i, match in enumerate(matches):
                                    contact_name = f"Contact {i+1}"
                                    comparison_data[contact_name] = [
                                        match.get('First Name', ''),
                                        match.get('Last Name', ''),
                                        match.get('Email', ''),
                                        match['Formatted Phone']
                                    ]
                                
                                comparison_df = pd.DataFrame(comparison_data)
                                st.table(comparison_df)
                    
                    st.download_button(
                        label="Download Duplicates CSV",
                        data=result['duplicates'].to_csv(index=False),
                        file_name="duplicate_contacts.csv",
                        mime="text/csv"
                    )
            
            with tab5:
                st.write("All processed contacts")
                st.dataframe(result['all'], use_container_width=True)
                
                st.download_button(
                    label="Download All Contacts CSV",
                    data=result['all'].to_csv(index=False),
                    file_name="all_contacts.csv",
                    mime="text/csv"
                )

if __name__ == "__main__":
    main() 