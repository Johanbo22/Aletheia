from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox
from typing import Optional

from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton
from ui.widgets.ControlElements import DataPlotStudioComboBox, DataPlotStudioLineEdit

class RegexReplaceDialog(QDialog):
    """
    Dialog for performing regex-based text replacements on a specific column.
    """
    def __init__(self, columns: list[str], parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.setWindowTitle("Regex Replace")
        self.setMinimumWidth(350)
        self.columns: list[str] = columns
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Target Column
        layout.addWidget(QLabel("Select Column:"))
        self.column_combo = DataPlotStudioComboBox()
        self.column_combo.addItems(self.columns)
        self.column_combo.setToolTip("Select the text column for regex replacement.")
        layout.addWidget(self.column_combo)

        # Regex Pattern
        layout.addWidget(QLabel("Regex Pattern:"))
        self.pattern_input = DataPlotStudioLineEdit()
        self.pattern_input.setPlaceholderText("e.g., ^[A-Za-z]+ or \\d+")
        self.pattern_input.setToolTip("Enter the Regular Expression pattern to match.")
        layout.addWidget(self.pattern_input)

        # Replacement Text
        layout.addWidget(QLabel("Replacement Text:"))
        self.replacement_input = DataPlotStudioLineEdit()
        self.replacement_input.setPlaceholderText("(Leave empty to delete matching text)")
        self.replacement_input.setToolTip("Text to replace the matches with. Leave blank to strip matches.")
        layout.addWidget(self.replacement_input)

        layout.addSpacing(10)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_ok = DataPlotStudioButton("Apply Regex", parent=self, base_color_hex=ThemeColors.MainColor)
        self.btn_ok.clicked.connect(self.validate_and_accept)
        
        self.btn_cancel = DataPlotStudioButton("Cancel", parent=self)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
    
    def validate_and_accept(self) -> None:
        """Validate inputs before accepting the dialog."""
        if not self.pattern_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Regex Pattern cannot be empty.")
            return
            
        self.accept()

    def get_parameters(self) -> tuple[str, str, str]:
        """
        Retrieve the configured regex replace parameters.
        Returns:
            tuple: (column_name, regex_pattern, replacement_text)
        """
        column: str = self.column_combo.currentText()
        pattern: str = self.pattern_input.text()
        replacement: str = self.replacement_input.text()
        
        return column, pattern, replacement