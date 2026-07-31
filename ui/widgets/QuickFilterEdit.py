from typing import List

from PyQt6.QtCore import QRect, QStringListModel, Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QResizeEvent, QTextCursor
from PyQt6.QtWidgets import QCompleter, QPlainTextEdit, QStyle, QToolButton

from ui.FilterSyntaxHighlighter import FilterSyntaxHighlighter

class QuickFilterEdit(QPlainTextEdit):
    """
    A QPlainTextEdit that is a one line widget to support a On-the-fly filter system for plotting

    This system allows for a filtering process that does not alter the dataset. The system provides a filter mask that is then seen by the PlotEngine to render the plot based on that filter.

    A FilterSyntaxHighlighter is attached to give more visual hints for the text being typed.
    """

    returnPressed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("quickFilterEdit")
        self.highlighter = FilterSyntaxHighlighter(self.document())

        # setyp to be one line
        self.setFixedHeight(34)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabChangesFocus(True)
        self.setPlaceholderText("Enter filter expression...")

        # Autocompleter
        self.completer = QCompleter(self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.activated.connect(self.insert_completion)
        # keywords
        self.base_keywords: List[str] = [
            "mean", "sum", "min", "max", "count", "std", "var", "median", "and", "or", "not", "in", "is", "NaN", "None",
            "True", "False", "abs", "round", "len", "str", "int", "float"
        ]
        self.current_keywords: List[str] = list(self.base_keywords)
        self.update_completer_model()

        # Setyp for clear button
        self.clear_button = QToolButton(self)
        self.clear_button.setObjectName("quickFilterClearButton")
        self.clear_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.setFixedSize(16, 16)
        self.clear_button.clicked.connect(self.clear)
        self.clear_button.hide()

        self.setProperty("hasText", False)
        self.textChanged.connect(self._on_text_changed)

    def set_columns(self, columns: List[str]) -> None:
        self.highlighter.set_columns(columns)
        self.current_keywords = sorted(list(set(self.base_keywords + columns)))
        self.update_completer_model()

    def update_completer_model(self) -> None:
        model = QStringListModel(self.current_keywords, self.completer)
        self.completer.setModel(model)

    def insert_completion(self, completion: str) -> None:
        tc = self.textCursor()
        extra = len(completion) - len(self.completer.completionPrefix())
        tc.movePosition(QTextCursor.MoveOperation.Left)
        tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)

    def text_under_cursor(self) -> str:
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        return tc.selectedText()

    def _on_text_changed(self):
        has_text = bool(self.toPlainText().strip())
        self.clear_button.setVisible(has_text)

        if self.property("hasText") != has_text:
            self.setProperty("hasText", has_text)
            self.style().unpolish(self)
            self.style().polish(self)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        clear_button_size_hint = self.clear_button.sizeHint()
        frame_width = self.frameWidth()
        x = self.width() - clear_button_size_hint.width() - frame_width - 6
        y = (self.height() - clear_button_size_hint.height()) // 2
        self.clear_button.move(x, y)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.completer and self.completer.popup().isVisible():
            if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Escape,
                               Qt.Key.Key_Tab, Qt.Key.Key_Backtab,
                               Qt.Key.Key_Up, Qt.Key.Key_Down):
                event.ignore()
                return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.returnPressed.emit()
            event.ignore()
            return

        is_shortcut = (event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Space)

        if not self.completer or not self.completer.popup().isVisible():
            super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

        ctrl_or_shift = event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
        if not is_shortcut and (ctrl_or_shift or not self.toPlainText()):
            return

        completion_prefix = self.text_under_cursor()

        if not is_shortcut and (len(completion_prefix) < 1):
            self.completer.popup().hide()
            return

        if completion_prefix != self.completer.completionPrefix():
            self.completer.setCompletionPrefix(completion_prefix)
            self.completer.popup().setCurrentIndex(self.completer.completionModel().index(0, 0))

        cursor_rect = self.cursorRect()
        x_pos = cursor_rect.x() + self.viewport().x()

        scroll_width = self.completer.popup().verticalScrollBar().sizeHint().width()
        popup_width = self.completer.popup().sizeHintForColumn(0) + scroll_width + 15

        target_rect = QRect(x_pos, 0, max(popup_width, 120), self.height())
        self.completer.complete(target_rect)

    def text(self) -> None:
        return self.toPlainText()

    def setText(self, text) -> None:
        self.setPlainText(text)

    def clear(self) -> None:
        self.setPlainText("")
        self.returnPressed.emit()
