import logging
from typing import List

from PyQt6.QtCore import QEvent, QObject, QPoint
from PyQt6.QtWidgets import QWidget

from src.ui.widgets.ToastNotification import ToastLevel, ToastNotification

class ToastManager(QObject):
    """
    Manages the creation, positioning, and lifecycle of ToastNotifications

    Anchors the notification bar to the top-right corner of the parent widget
    Automatically handles repositioning events when the parent resizes or when
    toast is dismissed
    """

    MARGIN_X: int = 15
    MARGIN_Y: int = 6
    SPACING_Y: int = 10
    TOAST_WIDTH: int = 420

    def __init__(self, parent_widget: QWidget) -> None:
        super().__init__(parent_widget)
        self._parent_widget = parent_widget
        self._active_toasts: List[ToastNotification] = []
        self._event_filters_installed = set()

        self._install_filter_on_window()
        self._logger = logging.getLogger(__name__)

    def _install_filter_on_window(self) -> None:
        if self._parent_widget not in self._event_filters_installed:
            self._parent_widget.installEventFilter(self)
            self._event_filters_installed.add(self._parent_widget)

        try:
            top_level = self._parent_widget.window()
            if top_level and top_level not in self._event_filters_installed:
                top_level.installEventFilter(self)
                self._event_filters_installed.add(top_level)
        except RuntimeError:
            pass

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Intercepts parent widget resize events to reposition the toasts"""
        try:
            top_level_window = self._parent_widget.window()
            if event.type() == QEvent.Type.Resize and (obj is self._parent_widget or obj is top_level_window):
                self._reposition_toasts(animate=False)
            return super().eventFilter(obj, event)
        except RuntimeError:
            return False

    def show_toast(self, title: str, message: str, level: ToastLevel = ToastLevel.INFO,
                   duration_ms: int = 4000) -> None:
        """
        Creates and displays a new toast notification.

        :param title: The header text.
        :param message: The detailed message text.
        :param level: Severity level dictating the styling.
        :param duration_ms: How long the toast remains visible before auto-dismissing.
        """
        self._install_filter_on_window()
        top_level_window: QWidget = self._parent_widget.window()

        toast = ToastNotification(
            parent=top_level_window,
            title=title,
            message=message,
            level=level,
            duration_ms=duration_ms
        )
        toast.setFixedWidth(self.TOAST_WIDTH)
        toast.adjustSize()

        toast.dismissing.connect(self._handle_toast_dismissing)

        self._active_toasts.append(toast)

        target_pos = self._calculate_toast_position(toast)

        toast.start_entry_animation(target_pos, start_offset_x=toast.width() + self.MARGIN_X)

    def _handle_toast_dismissing(self, toast: QWidget) -> None:
        """Removes the toast from active layout tracking when its being dismissed"""
        try:
            if toast in self._active_toasts:
                self._active_toasts.remove(toast)
        except RuntimeError:
            pass
        self._reposition_toasts(animate=True)

    def _clean_dead_toasts(self) -> None:
        valid_toasts: List[ToastNotification] = []
        for toast in self._active_toasts:
            try:
                _ = toast.isEnabled()
                valid_toasts.append(toast)
            except RuntimeError:
                pass
        self._active_toasts = valid_toasts

    def _reposition_toasts(self, animate: bool = True) -> None:
        """Recalculates the positions for all active toasts and translate their positon"""
        self._clean_dead_toasts()
        for toast in self._active_toasts:
            try:
                target_pos = self._calculate_toast_position(toast)
                if animate:
                    toast.animate_to_position(target_pos)
                else:
                    toast.move(target_pos)
            except RuntimeError:
                pass

    def _calculate_toast_position(self, target_toast: ToastNotification) -> QPoint:
        """
        Calculates the QPoint for a specific toast to properly stack
        """
        try:
            top_level_window: QWidget = self._parent_widget.window()
            window_rect = top_level_window.rect()
        except RuntimeError:
            return QPoint(0, 0)

        target_x = window_rect.width() - self.TOAST_WIDTH - self.MARGIN_X
        target_y = self.MARGIN_Y

        self._clean_dead_toasts()

        for active_toast in self._active_toasts:
            if active_toast is target_toast:
                break
            try:
                target_y += active_toast.height() + self.SPACING_Y
            except RuntimeError:
                continue

        return QPoint(target_x, target_y)
