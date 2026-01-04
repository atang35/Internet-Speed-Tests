from multiprocessing import connection
import os
import sys
import re
import json
import pandas as pd
import pyodbc
import datetime
import holidays
from datetime import datetime, date, timezone, timedelta, tzinfo
import pytz
from pathlib import Path

from sqlalchemy import text, create_engine
from dotenv import load_dotenv
from datetime import datetime
from rich.console import Console

# project directory or path
PROJECT_DIR = Path.cwd()

SQL_DIR = PROJECT_DIR / "sql"

# initialise console
console = Console()

MaseruTimeZone = pytz.timezone('Africa/Maseru')

ls_holidays = holidays.country_holidays("LS")

DRIVER = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")
HOST = os.getenv("SQLSERVER_HOST", "127.0.0.1")
PORT = os.getenv("SQLSERVER_PORT", "1433")
DB = os.getenv("SQLSERVER_DB", "InternetSpeed_DB")
UID = os.getenv("SQLSERVER_USER", "sa")
PWD = os.getenv("SQLSERVER_PWD")



#=================================================================================
#               extract integer from a text
#==================================================================================
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


   
def db_connection():
    """_summary_

    Returns:
        _type_: _description_
    """    
    connection_string = (
        f"DRIVER={DRIVER};"
        f"SERVER=127.0.0.1,{PORT};"
        f"UID={UID};"
        f"PWD={PWD};"
        "TrustServerCertificate=yes;"
        "Encrypt=yes;"
        "Login Timeout=90;"
        "Connect Timeout=90;"   
    )
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        conn.autocommit=False
        cursor = conn.execute("USE InternetSpeed_DB")
        cursor.close()
        
        return conn
    except pyodbc.Error as e:
        console.print(f"[bold red]Database connection failed: {e}[/]")
        sys.exit(1)


#======================================================================
#               load the queries into the python sql wrapper
#======================================================================
def load_sql_files(filename: str) -> str:
    """_summary_

    Args:
        filename (str): the sql script to read

    Raises:
        FileNotFoundError: if the sql script being referenced does not exist then the Error rises

    Returns:
        str: _description_
    """
    path =  Path.cwd() / "sql" / filename
    if not path.exists():
        raise FileNotFoundError(f"SQL file could not be found")
    
    return path.read_text()


#=====================================================
# Set the time frame for tracking internet speeds 
# we will default to the maximum we have 
#=====================================================

def time_bounds(df: pd.DataFrame, date_col: str):
    if date_col in df.columns:
        s = pd.to_datetime(df[date_col], errors="coerce")
    else:
        raise KeyError(f"Column '{date_col}' not found in data frame: {df}")
    
    return s.min(), s.max()


#===========================================================
#           A function to create and get sql connection
#============================================================
def get_db_connection():
    connection_string = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={HOST},{PORT};"
        f"DATABASE={DB};"
        f"UID={UID};"
        f"PWD={PWD};"
        "TrustServerCertificate=yes;"
        "Encrypt=yes;"
        "Login Timeout=30;"
        "Connect Timeout=30;"
    )
    
    return pyodbc.connect(connection_string)


def fetch_time_bounds(conn, sql_time_bounds: str):
    b = pd.read_sql(sql_time_bounds, conn).iloc[0]
    return pd.to_datetime(b["min_dt"]), pd.to_datetime(b["max_dt"])