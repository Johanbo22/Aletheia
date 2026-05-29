from email.charset import QP

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QLabel, QSpinBox, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QColor, QShortcut, QKeySequence, QGuiApplication, QMouseEvent

from ui.theme import ThemeColors
from ui.managers.plot_tab_managers.color_manager import ColorManager

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

        # Debounce timer
        debounce_interval_ms: int = 300
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(debounce_interval_ms)
        self._update_timer.timeout.connect(self._emit_update)

        self._drag_pos: QPoint | None = None
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        
        # Text edit area
        self.text_edit = QLineEdit()
        self.text_edit.setMinimumWidth(120)
        self.text_edit.setToolTip("Edit annotation text")
        self.text_edit.textChanged.connect(self._schedule_update)
        self.text_edit.returnPressed.connect(self._emit_update)
        layout.addWidget(self.text_edit)
        
        layout.addWidget(QLabel("Size:"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(6, 48)
        self.size_spin.setToolTip("Font Size")
        self.size_spin.setAccelerated(True)
        self.size_spin.setKeyboardTracking(False)
        self.size_spin.valueChanged.connect(self._schedule_update)
        layout.addWidget(self.size_spin)

        self.bold_btn = QPushButton("B")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setToolTip("Bold")
        font = self.bold_btn.font()
        font.setBold(True)
        self.bold_btn.setFont(font)
        self.bold_btn.toggled.connect(self._schedule_update)
        layout.addWidget(self.bold_btn)

        self.italic_btn = QPushButton("I")
        self.italic_btn.setCheckable(True)
        self.italic_btn.setToolTip("Italic")
        font = self.italic_btn.font()
        font.setItalic(True)
        self.italic_btn.setFont(font)
        self.italic_btn.toggled.connect(self._schedule_update)
        layout.addWidget(self.italic_btn)
        
        self.color_btn = QPushButton("A")
        self.color_btn.setToolTip("Text Color")
        self.color_btn.clicked.connect(self._choose_color)
        layout.addWidget(self.color_btn)
        
        self.bg_color_btn = QPushButton("Bg")
        self.bg_color_btn.setToolTip("Background color")
        self.bg_color_btn.clicked.connect(self._choose_bg_color)
        layout.addWidget(self.bg_color_btn)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setObjectName("DestructiveButton")
        self.delete_btn.clicked.connect(self._emit_delete)
        layout.addWidget(self.delete_btn)
        
        self.setLayout(layout)

        self.esc_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.esc_shortcut.activated.connect(self.close)
        
    def load_annotations(self, index: int, ann_data: dict) -> None:
        self.blockSignals(True)
        self.current_index = index
        self.text_edit.setText(ann_data.get("text", ""))
        self.size_spin.setValue(ann_data.get("fontsize", 12))
        self.current_color = ann_data.get("color", "black")
        self.current_bg_color = ann_data.get("bg_color", "wheat")

        self.bold_btn.setChecked(ann_data.get("fontweight", "normal") == "bold")
        self.italic_btn.setChecked(ann_data.get("fontstyle", "normal") == "italic")
        
        ColorManager.update_button_color_swatch(self.color_btn, QColor(self.current_color))
        ColorManager.update_button_color_swatch(self.bg_color_btn, QColor(self.curreng_bg_color))

        self.text_edit.setFocus()
        self.text_edit.selectAll()
        
        self.blockSignals(False)
    
    def _choose_color(self) -> None:
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor(self.current_color), self, options=QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self.current_color = color.name(QColor.NameFormat.HexArgb) if color.alpha() < 255 else color.name()
            ColorManager.update_button_color_swatch(self.color_btn, QColor(self.current_color))
            
            self._emit_update()

    
    def _choose_bg_color(self) -> None:
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor(self.current_bg_color), self, options=QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self.current_bg_color = color.name(QColor.NameFormat.HexArgb) if color.alpha() < 255 else color.name()
            ColorManager.update_button_color_swatch(self.bg_color_btn, QColor(self.current_bg_color))
            
            self._emit_update()

    def _schedule_update(self) -> None:
        if self.current_index >= 0:
            self._update_timer.start()
    
    def _emit_update(self) -> None:
        if self.current_index < 0:
            return
        self._update_timer.stop()
        data = {
            "text": self.text_edit.text(),
            "fontsize": self.size_spin.value(),
            "color": self.current_color,
            "bg_color": self.current_bg_color,
            "fontweight": "bold" if self.bold_btn.isChecked() else "normal",
            "fontstyle": "italic" if self.italic_btn.isChecked() else "normal"
        }
        self.styleChanged.emit(self.current_index, data)
    
    def _emit_delete(self) -> None:
        if self.current_index >= 0:
            self.deleteRequested.emit(self.current_index)
            self.close()

    def show_at_clamped(self, global_pos: QPoint) -> None:
        """Shows the toolbar, and clamps position to avoid spawning off-screen"""
        self.adjustSize()
        toolbar_rect = self.rect()

        screen = QGuiApplication.screenAt(global_pos)
        if not screen:
            screen = QGuiApplication.primaryScreen()

        screen_rect = screen.availableGeometry()

        x = global_pos.x()
        y = global_pos.y()

        if x + toolbar_rect.width() > screen_rect.right():
            x = screen_rect.right() - toolbar_rect.width() - 10
        if y + toolbar_rect.height() > screen_rect.bottom():
            y = screen_rect.bottom() - toolbar_rect.height() - 10

        self.move(QPoint(x, y))
        self.show()
        self.raise_()
        self.activateWindow()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            diff = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + diff)
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()
        super().mouseMoveEvent(event)