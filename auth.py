import os
from azure.identity import ClientSecretCredential
import streamlit as st

def get_auth_headers():
    """Get authentication headers for Microsoft Graph API calls"""
    try:
        # Get credentials from environment variables
        tenant_id = os.getenv("TENANT_ID")
        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")

        if not all([tenant_id, client_id, client_secret]):
            st.error("Missing required Azure AD credentials in environment variables")
            return {}

        # Create credential object
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )

        # Get token
        token = credential.get_token("https://graph.microsoft.com/.default").token
        
        # Return headers
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    except Exception as e:
        st.error(f"Authentication error: {str(e)}")
        return {}