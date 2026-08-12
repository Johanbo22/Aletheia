# Changelog
All notable changes to Aletheia will be documented in this file.

The format is based on Keep a Changelog (https://keepachangelog.com/en/1.0.0/),
and this project adheres to Semantic Versioning.

## v.0.5.0

### Added

- Customization of the secondary axes plot elements such as label, label font size and font weight.
- A ViewCube to interactively rotate a 3D canvas. This also updates the controls of Azimuth and Elevation angles.
- ArrowProps editing for Manual annotations. Includes box styling options, arrow pointers with targets.
- A Drawing Order widget to manually set Z order of plot elements
- A Keyboard and mouse shortcut reference tool for the PlotStudio interface.
- The QuickFilter in the Filters & Subsets tab in plot studio now highlights: numbers, strings, bools and functions
- Toggle Column Visibility to hide or show table columns via checkboxes in the Columns tab without modifying underlying
  data.

### Changed

- Improved naming and UX by naming the line on a secondary axes object with a "Secondary" to indicate the objects
  position in the canvas. This can be overwritten by changing the labels in the "Layout and Text" options under "Legend"
- Dropping multiple items into the application will now select the first valid data file instead of failing to load
- Allow for editing of data table upon double click

### Fixed

- Fixed an issue where trying to customize the thickness, style or color lines on the secondary axis object would cause
  the controls to revert back to default values.
- Resolved an issue where the 3D ViewCube tool would appear inside the Export Plot preview image and also in the
  finalized exported file.
- Resolved an issue in the visual annotation editor where dragging an annotation marker locked it vertically atop the
  mini-canvas
- Fixed a bug where using the spinboxes to move an annotation would in fact not move it.
- Resolved an issue where the proxy canvas for annotation editing failed to respond to the X/Y spinboxes or the "Enable
  Pointer Arrow" toggle while creating a new annotation.
- Fixed a bug where the progress bar would be at 100% and stay there while loading a task.
- Resolved an issue where the autocomplete suggestion box for the Quick Filter edit would overlap and obscure the text
  being typed.
- Optimized data table rendering
- Fixed issue where the loading screen would flash when loading small files.
- Resolved an issue where a temporary freeze would occur when working with large dataset during auto saves.
- Fixed a text formatting issue in the "Version History" dialog where multi-line bullet points wrapped into unnecessary
  extra lines.
- Fixed bug where the Plot studio tab was not visible when creating an empty dataset from the launch page.
- Fixed bug where pressing backspace in the Script editor dialog would delete two characters instead of 1.
- Resolved an issue where running custom Python code in the Script Editor would immediately revert the visual plot back
  to the UI configuration
- Fixed an issue in Light Mode where the "Insert Snippet" in the Script Editor Dialog menu text was unreadable
- Addressed a visual glitch were hovering or clicking on variables in the Script Editor Dialog Variable Explorer made
  the text disappear
- Fixed a bug where the "Search Columns" bar in the Script Editor Dialog did not filter properly.
- Fixed a bug where generating a Pie chart would render all slices in the same color with no way to change it.

## v.0.4.4 [Patch]

### Added

- Toggle the visibility of annotations using checkboxes in the list of annotations without the need to delete them.
- Reset to Defaults button for the Plot Settings Panel to reset all settings to their default value.
- More dark mode styling

### Changed

- Layout of the Annotations tab. Moved the Annotations list up to be below the annotations tools group.

### Fixed

- Fixed a text issue where "3D" was still written with "2D and Gridded" plot categories.
- Fixed an issue where searching for tools in the plot settings panel did not return any results despite the tool
  existing.

## v.0.4.3 [Patch]

### Added

- _set_spine_preset helper method to apply boolean state tuples to toggle switches for spine presets.
- Spine formatting and visibility now iterates over all connected subplot axes (e.g., secondary Y axes) to prevent
  background spines from persisting.
- Added tooltips to tools in the plotting tab
- Added the automatic annotation that gets added with a KDE overlay for histograms to the Annotations list so it can be
  edited or removed. A similar change is also applied to the RMSE, R^2 and regression equation annotation for scatter
  plots.
- A "Cancel / Deselect" button to the manual annotations tab.

### Changed

- Removed the disruptive QMessageBox confirmation dialog in inject_subset_to_dataframe.
- Moved 3D plots selection buttons into their own category instead of sitting in 2D and gridded
- Updated custom legend label parsing to use a semicolon (;) delimiter instead of a comma (,), which resolves the issue
  with locations or items containing commas (e.g., "London, United Kingdom").
- Changed the layout and states of Scatter Plot analysis. The rest of the settings now depend on the check for a
  regression line.
- Changed the layout of the Data Table feature for plotting

### Fixed

- Resolved a state-tracking bug where newly created aggregations did not update the `viewing_aggregation_name` flag. The
  Status Bar will now display the "Viewing Aggregation: {name}" label upon creation.
- Fixed an issue where the "Restore View" button failed to revert newly created aggregations by getting the
  `pre_agg_view_df` prior to applying the transformation.
- Fixed an incorrect Toast where duplicate aggregation names mapped to a "Data not found" UI error. Now appropriately
  gives an "Aggregation already exists" warning.
- Eliminated PyQt6 C++ memory leak caused by leftover `QAbstractTableModel` instances by triggering `.deleteLater()`
  when clearing table models in `view_saved_aggregations` and `restore_aggregation_view`.
- Corrected a typographical error in `apply_text_manipulation` ("whitepsace" -> "whitespace") that caused the "Trim
  trailing whitespace" action to fail.
- Fixed an `AttributeError` crash in `duplicate_column` when triggering the action with an empty dataset.
- Fixed a bug where refreshing Google Sheets failed to update the underlying dataset despite indicating success.
- Fixed an issue where exporting "Selected Rows Only" with no active selection would inadvertently export the entire
  dataset instead of alerting the user.
- Eliminated significant UI freezes and memory spikes when attempting to export large datasets.
- Fixed a `TypeError` crash caused by attempting string-to-numeric casting on empty or unformatted fields in
  `apply_filter`.
- UI blocking during refresh_active_subsets which synchronously re-applied large subsets.
- Consecutive Subset Injection context bug: Sequential subset application previously operated against the most recently
  injected data. It now correctly scopes the logic back to the master DataFrame.
- Fixed critical state-desync in `apply_sort` where sorting was incorrectly delegated to the View (
  `QTableView.sortByColumn`) instead of the Model (`DataHandler.sort_data`), causing sorting operations to bypass
  history and pipeline tracking.
- Added missing toast notification to `open_column_reorder_dialog` to ensure user feedback upon failure.
- Blocked signals during resets of independent_grid_check within on_grid_toggle to prevent double-draw on disabling
  grids.
- Fixed a UI lock-out bug where deleting a reference line or clearing the lines list disabled the "Add Reference Line"
  button.
- Fixed an issue where loading a saved plot configuration disabled the reference line creation UI.
- Resolved a UI soft-lock issue where the "Add Reference Span" button remained disabled after deleting a span or
  clearing the list.
- Removed ShowAlphaChannel from QColorDialog for ReferenceSpans to prevent conflicting transparency inputs between the
  color picker and the dedicated alpha spinbox.
- SeriesCustomizationManager.update_bar_selector mismatched list indexing causing incorrectly populated combo boxes.
- SeriesCustomizationManager.on_bar_selected ghosting UI states; UI resets values when a selected bar has default (None)
  properties.
- SeriesCustomizationManager.on_line_selected ghosting UI states; ensuring colors, markers, and alpha sliders correctly
  reflect missing or default states.
- Proper fallback conditions in SubplotManager.on_active_subplot_changed and SubplotManager.update_overlay to hide the
  subplot selection overlay when no plot is active or when the axis geometry is destroyed.
- Fixed the erroneous "Plot type changed to: Line" log on application startup.
- Prevented redundant method calls and double-logging of plot type changes when a saved plot configuration is loaded.
- Prevented the "Data change detected" log message at application startup by ensuring the DataFrame exists before
  marking the plot as changed.
- Resolved the sticky canvas overlay by hiding the "Update required" message (show_update_required(False)) when a plot
  finishes generating.
- Fixed bug where legend labels could be renamed.
- Fixed issue where certain configuration states would not update the plot upon change and required a full redraw.
- Fixed bug where using keyboard to change values in Spinboxes could causes issue with desired values. Disabled
  KeyboardTracking for spinboxes in Appearance and Customization tabs of Plotting tab.
- Fixed issue where toggling independent spine visibility did not fully remove the spine from the canvas.
- Introduced an _is_generating state lock across the plot generation lifecycle to prevent concurrent worker execution
  and Matplotlib race condition crashes.
- Fixed a bar chart rendering bug where stacked lines were rendered on non-stacked bar charts
- Fixed a rendering bug with bar charts that caused them not to render
- Fixed an issue where changing the minor tick direction and width on X and Y axis did not update the plot
- Fixed an issue where "Fancy Box" and "Show Shadow" for legends remained active when the legend frame was hidden
- Fixed issue where gridlines did not update the plot correctly and did not render at all in some cases
- Fixed a layout issue where the gridline group did not resize correctly when untoggling gridlines
- Fixed an issue where the bar width setting was enabled for histograms
- Fixed an issue where changing the value for the bar edge width did not render the plot automatically.
- Fixed an issue where overlaying a histogram with a normal distribution curve or a Kernel density estimate did not
  trigger the UI to allow for customizations of these lines.
- Fixed issue with error bars not updating when selecting a new color.
- Fixed an issue with text box not being drawn when enabling or when changing properties
- Fixed a bug where the label for Font Size for Data Table settings in the Annotation tab did not disappear when
  checking the "Auto Font size" check.
- Fixed a bug where reference line properties did not update correctly in the plot legend.
- Fixed an issue where reference lines would inherit the appearance of other plotted lines when the "Per-Line
  customization" toggle was active.
- Fixed the issue where the "Add Annotation" button remained active while editing an existing annotation
- Resolved an issue where toggling "Turn off Axis" during Geospatial plotting would cause a crash if a classification
  scheme or categorical data was mapped in the legend.

## v.0.4.2 [Patch]

### Added

- Context menu options "Select All" and "Clear Selection" within the data table
- Auto-truncation logic for the History Tab list items. Multi-column operations (like dropping >3 columns) now
  truncate (e.g., `Drop Columns: A, B, C and 4 more`) to prevent UI overflow.
- Silent cache cleanup method (`_remove_recent_project`) that triggers when a user attempts to open a moved or deleted
  file from the Welcome Page.
- Native clear buttons added to `QLineEdit` components in Appearance and Geospatial tabs for resets.

### Changed

- Removed hardcoded shortcuts for Windows to the QKeySequence.StandardKey enum
- Refactored `MainWindow.clear_all` to accept a `force_clear` param, to prevent unnecessary discard data prompts.
- Changed the icon for "Reset to Original" in the Data Operations Panel from `IconType.Redo` to `IconType.RefreshItem`
  to accurately reflect a "reset/restart" action.
- Clicking the Error/Warning issue counter badge in the Status Bar now automatically clears the counters (acknowledging
  the alert) prior to opening the log history modal.
- Refactored the string memory processing in `MainDataTableView.copy_selection` from a `+=` iterative loop into a
  hash-mapping architecture.
- Enabled `setAccelerated(True)` and Adaptive Decimal Steps for SpinBoxes with large ranges (e.g. ±1e9) in
  `annotations_settings_tab.py` to improve scrolling speed.
- Disabled `setKeyboardTracking` on high-range SpinBoxes to prevent stuttering/UI lockups during typing.
- Containerized conditional elements in `customization_settings_tab.py` (Donut Width) into wrapper `QWidget`s to ensure
  layout margins collapse when elements are hidden.

### Fixed

- Fixed an issue where the "Previous match" button in the data search bar failed to highlight the match
- Fixed a bug where closing the search bar did not emit the close_requested signal properly
- Fixed a visual bug causing the search bar to go off-screen if opened or closed in quick succession
- Resolved a memory leak by the SearchWorker instance.
- **CodeEditor**:
  - Fixed a crash caused by the QThread garbage collection while triggering the AST linting worker. Old threads are now
    properly disconnected and scheduled for deletion.
  - Fixed a bug that caused fully-typed autocomplete suggestions to duplicate text (for example, typing 'print' resulted
    in 'printprint').
  - Fixed a memory leak and potential rendering failure when folded blocks were deleted, leaving QTextCursor references
    in memory.
- Fixed a regex boundary bug that caused multiline strings (""" or ''') to continue downward if the closing quotes were
  placed at index 0 of a newline.
- Fixed bug where flipping axes did not work due to incorrect method call on the widget current_plot_type_name
- Fixed a bug where Subplot Configuration group would not change when Add subplot check was toggled.
- Fixed layout issues with the Variables group in the GeneralSettingsTab where depending on toggled MultiYColumnCheck
  would cause layout sizing glitches.
- Fixed animation layout bugs with the `AutoResizingStackedWidget`.
- Fixed resizing bugs with the `AutoSaveIndicator`
- Fixed bug where AutoSaveIndicator vanished during saving.
- Enhanced AutoSaveIndicator alignments for cross-platform and scaling values
- Addressed an issue where updating plot settings triggered repeated "Plot Generated" toasts.
- Fixed a typo "retrieved" in the `PlotGenerationManager._restore_frozen_data` method.
- Fixed a spelling error in `DataTableModel` which inadvertently enforced the wrong alignment on numerical cells
- Missing newline escape in the table tooltip header string.
- A syntax error with the LogLevel when exporting data to clipboard
- Fixed a bug where drag-dropping a file would trigger a QMessageBox dialog prompt.
- Fixed an incorrect logic bug in `StatusBar.set_progress` where .minimum() was used instead of .maximum()
- Clipped `StatusBar.update_memory_usage`'s percentage to a hard maximum of 100.0, resolving unhandled state behaviors
  internally observed by QProgressBar objects accepting overflowing percentages prior to garbage cleanup.
- Fixed clipboard formatting error in `_copy_latest_log` that incorrectly persisted `HTML.escape()` characters (e.g.,
  `&lt;`) via regex stripping. Strings are now properly `html.unescape()`'d before insertion to the system clipboard.
- Corrected the `_on_table_double_clicked` slot signature in `DataTab` to accept wildcard args (`*args`), solving a
  silent potential structural TypeError when PyQt automatically pushes `QModelIndex` signals onto 0-argument slots.
- Typographical error (`occurted` -> `occurred`) in Google Sheet export failure prompts.
- Fixed an architectural vulnerability in `DataTab.apply_table_settings` where an invalid grid hex color would `return`
  early, completely skipping and breaking all remaining user customizations.
- Fixed the "Recent Projects" dead-link persistence bug. Failing to load a missing project now successfully removes it
  from the `QSettings` configurations rather than permanently leaving it as a dead shortcut.
- Addressed a severe data-loss bug during the boot sequence recovery check. If a user escaped or closed the dialog
  window without responding, it fell to a default case that deleted their autosaved files.
- Prevented unhandled `AttributeError` instances from destroying the system thread if a user accidentally invoked
  standard plot zooming combinations (`Ctrl++` / `Ctrl+-`) before any `current_figure` was actually generated by the
  system backend.
- Upgraded the Drag and Drop event validation block. Passing checks now mandate verification that an incoming drop is
  structurally a `filepath.is_file()` to reject directories craftily named with a file suffix
- Restored the data model's rendering stability for DataFrames storing nested arrays or lists (common with
  ML/embeddings) by capturing and parsing the `pd.isna` logic without triggering pandas’ Truth Value ambiguity
  exceptions.

### Removed

- Old animation module for UI contextual animations related to operations.

## v.0.4.1 [Patch]
### Added
- The "Read more" button in the HelpExplorerDialog now displays the URL that the buttons sends to
- A "More details" button in the HelpDialog to send a request to view the page in HelpExplorerDialog
- Updated help database

### Changed
- Updated the layout in HelpExplorerDialog to better accommodate animation frame and text frames
- Updated the button layout in HelpDialog to separate the buttons more evenly.

### Fixed
- Fixed a layout issue in the HelpExplorerDialog where the "Read more" button was stretched too far
- Resolved an issue where viewing the Changelog pop repeatedly would result in a memory leak over time
- Fixed an unintended behavior where having more than 4 recent projects would permanently delete older projects instead
  of just hiding them
- Fixed settings parser to handle corrupted recent project files without causing a crash.
- Fixed memory leak in the Status Bar caused by `LogHistoryPopup` uncollected widget instances.
- Fixed a bug where indeterminate progress indicators auto-hid instantly.
- Fixed a UX glitch where the source data string permanently changed to 'Copied!'.
- Fixed overlapping styling behaviors when logging successive terminal messages rapidly.
- Resolved a rendering artifact that caused Qt bounds errors when grid layouts were made smaller
- Fixed a spelling mistake in grid tooltips for Subplot Config
- Fixed an issue where Toast notifications would behave erratically or cancel their animations
- Fixed a issue where toasts would auto-dismiss while cursor was hovering on toast
- Resolved a memory leak and visual artifact where auto-annotations duplicated on canvas redrawing
- Resolved significant GUI blocking on auto-annotation rendering
- Fixed a bug where opening the ColorDialog on the ContextualAnnotationToolbar would close the toolbar instantly
- Fixed issue where annotation toolbar could be left off-screen
- Added a `mouseReleaseEvent` to property handle the finish of dragging an annotation, fixing bug where dragging
  annotation would not release upon mouse button release.

## v.0.4.0 [Prerelease]
### Added
- Added a ReferenceSpanManager to configure axhspan and axvspans to the canvas
- UI updated to allow for configuring the spans
- CodeExporter and PlotConfigManager updated to handle new spans
- Sort by index for Sort Data in Transform tab.
- Dynamic visibility for the View menu items so they only appear when the Plot Studio is actively on-screen (docked or set as active tab).
- HelpAnimationPreviewPopup widget utilizing QPropertyAnimation and Qt.WindowType.ToolTip to provide faded window previews of the module's instructional animations.
- Global Signal event bus for signals emitting Toast Notifications to MainWindow
- Toast Notification system initial implementation.
- Added selection boundary checks in ConsoleDialog._custom_key_press_event for Backspace, Delete, and general text input to prevent users from accidentally deleting the console history or command prompt by highlighting overlapping text.
- Stacked bar chart support. Added a toggle in the General settings when selecting a bar plot type
- Feature to define the resulting DataType (`string`, `int`, `float`, `datetime`, `category`, `Auto-infer`) when creating a Computed Column.
- A sticky header label in ColumnsTab to persistently display the currently selected column(s) regardless of scroll position.
- Full implementation of ToastNotification system
- Added an action to the table context menu to highlight missing values
- Added a 'X' and a checkmark to the ToggleSwitch when OFF and ON.
- Added a "Restore View" button within the "Transform" tab under "Saved Aggregation" to revert to the unaggregated data
  view.
- Added an "Open Report Folder" button to the fatal crash dialog (`core/error_handler.py`) to allow users immediate
  access to generated logs.
- Added a Toast notification to explicitly inform users when multiple files are dragged and dropped that only the first
  file is processed.
- Implemented `QApplication.processEvents()` and wait cursors during synchronous Database Imports to prevent full UI
  freezes before the Progress Dialog has rendered (`ui/main_window.py`).
- Added Toast notifications to Plot Canvas Zoom actions (In/Out/Reset) to keep user visual focus on the canvas rather
  than checking the status bar (`ui/main_window.py`).
- Added a transparent Toast notification when synchronizing data back from the Python Console to explain the UI refresh
  state (`ui/main_window.py`).
- Added explicit default buttons to the "Export Python Script" and "Export Log" dialogs to fully support keyboard-only
  workflow (`ui/main_window.py`).
- Added an info toast when attempting to double-click on a cell to edit it.
- Added a confirmation dialog to `PlotTab.clear_plot()` to prevent work loss
- Global WaitCursor toggles for file import

### Changed
- UI layout for both ReferenceLines and ReferenceSpans
- Optimized _helper_is_datetime_column in plot_engine.py to use fast, vectorized pandas operations instead of a slow Python for loop over rows. This prevents UI stuttering when loading datasets with complex object columns.
- Enhanced the Autosave UX in main_window.py by ensuring the application logs a success message to the status bar, reassuring the user that their data is safe without throwing intrusive popups.
- Improved the "Export Code" dialog in main_window.py with setInformativeText and clearer button labels so the user understands exactly what is being exported (Data Pipeline vs. Data + Plotting Logic).
- Improved axis label formatting in plot_engine.py to beautifully join multiple Y-columns (e.g., "Revenue, Profit") instead of printing a raw Python list string (e.g., "['Revenue', 'Profit']").
- Appended .deleteLater() to ProgressDialog cleanup sequences in main_window.py to prevent Qt resource leaking after multiple file imports.
- Enforced a single-instance pattern for the Python Console via open_python_console(). Clicking the console button repeatedly will now pull the existing window to the foreground rather than spawning detached, overlapping instances that can desync the UI.
- Enhanced dragEnterEvent to utilize Qt.DropAction.CopyAction. This tells the operating system to show the native "copy" cursor during drag-and-drop, assuring the user that the file is being duplicated into the app, not moved or deleted from their disk.
- Updated a lot of styling to be standardized across widgets
- Extracted duplicate dynamic module loading operations out of HelpDialog and HelpAnimationPreviewPopup into a unified load_help_animation_widget utility method located in help_animation_engine.py.
- Updated CodeExporter and PlotConfigManager to handle subsets and subplots.
- Improved local file and project import workflows by persisting the last opened directory across sessions using `QSettings`. `QFileDialog` now opens in the user's previously visited path rather than the default project root.
- Using QApplication.processEvents() to help reduce load time when changing color theme.
- Disabled the "Edit JSON", "Apply theme", and "Delete theme" buttons in the Appearance Tab by default.
- Added _on_theme_selection_changed handler in ThemeManager to dynamically toggle theme-dependent buttons, preventing invalid theme file manipulation operations.
- Enhancements for the statistics tab and the test results tab with embedded JavaScript, visualizations, css etc.
- Updated p-value formatting in the statistical test result view to only use scientific notation for very small numbers (p < 0.0001). Standard, more readable decimal formatting is now applied for larger values.
- Optimized is_missing checks in DataTableModel.data() by replacing chained Python-level isinstance and isnan
  evaluations with pandas' native pd.isna(). This significantly reduces CPU overhead and eliminates UI stuttering during
  rapid table repainting and scrolling.
- Substituted iterative pandas Series aggregations in DataTableModel._update_column_alignments with a single vectorized
  self._data.isna().sum() operation, drastically reducing UI thread blockage when processing large DataFrames.
- Optimized `SearchWorker` global data search by preventing redundant string casting (`astype(str)`) on text columns,
  drastically improving search performance and reducing memory usage on large datasets.
- Optimized Google Sheets data parsing by switching the pandas.read_csv engine from "python" to "c" in
  DataIOManager.import_google_sheets, resolving a significant performance and memory bottleneck for large datasets.
- Improved the formatting and clarity of the Python Script Export dialog options (`ui/main_window.py`).
- Streamlined the "Clear Workspace" routine to eliminate redundant user prompting (asking to clear, then asking to
  save).
- Refined the `Ctrl+F` Find shortcut's `Qt.ShortcutContext` to `WidgetWithChildrenShortcut`, preventing the Data Search
  Bar from intercepting keyboard events while the user is actively working in the Plot Studio tab (`ui/data_tab.py`).
- Refactored the autosave recovery dialog to have more explicit buttons
- Update the Critical Error dialog to remind that system recovering is enabled.

### Fixed
- Python syntax highlighting overwriting string literals if they contained a # (hash) character.
- MainWindow._update_recent_projects no longer empties the recent files list when a project is saved/opened
- Replaced typo: list[recent_files] with list(recent_files) to prevent runtime TypeError during tuple casting.
- Initialized self.autosave_enabled in MainWindow.__init__ to prevent AttributeError crashes in the autosave background timer.
- Fixed a bug in ScriptManager where custom scripts would incorrectly force gridlines to toggle on during GUI synchronization by checking the visibility state of the grid Line2D objects instead of their sheer existence.
- Fixed a critical typo (self._history_sort_state) in data_handler.py that would cause an AttributeError or corrupt the sorting state when a data macro pipeline fails and triggers a rollback.
- Fixed a visual bug in plot_engine.py where the default plot title would render as an integer (e.g., "0" or "1") instead of the actual plot type name (e.g., "Line", "Scatter") when axes were flipped or labels were auto-generated.
- Fixed a desynchronization bug in main_window.py where triggering Undo or Redo did not update the Plot Studio's dropdown menus or the Status Bar's row/column counts.
- Fixed a bug where the ContextualAnnotationToolbar could not be loaded properly due to a typo.
- Removed obtrusive warning message boxes from zoom_in, zoom_out, and zoom_reset functions.
- Fixed a visual bug in the status bar where the terminal QLineEdit would fail to revert its border and text color to the default idle styling after displaying warning or error messages. The _reset_to_idle_state method now correctly unpolishes and repolishes the widget with the "IDLE" log level property.
- Fixed a bug where untoggling the "Share X axis" when configuring subplots would not re apply the x axis on the canvas.
- Resolved a visual glitch in GridSpecDesignerWidget where "Empty Space" labels remained visible behind merged plot cells.
- Fixed issues where the ContextualAnnotationToolbar would be triggered when trying to move an annotation.
- Fixed a missing background color for extract_date, duplicate_column, data_normalization, and iqr help_animation
- - Fixed a bug where opening a file or reverting to the root state would inadvertently spawn infinite `Sort[Index] (Asc)` entries in the `PipelineGraphView` due to implicit QTableView header syncing. A monotonicity guard now checks the `DataFrame` state directly to prevent generating duplicate or initial sort-state history nodes.
- Prevented the x-axis labels on the BinningPreviewWidget distribution chart from being cut off at the bottom by explicitly reserving bottom margin space via subplots_adjust().
- Resolved a performance bottleneck in the AggregationDialog where iteratively appending rows inside a loop triggered sequential, redundant UI redraws and signals, significantly slowing down view population for large DataFrames.
- Resolved a TypeError in ConsoleDialog during Ctrl+Minus key events caused by an invalid tuple check syntax in _custom_key_press_event.
- Prevented the main application from crashing/closing when quit(), exit(), or sys.exit() are entered in the ConsoleDialog. These commands will now properly close only the dialog itself.
- Fixed issues where the graph view for operations did not export properly and could not be reapplied to a dataset. UUIDs were not assigned to operations causing them to loose their parent. 
- Fixed up animations lag issues for the PipelineGraphView.
- Box plots now properly map the x_col selection to the categorical X-axis, enabling grouped distributions (e.g., viewing 'Sales' distribution grouped by 'Region').
- Fixed visual bug when editing Table cells where underlying data text was visible when editing
- Fixed visual bug when editing Table cells where cell layout border did not match cell before editing.
- Fixed an IndexError in the column reordering animation caused by a missing end-position coordinate for the middle column.
- Fixed an AttributeError on the available columns list in AggregationDialog where the QListWidgetItem was not updated
  to a QModelIndex.
- Fixed a bug where jumping backwards to previous states in the history tree would not reset the visual order of
  reordered columns
- Removed the persistent `status_bar.log` entry for background autosaves (`ui/main_window.py`) to reduce log noise and
  preserve the visibility of meaningful user-driven actions in the console history.

## v 0.3.1 [Patch]
### Added
- A GlobalExceptionHandler to log crash and unhandled exceptions to a file.
- Created a `General` configuration tab in `SettingsDialog` targeting application-level settings like Autosave triggers and intervals.
 
### Changed
- Rewrote how SVG paths and data is stored. Stored in icon_data.json and is loaded once per runtime sequence.
- Moved the CodeEditor widget into the correct directory /widgets instead of a /dialogs
- Improved animations for AutosaveIndicator and StatusBar labels.
- Explicitly cast rule values to float in DataTableModel._compile_rules to prevent TypeError exceptions during conditional rendering comparisons.
- Converted the hard block on Python code export for file-less datasets (Database imports, synthethic sets) into a user-bypassable warning in MainWindow.export_code().
- Appended `DataPlotStudioApp.settings` payload to query `QSettings` for `enable_autosave`, `autosave_interval`,
### Fixed
- Resolved a UI bug in the DatabaseConnectionDialog where the text "Testing..." erroneously remained next to the "Connection successful" message.
- Fixed a missing animation for the settings search inside the plot studio tab
- Fixed a couple of issues in ConsoleDialog: Bug with pasting text would only evaluate last line, Bug with potential overtyping of command prompt ">>>" would crash the Console and throw a SystemError.
- Fixed an `UnboundLocalError` in `DataTableModel.data()` triggered when toggling edit mode. The logic now correctly evaluates `is_insert_row OR is_insert_col` (instead of `AND`) to prevent out-of-bounds DataFrame indexing on the appended insertion placeholders.
- Fixed an issue in PlotTab._generate_main_plot() where canceling a plot generation progress dialog erroneously triggered a critical crash popup. Cancellations are now caught gracefully via InterruptedError.
- Fixed a critical visualization bug where large, downsampled Line and Area plots rendered as randomized spaghetti lines; PlotDataPrepWorker now appends .sort_index() to preserve sequential data order.
- Fixed a silent state desynchronization bug in PlotTab.update_column_combo() where missing columns would auto-resolve to default fallback columns without notifying the visualization engine.
- Fixed a visual artifacting issue in DataTableModel where brush/lasso row highlights were inaccurately preserved across table sorting operations. Highlight states are now cleared on sort.
- Fixed a critical logic block in DataTableModel.setData() that rendered table checkboxes permanently immutable due to an overly aggressive initial guard clause checking for EditRole.
- Fixed an oversight in PlotTab.get_active_dataframe() where incorrect object reflection (hasattr(self) instead of hasattr(self.view)) caused the application to completely ignore user-selected data subsets during plot generation.
- Fixed a bug in the PlotSettingsPanel search filter where hasattr(self, "text") caused the search index to overlook interactive UI elements like Checkboxes and RadioButtons. It now correctly targets hasattr(child, "text").
- Fixed a vulnerability in PlotTab.activate_subset() where requesting a non-existent subset would place the UI into an invalid state, disrupting future operations. The method now safely exits if the target is invalid.
- Fixed a highly destructive data-loss bug in PlotDataPrepWorker._is_datetime_column() where plain numeric strings were aggressively evaluated as timestamps and all subsequent text data was forcibly converted to NaT. The validation heuristic is now stricter and checks multiple rows.
- Fixed an AttributeError application crash in MainWindow._update_recent_projects() caused by PyQt6 silently converting QSettings list data into immutable Python tuples.
- Fixed a UI threading quirk in MainWindow.export_google_sheets() where modal error dialogs spawned beneath or concurrently with the blocking progress dialog. Progress windows are now gracefully terminated before errors manifest.
- Fixed an issue in MainWindow.export_data_dialog() where exporting DataFrame contents directly to the clipboard caused silent failures in the logging system due to a missing file path. Logs will now accurately report "Export complete to Clipboard".
- Fixed an issue where project files could not be opened via drag-and-drop. The drag-and-drop handler now explicitly recognizes the application's native project extension and correctly routes the file to the project loading mechanism rather than the data import pipeline.
- Resolved a bug where the QTableView model would not display after clicking "New Project" and loading a new file. The model is now cleanly destroyed on project reset and strictly re-attached during data view updates.

## v 0.3.0 [Prerelease]
### Added
- Support for selecting multiple aggregation functions for a single column simultaneously via MultiIndex unpacking.
- Added support for quantile calculation during aggregations.
- threading.Event as a cancellation token pattern within AggregationDialog to gracefully abort stale async PreviewWorker executions.
- Worker for Reading files in thread
- Renameable output columns in AggregationDialog
- Support of adding lines in plots using Axhline, Axvline, Axline
- Minor animation for when the SearchBar is called
- Dynamic form validation to disable the "Apply Fill" button when the "Static Value" method is selected but the input field is empty for the FillMissingDialog
- FillMissingDialog: validate_inputs acts as a soft warning. The "Apply Fill" button remains enabled, allowing users to intentionally override and change column data types.
- Animations for the LogHistoryPopup window
- A Diff system for history states.
- A buffer management system to handle dataframes in memory
- Module documentation
- Added a confirmation dialog for DataTabController.refresh_google_sheets() to prevent accidental data loss.
### Changed
- Refactored `AggregationDialog` UI to render individual Date Grouping frequency dropdowns dynamically for each datetime column selected, replacing the single global dropdown configuration.
- Applied a minimum height constraints to the agg_table widget within AggregationDialog.py to prevent the UI component from shrinking excessively when the user removes all items and the list is empty.
- Updated the clear_all_aggregations method in AggregationDialog.py to require user confirmation via a QMessageBox before emptying the aggregation configurations
- Button alignments for host OS in AppendDialog
- Elided long file formats in the edit bar in AppendDialog
- The Browse file method in AppendDialog is split up to make use of FileReaderWorker.
- Updated database for tutorials 
- Refactored CreateSubsetDialog to use FilterAdvancedDialog UI and reduce technical debt
- Updated the animation when search for columns in the ColumnReorderDialog to be not instant
- Populating the target column in FillMissingDialog now filters out columns that do not contain any missing values.
- FillMissingDialog: The "All Columns" option is now removed, and the entire form is disabled if the dataset contains no missing values whatsoever.
- The main navigation tabs ("Data Explorer" and "Plot Studio") are now hidden when the application is on the `LandingPage` (i.e., when no project or data is loaded).
- PipelineGraphViewer can now handle branches of states, allowing for multiple states to be stored.
- Huge refactor of all ControlElements, All DataPlotStudio* widgets and controls are deprecated.
### Fixed
- Fixed a scaling bug on the logo in the About section
- Fixed a bug in AggregationDialog.remove_column_from_agg where a 'o' was inserted instead of a 0 resulting in a crash when removing items.
- Fixed a bug in DataMutator.read_file() where the return statement was not given. 
- Fixed an issue with older pandas API for date mapping frequencies being used for aggregation of datetime data.
- Fixed updates to the GUI from ScriptEditorDialog
- Fixed a sizing issue wth the BinningPreviewWidget on smaller screens.
- Fixed a bug in the regex validation of custom bin edge values.
- Fixed an overlapping visual bug between the function list and the output name edt box in AggregationDialog.
- Fixed some float/int conversion errors when reading and writing to plotting configurations while using the ScriptEditor
- Fixed an issue where the data source filepath was lost when loading a `.ath` project or recovering an autosave.
- Fixed a buggy scrolling speed in the ColumnReorderDialog

## Removed
- HistoryManager will be removed, as it no longer serves a function
- ControlElements file with all DataPlotStudio* control widgets removed
- Control elements.css file. Control elements now have their own css file instead
- AnimatedButton has been removed as DataPlotStudioButton is no longer served as a subclass of QPushButton. Relying on QPushButtons instead.
- Removed the typewriter effect for buttons.

## v 0.2.1 [Patch]
### Changed
- Updated PlotTab._update_customization_visibility to automatically disable and uncheck tight_layout_check when a 3D plot type is selected, preventing the UserWarning associated with margin calculation limits in matplotlib's 3D axes.

### Fixed
- AttributeError during regression plotting when using DataFrames backed by PyArrow or nullable extension types. RegressionAnalyser.clean_data now explicitly forces data to standard float np.ndarray using .to_numpy(dtype=float, na_value=np.nan), preventing missing attribute errors when calculating bounds.
- Fixed a TypeError in pie_strategy.py where PlotEngine._set_labels() received multiple values for xlabel and ylabel by popping them from general_kwargs prior to method execution.
- Fixed a TypeError (ufunc 'isfinite' not supported) in gridded plots (e.g., Contour, Pcolormesh) by coercing the Z column to numeric and casting the final pivot matrix to float dtype in _prepare_gridded_data().
- Resolved TypeError: got multiple values for keyword argument in GeoSpatialPlotStrategy by safely removing explicitly passed parameters from kwargs before unpacking them into gdf.plot().
- Fixed a styling error on missing percentages in the Statistics Panel

## v 0.2.0 [Prerelease]
### Added
- Initial 3D plotting support: Supports Scatter, Line and Surface
- Z-Axis selection, axis label, axis parameters support
- Camera settings for 3D plots 
- Code Export of 3D plots
- PlotConfigManager updated to recognize is_3d_axes flag, z-axis, and camera settings
- SyntaxHighlightSettingsDialog to permit modification of Python keyword and tokens highlighting
- Color theme presets (Light Theme, Solarized Dark, and Dracula) to SyntaxHighlightSettingsDialog.
- Added a `Settings` button to the `LandingPage` sidebar for direct access to application settings.
- Implemented `Recent Projects` section on the `LandingPage` to display up to 4 most recently accessed projects.
- Added automatic file path validation to remove deleted/moved projects from QSettings history.
- Project saving and opening actions automatically updates the global recent files registry used by the Landing Page.
- Bracket pair highlighting in `CodeEditor`.
- `Ctrl+G` shortcut in `CodeEditor` to jump directly to a specified line number.
- `Alt+Z` shortcut in `CodeEditor` to toggle word wrapping on and off.
- `Alt+W` shortcut in `CodeEditor` to toggle whitespace rendering
- Deleting a line using keyboard shortcut `Ctrl+Shift+K`
- Move lines or blocks of lines up or down using `Alt+Down/up` arrow keys
- Native Live Linting in the `CodeEditor`. Syntax errors are now parsed continuously in a background thread, highlighting broken lines with a red underline.
- Syntax Error tooltips. Hovering the mouse over a squiggly red line will now display a popup explaining the Python `SyntaxError`.
- Native code folding in `CodeEditor`. Blocks of code can now be collapsed or expanded by clicking the `[-]` / `[+]` indicators in the line number margin.
- Interactive `+` cells at the trailing row and column of the Data Table when `editable` is toggled on.
- `DataTableModel.insert_empty_row()` and `DataTableModel.insert_empty_column()` methods to dynamically expand the dataset.
- A distribution bar chart widget for the BinningDialog to visualize binnings result on the dataset before validation.
- Improvements to caching and rendering of the PipelineGraphViewer widget. 
- Zooming bounds for the PipelineGraphViewer and keyboard shortcuts for faster navigation
- A thread to fetch schema information on a database.
- Bold and italic font styles for annotations using Toolbar
- Annotations toolbar color choice now has Alpha channel.
- CanvasInteractionManager to encapsulate all mouse events for canvas interactions
- PlotFormattingManager to handle all Plot formatting sequences
- Scientitic notation, thousands seperator and gridline style toggles for Table customization.
- UI updates and styling for SplitColumnDialog
- More Help animations
- Splash_Screen at startup
- appInit to handle startup functions

### Changed
- Modifed PythonHighlighter to dynamically rebuild regex rules natively when its theme is altered.
- `CodeEditor` now defaults to horizontal scrolling (no word wrap) to preserve code formatting visually.
- `DataTableModel.rowCount()` and `columnCount()` dynamically append 1 extra index when the table is editable.
- `DataTableModel.data()`, `flags()`, and `headerData()` augmented to safely intercept requests targeting the artificial insertion cells to prevent `IndexError` on the underlying DataFrame.
- `set_editable()` now properly broadcasts `layoutAboutToBeChanged` to safely expand/collapse the insertion UI.
- Validation of renaming columns. UI reflecting name before submitting.
- Centralised styling into component styling files
- CreateDatasetDialog has received numerous updates to UX
- Refactored rendering of the GridSpecDesigner widget
- Optimized rendering and animation flow of PipelineGraphViewer
- Optimized performance of loading data from Google Sheets
- Improved stability of Database Connections and loading data from large databases.
- Overhauled styling and animations for control-elements
- General UX updates for FilterAdvancedDialog
- Layout for Filter-tab in the Data-operations panel.
- Moved Theme handling from PlotTab into ThemeManager
- Moved script editor handling from PlotTab into ScriptManager
- Moved Subplot handling from PlotTab to SubplotManager
- Moved Annotation handling and annotation+mouse interactions form PlotTab to AnnotationManager
- Refactored PlotTab to delegate canvas interaction handling to CanvasInteractionManager.
- Upgraded CodeEditor.duplicateLine (Ctrl+D) to natively handle copying multi-line user selections without explicit bounding box edge conflicts.
- Refactored DataTab with DataViewToolbar and DataSearchBar objects to lessen class size.
- Major refactor of PlotEngine and the plot strategies. All plot definitions are moved from engine and gathered using PlotEngine._execute_strategy.
- Elevated HelpExplorerDialog to a ApplicationWindow when requested. 

### Fixed
- Fixed bug where unchecking "Show Data Table" would not remove the table without a manual redraw of canvas.
- Fixed a bug in AdvancedFilterDialog where removing an active filter condition failed to refresh the query preview at the bottom of the dialog.
- Fixed bug in CreateDatasetDialog._apply_prefix_to_table where _validate_schema was missing execution parentheses, preventing duplicate validation upon bulk rename.
- Fixed scroll stuttering issue on the PipelineGraphViewer
- Function insertion bug in ComputedColumnDialog
- Fixed a styling bug with the Window Menu not applying the same style as the other menus
- Fixed a stretching issue causing a large gap in the subset tab.
- Fixed an issue where unchecking "Add subplots" did not automatically clear the canvas
- Resolved a bug where subset_column_combo and sort_column_combo failed to populate with DataFrame columns upon data load
- Fixed a bug where clicking the Refresh Button while a subset was active would cause the other subsets to loose data.
- Fixed an issue where hovering over a point in the canvas caused an wrong index and wrong value to be returned
- Fixed an alignment bug with the buttons in the cleaning tab.
- Resolved visual bug in the Axis Label Options where Z-axis controls were visible on top of other tabs.
- Resolved a TypeError in DataPlotStudioSlider.mousePressEvent by correctly unpacking the x or y integer coordinate from the QMouseEvent's QPoint prior to calculating the click-to-jump value.
- Resolved a critical race condition where opening a second application instance would erroneously purge the primary instance's temporary data before the singleton lock forced a shutdown.
- Fixed bug with Combobox corners not matching other control widgets.
- An unparented QMessageBox in ui/main_window.py

### Removed
- _on_draw_event, _setup_brush_and_link, _handle_brush_selection, on_pick, on_scroll, on_mouse_press, on_mouse_move, and on_mouse_release from PlotTab.
- Canvas mpl_connect hooks from PlotTab._connect_main_controls
- Deleted 17 styling and attribute configuration methods from PlotTab. They now reside in PlotFormattingManager

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
