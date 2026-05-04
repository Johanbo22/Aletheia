import keyword
from enum import Enum, auto
from typing import Optional, List, Tuple
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout
from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton
from ui.widgets.ControlElements import DataPlotStudioLineEdit


class ValidationState(Enum):
    Valid = auto()
    Empty = auto()
    Unchanged = auto()
    AlreadyExists = auto()
    Keyword = auto()
    InvalidCharacter = auto()

class RenameColumnDialog(QDialog):
    """Dialog for renaming a column"""

    def __init__(self, column_name: str, existing_columns: Optional[List[str]] = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rename Column")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setModal(True)
        self.resize(400, 150)

        self.column_name: str = column_name
        self.existing_columns: List[str] = existing_columns if existing_columns else []
        self.new_name_input: Optional[DataPlotStudioLineEdit] = None
        self.error_label: Optional[QLabel] = None
        self.rename_button: Optional[DataPlotStudioButton] = None
        self.init_ui()

    def init_ui(self):
        """Initialize dialog UI"""
        layout = QVBoxLayout()
        layout.setObjectName("rename_dialog_main_layout")
        
        # Old name display
        old_name_layout = QHBoxLayout()
        current_name_label = QLabel("Current Name:")
        current_name_label.setObjectName("current_name_label")
        old_name_layout.addWidget(current_name_label)
        
        old_name_display = DataPlotStudioLineEdit()
        old_name_display.setObjectName("current_name_display")
        old_name_display.setText(self.column_name)
        old_name_display.setReadOnly(True)
        old_name_layout.addWidget(old_name_display)
        layout.addLayout(old_name_layout)
        
        # New name input
        new_name_layout = QHBoxLayout()
        new_name_label = QLabel("New Name:")
        new_name_label.setObjectName("new_name_label")
        new_name_layout.addWidget(new_name_label)
        
        self.new_name_input = DataPlotStudioLineEdit()
        self.new_name_input.setObjectName("new_name_input")
        self.new_name_input.setPlaceholderText(f"Enter new name for '{self.column_name}'")
        self.new_name_input.setMinimumWidth(200)
        self.new_name_input.textChanged.connect(self.on_name_text_changed)
        new_name_layout.addWidget(self.new_name_input)
        layout.addLayout(new_name_layout)
        
        # Error display label
        self.error_label = QLabel("")
        self.error_label.setObjectName("rename_error_label")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        
        layout.addSpacing(20)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.rename_button = DataPlotStudioButton("Rename", parent=self, base_color_hex=ThemeColors.MainColor, text_color_hex="white")
        self.rename_button.setObjectName("rename_submit_button")
        self.rename_button.setMinimumWidth(100)
        self.rename_button.setEnabled(False)
        self.rename_button.setDefault(True)
        self.rename_button.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(self.rename_button)
        
        cancel_button = DataPlotStudioButton("Cancel", parent=self)
        cancel_button.setObjectName("rename_cancel_button")
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        self.new_name_input.setFocus()
        self.new_name_input.returnPressed.connect(self.rename_button.click)

    def validate_name(self, new_name: str) -> Tuple[ValidationState, str]:
        if not new_name:
            return ValidationState.Empty, "New column name cannot be empty"
        if new_name == self.column_name:
            return ValidationState.Unchanged, "New name must be different from current name"
        if new_name in self.existing_columns:
            return ValidationState.AlreadyExists, f"Column '{new_name}' already exists in the dataset"
        if keyword.iskeyword(new_name):
            return ValidationState.Keyword, f"'{new_name}' is a reserved Python keyword"
        if "`" in new_name:
            return ValidationState.InvalidCharacter, "Column names cannot contain backticks (`)"
        
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
            self.new_name_input.setProperty("inputState", "error")
        
        self.new_name_input.style().unpolish(self.new_name_input)
        self.new_name_input.style().polish(self.new_name_input)
        
    def validate_and_accept(self) -> None:
        if not self.new_name_input:
            return
        
        new_name: str = self.new_name_input.text().strip()
        state, error_message = self.validate_name(new_name)
        
        if state != ValidationState.Valid:
            QMessageBox.warning(self, "Validation Error", error_message)
            return
        self.accept()

    def get_new_name(self) -> str:
        """Return the new column name"""
        return self.new_name_input.text().strip()