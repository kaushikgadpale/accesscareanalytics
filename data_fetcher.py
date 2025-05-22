import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from config import LOCAL_TZ
import os
import requests
import msal
import time
import json
import asyncio
from dotenv import load_dotenv

# Try to load from .env file
load_dotenv()

# Fallback: If environment variables are not loaded, try to load from env.txt
tenant_id = os.getenv('TENANT_ID')
client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')

if not tenant_id or not client_id or not client_secret:
    try:
        # Read env.txt and parse variables
        with open('env.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        # Set environment variable
                        os.environ[key] = value
        
        # Try getting the variables again
        tenant_id = os.getenv('TENANT_ID')
        client_id = os.getenv('CLIENT_ID')
        client_secret = os.getenv('CLIENT_SECRET')
        
        if not tenant_id or not client_id or not client_secret:
            st.error("Failed to load all required credentials from env.txt")
    except Exception as e:
        st.error(f"Error loading variables from env.txt: {str(e)}")

# Check if environment variables are loaded
if not tenant_id or not client_id or not client_secret:
    st.error("Missing environment variables for Microsoft Graph authentication. Please check your .env file or env.txt.")

async def get_access_token():
    """Get access token for Microsoft Graph API"""
    try:
        # Get credentials
        tenant = os.getenv('TENANT_ID')
        client = os.getenv('CLIENT_ID')
        secret = os.getenv('CLIENT_SECRET')
        
        if not tenant or not client or not secret:
            st.error("Missing required environment variables for authentication")
            return None
            
        # Use msal directly to get a token
        app = msal.ConfidentialClientApplication(
            client_id=client,
            client_credential=secret,
            authority=f"https://login.microsoftonline.com/{tenant}"
        )
        
        # Get token directly 
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        
        if "access_token" not in result:
            st.error(f"Failed to get access token: {result.get('error_description', '')}")
            return None
            
        return result["access_token"]
    except Exception as e:
        st.error(f"Failed to get access token: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return None

async def make_graph_request(endpoint, method="GET", params=None, data=None):
    """Make a request to the Microsoft Graph API"""
    try:
        # Get access token
        token = await get_access_token()
        if not token:
            return None
            
        # Set up headers
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Construct full URL
        base_url = "https://graph.microsoft.com/v1.0"
        url = f"{base_url}{endpoint}"
        
        # Make the request using requests library
        response = await asyncio.to_thread(
            lambda: requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data
            )
        )
        
        # Check if request was successful
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Graph API request failed: {response.status_code} {response.text}")
            return None
    except Exception as e:
        st.error(f"Error making Graph API request: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
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
    """Fetch all booking businesses using Microsoft Graph REST API"""
    try:
        with st.spinner("Fetching booking businesses..."):
            # Make a direct request to the booking businesses endpoint
            result = await make_graph_request("/solutions/bookingBusinesses")
            
            if not result:
                st.warning("No businesses found in your Microsoft Bookings account")
                return []
                
            if "value" not in result:
                st.warning("API response does not contain 'value' attribute")
                return []
                
            businesses = [
                {"id": biz["id"], "name": biz["displayName"]} 
                for biz in result["value"]
            ]
            
            st.success(f"Successfully fetched {len(businesses)} booking businesses")
            return businesses
    except Exception as e:
        st.error(f"Failed to fetch businesses: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return []

async def fetch_business_details(business_id):
    """Fetch detailed information about a booking business"""
    try:
        # Make a direct request to the specific booking business
        result = await make_graph_request(f"/solutions/bookingBusinesses/{business_id}")
        
        if not result:
            return None
            
        return {
            "id": result.get('id', ''),
            "name": result.get('displayName', ''),
            "business_type": result.get('businessType', ''),
            "default_currency_iso": result.get('defaultCurrencyIso', ''),
            "email": result.get('email', ''),
            "phone": result.get('phone', ''),
            "website_url": result.get('websiteUrl', ''),
            "scheduling_policy": {
                "allow_staff_selection": result.get('schedulingPolicy', {}).get('allowStaffSelection', False),
                "time_slot_interval": result.get('schedulingPolicy', {}).get('timeSlotInterval', 30),
                "minimum_lead_time": result.get('schedulingPolicy', {}).get('minimumLeadTime', 0),
                "maximum_advance": result.get('schedulingPolicy', {}).get('maximumAdvance', 30)
            },
            "business_hours": result.get('businessHours', []),
            "services": result.get('services', []),
            "staff_members": result.get('staffMembers', [])
        }
    except Exception as e:
        # Create a default minimal business details object instead of failing completely
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
    """Fetch appointments using Microsoft Graph API"""
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
    
    # Ensure businesses is a list
    if not isinstance(businesses, list):
        businesses = [businesses]

    for idx, business in enumerate(businesses):
        try:
            # Get business ID and name
            if isinstance(business, dict) and "id" in business and "name" in business:
                business_id = business["id"]
                business_name = business["name"]
            elif isinstance(business, str):
                # If it's just a string ID, fetch the business details
                all_businesses = await fetch_businesses()
                
                # Try to find by ID first
                try:
                    business_info = next((b for b in all_businesses if b["id"] == business), None)
                    if not business_info:
                        # Try to find by name
                        business_info = next((b for b in all_businesses if b["name"] == business), None)
                    
                    if not business_info:
                        continue
                        
                    business_id = business_info["id"]
                    business_name = business_info["name"]
                except Exception as lookup_err:
                    st.error(f"Error looking up business details: {str(lookup_err)}")
                    continue
            else:
                continue
            
            # Fetch business details
            business_details = await fetch_business_details(business_id)
            
            # Build the calendar view URL with query parameters
            endpoint = f"/solutions/bookingBusinesses/{business_id}/calendarView"
            params = {
                "start": start_str,
                "end": end_str,
                "$top": max_results
            }
            
            # Make the request
            result = await make_graph_request(endpoint, params=params)
            
            if not result or "value" not in result:
                continue
                
            appointments_data = result["value"]
            appointment_count = len(appointments_data)
            
            # Create a progress bar for this business's appointments
            appt_progress = st.progress(0)
            
            for appt_idx, appt in enumerate(appointments_data):
                try:
                    # Update progress for this business's appointments
                    appt_progress.progress((appt_idx + 1) / appointment_count)
                    
                    # Get customer information
                    customer_info = {
                        "phone": appt.get('customerPhone', ''),
                        "location": None,
                        "timezone": appt.get('customerTimeZone', ''),
                        "notes": appt.get('customerNotes', ''),
                        "email": appt.get('customerEmailAddress', '')
                    }
                    
                    # Process customer form answers
                    form_answers = {}
                    customers = appt.get('customers', [])
                    if customers and len(customers) > 0:
                        customer = customers[0]
                        custom_answers = customer.get('customQuestionAnswers', [])
                        for answer in custom_answers:
                            question = answer.get('question', '')
                            ans = answer.get('answer', '')
                            form_answers[question] = ans
                    
                    # Get service details
                    service_info = {
                        "id": appt.get('serviceId', ''),
                        "name": appt.get('serviceName', ''),
                        "location": None,
                        "notes": appt.get('serviceNotes', ''),
                        "price": float(appt.get('price', 0)),
                        "price_type": str(appt.get('priceType', 'notSet'))
                    }
                    
                    # Get service location
                    service_location = appt.get('serviceLocation', {})
                    if service_location:
                        service_info["location"] = {
                            "name": service_location.get('displayName', ''),
                            "address": service_location.get('address', None)
                        }
                    
                    # Get appointment metadata
                    start_dt = None
                    if 'startDateTime' in appt and appt['startDateTime']:
                        try:
                            date_time_str = appt['startDateTime'].get('dateTime', '')
                            if date_time_str:
                                start_dt = datetime.fromisoformat(date_time_str.replace('Z', '+00:00')).astimezone(LOCAL_TZ)
                        except Exception:
                            # Use a fallback date if possible
                            if 'createdDateTime' in appt and appt['createdDateTime']:
                                created_dt_str = appt['createdDateTime']
                                try:
                                    start_dt = datetime.fromisoformat(created_dt_str.replace('Z', '+00:00')).astimezone(LOCAL_TZ)
                                except:
                                    start_dt = datetime.now(LOCAL_TZ)
                            else:
                                start_dt = datetime.now(LOCAL_TZ)
                    else:
                        # Default to current time if no start time found
                        start_dt = datetime.now(LOCAL_TZ)
                    
                    end_dt = None
                    if 'endDateTime' in appt and appt['endDateTime']:
                        try:
                            date_time_str = appt['endDateTime'].get('dateTime', '')
                            if date_time_str:
                                end_dt = datetime.fromisoformat(date_time_str.replace('Z', '+00:00')).astimezone(LOCAL_TZ)
                        except Exception:
                            # Calculate an estimated end time (add 30 minutes to start)
                            if start_dt:
                                end_dt = start_dt + timedelta(minutes=30)
                    elif start_dt:
                        # Default to start + 30 minutes if no end time found
                        end_dt = start_dt + timedelta(minutes=30)
                    
                    created_dt = None
                    if 'createdDateTime' in appt:
                        try:
                            created_dt_str = appt['createdDateTime']
                            created_dt = datetime.fromisoformat(created_dt_str.replace('Z', '+00:00')).astimezone(LOCAL_TZ)
                        except Exception:
                            created_dt = datetime.now(LOCAL_TZ)
                    
                    last_updated_dt = None
                    if 'lastUpdatedDateTime' in appt:
                        try:
                            updated_dt_str = appt['lastUpdatedDateTime']
                            last_updated_dt = datetime.fromisoformat(updated_dt_str.replace('Z', '+00:00')).astimezone(LOCAL_TZ)
                        except Exception:
                            # Use created date as fallback for last updated
                            last_updated_dt = created_dt if created_dt else datetime.now(LOCAL_TZ)
                    
                    # Get cancellation details
                    cancellation_info = None
                    if 'cancellationDateTime' in appt and appt['cancellationDateTime']:
                        try:
                            date_time_str = appt['cancellationDateTime'].get('dateTime', '')
                            if date_time_str:
                                cancellation_datetime = datetime.fromisoformat(date_time_str.replace('Z', '+00:00')).astimezone(LOCAL_TZ)
                                cancellation_info = {
                                    "datetime": cancellation_datetime,
                                    "reason": appt.get('cancellationReason', ''),
                                    "reason_text": appt.get('cancellationReasonText', ''),
                                    "notification_sent": appt.get('cancellationNotificationSent', False)
                                }
                        except Exception:
                            # Use a default cancellation info if status shows cancelled
                            if appt.get('status', '').lower() == 'cancelled':
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
                    staff_members = appt.get('staffMemberIds', [])
                    
                    appointment_data = {
                        "Business": business_name,
                        "Customer": appt.get('customerName', ''),
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
                        "Notes": appt.get('customerNotes', ''),
                        "ID": appt.get('id', ''),
                        "Source": "Booking",
                        "Is Online": appt.get('isLocationOnline', False),
                        "Join URL": appt.get('joinWebUrl', ''),
                        "SMS Enabled": appt.get('smsNotificationsEnabled', False),
                        "Staff Members": ", ".join(staff_members) if staff_members else '',
                        "Additional Info": appt.get('additionalInformation', ''),
                        "Appointment Label": appt.get('appointmentLabel', ''),
                        "Self Service ID": appt.get('selfServiceAppointmentId', ''),
                        "Customer Can Manage": appt.get('isCustomerAllowedToManageBooking', False),
                        "Opt Out of Email": appt.get('optOutOfCustomerEmail', False),
                        "Pre Buffer (min)": parse_buffer_duration(appt.get('preBuffer', '')),
                        "Post Buffer (min)": parse_buffer_duration(appt.get('postBuffer', '')),
                        "Filled Attendees": appt.get('filledAttendeesCount', 0),
                        "Max Attendees": appt.get('maximumAttendeesCount', 0),
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
                except (KeyError, ValueError):
                    continue
            
            # Clear the appointment progress bar
            appt_progress.empty()        
            progress_bar.progress((idx + 1) / len(businesses))
        except Exception as e:
            st.error(f"Error fetching appointments for business: {str(e)}")
    
    progress_bar.empty()
    return appointments

def parse_buffer_duration(duration_str):
    """Parse buffer duration (could be in ISO 8601 format or in minutes)"""
    if not duration_str:
        return 0
    
    # If it's already a number, return it
    if isinstance(duration_str, (int, float)):
        return duration_str
        
    # If it's an ISO 8601 duration, parse it
    if isinstance(duration_str, str) and duration_str.startswith('P'):
        return parse_iso_duration(duration_str)
        
    # Default to 0
    return 0

def get_appointment_status(appt):
    """Determine appointment status"""
    status = appt.get('status', '').lower()
    if status == 'cancelled':
        return "Cancelled"
    if 'completedDateTime' in appt and appt['completedDateTime']:
        return "Completed"
    return "Scheduled"