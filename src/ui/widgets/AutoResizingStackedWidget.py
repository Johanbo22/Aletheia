from PyQt6.QtCore import QAbstractAnimation, QEasingCurve, QParallelAnimationGroup, QPropertyAnimation, QSize, \
    QVariantAnimation, pyqtSlot
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QLabel, QSizePolicy, QStackedWidget, QWidget

QT_MAX_WIDGET_SIZE: int = 16777215

class AutoResizingStackedWidget(QStackedWidget):
    """
    A QStackedWidget that automatically animates its height when transitioning
    between child widgets of different sizes

    Uses a parallel animation group to fade a snapshot the current widget while resizing
    the container height to match the next widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        :param parent: The parent QWidget object.
        """
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        # Animation settings
        self._transition_duration: int = 300
        self._easing_curve: QEasingCurve = QEasingCurve(QEasingCurve.Type.InOutQuad)
        self._animation_group: QParallelAnimationGroup | None = None
        self._ghost_label: QLabel | None = None

    def sizeHint(self) -> QSize:
        """
        Return the preferred size hint of the currently active widget

        :return: QSize representing the target dimensions
        """
        current = self.currentWidget()
        if current:
            return current.sizeHint()
        return QSize(0, 0)

    def minimumSizeHint(self) -> QSize:
        """
        Return the minimum size hint of the currently active widget.

        :return: QSize representing the minimum viable dimensions
        """
        current = self.currentWidget()
        if current:
            return current.minimumSizeHint()
        return QSize(0, 0)

    def setCurrentIndex(self, index: int) -> None:
        """
        Change the active widget index and trigger the resizing animation

        :param index: The index of the target widget to display
        """
        if self.currentIndex() == index:
            return

        if self._animation_group and self._animation_group.state() == QAbstractAnimation.State.Running:
            self._animation_group.stop()

        self._delete_ghost_label()
        if self._animation_group:
            self._animation_group.deleteLater()
            self._animation_group = None

        current_widget: QWidget = self.currentWidget()
        next_widget: QWidget = self.widget(index)

        if not current_widget or not next_widget or not self.isVisible():
            super().setCurrentIndex(index)
            return

        self._setup_ghost_label(current_widget)

        start_height: int = self.height()

        super().setCurrentIndex(index)
        self._ghost_label.raise_()

        next_widget.updateGeometry()
        end_height: int = next_widget.sizeHint().height()

        self._start_transition_animations(start_height, end_height)

    def _setup_ghost_label(self, current_widget: QWidget) -> None:
        """
        Create and overlay a visual snapshot of the current widget

        :param current_widget: The QWidget currently visible before the transition
        """
        current_pixmap: QPixmap = current_widget.grab()

        self._ghost_label = QLabel(self)
        self._ghost_label.setPixmap(current_pixmap)
        self._ghost_label.setGeometry(current_widget.geometry())
        self._ghost_label.show()

    def _start_transition_animations(self, start_height: int, end_height: int) -> None:
        """
        Configure and initiate the parallel height and opacity animations

        :param start_height: Container height at the start of the animation
        :param end_height: Target height of the incoming widget
        """
        self._animation_group = QParallelAnimationGroup(self)

        height_animation = QVariantAnimation(self._animation_group)
        height_animation.setDuration(self._transition_duration)
        height_animation.setEasingCurve(self._easing_curve)
        height_animation.setStartValue(start_height)
        height_animation.setEndValue(end_height)
        height_animation.valueChanged.connect(self.setFixedHeight)
        self._animation_group.addAnimation(height_animation)

        opacity_effect = QGraphicsOpacityEffect(self._ghost_label)
        self._ghost_label.setGraphicsEffect(opacity_effect)

        fade_animation = QPropertyAnimation(opacity_effect, b"opacity", self._animation_group)
        fade_animation.setDuration(self._transition_duration)
        fade_animation.setEasingCurve(self._easing_curve)
        fade_animation.setStartValue(1.0)
        fade_animation.setEndValue(0.0)
        self._animation_group.addAnimation(fade_animation)

        self._animation_group.finished.connect(self._on_transition_finished)
        self._animation_group.start()

    def _delete_ghost_label(self) -> None:
        """Helper to remove the ghost label and the effects associated with it"""
        if self._ghost_label:
            self._ghost_label.hide()
            self._ghost_label.deleteLater()
            self._ghost_label = None

    @pyqtSlot()
    def _on_transition_finished(self) -> None:
        """
        Clean up constraints and references after the animation sequence is completed.
        """
        self.setMinimumHeight(0)
        self.setMaximumHeight(QT_MAX_WIDGET_SIZE)
        self.updateGeometry()

        self._delete_ghost_label()
