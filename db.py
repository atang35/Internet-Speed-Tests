from json import load
import os
import urllib.parse
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import pandas as pd

PROJECT_DIR = Path.cwd()

load_dotenv(PROJECT_DIR / ".env")

def make_engine():
    """
    
    """
    
    # Example
    server = os.getenv("SQLSERVER_HOST")
    database = os.getenv("SQLSERVER_DB")
    username = os.getenv("SQLSERVER_USER")
    password = os.getenv("SQLSERVER_PWD")
    driver = os.getenv("SQLSERVER_DRIVER")
    
    # ODBC connection string
    
    odbc_str = (
        f"DRIVER={driver};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=30;"
    )
    
    connection_url = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(odbc_str)
    
    engine = create_engine(
        connection_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=5,
        max_overflow=10,
        future=True
    )
    
    return engine

ENGINE = make_engine()
