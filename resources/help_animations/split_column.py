from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget

from src.ui.help_animation_engine import HelpAnimationEngine


class Animation(HelpAnimationEngine):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, fps=60, duration_ms=7500)

        self.c_bg: QColor = QColor("#2b2b2b")
        self.c_table_bg: QColor = QColor("#1e1e1e")
        self.c_header_bg: QColor = QColor("#333333")
        self.c_border: QColor = QColor("#444444")
        self.c_text: QColor = QColor("#e0e0e0")
        self.c_source_hl: QColor = QColor("#2b4a6b")
        self.c_new_col: QColor = QColor("#2b6b4a")

        self.headers: tuple[str, str, str, str] = (
            "ID",
            "Full Name",
            "First_Name",
            "Last_Name",
        )
        self.base_widths: tuple[float, float, float, float] = (
            45.0,
            135.0,
            100.0,
            100.0,
        )
        self.row_height: float = 36.0

        self.rows: tuple[tuple[str, str, str, str], ...] = (
            ("1", "Alice, Smith", "Alice", "Smith"),
            ("2", "Bob, Jones", "Bob", "Jones"),
            ("3", "Carol, White", "Carol", "White"),
        )
        self.start_y: float = 65.0

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        painter.fillRect(self.rect(), self.c_bg)

        hl_prog: float = self.get_eased_progress(progress, 0.10, 0.25)
        expand_prog: float = self.get_eased_progress(progress, 0.30, 0.55)
        pop_prog: float = self.get_eased_progress(progress, 0.55, 0.80)
        outro_prog: float = self.get_eased_progress(progress, 0.85, 1.00)

        widths: list[float] = [
            self.base_widths[0],
            self.base_widths[1],
            self.base_widths[2] * expand_prog,
            self.base_widths[3] * expand_prog,
        ]
        total_w: float = sum(widths)
        start_x: float = (float(self.width()) - total_w) / 2.0

        self._draw_table(painter, start_x, widths, hl_prog, pop_prog, outro_prog)
        self._draw_caption(painter, hl_prog, expand_prog, pop_prog)

    def _draw_table(
        self,
        painter: QPainter,
        start_x: float,
        widths: list[float],
        hl_prog: float,
        pop_prog: float,
        outro_prog: float,
    ) -> None:
        curr_x: float = start_x
        for c_idx, width in enumerate(widths):
            if width <= 0.5:
                continue

            header_bg, cell_bg, text_alpha = self._resolve_column_style(
                c_idx, hl_prog, pop_prog, outro_prog
            )
            self._draw_header_cell(
                painter, curr_x, width, self.headers[c_idx], header_bg, text_alpha
            )
            self._draw_column_rows(
                painter, curr_x, width, c_idx, cell_bg, text_alpha, pop_prog
            )
            curr_x += width

    def _resolve_column_style(
        self, c_idx: int, hl_prog: float, pop_prog: float, outro_prog: float
    ) -> tuple[QColor, QColor, int]:
        if c_idx == 1:
            intensity: float = hl_prog * (1.0 - outro_prog)
            return (
                self.lerp_color(self.c_header_bg, self.c_source_hl, intensity),
                self.lerp_color(self.c_table_bg, self.c_source_hl, intensity),
                255,
            )
        if c_idx in (2, 3):
            intensity = 1.0 - outro_prog
            return (
                self.lerp_color(self.c_header_bg, self.c_new_col, intensity),
                self.lerp_color(self.c_table_bg, self.c_new_col, intensity),
                int(255 * pop_prog),
            )
        return self.c_header_bg, self.c_table_bg, 255

    def _draw_header_cell(
        self,
        painter: QPainter,
        x_pos: float,
        width: float,
        title: str,
        bg_color: QColor,
        text_alpha: int,
    ) -> None:
        rect: QRectF = QRectF(x_pos, self.start_y, width, self.row_height)
        painter.setBrush(bg_color)
        painter.setPen(self.c_border)
        painter.drawRect(rect)

        painter.save()
        painter.setClipRect(rect)
        painter.setFont(self.font_bold)
        txt_col: QColor = QColor(self.c_text)
        txt_col.setAlpha(text_alpha)
        painter.setPen(txt_col)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, title)
        painter.restore()

    def _draw_column_rows(
        self,
        painter: QPainter,
        x_pos: float,
        width: float,
        c_idx: int,
        bg_color: QColor,
        text_alpha: int,
        pop_prog: float,
    ) -> None:
        for r_idx, row in enumerate(self.rows):
            y_pos: float = self.start_y + ((r_idx + 1) * self.row_height)
            rect: QRectF = QRectF(x_pos, y_pos, width, self.row_height)
            painter.setBrush(bg_color)
            painter.setPen(self.c_border)
            painter.drawRect(rect)

            painter.save()
            painter.setClipRect(rect)
            painter.setFont(self.font_main)
            if c_idx in (2, 3):
                painter.translate(-15.0 * (1.0 - pop_prog), 0.0)

            txt_col: QColor = QColor(self.c_text)
            txt_col.setAlpha(text_alpha)
            painter.setPen(txt_col)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, row[c_idx])
            painter.restore()

    def _draw_caption(
        self,
        painter: QPainter,
        hl_prog: float,
        expand_prog: float,
        pop_prog: float,
    ) -> None:
        painter.setFont(self.font_main)
        painter.setPen(self.c_text)
        rect: QRectF = QRectF(0.0, 240.0, float(self.width()), 30.0)

        if pop_prog >= 1.0:
            msg: str = "Split complete: 2 new columns created."
        elif expand_prog > 0.0:
            msg = "Splitting on delimiter ',' into new columns..."
        elif hl_prog > 0.0:
            msg = "Scanning 'Full Name' for delimiter ','..."
        else:
            msg = "Original Dataset"

        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, msg)