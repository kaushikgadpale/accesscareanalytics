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
            "id": getattr(result, 'id', ''),
            "name": getattr(result, 'display_name', ''),
            "business_type": getattr(result, 'business_type', ''),
            "default_currency_iso": getattr(result, 'default_currency_iso', ''),
            "email": getattr(result, 'email', ''),
            "phone": getattr(result, 'phone', ''),
            "website_url": getattr(result, 'website_url', ''),
            "scheduling_policy": {
                "allow_staff_selection": result.scheduling_policy.allow_staff_selection if hasattr(result, 'scheduling_policy') and hasattr(result.scheduling_policy, 'allow_staff_selection') else False,
                "time_slot_interval": result.scheduling_policy.time_slot_interval if hasattr(result, 'scheduling_policy') and hasattr(result.scheduling_policy, 'time_slot_interval') else 30,
                "minimum_lead_time": result.scheduling_policy.minimum_lead_time if hasattr(result, 'scheduling_policy') and hasattr(result.scheduling_policy, 'minimum_lead_time') else 0,
                "maximum_advance": result.scheduling_policy.maximum_advance if hasattr(result, 'scheduling_policy') and hasattr(result.scheduling_policy, 'maximum_advance') else 30
            },
            "business_hours": result.business_hours if hasattr(result, 'business_hours') else [],
            "services": result.services if hasattr(result, 'services') else [],
            "staff_members": result.staff_members if hasattr(result, 'staff_members') else []
        }
    except Exception as e:
        # Create a default minimal business details object instead of failing completely
        st.warning(f"Error fetching business details (ID: {business_id}): {str(e)}")
        return {
            "id": business_id,
            "name": "",
            "business_type": "",
            "default_currency_iso": "",
            "email": "",
            "phone": "",
            "website_url": "",
            "scheduling_policy": {
                "allow_staff_selection": False,
                "time_slot_interval": 30,
                "minimum_lead_time": 0,
                "maximum_advance": 30
            },
            "business_hours": [],
            "services": [],
            "staff_members": []
        }

async def fetch_appointments(businesses, start_date, end_date, max_results):
    """Fetch appointments using Microsoft Graph SDK"""
    appointments = []
    progress_bar = st.progress(0)
    
    # Debug information
    st.write(f"Debug: Type of businesses = {type(businesses)}")
    if businesses:
        if isinstance(businesses, list):
            st.write(f"Debug: Number of businesses = {len(businesses)}")
            if len(businesses) > 0:
                st.write(f"Debug: First business type = {type(businesses[0])}")
                st.write(f"Debug: First business value = {businesses[0]}")
        else:
            st.write(f"Debug: Single business type = {type(businesses)}")
            st.write(f"Debug: Business value = {businesses}")
    
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
    
    # Ensure businesses is a list
    if not isinstance(businesses, list):
        businesses = [businesses]
    
    graph_client = await get_graph_client()
    if not graph_client:
        st.error("Failed to initialize Graph client")
        return []

    for idx, business in enumerate(businesses):
        try:
            # Get business ID and name
            if isinstance(business, dict) and "id" in business and "name" in business:
                business_id = business["id"]
                business_name = business["name"]
                st.write(f"Debug: Processing business from dict: {business_name}")
            elif isinstance(business, str):
                # If it's just a string ID, fetch the business details
                st.write(f"Debug: Processing business from string ID: {business}")
                all_businesses = await fetch_businesses()
                
                # Try to find by ID first
                try:
                    business_info = next((b for b in all_businesses if b["id"] == business), None)
                    if not business_info:
                        # Try to find by name
                        business_info = next((b for b in all_businesses if b["name"] == business), None)
                    
                    if not business_info:
                        st.warning(f"Could not find business information for {business}")
                        continue
                        
                    business_id = business_info["id"]
                    business_name = business_info["name"]
                    st.write(f"Debug: Found business details: {business_name} ({business_id})")
                except Exception as lookup_err:
                    st.error(f"Error looking up business details: {str(lookup_err)}")
                    st.write(f"Debug: all_businesses = {all_businesses}")
                    continue
            else:
                st.warning(f"Invalid business format: {business} of type {type(business)}")
                continue
            
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

            st.write(f"Debug: Fetching calendar view for business ID: {business_id}")
            result = await graph_client.solutions.booking_businesses.by_booking_business_id(business_id).calendar_view.get(
                request_configuration=request_configuration
            )
            
            if not result:
                st.write(f"No appointments found for {business_name}")
                continue
                
            appointment_count = len(result.value)
            st.write(f"Processing {appointment_count} appointments for {business_name}")
            
            # Create a progress bar for this business's appointments
            appt_progress = st.progress(0)
            
            for appt_idx, appt in enumerate(result.value):
                try:
                    # Update progress for this business's appointments
                    appt_progress.progress((appt_idx + 1) / appointment_count)
                    
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
                    start_dt = None
                    if hasattr(appt, 'start_date_time') and appt.start_date_time:
                        try:
                            date_time_str = getattr(appt.start_date_time, 'date_time', '')
                            if date_time_str:
                                start_dt = datetime.fromisoformat(date_time_str.replace('Z', '+00:00')).astimezone(LOCAL_TZ)
                        except Exception as e:
                            st.warning(f"Error parsing start date time: {str(e)}")
                            # Use a fallback date if possible
                            if hasattr(appt, 'created_date_time') and appt.created_date_time:
                                start_dt = appt.created_date_time.astimezone(LOCAL_TZ)
                            else:
                                start_dt = datetime.now(LOCAL_TZ)
                    else:
                        # Default to current time if no start time found
                        start_dt = datetime.now(LOCAL_TZ)
                    
                    end_dt = None
                    if hasattr(appt, 'end_date_time') and appt.end_date_time:
                        try:
                            date_time_str = getattr(appt.end_date_time, 'date_time', '')
                            if date_time_str:
                                end_dt = datetime.fromisoformat(date_time_str.replace('Z', '+00:00')).astimezone(LOCAL_TZ)
                        except Exception as e:
                            st.warning(f"Error parsing end date time: {str(e)}")
                            # Calculate an estimated end time (add 30 minutes to start)
                            if start_dt:
                                end_dt = start_dt + timedelta(minutes=30)
                    elif start_dt:
                        # Default to start + 30 minutes if no end time found
                        end_dt = start_dt + timedelta(minutes=30)
                    
                    created_dt = None
                    if hasattr(appt, 'created_date_time'):
                        try:
                            created_dt = appt.created_date_time.astimezone(LOCAL_TZ)
                        except Exception as e:
                            st.warning(f"Error parsing created date time: {str(e)}")
                            created_dt = datetime.now(LOCAL_TZ)
                    
                    last_updated_dt = None
                    if hasattr(appt, 'last_updated_date_time'):
                        try:
                            last_updated_dt = appt.last_updated_date_time.astimezone(LOCAL_TZ)
                        except Exception as e:
                            st.warning(f"Error parsing last updated date time: {str(e)}")
                            # Use created date as fallback for last updated
                            last_updated_dt = created_dt if created_dt else datetime.now(LOCAL_TZ)
                    
                    # Get cancellation details
                    cancellation_info = None
                    if hasattr(appt, 'cancellation_date_time') and appt.cancellation_date_time:
                        try:
                            date_time_str = getattr(appt.cancellation_date_time, 'date_time', '')
                            if date_time_str:
                                cancellation_datetime = datetime.fromisoformat(date_time_str.replace('Z', '+00:00')).astimezone(LOCAL_TZ)
                                cancellation_info = {
                                    "datetime": cancellation_datetime,
                                    "reason": getattr(appt, 'cancellation_reason', ''),
                                    "reason_text": getattr(appt, 'cancellation_reason_text', ''),
                                    "notification_sent": getattr(appt, 'cancellation_notification_sent', False)
                                }
                        except Exception as e:
                            st.warning(f"Error parsing cancellation date time: {str(e)}")
                            # Use a default cancellation info if status shows cancelled
                            if getattr(appt, 'status', '').lower() == 'cancelled':
                                cancellation_info = {
                                    "datetime": last_updated_dt or datetime.now(LOCAL_TZ),
                                    "reason": "Unknown",
                                    "reason_text": "",
                                    "notification_sent": False
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
                except (KeyError, ValueError) as e:
                    st.warning(f"Skipping malformed appointment: {str(e)}")
                    continue
            
            # Clear the appointment progress bar
            appt_progress.empty()        
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