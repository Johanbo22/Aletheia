# ui/status_bar.py
from re import I

from PyQt6.QtWidgets import QStatusBar, QLabel, QLineEdit, QProgressBar, QApplication, QFrame, QMenu
from PyQt6.QtCore import Qt, QPoint, QTimer, QEvent
from PyQt6.QtGui import QAction, QCursor
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from core.logger import Logger
from ui.widgets.AnimatedButton import DataPlotStudioButton
from ui.dialogs.LogHistoryPopup import LogHistoryPopup

class LogLevel(Enum):
    """Defines the logging levels"""
    SUCCESS = "SUCCESS"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class LogColor(Enum):
    """Logging level color maps"""
    SUCCESS = "#00ff00"
    INFO = "#00ff00"
    WARNING = "#ffaa00"
    ERROR = "#ff0000"

class StatusBarConstants:
    TYPEWRITER_INTERVAL_MS: int = 20
    ANIMATION_CHUNK_DIVISOR: int = 50
    DEFAULT_ACTION_TIMEOUT_SEC: int = 2
    CLEAR_TIMER_MS: int = 8000
    HIDE_PROGRESS_BAR_INTERVAL: int = 1200
    MAX_LOG_HISTORY: int = 200


class StatusBar(QStatusBar):
    """Custom status bar with terminal output, Added history viewer
    """
    
    def __init__(self) -> None:
        super().__init__()
        
        #logger will be set by main app
        self.logger: Optional[Logger] = Logger.get_instance()

        #track changes
        self.recent_actions: List[Any] = []
        self.log_history: list[str] = []
        self.action_timeout: int = StatusBarConstants.DEFAULT_ACTION_TIMEOUT_SEC 
        self.last_action_time: Optional[datetime] = None
        
        # Message queue for the typerwrite animation
        # Should prevent stuttering on multiple calls 
        self.message_queue: list[tuple[str, str]] = []
        self.is_typing: bool = False

        #Timer effect for type
        self.typewriter_timer: QTimer = QTimer()
        self.typewriter_timer.setInterval(StatusBarConstants.TYPEWRITER_INTERVAL_MS)
        self.typewriter_timer.timeout.connect(self._type_next_char)
        self.current_anim_text: str = ""
        self.current_anim_index: int = 0
        
        # An auto clear timer to remove previous logs
        # After 8 seconds the old message is cleared from the terminal
        self.clear_timer: QTimer = QTimer()
        self.clear_timer.setInterval(StatusBarConstants.CLEAR_TIMER_MS)
        self.clear_timer.setSingleShot(True)
        self.clear_timer.timeout.connect(self._reset_to_idle_state)

        self.setObjectName("main_status_bar")

        # Adding a label of data stat
        self.stats_label = QLabel("No Data")
        self.stats_label.setObjectName("stats_label")
        
        self.memory_bar = QProgressBar()
        self.memory_bar.setObjectName("status_memory_bar")
        self.memory_bar.setFixedWidth(100)
        self.memory_bar.setTextVisible(True)
        self.memory_bar.setFormat("Mem: %p%")
        self.memory_bar.setProperty("usageLevel", "normal")
        self.memory_bar.setToolTip("History Buffer Memory Usage")
        self.memory_bar.hide()

        # Adding some progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("status_progress_bar")
        self.progress_bar.setFixedWidth(150)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        
        # Terminal-like output area
        self.terminal = QLineEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setObjectName("status_terminal")
        self.terminal.setCursor(Qt.CursorShape.PointingHandCursor)
        self.terminal.setToolTip("Click to view Log History")
        self.terminal.installEventFilter(self)
        
        # Right-click context menu
        self.terminal.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.terminal.customContextMenuRequested.connect(self._show_terminal_context_menu)

        # Open history button
        self.history_button = DataPlotStudioButton("≡", base_color_hex="#333", hover_color_hex="#444", text_color_hex="#ddd", padding="4px")
        self.history_button.setToolTip("View Log History")
        self.history_button.setFixedWidth(24)
        self.history_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_button.setObjectName("status_history_button")
        self.history_button.clicked.connect(self.show_log_history)
        
        self.error_count: int = 0
        self.warning_count: int = 0
        
        self.issue_counter_label = QLabel("")
        self.issue_counter_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.issue_counter_label.setToolTip("Click to view issues in Log History")
        self.issue_counter_label.setObjectName("issue_counter_label")
        self.issue_counter_label.hide()
        self.issue_counter_label.installEventFilter(self)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setObjectName("status_state_label")
        self.status_label.setProperty("logLevel", "IDLE")
        
        # Auto hide progress bar
        self.progress_hide_timer: QTimer = QTimer()
        self.progress_hide_timer.setSingleShot(True)
        self.progress_hide_timer.setInterval(StatusBarConstants.HIDE_PROGRESS_BAR_INTERVAL)
        self.progress_hide_timer.timeout.connect(self._hide_progress_bar)
        
        # Add widgets to status bar
        self.addWidget(self.status_label, 0)
        self.addWidget(self.terminal, 1)
        self.addWidget(self.issue_counter_label)
        self.addWidget(self.history_button)

        self.source_label = QLabel("")
        self.source_label.setObjectName("source_label")
        self.source_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.source_label.installEventFilter(self)
        self._full_source_path: str = ""

        self.view_context_label = QLabel("")
        self.view_context_label.setObjectName("view_context_label")
        
        self.addPermanentWidget(self._create_separator())
        self.addPermanentWidget(self.progress_bar)
        self.addPermanentWidget(self.source_label)
        self.addPermanentWidget(self._create_separator())
        self.addPermanentWidget(self.view_context_label)
        self.addPermanentWidget(self._create_separator())
        self.addPermanentWidget(self.memory_bar)
        self.addPermanentWidget(self._create_separator())
        self.addPermanentWidget(self.stats_label)
    
    def _create_separator(self) -> QFrame:
        """Creates a vertical line to separate bar components"""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setProperty("styleClass", "status_separator")
        return line

    def set_logger(self, logger: Logger) -> None:
        """Set the logger instance"""
        self.logger = logger
    
    def log(self, message: str, level: LogLevel = LogLevel.INFO, action_type: Optional[str] = None, log_to_file: bool = True) -> None:
        """Log a message to the terminal"""
        if isinstance(level, str):
            try:
                level = LogLevel[level.upper()]
            except KeyError:
                level = LogLevel.INFO
        timestamp: str = datetime.now().strftime("%H:%M:%S")
        
        color: str = LogColor[level.name].value
        
        display_message: str = f"{message}"
        log_message: str = f"[{timestamp}] | {display_message}"
        html_log: str = f'<span style="color:#777777">[{timestamp}]</span> <span style="color:{color}">{display_message}</span>'

        # Store the log in the history
        self.log_history.append(html_log)
        if len(self.log_history) > StatusBarConstants.MAX_LOG_HISTORY:
            self.log_history.pop(0)
        
        if hasattr(self, "popup") and self.popup is not None and self.popup.isVisible():
            self.popup.append_live_log(html_log)
        
        status_text: str = "Ready"
        
        if level == LogLevel.WARNING:
            status_text = "Warning"
            self.warning_count += 1
            self._update_issue_counters()
        elif level == LogLevel.ERROR:
            status_text = "Error"
            self.error_count += 1
            self._update_issue_counters()
        
        self.status_label.setText(status_text)
        self.status_label.setProperty("logLevel", level.name)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        
        self.message_queue.append((log_message, level.name))
        if not self.is_typing:
            self._process_next_message()

        #log to file logger if available
        if log_to_file and self.logger:
            if level == LogLevel.INFO:
                self.logger.info(message)
            elif level == LogLevel.SUCCESS:
                self.logger.success(message)
            elif level == LogLevel.WARNING:
                self.logger.warning(message)
            elif level == LogLevel.ERROR:
                self.logger.error(message)
        else:
            if log_to_file:
                print(f"Warning: logger not present. Message not logged: {message}")
    
    def _process_next_message(self) -> None:
        """Process the next messsage in the queue to animation"""
        if not self.message_queue:
            self.is_typing = False
            self.typewriter_timer.stop()
            self.clear_timer.start()
            return
        
        self.is_typing = True
        self.clear_timer.stop()
        log_message, level_name = self.message_queue.pop(0)
        
        self.terminal.setProperty("logLevel", level_name)
        
        if level_name == "ERROR":
            self.terminal.setProperty("errorFlash", True)
            QTimer.singleShot(400, self._clear_error_flash)
        else:
            self.terminal.setProperty("errorFlash", False)
            
        self.terminal.style().unpolish(self.terminal)
        self.terminal.style().polish(self.terminal)
        
        self.terminal.setToolTip(f"Current log:\n{log_message}\n\nClick to view log history")
        self._start_typing(log_message)
    
    def _clear_error_flash(self) -> None:
        self.terminal.setProperty("errorFlash", False)
        self.terminal.style().unpolish(self.terminal)
        self.terminal.style().polish(self.terminal)
    
    def _reset_to_idle_state(self) -> None:
        """Visually reset the status bar to prevent stale messages"""
        self.terminal.setText("")
        self.terminal.setToolTip("Click to view log history")
        self.status_label.setText("Idle")
        self.status_label.setProperty("logLevel", "IDLE")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        
    def _start_typing(self, text: str) -> None:
        """Initialize the typewriter effect"""
        self.typewriter_timer.stop()
        self.current_anim_text = text
        self.current_anim_index = 0
        self.terminal.setText("")
        self.typewriter_timer.start()
    
    def _type_next_char(self) -> None:
        if self.current_anim_index < len(self.current_anim_text):
            chunk_size: int = max(1, len(self.current_anim_text) // StatusBarConstants.ANIMATION_CHUNK_DIVISOR)

            end_index: int = min(self.current_anim_index + chunk_size, len(self.current_anim_text))

            current_text: str = self.current_anim_text[:end_index]
            self.terminal.setText(current_text)
            self.current_anim_index = end_index
        else:
            self._process_next_message()
    
    def log_action(self, action: str, details: Optional[Dict[str, Any]] = None, level: LogLevel = LogLevel.SUCCESS) -> None:
        """log actions"""
        if isinstance(level, str):
            try:
                level = LogLevel[level.upper()]
            except KeyError:
                level = LogLevel.SUCCESS
                
        # message for statusbar
        status_message: str = action

        #detail message for log file
        detailed_message: str = action
        if details:
            detail_parts: List[str] = []
            for key, value in details.items():
                detail_parts.append(f"{key}={value}")
            detailed_message += f" | {', '.join(detail_parts)}"
        
        #show statusbarmsg 
        self.log(status_message, level, log_to_file=False)

        # log detailed
        if self.logger and details:
            if level == LogLevel.SUCCESS:
                self.logger.success(detailed_message)
            elif level == LogLevel.INFO:
                self.logger.info(detailed_message)
            elif level == LogLevel.WARNING:
                self.logger.warning(detailed_message)
            elif level == LogLevel.ERROR:
                self.logger.error(detailed_message)
    
    def eventFilter(self, source: Any, event: QEvent) -> bool:
        """Intercept mouse clicks on the terminal to open the history popup."""
        if event.type() == QEvent.Type.MouseButtonPress and hasattr(event, "button") and event.button() == Qt.MouseButton.LeftButton:
            if hasattr(self, "terminal") and source is self.terminal:
                self.show_log_history()
                return True
            if hasattr(self, "issue_counter_label") and source is self.issue_counter_label:
                self.show_log_history()
                return True
            if hasattr(self, "source_label") and source is self.source_label and self._full_source_path:
                clipboard = QApplication.clipboard()
                if clipboard:
                    clipboard.setText(self._full_source_path)
                    
                    original_text = self.source_label.text()
                    self.source_label.setText("Copied!")
                    QTimer.singleShot(1500, lambda: self.source_label.setText(original_text))
        
        return super().eventFilter(source, event)

    def update_data_stats(self, df: Any) -> None:
        """Update the status bar widget to show dataframe dimensions"""
        if df is not None and hasattr(df, "shape") and len(df.shape) == 2:
            rows: int = df.shape[0]
            cols: int = df.shape[1]
            self.stats_label.setText(f"Rows: {rows:,} | Columns: {cols}")
            self.memory_bar.show()
        else:
            self.stats_label.setText("No data")
            self.memory_bar.hide()
    
    def update_memory_usage(self, current_bytes: int, max_bytes: int) -> None:
        """
        Updates the memory progress bar 
        """
        if max_bytes <= 0:
            return
        
        percentage: float = (current_bytes / max_bytes) * 100
        self.memory_bar.setValue(int(percentage))
        
        current_mb: float = current_bytes / (1024 * 1024)
        max_mb: float = max_bytes / (1024 * 1024)
        
        tooltip_text: str = f"Memory Usage: {current_mb:.1f} MB / {max_mb:.1f} MB ({percentage:.1f}%)"
        
        usage_level: str = "normal"
        if percentage >= 90:
            usage_level = "critical"
            tooltip_text += "\nWarning: Buffer almost full. Oldest data states will be dropped."
        elif percentage >= 75:
            usage_level = "warning"
        
        self.memory_bar.setToolTip(tooltip_text)
        
        if self.memory_bar.property("usageLevel") != usage_level:
            self.memory_bar.setProperty("usageLevel", usage_level)
            self.memory_bar.style().unpolish(self.memory_bar)
            self.memory_bar.style().polish(self.memory_bar)
            
            if usage_level == "critical":
                self.log("Memory usage is almost full. Older actions may be lost...", LogLevel.WARNING)

    
    def _update_issue_counters(self) -> None:
        """updates the issue trackers"""
        if self.error_count == 0 and self.warning_count == 0:
            self.issue_counter_label.hide()
            return
        
        parts = []
        if self.error_count > 0:
            parts.append(f"<span style='color: #ff5555;'>\u26CC {self.error_count}</span>")
        if self.warning_count > 0:
            parts.append(f"<span style='color: #ffaa00;'>\u26A0 {self.warning_count}</span>")
        
        self.issue_counter_label.setText(" ".join(parts))
        self.issue_counter_label.show()
    
    def clear_issue_counters(self) -> None:
        """Reset counters"""
        self.error_count = 0
        self.warning_count = 0
        self._update_issue_counters()
    
    def _hide_progress_bar(self) -> None:
        """ hide the progress bar after completion."""
        self.progress_bar.hide()
        self.progress_bar.setValue(0)
        
    def show_progress(self, show: bool = True, indeterminate: bool = False) -> None:
        """toggles the progress bar visibility"""
        if not show:
            self.progress_hide_timer.stop()
            self.progress_bar.hide()
        
        self.progress_hide_timer.stop()
        
        if indeterminate:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
        
        self.progress_bar.show()
    
    def set_progress(self, value: int) -> None:
        """Set the progress bar value and trigger auto-hide at 100%."""
        self.progress_bar.setValue(value)
        
        if value >= self.progress_bar.maximum():
            self.progress_hide_timer.start()
        else:
            self.progress_hide_timer.stop()
            if self.progress_bar.isHidden():
                self.progress_bar.show()
        
    def show_log_history(self) -> None:
        """Open a popup window showing all session logs"""
        if hasattr(self, "popup") and self.popup is not None and self.popup.isVisible():
            self.popup.close()
            return
        
        self.popup = LogHistoryPopup(self.log_history, self)

        button_position = self.history_button.mapToGlobal(QPoint(0, 0))
        button_width = self.history_button.width()
        button_height = self.history_button.height()

        popup_width = self.popup.width()
        popup_height = self.popup.height()

        screen = self.history_button.screen()
        if not screen:
            screen = QApplication.primaryScreen()
        screen_geom = screen.availableGeometry()

        x = button_position.x()

        if x + popup_width > screen_geom.right():
            x = (button_position.x() + button_width) - popup_width

            if x < screen_geom.left():
                x = screen_geom.left()
        
        y = button_position.y() - popup_height
        if y < screen_geom.top():
            y = button_position.y() + button_height
        
        self.popup.show_with_animation(QPoint(x, y))
    
    def _show_terminal_context_menu(self, position: QPoint) -> None:
        """Right-click context menu on the terminal bar"""
        menu = QMenu(self)
        menu.setObjectName("terminal_context_menu")
        
        open_action = QAction("Open Log History", self)
        open_action.triggered.connect(self.show_log_history)
        
        copy_action = QAction("Copy latest log", self)
        copy_action.triggered.connect(self._copy_latest_log)
        if not self.log_history:
            copy_action.setEnabled(False)
        
        clear_action = QAction("Clear All logs", self)
        clear_action.triggered.connect(lambda: self.log_history.clear() or self.clear_issue_counters() or self._reset_to_idle_state())
        if not self.log_history:
            clear_action.setEnabled(False)
        
        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(copy_action)
        menu.addAction(clear_action)
        
        menu.exec(self.terminal.mapToGlobal(position))
    
    def _copy_latest_log(self) -> None:
        """method to copy the most recent log to clipboard"""
        if self.log_history:
            latest_html = self.log_history[-1]
            import re
            text_stripped_html = re.sub('<[^<]+>', '', latest_html)
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(text_stripped_html)

    def set_data_source(self, source_text: str) -> None:
        """Update the data source label"""
        if source_text:
            self._full_source_path = source_text
            metrics = self.source_label.fontMetrics()
            full_text = f"Source: {source_text}"
            elided_text = metrics.elidedText(full_text, Qt.TextElideMode.ElideMiddle, 250)
            
            self.source_label.setText(elided_text)
            self.source_label.setToolTip(f"{full_text}\n\nClick to copy full path")
            self.source_label.show()
        else:
            self.source_label.clear()
            self.source_label.hide()
    
    def set_view_context(self, context_text: str, context_type: str = "subset") -> None:
        """update the view context label to match current viewing"""
        if not context_text or context_type == "normal":
            self.view_context_label.clear()
            self.view_context_label.hide()
            return
        
        metrics = self.view_context_label.fontMetrics()
        elided_text = metrics.elidedText(context_text, Qt.TextElideMode.ElideRight, 200)
        
        self.view_context_label.setText(elided_text)
        self.view_context_label.setToolTip(f"Context: {context_text}")
        self.view_context_label.show()

        # Colors
        self.view_context_label.setProperty("contextType", context_type)
        self.view_context_label.style().unpolish(self.view_context_label)
        self.view_context_label.style().polish(self.view_context_label)