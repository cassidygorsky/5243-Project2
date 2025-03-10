# 5243-Project2

## Choose dataset

## Data Cleaning and Preprocessing

## **Feature Engineering**
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
                

## Exploratory Data Analysis 
**Exploratory Data Analysis** 
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

## Contributions
* Yinhan Wang (yw4482)
* Iris June Chang (ijc2119) - Feature Engineering 
* Mingyan Xu (mx2294)
* Cassidy Gorsky (cg3520)

