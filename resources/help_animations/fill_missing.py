from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPen

from src.ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    def __init__(self):
        super().__init__(duration_ms=5000)

        self.c_bg = QColor("#2b2b2b")
        self.c_table_bg = QColor("#1e1e1e")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")
        self.c_text_muted = QColor("#888888")

        self.c_target_bg = QColor("#8a6d3b")
        self.c_filled_bg = QColor("#2d5a2d")
        self.c_filled_text = QColor("#ccffcc")

        self.headers = ["Name", "Age", "Score"]

        self.data_rows = [
            {"cols": ["Alice", "25", "88"],   "missing": False, "nan_idx": -1},
            {"cols": ["Bob", "NaN", "92"],    "missing": True,  "nan_idx": 1, "fill_val": "0"},
            {"cols": ["Charlie", "30", "NaN"], "missing": True,  "nan_idx": 2, "fill_val": "0"},
            {"cols": ["David", "28", "79"],   "missing": False, "nan_idx": -1},
        ]

        self.row_height = 35
        self.col_widths = [100, 80, 80]
        self.table_width = sum(self.col_widths)

        self.start_x = (self.width() - self.table_width) / 2
        self.start_y = 60

    def draw_animation(self, painter, progress):
        painter.fillRect(self.rect(), self.c_bg)

        detect_prog = self.get_eased_progress(progress, 0.1, 0.3)
        transform_prog = self.get_eased_progress(progress, 0.3, 0.6)
        success_prog = self.get_eased_progress(progress, 0.6, 0.9)

        self._draw_row(painter, self.start_y - self.row_height, self.headers, is_header=True)

        for i, row in enumerate(self.data_rows):
            y = self.start_y + (i * self.row_height)
            bg_color = self.c_table_bg
            text_color = self.c_text
            nan_idx = row.get("nan_idx", -1)

            display_cols = list(row["cols"])

            if row["missing"]:
                if detect_prog > 0 and transform_prog == 0:
                    bg_color = self.lerp_color(self.c_table_bg, self.c_target_bg, detect_prog)
                
                if transform_prog > 0.5:
                    display_cols[nan_idx] = row["fill_val"]
                
                if success_prog > 0:
                    flash = 1.0 - abs(success_prog - 0.5) * 2
                    bg_color = self.lerp_color(self.c_table_bg, self.c_filled_bg, flash)
                    text_color = self.lerp_color(self.c_text, self.c_filled_text, flash)
        
            self._draw_row(painter, y, display_cols, 
                            bg_color=bg_color, 
                            text_color=text_color,
                            highlight_idx=nan_idx if row["missing"] else -1,
                            highlight_intensity=detect_prog if transform_prog == 0 else 0)

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
                painter.setBrush(Qt.BrushStyle.NoBrush)
                highlight_c = QColor("#ffaa00")
                highlight_c.setAlphaF(highlight_intensity)
                
                high_pen = QPen(highlight_c, 2)
                painter.setPen(high_pen)
                
                painter.drawRect(cell_rect.adjusted(1,1,-1,-1))
            
            painter.setPen(text_color)
            text_rect = cell_rect.adjusted(5, 0, -5, 0)
            align = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            if i == 1: align = Qt.AlignmentFlag.AlignCenter
            if i == 2: align = Qt.AlignmentFlag.AlignCenter

            painter.drawText(text_rect, align, text)
            
            painter.setPen(self.c_border)
            painter.drawLine(int(current_x + w), int(y), int(current_x + w), int(y + self.row_height))
            
            current_x += w
        
        painter.drawLine(int(x), int(y + self.row_height), int(x + self.table_width), int(y + self.row_height))
        painter.drawLine(int(x), int(y), int(x), int(y + self.row_height))
        if is_header:
            painter.drawLine(int(x), int(y), int(x + self.table_width), int(y))