from PyQt6.QtCore import QSize, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QDialog, QPushButton

from src.ui.widgets.mixins import HoverFocusAnimationMixin

class ColormapButton(HoverFocusAnimationMixin, QPushButton):
    currentTextChanged = pyqtSignal(str)
    currentIndexChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        QPushButton.__init__(self, parent)
        HoverFocusAnimationMixin.__init__(
            self,
            base_color=QColor("#ccc")
        )

        self.current_colormap = "viridis"
        self.setText("viridis")
        self.setIconSize(QSize(100, 20))

        self.clicked.connect(self._open_picker)
        self._update_display()
        self._update_stylesheet(self._base_border_color)

    def _update_stylesheet(self, color: QColor) -> None:
        self.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: 5px;
                border: 1.5px solid {color.name()};
                border-radius: 4px;
                background-color: white;
            }}
            QPushButton:hover {{
                background-color: #f0f0f0;
            }}
        """)

    def _open_picker(self):
        from src.ui.dialogs import ColormapPickerDialog
        dialog = ColormapPickerDialog(self.current_colormap, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_colormap = dialog.get_selected_colormap()
            if new_colormap and new_colormap != self.current_colormap:
                self.setCurrentText(new_colormap)

    def setCurrentText(self, text):
        self.current_colormap = text
        self._update_display()
        self.currentTextChanged.emit(text)

    def currentText(self):
        return self.current_colormap

    def setCurrentIndex(self, index):
        pass

    def _update_display(self):
        from src.ui.dialogs import ColormapPickerDialog
        self.setText(f" {self.current_colormap}")
        icon = ColormapPickerDialog.generate_icon(self.current_colormap)
        self.setIcon(icon)