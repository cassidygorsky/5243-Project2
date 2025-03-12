## Importing the necessary libraries
from shiny import App, render, ui, reactive
import pandas as pd
import numpy as np
import seaborn as sns
import io
import re
import tempfile
from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder
from sklearn.impute import SimpleImputer
import matplotlib.pyplot as plt
from scipy import stats
from sklearn.feature_selection import VarianceThreshold
from sklearn.decomposition import PCA
pd.options.mode.chained_assignment = None
import pyreadr  # For reading RDS files. Had to manually install pyreadr through my anaconda prompt


## Upload default data
default_data = pd.read_csv('lung_disease_data.csv')

# all the clean steps are coded as functions and then add into shiny
## data format clean (standardize string,  convert string into number if avaliable)
def clean_strings_and_convert_numbers(df):
    df_clean = df.copy()
    for col in df_clean.select_dtypes(include=["object"]).columns:
        # remove space and convert to lower
        df_clean[col] = df_clean[col].str.strip().str.lower()
        # remove to np.nan
        df_clean[col] = df_clean[col].replace(["na", "n/a", "none", "null", ""], np.nan)
        # convert to number
        try:
            converted = pd.to_numeric(df_clean[col], errors="coerce")
            if converted.notna().mean() > 0.5:
                df_clean[col] = converted
        except Exception:
            pass
    return df_clean

## convert to datetime
def convert_to_dates(df):
    df_clean = df.copy()
    for col in df_clean.columns:
        if df_clean[col].dtype == "object":
            try:
                converted = pd.to_datetime(df_clean[col], errors="coerce")
                if converted.notna().mean() > 0.5:
                    df_clean[col] = converted
            except Exception:
                pass
    return df_clean

## remove duplicates
def remove_duplicates(df):
    return df.drop_duplicates()

## missing value(able to replace missing value with mean, median, mode or just drop)
## user can handle specific columns also automately handle all numerical columns
def handle_missing_values(df, strategy="mean", drop_columns=[]):
    if len(drop_columns) > 0:

        df = df.dropna(subset=drop_columns)
    else:
        if strategy == "drop":
            df = df.dropna()
        else:
            imputer = SimpleImputer(strategy=strategy)
            num_cols = df.select_dtypes(include=["number"]).columns
            df[num_cols] = imputer.fit_transform(df[num_cols])

    return df

## outlier
## function detect outliers using IQR method or z-score method, and can delete, replace as mean or quantiles
def handle_outliers(df, method="IQR", z_thresh=3, columns=None, handling_method="delete"):
    if columns is None:
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    else:
        numeric_cols = [col for col in columns if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
    if not numeric_cols:
        return df, pd.DataFrame()

    # category as methods
    if method == "IQR":
        if handling_method == "delete":
            mask = pd.Series(False, index=df.index)
            for col in numeric_cols:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                mask = mask | ((df[col] < lower_bound) | (df[col] > upper_bound))
            outliers = df[mask]
            df_clean = df[~mask]
            modifications = outliers.copy()
        elif handling_method in ["mean", "median", "winsorize"]:
            df_clean = df.copy()
            modifications = []
            for col in numeric_cols:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                for idx, value in df_clean[col].iteritems():
                    if value < lower_bound or value > upper_bound:
                        original_value = value
                        if handling_method == "mean":
                            replacement = df[col].mean()
                        elif handling_method == "median":
                            replacement = df[col].median()
                        elif handling_method == "winsorize":
                            replacement = lower_bound if value < lower_bound else upper_bound
                        modifications.append({
                            "index": idx,
                            "column": col,
                            "original": original_value,
                            "replacement": replacement
                        })
                        df_clean.at[idx, col] = replacement
                    modifications = pd.DataFrame(modifications)
                else:
                    df_clean = df.copy()
                    modifications = pd.DataFrame()
        elif method == "Z-score":
            if handling_method == "delete":
                mask = pd.Series(False, index=df.index)
                for col in numeric_cols:
                    mean = df[col].mean()
                    std = df[col].std()
                    lower_bound = mean - z_thresh * std
                    upper_bound = mean + z_thresh * std
                    mask = mask | ((df[col] < lower_bound) | (df[col] > upper_bound))
                outliers = df[mask]
                df_clean = df[~mask]
                modifications = outliers.copy()
            elif handling_method in ["mean", "median", "winsorize"]:
                df_clean = df.copy()
                modifications = []
                for col in numeric_cols:
                    mean = df[col].mean()
                    std = df[col].std()
                    lower_bound = mean - z_thresh * std
                    upper_bound = mean + z_thresh * std
                    for idx, value in df_clean[col].iteritems():
                        if value < lower_bound or value > upper_bound:
                            original_value = value
                            if handling_method == "mean":
                                replacement = mean
                            elif handling_method == "median":
                                replacement = df[col].median()
                            elif handling_method == "winsorize":
                                replacement = lower_bound if value < lower_bound else upper_bound
                            modifications.append({
                                "index": idx,
                                "column": col,
                                "original": original_value,
                                "replacement": replacement
                            })
                            df_clean.at[idx, col] = replacement
                        modifications = pd.DataFrame(modifications)
                    else:
                        df_clean = df.copy()
                        modifications = pd.DataFrame()
                else:
                    df_clean = df.copy()
                    modifications = pd.DataFrame()
                return df_clean, modifications

## standardize numerical data
## choose specific columns to normalize
def normalize_data(df, normalize_columns=[]):
    if len(normalize_columns) > 0:
        scaler = StandardScaler()
        df[normalize_columns] = scaler.fit_transform(df[normalize_columns])
    return df

## encoding categorical variables
## for variables' unique value lessthan a user set threshold using one-hot encoing, or use lable encoding. default threshold:10
def encode_categorical_data(df, one_hot_threshold=10):
    df = df.copy()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns
    for col in categorical_cols:
        unique_values = df[col].nunique()
        # skip if only one unique value
        if unique_values <= 1:
            continue

        if unique_values <= one_hot_threshold:
            encoder = OneHotEncoder(sparse_output=False, drop="first")
            encoded_cols = encoder.fit_transform(df[[col]])
            if encoded_cols.shape[1] == 0:
                continue
            encoded_df = pd.DataFrame(encoded_cols, columns=encoder.get_feature_names_out([col]), index=df.index)
            df = df.drop(columns=[col])
            df = pd.concat([df, encoded_df], axis=1)
        else:
            from sklearn.preprocessing import LabelEncoder
            encoder = LabelEncoder()
            df[col] = encoder.fit_transform(df[col])
    return df


def zero_var(data, t):
    num_col = data.select_dtypes(include=['number']).columns.tolist()

    if not data.isnull().values.any():
        vt = VarianceThreshold(threshold=t)
        x_num = data[num_col]
        vt.fit(x_num)
        features_to_keep = x_num.columns[vt.get_support()]
        features_to_drop = [col for col in x_num.columns if col not in features_to_keep]
        data = data.drop(columns=features_to_drop)

        return data, features_to_drop


# UI Layout
app_ui = ui.page_sidebar(
    ui.sidebar( #sidebar for uploading data
        # for data selection
        ui.input_radio_buttons("data_source", "Choose Data Source: ", 
                   choices=["Upload dataset", "Use Default Data"], selected="Use Default Data"),

        # This will conditionally show the file upload input
        ui.output_ui("show_upload"),
        title="Load Data",
    ),
    ui.page_fillable( #page for the tabs
        ui.navset_card_tab(
                ui.nav_panel("User Guide",

                ui.markdown("""
                ### **Feature Engineering**
                The Feature Engineering section allows users to create new features and modify existing features, providing visual feedback to display the impact of such transformations.
                #### Target Feature Transformation 
                Select a column and transformation method (Log Transformation, Box-Cox, Yeo-Johnson) to see the impact of the transformation on the column. 
                Note that the column must have missing values filled in from the data preprocessing step in order for the Box-Cox and Yeo-Johnson to yield results. 
                Typically, the Box-Cox method requires that the column values are positive, but this has been considered such that non-positive values are accommodated for. 
                #### Feature Selection
                This method allows for dimensionality reduction. There are several feature selection methods:
                - **PCA** allows the user to select number of PCA components and yields the variance explained by each component. Please ensure the data is properly preprocessed to yield results (e.g. handle missing values, scaling, hot-one encoding, etc.) 
                - **Filter Zero-Var Variables** allows users to select variance threshold (from 0 to max(var)) for filtering and returns the features dropped at said threshold. Please ensure data is properly processed to yield results (e.g. fill missing values, etc.)
                - **Manually Remove** allows users to select specific column(s) to manually remove from the table. 
                #### Create New Features
                This method allows users to create new features based on pre-existing features in the data. Input name of new feature, new feature formula, and the pre-existing features which are used in the new formula.
                In the "Input New Formula," please ensure the columns are spelled correctly and the expression is a valid math expression. Also features should not have spaces in their names. 
                
                
                """),
                ui.markdown("""
                ### **Exploratory Data Analysis** 
                The EDA section allows users to explore data through interactive visualizations, summary statistics, and correlation analysis.  
                Filters can be applied to focus on specific subsets of the dataset, and all outputs update dynamically based on user selections.                
                #### Apply Filters  
                Filters help refine the dataset for analysis. For numerical columns, sliders allow selection of value ranges, while categorical columns can be filtered using dropdown menus.  
                When a filter is adjusted, all visualizations and statistical summaries update automatically.  
                #### Visualization  
                Several types of visualizations are available to help interpret the data:  
                - **Histograms** display the distribution of a single numerical variable.  
                - **Scatter plots** show relationships between two numerical variables.  
                - **Box plots** highlight the spread of data and detect potential outliers.  
                - **Correlation heatmaps** provide an overview of relationships between numerical features.  
                #### Statistical Insights  
                Summary statistics, including mean, median, minimum, maximum, and standard deviation, offer a quick overview of the dataset.  
                A correlation table helps identify potential relationships between numerical variables, which can be useful for deeper analysis.  
                """)
            ),

            ui.nav_panel("Data Output", 
                         ui.input_action_button("save_changes_cleaning", "Save Changes"),
                         ui.output_table("table")),
            ui.nav_panel("Cleaning & Preprocessing", 
                         # upper part: different operation columns
                        #ui.input_action_button("save_changes_cleaning", "Save Changes"), #save changes button
                         ui.row(
                             # basic clean (string clean, number convert, duplication remove)
                             ui.column(2,
                                       ui.h4("Data Cleaning"),
                                       ui.input_checkbox("apply_string_cleaning", "Clean Strings & Convert Numbers",
                                                         value=False),
                                       ui.input_checkbox("apply_date_conversion", "Convert to Dates", value=False),
                                       ui.input_checkbox("remove_duplicates", "Remove Duplicate Rows", value=False)
                                       ),
                             # missing value
                             ui.column(2,
                                       ui.h4("Missing Value Handling"),
                                       ui.input_selectize("missing_value_strategy", "Missing Value Strategy:",
                                                          choices=["mean", "median", "mode", "drop"], selected="mean"),
                                       ui.input_checkbox("select_all_na", "Select All Columns for NA Removal",
                                                         value=False),
                                       ui.input_checkbox("deselect_all_na", "Deselect All Columns for NA Removal",
                                                         value=False),
                                       ui.input_selectize("drop_na_columns", "Columns to Drop NA:", choices=[],
                                                          multiple=True)
                                       ),
                             # ouliers
                             ui.column(2,
                                       ui.h4("Outlier Handling"),
                                       ui.input_checkbox("remove_outliers", "Handle Outliers", value=False),
                                       ui.input_radio_buttons("outlier_method", "Detection Method:",
                                                              choices=["IQR", "Z-score"], selected="IQR"),
                                       ui.input_slider("zscore_threshold", "Z-score Threshold", min=2, max=5, value=3,
                                                       step=0.1),
                                       ui.input_selectize("outlier_columns", "Columns for Outlier Handling:",
                                                          choices=[], multiple=True),
                                       ui.input_checkbox("select_all_outliers", "Select All Numeric Columns",
                                                         value=False),
                                       ui.input_checkbox("deselect_all_outliers", "Deselect All Numeric Columns",
                                                         value=False),
                                       ui.input_selectize("outlier_handling", "Handling Option:",
                                                          choices=["delete", "mean", "median", "winsorize"],
                                                          selected="delete")
                                       ),
                             # normalize
                             ui.column(2,
                                       ui.h4("Normalization"),
                                       ui.input_checkbox("enable_normalization", "Enable Normalization", value=False),
                                       ui.input_checkbox("select_all_normalize", "Select All Numeric Columns",
                                                         value=False),
                                       ui.input_checkbox("deselect_all_normalize", "Deselect All Numeric Columns",
                                                         value=False),
                                       ui.input_selectize("normalize_columns", "Columns to Normalize:", choices=[],
                                                          multiple=True)
                                       ),
                            # encode
                            ui.column(2,
                                ui.h4("Encoding"),
                                ui.input_checkbox("perform_encoding", "Perform Encoding", value=False),
                                ui.input_slider("one_hot_threshold", "One-Hot Encoding Threshold", min=2, max=50, value=10)
                            )
                        ),
                        # lower part: left for data preview, right for modifications review
                        ui.row(
                            ui.column(6,
                                ui.h4("Data Set Preview"),
                                ui.output_table("preview_table")
                            ),
                            ui.column(6,
                                ui.h4("Modifications (Deleted/Changed Rows)"),
                                ui.output_table("modifications_table")
                            )
                        )
                    ),
            ui.nav_panel("Feature Engineering",
                        ui.row(
                            ui.column(4,
                         ui.input_radio_buttons(
                             "method",
                             "Choose a method:",
                             {
                                 "trans": "Target Feature Transformation",
                                 "select": "Feature Selection",
                                 "new": "Create New Features"}
                         )),
                             # ui.column(6,
                             #     ui.input_action_button(
                             #     "update_data", "Update Table", )
                             #           )
                            ),
                        # Target Feature Transformation
                        ui.row(
                        ui.panel_conditional(
                            "input.method.includes('trans')",

                            # drop down menu for which feature transformation method
                            ui.column(4,
                            ui.input_select(
                                "target_trans",
                                "Select Transformation Method:",
                                {"log": "Log Transformation", "bc": "Box-Cox Transformation",
                                 "yj": "Yeo-Johnson Transformation"}, selected=None)),

                            ui.column(4,
                                ui.input_select("target_feat", "Choose Target Feature:",choices=[], selected=None)),


                                ui.output_plot("target_fe_plot")
                        )),
                        ui.row(
                        # Feature Selection Methods
                        ui.column(4,
                            ui.panel_conditional(
                                    "input.method.includes('select')",
                            # "input.method === 'select'",
                            # drop down menu for which feature selection method
                            ui.input_select(
                                "feat_select",
                                "Select Feature Selection Method:",
                                {"pca": "PCA", "zero": "Filter Zero-Var Features", "rem":"Manually Remove"}, selected=None))),

                            # if pca chosen
                            ui.panel_conditional("input.method.includes('select') && input.feat_select === 'pca'",
                        ui.column(4,
                            ui.input_slider("num_components", "# of PCA Components:", min=1, max=10, value=1)),
                            # text containing info about feature selection (e.g. feat dropped)
                            ui.output_text("pca_label"),
                            ),

                            # if zero variance features filter chosen
                            ui.panel_conditional(
                            "input.method.includes('select') && input.feat_select === 'zero'",
                                ui.column(4,
                            ui.input_slider("var", "Variance Threshold:", min=0, max=10, value=0)),

                            # text containing info about feature selection (e.g. feat dropped)
                            ui.output_text("fd_label")
                            ),

                            # if manual removal chosen
                            ui.column(4,
                            ui.panel_conditional(
                            "input.method.includes('select') && input.feat_select === 'rem'",
                            ui.input_selectize("rem_feat", "Select Features to Remove:",choices=[], multiple=True),
                            )),
                        ),
                        ui.panel_conditional(
                            "input.method.includes('new')",
                            # drop down menu for which feature transformation method
                            #     ui.output_text_verbatim("instructions"),############3
                        ui.row(
                        ui.column(4,
                                      ui.input_text(
                                          "new_name",
                                          "Input New Feature Name",
                                      )),
                            ui.column(4,
                                      ui.input_text(
                                          "new_feat",
                                          "Input New Feature Formula",
                                      )),
                            ui.column(4,
                                ui.input_selectize("feats", "Select Features in Formula:",choices=[], multiple=True))),

                            ui.row(
                            ui.output_text("new_feat_info"))
                        ),
                        ui.output_table("fe_modified_table")
            ),
                        ui.nav_panel("EDA", 
                ui.row(
                    ui.column(4,
                        ui.input_select("plot_type", "Select Plot Type", 
                                        choices=["Histogram", "Scatter Plot", "Box Plot", "Correlation Heatmap"], multiple=False),
                        ui.input_select("x_var", "Choose X-axis Variable (for all plots)", choices=[], multiple=False),
                        ui.input_select("y_var", "Choose Y-axis Variable (for scatterplot only)", choices=[], multiple=False),               
                    ),
                    ui.column(4,
                        ui.output_ui("dynamic_filters_num"),
                    ),
                    ui.column(4,
                        ui.output_ui("dynamic_filters_cate"),
                    )
                ),
                ui.output_image("dynamic_plot", height="600px"),
                ui.h4("Dataset Summary"),
                ui.output_table("summary_stats"),
                ui.output_table("correlation_table")
            ),
            id="tab"
            )  
        ),
    title="Team 10- 5243 Project 2",
)

# Server Logic
def server(input, output, session):
    removed_rows = reactive.Value(pd.DataFrame())
    outlier_modifications = reactive.Value(pd.DataFrame())
    
    # Dynamically show the file upload input based on selection
    @render.ui
    def show_upload():
        if input.data_source() == "Upload dataset":
            return ui.input_file("file", "Upload a dataset", multiple=False, accept=[".csv", ".rds", ".xlsx", ".json"])
        return None  # Hide if "Default Dataset" is selected
    
    # Replace special characters with underscores when dataset is uploaded
    def clean_column_name(col_name):
        return re.sub(r'[^a-zA-Z0-9_]', '_', col_name)
        
    # Create a reactive data store to hold the dataset
    stored_data = reactive.Value(None)  # Starts as None, will be set by get_data()

    # Reset store_data when a new dataset is selected
    @reactive.effect #run whenever it's dependencies change
    def reset_data():
        """When the user selects a new dataset, reset the stored dataset."""
        stored_data.set(get_data())  # Set store_data to the freshly loaded dataset

    # Reactive function to read uploaded file
    @reactive.calc
    def get_data(): #to do: need to create a button to call this on each page
        if input.data_source() == "Use Default Data":
            return default_data.copy()

        file = input.file()
        if not file:
            return None  # No file uploaded yet
        # Get file extension
        ext = file[0]["name"].split(".")[-1].lower()

        #Read file based on format
        try:
            if ext == "csv":
                df = pd.read_csv(file[0]["datapath"])
                df.columns = [clean_column_name(col) for col in df.columns]
            elif ext in ["xls", "xlsx"]:
                df = pd.read_excel(file[0]["datapath"])
                df.columns = [clean_column_name(col) for col in df.columns]
            elif ext == "json":
                df = pd.read_json(file[0]["datapath"])
                df.columns = [clean_column_name(col) for col in df.columns]
            elif ext == "rds":
                df = pyreadr.read_r(file[0]["datapath"])[None]  # Extract first object
                df.columns = [clean_column_name(col) for col in df.columns]
            else:
                return None  # Unsupported file type
            return df
        except Exception as e:
            print(f"Error reading file: {e}")
            return None  # Return None if there's an error

    # Render table output
    @output
    @render.table
    def table(): #refresh data
        return stored_data.get()
    
    #save updated data after cleaning
    @reactive.effect
    def modify_data_cleaning():
        """Modify data when 'Save Changes' is clicked in Tab 1."""
        if input.save_changes_cleaning:
            df = stored_data.get()
            df["new_column"] = 2  # Example modification
            stored_data.set(df)

    @reactive.effect
    def update_column_choices():
        df = get_data()
        if df is not None:
            numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()
            ui.update_selectize("drop_na_columns", choices=df.columns.tolist(), session=session)
            ui.update_selectize("normalize_columns", choices=numeric_columns, session=session)
            ui.update_selectize("outlier_columns", choices=numeric_columns, session=session)
            ui.update_select("target_feat", label="Select Target Feature", choices=numeric_columns, session=session)
            variance = df[numeric_columns].var()
            ui.update_slider("var", max=int(variance.max()))
            if input.method() == 'select' and input.feat_select() == 'pca':
                data = encoded_data() if input.perform_encoding() else cleaned_data()
                ui.update_slider("num_components", max = data.shape[1])
            ui.update_selectize("rem_feat", choices=df.columns.tolist(), session=session)
            ui.update_selectize("feats", choices=numeric_columns, session=session)

            if input.select_all_na():
                ui.update_selectize("drop_na_columns", selected=df.columns.tolist(), session=session)
            elif input.deselect_all_na():
                ui.update_selectize("drop_na_columns", selected=[], session=session)

            if input.select_all_normalize():
                ui.update_selectize("normalize_columns", selected=numeric_columns, session=session)
            elif input.deselect_all_normalize():
                ui.update_selectize("normalize_columns", selected=[], session=session)

            if input.select_all_outliers():
                ui.update_selectize("outlier_columns", selected=numeric_columns, session=session)
            elif input.deselect_all_outliers():
                ui.update_selectize("outlier_columns", selected=[], session=session)

    @reactive.calc
    def cleaned_data():
        df = get_data()
        if df is None:
            print("⚠ No data to clean")
            return None
        ### standardize data format
        if input.apply_string_cleaning():
            df = clean_strings_and_convert_numbers(df)
        ### date convert
        if input.apply_date_conversion():
            df = convert_to_dates(df)
        ### missing value
        df = handle_missing_values(df, strategy=input.missing_value_strategy(), drop_columns=input.drop_na_columns())

        ### duplications
        if input.remove_duplicates():
            mask = df.duplicated(keep='first')
            removed = df[mask]
            removed_rows.set(removed)
            df = remove_duplicates(df)
        else:
            removed_rows.set(pd.DataFrame())

        ### outliers
        if input.remove_outliers():
            method = input.outlier_method()
            z_thresh = input.zscore_threshold()
            outlier_cols = list(input.outlier_columns()) if input.outlier_columns() else df.select_dtypes(
                include=["number"]).columns.tolist()
            handling_option = input.outlier_handling()
            df, modifications = handle_outliers(df, method=method, z_thresh=z_thresh, columns=outlier_cols,
                                                handling_method=handling_option)
            outlier_modifications.set(modifications)
        else:
            outlier_modifications.set(pd.DataFrame())

        ### normalize
        if input.enable_normalization():
            normalize_columns = list(input.normalize_columns())
            df = normalize_data(df, normalize_columns=normalize_columns)

        return df

    ### encoding
    @reactive.calc
    def encoded_data():
        df = cleaned_data()
        if df is None:
            return None
        if input.perform_encoding():
            return encode_categorical_data(df, one_hot_threshold=input.one_hot_threshold())
        else:
            return df

    ### combine outliers and duplications
    @reactive.calc
    def modifications_data():
        dup = removed_rows()
        out_mod = outlier_modifications()
        if dup is None:
            dup = pd.DataFrame()
        if out_mod is None:
            out_mod = pd.DataFrame()
        if dup.empty and out_mod.empty:
            return pd.DataFrame()
        try:
            return pd.concat([dup, out_mod], ignore_index=True)
        except Exception:
            return out_mod

    # data preview
    @output
    @render.table
    def table():
        return get_data()

    @output
    @render.table
    def preview_table():
        df = encoded_data() if input.perform_encoding() else cleaned_data()
        if df is None or df.empty:
            return pd.DataFrame({"Message": ["No data available"]})
        n = len(df)
        if n > 20:
            preview = pd.concat([df.head(10), df.tail(10)])
        else:
            preview = df
        return preview

    ### modifications
    @output
    @render.table
    def modifications_table():
        return modifications_data()

    @output
    @render.table
    def encoded_table():
        return encoded_data()

    #### Feature Engineering
    @output
    @render.table
    def fe_modified_table():
        n = len(cleaned_data())
        if n > 20:
            if input.method()=='trans':
                preview = pd.concat([target_fe_calc().head(10), target_fe_calc().tail(10)])
            elif input.method()=='select'  and input.feat_select() == 'pca' and pca_return is not None:
                return
            #     try:
            #         data, text = pca_return()
            #     except Exception:
            #         data = encoded_data() if input.perform_encoding() else cleaned_data()
            elif input.method()=='select' and input.feat_select() == 'zero' and zero_return is not None:
                try:
                    data, features_to_drop = zero_return()
                    preview = pd.concat([data.head(10), data.tail(10)])
                except Exception:
                    preview =pd.concat([encoded_data().head(10), encoded_data().tail(10)]) if input.perform_encoding() else pd.concat([cleaned_data().head(10), cleaned_data().tail(10)])
            elif input.method()=='new' and new_feat() is not None:
                try:
                    data=new_feat()
                    preview = pd.concat([data.head(10), data.tail(10)])
                except Exception:
                    preview =pd.concat([encoded_data().head(10), encoded_data().tail(10)]) if input.perform_encoding() else pd.concat([cleaned_data().head(10), cleaned_data().tail(10)])
            elif input.method()=='select' and input.feat_select() == 'rem':
                preview = pd.concat([manual_remove().head(10), manual_remove().tail(10)])
            elif input.perform_encoding():
                preview = pd.concat([encoded_data().head(10), encoded_data().tail(10)])
            else:
                preview = pd.concat([cleaned_data().head(10), cleaned_data().tail(10)])
        elif input.perform_encoding():
            preview = encoded_data()
        else:
            preview = cleaned_data()
        return preview



    # @reactive.event(input.update_data, ignore_none=True)
    # @reactive.calc
    # def save_changes():
    #     data = encoded_data() if input.perform_encoding() else cleaned_data()
    #     if len(input.method())>0:
    #         if 'trans' in input.method():
    #             data = target_fe_calc()
    #         elif 'select' in input.method() and input.feat_select() == 'pca':
    #             data, text = pca_return()
    #         elif 'select' in input.method() and input.feat_select() == 'zero':
    #             data, features_to_drop = zero_return()
    #         elif 'new' in input.method():
    #             data = new_feat()
    #         if 'select' in input.method() and input.feat_select() == 'rem':
    #             data = manual_remove()
    #     return data


    # def save_changes():
    #     data = encoded_data() if input.perform_encoding() else cleaned_data()
    #     if input.update_data():
    #         if input.method() == 'trans':
    #             data = target_fe_calc()
    #         elif input.method() == 'select' and input.feat_select() == 'pca':
    #             data, text = pca_return()
    #         elif input.method() == 'select' and input.feat_select() == 'zero':
    #             data, features_to_drop = zero_return()
    #         elif input.method() == 'new':
    #             data = new_feat()
    #         if input.method() == 'select' and input.feat_select() == 'rem':
    #             data = manual_remove()
    #     else:
    #         ui.update_action_button("update_data", disabled=True)
    #     return data


    # Feature engineering: Target FE Method
    @reactive.calc
    def target_fe_calc():
        data = encoded_data() if input.perform_encoding() else cleaned_data()
        target = input.target_feat()

        if input.target_trans() == 'log':
            col_name = str(target) + '_Lognorm'
            data[col_name] = np.log(data[target])
        elif data[target].isnull().values.any():
            print("⚠ Please Fill Missing Data First")
            return None
        elif not data[target].isnull().values.any():
            if input.target_trans() == 'bc':
                col_name = str(target) + '_Boxcox'
                min_val = data[target].min()
                if min_val <= 0:
                    data[target] = data[target] + abs(min_val) + 1
                transformed, lam = stats.boxcox(data[target])
                data[col_name] =transformed
            elif input.target_trans() == 'yj':
                col_name = str(target) + '_YeoJohnson'
                transformed, lam = stats.yeojohnson(data[target])
                data[col_name] = transformed

        return data

    # Plot of Target FE Method
    @output
    @render.plot
    def target_fe_plot():
        data = target_fe_calc()
        target = input.target_feat()
        if target_fe_calc() is None:
            plot = plt.hist(target)
            plt.title('Untransformed Feature')
            return plot
        elif input.target_trans() == 'log':
            col_name = target + '_Lognorm'
        elif input.target_trans()  == 'bc':
            col_name = target + '_Boxcox'
        elif input.target_trans()  == 'yj':
            col_name = target + '_YeoJohnson'
        else:
            plot = plt.hist(target)
            plt.title('Untransformed Feature')
            return plot

        fig, axes = plt.subplots(1, 2)
        data.hist(target, ax=axes[0])
        data.hist(col_name, ax=axes[1])

        return fig

    #PCA Feature Selection
    @reactive.calc
    def pca_return():
        data = encoded_data() if input.perform_encoding() else cleaned_data()
        s_method = input.feat_select()
        num_col = data.select_dtypes(include=['number']).columns.tolist()

        if s_method == 'pca':
            try:
                pca = PCA(n_components=input.num_components())
                # pca_result = pca.fit_transform(data[num_col])
                columns = ['pca_comp_%i' % i for i in range(4)]
                pca_result = pd.DataFrame(pca.fit_transform(data), columns=columns, index=data.index)

                text = []
                for i, ratio in enumerate(pca.explained_variance_ratio_):
                    text.append(f'PC{i + 1}: {ratio:.4f}')

                return pca_result, text
            except Exception:
                return None

    #Plot of PCA--it wasn't working so i left it out for now
    # @output
    # @render.plot
    # def pca_plot():
    #     if pca_return() is not None and input.num_components()>1:
    #         pca_result, text = pca_return()
    #
    #         plt.figure()
    #         plt.scatter(pca_result[:, 0], pca_result[:, 1], alpha=0.7, edgecolors='k')
    #         plt.xlabel('Principle 1')
    #         plt.ylabel('Principle 2')
    #         plt.title('Principle 1 vs Principle 2')
    #
    #         return plt

    @output
    @render.text
    def pca_label():
        if input.feat_select() == 'pca':
            if pca_return() is None:
                return "Please Preprocess Data before Feature Selection or alter # of Components"
            else:
                pca_result, text = pca_return()
                if len(text) > 0:
                    return "    Explained Variance Ratio By Component: " + str(text)

    #Filter zero variance features
    @reactive.calc
    def zero_return():
        data = encoded_data() if input.perform_encoding() else cleaned_data()
        s_method = input.feat_select()

        if s_method == 'zero':
            try:
                threshold = input.var()
                data, features_to_drop = zero_var(data,threshold)
                return data, features_to_drop
            except Exception:
                return "error"

    # gives features dropped for zero variance filtering
    @output
    @render.text
    def fd_label():
        if input.feat_select() == 'zero':
            if zero_return() =="error":
                return "    Please Preprocess Data before Feature Selection"

            data, features_to_drop = zero_return()
            if len(features_to_drop) == 0:
                return "    No Features Dropped"
            return "    Features Dropped:" + str(features_to_drop)

    @reactive.calc
    def manual_remove():
        data = encoded_data() if input.perform_encoding() else cleaned_data()
        if input.feat_select() == 'rem':
            feats_to_remove = input.rem_feat()
            for f in feats_to_remove:
                data = data.drop(columns=[f])
        return data
    
    @reactive.calc
    def new_feat():
        data = encoded_data() if input.perform_encoding() else cleaned_data()
        if input.method() == 'new':
            name = input.new_name()
            formula = str(input.new_feat())
            feat_used = input.feats()
            x = formula
            if formula == "" or name == "" or len(feat_used) == 0:
                return None
            for f in feat_used:
                x = x.replace(str(f),"data."+str(f))

            try:
                data[name] = pd.eval(x, target= data)
                return data
            except Exception:
                return None

    @output
    @render.text
    def new_feat_info():
        name = input.new_name()
        formula = str(input.new_feat())
        feat_used = input.feats()
        if input.method() == 'new':
            if new_feat() is None and (formula == "" or name == "" or len(feat_used) == 0):
                return "Please Fill Each Input"
            elif new_feat() is None:
                return "Error! Please correct expression"
            else:
                name = input.new_name()
                return "New column '" + name + "' created!"



    # EDA Part        
    # Load dataset after filtering
    @reactive.calc
    def filtered_data():
        df = get_data()
        if df is None:
            return None

        # Apply filters for the default dataset
        if input.data_source() == "Use Default Data":
            df = df[(df["Age"] >= input.filter_age()[0]) & (df["Age"] <= input.filter_age()[1])]
            df = df[(df["Hospital Visits"] >= input.filter_hospital_visits()[0]) & (df["Hospital Visits"] <= input.filter_hospital_visits()[1])]
            if input.filter_gender() != "All":
                df = df[df["Gender"] == input.filter_gender()]
            if input.filter_smoking() != "All":
                df = df[df["Smoking Status"] == input.filter_smoking()]
        
        # Apply dynamic filtering for uploaded dataset
        elif input.data_source() == "Upload dataset":
            for col in df.columns:
                if f"filter_{col}" in input:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        df = df[(df[col] >= input[f"filter_{col}"]()[0]) & (df[col] <= input[f"filter_{col}"]()[1])]
                    elif pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_categorical_dtype(df[col]):
                        if input[f"filter_{col}"]() != "All":
                            df = df[df[col] == input[f"filter_{col}"]()]
        
        return df

    # filters for categorical columns
    @output
    @render.ui
    def dynamic_filters_cate():
        df = get_data()
        if df is None:
            return None  # No data available yet

        # If using the default dataset, show predefined filters
        if input.data_source() == "Use Default Data":
            return ui.div(
                ui.input_select("filter_gender", "Filter by Gender", 
                                choices=["All"] + df["Gender"].dropna().unique().tolist(), multiple=False),
                ui.input_select("filter_smoking", "Filter by Smoking Status", 
                                choices=["All"] + df["Smoking Status"].dropna().unique().tolist(), multiple=False)
            )

        filter_ui = []        
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        for col in categorical_cols:
            unique_values = df[col].dropna().unique().tolist()
            if len(unique_values) > 0:
                filter_ui.append(
                    ui.input_select(f"filter_{col}", f"Filter by {col}", 
                                    choices=["All"] + unique_values, multiple=False)
                )
        return ui.div(*filter_ui)

    # filters for numerical columns
    @output
    @render.ui
    def dynamic_filters_num():
        df = get_data()
        if df is None:
            return None  # No data available yet

        # If using the default dataset, show predefined filters
        if input.data_source() == "Use Default Data":
            return ui.div(
                ui.input_slider("filter_age", "Filter by Age Range", 
                                min=int(df["Age"].min()), max=int(df["Age"].max()), 
                                value=(int(df["Age"].min()), int(df["Age"].max())), step=1),
                ui.input_slider("filter_hospital_visits", "Filter by Hospital Visits", 
                                min=int(df["Hospital Visits"].min()), max=int(df["Hospital Visits"].max()), 
                                value=(int(df["Hospital Visits"].min()), int(df["Hospital Visits"].max())), step=1),
            )

        # If using an uploaded dataset, dynamically generate filters
        filter_ui = []

        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        for col in numeric_cols:
            filter_ui.append(
                ui.input_slider(f"filter_{col}", f"Filter by {col}", 
                                min=float(df[col].min()), max=float(df[col].max()), 
                                value=(float(df[col].min()), float(df[col].max())), step=0.1)
            )
        return ui.div(*filter_ui)

    @reactive.Effect
    def update_choices():
        df = get_data()
        if df is not None:
            choices = df.columns.tolist()
            ui.update_select("x_var", choices=choices)
            ui.update_select("y_var", choices=choices)

    # statistics summary
    @output
    @render.table
    def summary_stats():
        df = filtered_data()
        if df is not None:
            summary = df.describe().transpose().round(2)
            summary.insert(0, 'Column', summary.index)
            return summary
    
    # correlation table
    @output
    @render.table
    def correlation_table():
        df = filtered_data()
        if df is not None:
            correlation = df.select_dtypes(include=["number"]).corr().round(2)
            correlation.insert(0, 'Column', correlation.index)
            return correlation

    # plots for features
    @output
    @render.image
    def dynamic_plot():
        df = filtered_data()
        if df is None or df.empty:
            return None
        plot_type = input.plot_type()
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        file_path = temp_file.name
        plt.figure(figsize=(10, 6))
        if plot_type == "Histogram":
            sns.histplot(df[input.x_var()], bins=30, kde=True)
            plt.title("Histogram")
            plt.xlabel(input.x_var())
            plt.ylabel("Count")
        elif plot_type == "Scatter Plot":
            sns.scatterplot(x=df[input.x_var()], y=df[input.y_var()], alpha=0.5)
            plt.title("Scatter Plot")
            plt.xlabel(input.x_var())
            plt.ylabel(input.y_var())
        elif plot_type == "Box Plot":
            sns.boxplot(x=df[input.x_var()])
            plt.title("Box Plot (Outlier Detection)")
            plt.xlabel(input.x_var())
        elif plot_type == "Correlation Heatmap":
            corr = df.select_dtypes(include=["number"]).corr()
            sns.heatmap(corr, annot=True, cmap="coolwarm")
            plt.title("Correlation Heatmap")
        plt.tight_layout()
        plt.savefig(file_path)
        return {"src": file_path, "width": "800px"}

# Run the Shiny App
app = App(app_ui, server)
