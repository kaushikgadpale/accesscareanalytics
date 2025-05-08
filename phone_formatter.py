import re

def format_phone_strict(raw_phone: str) -> tuple:
    """Strict phone number formatting with validation"""
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
        return (digits, f"Error: {str(e)}")
    
    return (digits, "Unknown")

def create_phone_analysis(df):
    """Create phone number analysis visuals"""
    if "Phone" not in df.columns:
        return None, None
    
    df["Formatted_Phone"], df["Phone_Status"] = zip(*df["Phone"].map(format_phone_strict))
    status_counts = df["Phone_Status"].value_counts().reset_index()
    
    pie_chart = px.pie(status_counts, names="index", values="Phone_Status", 
                      title="Phone Number Validation Status")
    treemap = px.treemap(status_counts, path=["index"], values="Phone_Status",
                        title="Phone Status Distribution")
    
    return pie_chart, treemap