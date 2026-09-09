import re
from enum import Enum, auto
from typing import List, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from src.core.global_signals import ToastLevel, global_signals

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}

class ValidationState(Enum):
    Valid = auto()
    Empty = auto()
    Unchanged = auto()
    AlreadyExists = auto()
    InvalidCharacter = auto()
    ReservedName = auto()

class RenameProjectDialog(QDialog):
    """Dialog for renaming a project on disk"""

    def __init__(self, current_name: str, existing_names: Optional[List[str]] = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rename Project")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setModal(True)
        self.resize(420, 150)

        self.current_name: str = current_name
        self.existing_names: List[str] = [name.lower() for name in (existing_names or [])]
        self.new_name_input: Optional[QLineEdit] = None
        self.error_label: Optional[QLabel] = None
        self.rename_button: Optional[QPushButton] = None
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setObjectName("rename_dialog_main_layout")

        old_name_layout = QHBoxLayout()
        current_name_label = QLabel("Current Name:")
        current_name_label.setObjectName("current_name_label")
        old_name_layout.addWidget(current_name_label)

        old_name_display = QLineEdit()
        old_name_display.setObjectName("current_name_display")
        old_name_display.setText(self.current_name)
        old_name_display.setReadOnly(True)
        old_name_layout.addWidget(old_name_display)
        layout.addLayout(old_name_layout)

        new_name_layout = QHBoxLayout()
        new_name_label = QLabel("New Name:")
        new_name_label.setObjectName("new_name_label")
        new_name_layout.addWidget(new_name_label)

        self.new_name_input = QLineEdit()
        self.new_name_input.setObjectName("new_name_input")
        self.new_name_input.setPlaceholderText(f"Enter new name for '{self.current_name}'")
        self.new_name_input.setMinimumWidth(220)
        self.new_name_input.setText(self.current_name)
        self.new_name_input.selectAll()
        self.new_name_input.textChanged.connect(self.on_name_text_changed)
        new_name_layout.addWidget(self.new_name_input)
        layout.addLayout(new_name_layout)

        self.error_label = QLabel("")
        self.error_label.setObjectName("rename_error_label")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        layout.addSpacing(20)

        button_layout = QHBoxLayout()

        self.rename_button = QPushButton("Rename")
        self.rename_button.setObjectName("MainActonButton")
        self.rename_button.setMinimumWidth(100)
        self.rename_button.setEnabled(False)
        self.rename_button.setDefault(True)
        self.rename_button.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(self.rename_button)

        cancel_button = QPushButton("Cancel", parent=self)
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        self.new_name_input.setFocus()
        self.new_name_input.returnPressed.connect(self.rename_button.click)

    def validate_name(self, new_name: str) -> Tuple[ValidationState, str]:
        if not new_name:
            return ValidationState.Empty, "New project name cannot be empty"
        if new_name == self.current_name:
            return ValidationState.Unchanged, "New name must be different from current name"
        if new_name.lower() in self.existing_names:
            return ValidationState.AlreadyExists, f"A project named '{new_name}' already exists in this folder"
        if new_name.upper() in _RESERVED_NAMES or new_name.rstrip(".") != new_name or new_name.rstrip() != new_name:
            return ValidationState.ReservedName, f"'{new_name}' is not a valid file name"
        if _INVALID_FILENAME_CHARS.search(new_name):
            return ValidationState.InvalidCharacter, r'Project names cannot contain \ / : * ? " < > |'

        return ValidationState.Valid, ""

    def on_name_text_changed(self, text: str) -> None:
        if not self.error_label or not self.rename_button or not self.new_name_input:
            return

        clean_text: str = text.strip()
        state, error_message = self.validate_name(clean_text)

        if state == ValidationState.Valid:
            self.error_label.setVisible(False)
            self.rename_button.setEnabled(True)
            self.new_name_input.setProperty("inputState", "valid")
        else:
            self.error_label.setText(error_message)
            self.error_label.setVisible(True)
            self.rename_button.setEnabled(False)
            self.new_name_input.setProperty("inputState", "invalid")

        self.new_name_input.style().unpolish(self.new_name_input)
        self.new_name_input.style().polish(self.new_name_input)

    def validate_and_accept(self) -> None:
        if not self.new_name_input:
            return

        new_name: str = self.new_name_input.text().strip()
        state, error_message = self.validate_name(new_name)

        if state != ValidationState.Valid:
            global_signals.request_toast(
                "Validation Error", error_message, ToastLevel.ERROR
            )
            return
        self.accept()

    def get_new_name(self) -> str:
        """Return the new project name"""
        return self.new_name_input.text().strip()
