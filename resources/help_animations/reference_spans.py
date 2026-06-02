from PyQt6.QtCore import QRectF, Qt, QPointF
from PyQt6.QtGui import QColor, QPen, QPainter

from ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """
    Animation showing the creation of reference spans.
    Sequentially highlights a vertical band (axvspan) and a horizontal band (axhspan).
    """

    def __init__(self) -> None:
        super().__init__(duration_ms=5000)

        self.c_bg: QColor = QColor("#2b2b2b")
        self.c_plot_bg: QColor = QColor("#1e1e1e")
        self.c_axis: QColor = QColor("#888888")

        self.c_hspan: QColor = QColor("#f1c40f")
        self.c_vspan: QColor = QColor("#9b59b6")

        self.margin: int = 40
        self.plot_area_rect: QRectF = QRectF(
            self.margin,
            60,
            self.width() - (self.margin * 2),
            self.height() - 80
        )

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        """
        Draws the animation frame based on the current progress.
        """
        painter.fillRect(self.rect(), self.c_bg)

        axis_prog = self.get_eased_progress(progress, 0.0, 0.15)
        vspan_prog = self.get_eased_progress(progress, 0.2, 0.5)
        hspan_prog = self.get_eased_progress(progress, 0.6, 0.9)

        painter.setBrush(self.c_plot_bg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.plot_area_rect)

        if axis_prog > 0:
            self._draw_axes(painter, axis_prog)
        if vspan_prog > 0:
            self._draw_vspan(painter, vspan_prog)
        if hspan_prog > 0:
            self._draw_hspan(painter, hspan_prog)

    def _draw_axes(self, painter: QPainter, progress: float) -> None:
        """Draws the X and Y coordinate axes."""
        painter.setPen(QPen(self.c_axis, 2))

        bottom_left = self.plot_area_rect.bottomLeft()

        y_top = bottom_left.y() - (self.plot_area_rect.height() * progress)
        painter.drawLine(bottom_left, QPointF(bottom_left.x(), y_top))

        x_right = bottom_left.x() + (self.plot_area_rect.width() * progress)
        painter.drawLine(bottom_left, QPointF(x_right, bottom_left.y()))

    def _draw_vspan(self, painter: QPainter, progress: float) -> None:
        """Draws a vertical reference span (axvspan) fading in."""
        span_width = self.plot_area_rect.width() * 0.2
        x_start = self.plot_area_rect.left() + (self.plot_area_rect.width() * 0.2)

        span_rect = QRectF(
            x_start,
            self.plot_area_rect.top(),
            span_width,
            self.plot_area_rect.height()
        )

        color = QColor(self.c_vspan)
        color.setAlphaF(0.4 * progress)

        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(span_rect)

    def _draw_hspan(self, painter: QPainter, progress: float) -> None:
        """Draws a horizontal reference span (axhspan) fading in."""
        span_height = self.plot_area_rect.height() * 0.25
        y_start = self.plot_area_rect.top() + (self.plot_area_rect.height() * 0.5)

        span_rect = QRectF(
            self.plot_area_rect.left(),
            y_start,
            self.plot_area_rect.width(),
            span_height
        )

        color = QColor(self.c_hspan)
        color.setAlphaF(0.4 * progress)

        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(span_rect)