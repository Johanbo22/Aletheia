import math
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter

from ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """
    Animation showing Data Normalization.
    Visualizes raw data values being scaled into a normalized [0, 1] range
    while maintaining proportions
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent, fps=60, duration_ms=8000)

        self.c_table_bg = QColor("#1e1e1e")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")

        self.c_bar_raw = QColor("#2b4a6b")
        self.c_bar_norm = QColor("#2ecc71")

        self.headers = ["Feature", "Value"]

        self.data_rows = [
            {"name": "A", "val": 20.0},
            {"name": "B", "val": 60.0},
            {"name": "C", "val": 100.0}
        ]

        self.max_val = 100.0

        self.table_w = 340
        self.row_h = 45
        self.col_widths = [100, 240]

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        p_intro = self.get_eased_progress(progress, 0.0, 0.15)
        p_transform = self.get_eased_progress(progress, 0.35, 0.65)
        p_outro = self.get_eased_progress(progress, 0.85, 1.0)

        cx = self.width() / 2
        cy = self.height() / 2

        start_x = cx - self.table_w / 2
        start_y = cy - (len(self.data_rows) + 1) * self.row_h / 2 - 10

        self._draw_header(painter, start_x, start_y, p_transform)

        for i, row in enumerate(self.data_rows):
            y = start_y + (i + 1) * self.row_h
            self._draw_row(painter, start_x, y, row["name"], row["val"], p_intro, p_transform)

        self._draw_scale_axis(
            painter,
            start_x + self.col_widths[0],
            start_y + (len(self.data_rows) + 1) * self.row_h,
            self.col_widths[1],
            p_intro,
            p_transform
        )

        if p_intro == 1.0 and p_outro == 0.0:
            formula_y = start_y + (len(self.data_rows) + 2) * self.row_h + 15
            painter.setFont(self.font_main)

            alpha = int(255 * math.sin(p_transform * math.pi)) if p_transform > 0 else 0
            if p_transform == 1.0:
                alpha = 255

            c = QColor(self.c_text)
            c.setAlpha(alpha)
            painter.setPen(c)

            if p_transform < 0.5:
                text = "Preparing to normalize..."
            else:
                text = "X_norm = X / X_Max"

            painter.drawText(QRectF(0, formula_y, float(self.width()), 30.0), Qt.AlignmentFlag.AlignCenter, text)

    def _draw_header(self, painter: QPainter, x: float, y: float, p_transform: float) -> None:
        painter.setFont(self.font_bold)
        curr_x = x

        for i, text in enumerate(self.headers):
            w = self.col_widths[i]
            rect = QRectF(curr_x, y, float(w), float(self.row_h))

            painter.setBrush(self.c_header_bg)
            painter.setPen(self.c_border)
            painter.drawRect(rect)

            display_text = text
            if i == 1:
                display_text = "Raw Value" if p_transform < 0.5 else "Normalized (0 - 1)"

            painter.setPen(self.c_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, display_text)
            curr_x += w

    def _draw_row(self, painter: QPainter, x: float, y: float, name: str, val: float, p_intro: float, p_transform: float) -> None:
        if p_intro == 0:
            return

        full_rect = QRectF(x, y, float(self.table_w), float(self.row_h))
        painter.setBrush(self.c_table_bg)
        painter.setPen(self.c_border)
        painter.drawRect(full_rect)

        name_rect = QRectF(x, y, float(self.col_widths[0]), float(self.row_h))
        painter.setPen(self.c_text)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, name)

        val_x = x + self.col_widths[0]
        val_w = self.col_widths[1]
        val_rect = QRectF(val_x, y, float(val_w), float(self.row_h))
        painter.drawRect(name_rect)
        painter.drawRect(val_rect)

        max_bar_w = val_w - 20
        target_w = (val / self.max_val) * max_bar_w
        bar_w = target_w * p_intro

        current_color = self.lerp_color(self.c_bar_raw, self.c_bar_norm, p_transform)
        norm_val = val / self.max_val
        current_val = val * (1 - p_transform) + norm_val * p_transform

        bar_rect = QRectF(val_x + 10, y + 5, float(bar_w), float(self.row_h - 10))
        painter.setBrush(current_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(bar_rect)

        painter.setPen(self.c_text)

        if p_transform < 0.1:
            val_text = f"{val:.1f}"
        elif p_transform > 0.9:
            val_text = f"{norm_val:.2f}"
        else:
            val_text = f"{current_val:.2f}"

        text_rect = QRectF(val_x + 15, y, float(bar_w - 10), float(self.row_h))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, val_text)

    def _draw_scale_axis(self, painter: QPainter, x: float, y: float, w: float, p_intro: float, p_transform: float) -> None:
        if p_intro == 0:
            return

        painter.setPen(self.c_border)
        painter.drawLine(int(x + 10), int(y + 5), int(x + w - 10), int(y + 5))

        painter.drawLine(int(x + 10), int(y + 5), int(x + 10), int(y + 10))
        painter.drawLine(int(x + w / 2), int(y + 5), int(x + w / 2), int(y + 10))
        painter.drawLine(int(x + w - 10), int(y + 5), int(x + w - 10), int(y + 10))

        painter.setFont(self.font_small)
        painter.setPen(self.c_text)

        mid_raw = self.max_val / 2
        max_raw = self.max_val

        mid_val = mid_raw * (1 - p_transform) + 0.5 * p_transform
        max_val = max_raw * (1 - p_transform) + 1.0 * p_transform

        mid_text = f"{mid_val:.1f}" if p_transform < 0.9 else "0.5"
        max_text = f"{max_val:.1f}" if p_transform < 0.9 else "1.0"

        painter.drawText(QRectF(x, y + 12, 20.0, 20.0), Qt.AlignmentFlag.AlignCenter, "0")
        painter.drawText(QRectF(x + w / 2 - 15, y + 12, 30.0, 20.0), Qt.AlignmentFlag.AlignCenter, mid_text)
        painter.drawText(QRectF(x + w - 30, y + 12, 40.0, 20.0), Qt.AlignmentFlag.AlignCenter, max_text)
