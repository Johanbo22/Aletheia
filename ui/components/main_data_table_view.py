from typing import Any

import numpy as np
import pandas as pd
from PyQt6.QtCore import QAbstractItemModel, QItemSelectionModel, QModelIndex, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication, QHeaderView, QMenu, QTableView, QWidget
from numpy import dtype, ndarray, signedinteger
from numpy._typing import _32Bit, _64Bit
from pandas import DataFrame, Series

from core.data_handler import DataHandler
from core.global_signals import global_signals
from ui.data_table_model import DataTableModel
from ui.status_bar import LogLevel, StatusBar
from ui.widgets.ToastNotification import ToastLevel

class MainDataTableView(QTableView):
    """
    Central object for the main data table as a QTableView
    Operates its own context menu, clipboard copying, highlighting.
    """

    request_table_settings: pyqtSignal | pyqtSignal = pyqtSignal()
    request_statistical_test: pyqtSignal | pyqtSignal = pyqtSignal()

    def __init__(self, status_bar: StatusBar, data_handler: DataHandler, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.status_bar = status_bar
        self.data_handler = data_handler

        self._is_missing_highlighted: bool = False

        self.setObjectName("MainDataTable")
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setWordWrap(False)
        self.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)

        self.horizontalHeader().setObjectName("MainDataHeader")
        self.verticalHeader().setObjectName("MainDataHeader")
        self.verticalHeader().setDefaultSectionSize(32)

        self.horizontalHeader().setResizeContentsPrecision(500)
        self.verticalHeader().setResizeContentsPrecision(500)

        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_table_context_menu)

        self.horizontalHeader().sectionClicked.connect(self._on_horizontal_header_clicked)
        self.verticalHeader().sectionClicked.connect(self._on_vertical_header_clicked)

        self.copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self)
        self.copy_shortcut.activated.connect(self.copy_selection)

    def show_table_context_menu(self, position: QPoint) -> None:
        """
        Constructs and displays the context menu for the data table
        :param position: The position of the mouse click
        """
        if self.data_handler.df is None:
            return

        menu: QMenu | QMenu = QMenu()

        resize_cols_action: QAction | None = menu.addAction("Resize Columns to Contents")
        resize_rows_action: QAction | None = menu.addAction("Resize Rows to Contents")
        menu.addSeparator()

        grid_action: QAction | QAction = QAction("Show Grid", menu)
        grid_action.setCheckable(True)
        grid_action.setChecked(self.showGrid())
        grid_action.triggered.connect(self.setShowGrid)
        menu.addAction(grid_action)

        alt_rows_action: QAction | QAction = QAction("Alternating Colors", menu)
        alt_rows_action.setCheckable(True)
        alt_rows_action.setChecked(self.alternatingRowColors())
        alt_rows_action.triggered.connect(self.setAlternatingRowColors)
        menu.addAction(alt_rows_action)
        menu.addSeparator()

        highlight_missing_action: QAction = QAction("Highlight Missing Values", menu)
        highlight_missing_action.setCheckable(True)
        highlight_missing_action.setChecked(self._is_missing_highlighted)
        menu.addAction(highlight_missing_action)
        menu.addSeparator()

        select_all_action: QAction | None = menu.addAction("Select All")
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)

        clear_selection_action: QAction | None = menu.addAction("Clear Selection")

        copy_action: QAction | None = menu.addAction("Copy Selection")
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)

        settings_action: QAction | None = menu.addAction("Table Settings...")
        stats_test_action: QAction | None = menu.addAction("Run Statistical Test...")

        action: QAction | None = menu.exec(self.viewport().mapToGlobal(position))

        if action == resize_cols_action:
            self.resizeColumnsToContents()
        elif action == resize_rows_action:
            self.resizeRowsToContents()
        elif action == highlight_missing_action:
            self.toggle_missing_values_highlight(highlight_missing_action.isChecked())
        elif action == select_all_action:
            self.selectAll()
        elif action == clear_selection_action:
            self.clearSelection()
        elif action == copy_action:
            self.copy_selection()
        elif action == settings_action:
            self.request_table_settings.emit()
        elif action == stats_test_action:
            self.request_statistical_test.emit()

    def copy_selection(self) -> None:
        """Copies the currently selected cells to the system clipboard as TSV"""
        selection_model: QItemSelectionModel | None = self.selectionModel()
        if selection_model is None or not selection_model.hasSelection():
            self.status_bar.log("No cells selected to copy", LogLevel.WARNING)
            return

        selected_indexes: list[QModelIndex] | list[Any] = selection_model.selectedIndexes()
        if not selected_indexes:
            return

        sorted_indexes: list[QModelIndex | QModelIndex] = sorted(selected_indexes,
                                                                 key=lambda idx: (idx.row(), idx.column()))
        rows_data: dict[int, list[str]] = {}
        for index in sorted_indexes:
            row = index.row()
            if row not in rows_data:
                rows_data[row] = []

            cell_data: Any | None = index.data(Qt.ItemDataRole.DisplayRole)
            rows_data[row].append(str(cell_data) if cell_data is not None else "")

        copied_lines = ["\t".join(rows_data[r]) for r in sorted(rows_data.keys())]
        copied_text = "\n".join(copied_lines)

        QApplication.clipboard().setText(copied_text)
        self.status_bar.log(f"Copied {len(selected_indexes)} cell(s) to clipboard", LogLevel.SUCCESS)

    def toggle_missing_values_highlight(self, enable: bool) -> None:
        """
        Toggles the highlighting of missing values on or off
        :param enable: True to highlight, False to clear
        """
        self._is_missing_highlighted = enable

        if self.data_handler.df is None or self.model() is None:
            return

        if not enable:
            if isinstance(self.model(), DataTableModel):
                self.model().set_highlighted_cells(set())
            self.status_bar.log("Cleared missing values highlight", LogLevel.INFO)
            return

        df: DataFrame = self.data_handler.df
        missing_cells: set[tuple[int, int]] = set()
        isna_mask: DataFrame = df.isna()

        for col_idx, col_name in enumerate(df.columns):
            col_data: Series | DataFrame | Any = df[col_name]
            is_missing: Series | DataFrame | Any = isna_mask[col_name].copy()

            if pd.api.types.is_object_dtype(col_data) or pd.api.types.is_string_dtype(col_data):
                is_empty_str: bool | Any = col_data.dropna().astype(str).str.strip() == ""
                is_missing = is_missing | is_empty_str.reindex(df.index, fill_value=False)

            missing_row_ilocs: ndarray[tuple[int, ...], dtype[signedinteger[_32Bit | _64Bit]]] = np.where(is_missing)[0]
            for row_idx in missing_row_ilocs:
                missing_cells.add((int(row_idx), col_idx))

        if isinstance(self.model(), DataTableModel):
            self.model().set_highlighted_cells(missing_cells)

        if not missing_cells:
            global_signals.request_toast(
                "No Missing Values",
                "There are no missing values found in this dataset",
                ToastLevel.INFO
            )
            self.status_bar.log("No missing values found in the dataset", LogLevel.INFO)
            self._is_missing_highlighted = False
        else:
            global_signals.request_toast(
                "Found Missing Values",
                f"Highlighted {len(missing_cells)} missing values",
                ToastLevel.SUCCESS
            )
            self.status_bar.log(f"Highlighted {len(missing_cells)} missing values", LogLevel.SUCCESS)

    def _on_horizontal_header_clicked(self, logical_index: int) -> None:
        """
        Handles the mouse clicks on the horizontal header for inserting columns
        :param logical_index: The logical index used by the model()
        """
        model: QAbstractItemModel | None = self.model()
        if not isinstance(model, DataTableModel) or not model.editable or model._data is None:
            return
        if logical_index != model._data.shape[1]:
            return
        model.insert_empty_column()

    def _on_vertical_header_clicked(self, logical_index: int) -> None:
        """
        Handles the mouse clicks on the vertical header to insert rows
        :param logical_index: The logical index used by the model()
        """
        model: QAbstractItemModel | None = self.model()
        if not isinstance(model, DataTableModel) or not model.editable or model._data is None:
            return
        if logical_index != model._data.shape[0]:
            return
        model.insert_empty_row()
