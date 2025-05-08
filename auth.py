from azure.identity import ClientSecretCredential
import streamlit as st
from config import CLIENT_ID, CLIENT_SECRET, TENANT_ID

def get_auth_headers():
    """Authenticate with Azure AD and return headers"""
    try:
        cred = ClientSecretCredential(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET
        )
        token = cred.get_token("https://graph.microsoft.com/.default").token
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    except Exception as e:
        st.error(f"🔒 Authentication failed: {str(e)}")
        return None