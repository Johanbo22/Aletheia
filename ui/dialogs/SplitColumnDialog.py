from PyQt6.QtWidgets import QSpinBox, QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QMessageBox, QFormLayout, QGraphicsOpacityEffect, QComboBox, QPushButton
from PyQt6.QtCore import Qt, pyqtSlot, QTimer, QPropertyAnimation, QEasingCurve
from typing import Optional
from enum import Enum
from ui.theme import ThemeColors

class DelimiterPreset(Enum):
    SPACE = ("Space", " ")
    COMMA = ("Comma", ",")
    SEMICOLON = ("Semicolon", ";")
    TAB = ("Tab", "\t")
    CUSTOM = ("Custom...", "")

    @property
    def display_name(self) -> str:
        return self.value[0]

    @property
    def separator(self) -> str:
        return self.value[1]

class SplitColumnDialog(QDialog):
    """Dialog for splitting a string column into new columns based on a delimiter"""
    def __init__(self, columns: list[str], parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Split Column")
        self.setMinimumWidth(550)
        self.setObjectName("SplitColumnDialog")

        self.columns: list[str] = columns
        self._parsed_new_columns: list[str] = []

        # Validation timer
        validation_timer_interval_ms = 200
        self._validation_timer = QTimer(self)
        self._validation_timer.setSingleShot(True)
        self._validation_timer.setInterval(validation_timer_interval_ms)
        self._validation_timer.timeout.connect(self._perform_validation)

        self.init_ui()
        self._trigger_validation()
    
    def init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.column_combo = QComboBox()
        self.column_combo.addItems(self.columns)
        self.column_combo.setToolTip("Select the text column you want to split")
        self.column_combo.setObjectName("SplitColumnCombo")
        form_layout.addRow("Column to Split:", self.column_combo)

        # Delimiter selection
        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("SplitPresetCombo")
        for preset in DelimiterPreset:
            self.preset_combo.addItem(preset.display_name, userData=preset)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)

        self.delimiter_input = QLineEdit()
        self.delimiter_input.setPlaceholderText("Enter custom delimiter...")
        self.delimiter_input.setToolTip("The character(s) separating the values")
        self.delimiter_input.setObjectName("SplitDelimiterInput")
        self.delimiter_input.setClearButtonEnabled(True)
        self.delimiter_input.textChanged.connect(self._trigger_validation)
        self.delimiter_input.hide()

        delimiter_layout = QHBoxLayout()
        delimiter_layout.setContentsMargins(0, 0, 0, 0)
        delimiter_layout.addWidget(self.preset_combo)
        delimiter_layout.addWidget(self.delimiter_input)
        form_layout.addRow("Delimiter:", delimiter_layout)

        self.auto_gen_spinbox = QSpinBox()
        self.auto_gen_spinbox.setObjectName("SplitAutoGenSpinBox")
        self.auto_gen_spinbox.setRange(2, 50)
        self.auto_gen_spinbox.setToolTip("Automatically generate sequential column names")
        self.auto_gen_spinbox.valueChanged.connect(self._auto_generate_names)
        form_layout.addRow("Auto-Generate names:", self.auto_gen_spinbox)

        self.new_columns_input = QLineEdit()
        self.new_columns_input.setPlaceholderText("e.g., First Name, Last Name")
        self.new_columns_input.setToolTip("Enter the names for the new columns, separated by commas")
        self.new_columns_input.setObjectName("SplitNewColumnsInput")
        self.new_columns_input.setClearButtonEnabled(True)
        self.new_columns_input.textChanged.connect(self._trigger_validation)
        form_layout.addRow("New Column Names.", self.new_columns_input)

        # Preview of the resulting columns
        self.preview_label = QLabel()
        self.preview_label.setObjectName("SplitColumnPreviewLabel")
        self.preview_label.setProperty("subtleText", True)
        self.preview_label.setWordWrap(True)
        form_layout.addRow("", self.preview_label)

        main_layout.addLayout(form_layout)

        # Error label for feedback
        self.error_label = QLabel()
        self.error_label.setObjectName("SplitColumnErrorLabel")
        self.error_label.setProperty("errorText", True)

        self._error_opacity_effect = QGraphicsOpacityEffect(self.error_label)
        self.error_label.setGraphicsEffect(self._error_opacity_effect)
        self._error_opacity_effect.setOpacity(0.0)

        self._error_animation = QPropertyAnimation(self._error_opacity_effect, b"opacity")
        self._error_animation.setDuration(250)
        self._error_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        main_layout.addWidget(self.error_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel", parent=self)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_ok = QPushButton("Apply Split")
        self.btn_ok.setObjectName("MainActionButton")
        self.btn_ok.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        main_layout.addLayout(btn_layout)

    @pyqtSlot(int)
    def _on_preset_changed(self, index: int) -> None:
        """Toggles the custom delimiter input based on the selected preset"""
        preset: DelimiterPreset = self.preset_combo.itemData(index)
        if preset == DelimiterPreset.CUSTOM:
            self.delimiter_input.show()
            self.delimiter_input.setFocus()
            self.delimiter_input.selectAll()
        else:
            self.delimiter_input.hide()
        self._trigger_validation()

    @pyqtSlot(int)
    def _auto_generate_names(self, count: int) -> None:
        """Generates sequential column names based on the value of the spinbox"""
        base_name = self.column_combo.currentText()
        if not base_name:
            base_name = "Split"

        generated_names = [f"{base_name}_{i+1}" for i in range(count)]
        self.new_columns_input.setText(", ".join(generated_names))

    @pyqtSlot()
    def _trigger_validation(self) -> None:
        """Restarts the timer to delay validation until typing pauses"""
        self._validation_timer.start()

    @pyqtSlot()
    def _perform_validation(self) -> None:
        """
        Validates inputs, check for existing column conflicts,
        caches parsed data and updates the UI
        """
        preset: DelimiterPreset = self.preset_combo.currentData()
        delimiter: str = self.delimiter_input.text() if preset == DelimiterPreset.CUSTOM else preset.separator

        if not delimiter:
            self.preview_label.setText("Preview: [None]")
            self._set_error("Please provide a valid delimiter")
            return

        new_cols_raw: str = self.new_columns_input.text()
        self._parsed_new_columns = [col.strip() for col in new_cols_raw.split(",") if col.strip()]

        if self._parsed_new_columns:
            formatted_preview = ", ".join(f"'{col}'" for col in self._parsed_new_columns)
            self.preview_label.setText(f"Preview: [{formatted_preview}]")
        else:
            self.preview_label.setText("Preview: [None]")

        if len(self._parsed_new_columns) < 2:
            self._set_error("Provide at least two new column names, separated by commas")
            return

        existing_conflicts = [col for col in self._parsed_new_columns if col in self.columns]
        if existing_conflicts:
            conflict_str = ", ".join(existing_conflicts)
            self._set_error(f"Conflict: Column(s) already exists: {conflict_str}")
            return

        self._clear_error()
        self.btn_ok.setEnabled(True)

    def _set_error(self, message: str) -> None:
        """Displays an error message and disables the apply button"""
        self.error_label.setText(message)
        self.btn_ok.setEnabled(False)

        if self._error_opacity_effect.opacity() == 0.0:
            self._error_animation.stop()
            self._error_animation.setEndValue(1.0)
            self._error_animation.start()

    def _clear_error(self) -> None:
        """Clears the error message and restores valid state"""
        if self._error_opacity_effect.opacity() > 0.0:
            self._error_animation.stop()
            self._error_animation.setEndValue(0.0)
            self._error_animation.start()

    def get_parameters(self) -> tuple[str, str, list[str]]:
        """
        Retrieves the configured split parameters

        Returns:
            tuple: (column_name, delimiter, list_of_new_column_names)
        """
        column: str = self.column_combo.currentText()
        preset: DelimiterPreset = self.preset_combo.currentData()
        delimiter: str = self.delimiter_input.text() if preset == DelimiterPreset.CUSTOM else preset.separator

        return column, delimiter, self._parsed_new_columns