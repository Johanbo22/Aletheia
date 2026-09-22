from typing import Optional, TYPE_CHECKING

from PyQt6.QtWidgets import QComboBox, QFormLayout, QFrame, QGroupBox, QLabel, QLineEdit, QVBoxLayout

from icons import IconType
from src.ui.components.data_tabs.base_data_tab import BaseDataTab

if TYPE_CHECKING:
    from src.controller.data_tab_controller import DataTabController

class FilteringTab(BaseDataTab):
    def __init__(self, parent=None, controller: Optional["DataTabController"] = None) -> None:
        super().__init__(parent, controller)
        self.init_ui()

    def init_ui(self) -> None:
        layout = self.setup_scrollable_layout()
        layout.setSpacing(16)

        filter_info = QLabel(
            "Filter your dataset by defining criteria. Use the Quick Filter for single conditions, or the Advanced Filter for complex, multi-conditional queries.")
        filter_info.setWordWrap(True)
        filter_info.setProperty("styleClass", "info_text")
        layout.addWidget(filter_info)

        self.filter_status_label = QLabel("Status: No active filters")
        self.filter_status_label.setWordWrap(True)
        self.filter_status_label.setProperty("styleClass", "status_indicator_inactive")
        layout.addWidget(self.filter_status_label)

        quick_filter_group = QGroupBox("Quick Filter")
        quick_filter_layout = QVBoxLayout(quick_filter_group)

        form_layout = QFormLayout()

        self.filter_column = QComboBox()
        self.filter_column.setToolTip("Select the column you wish to apply a filter to")
        form_layout.addRow(QLabel("Column:"), self.filter_column)

        self.filter_condition = QComboBox()
        self.filter_condition.addItem("Equals", "==")
        self.filter_condition.addItem("Does not equal", "!=")
        self.filter_condition.addItem("Greater than", ">")
        self.filter_condition.addItem("Less than", "<")
        self.filter_condition.addItem("Greater than or equal", ">=")
        self.filter_condition.addItem("Less than or equal", "<=")
        self.filter_condition.addItem("Contains", "contains")
        self.filter_condition.setToolTip("Select the conditional operation to apply to the column.")
        form_layout.addRow(QLabel("Condition:"), self.filter_condition)

        self.filter_value = QLineEdit()
        self.filter_value.setPlaceholderText("Enter evaluation value...")
        self.filter_value.setClearButtonEnabled(True)
        self.filter_value.setToolTip(
            "Enter the value you want the column to be evaluated to.\nNote: Reference your data. This is case-sensitive")
        form_layout.addRow(QLabel("Value:"), self.filter_value)

        self.filter_preview_label = QLabel("")
        self.filter_preview_label.setWordWrap(True)
        self.filter_preview_label.setProperty("styleClass", "filter_preview_label")
        self.filter_preview_label.setVisible(False)
        form_layout.addRow(self.filter_preview_label)

        quick_filter_layout.addLayout(form_layout)

        quick_filter_layout.addLayout(self._create_operation_row(
            title="Apply Filter",
            tooltip="Apply the configured filter",
            callback=self.controller.apply_filter,
            help_id="apply_filter",
            icon_type=IconType.Filter
        ))

        quick_filter_layout.addLayout(self._create_operation_row(
            title="Clear Filters",
            tooltip="Reset the dataset to its original state and remove the filters",
            callback=self.controller.clear_filters,
            help_id="",
            icon_type=IconType.ClearFilter
        ))
        layout.addWidget(quick_filter_group)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setObjectName("landing_vertical_separator")
        layout.addWidget(separator)

        advanced_filter_group = QGroupBox("Advanced Filter")
        advanced_filter_layout = QVBoxLayout(advanced_filter_group)
        advanced_filter_layout.setSpacing(12)

        advanced_filter_layout.addLayout(self._create_operation_row(
            title="Advanced Filter",
            tooltip="Open the advanced multi-conditional filter to build more complex filters",
            callback=self.controller.open_advanced_filter,
            help_id="apply_filter",
            icon_type=IconType.AdvancedFilter
        ))
        layout.addWidget(advanced_filter_group)

        layout.addStretch()

        self.apply_destructive_styling_tags(["clear_filters"])
        self.filter_column.currentTextChanged.connect(self.controller.update_filter_preview_live)
        self.filter_condition.currentTextChanged.connect(self.controller.update_filter_preview_live)
        self.filter_value.textChanged.connect(self.controller.update_filter_preview_live)

    def get_filter_parameters(self) -> tuple[str, str, str]:
        return (
            self.filter_column.currentText(),
            self.filter_condition.currentData(),
            self.filter_value.text()
        )

    def set_filter_active_state(self, is_active: bool, message: str = "") -> None:
        """
        Updates the tab UI to reflect whether a filter is active

        :param is_active: True if a filter is active
        :param message: Optional message about the active filter
        """
        if is_active:
            self.filter_status_label.setText(f"Status: {message}")
            self.filter_status_label.setProperty("styleClass", "status_indicator_active")
        else:
            self.filter_status_label.setText("Status: No active filters")
            self.filter_status_label.setProperty("styleClass", "status_indicator_inactive")

        self.filter_status_label.style().unpolish(self.filter_status_label)
        self.filter_status_label.style().polish(self.filter_status_label)

    def update_filter_preview(self, filtered_count: int, total_count: int) -> None:
        """
        Updates the filter preview label to show how many rows would be affected by the current filter
        :param filtered_count: Number of rows that match the filter criteria
        :param total_count: The total number of rows in the dataset
        """
        if filtered_count == total_count or filtered_count == 0:
            self.filter_preview_label.setVisible(False)
            return

        percentage = (filtered_count / total_count * 100) if total_count > 0 else 0
        preview_text = f"This will filter to {filtered_count:,} rows ({percentage:.0f}% of the data)"
        self.filter_preview_label.setText(preview_text)
        self.filter_preview_label.setVisible(True)

        self.filter_preview_label.style().unpolish(self.filter_preview_label)
        self.filter_preview_label.style().polish(self.filter_preview_label)

    def clear_filter_preview(self) -> None:
        """Clears and hides the filter preview label"""
        self.filter_preview_label.setText("")
        self.filter_preview_label.setVisible(False)
