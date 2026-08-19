from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor

from src.ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """
    Animation showing a specific column being identified and removed from the dataset.
    """
    
    def __init__(self):
        super().__init__(duration_ms=5000)
        
        self.c_bg = QColor("#2b2b2b")
        self.c_table_bg = QColor("#1e1e1e")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")
        
        self.c_drop_bg = QColor("#662222")    
        self.c_drop_text = QColor("#ffcccc")
        
        self.headers = ["ID", "Temp (C)", "Notes"]
        self.drop_col_idx = 2 
        
        self.data_rows = [
            ["001", "24.5", "Valid"],
            ["002", "25.1", "Check"],
            ["003", "23.8", "OK"],
            ["004", "24.2", "Verify"],
            ["005", "24.9", "OK"],
        ]
        
        self.row_height = 32
        self.base_col_widths = [60, 80, 100]
        self.total_width = sum(self.base_col_widths)
        
        self.start_y = 60

    def draw_animation(self, painter, progress):
        
        painter.fillRect(self.rect(), self.c_bg)
        
        highlight_prog = self.get_eased_progress(progress, 0.1, 0.3)
        collapse_prog = self.get_eased_progress(progress, 0.3, 0.7)
        
        current_widths = list(self.base_col_widths)
        target_width = current_widths[self.drop_col_idx]
        
        current_widths[self.drop_col_idx] = target_width * (1.0 - collapse_prog)
        
        current_total_width = sum(current_widths)
        start_x = (self.width() - current_total_width) / 2
        
        self._draw_row(painter, start_x, self.start_y - self.row_height, 
                    self.headers, current_widths, 
                    is_header=True, 
                    highlight_intensity=highlight_prog,
                    collapse_alpha=1.0-collapse_prog)
        
        for i, row in enumerate(self.data_rows):
            y = self.start_y + (i * self.row_height)
            self._draw_row(painter, start_x, y, 
                        row, current_widths, 
                        is_header=False, 
                        highlight_intensity=highlight_prog,
                        collapse_alpha=1.0-collapse_prog)


    def _draw_row(self, painter, x, y, col_texts, widths, is_header=False, highlight_intensity=0.0, collapse_alpha=1.0):
        current_x = x
        
        if is_header:
            painter.setFont(self.font_bold)
        else:
            painter.setFont(self.font_main)
            
        for i, text in enumerate(col_texts):
            w = widths[i]
            
            if w < 1:
                continue
            
            cell_rect = QRectF(current_x, y, w, self.row_height)
            
            bg_color = self.c_header_bg if is_header else self.c_table_bg
            text_color = self.c_text
            
            if i == self.drop_col_idx:
                
                if highlight_intensity > 0:
                    bg_color = self.lerp_color(bg_color, self.c_drop_bg, highlight_intensity)
                    text_color = self.lerp_color(text_color, self.c_drop_text, highlight_intensity)
                
                text_color.setAlphaF(collapse_alpha)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bg_color)
            painter.drawRect(cell_rect)
            
            painter.setPen(text_color)
            painter.save()
            painter.setClipRect(cell_rect) 
            
            text_rect = cell_rect.adjusted(5, 0, -5, 0)
            align = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            if i == 0: align = Qt.AlignmentFlag.AlignCenter
            
            painter.drawText(text_rect, align, text)
            painter.restore()
            
            painter.setPen(self.c_border)
            painter.drawLine(int(current_x + w), int(y), int(current_x + w), int(y + self.row_height))
            painter.drawLine(int(current_x), int(y + self.row_height), int(current_x + w), int(y + self.row_height))
            if is_header:
                painter.drawLine(int(current_x), int(y), int(current_x + w), int(y))
            if i == 0:
                painter.drawLine(int(current_x), int(y), int(current_x), int(y + self.row_height))
            
            current_x += w