from PyQt6.QtWidgets import QWidget, QLabel, QGraphicsOpacityEffect, QHBoxLayout
from PyQt6.QtCore import QEasingCurve, QParallelAnimationGroup, QPoint, QTimer, Qt, QPropertyAnimation

from ui.icons import IconBuilder, IconType

class AutosaveIndicator(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("AutosaveIndicatorWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        self.icon_label = QLabel()
        self.icon_label.setObjectName("AutosaveIcon")
        pixmap = IconBuilder.build(IconType.AppIcon, resolution=24).pixmap(24, 24)
        self.icon_label.setPixmap(pixmap)
        
        self.text_label = QLabel("Saving...")
        self.text_label.setObjectName("AutosaveText")
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        
        self.hide()
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self._transition_duration_ms: int = 300

        self.show_fade = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.show_fade.setDuration(self._transition_duration_ms)
        self.show_fade.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.show_slide = QPropertyAnimation(self, b"pos")
        self.show_slide.setDuration(self._transition_duration_ms)
        self.show_slide.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        self.show_group = QParallelAnimationGroup(self)
        self.show_group.addAnimation(self.show_fade)
        self.show_group.addAnimation(self.show_slide)
        
        self.pulse_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.pulse_anim.setDuration(1200)
        self.pulse_anim.setKeyValueAt(0.0, 1.0)
        self.pulse_anim.setKeyValueAt(0.5, 0.4)
        self.pulse_anim.setKeyValueAt(1.0, 1.0)
        self.pulse_anim.setLoopCount(-1)
        
        self.show_group.finished.connect(self.pulse_anim.start)

        self.hide_fade = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.hide_fade.setDuration(self._transition_duration_ms)
        self.hide_fade.setEasingCurve(QEasingCurve.Type.InQuad)
        
        self.hide_slide = QPropertyAnimation(self, b"pos")
        self.hide_slide.setDuration(self._transition_duration_ms)
        self.hide_slide.setEasingCurve(QEasingCurve.Type.InQuad)
        
        self.hide_group = QParallelAnimationGroup(self)
        self.hide_group.addAnimation(self.hide_fade)
        self.hide_group.addAnimation(self.hide_slide)
        self.hide_group.finished.connect(self.hide)
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade_out)

    def show_indicator(self) -> None:
        """Defines the position and exposes the indicator"""
        parent_rect = self.parent().rect()
        self.adjustSize()

        target_x: int = parent_rect.width() - self.width() - 20
        target_y: int = 20
        start_y: int = target_y + 10

        self.move(target_x, start_y)
        self.opacity_effect.setOpacity(0.0)
        self.raise_()
        self.show()

        self.hide_group.stop()
        self.pulse_anim.stop()
        
        self.show_fade.setStartValue(0.0)
        self.show_fade.setEndValue(1.0)
        
        self.show_slide.setStartValue(QPoint(target_x, start_y))
        self.show_slide.setEndValue(QPoint(target_x, target_y))
        
        self.show_group.start()
        
        self.hide_timer.start(2500)
    
    def fade_out(self) -> None:
        """Animates the indicator fading out and sliding down slightly."""
        self.show_group.stop()
        self.pulse_anim.stop()

        current_pos: QPoint = self.pos()
        target_y: int = current_pos.y() + 10

        current_opacity = self.opacity_effect.opacity()
        
        self.hide_fade.setStartValue(current_opacity)
        self.hide_fade.setEndValue(0.0)
        
        self.hide_slide.setStartValue(current_pos)
        self.hide_slide.setEndValue(QPoint(current_pos.x(), target_y))
        
        self.hide_group.start()