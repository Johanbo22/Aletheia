from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPen

from src.ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """Animation to show duplicate rows being removed"""

    def __init__(self):
        super().__init__(duration_ms=6000)

        self.c_bg = QColor("#2b2b2b")
        self.c_table_bg = QColor("#1e1e1e")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")
        self.c_text_muted = QColor("#888888")

        # Highlighting colors
        self.c_dup_bg = QColor("#662222")
        self.c_dup_text = QColor("#ffcccc")

        # Table data
        self.headers = ["ID", "Category", "Value"]

        self.data_rows = [
            {"cols": ["101", "Sales", "500"],   "dup": False},
            {"cols": ["102", "Marketing", "320"], "dup": True},
            {"cols": ["101", "Sales", "500"],   "dup": False},
            {"cols": ["103", "IT", "850"],      "dup": False},
            {"cols": ["102", "Marketing", "320"], "dup": True},
            {"cols": ["104", "HR", "210"],      "dup": False}
        ]
        
        # Layout
        self.row_height = 32
        self.col_widths = [60, 100, 80]
        self.table_width = sum(self.col_widths)

        # Centering of the table in the widget
        self.start_x = (self.width() - self.table_width) / 2
        self.start_y = 60

    def draw_animation(self, painter, progress):
        # Draw background
        painter.fillRect(self.rect(), self.c_bg)

        # Animation
        highlight_prog = self.get_eased_progress(progress, 0.1, 0.3)
        fade_prog = self.get_eased_progress(progress, 0.35, 0.6)
        collapse_prog = self.get_eased_progress(progress, 0.6, 0.9)

        # Draw table Head
        header_y = self.start_y - self.row_height
        self._draw_row(painter, header_y, self.headers, is_header=True)

        #Draw ros
        for i, row in enumerate(self.data_rows):
            y = self.start_y + (i * self.row_height)

            opacity = 1.0
            if row["dup"]:
                opacity = 1.0 - fade_prog
            
            shift = 0
            if not row["dup"]:
                dups_above = sum(1 for r in self.data_rows[:i] if r["dup"])
                shift = dups_above * self.row_height * collapse_prog
            
            y -= shift

            if opacity > 0.01:
                painter.setOpacity(opacity)

                bg_color = self.c_table_bg
                text_color = self.c_text

                if row["dup"] and highlight_prog > 0:
                    bg_color = self.lerp_color(self.c_table_bg, self.c_dup_bg, highlight_prog)
                    text_color = self.lerp_color(self.c_text, self.c_dup_bg, highlight_prog)
                
                self._draw_row(painter, y, row["cols"], bg_color=bg_color, text_color=text_color)
        
        painter.setOpacity(1.0)

    def _draw_row(self, painter, y, col_texts, is_header=False, bg_color=None, text_color=None):
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

            painter.setPen(text_color)
            text_rect = cell_rect.adjusted(5, 0, -5, 0)
            align = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            if i == 0:
                align = Qt.AlignmentFlag.AlignCenter
            painter.drawText(text_rect, align, text)

            painter.setPen(self.c_border)
            painter.drawLine(int(current_x + w), int(y), int(current_x + w), int(y + self.row_height))

            current_x += w
        
        # Draw bottom line
        painter.drawLine(int(x), int(y + self.row_height), int(x + self.table_width), int(y + self.row_height))
        
        # Draw Left Line
        painter.drawLine(int(x), int(y), int(x), int(y + self.row_height))

        if is_header:
            painter.drawLine(int(x), int(y), int(x + self.table_width), int(y))