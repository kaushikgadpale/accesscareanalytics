import requests
import streamlit as st
from datetime import datetime
from config import LOCAL_TZ
from auth import get_auth_headers

def fetch_cancelled_emails(user_principal_name, max_results=500):
    """Fetch cancellation emails from Outlook mailbox"""
    headers = get_auth_headers()
    if not headers:
        return []
    
    try:
        # Verify mailbox access
        test_response = requests.get(
            f"https://graph.microsoft.com/v1.0/users/{user_principal_name}",
            headers=headers
        )
        if test_response.status_code != 200:
            st.error("Mailbox access denied. Verify permissions!")
            return []
        
        # Query parameters for cancellation emails
        params = {
            "$filter": "contains(subject,'cancelled') or contains(subject,'canceled')",
            "$top": max_results,
            "$select": "subject,receivedDateTime,from,bodyPreview"
        }
        
        response = requests.get(
            f"https://graph.microsoft.com/v1.0/users/{user_principal_name}/messages",
            headers=headers,
            params=params
        )
        
        cancellations = []
        for message in response.json().get("value", []):
            received_dt = datetime.fromisoformat(
                message["receivedDateTime"].replace("Z", "+00:00")
            ).astimezone(LOCAL_TZ)
            
            cancellations.append({
                "Business": "Email Cancellation",
                "Customer": message["from"]["emailAddress"].get("name", ""),
                "Email": message["from"]["emailAddress"].get("address", ""),
                "Phone": "",
                "Service": extract_service_from_subject(message["subject"]),
                "Start Date": received_dt,
                "End Date": None,
                "Duration (min)": 0,
                "Status": "Cancelled",
                "Notes": message.get("bodyPreview", ""),
                "ID": f"email-{message['id']}",
                "Source": "Email"
            })
        
        return cancellations
    
    except Exception as e:
        st.error(f"Email fetch failed: {str(e)}")
        return []

def extract_service_from_subject(subject):
    """Extract service name from email subject"""
    subject = subject.lower()
    markers = ["for ", "service: ", "appointment for "]
    for marker in markers:
        if marker in subject:
            return subject.split(marker)[1].strip().title()
    return "Unknown"