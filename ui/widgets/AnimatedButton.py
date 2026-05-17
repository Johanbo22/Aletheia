from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, pyqtProperty, QTimer, Qt, QEvent, QSize
from PyQt6.QtGui import QColor, QKeyEvent
from PyQt6.QtWidgets import QPushButton

from ui.theme import ThemeColors


class DataPlotStudioButton(QPushButton):
    """
    Custom QPushButton, default button for Aletheia\n
    If unique buttons with unique styling is required, use regular QPushButton.setObjectName() and style it in css file\n
    Regular main action buttons use the theme.ThemeColors.MainColor property
    """
    
    _HOVER_DARKEN_FACTOR: int = 110
    _HOVER_LIGHTEN_FACTOR: int = 130
    _PRESSED_DARKEN_FACTOR: int = 115
    _LIGHTNESS_THRESHOLD: float = 0.5

    def __init__(self,
                text: str,
                parent=None,
                base_color_hex: str = ThemeColors.ButtonDefaultColor,
                hover_color_hex: str | None = None,
                pressed_color_hex: str | None = None,
                text_color_hex: str | None = None,
                border_style: str = "none",
                padding: str = "8px",
                border_radius: str = "4px",
                font_weight: str = "bold",
                typewriter_effect: bool = False,
                accessible_description: str | None = None,
                tooltip: str | None = None,
                icon_size: QSize | None = QSize(20, 20)) -> None:
        super().__init__(text, parent)
        
        # Setting accessibility tags for screen readers. 
        # This will help with the type writer effect for screen readers
        self.setAccessibleName(text)
        if accessible_description:
            self.setAccessibleDescription(accessible_description)
        if tooltip:
            self.setToolTip(tooltip)
        
        
        self.setIconSize(icon_size)
            
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        self.setProperty("keyboard_focus", False)

        self._base_color = QColor(base_color_hex)
        self._hover_color, self._pressed_color = self._derive_colors(self._base_color, hover_color_hex, pressed_color_hex)
        self._text_color = self._derive_text_color(self._base_color, text_color_hex)

        self._border_style = border_style
        self._padding = padding
        self._border_radius = border_radius
        self._font_weight = font_weight

        self._animated_color = self._base_color

        # Typewriter effect
        self._use_typewriter_effect = typewriter_effect
        self._full_text = text
        self._current_text_index = 0
        self._typewriter_timer = QTimer(self)
        self._typewriter_timer.setInterval(50)
        self._typewriter_timer.timeout.connect(self._update_typewriter_text)

        self.enter_animation = QPropertyAnimation(self, b"animated_color")
        self.enter_animation.setDuration(150)
        self.enter_animation.setEndValue(self._hover_color)
        self.enter_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.leave_animation = QPropertyAnimation(self, b"animated_color")
        self.leave_animation.setDuration(250)
        self.leave_animation.setEndValue(self._base_color)
        self.leave_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self._update_stylesheet(self._base_color)

    def setText(self, text: str) -> None:
        self._full_text = text
        self.setAccessibleName(text)
        if self._typewriter_timer.isActive():
            self._current_text_index = 0
            super().setText("")
        else:
            super().setText(text)
    
    def _update_typewriter_text(self) -> None:
        if self._current_text_index <= len(self._full_text):
            super().setText(self._full_text[:self._current_text_index])
            self._current_text_index += 1
        else:
            self._typewriter_timer.stop()

    @pyqtProperty(QColor)
    def animated_color(self) -> QColor:
        """Get the current animated color."""
        return self._animated_color

    @animated_color.setter
    def animated_color(self, color: QColor) -> None:
        """Set the animated color and update the stylesheet."""
        self._animated_color = color
        self._update_stylesheet(color)

    def _update_stylesheet(self, color: QColor) -> None:
        """
        Updates the button's stylesheet based on its role (determined by base color)
        and the current animated color.
        """
        focus_ring_color = self._text_color.name()
        disabled_bg_rgba = f"rgba({color.red()}, {color.green()}, {color.blue()}, 128)"
        disabled_text_rgba = f"rgba({self._text_color.red()}, {self._text_color.green()}, {self._text_color.blue()}, 128)"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color.name()};
                color: {self._text_color.name()};
                font-weight: {self._font_weight};
                padding: {self._padding};
                border: {self._border_style};
                border-radius: {self._border_radius};
            }}
            QPushButton:pressed {{
                background-color: {self._pressed_color.name()};
            }}
            QPushButton[keyboard_focus="true"] {{
                border: 2px solid {focus_ring_color};
                outline: none;
            }}
            QPushButton:disabled {{
                background-color: {disabled_bg_rgba};
                color: {disabled_text_rgba};
            }}
        """)

    def _start_active_animations(self) -> None:
        """Triggers visual state for hovering"""
        self.leave_animation.stop()
        self.enter_animation.setStartValue(self.animated_color)
        self.enter_animation.start()
        
        if self._use_typewriter_effect and self.isEnabled():
            self._current_text_index = 0
            super().setText("")
            self._typewriter_timer.start()
    
    def _revert_active_animations(self) -> None:
        """Reverts the button to resting state"""
        self.enter_animation.stop()
        self.leave_animation.setStartValue(self.animated_color)
        self.leave_animation.start()
        
        if self._use_typewriter_effect:
            self._typewriter_timer.stop()
            super().setText(self._full_text)
    
    def enterEvent(self, event) -> None:
        """Called when the mouse enters the button widget."""
        if not self.property("keyboard_focus"):
            self._start_active_animations()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Called when the mouse leaves the button widget."""
        if not self.property("keyboard_focus"):
            self._revert_active_animations()
        super().leaveEvent(event)
    
    def focusInEvent(self, event) -> None:
        """Called when button recieves keyboard focus"""
        reason = event.reason()
        if reason in (Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason):
            self.setProperty("keyboard_focus", True)
            self.style().unpolish(self)
            self.style().polish(self)
            if not self.underMouse():
                self._start_active_animations()
        super().focusInEvent(event)
    
    def focusOutEvent(self, event) -> None:
        """Called when button loosees focus from keybaord"""
        if self.property("keyboard_focus"):
            self.setProperty("keyboard_focus", False)
            self.style().unpolish(self)
            self.style().polish(self)
            
        if not self.underMouse():
            self._revert_active_animations()
        super().focusOutEvent(event)
        
    def mousePressEvent(self, event) -> None:
        """Completes the typewriter effect if clicked while animation is not finished"""
        if self._use_typewriter_effect and self._typewriter_timer.isActive():
            self._typewriter_timer.stop()
            super().setText(self._full_text)
        super().mousePressEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Complete the typewriter effect if activated by keyboard accept"""
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._use_typewriter_effect and self._typewriter_timer.isActive():
                self._typewriter_timer.stop()
                super().setText(self._full_text)
        super().keyPressEvent(event)
    def _derive_colors(self, base_color: QColor, hover_hex: str | None, pressed_hex: str | None) -> tuple[QColor, QColor]:
        """Derives the hover and pressed colors on the base colors"""
        if hover_hex:
            hover_color = QColor(hover_hex)
        else:
            if base_color.lightnessF() > self._LIGHTNESS_THRESHOLD:
                hover_color = base_color.darker(self._HOVER_DARKEN_FACTOR)
            else:
                hover_color = base_color.lighter(self._HOVER_LIGHTEN_FACTOR)
        if pressed_hex:
            pressed_color = QColor(pressed_hex)
        else:
            pressed_color = hover_color.darker(self._PRESSED_DARKEN_FACTOR)
        
        return hover_color, pressed_color
    
    def _derive_text_color(self, base_color: QColor, text_hex: str | None) -> QColor:
        if text_hex:
            return QColor(text_hex)
        
        return QColor("#ffffff") if base_color.lightnessF() < self._LIGHTNESS_THRESHOLD else QColor("#000000")

    def updateColors(self,
                    base_color_hex: str,
                    hover_color_hex: str | None = None,
                    pressed_color_hex: str = None,
                    text_color_hex: str | None = None) -> None:
        """Method to preserve buttons color when using a qcolordialog"""
        self._base_color = QColor(base_color_hex)
        self._hover_color, self._pressed_color = self._derive_colors(self._base_color, hover_color_hex, pressed_color_hex)
        self._text_color = self._derive_text_color(self._base_color, text_color_hex)

        self.enter_animation.setEndValue(self._hover_color)
        self.leave_animation.setEndValue(self._base_color)

        self.animated_color = self._base_color
        self._update_stylesheet(self._base_color)