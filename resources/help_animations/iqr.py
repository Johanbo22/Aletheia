from PyQt6.QtCore import QRectF, Qt, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen

from ui.help_animation_engine import HelpAnimationEngine


class Animation(HelpAnimationEngine):
    """
    Animation showing Interquartile Range (IQR) Outlier Detection.
    Visualizes an array of data, finding Q1 and Q3, calculating the IQR,
    establishing a mathematical boundary, and dropping values outside of it.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent, fps=60, duration_ms=9000)

        self.c_bg_normal = QColor("#333333")
        self.c_bg_quartile = QColor("#2b4a6b")
        self.c_bg_outlier = QColor("#6b2b2b")
        self.c_border = QColor("#555555")
        self.c_text = QColor("#e0e0e0")
        self.c_accent = QColor("#e74c3c")
        self.values = [10, 12, 14, 15, 16, 18, 45]

        self.q1_idx = 1
        self.q3_idx = 5
        self.outlier_idx = 6

        self.box_w = 42.0
        self.box_h = 42.0
        self.spacing = 10.0

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        p_intro = self.get_eased_progress(progress, 0.0, 0.10)
        p_quartiles = self.get_eased_progress(progress, 0.15, 0.35)
        p_bounds = self.get_eased_progress(progress, 0.40, 0.60)
        p_detect = self.get_eased_progress(progress, 0.65, 0.80)
        p_outro = self.get_eased_progress(progress, 0.85, 1.0)

        if p_intro == 0.0:
            return

        total_w = len(self.values) * self.box_w + (len(self.values) - 1) * self.spacing
        cx = self.width() / 2.0
        cy = self.height() / 2.0

        start_x = cx - total_w / 2.0
        start_y = cy - self.box_h / 2.0 - 20.0

        self._draw_boxes(painter, start_x, start_y, p_intro, p_quartiles, p_detect, p_outro)
        self._draw_quartile_markers(painter, start_x, start_y, p_quartiles)
        self._draw_bounds(painter, start_x, start_y, p_bounds)
        self._draw_explanation(painter, cy + 80.0, p_quartiles, p_bounds, p_detect, p_outro)

    def _draw_boxes(self, painter: QPainter, start_x: float, y: float, p_intro: float, p_quartiles: float,
                    p_detect: float, p_outro: float) -> None:
        painter.setFont(self.font_main)

        for i, val in enumerate(self.values):
            x = start_x + i * (self.box_w + self.spacing)

            current_y = y
            alpha_mult = p_intro

            bg_color = self.c_bg_normal
            if i in (self.q1_idx, self.q3_idx):
                bg_color = self.lerp_color(bg_color, self.c_bg_quartile, p_quartiles)
            elif i == self.outlier_idx:
                bg_color = self.lerp_color(bg_color, self.c_bg_outlier, p_detect)

                current_y += 40.0 * p_outro
                alpha_mult *= (1.0 - p_outro)

            rect = QRectF(x, current_y, self.box_w, self.box_h)

            c_bg = QColor(bg_color)
            c_bg.setAlpha(int(255 * alpha_mult))
            painter.setBrush(c_bg)

            c_border = QColor(self.c_border)
            c_border.setAlpha(int(255 * alpha_mult))
            painter.setPen(c_border)

            painter.drawRect(rect)

            c_text = QColor(self.c_text)
            c_text.setAlpha(int(255 * alpha_mult))
            painter.setPen(c_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(val))

    def _draw_quartile_markers(self, painter: QPainter, start_x: float, y: float, p_quartiles: float) -> None:
        if p_quartiles == 0.0:
            return

        alpha = int(255 * p_quartiles)
        c_line = QColor(self.c_bg_quartile)
        c_line.setAlpha(alpha)

        pen = QPen(c_line, 2)
        painter.setPen(pen)
        painter.setFont(self.font_small)

        q1_cx = start_x + self.q1_idx * (self.box_w + self.spacing) + self.box_w / 2.0
        q3_cx = start_x + self.q3_idx * (self.box_w + self.spacing) + self.box_w / 2.0

        bottom_y = y + self.box_h

        painter.drawLine(QPointF(q1_cx, bottom_y + 5.0), QPointF(q1_cx, bottom_y + 15.0))
        painter.drawLine(QPointF(q3_cx, bottom_y + 5.0), QPointF(q3_cx, bottom_y + 15.0))
        painter.drawLine(QPointF(q1_cx, bottom_y + 15.0), QPointF(q3_cx, bottom_y + 15.0))

        c_text = QColor(self.c_text)
        c_text.setAlpha(alpha)
        painter.setPen(c_text)

        painter.drawText(QRectF(q1_cx - 20.0, y - 25.0, 40.0, 20.0), Qt.AlignmentFlag.AlignCenter, "Q1")
        painter.drawText(QRectF(q3_cx - 20.0, y - 25.0, 40.0, 20.0), Qt.AlignmentFlag.AlignCenter, "Q3")

        iqr_rect = QRectF(q1_cx, bottom_y + 18.0, q3_cx - q1_cx, 20.0)
        painter.drawText(iqr_rect, Qt.AlignmentFlag.AlignCenter, "IQR = 6")

    def _draw_bounds(self, painter: QPainter, start_x: float, y: float, p_bounds: float) -> None:
        if p_bounds == 0.0:
            return

        alpha = int(255 * p_bounds)
        c_accent = QColor(self.c_accent)
        c_accent.setAlpha(alpha)

        pen = QPen(c_accent, 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)

        limit_x = start_x + self.q3_idx * (self.box_w + self.spacing) + self.box_w + self.spacing / 2.0

        painter.drawLine(QPointF(limit_x, y - 25.0), QPointF(limit_x, y + self.box_h + 35.0))

        painter.setFont(self.font_small)
        painter.drawText(QRectF(limit_x - 60.0, y - 45.0, 120.0, 20.0), Qt.AlignmentFlag.AlignCenter,
                         "Upper Limit (27)")

    def _draw_explanation(self, painter: QPainter, y: float, p_quartiles: float, p_bounds: float, p_detect: float,
                          p_outro: float) -> None:
        painter.setFont(self.font_main)
        painter.setPen(self.c_text)

        if p_outro == 1.0:
            text = "Cleaned: Outliers successfully removed."
        elif p_detect == 1.0 and p_outro > 0.0:
            text = "Dropping data points outside bounds..."
        elif p_bounds == 1.0 and p_detect > 0.0:
            text = "Flagging values > 27 as Outliers."
        elif p_quartiles == 1.0 and p_bounds > 0.0:
            text = "Upper Bound = Q3 + (1.5 × IQR)"
        elif p_quartiles > 0.0:
            text = "Finding the 25th (Q1) and 75th (Q3) percentiles..."
        else:
            text = "Sorted Dataset"

        painter.drawText(QRectF(0.0, y, float(self.width()), 30.0), Qt.AlignmentFlag.AlignCenter, text)