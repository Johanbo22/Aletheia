from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFontMetrics

from src.ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    def __init__(self):
        super().__init__(duration_ms=5000)
        
        self.c_bg = QColor("#2b2b2b")
        self.c_table_bg = QColor("#1e1e1e")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")
        
        self.c_action_bg = QColor("#2b4a6b")  
        self.c_success_bg = QColor("#2d5a2d") 
        self.c_success_text = QColor("#ccffcc")
        self.c_type_tag = QColor("#ffaa00") 
        
        self.headers = ["ID", "Sales", "Region"]
        self.target_col_idx = 1

        self.data_rows = [
            ["001", "500", "North"],
            ["002", "1200", "West"],
            ["003", "850", "East"],
            ["004", "430", "North"],
        ]
        
        self.row_height = 32
        self.col_widths = [60, 100, 80]
        self.table_width = sum(self.col_widths)
        
        self.start_x = (self.width() - self.table_width) / 2
        self.start_y = 70

    def draw_animation(self, painter, progress):
        painter.fillRect(self.rect(), self.c_bg)

        
        highlight_prog = self.get_eased_progress(progress, 0.1, 0.3)
        trans_prog = self.get_eased_progress(progress, 0.3, 0.7)
        success_prog = self.get_eased_progress(progress, 0.7, 0.9)
        
        header_text_suffix = "(Obj)"
        if success_prog > 0.5:
            header_text_suffix = "(Int64)"
            
        col_bg = self.c_table_bg
        col_fg = self.c_text
        
        if highlight_prog > 0:
            col_bg = self.lerp_color(self.c_table_bg, self.c_action_bg, highlight_prog)
        
        if success_prog > 0:
            flash = 1.0 - abs(success_prog - 0.5) * 2
            col_bg = self.lerp_color(self.c_action_bg, self.c_success_bg, flash)
            col_fg = self.lerp_color(self.c_text, self.c_success_text, flash)

        current_x = self.start_x
        
        for c_idx, width in enumerate(self.col_widths):
            
            is_target = (c_idx == self.target_col_idx)
            
            rect_h = QRectF(current_x, self.start_y - self.row_height, width, self.row_height)
            painter.setBrush(self.c_header_bg)
            painter.setPen(self.c_border)
            painter.drawRect(rect_h)
            
            painter.setPen(self.c_text)
            painter.setFont(self.font_bold)
            
            h_text = self.headers[c_idx]
            if is_target:
                h_text += f" {header_text_suffix}"
                
            painter.drawText(rect_h, Qt.AlignmentFlag.AlignCenter, h_text)
            
            painter.setFont(self.font_main)
            for r_idx, row_data in enumerate(self.data_rows):
                y = self.start_y + (r_idx * self.row_height)
                rect_c = QRectF(current_x, y, width, self.row_height)
                
                bg = col_bg if is_target else self.c_table_bg
                painter.setBrush(bg)
                painter.setPen(self.c_border)
                painter.drawRect(rect_c)
                
                text = row_data[c_idx]
                text_color = col_fg if is_target else self.c_text
                painter.setPen(text_color)
                
                if is_target:
                    fm = QFontMetrics(painter.font())
                    txt_w = fm.horizontalAdvance(text)
                    
                    left_x = rect_c.left() + 10
                    right_x = rect_c.right() - txt_w - 10
                    
                    text_x = left_x + (right_x - left_x) * trans_prog
                    
                    text_y = rect_c.center().y() + (fm.descent() + fm.ascent()) / 2 - fm.descent()
                    
                    painter.drawText(QRectF(text_x, rect_c.top(), txt_w + 10, self.row_height), 
                                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, 
                                    text)
                    
                else:
                    text_rect = rect_c.adjusted(10, 0, -10, 0)
                    painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
            
            current_x += width

        