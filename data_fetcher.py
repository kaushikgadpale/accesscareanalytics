import requests
import pandas as pd
from datetime import datetime
from config import LOCAL_TZ, GRAPH_API_BASE
from auth import get_auth_headers
import streamlit as st
import pytz

def fetch_businesses():
    """Fetch all booking businesses from Microsoft Graph"""
    headers = get_auth_headers()
    if not headers:
        st.error("Failed to get authentication headers")
        return []
    
    try:
        response = requests.get(
            "https://graph.microsoft.com/v1.0/solutions/bookingBusinesses",
            headers=headers
        )
        response.raise_for_status()
        businesses = [
            {"id": biz["id"], "name": biz["displayName"]} 
            for biz in response.json().get("value", [])
        ]
        if not businesses:
            st.warning("No businesses found in your Microsoft Bookings account")
        return businesses
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            st.error("Permission denied. Please ensure the app has Bookings.Read.All permission")
        else:
            st.error(f"HTTP error occurred: {str(e)}")
        return []
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
    
    # Format dates for API - ensure we use UTC for the API request
    start_datetime = datetime.combine(start_date, datetime.min.time()).astimezone(LOCAL_TZ).astimezone(pytz.UTC)
    end_datetime = datetime.combine(end_date, datetime.max.time()).astimezone(LOCAL_TZ).astimezone(pytz.UTC)
    
    # Ensure we're not using future dates
    now = datetime.now(LOCAL_TZ).astimezone(pytz.UTC)
    if start_datetime > now:
        start_datetime = now
    if end_datetime > now:
        end_datetime = now
    
    # First get all businesses if not provided
    if not businesses:
        businesses = fetch_businesses()
    
    for idx, business in enumerate(businesses):
        try:
            # Get business ID and name - handle both string and dict cases
            if isinstance(business, dict):
                business_id = business["id"]
                business_name = business["name"]
            else:
                # If it's just a string (business name), fetch the ID
                all_businesses = fetch_businesses()
                business_info = next((b for b in all_businesses if b["name"] == business), None)
                if not business_info:
                    st.warning(f"Could not find business ID for {business}")
                    continue
                business_id = business_info["id"]
                business_name = business
            
            url = f"{GRAPH_API_BASE}/solutions/bookingBusinesses/{business_id}/appointments?$top={max_results}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            for appt in response.json().get("value", []):
                try:
                    start_dt = datetime.fromisoformat(appt["startDateTime"]["dateTime"].replace("Z", "+00:00")).astimezone(LOCAL_TZ)
                    if not (start_date <= start_dt.date() <= end_date):
                        continue
                    
                    end_dt = None
                    if appt.get("endDateTime"):
                        end_dt = datetime.fromisoformat(appt["endDateTime"]["dateTime"].replace("Z", "+00:00")).astimezone(LOCAL_TZ)
                    
                    # Get customer phone number
                    phone = ""
                    if appt.get("customers") and len(appt["customers"]) > 0:
                        phone = appt["customers"][0].get("phone", "")
                    
                    appointments.append({
                        "Business": business_name,
                        "Customer": appt.get("customerName", ""),
                        "Email": appt.get("customerEmailAddress", ""),
                        "Phone": phone,
                        "Service": appt.get("serviceName", ""),
                        "Start Date": start_dt,
                        "End Date": end_dt,
                        "Duration (min)": (end_dt - start_dt).total_seconds() / 60 if end_dt else 0,
                        "Status": "Cancelled" if appt.get("cancelledDateTime") else ("Completed" if appt.get("completedDateTime") else "Scheduled"),
                        "Notes": appt.get("customerNotes", ""),
                        "ID": appt.get("id", ""),
                        "Source": "Booking"
                    })
                except (KeyError, ValueError) as e:
                    st.warning(f"Skipping malformed appointment: {str(e)}")
                    continue
            
            progress_bar.progress((idx + 1) / len(businesses))
        except Exception as e:
            st.error(f"Error fetching appointments for {business_name}: {str(e)}")
    
    progress_bar.empty()
    return appointments

def process_appointment(appt, business):
    """Process individual appointment data"""
    try:
        start_dt = datetime.fromisoformat(appt["startDateTime"]["dateTime"].replace("Z", "+00:00")).astimezone(LOCAL_TZ)
        end_dt = datetime.fromisoformat(appt["endDateTime"]["dateTime"].replace("Z", "+00:00")).astimezone(LOCAL_TZ) if appt.get("endDateTime") else None
        
        # Safely get customer phone number
        phone = ""
        if appt.get("customers") and len(appt["customers"]) > 0:
            phone = appt["customers"][0].get("phone", "")
        
        return {
            "Business": business["name"],
            "Customer": appt.get("customerName", ""),
            "Email": appt.get("customerEmailAddress", ""),
            "Phone": phone,
            "Service": appt.get("serviceName", ""),
            "Start Date": start_dt,
            "End Date": end_dt,
            "Duration (min)": (end_dt - start_dt).total_seconds() / 60 if end_dt else 0,
            "Status": get_appointment_status(appt),
            "Notes": appt.get("customerNotes", ""),
            "ID": appt.get("id", ""),
            "Source": "Booking"
        }
    except Exception as e:
        st.error(f"Error processing appointment: {str(e)}")
        return None

def get_appointment_status(appt):
    """Determine appointment status"""
    if appt.get("status") == "cancelled":
        return "Cancelled"
    if appt.get("completedDateTime"):
        return "Completed"
    return "Scheduled"