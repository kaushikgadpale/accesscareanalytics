import pandas as pd
import streamlit as st
import plotly.express as px
from config import LOCAL_TZ

def analyze_patients(df):
    """Analyze patient data and return unique patients, booking frequency, and service usage"""
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    # Get unique patients with their most recent appointment
    unique_patients = (df[["Email", "Customer", "Phone", "Start Date"]]
                      .sort_values("Start Date", ascending=False)
                      .groupby(["Email", "Customer", "Phone"])
                      .first()
                      .reset_index())
    
    # Analyze booking frequency and patterns
    booking_freq = (df.groupby("Email")
                   .agg({
                       "Customer": "first",
                       "Service": "count",
                       "Business": "nunique",
                       "Duration (min)": "sum",
                       "Start Date": ["min", "max"],
                       "Status": lambda x: (x == "Cancelled").mean() * 100
                   })
                   .reset_index())
    
    # Rename columns
    booking_freq.columns = ["Email", "Customer", "Total_Appointments", "Unique_Businesses", 
                          "Total_Duration", "First_Visit", "Last_Visit", "Cancellation_Rate"]
    
    # Calculate days between first and last visit
    booking_freq["Days_Between_Visits"] = (
        booking_freq["Last_Visit"] - booking_freq["First_Visit"]
    ).dt.days
    
    # Sort by total appointments
    booking_freq = booking_freq.sort_values("Total_Appointments", ascending=False)
    
    # Analyze service preferences
    service_usage = (df.groupby(["Email", "Customer"])
                    .agg({
                        "Service": ["count", lambda x: ", ".join(sorted(x.unique()))],
                        "Business": lambda x: x.mode().iloc[0] if not x.empty else "",
                        "Duration (min)": "mean"
                    })
                    .reset_index())
    
    # Rename columns
    service_usage.columns = ["Email", "Customer", "Service_Count", "Services", 
                           "Preferred_Business", "Avg_Duration"]
    
    return unique_patients, booking_freq, service_usage

def analyze_service_mix(df):
    """Analyze service mix and return service counts and duration analysis"""
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    # Count services
    service_counts = df["Service"].value_counts().reset_index()
    service_counts.columns = ["Service", "Count"]
    
    # Calculate total and threshold for "Other" category
    total = service_counts["Count"].sum()
    thresh = total * 0.05
    
    # Group small services into "Other"
    small_services = service_counts[service_counts["Count"] < thresh]
    if not small_services.empty:
        other = pd.DataFrame([{"Service": "Other", "Count": small_services["Count"].sum()}])
        service_counts = pd.concat([service_counts[service_counts["Count"] >= thresh], other], ignore_index=True)
    
    # Analyze service duration
    duration_analysis = (df.groupby("Service")
                        .agg({
                            "Duration (min)": ["mean", "min", "max", "count"]
                        })
                        .reset_index())
    
    # Rename columns
    duration_analysis.columns = ["Service", "Avg_Duration", "Min_Duration", "Max_Duration", "Appointment_Count"]
    duration_analysis = duration_analysis.sort_values("Appointment_Count", ascending=False)
    
    return service_counts, duration_analysis

def analyze_clients(df):
    """Analyze client data and return client performance metrics"""
    if df.empty:
        return pd.DataFrame()
    
    # Calculate client metrics
    client_analysis = (df.groupby("Business")
                      .agg({
                          "Start Date": "count",  # Use Start Date for counting appointments
                          "Duration (min)": "mean",
                          "Status": lambda x: (x == "Cancelled").mean() * 100,
                          "Service": "nunique",
                          "Email": "nunique"
                      })
                      .reset_index())
    
    # Rename columns
    client_analysis.columns = ["Business", "Total_Appointments", "Avg_Duration", 
                             "Cancellation_Rate", "Unique_Services", "Recurring_Patients"]
    
    # Round numeric columns
    client_analysis = client_analysis.round(2)
    
    # Sort by total appointments
    client_analysis = client_analysis.sort_values("Total_Appointments", ascending=False)
    
    return client_analysis