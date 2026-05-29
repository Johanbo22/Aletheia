from PyQt6.QtWidgets import QVBoxLayout, QLabel, QGroupBox
from typing import Optional, TYPE_CHECKING

from ui.components.data_tabs.base_data_tab import BaseDataTab
from ui.icons import IconType

if TYPE_CHECKING:
    from ui.controllers.data_tab_controller import DataTabController

class CleaningTab(BaseDataTab):
    """
    Tab widget for data cleaning operations
    Index 0 in DataTab
    """
    def __init__(self, parent=None, controller: Optional["DataTabController"] = None) -> None:
        super().__init__(parent, controller)
        self.init_ui()
    
    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        clean_info = QLabel("This tab includes operations to clean your dataset")
        clean_info.setWordWrap(True)
        clean_info.setProperty("styleClass", "info_text")
        layout.addWidget(clean_info)

        basic_group = QGroupBox("Basic Operations")
        basic_layout = QVBoxLayout()
        
        basic_layout.addLayout(self._create_operation_row(
            title="Remove Duplicate Rows",
            tooltip="Use this to remove any instances of duplicate row entries in your dataset",
            callback=self.controller.remove_duplicates,
            help_id="remove_duplicates",
            icon_type=IconType.RemoveDuplicates,
            button_stretch=1
        ))
        basic_layout.addLayout(self._create_operation_row(
            title="Drop Missing Values",
            tooltip="Use this to remove rows in your dataset with incomplete entries",
            callback=self.controller.drop_missing,
            help_id="drop_missing",
            icon_type=IconType.DropMissingValues,
            button_stretch=1
        ))
        basic_layout.addLayout(self._create_operation_row(
            title="Fill Missing Values",
            tooltip="Use this to fill in 'NaN' values in your dataset with something else",
            callback=self.controller.fill_missing,
            help_id="fill_missing",
            icon_type=IconType.FillMissingValues,
            button_stretch=1
        ))
        basic_layout.addLayout(self._create_operation_row(
            title="Drop Empty Columns",
            tooltip="Removes columns where all rows have missing values (NaN/NaT)",
            callback=self.controller.drop_empty_columns,
            help_id="drop_empty_columns",
            icon_type=IconType.DropColumn,
            button_stretch=1
        ))
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        layout.addSpacing(10)
        
        outlier_group = QGroupBox("Outlier Detection Tools")
        outlier_layout = QVBoxLayout()
        
        outlier_layout.addLayout(self._create_operation_row(
            title="Z-Score",
            tooltip="Detect outliers using Z-Score (Standard Deviations from mean)",
            callback=(lambda: self.controller.open_outlier_dialog("z_score")),
            help_id="zscore",
            button_stretch=1
        ))
        outlier_layout.addLayout(self._create_operation_row(
            title="Interquartile Range (IQR)",
            tooltip="Detect outliers using the Interquartile Range method",
            callback=lambda: self.controller.open_outlier_dialog("iqr"),
            help_id="iqr",
            button_stretch=1
        ))
        outlier_layout.addLayout(self._create_operation_row(
            title="Isolation Forest",
            tooltip="Detect outliers using Machine Learning (Isolation Forest Method)",
            callback=(lambda: self.controller.open_outlier_dialog("isolation_forest")),
            help_id="isolation_forest",
            button_stretch=1
        ))
        
        outlier_group.setLayout(outlier_layout)
        layout.addWidget(outlier_group)
        layout.addStretch()