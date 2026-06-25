from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainterPath, QPen

from ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """
    Animation showing data grouping and aggregation.
    Visualizes rows with the same category merging into a single summary row.
    """
    
    def __init__(self):
        super().__init__(duration_ms=8000)
        
        self.c_bg = QColor("#2b2b2b")
        self.c_table_bg = QColor("#1e1e1e")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")
        
        self.c_cat_a = QColor("#2b4a6b") 
        self.c_cat_b = QColor("#6b2b2b") 
        
        self.c_sigma = QColor("#ffaa00") 
        
        self.headers = ["Region", "Sales"]
        
        self.raw_rows = [
            {"vals": ["East", "100"], "cat": "A"},
            {"vals": ["West", "50"],  "cat": "B"},
            {"vals": ["East", "200"], "cat": "A"},
            {"vals": ["West", "20"],  "cat": "B"},
            {"vals": ["East", "50"],  "cat": "A"},
        ]
        
        self.agg_rows = [
            {"vals": ["East", "350"], "cat": "A"}, 
            {"vals": ["West", "70"],  "cat": "B"},
        ]
        
        self.col_widths = [80, 60]
        self.table_w = sum(self.col_widths)
        self.row_h = 28
        
        self.left_x = 20
        self.right_x = 360
        self.start_y = 70
        
        self.center_x = (self.left_x + self.table_w + self.right_x) / 2
        self.center_y = self.start_y + (len(self.raw_rows) * self.row_h) / 2

    def draw_animation(self, painter, progress):
        
        painter.fillRect(self.rect(), self.c_bg)
                
        identify_prog = self.get_eased_progress(progress, 0.0, 0.2)
        merge_prog = self.get_eased_progress(progress, 0.2, 0.7)
        result_prog = self.get_eased_progress(progress, 0.7, 0.9)
        
        self._draw_sigma(painter, self.center_x, self.center_y, 
                        active_intensity=merge_prog)

        self._draw_header(painter, self.left_x, self.start_y - self.row_h)
        
        for i, row in enumerate(self.raw_rows):
            y = self.start_y + (i * self.row_h)
            
            base_bg = self.c_table_bg
            target_bg = self.c_cat_a if row["cat"] == "A" else self.c_cat_b
            
            bg = self.lerp_color(base_bg, target_bg, identify_prog)
            
            opacity = 1.0 - (merge_prog * 1.5)
            if opacity > 0:
                painter.setOpacity(opacity)
                self._draw_row(painter, self.left_x, y, row["vals"], bg, self.c_text)
                painter.setOpacity(1.0)

            if 0 < merge_prog < 1.0:
                # Target Y depends on which aggregate row it belongs to
                target_idx = 0 if row["cat"] == "A" else 1
                target_y = self.start_y + (target_idx * self.row_h)
                
                # Interpolate Position
                curr_x = self.left_x + (self.right_x - self.left_x) * merge_prog
                curr_y = y + (target_y - y) * merge_prog
                
                scale = 1.0 - (0.2 * merge_prog)
                
                painter.save()
                painter.translate(curr_x, curr_y)
                painter.scale(scale, scale)
                self._draw_row(painter, 0, 0, row["vals"], bg, self.c_text)
                painter.restore()

        self._draw_header(painter, self.right_x, self.start_y - self.row_h)
        
        total_h = len(self.agg_rows) * self.row_h
        painter.setPen(self.c_border)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(self.right_x, self.start_y, self.table_w, total_h))
        
        for i, row in enumerate(self.agg_rows):
            y = self.start_y + (i * self.row_h)
            
            
            opacity = self.get_eased_progress(merge_prog, 0.8, 1.0)
            if result_prog > 0: opacity = 1.0
            
            if opacity > 0:
                painter.setOpacity(opacity)
                
                bg = self.c_cat_a if row["cat"] == "A" else self.c_cat_b
                
                self._draw_row(painter, self.right_x, y, row["vals"], bg, self.c_text)
                painter.setOpacity(1.0)

        

    def _draw_sigma(self, painter, cx, cy, active_intensity=0.0):
        """Draws a mathematical Summation (Sigma) symbol."""
        size = 25
        
        color = self.c_border
        if active_intensity > 0:
            color = self.lerp_color(self.c_border, self.c_sigma, active_intensity)
            
        painter.setPen(QPen(color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Sigma Path
        path = QPainterPath()
        # Top right
        path.moveTo(cx + size/2, cy - size/2)
        # Top left
        path.lineTo(cx - size/2, cy - size/2)
        # Center
        path.lineTo(cx, cy)
        # Bottom left
        path.lineTo(cx - size/2, cy + size/2)
        # Bottom right
        path.lineTo(cx + size/2, cy + size/2)
        
        painter.drawPath(path)
        
        painter.setPen(self.c_text)
        painter.setFont(self.font_small)
        painter.drawText(QRectF(cx - 30, cy + size/2 + 5, 60, 20), 
                        Qt.AlignmentFlag.AlignCenter, "Sum")

    def _draw_header(self, painter, x, y):
        painter.setFont(self.font_bold)
        curr_x = x
        for i, text in enumerate(self.headers):
            w = self.col_widths[i]
            rect = QRectF(curr_x, y, w, self.row_h)
            
            painter.setBrush(self.c_header_bg)
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