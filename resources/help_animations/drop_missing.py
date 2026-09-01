from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPen

from src.ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    def __init__(self):
        super().__init__(duration_ms=6000)

        self.c_bg = QColor("#2b2b2b")
        self.c_table_bg = QColor("#1e1e1e")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")
        self.c_text_muted = QColor("#888888")

        self.c_missing_bg = QColor("#662222")
        self.c_missing_cell = QColor("#a63333")
        self.c_missing_text = QColor("#ffcccc")

        self.headers = ["ID", "Sensor", "Value"]

        self.data_rows = [
            {"cols": ["001", "Temp_A", "24.5"], "missing": False},
            {"cols": ["002", "Temp_B", "NaN"],  "missing": True, "nan_index": 2},
            {"cols": ["003", "Press_A", "1013"], "missing": False},
            {"cols": ["004", "Press_B", "NaN"],  "missing": True, "nan_index": 2},
            {"cols": ["005", "Humid_A", "45%"], "missing": False},
            {"cols": ["006", "NaN",     "52%"], "missing": True, "nan_index": 1},
        ]

        self.row_height = 32
        self.col_widths = [50, 90, 80]
        self.table_width = sum(self.col_widths)

        self.start_x = (self.width() - self.table_width) / 2
        self.start_y = 60

    def draw_animation(self, painter, progress):
        painter.fillRect(self.rect(), self.c_bg)

        highlight_prog = self.get_eased_progress(progress, 0.1, 0.3)
        fade_prog = self.get_eased_progress(progress, 0.35, 0.6)
        collapse_prog = self.get_eased_progress(progress, 0.6, 0.9)

        self._draw_row(painter, self.start_y - self.row_height, self.headers, is_header=True)

        for i, row in enumerate(self.data_rows):
            y = self.start_y + (i * self.row_height)
            shift = 0
            if not row["missing"]:
                missing_above = sum(1 for r in self.data_rows[:i] if r["missing"])
                shift = missing_above * self.row_height * collapse_prog
            
            y -= shift

            opacity = 1.0
            if row["missing"]:
                opacity = 1.0 - fade_prog
            
            if opacity > 0.01:
                painter.setOpacity(opacity)

                bg_color = self.c_table_bg
                text_color = self.c_text

                if row["missing"] and highlight_prog > 0:
                    bg_color = self.lerp_color(self.c_table_bg, self.c_missing_bg, highlight_prog)
                    text_color = self.lerp_color(self.c_text, self.c_missing_text, highlight_prog)
                
                nan_idx = row.get("nan_index", -1) if row["missing"] else -1

                self._draw_row(painter, y, row["cols"], bg_color=bg_color, text_color=text_color, highlight_idx=nan_idx, highlight_intensity=highlight_prog)
        
        painter.setOpacity(1.0)

    def _draw_row(self, painter, y, col_texts, is_header=False, bg_color=None, text_color=None, highlight_idx=-1, highlight_intensity=0.0):
        x = self.start_x

        if is_header:
            bg_color = self.c_header_bg
            text_color = self.c_text
            painter.setFont(self.font_bold)
        else:
            painter.setFont(self.font_main)
        
        row_rect = QRectF(x, y, self.table_width, self.row_height)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRect(row_rect)

        current_x = x
        painter.setPen(QPen(self.c_border, 1))

        for i, text in enumerate(col_texts):
            w = self.col_widths[i]
            cell_rect = QRectF(current_x, y, w, self.row_height)

            if i == highlight_idx and highlight_intensity > 0:
                hlt_color = self.lerp_color(bg_color, self.c_missing_cell, highlight_intensity)
                painter.setBrush(hlt_color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(cell_rect)

                painter.setPen(self.c_border)
            
            painter.setPen(text_color)
            text_rect = cell_rect.adjusted(5, 0, -5, 0)
            align = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            if i == 0: align = Qt.AlignmentFlag.AlignCenter

            painter.drawText(text_rect, align, text)

            painter.setPen(self.c_border)
            painter.drawLine(int(current_x + w), int(y), int(current_x + w), int(y + self.row_height))
            
            current_x += w
        
        painter.drawLine(int(x), int(y + self.row_height), int(x + self.table_width), int(y + self.row_height))
        painter.drawLine(int(x), int(y), int(x), int(y + self.row_height))
        if is_header:
            painter.drawLine(int(x), int(y), int(x + self.table_width), int(y))
