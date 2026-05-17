<div align="center">
    <img src="resources/images/logo.png" alt="DataPlotStudio Logo" width="200" height="200">
</div>

# Aletheia

Aletheia is a GUI implementation of the Matplotlib plotting and pandas data analytics capabilities. 
The program is built up of two primary interfaces:
* A data driven tab where you can view, edit, manipulate and alter data based primarily on the pandas library and embedded tools.
* A plotting interface where you can plot your data, as well as tweaking the plot in a graphical environment based on the Matplotlib's `pyplot` functionality.


## Features
* Import data from files: csv, Microsoft Excel, text files, JSON and GeoSpatial fileformats (shp, GeoPackage, GeoJSON)
* Import data from Google Sheets documents and from SQLite, PostgreSQL and SQL databases
* Edit and manipulate your data visually using tools from pandas and embedded custom tools
* View statistics about your data
* Plot the data with 30 different available plot types using Matplotlib and Seaborn
* Interactively design and customize your plots
* Add custom plotting code using the integrated Python editor to augment the your data visualization even further
* Export data and Python code to share or use in other tools

## Requirements
Following Python packages are required for the application to run:
```text
pandas==2.2.3
duckdb==1.1.3
pyarrow>=14.0.1
contextily>=1.7.0
numpy==2.2.3
requests==2.32.3
SQLAlchemy==2.0.36
geopandas==1.0.1
scikit-learn==1.6.1
scipy==1.14.1
matplotlib==3.9.2
seaborn==0.13.2
PyQt6==6.10.0
PyQt6-Qt6==6.10.1
PyQt6-WebEngine==6.10.0
PyQt6-WebEngine-Qt6==6.10.1
PyQt6_sip==13.10.2
```

## Building from source
To build the project from source:

1. Clone the repository:
```
git clone https://github.com/Johanbo22/Aletheia.git
```

2. Synchronize the virtual environment and install dependencies

```
uv sync
```

3. Navigate into the Aletheia root directory and run main
```
cd Aletheia
python ./main.py
```