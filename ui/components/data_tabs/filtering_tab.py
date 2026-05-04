from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget
from typing import Optional, TYPE_CHECKING

from ui.components.data_tabs.base_data_tab import BaseDataTab
from ui.widgets import DataPlotStudioButton
from ui.icons import IconType, IconBuilder
from ui.widgets.ControlElements import DataPlotStudioComboBox, DataPlotStudioLineEdit

if TYPE_CHECKING:
    from ui.controllers.data_tab_controller import DataTabController
    
class FilteringTab(BaseDataTab):
    def __init__(self, parent=None, controller: Optional["DataTabController"] = None) -> None:
        super().__init__(parent, controller)
        self.init_ui()
    
    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        filter_info = QLabel("This tab has operations to help you filter your dataset based on own criteria. Use the 'Advanced Filter' dialog to apply more than one filter")
        filter_info.setWordWrap(True)
        filter_info.setProperty("styleClass", "info_text")
        layout.addWidget(filter_info)
        
        layout.addWidget(QLabel("Column:"))
        filter_column_info = QLabel("Select the column you wish to apply a filter to")
        filter_column_info.setWordWrap(True)
        filter_column_info.setProperty("styleClass", "info_text")
        layout.addWidget(filter_column_info)
        
        self.filter_column = DataPlotStudioComboBox()
        layout.addWidget(self.filter_column)
        
        layout.addWidget(QLabel("Condition:"))
        filter_condition_info = QLabel("Select which conditional to apply to column. N.B. Uses Python Syntax")
        filter_condition_info.setProperty("styleClass", "info_text")
        filter_condition_info.setWordWrap(True)
        layout.addWidget(filter_condition_info)
        
        self.filter_condition = DataPlotStudioComboBox()
        self.filter_condition.addItems(["==", "!=", ">", "<", ">=", "<=", "contains"])
        layout.addWidget(self.filter_condition)
        
        layout.addWidget(QLabel("Value:"))
        filter_value_info = QLabel("Enter the value you want the column to be evaluated to.\nNote: Reference your data. This is case-sensitive")
        filter_value_info.setWordWrap(True)
        filter_value_info.setProperty("styleClass", "info_text")
        layout.addWidget(filter_value_info)
        
        self.filter_value = DataPlotStudioLineEdit()
        layout.addWidget(self.filter_value)
        
        layout.addLayout(self._create_operation_row(
            title="Apply Filter",
            tooltip="Apply the configured filter",
            callback=self.controller.apply_filter,
            help_id="apply_filter",
            icon_type=IconType.Filter
        ))
        
        clear_filter_layout = QHBoxLayout()
        clear_filter_button = DataPlotStudioButton("Clear Filters", parent=self)
        clear_filter_button.setToolTip("Reset the dataset to its original state and remove the filters")
        clear_filter_button.setIcon(IconBuilder.build(IconType.ClearFilter))
        clear_filter_button.clicked.connect(self.controller.clear_filters)
        
        placeholder = QWidget()
        placeholder.setFixedSize(24, 24)
        clear_filter_layout.addWidget(clear_filter_button)
        clear_filter_layout.addWidget(placeholder)
        layout.addLayout(clear_filter_layout)
        
        layout.addSpacing(10)
        
        layout.addLayout(self._create_operation_row(
            title="Advanced Filter",
            tooltip="Open the advanced multi-conditional filter to build more complex filters",
            callback=self.controller.open_advanced_filter,
            help_id="apply_filter",
            icon_type=IconType.AdvancedFilter
        ))
        layout.addStretch()
    
    def get_filter_parameters(self) -> tuple[str, str, str]:
        return (
            self.filter_column.currentText(),
            self.filter_condition.currentText(),
            self.filter_value.text()
        )