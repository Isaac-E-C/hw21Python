import re
from datetime import datetime, timedelta


def validate_date_format(date_str: str) -> bool:
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_time_format(time_str: str) -> bool:
    if not re.match(r"^\d{2}:\d{2}$", time_str):
        return False
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False


def validate_min_anticipation(date_str: str, time_str: str):
    appointment_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    now = datetime.now()
    min_hours = 24
    if appointment_dt - now < timedelta(hours=min_hours):
        raise ValueError(f"Appointments must be scheduled at least {min_hours} hours in advance")


def validate_cancellation_lead_time(date_str: str, time_str: str):
    appointment_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    now = datetime.now()
    min_hours = 2
    if appointment_dt - now < timedelta(hours=min_hours):
        raise ValueError(f"Cancellations must be made at least {min_hours} hours before the appointment")
