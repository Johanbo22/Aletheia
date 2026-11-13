from dataclasses import dataclass

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from src.ui.help_animation_engine import HelpAnimationEngine


@dataclass(frozen=True)
class SortableRow:
    values: tuple[str, str, str]
    initial_idx: int
    sorted_idx: int
    tint: QColor


class Animation(HelpAnimationEngine):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, fps=60, duration_ms=6500)

        self.c_bg: QColor = QColor("#2b2b2b")
        self.c_table_bg: QColor = QColor("#1e1e1e")
        self.c_header_bg: QColor = QColor("#333333")
        self.c_border: QColor = QColor("#444444")
        self.c_text: QColor = QColor("#e0e0e0")
        self.c_sort_header: QColor = QColor("#2b4a6b")

        self.headers: tuple[str, str, str] = ("ID", "Agent", "Score")
        self.col_widths: tuple[float, float, float] = (55.0, 105.0, 90.0)
        self.table_width: float = sum(self.col_widths)
        self.row_height: float = 34.0

        self.rows: tuple[SortableRow, ...] = (
            SortableRow(("001", "Charlie", "45"), 0, 2, QColor("#3d3522")),
            SortableRow(("002", "Alice", "12"), 1, 0, QColor("#223d33")),
            SortableRow(("003", "David", "88"), 2, 3, QColor("#2b354f")),
            SortableRow(("004", "Bob", "27"), 3, 1, QColor("#3b283d")),
        )

        self.start_x: float = (550.0 - self.table_width) / 2.0
        self.start_y: float = 55.0

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        painter.fillRect(self.rect(), self.c_bg)

        hl_prog: float = self.get_eased_progress(progress, 0.10, 0.25)
        move_prog: float = self.get_eased_progress(progress, 0.30, 0.75)
        pulse_prog: float = self.get_eased_progress(progress, 0.78, 0.95)

        self._draw_header(painter, hl_prog)
        self._draw_rows(painter, hl_prog, move_prog)

        if pulse_prog > 0.0:
            self._draw_pulse(painter, pulse_prog)

        self._draw_caption(painter, hl_prog, move_prog)

    def _draw_header(self, painter: QPainter, hl_prog: float) -> None:
        painter.setFont(self.font_bold)
        curr_x: float = self.start_x

        for idx, text in enumerate(self.headers):
            width: float = self.col_widths[idx]
            rect: QRectF = QRectF(curr_x, self.start_y, width, self.row_height)

            bg: QColor = self.c_header_bg
            label: str = text
            if idx == 2 and hl_prog > 0.0:
                bg = self.lerp_color(self.c_header_bg, self.c_sort_header, hl_prog)
                if hl_prog > 0.5:
                    label = f"{text} ▲"

            painter.setBrush(bg)
            painter.setPen(self.c_border)
            painter.drawRect(rect)
            painter.setPen(self.c_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
            curr_x += width

    def _draw_rows(self, painter: QPainter, hl_prog: float, move_prog: float) -> None:
        painter.setFont(self.font_main)
        for row in self.rows:
            y_init: float = self.start_y + ((row.initial_idx + 1) * self.row_height)
            y_final: float = self.start_y + ((row.sorted_idx + 1) * self.row_height)
            curr_y: float = y_init + ((y_final - y_init) * move_prog)

            row_bg: QColor = self.lerp_color(self.c_table_bg, row.tint, hl_prog)
            curr_x: float = self.start_x

            for c_idx, cell_text in enumerate(row.values):
                width: float = self.col_widths[c_idx]
                rect: QRectF = QRectF(curr_x, curr_y, width, self.row_height)
                painter.setBrush(row_bg)
                painter.setPen(self.c_border)
                painter.drawRect(rect)
                painter.setPen(self.c_text)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, cell_text)
                curr_x += width

    def _draw_pulse(self, painter: QPainter, pulse_prog: float) -> None:
        intensity: float = pulse_prog * (1.0 - pulse_prog) * 4.0
        total_h: float = (len(self.rows) + 1) * self.row_height
        border_col: QColor = self.lerp_color(
            self.c_border, self.success_color, intensity
        )

        painter.setPen(QPen(border_col, 2.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(
            QRectF(
                self.start_x - 1.0,
                self.start_y - 1.0,
                self.table_width + 2.0,
                total_h + 2.0,
            )
        )

    def _draw_caption(
        self, painter: QPainter, hl_prog: float, move_prog: float
    ) -> None:
        painter.setFont(self.font_main)
        painter.setPen(self.c_text)
        rect: QRectF = QRectF(0.0, 260.0, float(self.width()), 30.0)

        if move_prog >= 1.0:
            msg: str = "Sorted by 'Score' (Ascending: 12 -> 88)."
        elif move_prog > 0.0:
            msg = "Reordering rows by 'Score'..."
        elif hl_prog > 0.0:
            msg = "Selecting target sort column: 'Score' (Ascending)..."
        else:
            msg = "Unsorted Dataset"

        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, msg)