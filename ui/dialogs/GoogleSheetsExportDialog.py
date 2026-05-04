from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QMessageBox, QFileDialog
from PyQt6.QtGui import QFont
from typing import Tuple

from ui.widgets import DataPlotStudioButton
from ui.widgets.ControlElements import DataPlotStudioLineEdit

class GoogleSheetsExportDialog(QDialog):
    """Dialog for configuring and executing a Google Sheets export"""
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export to Google Sheets")
        self.setModal(True)
        self.resize(550, 250)
        self._init_ui()
        
    def _init_ui(self) -> None:
        layout = QVBoxLayout()
        
        info_label = QLabel("Configure Google Sheets Export details:")
        info_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        layout.addWidget(info_label)
        
        form_layout = QFormLayout()
        
        # Credentials selecstion
        self.credentials_input = DataPlotStudioLineEdit()
        self.credentials_input.setPlaceholderText("Select Service Account JSON file...")
        self.credentials_input.setReadOnly(True)
        
        browse_button = DataPlotStudioButton("Browse...", parent=self)
        browse_button.clicked.connect(self._browse_credentials)
        
        cred_layout = QHBoxLayout()
        cred_layout.addWidget(self.credentials_input)
        cred_layout.addWidget(browse_button)
        
        form_layout.addRow(QLabel("Credentials (JSON):"), cred_layout)
        
        # Target Sheet ID
        self.sheet_id_input = DataPlotStudioLineEdit()
        self.sheet_id_input.setPlaceholderText("Paste target Google Sheet ID here")
        self.sheet_id_input.setToolTip("The unique alphanumeric ID found in the Google Sheets URL.")
        form_layout.addRow(QLabel("Target Sheet ID:"), self.sheet_id_input)

        # Target Worksheet Name
        self.sheet_name_input = DataPlotStudioLineEdit()
        self.sheet_name_input.setText("Sheet1")
        self.sheet_name_input.setPlaceholderText("e.g., ExportedData")
        self.sheet_name_input.setToolTip("Name of the specific tab. It will be created if it does not exist.")
        form_layout.addRow(QLabel("Worksheet Name:"), self.sheet_name_input)

        layout.addLayout(form_layout)
        
        help_text = QLabel(
            "Note: You must use a Google Cloud Service Account. Ensure you have shared the target Google Sheet "
            "with the Service Account's email address (e.g., service-account@project.iam.gserviceaccount.com) "
            "and granted it 'Editor' permissions."
        )
        help_text.setWordWrap(True)
        help_text.setProperty("styleClass", "help_box")
        layout.addWidget(help_text)

        layout.addSpacing(15)
        # Dialog Buttons
        button_layout = QHBoxLayout()
        
        export_button = DataPlotStudioButton("Export Data", parent=self)
        export_button.clicked.connect(self._validate_and_accept)
        button_layout.addWidget(export_button)

        cancel_button = DataPlotStudioButton("Cancel", parent=self)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _browse_credentials(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Credentials JSON", "", "JSON files (*.json)")
        if filepath:
            self.credentials_input.setText(filepath)
    
    def _validate_and_accept(self) -> None:
        if not self.credentials_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please select a valid Service Account JSON credentials file.")
            return
        if not self.sheet_id_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please provide a target Google Sheet ID.")
            return
        if not self.sheet_name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please provide a Worksheet Name.")
            return
        self.accept()
    
    def get_inputs(self) -> Tuple[str, str, str]:
        return (
            self.credentials_input.text().strip(),
            self.sheet_id_input.text().strip(),
            self.sheet_name_input.text().strip()
        )