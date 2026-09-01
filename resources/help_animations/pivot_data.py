from typing import List

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen

from src.ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """
    Animation showing data pivoting (Long to Wide format).
    Visualizes transforming a dataset by rotating unique values from a
    column into new individual columns, aligned by an index.
    """

    def __init__(self) -> None:
        super().__init__(duration_ms=7500)

        self.c_bg = QColor("#2b2b2b")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")

        self.c_index = QColor("#2b4a6b")
        self.c_column = QColor("#2b6b4a")
        self.c_value = QColor("#6b4a2b")

        self.long_headers: List[str] = ["Region", "Year", "Sales"]
        self.long_rows: List[List[str]] = [
            ["North", "2023", "10"],
            ["North", "2024", "15"],
            ["South", "2023", "20"],
            ["South", "2024", "25"],
        ]

        self.wide_headers: List[str] = ["Region", "2023", "2024"]
        self.wide_rows: List[List[str]] = [
            ["North", "10", "15"],
            ["South", "20", "25"]
        ]

        self.col_w: int = 70
        self.row_h: int = 28
        self.table_width: int = self.col_w * 3

        self.start_x: float = (550 - self.table_width) / 2
        self.start_y_long: float = 40.0
        self.start_y_wide: float = self.start_y_long + self.row_h

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        painter.fillRect(self.rect(), self.c_bg)

        hl_long_prog: float = self.get_eased_progress(progress, 0.10, 0.25)
        if progress > 0.30:
            hl_long_prog = 1.0 - self.get_eased_progress(progress, 0.30, 0.35)

        transition_prog: float = self.get_eased_progress(progress, 0.35, 0.55)

        hl_wide_prog: float = self.get_eased_progress(progress, 0.55, 0.70)
        if progress > 0.75:
            hl_wide_prog = 1.0 - self.get_eased_progress(progress, 0.75, 0.85)

        pulse_prog: float = self.get_eased_progress(progress, 0.85, 1.00)

        if transition_prog < 1.0:
            opacity: float = 1.0 - transition_prog
            painter.setOpacity(opacity)
            offset_x: float = self.start_x - (transition_prog * 60.0)
            self._draw_long_table(painter, offset_x, self.start_y_long, hl_long_prog)

        if transition_prog > 0.0:
            opacity: float = transition_prog
            painter.setOpacity(opacity)
            offset_x: float = self.start_x + ((1.0 - transition_prog) * 60.0)
            self._draw_wide_table(painter, offset_x, self.start_y_wide, hl_wide_prog)

        painter.setOpacity(1.0)

        if pulse_prog > 0:
            self._draw_success_pulse(painter, pulse_prog)

    def _draw_long_table(self, painter: QPainter, x: float, y: float, highlight_prog: float) -> None:
        """Renders the initial long-format dataset with contextual highlights."""
        bg_index = self.lerp_color(self.c_bg, self.c_index, highlight_prog * 0.5)
        bg_col = self.lerp_color(self.c_bg, self.c_column, highlight_prog * 0.5)
        bg_val = self.lerp_color(self.c_bg, self.c_value, highlight_prog * 0.3)

        painter.setFont(self.font_bold)
        header_colors = [
            self.lerp_color(self.c_header_bg, self.c_index, highlight_prog * 0.8),
            self.lerp_color(self.c_header_bg, self.c_column, highlight_prog * 0.8),
            self.lerp_color(self.c_header_bg, self.c_value, highlight_prog * 0.5)
        ]

        self._draw_row(painter, x, y, self.long_headers, header_colors)

        painter.setFont(self.font_main)
        row_colors = [bg_index, bg_col, bg_val]

        for index, row in enumerate(self.long_rows):
            row_y = y + ((index + 1) * self.row_h)
            self._draw_row(painter, x, row_y, row, row_colors)

    def _draw_wide_table(self, painter: QPainter, x: float, y: float, highlight_prog: float) -> None:
        """Renders the final pivoted dataset showing where data migrated."""
        bg_index = self.lerp_color(self.c_bg, self.c_index, highlight_prog * 0.5)
        bg_val = self.lerp_color(self.c_bg, self.c_value, highlight_prog * 0.3)

        painter.setFont(self.font_bold)
        header_colors = [
            self.lerp_color(self.c_header_bg, self.c_index, highlight_prog * 0.8),
            self.lerp_color(self.c_header_bg, self.c_column, highlight_prog * 0.9),
            self.lerp_color(self.c_header_bg, self.c_column, highlight_prog * 0.9)
        ]
        self._draw_row(painter, x, y, self.wide_headers, header_colors)

        painter.setFont(self.font_main)
        row_colors = [bg_index, bg_val, bg_val]

        for index, row in enumerate(self.wide_rows):
            row_y = y + ((index + 1) * self.row_h)
            self._draw_row(painter, x, row_y, row, row_colors)

    def _draw_row(self, painter: QPainter, x: float, y: float, values: List[str], bg_colors: List[QColor]) -> None:
        """Helper to draw a horizontal sequence of cells."""
        current_x: float = x

        for index, text in enumerate(values):
            rect = QRectF(current_x, y, self.col_w, self.row_h)

            painter.setBrush(bg_colors[index])
            painter.setPen(self.c_border)
            painter.drawRect(rect)

            painter.setPen(self.c_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

            current_x += self.col_w

    def _draw_success_pulse(self, painter: QPainter, pulse_progress: float) -> None:
        pulse_intensity: float = pulse_progress * (1.0 - pulse_progress) * 4.0

        total_rows: int = 1 + len(self.wide_rows)
        total_height: float = total_rows * self.row_h

        highlight_color = self.lerp_color(self.c_border, self.accent_color, pulse_intensity)

        painter.setPen(QPen(highlight_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(
            QRectF(self.start_x - 1, self.start_y_wide - 1, self.table_width + 2, total_height + 2)
        )