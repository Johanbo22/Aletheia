from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPen, QFontMetrics

from src.ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    
    def __init__(self):
        super().__init__(duration_ms=5000)
        
        self.c_bg = QColor("#2b2b2b")
        self.c_table_bg = QColor("#1e1e1e")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")
        
        self.c_edit_bg = QColor("#2b4a6b") 
        self.c_cursor = QColor("#ffffff")
        self.c_success_bg = QColor("#2d5a2d") 
        self.c_success_text = QColor("#ccffcc")
        
        self.headers = ["ID", "Var_X", "Status"] 
        self.target_idx = 1
        self.target_final_name = "Temperature"
        
        self.data_rows = [
            ["001", "24.5", "OK"],
            ["002", "25.1", "OK"],
            ["003", "23.8", "Low"],
            ["004", "24.2", "OK"],
        ]
        
        self.row_height = 32
        self.col_widths = [60, 120, 80] 
        self.table_width = sum(self.col_widths)
        
        self.start_x = (self.width() - self.table_width) / 2
        self.start_y = 70

    def draw_animation(self, painter, progress):
        
        painter.fillRect(self.rect(), self.c_bg)
        
        focus_prog = self.get_eased_progress(progress, 0.1, 0.2)
        typing_prog = self.get_eased_progress(progress, 0.2, 0.7)
        success_prog = self.get_eased_progress(progress, 0.7, 0.9)
        
        header_text = self.headers[self.target_idx]
        header_bg = self.c_header_bg
        header_fg = self.c_text
        show_cursor = False
        
        if focus_prog > 0:
            header_bg = self.lerp_color(self.c_header_bg, self.c_edit_bg, focus_prog)
        
        if typing_prog > 0:
            header_bg = self.c_edit_bg
            
            total_chars = len(self.target_final_name)
            chars_to_show = int(total_chars * typing_prog)
            
            header_text = self.target_final_name[:chars_to_show]
            
            if typing_prog < 0.95:
                show_cursor = (int(typing_prog * 20) % 2) == 0
            
        if success_prog > 0:
            header_text = self.target_final_name
            
            flash = 1.0 - abs(success_prog - 0.5) * 2
            header_bg = self.lerp_color(self.c_edit_bg, self.c_success_bg, flash)
            header_fg = self.lerp_color(self.c_text, self.c_success_text, flash)
            show_cursor = False

        current_x = self.start_x
        painter.setFont(self.font_bold)
        
        for i, original_text in enumerate(self.headers):
            w = self.col_widths[i]
            rect = QRectF(current_x, self.start_y - self.row_height, w, self.row_height)
            
            bg = header_bg if i == self.target_idx else self.c_header_bg
            fg = header_fg if i == self.target_idx else self.c_text
            text = header_text if i == self.target_idx else original_text
            
            painter.setBrush(bg)
            painter.setPen(self.c_border)
            painter.drawRect(rect)
            
            painter.setPen(fg)
            text_rect = rect.adjusted(5, 0, -5, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
            
            if i == self.target_idx and show_cursor:
                fm = QFontMetrics(painter.font())
                txt_w = fm.horizontalAdvance(text)
                cursor_x = text_rect.left() + txt_w + 2
                cursor_h = fm.height() - 4
                cy = text_rect.center().y() - (cursor_h / 2)
                
                painter.setPen(QPen(self.c_cursor, 1.5))
                painter.drawLine(int(cursor_x), int(cy), int(cursor_x), int(cy + cursor_h))
            
            current_x += w

        painter.setFont(self.font_main)
        for r_idx, row in enumerate(self.data_rows):
            y = self.start_y + (r_idx * self.row_height)
            current_x = self.start_x
            
            for c_idx, text in enumerate(row):
                w = self.col_widths[c_idx]
                rect = QRectF(current_x, y, w, self.row_height)
                
                painter.setBrush(self.c_table_bg)
                painter.setPen(self.c_border)
                painter.drawRect(rect)
                
                painter.setPen(self.c_text)
                text_rect = rect.adjusted(5, 0, -5, 0)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
                
                current_x += w