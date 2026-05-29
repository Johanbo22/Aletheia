from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QGroupBox, QPushButton
from PyQt6.QtCore import Qt
from typing import Optional, TYPE_CHECKING

from ui.components.data_tabs.base_data_tab import BaseDataTab
from ui.icons import IconBuilder, IconType
from ui.widgets.PipelineGraphView import PipelineGraphView

if TYPE_CHECKING:
    from ui.controllers.data_tab_controller import DataTabController

class HistoryTab(BaseDataTab):
    def __init__(self, parent=None, controller: Optional["DataTabController"] = None) -> None:
        super().__init__(parent, controller)
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)

        history_info = QLabel("View and revert to a previous state of data state")
        history_info.setWordWrap(True)
        history_info.setProperty("styleClass", "info_text")
        layout.addWidget(history_info)

        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.controller.on_history_clicked)
        self.history_list.setVisible(False)
        layout.addWidget(self.history_list)

        self.pipeline_graph = PipelineGraphView(self)
        self.pipeline_graph.node_selected.connect(self._on_graph_node_selected)
        layout.addWidget(self.pipeline_graph)
        
        history_help = QLabel("Click on a state to go back/forwards to it.\nGray items are undone operations.")
        history_help.setWordWrap(True)
        history_help.setProperty("styleClass", "muted_text")
        layout.addWidget(history_help)
        
        macro_group = QGroupBox("Data Pipeline Macros")
        macro_layout = QVBoxLayout()
        macro_info = QLabel("Save your current sequence of data operations as a macro, or apply an existing macro to this dataset")
        macro_info.setWordWrap(True)
        macro_info.setProperty("styleClass", "info_text")
        macro_layout.addWidget(macro_info)
        
        macro_buttons_layout = QHBoxLayout()
        self.save_macro_btn = QPushButton("Save Macro", parent=self)
        self.save_macro_btn.setIcon(IconBuilder.build(IconType.SaveProject))
        self.save_macro_btn.clicked.connect(self.controller.save_pipeline_macro)
        macro_buttons_layout.addWidget(self.save_macro_btn)
        
        self.load_macro_btn = QPushButton("Apply Macro", parent=self)
        self.load_macro_btn.setIcon(IconBuilder.build(IconType.ImportFile))
        self.load_macro_btn.clicked.connect(self.controller.load_pipeline_macro)
        macro_buttons_layout.addWidget(self.load_macro_btn)
        
        macro_layout.addLayout(macro_buttons_layout)
        macro_group.setLayout(macro_layout)
        layout.addWidget(macro_group)

    def _on_graph_node_selected(self, node_id: str) -> None:
        if not self.controller:
            return
        self.controller.jump_to_history_state(node_id)

    def get_selected_history_index(self) -> Optional[str]:
        item = self.history_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def select_history_item_by_index(self, target_node_id: str) -> None:
        for i in range(self.history_list.count()):
            list_item = self.history_list.item(i)
            if list_item.data(Qt.ItemDataRole.UserRole) == target_node_id:
                self.history_list.setCurrentItem(list_item)
                break