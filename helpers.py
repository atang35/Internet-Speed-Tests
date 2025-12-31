import re
import json
import pandas as pd
import pyodbc
import datetime
import holidays
from datetime import datetime, date, timezone, timedelta, tzinfo
import pytz

from datetime import datetime

from rich.console import Console

MaseruTimeZone = pytz.timezone('Africa/Maseru')

ls_holidays = holidays.country_holidays("LS")
console = Console()

def extract_int(value):
    text = str(value)
    match = re.search(r'-?\d+', text)
    
    if match:
        return int(match.group())
    else:
        raise ValueError(f"Cannot extract integer from text: {text!r}")
    
    
def time_dim(cursor, measured_at_utc: datetime):
    if measured_at_utc.tzinfo is None:
        measured_at_utc = measured_at_utc.replace(tzinfo=timezone.utc)
        
    utc_dt = measured_at_utc
    dt = utc_dt.astimezone(MaseruTimeZone) #local time

    
    # dimensions based on local time zone
    date_key = int(dt.strftime("%Y%m%d"))
    year = dt.year
    month = dt.month
    month_name = dt.strftime("%B")
    day = dt.day
    day_of_week = dt.isoweekday()
    day_of_week_name = dt.strftime("%A")
    week_of_year = dt.isocalendar()[1]
    quarter = (month - 1) // 3 + 1
    hour = dt.hour
    is_weekend = 1 if day_of_week >= 6 else 0
    is_holiday = 1 if dt.date() in ls_holidays else 0
    
    
    cursor.execute("""
                   IF NOT EXISTS (SELECT 1 FROM dbo.time_metadata WHERE time_id = ?)
                   INSERT INTO dbo.time_metadata (
                       time_id,
                       local_tz,
                       date_key,
                       year,
                       month,
                       month_name,
                       day,
                       day_of_week,
                       day_of_week_name,
                       week_of_year,
                       quarter,
                       hour,
                       is_weekend,
                       is_holiday
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   """, (
                       utc_dt,
                       utc_dt,
                       dt,
                       date_key,
                       year,
                       month,
                       month_name,
                       day,
                       day_of_week,
                       day_of_week_name,
                       week_of_year,
                       quarter,
                       hour,
                       is_weekend,
                       is_holiday
                   ) )

    
   
    