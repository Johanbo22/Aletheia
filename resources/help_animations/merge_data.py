from typing import List
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPen, QPainter

from ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """
    Animation showing data merging (joining)
    Visualizes two datasets aligning by a common key column horizontally
    into a single expanded dataset
    """

    def __init__(self) -> None:
        super().__init__(duration_ms=6000)

        self.c_bg = QColor("#2b2b2b")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")

        self.c_dataset_1 = QColor("#2b4a6b")
        self.c_dataset_2 = QColor("#2b6b4a")
        self.c_highlight = QColor("#6b5a2b")

        self.col_w_id: int = 50
        self.col_w_data: int = 100
        self.row_height: int = 28

        self.ds1_headers: List[str] = ["ID", "Item"]
        self.ds1_rows: List[List[str]] = [
            ["1", "Apple"],
            ["2", "Pear"]
        ]

        self.ds2_headers: List[str] = ["ID", "Price"]
        self.ds2_rows: List[List[str]] = [
            ["1", "$2.00"],
            ["2", "$3.50"]
        ]

        self.ds1_start_x: float = 100.0
        self.ds2_start_x: float = 350.0
        self.start_y: float = 100.0

        self.ds2_id_final_x: float = self.ds1_start_x
        self.ds2_data_final_x: float = self.ds1_start_x + self.col_w_id + self.col_w_data

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        painter.fillRect(self.rect(), self.c_bg)

        highlight_prog: float = self.get_eased_progress(progress, 0.1, 0.3)
        move_prog: float = self.get_eased_progress(progress, 0.3, 0.7)
        pulse_prog: float = self.get_eased_progress(progress, 0.7, 0.9)

        self._draw_table(
            painter,
            self.ds1_start_x,
            self.start_y,
            self.ds1_headers,
            self.ds1_rows,
            self.c_dataset_1,
            highlight_prog
        )
        ds2_current_id_x: float = self.ds2_start_x + (self.ds2_id_final_x - self.ds2_start_x) * move_prog
        ds2_data_start_x: float = self.ds2_start_x + self.col_w_id
        ds2_current_data_x: float = ds2_data_start_x + (self.ds2_data_final_x - ds2_data_start_x) * move_prog

        id_opacity: float = 1.0 - move_prog

        if id_opacity > 0:
            painter.setOpacity(id_opacity)
            self._draw_column(
                painter,
                ds2_current_id_x,
                self.start_y,
                self.ds2_headers[0],
                [row[0] for row in self.ds2_rows],
                self.c_dataset_2,
                self.col_w_id,
                highlight_prog
            )
            painter.setOpacity(1.0)

        self._draw_column(
            painter,
            ds2_current_data_x,
            self.start_y,
            self.ds2_headers[1],
            [row[1] for row in self.ds2_rows],
            self.c_dataset_2,
            self.col_w_data,
            highlight_prog=0.0
        )

        if pulse_prog > 0:
            self._draw_success_pulse(painter, pulse_prog)

    def _draw_table(
            self,
            painter: QPainter,
            x: float,
            y: float,
            headers: List[str],
            rows: List[List[str]],
            bg_color: QColor,
            highlight_prog: float
    ) -> None:
        self._draw_column(
            painter, x, y, headers[0], [r[0] for r in rows],
            bg_color, self.col_w_id, highlight_prog
        )
        self._draw_column(
            painter, x + self.col_w_id, y, headers[1], [r[1] for r in rows],
            bg_color, self.col_w_data, highlight_prog=0.0
        )

    def _draw_column(
            self,
            painter: QPainter,
            x: float,
            y: float,
            header: str,
            values: List[str],
            bg_color: QColor,
            width: int,
            highlight_prog: float
    ) -> None:
        """Helper to draw a single vertical column of a table."""
        current_bg = self.lerp_color(bg_color, self.c_highlight, highlight_prog)
        current_header_bg = self.lerp_color(self.c_header_bg, self.c_highlight, highlight_prog)

        painter.setFont(self.font_bold)
        rect = QRectF(x, y, width, self.row_height)
        painter.setBrush(current_header_bg)
        painter.setPen(self.c_border)
        painter.drawRect(rect)

        painter.setPen(self.c_text)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, header)

        painter.setFont(self.font_main)
        for index, val in enumerate(values):
            row_y = y + (index + 1) * self.row_height
            rect = QRectF(x, row_y, width, self.row_height)

            painter.setBrush(current_bg)
            painter.setPen(self.c_border)
            painter.drawRect(rect)

            painter.setPen(self.c_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, val)

    def _draw_success_pulse(self, painter: QPainter, pulse_progress: float) -> None:
        """Draws an animated expanding and fading border around the final merged table."""
        pulse_intensity: float = pulse_progress * (1.0 - pulse_progress) * 4.0

        total_height: float = (1 + len(self.ds1_rows)) * self.row_height
        total_width: float = self.col_w_id + (self.col_w_data * 2)

        highlight_color = self.lerp_color(self.c_border, self.accent_color, pulse_intensity)

        painter.setPen(QPen(highlight_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(
            QRectF(self.ds1_start_x - 1, self.start_y - 1, total_width + 2, total_height + 2)
        )