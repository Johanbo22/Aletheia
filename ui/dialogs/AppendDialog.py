import pandas as pd
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt
from core.data_handler import DataHandler
from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton
from ui.widgets.ControlElements import DataPlotStudioCheckBox, DataPlotStudioLineEdit

class AppendDialog(QDialog):
    """
    Dialog to configure and execute data concatenation/appending operations.
    Allows users to load an external file and append it to the current active DataFrame.
    """
    def __init__(self, data_handler: DataHandler, parent=None):
        super().__init__(parent)
        self.data_handler = data_handler
        self.other_df: Optional[pd.DataFrame] = None
        
        self.setWindowTitle("Append / Concatenate Data")
        self.setMinimumWidth(550)
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
        self.file_path_edit = DataPlotStudioLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("No file selected...")
        
        browse_btn = DataPlotStudioButton("Browse", parent=self)
        browse_btn.setToolTip("Open a file explorer to find the file you want to append")
        browse_btn.clicked.connect(self.browse_file)
        
        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)

        layout.addSpacing(10)
        
        # Configuration options
        self.ignore_index_checkbox = DataPlotStudioCheckBox("Ignore Index")
        self.ignore_index_checkbox.setChecked(True)
        self.ignore_index_checkbox.setToolTip("If checked, the resulting DataFrame will be re-indexed from 0 to n-1\nThis is default")
        layout.addWidget(self.ignore_index_checkbox)
        
        layout.addStretch()
        
        # Accept/reject buttons
        btn_layout = QHBoxLayout()
        cancel_btn = DataPlotStudioButton("Cancel", parent=self)
        cancel_btn.clicked.connect(self.reject)
        
        self.append_btn = DataPlotStudioButton("Append Data", parent=self, base_color_hex=ThemeColors.MainColor)
        self.append_btn.clicked.connect(self.accept_append)
        self.append_btn.setEnabled(False)
        
        btn_layout.addWidget(self.append_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def browse_file(self) -> None:
        """Opens a file dialog, reads the selected file, and validates schema alignment."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Append",
            "",
            "Supported Files (*.csv *.xlsx *.xls *.json *.txt);;All Files (*)"
        )
        if file_path:
            try:
                # Read without modifying the active datahandler state
                self.other_df = self.data_handler.read_file(file_path)
                self.file_path_edit.setText(file_path)
                self.append_btn.setEnabled(True)
                
                # Schema validation and warning
                current_cols = set(self.data_handler.df.columns)
                other_cols = set(self.other_df.columns)
                
                missing_cols = current_cols - other_cols
                extra_cols = other_cols - current_cols
                if missing_cols or extra_cols:
                    warning_msg = "Schema mismatch between the datasets.\n\n"
                    if missing_cols:
                        warning_msg += f"Missing in new file: {', '.join(list(missing_cols)[:3])}{'...' if len(missing_cols) > 3 else ''}\n"
                    if extra_cols:
                        warning_msg += f"Extra in new file: {', '.join(list(extra_cols)[:3])}{'...' if len(extra_cols) > 3 else ''}\n"
                    
                    warning_msg += "\nUnmatched columns will be populated with 'NaN'\nProceed?"
                    reply = QMessageBox.warning(
                        self, "Schema Mismatch", warning_msg,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        self.other_df = None
                        self.file_path_edit.clear()
                        self.append_btn.setEnabled(False)
            except Exception as ReadError:
                QMessageBox.critical(self, "Read Error", f"Failed to read file:\n{str(ReadError)}")

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