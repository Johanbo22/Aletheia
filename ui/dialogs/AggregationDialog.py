from enum import Enum
from PyQt6.QtGui import QFont, QKeySequence, QShortcut, QIcon
from PyQt6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QTableWidget, QHeaderView, QAbstractItemView, QTableWidgetItem, QMenu, QSplitter, QWidget, QListWidgetItem
from PyQt6.QtCore import Qt, QThreadPool, QTimer, QPoint
from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton
import pandas as pd
from ui.widgets.ControlElements import DataPlotStudioComboBox, DataPlotStudioGroupBox, DataPlotStudioLineEdit, DataPlotStudioListWidget
from ui.workers import AggregationWorker

DIALOG_WIDTH: int = 1200
DIALOG_HEIGHT: int = 700
PREVIEW_TABLE_MAX_HEIGHT: int = 200
DEFAULT_PREVIEW_LIMIT: int = 5
DEBOUNCE_DELAY_MS: int = 300

class AggregationFunctions(str, Enum):
    """Enumeration of supported pandas aggregation functions."""
    MEAN = "mean"
    SUM = "sum"
    MEDIAN = "median"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    STD = "std"
    VAR = "var"
    FIRST = "first"
    LAST = "last"
    NUNIQUE = "nunique"

AGGREGATION_TOOLTIPS: dict[AggregationFunctions, str] = {
    AggregationFunctions.MEAN: "Average of all values",
    AggregationFunctions.SUM: "Total sum of all values",
    AggregationFunctions.MEDIAN: "Middle value separating the higher half from the lower half",
    AggregationFunctions.MIN: "Smallest value",
    AggregationFunctions.MAX: "Largest value",
    AggregationFunctions.COUNT: "Number of non-null values",
    AggregationFunctions.STD: "Standard deviation (measure of data variation)",
    AggregationFunctions.VAR: "Variance (squared standard deviation)",
    AggregationFunctions.FIRST: "First value encountered",
    AggregationFunctions.LAST: "Last value encountered",
    AggregationFunctions.NUNIQUE: "Number of distinct, unique values",
}

class AggregationDialog(QDialog):
    """Dialog for data aggregation operations"""

    def __init__(self, data_handler, parent=None):
        super().__init__(parent)
        self.data_handler = data_handler
        self.thread_pool = QThreadPool.globalInstance()
        self.result_df = None
        self.setWindowTitle("Aggregate Data")
        self.setModal(True)
        self.resize(DIALOG_WIDTH, DIALOG_HEIGHT)
        self.columns = list(data_handler.df.columns)

        self.date_grouping_options = ["None", "Year", "Quarter", "Month", "Week", "Day"]
        
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(DEBOUNCE_DELAY_MS)
        self.preview_timer.timeout.connect(self._execute_preview)
        
        self.init_ui()

    def init_ui(self):
        """Initialize dialog UI"""
        main_layout = QVBoxLayout()
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        top_widget = QWidget()
        # Top sction with configuration options
        config_layout = QHBoxLayout(top_widget)
        config_layout.setContentsMargins(0, 0, 0, 0)
        

        # first: group-by section
        group_box = DataPlotStudioGroupBox("Group By")
        group_layout = QVBoxLayout()

        group_info = QLabel("Select columns to group by:")
        group_font = group_info.font()
        group_font.setPointSize(9)
        group_info.setFont(group_font)
        group_layout.addWidget(group_info)
        
        # Search bar for the group by list
        self.group_by_search_input = DataPlotStudioLineEdit()
        self.group_by_search_input.setPlaceholderText("Search columns...")
        self.group_by_search_input.setClearButtonEnabled(True)
        self.group_by_search_input.textChanged.connect(self.filter_group_by_columns)
        group_layout.addWidget(self.group_by_search_input)

        self.group_by_list = DataPlotStudioListWidget()
        self.group_by_list.setSelectionMode(
            DataPlotStudioListWidget.SelectionMode.MultiSelection
        )
        self.group_by_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.group_by_list.model().rowsMoved.connect(self.update_preview)
        
        self._populate_list_with_icons(self.group_by_list, self.columns)
        self.group_by_list.itemSelectionChanged.connect(self.on_group_selection_change)
        group_layout.addWidget(self.group_by_list)

        # Date grouping for datetime cols
        self.date_group_frame = DataPlotStudioGroupBox("Date Grouping")
        self.date_group_frame.setVisible(False)
        date_layout = QFormLayout()
        self.date_freq_combo = DataPlotStudioComboBox()
        self.date_freq_combo.addItems(self.date_grouping_options)
        self.date_freq_combo.currentTextChanged.connect(self.update_preview)
        date_layout.addRow("Frequency:", self.date_freq_combo)
        self.date_group_frame.setLayout(date_layout)
        group_layout.addWidget(self.date_group_frame)

        group_box.setLayout(group_layout)
        config_layout.addWidget(group_box, 1)

        # Aggregation section
        agg_box = DataPlotStudioGroupBox("Aggregation Columns")
        agg_layout = QVBoxLayout()

        selection_layout = QHBoxLayout()

        # _Available cols
        available_layout = QVBoxLayout()
        available_layout.addWidget(QLabel("Available Columns:"))
        
        # Search bar to filter columns
        self.column_search_input = DataPlotStudioLineEdit()
        self.column_search_input.setPlaceholderText("Search columns...")
        self.column_search_input.setClearButtonEnabled(True)
        self.column_search_input.textChanged.connect(self.filter_available_columns)
        
        self.column_search_input.returnPressed.connect(self.add_first_visible_column_to_agg)
        
        available_layout.addWidget(self.column_search_input)
        
        self.available_list = DataPlotStudioListWidget()
        self._populate_list_with_icons(self.available_list, self.columns)
        self.available_list.setSelectionMode(DataPlotStudioListWidget.SelectionMode.ExtendedSelection)
        self.available_list.itemDoubleClicked.connect(self.add_single_column_to_agg)
        
        self.available_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.available_list.customContextMenuRequested.connect(self._show_available_list_context_menu)
        
        available_layout.addWidget(self.available_list)
        selection_layout.addLayout(available_layout)

        # Buttons
        button_layout = QVBoxLayout()
        button_layout.addStretch()
        self.button_add = DataPlotStudioButton("Add >", parent=self)
        self.button_add.setToolTip("Add selected columns to aggregation setup")
        self.button_add.setMaximumWidth(120)
        self.button_add.clicked.connect(self.add_column_to_agg)
        button_layout.addWidget(self.button_add)
        
        self.button_remove = DataPlotStudioButton("< Remove", parent=self)
        self.button_remove.setToolTip("Remove selected columns from aggregation setup")
        self.button_remove.setMaximumWidth(120)
        self.button_remove.clicked.connect(self.remove_column_from_agg)
        button_layout.addWidget(self.button_remove)
        
        self.button_clear_all = DataPlotStudioButton("<< Clear All", parent=self)
        self.button_clear_all.setToolTip("Remove all columns from aggregation setup")
        self.button_clear_all.setMaximumWidth(120)
        self.button_clear_all.clicked.connect(self.clear_all_aggregations)
        button_layout.addWidget(self.button_clear_all)
        
        button_layout.addStretch()
        selection_layout.addLayout(button_layout)

        # Selected columns table
        selected_layout = QVBoxLayout()
        selected_layout.addWidget(QLabel("Selected:"))
        
        table_and_controls_layout = QHBoxLayout()
        
        self.agg_table = QTableWidget()
        self.agg_table.setAlternatingRowColors(True)
        self.agg_table.setColumnCount(2)
        self.agg_table.setHorizontalHeaderLabels(["Column", "Function"])
        
        header_font = self.agg_table.horizontalHeader().font()
        header_font.setBold(True)
        self.agg_table.horizontalHeader().setFont(header_font)
        self.agg_table.verticalHeader().setDefaultSectionSize(35)
        
        self.agg_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.agg_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.agg_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.agg_table.verticalHeader().setVisible(False)
        self.agg_table.cellDoubleClicked.connect(self.remove_single_column_from_agg)
        
        self.agg_table.cellDoubleClicked.connect(self.remove_single_column_from_agg)
        self.agg_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.agg_table.customContextMenuRequested.connect(self._show_agg_table_context_menu)
        
        # Keyboard shortcuts for row deletion
        self.delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self.agg_table)
        self.delete_shortcut.activated.connect(self.remove_single_column_from_agg)
        self.backspace_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Backspace), self.agg_table)
        self.backspace_shortcut.activated.connect(self.remove_column_from_agg)
        
        table_and_controls_layout.addWidget(self.agg_table)
        
        reorder_layout = QVBoxLayout()
        self.btn_move_up = DataPlotStudioButton("", parent=self)
        self.btn_move_up.setIcon(QIcon("icons/ui_styling/arrow-big-up.svg"))
        self.btn_move_up.setToolTip("Move selected column up")
        self.btn_move_up.clicked.connect(self.move_agg_row_up)
        
        self.btn_move_down = DataPlotStudioButton("", parent=self)
        self.btn_move_down.setIcon(QIcon("icons/ui_styling/arrow-big-down.svg"))
        self.btn_move_down.setToolTip("Move selected column down")
        self.btn_move_down.clicked.connect(self.move_agg_row_down)
        
        reorder_layout.addWidget(self.btn_move_up)
        reorder_layout.addWidget(self.btn_move_down)
        reorder_layout.addStretch()
        
        table_and_controls_layout.addLayout(reorder_layout)
        selected_layout.addLayout(table_and_controls_layout)
        selection_layout.addLayout(selected_layout)

        agg_layout.addLayout(selection_layout)
        agg_box.setLayout(agg_layout)
        config_layout.addWidget(agg_box, 2)

        self.main_splitter.addWidget(top_widget)

        # Preview table section
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        preview_label = QLabel("Preview:")
        preview_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        bottom_layout.addWidget(preview_label)

        self.preview_table = QTableWidget()
        self.preview_table.horizontalHeader().setObjectName("MainDataHeader")
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.setMaximumHeight(PREVIEW_TABLE_MAX_HEIGHT)
        
        preview_header_font = self.preview_table.horizontalHeader().font()
        preview_header_font.setBold(True)
        self.preview_table.horizontalHeader().setFont(preview_header_font)
        self.preview_table.setGridStyle(Qt.PenStyle.DotLine)
        
        bottom_layout.addWidget(self.preview_table)

        self.main_splitter.addWidget(bottom_widget)
        
        self.main_splitter.setSizes([DIALOG_HEIGHT - PREVIEW_TABLE_MAX_HEIGHT, PREVIEW_TABLE_MAX_HEIGHT])

        main_layout.addWidget(self.main_splitter)
        main_layout.addSpacing(10)

        # Save secion
        self.save_agg_group = DataPlotStudioGroupBox(
            "Save this aggregation", parent=self
        )
        self.save_agg_group.setCheckable(True)
        self.save_agg_group.setChecked(False)

        save_layout = QFormLayout()
        self.save_name_input = DataPlotStudioLineEdit()
        self.save_name_input.setPlaceholderText("e.g., 'Sales by Region'")
        save_layout.addRow(QLabel("Save as:"), self.save_name_input)

        self.save_agg_group.setLayout(save_layout)
        main_layout.addWidget(self.save_agg_group)

        # buttons for accept and reject
        btn_layout = QHBoxLayout()
        self.apply_button = DataPlotStudioButton("Apply Aggregation", parent=self, base_color_hex=ThemeColors.MainColor)
        self.apply_button.clicked.connect(self.validate_and_accept)
        self.apply_button.setEnabled(False)
        self.apply_button.setDefault(True)
        btn_layout.addWidget(self.apply_button)

        cancel_button = DataPlotStudioButton("Cancel", parent=self)
        cancel_button.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_button)

        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)
        
        self.column_search_input.setFocus()
        self.update_preview()

    def on_group_selection_change(self):
        """Changes in group by selection t show date options"""
        selected_items = self.group_by_list.selectedItems()
        show_date_options = False

        # check for datetime
        for item in selected_items:
            col_name = item.text()
            if pd.api.types.is_datetime64_any_dtype(self.data_handler.df[col_name]):
                show_date_options = True
                break

        self.date_group_frame.setVisible(show_date_options)
        self.update_preview()
    
    def filter_available_columns(self, search_text: str) -> None:
        """Filter the available columns list based on the user's search query."""
        for i in range(self.available_list.count()):
            item = self.available_list.item(i)
            #Hide all other items
            item.setHidden(search_text.lower() not in item.text().lower())
    
    def filter_group_by_columns(self, search_text: str) -> None:
        """Filter the group by column list based on user's search query"""
        for i in range(self.group_by_list.count()):
            item = self.group_by_list.item(i)
            item.setHidden(search_text.lower() not in item.text().lower())
    
    def add_single_column_to_agg(self, item: QTableWidgetItem) -> None:
        """Handle double-click event to add a single column directly to the aggregation config."""
        self._add_specific_column_to_agg(item.text())
        self.update_preview()
        
    def add_first_visible_column_to_agg(self) -> None:
        """Add the top visible column in the available list wehen hittin ENter/Return key"""
        for i in range(self.available_list.count()):
            item = self.available_list.item(i)
            if not item.isHidden():
                self._add_specific_column_to_agg(item.text())
                self.column_search_input.clear()
                self.update_preview()
                break
        
    def clear_all_aggregations(self) -> None:
        """Remove all currently selected columns from the aggregation table."""
        self.agg_table.setRowCount(0)
        self.update_preview()
    
    def _show_available_list_context_menu(self, position: QPoint) -> None:
        """Display a right-click context menu for the available columns list."""
        menu = QMenu(self)
        select_all_action = menu.addAction("Select All")
        
        action = menu.exec(self.available_list.viewport().mapToGlobal(position))
        
        if action == select_all_action:
            self.available_list.selectAll()
    
    def move_agg_row_up(self) -> None:
        """Move the currently selected aggregation row up by one position."""
        row: int = self.agg_table.currentRow()
        if row > 0:
            self._swap_agg_rows(row, row - 1)
    
    def move_agg_row_down(self) -> None:
        """Move the currently selected aggregation row down by one position."""
        row: int = self.agg_table.currentRow()
        if row >= 0 and row < self.agg_table.rowCount() - 1:
            self._swap_agg_rows(row, row + 1)
    
    def _swap_agg_rows(self, row1: int, row2: int) -> None:
        """Helper to swap table row data and their widgets"""
        col1: str = self.agg_table.item(row1, 0).text()
        func1: str = self.agg_table.cellWidget(row1, 1).currentText()
        
        col2: str = self.agg_table.item(row2, 0).text()
        func2: str = self.agg_table.cellWidget(row2, 1).currentText()
        
        self.agg_table.item(row1, 0).setText(col2)
        self.agg_table.cellWidget(row1, 1).setCurrentText(func2)
        
        self.agg_table.item(row2, 0).setText(col1)
        self.agg_table.cellWidget(row2, 1).setCurrentText(func1)
        
        self.agg_table.selectRow(row2)
        self.update_preview()
    
    def _show_agg_table_context_menu(self, position: QPoint) -> None:
        """Display a right-click context menu for the aggregation table."""
        menu = QMenu(self)
        
        remove_action = menu.addAction("Remove Selected")
        menu.addSeparator()
        clear_action = menu.addAction("Clear All")
        
        # Disable remove if no rows are selected
        if not self.agg_table.selectedIndexes():
            remove_action.setEnabled(False)
        
        # Disable clear if table is empty
        if self.agg_table.rowCount() == 0:
            clear_action.setEnabled(False)
        
        # Execute menu at global cursor position
        action = menu.exec(self.agg_table.viewport().mapToGlobal(position))
        
        if action == remove_action:
            self.remove_column_from_agg()
        elif action == clear_action:
            self.clear_all_aggregations()
    
    def _add_specific_column_to_agg(self, col_name: str) -> None:
        """Internal helper to add a specific column by name"""
        exists: bool = False
        for row in range(self.agg_table.rowCount()):
            if self.agg_table.item(row, 0).text() == col_name:
                exists = True
                break
        
        if not exists:
            row: int = self.agg_table.rowCount()
            self.agg_table.insertRow(row)
            
            name_item = QTableWidgetItem(col_name)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.agg_table.setItem(row, 0, name_item)
            
            combo = DataPlotStudioComboBox()
            for index, func in enumerate(AggregationFunctions):
                combo.addItem(func.value)
                combo.setItemData(index, AGGREGATION_TOOLTIPS[func], Qt.ItemDataRole.ToolTipRole)
            
            # Default based on type
            if pd.api.types.is_numeric_dtype(self.data_handler.df[col_name]):
                combo.setCurrentText("sum")
            else:
                combo.setCurrentText("count")

            combo.currentTextChanged.connect(self.update_preview)
            self.agg_table.setCellWidget(row, 1, combo)

    def add_column_to_agg(self):
        """Add selected columns from the list to the aggregation table"""
        for item in self.available_list.selectedItems():
            self._add_specific_column_to_agg(item.text())
        self.update_preview()

    def remove_column_from_agg(self):
        """Remove selected rows from aggregation table"""
        rows = sorted(
            set(index.row() for index in self.agg_table.selectedIndexes()), reverse=True
        )
        for row in rows:
            self.agg_table.removeRow(row)
        self.update_preview()
    
    def remove_single_column_from_agg(self, row: int) -> None:
        """Handle double-click event to remove a specific row from the aggregation table."""
        self.agg_table.removeRow(row)
        self.update_preview()
    
    def _evaluate_apply_button_state(self, group_cols: list[str], agg_config: dict[str, str]) -> None:
        """Dynamically enable or disable the apply button based on configuration validity."""
        has_groups: bool = len(group_cols) > 0
        has_aggs: bool = len(agg_config) > 0
        overlap: set[str] = set(group_cols) & set(agg_config.keys())
        
        # Valid if we have both groups and aggregations, and no overlapping columns
        is_valid: bool = has_groups and has_aggs and not bool(overlap)
        
        self.apply_button.setEnabled(is_valid)
        if not is_valid:
            self.apply_button.setToolTip("Select at least one group-by and one aggregation column")
        else:
            self.apply_button.setToolTip("")

    def get_current_config(self):
        """Construct the config"""
        group_cols = [item.text() for item in self.group_by_list.selectedItems()]

        agg_config = {}
        for row in range(self.agg_table.rowCount()):
            col = self.agg_table.item(row, 0).text()
            func = self.agg_table.cellWidget(row, 1).currentText()
            agg_config[col] = func

        date_grouping = {}
        if (self.date_group_frame.isVisible()and self.date_freq_combo.currentText() != "None"):
            freq = self.date_freq_combo.currentText()
            for col in group_cols:
                if pd.api.types.is_datetime64_any_dtype(self.data_handler.df[col]):
                    date_grouping[col] = freq

        return group_cols, agg_config, date_grouping
    
    def _populate_list_with_icons(self, list_widget: DataPlotStudioListWidget, columns: list[str]) -> None:
        """Populate a list widget with column names and data-type specific icons."""
        list_widget.clear()
        for col_name in columns:
            item = QListWidgetItem(col_name)
            
            # Determine icon based on pandas dtype
            # TODO change these icons to use IconBuilder.build(IconType.Type)
            dtype = self.data_handler.df[col_name].dtype
            if pd.api.types.is_numeric_dtype(dtype):
                icon_path = "icons/data_operations/calculator.svg"
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                icon_path = "icons/data_operations/calendar-clock.svg"
            else:
                icon_path = "icons/data_operations/text_operation.svg"
            
            item.setIcon(QIcon(icon_path))
            list_widget.addItem(item)

    def update_preview(self) -> None:
        """Restarts the debounce timer. The actual preview is generated on timeout."""
        group_cols, agg_config, _ = self.get_current_config()
        self._evaluate_apply_button_state(group_cols, agg_config)
        
        self.preview_table.clear()
        self.preview_table.setRowCount(1)
        self.preview_table.setColumnCount(1)
        self.preview_table.setHorizontalHeaderLabels(["Status"])
        self.preview_table.setItem(0, 0, QTableWidgetItem("Updating preview..."))
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.preview_timer.start()
    
    def _execute_preview(self) -> None:
        """Generate and display aggragation preview"""
        group_cols, agg_config, date_grouping = self.get_current_config()

        if not group_cols and not agg_config:
            self.preview_table.clear()
            self.preview_table.setRowCount(0)
            self.preview_table.setColumnCount(1)
            self.preview_table.setHorizontalHeaderLabels(["Status"])
            self.preview_table.setItem(
                0, 0, QTableWidgetItem("Select columns to see preview")
            )
            self.preview_table.horizontalHeader().setSectionResizeMode(
                0, QHeaderView.ResizeMode.Stretch
            )
            return

        try:
            preview_df = self.data_handler.preview_aggregation(
                group_by=group_cols,
                agg_config=agg_config,
                date_grouping=date_grouping,
                limit=DEFAULT_PREVIEW_LIMIT,
            )

            self.preview_table.clear()
            self.preview_table.setRowCount(len(preview_df))
            self.preview_table.setColumnCount(len(preview_df.columns))
            self.preview_table.setHorizontalHeaderLabels(
                [str(column) for column in preview_df.columns]
            )

            for row in range(len(preview_df)):
                for col in range(len(preview_df.columns)):
                    val = preview_df.iloc[row, col]
                    item = QTableWidgetItem(str(val))
                    self.preview_table.setItem(row, col, item)

            self.preview_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Interactive
            )

        except Exception as PreviewTableError:
            self.preview_table.clear()
            self.preview_table.setRowCount(1)
            self.preview_table.setColumnCount(1)
            self.preview_table.setHorizontalHeaderLabels(["Error"])
            self.preview_table.setItem(
                0, 0, QTableWidgetItem(f"Cannot preview: {str(PreviewTableError)}")
            )
            self.preview_table.horizontalHeader().setSectionResizeMode(
                0, QHeaderView.ResizeMode.Stretch
            )

    def validate_and_accept(self):
        """Validate selections before accepting"""
        group_cols, agg_config, date_grouping = self.get_current_config()

        if not group_cols:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please select at least one column to group by",
            )
            return

        if not agg_config:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please select at least one column to aggregate",
            )
            return

        # check for overlap
        overlap = set(group_cols) & set(agg_config.keys())
        if overlap:
            QMessageBox.warning(
                self,
                "Validation Error",
                f"Columns cannot be both grouped and aggregated:\n{', '.join(overlap)}",
            )
            return

        # check if name is given
        if self.save_agg_group.isChecked() and not self.save_name_input.text().strip():
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please enter a name for the aggregation you want to save.",
            )
            return
        
        self.setEnabled(False)
        self.button_add.setEnabled(False)
        self.button_remove.setEnabled(False)
        
        worker = AggregationWorker(self.data_handler, group_cols,agg_config, date_grouping)
        worker.signals.finished.connect(self.on_aggregation_finished)
        worker.signals.error.connect(self.on_aggregation_error)
        self.thread_pool.start(worker)
    
    def on_aggregation_finished(self, result_df):
        self.result_df = result_df
        self.setEnabled(True)
        self.accept()
    
    def on_aggregation_error(self, error):
        self.setEnabled(True)
        self.button_add.setEnabled(True)
        self.button_remove.setEnabled(True)
        QMessageBox.critical(self, "Aggregation Error", f"An error occurred:\n{str(error)}")

    def get_aggregation_config(self):
        """Return the aggregation config"""
        group_cols, agg_config, date_grouping = self.get_current_config()

        config = {
            "group_by": group_cols,
            "agg_config": agg_config,
            "date_grouping": date_grouping,
            "aggregation_name": self.save_name_input.text().strip()
            if self.save_agg_group.isChecked()
            else "",
        }

        return config
