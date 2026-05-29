from typing import List, Dict, Any
import keyword
import pandas as pd

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox, QLineEdit, QGroupBox, QComboBox, QCheckBox, QPushButton

from ui.theme import ThemeColors
from ui.icons import IconBuilder, IconType

class RollingWindowDialog(QDialog):
    """
    Dialog for configuration of rolling window operations
    """
    def __init__(self, df: pd.DataFrame, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Apply Rolling Window")
        self.setModal(True)
        self.resize(650, 600)
        
        self.df: pd.DataFrame = df
        self.numeric_columns: List[str] = df.select_dtypes(include=["number"]).columns.tolist()
        self.existing_columns: List[str] = df.columns.tolist()
        
        self.init_ui()
    
    def init_ui(self) -> None:
        layout = QVBoxLayout()
        
        info_label = QLabel("Calculate moving averages and other rolling statistics. The window size determines how many previous rows are included in the calculation.")
        info_label.setWordWrap(True)
        info_label.setProperty("styleClass", "info_text")
        layout.addWidget(info_label)
        layout.addSpacing(10)
        
        settings_group = QGroupBox("Rolling Parameters")
        settings_layout = QFormLayout()
        settings_layout.setSpacing(10)
        
        # Target colymn
        self.column_combo = QComboBox()
        self.column_combo.addItems(self.numeric_columns)
        self.column_combo.setToolTip("Select the numeric column to apply the rolling window to.")
        self.column_combo.currentTextChanged.connect(self._on_parameters_changed)
        settings_layout.addRow("Target Column:", self.column_combo)
        
        # window size
        self.window_spin = QSpinBox()
        self.window_spin.setRange(2, 100000)
        self.window_spin.setValue(3)
        self.window_spin.valueChanged.connect(self._on_parameters_changed)
        settings_layout.addRow("Window Size:", self.window_spin)
        
        self.min_periods_spin = QSpinBox()
        self.min_periods_spin.setRange(1, 100000)
        self.min_periods_spin.setValue(1)
        self.min_periods_spin.setSpecialValueText("Default (Window Size)")
        self.min_periods_spin.setValue(self.min_periods_spin.minimum())
        self.min_periods_spin.setToolTip("Minimum number of observations in the window required to have a value; otherwise the result is NaN")
        self.min_periods_spin.valueChanged.connect(self._on_parameters_changed)
        settings_layout.addRow("Min Periods:", self.min_periods_spin)
        
        self.center_checkbox = QCheckBox("Center the window labels")
        self.center_checkbox.setToolTip("Set the labels at the center of the window rather than the right edge. Prevents phase shifts.")
        self.center_checkbox.stateChanged.connect(self._on_parameters_changed)
        settings_layout.addRow("Alignment:", self.center_checkbox)
        
        self.operation_combo = QComboBox()
        operations = [
            ("Moving Average (Mean)", "mean"),
            ("Moving Sum", "sum"),
            ("Moving Median", "median"),
            ("Rolling Minimum", "min"),
            ("Rolling Maximum", "max"),
            ("Rolling Std. Dev.", "std")
        ]
        for display_text, internal_val in operations:
            self.operation_combo.addItem(display_text, internal_val)
        self.operation_combo.setToolTip("The mathematical operation to apply across the moving window.")
        self.operation_combo.currentTextChanged.connect(self._on_parameters_changed)
        settings_layout.addRow("Operation:", self.operation_combo)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()
        output_layout.setSpacing(5)
        
        form_layout = QFormLayout()
        self.new_name_input = QLineEdit()
        self.new_name_input.setToolTip("The name of the new column that will store the rolling results.")
        self.new_name_input.textChanged.connect(self._live_validate_name)
        form_layout.addRow("New Column Name:", self.new_name_input)
        
        output_layout.addLayout(form_layout)
        
        self.validation_label = QLabel("")
        self.validation_label.setProperty("statusState", "success")
        output_layout.addWidget(self.validation_label)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(2)
        self.preview_table.horizontalHeader().setObjectName("MainDataHeader")
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.preview_table.verticalHeader().setObjectName("MainDataHeader")
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        preview_layout.addWidget(self.preview_table)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        layout.addStretch()
        
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Apply")
        self.ok_button.setObjectName("MainActionButton")
        self.ok_button.setIcon(IconBuilder.build(IconType.Checkmark))
        self.ok_button.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(self.ok_button)

        cancel_button = QPushButton("Cancel", parent=self)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        self._auto_generate_name()
        self._live_validate_name()
    
    def _on_parameters_changed(self, *args) -> None:
        self._auto_generate_name()
    
    def _auto_generate_name(self, *args) -> None:
        if not self.column_combo or not self.window_spin or not self.operation_combo or not self.new_name_input:
            return
        
        col = self.column_combo.currentText()
        win = self.window_spin.value()
        op = self.operation_combo.currentText()
        
        default_name = f"{col}_rolling_{win}_{op}"
        self.new_name_input.blockSignals(True)
        self.new_name_input.setText(default_name)
        self.new_name_input.blockSignals(False)
        self._live_validate_name()
    
    def _live_validate_name(self) -> None:
        if not self.new_name_input:
            return
        
        name: str = self.new_name_input.text().strip()
        is_valid = True
        msg = "Valid column name"
        state = "success"
        
        if not name:
            is_valid = False
            msg = "Column name cannot be empty."
            state = "error"
        elif name in self.existing_columns:
            is_valid = False
            msg = f"Column '{name}' already exists."
            state = "error"
        elif keyword.iskeyword(name):
            is_valid = False
            msg = "Name cannot be a Python keyword."
            state = "error"
        elif "`" in name:
            is_valid = False
            msg = "Name cannot contain backticks."
            state = "error"
        
        self.validation_label.setText(msg)
        self.validation_label.setProperty("statusState", state)
        self.validation_label.style().unpolish(self.validation_label)
        self.validation_label.style().polish(self.validation_label)
        
        self.ok_button.setEnabled(is_valid)
        if is_valid:
            self._update_preview()
        else:
            self.preview_table.clearContents()
            self.preview_table.setRowCount(0)
    
    def _update_preview(self) -> None:
        col = self.column_combo.currentText()
        win = self.window_spin.value()
        min_p = None if self.min_periods_spin.value() == self.min_periods_spin.minimum() else self.min_periods_spin.value()
        center = self.center_checkbox.isChecked()
        op = self.operation_combo.currentData()
        new_col_name = self.new_name_input.text().strip()
        
        if not col or col not in self.df.columns:
            return
        
        try:
            end_idx = min(len(self.df), win + 5)
            preview_df = self.df[[col]].head(end_idx).copy()
            
            rolling_obj = preview_df[col].rolling(window=win, min_periods=min_p, center=center)
            
            if op == "mean":
                preview_df[new_col_name] = rolling_obj.mean()
            elif op == "sum":
                preview_df[new_col_name] = rolling_obj.sum()
            elif op == "min":
                preview_df[new_col_name] = rolling_obj.min()
            elif op == "max":
                preview_df[new_col_name] = rolling_obj.max()
            elif op == "std":
                preview_df[new_col_name] = rolling_obj.std()
            elif op == "median":
                preview_df[new_col_name] = rolling_obj.median()
            
            start_display = max(0, win - 3)
            display_df = preview_df.iloc[start_display:start_display+6]
            
            self.preview_table.setRowCount(len(display_df))
            self.preview_table.setHorizontalHeaderLabels([col, new_col_name])
            self.preview_table.setVerticalHeaderLabels([str(i) for i in display_df.index])
            
            for row_idx, (_, row_data) in enumerate(display_df.iterrows()):
                orig_val = str(row_data[col]) if pd.notna(row_data[col]) else "NaN"
                roll_val = f"{row_data[new_col_name]:.4f}" if pd.notna(row_data[new_col_name]) else "NaN"
                
                self.preview_table.setItem(row_idx, 0, QTableWidgetItem(orig_val))
                self.preview_table.setItem(row_idx, 1, QTableWidgetItem(roll_val))
        except Exception:
            self.preview_table.clearContents()
            self.preview_table.setRowCount(0)
            
                
    def validate_and_accept(self) -> None:
        if not self.new_name_input:
            return
        
        new_name: str = self.new_name_input.text().strip()
        if not new_name or new_name in self.existing_columns or keyword.iskeyword(new_name):
            return
        self.accept()
    
    def get_config(self) -> Dict[str, Any]:
        min_p = None if self.min_periods_spin.value() == self.min_periods_spin.minimum() else self.min_periods_spin.value()
        return {
            "column": self.column_combo.currentText(),
            "window": self.window_spin.value(),
            "min_periods": min_p,
            "center": self.center_checkbox.isChecked(),
            "operation": self.operation_combo.currentText(),
            "new_column": self.new_name_input.text().strip()
        }