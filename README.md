# Access Care Analytics Dashboard

A comprehensive healthcare analytics and operational intelligence dashboard for Access Care.

## Overview

This dashboard provides unified analytics and operational intelligence for healthcare appointment management, patient communication, and business operations. It features a dark-themed, professional interface with intuitive navigation and powerful data visualization.

## Features

- **Dashboard Analytics**: Track appointment bookings, status distribution, and performance metrics
- **Patient & Client Management**: Contact management, communication tools, and data export
- **Tools**: Phone validation, API inspection, and date/time utilities
- **Integrations**: Microsoft Graph API, Airtable, and webhook connections
- **Content Creator**: Templates and SOW generation tools

## Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd accesscareanalytics
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your credentials:
   ```
   AZURE_CLIENT_ID=your-client-id
   AZURE_CLIENT_SECRET=your-client-secret
   AZURE_TENANT_ID=your-tenant-id
   AIRTABLE_API_KEY=your-airtable-key
   AIRTABLE_BASE_ID=your-airtable-base
   ```

## Running the Dashboard

To run the dashboard locally:

```
streamlit run app.py
```

The dashboard will be available at http://localhost:8501.

## Required Files

Make sure you have all these files in your project directory:

- `app.py`: Main application file
- `config.py`: Configuration settings
- `icons.py`: Icon definitions and utilities
- `styles.css`: Custom CSS styling
- `ms_integrations.py`: Microsoft integrations
- `airtable_integration.py`: Airtable integration
- `phone_formatter.py`: Phone validation utilities

## Custom Logo

The dashboard uses a dynamically generated logo by default. To use your own logo:

1. Add a file named `logo.png` to the project root directory
2. The logo will be automatically detected and used

## Color Theme

The dashboard uses a professional dark color theme. You can customize the colors in `config.py` under the `THEME_CONFIG` dictionary.

## Screenshots

[Screenshots will be added here]

## License

This project is proprietary and confidential.

© 2023 Access Care Analytics. All rights reserved. 