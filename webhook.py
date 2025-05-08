from fastapi import FastAPI, Request, Response
import streamlit as st
import requests
from datetime import datetime
import threading
from config import LOCAL_TZ, GRAPH_API_BASE, CLIENT_STATE_SECRET
from auth import get_auth_headers

app = FastAPI()

@app.get("/webhook")
async def verify(validationToken: str = None):
    if validationToken:
        return Response(content=validationToken, media_type="text/plain")
    return Response(status_code=400)

@app.post("/webhook")
async def notify(req: Request):
    data = await req.json()
    for note in data.get("value", []):
        if note.get("clientState") != CLIENT_STATE_SECRET:
            continue
        ev_id = note.get("resourceData", {}).get("id") or note.get("resource", "").split("/")[-1]
        typ = note.get("changeType")
        # Mark deleted → Cancelled
        if typ == "deleted" and st.session_state.appointment_data is not None:
            idx = st.session_state.appointment_data.index
            if ev_id in idx:
                st.session_state.appointment_data.at[ev_id, "Status"] = "Cancelled"
        else:
            # fetch full event → detect updated times
            hdr = get_auth_headers()
            r = requests.get(f"{GRAPH_API_BASE}/users/{note['resource'].split('/')[2]}/events/{ev_id}",
                           headers=hdr)
            if r.status_code != 200:
                continue
            e = r.json()
            s = datetime.fromisoformat(e["start"]["dateTime"]).astimezone(LOCAL_TZ)
            t = datetime.fromisoformat(e["end"]["dateTime"]).astimezone(LOCAL_TZ)
            # assume ID==eventID
            df = st.session_state.appointment_data
            if ev_id in df.index:
                old = df.loc[ev_id]
                if s != old["Start Date"] or t != old["End Date"]:
                    st.session_state.appointment_data.at[ev_id, "Status"] = "Rescheduled"
                st.session_state.appointment_data.at[ev_id, ["Start Date", "End Date"]] = [s, t]
            else:
                # new event → treat as scheduled
                st.session_state.appointment_data.loc[ev_id] = {
                    "Business": "CalendarEvent",
                    "Customer": "",
                    "Email": "",
                    "Phone": "",
                    "Service": e.get("subject", ""),
                    "Start Date": s,
                    "End Date": t,
                    "Duration (min)": (t-s).total_seconds()/60,
                    "Status": "Scheduled",
                    "Notes": "",
                    "Source": "Calendar",
                    "ID": ev_id
                }
    return Response(status_code=202)

def run_webhook():
    """Start the webhook server"""
    import uvicorn
    import socket
    
    # Try ports 8000-8010
    for port in range(8000, 8011):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('0.0.0.0', port))
            sock.close()
            # Port is available, use it
            uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
            break
        except socket.error:
            continue
        finally:
            sock.close()

if __name__ == "__main__":
    run_webhook()