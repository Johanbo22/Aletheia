import sys
import keyword
import builtins
import pydoc
import re
import code
import traceback
import pandas as pd
import numpy as np
from typing import Any, Callable, Dict, List

from PyQt6.QtCore import Qt, QEvent, QSettings, QStringListModel
from PyQt6.QtGui import QTextCursor, QColor, QFontDatabase, QFont, QKeyEvent, QKeySequence, QGuiApplication
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPlainTextEdit, QCompleter

from core.data_handler import DataHandler
from resources.version import APPLICATION_NAME
from ui.dialogs.ScriptEditorDialog import StreamRedirector
from ui.PythonHighlighter import PythonHighlighter

class ConsoleDialog(QDialog):
    """
    A Python console intended to allow direct DataFrame manipulation
    """
    def __init__(self, data_handler: DataHandler, sync_callback: Callable[[], None], parent: Any = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Python Console")
        self.resize(850, 500)
        self.setModal(False)
        
        self.data_handler: DataHandler = data_handler
        self.sync_callback: Callable[[], None] = sync_callback
        
        self.console_history: List[str] = []
        self.console_history_idx: int = 0
        
        self.console_namespace: Dict[str, Any] = {
            "__builtins__": __builtins__,
            "df": self.data_handler.df,
            "dh": self.data_handler,
            "pd": pd,
            "np": np,
            "help": self._custom_help
        }
        self._is_executing: bool = False
        self.multiline_buffer: List[str] = []
        self._input_start_position: int = 0
        
        self._init_ui()
        self._setup_autocompletion()
        self._setup_streams()
        self._read_settings()
        self._print_welcome_message()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        self.console_output = QPlainTextEdit()
        self.console_output.setObjectName("interactive_console_output")
        self.console_output.setReadOnly(False)
        self._original_key_press = self.console_output.keyPressEvent
        self.console_output.keyPressEvent = self._custom_key_press_event
        
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.console_output.setFont(font)
        self.highlighter: PythonHighlighter = PythonHighlighter(self.console_output.document())
        
        layout.addWidget(self.console_output)
        self._setup_autocompletion()
    
    def _setup_streams(self) -> None:
        self.original_stdout: Any = sys.stdout
        self.original_stderr: Any = sys.stderr

        self.stdout_redirector = StreamRedirector(self.console_output, self.original_stdout, color="#f8f8f2")
        self.stderr_redirector = StreamRedirector(self.console_output, self.original_stderr, color="#ff5555")

        sys.stdout = self.stdout_redirector
        sys.stderr = self.stderr_redirector
    
    def _print_welcome_message(self) -> None:
        self.console_output.blockSignals(True)
        print(f"{APPLICATION_NAME} Python Console")
        print("----------------------------------")
        print("Available variables:")
        print("  df   : Current pandas DataFrame")
        print("  dh   : DataHandler instance")
        print("  pd   : pandas library")
        print("  np   : numpy library")
        print("  help : Type help(object) for documentation (e.g. help(df.dropna))")
        print("\nType your Python commands below. Press Enter to execute.")
        sys.stdout.flush()
        self.console_output.blockSignals(False)
        self._append_console_prompt()
    
    def _read_settings(self) -> None:
        """Restore window geometry from settings."""
        settings: QSettings = QSettings(f"{APPLICATION_NAME}", "InteractiveConsole")
        saved_geometry = settings.value("geometry")
        if saved_geometry:
            self.restoreGeometry(saved_geometry)

    def _write_settings(self) -> None:
        """Save current window geometry."""
        settings: QSettings = QSettings(f"{APPLICATION_NAME}", "InteractiveConsole")
        settings.setValue("geometry", self.saveGeometry())
    
    def closeEvent(self, event: QEvent) -> None:
        self._write_settings()
        if hasattr(self, 'completer') and self.completer.popup():
            self.completer.popup().hide()
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        super().closeEvent(event)
    
    def _custom_key_press_event(self, event: QEvent | QKeyEvent) -> None:
        if hasattr(self, 'completer') and self.completer.popup() and self.completer.popup().isVisible():
            if event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                completion = self.completer.currentCompletion()
                if completion:
                    self._insert_completion(completion)
                self.completer.popup().hide()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Escape:
                self.completer.popup().hide()
                event.accept()
                return
            elif event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                self.completer.popup().keyPressEvent(event)
                event.accept()
                return
            elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.completer.popup().hide()

        cursor: QTextCursor = self.console_output.textCursor()

        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_L:
                self._clear_console()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_C:
                if not self.console_output.textCursor().hasSelection():
                    self._cancel_current_line()
                    event.accept()
                    return
            elif event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self.console_output.zoomIn(1)
                event.accept()
                return
            elif event.key() in (Qt.Key.Key_Minus):
                self.console_output.zoomOut(1)
                event.accept()
                return
        if event.matches(QKeySequence.StandardKey.Paste):
            self._handle_paste_event()
            event.accept()
            return

        if event.key() == Qt.Key.Key_Backspace:
            if cursor.position() <= self._input_start_position:
              event.accept()
              return
        elif event.key() == Qt.Key.Key_Left:
            if cursor.position() <= self._input_start_position:
                event.accept()
                return
        elif event.key() == Qt.Key.Key_Home:
            move_mode = QTextCursor.MoveMode.KeepAnchor if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else QTextCursor.MoveMode.MoveAnchor
            cursor.setPosition(self._input_start_position, move_mode)
            self.console_output.setTextCursor(cursor)
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Up:
            self._navigate_history(-1)
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Down:
            self._navigate_history(1)
            event.accept()
            return
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._execute_current_line()
            event.accept()
            return

        if event.text() and cursor.position() < self._input_start_position:
            if not (event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier)):
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.console_output.setTextCursor(cursor)

        self._original_key_press(event)

    def _navigate_history(self, direction: int) -> None:
        if not self.console_history:
            return
        
        self.console_history_idx += direction
        self.console_history_idx = max(0, min(self.console_history_idx, len(self.console_history)))
        
        if self.console_history_idx < len(self.console_history):
            self._replace_console_input(self.console_history[self.console_history_idx])
        else:
            self._replace_console_input("")
    
    def _clear_console(self) -> None:
        self.console_output.blockSignals(True)
        self.console_output.clear()
        self.console_output.blockSignals(False)
        self._print_welcome_message()
    
    def _cancel_current_line(self) -> None:
        self.multiline_buffer.clear()
        
        self.console_output.blockSignals(True)
        cursor: QTextCursor = self.console_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.console_output.setTextCursor(cursor)
        
        fmt = cursor.charFormat()
        fmt.setForeground(QColor("#ff5555"))
        cursor.setCharFormat(fmt)
        cursor.insertText("^C\n")
        
        self.console_output.blockSignals(False)
        self._append_console_prompt()

    def _handle_paste_event(self) -> None:
        """Processes pasted text and evaluating as multiline"""
        clipboard = QGuiApplication.clipboard()
        text: str = clipboard.text()

        if not text:
            return

        cursor: QTextCursor = self.console_output.textCursor()
        if cursor.position() < self._input_start_position:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.console_output.setTextCursor(cursor)

        lines = text.splitlines()
        for i, line in enumerate(lines):
            self.console_output.insertPlainText(line)
            if i < len(lines) - 1:
                self._execute_current_line()
        
    def _execute_current_line(self) -> None:
        self._is_executing = True
        
        try:
            cursor: QTextCursor = self.console_output.textCursor()
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)

            raw_line: str = cursor.selectedText()
            
            if raw_line.startswith(">>> "): command = raw_line[4:]
            elif raw_line.startswith("... "): command = raw_line[4:]
            elif raw_line.startswith(">>>"): command = raw_line[3:]
            elif raw_line.startswith("..."): command = raw_line[3:]
            else: command = raw_line

            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.console_output.setTextCursor(cursor)
            
            if command in ("clear", "clear()") and not self.multiline_buffer:
                self._clear_console()
                return
            
            self.console_output.blockSignals(True)
            print("")
            sys.stdout.flush()
            self.console_output.blockSignals(False)

            self.multiline_buffer.append(command)
            source_code: str = "\n".join(self.multiline_buffer)

            try:
                is_complete = code.compile_command(source_code)
                
                if is_complete is None and command != "":
                    self._append_multiline_prompt()
                    return
                    
            except (SyntaxError, OverflowError, ValueError):
                pass

            if source_code.strip():
                self._add_to_history(source_code.strip())
                self._run_command(source_code)

            self.multiline_buffer.clear()
            self._append_console_prompt()
            
        finally:
            self._is_executing = False
    
    def _append_multiline_prompt(self) -> None:
        self.console_output.blockSignals(True)
        cursor: QTextCursor = self.console_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        fmt = cursor.charFormat()
        fmt.setForeground(QColor("#f1fa8c"))
        font = fmt.font()
        font.setItalic(False)
        font.setBold(False)
        fmt.setFont(font)
        cursor.setCharFormat(fmt)
        cursor.insertText("... ")

        fmt.setForeground(QColor("#f8f8f2"))
        font.setBold(False)
        fmt.setFont(font)
        cursor.setCharFormat(fmt)
        
        self.console_output.setTextCursor(cursor)
        self._input_start_position = self.console_output.textCursor().position()
        self.console_output.setCurrentCharFormat(fmt)
        self.console_output.blockSignals(False)
        
    def _run_command(self, command: str) -> None:
        if self.data_handler.df is not self.console_namespace.get("df"):
            self.console_namespace["df"] = self.data_handler.df

        try:
            try:
                result: Any = eval(command, self.console_namespace)
                if result is not None:
                    print(result)
                    
                    if isinstance(result, pd.DataFrame) and command.startswith("df.") and "inplace" not in command:
                        self._print_tip(f"Tip: This returned a copy. To apply it, use assignment: df = {command}")
                        
            except SyntaxError:
                exec(command, self.console_namespace)

            new_df = self.console_namespace.get("df")
            if new_df is not self.data_handler.df:
                self.data_handler._save_state()
                self.data_handler.df = new_df
                
                self.data_handler.operation_log.append({
                    "type": "console_command",
                    "command": command
                })
                self.sync_callback()
                self._update_completer_model()

        except Exception as execution_error:
            error_details = "".join(traceback.format_exception_only(type(execution_error), execution_error)).strip()
            self._print_error(error_details)
    
    def _print_tip(self, tip_message: str) -> None:
        """Print a helpful tip message in a visible color."""
        self.console_output.blockSignals(True)
        cursor: QTextCursor = self.console_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = cursor.charFormat()
        fmt.setForeground(QColor("#8be9fd"))
        fmt.setFontItalic(True)
        cursor.setCharFormat(fmt)
        cursor.insertText(f"{tip_message}\n")
        
        self.console_output.setTextCursor(cursor)
        self.console_output.ensureCursorVisible()
        self.console_output.blockSignals(False)
    
    def _setup_autocompletion(self) -> None:
        self.completer: QCompleter = QCompleter(self)
        self.completer_model: QStringListModel = QStringListModel(self)
        self.completer.setModel(self.completer_model)
        self.completer.setWidget(self.console_output)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.popup().setObjectName("interactive_console_popup")
        
        self.completer.activated.connect(self._insert_completion)

        self.console_output.textChanged.connect(self._handle_text_changed)
        self._update_completer_model()
    
    def _update_completer_model(self) -> None:
        """
        Method to aggregate attributes, keywords etc to
        populate the completer model
        """
        completion_words: set[str] = set(keyword.kwlist + dir(builtins))
        completion_words.update(self.console_namespace.keys())
        
        completion_words.update(attr for attr in dir(pd) if not attr.startswith("_"))
        completion_words.update(attr for attr in dir(np) if not attr.startswith("_"))
        completion_words.update(attr for attr in dir(self.data_handler) if not attr.startswith("_"))

        if self.data_handler.df is not None:
            completion_words.update(attr for attr in dir(self.data_handler.df) if not attr.startswith("_"))
            completion_words.update(str(column) for column in self.data_handler.df.columns)
        
        self.completer_model.setStringList(sorted(list(completion_words)))
    
    def _handle_text_changed(self) -> None:
        if self._is_executing:
            return

        cursor: QTextCursor = self.console_output.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        completion_prefix: str = cursor.selectedText()

        if completion_prefix != self.completer.completionPrefix():
            self.completer.setCompletionPrefix(completion_prefix)
            self.completer.popup().setCurrentIndex(self.completer.completionModel().index(0, 0))
            
        if len(completion_prefix) < 2 or ">>>" in completion_prefix:
            if self.completer.popup() and self.completer.popup().isVisible():
                self.completer.popup().hide()
            return

        if self.completer.currentCompletion() == completion_prefix:
            if self.completer.popup() and self.completer.popup().isVisible():
                self.completer.popup().hide()
            return

        cursor_rect = self.console_output.cursorRect()
        
        scroll_width: int = self.completer.popup().verticalScrollBar().sizeHint().width()
        popup_width: int = max(300, self.completer.popup().sizeHintForColumn(0) + scroll_width + 20)
        cursor_rect.setWidth(popup_width)
        
        cursor_rect.translate(0, 6)
        
        self.completer.complete(cursor_rect)
    
    def _insert_completion(self, completion: str) -> None:
        if self.completer.widget() is not self.console_output:
            return

        self.console_output.blockSignals(True)
        cursor: QTextCursor = self.console_output.textCursor()
        prefix_length: int = len(self.completer.completionPrefix())
        
        cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, prefix_length)
        
        cursor.insertText(completion)
        self.console_output.setTextCursor(cursor)
        self.console_output.blockSignals(False)
    
    def _add_to_history(self, command: str) -> None:
        if not self.console_history or self.console_history[-1] != command:
            self.console_history.append(command)
            if len(self.console_history) > 1000:
                self.console_history.pop(0)
        self.console_history_idx = len(self.console_history)
    
    def _replace_console_input(self, new_text: str) -> None:
        self.console_output.blockSignals(True)
        cursor: QTextCursor = self.console_output.textCursor()
        cursor.setPosition(self._input_start_position, QTextCursor.MoveMode.MoveAnchor)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

        fmt = cursor.charFormat()
        fmt.setForeground(QColor("#f8f8f2"))
        font = fmt.font()
        font.setItalic(False)
        font.setBold(False)
        fmt.setFont(font)
        cursor.setCharFormat(fmt)

        cursor.insertText(new_text)
        self.console_output.setTextCursor(cursor)
        self.console_output.setCurrentCharFormat(fmt)
        self.console_output.blockSignals(False)
    
    def _print_error(self, error_message: str) -> None:
        self.console_output.blockSignals(True)
        cursor: QTextCursor = self.console_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = cursor.charFormat()
        fmt.setForeground(QColor("#ff5555"))
        cursor.setCharFormat(fmt)
        cursor.insertText(f"{error_message}\n")
        
        self.console_output.setTextCursor(cursor)
        self.console_output.ensureCursorVisible()
        self.console_output.blockSignals(False)
    
    def _append_console_prompt(self) -> None:
        self.console_output.blockSignals(True)
        cursor: QTextCursor = self.console_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        fmt = cursor.charFormat()
        fmt.setForeground(QColor("#f8f8f2"))
        font = fmt.font()
        font.setItalic(False)
        font.setBold(False)
        fmt.setFont(font)
        cursor.setCharFormat(fmt)
        cursor.insertText(">>> ")

        fmt.setForeground(QColor("#f8f8f2"))
        font.setBold(False)
        fmt.setFont(font)
        cursor.setCharFormat(fmt)
        
        self.console_output.setTextCursor(cursor)
        self._input_start_position = self.console_output.textCursor().position()
        self.console_output.setCurrentCharFormat(fmt)
        self.console_output.blockSignals(False)
    
    def _custom_help(self, request: Any = None) -> None:
        if request is None:
            print(f"Welcome to {APPLICATION_NAME} Console Help!\nType help(object) to get help about a specific object or method.")
            return
        
        try:
            self.console_output.blockSignals(True)
            
            doc_string: str = pydoc.render_doc(request, "Help on %s:")
            encoded_doc_string: str = re.sub(r'.\x08', '', doc_string)
            print(encoded_doc_string)
            sys.stdout.flush()
        
        except Exception as help_error:
            self._print_error(f"Failed to fetch documentation: {help_error}")
        finally:
            self.console_output.blockSignals(False)