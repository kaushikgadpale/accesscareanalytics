import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from config import LOCAL_TZ
from azure.identity import ClientSecretCredential
import os
from dotenv import load_dotenv
from msgraph import GraphServiceClient
from msgraph.generated.solutions.booking_businesses.booking_businesses_request_builder import BookingBusinessesRequestBuilder
from msgraph.generated.solutions.booking_businesses.item.calendar_view.calendar_view_request_builder import CalendarViewRequestBuilder
from kiota_abstractions.base_request_configuration import RequestConfiguration

load_dotenv()

def get_graph_client():
    """Initialize Microsoft Graph client using Azure authentication"""
    try:
        credential = ClientSecretCredential(
            tenant_id=os.getenv('TENANT_ID'),
            client_id=os.getenv('CLIENT_ID'),
            client_secret=os.getenv('CLIENT_SECRET')
        )
        # Initialize the Graph client
        return GraphServiceClient(credentials=credential)
    except Exception as e:
        st.error(f"Failed to initialize Graph client: {str(e)}")
        return None

def parse_iso_duration(duration_str):
    """Parse ISO 8601 duration string to minutes"""
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

def fetch_businesses():
    """Fetch all booking businesses using Microsoft Graph SDK"""
    try:
        graph_client = get_graph_client()
        if not graph_client:
            st.warning("Failed to initialize Graph client")
            return []
            
        result = graph_client.solutions.booking_businesses.get()
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

def fetch_appointments(businesses, start_date, end_date, max_results):
    """Fetch appointments using Microsoft Graph SDK"""
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
        businesses = fetch_businesses()
    
    graph_client = get_graph_client()
    if not graph_client:
        st.error("Failed to initialize Graph client")
        return []

    for idx, business in enumerate(businesses):
        try:
            # Get business ID and name
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
            
            # Use calendarView with SDK
            query_params = CalendarViewRequestBuilder.CalendarViewRequestBuilderGetQueryParameters(
                start=start_str,
                end=end_str,
                top=max_results
            )
            
            request_configuration = RequestConfiguration(
                query_parameters=query_params
            )

            result = graph_client.solutions.booking_businesses.by_booking_business_id(business_id).calendar_view.get(
                request_configuration=request_configuration
            )
            
            if not result:
                continue
                
            for appt in result.value:
                try:
                    start_dt = datetime.fromisoformat(appt.start_date_time.dateTime.replace('Z', '+00:00')).astimezone(LOCAL_TZ)
                    end_dt = None
                    if appt.end_date_time:
                        end_dt = datetime.fromisoformat(appt.end_date_time.dateTime.replace('Z', '+00:00')).astimezone(LOCAL_TZ)
                    
                    # Get customer information
                    customer_info = {
                        "phone": "",
                        "location": None,
                        "timezone": "",
                        "notes": "",
                        "email": appt.customer_email_address or ''
                    }
                    
                    if appt.customers and len(appt.customers) > 0:
                        customer = appt.customers[0]
                        customer_info.update({
                            "phone": customer.phone or '',
                            "location": customer.customer_location,
                            "timezone": customer.customer_time_zone or '',
                            "notes": appt.customer_notes or ''
                        })
                    
                    # Get cancellation details
                    cancellation_info = None
                    if appt.cancellation_date_time:
                        cancellation_info = {
                            "datetime": datetime.fromisoformat(appt.cancellation_date_time.dateTime.replace('Z', '+00:00')).astimezone(LOCAL_TZ),
                            "reason": appt.cancellation_reason or '',
                            "reason_text": getattr(appt, 'cancellation_reason_text', ''),
                            "notification_sent": getattr(appt, 'cancellation_notification_sent', False)
                        }
                    
                    # Get service details
                    service_info = {
                        "id": appt.service_id or '',
                        "name": appt.service_name or '',
                        "location": appt.service_location,
                        "notes": appt.service_notes or '',
                        "price": getattr(appt, 'price', 0),
                        "price_type": getattr(appt, 'price_type', '')
                    }
                    
                    # Get appointment metadata
                    created_dt = datetime.fromisoformat(appt.created_date_time.replace('Z', '+00:00')).astimezone(LOCAL_TZ) if appt.created_date_time else None
                    last_updated_dt = datetime.fromisoformat(appt.last_updated_date_time.replace('Z', '+00:00')).astimezone(LOCAL_TZ) if appt.last_updated_date_time else None
                    
                    appointments.append({
                        "Business": business_name,
                        "Customer": appt.customer_name or '',
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
                        "Notes": appt.customer_notes or '',
                        "ID": appt.id or '',
                        "Source": "Booking",
                        "Is Online": getattr(appt, 'is_location_online', False),
                        "Join URL": getattr(appt, 'join_web_url', ''),
                        "SMS Enabled": getattr(appt, 'sms_notifications_enabled', False),
                        "Staff Members": ", ".join(appt.staff_member_ids) if appt.staff_member_ids else '',
                        "Additional Info": getattr(appt, 'additional_information', ''),
                        "Appointment Label": getattr(appt, 'appointment_label', ''),
                        "Self Service ID": getattr(appt, 'self_service_appointment_id', ''),
                        "Cancellation DateTime": cancellation_info["datetime"] if cancellation_info else None,
                        "Cancellation Reason": cancellation_info["reason"] if cancellation_info else "",
                        "Cancellation Details": cancellation_info["reason_text"] if cancellation_info else "",
                        "Cancellation Notification Sent": cancellation_info["notification_sent"] if cancellation_info else False,
                        "Customer Can Manage": getattr(appt, 'is_customer_allowed_to_manage_booking', False),
                        "Opt Out of Email": getattr(appt, 'opt_out_of_customer_email', False),
                        "Pre Buffer (min)": parse_iso_duration(getattr(appt, 'pre_buffer', '')),
                        "Post Buffer (min)": parse_iso_duration(getattr(appt, 'post_buffer', ''))
                    })
                except (KeyError, ValueError) as e:
                    st.warning(f"Skipping malformed appointment: {str(e)}")
                    continue
                
            progress_bar.progress((idx + 1) / len(businesses))
        except Exception as e:
            st.error(f"Error fetching appointments for {business_name}: {str(e)}")
    
    progress_bar.empty()
    return appointments

def get_appointment_status(appt):
    """Determine appointment status"""
    if getattr(appt, 'status', '') == 'cancelled':
        return "Cancelled"
    if getattr(appt, 'completed_date_time', None):
        return "Completed"
    return "Scheduled"