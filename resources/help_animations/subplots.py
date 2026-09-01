from PyQt6.QtCore import QRectF, Qt, QPointF
from PyQt6.QtGui import QColor, QPen, QPainterPath

from src.ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """
    Animation showing the creation of multiple subplots (2x2 grid).
    Visualizes a single canvas splitting into four distinct plot areas.
    """
    
    def __init__(self):
        super().__init__(duration_ms=7000)
        
        self.c_bg = QColor("#2b2b2b")
        self.c_plot_bg = QColor("#1e1e1e")
        self.c_axis = QColor("#888888")
        self.c_text = QColor("#e0e0e0")
        self.c_highlight = QColor("#4a90e2") # Selection highlight
        
        self.c_p1 = QColor("#4a90e2") 
        self.c_p2 = QColor("#e74c3c") 
        self.c_p3 = QColor("#2ecc71") 
        self.c_p4 = QColor("#f1c40f") 
        
        self.margin = 40
        self.plot_area_rect = QRectF(self.margin, 60, 
                                     self.width() - (self.margin*2), 
                                     self.height() - 80)
        
    def draw_animation(self, painter, progress):
        painter.fillRect(self.rect(), self.c_bg)
        
        
        split_prog = self.get_eased_progress(progress, 0.2, 0.5)
        pop_prog = self.get_eased_progress(progress, 0.5, 0.9)
        
        w = self.plot_area_rect.width()
        h = self.plot_area_rect.height()
        cx = self.plot_area_rect.center().x()
        cy = self.plot_area_rect.center().y()
        
        painter.setBrush(self.c_plot_bg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.plot_area_rect)
        
        
        gap = 10 * split_prog 
        
        r1 = QRectF(self.plot_area_rect.left(), self.plot_area_rect.top(), 
                    (w/2) - gap, (h/2) - gap)
        r2 = QRectF(cx + gap, self.plot_area_rect.top(), 
                    (w/2) - gap, (h/2) - gap)
        r3 = QRectF(self.plot_area_rect.left(), cy + gap, 
                    (w/2) - gap, (h/2) - gap)
        r4 = QRectF(cx + gap, cy + gap, 
                    (w/2) - gap, (h/2) - gap)
        
        painter.setPen(QPen(self.c_axis, 2))
        painter.setBrush(self.c_plot_bg)
        
        if split_prog > 0:
            painter.drawRect(r1)
            painter.drawRect(r2)
            painter.drawRect(r3)
            painter.drawRect(r4)
        else:
            painter.drawRect(self.plot_area_rect)

        # Charts
        if pop_prog > 0:
            # Quadrant 1: Line Chart
            self._draw_line_chart(painter, r1, self.c_p1, pop_prog)
            
            # Quadrant 2: Bar Chart (Delay slightly)
            p2_prog = self.get_eased_progress(pop_prog, 0.2, 1.0)
            if p2_prog > 0:
                self._draw_bar_chart(painter, r2, self.c_p2, p2_prog)

            # Quadrant 3: Scatter Chart
            p3_prog = self.get_eased_progress(pop_prog, 0.4, 1.0)
            if p3_prog > 0:
                self._draw_scatter_chart(painter, r3, self.c_p3, p3_prog)
                
            # Quadrant 4: Area Chart
            p4_prog = self.get_eased_progress(pop_prog, 0.6, 1.0)
            if p4_prog > 0:
                self._draw_area_chart(painter, r4, self.c_p4, p4_prog)


    def _draw_line_chart(self, painter, rect, color, progress):
        """Draws a simple sine-wave like line."""
        painter.setClipRect(rect)
        
        # Points
        points = []
        steps = 10
        dx = rect.width() / steps
        for i in range(steps + 1):
            x = rect.left() + (i * dx)
            normalized_y = 0.5 + 0.3 * (-1 if i % 2 else 1) 
            y = rect.bottom() - (rect.height() * normalized_y)
            points.append(QPointF(x, y))
            
        path = QPainterPath()
        path.moveTo(points[0])
        for p in points[1:]:
            path.lineTo(p)
            
        
        color.setAlphaF(progress)
        painter.setPen(QPen(color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        painter.setClipping(False)

    def _draw_bar_chart(self, painter, rect, color, progress):
        """Draws 4 bars."""
        bars = [0.6, 0.8, 0.4, 0.9]
        bar_w = (rect.width() / len(bars)) * 0.6
        gap = (rect.width() / len(bars)) * 0.4
        
        start_x = rect.left() + (gap / 2)
        
        color.setAlphaF(progress)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        
        for i, val in enumerate(bars):
            h = rect.height() * val * progress 
            x = start_x + (i * (bar_w + gap))
            y = rect.bottom() - h
            
            painter.drawRect(QRectF(x, y, bar_w, h))

    def _draw_scatter_chart(self, painter, rect, color, progress):
        """Draws random dots."""
        dots = [(0.2, 0.3), (0.4, 0.6), (0.6, 0.4), (0.8, 0.8), (0.5, 0.5)]
        
        color.setAlphaF(progress)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        
        radius = 4 * progress
        
        for rx, ry in dots:
            cx = rect.left() + (rect.width() * rx)
            cy = rect.bottom() - (rect.height() * ry)
            painter.drawEllipse(QPointF(cx, cy), radius, radius)

    def _draw_area_chart(self, painter, rect, color, progress):
        """Draws filled area."""
        painter.setClipRect(rect)
        
        path = QPainterPath()
        path.moveTo(rect.left(), rect.bottom())
        
        # Peak
        path.lineTo(rect.left() + rect.width()*0.5, rect.top() + rect.height()*0.2)
        path.lineTo(rect.right(), rect.bottom())
        path.closeSubpath()
        
        c_fill = QColor(color)
        c_fill.setAlphaF(0.5 * progress)
        
        painter.setBrush(c_fill)
        painter.setPen(QPen(color, 2))
        painter.drawPath(path)
        painter.setClipping(False)