from typing import Optional

from PyQt6.QtCore import QEasingCurve, QEvent, QPoint, QPointF, QPropertyAnimation, QRect, QRectF, QSize, Qt, \
    pyqtProperty
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPaintEvent, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QCheckBox, QWidget

from src.ui.theme import ThemeColors
from src.ui.widgets.mixins import HoverFocusAnimationMixin

class ToggleSwitch(HoverFocusAnimationMixin, QCheckBox):
    """
    A custom animated toggle switch widget

    This widget extends QCheckBox to provide a modern, animated toggle switch
    visual interface. It handles custom rendering, including animated transitions
    for the toggle handle, color interpretation, and hover/focus states.
    Styling is driven by runtime QPaintEvent rendering.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Sets up the default dimensions, internal margins, and the property
        animation responsible for the handle sliding effect

        :param parent: The parent widget, if any
        """
        QCheckBox.__init__(self, parent)

        HoverFocusAnimationMixin.__init__(self)

        self._track_height = 22
        self._track_width = 40
        self._margin = 4
        self._spacing = 8

        self._handle_position = 1.0 if self.isChecked() else 0.0

        self._handle_animation = QPropertyAnimation(self, b"handle_position", self)
        handle_animation_duration: int = 250
        self._handle_animation.setDuration(handle_animation_duration)
        self._handle_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.toggled.connect(self._on_toggled)

        self._update_cursor_state()

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.EnabledChange:
            self._update_cursor_state()
            self.update()

    def _update_cursor_state(self) -> None:
        if self.isEnabled():
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.unsetCursor()

    @pyqtProperty(float)
    def handle_position(self) -> float:
        """
        The current position of the toggle handle

        This property is used by the QPropertyAnimation to interpolate the handle's
        position and scale the checkmark between 0.0 (off) and 1.0 (on)

        :return: A float representing the interpolation progress
        """
        return self._handle_position

    @handle_position.setter
    def handle_position(self, pos: float) -> None:
        self._handle_position = pos
        self.update()

    def _on_toggled(self, checked: bool) -> None:
        start = self._handle_position
        end = 1.0 if checked else 0.0

        self._handle_animation.stop()
        self._handle_animation.setStartValue(start)
        self._handle_animation.setEndValue(end)
        self._handle_animation.start()

    def _update_stylesheet(self, color: QColor) -> None:
        self.update()

    def sizeHint(self) -> QSize:
        """
        Calculate the recommended geometric size for the widget

        The size includes the toggle track dimensions, internal spacing and
        calculates the bounding box of the text label if present


        :return: The recommended QSize for the layout manager
        """
        size = QSize(self._track_width, self._track_height)
        text = self.text()
        if text:
            font_metric = self.fontMetrics()
            width = self._track_width + self._spacing + font_metric.horizontalAdvance(text)
            height = max(self._track_height, font_metric.height())
            size = QSize(width, height)
        return size

    def hitButton(self, pos: QPoint) -> bool:
        """
        Determine if a mouse event lies within the interactive area

        :param pos: The position of the mouse interaction relative to the widget
        :return: True if the point is within the actionable contents rectangle
        """
        return self.contentsRect().contains(pos)

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Render the toggle switch components and visual states

        Orchestrates the drawing sequence for the background track, the handle,
        the internal checkmark vector when toggled, and the text label.
        Antialiasing is applied for smooth edges

        :param event: The Qt paint event containing the update region
        :return: None
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        opacity, track_color, handle_color, text_color = self._determine_colors_and_opacity()
        painter.setOpacity(opacity)

        content_rect = self.contentsRect()
        y_offset = float(content_rect.top() + round((content_rect.height() - self._track_height) / 2))
        x_offset = float(content_rect.left())

        self._draw_track(painter, x_offset, y_offset, track_color)

        handle_rect = self._calculate_handle_rect(x_offset, y_offset)
        self._draw_handle(painter, handle_rect, handle_color)

        self._draw_handle_icon(painter, handle_rect, track_color, opacity)

        if self.text():
            painter.setFont(self.font())
            self._draw_text(painter, content_rect, x_offset, text_color)

        painter.end()

    def _determine_colors_and_opacity(self) -> tuple[float, QColor, QColor, QColor]:
        if not self.isEnabled():
            return (
                0.5,
                ThemeColors.BORDER_BASE,
                ThemeColors.BG_WHITE,
                ThemeColors.TEXT_DISABLED
            )
        color_off = ThemeColors.BORDER_BASE
        color_on = ThemeColors.ACCENT_COLOR

        track_color = self._interpolate_color(color_off, color_on, self._handle_position)

        text_active = self._interpolate_color(ThemeColors.TEXT_PRIMARY, ThemeColors.ACCENT_COLOR,
                                              self._handle_position * 0.8)

        return 1.0, track_color, ThemeColors.BG_WHITE, text_active

    def _interpolate_color(self, start_color: QColor, end_color: QColor, progress: float) -> QColor:
        red = start_color.red() + (end_color.red() - start_color.red()) * progress
        green = start_color.green() + (end_color.green() - start_color.green()) * progress
        blue = start_color.blue() + (end_color.blue() - start_color.blue()) * progress
        return QColor(int(red), int(green), int(blue))

    def _draw_track(self, painter: QPainter, x_offset: float, y_offset: float, track_color: QColor) -> None:
        track_rect = QRectF(x_offset, y_offset, float(self._track_width), float(self._track_height))
        radius = self._track_height / 2.0

        painter.setBrush(QBrush(track_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(track_rect, radius, radius)

        if self.isEnabled():
            shadow_rect = track_rect.adjusted(0, 0, 0, -self._track_height * 0.3)
            gradient = QLinearGradient(shadow_rect.topLeft(), shadow_rect.bottomLeft())
            gradient.setColorAt(0.0, QColor(0, 0, 0, 30))
            gradient.setColorAt(1.0, QColor(0, 0, 0, 0))

            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(track_rect, radius, radius)

        try:
            border_color = self.animated_border_color
            if border_color.alpha() > 0:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(border_color, 2))
                painter.drawRoundedRect(track_rect.adjusted(1, 1, -1, -1), radius - 1.0, radius - 1.0)
        except AttributeError:
            pass

    def _calculate_handle_rect(self, x_offset: float, y_offset: float) -> QRectF:
        handle_diameter = self._track_height - (2 * self._margin)
        available_width = self._track_width - (2 * self._margin) - handle_diameter

        current_offset = available_width * self._handle_position
        handle_x = x_offset + self._margin + current_offset
        handle_y = y_offset + self._margin

        squish_amount = 4.0 if self.isDown() else 0.0
        squish_offset_x = -squish_amount if self.isChecked() else 0.0

        return QRectF(handle_x + squish_offset_x, handle_y, handle_diameter + squish_amount, handle_diameter)

    def _draw_handle(self, painter: QPainter, handle_rect: QRectF, handle_color: QColor) -> None:
        if self.isEnabled() and not self.isDown():
            for i, alpha in enumerate([12, 8, 4]):
                painter.setBrush(QBrush(QColor(0, 0, 0, alpha)))
                painter.setPen(Qt.PenStyle.NoPen)
                offset = (i + 1.0) * 0.5
                painter.drawEllipse(handle_rect.translated(0, offset * 1.5).adjusted(-offset, -offset, offset, offset))

        painter.setBrush(QBrush(handle_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(handle_rect)

    def _draw_handle_icon(self, painter: QPainter, handle_rect: QRectF, track_color: QColor,
                          base_opacity: float) -> None:
        painter.setOpacity(base_opacity)

        icon_pen = QPen(track_color, 2.0)
        icon_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        icon_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(icon_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        center_x = handle_rect.center().x()
        center_y = handle_rect.center().y()
        handle_radius = handle_rect.height() / 2.0

        progress = self._handle_position

        def interpolate_coordinates(p_off: tuple[float, float], p_on: tuple[float, float]) -> QPointF:
            """Interpolates coordinates geometrically based on animation progress"""
            x = p_off[0] + (p_on[0] - p_off[0]) * progress
            y = p_off[1] + (p_on[1] - p_off[1]) * progress
            return QPointF(center_x + x * handle_radius, center_y + y * handle_radius)

        # Two segments forming \ in the X and the shortest leg in the checkmark
        # Second segment forms the / in the X and the longest leg in the checkmark
        p1a = interpolate_coordinates((-0.35, -0.35), (-0.4, 0.0))
        p1b = interpolate_coordinates((0.35, 0.35), (-0.1, 0.3))

        p2a = interpolate_coordinates((-0.35, 0.35), (-0.1, 0.3))
        p2b = interpolate_coordinates((0.35, -0.35), (0.4, -0.4))

        path = QPainterPath()
        path.moveTo(p1a)
        path.lineTo(p1b)

        path.moveTo(p2a)
        path.lineTo(p2b)

        painter.drawPath(path)

    def _draw_text(self, painter: QPainter, content_rect: QRect, x_offset: float, text_color: QColor) -> None:
        text_rect = QRectF(content_rect)
        text_start_x = x_offset + float(self._track_width) + float(self._spacing)
        text_rect.setLeft(text_start_x)

        painter.setPen(text_color)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())
