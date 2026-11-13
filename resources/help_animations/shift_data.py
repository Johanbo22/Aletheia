from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
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
        self.c_muted: QColor = QColor("#888888")
        self.c_shift_bg: QColor = QColor("#2b4a6b")
        self.c_nan_bg: QColor = QColor("#5a3e2b")

        self.headers: tuple[str, str, str] = ("Day", "Price", "Price_lag_1")
        self.col_widths: tuple[float, float, float] = (60.0, 90.0, 110.0)
        self.table_width: float = sum(self.col_widths)
        self.row_height: float = 34.0

        self.days: tuple[str, ...] = ("Mon", "Tue", "Wed", "Thu")
        self.prices: tuple[str, ...] = ("105", "112", "108", "120")

        self.start_x: float = (550.0 - self.table_width) / 2.0
        self.start_y: float = 55.0

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        painter.fillRect(self.rect(), self.c_bg)

        copy_prog: float = self.get_eased_progress(progress, 0.10, 0.35)
        shift_prog: float = self.get_eased_progress(progress, 0.40, 0.70)
        nan_prog: float = self.get_eased_progress(progress, 0.70, 0.90)

        self._draw_headers(painter, copy_prog)
        self._draw_base_table(painter, copy_prog)
        if copy_prog > 0.0:
            self._draw_shifted_column(painter, copy_prog, shift_prog, nan_prog)

        self._draw_caption(painter, copy_prog, shift_prog, nan_prog)

    def _draw_headers(self, painter: QPainter, copy_prog: float) -> None:
        painter.setFont(self.font_bold)
        curr_x: float = self.start_x

        for idx, text in enumerate(self.headers):
            width: float = self.col_widths[idx]
            alpha: float = copy_prog if idx == 2 else 1.0
            if alpha <= 0.0:
                continue

            rect: QRectF = QRectF(curr_x, self.start_y, width, self.row_height)
            painter.setOpacity(alpha)
            painter.setBrush(self.c_header_bg)
            painter.setPen(self.c_border)
            painter.drawRect(rect)
            painter.setPen(self.c_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            painter.setOpacity(1.0)
            curr_x += width

    def _draw_base_table(self, painter: QPainter, copy_prog: float) -> None:
        painter.setFont(self.font_main)
        for r_idx, day in enumerate(self.days):
            y_pos: float = self.start_y + ((r_idx + 1) * self.row_height)
            day_rect: QRectF = QRectF(
                self.start_x, y_pos, self.col_widths[0], self.row_height
            )
            price_rect: QRectF = QRectF(
                self.start_x + self.col_widths[0],
                y_pos,
                self.col_widths[1],
                self.row_height,
            )

            painter.setBrush(self.c_table_bg)
            painter.setPen(self.c_border)
            painter.drawRect(day_rect)
            painter.drawRect(price_rect)

            painter.setPen(self.c_text)
            painter.drawText(day_rect, Qt.AlignmentFlag.AlignCenter, day)
            painter.drawText(price_rect, Qt.AlignmentFlag.AlignCenter, self.prices[r_idx])

            if copy_prog > 0.0:
                lag_x: float = self.start_x + self.col_widths[0] + self.col_widths[1]
                lag_bg_rect: QRectF = QRectF(
                    lag_x, y_pos, self.col_widths[2], self.row_height
                )
                painter.setOpacity(copy_prog)
                painter.setBrush(self.c_table_bg)
                painter.setPen(self.c_border)
                painter.drawRect(lag_bg_rect)
                painter.setOpacity(1.0)

    def _draw_shifted_column(
        self,
        painter: QPainter,
        copy_prog: float,
        shift_prog: float,
        nan_prog: float,
    ) -> None:
        lag_x: float = self.start_x + self.col_widths[0] + self.col_widths[1]
        col_w: float = self.col_widths[2]
        clip_rect: QRectF = QRectF(
            lag_x,
            self.start_y + self.row_height,
            col_w,
            len(self.prices) * self.row_height,
        )

        painter.save()
        painter.setClipRect(clip_rect)
        painter.setFont(self.font_main)

        for r_idx, price in enumerate(self.prices):
            base_y: float = self.start_y + ((r_idx + 1) * self.row_height)
            shifted_y: float = base_y + (shift_prog * self.row_height)
            cell_rect: QRectF = QRectF(lag_x, shifted_y, col_w, self.row_height)

            opacity: float = copy_prog
            if r_idx == len(self.prices) - 1:
                opacity *= 1.0 - shift_prog

            painter.setOpacity(opacity)
            painter.setBrush(self.c_shift_bg)
            painter.setPen(QPen(self.c_border, 1.0))
            painter.drawRect(cell_rect)
            painter.setPen(self.c_text)
            painter.drawText(cell_rect, Qt.AlignmentFlag.AlignCenter, price)

        if nan_prog > 0.0:
            nan_rect: QRectF = QRectF(
                lag_x, self.start_y + self.row_height, col_w, self.row_height
            )
            painter.setOpacity(nan_prog)
            painter.setBrush(self.c_nan_bg)
            painter.setPen(self.c_border)
            painter.drawRect(nan_rect)
            painter.setPen(self.c_muted)
            painter.drawText(nan_rect, Qt.AlignmentFlag.AlignCenter, "NaN")

        painter.restore()

    def _draw_caption(
        self,
        painter: QPainter,
        copy_prog: float,
        shift_prog: float,
        nan_prog: float,
    ) -> None:
        painter.setFont(self.font_main)
        painter.setPen(self.c_text)
        rect: QRectF = QRectF(0.0, 260.0, float(self.width()), 30.0)

        if nan_prog > 0.0:
            text: str = "Empty leading row filled with NaN (or custom fill value)."
        elif shift_prog > 0.0:
            text = "Shifting values down by 1 period (Lag +1)..."
        elif copy_prog > 0.0:
            text = "Creating target shift column..."
        else:
            text = "Original Sequential Series"

        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)