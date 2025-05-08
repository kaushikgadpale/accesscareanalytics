import os
from dotenv import load_dotenv
import pytz
from datetime import datetime, timedelta

load_dotenv()

# Azure AD Configuration
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")

# Graph API
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

# Application Settings
LOCAL_TZ = pytz.timezone("US/Eastern")
LOGO_PATH = "image002.png" if os.path.exists("image002.png") else None
WEBHOOK_PUBLIC_URL = os.getenv("WEBHOOK_PUBLIC_URL", "https://msbookingsync.onrender.com")

# Time Presets
today = datetime.now(LOCAL_TZ).date()
DATE_PRESETS = {
    "Last 7 Days": (today - timedelta(days=7), today),
    "Last 30 Days": (today - timedelta(days=30), today),
    "Last 90 Days": (today - timedelta(days=90), today),
    "This Month": (today.replace(day=1), today),
    "Last Month": (
        (today.replace(day=1) - timedelta(days=1)).replace(day=1),
        today.replace(day=1) - timedelta(days=1)
    ),
    "Custom": None
}

# Theme Configuration
THEME_CONFIG = {
    "PRIMARY_COLOR": "#007BFF",
    "SECONDARY_COLOR": "#D4AF37",
    "BACKGROUND_COLOR": "#F8F9FA",
    "TEXT_COLOR": "#333333",
    "ACCENT_COLOR": "#4A90E2",
    "WARNING_COLOR": "#FF6B6B"
}

# Webhook Configuration
CLIENT_STATE_SECRET = os.getenv("CLIENT_STATE_SECRET", "your-secret-here")
