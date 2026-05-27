from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter

from ui.help_animation_engine import HelpAnimationEngine


class Animation(HelpAnimationEngine):
    """
    Animation illustrating the Z-Score outlier detection method.

    The animation unfolds in three distinct phases:
    1. Reveals the computed Z-Score column.
    2. Highlights the row containing a Z-Score exceeding the threshold.
    3. Collapses and removes the identified outlier row from the dataset.
    """

    def __init__(self) -> None:
        super().__init__(duration_ms=6000)

        self.c_bg: QColor = QColor("#2b2b2b")
        self.c_table_bg: QColor = QColor("#1e1e1e")
        self.c_header_bg: QColor = QColor("#333333")
        self.c_border: QColor = QColor("#444444")
        self.c_text: QColor = QColor("#e0e0e0")

        self.c_outlier_bg: QColor = QColor("#662222")
        self.c_outlier_text: QColor = QColor("#ffcccc")
        self.c_zscore_bg: QColor = QColor("#2a4d69")

        self.headers: list[str] = ["ID", "Value", "Z-Score"]
        self.outlier_row_idx: int = 2
        self.score_col_idx: int = 2

        self.data_rows: list[list[str]] = [
            ["001", "10.1", "-0.2"],
            ["002", "11.2", "-0.1"],
            ["003", "95.5", "3.8"],
            ["004", "9.8", "-0.3"],
            ["005", "10.5", "-0.2"],
        ]

        self.base_row_height: float = 32.0
        self.base_col_widths: list[float] = [60.0, 80.0, 80.0]
        self.start_y: float = 60.0

    def draw_animation(self, painter: "QPainter", progress: float) -> None:
        """
        Draws the animation sequence onto the provided painter based on completion progress.

        :param painter: The QPainter instance responsible for rendering the widget.
        :param progress: A float between 0.0 and 1.0 representing animation timeline.
        """
        painter.fillRect(self.rect(), self.c_bg)

        reveal_prog: float = self.get_eased_progress(progress, 0.0, 0.3)
        highlight_prog: float = self.get_eased_progress(progress, 0.3, 0.6)
        collapse_prog: float = self.get_eased_progress(progress, 0.6, 1.0)

        current_widths: list[float] = list(self.base_col_widths)
        current_widths[self.score_col_idx] *= reveal_prog

        current_total_width: float = sum(current_widths)
        start_x: float = (self.width() - current_total_width) / 2.0

        self._draw_row(
            painter=painter, x=start_x, y=self.start_y - self.base_row_height,
            col_texts=self.headers, widths=current_widths,
            row_height=self.base_row_height, is_header=True,
            reveal_intensity=reveal_prog
        )

        current_y: float = self.start_y

        for index, row in enumerate(self.data_rows):
            is_outlier: bool = (index == self.outlier_row_idx)

            row_h: float = self.base_row_height
            if is_outlier:
                row_h *= (1.0 - collapse_prog)

            if row_h < 1.0:
                continue

            row_highlight: float = highlight_prog if is_outlier else 0.0
            row_alpha: float = 1.0 - collapse_prog if is_outlier else 1.0

            self._draw_row(
                painter=painter, x=start_x, y=current_y,
                col_texts=row, widths=current_widths,
                row_height=row_h, is_header=False,
                highlight_intensity=row_highlight,
                alpha=row_alpha,
                reveal_intensity=reveal_prog
            )

            current_y += row_h

    def _draw_row(
            self, painter: "QPainter", x: float, y: float, col_texts: list[str],
            widths: list[float], row_height: float, is_header: bool = False,
            highlight_intensity: float = 0.0, alpha: float = 1.0, reveal_intensity: float = 1.0
    ) -> None:
        """
        Helper method to render a single table row with dynamic dimensions and colors.

        :param painter: QPainter context.
        :param x: Starting X coordinate for the row.
        :param y: Starting Y coordinate for the row.
        :param col_texts: List of strings containing cell data.
        :param widths: Target widths for each column cell.
        :param row_height: Target height of the row.
        :param is_header: Boolean flag toggling header styling.
        :param highlight_intensity: Lerp factor (0-1) for warning color mapping.
        :param alpha: Transparency factor for fade-outs.
        :param reveal_intensity: Lerp factor (0-1) for new column reveals.
        """
        current_x: float = x
        painter.setFont(self.font_bold if is_header else self.font_main)

        for index, text in enumerate(col_texts):
            col_w: float = widths[index]
            if col_w < 1.0:
                continue

            cell_rect: QRectF = QRectF(current_x, y, col_w, row_height)

            bg_color: QColor = self.c_header_bg if is_header else self.c_table_bg
            text_color: QColor = QColor(self.c_text)

            if index == self.score_col_idx:
                bg_color = self.lerp_color(bg_color, self.c_zscore_bg, reveal_intensity * 0.5)
                text_color.setAlphaF(reveal_intensity * alpha)
            else:
                text_color.setAlphaF(alpha)

            if highlight_intensity > 0:
                bg_color = self.lerp_color(bg_color, self.c_outlier_bg, highlight_intensity)
                text_color = self.lerp_color(text_color, self.c_outlier_text, highlight_intensity)
                text_color.setAlphaF(alpha)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bg_color)
            painter.drawRect(cell_rect)

            painter.setPen(text_color)
            painter.save()
            painter.setClipRect(cell_rect)

            text_rect: QRectF = cell_rect.adjusted(5.0, 0.0, -5.0, 0.0)
            align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            if index == 0:
                align = Qt.AlignmentFlag.AlignCenter

            painter.drawText(text_rect, align, text)
            painter.restore()

            border_color: QColor = QColor(self.c_border)
            border_color.setAlphaF(alpha)
            painter.setPen(border_color)

            line_right_x: int = int(current_x + col_w)
            line_bottom_y: int = int(y + row_height)
            line_y: int = int(y)
            line_x: int = int(current_x)

            painter.drawLine(line_right_x, line_y, line_right_x, line_bottom_y)
            painter.drawLine(line_x, line_bottom_y, line_right_x, line_bottom_y)

            if is_header:
                painter.drawLine(line_x, line_y, line_right_x, line_y)
            if index == 0:
                painter.drawLine(line_x, line_y, line_x, line_bottom_y)

            current_x += col_w