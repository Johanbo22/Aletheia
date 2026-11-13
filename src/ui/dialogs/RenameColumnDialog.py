import keyword
from enum import Enum, auto
from typing import List, Optional, Tuple

from PyQt6.QtCore import QAbstractAnimation, QPropertyAnimation, Qt
from PyQt6.QtWidgets import QDialog, QFormLayout, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QLineEdit, QPushButton, \
    QVBoxLayout

from src.core.global_signals import ToastLevel, global_signals

class ValidationState(Enum):
    Valid = auto()
    Empty = auto()
    Unchanged = auto()
    AlreadyExists = auto()
    Keyword = auto()
    InvalidCharacter = auto()

class RenameColumnDialog(QDialog):
    """
    Dialog for renaming a column
    Also serves as a parent to the RenameProjectDialog
    """

    def __init__(self, column_name: str, existing_columns: Optional[List[str]] = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rename Column")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setModal(True)
        self.resize(420, 180)

        self.column_name: str = column_name
        self.existing_columns: List[str] = existing_columns if existing_columns else []
        self.case_sensitive: bool = True
        self.new_name_input: Optional[QLineEdit] = None
        self.error_label: Optional[QLabel] = None
        self.rename_button: Optional[QPushButton] = None
        self.error_animation: Optional[QPropertyAnimation] = None

        self.init_ui()

    def init_ui(self):
        """Initialize dialog UI"""
        layout = QVBoxLayout()
        layout.setObjectName("rename_dialog_main_layout")

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Old name display
        current_name_label = QLabel("Current Name:")
        current_name_label.setObjectName("current_name_label")

        old_name_display = QLineEdit()
        old_name_display.setObjectName("current_name_display")
        old_name_display.setText(self.column_name)
        old_name_display.setReadOnly(True)
        form_layout.addRow(current_name_label, old_name_display)

        # New name input
        new_name_label = QLabel("New Name:")
        new_name_label.setObjectName("new_name_label")

        self.new_name_input = QLineEdit()
        self.new_name_input.setObjectName("new_name_input")
        self.new_name_input.setPlaceholderText(f"Enter new name for '{self.column_name}'")
        self.new_name_input.setMinimumWidth(200)
        self.new_name_input.textChanged.connect(self.on_name_text_changed)
        form_layout.addRow(new_name_label, self.new_name_input)

        layout.addLayout(form_layout)

        # Error display label
        self.error_label = QLabel("")
        self.error_label.setObjectName("rename_error_label")

        opacity_effect = QGraphicsOpacityEffect(self.error_label)
        start_opacity: float = 0.0
        opacity_effect.setOpacity(start_opacity)
        self.error_label.setGraphicsEffect(opacity_effect)

        self.error_animation = QPropertyAnimation(opacity_effect, b"opacity")
        animation_duration: int = 200
        end_opacity: float = 1.0
        self.error_animation.setDuration(animation_duration)
        self.error_animation.setStartValue(start_opacity)
        self.error_animation.setEndValue(end_opacity)

        layout.addWidget(self.error_label)
        layout.addSpacing(10)

        # Buttons
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

        self.new_name_input.selectAll()
        self.new_name_input.setFocus()
        self.new_name_input.returnPressed.connect(self.rename_button.click)

    def validate_name(self, new_name: str) -> Tuple[ValidationState, str]:
        if not new_name:
            return ValidationState.Empty, "New column name cannot be empty"
        if self._same_as_current(new_name):
            return ValidationState.Unchanged, "New name must be different from current name"
        if self._already_exists(new_name):
            return ValidationState.AlreadyExists, f"Column '{new_name}' already exists in the dataset"
        if keyword.iskeyword(new_name):
            return ValidationState.Keyword, f"'{new_name}' is a reserved Python keyword"
        if "`" in new_name:
            return ValidationState.InvalidCharacter, "Column names cannot contain backticks (`)"

        return ValidationState.Valid, ""

    def _same_as_current(self, new_name: str) -> bool:
        """Check whether the candidate name equals the current one"""
        if self.case_sensitive:
            return new_name == self.column_name
        return new_name.lower() == self.column_name.lower()

    def _already_exists(self, new_name: str) -> bool:
        """Check whether the candidate name collides with an existing name"""
        if self.case_sensitive:
            return new_name in self.existing_columns
        return new_name.lower() in [name.lower() for name in self.existing_columns]

    def _animate_error(self, show: bool, message: str = "") -> None:
        """Fade the error label in or out based on the validation state"""
        if not self.error_label or not self.error_animation:
            return

        if show:
            self.error_label.setText(message)
            self.error_animation.setDirection(QAbstractAnimation.Direction.Forward)
        else:
            self.error_animation.setDirection(QAbstractAnimation.Direction.Backward)

        if self.error_animation.state() != QAbstractAnimation.State.Running:
            self.error_animation.start()

    def on_name_text_changed(self, text: str) -> None:
        if not self.error_label or not self.rename_button or not self.new_name_input:
            return

        clean_text: str = text.strip()
        state, error_message = self.validate_name(clean_text)

        if state == ValidationState.Valid:
            self._animate_error(False)
            self.rename_button.setEnabled(True)
            self.new_name_input.setProperty("inputState", "valid")
        else:
            self._animate_error(True, error_message)
            self.rename_button.setEnabled(False)
            self.new_name_input.setProperty("inputState", "error")

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
        """Return the new column name"""
        return self.new_name_input.text().strip()
