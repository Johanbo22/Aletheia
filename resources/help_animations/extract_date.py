from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter

from ui.help_animation_engine import HelpAnimationEngine


class Animation(HelpAnimationEngine):
    """
    Animation showing the extraction of date components.
    Visualizes selecting a complex datetime string, spawning a new column,
    and extracting a specific granular component (e.g., Month) into it.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent, fps=60, duration_ms=8000)

        self.c_table_bg = QColor("#1e1e1e")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")

        self.c_highlight_bg = QColor("#2b4a6b")
        self.c_accent_text = QColor("#2ecc71")

        self.columns = [
            {"name": "ID", "is_target": False, "is_new": False},
            {"name": "Timestamp", "is_target": True, "is_new": False},
            {"name": "Month", "is_target": False, "is_new": True}
        ]

        self.rows = [
            ["1", "2023-10-15 08:30", "October"],
            ["2", "2024-01-22 14:15", "January"],
            ["3", "2023-05-05 09:00", "May"]
        ]

        self.base_col_widths = [60.0, 160.0, 110.0]
        self.row_h = 45.0

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        p_intro = self.get_eased_progress(progress, 0.0, 0.1)
        p_highlight = self.get_eased_progress(progress, 0.15, 0.25)
        p_expand = self.get_eased_progress(progress, 0.30, 0.50)
        p_extract = self.get_eased_progress(progress, 0.55, 0.75)
        p_outro = self.get_eased_progress(progress, 0.85, 1.0)

        if p_intro == 0.0:
            return

        total_w = 0.0
        col_widths = []
        for i, col in enumerate(self.columns):
            if col["is_new"]:
                w = self.base_col_widths[i] * p_expand
            else:
                w = self.base_col_widths[i]

            col_widths.append(w)
            total_w += w

        cx = self.width() / 2.0
        cy = self.height() / 2.0

        start_x = cx - total_w / 2.0
        start_y = cy - (len(self.rows) + 1) * self.row_h / 2.0 - 15.0

        self._draw_table(painter, start_x, start_y, col_widths, p_highlight, p_extract, p_outro)
        self._draw_explanation(painter, start_y + (len(self.rows) + 1) * self.row_h + 20.0, p_highlight, p_expand,
                               p_extract)

    def _draw_table(self, painter: QPainter, x: float, y: float, col_widths: list[float], p_highlight: float,
                    p_extract: float, p_outro: float) -> None:
        curr_x = x
        for c_idx, col in enumerate(self.columns):
            w = col_widths[c_idx]

            if w <= 0.1:
                continue

            if col["is_target"]:
                highlight_intensity = p_highlight * (1.0 - p_outro)
                header_bg = self.lerp_color(self.c_header_bg, self.c_highlight_bg, highlight_intensity)
                cell_bg = self.lerp_color(self.c_table_bg, self.c_highlight_bg, highlight_intensity)
            else:
                header_bg = self.c_header_bg
                cell_bg = self.c_table_bg

            self._draw_header_cell(painter, curr_x, y, w, col, header_bg, p_extract, p_outro)
            self._draw_row_cells(painter, curr_x, y, w, c_idx, col, cell_bg, p_extract, p_outro)

            curr_x += w

    def _draw_header_cell(self, painter: QPainter, x: float, y: float, w: float, col: dict, bg_color: QColor,
                          p_extract: float, p_outro: float) -> None:
        rect = QRectF(x, y, w, self.row_h)

        painter.setBrush(bg_color)
        painter.setPen(self.c_border)
        painter.drawRect(rect)

        painter.save()
        painter.setClipRect(rect)
        painter.setFont(self.font_bold)

        text_alpha = 255
        if col["is_new"]:
            text_alpha = int(255 * p_extract)
            c_text = self.lerp_color(self.c_accent_text, self.c_text, p_outro)
        else:
            c_text = QColor(self.c_text)

        c_text.setAlpha(text_alpha)
        painter.setPen(c_text)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, col["name"])

        painter.restore()

    def _draw_row_cells(self, painter: QPainter, x: float, start_y: float, w: float, c_idx: int, col: dict,
                        bg_color: QColor, p_extract: float, p_outro: float) -> None:
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

            if col["is_new"]:
                text_alpha = int(255 * p_extract)
                c_text = self.lerp_color(self.c_accent_text, self.c_text, p_outro)
                c_text.setAlpha(text_alpha)

                slide_x = -20.0 * (1.0 - p_extract)
                painter.translate(slide_x, 0)
            else:
                c_text = QColor(self.c_text)

            painter.setPen(c_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, val)

            painter.restore()

    def _draw_explanation(self, painter: QPainter, y: float, p_highlight: float, p_expand: float,
                          p_extract: float) -> None:
        painter.setFont(self.font_main)
        painter.setPen(self.c_text)

        if p_extract == 1.0:
            text = "Feature isolated! Ready for grouping or analysis."
        elif p_expand == 1.0 and p_extract > 0.0:
            text = "Isolating 'Month' component..."
        elif p_highlight == 1.0 and p_expand > 0.0:
            text = "Allocating space for new feature..."
        elif p_highlight > 0.0:
            text = "Selecting Datetime column..."
        else:
            text = "Raw Dataset"

        painter.drawText(QRectF(0.0, y, float(self.width()), 30.0), Qt.AlignmentFlag.AlignCenter, text)