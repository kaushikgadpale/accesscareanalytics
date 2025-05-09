import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from config import LOCAL_TZ
from msgraph import GraphServiceClient
from azure.identity import ClientSecretCredential
from kiota_abstractions.request_configuration import RequestConfiguration
import os
from dotenv import load_dotenv

load_dotenv()

def get_graph_client():
    """Initialize Microsoft Graph client"""
    try:
        credential = ClientSecretCredential(
            tenant_id=os.getenv('AZURE_TENANT_ID'),
            client_id=os.getenv('AZURE_CLIENT_ID'),
            client_secret=os.getenv('AZURE_CLIENT_SECRET')
        )
        return GraphServiceClient(credential)
    except Exception as e:
        st.error(f"Failed to initialize Graph client: {str(e)}")
        return None

def parse_iso_duration(duration_str):
    """Parse ISO 8601 duration string to minutes
    Examples:
    PT30M -> 30 (30 minutes)
    PT1H -> 60 (1 hour = 60 minutes)
    PT1H30M -> 90 (1 hour 30 minutes = 90 minutes)
    PT60S -> 1 (60 seconds = 1 minute)
    """
    if not duration_str:
        return 0
        
    minutes = 0
    # Remove PT prefix
    duration = duration_str.replace('PT', '')
    
    # Handle hours
    if 'H' in duration:
        hours, duration = duration.split('H')
        minutes += int(hours) * 60
    
    # Handle minutes
    if 'M' in duration:
        mins, duration = duration.split('M')
        minutes += int(mins)
    
    # Handle seconds
    if 'S' in duration:
        secs = duration.replace('S', '')
        minutes += int(secs) // 60
    
    return minutes

async def fetch_businesses():
    """Fetch all booking businesses using Microsoft Graph SDK"""
    try:
        graph_client = get_graph_client()
        if not graph_client:
            return []
        
        result = await graph_client.solutions.booking_businesses.get()
        if not result:
            st.warning("No businesses found in your Microsoft Bookings account")
            return []
            
        businesses = [
            {"id": biz.id, "name": biz.display_name} 
            for biz in result.value
        ]
        return businesses
    except Exception as e:
        st.error(f"Failed to fetch businesses: {str(e)}")
        return []

async def fetch_appointments(businesses, start_date, end_date, max_results):
    """Fetch appointments using Microsoft Graph SDK"""
    graph_client = get_graph_client()
    if not graph_client:
        return []
    
    appointments = []
    progress_bar = st.progress(0)
    
    # Format dates for API - ensure we use UTC
    start_datetime = datetime.combine(start_date, datetime.min.time()).astimezone(LOCAL_TZ).astimezone(pytz.UTC)
    end_datetime = datetime.combine(end_date, datetime.max.time()).astimezone(LOCAL_TZ).astimezone(pytz.UTC)
    
    # Ensure we're not using future dates
    now = datetime.now(LOCAL_TZ).astimezone(pytz.UTC)
    if start_datetime > now:
        start_datetime = now
    if end_datetime > now:
        end_datetime = now
    
    # Format datetime strings for API
    start_str = start_datetime.isoformat().replace('+00:00', 'Z')
    end_str = end_datetime.isoformat().replace('+00:00', 'Z')
    
    # First get all businesses if not provided
    if not businesses:
        businesses = await fetch_businesses()
    
    for idx, business in enumerate(businesses):
        try:
            # Get business ID and name
            if isinstance(business, dict):
                business_id = business["id"]
                business_name = business["name"]
            else:
                # If it's just a string (business name), fetch the ID
                all_businesses = await fetch_businesses()
                business_info = next((b for b in all_businesses if b["name"] == business), None)
                if not business_info:
                    st.warning(f"Could not find business ID for {business}")
                    continue
                business_id = business_info["id"]
                business_name = business
            
            # Use calendarView with SDK
            query_params = {
                'start': start_str,
                'end': end_str,
                '$top': max_results
            }
            
            result = await graph_client.solutions.booking_businesses.by_booking_business_id(business_id).calendar_view.get(
                request_configuration=RequestConfiguration(query_parameters=query_params)
            )
            
            if not result:
                continue
                
            for appt in result.value:
                try:
                    start_dt = datetime.fromisoformat(appt.start_date_time.date_time.replace('Z', '+00:00')).astimezone(LOCAL_TZ)
                    end_dt = None
                    if appt.end_date_time:
                        end_dt = datetime.fromisoformat(appt.end_date_time.date_time.replace('Z', '+00:00')).astimezone(LOCAL_TZ)
                    
                    # Get customer information
                    customer_info = {
                        "phone": "",
                        "location": None,
                        "timezone": "",
                        "notes": "",
                        "email": appt.customer_email_address or ""
                    }
                    
                    if appt.customers and len(appt.customers) > 0:
                        customer = appt.customers[0]
                        customer_info.update({
                            "phone": customer.phone or "",
                            "location": customer.customer_location,
                            "timezone": customer.customer_time_zone or "",
                            "notes": appt.customer_notes or ""
                        })
                    
                    # Get cancellation details
                    cancellation_info = None
                    if appt.cancellation_date_time:
                        cancellation_info = {
                            "datetime": datetime.fromisoformat(appt.cancellation_date_time.date_time.replace('Z', '+00:00')).astimezone(LOCAL_TZ),
                            "reason": appt.cancellation_reason or "",
                            "reason_text": appt.cancellation_reason_text or "",
                            "notification_sent": appt.cancellation_notification_sent or False
                        }
                    
                    # Get service details
                    service_info = {
                        "id": appt.service_id or "",
                        "name": appt.service_name or "",
                        "location": appt.service_location,
                        "notes": appt.service_notes or "",
                        "price": appt.price or 0,
                        "price_type": appt.price_type or ""
                    }
                    
                    # Get appointment metadata
                    created_dt = datetime.fromisoformat(appt.created_date_time.replace('Z', '+00:00')).astimezone(LOCAL_TZ) if appt.created_date_time else None
                    last_updated_dt = datetime.fromisoformat(appt.last_updated_date_time.replace('Z', '+00:00')).astimezone(LOCAL_TZ) if appt.last_updated_date_time else None
                    
                    appointments.append({
                        "Business": business_name,
                        "Customer": appt.customer_name or "",
                        "Email": customer_info["email"],
                        "Phone": customer_info["phone"],
                        "Customer Location": str(customer_info["location"]) if customer_info["location"] else "",
                        "Customer Timezone": customer_info["timezone"],
                        "Customer Notes": customer_info["notes"],
                        "Service": service_info["name"],
                        "Service ID": service_info["id"],
                        "Service Location": str(service_info["location"]) if service_info["location"] else "",
                        "Service Notes": service_info["notes"],
                        "Price": service_info["price"],
                        "Price Type": service_info["price_type"],
                        "Start Date": start_dt,
                        "End Date": end_dt,
                        "Created Date": created_dt,
                        "Last Updated": last_updated_dt,
                        "Duration (min)": (end_dt - start_dt).total_seconds() / 60 if end_dt else 0,
                        "Status": get_appointment_status(appt),
                        "Notes": appt.customer_notes or "",
                        "ID": appt.id or "",
                        "Source": "Booking",
                        "Is Online": appt.is_location_online or False,
                        "Join URL": appt.join_web_url or "",
                        "SMS Enabled": appt.sms_notifications_enabled or False,
                        "Staff Members": ", ".join(appt.staff_member_ids or []),
                        "Additional Info": appt.additional_information or "",
                        "Appointment Label": appt.appointment_label or "",
                        "Self Service ID": appt.self_service_appointment_id or "",
                        "Cancellation DateTime": cancellation_info["datetime"] if cancellation_info else None,
                        "Cancellation Reason": cancellation_info["reason"] if cancellation_info else "",
                        "Cancellation Details": cancellation_info["reason_text"] if cancellation_info else "",
                        "Cancellation Notification Sent": cancellation_info["notification_sent"] if cancellation_info else False,
                        "Customer Can Manage": appt.is_customer_allowed_to_manage_booking or False,
                        "Opt Out of Email": appt.opt_out_of_customer_email or False,
                        "Pre Buffer (min)": parse_iso_duration(appt.pre_buffer or ""),
                        "Post Buffer (min)": parse_iso_duration(appt.post_buffer or "")
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
    if getattr(appt, 'status', None) == 'cancelled':
        return "Cancelled"
    if getattr(appt, 'completed_date_time', None):
        return "Completed"
    return "Scheduled"