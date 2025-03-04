#Had to make some changes to my conda PATH on my computer to get this to work
#Needed to install the shiny package and run pip install shiny in the terminal

## Importing the necessary libraries
from shiny import App, render, ui, reactive
import pandas as pd
#import pyreadr  # For reading RDS files

## Upload deault data
default_data = pd.read_csv('lung_disease_data.csv')

# UI Layout
app_ui = ui.page_sidebar(
    ui.sidebar( #sidebar for uploading data
        # for data selection
        ui.input_radio_buttons("data_source", "Choose Data Source: ", 
                   choices=["Upload dataset", "Use Default Data"], selected="Use Default Data"),

        ui.input_file("file", "Upload a dataset", multiple=False, accept=[".csv",".rds",".xlsx",".json"]),
        title="Load Data",
    ),
    ui.page_fillable( #page for the tabs
        ui.navset_card_tab(  
            ui.nav_panel("Data Output", 
                ui.output_table("table")),
            ui.nav_panel("Cleaning & Preprocessing", "Panel B content"),
            ui.nav_panel("Feature Engineering", "Panel C content"),
            ui.nav_panel("EDA", "Panel D content"),
            id="tab"
            )  
        ),
    title="Team 10- 5243 Project 2",
)

# Server Logic
def server(input, output, session):

    # Reactive function to read uploaded file
    @reactive.calc
    def get_data():
        if input.data_source() == "Use Default Data":
            return default_data
        file = input.file()
        if not file:
            return None  # No file uploaded yet
        return pd.read_csv(file[0]["datapath"])  # Read CSV

    # Render table output
    @output
    @render.table
    def table():
        data = get_data()
        return data 

# Run the Shiny App
app = App(app_ui, server)
