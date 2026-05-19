import threading
from enum import Enum

import pandas as pd
from PyQt6.QtCore import Qt, QThreadPool, QTimer, QPoint, QObject, pyqtSignal, QRunnable, QSortFilterProxyModel, QModelIndex
from PyQt6.QtGui import QFont, QKeySequence, QShortcut, QIcon, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QTableWidget, \
    QHeaderView, QAbstractItemView, QTableWidgetItem, QSplitter, QWidget, QListWidgetItem, QListView
from xlrd import colname

from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton
from ui.widgets.ControlElements import DataPlotStudioComboBox, DataPlotStudioGroupBox, DataPlotStudioLineEdit, \
    DataPlotStudioListWidget, DataPlotStudioMenu
from ui.workers import AggregationWorker
from ui.icons import IconBuilder, IconType

DIALOG_WIDTH: int = 1200
DIALOG_HEIGHT: int = 700
PREVIEW_TABLE_MAX_HEIGHT: int = 200
DEFAULT_PREVIEW_LIMIT: int = 5
DEBOUNCE_DELAY_MS: int = 300
MIN_AGG_TABLE_HEIGHT: int = 150

class PreviewSignals(QObject):
    finished = pyqtSignal(int, object)
    error = pyqtSignal(int, str)

class PreviewWorker(QRunnable):
    """Worker to calculate the aggregation preview asynchronously"""
    def __init__(self, data_handler, group_cols: list[str], agg_config: dict[str, list[str]], date_grouping: dict[str, str], limit: int, req_id: int, cancel_token: threading.Event) -> None:
        super().__init__()
        self.data_handler = data_handler
        self.group_cols = group_cols
        self.agg_config = agg_config
        self.date_grouping = date_grouping
        self.limit = limit
        self.req_id = req_id
        self.cancel_token = cancel_token
        self.signals = PreviewSignals()

    def run(self) -> None:
        if self.cancel_token.is_set():
            return
        try:
            preview_df = self.data_handler.preview_aggregation(
                group_by=self.group_cols,
                agg_config=self.agg_config,
                date_grouping=self.date_grouping,
                limit=self.limit
            )
            if self.cancel_token.is_set():
                return
            self.signals.finished.emit(self.req_id, preview_df)
        except Exception as error:
            self.signals.error.emit(self.req_id, str(error))

class AggregationFunctions(str, Enum):
    """
    Enumeration of supported pandas aggregation functions.
    These are all the functions that the AggregationDialog of Aletheia currently allows
    """
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
    Q25 = "q25"
    Q75 = "q75"
    Q90 = "q90"

# A dict to assign for tooltip role
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
    AggregationFunctions.Q25: "25th Percentile (First Quartile)",
    AggregationFunctions.Q75: "75th Percentile (Third Quartile)",
    AggregationFunctions.Q90: "90th Percentile",
}

# Aggregation functions that require numeric dataa
NUMERIC_ONLY_FUNCTIONS: set[AggregationFunctions] = {
    AggregationFunctions.MEAN,
    AggregationFunctions.SUM,
    AggregationFunctions.MEDIAN,
    AggregationFunctions.STD,
    AggregationFunctions.VAR,
    AggregationFunctions.Q25,
    AggregationFunctions.Q75,
    AggregationFunctions.Q90
}

# Functions that is safe for all data types
UNIVERSAL_FUNCTIONS: set[AggregationFunctions] = {
    AggregationFunctions.MIN,
    AggregationFunctions.MAX,
    AggregationFunctions.COUNT,
    AggregationFunctions.FIRST,
    AggregationFunctions.LAST,
    AggregationFunctions.NUNIQUE,
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
        self.date_freq_combos: dict[str, DataPlotStudioComboBox] = {}
        self._preview_request_id: int = 0
        self._current_cancel_token: threading.Event | None = None
        
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

        self.group_by_list_view = QListView()
        self.group_by_list_view.setObjectName("dpsListWidget")
        self.group_by_list_view.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.group_by_list_view.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

        self.group_by_model = QStandardItemModel()
        self.group_by_model.rowsMoved.connect(self.update_preview)

        self.group_by_proxy = QSortFilterProxyModel()
        self.group_by_proxy.setSourceModel(self.group_by_model)
        self.group_by_proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self.group_by_list_view.setModel(self.group_by_proxy)

        self._populate_list_with_icons(self.group_by_model, self.columns)
        self.group_by_list_view.selectionModel().selectionChanged.connect(self.on_group_selection_change)
        group_layout.addWidget(self.group_by_list_view)

        self.date_hint_label = QLabel("Select a datetime column to enable date grouping")
        self.date_hint_label.setObjectName("DateGroupingHintLabel")
        hint_font = self.date_hint_label.font()
        hint_font.setPointSize(8)
        hint_font.setItalic(True)
        self.date_hint_label.setFont(hint_font)
        self.date_hint_label.setWordWrap(True)
        group_layout.addWidget(self.date_hint_label)

        # Date grouping for datetime cols
        self.date_group_frame = DataPlotStudioGroupBox("Date Grouping")
        self.date_group_frame.setVisible(False)
        self.date_group_layout = QFormLayout()
        self.date_group_frame.setLayout(self.date_group_layout)
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
        
        self.available_list_view = QListView()
        self.available_list_view.setObjectName("dpsListWidget")
        self.available_list_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        self.available_model = QStandardItemModel()
        self.available_proxy = QSortFilterProxyModel()
        self.available_proxy.setSourceModel(self.available_model)
        self.available_proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self.available_list_view.setModel(self.available_proxy)
        self._populate_list_with_icons(self.available_model, self.columns)

        self.available_list_view.doubleClicked.connect(self.add_single_column_to_agg)
        self.available_list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.available_list_view.customContextMenuRequested.connect(self._show_available_list_context_menu)

        # Keyboard shortcuts for addition to the aggregation list
        self.list_enter_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self.available_list_view)
        self.list_enter_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        self.list_enter_shortcut.activated.connect(self.add_column_to_agg)

        self.list_enter_numpad_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Enter), self.available_list_view)
        self.list_enter_numpad_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        self.list_enter_numpad_shortcut.activated.connect(self.add_column_to_agg)

        self.list_space_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self.available_list_view)
        self.list_space_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        self.list_space_shortcut.activated.connect(self.add_column_to_agg)
        
        available_layout.addWidget(self.available_list_view)
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
        self.agg_table.setColumnCount(3)
        self.agg_table.setHorizontalHeaderLabels(["Column", "Function", "Output Name"])
        
        header_font = self.agg_table.horizontalHeader().font()
        header_font.setBold(True)
        self.agg_table.horizontalHeader().setFont(header_font)
        self.agg_table.verticalHeader().setDefaultSectionSize(35)
        
        self.agg_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.agg_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.agg_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.agg_table.setColumnWidth(1, 140)
        self.agg_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.agg_table.verticalHeader().setVisible(False)
        self.agg_table.setMinimumHeight(MIN_AGG_TABLE_HEIGHT)
        self.agg_table.cellDoubleClicked.connect(self.remove_single_column_from_agg)
        
        self.agg_table.cellDoubleClicked.connect(self.remove_single_column_from_agg)
        self.agg_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.agg_table.customContextMenuRequested.connect(self._show_agg_table_context_menu)
        
        # Keyboard shortcuts for row deletion
        self.delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self.agg_table)
        self.delete_shortcut.activated.connect(self.remove_column_from_agg)
        self.backspace_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Backspace), self.agg_table)
        self.backspace_shortcut.activated.connect(self.remove_column_from_agg)

        self.move_up_shortcut = QShortcut(QKeySequence("Alt+Up"), self.agg_table)
        self.move_up_shortcut.activated.connect(self.move_agg_row_up)
        self.move_down_shortcut = QShortcut(QKeySequence("Alt+Down"), self.agg_table)
        self.move_down_shortcut.activated.connect(self.move_agg_row_down)
        
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
        self.save_agg_group.toggled.connect(self._on_save_group_toggled)

        save_layout = QFormLayout()
        self.save_name_input = DataPlotStudioLineEdit()
        self.save_name_input.setPlaceholderText("e.g., 'Sales by Region'")
        self.save_name_input.textChanged.connect(self._re_evaluate_apply_button)
        save_layout.addRow(QLabel("Save as:"), self.save_name_input)

        self.save_agg_group.setLayout(save_layout)
        main_layout.addWidget(self.save_agg_group)

        # buttons for accept and reject
        btn_layout = QHBoxLayout()
        self.apply_button = DataPlotStudioButton("Apply Aggregation", parent=self, base_color_hex=ThemeColors.MainColor, text_color_hex="white")
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

    def _on_save_group_toggled(self, checked: bool) -> None:
        """Handle toggling of the save aggregation group"""
        if checked:
            self.save_name_input.setFocus()
        self._re_evaluate_apply_button()

    def on_group_selection_change(self):
        """Changes in group by selection t show date options"""
        selected_indexes = self.group_by_list_view.selectionModel().selectedIndexes()
        show_date_options = False

        existing_states: dict[str, str] = {
            col: combo.currentText() for col, combo in self.date_freq_combos.items()
        }

        while self.date_group_layout.count():
            item = self.date_group_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.date_freq_combos.clear()

        # check for datetime
        for item in selected_indexes:
            col_name = item.data()
            if pd.api.types.is_datetime64_any_dtype(self.data_handler.df[col_name]):
                show_date_options = True

                combo = DataPlotStudioComboBox()
                combo.addItems(self.date_grouping_options)

                if col_name in existing_states:
                    combo.setCurrentText(existing_states[col_name])
                combo.currentTextChanged.connect(self.update_preview)
                self.date_group_layout.addRow(f"{col_name}:", combo)
                self.date_freq_combos[col_name] = combo

        self.date_group_frame.setVisible(show_date_options)
        self.date_hint_label.setVisible(not show_date_options)
        self.update_preview()
    
    def filter_available_columns(self, search_text: str) -> None:
        """Filter the available columns list based on the user's search query."""
        self.available_proxy.setFilterFixedString(search_text)
    
    def filter_group_by_columns(self, search_text: str) -> None:
        """Filter the group by column list based on user's search query"""
        self.group_by_proxy.setFilterFixedString(search_text)
    
    def add_single_column_to_agg(self, index: QTableWidgetItem) -> None:
        """Handle double-click event to add a single column directly to the aggregation config."""
        self._add_specific_column_to_agg(index.text())
        self.update_preview()
        
    def add_first_visible_column_to_agg(self) -> None:
        """Add the top visible column in the available list wehen hittin ENter/Return key"""
        if self.available_proxy.rowCOunt() > 0:
            first_index = self.available_proxy.index(0, 0)
            self._add_specific_column_to_agg(first_index.data())
            self.column_search_input.clear()
            self.update_preview()
        
    def clear_all_aggregations(self) -> None:
        """Remove all currently selected columns from the aggregation table."""
        if self.agg_table.rowCount() == 0:
            return

        confirmation = QMessageBox.question(
            self,
            "Confirm Clear All",
            "Are you sure you want to remove all configured aggregations?\nThis action cannot be undone",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirmation == QMessageBox.StandardButton.Yes:
            self.agg_table.setRowCount(0)
            self.update_preview()
    
    def _show_available_list_context_menu(self, position: QPoint) -> None:
        """Display a right-click context menu for the available columns list."""
        menu = DataPlotStudioMenu(self)
        select_all_action = menu.addAction("Select All")
        
        action = menu.exec(self.available_list_view.viewport().mapToGlobal(position))
        
        if action == select_all_action:
            self.available_list_view.selectAll()
    
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
        col_count: int = self.agg_table.columnCount()

        items1 = [self.agg_table.takeItem(row1, c) for c in range(col_count)]
        widgets1 = [self.agg_table.cellWidget(row1, c) for c in range(col_count)]

        items2 = [self.agg_table.takeItem(row2, c) for c in range(col_count)]
        widgets2 = [self.agg_table.cellWidget(row2, c) for c in range(col_count)]

        for c in range(col_count):
            if items1[c] is not None:
                self.agg_table.setItem(row2, c, items1[c])
            if widgets1[c] is not None:
                self.agg_table.setCellWidget(row2, c, widgets1[c])

        for c in range(col_count):
            if items2[c] is not None:
                self.agg_table.setItem(row1, c, items2[c])
            if widgets2[c] is not None:
                self.agg_table.setCellWidget(row1, c, widgets2[c])
        
        self.agg_table.selectRow(row2)
        self.update_preview()
    
    def _show_agg_table_context_menu(self, position: QPoint) -> None:
        """Display a right-click context menu for the aggregation table."""
        menu = DataPlotStudioMenu(self)
        
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

    def _get_allowed_functions(self, col_name: str) -> list[AggregationFunctions]:
        """Get a list of allowed aggregation functions based on the column type"""
        if pd.api.types.is_numeric_dtype(self.data_handler.df[col_name]):
            return list(AggregationFunctions)
        else:
            return list(UNIVERSAL_FUNCTIONS)
    
    def _add_specific_column_to_agg(self, col_name: str) -> None:
        """Internal helper to add a specific column by name"""
        row: int = self.agg_table.rowCount()
        self.agg_table.insertRow(row)

        name_item = QTableWidgetItem(col_name)
        name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.agg_table.setItem(row, 0, name_item)

        combo = DataPlotStudioComboBox()
        allowed_functions = self._get_allowed_functions(col_name)
        for index, func in enumerate(allowed_functions):
            combo.addItem(func.value)
            combo.setItemData(index, AGGREGATION_TOOLTIPS[func], Qt.ItemDataRole.ToolTipRole)

        # Default based on type
        if pd.api.types.is_numeric_dtype(self.data_handler.df[col_name]):
            combo.setCurrentText(AggregationFunctions.SUM.value)
        else:
            combo.setCurrentText(AggregationFunctions.COUNT.value)

        combo.currentTextChanged.connect(self.update_preview)
        self.agg_table.setCellWidget(row, 1, combo)

        out_name_edit = DataPlotStudioLineEdit()
        out_name_edit.setPlaceholderText(f"{col_name}_{combo.currentText()}")
        out_name_edit.textChanged.connect(self.update_preview)
        self.agg_table.setCellWidget(row, 2, out_name_edit)

        combo.currentTextChanged.connect(
            lambda text, edit=out_name_edit, c=col_name: edit.setPlaceholderText(f"{c}_{text}")
        )

        self.agg_table.selectRow(row)
        self.agg_table.scrollToItem(name_item)

    def add_column_to_agg(self):
        """Add selected columns from the list to the aggregation table"""
        for index in self.available_list_view.selectionModel().selectedIndexes():
            self._add_specific_column_to_agg(index.data())
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
    
    def _evaluate_apply_button_state(self, group_cols: list[str], agg_config: dict[str, list[str]]) -> None:
        """Dynamically enable or disable the apply button based on configuration validity."""
        has_groups: bool = len(group_cols) > 0
        has_aggs: bool = len(agg_config) > 0
        overlap: set[str] = set(group_cols) & set(agg_config.keys())

        requires_name: bool = self.save_agg_group.isChecked()
        has_name: bool = bool(self.save_name_input.text().strip())

        is_valid: bool = has_groups and has_aggs and not bool(overlap)
        if requires_name and not has_name:
            is_valid = False

        self.apply_button.setEnabled(is_valid)

        if overlap:
            self.apply_button.setToolTip(f"Overlapping columns: {', '.join(overlap)}")
        elif not has_groups or not has_aggs:
            self.apply_button.setToolTip("Select at least one group-by and one aggregation column")
        elif requires_name and not has_name:
            self.apply_button.setToolTip("Please enter a name for the saved aggregation")
        else:
            self.apply_button.setToolTip("Apply configuration")

    def get_current_config(self) -> tuple[list[str], dict[str, list[str]], dict[str, str], dict[str, str]]:
        """Construct the config"""
        group_cols: list[str] = [index.data() for index in self.group_by_list_view.selectionModel().selectedIndexes()]
        agg_config: dict[str, list[str]] = {}
        rename_mapping: dict[str, str] = {}

        for row in range(self.agg_table.rowCount()):
            col = self.agg_table.item(row, 0).text()
            func = self.agg_table.cellWidget(row, 1).currentText()
            if col not in agg_config:
                agg_config[col] = []
            if func not in agg_config:
                agg_config[col].append(func)

            out_name_widget = self.agg_table.cellWidget(row, 2)
            if out_name_widget:
                out_name = out_name_widget.text().strip()
                if out_name:
                    rename_mapping[f"{col}_{func}"] = out_name

        date_grouping: dict[str, str] = {}
        if self.date_group_frame.isVisible():
            for col, combo in self.date_freq_combos.items():
                freq = combo.currentText()
                if freq != "None" and col in group_cols:
                    date_grouping[col] = freq

        return group_cols, agg_config, date_grouping, rename_mapping
    
    def _populate_list_with_icons(self, model: QStandardItemModel, columns: list[str]) -> None:
        """Populate a standard item model with column names and their data type"""
        model.clear()
        for col_name in columns:
            item = QStandardItem(col_name)

            dtype = self.data_handler.df[col_name].dtype
            if pd.api.types.is_numeric_dtype(dtype):
                icon = IconBuilder.build(IconType.Calculator)
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                icon = IconBuilder.build(IconType.DatetimeTools)
            else:
                icon = IconBuilder.build(IconType.TextOperation)

            item.setIcon(icon)
            item.setEditable(False)
            model.appendRow(item)

    def _re_evaluate_apply_button(self) -> None:
        group_cols, agg_config, _, _ = self.get_current_config()
        self._evaluate_apply_button_state(group_cols, agg_config)

    def update_preview(self) -> None:
        """Restarts the debounce timer. The actual preview is generated on timeout."""
        group_cols, agg_config, _, _ = self.get_current_config()
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
        group_cols, agg_config, date_grouping, _ = self.get_current_config()

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

        self._preview_request_id += 1
        if self._current_cancel_token is not None:
            self._current_cancel_token.set()

        self._current_cancel_token = threading.Event()

        worker = PreviewWorker(
            self.data_handler,
            group_cols,
            agg_config,
            date_grouping,
            DEFAULT_PREVIEW_LIMIT,
            self._preview_request_id,
            self._current_cancel_token
        )
        worker.signals.finished.connect(self._on_preview_finished)
        worker.signals.error.connect(self._on_preview_error)
        self.thread_pool.start(worker)

    def _on_preview_finished(self, req_id: int, preview_df: pd.DataFrame) -> None:
        """Handle successful async preview generation."""
        if req_id != self._preview_request_id:
            return
        _, _, _, rename_mapping = self.get_current_config()
        if rename_mapping:
            preview_df = preview_df.rename(columns=rename_mapping)

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

    def _on_preview_error(self, req_id: int, error_msg: str) -> None:
        """Handle errors during async preview generation."""
        if req_id != self._preview_request_id:
            return

        self.preview_table.clear()
        self.preview_table.setRowCount(1)
        self.preview_table.setColumnCount(1)
        self.preview_table.setHorizontalHeaderLabels(["Error"])
        self.preview_table.setItem(
            0, 0, QTableWidgetItem(f"Cannot preview: {error_msg}")
        )
        self.preview_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )

    def validate_and_accept(self):
        """Validate selections before accepting"""
        group_cols, agg_config, date_grouping, _ = self.get_current_config()

        if not group_cols:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please select at least one column to group by",
            )
            self.group_by_search_input.setFocus()
            return

        if not agg_config:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please select at least one column to aggregate",
            )
            self.column_search_input.setFocus()
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
            self.save_name_input.setFocus()
            return

        self.setEnabled(False)
        self.button_add.setEnabled(False)
        self.button_remove.setEnabled(False)

        worker = AggregationWorker(self.data_handler, group_cols, agg_config, date_grouping)
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
        group_cols, agg_config, date_grouping, rename_mapping = self.get_current_config()

        config = {
            "group_by": group_cols,
            "agg_config": agg_config,
            "date_grouping": date_grouping,
            "aggregation_name": self.save_name_input.text().strip()
            if self.save_agg_group.isChecked()
            else "",
            "rename_mapping": rename_mapping
        }

        return config
