from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QGroupBox, QComboBox, QPushButton
from PyQt6.QtCore import Qt
from typing import Optional, TYPE_CHECKING

from ui.components.data_tabs.base_data_tab import BaseDataTab
from ui.icons import IconType, IconBuilder

if TYPE_CHECKING:
    from ui.controllers.data_tab_controller import DataTabController

class TransformTab(BaseDataTab):
    def __init__(self, parent=None, controller: Optional["DataTabController"] = None) -> None:
        super().__init__(parent, controller)
        self.init_ui()

    def init_ui(self) -> None:
        layout = self.setup_scrollable_layout()

        transform_info = QLabel("This tab allows you to alter your input data by using transformation tools")
        transform_info.setWordWrap(True)
        transform_info.setProperty("styleClass", "info_text")
        layout.addWidget(transform_info)
        layout.addSpacing(10)
        
        reshape_group = QGroupBox("Reshape && Group Data")
        reshape_layout = QVBoxLayout()

        reshape_layout.addLayout(self._create_operation_row(
            title="Aggregate Data",
            tooltip="Group and aggregate data",
            callback=self.controller.open_aggregation_dialog,
            help_id="aggregate_data",
            icon_type=IconType.DataTransform 
        ))

        reshape_layout.addLayout(self._create_operation_row(
            title="Melt/Unpivot Data",
            tooltip="Reshape wide data to long format",
            callback=self.controller.open_melt_dialog,
            help_id="melt_data",
            icon_type=IconType.PivotData
        ))
        
        reshape_layout.addLayout(self._create_operation_row(
            title="Pivot Table",
            tooltip="Reshape data using index, columns and values",
            callback=self.controller.open_pivot_dialog,
            help_id="pivot_data",
            icon_type=IconType.DataTransform
        ))
        reshape_group.setLayout(reshape_layout)
        layout.addWidget(reshape_group)
        
        combine_group = QGroupBox("Combine Datasets")
        combine_layout = QVBoxLayout()
        
        combine_layout.addLayout(self._create_operation_row(
            title="Merge / Join Datasets",
            tooltip="Join the current dataset with another file",
            callback=self.controller.open_merge_dialog,
            help_id="merge_data",
            icon_type=IconType.ImportFile
        ))
        
        combine_layout.addLayout(self._create_operation_row(
            title="Append / Concatenate Data",
            tooltip="Stack datasets vertically by appending rows from another file",
            callback=self.controller.open_append_dialog,
            help_id="append_data",
            icon_type=IconType.ImportFile
        ))
        combine_group.setLayout(combine_layout)
        layout.addWidget(combine_group)
        
        sequential_group = QGroupBox("Sequential && Time-Series")
        sequential_layout = QVBoxLayout()
        
        sequential_layout.addLayout(self._create_operation_row(
            title="Rolling Window",
            tooltip="Calculate rolling statistics (example: moving averages)",
            callback=self.controller.open_rolling_window_dialog,
            help_id="rolling_window",
            icon_type=IconType.DataTransform
        ))
        
        sequential_layout.addLayout(self._create_operation_row(
            title="Shift / Lag Data",
            tooltip="Shift index by desired number of periods",
            callback=self.controller.open_shift_dialog,
            help_id="shift_data",
            icon_type=IconType.DataTransform
        ))

        sequential_layout.addLayout(self._create_operation_row(
            title="Percentage Change",
            tooltip="Calculate fractional change between current and prior element",
            callback=self.controller.open_pct_change_dialog,
            help_id="percentage_change",
            icon_type=IconType.DataTransform
        ))
        sequential_group.setLayout(sequential_layout)
        layout.addWidget(sequential_group)

        # Sorting
        sorting_group = QGroupBox("Sort Data")
        sorting_layout = QVBoxLayout()
        sort_controls = QHBoxLayout()
        self.sort_column_combo = QComboBox()
        sort_controls.addWidget(self.sort_column_combo, 2)
        self.sort_order_combo = QComboBox()
        self.sort_order_combo.addItems(["Ascending", "Descending"])
        sort_controls.addWidget(self.sort_order_combo, 1)
        sorting_layout.addLayout(sort_controls)
        
        sorting_layout.addLayout(self._create_operation_row(
            title="Sort Data",
            tooltip="Permanently sort dataset",
            callback=self.controller.apply_sort,
            help_id="sort_data",
            icon_type=IconType.Sort
        ))
        sorting_group.setLayout(sorting_layout)
        layout.addWidget(sorting_group)

        layout.addSpacing(10)

        # Saved Aggregations
        saved_agg_group = QGroupBox("Saved Aggregations")
        saved_agg_layout = QVBoxLayout()

        self.saved_agg_list = QListWidget()
        self.saved_agg_list.setMaximumHeight(150)
        self.saved_agg_list.itemClicked.connect(self.controller.on_saved_agg_selected)
        saved_agg_layout.addWidget(self.saved_agg_list)

        saved_agg_buttons = QHBoxLayout()
        self.view_agg_btn = QPushButton("View Aggregations", parent=self)
        self.view_agg_btn.setIcon(IconBuilder.build(IconType.ViewItem))
        self.view_agg_btn.setEnabled(False)
        self.view_agg_btn.clicked.connect(self.controller.view_saved_aggregations)
        saved_agg_buttons.addWidget(self.view_agg_btn)

        self.refresh_agg_list_btn = QPushButton("Refresh", parent=self)
        self.refresh_agg_list_btn.setIcon(IconBuilder.build(IconType.RefreshItem))
        self.refresh_agg_list_btn.clicked.connect(self.controller.refresh_saved_agg_list)
        saved_agg_buttons.addWidget(self.refresh_agg_list_btn)
        saved_agg_layout.addLayout(saved_agg_buttons)

        self.delete_agg_btn = QPushButton("Delete Selected Aggregation", parent=self)
        self.delete_agg_btn.setIcon(IconBuilder.build(IconType.DeleteItem))
        self.delete_agg_btn.setEnabled(False)
        self.delete_agg_btn.clicked.connect(self.controller.delete_saved_aggregation)
        saved_agg_layout.addWidget(self.delete_agg_btn)

        saved_agg_group.setLayout(saved_agg_layout)
        layout.addWidget(saved_agg_group)

        layout.addStretch()
    
    def get_sort_parameters(self) -> tuple[str, str]:
        return (self.sort_column_combo.currentText(), self.sort_order_combo.currentText())
    
    def get_selected_saved_aggregations(self) -> Optional[str]:
        item = self.saved_agg_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None
    
    def update_saved_aggregation_list(self, aggregations: list[tuple[str, int]]) -> None:
        from PyQt6.QtWidgets import QListWidgetItem
        self.saved_agg_list.clear()
        if not aggregations:
            placeholder = QListWidgetItem("No saved aggregations")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.saved_agg_list.addItem(placeholder)
            return
        
        for name, row_count in aggregations:
            item = QListWidgetItem(f"{name} ({row_count}) rows")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.saved_agg_list.addItem(item)
    
    def set_aggregations_buttons_enabled(self, enabled: bool) -> None:
        self.view_agg_btn.setEnabled(enabled)
        self.delete_agg_btn.setEnabled(enabled)