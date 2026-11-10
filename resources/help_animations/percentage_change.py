from typing import Dict, List

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen

from src.ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """
    Animation showing the calculation of percentage change
    """

    def __init__(self) -> None:
        super().__init__(duration_ms=7000)

        self.c_bg: QColor = QColor("#2b2b2b")
        self.c_table_bg: QColor = QColor("#1e1e1e")
        self.c_header_bg: QColor = QColor("#333333")
        self.c_border: QColor = QColor("#444444")
        self.c_text: QColor = QColor("#e0e0e0")

        self.c_operand_highlight: QColor = QColor("#2b4a6b")
        self.c_result_pos: QColor = QColor("#2b6b4a")
        self.c_result_neg: QColor = QColor("#6b2b2b")

        self.headers: List[str] = ["ID", "Value", "% Change"]
        self.col_widths: List[int] = [50, 90, 100]
        self.table_width: int = sum(self.col_widths)
        self.row_height: int = 35

        self.data_rows: List[Dict[str, str]] = [
            {"id": "1", "val": "100", "pct": "NaN", "trend": "none"},
            {"id": "2", "val": "120", "pct": "+20.0%", "trend": "pos"},
            {"id": "3", "val": "90", "pct": "-25.0%", "trend": "neg"},
            {"id": "4", "val": "99", "pct": "+10.0%", "trend": "pos"},
        ]

        self.start_x: float = (550 - self.table_width) / 2
        self.start_y: float = (350 - (self.row_height * (len(self.data_rows) + 1))) / 2

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        painter.fillRect(self.rect(), self.c_bg)

        eval_progress: float = self.get_eased_progress(progress, 0.1, 0.4)
        calc_progress: float = self.get_eased_progress(progress, 0.4, 0.7)
        pulse_progress: float = self.get_eased_progress(progress, 0.7, 0.9)

        self._draw_headers(painter, calc_progress)
        self._draw_rows(painter, eval_progress, calc_progress)

        if pulse_progress > 0:
            self._draw_pulse(painter, pulse_progress)

    def _draw_headers(self, painter: QPainter, calc_progress: float) -> None:
        painter.setFont(self.font_bold)
        current_x: float = self.start_x

        for index, text in enumerate(self.headers):
            width: int = self.col_widths[index]
            rect: QRectF = QRectF(current_x, self.start_y, width, self.row_height)

            opacity: float = 1.0
            if index == 2:
                opacity = calc_progress

            if opacity > 0:
                painter.setOpacity(opacity)
                painter.setBrush(self.c_header_bg)
                painter.setPen(self.c_border)
                painter.drawRect(rect)

                painter.setPen(self.c_text)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
                painter.setOpacity(1.0)

            current_x += width

    def _draw_rows(self, painter: QPainter, eval_progress: float, calc_progress: float) -> None:
        painter.setFont(self.font_main)

        for r_idx, row in enumerate(self.data_rows):
            y_pos: float = self.start_y + ((r_idx + 1) * self.row_height)
            current_x: float = self.start_x

            base_values: List[str] = [row["id"], row["val"]]

            for c_idx, text in enumerate(base_values):
                width: int = self.col_widths[c_idx]
                rect: QRectF = QRectF(current_x, y_pos, width, self.row_height)

                bg: QColor = self.c_table_bg
                if c_idx == 1 and eval_progress > 0:
                    intensity: float = eval_progress * (1.0 - calc_progress)
                    bg = self.lerp_color(self.c_table_bg, self.c_operand_highlight, intensity)

                painter.setBrush(bg)
                painter.setPen(self.c_border)
                painter.drawRect(rect)

                painter.setPen(self.c_text)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

                current_x += width

            if calc_progress > 0:
                self._draw_pct_cell(painter, current_x, y_pos, row, calc_progress)

    def _draw_pct_cell(
            self,
            painter: QPainter,
            x: float,
            y: float,
            row: Dict[str, str],
            calc_progresss: float
    ) -> None:
        width: int = self.col_widths[2]
        rect: QRectF = QRectF(x, y, width, self.row_height)

        painter.setOpacity(calc_progresss)

        target_bg: QColor = self.c_table_bg
        if row["trend"] == "pos":
            target_bg = self.c_result_pos
        elif row["trend"] == "neq":
            target_bg = self.c_result_neg

        result_bg: QColor = self.lerp_color(self.c_table_bg, target_bg, 1.0 - calc_progresss)
        painter.setBrush(result_bg)
        painter.setPen(self.c_border)
        painter.drawRect(rect)

        painter.setPen(self.c_text)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, row["pct"])
        painter.setOpacity(1.0)

    def _draw_pulse(self, painter: QPainter, pulse_prog: float) -> None:
        intensity: float = pulse_prog * (1.0 - pulse_prog) * 4.0

        col_x: float = self.start_x + sum(self.col_widths[:2])
        total_h: float = self.row_height * (len(self.data_rows) + 1)
        col_w: float = self.col_widths[2]

        pulse_color: QColor = self.lerp_color(self.c_border, self.accent_color, intensity)

        painter.setPen(QPen(pulse_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(col_x - 1, self.start_y - 1, col_w + 2, total_h + 2))
