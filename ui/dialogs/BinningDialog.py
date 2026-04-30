from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QWidget, QFormLayout, QProgressBar
from PyQt6.QtCore import Qt, QRegularExpression, QTimer
from PyQt6.QtGui import QRegularExpressionValidator
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton, DataPlotStudioLineEdit, DataPlotStudioComboBox, DataPlotStudioSpinBox, DataPlotStudioGroupBox, DataPlotStudioCheckBox

import pandas as pd
from typing import Any, Optional
from enum import Enum

class BinningPreviewWidget(QWidget):
    """Displays a vertical bar chart to represent bin distribution"""
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("binning_preview_widget")
        self.setMinimumHeight(180)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.figure = Figure(figsize=(5,3), dpi=100)
        self.figure.patch.set_alpha(0.0)
        self.canvas = FigureCanvas(self.figure)
        self.main_layout.addWidget(self.canvas)
        
        self.ax = self.figure.add_subplot(111)
        
        self.empty_state_label = QLabel("Not enough valid data to generate a preview.")
        self.empty_state_label.setObjectName("preview_empty_label")
        self.empty_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.empty_state_label)
        
        self.clear_preview()
    
    def clear_preview(self) -> None:
        """Removes the chart data and displays the empty state label."""
        self.ax.clear()
        self.canvas.draw()
        self.canvas.setVisible(False)
        self.empty_state_label.setVisible(True)
    
    def update_preview(self, binned_series: pd.Series) -> None:
        """Generates a vertical bar chart representing the distribution of binned data."""
        counts = binned_series.value_counts(sort=False)
        total_count = len(binned_series)
        
        if total_count == 0 or counts.empty:
            self.clear_preview()
            return
        
        self.empty_state_label.setVisible(False)
        self.canvas.setVisible(True)
        
        self.ax.clear()
        
        labels = [str(cat) for cat in counts.index]
        values = counts.values
        
        bars = self.ax.bar(labels, values, color=ThemeColors.MainColor, edgecolor="none", alpha=0.85)
        
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["left"].set_visible(False)
        self.ax.spines["bottom"].set_color("#CCCCCC")
        self.ax.set_yticks([])
        
        self.ax.tick_params(axis="x", rotation=45, labelsize=9, bottom=False)
        self.ax.margins(y=0.20)
        
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                self.ax.annotate(
                    f"{int(height)}",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0,3),
                    textcoords="offset points",
                    ha="center", va="bottom",
                    fontsize=8,
                    color="#555555"
                )
        self.figure.tight_layout()
        self.canvas.draw()

class BinningMethod(Enum):
    """Enumeration of supported binning strategies."""
    FixedBins = "Fixed Number of Bins"
    Quantiles = "Quantiles"
    CustomEdges = "Custom Edges"

class LabelStrategy(Enum):
    """Enumeration of supported labeling strategies."""
    Default = "Default Intervals (e.g., (0, 10])"
    Custom = "Custom Comma-Separated"
    Sequential = "Sequential Prefix"

class BinningDialog(QDialog):
    """Dialog for binning continious variables"""
    
    def __init__(self, columns: list, data_frame: Optional[pd.DataFrame] = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Bin data")
        self.resize(550, 600)
        self.columns = columns
        self.data_frame = data_frame
        self.result_config = None
        
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(400)
        self.preview_timer.timeout.connect(self._generate_preview)
        
        self.init_ui()
    
    def init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        
        # General Config
        general_group = DataPlotStudioGroupBox("General")
        general_group.setObjectName("binning_general_group")
        self.general_layout = QFormLayout(general_group)
        self.general_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
        self.column_combo = DataPlotStudioComboBox()
        self.column_combo.addItems(self.columns)
        self.column_combo.currentIndexChanged.connect(self._auto_generate_name)
        self.general_layout.addRow("Select Numeric Column:", self.column_combo)
        
        self.new_name_input = DataPlotStudioLineEdit()
        self.new_name_input.setPlaceholderText("e.g., Age_Group")
        self.new_name_input.setToolTip("Must be a valid Python identifier. Spaces and special characters are not allowed")
        
        identifier_regex = QRegularExpression(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
        self.new_name_input.setValidator(QRegularExpressionValidator(identifier_regex, self.new_name_input))
        self.general_layout.addRow("New Column Name:", self.new_name_input)
        
        main_layout.addWidget(general_group)
        
        # Binning Strategy group
        method_group = DataPlotStudioGroupBox("Binning Strategy")
        method_group.setObjectName("binning_method_group")
        self.method_layout = QFormLayout(method_group)
        self.method_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
        self.method_combo = DataPlotStudioComboBox()
        self.method_combo.addItems([method.value for method in BinningMethod])
        self.method_combo.setToolTip("Select the statistical strategy for dividing the data into bins")
        self.method_combo.currentIndexChanged.connect(self._update_input_visibility)
        self.method_layout.addRow("Binning Method:", self.method_combo)
        
        self.bin_count_widget = QWidget()
        bin_count_layout = QVBoxLayout(self.bin_count_widget)
        bin_count_layout.setContentsMargins(0, 0, 0, 0)
        self.bin_count_spin = DataPlotStudioSpinBox()
        self.bin_count_spin.setRange(2, 100)
        self.bin_count_spin.setValue(5)
        bin_count_layout.addWidget(self.bin_count_spin)
        self.method_layout.addRow("Number of Bins:", self.bin_count_widget)
        
        self.custom_edges_widget = QWidget()
        custom_edges_layout = QVBoxLayout(self.custom_edges_widget)
        custom_edges_layout.setContentsMargins(0, 0, 0, 0)
        self.edges_input = DataPlotStudioLineEdit()
        self.edges_input.setPlaceholderText("e.g., 0, 18, 35, 60, 100")
        
        edge_regex = QRegularExpression(r"^[0-9.,\s\-]+$")
        self.edges_input.setValidator(QRegularExpressionValidator(edge_regex, self.edges_input))
        custom_edges_layout.addWidget(self.edges_input)
        
        self.catch_all_checkbox = DataPlotStudioCheckBox("Add -∞ and ∞ to edges to catch out-of-bounds data")
        self.catch_all_checkbox.setChecked(True)
        self.catch_all_checkbox.setToolTip("Ensures no data becomes 'NaN' by extending the first and last bins to infinity")
        custom_edges_layout.addWidget(self.catch_all_checkbox)
        
        self.method_layout.addRow("Bin Edges:", self.custom_edges_widget)
        main_layout.addWidget(method_group)
        
        # Labelling group
        labeling_group = DataPlotStudioGroupBox("Labeling")
        labeling_group.setObjectName("binning_labeling_group")
        self.labeling_layout = QFormLayout(labeling_group)
        self.labeling_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
        self.labels_strategy_combo = DataPlotStudioComboBox()
        self.labels_strategy_combo.addItems([strategy.value for strategy in LabelStrategy])
        self.labels_strategy_combo.setToolTip("Define how the resulting bins will be named in the new column.")
        self.labels_strategy_combo.currentIndexChanged.connect(self._update_input_visibility)
        self.labeling_layout.addRow("Labeling Properties:", self.labels_strategy_combo)
        
        self.custom_labels_widget = QWidget()
        custom_labels_layout = QVBoxLayout(self.custom_labels_widget)
        custom_labels_layout.setContentsMargins(0, 0, 0, 0)
        self.labels_input = DataPlotStudioLineEdit()
        self.labels_input.setPlaceholderText("e.g., Low, Medium, High")
        custom_labels_layout.addWidget(self.labels_input)
        self.labeling_layout.addRow("Custom Labels:", self.custom_labels_widget)
        
        self.prefix_labels_widget = QWidget()
        prefix_labels_layout = QVBoxLayout(self.prefix_labels_widget)
        prefix_labels_layout.setContentsMargins(0, 0, 0, 0)
        self.prefix_input = DataPlotStudioLineEdit()
        self.prefix_input.setPlaceholderText("e.g., Group (results in Group 1, Group 2...)")
        prefix_labels_layout.addWidget(self.prefix_input)
        self.labeling_layout.addRow("Prefix for Sequential Labels:", self.prefix_labels_widget)
        main_layout.addWidget(labeling_group)
        
        # ADvanced settings
        advanced_group = DataPlotStudioGroupBox("Advanced Options")
        advanced_group.setObjectName("binning_advanced_group")
        advanced_layout = QVBoxLayout(advanced_group)
        
        self.right_inclusive_checkbox = DataPlotStudioCheckBox("Right-inclusive intervals (e.g. (0-10])")
        self.right_inclusive_checkbox.setChecked(True)
        advanced_layout.addWidget(self.right_inclusive_checkbox)
        
        self.drop_original_checkbox = DataPlotStudioCheckBox("Drop Original column after binning")
        self.drop_original_checkbox.setChecked(False)
        advanced_layout.addWidget(self.drop_original_checkbox)
        main_layout.addWidget(advanced_group)
        
        preview_group = DataPlotStudioGroupBox("Distribution Preview")
        preview_group.setObjectName("binning_preview_group")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_widget = BinningPreviewWidget()
        preview_layout.addWidget(self.preview_widget)
        main_layout.addWidget(preview_group)
        
        # Status labels
        self.hint_label = QLabel()
        self.hint_label.setObjectName("binning_hint_label")
        main_layout.addWidget(self.hint_label)
        
        main_layout.addStretch()
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.apply_button = DataPlotStudioButton(
            "Create Bins",
            parent=self,
            base_color_hex=ThemeColors.MainColor,
            text_color_hex="white"
        )
        self.apply_button.setDefault(True)
        self.apply_button.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(self.apply_button)
        
        self.cancel_button = DataPlotStudioButton("Cancel", parent=self)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(button_layout)
        
        self.new_name_input.textChanged.connect(self._validate_form)
        self.edges_input.textChanged.connect(self._validate_form)
        self.labels_input.textChanged.connect(self._validate_form)
        self.prefix_input.textChanged.connect(self._validate_form)
        
        self.bin_count_spin.valueChanged.connect(self._validate_form)
        self.catch_all_checkbox.stateChanged.connect(self._validate_form)
        self.right_inclusive_checkbox.stateChanged.connect(self._validate_form)
        
        self._update_input_visibility()
        self._auto_generate_name()
        self._validate_form()
    
    def _update_input_visibility(self) -> None:
        """Toggle inputs on the selected method"""
        selected_method_text = self.method_combo.currentText()
        is_custom = selected_method_text == BinningMethod.CustomEdges.value
        
        self._set_row_visible(self.bin_count_widget, not is_custom, self.method_layout)
        self._set_row_visible(self.custom_edges_widget, is_custom, self.method_layout)
        
        selected_strategy_text = self.labels_strategy_combo.currentText()
        self._set_row_visible(self.custom_labels_widget, selected_strategy_text == LabelStrategy.Custom.value, self.labeling_layout)
        self._set_row_visible(self.prefix_labels_widget, selected_strategy_text == LabelStrategy.Sequential.value, self.labeling_layout)
        
        self._validate_form()
    
    def _set_row_visible(self, widget: QWidget, visible: bool, layout: QFormLayout) -> None:
        widget.setVisible(visible)
        
        label = layout.labelForField(widget)
        if label:
            label.setVisible(visible)
    
    def _validate_form(self) -> None:
        is_valid = True
        hint_text = ""
        
        self._parsed_bins = None
        self._parsed_labels = None
        self._pd_method = "cut"
        
        new_name = self.new_name_input.text().strip()
        if not new_name:
            is_valid = False
            hint_text = "Please enter a valid new column name."
            
        expected_bins = self.bin_count_spin.value()
        selected_method_text = self.method_combo.currentText()
        
        if selected_method_text == BinningMethod.FixedBins.value:
            self._parsed_bins = expected_bins
            self._pd_method = "cut"
        elif selected_method_text == BinningMethod.Quantiles.value:
            self._parsed_bins = expected_bins
            self._pd_method = "qcut"
        elif selected_method_text == BinningMethod.CustomEdges.value:
            self._pd_method = "cut"
            edges_str = self.edges_input.text().strip()
            if not edges_str:
                is_valid = False
                hint_text = hint_text or "Please provide comma-separated bin edges."
            else:
                try:
                    bins = [float(x.strip()) for x in edges_str.split(",") if x.strip()]
                    if len(bins) < 1:
                        raise ValueError()
                    
                    if any(bins[i] >= bins[i+1] for i in range(len(bins) - 1)):
                        is_valid = False
                        hint_text = hint_text or "Edges must be strictly increasing."
                    else:
                        if self.catch_all_checkbox.isChecked():
                            if bins[0] != float("-inf"): bins.insert(0, float("-inf"))
                            if bins[-1] != float("inf"): bins.append(float("inf"))
                        
                        if len(bins) < 2:
                            is_valid = False
                            hint_text = hint_text or "At least two valid edges are required."
                        else:
                            expected_bins = len(bins) - 1
                            self._parsed_bins = bins
                except ValueError:
                    is_valid = False
                    hint_text = hint_text or "Invalid numerical edges provided."
                    
        selected_strategy_text = self.labels_strategy_combo.currentText()
        if selected_strategy_text == LabelStrategy.Custom.value:
            self.labels_input.setPlaceholderText(f"Enter {expected_bins} comma-separated labels...")
            
            labels_str = self.labels_input.text().strip()
            if not labels_str:
                is_valid = False
                hint_text = hint_text or f"Provide {expected_bins} custom labels."
            else:
                labels = [x.strip() for x in labels_str.split(",") if x.strip()]
                if len(labels) != expected_bins:
                    is_valid = False
                    hint_text = hint_text or f"Expected {expected_bins} labels, but found {len(labels)}."
                elif len(labels) != len(set(labels)):
                    is_valid = False
                    hint_text = hint_text or "Custom labels must be unique."
                else:
                    self._parsed_labels = labels
                    
        elif selected_strategy_text == LabelStrategy.Sequential.value:
            prefix = self.prefix_input.text().strip()
            if not prefix:
                is_valid = False
                hint_text = hint_text or "Provide a prefix for sequential labels."
            else:
                self._parsed_labels = [f"{prefix} {i+1}" for i in range(expected_bins)]

        if is_valid:
            self.hint_label.setText("Ready to create bins.")
            self.hint_label.setProperty("status", "success")
            self.preview_timer.start()
        else:
            self.hint_label.setText(hint_text)
            self.hint_label.setProperty("status", "error")
            self.preview_timer.stop()
            self.preview_widget.clear_preview()
            
        self.hint_label.style().unpolish(self.hint_label)
        self.hint_label.style().polish(self.hint_label)

        self.apply_button.setEnabled(is_valid)
        
    def _generate_preview(self) -> None:
        if self.data_frame is None or self.data_frame.empty:
            self.preview_widget.clear_preview()
            return
        
        column_name = self.column_combo.currentText()
        if column_name not in self.data_frame.columns:
            return
        
        sample_series = self.data_frame[column_name].dropna().head(1000)
        
        try:
            if self._pd_method == "cut":
                binned_data = pd.cut(
                    sample_series, 
                    bins=self._parsed_bins, 
                    labels=self._parsed_labels, 
                    right=self.right_inclusive_checkbox.isChecked()
                )
            elif self._pd_method == "qcut":
                binned_data = pd.qcut(
                    sample_series, 
                    q=self._parsed_bins, 
                    labels=self._parsed_labels
                )
            else:
                return
            
            self.preview_widget.update_preview(binned_data)
        except Exception as err:
            self.preview_widget.clear_preview()
            self.hint_label.setText(f"Configuration Error: {str(err).capitalize()}")
            self.hint_label.setProperty("status", "error")
            self.hint_label.style().unpolish(self.hint_label)
            self.hint_label.style().polish(self.hint_label)
            self.apply_button.setEnabled(False)
    
    def _auto_generate_name(self) -> None:
        """Suggest names for the new column"""
        col = self.column_combo.currentText()
        if col:
            self.new_name_input.setText(f"{col}_binned")
    
    def validate_and_accept(self) -> None:
        if not self.apply_button.isEnabled():
            return
            
        self.result_config = {
            "column": self.column_combo.currentText(),
            "new_column": self.new_name_input.text().strip(),
            "method": self._pd_method,
            "bins": self._parsed_bins,
            "labels": self._parsed_labels,
            "right_inclusive": self.right_inclusive_checkbox.isChecked(),
            "drop_original": self.drop_original_checkbox.isChecked()
        }
        self.accept()
    
    def get_config(self) -> dict[str, Any] | None:
        return self.result_config