from PyQt6.QtWidgets import QVBoxLayout, QLabel, QFormLayout
from typing import Optional, TYPE_CHECKING

from ui.components.data_tabs.base_data_tab import BaseDataTab
from ui.icons import IconType
from ui.widgets.ControlElements import DataPlotStudioComboBox, DataPlotStudioLineEdit, DataPlotStudioGroupBox

if TYPE_CHECKING:
    from ui.controllers.data_tab_controller import DataTabController
    
class FilteringTab(BaseDataTab):
    def __init__(self, parent=None, controller: Optional["DataTabController"] = None) -> None:
        super().__init__(parent, controller)
        self.init_ui()
    
    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        filter_info = QLabel("Filter your dataset by defining criteria. Use the Quick Filter for single conditions, or the Advanced Filter for complex, multi-conditional queries.")
        filter_info.setWordWrap(True)
        filter_info.setProperty("styleClass", "info_text")
        layout.addWidget(filter_info)
        layout.addSpacing(10)
        
        quick_filter_group = DataPlotStudioGroupBox("Quick Filter")
        quick_filter_layout = QVBoxLayout(quick_filter_group)
        quick_filter_layout.setSpacing(12)
        
        form_layout = QFormLayout()
        
        self.filter_column = DataPlotStudioComboBox()
        self.filter_column.setToolTip("Select the column you wish to apply a filter to")
        form_layout.addRow(QLabel("Column:"), self.filter_column)
        
        self.filter_condition = DataPlotStudioComboBox()
        self.filter_condition.addItems(["==", "!=", ">", "<", ">=", "<=", "contains"])
        self.filter_condition.setToolTip("Select which conditional to apply to column. N.B. Uses Python Syntax")
        form_layout.addRow(QLabel("Condition:"), self.filter_condition)
        
        self.filter_value = DataPlotStudioLineEdit()
        self.filter_value.setPlaceholderText("Enter evaluation value...")
        self.filter_value.setToolTip("Enter the value you want the column to be evaluated to.\nNote: Reference your data. This is case-sensitive")
        form_layout.addRow(QLabel("Value:"), self.filter_value)
        
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
        
        advanced_filter_group = DataPlotStudioGroupBox("Advanced Filter")
        advanced_filter_layout = QVBoxLayout(advanced_filter_group)
        advanced_filter_layout.setSpacing(12)
        
        advanced_filter_layout.addLayout(self._create_operation_row(
            title="Advanced Filter",
            tooltip="Open the advanced multi-conditional filter to build more complex filters",
            callback=self.controller.open_advanced_filter,
            help_id="advanced_filter",
            icon_type=IconType.AdvancedFilter
        ))
        layout.addWidget(advanced_filter_group)
        
        layout.addStretch()
    
    def get_filter_parameters(self) -> tuple[str, str, str]:
        return (
            self.filter_column.currentText(),
            self.filter_condition.currentText(),
            self.filter_value.text()
        )