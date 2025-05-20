# This file makes the airtable directory a Python package
from modules.airtable.fetch import fetch_from_airtable
from modules.airtable.utilization import get_utilization_data
from modules.airtable.pnl import get_pnl_data
from modules.airtable.sow import get_sow_data
from modules.airtable.kpi import get_kpi_data, calculate_performance_score

__all__ = [
    'fetch_from_airtable',
    'get_utilization_data',
    'get_pnl_data',
    'get_sow_data',
    'get_kpi_data',
    'calculate_performance_score'
] 