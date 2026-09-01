from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, pyqtProperty
from PyQt6.QtGui import QColor

from src.ui.theme import ThemeColors

class HoverFocusAnimationMixin:
    """
    Mixin to centralise animation of border color changes, hover and focus events
    Requires the subclass to
    - inherit from a QWidget class
    - Implement a _update_stylesheet(self, color: QColor) method.
    """
    
    def __init__(self, base_color: QColor = None, hover_color: QColor = None, focus_color: QColor = None):
        # Allow for custom colors,
        # but default to ThemeColors
        self._base_border_color = base_color if base_color else ThemeColors.BORDER_BASE
        self._hover_border_color = hover_color if hover_color else ThemeColors.BORDER_HOVER
        self._focus_border_color = focus_color if focus_color else ThemeColors.BORDER_FOCUS
        
        self._animated_color = self._base_border_color
        self._is_focussed = False
        
        self.animation = QPropertyAnimation(self, b"animated_border_color")
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        QTimer.singleShot(0, self._apply_initial_style)
    
    def _apply_initial_style(self) -> None:
        self.animated_border_color = self._base_border_color
        
    
    @pyqtProperty(QColor)
    def animated_border_color(self) -> QColor:
        return self._animated_color
    
    @animated_border_color.setter
    def animated_border_color(self, color: QColor) -> None:
        self._animated_color = color
        self._update_stylesheet(color)
        
    def _update_stylesheet(self, color: QColor) -> None:
        raise NotImplementedError("Subclasses of HoverFocusAnimationMixin must implement _update_stylesheet")

    def _animate_to(self, color: QColor) -> None:
        self.animation.stop()
        self.animation.setEndValue(color)
        self.animation.start()
    
    def enterEvent(self, event) -> None:
        if not self._is_focussed and self.isEnabled():
            self._animate_to(self._hover_border_color)
        super().enterEvent(event)
    
    def leaveEvent(self, event) -> None:
        if not self._is_focussed:
            self._animate_to(self._base_border_color)
        super().leaveEvent(event)
    
    def focusInEvent(self, event) -> None:
        self._is_focussed = True
        self._animate_to(self._focus_border_color)
        super().focusInEvent(event)
    
    def focusOutEvent(self, event) -> None:
        self._is_focussed = False
        # Ensure hover color when mouse is below
        if self.underMouse():
            self._animate_to(self._hover_border_color)
        else:
            self._animate_to(self._base_border_color)
        super().focusOutEvent(event)