import pyodbc
from datetime import datetime, time
import os
import sys
from dotenv import load_dotenv

from pytz import utc
from rich.console import Console
from sqlalchemy import exists
from helpers import time_dim
from speedtest import get_server_info

console = Console()


load_dotenv()
DRIVER = os.getenv("SQLSERVER_DRIVER")
SERVER = os.getenv("SQLSERVER_HOST")
PORT = os.getenv("SQLSERVER_PORT")
USER = os.getenv("SQLSERVER_USER")
PWD = os.getenv("SQLSERVER_PWD")
DB = os.getenv("SQLSERVER_DB")
UID = os.getenv("SQLSERVER_USER")


def enrich_server(cursor, data: dict) -> dict:
    cursor.execute(
        "SELECT 1 FROM dbo.servers WHERE server_id = ?", 
        (data["server_id"],)
    )
    exists = cursor.fetchone() is not None
    
    if exists:
        return data
    
    ip_data = get_server_info(data["server_ip"])
    
    if ip_data:
        data["server_latitude"] = ip_data.get("latitude")
        data["server_longitude"] = ip_data.get("longitude")
    return data

def get_db_connection():
    """
    create and return a connection to the SQL Server database
    """
    conn_str = (
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
        
        
def load_to_sql(data: dict):
    if not data:
        return
    
    conn = None
    
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()
        
        # 1. update time_metadata table 
        time_dim(cursor=cursor, measured_at_utc=data["measured_at_utc"])
        data = enrich_server(cursor=cursor, data=data)
        
        # 2. upsert to servers table
        cursor.execute("""
        UPDATE dbo.servers
        SET 
            server_name = ?,
            server_host = ?,
            server_location = ?,
            server_country = ?,
            server_ip = ?,
            server_port = ?,
            server_latitude = ?,
            server_longitude = ?,
            isp = ?,
            last_seen_utc = GETUTCDATE()
        WHERE server_id = ?
        """, (
                data["server_name"], data["server_host"], data["server_location"],
                data["server_country"], data["server_ip"], data["server_port"],
                data["server_latitude"], data["server_longitude"], data["isp"],
                data["server_id"]
            ))

        if cursor.rowcount == 0:
            cursor.execute("""
                           INSERT INTO dbo.servers (
                               server_id, server_name, server_host, server_location, server_country,
                               server_ip, server_port, server_latitude, server_longitude,
                               isp, first_seen_utc, last_seen_utc
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETUTCDATE(), GETUTCDATE())
                        """, (
                            data["server_id"], data["server_name"], data["server_host"],
                            data["server_location"], data["server_country"],
                            data["server_ip"], data["server_port"],
                            data["server_latitude"], data["server_longitude"],
                            data["isp"]
                        ))
        

        # 3. Insert result metadata (ignore if already exists)
        cursor.execute("""
                        IF NOT EXISTS (SELECT 1 FROM result_metadata WHERE result_id = ?)
                        INSERT INTO result_metadata (
                        result_id, result_url, result_persisted, measured_at_utc
                        ) VALUES (?, ?, ?, ?)
                    """, (
                        data["result_id"],
                        data["result_id"],
                        data["result_url"], 
                        data["result_persisted"],
                        data["measured_at_utc"]
        ))
        
        # 4. Insert Speed fact
        cursor.execute("""
            INSERT INTO internet_speeds (
                result_id, server_id, measured_at_utc,
                download_mbps, upload_mbps, latency_ms, jitter_ms, packet_loss_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["result_id"],
            data["server_id"],
            data["measured_at_utc"],
            data["download_mbps"],
            data["upload_mbps"],
            data["latency_ms"],
            data["jitter_ms"],
            data["packet_loss_pct"]
        ))
        
        conn.commit()
        console.print(f"[green bold]Successfully saved the speed test results to SQL Server[/]")
        
    except Exception as e:
        console.print(f"[bold red]Database Error: {e}[/]")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
        
        
