import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from config import LOCAL_TZ
import asyncio
import plotly.express as px
from auth import get_auth_headers
from data_fetcher import fetch_appointments, fetch_businesses, get_access_token, make_graph_request
import os

# Get mailboxes from environment variable
BOOKINGS_MAILBOXES = os.getenv("BOOKINGS_MAILBOXES", "").split(",")

async def get_graph_client():
    """Initialize Microsoft Graph client using Azure authentication"""
    # This is now a legacy function for compatibility
    # Return None and use direct API calls instead
    return None

async def fetch_businesses_for_appointments():
    """
    Fetch all businesses from Microsoft Bookings for appointments section
    Returns businesses organized for display with grouping by first two letters
    """
    try:
        # Fetch all businesses
        businesses = await fetch_businesses()
        
        if not businesses:
            return {}
            
        # Organize businesses by first two letters of name
        grouped_businesses = {}
        for business in businesses:
            name = business["name"]
            # Use first two letters for grouping (or just first letter if name is only one character)
            prefix = name[:2].upper() if len(name) > 1 else name[0].upper()
            
            if prefix not in grouped_businesses:
                grouped_businesses[prefix] = []
            
            grouped_businesses[prefix].append(business)
        
        # Sort the groups and businesses within each group
        sorted_groups = {}
        for prefix in sorted(grouped_businesses.keys()):
            sorted_groups[prefix] = sorted(grouped_businesses[prefix], key=lambda x: x["name"])
            
        return sorted_groups
    except Exception as e:
        st.error(f"Failed to fetch businesses: {str(e)}")
        return {}

async def fetch_bookings_data(start_date, end_date, max_results=500, selected_businesses=None):
    """Fetch bookings data for the specified date range"""
    try:
        # Use provided selected businesses if available
        businesses = selected_businesses
        
        # Handle None or empty list case
        if businesses is None or (isinstance(businesses, list) and len(businesses) == 0):
            businesses = await fetch_businesses()
            if not businesses:
                st.warning("No businesses found in your Microsoft Bookings account")
                return []
        
        # Ensure businesses is a list
        if not isinstance(businesses, list):
            businesses = [businesses]
            
        # If businesses are just IDs (strings), convert them to proper format for fetch_appointments
        processed_businesses = []
        try:
            if businesses and isinstance(businesses[0], str):
                # These are likely just IDs, fetch the full business information
                all_business_details = await fetch_businesses()
                
                if not all_business_details:
                    st.warning("Failed to fetch business details")
                    return []
                    
                # Match IDs with business details
                for business_id in businesses:
                    business_info = next((b for b in all_business_details if b["id"] == business_id), None)
                    if business_info:
                        processed_businesses.append(business_info)
                    else:
                        st.warning(f"Could not find details for business ID: {business_id}")
                
                if processed_businesses:
                    businesses = processed_businesses
                else:
                    st.warning("Could not find details for any of the selected businesses")
                    return []
        except Exception as e:
            st.error(f"Error processing business IDs: {str(e)}")
            import traceback
            st.error(f"Traceback: {traceback.format_exc()}")
            # Continue with original businesses list
            
        with st.spinner(f"Fetching appointments from {len(businesses)} booking pages..."):
            # Fetch appointments for each business
            appointments = await fetch_appointments(businesses, start_date, end_date, max_results)
            
            if not appointments:
                st.warning("No appointments found for the selected date range")
                return []
                
            st.success(f"Successfully fetched {len(appointments)} appointments")
            return appointments
        
    except Exception as e:
        st.error(f"Failed to fetch bookings data: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return []

async def inspect_calendar_api():
    """Inspect the Microsoft Graph calendar API to determine parameter names"""
    try:
        # Use direct API call instead of graph client
        result = await make_graph_request("/me/calendar")
        if not result:
            return None, "Failed to make direct API call to Graph API"
        
        # Return the events endpoint for inspection
        return result, None
    except Exception as e:
        return None, f"Error inspecting calendar API: {str(e)}"

async def fetch_calendar_events(start_date, end_date, max_results=1000, user_id="info-usa@accesscare.health"):
    """Fetch calendar events for a user in the specified date range"""
    try:
        # Format dates for API - ensure we use UTC
        start_datetime = datetime.combine(start_date, datetime.min.time()).astimezone(LOCAL_TZ).astimezone(pytz.UTC)
        end_datetime = datetime.combine(end_date, datetime.max.time()).astimezone(LOCAL_TZ).astimezone(pytz.UTC)
        
        # Format datetime strings for API
        start_str = start_datetime.isoformat().replace('+00:00', 'Z')
        end_str = end_datetime.isoformat().replace('+00:00', 'Z')
        
        with st.spinner(f"Fetching calendar events for {user_id}..."):
            # Try the specified user's calendars first
            try:
                # Get all calendars for the specified user
                calendars_result = await make_graph_request(f"/users/{user_id}/calendars")
                
                if not calendars_result or "value" not in calendars_result or not calendars_result["value"]:
                    # If no calendars found, try with default calendar
                    return await fetch_default_calendar_events(None, start_str, end_str, max_results, user_id)
                
                calendars = calendars_result["value"]
                
                # Fetch events from all calendars
                all_events = []
                
                # Create a progress bar for fetching events
                progress_bar = st.progress(0)
                calendar_count = len(calendars)
                
                for i, calendar in enumerate(calendars):
                    if "id" not in calendar:
                        continue
                        
                    calendar_id = calendar["id"]
                    calendar_name = calendar["name"] if "name" in calendar else f"Calendar {calendar_id}"
                    
                    # Update progress bar
                    progress_bar.progress((i) / calendar_count)
                    
                    # Get events from this calendar
                    try:
                        # Get events from this calendar with direct API call
                        # Build the calendar events endpoint
                        params = {
                            "startDateTime": start_str,
                            "endDateTime": end_str,
                            "$top": max_results
                        }
                        
                        calendar_events = await make_graph_request(f"/users/{user_id}/calendars/{calendar_id}/calendarView", params=params)
                        
                        if calendar_events and "value" in calendar_events:
                            # Process events into standardized format
                            for event in calendar_events["value"]:
                                # Add calendar name to each event
                                event["calendarName"] = calendar_name
                                all_events.append(event)
                    except Exception as cal_err:
                        continue
                
                # Clear progress bar
                progress_bar.empty()
                
                # Process all events
                if all_events:
                    return process_calendar_events(all_events)
                else:
                    st.warning("No events found in any calendar")
                    return []
                    
            except Exception as cal_list_err:
                # Fall back to default calendar
                return await fetch_default_calendar_events(None, start_str, end_str, max_results, user_id)
        
    except Exception as e:
        st.error(f"Failed to fetch calendar events: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return []

async def fetch_default_calendar_events(graph_client, start_str, end_str, max_results=1000, user_id="info-usa@accesscare.health"):
    """Fetch events from the default calendar (fallback method)"""
    try:
        with st.spinner(f"Fetching events from default calendar for {user_id}..."):
            # Create query parameters for direct API call
            params = {
                "startDateTime": start_str,
                "endDateTime": end_str,
                "$top": max_results
            }
            
            # Make direct API call to get events - use the specific user instead of "me"
            events_result = await make_graph_request(f"/users/{user_id}/calendar/calendarView", params=params)
            
            if not events_result or "value" not in events_result:
                # Try "me" as a last resort
                events_result = await make_graph_request("/me/calendar/calendarView", params=params)
                
                if not events_result or "value" not in events_result:
                    st.warning("No events found in default calendar")
                    return []
            
            events = events_result["value"]
            
            # Process events into standardized format
            return process_calendar_events(events)
        
    except Exception as e:
        st.error(f"Failed to fetch events from default calendar: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return []

def process_calendar_events(events):
    """Process calendar events into a standardized format"""
    processed_events = []
    error_count = 0
    
    for event in events:
        try:
            # Extract basic event information
            event_id = event.get("id", "")
            subject = event.get("subject", "Unknown Subject")
            
            # Get calendar name if available
            calendar_name = event.get("calendarName", "Default")
            
            # Get organizer info - safely handle None values
            organizer_name = ""
            organizer_email = ""
            if event.get("organizer") is not None and event.get("organizer", {}).get("emailAddress") is not None:
                organizer_name = event["organizer"]["emailAddress"].get("name", "")
                organizer_email = event["organizer"]["emailAddress"].get("address", "")
            
            # Get time information - safely handle None values
            start_time = None
            if event.get("start") is not None and event["start"].get("dateTime") is not None:
                start_str = event["start"]["dateTime"]
                timezone = event["start"].get("timeZone", "UTC")
                try:
                    # Parse the time string
                    start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    # Convert to local timezone if possible
                    try:
                        if timezone != "UTC":
                            timezone_obj = pytz.timezone(timezone)
                            start_time = start_time.replace(tzinfo=pytz.UTC).astimezone(timezone_obj)
                        # Always convert to local timezone for display
                        start_time = start_time.astimezone(LOCAL_TZ)
                    except Exception:
                        # If timezone conversion fails, keep UTC
                        pass
                except Exception:
                    start_time = datetime.now(LOCAL_TZ)
            
            end_time = None
            if event.get("end") is not None and event["end"].get("dateTime") is not None:
                end_str = event["end"]["dateTime"]
                timezone = event["end"].get("timeZone", "UTC")
                try:
                    # Parse the time string
                    end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                    # Convert to local timezone if possible
                    try:
                        if timezone != "UTC":
                            timezone_obj = pytz.timezone(timezone)
                            end_time = end_time.replace(tzinfo=pytz.UTC).astimezone(timezone_obj)
                        # Always convert to local timezone for display
                        end_time = end_time.astimezone(LOCAL_TZ)
                    except Exception:
                        # If timezone conversion fails, keep UTC
                        pass
                except Exception:
                    if start_time:
                        end_time = start_time + timedelta(hours=1)
                    else:
                        end_time = datetime.now(LOCAL_TZ) + timedelta(hours=1)
            elif start_time:
                # Default to start + 1 hour if no end time found
                end_time = start_time + timedelta(hours=1)
            
            # Calculate duration in minutes
            duration_minutes = 0
            if start_time and end_time:
                duration_minutes = (end_time - start_time).total_seconds() / 60
            
            # Get location information - safely handle None
            location = ""
            if event.get("location") is not None:
                location = event["location"].get("displayName", "")
            
            # Get online meeting info - safely handle None
            is_online_meeting = event.get("isOnlineMeeting", False)
            online_meeting_url = event.get("onlineMeetingUrl", "")
            if not online_meeting_url and event.get("onlineMeeting") is not None:
                online_meeting_url = event["onlineMeeting"].get("joinUrl", "")
            
            # Get attendees - safely handle None
            attendees = []
            if event.get("attendees") is not None:
                for attendee in event["attendees"]:
                    if attendee.get("emailAddress") is not None:
                        attendee_name = attendee["emailAddress"].get("name", "")
                        attendee_email = attendee["emailAddress"].get("address", "")
                        attendee_type = attendee.get("type", "")
                        attendee_response = ""
                        if attendee.get("status") is not None:
                            attendee_response = attendee["status"].get("response", "")
                        
                        attendees.append({
                            "name": attendee_name,
                            "email": attendee_email,
                            "type": attendee_type,
                            "response": attendee_response
                        })
            
            # Get body/description - safely handle None
            body_content = ""
            if event.get("body") is not None and event["body"].get("content") is not None:
                body_content = event["body"]["content"]
            
            # Create standardized event object
            event_obj = {
                "ID": event_id,
                "Subject": subject,
                "Calendar": calendar_name,
                "Start Time": start_time,
                "End Time": end_time,
                "Duration (min)": duration_minutes,
                "Organizer": organizer_name,
                "Organizer Email": organizer_email,
                "Location": location,
                "Is Online Meeting": is_online_meeting,
                "Online Meeting URL": online_meeting_url,
                "Attendee Count": len(attendees),
                "Attendees": ", ".join([f"{a['name']} ({a['email']})" for a in attendees if a["name"] or a["email"]]),
                "Body": body_content
            }
            
            processed_events.append(event_obj)
        except Exception:
            error_count += 1
            continue
    
    return processed_events

async def fetch_forms_responses(form_id):
    """Fetch responses for a Microsoft Form"""
    try:
        graph_client = await get_graph_client()
        if not graph_client:
            st.error("Failed to initialize Graph client")
            return None
        
        # Get form details
        try:
            # Attempt to get the form details
            form = await graph_client.users.by_user_id("me").forms.by_form_id(form_id).get()
            if not form:
                st.warning(f"Form with ID {form_id} not found")
                return None
            
            # Get form responses
            responses = await graph_client.users.by_user_id("me").forms.by_form_id(form_id).responses.get()
            if not responses or not responses.value:
                st.warning("No responses found for this form")
                return None
        except Exception as e:
            error_message = str(e)
            st.error(f"Failed to access form: {error_message}")
            
            # Provide more detailed troubleshooting guidance
            st.markdown("""
            <div style="background-color: #ffebee; padding: 1rem; border-radius: 10px; margin-top: 1rem;">
                <h4 style="margin-top: 0; color: #c62828;">Microsoft Forms API Integration Issues</h4>
                <p>Microsoft Graph API has limitations when accessing Forms data. Common issues include:</p>
                <ul>
                    <li><strong>Permission scope:</strong> Ensure your app has <code>Forms.Read.All</code> permission in Azure AD</li>
                    <li><strong>Form ID format:</strong> Check if you're using the correct Form ID format - try both the long ID from the URL and the short ID</li>
                    <li><strong>API Path:</strong> The Forms API path might have changed. Try alternative paths:
                        <ul>
                            <li><code>/me/forms/{form_id}</code></li>
                            <li><code>/users/{user_id}/forms/{form_id}</code></li>
                        </ul>
                    </li>
                    <li><strong>Form ownership:</strong> You must be the owner of the form or have proper admin permissions</li>
                </ul>
                <p><strong>Alternative solutions:</strong></p>
                <ol>
                    <li>Try using Microsoft Power Automate to connect Forms to your data destination</li>
                    <li>Use the Excel export feature in Microsoft Forms and process the data manually</li>
                    <li>Check the latest Microsoft Graph documentation for Forms API changes</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)
            return None
        
        # Process form responses
        form_data = {
            "title": getattr(form, "title", "Unknown Form"),
            "description": getattr(form, "description", ""),
            "response_count": len(responses.value) if responses.value else 0,
            "created_date": getattr(form, "created_date_time", None),
            "last_modified": getattr(form, "last_modified_date_time", None),
            "responses": []
        }
        
        # Process each response
        for response in responses.value:
            try:
                response_data = {
                    "id": getattr(response, "id", ""),
                    "created_date": getattr(response, "created_date_time", None),
                    "answers": {}
                }
                
                # Process answers
                if hasattr(response, "answers") and response.answers:
                    for answer in response.answers:
                        question_id = getattr(answer, "question_id", "")
                        if question_id:
                            # Get question text
                            question_text = ""
                            if hasattr(form, "questions") and form.questions:
                                for question in form.questions:
                                    if getattr(question, "id", "") == question_id:
                                        question_text = getattr(question, "title", "")
                                        break
                            
                            # Get answer value
                            answer_text = ""
                            if hasattr(answer, "value"):
                                answer_text = answer.value
                            
                            # Store answer
                            response_data["answers"][question_text or question_id] = answer_text
                
                form_data["responses"].append(response_data)
            except Exception as e:
                st.warning(f"Error processing form response: {str(e)}")
                continue
        
        return form_data
    except Exception as e:
        st.error(f"Failed to fetch form responses: {str(e)}")
        st.markdown("""
        <div style="background-color: #ffebee; padding: 1rem; border-radius: 10px; margin-top: 1rem;">
            <h4 style="margin-top: 0; color: #c62828;">Connection Error</h4>
            <p>There was a problem connecting to the Microsoft Forms service. Please check:</p>
            <ul>
                <li>Your internet connection</li>
                <li>Your authentication credentials</li>
                <li>That the Microsoft Graph API is available</li>
            </ul>
            <p>You may also need to check the Microsoft 365 Service Health Dashboard for any outages.</p>
        </div>
        """, unsafe_allow_html=True)
        return None

def render_calendar_tab(df):
    """Render the calendar data tab"""
    st.header("Calendar Integration")
    
    # Add instructions
    st.markdown("""
    <div style="background-color: white; padding: 1rem; border-radius: 10px; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
        <h4 style="margin-top: 0; color: #2c3e50;">ℹ️ Calendar Integration</h4>
        <p>This feature fetches events from the <strong>info-usa@accesscare.health</strong> calendar by default. Due to Microsoft Graph API limitations, events are first retrieved without date filtering and then filtered client-side to match your selected date range.</p>
        <p style="margin-bottom: 0; font-style: italic; color: #7f8c8d;">Note: If you have many calendar events, it may take longer to load and filter. Consider using a shorter date range if you experience performance issues.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get date range from session state or use default
    today = datetime.now(LOCAL_TZ).date()
    default_start = today - timedelta(days=30)
    default_end = today
    
    col1, col2 = st.columns(2)
    with col1:
        cal_start_date = st.date_input("Start Date", default_start, key="cal_start_date")
    with col2:
        cal_end_date = st.date_input("End Date", default_end, key="cal_end_date")
    
    if cal_start_date > cal_end_date:
        st.error("Start date must be before end date")
        return
    
    # Add calendar selection option
    calendar_email = st.text_input(
        "Calendar Email (Optional)", 
        value="info-usa@accesscare.health",
        placeholder="info-usa@accesscare.health", 
        help="Enter email address of the calendar to fetch. Default is info-usa@accesscare.health"
    )
    
    cal_max_results = st.slider("Max Calendar Events", 50, 1000, 200, key="cal_max_events")
    
    # Add a section for API debugging
    with st.expander("API Inspection & Debugging", expanded=False):
        st.markdown("""
        <div style="background-color: #f8f9fa; padding: 1rem; border-radius: 6px; margin-bottom: 1rem;">
            <h4 style="margin-top: 0; color: #2c3e50;">🔍 Graph API Inspection</h4>
            <p>This section helps diagnose Microsoft Graph API integration issues.</p>
        </div>
        """, unsafe_allow_html=True)
        
        inspect_button = st.button("🔍 Inspect Graph API", key="inspect_api")
        
        if inspect_button:
            with st.spinner("Inspecting Microsoft Graph API..."):
                events_api, error = asyncio.run(inspect_calendar_api())
                
                if error:
                    st.error(f"Failed to inspect API: {error}")
                elif events_api:
                    # Show available API information
                    st.success("Successfully connected to Microsoft Graph API")
                    
                    # Display simple Microsoft Graph SDK information without external modules
                    st.markdown("### Microsoft Graph SDK Information")
                    try:
                        # Try to get msgraph details directly from the module
                        import msgraph
                        st.write("Microsoft Graph SDK is available.")
                        
                        # Get module info if possible
                        module_info = []
                        
                        # Try to get version
                        if hasattr(msgraph, "__version__"):
                            module_info.append(f"Version: {msgraph.__version__}")
                        
                        # Try to get module path
                        try:
                            module_info.append(f"Path: {msgraph.__file__}")
                        except:
                            pass
                        
                        if module_info:
                            for info in module_info:
                                st.code(info)
                    except ImportError:
                        st.warning("Microsoft Graph SDK (msgraph) is not directly importable.")
                    except Exception as e:
                        st.warning(f"Could not get SDK information: {str(e)}")
                    
                    st.markdown("### API Structure Information")
                    
                    # Try to get parameter info from EventsRequestBuilder
                    try:
                        param_class = EventsRequestBuilder.EventsRequestBuilderGetQueryParameters
                        param_init = param_class.__init__
                        param_args = param_init.__code__.co_varnames
                        
                        st.write("#### Available Parameters:")
                        st.code(", ".join(param_args))
                    except Exception as param_err:
                        st.warning(f"Could not inspect parameters: {str(param_err)}")
                        
                    # Manual API call attempt
                    st.markdown("### Test Direct API Call")
                    test_api_button = st.button("Test Direct API Call", key="test_api")
                    
                    if test_api_button:
                        try:
                            # Try a simple API call to get a single event
                            result = asyncio.run(events_api.get(top=1))
                            if result and hasattr(result, "value"):
                                st.success(f"API call successful! Found {len(result.value)} events")
                            else:
                                st.warning("API call successful but no events returned")
                        except Exception as api_err:
                            st.error(f"API call failed: {str(api_err)}")
    
    fetch_cal_button = st.button("🔄 Fetch Calendar Data")
    
    if fetch_cal_button:
        with st.spinner("Fetching calendar events..."):
            try:
                # Fetch calendar events asynchronously with the selected calendar
                calendar_events = asyncio.run(fetch_calendar_events(cal_start_date, cal_end_date, cal_max_results, calendar_email))
                
                if calendar_events:
                    # Convert to DataFrame
                    cal_df = pd.DataFrame(calendar_events)
                    
                    # Filter the events to the selected date range
                    if "Start Time" in cal_df.columns:
                        # Check if events have valid dates
                        valid_dates = cal_df["Start Time"].notna()
                        date_filtered_df = cal_df[valid_dates].copy()
                        
                        if len(date_filtered_df) > 0:
                            # Apply date filter for the selected range
                            if cal_start_date and cal_end_date:
                                date_filtered_df = date_filtered_df[
                                    (date_filtered_df["Start Time"].dt.date >= cal_start_date) &
                                    (date_filtered_df["Start Time"].dt.date <= cal_end_date)
                                ]
                                
                                # Update the dataframe with filtered results
                                cal_df = date_filtered_df
                    
                    # Store in session state
                    st.session_state['calendar_df'] = cal_df
                    
                    if len(cal_df) > 0:
                        # Display success message
                        st.success(f"Successfully fetched {len(cal_df)} calendar events in the selected date range")
                        
                        # Display event metrics with improved styling
                        st.markdown("""
                        <div style="margin: 1.5rem 0 1rem 0;">
                            <h3 style="font-size: 1.5rem;">📊 Event Metrics</h3>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        metric_cols = st.columns(3)
                        with metric_cols[0]:
                            st.metric("Total Events", len(cal_df))
                        
                        online_count = cal_df["Is Online Meeting"].sum() if "Is Online Meeting" in cal_df.columns else 0
                        with metric_cols[1]:
                            st.metric("Online Meetings", online_count)
                        
                        unique_organizers = cal_df["Organizer"].nunique() if "Organizer" in cal_df.columns else 0
                        with metric_cols[2]:
                            st.metric("Unique Organizers", unique_organizers)
                        
                        # Create visualizations with improved styling
                        st.markdown("""
                        <div style="margin: 2rem 0 1rem 0;">
                            <h3 style="font-size: 1.5rem;">📊 Event Distribution</h3>
                            <p style="color: #7f8c8d; margin-top: 0.3rem;">Analysis of events by day of week</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        try:
                            # Events by day of week
                            cal_df["Day of Week"] = cal_df["Start Time"].dt.day_name()
                            day_counts = cal_df.groupby("Day of Week").size().reset_index(name="Count")
                            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                            day_counts["Day Order"] = day_counts["Day of Week"].apply(lambda x: day_order.index(x) if x in day_order else 999)
                            day_counts = day_counts.sort_values("Day Order")
                            
                            fig = px.bar(
                                day_counts,
                                x="Day of Week",
                                y="Count",
                                title="Events by Day of Week",
                                category_orders={"Day of Week": day_order},
                                color="Count",
                                color_continuous_scale="viridis"
                            )
                            fig.update_layout(
                                height=400,
                                coloraxis_showscale=False,
                                margin=dict(l=20, r=20, t=50, b=20),
                                title_font=dict(size=18),
                                plot_bgcolor='rgba(0,0,0,0.02)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        except Exception as e:
                            st.warning(f"Could not create day of week visualization: {str(e)}")
                        
                        # Show data table with improved styling
                        st.markdown("""
                        <div style="margin: 2rem 0 1rem 0;">
                            <h3 style="font-size: 1.5rem;">📋 Calendar Events</h3>
                            <p style="color: #7f8c8d; margin-top: 0.3rem;">Detailed list of all calendar events</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Add search functionality
                        search_term = st.text_input("🔍 Search by subject or organizer", key="calendar_search")
                        
                        if "Body" in cal_df.columns:
                            # Remove body column to save space
                            display_df = cal_df.drop(columns=["Body"])
                        else:
                            display_df = cal_df
                        
                        # Filter data if search term is provided
                        if search_term:
                            filtered_df = display_df[
                                display_df["Subject"].str.contains(search_term, case=False, na=False) |
                                display_df["Organizer"].str.contains(search_term, case=False, na=False)
                            ]
                            st.dataframe(filtered_df, use_container_width=True)
                            if len(filtered_df) == 0:
                                st.info(f"No results found for '{search_term}'")
                            else:
                                st.caption(f"Showing {len(filtered_df)} of {len(display_df)} events")
                        else:
                            st.dataframe(display_df, use_container_width=True)
                        
                        # Download option with improved styling
                        csv = cal_df.to_csv(index=False)
                        st.download_button(
                            "📥 Download Calendar Events CSV",
                            csv,
                            "calendar_events.csv",
                            "text/csv",
                            key="download-calendar"
                        )
                    else:
                        st.warning("No calendar events found for the selected date range.")
                else:
                    st.warning("No calendar events found for the selected date range")
            except Exception as e:
                error_message = str(e)
                st.error(f"Error fetching calendar events: {error_message}")
                
                # Show more detailed troubleshooting information
                st.markdown(f"""
                <div style="background-color: #ffebee; padding: 1rem; border-radius: 10px; margin-top: 1rem;">
                    <h4 style="margin-top: 0; color: #c62828;">Troubleshooting Calendar Integration</h4>
                    <p>The following error occurred: <code>{error_message}</code></p>
                    
                    <h5 style="color: #c62828; margin-top: 0.8rem;">Common Issues</h5>
                    <ul>
                        <li><strong>Parameter name errors:</strong> The Microsoft Graph SDK frequently updates parameter names. If you see errors about unexpected arguments, try using these parameter names:
                            <ul>
                                <li>For date range: <code>start</code> and <code>end</code> (or try <code>startDateTime</code> and <code>endDateTime</code>)</li>
                                <li>For query limits: <code>top</code> (not <code>$top</code>)</li>
                            </ul>
                        </li>
                        <li><strong>Permission errors:</strong> Ensure your Azure AD app has the following permissions:
                            <ul>
                                <li><code>Calendars.Read</code> - To read calendar data</li>
                                <li><code>Calendars.Read.Shared</code> - To read shared calendars (optional)</li>
                            </ul>
                        </li>
                        <li><strong>Authentication errors:</strong> Make sure your authentication credentials are valid and not expired</li>
                        <li><strong>Date formatting issues:</strong> Ensure dates are properly formatted in ISO 8601 format with 'Z' suffix</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
    
    # Display previously fetched data
    elif 'calendar_df' in st.session_state and not st.session_state['calendar_df'].empty:
        st.info("Displaying previously fetched calendar data. Click 'Fetch Calendar Data' to refresh.")
        cal_df = st.session_state['calendar_df']
        
        # Display event metrics
        st.subheader("Event Metrics")
        metric_cols = st.columns(3)
        with metric_cols[0]:
            st.metric("Total Events", len(cal_df))
        
        online_count = cal_df["Is Online Meeting"].sum() if "Is Online Meeting" in cal_df.columns else 0
        with metric_cols[1]:
            st.metric("Online Meetings", online_count)
        
        unique_organizers = cal_df["Organizer"].nunique() if "Organizer" in cal_df.columns else 0
        with metric_cols[2]:
            st.metric("Unique Organizers", unique_organizers)
        
        # Show data table
        st.subheader("Calendar Events")
        if "Body" in cal_df.columns:
            # Remove body column to save space
            display_df = cal_df.drop(columns=["Body"])
        else:
            display_df = cal_df
        
        st.dataframe(display_df, use_container_width=True)
        
        # Download option
        csv = cal_df.to_csv(index=False)
        st.download_button(
            "📥 Download Calendar Events CSV",
            csv,
            "calendar_events.csv",
            "text/csv",
            key="download-calendar"
        )

def render_forms_tab():
    """Render the MS Forms tab"""
    st.header("Microsoft Forms Integration")
    
    # Add instructions
    st.markdown("""
    <div style="background-color: white; padding: 1rem; border-radius: 10px; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
        <h4 style="margin-top: 0; color: #2c3e50;">ℹ️ Forms Integration</h4>
        <p style="margin-bottom: 0;">This feature fetches responses from your Microsoft Forms. You'll need the Form ID, which can be found in your form's URL (e.g., <code>https://forms.office.com/Pages/ResponsePage.aspx?id=YOUR_FORM_ID_HERE</code>). Ensure your app has <code>Forms.Read.All</code> permission.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Form ID input with better styling
    form_id = st.text_input("Enter Form ID", key="form_id_input", 
                            placeholder="e.g., 1aBcD2efGh3iJkL4mN5oPqR6sTuVwXyZ")
    fetch_form_button = st.button("🔄 Fetch Form Responses", use_container_width=True)
    
    if fetch_form_button and form_id:
        with st.spinner("Fetching form responses..."):
            try:
                # Fetch form responses asynchronously
                form_data = asyncio.run(fetch_forms_responses(form_id))
                
                if form_data:
                    # Store in session state
                    st.session_state['form_data'] = form_data
                    
                    # Display success message
                    st.success(f"Successfully fetched form data with {form_data['response_count']} responses")
                    
                    # Display form information with better styling
                    st.markdown(f"""
                    <div style="background-color: white; padding: 1.5rem; border-radius: 10px; margin: 1.5rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                        <h3 style="margin-top: 0; color: #2c3e50;">{form_data["title"]}</h3>
                        <p style="margin-bottom: 0;">{form_data["description"]}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show metrics with improved styling
                    st.markdown("""
                    <div style="margin: 1.5rem 0 1rem 0;">
                        <h3 style="font-size: 1.5rem;">📊 Response Metrics</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    metric_cols = st.columns(3)
                    with metric_cols[0]:
                        st.metric("Total Responses", form_data["response_count"])
                    
                    # Add more metrics if available
                    created_date = form_data.get("created_date")
                    if created_date:
                        with metric_cols[1]:
                            if isinstance(created_date, str):
                                try:
                                    created_date = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                                except:
                                    pass
                            st.metric("Form Created", created_date.strftime("%Y-%m-%d") if hasattr(created_date, "strftime") else str(created_date))
                    
                    last_modified = form_data.get("last_modified")
                    if last_modified:
                        with metric_cols[2]:
                            if isinstance(last_modified, str):
                                try:
                                    last_modified = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                                except:
                                    pass
                            st.metric("Last Updated", last_modified.strftime("%Y-%m-%d") if hasattr(last_modified, "strftime") else str(last_modified))
                    
                    # Process responses to create a tabular view
                    if form_data["responses"]:
                        # Get all unique questions
                        all_questions = set()
                        for response in form_data["responses"]:
                            all_questions.update(response["answers"].keys())
                        
                        # Create rows for each response
                        rows = []
                        for response in form_data["responses"]:
                            row = {"Response ID": response["id"], "Submitted Date": response["created_date"]}
                            
                            # Add each answer
                            for question in all_questions:
                                row[question] = response["answers"].get(question, "")
                            
                            rows.append(row)
                        
                        # Convert to DataFrame
                        responses_df = pd.DataFrame(rows)
                        
                        # Store in session state
                        st.session_state['form_responses_df'] = responses_df
                        
                        # Show responses table with improved styling
                        st.markdown("""
                        <div style="margin: 2rem 0 1rem 0;">
                            <h3 style="font-size: 1.5rem;">📋 Form Responses</h3>
                            <p style="color: #7f8c8d; margin-top: 0.3rem;">Detailed list of all form submissions</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Add search functionality
                        if len(responses_df) > 5:
                            search_cols = list(responses_df.columns)
                            search_term = st.text_input("🔍 Search responses", key="forms_search")
                            
                            if search_term:
                                matches = pd.DataFrame(False, index=responses_df.index, columns=[1])
                                for col in search_cols:
                                    matches = matches | responses_df[col].astype(str).str.contains(search_term, case=False, na=False)
                                
                                filtered_df = responses_df[matches[1]]
                                st.dataframe(filtered_df, use_container_width=True)
                                
                                if len(filtered_df) == 0:
                                    st.info(f"No results found for '{search_term}'")
                                else:
                                    st.caption(f"Showing {len(filtered_df)} of {len(responses_df)} responses")
                            else:
                                st.dataframe(responses_df, use_container_width=True)
                        else:
                            st.dataframe(responses_df, use_container_width=True)
                        
                        # Download option with improved styling
                        csv = responses_df.to_csv(index=False)
                        st.download_button(
                            "📥 Download Form Responses CSV",
                            csv,
                            f"form_responses_{form_data['title'].replace(' ', '_')}.csv",
                            "text/csv",
                            key="download-form-responses"
                        )
                    else:
                        st.warning("No responses found for this form")
                else:
                    st.error("Failed to fetch form data or no data available")
            except Exception as e:
                st.error(f"Error fetching form responses: {str(e)}")
                st.markdown("""
                <div style="background-color: #ffebee; padding: 1rem; border-radius: 10px; margin-top: 1rem;">
                    <h4 style="margin-top: 0; color: #c62828;">Troubleshooting</h4>
                    <p>If you're seeing errors, please check the following:</p>
                    <ul>
                        <li>Verify the Form ID is correct</li>
                        <li>Ensure your app has <code>Forms.Read.All</code> permission</li>
                        <li>Check that you have access to the form</li>
                    </ul>
                    <p>Note: This feature requires Microsoft Graph API version that supports Forms endpoints.</p>
                </div>
                """, unsafe_allow_html=True)
    elif fetch_form_button and not form_id:
        st.warning("Please enter a Form ID to fetch responses")
    
    # Display previously fetched data
    elif 'form_data' in st.session_state and 'form_responses_df' in st.session_state:
        st.info("Displaying previously fetched form data. Enter a Form ID and click 'Fetch Form Responses' to refresh.")
        
        form_data = st.session_state['form_data']
        responses_df = st.session_state['form_responses_df']
        
        # Display form information with better styling
        st.markdown(f"""
        <div style="background-color: white; padding: 1.5rem; border-radius: 10px; margin: 1.5rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
            <h3 style="margin-top: 0; color: #2c3e50;">{form_data["title"]}</h3>
            <p style="margin-bottom: 0;">{form_data["description"]}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show metrics
        st.metric("Total Responses", form_data["response_count"])
        
        # Show responses table
        st.subheader("Form Responses")
        st.dataframe(responses_df, use_container_width=True)
        
        # Download option
        csv = responses_df.to_csv(index=False)
        st.download_button(
            "📥 Download Form Responses CSV",
            csv,
            f"form_responses_{form_data['title'].replace(' ', '_')}.csv",
            "text/csv",
            key="download-form-responses"
        )

async def track_booking_cancellations(start_date, end_date, selected_businesses=None, max_results=1000, check_emails=True, email_days_back=30):
    """
    Track cancelled appointments by comparing current and previous appointment data
    and by checking cancellation emails in mailboxes.
    
    Args:
        start_date: Start date for fetching appointments
        end_date: End date for fetching appointments
        selected_businesses: List of business IDs to fetch appointments for
        max_results: Maximum number of results to fetch
        check_emails: Whether to also check cancellation emails
        email_days_back: Number of days to look back for cancellation emails
        
    Returns:
        List of cancelled appointments (appointments present in previous data but not in current)
    """
    try:
        cancellations = []
        
        # Method 1: Compare current and previous appointment datasets
        st.info("Checking for cancelled appointments by comparing datasets...")
        
        # Get current appointments
        current_appointments = await fetch_bookings_data(start_date, end_date, max_results, selected_businesses)
        
        # Convert to DataFrame for easier comparison
        current_df = pd.DataFrame(current_appointments) if current_appointments else pd.DataFrame()
        
        # Get previous snapshot from session state if it exists
        if 'previous_appointments' not in st.session_state:
            st.session_state.previous_appointments = current_df
            st.info("First run - storing current appointments as baseline")
        else:
            # Get previous snapshot
            previous_df = st.session_state.previous_appointments
            
            # Find cancelled appointments (present in previous but not in current)
            comparison_cancellations = []
            if not previous_df.empty and not current_df.empty and 'ID' in previous_df.columns and 'ID' in current_df.columns:
                previous_ids = set(previous_df['ID'])
                current_ids = set(current_df['ID'])
                
                # IDs that were in previous but not in current
                cancelled_ids = previous_ids - current_ids
                
                # Get the full records for cancelled appointments
                if cancelled_ids:
                    comparison_cancellations = previous_df[previous_df['ID'].isin(cancelled_ids)].to_dict('records')
                    
                    # Add cancellation source
                    for appt in comparison_cancellations:
                        appt["CancellationSource"] = "Dataset Comparison"
                    
                    st.success(f"Found {len(comparison_cancellations)} cancelled appointments by comparing datasets")
                    cancellations.extend(comparison_cancellations)
                else:
                    st.info("No cancellations found by comparing datasets")
        
        # Update the previous appointments for next time
        st.session_state.previous_appointments = current_df
        
        # Method 2: Check cancellation emails in mailboxes
        if check_emails:
            st.info("Checking for cancellation emails in mailboxes...")
            email_cancellations = await fetch_cancellation_emails(email_days_back)
            
            if email_cancellations:
                st.success(f"Found {len(email_cancellations)} cancellations from emails")
                
                # Add to cancellations list, avoiding duplicates by ID if possible
                existing_ids = set(c.get('ID') for c in cancellations if c.get('ID'))
                
                for email_cancel in email_cancellations:
                    if not email_cancel.get('ID') or email_cancel.get('ID') not in existing_ids:
                        cancellations.append(email_cancel)
                        if email_cancel.get('ID'):
                            existing_ids.add(email_cancel.get('ID'))
            else:
                st.info("No cancellations found in emails")
        
        # Return all cancellations found
        return cancellations
        
    except Exception as e:
        st.error(f"Error tracking cancellations: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return []

async def fetch_cancellation_emails(days_back=30):
    """
    Fetch cancellation emails from mailboxes defined in BOOKINGS_MAILBOXES env var
    
    Args:
        days_back: Number of days to look back for cancellation emails
        
    Returns:
        List of cancellation emails with appointment details
    """
    try:
        # If no mailboxes are defined, return empty list
        if not BOOKINGS_MAILBOXES or BOOKINGS_MAILBOXES[0] == '':
            st.warning("No mailboxes defined in BOOKINGS_MAILBOXES environment variable")
            return []
            
        st.info(f"Checking {len(BOOKINGS_MAILBOXES)} mailboxes for cancellation emails...")
        
        # Get graph client
        graph_client = await get_graph_client()
        if not graph_client:
            st.error("Failed to initialize Graph client")
            return []
            
        # Calculate date range for search
        end_date = datetime.now(LOCAL_TZ)
        start_date = end_date - timedelta(days=days_back)
        
        # Format dates for API
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()
        
        all_cancellation_emails = []
        
        # Create a progress bar
        progress_bar = st.progress(0)
        
        # Process each mailbox
        for i, mailbox in enumerate(BOOKINGS_MAILBOXES):
            if not mailbox.strip():
                continue
                
            progress_bar.progress((i / len(BOOKINGS_MAILBOXES)), text=f"Checking mailbox: {mailbox}")
            
            try:
                # Search for emails with 'cancelled' or 'canceled' in the subject or body
                # This follows the Microsoft Graph API for searching messages
                search_query = "(subject:cancelled OR subject:canceled OR subject:cancellation OR body:cancelled OR body:canceled OR body:cancellation) AND received:>=" + start_str + " AND received:<=" + end_str
                
                # Create request configuration with search query
                request_config = RequestConfiguration()
                request_config.query_parameters = {
                    "$search": f'"{search_query}"',
                    "$orderby": "receivedDateTime desc",
                    "$top": 100,  # Max items per request
                    "$select": "id,subject,receivedDateTime,from,body,bodyPreview"
                }
                
                # Execute the search, handling proper mailbox access
                if mailbox.lower() == "me" or not mailbox.strip():
                    # Use current user's mailbox
                    messages_request = graph_client.me.messages
                else:
                    # Use specific mailbox
                    messages_request = graph_client.users.by_user_id(mailbox).messages
                
                # Get messages with search parameters
                messages = await messages_request.get(request_configuration=request_config)
                
                if not messages or not hasattr(messages, "value"):
                    st.info(f"No cancellation emails found in {mailbox}")
                    continue
                    
                st.success(f"Found {len(messages.value)} potential cancellation emails in {mailbox}")
                
                # Process each message
                for message in messages.value:
                    # Extract appointment details from email
                    appointment_info = extract_appointment_from_email(message)
                    if appointment_info:
                        appointment_info["Mailbox"] = mailbox
                        appointment_info["EmailID"] = message.id if hasattr(message, "id") else ""
                        appointment_info["ReceivedTime"] = message.received_date_time if hasattr(message, "received_date_time") else None
                        all_cancellation_emails.append(appointment_info)
                
                # Check if there are more pages
                next_link = getattr(messages, "odata_next_link", None)
                
                # Handle pagination
                while next_link and len(all_cancellation_emails) < 500:  # Limit to 500 emails total
                    next_request = messages_request.with_url(next_link)
                    next_messages = await next_request.get()
                    
                    if next_messages and hasattr(next_messages, "value"):
                        for message in next_messages.value:
                            appointment_info = extract_appointment_from_email(message)
                            if appointment_info:
                                appointment_info["Mailbox"] = mailbox
                                appointment_info["EmailID"] = message.id if hasattr(message, "id") else ""
                                appointment_info["ReceivedTime"] = message.received_date_time if hasattr(message, "received_date_time") else None
                                all_cancellation_emails.append(appointment_info)
                                
                        next_link = getattr(next_messages, "odata_next_link", None)
                    else:
                        break
            
            except Exception as e:
                st.error(f"Error processing mailbox {mailbox}: {str(e)}")
                continue
                
        # Complete the progress bar
        progress_bar.progress(1.0, text=f"Completed checking all mailboxes")
        
        # Return all found cancellation emails
        return all_cancellation_emails
        
    except Exception as e:
        st.error(f"Error fetching cancellation emails: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return []

def extract_appointment_from_email(message):
    """
    Extract appointment details from an email message object
    
    Args:
        message: Email message object from Microsoft Graph
        
    Returns:
        Dictionary with appointment details or None if not a cancellation
    """
    try:
        # Basic validation
        if not hasattr(message, "subject") or not message.subject:
            return None
            
        subject = message.subject.lower()
        body_preview = message.body_preview.lower() if hasattr(message, "body_preview") and message.body_preview else ""
        body = message.body.content if hasattr(message, "body") and hasattr(message.body, "content") else ""
        
        # Check if this is definitely a cancellation email
        cancellation_terms = ["cancelled", "canceled", "cancellation"]
        is_cancellation = any(term in subject for term in cancellation_terms) or any(term in body_preview for term in cancellation_terms)
        
        if not is_cancellation:
            return None
            
        # Extract customer name - look for common patterns
        # This is a basic implementation - can be enhanced with more robust regex patterns
        customer_name = ""
        if "appointment with" in body.lower():
            # Try to extract name after "appointment with"
            name_part = body.lower().split("appointment with")[1].split(".")[0].strip()
            if name_part and len(name_part) < 50:  # Reasonable name length
                customer_name = name_part
                
        # Default values for extracted information
        appointment_info = {
            "ID": None,  # Will be filled if we can extract a booking ID
            "Customer": customer_name,
            "Business": None,
            "Service": None,
            "Status": "Cancelled",
            "Start Date": None,
            "Subject": message.subject,
            "CancellationSource": "Email"
        }
        
        # Try to extract appointment ID - look for common patterns
        # IDs often appear as "Booking #12345" or "Appointment ID: 12345"
        id_patterns = [
            r"booking\s+#?\s*([a-zA-Z0-9-]+)",
            r"appointment\s+#?\s*([a-zA-Z0-9-]+)",
            r"confirmation\s+#?\s*([a-zA-Z0-9-]+)",
            r"id:\s*([a-zA-Z0-9-]+)",
            r"reference\s+#?\s*([a-zA-Z0-9-]+)"
        ]
        
        import re
        for pattern in id_patterns:
            match = re.search(pattern, body.lower())
            if match:
                appointment_info["ID"] = match.group(1)
                break
                
        # Try to extract appointment date
        date_patterns = [
            r"appointment\s+on\s+(\w+,\s+\w+\s+\d{1,2},\s+\d{4})",
            r"scheduled\s+for\s+(\w+,\s+\w+\s+\d{1,2},\s+\d{4})",
            r"(\d{1,2}/\d{1,2}/\d{2,4})",
            r"(\d{4}-\d{2}-\d{2})"
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, body)
            if match:
                try:
                    # This is a simplistic date parser - could be enhanced
                    date_str = match.group(1)
                    # Try different date formats
                    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%A, %B %d, %Y"]:
                        try:
                            appointment_date = datetime.strptime(date_str, fmt)
                            appointment_info["Start Date"] = appointment_date
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass
                
                if appointment_info["Start Date"]:
                    break
        
        # Extract business name from email domains and signature blocks
        if hasattr(message, "from") and hasattr(message.from_, "email_address"):
            sender_email = message.from_.email_address.address if hasattr(message.from_.email_address, "address") else ""
            
            # Check if it's from a business domain
            if sender_email and "@" in sender_email:
                domain = sender_email.split("@")[1]
                if "accesscare" in domain:
                    appointment_info["Business"] = "Access Care"
                    
        # Look for service name in common formats
        service_patterns = [
            r"service:\s*([^\n\r.]+)",
            r"appointment\s+type:\s*([^\n\r.]+)",
            r"regarding\s+your\s+([^\n\r.]+?)\s+appointment"
        ]
        
        for pattern in service_patterns:
            match = re.search(pattern, body.lower())
            if match:
                service = match.group(1).strip()
                if service and len(service) < 50:  # Reasonable service name length
                    appointment_info["Service"] = service
                break
                
        return appointment_info
        
    except Exception as e:
        st.warning(f"Error extracting appointment from email: {str(e)}")
        return None 