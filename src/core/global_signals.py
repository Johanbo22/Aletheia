from enum import Enum, StrEnum
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

class ToastLevel(StrEnum):
    """Enumeration of available severity levels for the Toast Notification"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

class LogLevel(Enum):
    """Defines the logging levels"""
    SUCCESS = "SUCCESS"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class GlobalSignals(QObject):
    """
    Global event bus for signal communication

    Acts as a global singleton registry for Qt Signals
    """
    toast_requested = pyqtSignal(str, str, ToastLevel, int)
    log_requested = pyqtSignal(str, str, object)
    help_explorer_requested = pyqtSignal(str)

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

    def request_log(self, message: str, level: LogLevel | str = LogLevel.INFO,
                    action_type: Optional[str] = None) -> None:
        """
        Helper method to emit a status bar log request globally.
        Callers should prefer this over calling log_requested.emit() directly.

        :param message: The detail message to log in the status bar/terminal.
        :param level: The severity level as string ('INFO', 'ERROR', 'SUCCESS', 'WARNING').
        :param action_type: Optional context string about the action.
        """
        self.log_requested.emit(message, level, action_type)

    def request_help_explorer(self, topic_id: str) -> None:
        """
        Method to emit a help explorer request globally

        :param topic_id: The specific topic ID to navigate to
        """
        self.help_explorer_requested.emit(topic_id)

global_signals = GlobalSignals()
