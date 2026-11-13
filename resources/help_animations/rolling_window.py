from dataclasses import dataclass

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from src.ui.help_animation_engine import HelpAnimationEngine

@dataclass(frozen=True)
class RollingRow:
    row_id: str
    raw_value: str
    rolling_mean: str

class Animation(HelpAnimationEngine):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, fps=60, duration_ms=7000)

        self.c_bg: QColor = QColor("#2b2b2b")
        self.c_table_bg: QColor = QColor("#1e1e1e")
        self.c_header_bg: QColor = QColor("#333333")
        self.c_border: QColor = QColor("#444444")
        self.c_text: QColor = QColor("#e0e0e0")
        self.c_muted: QColor = QColor("#888888")
        self.c_window_fill: QColor = QColor("#2b4a6b")
        self.c_window_border: QColor = QColor("#4a90e2")
        self.c_result_bg: QColor = QColor("#2b6b4a")

        self.headers: tuple[str, str, str] = ("ID", "Value", "Roll_Mean(3)")
        self.col_widths: tuple[float, float, float] = (50.0, 90.0, 120.0)
        self.table_width: float = sum(self.col_widths)
        self.row_height: float = 32.0

        self.rows: tuple[RollingRow, ...] = (
            RollingRow("1", "10", "NaN"),
            RollingRow("2", "20", "NaN"),
            RollingRow("3", "30", "20.0"),
            RollingRow("4", "40", "30.0"),
            RollingRow("5", "50", "40.0"),
        )

        self.start_x: float = (550.0 - self.table_width) / 2.0
        self.start_y: float = 55.0

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        painter.fillRect(self.rect(), self.c_bg)

        reveal_col: float = self.get_eased_progress(progress, 0.05, 0.20)
        slide_1: float = self.get_eased_progress(progress, 0.30, 0.50)
        slide_2: float = self.get_eased_progress(progress, 0.55, 0.75)

        window_top_idx: float = slide_1 + slide_2
        self._draw_headers(painter, reveal_col)
        self._draw_rows(painter, reveal_col, window_top_idx, progress)

        if reveal_col > 0.0:
            self._draw_sliding_window(painter, window_top_idx, reveal_col)

        self._draw_caption(painter, progress)

    def _draw_headers(self, painter: QPainter, reveal_col: float) -> None:
        painter.setFont(self.font_bold)
        curr_x: float = self.start_x

        for idx, title in enumerate(self.headers):
            width: float = self.col_widths[idx]
            alpha: float = reveal_col if idx == 2 else 1.0
            if alpha <= 0.0:
                continue

            rect: QRectF = QRectF(curr_x, self.start_y, width, self.row_height)
            painter.setOpacity(alpha)
            painter.setBrush(self.c_header_bg)
            painter.setPen(self.c_border)
            painter.drawRect(rect)
            painter.setPen(self.c_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, title)
            painter.setOpacity(1.0)
            curr_x += width

    def _draw_rows(
            self,
            painter: QPainter,
            reveal_col: float,
            window_top_idx: float,
            progress: float,
    ) -> None:
        painter.setFont(self.font_main)
        active_end_row: int = int(round(window_top_idx)) + 2

        for r_idx, row in enumerate(self.rows):
            y_pos: float = self.start_y + ((r_idx + 1) * self.row_height)
            self._draw_base_cells(painter, y_pos, row)
            if reveal_col > 0.0:
                self._draw_result_cell(
                    painter, y_pos, r_idx, row, reveal_col, active_end_row, progress
                )

    def _draw_base_cells(self, painter: QPainter, y_pos: float, row: RollingRow) -> None:
        curr_x: float = self.start_x
        for c_idx, val in enumerate((row.row_id, row.raw_value)):
            width: float = self.col_widths[c_idx]
            rect: QRectF = QRectF(curr_x, y_pos, width, self.row_height)
            painter.setBrush(self.c_table_bg)
            painter.setPen(self.c_border)
            painter.drawRect(rect)
            painter.setPen(self.c_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, val)
            curr_x += width

    def _draw_result_cell(
            self,
            painter: QPainter,
            y_pos: float,
            r_idx: int,
            row: RollingRow,
            reveal_col: float,
            active_end_row: int,
            progress: float,
    ) -> None:
        res_x: float = self.start_x + self.col_widths[0] + self.col_widths[1]
        rect: QRectF = QRectF(res_x, y_pos, self.col_widths[2], self.row_height)

        is_computed: bool = (
                (r_idx <= 2 and progress >= 0.22)
                or (r_idx == 3 and progress >= 0.48)
                or (r_idx == 4 and progress >= 0.73)
        )
        is_active_target: bool = r_idx == active_end_row and r_idx >= 2

        bg_color: QColor = self.c_result_bg if is_active_target else self.c_table_bg
        painter.setOpacity(reveal_col)
        painter.setBrush(bg_color)
        painter.setPen(self.c_border)
        painter.drawRect(rect)

        if is_computed:
            pen_color: QColor = self.c_muted if row.rolling_mean == "NaN" else self.c_text
            painter.setPen(pen_color)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, row.rolling_mean)

        painter.setOpacity(1.0)

    def _draw_sliding_window(
            self, painter: QPainter, window_top_idx: float, reveal_col: float
    ) -> None:
        win_x: float = self.start_x + self.col_widths[0]
        win_y: float = self.start_y + ((1.0 + window_top_idx) * self.row_height)
        win_w: float = self.col_widths[1]
        win_h: float = 3.0 * self.row_height

        fill: QColor = QColor(self.c_window_fill)
        fill.setAlphaF(0.35 * reveal_col)
        border: QColor = QColor(self.c_window_border)
        border.setAlphaF(reveal_col)

        painter.setBrush(fill)
        painter.setPen(QPen(border, 2.0))
        painter.drawRect(QRectF(win_x, win_y, win_w, win_h))

    def _draw_caption(self, painter: QPainter, progress: float) -> None:
        painter.setFont(self.font_main)
        painter.setPen(self.c_text)
        caption_rect: QRectF = QRectF(0.0, 275.0, float(self.width()), 30.0)

        if progress < 0.22:
            msg: str = "Initializing 3-period rolling window..."
        elif progress < 0.48:
            msg = "Window [10, 20, 30] -> Mean = 20.0"
        elif progress < 0.73:
            msg = "Window slides down: [20, 30, 40] -> Mean = 30.0"
        else:
            msg = "Window slides down: [30, 40, 50] -> Mean = 40.0"

        painter.drawText(caption_rect, Qt.AlignmentFlag.AlignCenter, msg)