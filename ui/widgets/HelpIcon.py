from typing import Optional

from PyQt6.QtCore import QEasingCurve, QEvent, QPoint, QPropertyAnimation, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QEnterEvent, QMouseEvent
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from ui.help_animation_engine import load_help_animation_widget

class HelpAnimationPreviewPopup(QWidget):
    """
    A popup widget to preview the help animation
    on hover over the HelpIcon
    """

    def __init__(self, topic_id: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.topic_id = topic_id
        self._opacity_anim: Optional[QPropertyAnimation] = None
        self.animation_duration_ms: int = 200

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.container = QWidget(self)
        self.container.setObjectName("HelpDialogContent")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(10, 10, 10, 10)

        layout.addWidget(self.container)

        animation_widget = load_help_animation_widget(self.topic_id)
        container_layout.addWidget(animation_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setWindowOpacity(0.0)

    def show_with_animation(self, pos: QPoint) -> None:
        """Fades in the popup at the given global position"""
        self.move(pos)
        self.show()
        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self._opacity_anim.setDuration(self.animation_duration_ms)
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._opacity_anim.start()

    def hide_with_animation(self) -> None:
        """Fades out and closes the popup"""
        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self._opacity_anim.setDuration(self.animation_duration_ms)
        self._opacity_anim.setStartValue(self.windowOpacity())
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self._opacity_anim.finished.connect(self.close)
        self._opacity_anim.start()

class HelpIcon(QLabel):
    """Creates a clickable '?' that emits a signal to an id in the tutorial.db database"""

    clicked = pyqtSignal(str)

    def __init__(self, topic_id: str, parent: Optional[QWidget] = None, size: int = 18) -> None:
        """
        Args:
            topic_id (str): The ID to fetch from the tutorial database.
            parent: The parent widget
            size (int): The width and height of the icon
        """

        super().__init__(parent)
        self.topic_id = topic_id

        timer_interval: int = 600
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(timer_interval)
        self._hover_timer.timeout.connect(self._show_preview)

        self._preview_popup: Optional[HelpAnimationPreviewPopup] = None

        self.setObjectName("HelpIconWidget")
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click for help")

        self._text_label = QLabel("?", self)
        self._text_label.setFixedSize(size, size)
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._hover_anim = QPropertyAnimation(self._text_label, b"pos", self)
        self._hover_anim.setDuration(350)
        self._hover_anim.setStartValue(QPoint(0, 0))
        self._hover_anim.setKeyValueAt(0.4, QPoint(0, -3))
        self._hover_anim.setKeyValueAt(0.7, QPoint(0, 1))
        self._hover_anim.setEndValue(QPoint(0, 0))
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutQuad)

    def enterEvent(self, event: QEnterEvent) -> None:
        """Starts the hover timer to show the preview popup"""
        self._hover_timer.start()
        self._hover_anim.stop()
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        """Stops the hover timer and hides the preview popup if visible"""
        self._hover_timer.stop()
        if self._preview_popup is not None:
            self._preview_popup.hide_with_animation()
            self._preview_popup = None
        super().leaveEvent(event)

    def _show_preview(self) -> None:
        """Instantiates and shows the animation preview popup"""
        if self._preview_popup is None:
            self._preview_popup = HelpAnimationPreviewPopup(self.topic_id)

        cursor_pos = QCursor.pos()
        target_pos = cursor_pos + QPoint(15, 15)

        self._preview_popup.ensurePolished()
        self._preview_popup.adjustSize()
        popup_size = self._preview_popup.sizeHint()

        screen = QApplication.screenAt(cursor_pos)
        if screen:
            screen_geom = screen.availableGeometry()

            if target_pos.x() + popup_size.width() > screen_geom.right():
                target_pos.setX(cursor_pos.x() - popup_size.width() - 15)

            if target_pos.y() + popup_size.height() > screen_geom.bottom():
                target_pos.setY(cursor_pos.y() - popup_size.height() - 15)

        self._preview_popup.show_with_animation(target_pos)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._hover_timer.stop()

            if self._preview_popup is not None:
                self._preview_popup.hide_with_animation()
                self._preview_popup = None
            self.clicked.emit(self.topic_id)
        super().mousePressEvent(event)
