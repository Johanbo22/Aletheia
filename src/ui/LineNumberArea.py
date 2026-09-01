from PyQt6.QtCore import QSize
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QWidget


class LineNumberArea(QWidget):
    """widget to draw line numbers in editor"""
    def __init__(self, editor) -> None:
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Routes mouse events to the code editor"""
        if hasattr(self.editor, "lineNumberAreaMousePressEvent"):
            self.editor.lineNumberAreaMousePressEvent(event)
        super().mousePressEvent(event)