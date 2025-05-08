import pandas as pd
import streamlit as st
from config import LOCAL_TZ

def analyze_patients(df):
    """Perform patient-focused analytics"""
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    # Unique patient analysis
    unique_patients = df[["Email", "Customer", "Phone"]].drop_duplicates()
    
    # Booking frequency analysis
    booking_freq = df.groupby("Email").agg(
        Customer=("Customer", "first"),
        Total_Appointments=("Service", "count"),
        Unique_Businesses=("Business", "nunique"),
        Total_Duration=("Duration (min)", "sum")
    ).reset_index()
    
    # Service utilization analysis
    service_usage = df.groupby(["Email", "Customer"])["Service"].agg(
        Service_Count="count",
        Services=lambda x: ", ".join(x.unique())
    ).reset_index()
    
    return unique_patients, booking_freq, service_usage

def analyze_service_mix(df):
    """Analyze service distribution and duration"""
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    # Service popularity
    service_counts = df["Service"].value_counts().reset_index()
    service_counts.columns = ["Service", "Count"]
    
    # Service duration metrics
    service_duration = df.groupby("Service").agg(
        Avg_Duration=("Duration (min)", "mean"),
        Min_Duration=("Duration (min)", "min"),
        Max_Duration=("Duration (min)", "max"),
        Appointment_Count=("Service", "count")
    ).reset_index()
    
    return service_counts, service_duration

def analyze_clients(df):
    """Analyze business client performance"""
    if df.empty:
        return pd.DataFrame()
    
    client_analysis = df.groupby("Business").agg(
        Total_Appointments=("ID", "count"),
        Avg_Duration=("Duration (min)", "mean"),
        Cancellation_Rate=("Status", lambda x: (x == "Cancelled").mean() * 100),
        Unique_Services=("Service", "nunique"),
        Recurring_Patients=("Email", pd.Series.nunique)
    ).reset_index()
    
    return client_analysis.round(2)