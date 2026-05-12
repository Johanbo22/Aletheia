import ast
from dataclasses import dataclass

from ui.LineNumberArea import LineNumberArea

from PyQt6.QtCore import QRect, Qt, QStringListModel, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QTextCursor, QTextFormat, QAction, QKeySequence, QKeyEvent, QWheelEvent, QTextCharFormat, QTextBlock, QPaintEvent, QMouseEvent, QTextOption
from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit, QCompleter, QMessageBox, QInputDialog, QToolTip
import traceback

@dataclass
class LintError:
    line_number: int
    offset: int
    message: str
    
class LintWorker(QThread):
    """Background thread for executing AST parsing"""
    lint_complete = pyqtSignal(list)
    
    def __init__(self, code_text: str) -> None:
        super().__init__()
        self.code_text: str = code_text
    
    def run(self) -> None:
        errors: list[LintError] = []
        try:
            ast.parse(self.code_text)
        except SyntaxError as syntax_err:
            if syntax_err.lineno is not None:
                offset: int = syntax_err.offset if syntax_err.offset is not None else 1
                errors.append(LintError(syntax_err.lineno, offset, str(syntax_err.msg)))
        except Exception:
            pass
        
        self.lint_complete.emit(errors)

class CodeEditor(QPlainTextEdit):
    """Custom texedit widget that serves as a code editor"""
    
    TAB_SPACES: str = "    "
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.lineNumberArea: LineNumberArea = LineNumberArea(self)

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()
        
        # Initialize the autocompleter
        self.completer: QCompleter | None = None
        self.initCompleter()
        
        # Initialize find and replace
        self.find_replace_dialog = None
        find_action = QAction("Find/Replace", self)
        find_action.setShortcut(QKeySequence("Ctrl+F"))
        find_action.triggered.connect(self.showFindReplaceDialog)
        self.addAction(find_action)
        
        # Comment toggle
        comment_action = QAction("Toggle Comment", self)
        comment_action.setShortcut(QKeySequence("Ctrl+K"))
        comment_action.triggered.connect(self.toggleComment)
        self.addAction(comment_action)
        
        # Line duplication
        duplicate_lines_action = QAction("Duplicate Lines", self)
        duplicate_lines_action.setShortcut(QKeySequence("Ctrl+D"))
        duplicate_lines_action.triggered.connect(self.duplicateLine)
        self.addAction(duplicate_lines_action)

        # Delete line
        delete_line_action = QAction("Delete Line", self)
        delete_line_action.setShortcut(QKeySequence("Ctrl+Shift+K"))
        delete_line_action.triggered.connect(self.deleteLine)
        self.addAction(delete_line_action)

        # Move lin up
        move_up_action = QAction("Move Line Up", self)
        move_up_action.setShortcut(QKeySequence("Alt+Up"))
        move_up_action.triggered.connect(self.moveLinesUp)
        self.addAction(move_up_action)

        # Move line down
        move_down_action = QAction("Move Line Down", self)
        move_down_action.setShortcut(QKeySequence("Alt+Down"))
        move_down_action.triggered.connect(self.moveLinesDown)
        self.addAction(move_down_action)
        
        # Go to line
        goto_action = QAction("Go To Line", self)
        goto_action.setShortcut(QKeySequence("Ctrl+G"))
        goto_action.triggered.connect(self.showGoToLineDialog)
        self.addAction(goto_action)

        # Word Wrap Toggle
        wrap_action = QAction("Toggle Word Wrap", self)
        wrap_action.setShortcut(QKeySequence("Alt+Z"))
        wrap_action.triggered.connect(self.toggleWordWrap)
        self.addAction(wrap_action)

        # Whitespace toggle
        whitespace_action = QAction("Toggle Whitespace", self)
        whitespace_action.setShortcut(QKeySequence("Alt+W"))
        whitespace_action.triggered.connect(self.toggleWhitespaceVisibility)
        self.addAction(whitespace_action)
        
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._folded_cursors: list[QTextCursor] = []
        
        # Linting state
        self._lint_selections: list[QTextEdit.ExtraSelection] = []
        self._lint_error_map: dict[int, str] = {}
        self._active_lint_worker: LintWorker | None = None
        
        self._lint_timer = QTimer(self)
        self._lint_timer.setSingleShot(True)
        self._lint_timer.setInterval(500)
        self._lint_timer.timeout.connect(self._startLinting)
        
        self.setMouseTracking(True)
        
        self.textChanged.connect(self._scheduleFoldUpdate)
        self.textChanged.connect(self._lint_timer.start)

        #font
        font = QFont("Consolas", 12)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(' '))

    def lineNumberAreaWidth(self) -> int:
        digits = 1
        max_value: int = max(1, self.blockCount())
        while max_value >= 10:
            max_value //= 10
            digits += 1

        space: int = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space + 15

    def updateLineNumberAreaWidth(self, _) -> None:
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy) -> None:
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr: QRect = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#2b2b2b"))

        block: QTextBlock = self.firstVisibleBlock()
        block_number: int = block.blockNumber()
        top: int = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom: int = top + round(self.blockBoundingRect(block).height())

        font_metrics = self.fontMetrics()
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number: str = str(block_number + 1)
                
                painter.setPen(QColor("#858585"))
                painter.drawText(
                    0, top, self.lineNumberArea.width() - 15, font_metrics.height(),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, number
                )
                
                if self.isFoldable(block):
                    is_folded: bool = self._isBlockFolded(block)
                    
                    margin_right: int = self.lineNumberArea.width()
                    box_size: int = 9
                    box_x: int = margin_right - 12
                    box_y: int = top + (font_metrics.height() - box_size) // 2
                    
                    painter.setPen(QColor("#A0A0A0"))
                    painter.drawRect(box_x, box_y, box_size, box_size)
                    painter.drawLine(box_x + 2, box_y + box_size // 2, box_x + box_size - 2, box_y + box_size // 2)
                    if is_folded:
                        painter.drawLine(box_x + box_size // 2, box_y + 2, box_x + box_size // 2, box_y + box_size - 2)

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1
    
    def lineNumberAreaMousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse clicks on the line number area for code folding interactions."""
        block: QTextBlock = self.firstVisibleBlock()
        top: int = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom: int = top + round(self.blockBoundingRect(block).height())
        
        while block.isValid():
            if block.isVisible():
                click_y: float = event.position().y()
                click_x: float = event.position().x()
                
                if top <= click_y <= bottom:
                    if click_x >= self.lineNumberArea.width() - 15:
                        if self.isFoldable(block):
                            self.toggleFold(block)
                    break
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
    
    def isFoldable(self, block: QTextBlock) -> bool:
        """Determines if a text block is a foldable parent based on indentation rules"""
        text: str = block.text()
        if not text.strip():
            return False
        
        current_indent: int = len(text) - len(text.lstrip())
        next_block: QTextBlock = block.next()
        
        # Skip empty lines
        while next_block.isValid() and not next_block.text().strip():
            next_block = next_block.next()
        
        if next_block.isValid():
            next_indent: int = len(next_block.text()) - len(next_block.text().lstrip())
            return next_indent > current_indent
        return False
    
    def _scheduleFoldUpdate(self) -> None:
        QTimer.singleShot(0, self.updateFoldVisibility)
    
    def _isBlockFolded(self, block: QTextBlock) -> bool:
        for cursor in self._folded_cursors:
            if cursor.block() == block:
                return True
        return False

    def toggleFold(self, block: QTextBlock) -> None:
        """Toggles fold states of block and pushes visibility update"""
        existing_cursor: QTextCursor | None = None
        
        for cursor in self._folded_cursors:
            if cursor.block() == block:
                existing_cursor = cursor
                break
                
        if existing_cursor is not None:
            self._folded_cursors.remove(existing_cursor)
        else:
            new_cursor = QTextCursor(block)
            self._folded_cursors.append(new_cursor)
        
        self._scheduleFoldUpdate()
    
    def updateFoldVisibility(self) -> None:
        """
        Calculates and updates the visibility of all blocks based on nested fold states
        """
        if not hasattr(self, 'lineNumberArea') or self.lineNumberArea is None:
            return

        try:
            block: QTextBlock = self.document().firstBlock()
            hide_until_indent: int = -1
            
            while block.isValid():
                is_folded: bool = self._isBlockFolded(block)
                    
                text: str = block.text()
                is_blank: bool = text.strip() == ""
                indent: int = len(text) - len(text.lstrip())
                
                if hide_until_indent != -1:
                    if not is_blank and indent <= hide_until_indent:
                        hide_until_indent = -1
                        block.setVisible(True)
                    else:
                        block.setVisible(False)
                else:
                    block.setVisible(True)
                    
                if block.isVisible() and not is_blank and is_folded:
                    hide_until_indent = indent
                    
                block = block.next()
                
            self.viewport().update()
            self.lineNumberArea.update()
        except Exception as e:
            print(f"CodeEditor Folding Error: {e}")
            traceback.print_exc()

    def highlightCurrentLine(self) -> None:
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor("#323232")
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
            
        # Bracket matching highlight
        try:
            extraSelections.extend(self.getBracketSelections())
            if hasattr(self, '_lint_selections'):
                extraSelections.extend(self._lint_selections)
        except Exception as e:
            print(f"CodeEditor Highlighting Error: {e}")

        self.setExtraSelections(extraSelections)
    
    def initCompleter(self):
        """Sets up the QCompleter for Python keywords and builtins"""
        self.completer = QCompleter()
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.popup().setObjectName("interactive_console_popup")
        self.completer.activated.connect(self.insertCompletion)
        
        try:
            from resources.autocomplete_keywords import AUTOCOMPLETE_KEYWORDS
            keywords = AUTOCOMPLETE_KEYWORDS
        except ImportError:
            print("Warning:_Could not import autocomplete_keywords. Using default")
            keywords = [
                "def", "class", "if", "else", "elif", "while", "for", "in", "return", 
                "try", "except", "import", "from", "as", "True", "False", "None", 
                "and", "or", "not", "break", "continue", "pass", "lambda", "with", 
                "is", "global", "raise", "yield", "print", "range", "len", "list", 
                "dict", "set", "str", "int", "float", "bool", "super", "__init__",
                "self", "None", "open", "zip", "enumerate", "isinstance"
            ]
        model = QStringListModel(keywords, self.completer)
        self.completer.setModel(model)
    
    def insertCompletion(self, completion):
        """Inserts the selected completion into text"""
        if self.completer.widget() != self:
            return
        
        text_cursor = self.textCursor()
        # calculate how manuy characters we must ignore that has already been tuyped
        extra = len(completion) - len(self.completer.completionPrefix())
        
        # Dont replace the hwole word if typing in the middle
        # complete at end
        # and then move cursor to end position and insert suffix
        text_cursor.movePosition(QTextCursor.MoveOperation.EndOfWord)
        text_cursor.insertText(completion[-extra:])
        self.setTextCursor(text_cursor)
        
    def textUnderCursor(self) -> str:
        """Returns the word under the cursor"""
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        return tc.selectedText()

    def startCompleter(self):
        """Trigger the completer popup"""
        if self.completer:
            self.handleCompleterUpdate(force=True)

    def handleCompleterUpdate(self, force: bool = False):
        """updates the completer prefix and shows the completion popup"""
        if not self.completer:
            return
        
        completionPrefix = self.textUnderCursor()
        
        # do not force the popup if 0 or 1 characters is typed
        # only force if keysequence is requested
        if not force and len(completionPrefix) < 1:
            self.completer.popup().hide()
            return
        
        if completionPrefix != self.completer.completionPrefix():
            self.completer.setCompletionPrefix(completionPrefix)
            self.completer.popup().setCurrentIndex(self.completer.completionModel().index(0, 0))
        
        cursor_rect = self.cursorRect()
        cursor_rect.setWidth(self.completer.popup().sizeHintForColumn(0) + self.completer.popup().verticalScrollBar().sizeHint().width())
        cursor_rect.translate(0, 6)
        
        self.completer.complete(cursor_rect)
    
    def showFindReplaceDialog(self):
        try:
            from ui.dialogs.FindReplaceDialog import FindReplaceDialog
            
            if not self.find_replace_dialog:
                self.find_replace_dialog = FindReplaceDialog(self)
            
            self.find_replace_dialog.show()
            self.find_replace_dialog.activateWindow()
            self.find_replace_dialog.raise_()
            
        except Exception as e:
            print(f"Error opening Find/Replace: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Could not open Find/Replace:\n{e}")
    
    def indentSelection(self, cursor: QTextCursor) -> None:
        """Indents the currently selected text blocks by 4 spaces"""
        try:
            has_selection: bool = cursor.hasSelection()
            start_pos: int = cursor.selectionStart()
            end_pos: int = cursor.selectionEnd()
            
            cursor.setPosition(start_pos)
            start_block: int = cursor.blockNumber()
            cursor.setPosition(end_pos)
            end_block: int = cursor.blockNumber()
            
            if has_selection and cursor.positionInBlock() == 0 and end_block > start_block:
                end_block -= 1
            
            cursor.beginEditBlock()
            for i in range(start_block, end_block + 1):
                block = self.document().findBlockByNumber(i)
                cursor.setPosition(block.position())
                cursor.insertText(self.TAB_SPACES)
            cursor.endEditBlock()
            
            if has_selection:
                cursor.setPosition(self.document().findBlockByNumber(start_block).position())
                cursor.setPosition(self.document().findBlockByNumber(end_block).position(), QTextCursor.MoveMode.KeepAnchor)
                cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            else:
                cursor.setPosition(start_pos + len(self.TAB_SPACES))
            self.setTextCursor(cursor)
        except Exception as e:
            print(f"CodeEditor Indent Error: {e}")
    
    def unindentSelection(self, cursor: QTextCursor) -> None:
        """Unindents the currently selected block by up to four space"""
        try:
            has_selection: bool = cursor.hasSelection()
            start_pos: int = cursor.selectionStart()
            end_pos: int = cursor.selectionEnd()
            
            cursor.setPosition(start_pos)
            start_block: int = cursor.blockNumber()
            cursor.setPosition(end_pos)
            end_block: int = cursor.blockNumber()

            if cursor.positionInBlock() == 0 and end_block > start_block:
                end_block -= 1
            
            cursor.beginEditBlock()
            removed_from_start: int = 0
            for i in range(start_block, end_block + 1):
                block = self.document().findBlockByNumber(i)
                cursor.setPosition(block.position())
                block_text: str = block.text()
                
                spaces_to_remove: int = 0
                if block_text.startswith(self.TAB_SPACES):
                    spaces_to_remove = len(self.TAB_SPACES)
                elif block_text.startswith("\t"):
                    spaces_to_remove = 1
                else:
                    for char in block_text[:len(self.TAB_SPACES)]:
                        if char == " ":
                            spaces_to_remove += 1
                        else:
                            break
                            
                if spaces_to_remove > 0:
                    cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, spaces_to_remove)
                    cursor.removeSelectedText()
                    if i == start_block:
                        removed_from_start = spaces_to_remove
                        
            cursor.endEditBlock()
            if has_selection:
                cursor.setPosition(self.document().findBlockByNumber(start_block).position())
                cursor.setPosition(self.document().findBlockByNumber(end_block).position(), QTextCursor.MoveMode.KeepAnchor)
                cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            else:
                new_pos: int = max(self.document().findBlockByNumber(start_block).position(), start_pos - removed_from_start)
                cursor.setPosition(new_pos)
                
            self.setTextCursor(cursor)
        except Exception as e:
            print(f"CodeEditor Unindent Error: {e}")
    
    def toggleComment(self) -> None:
        """Toggles Python comments for the selected line"""
        cursor: QTextCursor = self.textCursor()
        cursor.beginEditBlock()
        
        has_selection: bool = cursor.hasSelection()
        start_pos: int = cursor.selectionStart()
        end_pos: int = cursor.selectionEnd()
        
        cursor.setPosition(start_pos)
        start_block: int = cursor.blockNumber()
        cursor.setPosition(end_pos)
        end_block: int = cursor.blockNumber()
        
        # do not include trailing block if only start of that block is included
        if has_selection and cursor.positionInBlock() == 0 and end_block > start_block:
            end_block -= 1
        
        # determine if commenting or uncommenting
        all_commented: bool = True
        for i in range(start_block, end_block + 1):
            block = self.document().findBlockByNumber(i)
            text: str = block.text().lstrip()
            if text and not text.startswith("#"):
                all_commented = False
                break
        
        for i in range(start_block, end_block + 1):
            block = self.document().findBlockByNumber(i)
            cursor.setPosition(block.position())
            text: str = block.text()
            
            if all_commented:
                indent_len: int = len(text) - len(text.lstrip())
                if text[indent_len:].startswith("# "):
                    cursor.setPosition(block.position() + indent_len)
                    cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 2)
                    cursor.removeSelectedText()
                elif text[indent_len:].startswith("#"):
                    cursor.setPosition(block.position() + indent_len)
                    cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 1)
                    cursor.removeSelectedText()
            else:
                indent_len: int = len(text) - len(text.lstrip())
                if text.strip():
                    cursor.setPosition(block.position() + indent_len)
                    cursor.insertText("#")
        cursor.endEditBlock()
    
    def showGoToLineDialog(self) -> None:
        """Prompts for a line number and navigates the cursor to that line"""
        current_line: int = self.textCursor().blockNumber() + 1
        max_lines: int = max(1, self.blockCount())
        
        line_number, ok = QInputDialog.getInt(
            self, "Go To Line", f"Enter line number (1 - {max_lines}):",
            current_line, 1, max_lines, 1
        )
        if ok:
            cursor: QTextCursor = self.textCursor()
            target_block = self.document().findBlockByNumber(line_number - 1)
            cursor.setPosition(target_block.position())
            self.setTextCursor(cursor)
            
            self.centerCursor()
    
    def toggleWordWrap(self) -> None:
        """Toggles between soft-wrapping text and horizontal scrolling"""
        if self.lineWrapMode() == QPlainTextEdit.LineWrapMode.NoWrap:
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def toggleWhitespaceVisibility(self) -> None:
        """Toggles the visual rendering of spaces as dots and tabs as arrows"""
        option = self.document().defaultTextOption()

        if option.flags() & QTextOption.Flag.ShowTabsAndSpaces:
            option.setFlags(option.flags() & ~QTextOption.Flag.ShowTabsAndSpaces)
        else:
            option.setFlags(option.flags() | QTextOption.Flag.ShowTabsAndSpaces)

        self.document().setDefaultTextOption(option)
            
    def getBracketSelections(self) -> list[QTextEdit.ExtraSelection]:
        """Finds and highlights matching bracket pairs if the cursor is adjacent to one"""
        selections: list[QTextEdit.ExtraSelection] = []
        cursor: QTextCursor = self.textCursor()
        
        # Match if no text is selected
        if cursor.hasSelection():
            return selections
        doc = self.document()
        pos = cursor.position()
        
        # Function to create a visual selection
        def create_selection(position: int) -> QTextEdit.ExtraSelection:
            sel = QTextEdit.ExtraSelection()
            format = QTextCharFormat()
            format.setBackground(QColor("#505050"))
            format.setForeground(QColor("#ffffff"))
            format.setFontWeight(QFont.Weight.Bold)
            sel.format = format
            c = QTextCursor(doc)
            c.setPosition(position)
            c.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 1)
            sel.cursor = c
            return sel
        
        char_right = doc.characterAt(pos)
        char_left = doc.characterAt(pos - 1) if pos > 0 else ''
        
        pairs = {'(': ')', '[': ']', '{': '}'}
        closing_pairs = {')': '(', ']': '[', '}': '{'}
        
        match_char = ''
        search_direction = 0
        start_pos = pos
        
        if char_right in pairs:
            match_char = pairs[char_right]
            search_direction = 1
        elif char_left in closing_pairs:
            match_char = closing_pairs[char_left]
            search_direction = -1
            start_pos = pos - 1
            char_right = char_left
        elif char_right in closing_pairs:
            match_char = closing_pairs[char_right]
            search_direction = -1
        elif char_left in pairs:
            match_char = pairs[char_left]
            search_direction = 1
            start_pos = pos - 1
            char_right = char_left
        
        if search_direction == 0:
            return selections

        # Search for the matching pair
        current_pos = start_pos + search_direction
        nesting_level = 1
        
        while 0 <= current_pos < doc.characterCount():
            current_char = doc.characterAt(current_pos)
            if current_char == char_right:
                nesting_level += 1
            elif current_char == match_char:
                nesting_level -= 1
                if nesting_level == 0:
                    selections.append(create_selection(start_pos))
                    selections.append(create_selection(current_pos))
                    break
            current_pos += search_direction
        
        return selections
    
    def duplicateLine(self) -> None:
        """Duplicates the current line or selected block of lines below"""
        cursor: QTextCursor = self.textCursor()
        cursor.beginEditBlock()

        start_pos: int = cursor.selectionStart()
        end_pos: int = cursor.selectionEnd()

        # Create the block bouindaries
        cursor.setPosition(start_pos)
        start_block: int = cursor.blockNumber()
        cursor.setPosition(end_pos)
        end_block: int = cursor.blockNumber()

        if cursor.hasSelection() and cursor.positionInBlock() == 0 and end_block > start_block:
            end_block -= 1

        cursor.setPosition(self.document().findBlockByNumber(start_block).position())
        cursor.setPosition(self.document().findBlockByNumber(end_block).position(), QTextCursor.MoveMode.KeepAnchor)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)

        fragment: str = cursor.selection().toPlainText()

        cursor.setPosition(self.document().findBlockByNumber(end_block).position())
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        cursor.insertText("\n" + fragment)

        cursor.endEditBlock()

    def deleteLine(self) -> None:
        """Deletes the current line or selected block of lines"""
        cursor: QTextCursor = self.textCursor()
        cursor.beginEditBlock()

        start_pos: int = cursor.selectionStart()
        end_pos: int = cursor.selectionEnd()

        cursor.setPosition(start_pos)
        start_block: int = cursor.blockNumber()
        cursor.setPosition(end_pos)
        end_block: int = cursor.blockNumber()

        if cursor.hasSelection() and cursor.positionInBlock() == 0 and end_block > start_block:
            end_block -= 1

        cursor.setPosition(self.document().findBlockByNumber(start_block).position())
        cursor.setPosition(self.document().findBlockByNumber(end_block).position(), QTextCursor.MoveMode.KeepAnchor)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)

        if start_block == 0 and end_block == self.document().blockCount() -1 :
            cursor.removeSelectedText()
        elif end_block < self.document().blockCount() - 1:
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
        else:
            cursor.removeSelectedText()
            cursor.deletePreviousChar()

        cursor.endEditBlock()

    def moveLinesUp(self) -> None:
        """Moves the current line or selected block of lines up by one"""
        cursor: QTextCursor = self.textCursor()
        cursor.beginEditBlock()

        start_pos: int = cursor.selectionStart()
        end_pos: int = cursor.selectionEnd()

        cursor.setPosition(start_pos)
        start_block: int = cursor.blockNumber()
        cursor.setPosition(end_pos)
        end_block: int = cursor.blockNumber()

        if cursor.hasSelection() and cursor.positionInBlock() == 0 and end_block > start_block:
            end_block -= 1

        if end_block > 0:
            cursor.setPosition(self.document().findBlockByNumber(start_block).position())
            cursor.setPosition(self.document().findBlockByNumber(end_block).position(), QTextCursor.MoveMode.KeepAnchor)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)

            fragment: str = cursor.selection().toPlainText()
            cursor.removeSelectedText()
            cursor.deletePreviousChar()

            cursor.setPosition(self.document().findBlockByNumber(start_block - 1).position())
            cursor.insertText(fragment + "\n")

            cursor.setPosition(self.document().findBlockByNumber(start_block - 1).position())
            cursor.setPosition(self.document().findBlockByNumber(end_block - 1).position(), QTextCursor.MoveMode.KeepAnchor)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(cursor)

        cursor.endEditBlock()

    def moveLinesDown(self) -> None:
        """Moves the current line or selected block of lines down by one line."""
        cursor: QTextCursor = self.textCursor()
        cursor.beginEditBlock()

        start_pos: int = cursor.selectionStart()
        end_pos: int = cursor.selectionEnd()

        cursor.setPosition(start_pos)
        start_block: int = cursor.blockNumber()
        cursor.setPosition(end_pos)
        end_block: int = cursor.blockNumber()

        if cursor.hasSelection() and cursor.positionInBlock() == 0 and end_block > start_block:
            end_block -= 1

        if end_block < self.document().blockCount() - 1:
            cursor.setPosition(self.document().findBlockByNumber(start_block).position())
            cursor.setPosition(self.document().findBlockByNumber(end_block).position(), QTextCursor.MoveMode.KeepAnchor)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)

            fragment: str = cursor.selection().toPlainText()

            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()

            cursor.setPosition(self.document().findBlockByNumber(start_block).position())
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            cursor.insertText("\n" + fragment)

            cursor.setPosition(self.document().findBlockByNumber(start_block + 1).position())
            cursor.setPosition(self.document().findBlockByNumber(end_block + 1).position(),
                               QTextCursor.MoveMode.KeepAnchor)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(cursor)

        cursor.endEditBlock()

    def _startLinting(self) -> None:
        """Creates the thread background to lint the text state"""
        text: str = self.toPlainText()
        self._active_lint_worker = LintWorker(text)
        self._active_lint_worker.lint_complete.connect(self._applyLintErrors)
        self._active_lint_worker.start()
    
    def _applyLintErrors(self, errors: list[LintError]) -> None:
        """Processes the results from the LintWorker and translates into information"""
        self._lint_selections.clear()
        self._lint_error_map.clear()
        
        doc = self.document()
        for error in errors:
            block_number: int = error.line_number - 1
            block: QTextBlock = doc.findBlockByNumber(block_number)
            
            if not block.isValid():
                continue
            
            self._lint_error_map[block_number] = error.message
            
            selection = QTextEdit.ExtraSelection()
            format = QTextCharFormat()
            format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
            format.setUnderlineColor(QColor("red"))
            selection.format = format
            
            cursor = QTextCursor(block)
            offset: int = max(0, error.offset - 1)
            cursor.setPosition(block.position() + offset)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            
            if cursor.selectedText().strip() == "":
                cursor.setPosition(block.position())
                cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            
            selection.cursor = cursor
            self._lint_selections.append(selection)
        
        self.highlightCurrentLine()
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if hasattr(self, "_lint_error_map") and self._lint_error_map:
            cursor: QTextCursor = self.cursorForPosition(event.position().toPoint())
            block_number: int = cursor.blockNumber()
            
            if block_number in self._lint_error_map:
                QToolTip.showText(event.globalPosition().toPoint(), f"SyntaxError: {self._lint_error_map[block_number]}", self)
            else:
                QToolTip.hideText()
        super().mouseMoveEvent(event)
    
    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handles zooming with ctrl + wheel"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoomIn(1)
            else:
                self.zoomOut(1)
            event.accept()
            return
        super().wheelEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent):
        if self.completer and self.completer.popup().isVisible():
            if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Escape, Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                event.ignore()
                return
        
        is_shortcut = (event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Space)
        if is_shortcut:
            self.startCompleter()
            return
        
        cursor = self.textCursor()
        text = event.text()

        pairs = {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'"}
        closing_chars = {')', ']', '}', '"', "'"}

        #tabs
        if event.key() == Qt.Key.Key_Tab:
            if cursor.hasSelection():
                self.indentSelection(cursor)
            else:
                cursor.insertText(self.TAB_SPACES)
            return
        #backtab
        if event.key() == Qt.Key.Key_Backtab:
            self.unindentSelection(cursor)
            return
        
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self.zoomIn(1)
                return
            elif event.key() == Qt.Key.Key_Minus:
                self.zoomOut(1)
                return
        
        #auto indent on enter
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            block = cursor.block()
            line_text = block.text()

            indentation = ""
            for char in line_text:
                if char == " ": indentation += " "
                elif char == "\t": indentation += "    "
                else: break

            if line_text.rstrip().endswith(":"):
                indentation += "    "
            #Input:(Enter)
            # Output: {
            #             |
            #         }
            pos = cursor.positionInBlock()
            if pos > 0 and pos < len(line_text):
                char_before = line_text[pos-1]
                char_after = line_text[pos]
                if char_before in "{[(" and char_after in "}])":
                    super().keyPressEvent(event)
                    self.insertPlainText(indentation)
                    cursor_pos = self.textCursor().position()
                    self.insertPlainText("\n" + indentation[:-4] if len(indentation)>=4 else "\n")

                    new_cursor = self.textCursor()
                    new_cursor.setPosition(cursor_pos)
                    self.setTextCursor(new_cursor)
                    return

            super().keyPressEvent(event)
            self.insertPlainText(indentation)
            return

        #backspace
        if event.key() == Qt.Key.Key_Backspace:
            pos = cursor.position()
            doc = self.document()
            if pos > 0 and pos < doc.characterCount() - 1:
                cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor)
                char_before = cursor.selectedText()
                cursor.clearSelection()

                cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
                char_after = cursor.selectedText()
                cursor.clearSelection()
                cursor.setPosition(pos)

                if char_before in pairs and pairs[char_before] == char_after:
                    cursor.deleteChar()

            super().keyPressEvent(event)
            return

        #typeover
        if text in closing_chars:
            pos = cursor.position()
            block_text = cursor.block().text()
            pos_in_block = cursor.positionInBlock()

            if pos_in_block < len(block_text):
                char_after = block_text[pos_in_block]
                if char_after == text:
                    cursor.movePosition(QTextCursor.MoveOperation.Right)
                    self.setTextCursor(cursor)
                    return

        #auto close quotes etc
        if text in pairs:
            super().keyPressEvent(event)
            self.insertPlainText(pairs[text])
            self.moveCursor(QTextCursor.MoveOperation.Left)
            return

        super().keyPressEvent(event)
        
        if self.completer:
            if text and (text.isalnum() or text == "_"):
                self.handleCompleterUpdate()
            elif text == ".":
                self.startCompleter()
            elif not text:
                pass