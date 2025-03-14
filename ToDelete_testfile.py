from shiny import App, render, ui, reactive
import pandas as pd

app_ui = ui.page_fluid(
    ui.input_action_button("refresh", "Refresh Table"),
    ui.output_table("table_output")
)

def server(input, output, session):
    # Store the dataframe in a reactive value
    data = reactive.Value(pd.DataFrame({"Name": ["Alice", "Bob"], "Age": [25, 30]}))

    @output
    @render.table
    def table_output():
        return data()

    # Button click updates the dataframe and triggers reactivity
    @reactive.effect
    @reactive.event(input.refresh)
    def update_data():
        df = data()
        df.loc[df["Name"] == "Alice", "Age"] += 1  # Modify Alice's age
        data.set(df)  # Update the reactive value, triggering reactivity

app = App(app_ui, server)