from PyQt6.QtCore import QObject, pyqtSignal
from ui.widgets.ToastNotification import ToastLevel

class GlobalSignals(QObject):
    """
    Global event bus for signal communication

    Acts as a global singleton registry for Qt Signals
    """
    toast_requested = pyqtSignal(str, str, ToastLevel, int)

global_signals = GlobalSignals()