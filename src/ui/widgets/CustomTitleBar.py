import logging
from typing import Optional

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMenuBar, QSizePolicy, QWidget

from icons.icon_registry import IconBuilder, IconType

logger = logging.getLogger(__name__)

class CustomTitleBar(QWidget):
    """
    Provides a custom frameless title bar interface

    Constians the image of the Aletheia logo and the menu bar
    """

    def __init__(self, parent: QWidget, menu_bar: QMenuBar) -> None:
        super().__init__(parent)
        self._parent_window: QWidget = parent
        self._menu_bar: QMenuBar = menu_bar
        self._drag_position: Optional[QPoint] = None
        self._init_ui()

    def _init_ui(self) -> None:
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)

        icon_size_XY: int = 36
        self.logo_label = QLabel(parent=self)
        self.logo_label.setPixmap(IconBuilder.build(IconType.AppIcon).pixmap(icon_size_XY, icon_size_XY))
        self.logo_label.setFixedSize(icon_size_XY, icon_size_XY)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.logo_label)

        self._menu_bar.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._menu_bar)
        layout.addStretch()
