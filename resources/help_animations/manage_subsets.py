from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor

from src.ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """
    Animation showing a Subset operation.
    Visualizes selecting a rectangular region of data (specific rows/cols)
    and extracting them into a new table.
    """
    
    def __init__(self):
        super().__init__(duration_ms=6000)
        
        self.c_bg = QColor("#2b2b2b")
        self.c_table_bg = QColor("#1e1e1e")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")
        self.c_dim_text = QColor("#555555")
        
        self.c_select_bg = QColor("#2b4a6b")  
        self.c_select_border = QColor("#4a90e2")
        
        self.headers = ["ID", "Name", "Score", "City"]
        self.data_rows = [
            ["001", "Alice", "85", "NY"],
            ["002", "Bob",   "92", "LA"],  
            ["003", "Carol", "88", "CHI"], 
            ["004", "Dave",  "75", "MIA"], 
            ["005", "Eve",   "95", "HOU"],
        ]
        
        self.target_rows = {1, 2, 3}
        self.target_cols = {1, 2}
        
        self.col_widths = [40, 60, 50, 50]
        self.row_h = 28
        self.table_w = sum(self.col_widths)
        
        self.left_x = 20
        self.right_x = 300
        self.start_y = 60

    def draw_animation(self, painter, progress):
        painter.fillRect(self.rect(), self.c_bg)
        
        select_prog = self.get_eased_progress(progress, 0.0, 0.3)
        extract_prog = self.get_eased_progress(progress, 0.3, 0.7)
        
        curr_x = self.left_x
        for c, text in enumerate(self.headers):
            w = self.col_widths[c]
            bg = self.c_header_bg
            if c in self.target_cols and select_prog > 0:
                bg = self.lerp_color(self.c_header_bg, self.c_select_bg, select_prog)
            
            txt_col = self.c_text
            if extract_prog > 0.5 and c not in self.target_cols:
                txt_col = self.c_dim_text
                
            self._draw_cell(painter, curr_x, self.start_y - self.row_h, w, self.row_h, 
                          text, bg, txt_col, is_bold=True)
            curr_x += w
            
        for r, row in enumerate(self.data_rows):
            y = self.start_y + (r * self.row_h)
            curr_x = self.left_x
            
            for c, text in enumerate(row):
                w = self.col_widths[c]
                
                is_selected = (r in self.target_rows) and (c in self.target_cols)
                
                bg = self.c_table_bg
                fg = self.c_text
                border = self.c_border
                
                if is_selected and select_prog > 0:
                    bg = self.lerp_color(self.c_table_bg, self.c_select_bg, select_prog)
                    if select_prog > 0.8:
                        border = self.lerp_color(self.c_border, self.c_select_border, select_prog)

                if extract_prog > 0.1 and not is_selected:
                    fg = self.lerp_color(self.c_text, self.c_dim_text, extract_prog)
                    border = self.lerp_color(self.c_border, self.c_bg, extract_prog) 
                
                self._draw_cell(painter, curr_x, y, w, self.row_h, text, bg, fg, border_color=border)
                
                if is_selected and extract_prog > 0:
                    new_c_idx = list(sorted(self.target_cols)).index(c)
                    new_r_idx = list(sorted(self.target_rows)).index(r)
                    
                    target_x = self.right_x + (sum([self.col_widths[i] for i in sorted(self.target_cols)[:new_c_idx]]))
                    target_y = self.start_y + (new_r_idx * self.row_h) 
                    
                    mov_x = curr_x + (target_x - curr_x) * extract_prog
                    mov_y = y + (target_y - y) * extract_prog
                    
                    painter.setOpacity(extract_prog) 
                    self._draw_cell(painter, mov_x, mov_y, w, self.row_h, text, 
                                  self.c_select_bg, self.c_text, 
                                  border_color=self.c_select_border)
                    painter.setOpacity(1.0)
                
                curr_x += w

        if extract_prog > 0.1:
            painter.setOpacity(extract_prog)
            
            curr_x = self.right_x
            for c in sorted(self.target_cols):
                w = self.col_widths[c]
                self._draw_cell(painter, curr_x, self.start_y - self.row_h, w, self.row_h, 
                              self.headers[c], self.c_header_bg, self.c_text, is_bold=True)
                curr_x += w
            
            # Placeholder Box for body
            subset_w = sum([self.col_widths[i] for i in self.target_cols])
            subset_h = len(self.target_rows) * self.row_h
            
            painter.setPen(self.c_border)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(self.right_x, self.start_y, subset_w, subset_h))
            
            painter.setOpacity(1.0)

    def _draw_cell(self, painter, x, y, w, h, text, bg, fg, border_color=None, is_bold=False):
        if border_color is None:
            border_color = self.c_border
            
        rect = QRectF(x, y, w, h)
        
        painter.setBrush(bg)
        painter.setPen(border_color)
        painter.drawRect(rect)
        
        if is_bold:
            painter.setFont(self.font_bold)
        else:
            painter.setFont(self.font_main)
            
        painter.setPen(fg)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)