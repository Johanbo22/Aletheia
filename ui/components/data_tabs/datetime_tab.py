from PyQt6.QtWidgets import QVBoxLayout, QLabel
from typing import Optional, TYPE_CHECKING

from ui.components.data_tabs.base_data_tab import BaseDataTab
from ui.widgets.ControlElements import DataPlotStudioComboBox
from ui.icons import IconType
from ui.widgets.ControlElements import DataPlotStudioGroupBox

if TYPE_CHECKING:
    from ui.controllers.data_tab_controller import DataTabController

class DatetimeTab(BaseDataTab):
    def __init__(self, parent=None, controller: Optional["DataTabController"] = None) -> None:
        super().__init__(parent, controller)
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        dt_info = QLabel("Extract date components from dates or calculate duration between datetime columns")
        dt_info.setWordWrap(True)
        dt_info.setProperty("styleClass", "info_text")
        layout.addWidget(dt_info)
        
        extract_group = DataPlotStudioGroupBox("Extract Date Components")
        extract_layout = QVBoxLayout()
        
        extract_layout.addWidget(QLabel("Source Date Columns:"))
        self.dt_source_combo = DataPlotStudioComboBox()
        extract_layout.addWidget(self.dt_source_combo)
        
        extract_layout.addWidget(QLabel("Date Component to Extract:"))
        self.dt_component_combo = DataPlotStudioComboBox()
        self.dt_component_combo.addItems(["Year", "Month", "Month Name", "Day", "Day of Week", "Quarter", "Hour"])
        extract_layout.addWidget(self.dt_component_combo)
        
        extract_layout.addLayout(self._create_operation_row(
            title="Extract Component",
            tooltip="Create a new column containing the selected time component",
            callback=self.controller.extract_date_component,
            help_id="extract_date",
            icon_type=IconType.DataTransform
        ))
        extract_group.setLayout(extract_layout)
        layout.addWidget(extract_group)
        
        layout.addSpacing(10)
        
        duration_group = DataPlotStudioGroupBox("Calculate Duration Difference")
        duration_layout = QVBoxLayout()
        
        duration_layout.addWidget(QLabel("Start Date Columns:"))
        self.dt_start_combo = DataPlotStudioComboBox()
        duration_layout.addWidget(self.dt_start_combo)
        
        duration_layout.addWidget(QLabel("End Date Column:"))
        self.dt_end_combo = DataPlotStudioComboBox()
        duration_layout.addWidget(self.dt_end_combo)
        
        duration_layout.addWidget(QLabel("Result Unit:"))
        self.dt_unit_combo = DataPlotStudioComboBox()
        self.dt_unit_combo.addItems(["Days", "Weeks", "Hours", "Minutes", "Seconds"])
        duration_layout.addWidget(self.dt_unit_combo)

        duration_layout.addLayout(self._create_operation_row(
            title="Calculate Duration",
            tooltip="Create a new column with the time difference between two datetime columns",
            callback=self.controller.calculate_date_difference,
            help_id="date_duration",
            icon_type=IconType.Calculator
        ))
        
        duration_group.setLayout(duration_layout)
        layout.addWidget(duration_group)
        layout.addStretch()
        
    def get_date_extraction_parameters(self) -> tuple[str, str]:
        return (self.dt_source_combo.currentText(), self.dt_component_combo.currentText())
    
    def get_date_diff_parameters(self) -> tuple[str, str, str]:
        return (
            self.dt_start_combo.currentText(),
            self.dt_end_combo.currentText(),
            self.dt_unit_combo.currentText()
        )