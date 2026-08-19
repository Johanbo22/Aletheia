from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor

from src.ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    
    def __init__(self):
        super().__init__(duration_ms=8000)
        
        self.c_bg = QColor("#2b2b2b")
        self.c_table_bg = QColor("#1e1e1e")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")
        
        self.c_id_col = QColor("#2b4a6b")  
        self.c_var_1 = QColor("#6b2b2b")   
        self.c_var_2 = QColor("#6b5a2b")  
        
        self.wide_headers = ["Product", "Q1", "Q2"]
        self.wide_rows = [
            ["A", "100", "120"],
            ["B", "200", "250"],
        ]
        
        self.long_headers = ["Product", "Quarter", "Sales"]
        self.long_rows = [
            ["A", "Q1", "100"],
            ["A", "Q2", "120"],
            ["B", "Q1", "200"],
            ["B", "Q2", "250"],
        ]
        
        self.wide_w = 140
        self.long_w = 160
        self.row_h = 28
        
        self.left_x = 20
        self.right_x = 360
        self.start_y = 60

    def draw_animation(self, painter, progress):
        painter.fillRect(self.rect(), self.c_bg)
        
        
        
        highlight_prog = self.get_eased_progress(progress, 0.0, 0.2)
        transform_prog = self.get_eased_progress(progress, 0.2, 0.8)
        
        self._draw_row(painter, self.left_x, self.start_y - self.row_h, 
                       self.wide_headers, [50, 50, 50], 
                       bg_colors=[self.c_header_bg, self.c_var_1, self.c_var_2],
                       is_header=True,
                       highlight_intensity=highlight_prog)
        
        for i, row in enumerate(self.wide_rows):
            y = self.start_y + (i * self.row_h)
            
            opacity = 1.0
            row_start_time = i * 0.3
            if transform_prog > row_start_time:
                opacity = 1.0 - (transform_prog - row_start_time) * 3
                if opacity < 0: opacity = 0
            
            if opacity > 0:
                painter.setOpacity(opacity)
                self._draw_row(painter, self.left_x, y, row, [50, 50, 50],
                               bg_colors=[self.c_table_bg]*3)
                painter.setOpacity(1.0)
            
            if transform_prog > row_start_time and opacity < 1.0:
                move_t = (transform_prog - row_start_time) * 2.5 # Speedge
                if move_t > 1.0: move_t = 1.0
                
                target_y_1 = self.start_y + ((i*2) * self.row_h)
                target_y_2 = self.start_y + ((i*2 + 1) * self.row_h)
                
                curr_x = self.left_x + (self.right_x - self.left_x) * move_t
                curr_y_1 = y + (target_y_1 - y) * move_t
                curr_y_2 = y + (target_y_2 - y) * move_t
                
                painter.setOpacity(move_t) 
                mov_row_1 = [row[0], self.wide_headers[1], row[1]]
                self._draw_row(painter, curr_x, curr_y_1, mov_row_1, [50, 60, 50],
                               bg_colors=[self.c_table_bg, self.c_var_1, self.c_table_bg])

                mov_row_2 = [row[0], self.wide_headers[2], row[2]]
                self._draw_row(painter, curr_x, curr_y_2, mov_row_2, [50, 60, 50],
                               bg_colors=[self.c_table_bg, self.c_var_2, self.c_table_bg])
                
                painter.setOpacity(1.0)

        self._draw_row(painter, self.right_x, self.start_y - self.row_h, 
                       self.long_headers, [50, 60, 50],
                       bg_colors=[self.c_header_bg, self.c_header_bg, self.c_header_bg],
                       is_header=True)
        
        total_h = len(self.long_rows) * self.row_h
        painter.setPen(self.c_border)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(self.right_x, self.start_y, self.long_w, total_h))
        
        for i, row in enumerate(self.long_rows):
            source_i = i // 2
            row_finish_time = source_i * 0.3 + 0.4 
            
            if transform_prog > row_finish_time:
                 y = self.start_y + (i * self.row_h)
                 
                 bg_cols = [self.c_table_bg]*3
                 if row[1] == "Q1": bg_cols[1] = self.c_var_1
                 if row[1] == "Q2": bg_cols[1] = self.c_var_2
                 
                 
                 self._draw_row(painter, self.right_x, y, row, [50, 60, 50],
                                bg_colors=bg_cols)

    def _draw_row(self, painter, x, y, cells, widths, bg_colors=None, is_header=False, highlight_intensity=0.0):
        if is_header:
            painter.setFont(self.font_bold)
        else:
            painter.setFont(self.font_main)
            
        current_x = x
        total_w = sum(widths)
        
        
        for i, text in enumerate(cells):
            w = widths[i]
            rect = QRectF(current_x, y, w, self.row_h)
            
            bg = self.c_table_bg
            if bg_colors and i < len(bg_colors):
                bg = bg_colors[i]
            
            if highlight_intensity > 0 and is_header and i > 0: 
                
                bg = self.lerp_color(bg, QColor("#886622"), highlight_intensity)
            
            painter.setBrush(bg)
            painter.setPen(self.c_border)
            painter.drawRect(rect)
            
            painter.setPen(self.c_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            
            current_x += w