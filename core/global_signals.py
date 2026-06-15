from PyQt6.QtCore import QObject, pyqtSignal
from ui.widgets.ToastNotification import ToastLevel

class GlobalSignals(QObject):
    """
    Global event bus for signal communication

    Acts as a global singleton registry for Qt Signals
    """
    toast_requested = pyqtSignal(str, str, ToastLevel, int)

    def request_toast(self, title: str, message: str, level: ToastLevel = ToastLevel.INFO,
                      duration_ms: int = 4000) -> None:
        """
        Helper method to emit a toast request with standard defaults.
        Callers should prefer this over calling toast_requested.emit() directly.

        :param title: The header text of the toast.
        :param message: The detailed message text.
        :param level: The severity level (default: ToastLevel.INFO).
        :param duration_ms: Display duration in milliseconds (default: 4000).
        """
        self.toast_requested.emit(title, message, level, duration_ms)

global_signals = GlobalSignals()
