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
LOGO_PATH = "logo.png" if os.path.exists("logo.png") else None
APP_TAGLINE = "Unified healthcare analytics and operational intelligence"
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
    'BACKGROUND_COLOR': '#1e1e2e',
    'TEXT_COLOR': '#e0def4',
    'PRIMARY_COLOR': '#9ccfd8',
    'SECONDARY_COLOR': '#c4a7e7',
    'ACCENT_COLOR': '#eb6f92',
    'SUCCESS_COLOR': '#31748f',
    'WARNING_COLOR': '#f6c177',
    'DANGER_COLOR': '#eb6f92',
    'LIGHT_COLOR': '#2a273f',
    'DARK_COLOR': '#191724',
    'SIDEBAR_BG': '#191724',
    'CARD_BG': '#26233a',
    'CARD_SHADOW': '0 4px 6px rgba(0,0,0,0.2)',
    'BORDER_RADIUS': '8px',
    'FONT_FAMILY': '"Inter", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
}

# Airtable Configuration
AIRTABLE_CONFIG = {
    'API_KEY': '',  # Set via environment variable AIRTABLE_API_KEY
    'BASE_ID': '',  # Set via environment variable AIRTABLE_BASE_ID
    'SOW_TABLE': 'SOW',
    'BOOKINGS_TABLE': 'Bookings',
    'INVOICES_TABLE': 'Invoices',
    'UTILIZATION_TABLE': 'Utilization',
    'API_URL': 'https://api.airtable.com/v0'
}

# Webhook Configuration
CLIENT_STATE_SECRET = os.getenv("CLIENT_STATE_SECRET", "your-secret-here")
