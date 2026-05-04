from typing import List, Dict, Any
import keyword
import pandas as pd

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView

from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton
from ui.icons import IconBuilder, IconType
from ui.widgets.ControlElements import DataPlotStudioComboBox, DataPlotStudioGroupBox, DataPlotStudioLineEdit, DataPlotStudioSpinBox

class PercentageChangeDialog(QDialog):
    """
    Dialog for configuration of percentage change operations
    """
    def __init__(self, df: pd.DataFrame, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Calculate Percentage Change")
        self.setModal(True)
        self.resize(650, 600)
        
        self.df: pd.DataFrame = df
        self.numeric_columns: List[str] = df.select_dtypes(include=["number"]).columns.tolist()
        self.existing_columns: List[str] = df.columns.tolist()
        
        self.init_ui()
    
    def init_ui(self) -> None:
        layout = QVBoxLayout()
        
        info_label = QLabel("Calculates the fractional change between the current and a prior element. Useful for calculating growth, Day-over-Day, or Month-over-Month changes.")
        info_label.setWordWrap(True)
        info_label.setProperty("styleClass", "info_text")
        layout.addWidget(info_label)
        layout.addSpacing(10)
        
        settings_group = DataPlotStudioGroupBox("Percentage Change Parameters")
        settings_layout = QFormLayout()
        settings_layout.setSpacing(10)
        
        self.column_combo = DataPlotStudioComboBox()
        self.column_combo.addItems(self.numeric_columns)
        self.column_combo.setToolTip("Select the numeric column to calculate changes for.")
        self.column_combo.currentTextChanged.connect(self._on_parameters_changed)
        settings_layout.addRow("Target Column:", self.column_combo)
        
        self.periods_spin = DataPlotStudioSpinBox()
        self.periods_spin.setRange(1, 100000)
        self.periods_spin.setValue(1)
        self.periods_spin.setToolTip("Periods to shift for forming percent change. (e.g., 1 for Day-over-Day).")
        self.periods_spin.valueChanged.connect(self._on_parameters_changed)
        settings_layout.addRow("Periods:", self.periods_spin)
        
        self.fill_method_combo = DataPlotStudioComboBox()
        operations = [
            ("Pad / Forward Fill", "pad"),
            ("Backfill", "bfill"),
            ("None", "none")
        ]
        for display_text, internal_val in operations:
            self.fill_method_combo.addItem(display_text, internal_val)
        self.fill_method_combo.setToolTip("How to handle NAs before computing changes.")
        self.fill_method_combo.currentTextChanged.connect(self._on_parameters_changed)
        settings_layout.addRow("NA Fill Method:", self.fill_method_combo)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        output_group = DataPlotStudioGroupBox("Output")
        output_layout = QVBoxLayout()
        output_layout.setSpacing(5)
        
        form_layout = QFormLayout()
        self.new_name_input = DataPlotStudioLineEdit()
        self.new_name_input.setToolTip("The name of the new column that will store the change results.")
        self.new_name_input.textChanged.connect(self._live_validate_name)
        form_layout.addRow("New Column Name:", self.new_name_input)
        
        output_layout.addLayout(form_layout)
        
        self.validation_label = QLabel("")
        self.validation_label.setProperty("statusState", "success")
        output_layout.addWidget(self.validation_label)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        preview_group = DataPlotStudioGroupBox("Preview")
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
        self.ok_button = DataPlotStudioButton("Apply", parent=self, base_color_hex=ThemeColors.MainColor, text_color_hex="white")
        self.ok_button.setIcon(IconBuilder.build(IconType.Checkmark))
        self.ok_button.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(self.ok_button)

        cancel_button = DataPlotStudioButton("Cancel", parent=self)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        self._auto_generate_name()
        self._live_validate_name()
    
    def _on_parameters_changed(self, *args) -> None:
        self._auto_generate_name()
    
    def _auto_generate_name(self, *args) -> None:
        if not self.column_combo or not self.periods_spin or not self.new_name_input:
            return
        
        col = self.column_combo.currentText()
        periods = self.periods_spin.value()
        
        default_name = f"{col}_pct_change_{periods}"
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
        periods = self.periods_spin.value()
        
        fill_raw = self.fill_method_combo.currentData()
        fill_method = None if fill_raw == "none" else fill_raw
        
        new_col_name = self.new_name_input.text().strip()
        
        if not col or col not in self.df.columns:
            return
        
        try:
            end_idx = min(len(self.df), periods + 10)
            preview_df = self.df[[col]].head(end_idx).copy()
            
            try:
                preview_df[new_col_name] = preview_df[col].pct_change(periods=periods, fill_method=fill_method)
            except TypeError:
                temp_col = preview_df[col].ffill() if fill_method in ['pad', 'ffill'] else preview_df[col].bfill() if fill_method in ['backfill', 'bfill'] else preview_df[col]
                preview_df[new_col_name] = temp_col.pct_change(periods=periods)
            
            self.preview_table.setRowCount(len(preview_df))
            self.preview_table.setHorizontalHeaderLabels([col, new_col_name])
            self.preview_table.setVerticalHeaderLabels([str(i) for i in preview_df.index])
            
            for row_idx, (_, row_data) in enumerate(preview_df.iterrows()):
                orig_val = str(row_data[col]) if pd.notna(row_data[col]) else "NaN"
                pct_val = f"{row_data[new_col_name]:.4%}" if pd.notna(row_data[new_col_name]) else "NaN"
                
                self.preview_table.setItem(row_idx, 0, QTableWidgetItem(orig_val))
                self.preview_table.setItem(row_idx, 1, QTableWidgetItem(pct_val))
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
        fill_raw = self.fill_method_combo.currentData()
        return {
            "column": self.column_combo.currentText(),
            "periods": self.periods_spin.value(),
            "fill_method": None if fill_raw == "none" else fill_raw,
            "new_column": self.new_name_input.text().strip()
        }