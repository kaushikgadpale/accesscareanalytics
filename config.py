import os
from dotenv import load_dotenv
import pytz
from datetime import datetime, timedelta

load_dotenv()

# Azure AD Configuration
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_TENANT_ID")

# Microsoft Bookings API Credentials
BOOKINGS_CLIENT_ID = os.getenv("BOOKINGS_CLIENT_ID", "99045f8a-bcc3-437e-b31a-76c0c2f57f8f")
BOOKINGS_CLIENT_SECRET = os.getenv("BOOKINGS_CLIENT_SECRET", "CzD8Q~N1ZjSuc2tTk_TONjJTTVXcFFZspvvOUbTl")
BOOKINGS_TENANT_ID = os.getenv("BOOKINGS_TENANT_ID", "4abd40cb-64d2-4adc-95c8-fa550e92be3e")

# Graph API
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v1.0")
GRAPH_API_BASE = os.getenv("GRAPH_API_ENDPOINT", "https://graph.microsoft.com")

# Application Settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
LOCAL_TZ = pytz.timezone(os.getenv("TZ", "US/Eastern"))
LOGO_PATH = "logo.png" if os.path.exists("logo.png") else None
APP_TAGLINE = "Unified healthcare analytics and operational intelligence"
WEBHOOK_PUBLIC_URL = os.getenv("WEBHOOK_PUBLIC_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# Batch Processing
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "5"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))

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
    'BACKGROUND_COLOR': '#ffffff',
    'TEXT_COLOR': '#1a1a1a',
    'PRIMARY_COLOR': '#404040',
    'SECONDARY_COLOR': '#666666',
    'ACCENT_COLOR': '#808080',
    'SUCCESS_COLOR': '#4d4d4d',
    'WARNING_COLOR': '#666666',
    'DANGER_COLOR': '#333333',
    'LIGHT_COLOR': '#f2f2f2',
    'DARK_COLOR': '#1a1a1a',
    'SIDEBAR_BG': '#f8f8f8',
    'CARD_BG': '#ffffff',
    'CARD_SHADOW': '0 4px 6px rgba(0,0,0,0.1)',
    'BORDER_RADIUS': '8px',
    'FONT_FAMILY': '"Inter", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
}

# Airtable Configuration
AIRTABLE_CONFIG = {
    'API_KEY': os.getenv("AIRTABLE_API_KEY", "patv9Ikg8QyX3Nkaz.35f1cb674b0275b0cbd3c28773af194b5fb11a1103ce857793e4d373dc3ba63a"),
    'BASE_ID': os.getenv("AIRTABLE_BASE_ID", "appglfuZMw0V0a6Sv"),
    'SOW_TABLE': 'SOW',
    'BOOKINGS_TABLE': os.getenv("AIRTABLE_TABLE_NAME", "Bookings"),
    'INVOICES_TABLE': 'Invoices',
    'UTILIZATION_TABLE': 'Utilization',
    'PATIENTS_TABLE': 'Patients',
    'API_URL': 'https://api.airtable.com/v0'
}

# Specific Airtable Bases
AIRTABLE_BASES = {
    'SOW': {
        'BASE_ID': 'appQuoOqTLlUsPfYm',
        'TABLE_ID': 'tblznIpP01lAlbbGx',
        'TABLE_NAME': 'SOW'
    },
    'UTILIZATION': {
        'BASE_ID': 'appJRwD6KL1MWi2Md',
        'TABLE_ID': 'tbli1imgxIk4xzbjS',
        'TABLE_NAME': 'Table 1',
        'FIELDS': {
            'CLIENT': 'fldMs2f73txO0grTs',
            'SITE': 'fldiX4pvUVDKQ6KpO',
            'DATE_OF_SERVICE': 'fld84tu9FIUsaO07B',
            'YEAR': 'flduckgBAvVHSBi0V',
            'HEADCOUNT': 'fldIuZJSLCGUdEflb',
            'WALKINS': 'fldMykivvaaClL0uL',
            'INTERESTED_PATIENTS': 'fld5Wh3MI7OdtBguG',
            'TOTAL_BOOKING_APPTS': 'fldkyvNU78GusJG1w',
            'TOTAL_COMPLETED_APPTS': 'fldG6lAlO9X8epGME',
            'DENTAL': 'fldMfsBy1v56ENtkI',
            'AUDIOLOGY': 'fldlTklf0FPa8gj5U',
            'VISION': 'fldNHp7zYj7SHMTpf',
            'MSK': 'fld7Eu23UBQHLQ4Up',
            'SKIN_SCREENING': 'fldkTAUWBHwqejp5B',
            'BIOMETRICS_AND_LABS': 'fldPr31M8RkcRU95E'
        }
    },
    'PNL': {
        'BASE_ID': 'appZPRl2FAi7Eqbij',
        'TABLE_ID': 'tblwxS5tU2cU6SKe8',
        'TABLE_NAME': 'PnL Master',
        'FIELDS': {
            'CLIENT': 'fld1sScJ7tvtqI7Dr',
            'SITE_LOCATION': 'fldJwI8Wm6OOt25rD',
            'SERVICE_DAYS': 'flde2RDyowbbfl4fw',
            'SERVICE_MONTH': 'fldYQCi1h4TcxbKEZ',
            'REVENUE_WELLNESS_FUND': 'fldBGDk3om4awcTY1',
            'REVENUE_DENTAL_CLAIM': 'fldgHyWPG9MezYuVg',
            'REVENUE_MEDICAL_CLAIM': 'fldFgs59rtkxLIWNR',
            'REVENUE_EVENT_TOTAL': 'fldqOaS0dnFf8yZAf',
            'REVENUE_MISSED_APPOINTMENTS': 'fldHFOQtwyQ0Q3FWd',
            'REVENUE_TOTAL': 'fld5TB15mT5wbWsVp',
            'REVENUE_PER_DAY_AVG': 'fldZiNcJKOAUm28zT',
            'EXPENSE_COGS_TOTAL': 'fldDIZCH8s1zHT3Dl',
            'EXPENSE_COGS_PER_DAY_AVG': 'fld1PoUqnGIq1JB86',
            'NET_PROFIT': 'fldgUJQhTxLd8xKw9',
            'NET_PROFIT_PERCENT': 'fldJGQ4NECEO8e8uW',
            'LAST_MODIFIED': 'fldVxMqI3Azfhlp1X'
        }
    },
    'KPI': {
        'BASE_ID': 'appenAXVtP86f4M9z',  # Onsite Reporting Base
        'TABLE_ID': 'tblzlzDIB1HuNIdgw',
        'TABLE_NAME': 'Daily KPI',
        'FIELDS': {
            'ID': 'fldnPvdlg1ofaNImG',
            'QUESTION': 'fldhPGfw6egYpp4Rx',
            'SELECT': 'fldAtqKvshgDb1kYr',
            'TAGS': 'fld0KGyhOQm45F60y',
            'DATE': 'fldYnyaTAf9vM9SIO',
            'PICTURES_POD_SETUP': 'fldQYS7eSLqjlS4ED',
            'EARGYM_PROMOTION': 'fldcptj6a0EHtsnMv',
            'CROSSBOOKING': 'fldPHIRIZm77Puwy0',
            'BOTD_EOD_FILLED': 'fldC73HUBZK5XKr3E',
            'PHOTOS_VIDEOS_TESTIMONIALS': 'fldpNQsUV59WsAFK5',
            'XRAYS_DENTAL_NOTES_UPLOADED': 'fldEpdMFzJIEXFERD',
            'IF_NO_WHY': 'fldtUCvGpspiqmSWz'
        }
    }
}

# Webhook Configuration
CLIENT_STATE_SECRET = os.getenv("CLIENT_STATE_SECRET", "your-secret-here")
