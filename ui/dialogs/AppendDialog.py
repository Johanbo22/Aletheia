from pathlib import Path
from typing import Dict, Any, Optional
from zipfile import BadZipFile

import pandas as pd
from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QMessageBox, QDialogButtonBox, \
    QApplication, QLineEdit, QCheckBox, QPushButton

from core.data_handler import DataHandler
from ui.theme import ThemeColors
from ui.workers import FileReaderWorker


class AppendDialog(QDialog):
    """
    Dialog to configure and execute data concatenation/appending operations.
    Allows users to load an external file and append it to the current active DataFrame.
    """
    def __init__(self, data_handler: DataHandler, parent=None):
        super().__init__(parent)
        self.data_handler = data_handler
        self.other_df: Optional[pd.DataFrame] = None
        self.thread_pool = QThreadPool.globalInstance()
        
        self.setWindowTitle("Append / Concatenate Data")

        font_metrics = self.fontMetrics()
        calculated_min_width = font_metrics.horizontalAdvance("x") * 70
        self.setMinimumWidth(calculated_min_width)

        self.init_ui()
    
    def init_ui(self) -> None:
        """Initializes the layout and UI components for the Append Dialog."""
        layout = QVBoxLayout(self)
        
        info_label = QLabel(
            "Select a file to append to the current dataset. Rows from the selected "
            "file will be added to the bottom of your current active dataframe"
        )
        info_label.setWordWrap(True)
        info_label.setProperty("styleClass", "info_text")
        layout.addWidget(info_label)
        
        # File selection layout
        file_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("No file selected...")
        self.file_path_edit.setClearButtonEnabled(True)
        
        browse_btn = QPushButton("Browse", parent=self)
        browse_btn.setToolTip("Open a file explorer to find the file you want to append")
        browse_btn.clicked.connect(self.browse_file)
        
        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)

        layout.addSpacing(10)
        
        # Configuration options
        self.ignore_index_checkbox = QCheckBox("Ignore Index")
        self.ignore_index_checkbox.setChecked(True)
        self.ignore_index_checkbox.setToolTip("If checked, the resulting DataFrame will be re-indexed from 0 to n-1\nThis is default")
        layout.addWidget(self.ignore_index_checkbox)
        
        layout.addStretch()
        
        # Accept/reject buttons
        button_box = QDialogButtonBox(Qt.Orientation.Horizontal, self)

        cancel_btn = QPushButton("Cancel", parent=self)
        cancel_btn.clicked.connect(self.reject)

        self.append_btn = QPushButton("Append Data")
        self.append_btn.setObjectName("MainActionButton")
        self.append_btn.clicked.connect(self.accept_append)
        self.append_btn.setEnabled(False)

        button_box.addButton(self.append_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton(cancel_btn, QDialogButtonBox.ButtonRole.RejectRole)

        layout.addWidget(button_box)

    def browse_file(self) -> None:
        """Opens a file dialog, reads the selected file, and calls for validates schema alignment."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Append",
            "",
            "Supported Files (*.csv *.xlsx *.xls *.json *.txt);;All Files (*)"
        )
        if file_path:
            self._set_loading_state(True)

            worker = FileReaderWorker(self.data_handler, file_path)
            worker.signals.success.connect(self._on_read_success)
            worker.signals.error_object.connect(self._on_read_error)
            self.thread_pool.start(worker)

    def _set_loading_state(self, is_loading: bool) -> None:
        """Toggles UI and cursor to indicate loading"""
        if is_loading:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.file_path_edit.setText("Reading file... Please wait")
            self.append_btn.setEnabled(False)
        else:
            QApplication.restoreOverrideCursor()

    def _on_read_success(self, df: pd.DataFrame, file_path: str) -> None:
        """Slot triggered on successful parsing of file"""
        self._set_loading_state(False)
        self.other_df = df

        path_obj = Path(file_path)
        if len(str(path_obj)) > 50 and len(path_obj.parts) > 3:
            elided_path = f"{path_obj.parts[0]}.../{path_obj.parent.name}/{path_obj.name}"
            display_text = elided_path.replace('\\', '/')
        else:
            display_text = path_obj.as_posix()

        self.file_path_edit.setText(display_text)
        self.file_path_edit.setToolTip(path_obj.as_posix())
        self.file_path_edit.setCursorPosition(0)
        self.append_btn.setEnabled(True)

        if not self._validate_datasets():
            self.other_df = None
            self.file_path_edit.clear()
            self.append_btn.setEnabled(False)

    def _on_read_error(self, read_error: Exception) -> None:
        """Slot triggered when the background thread encounters an exception during parsing."""
        self._set_loading_state(False)
        self.other_df = None
        self.file_path_edit.clear()
        self.append_btn.setEnabled(False)

        if isinstance(read_error, FileNotFoundError):
            QMessageBox.critical(self, "Read Error", "The selected file could not be found. Please verify the file path.")
        elif isinstance(read_error, pd.errors.EmptyDataError):
            QMessageBox.critical(self, "Read Error", "The selected file contains no data or is entirely empty.")
        elif isinstance(read_error, pd.errors.ParserError):
            QMessageBox.critical(self, "Read Error", "Failed to parse the file. Please ensure it is a properly formatted tabular data file.")
        elif isinstance(read_error, (ValueError, BadZipFile)):
            QMessageBox.critical(self, "Read Error", "The file appears to be corrupted, encrypted, or is an invalid Excel/Zip archive.")
        else:
            QMessageBox.critical(self, "Read Error", f"An unexpected error occurred while reading the file:\n{str(read_error)}")

    def _validate_datasets(self) -> bool:
        """
        Validates column names and datatypes between the active DataFrame and the appended DataFrame

        Evaluates both missing/extra columns and intersecting columns for type mis match to warn user
        of a potential pandas casting (int -> object)

        @return: True if the datasets match or if the user approves of the changes.
                False if the user cancels
        """
        current_df = self.data_handler.df
        new_df = self.other_df

        if current_df is None or new_df is None:
            return False

        current_cols = set(current_df.columns)
        other_cols = set(new_df.columns)

        missing_cols = current_cols - other_cols
        extra_cols = other_cols - current_cols
        common_cols = current_cols.intersection(other_cols)

        dtype_mismatches = []
        for col in common_cols:
            if current_df[col].dtype != new_df[col].dtype:
                dtype_mismatches.append(f"'{col}' ({current_df[col].dtype} vs {new_df[col].dtype})")

        # Quick exit if no mismatch
        if not (missing_cols or extra_cols or dtype_mismatches):
            return True

        warning_msg = "Discrepancies found between the datasets.\n\n"
        if missing_cols:
            warning_msg += f"Missing in new file: {', '.join(list(missing_cols)[:3])}{'...' if len(missing_cols) > 3 else ''}\n"
        if extra_cols:
            warning_msg += f"Extra in new file: {', '.join(list(extra_cols)[:3])}{'...' if len(extra_cols) > 3 else ''}\n"
        if dtype_mismatches:
            warning_msg += f"Data Type mismatches: {', '.join(dtype_mismatches[:3])}{'...' if len(dtype_mismatches) > 3 else ''}\n"

        warning_msg += "\nProceeding may result in 'NaN' values or column type casting (e.g., to 'object').\nDo you want to continue?"

        reply = QMessageBox.warning(
            self, "Dataset Mismatch Warning", warning_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def accept_append(self) -> None:
        """Validates state before accepting the dialog."""
        if self.other_df is not None:
            self.accept()
    
    def get_config(self) -> Dict[str, Any]:
        """Returns the configuration required to execute the append operation."""
        return {
            "other_df": self.other_df,
            "ignore_index": self.ignore_index_checkbox.isChecked()
        }