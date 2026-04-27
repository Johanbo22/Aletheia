from typing import Optional

from PyQt6.QtCore import Qt,  QSize,  QRect, QRectF,  QEasingCurve,  QPropertyAnimation, pyqtProperty, QPoint, QPointF, QEvent
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPaintEvent
from PyQt6.QtWidgets import QCheckBox, QWidget

from ui.theme import ThemeColors
from ui.widgets.mixins import HoverFocusAnimationMixin

class DataPlotStudioToggleSwitch(HoverFocusAnimationMixin, QCheckBox):
    """A toggle switch widget"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        QCheckBox.__init__(self, parent)
        
        HoverFocusAnimationMixin.__init__(self)
        
        self._track_height = 22
        self._track_width = 40
        self._margin = 4
        self._spacing = 8
        
        self._handle_position = 1.0 if self.isChecked() else 0.0
        
        self._handle_animation = QPropertyAnimation(self, b"handle_position", self)
        self._handle_animation.setDuration(200)
        self._handle_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
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
        size = QSize(self._track_width, self._track_height)
        text = self.text()
        if text:
            font_metric = self.fontMetrics()
            width = self._track_width + self._spacing + font_metric.horizontalAdvance(text)
            height = max(self._track_height, font_metric.height())
            size = QSize(width, height)
        return size
    
    def hitButton(self, pos: QPoint) -> bool:
        return self.contentsRect().contains(pos)

    def paintEvent(self, event: QPaintEvent) -> None:
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
        
        if self._handle_position > 0.0:
            self._draw_checkmark(painter, handle_rect, track_color, opacity)
        
        if self.text():
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
        return 1.0, track_color, ThemeColors.BG_WHITE, ThemeColors.TEXT_PRIMARY
    
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
        
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(self.animated_border_color, 2))
            painter.drawRoundedRect(track_rect.adjusted(1, 1, -1, -1), radius - 1.0, radius - 1.0)
        
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
            painter.setBrush(QBrush(QColor(0, 0, 0, 20)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(handle_rect.translated(0, 1.0).adjusted(-0.5, -0.5, 0.5, 0.5))
            
            painter.setBrush(QBrush(QColor(0, 0, 0, 10)))
            painter.drawEllipse(handle_rect.translated(0, 2.0).adjusted(-1.0, -1.0, 1.0, 1.0))
        
        painter.setBrush(QBrush(handle_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(handle_rect)
    
    def _draw_checkmark(self, painter: QPainter, handle_rect: QRectF, track_color: QColor, base_opacity: float) -> None:
        painter.setOpacity(base_opacity * self._handle_position)
        
        checkmark_pen = QPen(track_color, 2.0)
        checkmark_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        checkmark_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(checkmark_pen)
        
        center_x = handle_rect.center().x()
        center_y = handle_rect.center().y()
        handle_radius = handle_rect.height() / 2.0
        
        p1 = QPointF(center_x - handle_radius * 0.4, center_y)
        p2 = QPointF(center_x - handle_radius * 0.1, center_y + handle_radius * 0.3)
        p3 = QPointF(center_x + handle_radius * 0.4, center_y - handle_radius * 0.4)
        
        painter.drawLine(p1, p2)
        painter.drawLine(p2, p3)
        
        painter.setOpacity(base_opacity)
    
    def _draw_text(self, painter: QPainter, content_rect: QRect, x_offset: float, text_color: QColor) -> None:
        text_rect = QRectF(content_rect)
        text_start_x = x_offset + float(self._track_width) + float(self._spacing)
        text_rect.setLeft(text_start_x)
        
        painter.setPen(text_color)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())