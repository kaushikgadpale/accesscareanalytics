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
        return ("N/A", "Missing")
    
    digits = re.sub(r"[^\d]", "", raw_phone)
    if len(digits) < 8:
        return (digits, "Too Short")
    if len(digits) > 15:
        return (digits, "Too Long")
    
    try:
        if digits.startswith("353"):
            return (f"+353{digits[3:]}", "Valid IE")
        if digits.startswith("44"):
            return (f"+44{digits[2:]}", "Valid UK")
        if digits.startswith("1") and len(digits) == 11:
            return (f"+1{digits[1:]}", "Valid US/CA")
        if len(digits) == 10:
            return (f"+1{digits}", "Valid US/CA")
    except Exception as e:
        return (digits, f"Error:{e}")
    
    return (digits, "Unknown")

def create_phone_analysis(df):
    """Create phone analysis visualizations"""
    if df.empty:
        return None, None
    
    # Get phone status counts
    status_counts = df["Phone Status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    
    # Create pie chart
    pie = px.pie(status_counts, names="Status", values="Count", title="Phone Number Status Distribution")
    
    # Create treemap
    tree = px.treemap(status_counts, path=["Status"], values="Count", title="Phone Number Status Breakdown")
    
    return pie, tree

def format_phone_dataframe(df):
    """Format phone numbers in a DataFrame"""
    if df.empty:
        return df
    
    df = df.copy()
    df["Formatted Phone"], df["Phone Status"] = zip(*df["Phone"].map(format_phone_strict))
    return df