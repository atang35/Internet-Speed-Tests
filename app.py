from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt 
import os 

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from shiny import App, render, ui
from shiny.express import input


from rich.console import Console


console = Console()


ui.panel_title("Internet Speed Test")
ui.input_slider("n", "N", 0, 10, 20)



load_dotenv()


@render.text
def txt():
    return f"n*2 is {input.n() * 2}"