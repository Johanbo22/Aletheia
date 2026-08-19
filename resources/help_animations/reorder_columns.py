from typing import List
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPen, QPainter

from src.ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """
    Animation showing column reordering.
    Visualizes a single column being selected, lifted, and dragged across
    the dataset to a new position, displacing the other columns.
    """

    def __init__(self) -> None:
        super().__init__(duration_ms=6500)

        self.c_bg = QColor("#2b2b2b")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")

        self.c_highlight = QColor("#2b4a6b")
        self.c_shadow = QColor(0, 0, 0, 120)

        self.headers: List[str] = ["ID", "Name", "Score"]
        self.rows: List[List[str]] = [
            ["1", "Alice", "95"],
            ["2", "Bob", "88"],
            ["3", "Charlie", "72"]
        ]

        self.col_widths: List[int] = [60, 120, 70]
        self.table_width: int = sum(self.col_widths)
        self.row_height: int = 28

        self.base_x: float = (550 - self.table_width) / 2
        self.base_y: float = 60.0

        self.start_x: List[float] = [
            0.0,
            self.col_widths[0],
            self.col_widths[0] + self.col_widths[1]
        ]

        self.end_x: List[float] = [
            self.col_widths[1] + self.col_widths[2],
            0.0,
            self.col_widths[1]
        ]

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        painter.fillRect(self.rect(), self.c_bg)

        hl_prog: float = self.get_eased_progress(progress, 0.05, 0.15)
        grab_prog: float = self.get_eased_progress(progress, 0.15, 0.25)
        move_prog: float = self.get_eased_progress(progress, 0.25, 0.70)
        drop_prog: float = self.get_eased_progress(progress, 0.70, 0.80)
        pulse_prog: float = self.get_eased_progress(progress, 0.85, 1.00)

        y_lift: float = (grab_prog - drop_prog) * -8.0

        current_x: List[float] = [
            self.start_x[i] + (self.end_x[i] - self.start_x[i]) * move_prog
            for i in range(3)
        ]

        for i in [1, 2]:
            self._draw_col(
                painter,
                col_idx=i,
                x=self.base_x + current_x[i],
                y=self.base_y,
                highlight_prog=0.0,
                is_lifted=False
            )

        if y_lift < 0:
            self._draw_shadow(
                painter,
                x=self.base_x + current_x[0],
                y=self.base_y + y_lift,
                width=self.col_widths[0]
            )

        current_hl: float = hl_prog * (1.0 - drop_prog)

        self._draw_col(
            painter,
            col_idx=0,
            x=self.base_x + current_x[0],
            y=self.base_y + y_lift,
            highlight_prog=current_hl,
            is_lifted=(y_lift < -0.1)
        )

        if pulse_prog > 0:
            self._draw_success_pulse(painter, pulse_prog)

    def _draw_col(
            self,
            painter: QPainter,
            col_idx: int,
            x: float,
            y: float,
            highlight_prog: float,
            is_lifted: bool
    ) -> None:
        bg_color = self.lerp_color(self.c_bg, self.c_highlight, highlight_prog)
        header_bg = self.lerp_color(self.c_header_bg, self.c_highlight, highlight_prog * 0.8)
        border_color = self.lerp_color(self.c_border, self.accent_color, highlight_prog * 0.5)

        active_border = border_color if is_lifted else self.c_border
        width = self.col_widths[col_idx]

        painter.setFont(self.font_bold)
        rect = QRectF(x, y, width, self.row_height)

        painter.setBrush(header_bg)
        painter.setPen(active_border)
        painter.drawRect(rect)

        painter.setPen(self.c_text)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.headers[col_idx])

        painter.setFont(self.font_main)
        for r_idx, row in enumerate(self.rows):
            cell_y = y + (r_idx + 1) * self.row_height
            rect = QRectF(x, cell_y, width, self.row_height)

            painter.setBrush(bg_color)
            painter.setPen(active_border)
            painter.drawRect(rect)

            painter.setPen(self.c_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, row[col_idx])

    def _draw_shadow(self, painter: QPainter, x: float, y: float, width: float) -> None:
        total_height = (len(self.rows) + 1) * self.row_height
        rect = QRectF(x + 4, y + 4, width, total_height)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.c_shadow)
        painter.drawRect(rect)

    def _draw_success_pulse(self, painter: QPainter, pulse_progress: float) -> None:
        pulse_intensity: float = pulse_progress * (1.0 - pulse_progress) * 4.0

        total_height: float = (1 + len(self.rows)) * self.row_height
        highlight_color = self.lerp_color(self.c_border, self.accent_color, pulse_intensity)

        painter.setPen(QPen(highlight_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.drawRect(
            QRectF(self.base_x - 1, self.base_y - 1, self.table_width + 2, total_height + 2)
        )