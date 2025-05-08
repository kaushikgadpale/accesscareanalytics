import requests
import pandas as pd
from datetime import datetime
from config import LOCAL_TZ, BOOKINGS_MAILBOXES
from auth import get_auth_headers
import streamlit as st

def fetch_businesses():
    """Fetch all booking businesses from Microsoft Graph"""
    headers = get_auth_headers()
    if not headers:
        return []
    
    try:
        response = requests.get(
            "https://graph.microsoft.com/v1.0/solutions/bookingBusinesses",
            headers=headers
        )
        response.raise_for_status()
        return [
            {"id": biz["id"], "name": biz["displayName"]} 
            for biz in response.json().get("value", [])
        ]
    except Exception as e:
        st.error(f"Failed to fetch businesses: {str(e)}")
        return []

def fetch_appointments(businesses, start_date, end_date, max_results):
    """Fetch appointments for selected businesses"""
    headers = get_auth_headers()
    if not headers:
        return []
    
    appointments = []
    progress_bar = st.progress(0)
    
    for idx, business in enumerate(businesses):
        try:
            url = f"https://graph.microsoft.com/v1.0/solutions/bookingBusinesses/{business['id']}/appointments?$top={max_results}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            for appt in response.json().get("value", []):
                start_dt = datetime.fromisoformat(appt["startDateTime"]["dateTime"].replace("Z", "+00:00")).astimezone(LOCAL_TZ)
                if not (start_date <= start_dt.date() <= end_date):
                    continue
                
                appointments.append(process_appointment(appt, business))
                
            progress_bar.progress((idx + 1) / len(businesses))
        except Exception as e:
            st.error(f"Error fetching appointments for {business['name']}: {str(e)}")
    
    progress_bar.empty()
    return appointments

def process_appointment(appt, business):
    """Process individual appointment data"""
    start_dt = datetime.fromisoformat(appt["startDateTime"]["dateTime"].replace("Z", "+00:00")).astimezone(LOCAL_TZ)
    end_dt = datetime.fromisoformat(appt["endDateTime"]["dateTime"].replace("Z", "+00:00")).astimezone(LOCAL_TZ) if appt.get("endDateTime") else None
    
    return {
        "Business": business["name"],
        "Customer": appt.get("customerName", ""),
        "Email": appt.get("customerEmailAddress", ""),
        "Phone": appt.get("customers", [{}])[0].get("phone", ""),
        "Service": appt.get("serviceName", ""),
        "Start Date": start_dt,
        "End Date": end_dt,
        "Duration (min)": (end_dt - start_dt).total_seconds() / 60 if end_dt else 0,
        "Status": get_appointment_status(appt),
        "Notes": appt.get("customerNotes", ""),
        "ID": appt.get("id", ""),
        "Source": "Booking"
    }

def get_appointment_status(appt):
    """Determine appointment status"""
    if appt.get("cancelledDateTime"):
        return "Cancelled"
    if appt.get("completedDateTime"):
        return "Completed"
    return "Scheduled"