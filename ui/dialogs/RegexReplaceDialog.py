from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QFormLayout, QMenu, QToolButton
from PyQt6.QtCore import Qt, QTimer
from typing import Optional
import re

from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton
from ui.widgets.ControlElements import DataPlotStudioComboBox, DataPlotStudioLineEdit, DataPlotStudioCheckBox, DataPlotStudioMenu

class RegexReplaceDialog(QDialog):
    """
    Dialog for performing regex-based text replacements on a specific column.
    """
    def __init__(self, columns: list[str], parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.setWindowTitle("Regex Replace")
        self.setMinimumWidth(700)
        self.setObjectName("RegexReplaceDialog")
        self.columns: list[str] = columns

        # Timer for performance
        preview_timer_ms = 300
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(preview_timer_ms)
        self.preview_timer.timeout.connect(self._execute_live_preview)

        self.init_ui()

    def init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Target column
        self.column_combo = DataPlotStudioComboBox()
        self.column_combo.addItems(self.columns)
        self.column_combo.setToolTip("Select the text column for regex replacement")
        self.column_combo.setObjectName("ColumnComboBox")
        form_layout.addRow("Select Column:", self.column_combo)

        # Regex pattern
        pattern_layout = QHBoxLayout()
        pattern_layout.setContentsMargins(0, 0, 0, 0)
        pattern_layout.setSpacing(5)

        self.pattern_input = DataPlotStudioLineEdit()
        self.pattern_input.setPlaceholderText("e.g., ^[A-Za-z]+ or \\d+")
        self.pattern_input.setToolTip("Enter the Regular Expression pattern to match")
        self.pattern_input.setObjectName("RegexPatternInput")
        pattern_layout.addWidget(self.pattern_input)

        self.preset_btn = QToolButton()
        self.preset_btn.setText("▾")
        self.preset_btn.setObjectName("RegexPresetButton")
        self.preset_btn.setToolTip("Insert common regex patterns")

        preset_menu = DataPlotStudioMenu(self)
        preset_menu.setObjectName("RegexPresetMenu")
        preset_menu.addAction(r"Numbers Only (\d+)", lambda: self.pattern_input.setText(r"\d+"))
        preset_menu.addAction(r"Letters Only ([A-Za-z]+)", lambda: self.pattern_input.setText(r"[A-Za-z]+"))
        preset_menu.addAction(r"Whitespace (\s+)", lambda: self.pattern_input.setText(r"\s+"))
        preset_menu.addAction(r"Email Address", lambda: self.pattern_input.setText(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"))
        preset_menu.addAction(r"Special Characters ([^A-Za-z0-9\s]+)", lambda: self.pattern_input.setText(r"[^A-Za-z0-9\s]+"))

        self.preset_btn.setMenu(preset_menu)
        self.preset_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        pattern_layout.addWidget(self.preset_btn)

        form_layout.addRow("Regex Pattern", pattern_layout)

        # validation Label
        self.validation_label = QLabel()
        self.validation_label.setObjectName("RegexValidationLabel")
        self.validation_label.hide()
        form_layout.addRow("", self.validation_label)

        # Replacement label
        self.replacement_input = DataPlotStudioLineEdit()
        self.replacement_input.setPlaceholderText("(Leave empty to delete matching text)")
        self.replacement_input.setToolTip("Text to replace the matches with. Leave blank to strip matches")
        self.replacement_input.setObjectName("ReplacementInput")
        self.replacement_input.textChanged.connect(lambda: self.update_live_preview())
        form_layout.addRow("Replacement Text:", self.replacement_input)

        # Options
        self.ignore_case_checkbox = DataPlotStudioCheckBox("Ignore Case")
        self.ignore_case_checkbox.setObjectName("IgnoreCaseCheckBox")
        self.ignore_case_checkbox.setToolTip("Perform case-insensitive matching")
        self.ignore_case_checkbox.stateChanged.connect(lambda: self.update_live_preview())
        form_layout.addRow("", self.ignore_case_checkbox)

        # Preview section
        form_layout.addRow(QLabel(""))

        self.test_string_input = DataPlotStudioLineEdit()
        self.test_string_input.setPlaceholderText("Enter a sample string to test...")
        self.test_string_input.setObjectName("TestStringInput")
        self.test_string_input.textChanged.connect(lambda: self.update_live_preview())
        form_layout.addRow("Test String:", self.test_string_input)

        self.preview_label = QLabel("<i>Result will appear here...</i>")
        self.preview_label.setObjectName("RegexPreviewLabel")
        self.preview_label.setProperty("previewState", "empty")
        self.preview_label.setWordWrap(True)
        # Text interaction so the result can be copied
        self.preview_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form_layout.addRow("Preview:", self.preview_label)

        main_layout.addLayout(form_layout)
        main_layout.addStretch()

        # Actions
        btn_layout = QHBoxLayout()
        self.btn_ok = DataPlotStudioButton("Apply Regex", parent=self, base_color_hex=ThemeColors.MainColor, text_color_hex="white")
        self.btn_ok.setObjectName("ApplyRegexButton")
        self.btn_ok.clicked.connect(self.validate_and_accept)
        self.btn_ok.setEnabled(False)

        self.pattern_input.textChanged.connect(lambda: self.update_live_preview())

        self.btn_cancel = DataPlotStudioButton("Cancel", parent=self)
        self.btn_cancel.setObjectName("CancelButton")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)

    def update_live_preview(self) -> None:
        """
        Triggered on keystroke. Restarts the timer to prevent
        UI freezing from rapid regex recompilation
        """
        self.preview_timer.stop()
        self.preview_timer.start()

    def _execute_live_preview(self) -> None:
        """
        Validate the regex pattern and generate a live preview
        of the replacement operation using a user's test string
        """
        pattern: str = self.pattern_input.text()
        replacement: str = self.replacement_input.text()
        test_string: str = self.test_string_input.text()

        if not pattern.strip():
            self.validation_label.hide()
            self.preview_label.setText("<i>Result will appear here...</i>")
            self.btn_ok.setEnabled(False)
            return

        flags = re.IGNORECASE if self.ignore_case_checkbox.isChecked() else 0
        try:
            compiled_regex = re.compile(pattern, flags)
            result: str = compiled_regex.sub(replacement, test_string)

            self.validation_label.hide()
            self.btn_ok.setEnabled(True)

            if test_string:
                safe_result = result.replace("<", "&lt;").replace(">", "&gt;")
                self.preview_label.setText(f"<b>{safe_result}</b>")
                self.preview_label.setProperty("previewState", "success")
            else:
                self.preview_label.setText("<i>Enter test string to see preview...</i>")
                self.preview_label.setProperty("previewState", "empty")

            self.preview_label.style().unpolish(self.preview_label)
            self.preview_label.style().polish(self.preview_label)

        except re.error as error:
            self.validation_label.setText(f"Invalid Regex/Replacement: {error.msg}")
            self.validation_label.show()
            self.preview_label.setText("<i>Error in pattern or replacement</i>")
            self.btn_ok.setEnabled(False)

            self.preview_label.setProperty("previewState", "error")
            self.preview_label.style().unpolish(self.preview_label)
            self.preview_label.style().polish(self.preview_label)

    def validate_and_accept(self) -> None:
        """Validate inputs before accepting the dialog."""
        pattern: str = self.pattern_input.text().strip()
        if not pattern:
            QMessageBox.warning(self, "Validation Error", "Regex Pattern cannot be empty")
            return
        try:
            re.compile(pattern)
        except re.error:
            QMessageBox.warning(self, "Validation Error", "The provided Regular Expression is invalid")
            return

    def get_parameters(self) -> tuple[str, str, str]:
        """
        Retrieve the configured regex replace parameters.
        Returns:
            tuple: (column_name, regex_pattern, replacement_text)
        """
        column: str = self.column_combo.currentText()
        pattern: str = self.pattern_input.text()
        replacement: str = self.replacement_input.text()

        if self.ignore_case_checkbox.isChecked() and not pattern.startswith("(?i)"):
            pattern = f"(?i){pattern}"
        
        return column, pattern, replacement