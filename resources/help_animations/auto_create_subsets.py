from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPen

from src.ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """
    Animation showing the "Auto Create Subsets" feature.
    Visualizes scanning a column (e.g., Department) and splitting the 
    single table into multiple named subsets based on unique values.
    """
    
    def __init__(self):
        super().__init__(duration_ms=8000)
        
        self.c_bg = QColor("#2b2b2b")
        self.c_table_bg = QColor("#1e1e1e")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")
        
        self.c_cat_1 = QColor("#2b4a6b") 
        self.c_cat_2 = QColor("#6b2b2b") 
        self.c_cat_3 = QColor("#2b6b4a") 
        
        self.headers = ["ID", "Dept"]
        self.split_col_idx = 1 
        
        # Raw Data
        self.rows = [
            {"vals": ["001", "Sales"], "cat": "Sales", "c_code": self.c_cat_1},
            {"vals": ["002", "HR"],    "cat": "HR",    "c_code": self.c_cat_2},
            {"vals": ["003", "Sales"], "cat": "Sales", "c_code": self.c_cat_1},
            {"vals": ["004", "IT"],    "cat": "IT",    "c_code": self.c_cat_3},
            {"vals": ["005", "HR"],    "cat": "HR",    "c_code": self.c_cat_2},
        ]
        
        self.groups = ["Sales", "HR", "IT"]
        
        self.col_widths = [50, 80]
        self.table_w = sum(self.col_widths)
        self.row_h = 28
        
        self.left_x = 20
        self.right_x = 320
        self.start_y = 60

    def draw_animation(self, painter, progress):
        painter.fillRect(self.rect(), self.c_bg)
        
        
        
        scan_prog = self.get_eased_progress(progress, 0.0, 0.2)
        dist_prog = self.get_eased_progress(progress, 0.2, 0.8)
        final_prog = self.get_eased_progress(progress, 0.8, 1.0)
        
        self._draw_header(painter, self.left_x, self.start_y - self.row_h,
                          highlight_idx=1 if scan_prog > 0 else -1,
                          highlight_alpha=scan_prog)
        
        # Draw Placeholder Box for source table (so it doesn't disappear completely)
        source_h = len(self.rows) * self.row_h
        painter.setPen(self.c_border)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(self.left_x, self.start_y, self.table_w, source_h))
        
        # Draw Rows
        for i, row in enumerate(self.rows):
            src_y = self.start_y + (i * self.row_h)
            
            group_idx = self.groups.index(row["cat"])
            
            group_y_base = self.start_y + (group_idx * 90)
            
            sibling_idx = sum(1 for r in self.rows[:i] if r["cat"] == row["cat"])
            target_y = group_y_base + 30 + (sibling_idx * self.row_h)
            
            curr_x = self.left_x
            curr_y = src_y
            
            if dist_prog > 0:
                # Stagger flight based on index
                flight_start = i * 0.1
                flight_dur = 0.5
                
                # Local progress for this specific row
                row_t = (dist_prog - flight_start) / flight_dur
                if row_t < 0: row_t = 0
                if row_t > 1: row_t = 1
                
                # Interpolate
                curr_x = self.left_x + (self.right_x - self.left_x) * row_t
                curr_y = src_y + (target_y - src_y) * row_t
            
            bg = self.c_table_bg
            if scan_prog > 0 and dist_prog == 0:
                bg = self.lerp_color(self.c_table_bg, row["c_code"], scan_prog * 0.3)
            
            if curr_x > self.left_x + 50:
                 bg = row["c_code"]
            
            self._draw_row(painter, curr_x, curr_y, row["vals"], bg, self.c_text)

        for g_idx, group_name in enumerate(self.groups):
            y_base = self.start_y + (g_idx * 90)
            rect = QRectF(self.right_x - 10, y_base, self.table_w + 20, 80)
            
            opacity = 0.2 + (dist_prog * 0.8)
            painter.setOpacity(opacity)
            
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(self.c_border, 1, Qt.PenStyle.DashLine))
            painter.drawRoundedRect(rect, 8, 8)
            
            label_rect = QRectF(self.right_x, y_base, self.table_w, 25)
            painter.setPen(self.c_text)
            painter.setFont(self.font_bold)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                             f"Subset: {group_name}")
            
            painter.setOpacity(1.0)
            

    def _draw_header(self, painter, x, y, highlight_idx=-1, highlight_alpha=0.0):
        painter.setFont(self.font_bold)
        curr_x = x
        for i, text in enumerate(self.headers):
            w = self.col_widths[i]
            rect = QRectF(curr_x, y, w, self.row_h)
            
            bg = self.c_header_bg
            if i == highlight_idx and highlight_alpha > 0:
                bg = self.lerp_color(self.c_header_bg, QColor("#aa8800"), highlight_alpha)
            
            painter.setBrush(bg)
            painter.setPen(self.c_border)
            painter.drawRect(rect)
            
            painter.setPen(self.c_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            curr_x += w

    def _draw_row(self, painter, x, y, vals, bg, text_color):
        painter.setFont(self.font_main)
        curr_x = x
        
        full_rect = QRectF(x, y, self.table_w, self.row_h)
        painter.setBrush(bg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(full_rect)
        
        painter.setPen(self.c_border)
        for i, text in enumerate(vals):
            w = self.col_widths[i]
            rect = QRectF(curr_x, y, w, self.row_h)
            
            painter.drawRect(rect) 
            
            painter.setPen(text_color)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            painter.setPen(self.c_border)
            
            curr_x += w