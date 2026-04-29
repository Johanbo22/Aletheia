# Changelog
All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog (https://keepachangelog.com/en/1.0.0/),
and this project adheres to Semantic Versioning.

## v0.1.4 [Prerelease]
### Changed
- Restructured `SubsetManager` cache keys to include underlying dataframe layout state, preventing incorrect cache returns when source data mutates.
- Refactored ProjectManager.load_project to streamline the parquet data parsing.
- `CodeExporter` now generates Pandas 2.0+ compliant code for missing value imputation (`.ffill()`/`.bfill()`) and aggregations.
- `CodeExporter` data operation filters utilizing 'contains' now default to `regex=False` to prevent crashes when searching for special characters.

### Fixed
- Fixed a bug where colorbars were not being properly deleted upon axis clearing
- Fixed an unhandled `KeyError` exception in `reapply_aggregation` when target aggregation columns are missing from the updated dataset.
- Fixed incorrect fallback logic in `SavedAggregation.from_dict` that could override valid empty `agg_config` definitions.
- Removed redundant validation checks inside `SubsetManager._apply_filters` processing logic.
- Corrected typo in the recover_autosave message.
- Fixed an issue where the script exporter generated invalid dictionary syntax for pandas grouped aggregations.
- Double-negative formatting artifacts in the generated regression equations.
- Unhandled `RuntimeError` exceptions when `scipy.optimize.curve_fit` fails to converge.

## v0.1.3 [Prerelease]
### Added
- User settings (font family, size, theme) now persist across application restarts.

### Fixed
- Bug where autosaving was triggered every 30 seconds instead of 5 minutes
- Prevented errors caused by attempting to zoom in or out via keyboard shortcuts while viewing the Data Explorer tab.
- Fixed a rendering bug where checking "Flip Axes" required a manual clear and regenerate the plot before taking effect.
- Fixed a bug in the Colormap Picker where toggling the "Reverse colormap" checkbox did not immediately update the visual preview
- Fixed an issue where turning off minor ticks would not update the plot immediately
- Fixed an issue where X-axis and Y-axis minor ticks could not be toggled independently.
- Fixed an issue where checking "Invert X-axis", "Invert Y-axis", or "X-axis on Top" did not trigger an update of the plot.
- Fixed older version of fillna() of pandas not updated correctly in 0.1.1
- Improved initial loadtime of start-up by offloading tempfile removal to threads.
- Fixed issues with redrawing GeoSpatial plots when changing parts of the plot.
- Fixed a freezing issue when assigning a Classification Scheme to a GeoSpatial plot.
- Fixed a bug where loading an autosave or project file containing GeoSpatial data would render geometry as raw bytes.

### Removed
- UI file-dialog calls in ProjectManager, moved to methods in UI

## v0.1.2 [Prerelease]
### Added
- Search bar inside the Data Explorer
- Worker to handle searching in a background thread
- BaseTab class with methods to set up a scrollable layout and a Hbox layout(button+icon)
- IconTypes for Search, Close, Up/DownArrow
- Added an method to build the DataPlotStudioIcon
- Added more animations to help_animations folder
- Added preview of colormaps with grayscaling test, discrete test and updated performance of filtering colormaps
- Added indeterminate states to ProgressBar
- Added credits for libraries used in AboutDialog
- Added a bug report link to AboutDialog
- Added an Autosave indicator that spawns every 5 minutes

### Changed
- Refactored DataOperationsPanel to separate classes for each tab.
- Creating a new dataset opens a more interactive dialog rather than the old input dialog.
- Redesigned the Create a new dataset dialog
- Updated ProgressBar visuals
- Highlighting rules for python syntax highlighting
- Updated CodeEditor completer instructions

### Fixed
- Fixed issue with correlation matricies calculation for Heatmaps
- Fixed issue with ColobarObjects on canvas retaining position upon deletion.
- Fixed and issue where clearing the redo stack would not free up allocated memory correctly.
- Fixed a bug where history items and operations were not being rendered.
- Fixed a bug where cancelling an operation where the ProgressBar is visible would not cancel the operation properly.
- Fixed CodeEditors completer being overlapped with the typed text
- Fixed a misalignment issue between the Data table and Data operations panel control widgets

### Removed
- SearchResultDialog will be removed as searching happens in the data table instead of in a dialog
- Methods in DataTab to search for items in the data table, linked to the old method of searching data.
- Methods relating to Plotly forgotten to be removed

## v0.1.1 [Prerelease]
### Added
- Caching logic (_compile_rules) to pre-process conditional formatting dictionary constraints into native Python execution tuples.
- Caching for column text alignments via _update_column_alignments() to calculate alignment enums strictly during state changes rather than per-draw request.
- Pre-instantiation of the background highlight QColor object to avoid C++ wrapper object allocation overhead in the render loop.
- Render booleans as checkboxes or as standard text.
- Toggle to choose how to represent booleans in the TableCustomizationDialog
- Backend integration of global color selection for gridlines
- Slight shadow effect to the information panel on the LandingPage
- Categorization of actions buttons on the LandingPage
- Logo to LandingPage
- Auto-clear messages in StatusBar after 8 seconds
- Copy to clipboard for the LogHistory
- Clear button to remvoe all Logs in the history
- Filter search for logs to find info/warnings or errors
- Right-click context menu for the StatusBar to access functions for LogHistory
- Submenus for Import and export in the File menu.
- Search bar for Group By column selection in AggregationDialog
- A context menu to select all available columns in the AggregationDialog
- A up-down arrow to change order of columns in the resulting df in the AggregationDialog.
- SearchResultsDialog now shows number of matches and has an inbuilt filtering system, incase of many results.
- **FilterAdvancedDialog**:
    - The Condition dropdown now dynamically updates based on the selected column type. Text options like "Contains Text" and "In List" are automatically hidden for Numerical and Date columns.
    - The Value spinbox for numerical columns now automatically bounds its acceptable range to the actual minimum and maximum values present in that specific dataset column (plus a 10% padding margin to allow further querying).
    - A confirmation prompt when closing the dialog (via Cancel or the `Esc` key) if there are unsaved filter configurations.
    - A targeted "Reset" button for each filter row, allowing users to flush a single filter's state independently.
- **ComputedColumnDialog**
    - Column filtering functionality to find specific columns
    - Function filtering to search the function library
    - A Clear button to reset the expression editor
    - A Ctrl+Return short to trigger the "Create Column" button
    - Tooltips for the functions library
    - A Status label to signify a valid expression as well as syntax error hinting
- Support for secondary y-axis for plots created with Plotly
- Customization controls for error bar customization. Including: linecolor, capsize, zorder and transparency.
- Script editor and code export supports Donut charts.
- Updated PlotExportDialog with image preview, aspect ratio, height and width settings. 
- WindowTitle updating to reflect unsaved changes and the current project loaded.
- Better variable parsing in the ScriptEditorDialog, variables in the current namespace will be loaded
- Added Data pipeline macro functionality to reuse data transformations as macros in the HistoryTab of the DataTab
- `MacroPreviewDialog` allows one to inspect the operations and parameters of a macro before executing it
- A rollback measure incase an operations in a macro fails the dataset is reset to its original state to avoid corrupting it.
- Dockwidget for the plot-tab to allow for side-by-side viewing of data and plot
- Nodegraph view for history of data operations instead of a static list. 
- A Python console to the DataTab to handle data operations using the console
- Added event listeners for scrolling, middle click panning, hovering for ToolTips on canvas
- Added event listener for right clicking on a subplot to make that subplot the current active subplot.
- Memory tracking in the status bar
- Added animations for SubsetData, CalculatingColumn/Datetime and SavingPlotasImages
- Added a small checkmark to Toggle switches when they are toggled.
- Added copying cell values from to table to table context menu.
- A dialog for reordering columns in the dataframe.
- Method in DataMutator to handle reordering of the columns as well as the UI buttons in the Columns Tab
- UI fields for assigning custom names to legend elements in Legend&Grid Tab
- UI fields for changing font-size of legend title and legend labels independently
- Updated CodeExporter to handle all legend elements from PlotConfig.
- Styling for the NavigationToolbar in at the top of the plot canvas.
- PlotConfigEditorDialog added a JSON syntax highlighting, error tracking of invalid json and a color insert button to easier get color codes in the JSON.
- Tool for dropping Empty columns where all row values are NaN
- Updated AboutDialog to a dialog instead of a Messagebox
- Added a Greeting to the plot tab before a plot is generated. This message also appears when clearing a plot.
- Filters to column list in ExportDialog
- Added support for choosing colors, fontweight, fontsize, rotation and coordinate placement of data point annotations
- Added background color changing for manually typed annotations
- Added a custom context-toolbar widget that allows for customization of annotations 
- Added port verification in DatabaseConnectionDialog
- Global settings search bar within `PlotSettingsPanel` to filter `QGroupBox` visibility across all tabs.
- Added dialogs for ShiftingData, CalculatingPercentageChange, RollingWindows. Methods for these are updated in DataMutator

### Changed
- Refactored `SavedAggregation` dataclass to use `agg_config` removing redundant fields
- Optimized `_get_foreground_data()` to utilize compiled functional operators (operator.lt, operator.gt, etc.) rather than performing inline dictionary lookups on every rendered cell.
- Bypassed legacy chunk-caching logic inside DataTableModel, routing direct O(1) Pandas .iat lookups.
- Optimized ToolTipRole delivery to immediately skip non-string scalars rather than forcibly casting everything to verify length.
- Optimized DisplayRole rendering by handling floats explicitly prior to executing slower Pandas type-checks (pd.isna).
- Refactored most of PlotSettingsTabs into more managable tabs. Cuts down on visual information spam.
- Changed HTML font metrics for links for changelog links
- Changed LandingPage to a 4:6 ratio
- Performance issues with larger datasets when using the Auto-Create Subset tool. Work has been offloaded to background thread.
- Clicking the terminal bar will open the LogHistoryPopup window
- Changed the general UI layout of FilterAdvancedDialog to not have more than 1 filter active on startup. More filters can be added by clicking "+ Add filter" button
- For FilterAdvancedDialog: The `QDateEdit` widget now defaults to the most recent date found within the currently selected datetime column, rather than statically defaulting to the current system date.
- Updated `CreateSubsetDialog` to be similar to FilterAdvancedDialog
- BinningDialogs validation process
- Refactored Plotly plot generation to use a similar strategy approach as regular plotting.
- Statistics Panel and Test results panel now renderings using a QWebEngineView. 
- Implemented a general support for error bars for scatter, line and bar plots.
- Changes for styling parameters, updated to more centralised css files and avoiding stylesheeting in python.
- Console in ScriptEditorDialog is now writeable 
- Updated plotting to run on a background thread to avoid freezing on large datasets.
- Refactored `clean_data` method to use a command-registry approach, making the method more maintainable
- Reworked the subplot creation to use a grid system and be more visual before committing to an subplot config. 
- Updated the VennDiagramWidget to have better colors and some animations
- Refactor of DataHandler into sub-classes of tasks: 
    - HistoryManager handles all data states and operation history
    - DataIOManager handles all I/O of files
    - DataMutator handles all the transformation algorithms for the data
    - DataHandler acts a bridge for app to access the same API
- Styling of Tabs
- Changes to the FigureCanvas Frame area to not overflow.
- Changed the visibility of plot customization controls for secondary plot types on a TwinAx
- Updated visual styling, ux of the OutlierDetectionDialog
- Updated IconRegistry with a 'Copy' icon
- General updates to interface of HelpDialog
- Optimized the annotation dragging system to help resolve lag
- Changed layout of DatabaseConnectionDialog
- Optimized the FPS of drawing ColorBlindness filters
- Improved the Advanced Filter dialog layout by dynamically hiding the value input field and its label when the selected condition does not require an input (e.g., "Is Null", "Is Not Null").
- CodeEditor: Modified keyPressEvent to force trigger the QCompleter popup when the . character is typed, enhancing object-oriented scripting support.
- Refactored `PlotExportDialog` dimension input fields to use a `QGridLayout`.
- Refactored _create_dps_package to write JSON and Parquet representations directly to the ZIP archive using in-memory streams, bypassing temporary directory creation and improving save speed for large dataframes.

### Fixed
- Fixed a bug in `AggregationManager.reapply_aggregation` where missing properties caused exceptions during data updates
- Prevented a potential crash in `get_aggregation_df` when retrieving results
- Fallbacks in `SavedAggregation.from_dict` to ensure backwards compatibility with older project files
- Fixed a bug where exporting code with a list-based filter created invalid syntax by recursing lists
- Fixed a crash in exported Python scripts when creating pie charts with empty datasets
- Fixed a crash in exported Python scripts when generating scatter plot analysis without assigning a y-column
- Fixed a crash in Google Sheets export when attempting to add a new worksheet
- Fixed a crash where SQLite exceptions across threads would intervene with workers
- Fixed an issue where exporting session logs resulted in heavily indented and difficult to read log file.
- Fixed a bug where index out of bounds or incorrect string slicing occurred when processing markdown headers with irregular whitespace
- Fixed a bug where LaTeX rendering settings failed to load
- Fixed a bug where legend edge colors failed to load/save properly 
- Fixed issue in Columns tab where ui was squeezed
- Fixed an issue where Data Operations panel remained visible while start screen was active.
- Fixed a bug where the app failed to prompt about unsaved script changes before closing python editor.
- Fixed high CPU usage during scrolling in DataTable
- Fixed an issue where correct text data type was rejected by the text manipulation tools for wrong datatype.
- Fixed an issue where a redundant log message would be written after every operation.
- Fixed a bug that caused tick labels to be overwritten with index numbers on plotting.
- Fixed an issue causing visual pop-in effect when widgets were initialized.
- Fixed a visual issue where frames around text in the "Whats New" information panel were drawn
- Fixed an issue on the LandingPage where the drop shadow of the "What's New" panel would visually clip at the edges of the application window.
- Fixed a bug where context label from Subsets and aggregations were not updated when a subset or aggregation was not in view.
- Fixed an issue where selecting "Is Null" or "Is Not Null" in FilterAdvancedDialog would not immediately update the query preview label.
- Fixed horizontal misalignment between the first filter row and subsequent rows in the FilterAdvancedDialog. The input fields now snap to a vertical grid regardless of whether the AND/OR logical operator is visible.
- Prevented the ability to submit a query in the FilterAdvancedDialog with an empty string value, which would previously bypass the text validation.
- Fixed a sizing issue of the splitter in the DataTab on small displays.
- Fixed an issue where Z-score outlier detection failed to calculate due to a mismatch between indexes from DataFrame
- Fixed a bug where duplicate column names could crash the distribution preview in the Outlier Detection Tool
- Fixed a bug where upon launch app did not start in maximised window
- Fixed an OOM error when storing undo states of large datasets
- Fixed an error where sorting state was not tracked by undo states.
- Fixed issues where a crash would lead to the temp directory not being deleted after use.
- Resolved a bug in the Python Console where an incomplete statement would cause a crash
- Fixed a bug where csv with malformed unicode would fail to load
- Fixed a typo in PlotEngine where canvas height was not accessed correctly
- Fixed an indexing error when trying to select values in canvas to find in DataTableModel
- Fixed rendering artifacts and blurriness on higher DPI displays
- Resolved an OOM crash when performing a search on a large dataset
- Enhanced rendering of the borders of the SubplotOverlay
- Fixed a bug where text from the SubplotOverlay did not disappear after animation was finished.
- Fixed lack of parameter in CodeExporter._generate_legend where parameters would reset upon using the ScriptEditor
- Fixed a bug where toggling independent minor/major gridlines would cause the settings to be unreadable
- Fixed a rendering issue with the `SubplotOverlay` where geometry was not shifted in both x and y axis.
- Fixed an issue where typing in QuickFilter caused the plot to immediately redraw and fail due to incomplete query.
- Fixed a style bug on MenuBar where the hover property was missing.
- Fixed a typo in PlotEngine that caused "OpenStreetMaps" to not be rendered
- Fixed bug where trying to export code would result in a crash
- Resolved an issue where changing the custom textbox duplicated the object on the canvas instead of just updating the existing one.

### Removed
- Removed self._data_buffer dictionary cache system and its associated clearance commands in sort, setData, and update_data for `DataTableModel`.
- Removed dynamic _is_numeric checking and inline bitwise enum combinations from DataTableModel.data().
- Top level export menu from MenuBar
- Plotly backend
- Widget_styles file
- Redundant custom style of QTabWidget

## v0.1.0 [Prerelease]
### Added
- Support for column duplication from the Columns tab in Data Tab
- Methods in `DataHandler` to handle data cleaning operations
- Data normalization tools in the Column panel. Support for Min-Max, Standard and Median normalization
- New `DataOperation` types: `Extract_DATE_COMPONENT` and `CALCULATE_DATE_DIFFERENCE`
- New datetime extraction and calculate duration methods and UI
- Flagging outliers to mark outliers in a new column. Method added to `DataHandler` and button implemented in `OutlierDetectionDialog`
- Better support for multiline indentation and unindentation for multiline selected text in `CodeEditor`
- Added better viewing of long cell content as tooltips in DataTable
- Added cell rendering for `datetime64` datatypes in the table
- Added a icons module to render icons at runtime instead of asset files. Uses `QIconEngine` to draw icons.
- Syntax highlighting for more Python keywords such as `async`, `await`, `match`, and `case`
- Support for scientific, binary and octal notation highlighting
- Added a method to DataPlotStudioButton to calculate the hover/pressed colors as well as the text color based on the base button color.
- Added cursor pointer on hover on buttons
- Added caching to used DataFrame. Allows for idle drawing of canvas instead of "Generating Plot" each time
- Added a notification to `SubplotOverlay` to notify when a click on generate plot is needed
- Added a pipeline to automatically update a plot with datasets smaller than 2000 rows
- Added text splitting. Split single columns into multiple by a delimiter
- Added regex replacement function. Use regex to replace string within a column.
- Added method to datahandler for vertically stacking datasets
- Added the AppendDialog UI component for selecting files to append
- Automatic parsing of datetime columns to avoid manual conversion.
- Text alignment and background color rules for table customization
- Added an apply and restore to defaults button for the TableCustomizationDialog
- **CodeEditor**: Clear console method and button to flush standard output, toggle_comments on multiple lines, read and write settings to remember UI states when closing window.
- Added a check for while loops to prevent them from freezing the app.
- **AggregationDialog**: Search and filter input for columns in AggregationDialog, Double click on item support, a clear all button for remove all selected aggregations at once, a timer for updating preview for large datasets. Drag-and-drop mode for group-by columns, tooltips for aggregation function. Icons for datatypes in column selection. A visual loading for updating the preview table.
- Checkboxes for right-inclusive intervals and dropping original column in binning-dialog. Bin_column method in DataHandler updated to reflect this. Enforce strict monotonic increase validation for custom bin edges to prevent pandas execution errors. Sequential labels for binning, a checkbox to add infinite bounds to upper and lower binning edges
- Search functionality inside the Data Subsets Tool to filter the existing subsets list.
- Right-click context menu in the `SubsetManagerDialog` list for quick access to actions.
- HTML formatting for subset filter logic to improve readability.
- Double-click action on subset items to instantly open the Data Viewer.
- Keyboard shortcuts (`Delete` and `Backspace`) to quickly remove selected subsets. And keyboard shortcut (`Return`) to view subset
- Alphabetical sorting for the subset list widget.
- "Duplicate" feature for Subsets to instantly clone filter configurations.
- Direct "Export Data" functionality, enabling saving a generated subset straight to a CSV file from the manager dialog.
- Alternating row colors in the subset list to enhance visual tracking of datasets.
- Using SVG draw paths for icons
### Changed
- Refactored the `clean_data` method to call separate methods for each action
- Updated `ColormapPickerDialog.generate_icon` to be a static method
- ColormapPickerDialog returns a cached value during dialog accept to prevent lag when indexing
- Checking if a column name exists in the dataset before renaming it. Before it only checked for the same name as current column being renamed.
- Updated the performance of the Datatable to not render the dataframe each time a visual element to the table is called
- The numeric check for cells in the table updates correctly when updating table or changing table elements.
- When editing `datetime64` data the EditRole uses ISO-formatted dates instead of generic `__str__` of `pd.Timestamp` objects
- The way the `DataTableModel` resets its layout. Using `being/endResetModel` to update model interface instead of recreating layout.
- Regex for keywords and builtins to reduce CPU usage during typing
- Disabled animation for plotting when not clicking generate plot button.
- Plotting is now modularised and uses a sequence strategy instead of a dict lookup
- Moved regression analysis into a new file `RegressionAnalyser` to free up space in PlotEngine
- Changed how the customizations of lines, bars and markers are handled when plotting updates. The old "Save Customizations to Plot" method has been removed and the customizatons are now reflected based on the GID of the bar/line/marker.
### Fixed
- Resolved a bug where `Trim trailing whitespace` triggered the lstrip operation instead of rstrip
- Fixed a `TypeError` that would cause a crash when exporting data to Google Sheets
- Fixed text typos in Data Tab
- A maths error in the IQR method `clip_outliers` where the upper limit was bound to Q1 instead of Q3. 
- Resolved a `TypeError` when parsing custom bin edge values
- Fixed an issue where a messagebox did not display the error correctly when binning data.
- Fixed issue where ColormapPickerDialog was instantiated every time a new colormap was chosen
- Fixed an issue with uninitialized colors for geospatial parameters when using the `CodeEditor` causing a crash.
- Fixed a crash that occurred when creating a new project upon application initialization.
- An update to the DataTableModel upon altering the table would instanciate a new model each time, which lead to memory leaks over time.
- Fixed a rendering artifact where menubar drop down menus displayed black corners
- Fixed incorrect color interpolation for the "On" state of the toggle switch widget. Previous color was a dull green instead of the default blue accent color. 
- Fixed an issue where escape sequences, `\"` ended string highlighting
- Fixed a bug where dot-notation for decorators were improperly formatted
- Keyboard focus for buttons when using tab to cycle through buttons was hidden
- Fixed issue where screen readers would read segmented strings with the typerwrite effect for buttons
- Fixed lag when adjusting sliders when plotting.
- Fixed issue where plot was instantly redrawn after clicking clear
- Fixed issue where SubplotOverlay information was being drawn every time an element was changed on the plot.
- Fixed a wrong calculation when calculating confidence intervals from a non linear regression
- Fixed a notation error when writing equation_str to canvas. Used e-notation causing small numbers to be represented as 1e-01 instead of just 1
- Fixed a sorting state bug where the sorting state was never updated when sorting data.
- Fixed a performance issues where data operations triggered canvas and plot rendering even when canvas was not in view.
- Fixed a bug where two categorical xaxis object could not be rendered.
- Fixed an issue where the MainWindow would not switch to the DataExplorer upon importing a new dataset.
- Fixed a crash when attempting to insert a tab without an active text selection in the python editor.
- Fixed a increment error in run_counter for ScriptEditor dialog causing wrong code history values
- Fixed a crash in `SubsetManagerDialog` occurring when saving a new subset
### Removed
- Redundant string conversion from RenameDialog
- All strategy_* methods from PlotEngine 
- Buttons for saving customizations to lines and bars in PlotTab
- IconEngine and manual drawing of icons

## v0.0.9 [Prerelease]
### Added
- A visual join diagram as a Venn Diagram in the Merge tool to preview the merge of datasets
- Data Cleaning Preview: The operations, "Remove Duplicates" and "Drop Missing Values", now highlight affected rows and requires a confirm to be removed.
- Select points in plot: A selection tool to select points in a plot will redirect to the data explorer and highlight the selected points.
- Added a colorblindess filter in the Appearance tab of the PlotTab, to allow for colorblindness accessibility
- Added a custom QGraphicsEffect SVG filter using numpy to calculate the rgba values for each colorblindess type.
- Statistical test support in `DataHandler` using `scipy.stats`
- An action to the table context menu to run statistical tests on two columns
- A separate Test results tab with the test results
- Support for a portable .dps zip format for project save files
- Internal SQLite database for each project
- Updated PlotConfigs to include all missing/newly added controls and properties.
- Regression type selection in the Scatter Plot settings panel
- Polynomial degree selection to configure polynomials
- Feature to export datasets to Google Sheets using Service Account
- Dialog for exporting datasets using Service Account credentialsJSON and target worksheets
- Menu action for "Export to Google Sheets"
### Changed
- Updated the plot engine to use matplotlib.colormaps registry
- Switched to defusedxml.ElemenTree for XML loading of project files.
- Google Sheets Import enforces data integrity by raising errors on bad lines instead of skipping them,
- Renaming columns and creating a new column validates for names that could cause issues or crashes.
- Refreshing google sheet documents now executes asynchronously
- Opening an existing project automatically renders the plot saved to the project file.
- Statistics generation is now handled by a separate class
- Changed to lazy loading of large tables in the table view.
- Disk I/O is handled by `tempfile.TemporaryDirectory()` to avoid corruption by partial save states
- Refactored scatter plot analysis to support generic *y_pred* arrays for R2, RMSE and standard errors
- Bound the canvas `SpanSelector` to right-click to avoid unintentional canvas selection when dragging annotations.
- Expanded `DataHandler` to use google-auth to export to a Service Account google sheet.
- Moved markdown_parsing from LandingPage.py to separate script in `core`
- Changed `log_action` in `StatusBar` with a flag to ensure details are only logged to file once per instance.
- Updated typing character in `StatusBar` to calculate chunk size based on string length. This ensures more consistent animation no matter length of log entry.
- Updated HTML text blocks to use transparent backgrounds that removes a blocky outline on text in Test Results Viewer and Statistics Viewer.
### Fixed
- Bug where twinx and twiny support was not properly implemented in the code editor. Would raise an error upon clicking "Run Script"
- Bug were the plotting engine would use cached data to redraw canvas, resulting in no change in redrawing even if data was changed.
- Memory leak where old Matplotlib figures were not being closed, leading to increased memory usage over time and a eventual OOM crash.
- Freezing when filter/aggregating large datasets
- Bug where flipping the axes (swtiching x and y axis) would cause a crash
- Issue where using a horizontal bar chart and adding a secondary y axis would cause the bar chart to become vertical.
- Resolved an issue where import errors were swallowed and reported as "empty" sheet when importing data from Google Sheets
- Fixed an issue where entering invalid numbers into an integer column would change the columns data type to object or corrupt the dataframe
- Fixed an issue where the SubplotOverlay would flicker upon resizing the canvas or window
- Fixed a code injection vulnerability where malicious strings could execute arbitrary code in exported scripts.
- Fixed an issue where clicking "New Project" in the menubar remained on the welcome page instead of creating an empty data table.
- Wrong arrow icons not being shown on scrollbars.
- Fixed an issue where integers cast to floating point were displayed using e-notation.
- Fixed issue where searching for values in a large dataset would cause a freezing due to indexing.
- Large spikes in latency when handling tables with >100k rows during fast scrolling
- A render bug when editing data and sorting the data table with large tables with > 100k rows
- Typos in `_load_appearance_config` mapped wrong keys for LaTeX rendering and y-label parameters
- Stuttering and text overwriting in terminal when receiving multiple log events
- File logging duplication issue with overlapping log entries.
- Method `update_data_stats` in `StatusBar` checks for the existance of df.shape before unpacking values.
- Wrong implementation of progress bar styling in the `FillMissingValuesDialog`
- Fixed aggressive caching for `generate_plot` that caused the plot not to update without prompting a data column change
- Resolved an issue where the GeoSpatial settings remained visible even when non-geospatial plot types were selected
### Removed
- Deprecated XML DOM tree proccessing for project save files and project configs

## v0.0.8 [Prerelease]
### Added:
- HoverFocusAnimationMixin class to handle border animations
- ThemeColors for a centralised widget color system
- New toggle switch widget to complement the checkbox system.
- Persistent history of the last 5 selected colormaps with a "Recently used" header.
- Landing Page: Added links to view bug fixes and version release notes from the welcome screen.
### Changed
- Widgets in dialogs, tabs etc.
### Removed
- Individual widget styling and animations.


## v0.0.7 [Prerelease]
### Added
- **Aggregate Data**
    - Aggregate multiple columns per grouping with a function
    - Date grouping to aggregate datetime data
    - Preview table for aggregated data in the dialog. View the result of data aggregation before committing to it.
- **Calculate Column**
    - Math, Trigonometry and String functions to be used in the Calculate Column dialog.
- **Detect Outliers**
    - A histogram to view distribution of data when checking for outliers using the Detect Outliers toolbox
    - Clipping outliers from data based on the threshold instead of just removing all rows.
- **Fill Missing**
    - Fill Missing Values now allows for grouping. Fill values in a column based on a grouping of another column
    - Fill Missing Values tool now has a progress bar that shows how many cells are NaN
- **Melt data**
    - Preview Table of the Melted/pivoted dataframe while using the MeltData Dialog. Allows for seeing the new data table before it is committed
- **Database Connections**
    - Profiles in Database Connection to avoid re-entering the same information all the time. Save and load profiles to get access to a prieviously connected database.
    - Use Raw URI strings to establish a connection to a database
- **Google Sheets Import**
    - History to google sheets import. The app will now remember the sheet_id last used to prevent re-entering the same details
- **Colormap picker**
    - Categorised Colormaps: Colormaps are now grouped by type
    - Reversing colormaps: Colormaps can be reversed using the "Reverse Colormap" checkbox
    - Improved filtering: The search function has now been improved.
- **Table Customisation**
    - Floating point precision to control the number of decimal places for floating-point numbers
    - Conditional formatting using a rule builder to highlight cells based on numerical rules
- **Filter and Subset Creation**
    - Data Type Aware inputs: Better widgets based on the data type instead of an arbitrary box
    - Nested conditions: Chain queries using different conditionals (eg ```A AND B OR C```)
    - Null Checks: Adds a "Is Null" and "Is Not Null" to check for NaN values in dataset.
- **Script Editor**
    - Insert code snippets: Common complemtary code snippets from a menu allows for adding snippets of code to enhance your plot
    - Variable explorer: A side panel with info and column names for the current active dataframe to assist in using the code editor.
    - Find and Replace: Search and replace words in the editor
    - Autocompletion: A basic auto-completion of python keywords and builtin functions when typing.
- **Pivot table**
    - Added pivot table creation from regular table format.
- **Merge datasets**
    - Added a dialog for merging / joining two datasets
- **Binning/Discretization**
    - Added support for binning numerical data into groups.
### Changed
- The expression field in Calculate Column Dialog now uses the CodeEditor styling for better syntax highlighting
- Stdout and Stderr from the python code editor will now send to an widget inside the editor instead of just the the system terminal.
### Fixed
- Wrong buttons used in Melt Dialog
- Text issue for a label in the Database Connection dialog
- Issue where RadioButton did not change styling when checked/unchecked.
- Popup bug when an item in a combobox was clicked the focus changed causing a crash.

## v0.0.6 [Prerelease]
### Added
- Added EPS, TIFF, PS, RAW bitmap and RGBA as options for file formats when saving figure. 
- Drag manually added annotations around the plot canvas.
### Changed
- DPI settings are now located in the dialog when exporting/saving the figure as an image.
### Fixed
- Issue where changing DPI, figure height or width would result in a canvas that was too large to view on screen.
- Issue where the overlay graphics for the current active subplot did not draw correctly and was offset by lower bbox.
- Bug where clearing a plot would result in an empty plot when recreating the same plot using the same parameters.
- Bug where checking "Auto Annotate Points" would result in unremoveable annotations as they would persist after unchecking.
- Bug where adding a manual annotation, moving it and then recreate the plot would duplicate the annotation
### Removed
- DPI settings from plotting interface.


## v0.0.5 [Prerelease]
### Added
- Coordinate Reference System Transformation for geospatial plots
- Adding basemap tiles from Esri, OpenStreetMap, CartoDB as background maps.
- Picker tools for canvas. Allows for clicking on elements in plot canvas and be moved to appropriate settings for that element
- TwinX support: Allows a secondary y axis to be plotted with its own scale.
- Export plot button: Added a button that gets relevant settings before exporting the plot. Is easier to find that the embedded tool from matplotlib that is hidden in the navigatortoolbar of the canvas.
- Quick Filter: Added a quick filter tool that can be used before plotting to write queries that filter the data based on an expression.
- Theme creator: Add default and custom themes to the plot. These are predefined JSON files where custom themes can be loaded.
- Edit theme: Edit custom themes or create copies of the default themes using the JSON editor. 
### Changed
- The plot selection is now a gridded format, instead of a list. Makes it easier to find and select the correct plot
- The visibility of certain UI in the "Customization" tab of the PlotStudio. Hides elements not useful for the current plot
- The support for the Plotly backend, Extended it to accomodate for more styling options directly from the matplotlib backend.
### Fixed
- Bug where freezing selected data for subplotting was ignored and overriden.
- Issues with slow table scrolling and slow plot rendering when using large datasets. Now using a cache system to store information about the plot. If the changes are styling based, the dataframe is not read again, instead cache data is used.
- Bug where coloraxis and color legends for geospatial plots was not parsed correctly and would either not show up or create duplicates.
- Bug where the data table on a plot was duplicated each time the placement parameter was changed. Caused multiple of the same table to be plotted.

## v0.0.4 [Prerelease]
### Added
- Text Manipulation to string data. Trim text data, and standardize casing etc
- Calculate column. Create new columns and use arithmetic, comparative and logical operations to calculate values in the new column.
- Sorting tool added to the operations panel on the right side of the data tab.
- Interpolation as options in the fill missing values tool. Choose between linear interpolation and time interpolation.
### Changed
- The way sorting the table is done. Allows a permanent sorting of data, useful before exporting data to a new file.
### Fixed
- Text error in Create and calculate column dialog
### Removed
-

## v0.0.3-alpha
### Added
- New search functionality to the data table. Allows for searching for values in the table and finds them.
- DuckDB databases as new possible database connections.
- A Test connection button so a database connection can be tested before a query is sent.
- Drag and drop files from explorer into the main view. This will load the file and import the data as normal.
- Welcome page with actions for opening existing project, creating new empty project, importing data from file, sheet, database
- Welcome page with what's new information
### Changed
- The way filtering data is handled. The reset does not happen automatically. Allows for filter into filter operations
### Fixed
- Bug where plotting any plots that cannot have legends. Legend now not parsed as keyword args to main engine.
- Bug where data table would reset position upon toggling edit mode ON/OFF.
### Removed
- Forced reset of data before using a new filter