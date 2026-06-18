import pandas as pd
from pathlib import Path

from PyQt6.QtWidgets import QAbstractItemView, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, \
    QTableView, \
    QTableWidgetItem, \
    QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from typing import Any

from core.global_signals import global_signals, ToastLevel

class SubsetTableModel(QAbstractTableModel):
    """
    Read-only self.table_view model for Subset data viewing
    """
    def __init__(self, data: pd.DataFrame, parent: Any = None) -> None:
        super().__init__(parent)
        self._data = data

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._data.columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            val = self._data.iat[index.row(), index.column()]
            return str(val) if not pd.isna(val) else ""
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._data.columns[section])
            if orientation == Qt.Orientation.Vertical:
                return str(self._data.index[section])
        return None


class SubsetDataViewer(QDialog):
    """View data in a subset"""

    def __init__(self, df, subset_name, parent=None):
        super().__init__(parent)
        self.df = df
        self.setWindowTitle(f"Subset Data: {subset_name}")
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # Info
        info = QLabel(f"Showing {len(df):,} rows x {len(df.columns)} columns")
        info.setObjectName("subset_info_label")
        layout.addWidget(info)

        # Table
        self.table_view = QTableView()
        self.table_view.horizontalHeader().setObjectName("MainDataHeader")
        self.table_view.verticalHeader().setObjectName("MainDataHeader")
        self.table_model = SubsetTableModel(self.df, self)
        self.table_view.setModel(self.table_model)
        self.table_view.setAlternatingRowColors(True)

        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        if len(self.df) <= 5000:
            self.table_view.resizeColumnsToContents()
        else:
            self.table_view.horizontalHeader().setDefaultSectionSize(120)
            self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        layout.addWidget(self.table_view)

        # Buttons
        btn_layout = QHBoxLayout()
        export_btn = QPushButton("Export this subset", parent=self)
        export_btn.clicked.connect(self.export_subset)

        close_btn = QPushButton("Close", parent=self)
        close_btn.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def export_subset(self):
        """Export the subset data into a file"""
        filepath_str, _ = QFileDialog.getSaveFileName(
            self,
            "Export Subset Data",
            "subset_data.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;JSON Files (*.json)"
        )
        if not filepath_str:
            return

        filepath = Path(filepath_str)
        try:
            if filepath.suffix == ".csv":
                self.df.to_csv(filepath, index=False)
            elif filepath.suffix == ".xlsx":
                self.df.to_excel(filepath, index=False)
            elif filepath.suffix == ".json":
                self.df.to_json(filepath)
            else:
                global_signals.request_toast("Export Failed", "Unsupported file format", ToastLevel.WARNING)
                return

            global_signals.request_toast(
                "Success",
                f"Subset exported to: {filepath.name}",
                ToastLevel.SUCCESS
            )

        except Exception as export_error:
            global_signals.request_toast(
                "Export error",
                f"Failed to export: {str(export_error)}",
                ToastLevel.ERROR
            )