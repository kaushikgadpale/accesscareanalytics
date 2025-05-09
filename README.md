# Access Care Analytics Dashboard

A comprehensive analytics dashboard for Microsoft Bookings data, providing insights into appointments, patient analysis, and contact management.

## Features

- 📋 Appointments Overview
- 👥 Patient Analysis
- 🏢 Client Overview
- 📞 Phone Number Validation
- 🧩 Service Mix Analysis
- 🚨 Cancellation Insights
- 📇 Contact Export (Outlook Format)
- 📊 Real-time Updates via Webhooks

## Prerequisites

- Python 3.11 or higher
- Microsoft Azure Account with Bookings API access
- Azure AD Application with appropriate permissions

### Required Azure AD Permissions

- Bookings.Read.All
- BookingsAppointment.Read.All
- BookingsAppointment.ReadWrite.All (if using webhooks)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd accesscareanalytics
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
```
Edit .env with your Azure AD credentials and other configurations.

## Configuration

Required environment variables:

```env
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
```

Optional configurations:
- `DEBUG`: Set to "True" for development
- `ENVIRONMENT`: "development" or "production"
- `TZ`: Timezone (default: UTC)
- `WEBHOOK_PUBLIC_URL`: For real-time updates
- `WEBHOOK_SECRET`: Webhook security

## Running Locally

```bash
streamlit run app.py
```

## Deployment

### Deploying to Render

1. Create a new Web Service on Render
2. Connect your repository
3. Configure the service:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `streamlit run app.py`
   - Environment Variables: Add all required variables

### Environment Variables on Render

Make sure to set these in your Render dashboard:
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `ENVIRONMENT=production`
- Other optional configurations

## Troubleshooting

Common issues and solutions:

1. Authentication Errors:
   - Verify Azure AD credentials
   - Check required permissions
   - Ensure correct tenant ID

2. Deployment Issues:
   - Check Python version compatibility
   - Verify all dependencies are installed
   - Check environment variables

3. Data Loading Issues:
   - Verify Microsoft Bookings access
   - Check API permissions
   - Confirm date range settings

## Support

For issues and feature requests, please create an issue in the repository.

## License

[Include your license information here] 