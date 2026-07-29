import math

from PyQt6.QtCore import QEasingCurve, QPointF, QRectF, QVariantAnimation, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QMouseEvent, QPaintEvent, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

class AnnotationLocatorWidget(QWidget):
    """
    A 2D proxy canvas that visually represents the 0.0 to 1.0 coordinate space
    of a Matplotlib canvas.
    Used to position text annotations and pointer arrows.
    """

    textPositionChanged = pyqtSignal(float, float)
    targetPositionChanged = pyqtSignal(float, float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AnnotationLocatorWidget")

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(200)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._aspect_ratio: float = 1.0

        self.text_pos = QPointF(0.5, 0.5)
        self.target_pos = QPointF(0.5, 0.4)

        self.has_arrow: bool = False
        self.text_color: QColor = QColor("black")

        self._dragged_node: str | None = None
        self._text_animation: QVariantAnimation | None = None
        self._target_animation: QVariantAnimation | None = None
        self._animation_duration: int = 250

    #####
    # Public setters that triggers the points moving animation
    #####

    def set_arrow_enabled(self, enabled: bool) -> None:
        """Toggles the rendering of the secondary target node and the connection line"""
        if self.has_arrow != enabled:
            self.has_arrow = enabled
            self.update()

    def set_text_color(self, color: QColor) -> None:
        """Updates the text node color to match the chosen font color"""
        if self.text_color != color:
            self.text_color = color
            self.update()

    def set_canvas_dimensions(self, width: float, height: float) -> None:
        """
        Updates the proxy canvas dimensions to match the target figure's aspect ratio
        """
        if width <= 0 or height <= 0:
            return

        self._aspect_ratio = width / height
        self.update()

    def _get_canvas_rect(self) -> QRectF:
        """Calculates the centered active canvas area based on the current aspect ratio"""
        widget_width, widget_height = self.width(), self.height()

        target_height = widget_height
        target_width = target_height * self._aspect_ratio

        if target_width > widget_width:
            target_width = widget_width
            target_height = target_width / self._aspect_ratio

        x = (widget_width - target_width) / 2.0
        y = (widget_height - target_height) / 2.0

        return QRectF(x, y, target_width, target_height)

    def set_text_pos(self, x: float, y: float) -> None:
        """Sets the text origin and animates to a new position if changed"""
        if self._dragged_node == "text":
            return

        new_pos = QPointF(x, y)
        if self.text_pos == new_pos:
            return

        if self._text_animation and self._text_animation.state() == QVariantAnimation.State.Running:
            self._text_animation.stop()

        self._text_animation = QVariantAnimation(self)
        self._text_animation.setStartValue(self.text_pos)
        self._text_animation.setEndValue(new_pos)
        self._text_animation.setDuration(self._animation_duration)
        self._text_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._text_animation.valueChanged.connect(self._on_text_animation_step)
        self._text_animation.start()

    def set_target_pos(self, x: float, y: float) -> None:
        """Sets the arrow target and animates to the new position if changed"""
        if self._dragged_node == "target":
            return

        new_pos = QPointF(x, y)
        if self.target_pos == new_pos:
            return

        if self._target_animation and self._target_animation.state() == QVariantAnimation.State.Running:
            self._target_animation.stop()

        self._target_animation = QVariantAnimation(self)
        self._target_animation.setStartValue(self.target_pos)
        self._target_animation.setEndValue(new_pos)
        self._target_animation.setDuration(self._animation_duration)
        self._target_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._target_animation.valueChanged.connect(self._on_target_animation_step)
        self._target_animation.start()

    def _on_text_animation_step(self, value: QPointF) -> None:
        self.text_pos = value
        self.update()

    def _on_target_animation_step(self, value: QPointF) -> None:
        self.target_pos = value
        self.update()

    #####
    # Mouse Event Handlers
    ## Handles the mouse Press, the move and the release of a point
    ## Hit Detection and dragging events
    #####

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Detects a click on a node to being a drag operation"""
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._text_animation and self._text_animation.state() == QVariantAnimation.State.Running:
            self._text_animation.stop()
        if self._target_animation and self._target_animation.state() == QVariantAnimation.State.Running:
            self._target_animation.stop()

        local_pos = self.mapFromGlobal(event.globalPosition().toPoint())
        click_pos = QPointF(local_pos.x(), local_pos.y())
        p_text = self._to_px(self.text_pos)
        p_target = self._to_px(self.target_pos)

        # Give priority to arrow target node
        if self.has_arrow:
            dist_target = math.hypot(click_pos.x() - p_target.x(), click_pos.y() - p_target.y())
            if dist_target < 15:
                self._dragged_node = "target"
                return

        dist_text = math.hypot(click_pos.x() - p_text.x(), click_pos.y() - p_text.y())
        if dist_text < 15:
            self._dragged_node = "text"
            return

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Updates the internal coordinates and emits signal while dragging nodes"""
        if not self._dragged_node:
            return

        local_pos = self.mapFromGlobal(event.globalPosition().toPoint())
        px = QPointF(local_pos.x(), local_pos.y())
        new_pos = self._to_pos(px)
        # Clamping to a 0.0-1.0 to not lose nodes outside canvas
        clamped_x = max(0.0, min(1.0, new_pos.x()))
        clamped_y = max(0.0, min(1.0, new_pos.y()))
        clamped_pos = QPointF(clamped_x, clamped_y)

        if self._dragged_node == "text":
            self.text_pos = clamped_pos
            self.textPositionChanged.emit(clamped_x, clamped_y)
        elif self._dragged_node == "target":
            self.target_pos = clamped_pos
            self.targetPositionChanged.emit(clamped_x, clamped_y)

        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Releases the currently grabbed node"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragged_node = None

    #####
    # Coordinate mapping and rendering
    ## Rendering paintEvent
    ####

    def _to_px(self, pos: QPointF) -> QPointF:
        """Maps 0-1 Matplotlib space to pixel space"""
        rect = self._get_canvas_rect()
        px_x = rect.x() + (pos.x() * rect.width())
        px_y = rect.y() + (rect.height() - (pos.y() * rect.height()))
        return QPointF(px_x, px_y)

    def _to_pos(self, px: QPointF) -> QPointF:
        """Maps pixel space to 0-1 Matplotlib space"""
        rect = self._get_canvas_rect()
        if rect.width() == 0 or rect.height() == 0:
            return QPointF(0, 0)

        x = (px.x() - rect.x()) / rect.width()
        y = (rect.bottom() - px.y()) / rect.height()
        return QPointF(x, y)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self._get_canvas_rect()

        painter.fillRect(self.rect(), QColor(100, 100, 100, 15))
        painter.fillRect(rect, QColor(128, 128, 128, 40))

        border_pen = QPen(QColor(150, 150, 150), 1)
        painter.setPen(border_pen)
        painter.drawRect(rect)

        grid_pen = QPen(QColor(150, 150, 150, 80))
        grid_pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)

        for i in [1, 2, 3]:
            vx = rect.x() + (rect.width() * (i / 4.0))
            painter.drawLine(QPointF(vx, rect.y()), QPointF(vx, rect.bottom()))
            vy = rect.y() + (rect.height() * (i / 4.0))
            painter.drawLine(QPointF(rect.x(), vy), QPointF(rect.right(), vy))

        p_text = self._to_px(self.text_pos)
        p_target = self._to_px(self.target_pos)

        if self.has_arrow:
            line_pen = QPen(QColor(150, 150, 150), 2)
            painter.setPen(line_pen)
            painter.drawLine(p_text, p_target)

            painter.setBrush(QBrush(QColor(128, 128, 128, 200)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(QRectF(p_target.x() - 4, p_target.y() - 4, 8, 8))

        painter.setBrush(QBrush(self.text_color))
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1.5))
        painter.drawEllipse(p_text, 7, 7)

        t_color = Qt.GlobalColor.black if self.text_color.lightness() > 150 else Qt.GlobalColor.white
        painter.setPen(QPen(t_color))

        font = painter.font()
        font.setPixelSize(10)
        font.setBold(True)
        painter.setFont(font)

        text_rect = QRectF(p_text.x() - 7, p_text.y() - 7, 14, 14)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "T")
