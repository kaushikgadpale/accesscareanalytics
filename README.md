# Access Care Analytics

A Streamlit dashboard for analyzing Microsoft Bookings data, providing insights into appointments, patient behavior, and business performance.

## Features

- Real-time appointment tracking and analytics
- Patient analysis and booking patterns
- Service mix analysis
- Client performance metrics
- Phone number validation
- Contact export for Microsoft Outlook
- Webhook integration for live updates

## Prerequisites

- Python 3.8+
- Microsoft Azure AD account with Bookings permissions
- Valid Azure AD application credentials

## Required Permissions

The Azure AD application requires the following Microsoft Graph permissions:
- Bookings.Read.All
- Bookings.ReadWrite.All
- BookingsAppointment.ReadWrite.All

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/accesscareanalytics.git
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

4. Create a `.env` file with your Azure AD credentials:
```env
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
TENANT_ID=your_tenant_id
WEBHOOK_PUBLIC_URL=your_webhook_url
CLIENT_STATE_SECRET=your_webhook_secret
```

## Usage

1. Start the Streamlit app:
```bash
streamlit run app.py
```

2. Open your browser and navigate to the provided URL (usually http://localhost:8501)

3. Select businesses and date range in the sidebar

4. Click "Fetch Data" to load appointments and view analytics

## Features

### Appointments Overview
- View all appointments with filtering options
- Track appointment status (Scheduled, Completed, Cancelled)
- Monitor appointment metrics

### Patient Analysis
- Track patient visit patterns
- Analyze service preferences
- Monitor cancellation rates

### Client Overview
- View business performance metrics
- Track appointment volumes
- Monitor cancellation rates

### Service Mix
- Analyze service popularity
- Track service duration patterns
- Identify trending services

### Phone Validation
- Validate phone number formats
- Track invalid numbers
- Support for multiple regions

### Contact Export
- Export patient contacts
- Microsoft Outlook compatible format
- Customizable export options

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 