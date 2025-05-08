from fastapi import FastAPI, Request, Response
import uvicorn
import threading
from datetime import datetime, timedelta
import requests
from config import CLIENT_STATE_SECRET, LOCAL_TZ, BOOKINGS_MAILBOXES
from auth import get_auth_headers
import streamlit as st

app = FastAPI()

@app.get("/webhook")
async def verify(validationToken: str = None):
    if validationToken:
        return Response(content=validationToken, media_type="text/plain")
    return Response(status_code=400)

@app.post("/webhook")
async def handle_notification(request: Request):
    data = await request.json()
    for notification in data.get("value", []):
        if notification.get("clientState") != CLIENT_STATE_SECRET:
            continue
        process_notification(notification)
    return Response(status_code=202)

def process_notification(notification):
    """Process individual webhook notification"""
    resource = notification.get("resource", "")
    change_type = notification.get("changeType")
    
    if "users" in resource and "events" in resource:
        user_id = resource.split("/")[2]
        event_id = resource.split("/")[-1]
        handle_calendar_event(user_id, event_id, change_type)
    # Add other resource types as needed

def handle_calendar_event(user_id, event_id, change_type):
    """Handle calendar event changes"""
    headers = get_auth_headers()
    if not headers:
        return
    
    try:
        if change_type == "deleted":
            update_cancelled_event(event_id)
        else:
            response = requests.get(
                f"https://graph.microsoft.com/v1.0/users/{user_id}/events/{event_id}",
                headers=headers
            )
            response.raise_for_status()
            update_or_add_event(response.json())
    except Exception as e:
        st.error(f"Error processing calendar event: {str(e)}")

def update_cancelled_event(event_id):
    """Mark event as cancelled in session state"""
    if st.session_state.appointment_data is not None and event_id in st.session_state.appointment_data.index:
        st.session_state.appointment_data.at[event_id, "Status"] = "Cancelled"

def update_or_add_event(event_data):
    """Update or add event in session state"""
    event_id = event_data["id"]
    start_dt = datetime.fromisoformat(event_data["start"]["dateTime"]).astimezone(LOCAL_TZ)
    end_dt = datetime.fromisoformat(event_data["end"]["dateTime"]).astimezone(LOCAL_TZ)
    
    if event_id in st.session_state.appointment_data.index:
        update_existing_event(event_id, start_dt, end_dt)
    else:
        add_new_event(event_data, event_id, start_dt, end_dt)

def run_webhook():
    """Run the webhook server"""
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

def start_webhook_thread():
    """Start webhook server in background thread"""
    threading.Thread(target=run_webhook, daemon=True).start()