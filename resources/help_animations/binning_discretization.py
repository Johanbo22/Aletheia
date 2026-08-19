from typing import Any, Dict, List

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen

from src.ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """
    Animation showing column binning / discretization.
    Visualizes continuous numerical values being evaluated and grouped into discrete category bins,
    resulting in a new categorical column.
    """
    
    def __init__(self) -> None:
        super().__init__(duration_ms=6000)
        
        self.c_bg: QColor = QColor("#2b2b2b")
        self.c_table_bg: QColor = QColor("#1e1e1e")
        self.c_header_bg: QColor = QColor("#333333")
        self.c_border: QColor = QColor("#444444")
        self.c_text: QColor = QColor("#e0e0e0")
        
        self.c_high_bin: QColor = QColor("#2b6b4a")  
        self.c_mid_bin: QColor = QColor("#6b5b2b")   
        self.c_low_bin: QColor = QColor("#6b2b2b")   
        
        self.headers: List[str] = ["ID", "Score", "Bin Category"]
        self.col_widths: List[int] = [50, 80, 110]
        self.table_width: int = sum(self.col_widths)
        self.row_height: int = 35
        
        self.data_rows: List[Dict[str, Any]] = [
            {"base_values": ["1", "88"], "bin_label": "High", "color": self.c_high_bin},
            {"base_values": ["2", "45"], "bin_label": "Mid",  "color": self.c_mid_bin},
            {"base_values": ["3", "15"], "bin_label": "Low",  "color": self.c_low_bin},
            {"base_values": ["4", "72"], "bin_label": "High", "color": self.c_high_bin},
        ]
        
        self.start_x: float = (550 - self.table_width) / 2
        self.start_y: float = (350 - (self.row_height * (len(self.data_rows) + 1))) / 2

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        
        painter.fillRect(self.rect(), self.c_bg)
                
        evaluate_progress: float = self.get_eased_progress(progress, 0.1, 0.4)
        bin_creation_progress: float = self.get_eased_progress(progress, 0.4, 0.7)
        pulse_progress: float = self.get_eased_progress(progress, 0.7, 0.9)
        
        self._draw_table_headers(painter, bin_creation_progress)
        self._draw_table_rows(painter, evaluate_progress, bin_creation_progress)

        if pulse_progress > 0:
            self._draw_success_pulse(painter, pulse_progress)

    def _draw_table_headers(self, painter: QPainter, bin_creation_progress: float) -> None:
        painter.setFont(self.font_bold)
        current_x: float = self.start_x
        
        for index, text in enumerate(self.headers):
            column_width: int = self.col_widths[index]
            cell_rect: QRectF = QRectF(current_x, self.start_y, column_width, self.row_height)
            
            cell_opacity: float = 1.0
            if index == 2:
                cell_opacity = bin_creation_progress
                
            if cell_opacity > 0:
                painter.setOpacity(cell_opacity)
                painter.setBrush(self.c_header_bg)
                painter.setPen(self.c_border)
                painter.drawRect(cell_rect)
                
                painter.setPen(self.c_text)
                painter.drawText(cell_rect, Qt.AlignmentFlag.AlignCenter, text)
                painter.setOpacity(1.0)
                
            current_x += column_width

    def _draw_table_rows(self, painter: QPainter, evaluate_progress: float, bin_creation_progress: float) -> None:
        painter.setFont(self.font_main)
        
        for row_index, row_data in enumerate(self.data_rows):
            y_position: float = self.start_y + ((row_index + 1) * self.row_height)
            current_x: float = self.start_x
            
            for col_index, cell_text in enumerate(row_data["base_values"]):
                column_width: int = self.col_widths[col_index]
                cell_rect: QRectF = QRectF(current_x, y_position, column_width, self.row_height)
                
                cell_background: QColor = self.c_table_bg
                if col_index == 1 and evaluate_progress > 0:
                    cell_background = self.lerp_color(self.c_table_bg, row_data["color"], evaluate_progress)
                    
                painter.setBrush(cell_background)
                painter.setPen(self.c_border)
                painter.drawRect(cell_rect)
                
                painter.setPen(self.c_text)
                painter.drawText(cell_rect, Qt.AlignmentFlag.AlignCenter, cell_text)
                
                current_x += column_width

            if bin_creation_progress > 0:
                bin_column_width: int = self.col_widths[2]
                bin_cell_rect: QRectF = QRectF(current_x, y_position, bin_column_width, self.row_height)
                
                painter.setOpacity(bin_creation_progress)
                painter.setBrush(row_data["color"])
                painter.setPen(self.c_border)
                painter.drawRect(bin_cell_rect)
                
                painter.setPen(self.c_text)
                painter.drawText(bin_cell_rect, Qt.AlignmentFlag.AlignCenter, row_data["bin_label"])
                painter.setOpacity(1.0)

    def _draw_success_pulse(self, painter: QPainter, pulse_progress: float) -> None:
        pulse_intensity: float = pulse_progress * (1.0 - pulse_progress) * 4.0 
        
        new_column_x: float = self.start_x + self.col_widths[0] + self.col_widths[1]
        total_table_height: float = self.row_height * (len(self.data_rows) + 1)
        new_column_width: float = self.col_widths[2]
        
        highlight_color: QColor = self.lerp_color(self.c_border, self.accent_color, pulse_intensity)
        
        painter.setPen(QPen(highlight_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(new_column_x - 1, self.start_y - 1, new_column_width + 2, total_table_height + 2))