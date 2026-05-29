from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QListWidgetItem, QListWidget, QGroupBox, QComboBox, QPushButton
from PyQt6.QtCore import Qt
from typing import Optional, TYPE_CHECKING

from ui.components.data_tabs.base_data_tab import BaseDataTab
from ui.icons import IconBuilder, IconType
from ui.theme import ThemeColors

if TYPE_CHECKING:
    from ui.controllers.data_tab_controller import DataTabController

class SubsetsTab(BaseDataTab):
    def __init__(self, parent=None, controller: Optional["DataTabController"] = None) -> None:
        super().__init__(parent, controller)
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)

        subset_info = QLabel("This tab allows you to create and manage data subsets.")
        subset_info.setWordWrap(True)
        subset_info.setProperty("styleClass", "info_text")
        layout.addWidget(subset_info)
        layout.addSpacing(10)

        layout.addLayout(self._create_operation_row(
            title="Manage Subsets",
            tooltip="Open Subset Manager",
            callback=self.controller.open_subset_manager,
            help_id="manage_subsets",
        ))
        layout.addSpacing(10)

        quick_subset_group = QGroupBox("Quick Subset Creation")
        quick_subset_layout = QVBoxLayout()

        combo_layout = QHBoxLayout()
        combo_label = QLabel("Split data by column values:")
        combo_layout.addWidget(combo_label)

        self.subset_column_combo = QComboBox()
        combo_layout.addWidget(self.subset_column_combo)

        quick_subset_layout.addLayout(combo_layout)

        quick_subset_layout.addLayout(self._create_operation_row(
            title="Auto-Create Subsets",
            tooltip="Split DataFrame into individual subsets",
            callback=self.controller.quick_create_subsets,
            help_id="auto_create_subsets",
        ))
        quick_subset_group.setLayout(quick_subset_layout)
        layout.addWidget(quick_subset_group)
        layout.addSpacing(10)

        subset_list_group = QGroupBox("Active Subsets")
        subset_list_layout = QVBoxLayout()

        self.active_subsets_list = QListWidget()
        self.active_subsets_list.setMaximumHeight(150)
        self.active_subsets_list.itemDoubleClicked.connect(self.controller.view_subset_quick)
        subset_list_layout.addWidget(self.active_subsets_list)

        subset_list_btns = QHBoxLayout()
        subset_list_btns.addStretch()
        view_subset_btn = QPushButton("View", parent=self)
        view_subset_btn.setIcon(IconBuilder.build(IconType.ViewItem))
        view_subset_btn.clicked.connect(self.controller.view_subset_quick)
        subset_list_btns.addWidget(view_subset_btn)

        self.refresh_subsets_btn = QPushButton("Refresh", parent=self)
        self.refresh_subsets_btn.setIcon(IconBuilder.build(IconType.RefreshItem))
        self.refresh_subsets_btn.clicked.connect(self.controller.refresh_active_subsets)
        subset_list_btns.addWidget(self.refresh_subsets_btn)
        subset_list_layout.addLayout(subset_list_btns)
        subset_list_group.setLayout(subset_list_layout)
        layout.addWidget(subset_list_group)
        layout.addSpacing(10)

        inject_group = QGroupBox("View Subset as Active DataFrame")
        inject_layout = QVBoxLayout()

        inject_info = QLabel("Insert the selected subset into the active DataFrame to work directly with it.")
        inject_info.setWordWrap(True)
        inject_info.setProperty("styleClass", "warning_info_text")
        inject_layout.addWidget(inject_info)
        inject_layout.addSpacing(10)

        self.inject_subset_btn = QPushButton("Insert Selected Subset")
        self.inject_subset_btn.setObjectName("MainActionButton")
        self.inject_subset_btn.clicked.connect(self.controller.inject_subset_to_dataframe)
        inject_layout.addWidget(self.inject_subset_btn)

        self.injection_status_label = QLabel("Status: Working with original data")
        self.injection_status_label.setObjectName("injection_status_label")
        self.injection_status_label.setProperty("statusState", "success")
        self.injection_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inject_layout.addWidget(self.injection_status_label)
        inject_layout.addSpacing(10)

        self.restore_original_btn = QPushButton("Revert to Original Data View")
        self.restore_original_btn.setObjectName("DestructiveButton")
        self.restore_original_btn.clicked.connect(self.controller.restore_original_dataframe)
        self.restore_original_btn.setEnabled(False)
        inject_layout.addWidget(self.restore_original_btn)

        inject_group.setLayout(inject_layout)
        layout.addWidget(inject_group)
        layout.addStretch()

    def get_quick_subset_column(self) -> str:
        return self.subset_column_combo.currentText()

    def get_selected_active_subset(self) -> Optional[str]:
        item = self.active_subsets_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def update_active_subsets_list(self, subsets: list[tuple[str, str]]) -> None:
        self.active_subsets_list.clear()
        for name, row_text in subsets:
            item = QListWidgetItem(f"{name} ({row_text})")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.active_subsets_list.addItem(item)
    
    def set_injection_status_ui(self, is_subset_active: bool, subset_name: str = "") -> None:
        if is_subset_active:
            self.injection_status_label.setText(f"Status: Working with a subset: '{subset_name}'")
            self.injection_status_label.setProperty("statusState", "warning")
            self.restore_original_btn.setEnabled(True)
            self.inject_subset_btn.setEnabled(False)
            self.refresh_subsets_btn.setEnabled(False)
        else:
            self.injection_status_label.setText("Status: Working with original data")
            self.injection_status_label.setProperty("statusState", "success")
            self.restore_original_btn.setEnabled(False)
            self.inject_subset_btn.setEnabled(True)
            self.refresh_subsets_btn.setEnabled(True)
        
        self.injection_status_label.style().unpolish(self.injection_status_label)
        self.injection_status_label.style().polish(self.injection_status_label)