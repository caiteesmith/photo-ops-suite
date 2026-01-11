from __future__ import annotations
from datetime import datetime, timedelta
from dateutil import parser

def parse_hhmm(date_str: str, time_str: str) -> datetime:
    """
    date_str: 'YYYY-MM-DD'
    time_str: 'HH:MM' (24h) or 'h:mm AM/PM'
    """
    dt = parser.parse(f"{date_str} {time_str}")
    return dt

def add_minutes(dt: datetime, mins: int) -> datetime:
    return dt + timedelta(minutes=int(mins))

def add_hours(dt: datetime, hours: float) -> datetime:
    return dt + timedelta(seconds=int(hours * 3600))

def fmt_time(dt: datetime) -> str:
    return dt.strftime("%-I:%M %p")  # mac/linux; on Windows use %#I

def safe_fmt_time(dt: datetime) -> str:
    # Windows-friendly fallback
    try:
        return fmt_time(dt)
    except Exception:
        return dt.strftime("%I:%M %p").lstrip("0")

def minutes_between(a: datetime, b: datetime) -> int:
    return int((b - a).total_seconds() // 60)