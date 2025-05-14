import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from config import LOCAL_TZ
import asyncio
import plotly.express as px
from msgraph import GraphServiceClient
from msgraph.generated.users.item.calendar.events.events_request_builder import EventsRequestBuilder
from kiota_abstractions.base_request_configuration import RequestConfiguration
from auth import get_auth_headers

async def get_graph_client():
    """Initialize Microsoft Graph client using Azure authentication"""
    from data_fetcher import get_graph_client as fetch_graph_client
    return await fetch_graph_client()

async def inspect_calendar_api():
    """Inspect the Microsoft Graph calendar API to determine parameter names"""
    try:
        graph_client = await get_graph_client()
        if not graph_client:
            return None, "Failed to initialize Graph client"
        
        # Get the events endpoint to check methods and parameters
        events_endpoint = graph_client.users.by_user_id("me").calendar.events
        
        # Return the events endpoint for inspection
        return events_endpoint, None
    except Exception as e:
        return None, f"Error inspecting calendar API: {str(e)}"

async def fetch_calendar_events(start_date, end_date, max_results=500, user_id="me"):
    """Fetch calendar events for a user in the specified date range"""
    try:
        graph_client = await get_graph_client()
        if not graph_client:
            st.error("Failed to initialize Graph client")
            return []
        
        # Format dates for API - ensure we use UTC
        start_datetime = datetime.combine(start_date, datetime.min.time()).astimezone(LOCAL_TZ).astimezone(pytz.UTC)
        end_datetime = datetime.combine(end_date, datetime.max.time()).astimezone(LOCAL_TZ).astimezone(pytz.UTC)
        
        # Format datetime strings for API
        start_str = start_datetime.isoformat().replace('+00:00', 'Z')
        end_str = end_datetime.isoformat().replace('+00:00', 'Z')
        
        # First try to use the API directly without query parameters
        try:
            # Try to get events directly with filtering in the URL
            events_url = f"/me/calendar/events?startDateTime={start_str}&endDateTime={end_str}&$top={max_results}"
            result = await graph_client.request(method="GET", url=events_url)
            
            if result and hasattr(result, "value") and result.value:
                # Return events from direct request
                return process_calendar_events(result.value)
        except Exception as direct_err:
            st.warning(f"Direct API request failed, trying with query parameters: {str(direct_err)}")
        
        # If direct request failed, try with request builder and different parameter naming conventions
        parameter_combinations = [
            # Try with standard parameter naming
            {"startDateTime": start_str, "endDateTime": end_str},
            # Try with snake_case parameter naming
            {"start_date_time": start_str, "end_date_time": end_str},
            # Try with simple parameter naming
            {"start": start_str, "end": end_str}
        ]
        
        for params in parameter_combinations:
            try:
                # Construct query parameters
                query_params_dict = {
                    **params,
                    "top": max_results,
                    "select": ["subject", "start", "end", "attendees", "organizer", "location", "body", "categories", "importance"]
                }
                
                # Log parameters being tried
                st.info(f"Trying with parameters: {list(params.keys())}")
                
                # Create query parameters object
                query_params = EventsRequestBuilder.EventsRequestBuilderGetQueryParameters(**query_params_dict)
                request_configuration = RequestConfiguration(query_parameters=query_params)
                
                # Get events
                result = await graph_client.users.by_user_id(user_id).calendar.events.get(
                    request_configuration=request_configuration
                )
                
                if result and hasattr(result, "value") and result.value:
                    st.success(f"Successfully fetched events with parameters: {list(params.keys())}")
                    return process_calendar_events(result.value)
                else:
                    st.warning("No events found with this parameter configuration")
            except Exception as e:
                st.warning(f"Parameter combination {list(params.keys())} failed: {str(e)}")
                continue
        
        # If all parameter combinations failed, try with OData filter
        try:
            # Create filter-based query
            filter_query = f"start/dateTime ge '{start_str}' and end/dateTime le '{end_str}'"
            query_params = EventsRequestBuilder.EventsRequestBuilderGetQueryParameters(
                filter=filter_query,
                top=max_results,
                select=["subject", "start", "end", "attendees", "organizer", "location", "body", "categories", "importance"]
            )
            
            request_configuration = RequestConfiguration(query_parameters=query_params)
            
            # Get events with filter
            result = await graph_client.users.by_user_id(user_id).calendar.events.get(
                request_configuration=request_configuration
            )
            
            if result and hasattr(result, "value") and result.value:
                st.success("Successfully fetched events with OData filter")
                return process_calendar_events(result.value)
            else:
                st.warning("No calendar events found with OData filter approach")
                return []
        except Exception as filter_err:
            st.error(f"OData filter approach failed: {str(filter_err)}")
            return []
            
    except Exception as e:
        st.error(f"Failed to fetch calendar events: {str(e)}")
        return []

def process_calendar_events(events):
    """Process calendar events returned from the API"""
    processed_events = []
    for event in events:
        try:
            # Process each event
            event_data = {
                "Subject": getattr(event, "subject", ""),
                "Start Time": datetime.fromisoformat(getattr(event.start, "date_time", "").replace('Z', '+00:00')).astimezone(LOCAL_TZ) if hasattr(event, "start") and hasattr(event.start, "date_time") else None,
                "End Time": datetime.fromisoformat(getattr(event.end, "date_time", "").replace('Z', '+00:00')).astimezone(LOCAL_TZ) if hasattr(event, "end") and hasattr(event.end, "date_time") else None,
                "Organizer": getattr(event.organizer.email_address, "name", "") if hasattr(event, "organizer") and hasattr(event.organizer, "email_address") else "",
                "Organizer Email": getattr(event.organizer.email_address, "address", "") if hasattr(event, "organizer") and hasattr(event.organizer, "email_address") else "",
                "Location": getattr(event.location, "display_name", "") if hasattr(event, "location") else "",
                "Is Online Meeting": getattr(event, "is_online_meeting", False),
                "Online Meeting URL": getattr(event, "online_meeting_url", ""),
                "ID": getattr(event, "id", ""),
                "Created": getattr(event, "created_date_time", None),
                "Last Modified": getattr(event, "last_modified_date_time", None),
                "Categories": ", ".join(event.categories) if hasattr(event, "categories") and event.categories else "",
                "Importance": getattr(event, "importance", "")
            }
            
            # Get attendees
            attendees = []
            if hasattr(event, "attendees") and event.attendees:
                for attendee in event.attendees:
                    if hasattr(attendee, "email_address") and hasattr(attendee.email_address, "address"):
                        attendees.append(getattr(attendee.email_address, "address", ""))
            
            event_data["Attendees"] = ", ".join(attendees)
            
            # Extract content from body if available
            if hasattr(event, "body") and hasattr(event.body, "content"):
                event_data["Body"] = event.body.content
            else:
                event_data["Body"] = ""
            
            processed_events.append(event_data)
        except Exception as e:
            st.warning(f"Error processing calendar event: {str(e)}")
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
        <p style="margin-bottom: 0;">This feature fetches your Outlook/Microsoft 365 calendar events. Make sure your app has the <code>Calendars.Read</code> permission enabled to access calendar data.</p>
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
                    
                    # Check SDK version
                    import msgraph_sdk
                    st.info(f"Microsoft Graph SDK Version: {msgraph_sdk.__version__ if hasattr(msgraph_sdk, '__version__') else 'Unknown'}")
                    
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
                # Fetch calendar events asynchronously
                calendar_events = asyncio.run(fetch_calendar_events(cal_start_date, cal_end_date, cal_max_results))
                
                if calendar_events:
                    # Convert to DataFrame
                    cal_df = pd.DataFrame(calendar_events)
                    
                    # Store in session state
                    st.session_state['calendar_df'] = cal_df
                    
                    # Display success message
                    st.success(f"Successfully fetched {len(cal_df)} calendar events")
                    
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
                    st.warning("No calendar events found in the selected date range")
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
                    
                    <h5 style="color: #c62828; margin-top: 0.8rem;">Microsoft Graph SDK Version</h5>
                    <p>Parameter names can vary between SDK versions. Check your SDK version and refer to the latest Microsoft Graph API documentation.</p>
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