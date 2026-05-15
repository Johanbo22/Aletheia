from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter

from ui.help_animation_engine import HelpAnimationEngine


class Animation(HelpAnimationEngine):
    """
    Animation showing the dropping of empty columns.
    Visualizes scanning a dataset for columns containing only missing values (NaN)
    and fluidly collapsing them to clean the dataset.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent, fps=60, duration_ms=8000)

        self.c_table_bg = QColor("#1e1e1e")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")

        self.c_highlight_bg = QColor("#5a2b2b")

        self.columns = [
            {"name": "ID", "empty": False},
            {"name": "Sensor_1", "empty": True},
            {"name": "Value", "empty": False},
            {"name": "Sensor_2", "empty": True}
        ]

        self.rows = [
            ["1", "NaN", "42.1", "NaN"],
            ["2", "NaN", "18.0", "NaN"],
            ["3", "NaN", "33.5", "NaN"]
        ]

        # Layout metrics
        self.base_col_w = 85.0
        self.row_h = 45.0

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        p_intro = self.get_eased_progress(progress, 0.0, 0.1)
        p_highlight = self.get_eased_progress(progress, 0.15, 0.35)
        p_transform = self.get_eased_progress(progress, 0.45, 0.75)

        if p_intro == 0.0:
            return

        total_w = 0.0
        col_widths = []
        for col in self.columns:
            w = self.base_col_w * (1.0 - p_transform) if col["empty"] else self.base_col_w
            col_widths.append(w)
            total_w += w

        cx = self.width() / 2.0
        cy = self.height() / 2.0

        start_x = cx - total_w / 2.0
        start_y = cy - (len(self.rows) + 1) * self.row_h / 2.0 - 15.0

        self._draw_table(painter, start_x, start_y, col_widths, p_highlight, p_transform)
        self._draw_explanation(painter, start_y + (len(self.rows) + 1) * self.row_h + 20.0, p_highlight, p_transform)

    def _draw_table(self, painter: QPainter, x: float, y: float, col_widths: list[float], p_highlight: float,
                    p_transform: float) -> None:
        curr_x = x
        for c_idx, col in enumerate(self.columns):
            w = col_widths[c_idx]

            if w <= 0.1:
                continue
            if col["empty"]:
                header_bg = self.lerp_color(self.c_header_bg, self.c_highlight_bg, p_highlight)
                cell_bg = self.lerp_color(self.c_table_bg, self.c_highlight_bg, p_highlight)
                text_alpha = int(255 * (1.0 - p_transform))
            else:
                header_bg = self.c_header_bg
                cell_bg = self.c_table_bg
                text_alpha = 255

            self._draw_header_cell(painter, curr_x, y, w, col["name"], header_bg, text_alpha)
            self._draw_row_cells(painter, curr_x, y, w, c_idx, cell_bg, text_alpha, p_transform)

            curr_x += w

    def _draw_header_cell(self, painter: QPainter, x: float, y: float, w: float, name: str, bg_color: QColor,
                          text_alpha: int) -> None:
        rect = QRectF(x, y, w, self.row_h)

        painter.setBrush(bg_color)
        painter.setPen(self.c_border)
        painter.drawRect(rect)

        painter.save()
        painter.setClipRect(rect)
        painter.setFont(self.font_bold)

        c_text = QColor(self.c_text)
        c_text.setAlpha(text_alpha)
        painter.setPen(c_text)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, name)

        painter.restore()

    def _draw_row_cells(self, painter: QPainter, x: float, start_y: float, w: float, c_idx: int, bg_color: QColor,
                        text_alpha: int, p_transform: float) -> None:
        for r_idx, row in enumerate(self.rows):
            y = start_y + (r_idx + 1) * self.row_h
            rect = QRectF(x, y, w, self.row_h)

            painter.setBrush(bg_color)
            painter.setPen(self.c_border)
            painter.drawRect(rect)

            painter.save()
            painter.setClipRect(rect)
            painter.setFont(self.font_main)

            val = row[c_idx]

            if val == "NaN":
                c_text = QColor(self.c_text)
                null_alpha = int(120 * (1.0 - p_transform))
                c_text.setAlpha(min(text_alpha, null_alpha))
            else:
                c_text = QColor(self.c_text)
                c_text.setAlpha(text_alpha)

            painter.setPen(c_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, val)

            painter.restore()

    def _draw_explanation(self, painter: QPainter, y: float, p_highlight: float, p_transform: float) -> None:
        """Draws the dynamic explanatory text beneath the table."""
        painter.setFont(self.font_main)

        c_text = QColor(self.c_text)
        painter.setPen(c_text)

        if p_transform == 1.0:
            text = "Cleaned: Empty columns removed."
        elif p_highlight == 1.0 and p_transform > 0.0:
            text = "Dropping columns..."
        elif p_highlight > 0.0:
            text = "Identifying columns with only missing values..."
        else:
            text = "Raw Dataset"

        painter.drawText(QRectF(0, float(y), float(self.width()), 30.0), Qt.AlignmentFlag.AlignCenter, text)