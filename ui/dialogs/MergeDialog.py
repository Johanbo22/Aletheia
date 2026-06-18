from pathlib import Path

import pandas as pd
from PyQt6.QtWidgets import QComboBox, QDialog, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, \
    QMessageBox, QPushButton, QVBoxLayout

from core.data_handler import DataHandler
from core.global_signals import LogLevel, ToastLevel, global_signals
from icons.icon_registry import IconBuilder, IconType
from ui.widgets.VennDiagramWidget import VennDiagramWidget

class MergeDialog(QDialog):
    """Dialog for merging / joining the current dataset with another file"""

    def __init__(self, data_handler: DataHandler, parent=None):
        super().__init__(parent)
        self.data_handler = data_handler
        self.right_df = None
        self.right_file_path = None

        self.setWindowTitle("Merge Datasets")
        self.resize(600, 500)
        self.setModal(True)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Dataset selection
        file_group = QGroupBox("Select Dataset to Join")
        file_layout = QHBoxLayout()

        self.file_label = QLabel("No file selected")
        self.file_label.setObjectName("merge_file_label")
        self.file_label.setProperty("status", "unselected")

        self.browse_button = QPushButton("Browse...", parent=self)
        self.browse_button.setIcon(IconBuilder.build(IconType.OpenProject))
        self.browse_button.clicked.connect(self.browse_file)

        file_layout.addWidget(self.file_label, 1)
        file_layout.addWidget(self.browse_button)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Join configs
        self.config_group = QGroupBox("Join Configueration")
        self.config_group.setEnabled(False)
        config_layout = QFormLayout()

        # join Type
        self.join_type_combo = QComboBox()
        self.join_type_combo.addItems(["inner", "left", "right", "outer"])
        self.join_type_combo.setToolTip(
            "Inner: Keep only matching rows\n"
            "Left: Keep all rows from the current data\n"
            "Right: Keep all rows from the new file\n"
            "Outer: Keep all rows from both"
        )
        self.join_type_combo.currentIndexChanged.connect(lambda: self.update_preview())
        config_layout.addRow("Join Type", self.join_type_combo)

        # Keys
        self.left_on_combo = QComboBox()
        self.left_on_combo.addItems(list(self.data_handler.df.columns))
        self.left_on_combo.currentIndexChanged.connect(lambda: self.update_preview())
        config_layout.addRow("Join On (Current Data)", self.left_on_combo)

        self.right_on_combo = QComboBox()
        self.right_on_combo.currentIndexChanged.connect(lambda: self.update_preview())
        config_layout.addRow("Join On (New Data)", self.right_on_combo)

        # Suffixes
        suffix_layout = QHBoxLayout()
        self.left_suffix = QLineEdit("_x")
        self.left_suffix.setPlaceholderText("Current data suffix")
        self.right_suffix = QLineEdit("_y")
        self.right_suffix.setPlaceholderText("New data suffix")
        suffix_layout.addWidget(QLabel("Left:"))
        suffix_layout.addWidget(self.left_suffix)
        suffix_layout.addWidget(QLabel("Right:"))
        suffix_layout.addWidget(self.right_suffix)

        config_layout.addRow("Suffixes", suffix_layout)

        self.config_group.setLayout(config_layout)
        layout.addWidget(self.config_group)

        self.venn_widget = VennDiagramWidget()
        self.venn_widget.setObjectName("VennDiagramWidget")
        layout.addWidget(self.venn_widget)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        self.merge_button = QPushButton("Merge Data")
        self.merge_button.setObjectName("MainActionButton")
        self.merge_button.clicked.connect(self.validate_and_accept)
        self.merge_button.setEnabled(False)

        cancel_button = QPushButton("Cancel", parent=self)
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.merge_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.update_preview()

    def browse_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Data file to merge", "",
                                                  "Data Files (*.csv *.xlsx *.xls *.json *.txt);;All Files (*)")

        if filepath:
            try:
                self.right_df = self.data_handler.read_file(filepath)
                self.right_file_path = filepath

                self.file_label.setText(f"{Path(filepath).name} ({len(self.right_df)} rows)")
                self.file_label.setProperty("status", "selected")
                self.file_label.style().unpolish(self.file_label)
                self.file_label.style().polish(self.file_label)

                self.right_on_combo.clear()
                self.right_on_combo.addItems(list(self.right_df.columns))

                self.config_group.setEnabled(True)
                self.merge_button.setEnabled(True)
                current_cols = set(self.data_handler.df.columns)
                for col in self.right_df.columns:
                    if col in current_cols:
                        self.right_on_combo.setCurrentText(col)
                        self.left_on_combo.setCurrentText(col)
                        break
                self.update_preview()
            except Exception as Error:
                global_signals.request_toast(
                    "Load Error", f"Failed to load file:\n{str(Error)}", ToastLevel.ERROR
                )
                global_signals.request_log(f"Failed to load file to merge: {str(Error)}", LogLevel.ERROR)
                self.right_df = None
                self.config_group.setEnabled(False)
                self.merge_button.setEnabled(False)
                self.update_preview()

    def update_preview(self, *args):
        left_count = len(self.data_handler.df) if self.data_handler.df is not None else 0
        right_count = len(self.right_df) if self.right_df is not None else 0
        join_type = self.join_type_combo.currentText().lower()
        result_count = 0

        if (self.right_df is not None and self.left_on_combo.currentText() and self.right_on_combo.currentText()):
            left_col = self.left_on_combo.currentText()
            right_col = self.right_on_combo.currentText()

            try:
                l_subset = self.data_handler.df[[left_col]].copy()
                r_subset = self.right_df[[right_col]].copy()
                l_subset[left_col] = l_subset[left_col].astype(str)
                r_subset[right_col] = r_subset[right_col].astype(str)

                l_subset.rename(columns={left_col: "key"}, inplace=True)
                r_subset.rename(columns={right_col: "key"}, inplace=True)

                merged_preview = pd.merge(l_subset, r_subset, on="key", how=join_type)
                result_count = len(merged_preview)
            except Exception as error:
                result_count = 0
                print(f"Preview merge failed: {error}")

        self.venn_widget.set_data(join_type, left_count, right_count, result_count)

    def validate_and_accept(self):
        if self.right_df is None:
            return

        left_col = self.left_on_combo.currentText()
        right_col = self.right_on_combo.currentText()

        if not left_col or not right_col:
            global_signals.request_toast(
                "Invalid Selection", "Please select joining columns for both datasets", ToastLevel.WARNING
            )
            return

        try:
            left_dtype = self.data_handler.df[left_col].dtype
            right_dtype = self.data_handler.df[right_col].dtype

            is_left_num = pd.api.types.is_numeric_dtype(left_dtype)
            is_right_num = pd.api.types.is_numeric_dtype(right_dtype)

            if is_left_num != is_right_num:
                res = QMessageBox.warning(
                    self,
                    "Type Mismatch Warning",
                    f"Column types might not match.\nLeft: {left_dtype}\nRight: {right_dtype}\n\nMerge might fail or return empty result. Continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if res == QMessageBox.StandardButton.No:
                    return
        except Exception:
            pass

        self.accept()

    def get_config(self):
        return {
            "right_df": self.right_df,
            "how"     : self.join_type_combo.currentText(),
            "left_on" : [self.left_on_combo.currentText()],
            "right_on": [self.right_on_combo.currentText()],
            "suffixes": (self.left_suffix.text(), self.right_suffix.text())
        }
