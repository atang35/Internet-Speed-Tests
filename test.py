from requests import get
import json 
import pandas as pd
import subprocess

from rich.console import Console

console = Console()

ip_address = "'8.8.8.8'"
ip_address_clean = ip_address.strip("'")
cmd = ["curl", f"https://ipapi.co/{ip_address_clean}/json/"]

ip_check = subprocess.run(cmd)
response=get("https://ipapi.co/8.8.8.8/json/")
resp = response.status_code
#console.print(ip_check)
response = int(str(response).strip().replace(" ", "").replace("Response", "").replace("<", "").replace(">", "").replace("[", "").replace("]", ""))

console.print(response == 429)
console.print(response)
console.print(resp)
console.print(ip_check)