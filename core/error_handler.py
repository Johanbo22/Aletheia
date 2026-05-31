"""
Global error handling module for Aletheia

Provides mechanisms to catch unhandled exceptions across all threads
generates a detailed crash report, saves it to disk and transmits to a
remote server if allowed.
"""
import sys
import platform
import traceback
import threading
from datetime import datetime
from pathlib import Path
from typing import Type, Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMessageBox
from mypyc.crash import crash_report

from core.logger import Logger
from resources.version import APPLICATION_NAME, APPLICATION_VERSION

class _ExceptionSignaler(QObject):
    """Internal signaler to route exception dialogs to the main GUI thread"""
    show_error_dialog = pyqtSignal(str, str)

class GlobalErrorHandler:
    """
    Manages unhandled application exceptions, crash reporting, and user notifications
    """

    def __init__(self, crash_report_dir: Optional[Path] = None) -> None:
        """
        :param crash_report_dir: Directory to store local crash reports. Defaults to 'crash_reports'
        """
        self.crash_dir: Path = crash_report_dir or Path("crash_reports")
        self.crash_dir.mkdir(parents=True, exist_ok=True)

        self._signaler = _ExceptionSignaler()
        self._signaler.show_error_dialog.connect(self._display_error_dialog)

    def setup_hooks(self) -> None:
        """
        Hook into system exception handlers for both main and worker threads
        """
        sys.excepthook = self._handle_main_thread_exception
        threading.excepthook = self._handle_worker_thread_exception

    def _handle_main_thread_exception( self,
            exc_type: Type[BaseException],
            exc_value: BaseException,
            exc_traceback: Any) -> None:
        """Handle exceptions occurring in the primary thread"""
        self._process_exception(exc_type, exc_value, exc_traceback)

    def _handle_worker_thread_exception(self, args: threading.ExceptHookArgs) -> None:
        """Handle exceptions occurring in the worker threads"""
        self._process_exception(args.exc_type, args.exc_value, args.exc_traceback)

    def _process_exception(self, exc_type: Any, exc_value: Any, exc_traceback: Any) -> None:
        """
        Processes an unhandled exception

        :param exc_type: The type of the exception
        :param exc_value: The exception instance
        :param exc_traceback: The traceback object
        """
        # Do not intercept deliberate execution interruptions
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        traceback_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

        try:
            Logger.get_instance().error(f"FATAL UNHANDLED EXCEPTION: {exc_type.__name__}: {exc_value}")
        except Exception:
            pass

        report_path = self._save_crash_report(traceback_str)

        self._signaler.show_error_dialog.emit(traceback_str, str(report_path))

    def _save_crash_report(self, traceback_str: str) -> Path:
        """
        Write the crash details to a local text file

        :param traceback_str: The formatted exception traceback
        :return: The Path object pointing to the generated crash report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"crash_report_{timestamp}.txt"
        report_path = self.crash_dir / filename

        system_info = (
            f"Application: {APPLICATION_NAME} v{APPLICATION_VERSION}\n"
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"OS: {platform.system()} {platform.release()} ({platform.version()})\n"
            f"Python Version: {platform.python_version()}\n"
            f"Platform Architecture: {platform.machine()}\n"
            f"{'-'*80}\n"
        )
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(system_info)
                f.write(traceback_str)
        except OSError as e:
            print(f"Failed to write crash report to disk: {e}", file=sys.stderr)

        return report_path

    def _display_error_dialog(self, traceback_str: str, report_path: str) -> None:
        """
        Display a critical error dialog to the user via the main GUI thread

        :param traceback_str: The raw traceback to display in the details section
        :param report_path: The path where the local crash report was saved
        """
        app = QApplication.instance()
        if app is None:
            print(traceback_str, file=sys.stderr)
            sys.exit(1)

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(f"{APPLICATION_NAME} - Critical Error")
        msg_box.setText("An unexpected critical error has occurred and the application must close")
        msg_box.setInformativeText(f"A detailed crash report has been saved to:\n{report_path}")
        msg_box.setDetailedText(traceback_str)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

        msg_box.setObjectName("CrashReporter")
        msg_box.exec()

        sys.exit(1)