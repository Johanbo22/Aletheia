import json
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, QMessageBox, QInputDialog, QGroupBox, QPushButton, QCheckBox, QSlider, QWidget, QFrame, QColorDialog
from PyQt6.QtGui import QFont, QCloseEvent, QSyntaxHighlighter, QTextCharFormat, QColor, QTextCursor, QTextFormat, QTextDocument, QShortcut, QKeySequence
from PyQt6.QtCore import Qt, QTimer, QRegularExpression

from ui.icons.icon_registry import IconBuilder, IconType
from ui.theme import ThemeColors
from ui.dialogs import CodeEditor

class JSONHighlighter(QSyntaxHighlighter):
    """
    A custom syntax highligher for JSON files
    """
    def __init__(self, document: QTextDocument):
        super().__init__(document)
        self.rules = []
        
        # Value strings
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#a3e4d7"))
        self.rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), fmt))
        
        # Key strings
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#85c1e9"))
        fmt.setFontWeight(QFont.Weight.Bold)
        self.rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"\s*:'), fmt))
        
        # numbers
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#f5b041"))
        self.rules.append((QRegularExpression(r'\b[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?\b'), fmt))
        
        # bools
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#c39bd3"))
        fmt.setFontWeight(QFont.Weight.Bold)
        self.rules.append((QRegularExpression(r'\b(true|false|null)\b'), fmt))
    
    def highlightBlock(self, text: str) -> None:
        for regex, fmt in self.rules:
            iterator = regex.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


class PlotConfigEditorDialog(QDialog):
    """Editor for plot config editing
    Used to create new plot configs from JSON configs or edit existing ones.
    """
    def __init__(self, theme_name: str, theme_content: Dict[str, Any], is_protected: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit theme - {theme_name}")
        self.resize(600, 700)
        self.theme_name = theme_name
        self.is_protected = is_protected
        self.new_theme_name = None
        self.final_content = None
        
        self.original_json: str = json.dumps(theme_content, indent=4)
        self.is_modified: bool = False

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        self.header_frame = QFrame()
        self.header_frame.setObjectName("PlotConfigHeader")
        self.header_frame.setProperty("protected", is_protected)
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setContentsMargins(12, 12, 12, 12)

        info_label = QLabel(f"Editing: <b>{theme_name}</b>")
        info_label.setObjectName("PlotConfigTitle")
        if is_protected:
            info_label.setText(f"Editing: <b>{theme_name}</b> (Read-Only Default)<br><i style='color:orange'>Changes must be saved as a new theme.</i>")
        header_layout.addWidget(info_label)
        layout.addWidget(self.header_frame)

        # Text editor
        self.editor = CodeEditor()
        self.editor.setObjectName("PlotConfigEditor")
        self.editor.setFont(QFont("Consolas", 10))
        self.editor.setLineWrapMode(CodeEditor.LineWrapMode.NoWrap)
        self.editor.completer = None
        self.highlighter = JSONHighlighter(self.editor.document())
        self.editor.setPlainText(self.original_json)
        layout.addWidget(self.editor)
        
        # A validation labels
        self.validation_label = QLabel("Valid JSON")
        self.validation_label.setObjectName("PlotConfigValidationLabel")
        self.validation_label.setProperty("status", "valid")
        layout.addWidget(self.validation_label)
        
        self.validation_timer = QTimer(self)
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self.validate_json)

        # Buttons
        button_layout = QHBoxLayout()
        self.format_button = QPushButton("Format JSON")
        self.format_button.setIcon(IconBuilder.build(IconType.OpenPythonEditor))
        self.format_button.setToolTip("Format JSON spacing (Ctrl+Shift+F)")
        
        self.color_button = QPushButton("Insert color")
        self.color_button.setIcon(IconBuilder.build(IconType.PlotAppearance))
        self.color_button.setToolTip("Pick a color and insert its Hex code at the cursor")
        
        
        self.reset_button = QPushButton("Reset")
        self.reset_button.setIcon(IconBuilder.build(IconType.RefreshItem))
        self.reset_button.setEnabled(False)
        
        self.cancel_button = QPushButton("Cancel")
        
        self.save_button = QPushButton("Save As..." if is_protected else "Save")
        self.save_button.setObjectName("MainActionButton")
        self.save_button.setToolTip("Save theme configuration (Ctrl+S)")

        self.format_button.clicked.connect(self.format_json_content)
        self.color_button.clicked.connect(self.insert_color_hex)
        self.reset_button.clicked.connect(self.reset_to_original)
        self.cancel_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self.handle_save)
        
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.handle_save)
        QShortcut(QKeySequence("Ctrl+Shift+F"), self).activated.connect(self.format_json_content)
        
        self.editor.textChanged.connect(self.handle_text_changed)
        
        button_layout.addWidget(self.format_button)
        button_layout.addWidget(self.color_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        layout.addLayout(button_layout)
    
    def validate_json(self) -> None:
        """
        Validates the JSON content
        Updates the validation label on typing
        """
        content: str = self.editor.toPlainText()
        try:
            json.loads(content)
            self.validation_label.setText("Valid JSON")
            self.validation_label.setProperty("status", "valid")
            self.editor.setProperty("status", "valid")
            self.save_button.setEnabled(True)
            self.format_button.setEnabled(True)
            self.editor.highlightCurrentLine()
            
        except json.JSONDecodeError as parse_error:
            self.validation_label.setText(f"Invalid JSON: {parse_error.msg} (Line: {parse_error.lineno}, Col: {parse_error.colno})")
            self.validation_label.setProperty("status", "error")
            self.editor.setProperty("status", "error")
            self.save_button.setEnabled(False)
            self.format_button.setEnabled(False)
            
            self.highlight_error_line(parse_error.lineno)
        
        self.validation_label.style().unpolish(self.validation_label)
        self.validation_label.style().polish(self.validation_label)
        self.editor.style().unpolish(self.editor)
        self.editor.style().polish(self.editor)
    
    def highlight_error_line(self, lineno: int) -> None:
        temp_cursor = QTextCursor(self.editor.document())
        temp_cursor.movePosition(QTextCursor.MoveOperation.Start)
        temp_cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor, lineno - 1)
        
        selection = QTextEdit.ExtraSelection()
        line_color = QColor("#ff5555")
        line_color.setAlpha(60)
        selection.format.setBackground(line_color)
        selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = temp_cursor
        selection.cursor.clearSelection()
        
        current_selections = self.editor.extraSelections()
        current_selections.append(selection)
        self.editor.setExtraSelections(current_selections)
    
    def format_json_content(self) -> None:
        try:
            content: Dict[str, Any] = json.loads(self.editor.toPlainText())
            formatted_json: str = json.dumps(content, indent=4)
            
            self.editor.blockSignals(True)
            self.editor.setPlainText(formatted_json)
            self.editor.blockSignals(False)
            
            self.validate_json()
        except json.JSONDecodeError:
            pass

    def handle_save(self):
        try:
            content = json.loads(self.editor.toPlainText())
        except json.JSONDecodeError as Error:
            QMessageBox.critical(self, "Invalid JSON", f"Error parsing JSON:\n{str(Error)}")
            return
        
        self.final_content = content

        if self.is_protected:
            name, ok = QInputDialog.getText(self, "Save theme as", "Enter new theme name:", text=f"{self.theme_name}_Copy")
            if ok and name:
                self.new_theme_name = name
                self.is_modified = False
                self.accept()
        else:
            self.is_modified = False
            self.accept()

    def handle_text_changed(self) -> None:
        self.validation_timer.start(400)
        
        current_text: str = self.editor.toPlainText()
        is_now_modified: bool = current_text != self.original_json
        
        if is_now_modified != self.is_modified:
            self.is_modified = is_now_modified
            self.reset_button.setEnabled(self.is_modified)
            
            base_title: str = f"Edit theme - {self.theme_name}"
            self.setWindowTitle(f"*{base_title}" if self.is_modified else base_title)
    
    def insert_color_hex(self) -> None:
        color = QColorDialog.getColor(parent=self, title="Select a color")
        if color.isValid():
            hex_code = color.name().upper()
            self.editor.textCursor().insertText(hex_code)
            self.editor.setFocus()
    
    def reset_to_original(self) -> None:
        if not self.is_modified:
            return
        
        reply = QMessageBox.question(
            self,
            "Reset Changes",
            "Are you sure you want to discard all changes and revert to the original JSON?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.editor.setPlainText(self.original_json)
            self.validate_json()
    
    def reject(self) -> None:
        if self.is_modified:
            reply = QMessageBox.warning(
                self, 
                "Unsaved Changes",
                "You have unsaved changes. Are you sure you want to discard them?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
        super().reject()
    
    def closeEvent(self, event: QCloseEvent) -> None:
        if self.is_modified:
            reply = QMessageBox.warning(
                self, 
                "Unsaved Changes",
                "You have unsaved changes. Are you sure you want to close without saving?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        event.accept()