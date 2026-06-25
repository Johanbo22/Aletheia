from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainterPath, QPen

from ui.animations import OverlayAnimationEngine

class DataTypeChangeAnimation(OverlayAnimationEngine):
    def __init__(self, parent=None, message="Changing Data Type", old_type="int", new_type="bool"):
        super().__init__(parent)
        self.message = str(message)
        self.old_type = old_type
        self.new_type = new_type

    def draw_content(self, painter):
        painter.scale(1.2, 1.2)
        
        color_old = QColor(70, 110, 160)   
        color_new = QColor(60, 160, 110)   
        text_color = QColor(255, 255, 255)
        border_pen = QPen(QColor(255, 255, 255, 150), 2)
        
        painter.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255))

        fm = painter.fontMetrics()
        title_w = fm.horizontalAdvance(self.message)
        title_h = fm.capHeight()
        
        title_x = -title_w / 2
        title_y = -55 + (title_h / 2)
        
        painter.drawText(int(title_x), int(title_y), self.message)
        
        painter.translate(0, 10)

        box_w = 80
        box_h = 36
        box_rect_base = QRectF(-box_w/2, -box_h/2, box_w, box_h)
        
        
        flip_start = 0.2
        flip_mid = 0.6
        
        current_text = ""
        current_bg = QColor(0, 0, 0)
        scale_y = 1.0 
        
        if self.progress < flip_start:
            current_text = self.old_type
            current_bg = color_old
            scale_y = 1.0
            
        elif self.progress < flip_mid:
            t = (self.progress - flip_start) / (flip_mid - flip_start)
            current_text = self.old_type
            current_bg = color_old
            scale_y = 1.0 - t 
            
        else:
            t = (self.progress - flip_mid) / (1.0 - flip_mid)
            current_text = self.new_type
            current_bg = color_new
            scale_y = t 

        painter.save()
        darkness = 1.0 - abs(scale_y)
        final_bg = current_bg.darker(int(100 + darkness * 150))
        
        safe_scale_y = max(0.01, scale_y)
        painter.scale(1.0, safe_scale_y)

        painter.setPen(border_pen)
        painter.setBrush(final_bg)
        painter.drawRoundedRect(box_rect_base, 4, 4)
        
        if safe_scale_y > 0.1:
            compensating_font_size = 14 * (1.0 / safe_scale_y)
            capped_size = min(compensating_font_size, 40)
            
            painter.setPen(text_color)
            painter.setFont(QFont("Consolas", int(capped_size), QFont.Weight.Bold))

            fm_box = painter.fontMetrics()
            text_str = str(current_text)
            
            txt_w = fm_box.horizontalAdvance(text_str)
            txt_ascent = fm_box.ascent()
            txt_descent = fm_box.descent()
            txt_h = txt_ascent - txt_descent
            
            txt_x = -txt_w / 2
            txt_y = (txt_ascent / 2) - 2
            
            painter.drawText(int(txt_x), int(txt_y), text_str)
            
        painter.restore()

        if flip_start < self.progress < 1.0:
            arrow_opacity = 1.0 - abs(self.progress - 0.6) / 0.4
            
            arrow_color = QColor(200, 200, 200)
            arrow_color.setAlphaF(max(0, arrow_opacity))
            
            painter.setPen(QPen(arrow_color, 3, Qt.PenStyle.DotLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            path = QPainterPath()
            path.moveTo(-50, 5)
            path.quadTo(0, -20, 50, 5)
            painter.drawPath(path)
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(arrow_color)
            path_head = QPainterPath()
            path_head.moveTo(50, 5)
            path_head.lineTo(42, 0)
            path_head.lineTo(42, 10)
            path_head.closeSubpath()
            painter.drawPath(path_head)