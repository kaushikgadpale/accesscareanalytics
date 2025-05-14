import streamlit as st
import pandas as pd
import requests
import os
import json
from datetime import datetime
from config import AIRTABLE_CONFIG, THEME_CONFIG

def get_airtable_credentials():
    """Get Airtable credentials from environment variables or session state"""
    # Check for credentials in session state first
    if 'airtable_api_key' in st.session_state and 'airtable_base_id' in st.session_state:
        return {
            'api_key': st.session_state['airtable_api_key'],
            'base_id': st.session_state['airtable_base_id']
        }
    
    # Otherwise try environment variables
    api_key = os.environ.get('AIRTABLE_API_KEY', AIRTABLE_CONFIG['API_KEY'])
    base_id = os.environ.get('AIRTABLE_BASE_ID', AIRTABLE_CONFIG['BASE_ID'])
    
    return {
        'api_key': api_key,
        'base_id': base_id
    }

def fetch_airtable_table(table_name, max_records=100):
    """Fetch records from an Airtable table"""
    credentials = get_airtable_credentials()
    api_key = credentials['api_key']
    base_id = credentials['base_id']
    
    if not api_key or not base_id:
        st.error("Airtable credentials not configured. Please set them up in the settings.")
        return None
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    url = f"{AIRTABLE_CONFIG['API_URL']}/{base_id}/{table_name}"
    
    try:
        response = requests.get(url, headers=headers, params={'maxRecords': max_records})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from Airtable: {str(e)}")
        return None

def create_airtable_record(table_name, record_data):
    """Create a new record in an Airtable table"""
    credentials = get_airtable_credentials()
    api_key = credentials['api_key']
    base_id = credentials['base_id']
    
    if not api_key or not base_id:
        st.error("Airtable credentials not configured. Please set them up in the settings.")
        return None
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    url = f"{AIRTABLE_CONFIG['API_URL']}/{base_id}/{table_name}"
    
    try:
        data = {'fields': record_data}
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error creating record in Airtable: {str(e)}")
        return None

def update_airtable_record(table_name, record_id, record_data):
    """Update an existing record in an Airtable table"""
    credentials = get_airtable_credentials()
    api_key = credentials['api_key']
    base_id = credentials['base_id']
    
    if not api_key or not base_id:
        st.error("Airtable credentials not configured. Please set them up in the settings.")
        return None
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    url = f"{AIRTABLE_CONFIG['API_URL']}/{base_id}/{table_name}/{record_id}"
    
    try:
        data = {'fields': record_data}
        response = requests.patch(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error updating record in Airtable: {str(e)}")
        return None

def convert_airtable_to_dataframe(airtable_data):
    """Convert Airtable JSON response to a pandas DataFrame"""
    if not airtable_data or 'records' not in airtable_data:
        return pd.DataFrame()
    
    records = []
    for record in airtable_data['records']:
        row = record['fields'].copy()
        row['id'] = record['id']
        records.append(row)
    
    return pd.DataFrame(records)

def render_airtable_settings():
    """Render Airtable settings form"""
    st.header("Airtable Integration Settings")
    
    st.markdown("""
    <div style="background-color: white; padding: 1rem; border-radius: 10px; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
        <h4 style="margin-top: 0; color: #2c3e50;">ℹ️ Airtable Integration</h4>
        <p style="margin-bottom: 0;">Configure your Airtable API credentials to connect to your Airtable base.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get current values from session state or config
    current_api_key = st.session_state.get('airtable_api_key', os.environ.get('AIRTABLE_API_KEY', ''))
    current_base_id = st.session_state.get('airtable_base_id', os.environ.get('AIRTABLE_BASE_ID', ''))
    
    # Create settings form
    with st.form("airtable_settings_form"):
        api_key = st.text_input("Airtable API Key", 
                               value=current_api_key,
                               type="password",
                               help="Your Airtable Personal Access Token (PAT)")
        
        base_id = st.text_input("Airtable Base ID", 
                               value=current_base_id,
                               help="The ID of your Airtable base (found in the API documentation)")
        
        submitted = st.form_submit_button("Save Settings")
        
        if submitted:
            st.session_state['airtable_api_key'] = api_key
            st.session_state['airtable_base_id'] = base_id
            st.success("Airtable settings saved successfully!")
    
    # Test connection button
    if st.button("Test Connection"):
        credentials = get_airtable_credentials()
        if not credentials['api_key'] or not credentials['base_id']:
            st.error("Please enter both API Key and Base ID")
        else:
            with st.spinner("Testing connection to Airtable..."):
                test_url = f"{AIRTABLE_CONFIG['API_URL']}/{credentials['base_id']}"
                headers = {
                    'Authorization': f'Bearer {credentials["api_key"]}',
                    'Content-Type': 'application/json'
                }
                
                try:
                    response = requests.get(f"{test_url}/metadata", headers=headers)
                    if response.status_code == 200:
                        st.success("Successfully connected to Airtable!")
                        
                        # Show available tables
                        tables = response.json().get('tables', [])
                        if tables:
                            st.write("Available tables in this base:")
                            table_list = [table['name'] for table in tables]
                            st.code("\n".join(table_list))
                    else:
                        st.error(f"Connection failed. Status code: {response.status_code}")
                        if response.status_code == 401:
                            st.error("Unauthorized. Please check your API key.")
                        elif response.status_code == 404:
                            st.error("Base not found. Please check your Base ID.")
                        else:
                            st.error(f"Error message: {response.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Connection error: {str(e)}")

def render_sow_generator():
    """Render the Statement of Work (SOW) generator interface"""
    st.header("Statement of Work Generator")
    
    st.markdown("""
    <div style="background-color: white; padding: 1rem; border-radius: 10px; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
        <h4 style="margin-top: 0; color: #2c3e50;">ℹ️ SOW Generator</h4>
        <p style="margin-bottom: 0;">Generate a Statement of Work document from your Airtable data.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check for credentials
    credentials = get_airtable_credentials()
    if not credentials['api_key'] or not credentials['base_id']:
        st.warning("Airtable credentials not configured. Please set them up in the settings tab.")
        return
    
    # Fetch SOW data from Airtable
    with st.spinner("Loading SOW data from Airtable..."):
        sow_table = AIRTABLE_CONFIG['SOW_TABLE']
        sow_data = fetch_airtable_table(sow_table)
        
        if not sow_data:
            st.error(f"Could not fetch data from {sow_table} table.")
            return
        
        sow_df = convert_airtable_to_dataframe(sow_data)
        
        if sow_df.empty:
            st.warning(f"No SOW records found in the {sow_table} table.")
            return
    
    # Display SOW records
    st.subheader("Available SOW Records")
    
    # Show a table of SOW records
    display_cols = ['id', 'Project Name', 'Client Company Name', 'SOW Date', 'SOW/Quote Number']
    display_cols = [col for col in display_cols if col in sow_df.columns]
    
    if display_cols:
        st.dataframe(sow_df[display_cols], use_container_width=True)
    else:
        st.warning("Could not find expected columns in the SOW table.")
        st.dataframe(sow_df.head(), use_container_width=True)
    
    # SOW Selection and Generation
    st.subheader("Generate SOW Document")
    
    if 'id' in sow_df.columns:
        selected_sow = st.selectbox(
            "Select SOW to generate",
            options=sow_df['id'].tolist(),
            format_func=lambda x: f"{sow_df[sow_df['id'] == x].get('Project Name', '').iloc[0] if not pd.isna(sow_df[sow_df['id'] == x].get('Project Name', '')).iloc[0] else ''} - {sow_df[sow_df['id'] == x].get('Client Company Name', '').iloc[0] if not pd.isna(sow_df[sow_df['id'] == x].get('Client Company Name', '')).iloc[0] else ''}"
        )
        
        if st.button("Generate SOW Document", use_container_width=True):
            with st.spinner("Generating SOW document..."):
                selected_record = sow_df[sow_df['id'] == selected_sow].iloc[0].to_dict()
                
                # Generate the SOW document
                sow_text = generate_sow_document(selected_record)
                
                if sow_text:
                    st.success("SOW document generated successfully!")
                    
                    # Display the document
                    with st.expander("Preview SOW Document", expanded=True):
                        st.markdown(sow_text)
                    
                    # Provide download option
                    st.download_button(
                        "Download SOW as Text",
                        sow_text,
                        file_name=f"SOW_{selected_record.get('SOW/Quote Number', 'document')}.txt",
                        mime="text/plain"
                    )
                    
                    # Update the Airtable record with the generated SOW
                    try:
                        update_result = update_airtable_record(
                            AIRTABLE_CONFIG['SOW_TABLE'],
                            selected_sow,
                            {"SOW Export": sow_text}
                        )
                        if update_result:
                            st.success("SOW document saved back to Airtable!")
                    except Exception as e:
                        st.warning(f"Could not save SOW back to Airtable: {str(e)}")

def generate_sow_document(record):
    """Generate a Statement of Work document from a record"""
    # Define placeholder mappings
    placeholders = {
        "{{ServiceProviderName}}": record.get('Service Provider Name', ''),
        "{{ServiceProviderAddress1}}": record.get('Service Provider Address Line 1', ''),
        "{{ServiceProviderAddress2}}": record.get('Service Provider Address Line 2', ''),
        "{{ServiceProviderCity}}": record.get('Service Provider City', ''),
        "{{ServiceProviderState}}": record.get('Service Provider State', ''),
        "{{ServiceProviderPostalCode}}": record.get('Service Provider Postal Code', ''),

        "{{ClientCompanyName}}": record.get('Client Company Name', ''),
        "{{ClientAddress1}}": record.get('Client Address Line 1', ''),
        "{{ClientCity}}": record.get('Client City', ''),
        "{{ClientState}}": record.get('Client State', ''),
        "{{ClientPostalCode}}": record.get('Client Postal Code', ''),

        "{{SOWDate}}": record.get('SOW Date', ''),
        "{{SOWEffectiveDate}}": record.get('SOW Effective Date', ''),
        "{{SOWDuration}}": record.get('SOW Duration/End Condition', ''),

        "{{ProjectName}}": record.get('Project Name', ''),
        "{{SOWQuoteNumber}}": record.get('SOW/Quote Number', ''),
        "{{ScheduledPlanningStartDate}}": record.get('Scheduled Planning Start Date', ''),
        "{{ScheduledEndDate}}": record.get('Scheduled End Date', ''),

        "{{ClientBusinessManager}}": record.get('Client Business Manager', ''),
        "{{AccessCareClientSuccessManager}}": record.get('Access Care Client Success Manager', ''),
        "{{AccessCareProjectManager}}": record.get('Access Care Project Manager', ''),
        "{{InsurancePartner}}": record.get('Insurance Partner', ''),

        "{{AccessCareSignatoryName}}": record.get('Access Care Signatory Name', ''),
        "{{AccessCareSignatoryTitle}}": record.get('Access Care Signatory Title', ''),
        "{{AccessCareSignatureDate}}": record.get('Date', ''),

        "{{ClientSignatoryName}}": record.get('Client Signatory Name', ''),
        "{{ClientSignatoryTitle}}": record.get('Client Signatory Title', ''),
        "{{ClientSignatureDate}}": record.get('Date 2', ''),

        # Timeline Fields
        "{{PlanningSchedulingTimeline}}": record.get('Scheduled Planning Start Date', ''),
        "{{OnsiteDentalTimeline}}": record.get('Scheduled End Date', ''),
        "{{UtilizationReportDate}}": record.get('Milestone Date', ''),
        "{{FinalFeedbackDebriefDate}}": "TBD",
        
        # Pricing Fields
        "{{DailyServiceMinimumAmount}}": record.get('Daily Service Minimum Amount', ''),
        "{{Per Chair Patient Minimum}}": record.get('Per Chair Patient Minimum', ''),
        "{{Chairs Per Pod}}": record.get('Chairs Per Pod', ''),
        "{{Claim Billing Rate}}": record.get('Claim Billing Rate', ''),
        "{{Value}}": record.get('Value', ''),
        "{{Claims Collection Method}}": record.get('Claims Collection Method', '')
    }
    
    # SOW Template
    sow_template = """
{{ServiceProviderName}}
{{ServiceProviderAddress1}}
{{ServiceProviderAddress2}}
{{ServiceProviderCity}}, {{ServiceProviderState}} {{ServiceProviderPostalCode}}

Statement of Work
{{SOWDate}}

---

# 1. PARTIES
This Statement of Work ("SOW") is entered into between:
Service Provider:
{{ServiceProviderName}}
{{ServiceProviderAddress1}}
{{ServiceProviderCity}}, {{ServiceProviderState}} {{ServiceProviderPostalCode}}

Client:
{{ClientCompanyName}}
{{ClientAddress1}}
{{ClientCity}}, {{ClientState}} {{ClientPostalCode}}

---

# 2. INTRODUCTION
This Statement of Work, effective {{SOWEffectiveDate}}, is entered into between {{ServiceProviderName}} and {{ClientCompanyName}} and shall remain in effect until completion of services or termination by either party in accordance with the terms herein.

Access Care proposes dedicated mobile dental care services to be made available for {{ClientCompanyName}} employees across selected locations.

---

# 3. ENGAGEMENT DETAILS
- Project Name: {{ProjectName}}
- SOW / Quote #: {{SOWQuoteNumber}}
- Scheduled Planning Start Date: {{ScheduledPlanningStartDate}}
- Launch of Dental Service Tour: {{ScheduledPlanningStartDate}} ➔ {{ScheduledEndDate}}
- Scheduled End Date: {{ScheduledEndDate}}
- Progressive Business Manager: {{ClientBusinessManager}}
- Access Care Client Success Manager: {{AccessCareClientSuccessManager}}
- Access Care Project Manager: {{AccessCareProjectManager}}
- Insurance Partner: {{InsurancePartner}}

---

# 4. DESCRIPTION & SCOPE OF WORK
Access Care Health LLC will deliver on-site comprehensive dental services to {{ClientCompanyName}} employees through a fully equipped mobile dental unit staffed by licensed dental professionals.

## 4.1 General Services
- Comprehensive Oral Examination
- Professional Dental Cleaning
- Digital Dental X-rays
- Oral Health Education
- Personalized Treatment Recommendations

## 4.2 Staffing
Onsite Leaders:
- Dentist
- Hygienist
- RDA's
- Trucking
- Logistics
- Practice Management / Client Success / Marketing

---

# 5. TIMELINE & DELIVERABLES
## 5.1 Project Milestones
- Planning & Scheduling: {{PlanningSchedulingTimeline}}
- On-site Dental Services: {{OnsiteDentalTimeline}}
- Utilization Report Delivery: {{UtilizationReportDate}}
- Final Feedback & Debriefing: {{FinalFeedbackDebriefDate}}

---

# 6. PRICING STRUCTURE
- Daily Service Minimum: {{DailyServiceMinimumAmount}}
- Per Chair Patient Minimum: {{Per Chair Patient Minimum}}
- Chairs Per Pod: {{Chairs Per Pod}}
- Claim Billing Rate: {{Claim Billing Rate}}
- Travel and Logistics: {{Value}}
- Claims Collection Method: {{Claims Collection Method}}

---

# 7. PROMOTIONAL & MARKETING MATERIALS
- Email Blast: Linked to Site Codes
- Digital Flyer: Linked to Site Codes
- Digital Banner: Linked to Site Codes

---

# 8. COMPLIANCE & CONFIDENTIALITY
Access Care Health LLC shall comply with all applicable local, state, and federal healthcare regulations while delivering services. All personal health information will be protected and only shared with the individual employee. Access Care will maintain strict compliance with HIPAA, GDPR, and other relevant data privacy laws throughout the duration of this engagement.

---

# 9. COMPANY ADDRESSES
Access Care Health, LLC  
3525 Ridge Meadow Pkwy  
Memphis, TN 38115  
USA

---

# 10. SIGNATURES
Access Care Health, LLC  
Signed By: {{AccessCareSignatoryName}}  
Title: {{AccessCareSignatoryTitle}}  
Date: {{AccessCareSignatureDate}}

The Progressive Corporation  
Signed By: {{ClientSignatoryName}}  
Title: {{ClientSignatoryTitle}}  
Date: {{ClientSignatureDate}}
"""
    
    # Replace placeholders
    for placeholder, value in placeholders.items():
        if value is None:
            value = ''
        sow_template = sow_template.replace(placeholder, str(value))
    
    return sow_template

def render_airtable_tabs():
    """Render the Airtable integration tabs"""
    st.header("Airtable Integration")
    
    # Create tabs for different Airtable functions
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 SOW Generator", 
        "📊 Utilization Reports", 
        "💰 Invoice Reports",
        "⚙️ Settings"
    ])
    
    with tab1:
        render_sow_generator()
    
    with tab2:
        st.header("Utilization Reports")
        st.info("This feature is coming soon.")
    
    with tab3:
        st.header("Invoice Reports")
        st.info("This feature is coming soon.")
    
    with tab4:
        render_airtable_settings() 