import re
import pandas as pd
import plotly.express as px

def format_phone_strict(raw_phone):
    """Format phone numbers in a strict format"""
    if isinstance(raw_phone, pd.DataFrame):
        # Handle DataFrame case
        df = raw_phone.copy()
        df["Formatted Phone"], df["Phone Status"] = zip(*df["Phone"].map(format_phone_strict))
        return df
    
    # Handle individual phone number case
    if not raw_phone or not isinstance(raw_phone, str):
        return ("", "Missing")
    
    # Remove all non-digit characters
    digits = re.sub(r"[^\d]", "", raw_phone)
    
    # Basic validation
    if len(digits) < 8:
        return ("", "Too Short")
    if len(digits) > 15:
        return ("", "Too Long")
    
    try:
        # Irish numbers (+353)
        if (digits.startswith("353") or 
            (len(digits) == 9 and digits.startswith("08")) or
            (len(digits) == 10 and digits.startswith("08"))):
            if digits.startswith("353"):
                formatted = f"+353 {digits[3:]}"
            else:
                formatted = f"+353 {digits[1:]}"
            return (formatted, "Valid IE")
        
        # UK numbers (+44)
        if (digits.startswith("44") or 
            (len(digits) == 11 and digits.startswith("07")) or
            (len(digits) == 10 and digits.startswith("0"))):
            if digits.startswith("44"):
                formatted = f"+44 {digits[2:]}"
            else:
                formatted = f"+44 {digits[1:]}"
            return (formatted, "Valid UK")
        
        # US/Canada numbers (+1)
        if ((digits.startswith("1") and len(digits) == 11) or 
            len(digits) == 10):
            area_code = digits[-10:-7]
            prefix = digits[-7:-4]
            line = digits[-4:]
            formatted = f"+1 ({area_code}) {prefix}-{line}"
            return (formatted, "Valid US/CA")
        
        # UAE numbers (+971)
        if (digits.startswith("971") or 
            (len(digits) == 9 and digits.startswith("0")) or
            (len(digits) in [9, 10] and digits.startswith("5"))):
            if digits.startswith("971"):
                formatted = f"+971 {digits[3:]}"
            elif digits.startswith("0"):
                formatted = f"+971 {digits[1:]}"
            else:
                formatted = f"+971 {digits}"
            return (formatted, "Valid UAE")
        
        # Philippines numbers (+63)
        if (digits.startswith("63") or 
            (len(digits) == 10 and digits.startswith("0")) or
            (len(digits) == 10 and digits.startswith("9"))):
            if digits.startswith("63"):
                formatted = f"+63 {digits[2:]}"
            elif digits.startswith("0"):
                formatted = f"+63 {digits[1:]}"
            else:
                formatted = f"+63 {digits}"
            return (formatted, "Valid PH")
        
        # Denmark numbers (+45)
        if (digits.startswith("45") or len(digits) == 8):
            if digits.startswith("45"):
                formatted = f"+45 {digits[2:]}"
            else:
                formatted = f"+45 {digits}"
            return (formatted, "Valid DK")
        
        # If no specific format matches but length is valid, return cleaned number
        if 8 <= len(digits) <= 15:
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
    
    if phone_number.startswith('+'):
        if '+353' in phone_number:
            return "Valid (Ireland)"
        elif '+44' in phone_number:
            return "Valid (UK)"
        elif '+1' in phone_number:
            return "Valid (US/Canada)"
        elif '+971' in phone_number:
            return "Valid (UAE)"
        elif '+63' in phone_number:
            return "Valid (Philippines)"
        elif '+45' in phone_number: 
            return "Valid (Denmark)"
        else:
            return "Valid (International)"
    
    if len(phone_number) < 10:
        return "Too Short"
    elif len(phone_number) > 15:
        return "Too Long"
    
    return "Invalid Format"