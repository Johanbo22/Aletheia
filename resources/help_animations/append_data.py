from typing import List

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen

from src.ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """
    Animation showing data appending
    Visualizes two datasets with the same columns merging vertically into a single dataset
    """
    def __init__(self) -> None:
        super().__init__(duration_ms=6000)
        
        self.c_bg = QColor("#2b2b2b")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")
        
        self.c_dataset_1 = QColor("#2b4a6b")
        self.c_dataset_2 = QColor("#2b6b4a")
        
        self.headers: List[str] = ["ID", "Category", "Value"]
        self.col_widths: List[int] = [40, 90, 70]
        self.table_width: int = sum(self.col_widths)
        self.row_height: int = 28
        
        self.dataset_1_rows: List[List[str]] = [
            ["1", "Alpha", "100"],
            ["2", "Beta", "200"]
        ]
        self.dataset_2_rows: List[List[str]] = [
            ["3", "Gamma", "300"],
            ["4", "Delta", "400"],
        ]
        
        self.start_x: float = (550 - self.table_width) / 2
        self.ds1_start_y: float = 40
        self.ds2_start_y: float = 200
        
        self.ds2_final_y: float = self.ds1_start_y + ((len(self.dataset_1_rows) + 1) * self.row_height)
    
    def draw_animation(self, painter: QPainter, progress: float) -> None:
        painter.fillRect(self.rect(), self.c_bg)
        
        move_progress: float = self.get_eased_progress(progress, 0.2, 0.7)
        pulse_progress: float = self.get_eased_progress(progress, 0.7, 0.9)
        
        self._draw_header(painter, self.start_x, self.ds1_start_y, opacity=1.0)
        
        for index, row in enumerate(self.dataset_1_rows):
            y_position: float = self.ds1_start_y + ((index + 1) * self.row_height)
            self._draw_row(painter, self.start_x, y_position, row, self.c_dataset_1, self.c_text)
            
        current_ds2_header_y: float = self.ds2_start_y + ((self.ds2_final_y - self.row_height - self.ds2_start_y) * move_progress)
        
        header_opacity: float = 1.0 - move_progress
        if header_opacity > 0:
            painter.setOpacity(header_opacity)
            self._draw_header(painter, self.start_x, current_ds2_header_y, opacity=header_opacity)
            painter.setOpacity(1.0)
        
        ds2_rows_initial_y: float = self.ds2_start_y + self.row_height
        
        for index, row in enumerate(self.dataset_2_rows):
            initial_row_y: float = ds2_rows_initial_y + (index * self.row_height)
            final_row_y: float = self.ds2_final_y + (index * self.row_height)
            
            current_row_y: float = initial_row_y + ((final_row_y - initial_row_y) * move_progress)
            
            self._draw_row(painter, self.start_x, current_row_y, row, self.c_dataset_2, self.c_text)
        
        if pulse_progress > 0:
            self._draw_success_pulse(painter, pulse_progress)
    
    def _draw_header(self, painter: QPainter, x: float, y: float, opacity: float) -> None:
        painter.setFont(self.font_bold)
        current_x: float = x
        
        for index, text in enumerate(self.headers):
            width: int = self.col_widths[index]
            rect = QRectF(current_x, y, width, self.row_height)
            
            painter.setBrush(self.c_header_bg)
            painter.setPen(self.c_border)
            painter.drawRect(rect)
            
            text_color = QColor(self.c_text)
            text_color.setAlphaF(opacity)
            painter.setPen(text_color)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            current_x += width
    
    def _draw_row(self, painter: QPainter, x: float, y: float, values: List[str], bg_color: QColor, text_color: QColor) -> None:
        painter.setFont(self.font_main)
        current_x: float = x
        
        full_row_rect = QRectF(x, y, self.table_width, self.row_height)
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(full_row_rect)
        
        painter.setPen(self.c_border)
        for index, text in enumerate(values):
            width: int = self.col_widths[index]
            rect = QRectF(current_x, y, width, self.row_height)
            
            painter.drawRect(rect)
            
            painter.setPen(text_color)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            painter.setPen(self.c_border)
            
            current_x += width
    
    def _draw_success_pulse(self, painter: QPainter, pulse_progress: float) -> None:
        pulse_intensity: float = pulse_progress * (1.0 - pulse_progress) * 4.0
        
        total_rows: int = 1 + len(self.dataset_1_rows) + len(self.dataset_2_rows)
        total_height: float = total_rows * self.row_height
        
        highlight_color = self.lerp_color(self.c_border, self.accent_color, pulse_intensity)
        
        painter.setPen(QPen(highlight_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(self.start_x - 1, self.ds1_start_y - 1, self.table_width + 2, total_height + 2))