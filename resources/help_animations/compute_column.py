from typing import Dict, List

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen

from src.ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """
    Animation showing the computation of a new column based on existing data.
    Visualizes the process of taking two numerical columns (Price and Qty),
    applying a mathematical operation (multiplication), and generating a new Total column.
    """
    
    def __init__(self) -> None:
        super().__init__(duration_ms=6000)
        
        self.c_bg: QColor = QColor("#2b2b2b")
        self.c_table_bg: QColor = QColor("#1e1e1e")
        self.c_header_bg: QColor = QColor("#333333")
        self.c_border: QColor = QColor("#444444")
        self.c_text: QColor = QColor("#e0e0e0")
        
        self.c_operand_highlight: QColor = QColor("#2b4a6b")
        self.c_result_highlight: QColor = QColor("#2b6b4a")
        
        # Table structural definitions
        self.headers: List[str] = ["ID", "Price", "Qty", "Total"]
        self.col_widths: List[int] = [40, 80, 80, 90]
        self.table_width: int = sum(self.col_widths)
        self.row_height: int = 35
        self.data_rows: List[Dict[str, str]] = [
            {"id": "1", "price": "10.00", "qty": "2", "total": "20.00"},
            {"id": "2", "price": "25.50", "qty": "4", "total": "102.00"},
            {"id": "3", "price": "50.00", "qty": "1", "total": "50.00"},
        ]
        self.start_x: float = (550 - self.table_width) / 2
        self.start_y: float = (350 - (self.row_height * (len(self.data_rows) + 1))) / 2

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        """
        Main drawing loop for the Compute Column animation.
        """
        painter.fillRect(self.rect(), self.c_bg)
                
        evaluate_progress: float = self.get_eased_progress(progress, 0.1, 0.4)
        computation_progress: float = self.get_eased_progress(progress, 0.4, 0.7)
        pulse_progress: float = self.get_eased_progress(progress, 0.7, 0.9)
        
        self._draw_table_headers(painter, computation_progress)
        self._draw_table_rows(painter, evaluate_progress, computation_progress)

        if pulse_progress > 0:
            self._draw_success_pulse(painter, pulse_progress)

    def _draw_table_headers(self, painter: QPainter, computation_progress: float) -> None:
        painter.setFont(self.font_bold)
        current_x: float = self.start_x
        
        for index, text in enumerate(self.headers):
            column_width: int = self.col_widths[index]
            cell_rect: QRectF = QRectF(current_x, self.start_y, column_width, self.row_height)
            
            cell_opacity: float = 1.0
            if index == 3:
                cell_opacity = computation_progress
                
            if cell_opacity > 0:
                painter.setOpacity(cell_opacity)
                painter.setBrush(self.c_header_bg)
                painter.setPen(self.c_border)
                painter.drawRect(cell_rect)
                
                painter.setPen(self.c_text)
                painter.drawText(cell_rect, Qt.AlignmentFlag.AlignCenter, text)
                painter.setOpacity(1.0)
                
            current_x += column_width

    def _draw_table_rows(self, painter: QPainter, evaluate_progress: float, computation_progress: float) -> None:
        painter.setFont(self.font_main)
        
        for row_index, row_data in enumerate(self.data_rows):
            y_position: float = self.start_y + ((row_index + 1) * self.row_height)
            current_x: float = self.start_x
            
            base_values: List[str] = [row_data["id"], row_data["price"], row_data["qty"]]
            
            for col_index, cell_text in enumerate(base_values):
                column_width: int = self.col_widths[col_index]
                cell_rect: QRectF = QRectF(current_x, y_position, column_width, self.row_height)
                
                cell_background: QColor = self.c_table_bg
                if col_index in (1, 2) and evaluate_progress > 0:
                    highlight_intensity: float = evaluate_progress * (1.0 - computation_progress)
                    cell_background = self.lerp_color(self.c_table_bg, self.c_operand_highlight, highlight_intensity)
                    
                painter.setBrush(cell_background)
                painter.setPen(self.c_border)
                painter.drawRect(cell_rect)
                
                painter.setPen(self.c_text)
                painter.drawText(cell_rect, Qt.AlignmentFlag.AlignCenter, cell_text)
                
                current_x += column_width

            if computation_progress > 0:
                total_column_width: int = self.col_widths[3]
                total_cell_rect: QRectF = QRectF(current_x, y_position, total_column_width, self.row_height)
                
                painter.setOpacity(computation_progress)
                
                result_bg: QColor = self.lerp_color(self.c_table_bg, self.c_result_highlight, 1.0 - computation_progress)
                painter.setBrush(result_bg)
                painter.setPen(self.c_border)
                painter.drawRect(total_cell_rect)
                
                painter.setPen(self.c_text)
                painter.drawText(total_cell_rect, Qt.AlignmentFlag.AlignCenter, row_data["total"])
                painter.setOpacity(1.0)

    def _draw_success_pulse(self, painter: QPainter, pulse_progress: float) -> None:
        pulse_intensity: float = pulse_progress * (1.0 - pulse_progress) * 4.0 
        
        new_column_x: float = self.start_x + sum(self.col_widths[:3])
        total_table_height: float = self.row_height * (len(self.data_rows) + 1)
        new_column_width: float = self.col_widths[3]
        
        highlight_color: QColor = self.lerp_color(self.c_border, self.accent_color, pulse_intensity)
        
        painter.setPen(QPen(highlight_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(new_column_x - 1, self.start_y - 1, new_column_width + 2, total_table_height + 2))