import os
from dotenv import load_dotenv
import pytz

load_dotenv()

# Azure AD Configuration
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")

# Application Settings
LOCAL_TZ = pytz.timezone("US/Eastern")
LOGO_PATH = "image002.png"
WEBHOOK_PUBLIC_URL = os.getenv("WEBHOOK_PUBLIC_URL")
CLIENT_STATE_SECRET = os.getenv("CLIENT_STATE_SECRET")
BOOKINGS_MAILBOXES = [m.strip() for m in os.getenv("BOOKINGS_MAILBOXES", "").split(",") if m.strip()]

# Time Presets
today = datetime.now(LOCAL_TZ).date()
DATE_PRESETS = {
    "Last 7 Days": (today - timedelta(days=7), today),
    "Last 30 Days": (today - timedelta(days=30), today),
    "This Month": (today.replace(day=1), today),
    "Last Month": (
        (today.replace(day=1) - timedelta(days=1)).replace(day=1),
        today.replace(day=1) - timedelta(days=1)
    ),
    "Custom": None
}

# Theme Configuration
THEME_CONFIG = {
    "PRIMARY_COLOR": "#0E4A6B",
    "SECONDARY_COLOR": "#D4AF37",
    "BACKGROUND_COLOR": "#F8F9FA",
    "TEXT_COLOR": "#333333",
    "ACCENT_COLOR": "#4A90E2",
    "WARNING_COLOR": "#FF6B6B"
}