from typing import final
from ui.LineNumberArea import LineNumberArea


from PyQt6.QtCore import QRect, Qt, QStringListModel
from PyQt6.QtGui import QColor, QFont, QPainter, QTextCursor, QTextFormat, QAction, QKeySequence, QTextDocument
from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit, QCompleter, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QMessageBox, QWidget
import traceback

from ui.dialogs.CodeEditor import CodeEditor
from ui.widgets.AnimatedButton import DataPlotStudioButton
from ui.widgets.ControlElements import DataPlotStudioCheckBox
from ui.widgets.ControlElements import DataPlotStudioLineEdit

class FindReplaceDialog(QDialog):
    """Floating dialog for find and replace"""
    def __init__(self, editor: CodeEditor):
        super().__init__(editor)
        self.editor = editor
        self.setWindowTitle("Find and Replace")
        self.setFixedWidth(300)
        
        layout = QVBoxLayout()
        
        # Find
        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("Find:"))
        self.find_input = DataPlotStudioLineEdit()
        find_layout.addWidget(self.find_input)
        layout.addLayout(find_layout)
        
        # Replace
        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("Replace:"))
        self.replace_input = DataPlotStudioLineEdit()
        replace_layout.addWidget(self.replace_input)
        layout.addLayout(replace_layout)
        
        # options
        self.case_sensitive_check = DataPlotStudioCheckBox("Case Sensitive")
        layout.addWidget(self.case_sensitive_check)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.find_next_button = DataPlotStudioButton("Find Next")
        self.replace_button = DataPlotStudioButton("Replace")
        self.replace_all_button = DataPlotStudioButton("Replace All")
        
        button_layout.addWidget(self.find_next_button)
        button_layout.addWidget(self.replace_button)
        button_layout.addWidget(self.replace_all_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

        # connections
        self.find_next_button.clicked.connect(self.find_next)
        self.replace_button.clicked.connect(self.replace)
        self.replace_all_button.clicked.connect(self.replace_all)
    
    def _get_flags(self) -> QTextDocument.FindFlag:
        flags = QTextDocument.FindFlag(0)
        if self.case_sensitive_check.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        return flags
        
    def find_next(self):
        """Finds and selects the next occurrence of the text."""
        try:
            text = self.find_input.text()
            if not text: return
            
            flags = self._get_flags()
            
            cursor = self.editor.textCursor()
            found_cursor = self.editor.document().find(text, cursor, flags)
            
            if found_cursor.isNull():
                start_cursor = self.editor.textCursor()
                start_cursor.movePosition(QTextCursor.MoveOperation.Start)
                found_cursor = self.editor.document().find(text, start_cursor, flags)
            
            if not found_cursor.isNull():
                self.editor.setTextCursor(found_cursor)
            else:
                QMessageBox.information(self, "Result", f"'{text}' not found.")
                
        except Exception:
            error_msg = traceback.format_exc()
            print(error_msg)
            QMessageBox.critical(self, "Error", f"An error occurred during Find:\n{error_msg}")
    
    def replace(self):
        """
        Replaces the current selection and finds the next one.
        """
        try:
            cursor = self.editor.textCursor()
            target = self.find_input.text()
            replacement = self.replace_input.text()
            
            is_match = False
            if cursor.hasSelection():
                selected_text = cursor.selectedText()
                if self.case_sensitive_check.isChecked():
                    is_match = (selected_text == target)
                else:
                    is_match = (selected_text.lower() == target.lower())

            if is_match:
                cursor.beginEditBlock()
                cursor.insertText(replacement)
                cursor.endEditBlock()
                
                self.editor.setTextCursor(cursor)
                
                self.find_next()
            else:
                self.find_next()
                
        except Exception:
            error_msg = traceback.format_exc()
            print(error_msg)
            QMessageBox.critical(self, "Error", f"An error occurred during Replace:\n{error_msg}")
    
    def replace_all(self):
        try:
            text = self.find_input.text()
            replacement = self.replace_input.text()
            if not text: return
            
            flags = self._get_flags()

            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            
            work_cursor = self.editor.document().find(text, cursor, flags)
            
            if work_cursor.isNull():
                QMessageBox.information(self, "Result", f"'{text}' not found.")
                return

            count = 0
            cursor.beginEditBlock()
            
            while not work_cursor.isNull():
                work_cursor.insertText(replacement)
                count += 1
                
                work_cursor = self.editor.document().find(text, work_cursor, flags)
                
            cursor.endEditBlock()
            
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cursor)
                
            QMessageBox.information(self, "Result", f"Replaced {count} occurrences of {text} with {replacement}.")
            
        except Exception:
            error_msg = traceback.format_exc()
            print(error_msg)
            QMessageBox.critical(self, "Error", f"An error occurred during Replace All:\n{error_msg}")