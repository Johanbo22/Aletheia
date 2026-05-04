from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QLabel, QSpinBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton
from ui.widgets.ControlElements import DataPlotStudioSpinBox

class ContextualAnnotationToolbar(QWidget):
    """
    A floating frameless toolbar that appears contextually over the plot
    when an annotation is selected on the canvas
    """
    # Two signals 
    # styleChanged emits (annotation_index: int, updated_props: dict)
    # deleteRequested emits (annotation_index: int)
    styleChanged = pyqtSignal(int, dict)
    deleteRequested = pyqtSignal(int)
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setObjectName("ContextualToolbar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        self.current_index: int = -1
        self.current_color: str = "black"
        self.current_bg_color: str = "wheat"
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        
        # Text edit area
        self.text_edit = QLineEdit()
        self.text_edit.setMinimumWidth(120)
        self.text_edit.textChanged.connect(self._emit_update)
        layout.addWidget(self.text_edit)
        
        layout.addWidget(QLabel("Size:"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(6, 48)
        self.size_spin.valueChanged.connect(self._emit_update)
        layout.addWidget(self.size_spin)
        
        self.color_btn = DataPlotStudioButton("A")
        self.color_btn.setToolTip("Text Color")
        self.color_btn.clicked.connect(self._choose_color)
        layout.addWidget(self.color_btn)
        
        self.bg_color_btn = DataPlotStudioButton("Bg")
        self.bg_color_btn.setToolTip("Background color")
        self.bg_color_btn.clicked.connect(self._choose_bg_color)
        layout.addWidget(self.bg_color_btn)
        
        self.delete_btn = DataPlotStudioButton("Delete", base_color_hex=ThemeColors.DestructiveColor, text_color_hex="white")
        self.delete_btn.setObjectName("DeleteAnnButton")
        self.delete_btn.clicked.connect(self._emit_delete)
        layout.addWidget(self.delete_btn)
        
        self.setLayout(layout)
        
    def load_annotations(self, index: int, ann_data: dict) -> None:
        self.blockSignals(True)
        self.current_index = index
        self.text_edit.setText(ann_data.get("text", ""))
        self.size_spin.setValue(ann_data.get("fontsize", 12))
        self.current_color = ann_data.get("color", "black")
        self.current_bg_color = ann_data.get("bg_color", "wheat")
        
        self.color_btn.updateColors(base_color_hex=self.current_color)
        self.bg_color_btn.updateColors(base_color_hex=self.current_bg_color)
        
        self.blockSignals(False)
    
    def _choose_color(self) -> None:
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor(self.current_color), self)
        if color.isValid():
            self.current_color = color.name()
            self.color_btn.updateColors(base_color_hex=self.current_color)
            self._emit_update()
    
    def _choose_bg_color(self) -> None:
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor(self.current_bg_color), self)
        if color.isValid():
            self.current_bg_color = color.name()
            self.bg_color_btn.updateColors(base_color_hex=self.current_bg_color)
            self._emit_update()
    
    def _emit_update(self) -> None:
        if self.current_index < 0:
            return
        data = {
            "text": self.text_edit.text(),
            "fontsize": self.size_spin.value(),
            "color": self.current_color,
            "bg_color": self.current_bg_color
        }
        self.styleChanged.emit(self.current_index, data)
    
    def _emit_delete(self) -> None:
        if self.current_index >= 0:
            self.deleteRequested.emit(self.current_index)
            self.close()