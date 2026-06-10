"""
Toast Notification widget to show similar properties to the StatusBar without logging to the logger instance

This is the replacement for a standard QMessageBox for information, warning, error that do not
require user interaction, for messages that do require user interaction assign QMessageBox.

The widget consists of the following properties:
TODO
"""
from enum import StrEnum

from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QSizePolicy, QStyle, QVBoxLayout, QWidget

class ToastLevel(StrEnum):
    """Enumeration of available severity levels for the Toast Notification"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

class ToastNotification(QWidget):
    """
    A notification widget that is non-blocking, and auto dismissing

    This widget is responsible for its own visual representation, progress tracking
    and entry/exit sliding animation. It communicates via the ToastManager via the closed signal
    """
    # A closed emit signal that is emitted when
    # the toast has finished its exit animation and is
    # ready to be destroyed
    closed = pyqtSignal(QWidget)

    ANIMATION_DURATION_MS: int = 300
    PROGRESS_UPDATE_INTERVAL_MS: int = 10

    def __init__(self, parent: QWidget, title: str, message: str, level: ToastLevel = ToastLevel.INFO, duration_ms: int = 3000) -> None:
        super().__init__(parent)
        self._title = title
        self._message = message
        self._level = level
        self._duration_ms = duration_ms
        self._time_left_ms = duration_ms

        self._setup_ui()
        self._setup_logic()

    def _setup_ui(self) -> None:
        """Initializes the layout and widgets inside the toast"""
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.setProperty("toastLevel", self._level.value)
        self.setObjectName("toastNotification")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        content_widget = QWidget(self)
        content_widget.setObjectName("toastContent")
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(10)

        # Icon
        self._icon_label = QLabel(content_widget)
        self._icon_label.setObjectName("toastIcon")
        self._icon_label.setPixmap(self._get_standard_icon().pixmap(24, 24))
        self._icon_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        content_layout.addWidget(self._icon_label, alignment=Qt.AlignmentFlag.AlignTop)

        # Text portion
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        self._title_label = QLabel(self._title, content_widget)
        self._title_label.setObjectName("toastTitle")
        self._title_label.setWordWrap(True)

        self._message_label = QLabel(self._message, content_widget)
        self._message_label.setObjectName("toastMessage")
        self._message_label.setWordWrap(True)

        text_layout.addWidget(self._title_label)
        text_layout.addWidget(self._message_label)
        text_layout.addStretch()
        content_layout.addLayout(text_layout)

        # Close button
        self._close_button = QPushButton(content_widget)
        self._close_button.setObjectName("toastCloseButton")
        self._close_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        self._close_button.setFixedSize(24, 24)
        self._close_button.setToolTip("Dismiss")
        content_layout.addWidget(self._close_button, alignment=Qt.AlignmentFlag.AlignTop)

        main_layout.addWidget(content_widget)

        # Progress bar
        self._progress_bar = QProgressBar(self)
        self._progress_bar.setObjectName("toastProgressBar")
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setRange(0, self._duration_ms)
        self._progress_bar.setValue(self._duration_ms)
        self._progress_bar.setFixedHeight(4)
        main_layout.addWidget(self._progress_bar)

        self.style().unpolish(self)
        self.style().polish(self)

    def _setup_logic(self) -> None:
        """Wires the signals and startst the auto dismiss timer"""
        self._close_button.clicked.connect(self.dismiss)

        self._timer = QTimer(self)
        self._timer.setInterval(self.PROGRESS_UPDATE_INTERVAL_MS)
        self._timer.timeout.connect(self._update_progress)

        self._slide_animation = QPropertyAnimation(self, b"pos", self)
        self._slide_animation.setDuration(self.ANIMATION_DURATION_MS)

    def _get_standard_icon(self) -> QIcon:
        """Maps the ToastLevel to a native standard Icon"""
        pixmap_map = {
            ToastLevel.INFO: QStyle.StandardPixmap.SP_MessageBoxInformation,
            ToastLevel.SUCCESS: QStyle.StandardPixmap.SP_DialogApplyButton,
            ToastLevel.WARNING: QStyle.StandardPixmap.SP_MessageBoxWarning,
            ToastLevel.ERROR: QStyle.StandardPixmap.SP_MessageBoxCritical,
        }
        standard_pixmap = pixmap_map.get(self._level, QStyle.StandardPixmap.SP_MessageBoxInformation)
        return self.style().standardIcon(standard_pixmap)

    def _update_progress(self) -> None:
        """Updates the visual progress bar and triggers dismissal when the timer expires"""
        self._time_left_ms -= self.PROGRESS_UPDATE_INTERVAL_MS
        self._progress_bar.setValue(self._time_left_ms)

        if self._time_left_ms <= 0:
            self._timer.stop()
            self.dismiss()

    def start_entry_animation(self, target_pos: QPoint, start_offset_x: int) -> None:
        """
        Animates the toast sliding into view

        :param target_pos: The final position of the toast
        :param start_offset_x: How far to the right the toast should start off-screen
        """
        start_pos = QPoint(target_pos.x() + start_offset_x, target_pos.y())
        self.move(start_pos)
        self.show()
        self.raise_()

        self._slide_animation.stop()
        self._slide_animation.setStartValue(start_pos)
        self._slide_animation.setEndValue(target_pos)
        self._slide_animation.setEasingCurve(QEasingCurve.Type.OutQuart)
        self._slide_animation.start()

        self._timer.start()

    def animate_to_position(self, target_pos: QPoint) -> None:
        """
        Translates the toast to a new position
        used when a toast above is closed
        """
        self.raise_()
        self._slide_animation.stop()
        self._slide_animation.setStartValue(self.pos())
        self._slide_animation.setEndValue(target_pos)
        self._slide_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._slide_animation.start()

    def dismiss(self) -> None:
        """Initiates the exit animation and preparest the toast for destruction"""
        self._timer.stop()
        self._close_button.setEnabled(False)

        current_pos = self.pos()
        target_pos = QPoint(current_pos.x() + self.width() + 20, current_pos.y())

        self._slide_animation.stop()
        self._slide_animation.setStartValue(current_pos)
        self._slide_animation.setEndValue(target_pos)
        self._slide_animation.setEasingCurve(QEasingCurve.Type.InBack)

        self._slide_animation.finished.connect(self._on_dismiss_finished)
        self._slide_animation.start()

    def _on_dismiss_finished(self) -> None:
        """Cleans up the widget at animation finish"""
        self.closed.emit(self)
        self.deleteLater()