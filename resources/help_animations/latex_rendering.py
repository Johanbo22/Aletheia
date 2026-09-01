from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainterPath, QPen

from src.ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """
    Animation showing the effect of enabling LaTeX rendering.
    """
    
    def __init__(self):
        super().__init__(duration_ms=6000)
        
        self.c_bg = QColor("#2b2b2b")
        self.c_plot_bg = QColor("#1e1e1e")
        self.c_axis = QColor("#888888")
        self.c_text = QColor("#e0e0e0")
        self.c_line = QColor("#4a90e2")
        self.c_highlight = QColor("#ffaa00") 
        
        # Fonts
        self.font_std = QFont("Segoe UI", 10)
        self.font_latex = QFont("Times New Roman", 12, QFont.Weight.Bold) 
        self.font_latex.setItalic(True)
        
        self.margin = 50
        self.plot_rect = QRectF(self.margin + 10, 80, 
                                self.width() - (self.margin*2), 
                                self.height() - 130)
        
    def draw_animation(self, painter, progress):
        painter.fillRect(self.rect(), self.c_bg)
        
        toggle_prog = self.get_eased_progress(progress, 0.4, 0.6)
        
        is_latex = toggle_prog > 0.5
        
        self._draw_controls(painter, is_latex, toggle_prog)
        painter.setBrush(self.c_plot_bg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.plot_rect)
        
        painter.setPen(QPen(self.c_axis, 2))
        # Y Axis
        painter.drawLine(int(self.plot_rect.left()), int(self.plot_rect.top()), 
                         int(self.plot_rect.left()), int(self.plot_rect.bottom()))
        # X Axis
        painter.drawLine(int(self.plot_rect.left()), int(self.plot_rect.bottom()), 
                         int(self.plot_rect.right()), int(self.plot_rect.bottom()))
        
        self._draw_sine_wave(painter, self.plot_rect)
        
        # Interpolate Color for transition effect
        text_color = self.c_text
        if 0 < toggle_prog < 1.0:
            flash = 1.0 - abs(toggle_prog - 0.5) * 2
            text_color = self.lerp_color(self.c_text, QColor("#ffffff"), flash)
            
        painter.setPen(text_color)
        
        title_rect = QRectF(0, 50, self.width(), 30)
        if is_latex:
            painter.setFont(self.font_latex)
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, "f(x) = sin(2πx) • e⁻ˣ")
        else:
            painter.setFont(self.font_std)
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, "Damped Sine Wave Function")
            
        painter.save()
        painter.translate(25, self.plot_rect.center().y())
        painter.rotate(-90)
        
        if is_latex:
            painter.setFont(self.font_latex)
            painter.drawText(QRectF(-100, -15, 200, 30), Qt.AlignmentFlag.AlignCenter, "Amplitude (A)")
        else:
            painter.setFont(self.font_std)
            painter.drawText(QRectF(-100, -15, 200, 30), Qt.AlignmentFlag.AlignCenter, "Amplitude")
            
        painter.restore()
        
        xlabel_rect = QRectF(self.plot_rect.left(), self.plot_rect.bottom() + 10, 
                             self.plot_rect.width(), 30)
        if is_latex:
            painter.setFont(self.font_latex)
            painter.drawText(xlabel_rect, Qt.AlignmentFlag.AlignCenter, "Time (t) [μs]")
        else:
            painter.setFont(self.font_std)
            painter.drawText(xlabel_rect, Qt.AlignmentFlag.AlignCenter, "Time (microseconds)")

    def _draw_controls(self, painter, is_checked, anim_progress):
        """Draws a simulated checkbox for 'Use LaTeX'"""
        cx = self.width() - 120
        cy = 55
        box_size = 16
        
        painter.setFont(self.font_small)
        painter.setPen(self.c_text)
        painter.drawText(cx + 25, cy + 13, "Use LaTeX")
        
        rect = QRectF(cx, cy, box_size, box_size)
        painter.setPen(self.c_axis)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)
        
        if is_checked:
            fill_color = self.c_highlight
            painter.setBrush(fill_color)
            painter.setPen(Qt.PenStyle.NoPen)
            scale = 1.0
            if anim_progress > 0.5:
                 scale = (anim_progress - 0.5) * 2
            
            center = rect.center()
            size = box_size * 0.7 * scale
            painter.drawRect(QRectF(center.x() - size/2, center.y() - size/2, size, size))

    def _draw_sine_wave(self, painter, rect):
        path = QPainterPath()
        steps = 50
        w = rect.width()
        h = rect.height()
        
        start_pt = QPointF(rect.left(), rect.center().y())
        path.moveTo(start_pt)
        
        import math
        for i in range(steps + 1):
            t = i / steps
            x = rect.left() + (w * t)
            
            val = math.sin(4 * math.pi * t) * math.exp(-2 * t)
            
            y = rect.center().y() - (val * (h * 0.4))
            path.lineTo(QPointF(x, y))
            
        painter.setPen(QPen(self.c_line, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)