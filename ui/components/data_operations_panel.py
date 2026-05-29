from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QHBoxLayout, QPushButton
from PyQt6.QtGui import QIcon

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ui.controllers.data_tab_controller import DataTabController

from core.resource_loader import get_resource_path
from ui.icons import IconBuilder, IconType
from ui.theme import ThemeColors

from ui.components.data_tabs import CleaningTab, FilteringTab, ColumnsTab, TransformTab, DatetimeTab, SubsetsTab, HistoryTab

class DataOperationsPanel(QWidget):
    """
    Operations Panel for the datatab
    """
    def __init__(self, parent=None, controller: Optional["DataTabController"] = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.init_ui()
    
    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        reset_button = QPushButton("Reset to Original")
        reset_button.setObjectName("DestructiveButton")
        reset_button.setIcon(IconBuilder.build(IconType.Redo))
        reset_button.clicked.connect(self.controller.reset_data)
        top_bar_layout.addWidget(reset_button)
        layout.addLayout(top_bar_layout)
        
        self.ops_tabs = QTabWidget()
        self.ops_tabs.setObjectName("ops_tabs")
        
        self.cleaning_tab = CleaningTab(self, self.controller)
        self.filtering_tab = FilteringTab(self, self.controller)
        self.columns_tab = ColumnsTab(self, self.controller)
        self.transform_tab = TransformTab(self, self.controller)
        self.subsets_tab = SubsetsTab(self, self.controller)
        self.datetime_tab = DatetimeTab(self, self.controller)
        self.history_tab = HistoryTab(self, self.controller)
        
        self.ops_tabs.addTab(self.cleaning_tab, IconBuilder.build(IconType.DataCleaning), "Data Cleaning")
        self.ops_tabs.addTab(self.filtering_tab, IconBuilder.build(IconType.Filter), "Filter Data")
        self.ops_tabs.addTab(self.columns_tab, IconBuilder.build(IconType.EditColumns), "Columns")
        self.ops_tabs.addTab(self.transform_tab, IconBuilder.build(IconType.DataTransform), "Transform")
        self.ops_tabs.addTab(self.datetime_tab, IconBuilder.build(IconType.DatetimeTools), "Datetime Tools")
        self.ops_tabs.addTab(self.subsets_tab, QIcon(get_resource_path("icons/data_operations/subset.png")), "Subsets") #TODO Change this icon
        self.ops_tabs.addTab(self.history_tab, IconBuilder.build(IconType.History), "History")
        
        layout.addWidget(self.ops_tabs)
    
    # Getters
    def get_filter_parameters(self) -> tuple[str, str, str]:
        return self.filtering_tab.get_filter_parameters()
    
    def get_selected_columns(self) -> list[str]:
        return self.columns_tab.get_selected_columns()
    
    def get_target_datatype(self) -> str:
        return self.columns_tab.get_target_datatype()
    
    def get_text_operation(self) -> str:
        return self.columns_tab.get_text_operation()
    
    def get_normalization_method(self) -> str:
        return self.columns_tab.get_normalization_method()
    
    def get_sort_parameters(self) -> tuple[str, str]:
        return self.transform_tab.get_sort_parameters()
    
    def get_date_extraction_parameters(self) -> tuple[str, str]:
        return self.datetime_tab.get_date_extraction_parameters()
    
    def get_date_diff_parameters(self) -> tuple[str, str, str]:
        return self.datetime_tab.get_date_diff_parameters()
    
    def get_quick_subset_column(self) -> str:
        return self.subsets_tab.get_quick_subset_column()
    
    def get_selected_saved_aggregation(self) -> Optional[str]:
        return self.transform_tab.get_selected_saved_aggregations()
    
    def get_selected_active_subset(self) -> Optional[str]:
        return self.subsets_tab.get_selected_active_subset()
    
    def get_selected_history_index(self) -> Optional[int]:
        return self.history_tab.get_selected_history_index()
    
    def update_saved_aggregation_list(self, aggregations: list[tuple[str, int]]) -> None:
        self.transform_tab.update_saved_aggregation_list(aggregations)
    
    def set_aggregation_buttons_enabled(self, enabled: bool) -> None:
        self.transform_tab.set_aggregations_buttons_enabled(enabled)
    
    def update_active_subsets_list(self, subsets: list[tuple[str, str]]) -> None:
        self.subsets_tab.update_active_subsets_list(subsets)
    
    def set_injection_status_ui(self, is_subset_active: bool, subset_name: str = "") -> None:
        self.subsets_tab.set_injection_status_ui(is_subset_active, subset_name)
    
    def select_history_item_by_index(self, target_index: int) -> None:
        self.history_tab.select_history_item_by_index(target_index)