import pyodbc
from datetime import datetime, time
import os
import sys
from dotenv import load_dotenv

from rich.console import Console
from helpers import time_dim

console = Console()
load_dotenv()

load_dotenv()
DRIVER = os.getenv("SQLSERVER_DRIVER")
SERVER = os.getenv("SQLSERVER_HOST")
PORT = os.getenv("SQLSERVER_PORT")
USER = os.getenv("SQLSERVER_USER")
PWD = os.getenv("SQLSERVER_PWD")
DB = os.getenv("SQLSERVER_DB")
UID = os.getenv("SQLSERVER_USER")


from speedtest import run_speedtest, get_server_info, transform
from helpers import time_dim
from ingest import get_db_connection, load_to_sql

if __name__ == "__main__":
    raw = run_speedtest()
    server_ip = raw["server"]["ip"]
    server_meta = get_server_info(server_ip)
    row = transform(raw)
    
    connection = get_db_connection()
    
    load_to_sql(row)