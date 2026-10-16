from typing import Tuple

from PyQt6.QtCore import QThreadPool, QTimer, pyqtSlot
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from icons import IconBuilder, IconType
from src.core.global_signals import ToastLevel, global_signals
from src.ui.workers import InternetConnectionCheckWorker

class GoogleSheetsExportDialog(QDialog):
    """Dialog for configuring and executing a Google Sheets export"""

    INTERNET_CONNECTION_ICON_SIZE: int = 24

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export to Google Sheets")
        self.setModal(True)
        self.resize(550, 250)
        self.threadpool = QThreadPool.globalInstance()
        self._init_ui()

        connection_duration: int = 5000
        self._connection_timer = QTimer(self)
        self._connection_timer.setInterval(connection_duration)
        self._connection_timer.timeout.connect(self._check_connection)
        self._connection_timer.start()
        self._check_connection()

    def _check_connection(self) -> None:
        """Checks the connection by starting InternetConnectionCheckWorker"""
        worker = InternetConnectionCheckWorker()
        worker.signals.finished.connect(self._on_connection_checked)
        self.threadpool.start(worker)

    @pyqtSlot(object)
    def _on_connection_checked(self, status: IconType) -> None:
        """Updates the connection icon based on ping status"""
        self.connection_status_label.setPixmap(
            IconBuilder.build(status).pixmap(self.INTERNET_CONNECTION_ICON_SIZE, self.INTERNET_CONNECTION_ICON_SIZE)
        )
        tooltip_map = {
            IconType.InternetHigh   : "Excellent internet connection",
            IconType.InternetMedium : "Good internet connection",
            IconType.InternetLow    : "Weak internet connection",
            IconType.InternetProblem: "Unstable internet connection",
            IconType.InternetOff    : "No internet connection",
            IconType.InternetNone   : "Checking connection..."
        }
        self.connection_status_label.setToolTip(tooltip_map.get(status, ""))

    def _init_ui(self) -> None:
        layout = QVBoxLayout()

        header_layout = QHBoxLayout()
        info_label = QLabel("Configure Google Sheets Export details:")
        info_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        header_layout.addWidget(info_label)

        header_layout.addStretch()

        self.connection_status_label = QLabel()
        self.connection_status_label.setToolTip("Checking internet connection...")
        self.connection_status_label.setPixmap(
            IconBuilder.build(IconType.InternetNone).pixmap(self.INTERNET_CONNECTION_ICON_SIZE, self.INTERNET_CONNECTION_ICON_SIZE)
        )
        header_layout.addWidget(self.connection_status_label)
        layout.addLayout(header_layout)

        form_layout = QFormLayout()

        # Credentials selection
        self.credentials_input = QLineEdit()
        self.credentials_input.setPlaceholderText("Select Service Account JSON file...")
        self.credentials_input.setReadOnly(True)

        browse_button = QPushButton("Browse...", parent=self)
        browse_button.clicked.connect(self._browse_credentials)

        cred_layout = QHBoxLayout()
        cred_layout.addWidget(self.credentials_input)
        cred_layout.addWidget(browse_button)

        form_layout.addRow(QLabel("Credentials (JSON):"), cred_layout)

        # Target Sheet ID
        self.sheet_id_input = QLineEdit()
        self.sheet_id_input.setPlaceholderText("Paste target Google Sheet ID here")
        self.sheet_id_input.setToolTip("The unique alphanumeric ID found in the Google Sheets URL.")
        form_layout.addRow(QLabel("Target Sheet ID:"), self.sheet_id_input)

        # Target Worksheet Name
        self.sheet_name_input = QLineEdit()
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

        export_button = QPushButton("Export Data", parent=self)
        export_button.setObjectName("MainActionButton")
        export_button.clicked.connect(self._validate_and_accept)
        button_layout.addWidget(export_button)

        cancel_button = QPushButton("Cancel", parent=self)
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
            global_signals.request_toast(
                "Validation Error", "Please selection a valid Service Account JSON credentials file", ToastLevel.WARNING
            )
            return
        if not self.sheet_id_input.text().strip():
            global_signals.request_toast(
                "Validation Error", "Please provide a target Google Sheet ID", ToastLevel.WARNING
            )
            return
        if not self.sheet_name_input.text().strip():
            global_signals.request_toast(
                "Validation Error", "Please provide a Worksheet Name", ToastLevel.WARNING
            )
            return
        self.accept()

    def get_inputs(self) -> Tuple[str, str, str]:
        return (
            self.credentials_input.text().strip(),
            self.sheet_id_input.text().strip(),
            self.sheet_name_input.text().strip()
        )
