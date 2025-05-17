import streamlit as st
import sys
import os

# Add parent directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the analytics dashboard
from airtable_analytics import render_analytics_dashboard

# Page configuration
st.set_page_config(
    page_title="Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
try:
    with open('styles.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    st.warning("Styles file not found. Some visual elements may not display correctly.")

# Render the analytics dashboard
render_analytics_dashboard() 