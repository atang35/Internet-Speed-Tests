from __future__ import annotations
from pathlib import Path

from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
from faicons import icon_svg

import os
from plotly.graph_objs.layout import yaxis
from great_tables import GT, html


from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from shiny import App, render, render_plot, ui, reactive
from shinywidgets import output_widget, render_plotly


from helpers import get_db_connection, load_sql_files, run_sql
from db import ENGINE

#from helpers import db_connection
from rich.console import Console


#sw.output_widget("speed_plot")
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


conn = get_db_connection()
conn.close()
console.print("Ok")


#==========================================================
# SQL queries to get data from the database
#==========================================================

SQL_LATEST = load_sql_files("01_latest.sql")
SQL_RAW_RANGE = load_sql_files("02_raw_range.sql")
SQL_HOURLY_MEDIANS = load_sql_files("03_median_speeds.sql")
SQL_TIME_BOUNDS = load_sql_files("04_time_bounds.sql")




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
            selected = "download_mbps",
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
        ui.output_ui("dynamic_metric_box"), #Absolute Change
        ui.output_ui("dynamic_pct_box") # Percentage Change
    ),    
    ui.hr(),
    
    ui.h4("Trend"),
    output_widget("trend_plot"),
    
    ui.hr(),
    
    ui.h4("Raw Data"),
    ui.output_ui("table"),
    ui.include_css(RESOURCES_DIR / 'styles.css' )
)

#===============================================================================
# ------------------------------------------- Server ---------------------------
#===============================================================================
# ... (imports and UI stay the same) ...

def server(input, output, session):
    
    # 1. Centralized mapping to keep things DRY
    METRIC_MAP = {
        "download_mbps": "median_download_mbps",
        "upload_mbps": "median_upload_mbps",
        "latency_ms": "median_latency_ms",
    }

    refresh_tick = reactive.Value(0)
    
    @reactive.effect
    @reactive.event(input.refresh)
    def _on_refresh():
        refresh_tick.set(refresh_tick.get() + 1)
        
    @reactive.calc
    def range_params():
        sd = input.start_date()
        ed = input.end_date()
        if sd is None or ed is None:
            return None
        
        return {
            "start_dt": datetime.combine(sd, datetime.min.time()), 
            "end_dt": datetime.combine(ed + timedelta(days=1), datetime.min.time())
        }

    @reactive.calc
    def hourly_medians():
        # Reactive dependencies
        refresh_tick.get() 
        params = range_params()
        
        if params is None:
            return pd.DataFrame()
        
        # Use ENGINE directly to handle connection pooling automatically
        df = run_sql(ENGINE, "03_median_speeds.sql", params=params)
        
        if not df.empty and "hour_bucket" in df.columns:
            df["hour_bucket"] = pd.to_datetime(df["hour_bucket"], errors="coerce")
        return df

    @reactive.calc
    def kpi_data():
        df = hourly_medians()
        if df.empty:
            return None
        
        col = METRIC_MAP[input.metric()]
        actual = float(df[col].iloc[-1])
        
        chg_abs, chg_pct = None, None
        if len(df) >= 2:
            prev = float(df[col].iloc[-2])
            chg_abs = actual - prev
            chg_pct = (chg_abs / prev * 100) if prev != 0 else None
            
        return {"actual": actual, "abs": chg_abs, "pct": chg_pct}

    # ============================= OUTPUTS =======================================    
    @render.ui
    def dynamic_metric_box():
        # 1. Access the data from existing kpi_data reactive
        data = kpi_data()
        if not data or data["abs"] is None:
            return ui.value_box("Change", "N/A", showcase=icon_svg("minus"))
        
        val = data["abs"]
        metric_name = input.metric()
        
        is_speed = "mbps" in metric_name.lower()  # Assuming your input ID is 'metric'
        
        # 2. Determine if 'higher is better'
        # Download and Upload (Mbps) are good when they go up.
        # Latency (ms) is bad when it goes up.
        
        is_good = (val >= 0) if is_speed else (val <= 0)
        
        # 3. Set theme and icon based on performance
        
        if val == 0:
            theme = "light"
            icon_name = "minus"
            text_color = "gray"
        elif is_good:
            theme = "success" # Green background
            icon_name = "arrow-up" if val > 0 else "arrow-down"
            text_color = "white"
        else:
            theme = "danger" # Red background
            icon_name = "arrow-up" if val > 0 else "arrow-down"
            text_color = "white"
        
        return ui.value_box(
            title = f"{metric_name.replace('_', ' ').title()} Change",
            value = f"{val:+.2f}",
            showcase = icon_svg(icon_name),
            theme = theme,
            subtitles = f"Measured in {'Mbps' if is_speed else 'ms'}"
        )
        
    @render.ui
    def dynamic_pct_box():
        data = kpi_data()
        if not data or data["pct"] is None:
            return ui.value_box("% Change", "-", showcase=icon_svg("percent"))
        
        pct_val = data["pct"]
        metric_name = input.metric()
        is_speed = "mbps" in metric_name.lower()
        
        # the same logic 
        is_good = (pct_val >= 0) if is_speed else (pct_val <= 0)
        
        # match the theme to the performance
        if pct_val == 0: 
            theme = "light"
        else:
            theme = "success" if is_good else "danger"
        return ui.value_box(
            title = "% change",
            value  = f"{pct_val:+.2f}%",
            showcase = icon_svg("percent"),
            theme = theme,
            subtitles = "Relative to previous hour"
        )
    
    @render.ui
    def kpi_actual():
        
        data = kpi_data()
        if not data: return "-"
        fmt = "{:.1f}" if input.metric() == "latency_ms" else "{:.2f}"
        return fmt.format(data["actual"])

    @render.ui
    def kpi_change_abs():
        data = kpi_data()
        if not data or data["abs"] is None: return "—"
        fmt = "{:+.1f}" if input.metric() == "latency_ms" else "{:+.2f}"
        return fmt.format(data["abs"])

    @render.ui
    def kpi_change_pct():
        data = kpi_data()
        if not data or data["pct"] is None: return "-"
        return f"{data['pct']:+.2f}%"

    @render_plotly
    def trend_plot():
        df = hourly_medians()
        
        # DEBUG: CHECK types in terminal
        print(df[['hour_bucket', METRIC_MAP[input.metric()]]].dtypes)
        print(df.head())
        
        if df.empty:
            return go.Figure().update_layout(title="No data for selected range")
        
        # Sort values to ensure line connects 
        
        df = df.sort_values("hour_bucket")
        min_date = df["hour_bucket"].min()
        max_date = df["hour_bucket"].max()
        
        metric_key = input.metric()
        col = METRIC_MAP[metric_key]
        unit = "ms" if metric_key == "latency_ms" else "Mbps"
        
        x_data = df["hour_bucket"].tolist()
        y_data = df[col].tolist()
        
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=x_data,
                y=y_data,
                mode="lines+markers",
                line=dict(width=3, color="#007bff"),
                marker=dict(size=6),
                connectgaps = True,
                hovertemplate=f"%{{y:.2f}} {unit}<extra></extra>"
            )
        )
        
        if "mbps" in col:
            fig.add_hline(
                y =35,
                line_dash = "dash",
                line_color = "red",
                line_width = 3,
                annotation_text = "ISP Promise (35 Mbps)",
                annotation_position ="bottom right"
            )
        
        fig.update_layout(
            xaxis = dict(
                type = "date",
                autorange = True,
                tickformat = "%b %d %Y \n%H:%M",
                title = "Time",
                automargin = True),
            yaxis = dict(
                title = metric_key.replace("_", " ").title(),
                autorange = True,
                automargin = True
            ),
            hovermode="x unified",
            template="plotly_white",
            margin = dict(
                l=50,
                r=20,
                t=30,
                b=60                
            )
        )
        return fig

    @render.ui
    def table():
        df = hourly_medians()
        
        if df.empty:
            return ui.div("No data available for selected range")
        
        cols = [
            "hour_bucket",
            "median_download_mbps",
            "median_upload_mbps",
             "median_latency_ms",
             ]
        gt = (
            GT(df[cols]
               .sort_values("hour_bucket", ascending = False))
            .tab_header(
                title = "Hourly Median Internet Speeds",
                subtitle = "Computed from raw speed test measurements"
            )
            .fmt_datetime(
                columns = "hour_bucket",
                date_style = "iso",
                time_style = "h_m_s_p"
            )
            .fmt_number(
                columns = ["median_download_mbps", "median_upload_mbps"],
                decimals = 2
            )
            .fmt_number(
                columns = "median_latency_ms",
                decimals = 1
            )
            .data_color(
                columns = "median_upload_mbps",
                palette= ["#f7fbff", "#08306b"]
            )
            .data_color(
                columns = "median_download_mbps",
                palette = ["#f7fcf5", "#00441b"]
            )
            .data_color(
                columns = "median_latency_ms",
                palette = ["#67000d", "#fff5f0"],
                reverse = True
            )
            .cols_label(
                hour_bucket = "Hour",
                median_download_mbps = "Download (Mbps)",
                median_upload_mbps = "Upload (Mbps)",
                median_latency_ms = "latency (ms)",
                )
            .opt_all_caps()
            .opt_table_outline()
            .tab_options(table_width="80%")
        )

        return gt


app = App(app_ui, server)