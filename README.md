# Access Care Analytics Dashboard

A comprehensive healthcare analytics and operational intelligence platform for Access Care, built with Streamlit and Python.

## Overview

This platform provides unified analytics and operational intelligence for healthcare appointment management, patient communication, and business operations. It features a modern, professional interface with intuitive navigation and powerful data visualization capabilities.

## Core Features

### Dashboard Analytics
- Real-time appointment tracking and visualization
- Performance metrics and KPIs
- Interactive data filtering and date range selection
- Customizable data views and exports

### Patient & Client Management
- Contact management and validation
- Phone number formatting and validation
- Patient communication tracking
- Data export capabilities (CSV, Excel)
- Microsoft Outlook contact integration

### Tools
- Phone number validation and formatting
- API inspection and testing
- Date/time utilities
- Data analysis tools
- Custom visualization generation

### Integrations
- Microsoft Graph API integration
  - Calendar events
  - Bookings data
  - Business appointments
  - Email tracking
- Airtable integration
  - Data synchronization
  - Analytics export
  - Custom table management
- Webhook connections
  - Real-time data updates
  - Event tracking

### Content Creator
- Statement of Work (SOW) generation
- Template management
- Document customization
- Export capabilities

## Technical Stack

- **Frontend**: Streamlit, Plotly, Custom CSS
- **Backend**: Python 3.x
- **Data Processing**: Pandas, NumPy
- **Integrations**: 
  - Microsoft Graph API
  - Airtable API
  - Custom webhooks
- **Visualization**: Plotly Express
- **Styling**: Custom CSS with dark theme

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd accesscareanalytics
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your credentials:
   ```
   AZURE_CLIENT_ID=your-client-id
   AZURE_CLIENT_SECRET=your-client-secret
   AZURE_TENANT_ID=your-tenant-id
   AIRTABLE_API_KEY=your-airtable-key
   AIRTABLE_BASE_ID=your-airtable-base
   ```

## Running the Application

To run the dashboard locally:

```bash
streamlit run app.py
```

The dashboard will be available at http://localhost:8501.

## Project Structure

```
accesscareanalytics/
├── app.py                 # Main application file
├── config.py             # Configuration settings
├── icons.py              # Icon definitions
├── styles.css            # Custom styling
├── ms_integrations.py    # Microsoft Graph integration
├── airtable_integration.py # Airtable integration
├── phone_formatter.py    # Phone validation utilities
├── sow_creator.py        # SOW generation
├── visualizations.py     # Custom visualizations
├── data_fetcher.py       # Data retrieval utilities
├── analytics.py          # Analytics functions
└── requirements.txt      # Python dependencies
```

## Customization

### Logo
The dashboard supports custom logos:
1. Add `logo.png` (80px width) for the header
2. Add `big_logo.png` (150px width) for the sidebar
3. If no logos are provided, a default SVG logo will be used

### Theme
The application uses a professional dark theme by default. Customize colors in `config.py` under the `THEME_CONFIG` dictionary.

## Security

- All API credentials are stored in environment variables
- Microsoft Graph API authentication using OAuth 2.0
- Secure webhook endpoints
- Data encryption in transit

## License

This project is proprietary and confidential.

© 2024 Access Care Analytics. All rights reserved. 