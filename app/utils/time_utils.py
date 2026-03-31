from datetime import datetime, date, time





def format_datetime(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime("%d-%m-%Y %I:%M %p")  # Example: 11-07-2025 02:45 PM

def format_date(d: date | None) -> str | None:
    if d is None:
        return None
    return d.strftime("%d-%m-%Y")  # Example: 11-07-2025

def format_time(t: time | None) -> str | None:
    if t is None:
        return None
    return t.strftime("%I:%M %p")  # Example: 09:15 AM