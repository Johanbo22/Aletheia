from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtProperty, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QBrush, QFont, QMouseEvent

class VennDiagramWidget(QWidget):
    """Custom widget to visualize a venn diagram for merging datasets"""
    
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(400, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)
        
        self.join_type: str = "inner"
        self.left_count: int = 0
        self.right_count: int = 0
        self.result_count: int= 0
        
        self._hovered_segment: str | None = None
        
        # Theme colors
        self._color_active: QColor = QColor("#3498DB")
        self._color_inactive: QColor = QColor("#ECF0F1")
        self._color_outline: QColor = QColor("#7F8C8D")
        self._text_color: QColor = QColor("#2C3E50")
        
        # sutle animations
        self._anim_progress: float = 1.0
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(750)
        self._animation.setEasingCurve(QEasingCurve.Type.OutBack)
        self._animation.valueChanged.connect(self._on_anim_step)
        
        
    @pyqtProperty(QColor)
    def activeColor(self) -> QColor:
        """Primary active segment color."""
        return self._color_active

    @activeColor.setter
    def activeColor(self, color: QColor) -> None:
        self._color_active = color
        self.update()

    @pyqtProperty(QColor)
    def inactiveColor(self) -> QColor:
        """Background inactive segment color."""
        return self._color_inactive

    @inactiveColor.setter
    def inactiveColor(self, color: QColor) -> None:
        self._color_inactive = color
        self.update()

    @pyqtProperty(QColor)
    def outlineColor(self) -> QColor:
        """Stroke color for the Venn diagram circles."""
        return self._color_outline

    @outlineColor.setter
    def outlineColor(self, color: QColor) -> None:
        self._color_outline = color
        self.update()

    @pyqtProperty(QColor)
    def textColor(self) -> QColor:
        """Text color for the statistics and labels."""
        return self._text_color

    @textColor.setter
    def textColor(self, color: QColor) -> None:
        self._text_color = color
        self.update()
    
    def _on_anim_step(self, value: float) -> None:
        self._anim_progress = value
        self.update()
        
    def set_data(self, join_type: str, left_c: int, right_c: int, res_c: int) -> None:
        """Update the diagram data and trigger repaint."""
        self.join_type = join_type.lower()
        self.left_count = left_c
        self.right_count = right_c
        self.result_count = res_c
        
        self._animation.stop()
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.start()
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        new_hover = None
        
        if hasattr(self, "_path_intersect") and self._path_intersect.contains(pos):
            new_hover = "intersect"
        elif hasattr(self, "_path_left_only") and self._path_left_only.contains(pos):
            new_hover = "left"
        elif hasattr(self, "_path_right_only") and self._path_right_only.contains(pos):
            new_hover = "right"
        
        if new_hover != self._hovered_segment:
            self._hovered_segment = new_hover
            self.update()
    
    def leaveEvent(self, event: QMouseEvent) -> None:
        self._hovered_segment = None
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        width = rect.width()
        height = rect.height()
        
        available_height = height - 90 
        target_radius = min(width / 4, available_height / 2)
        radius = target_radius * (0.5 + 0.5 * self._anim_progress)
        
        target_offset = radius * 0.75
        start_offset = width / 2.5
        offset = start_offset - (start_offset - target_offset) * self._anim_progress
        
        center_y = 50 + (available_height / 2)
        c1 = QPointF(width / 2 - offset, center_y)
        c2 = QPointF(width / 2 + offset, center_y)
        
        path_left = QPainterPath()
        path_left.addEllipse(c1, radius, radius)
        
        path_right = QPainterPath()
        path_right.addEllipse(c2, radius, radius)
        
        self._path_intersect = path_left.intersected(path_right)
        self._path_left_only = path_left.subtracted(path_right)
        self._path_right_only = path_right.subtracted(path_left)
        
        base_active_alpha = 180
        base_inactive_alpha = 100
        
        def create_brush(color: QColor, segment_id: str, is_active: bool) -> QBrush:
            alpha = base_active_alpha if is_active else base_inactive_alpha
            if self._hovered_segment == segment_id:
                alpha = min(255, alpha + 50)
            
            color = QColor(color)
            color.setAlpha(int(alpha * self._anim_progress))
            return QBrush(color)
        
        active_color = QColor(self.activeColor)
        inactive_color = QColor(self.inactiveColor)
        
        brush_inner = create_brush(active_color if self.join_type in ["inner", "left", "right", "outer"] else inactive_color, "intersect", self.join_type in ["inner", "left", "right", "outer"])
        brush_left = create_brush(active_color if self.join_type in ["left", "outer"] else inactive_color, "left", self.join_type in ["left", "outer"])
        brush_right = create_brush(active_color if self.join_type in ["right", "outer"] else inactive_color, "right", self.join_type in ["right", "outer"])
                    
        # Draw the segments
        painter.setPen(Qt.PenStyle.NoPen)
        
        painter.setBrush(brush_left)
        painter.drawPath(self._path_left_only)
        
        painter.setBrush(brush_right)
        painter.drawPath(self._path_right_only)
        
        painter.setBrush(brush_inner)
        painter.drawPath(self._path_intersect)
        
        painter.setBrush(Qt.BrushStyle.NoBrush)
        outlinecolor = QColor(self.outlineColor)
        outlinecolor.setAlpha(int(255 * self._anim_progress))
        painter.setPen(QPen(outlinecolor, 2.5))
        painter.drawPath(path_left)
        painter.drawPath(path_right)
        
        text_c = QColor(self.textColor)
        text_c.setAlpha(int(255 * self._anim_progress))
        painter.setPen(text_c)
        
        # Result Header (Top center)
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(0, 5, width, 25), Qt.AlignmentFlag.AlignCenter, f"Resulting Rows: {self.result_count}")
        
        font.setPointSize(9)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(QRectF(0, 25, width, 20), Qt.AlignmentFlag.AlignCenter, f"({self.join_type.capitalize()} Join)")
        
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        
        text_y = center_y + radius + 10
        painter.drawText(QRectF(c1.x() - radius, text_y, radius * 2, 20), Qt.AlignmentFlag.AlignCenter, f"Current: {self.left_count}")
        painter.drawText(QRectF(c2.x() - radius, text_y, radius * 2, 20), Qt.AlignmentFlag.AlignCenter, f"New: {self.right_count}")