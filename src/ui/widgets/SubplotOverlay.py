from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, pyqtProperty, QSequentialAnimationGroup, QPauseAnimation, QRectF, QPoint
from PyQt6.QtGui import QColor, QPainter, QPen, QPaintEvent
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class SubplotOverlay(QWidget):
    """
    A custom widget that paints a square around the currently active subplot

    When a single plot is configured a single box around that plot is painted.
    When multiple subplots are configured a label is painted in the middle of the
    bounding rect to tell which index the current subplot has (eg Plot 1,2,3 etc)
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._border_color: QColor = QColor("#2196F3")
        self._current_opacity: float = 1.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.hide()

        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.update_notice_label = QLabel("Data has changed. Click 'Generate Plot' to update")
        self.update_notice_label.setObjectName("update_notice_label")
        self.update_notice_label.hide()
        self.v_layout.addWidget(self.update_notice_label)
        
        self.label_widget = QLabel()
        self.label_widget.setObjectName("subplot_overlay_label")
        self.label_widget.setStyleSheet(self._get_label_style(1.0))
        self.v_layout.addWidget(self.label_widget)

        self.fade_animation = QPropertyAnimation(self, b"overlay_opacity")
        self.fade_animation.setDuration(1000)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.1)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        
        self.animation_sequence = QSequentialAnimationGroup(self)
        
        self.pause_animation = QPauseAnimation(1000, self)
        self.animation_sequence.addAnimation(self.pause_animation)
        self.animation_sequence.addAnimation(self.fade_animation)
        
        self.fade_animation.finished.connect(self._on_animation_finished)

    def _get_label_style(self, opacity: float) -> str:
        """
        Dynamically generates the style string to handle alpha fading.
        """
        alpha = int(opacity * 255)
        bg_alpha = int(opacity * 230)
        return (f"background-color: rgba(33, 150, 243, {bg_alpha}); "
                f"color: rgba(255, 255, 255, {alpha}); "
                "font-weight: 600; padding: 6px 12px; border-radius: 4px; "
                "font-size: 11pt; border: 1px solid rgba(255, 255, 255, 0.3);")

    @pyqtProperty(float)
    def overlay_opacity(self) -> float:
        return self._current_opacity
    
    @overlay_opacity.setter
    def overlay_opacity(self, value: float) -> None:
        self._current_opacity = value
        self.label_widget.setStyleSheet(self._get_label_style(value))
        self.update()
        
    @pyqtProperty(QColor)
    def border_color(self) -> QColor:
        return self._border_color
    
    @border_color.setter
    def border_color(self, color: QColor) -> None:
        self._border_color = color
        self.update()
    
    def show_update_required(self, visible: bool = True) -> None:
        """
        Shows or hides the update required notice overlay

        :param visible: Whether the notice should be visible.
        """
        self.update_notice_label.setVisible(visible)
        if visible:
            self.animation_sequence.stop()
            self.overlay_opacity = 1.0
            self.show()
        elif not self.label_widget.isVisible() and self.overlay_opacity == 1.0:
            self.hide()

    def _on_animation_finished(self) -> None:
        """
        Called when the fade animation completes.
        Hides the text label but retains the faint border values.
        """
        self.label_widget.hide()

    def update_info(self, text: str, geometry: tuple[int, int, int, int], is_resize: bool = False) -> None:
        """
        Updates the overlay text and geometry when subplot information changes.

        :param text: The text to display in the overlay.
        :param geometry: The geometry bounding box (x, y, width, height) for the overlay.
        :param is_resize: Flag indicating if the update is triggered by a resize event.
        """
        gx, gy, w, h = geometry
        if self.parentWidget():
            local_pos = self.parentWidget().mapFromGlobal(QPoint(gx, gy))
            self.setGeometry(local_pos.x(), local_pos.y(), w, h)
        else:
            self.setGeometry(gx, gy, w, h)

        self.raise_()

        if not is_resize:
            self.label_widget.setText(text)
            self.label_widget.show()
            self.show()

            self.animation_sequence.stop()
            self.overlay_opacity = 1.0
            self.animation_sequence.start()

    def paintEvent(self, event: QPaintEvent):
        """Draw a blue border around the subplot for the user to see"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setOpacity(self._current_opacity)
        #the draw duude
        pen = QPen(self._border_color)
        pen.setWidth(4)
        
        pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(pen)

        rect = QRectF(self.rect()).adjusted(2.0, 2.0, -2.0, -2.0)
        painter.drawRect(rect)