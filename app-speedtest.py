from pathlib import Path

from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from faicons import icon_svg

import os
import pyodbc


from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from shiny import App, render, render_plot, ui, reactive


from helpers import get_db_connection, load_sql_files, time_bounds, fetch_time_bounds

#from helpers import db_connection
from rich.console import Console

console = Console()

#========================================================
#               Define .env variables
#=========================================================
PROJECT_DIR = Path.cwd()
RESOURCES_DIR = PROJECT_DIR / "resources"

env_file = PROJECT_DIR / '.env'
load_dotenv(env_file)

#=======================================================================
# Connect to the data source 
# Load database credentials from .env variable
#===================================================================
DRIVER = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")
HOST = os.getenv("SQLSERVER_HOST", "127.0.0.1")
PORT = os.getenv("SQLSERVER_PORT", "1433")
DB = os.getenv("SQLSERVER_DB", "InternetSpeed_DB")
UID = os.getenv("SQLSERVER_USER", "sa")
PWD = os.getenv("SQLSERVER_PWD")


if not PWD:
    raise RuntimeError("Missing Database password in .env")



#==========================================================
# SQL queries to get data from the database
#==========================================================

SQL_LATEST = load_sql_files("01_latest.sql")
SQL_RAW_RANGE = load_sql_files("02_raw_range.sql")
SQL_HOURLY_MEDIANS = load_sql_files("03_median_speeds.sql")
SQL_TIME_BOUNDS = load_sql_files("04_time_bounds.sql")

#============================================================
#               Get data using the queries
#=============================================================

with get_db_connection() as conn:
    raw_range_df = pd.read_sql(SQL_RAW_RANGE, conn)
    median_speeds_df = pd.read_sql(SQL_HOURLY_MEDIANS, conn)




#==============================================================================================
#                       App UI Elements
#==============================================================================================

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select(
            "metric",
            "Metric",
            choices={
                "download_mbps": "Download (Mbps)",
                "upload_mbps": "Upload (Mbps)",
                "latency_ms": "Latency (ms)"
                },
            selected = "downloads_mbps",
            ),
        ui.input_date(
            "start_date",
            "Start Date",
            value = (datetime.today() - timedelta(days=7)).date()),
        ui.input_date(
            "end_date", 
            "End Date",
            value = datetime.today().date()
            ),
        ui.input_action_button("refresh", "Refresh"),
    ),
    ui.h2("Internet Speed Dashboard"),
    ui.layout_column_wrap(
        ui.value_box("Actual",
                     ui.output_ui("kpi_actual"),
                     showcase=icon_svg("rocket"),
                     ),
        ui.value_box("Change",
                     ui.output_ui("kpi_change_abs"),
                     showcase=icon_svg("change_icon")
                     ),
        ui.value_box("% Change",
                     ui.output_ui("kpi_change_pct"),
                     showcase=icon_svg("percent")
                     ),        
        ),
    ui.hr(),
    
    ui.h4("Trend"),
    ui.output_plot("trend_plot"),
    
    ui.hr(),
    
    ui.h4("Raw Data"),
    ui.output_data_frame("table")
)

#===============================================================================
# ------------------------------------------- Server ---------------------------
#===============================================================================
def server(input, output, session):
    
    @reactive.calc
    def df():
        input.refresh() # manual refresh trigger
        start = pd.to_datetime(input.start_date())
        end = pd.to_datetime(input.end_date()) + pd.Timedelta(days=1)
        
        query = """
                SELECT
                    t.local_tz,
                    i.download_mbps,
                    i.upload_mbps,
                    i.latency_ms,
                    i.jitter_ms
                FROM dbo.internet_speeds i
                JOIN dbo.time_metadata t ON i.measured_at_utc = t.time_id
                WHERE t.local_tz >= ? AND t.local_tz < ?;             
        """
        
        connection = None
        
        try: 
            connection = db_connection()
            data = pd.read_sql(query, connection, params=[start, end])
  
        
            if not data.empty:
                data["local_tz"] = pd.to_datetime(data["local_tz"])
        
            return data
        finally:
            if connection is not None:
                connection.close()
                
    @output
    @render.text

    def kpi_down():
        d = df() 
        return "" if d.empty else f"{d['download_mbps'].iloc[-1]:.2f}"
    
    @output
    @render.text
    def kpi_up():
        d = df()
        
        return "" if d.empty else f"{d['upload_mbps'].iloc[-1]:.2f}"
    
    @output
    @render.text
    
    def kpi_latency():
        d = df()
        
        return "" if d.empty else f"{d['latency_ms'].iloc[-1]:.2f}"

    @output
    @render.plot

    def trend_plot():
        d = df()
        
        fig, ax = plt.subplots()
        if not d.empty:
            ax.plot(d["local_tz"], d["download_mbps"], label="Download")
            ax.plot(d["local_tz"], d["upload_mbps"], label="Upload")
            ax.set_ylabel("Mbps")
            ax.set_xlabel("Time")
            ax.legend()
        return fig

    @output
    @render.data_frame

    def table():
        return df()
    
app = App(app_ui, server)    