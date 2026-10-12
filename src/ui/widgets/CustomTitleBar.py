import logging
from typing import Optional

from PyQt6.QtCore import QPoint, QPointF, QRect, Qt
from PyQt6.QtGui import QMouseEvent, QScreen
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMenuBar, QPushButton, QSizePolicy, QStyle, QWidget

from icons.icon_registry import IconBuilder, IconType

logger = logging.getLogger(__name__)

class CustomTitleBar(QWidget):
    """
    Provides a custom frameless title bar interface

    Constians the image of the Aletheia logo, the menu bar and window controls from left to right.
    """

    def __init__(self, parent: QWidget, menu_bar: QMenuBar) -> None:
        super().__init__(parent)
        self._parent_window: QWidget = parent
        self._menu_bar: QMenuBar = menu_bar
        self._drag_position: Optional[QPoint] = None
        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("CustomTitleBar") # TODO (tim) adding styling
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

        button_size_XY: int = 32
        self.minimize_btn: QPushButton = QPushButton(parent=self)
        self.minimize_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMinButton))
        self.minimize_btn.clicked.connect(self._parent_window.showMinimized)

        self.maximize_btn: QPushButton = QPushButton(parent=self)
        self.maximize_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))
        self.maximize_btn.clicked.connect(self._toggle_maximize)

        self.close_btn: QPushButton = QPushButton(parent=self)
        self.close_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        self.close_btn.clicked.connect(self._parent_window.close)

        for button in (self.minimize_btn, self.maximize_btn, self.close_btn):
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setObjectName("TitleBarWindowControlButton")
            button.setFixedSize(button_size_XY, button_size_XY)

        layout.addWidget(self.minimize_btn)
        layout.addWidget(self.maximize_btn)
        layout.addWidget(self.close_btn)

    def _toggle_maximize(self) -> None:
        """Toggle the parent window between max and normal state"""
        if self._parent_window.isMaximized():
            self._parent_window.showNormal()
            self.maximize_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))
        else:
            self._parent_window.showMaximized()
            self.maximize_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Record the drag positon"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self._parent_window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Move the window to follow the cursor"""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_position is not None:
            if self._parent_window.isMaximized():
                self._parent_window.showNormal()
                self.maximize_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))

                # Shifting the drag anchor to make mouse remain in center of titlebar / caption
                width_ratio: float = event.position().x() / max(1, self.width())
                new_x: int = int(self._parent_window.width() * width_ratio)
                self._drag_position = QPoint(new_x, int(event.position().y()))

            new_pos: QPoint = event.globalPosition().toPoint() - self._drag_position
            self._parent_window.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Clear the drag position and handle screen snapping"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = None

            screen: QScreen = self.window().screen()
            if screen:
                screen_geometry: QRect = screen.availableGeometry()
                global_pos: QPointF = event.globalPosition()
                global_x: float = global_pos.x()
                global_y: float = global_pos.y()

                snap_threshold: int = 10

                if global_y <= screen_geometry.top() + snap_threshold:
                    self._parent_window.showMaximized()
                    self.maximize_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton))

                elif global_x <= screen_geometry.left() + snap_threshold:
                    self._parent_window.showNormal()
                    self.maximize_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))
                    new_width: int = screen_geometry.width() // 2
                    self._parent_window.setGeometry(
                        screen_geometry.left(), screen_geometry.top(), new_width, screen_geometry.height()
                    )

                elif global_x >= screen_geometry.right() - snap_threshold:
                    self._parent_window.showNormal()
                    self.maximize_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))
                    new_width: int = screen_geometry.width() // 2
                    self._parent_window.setGeometry(
                        screen_geometry.right() - new_width + 1, screen_geometry.top(), new_width,
                        screen_geometry.height()
                    )

            event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Maximise or restore the window on double click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()
            event.accept()
