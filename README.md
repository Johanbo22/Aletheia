<div align="center">
    <img src="resources/images/logo.png" alt="DataPlotStudio Logo" width="200" height="200">
</div>

# Aletheia

Aletheia is a GUI Exploratory Data Analysis (EDA) implementation of the Matplotlib plotting and pandas data analytics
capabilities.
The program is built up of two primary interfaces:
* A data driven tab where you can view, edit, manipulate and alter data based primarily on the pandas library and embedded tools.
* A plotting interface where you can plot your data, as well as tweaking the plot in a graphical environment based on the Matplotlib's `pyplot` functionality.


## Features
* Import data from files: csv, Microsoft Excel, text files, JSON and GeoSpatial fileformats (shp, GeoPackage, GeoJSON)
* Import data from Google Sheets documents and from SQLite, PostgreSQL and SQL databases
* Edit and manipulate your data visually using tools from pandas, embedded custom tools or using the command-line
  interface
* View statistics about your data and run statistical test on the data
* Plot the data with 30 different available plot types using Matplotlib and Seaborn
* Interactively design and customise your plots
* Add custom Python plotting code using the integrated Python editor to augment your data visualisation even further
* Export data and Python code to share or use in other tools

## Requirements
Aletheia requires **Python 3.12 or higher** to be installed. You can download Python from the [official website](https://www.python.org/downloads/) \
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

## Installation
To install Aletheia on your system, we have provided a few different approaches to suit your application installation approach.

### Build from source
To build the project into a compiled binary from source code:

1. Clone the repository:
```
git clone https://github.com/Johanbo22/Aletheia.git
cd Aletheia
```

2. Navigate into `scripts/` directory

```
cd scripts
```

For Linux and macOS run:
```shell
./installAletheia.sh
```

For Windows run:
```shell
installAletheia.bat
```
This will create a compiled binary of Aletheia in the `dist/` directory.\
Navigate to it:
```
cd ..
cd dist/
```

### Run from source
Alternatively if you do not wish to create a binary, the application can be run directly from the source code provided:
1. Clone the repository
```commandline
git clone https://github.com/Johanbo22/Aletheia.git
cd Aletheia
```
2. Synchronise the virtual environment and install dependencies
```commandline
uv sync
```
3. Run main.py
```commandline
python ./main.py
```

### Download compiled binaries
If you do not wish to compile the application yourself, a package containing the compiled binary can be found in the [latest release](https://github.com/Johanbo22/Aletheia/releases/latest). \
Here you can download the latest version of Aletheia matching your operating system.


