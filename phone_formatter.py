import re
import pandas as pd
import plotly.express as px

def format_phone_strict(raw_phone):
    """
    Format phone numbers in a strict format that's compatible with WhatsApp
    
    WhatsApp requires format: +[country code][number without leading zeros]
    For example: +1 555 123 4567 or +44 7911 123456
    """
    if isinstance(raw_phone, pd.DataFrame):
        # Handle DataFrame case
        df = raw_phone.copy()
        df["Formatted Phone"], df["Phone Status"] = zip(*df["Phone"].map(format_phone_strict))
        return df
    
    # Handle individual phone number case
    if not raw_phone or not isinstance(raw_phone, str):
        return ("", "Missing")
    
    # Remove all non-digit characters
    digits = re.sub(r"[^\d+]", "", raw_phone)
    
    # If there's already a + in the number, remove all characters before and including it
    # This ensures we only keep the digits after the international prefix
    if "+" in digits:
        digits = re.sub(r"^.*?\+", "", digits)
    
    # Basic validation - count the actual digits
    if len(digits) < 8:
        return ("", "Too Short")
    if len(digits) > 15:
        return ("", "Too Long")
    
    try:
        # Detect country code from the starting digits
        
        # Country code detection patterns (arranged from most to least specific)
        country_patterns = [
            # Format: (regex_pattern, country_code, country_name, leading_digits_to_remove)
            # North America: +1
            (r"^1\d{10}$", "1", "US/CA", 1),  # US/Canada with country code
            (r"^\d{10}$", "1", "US/CA", 0),   # US/Canada without country code
            
            # UK: +44
            (r"^44\d{10}$", "44", "UK", 2),         # UK with country code
            (r"^0\d{10}$", "44", "UK", 1),          # UK with leading 0
            (r"^7\d{9}$", "44", "UK", 0),           # UK mobile without leading 0
            
            # Ireland: +353
            (r"^353\d{9}$", "353", "IE", 3),        # Ireland with country code
            (r"^0\d{9}$", "353", "IE", 1),          # Ireland with leading 0
            
            # UAE: +971
            (r"^971\d{9}$", "971", "UAE", 3),       # UAE with country code
            (r"^0\d{9}$", "971", "UAE", 1),         # UAE with leading 0
            (r"^5\d{8}$", "971", "UAE", 0),         # UAE mobile without leading 0
            
            # Philippines: +63
            (r"^63\d{10}$", "63", "PH", 2),         # Philippines with country code
            (r"^0\d{10}$", "63", "PH", 1),          # Philippines with leading 0
            (r"^9\d{9}$", "63", "PH", 0),           # Philippines mobile without leading 0
            
            # Denmark: +45
            (r"^45\d{8}$", "45", "DK", 2),          # Denmark with country code
            (r"^\d{8}$", "45", "DK", 0),            # Denmark without country code
            
            # India: +91
            (r"^91\d{10}$", "91", "IN", 2),         # India with country code
            (r"^0\d{10}$", "91", "IN", 1),          # India with leading 0
            (r"^[6789]\d{9}$", "91", "IN", 0),      # India mobile without leading 0
            
            # Australia: +61
            (r"^61\d{9}$", "61", "AU", 2),          # Australia with country code
            (r"^0\d{9}$", "61", "AU", 1),           # Australia with leading 0
            (r"^4\d{8}$", "61", "AU", 0),           # Australia mobile without leading 0
            
            # Mexico: +52
            (r"^52\d{10}$", "52", "MX", 2),         # Mexico with country code
            (r"^0\d{10}$", "52", "MX", 1),          # Mexico with leading 0
            
            # Brazil: +55
            (r"^55\d{10,11}$", "55", "BR", 2),      # Brazil with country code
            (r"^0\d{10,11}$", "55", "BR", 1),       # Brazil with leading 0
            
            # Germany: +49
            (r"^49\d{10,11}$", "49", "DE", 2),      # Germany with country code
            (r"^0\d{10,11}$", "49", "DE", 1),       # Germany with leading 0
            
            # France: +33
            (r"^33\d{9}$", "33", "FR", 2),          # France with country code
            (r"^0\d{9}$", "33", "FR", 1),           # France with leading 0
            
            # Spain: +34
            (r"^34\d{9}$", "34", "ES", 2),          # Spain with country code
            (r"^\d{9}$", "34", "ES", 0),            # Spain without country code
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
            
            # Format for WhatsApp - always use the + prefix followed by country code and number
            formatted = f"+{country_code} {formatted_number}"
            
            # Apply country-specific formatting where appropriate
            if country_code == "1":  # US/Canada: +1 (XXX) XXX-XXXX
                if len(formatted_number) == 10:
                    area_code = formatted_number[:3]
                    prefix = formatted_number[3:6]
                    line = formatted_number[6:]
                    formatted = f"+1 ({area_code}) {prefix}-{line}"
            elif country_code == "44":  # UK: +44 XXXX XXXXXX
                if len(formatted_number) >= 10:
                    formatted = f"+44 {formatted_number}"
            
            return (formatted, f"Valid {country_name}")
        
        # If no specific format matches but length is valid (fallback)
        # Try to detect country code from first digits
        if len(digits) >= 11 and digits[:1] == "1":
            # Likely North America
            return (f"+1 {digits[1:]}", "Valid US/CA")
        elif len(digits) >= 11 and digits[:2] == "44":
            # Likely UK
            return (f"+44 {digits[2:]}", "Valid UK")
        elif len(digits) >= 12 and digits[:3] == "353":
            # Likely Ireland
            return (f"+353 {digits[3:]}", "Valid IE")
        elif len(digits) >= 12 and digits[:3] == "971":
            # Likely UAE
            return (f"+971 {digits[3:]}", "Valid UAE")
        elif len(digits) >= 11 and digits[:2] == "63":
            # Likely Philippines
            return (f"+63 {digits[2:]}", "Valid PH")
        elif len(digits) >= 10 and digits[:2] == "45":
            # Likely Denmark
            return (f"+45 {digits[2:]}", "Valid DK")
        elif len(digits) >= 12 and digits[:2] == "91":
            # Likely India
            return (f"+91 {digits[2:]}", "Valid IN")
        else:
            # Can't determine country - format with best guess
            # Most international numbers have 2-3 digit country codes
            if len(digits) >= 11:
                # Assume first 2 digits are country code
                return (f"+{digits[:2]} {digits[2:]}", "Unknown Format")
            else:
                return (f"+{digits}", "Unknown Format")
            
    except Exception as e:
        return ("", f"Error: {str(e)}")
    
    return ("", "Invalid Format")

def create_phone_analysis(df):
    """Create phone analysis visualizations"""
    if df.empty:
        return None, None
    
    # Get phone status counts
    status_counts = df["Phone Status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    
    # Create pie chart
    pie = px.pie(
        status_counts, 
        names="Status", 
        values="Count", 
        title="Phone Number Status Distribution",
        hole=0.3
    )
    
    # Create treemap showing country distribution
    valid_phones = df[df["Phone Status"].str.startswith("Valid")]
    country_counts = valid_phones["Phone Status"].value_counts().reset_index()
    country_counts.columns = ["Country", "Count"]
    
    tree = px.treemap(
        country_counts,
        path=["Country"],
        values="Count",
        title="Phone Number Country Distribution"
    )
    
    return pie, tree

def format_phone_dataframe(df):
    """Format phone numbers in a DataFrame"""
    if df.empty:
        return df
    
    # Create a copy and add formatted phones
    df = df.copy()
    df["Formatted Phone"], df["Phone Status"] = zip(*df["Phone"].map(format_phone_strict))
    
    # Get unique phone numbers with their associated emails and customers
    phone_status = (df[["Customer", "Email", "Phone", "Formatted Phone", "Phone Status"]]
                   .drop_duplicates(subset=["Phone"])
                   .sort_values(["Phone Status", "Phone"]))
    
    return phone_status

def prepare_outlook_contacts(df):
    """Prepare contacts for Outlook import with proper field mapping"""
    if df.empty:
        return pd.DataFrame()
    
    # Check which columns are available in the dataframe
    required_cols = ["Customer", "Email", "Phone"]
    optional_cols = ["ID", "Business", "Service Location", "Customer Location", 
                     "Customer Timezone", "Is Online", "Join URL", "Staff Members"]
    
    # Ensure all required columns exist
    for col in required_cols:
        if col not in df.columns:
            return pd.DataFrame()  # Return empty dataframe if missing required columns
    
    # Create a list of columns to extract, only including those that exist
    extract_cols = required_cols.copy()
    for col in optional_cols:
        if col in df.columns:
            extract_cols.append(col)
    
    # Get unique contacts with formatted phones
    contacts = df[extract_cols].drop_duplicates()
    
    # Add a unique index if ID is not available
    if "ID" not in contacts.columns:
        contacts["ID"] = contacts.index.astype(str)
    
    formatted_phones = pd.DataFrame([
        format_phone_strict(phone) for phone in contacts["Phone"]
    ], columns=["Formatted Phone", "Phone Status"])
    
    # Only keep valid phone numbers and remove duplicates
    contacts["Business Phone"] = [
        phone if status.startswith("Valid") else ""
        for phone, status in zip(formatted_phones["Formatted Phone"], formatted_phones["Phone Status"])
    ]
    
    # Remove duplicate phone numbers, keeping the first occurrence
    contacts = contacts[contacts["Business Phone"] != ""].drop_duplicates(subset=["Business Phone"])
    
    # Split customer name into first and last name
    name_parts = contacts["Customer"].str.split(" ", n=1, expand=True)
    contacts["First Name"] = name_parts[0] if 0 in name_parts else ""
    contacts["Last Name"] = name_parts[1] if 1 in name_parts else ""
    
    # Create notes field with form answers for each contact
    contact_notes = {}
    for idx, row in contacts.iterrows():
        contact_id = row['ID']
        
        # Find the original appointment with this ID (using index if ID is not from original data)
        matched_rows = None
        if "ID" in df.columns:
            matched_rows = df[df['ID'] == contact_id]
        else:
            # If ID is not from original data, try to match using other fields
            matched_rows = df[(df['Customer'] == row['Customer']) & 
                            (df['Email'] == row['Email']) & 
                            (df['Phone'] == row['Phone'])]
        
        if not matched_rows.empty:
            appt = matched_rows.iloc[0]
            notes = []
            
            # Collect all form answers
            form_fields = [col for col in appt.index if col.startswith('Form:')]
            if form_fields:
                for field in form_fields:
                    if pd.notna(appt[field]) and appt[field]:
                        question = field.replace('Form: ', '')
                        answer = appt[field]
                        notes.append(f"{question}: {answer}")
            
            contact_notes[contact_id] = "\n".join(notes)
    
    # Add notes to contacts dataframe
    contacts['Notes'] = contacts['ID'].map(lambda x: contact_notes.get(x, ""))
    
    # Default values for optional fields
    company = ""
    department = ""
    office_location = ""
    business_country = ""
    manager_name = ""
    
    # Set values for optional fields if they exist
    if "Business" in contacts.columns:
        company = contacts["Business"]
    if "Service Location" in contacts.columns:
        department = contacts["Service Location"]
    if "Customer Location" in contacts.columns:
        office_location = contacts["Customer Location"]
    if "Customer Timezone" in contacts.columns:
        business_country = contacts["Customer Timezone"]
    if "Staff Members" in contacts.columns:
        manager_name = contacts["Staff Members"]
    
    # Calculate web page field
    web_page = ""
    if "Is Online" in contacts.columns and "Join URL" in contacts.columns:
        web_page = contacts.apply(
            lambda x: x["Join URL"] if x["Is Online"] else "", 
            axis=1
        )
    
    # Map to Outlook contact fields - keeping only the standard Outlook fields
    outlook_contacts = pd.DataFrame({
        "First Name": contacts["First Name"],
        "Middle Name": "",
        "Last Name": contacts["Last Name"],
        "Title": "",
        "Suffix": "",
        "Nickname": "",
        "Given Yomi": "",
        "Surname Yomi": "",
        "E-mail Address": contacts["Email"],
        "E-mail 2 Address": "",
        "E-mail 3 Address": "",
        "Home Phone": "",
        "Home Phone 2": "",
        "Business Phone": contacts["Business Phone"],
        "Business Phone 2": "",
        "Mobile Phone": contacts["Business Phone"],
        "Car Phone": "",
        "Other Phone": "",
        "Primary Phone": "",
        "Pager": "",
        "Business Fax": "",
        "Home Fax": "",
        "Other Fax": "",
        "Company Main Phone": "",
        "Callback": "",
        "Radio Phone": "",
        "Telex": "",
        "TTY/TDD Phone": "",
        "IMAddress": "",
        "Job Title": "",  # Leaving job title blank as requested
        "Department": department,  # Service location as Department
        "Company": company,  # Business name as Company (patient's booking site)
        "Office Location": office_location,  # Customer location as Office
        "Manager's Name": manager_name,  # Staff members as Manager
        "Assistant's Name": "",
        "Assistant's Phone": "",
        "Company Yomi": "",
        "Business Street": "",
        "Business City": "",
        "Business State": "",
        "Business Postal Code": "",
        "Business Country/Region": business_country,  # Customer timezone as Country/Region
        "Home Street": "",
        "Home City": "",
        "Home State": "",
        "Home Postal Code": "",
        "Home Country/Region": "",
        "Other Street": "",
        "Other City": "",
        "Other State": "",
        "Other Postal Code": "",
        "Other Country/Region": "",
        "Personal Web Page": "",
        "Spouse": "",
        "Schools": "",
        "Hobby": "",
        "Location": "",
        "Web Page": web_page,  # Meeting URL as Web Page
        "Birthday": "",
        "Anniversary": "",
        "Notes": contacts["Notes"]
    })
    
    return outlook_contacts

def create_appointments_flow(df):
    """Create appointments flow analysis visualization"""
    if df.empty or "Creation Time" not in df.columns or "Booking Page" not in df.columns:
        return None
    
    # Convert Creation Time to datetime if it's not already
    df = df.copy()
    df["Creation Date"] = pd.to_datetime(df["Creation Time"]).dt.date
    
    # Group by date and booking page
    appointments_by_date = df.groupby(["Creation Date", "Booking Page"]).size().reset_index(name="Number of Bookings")
    
    # Create bar chart
    bar = px.bar(
        appointments_by_date,
        x="Creation Date",
        y="Number of Bookings",
        color="Booking Page",
        title="Appointments Flow by Booking Page",
        labels={
            "Creation Date": "Date",
            "Number of Bookings": "Number of Appointments",
            "Booking Page": "Booking Page"
        }
    )
    
    # Customize layout
    bar.update_layout(
        xaxis_tickangle=-45,
        barmode="stack",
        showlegend=True,
        legend_title="Booking Pages",
        height=600
    )
    
    return bar

def process_uploaded_phone_list(uploaded_file):
    """Process an uploaded file with phone numbers and convert to dataframe"""
    import pandas as pd
    import io
    
    if uploaded_file is None:
        return None
    
    try:
        # Determine file type
        file_type = uploaded_file.name.split('.')[-1].lower()
        
        if file_type == 'csv':
            df = pd.read_csv(uploaded_file)
        elif file_type in ['xls', 'xlsx']:
            df = pd.read_excel(uploaded_file)
        else:
            return None, "Unsupported file format. Please upload a CSV or Excel file."
        
        # Validate the dataframe has required columns
        required_phone_column = False
        
        # Check for common phone column names
        phone_column_names = ['Phone', 'Mobile', 'Phone Number', 'Mobile Number', 
                             'Cell', 'Cell Phone', 'Telephone', 'Contact Number',
                             'Business Phone', 'Home Phone', 'Work Phone']
        
        found_phone_column = None
        for col in phone_column_names:
            if col in df.columns:
                found_phone_column = col
                required_phone_column = True
                break
        
        if not required_phone_column:
            return None, "No phone number column found. The file should contain a column named 'Phone', 'Mobile', 'Phone Number', etc."
        
        # Prepare the dataframe for processing
        formatted_df = pd.DataFrame()
        formatted_df['Original Phone'] = df[found_phone_column]
        
        # Add any name columns if available
        if 'First Name' in df.columns:
            formatted_df['First Name'] = df['First Name']
        if 'Last Name' in df.columns:
            formatted_df['Last Name'] = df['Last Name']
        if 'Name' in df.columns and 'First Name' not in df.columns:
            # Try to split the name
            formatted_df['First Name'] = df['Name'].apply(lambda x: str(x).split(' ')[0] if pd.notna(x) else '')
            formatted_df['Last Name'] = df['Name'].apply(lambda x: ' '.join(str(x).split(' ')[1:]) if pd.notna(x) and len(str(x).split(' ')) > 1 else '')
        
        # Add email if available
        if 'Email' in df.columns:
            formatted_df['Email'] = df['Email']
        elif 'E-mail' in df.columns:
            formatted_df['Email'] = df['E-mail']
        elif 'E-mail Address' in df.columns:
            formatted_df['Email'] = df['E-mail Address']
        
        # Format phone numbers
        formatted_df['Formatted Phone'] = formatted_df['Original Phone'].apply(
            lambda x: format_phone_strict(str(x)) if pd.notna(x) else ''
        )
        
        # Add phone status column
        formatted_df['Phone Status'] = formatted_df['Formatted Phone'].apply(
            lambda x: get_phone_status(x)
        )
        
        return formatted_df, None
    except Exception as e:
        return None, f"Error processing file: {str(e)}"

def get_phone_status(phone_number):
    """Get status of a phone number after formatting"""
    if not phone_number:
        return "Missing"
    
    # Handle tuple format (output from format_phone_strict)
    if isinstance(phone_number, tuple) and len(phone_number) > 1:
        # Second element of tuple contains status
        return phone_number[1]
    
    # If it's just a string, check its format
    if isinstance(phone_number, str):
        if phone_number.startswith('+'):
            # Extract country code
            match = re.match(r"^\+(\d{1,3})", phone_number)
            if match:
                country_code = match.group(1)
                country_map = {
                    "1": "Valid US/CA",    # United States/Canada
                    "44": "Valid UK",      # United Kingdom
                    "353": "Valid IE",     # Ireland
                    "971": "Valid UAE",    # UAE/Dubai
                    "45": "Valid DK",      # Denmark
                    "63": "Valid PH",      # Philippines
                    "91": "Valid IN",      # India
                    "61": "Valid AU",      # Australia
                    "52": "Valid MX",      # Mexico
                    "55": "Valid BR",      # Brazil
                    "49": "Valid DE",      # Germany
                    "33": "Valid FR",      # France
                    "34": "Valid ES",      # Spain
                }
                return country_map.get(country_code, "Valid International")
        
        # Length checks
        if len(re.sub(r"[^\d]", "", phone_number)) < 8:
            return "Too Short"
        elif len(re.sub(r"[^\d]", "", phone_number)) > 15:
            return "Too Long"
    
    return "Invalid Format"