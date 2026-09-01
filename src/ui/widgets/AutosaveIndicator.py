from PyQt6.QtCore import QEasingCurve, QEvent, QObject, QParallelAnimationGroup, QPoint, QPropertyAnimation, QRect, \
    QTimer, Qt
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget

from icons import IconBuilder, IconType

class AutosaveIndicator(QWidget):
    """
    A non-interactive overlay widget that indicates an autosave operation

    This widget provides a notification by displaying an icon and text.
    It uses Qt's animation framework to transition into view, pulse while active
    and fade out. It is transparent to mouse events to not block user interactions in UI
    """

    # Constants
    _MARGIN_H: int = 10
    _MARGIN_V: int = 5
    _SPACING: int = 8

    _OFFSET_X: int = 20
    _OFFSET_Y: int = 20
    _SLIDE_Y: int = 10

    _TRANSITION_MS: int = 300
    _PULSE_MS: int = 1200
    _DISPLAY_MS: int = 2500

    _OPACITY_MAX: float = 1.0
    _OPACITY_MIN: float = 0.0
    _OPACITY_PULSE: float = 0.4

    def __init__(self, parent: QWidget) -> None:
        """
        Initialize the autosave widget and animation sequence

        Configures the layout containing the icon and status text
        It also pre-allocates and configures the QPropertyAnimation and
        QParallelAnimation instances to prevent overhead during save events

        :param parent: The parent widget over which this indicator is drawn
        """
        super().__init__(parent)
        self.setObjectName("AutosaveIndicatorWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        if parent is not None:
            parent.installEventFilter(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(self._MARGIN_H, self._MARGIN_V, self._MARGIN_H, self._MARGIN_V)
        layout.setSpacing(self._SPACING)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

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

        self.show_fade = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.show_fade.setDuration(self._TRANSITION_MS)
        self.show_fade.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.show_slide = QPropertyAnimation(self, b"pos")
        self.show_slide.setDuration(self._TRANSITION_MS)
        self.show_slide.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.show_group = QParallelAnimationGroup(self)
        self.show_group.addAnimation(self.show_fade)
        self.show_group.addAnimation(self.show_slide)

        self.pulse_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.pulse_anim.setDuration(self._PULSE_MS)
        self.pulse_anim.setKeyValueAt(0.0, self._OPACITY_MAX)
        self.pulse_anim.setKeyValueAt(0.5, self._OPACITY_PULSE)
        self.pulse_anim.setKeyValueAt(1.0, self._OPACITY_MAX)
        self.pulse_anim.setLoopCount(-1)

        self.show_group.finished.connect(self.pulse_anim.start)

        self.hide_fade = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.hide_fade.setDuration(self._TRANSITION_MS)
        self.hide_fade.setEasingCurve(QEasingCurve.Type.InQuad)

        self.hide_slide = QPropertyAnimation(self, b"pos")
        self.hide_slide.setDuration(self._TRANSITION_MS)
        self.hide_slide.setEasingCurve(QEasingCurve.Type.InQuad)

        self.hide_group = QParallelAnimationGroup(self)
        self.hide_group.addAnimation(self.hide_fade)
        self.hide_group.addAnimation(self.hide_slide)
        self.hide_group.finished.connect(self.hide)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade_out)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """
        Intercept parent resize events to reposition the indicator

        Prevents the widget from floating on the UI edge if the
        parent window changes size while the indicator is visible.

        :param obj: The object emitting the event
        :param event: The event emitted
        :return: bool indicating if the event was completed
        """
        if self.parent() and obj == self.parent() and event.type() == QEvent.Type.Resize:
            self._recalculate_position()
        return super().eventFilter(obj, event)

    def _recalculate_position(self) -> None:
        """
        Adjusts X-coordinate when parent resizes
        Update active animations to prevent snapping
        """
        if not self.parent() or not self.isVisible():
            return

        parent_rect: QRect = self.parent().rect()
        target_x: int = max(self._MARGIN_H, parent_rect.width() - self.width() - self._OFFSET_X)

        current_pos: QPoint = self.pos()
        self.move(target_x, current_pos.y())

        if self.show_group.state() == QParallelAnimationGroup.State.Running:
            self._update_animation_x(self.show_slide, target_x)

        if self.hide_group.state() == QParallelAnimationGroup.State.Running:
            self._update_animation_x(self.hide_slide, target_x)

    def _update_animation_x(self, anim: QPropertyAnimation, target_x: int) -> None:
        """
        Update the X coordinate of a position animation

        :param anim: The running QPropertyAnimation for position
        :param target_x: The new target X coordinate
        """
        start_val: QPoint | None = anim.startValue()
        end_val: QPoint | None = anim.endValue()
        if isinstance(start_val, QPoint) and isinstance(end_val, QPoint):
            anim.setStartValue(QPoint(target_x, start_val.y()))
            anim.setEndValue(QPoint(target_x, start_val.y()))

    def show_indicator(self) -> None:
        """
        Position and expose the indicator with an entrance animation

        Calculates the target position based on parent widget's current
        dimensions.
        """
        if not self.parent():
            return

        parent_rect: QRect = self.parent().rect()
        self.adjustSize()

        target_x: int = max(self._MARGIN_H, parent_rect.width() - self.width() - self._OFFSET_X)
        target_y: int = self._OFFSET_Y

        is_hiding: bool = self.hide_group.state() == QParallelAnimationGroup.State.Running

        if self.isVisible() and is_hiding:
            start_y: int = self.pos().y()
            start_opacity: float = self.opacity_effect.opacity()
        elif not self.isVisible():
            start_y: int = target_y + self._SLIDE_Y
            start_opacity: float = self._OPACITY_MIN
            self.move(target_x, start_y)
            self.opacity_effect.setOpacity(start_opacity)
        else:
            start_y: int = self.pos().y()
            start_opacity: float = self.opacity_effect.opacity()

        self.raise_()
        self.show()

        self.hide_group.stop()
        self.pulse_anim.stop()

        self.show_fade.setStartValue(start_opacity)
        self.show_fade.setEndValue(self._OPACITY_MAX)

        self.show_slide.setStartValue(QPoint(target_x, start_y))
        self.show_slide.setEndValue(QPoint(target_x, target_y))

        self.show_group.start()
        self.hide_timer.start(self._DISPLAY_MS)

    def fade_out(self) -> None:
        """
        Trigger the exit animation for the indicator

        Interrupts the show and pulse animations to prevent property updates.
        Calculates a slide down based on current position and starts the fade-out
        parallel animation group.
        """
        self.show_group.stop()
        self.pulse_anim.stop()

        current_pos: QPoint = self.pos()
        target_y: int = current_pos.y() + self._SLIDE_Y

        current_opacity: float = self.opacity_effect.opacity()

        self.hide_fade.setStartValue(current_opacity)
        self.hide_fade.setEndValue(self._OPACITY_MIN)

        self.hide_slide.setStartValue(current_pos)
        self.hide_slide.setEndValue(QPoint(current_pos.x(), target_y))

        self.hide_group.start()
