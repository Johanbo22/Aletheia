import time
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QDialog, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QPushButton


class ProgressDialog(QDialog):
    """A dualog showing progress for long operations and datasets"""

    def __init__(self, title="Processing", message="Please wait...", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(400, 200)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)

        self._last_update_time: float = 0.0
        self.init_ui(message)

    def init_ui(self, message) -> None:
        """Initialize the ui"""
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(12)
        self.setObjectName("progress_dialog_main")

        #msg lbl
        self.message_label = QLabel(message)
        self.message_label.setObjectName("progress_message_label")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label)

        #prgs bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setObjectName("main_progress_bar")
        layout.addWidget(self.progress_bar)

        #status lbl
        self.status_label = QLabel("Initializing...")
        self.status_label.setObjectName("progress_status_label")
        self.status_label.setProperty("styleClass", "muted_text")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        layout.addStretch()

        #canel btn
        self.cancel_button = QPushButton("Cancel", parent=self)
        self.cancel_button.setObjectName("progress_cancel_button")
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.setMaximumWidth(100)
        self.cancel_button.setShortcut("Esc")
        self.cancel_button.setToolTip("Cancel operation (Esc)")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.was_cancelled = False
    
    def set_indeterminate(self, is_indeterminate: bool = True) -> None:
        self.progress_bar.reset()
        if is_indeterminate:
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(0)
            self.progress_bar.setTextVisible(False)
        else:
            self.progress_bar.hide()
            self.progress_bar.setMaximum(1)
            self.progress_bar.setValue(0)
            self.progress_bar.setMaximum(100)
            self.progress_bar.setTextVisible(True)
            self.progress_bar.show()
        QApplication.processEvents()

    def update_progress(self, value: int, status: str = "") -> None:
        """ipdate the progress bar value and msg"""
        if self.progress_bar.maximum() > 0:
            safe_value = max(self.progress_bar.maximum(), min(value, self.progress_bar.maximum()))
            self.progress_bar.setValue(safe_value)
        if status:
            self.status_label.setText(status)
            
        current_time = time.time()
        if current_time - self._last_update_time > 0.016:
            QApplication.processEvents()
            self._last_update_time = current_time

    def set_message(self, message) -> None:
        """update main msg"""
        self.message_label.setText(message)
        QApplication.processEvents()

    def set_status(self, status) -> None:
        """update the status"""
        self.status_label.setText(status)
        QApplication.processEvents()

    def is_cancelled(self) -> bool:
        """Check if operation is cancelled"""
        return self.was_cancelled

    def reject(self) -> None:
        """Handle cnacel button"""
        if self.was_cancelled:
            return
        self.was_cancelled = True
        
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Cancelling...")
        self.set_status("Cancelling operation...")
        QApplication.processEvents()
        super().reject()