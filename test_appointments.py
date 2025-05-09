import pandas as pd
from phone_formatter import create_appointments_flow

# Create sample test data
data = {
    'Creation Time': [
        '2024-03-01 09:00:00',
        '2024-03-01 14:30:00',
        '2024-03-02 10:15:00',
        '2024-03-02 16:45:00',
        '2024-03-03 11:20:00',
        '2024-03-03 13:00:00',
        '2024-03-03 15:30:00'
    ],
    'Booking Page': [
        'General Consultation',
        'Urgent Care',
        'General Consultation',
        'Specialist Visit',
        'Urgent Care',
        'General Consultation',
        'Specialist Visit'
    ]
}

# Create DataFrame
df = pd.DataFrame(data)

# Generate the visualization
chart = create_appointments_flow(df)

# Save the chart as HTML
if chart:
    chart.write_html('appointments_flow.html')
    print("Chart has been generated and saved as 'appointments_flow.html'")
else:
    print("Failed to generate chart") 