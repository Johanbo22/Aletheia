from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen

from ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """
    Animation showing the creation of different reference lines
    Sequentially draws a horizontal line, a vertical line and an arbitrary line
    """
    def __init__(self) -> None:
        super().__init__(duration_ms=6000)

        self.c_bg: QColor = QColor("#2b2b2b")
        self.c_plot_bg: QColor = QColor("#1e1e1e")
        self.c_axis: QColor = QColor("#888888")

        # Line colors
        self.c_hline: QColor = QColor("#4a90e2")
        self.c_vline: QColor = QColor("#e74c3c")
        self.c_axline: QColor = QColor("#2ecc71")

        self.margin: int = 40
        self.plot_area_rect: QRectF = QRectF(
            self.margin,
            60,
            self.width() - (self.margin * 2),
            self.height() - 80
        )

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        """Draws the animation frame"""
        painter.fillRect(self.rect(), self.c_bg)

        axis_prog = self.get_eased_progress(progress, 0.0, 0.1)
        hline_prog = self.get_eased_progress(progress, 0.15, 0.35)
        vline_prog = self.get_eased_progress(progress, 0.45, 0.65)
        axline_prog = self.get_eased_progress(progress, 0.75, 0.95)

        painter.setBrush(self.c_plot_bg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.plot_area_rect)

        if axis_prog > 0:
            self._draw_axes(painter, axis_prog)
        if hline_prog > 0:
            self._draw_hline(painter, hline_prog)
        if vline_prog > 0:
            self._draw_vline(painter, vline_prog)
        if axline_prog > 0:
            self._draw_axline(painter, axline_prog)

    def _draw_axes(self, painter: QPainter, progress: float) -> None:
        """Draws the X and Y coordinate axes"""
        painter.setPen(QPen(self.c_axis, 2))

        bottom_left = self.plot_area_rect.bottomLeft()

        y_top = bottom_left.y() - (self.plot_area_rect.height() * progress)
        painter.drawLine(bottom_left, QPointF(bottom_left.x(), y_top))

        x_right = bottom_left.x() + (self.plot_area_rect.width() * progress)
        painter.drawLine(bottom_left, QPointF(x_right, bottom_left.y()))

    def _draw_hline(self, painter: QPainter, progress: float) -> None:
        """Draws a horizontal reference line"""
        y_pos = self.plot_area_rect.top() + (self.plot_area_rect.height() * 0.3)
        start_x = self.plot_area_rect.left()
        end_x = start_x + (self.plot_area_rect.width() * progress)

        painter.setPen(QPen(self.c_hline, 3, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(start_x, y_pos), QPointF(end_x, y_pos))

    def _draw_vline(self, painter: QPainter, progress: float) -> None:
        """Draws a vertical reference line"""
        x_pos = self.plot_area_rect.left() + (self.plot_area_rect.width() * 0.7)
        start_y = self.plot_area_rect.bottom()
        end_y = start_y - (self.plot_area_rect.height() * progress)

        painter.setPen(QPen(self.c_vline, 3, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(x_pos, start_y), QPointF(x_pos, end_y))

    def _draw_axline(self, painter: QPainter, progress: float) -> None:
        """Draws an arbitrary angle reference line"""
        start_pt = QPointF(
            self.plot_area_rect.left() + (self.plot_area_rect.width() * 0.1),
            self.plot_area_rect.bottom() - (self.plot_area_rect.height() * 0.2)
        )

        target_pt = QPointF(
            self.plot_area_rect.right() - (self.plot_area_rect.width() * 0.1),
            self.plot_area_rect.top() + (self.plot_area_rect.height() * 0.2)
        )

        current_x = start_pt.x() + ((target_pt.x() - start_pt.x()) * progress)
        current_y = start_pt.y() + ((target_pt.y() - start_pt.y()) * progress)

        painter.setPen(QPen(self.c_axline, 3, Qt.PenStyle.DashLine))
        painter.drawLine(start_pt, QPointF(current_x, current_y))