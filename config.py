import os
from dotenv import load_dotenv
import pytz
from datetime import datetime, timedelta

load_dotenv()

# Azure AD Configuration
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_TENANT_ID")

# Graph API
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v1.0")
GRAPH_API_BASE = os.getenv("GRAPH_API_ENDPOINT", "https://graph.microsoft.com")

# Application Settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
LOCAL_TZ = pytz.timezone(os.getenv("TZ", "UTC"))
LOGO_PATH = "image002.png" if os.path.exists("image002.png") else None
WEBHOOK_PUBLIC_URL = os.getenv("WEBHOOK_PUBLIC_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

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
