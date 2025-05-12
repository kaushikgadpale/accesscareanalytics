import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from config import LOCAL_TZ
from azure.identity import ClientSecretCredential
import os
from dotenv import load_dotenv
from msgraph import GraphServiceClient
from msgraph.generated.solutions.booking_businesses.booking_businesses_request_builder import BookingBusinessesRequestBuilder
from msgraph.generated.solutions.booking_businesses.item.calendar_view.calendar_view_request_builder import CalendarViewRequestBuilder
from kiota_abstractions.base_request_configuration import RequestConfiguration
import asyncio

load_dotenv()

async def get_graph_client():
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

async def fetch_businesses():
    """Fetch all booking businesses using Microsoft Graph SDK"""
    try:
        graph_client = await get_graph_client()
        if not graph_client:
            st.warning("Failed to initialize Graph client")
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

async def fetch_business_details(business_id):
    """Fetch detailed information about a booking business"""
    try:
        graph_client = await get_graph_client()
        if not graph_client:
            return None
            
        result = await graph_client.solutions.booking_businesses.by_booking_business_id(business_id).get()
        if not result:
            return None
            
        return {
            "id": result.id,
            "name": result.display_name,
            "business_type": result.business_type,
            "default_currency_iso": result.default_currency_iso,
            "email": result.email,
            "phone": result.phone,
            "website_url": result.website_url,
            "scheduling_policy": {
                "allow_staff_selection": result.scheduling_policy.allow_staff_selection if hasattr(result, 'scheduling_policy') else False,
                "time_slot_interval": result.scheduling_policy.time_slot_interval if hasattr(result, 'scheduling_policy') else 30,
                "minimum_lead_time": result.scheduling_policy.minimum_lead_time if hasattr(result, 'scheduling_policy') else 0,
                "maximum_advance": result.scheduling_policy.maximum_advance if hasattr(result, 'scheduling_policy') else 30
            },
            "business_hours": result.business_hours if hasattr(result, 'business_hours') else [],
            "services": result.services if hasattr(result, 'services') else [],
            "staff_members": result.staff_members if hasattr(result, 'staff_members') else []
        }
    except Exception as e:
        st.error(f"Failed to fetch business details: {str(e)}")
        return None

async def fetch_appointments(businesses, start_date, end_date, max_results):
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
        businesses = await fetch_businesses()
    
    graph_client = await get_graph_client()
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
                all_businesses = await fetch_businesses()
                business_info = next((b for b in all_businesses if b["name"] == business), None)
                if not business_info:
                    st.warning(f"Could not find business ID for {business}")
                    continue
                business_id = business_info["id"]
                business_name = business
            
            # Fetch business details
            business_details = await fetch_business_details(business_id)
            
            # Use calendarView with SDK
            query_params = CalendarViewRequestBuilder.CalendarViewRequestBuilderGetQueryParameters(
                start=start_str,
                end=end_str,
                top=max_results
            )
            
            request_configuration = RequestConfiguration(
                query_parameters=query_params
            )

            result = await graph_client.solutions.booking_businesses.by_booking_business_id(business_id).calendar_view.get(
                request_configuration=request_configuration
            )
            
            if not result:
                st.write(f"No appointments found for {business_name}")
                continue
                
            st.write(f"Processing {len(result.value)} appointments for {business_name}")
            for appt in result.value:
                try:
                    # Get customer information
                    customer_info = {
                        "phone": getattr(appt, 'customer_phone', ''),
                        "location": None,
                        "timezone": getattr(appt, 'customer_time_zone', ''),
                        "notes": getattr(appt, 'customer_notes', ''),
                        "email": getattr(appt, 'customer_email_address', '')
                    }
                    
                    # Process customer form answers
                    form_answers = {}
                    if appt.customers and len(appt.customers) > 0:
                        customer = appt.customers[0]
                        if hasattr(customer, 'custom_question_answers'):
                            for answer in customer.custom_question_answers:
                                question = getattr(answer, 'question', '')
                                ans = getattr(answer, 'answer', '')
                                form_answers[question] = ans
                    
                    # Get service details
                    service_info = {
                        "id": getattr(appt, 'service_id', ''),
                        "name": getattr(appt, 'service_name', ''),
                        "location": None,
                        "notes": getattr(appt, 'service_notes', ''),
                        "price": float(getattr(appt, 'price', 0)),
                        "price_type": str(getattr(appt, 'price_type', 'notSet'))
                    }
                    
                    # Get service location
                    if hasattr(appt, 'service_location'):
                        service_location = appt.service_location
                        service_info["location"] = {
                            "name": getattr(service_location, 'display_name', ''),
                            "address": getattr(service_location, 'address', None)
                        }
                    
                    # Get appointment metadata
                    start_dt = datetime.fromisoformat(appt.start_date_time.date_time.replace('Z', '+00:00')).astimezone(LOCAL_TZ)
                    end_dt = None
                    if appt.end_date_time:
                        end_dt = datetime.fromisoformat(appt.end_date_time.date_time.replace('Z', '+00:00')).astimezone(LOCAL_TZ)
                    
                    created_dt = None
                    if hasattr(appt, 'created_date_time'):
                        created_dt = appt.created_date_time.astimezone(LOCAL_TZ)
                    
                    last_updated_dt = None
                    if hasattr(appt, 'last_updated_date_time'):
                        last_updated_dt = appt.last_updated_date_time.astimezone(LOCAL_TZ)
                    
                    # Get cancellation details
                    cancellation_info = None
                    if hasattr(appt, 'cancellation_date_time') and appt.cancellation_date_time:
                        cancellation_info = {
                            "datetime": datetime.fromisoformat(appt.cancellation_date_time.date_time.replace('Z', '+00:00')).astimezone(LOCAL_TZ),
                            "reason": getattr(appt, 'cancellation_reason', ''),
                            "reason_text": getattr(appt, 'cancellation_reason_text', ''),
                            "notification_sent": getattr(appt, 'cancellation_notification_sent', False)
                        }
                    
                    # Calculate duration in minutes
                    duration_minutes = 0
                    if end_dt and start_dt:
                        duration_minutes = (end_dt - start_dt).total_seconds() / 60
                    
                    # Get staff members
                    staff_members = []
                    if hasattr(appt, 'staff_member_ids'):
                        staff_members = appt.staff_member_ids
                    
                    appointment_data = {
                        "Business": business_name,
                        "Customer": getattr(appt, 'customer_name', ''),
                        "Email": customer_info["email"],
                        "Phone": customer_info["phone"],
                        "Customer Location": str(customer_info["location"]) if customer_info["location"] else "",
                        "Customer Timezone": customer_info["timezone"],
                        "Customer Notes": customer_info["notes"],
                        "Service": service_info["name"],
                        "Service ID": service_info["id"],
                        "Service Location": str(service_info["location"]["name"]) if service_info["location"] else "",
                        "Service Notes": service_info["notes"],
                        "Price": service_info["price"],
                        "Price Type": service_info["price_type"],
                        "Start Date": start_dt,
                        "End Date": end_dt,
                        "Created Date": created_dt,
                        "Last Updated": last_updated_dt,
                        "Duration (min)": duration_minutes,
                        "Status": get_appointment_status(appt),
                        "Notes": getattr(appt, 'customer_notes', ''),
                        "ID": getattr(appt, 'id', ''),
                        "Source": "Booking",
                        "Is Online": getattr(appt, 'is_location_online', False),
                        "Join URL": getattr(appt, 'join_web_url', ''),
                        "SMS Enabled": getattr(appt, 'sms_notifications_enabled', False),
                        "Staff Members": ", ".join(staff_members) if staff_members else '',
                        "Additional Info": getattr(appt, 'additional_information', ''),
                        "Appointment Label": getattr(appt, 'appointment_label', ''),
                        "Self Service ID": getattr(appt, 'self_service_appointment_id', ''),
                        "Customer Can Manage": getattr(appt, 'is_customer_allowed_to_manage_booking', False),
                        "Opt Out of Email": getattr(appt, 'opt_out_of_customer_email', False),
                        "Pre Buffer (min)": getattr(appt, 'pre_buffer', timedelta(0)).total_seconds() / 60,
                        "Post Buffer (min)": getattr(appt, 'post_buffer', timedelta(0)).total_seconds() / 60,
                        "Filled Attendees": getattr(appt, 'filled_attendees_count', 0),
                        "Max Attendees": getattr(appt, 'maximum_attendees_count', 0),
                        "Cancellation DateTime": cancellation_info["datetime"] if cancellation_info else None,
                        "Cancellation Reason": cancellation_info["reason"] if cancellation_info else "",
                        "Cancellation Details": cancellation_info["reason_text"] if cancellation_info else "",
                        "Cancellation Notification Sent": cancellation_info["notification_sent"] if cancellation_info else False,
                        "Business Type": business_details["business_type"] if business_details else "",
                        "Business Email": business_details["email"] if business_details else "",
                        "Business Phone": business_details["phone"] if business_details else "",
                        "Business Website": business_details["website_url"] if business_details else ""
                    }
                    
                    # Add form answers to appointment data
                    for question, answer in form_answers.items():
                        appointment_data[f"Form: {question}"] = answer
                    
                    appointments.append(appointment_data)
                    st.write(f"Successfully processed appointment for {appointment_data['Customer']} at {appointment_data['Start Date']}")
                except (KeyError, ValueError) as e:
                    st.warning(f"Skipping malformed appointment: {str(e)}")
                    continue
                
            progress_bar.progress((idx + 1) / len(businesses))
            st.write(f"Completed processing {business_name}")
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