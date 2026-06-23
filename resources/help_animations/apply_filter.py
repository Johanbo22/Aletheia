from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainterPath, QPen

from ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    def __init__(self):
        super().__init__(duration_ms=7000)
        
        # Colors
        self.c_bg = QColor("#2b2b2b")
        self.c_table_bg = QColor("#1e1e1e")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")
        self.c_accent = QColor("#4a90e2")
        self.c_match = QColor("#2d5a2d")
        self.c_dim = QColor("#222222")

        # Data
        self.headers = ["Country", "Region"]
        self.filter_col_idx = 1
        self.filter_val = "Asia"

        self.data_rows = [
            ["China", "Asia"],
            ["France", "Europe"],
            ["Japan", "Asia"],
            ["Brazil", "South Am."],
            ["India", "Asia"],
        ]

        # Layout
        self.table_w = 160
        self.row_h = 28
        self.left_x = 20
        self.right_x = 360
        self.start_y = 70

        self.center_x = (self.left_x + self.table_w + self.right_x) / 2
        self.center_y = self.start_y + (len(self.data_rows) * self.row_h) / 2

    def draw_animation(self, painter, progress):
        painter.fillRect(self.rect(), self.c_bg)

        phase1_highlight = self.get_eased_progress(progress, 0.0, 0.2)
        phase2_drop = self.get_eased_progress(progress, 0.2, 0.4)
        phase3_process = self.get_eased_progress(progress, 0.4, 0.6)
        phase4_transfer = self.get_eased_progress(progress, 0.6, 0.9)

        self._draw_funnel(painter, self.center_x, self.center_y, active_intensity=phase3_process)

        if 0 < phase2_drop < 1.0:
            p0 = QPointF(self.left_x + (self.table_w * 0.75), self.start_y - 10)

            # Point1 is above funnel
            p1 = QPointF(self.center_x, self.center_y - 45)
            #Point2 is inside the funnel
            p2 = QPointF(self.center_x, self.center_y - 10)

            curr_x, curr_y = p0.x(), p0.y()
            angle = 0.0
            scale = 1.0
            opacity = 1.0

            # moves text to funnel until phase =0 50
            # Rotate 90 for 25
            # FDrop into funnel
            if phase2_drop <= 0.5:
                t = phase2_drop / 0.5
                curr_x = p0.x() + (p1.x() - p0.x()) * t
                curr_y = p0.y() + (p1.y() - p0.y()) * t
            elif phase2_drop <= 0.75:
                curr_x, curr_y = p1.x(), p1.y()
                t = (phase2_drop - 0.5) / 0.25
                angle = 90 * t
            else:
                curr_x = p1.x()
                angle = 90
                t = (phase2_drop - 0.75) / 0.25
                curr_y = p1.y() + (p2.y() - p1.y()) * t
                opacity = 1.0 - t
                scale = 1.0 - (0.3 * t)
            
            painter.save()
            painter.translate(curr_x, curr_y)
            painter.rotate(angle)
            painter.scale(scale, scale)

            text_color = QColor(self.c_accent)
            text_color.setAlphaF(opacity)
            painter.setPen(text_color)
            painter.setFont(self.font_bold)

            text = f'== "{self.filter_val}"'
            fm = painter.fontMetrics()
            w = fm.horizontalAdvance(text)
            h = fm.height()

            painter.drawText(QRectF(-w/2, -h/2, w, h), Qt.AlignmentFlag.AlignCenter, text)
            painter.restore()

        # Original table
        self._draw_table_header(painter, self.left_x, self.start_y - self.row_h, highlight_idx=1 if phase1_highlight > 0 else -1, highlight_alpha=phase1_highlight)

        # Draw Rows
        for i, row in enumerate(self.data_rows):
            y = self.start_y + (i * self.row_h)
            is_match = row[self.filter_col_idx] == self.filter_val

            # Colors
            bg = self.c_table_bg
            txt = self.c_text

            if phase3_process > 0:
                if is_match:
                    bg = self.lerp_color(self.c_table_bg, self.c_match, phase3_process)
                else:
                    txt = self.lerp_color(self.c_text, self.c_border, phase3_process)
            
            self._draw_row(painter, self.left_x, y, row, bg, txt)

            if is_match and phase4_transfer > 0:
                travel_dist = self.right_x - self.left_x

                stagger = max(0, min(1, (phase4_transfer * 1.5) - (i * 0.1)))

                if stagger > 0:
                    tx = self.left_x + (travel_dist * stagger)
                    match_idx = sum(1 for r in self.data_rows[:i] if r[1] == self.filter_val)
                    target_y = self.start_y + (match_idx * self.row_h)

                    ty = y + (target_y - y) * stagger

                    self._draw_row(painter, tx, ty, row, self.c_match, self.c_text)
        
        # Draw right table
        self._draw_table_header(painter, self.right_x, self.start_y - self.row_h)

        # Draws a placeholder body 
        body_h = len(self.data_rows) * self.row_h
        painter.setPen(self.c_border)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(self.right_x, self.start_y, self.table_w, body_h))
        
    
    def _draw_funnel(self, painter, cx, cy, active_intensity=0.0):
        size = 20

        # colors
        color = self.c_border
        if active_intensity > 0:
            color = self.lerp_color(self.c_border, self.c_accent, active_intensity)
        
        painter.setPen(QPen(color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        #Drwa path
        path = QPainterPath()
        path.moveTo(cx - size, cy - size)
        path.lineTo(cx + size, cy - size)
        path.lineTo(cx + (size/2), cy + (size/2))
        path.lineTo(cx + (size/2), cy + size)
        path.lineTo(cx - (size/2), cy + size)
        path.lineTo(cx - (size/2), cy + (size/2))
        path.closeSubpath()

        painter.drawPath(path)
        painter.setPen(self.c_text)
        painter.setFont(self.font_small)
        painter.drawText(QRectF(cx - 30, cy + size + 5, 60, 20), Qt.AlignmentFlag.AlignCenter, "Filter")
    
    def _draw_table_header(self, painter, x, y, highlight_idx=-1, highlight_alpha=0.0):
        painter.setFont(self.font_bold)

        col_w = self.table_w / 2

        for i, text in enumerate(self.headers):
            rect = QRectF(x + (i * col_w), y, col_w, self.row_h)

            bg = self.c_header_bg

            if i == highlight_idx and highlight_alpha > 0:
                bg = self.lerp_color(self.c_header_bg, self.c_accent, highlight_alpha)
            
            painter.setBrush(bg)
            painter.setPen(self.c_border)
            painter.drawRect(rect)
            painter.setPen(self.c_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    
    def _draw_row(self, painter, x, y, row_data, bg_color, text_color):
        painter.setFont(self.font_main)
        col_w = self.table_w / 2

        full_rect = QRectF(x, y, self.table_w, self.row_h)
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(full_rect)

        # Draw the individual cells
        painter.setPen(self.c_border)
        for i, text in enumerate(row_data):
            rect = QRectF(x + (i * col_w), y, col_w, self.row_h)
            painter.drawRect(rect)
            
            painter.setPen(text_color)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            painter.setPen(self.c_border)