#Had to make some changes to my conda PATH on my computer to get this to work
#Needed to install the shiny package and run pip install shiny in the terminal

## Importing the necessary libraries
from shiny import App, render, ui, reactive
import pandas as pd

## Upload deault data
default_data = pd.read_csv('lung_disease_data.csv')

# UI Layout
app_ui = ui.page_fluid(
    ui.panel_title(ui.h2("Team 10- Project 2",class_="pt-4 pb-4 text-center")),
    ui.h2("Upload a CSV File"),
    ui.input_radio_buttons("data_source", "Choose Data Source", 
                   choices=["Upload CSV", "Use Default Data"], selected="Use Default Data"),
    ui.input_file("file", "Choose CSV File", multiple=False, accept=[".csv"]),
    ui.output_table("table")  # To display the uploaded data
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
