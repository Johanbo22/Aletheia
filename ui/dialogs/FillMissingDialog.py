from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
    QProgressBar,
    QFrame,
)
import pandas as pd

from ui.widgets.ControlElements import DataPlotStudioCheckBox, DataPlotStudioComboBox, DataPlotStudioLineEdit

class FillMissingDialog(QDialog):
    """Dialog for the user to manipulate their data using the fill missing tool"""

    def __init__(self, columns: list[str], df: pd.DataFrame = None, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.columns: list[str] = columns
        self.df: pd.DataFrame = df
        self.setWindowTitle("Fill Missing Values")
        self.setModal(True)
        self.resize(400, 300)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        info = QLabel("Select how to fill missing values (NaN) in your dataset.")
        info.setProperty("styleClass", "info_text")
        layout.addWidget(info)

        layout.addSpacing(10)

        # this is the columns selection UI
        layout.addWidget(QLabel("Target Column:"))
        self.column_combo = DataPlotStudioComboBox()
        self.column_combo.addItem("All Columns")
        self.column_combo.addItems(self.columns)
        self.column_combo.currentTextChanged.connect(self.update_stats)
        layout.addWidget(self.column_combo)

        # Stats frame
        self.stats_frame = QFrame()
        self.stats_frame.setObjectName("fill_missing_stats_frame")
        stats_layout = QVBoxLayout(self.stats_frame)

        self.stats_label = QLabel("Missing Values: N/A")
        self.stats_label.setObjectName("fill_missing_stats_label")
        stats_layout.addWidget(self.stats_label)

        self.missing_progress = QProgressBar()
        self.missing_progress.setTextVisible(False)
        self.missing_progress.setObjectName("fill_missing_progress")
        self.missing_progress.setProperty("severity", "high")
        stats_layout.addWidget(self.missing_progress)

        layout.addWidget(self.stats_frame)

        layout.addSpacing(10)

        # the user selects the method here
        layout.addWidget(QLabel("Fill Method:"))
        self.method_combo = DataPlotStudioComboBox()
        self.method_combo.addItems(
            [
                "Forward Fill (Previous Values)",
                "Backward Fill (Next Value)",
                "Linear Interpolation",
                "Time Interpolation",
                "Static Value (Type Below)",
                "Mean (Average)",
                "Median (Middle Value)",
                "Mode (Most Common)",
            ]
        )
        self.method_combo.currentTextChanged.connect(self.on_method_change)
        layout.addWidget(self.method_combo)

        layout.addSpacing(10)

        # grouping option
        self.group_check = DataPlotStudioCheckBox("Group By another Column")
        self.group_check.setToolTip(
            "Calculate the fill value based on groups (e.g., Mean_Salary byt Job_title)"
        )
        self.group_check.toggled.connect(self.toggle_group_combo)
        layout.addWidget(self.group_check)

        self.group_combo = DataPlotStudioComboBox()
        self.group_combo.addItems(self.columns)
        self.group_combo.setEnabled(False)
        self.group_combo.setVisible(False)
        layout.addWidget(self.group_combo)

        layout.addSpacing(10)

        # this is where the user types the value they want to fill. hidden by default unless method == staticvalue
        self.value_group = QWidget()
        value_layout = QVBoxLayout(self.value_group)
        value_layout.setContentsMargins(0, 0, 0, 0)
        value_layout.addWidget(QLabel("Enter Value:"))
        self.value_input = DataPlotStudioLineEdit()
        self.value_input.setPlaceholderText("e.g. 0, Unknown, 1.5")
        value_layout.addWidget(self.value_input)
        layout.addWidget(self.value_group)
        self.value_group.setVisible(False)

        layout.addStretch()

        # btns
        button_layout = QHBoxLayout()
        apply_btn = DataPlotStudioButton(
            "Apply Fill",
            parent=self,
            base_color_hex=ThemeColors.MainColor,
            text_color_hex="white",
            font_weight="bold",
        )
        apply_btn.clicked.connect(self.accept)

        cancel_btn = DataPlotStudioButton("Cancel", parent=self)
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(apply_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.update_stats()

    def on_method_change(self, text: str):
        """Show or hide the value intput box"""
        is_static: bool = "Static Value" in text
        self.value_group.setVisible(is_static)

        is_interpol: bool = "Interpolation" in text
        if is_static or is_interpol:
            self.group_check.setChecked(False)
            self.group_check.setEnabled(False)
        else:
            self.group_check.setEnabled(True)

    def toggle_group_combo(self, checked: bool):
        """Show or hide the group selection box"""
        self.group_combo.setVisible(checked)
        self.group_combo.setEnabled(checked)

    def update_stats(self):
        """Calculate and display nussubg value stats for the selected column"""
        if self.df is None:
            self.stats_frame.setVisible(False)
            return

        col: str = self.column_combo.currentText()
        total_rows = len(self.df)

        if total_rows == 0:
            return

        missing_count: int = 0
        percentage: float = 0.0
        if col == "All Columns":
            missing_count = self.df.isnull().sum().sum()
            total_cells: int = self.df.size
            if total_cells > 0:
                percentage = (missing_count / total_cells) * 100
            self.stats_label.setText(
                f"Total Missing Values: {missing_count:,} / {total_cells:,} ({percentage:.1f}%)"
            )
            self.missing_progress.setMaximum(total_cells)
        else:
            if col in self.df.columns:
                missing_count = int(self.df[col].isnull().sum())
                if total_rows > 0:
                    percentage = (missing_count / total_rows) * 100
                self.stats_label.setText(
                    f"Missing in '{col}': {missing_count:,} / {total_rows:,} ({percentage:.1f}%)"
                )
                self.missing_progress.setMaximum(total_rows)
        
        self.missing_progress.setValue(int(missing_count))

        severity = "low"
        if percentage > 0 and percentage < 10:
            severity = "medium"
        elif percentage >= 10:
            severity = "high"
        
        self.missing_progress.setProperty("severity", severity)
        self.missing_progress.style().unpolish(self.missing_progress)
        self.missing_progress.style().polish(self.missing_progress)

    def get_config(self) -> dict[str, str | None]:
        """Get the user selection"""
        text: str = self.method_combo.currentText()
        method: str = "ffill"

        if "Forward" in text:
            method = "ffill"
        elif "Backward" in text:
            method = "bfill"
        elif "Linear" in text:
            method = "linear_interpolation"
        elif "Time" in text:
            method = "time_interpolation"
        elif "Static" in text:
            method = "static_value"
        elif "Mean" in text:
            method = "mean"
        elif "Median" in text:
            method = "median"
        elif "Mode" in text:
            method = "mode"
            
        final_value: str | None = self.value_input.text().strip() if "Static" in text else None

        return {
            "column": self.column_combo.currentText(),
            "method": method,
            "value": final_value,
            "group_by": self.group_combo.currentText() if self.group_check.isChecked() else None
        }
