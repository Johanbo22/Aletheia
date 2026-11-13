from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget

from src.ui.help_animation_engine import HelpAnimationEngine


class Animation(HelpAnimationEngine):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, fps=60, duration_ms=6500)

        self.c_bg: QColor = QColor("#2b2b2b")
        self.c_table_bg: QColor = QColor("#1e1e1e")
        self.c_header_bg: QColor = QColor("#333333")
        self.c_border: QColor = QColor("#444444")
        self.c_text: QColor = QColor("#e0e0e0")
        self.c_panel_bg: QColor = QColor("#3a3a3a")
        self.c_focus_bg: QColor = QColor("#2b4a6b")
        self.c_success_bg: QColor = QColor("#2d5a2d")
        self.c_success_text: QColor = QColor("#ccffcc")

        self.headers: tuple[str, str] = ("ID", "City")
        self.col_widths: tuple[float, float] = (60.0, 180.0)
        self.table_width: float = sum(self.col_widths)
        self.row_height: float = 34.0

        self.rows: tuple[tuple[str, str, str, str], ...] = (
            ("1", '  "new york"  ', '"new york"', '"New York"'),
            ("2", ' "cOPENHAGEN" ', '"cOPENHAGEN"', '"Copenhagen"'),
            ("3", '   "tOKYO"    ', '"tOKYO"', '"Tokyo"'),
        )

        self.start_x: float = (550.0 - self.table_width) / 2.0
        self.start_y: float = 105.0

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        painter.fillRect(self.rect(), self.c_bg)

        panel_prog: float = self.get_eased_progress(progress, 0.08, 0.22)
        trim_prog: float = self.get_eased_progress(progress, 0.28, 0.50)
        case_prog: float = self.get_eased_progress(progress, 0.55, 0.78)
        flash_prog: float = self.get_eased_progress(progress, 0.78, 0.95)

        self._draw_operation_banner(painter, panel_prog, trim_prog, case_prog)
        self._draw_headers(painter, panel_prog)
        self._draw_rows(painter, panel_prog, trim_prog, case_prog, flash_prog)

    def _draw_operation_banner(
        self,
        painter: QPainter,
        panel_prog: float,
        trim_prog: float,
        case_prog: float,
    ) -> None:
        if panel_prog <= 0.0:
            return

        banner_w: float = 280.0
        banner_h: float = 34.0
        banner_x: float = (float(self.width()) - banner_w) / 2.0
        banner_y: float = 20.0 - ((1.0 - panel_prog) * 30.0)

        rect: QRectF = QRectF(banner_x, banner_y, banner_w, banner_h)
        painter.setOpacity(panel_prog)
        painter.setBrush(self.c_panel_bg)
        painter.setPen(self.c_border)
        painter.drawRoundedRect(rect, 4.0, 4.0)

        if case_prog > 0.0:
            op_text: str = "Operation: Convert to Title Case"
        elif trim_prog > 0.0:
            op_text = "Operation: Trim Whitespace"
        else:
            op_text = "Target Column: 'City'"

        painter.setFont(self.font_bold)
        painter.setPen(self.c_text)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, op_text)
        painter.setOpacity(1.0)

    def _draw_headers(self, painter: QPainter, panel_prog: float) -> None:
        painter.setFont(self.font_bold)
        curr_x: float = self.start_x

        for idx, text in enumerate(self.headers):
            width: float = self.col_widths[idx]
            rect: QRectF = QRectF(
                curr_x, self.start_y - self.row_height, width, self.row_height
            )
            bg: QColor = (
                self.lerp_color(self.c_header_bg, self.c_focus_bg, panel_prog)
                if idx == 1
                else self.c_header_bg
            )
            painter.setBrush(bg)
            painter.setPen(self.c_border)
            painter.drawRect(rect)
            painter.setPen(self.c_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            curr_x += width

    def _draw_rows(
        self,
        painter: QPainter,
        panel_prog: float,
        trim_prog: float,
        case_prog: float,
        flash_prog: float,
    ) -> None:
        painter.setFont(self.font_main)
        flash: float = (
            1.0 - abs(flash_prog - 0.5) * 2.0 if flash_prog > 0.0 else 0.0
        )

        for r_idx, row in enumerate(self.rows):
            y_pos: float = self.start_y + (r_idx * self.row_height)
            id_rect: QRectF = QRectF(
                self.start_x, y_pos, self.col_widths[0], self.row_height
            )
            city_rect: QRectF = QRectF(
                self.start_x + self.col_widths[0],
                y_pos,
                self.col_widths[1],
                self.row_height,
            )

            painter.setBrush(self.c_table_bg)
            painter.setPen(self.c_border)
            painter.drawRect(id_rect)
            painter.setPen(self.c_text)
            painter.drawText(id_rect, Qt.AlignmentFlag.AlignCenter, row[0])

            city_bg: QColor = self.lerp_color(
                self.c_table_bg, self.c_focus_bg, panel_prog * 0.4
            )
            city_fg: QColor = self.c_text
            if flash > 0.0:
                city_bg = self.lerp_color(city_bg, self.c_success_bg, flash)
                city_fg = self.lerp_color(self.c_text, self.c_success_text, flash)

            painter.setBrush(city_bg)
            painter.setPen(self.c_border)
            painter.drawRect(city_rect)

            display_val: str = row[1]
            if case_prog >= 0.5:
                display_val = row[3]
            elif trim_prog >= 0.5:
                display_val = row[2]

            painter.setPen(city_fg)
            painter.drawText(city_rect, Qt.AlignmentFlag.AlignCenter, display_val)