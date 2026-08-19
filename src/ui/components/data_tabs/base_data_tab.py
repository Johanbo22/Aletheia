from typing import Callable, Optional, TYPE_CHECKING

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from icons import IconBuilder, IconType
from src.ui.widgets import HelpIcon

if TYPE_CHECKING:
    from src.controller.data_tab_controller import DataTabController

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
        row_layout.setContentsMargins(0, 2, 0, 2)
        row_layout.setSpacing(6)

        button = QPushButton(title, parent=self)
        button.setToolTip(tooltip)

        if help_id:
            button.setObjectName(f"op_btn_{help_id}")

        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

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

    def apply_destructive_styling_tags(self, destructive_ids: list[str]) -> None:
        """
        Tags destructive buttons with a severity property
        """
        for btn_id in destructive_ids:
            btn: QPushButton = self.findChild(QPushButton, btn_id)
            if not btn:
                btn = self.findChild(QPushButton, f"op_btn_{btn_id}")
            if btn:
                btn.setProperty("actionSeverity", "destructive")
                btn.style().unpolish(btn)
                btn.style().polish(btn)
