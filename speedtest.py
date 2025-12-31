from copy import Error
import json
import subprocess
from datetime import datetime, timezone
import sys


import re

from pandas.io.gbq import import_optional_dependency
from requests import get, RequestException

from rich import console
from rich.console import Console
#from helpers import extract_int

console = Console()



def run_speedtest(server_id=None) -> dict:
    """_summary_
    Run a speedtest and return the results as a dictionary
    
    Args:
        server_id: The ID of the server to test

    Returns:
        A dictionary containing the speedtest results
    """
    cmd = ["speedtest", "--format", "json-pretty", "--progress", "no"]
    
    if server_id:
        cmd.extend(["--server-id", str(server_id)])

    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return json.loads(p.stdout)
    except subprocess.CalledProcessError as subprocess_error:
        console.print(f"[bold red]Speedtest CLI failed: {subprocess_error.stderr.strip()}[/]")
        return None
    except json.JSONDecodeError as json_error:
        console.print(f"[bold red]Failed to parse JSON from speedtest after 60 seconds: {json_error}[/]")
        return None
    except Exception as e:
        console.print(f"[bold red]Unexpected error running speedtest: {e}[/]")
        return None


def get_server_info(ip_address: str) -> dict | None:
    """_summary_

    Args:
        ip_address (str): _description_

    Returns:
        dict | None: _description_
    """
    if not ip_address:
        console.print(f"[bold yellow]No valid IP address provided[/]")
        return None
    
    ip_address = ip_address.strip()
    url = f"https://ipapi.co/{ip_address}/json/"
    cmd = ["curl", url]
    
    try:
        response = get(url, timeout=8)
        
        if response.status_code != 200:
            console.print(f"[bold yellow]ipapi.co -> {response.status_code} for {ip_address}[/]")
            if response.status_code == 429:
                console.print(f"[bold yellow]Rate limit hit - try again later[/]")
            return None
        # parse data only if the status code = 200
        data = response.json()
        
        # API level errors
        if data.get("error"):
            console.print(f"[bold yellow]ipapi.co error :{data.get('message') or data.get('reason')}[/]")
            return None
        console.print(f"[dim]Enriched {ip_address} with meta data from ipapi.co[/]")
        return data
    except RequestException as e:
        console.print(f"[bold red]Network error fetching information for {ip_address}: {e}[/]")
        return None
    except ValueError as e:
        console.print(f"[red bold]Invalid json response from ipapi.co: {e}[/]")
        return None
    except Exception as e:
        console.print(f"[bold red]Unexpected error in getting server information: {e}[/]")
        return None

def transform(raw_results: dict) -> dict | None:
    """ the function will transform the json response from running the speedtest CLI

    Args:
        raw_results (dict): json 

    Returns:
        dict | None: _description_
    """
    try:
        ts_str = raw_results["timestamp"]
        measured_at_utc = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        
        # Bandwidth is in bytes/sec -> convert to Mbps
        down_mbps = (raw_results["download"]["bandwidth"] * 8) / 1_000_000       
        up_mbps = (raw_results["upload"]["bandwidth"] * 8) / 1_000_000
        
        # Ping Info
        latency_ms = raw_results["ping"]["latency"]
        jitter_ms = raw_results["ping"].get("jitter")
        packet_loss_pct = raw_results.get("packetLoss")
        
        # Other core fields
        isp = raw_results.get("isp")
        server_id = raw_results["server"]["id"]
        server_name = str(raw_results["server"]["name"])
        server_location = raw_results["server"]["location"]
        server_host = raw_results["server"]["host"]
        server_country = raw_results["server"]["country"]
        server_ip = str(raw_results["server"]["ip"]).strip().strip("'").strip('"')
        server_port = raw_results["server"]["port"]
                
        # results meta data
        result_id = raw_results["result"]["id"]
        result_url = str(raw_results["result"].get("url"))
        result_persisted = raw_results["result"]["persisted"]
        
        
        # extract server coordinates
        #ip_data = get_server_info(server_ip)
        
        server_lat = None
        server_long = None
        
        return {
            "measured_at_utc": measured_at_utc,
            "download_mbps": down_mbps,
            "upload_mbps": up_mbps,
            "latency_ms": latency_ms,
            "jitter_ms": jitter_ms,
            "packet_loss_pct": packet_loss_pct,
            "isp": isp,
            "server_id": server_id,
            "server_name": server_name,
            "server_location": server_location,
            "server_host": server_host,
            "server_country": server_country,
            "server_ip": server_ip,
            "server_port": server_port,
            "result_id": result_id,
            "result_url": result_url,
            "result_persisted": result_persisted,
            "server_latitude": server_lat,
            "server_longitude": server_long,
        }
    except Exception as e:
        console.print(f"[bold red]Error transforming results: {e}[/]")
        return None
        