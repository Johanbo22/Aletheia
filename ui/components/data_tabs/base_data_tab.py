from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QScrollArea, QFrame, QPushButton

from typing import Optional, Callable, TYPE_CHECKING

from ui.widgets import HelpIcon
from ui.icons import IconBuilder, IconType

if TYPE_CHECKING:
    from ui.controllers.data_tab_controller import DataTabController
    
class BaseDataTab(QWidget):
    """
    Base class for the general data ta b
    """
    def __init__(self, parent: Optional[QWidget] = None, controller: Optional["DataTabController"] = None) -> None:
        super().__init__(parent)
        self.controller = controller
    
    def setup_scrollable_layout(self) -> QVBoxLayout:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setProperty("styleClass", "transparent_scroll_area")
        
        container = QWidget()
        container.setObjectName("TransparentScrollContent")
        
        scrollable_layout = QVBoxLayout(container)
        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)
        return scrollable_layout
    
    def _create_operation_row(
        self,
        title: str,
        tooltip: str,
        callback: Optional[Callable],
        help_id: str,
        icon_type: Optional[IconType] = None,
        button_stretch: int = 0
    ) -> QHBoxLayout:
        """
        A setup for a general Horizontal box layout containing a button + helpicon
        """
        row_layout = QHBoxLayout()
        
        button = QPushButton(title, parent=self)
        button.setToolTip(tooltip)
        
        if icon_type is not None:
            button.setIcon(IconBuilder.build(icon_type))
        
        if callback is not None:
            button.clicked.connect(callback)
        
        help_icon = HelpIcon(help_id)
        if self.controller is not None:
            help_icon.clicked.connect(self.controller.show_help_dialog)
        
        row_layout.addWidget(button, button_stretch)
        row_layout.addWidget(help_icon)
        
        return row_layout