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
    
    # Get unique contacts with formatted phones
    contacts = df[["Customer", "Email", "Phone"]].drop_duplicates()
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
    contacts[["First Name", "Last Name"]] = contacts["Customer"].str.split(" ", n=1, expand=True)
    
    # Map to Outlook contact fields
    outlook_contacts = pd.DataFrame({
        "First Name": contacts["First Name"],
        "Middle Name": "",
        "Last Name": contacts.get("Last Name", ""),
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
        "Mobile Phone": "",
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
        "Job Title": "",
        "Department": "",
        "Company": "",
        "Office Location": "",
        "Manager's Name": "",
        "Assistant's Name": "",
        "Assistant's Phone": "",
        "Company Yomi": "",
        "Business Street": "",
        "Business City": "",
        "Business State": "",
        "Business Postal Code": "",
        "Business Country/Region": "",
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
        "Web Page": "",
        "Birthday": "",
        "Anniversary": "",
        "Notes": ""
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