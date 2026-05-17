# ui/dialogs/ComputedColumnDialog.py
import ast
import keyword
import re
from enum import Enum
from typing import NamedTuple

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QAbstractItemView, QGridLayout, QTreeWidget, QTreeWidgetItem, QSplitter, QWidget, QListWidgetItem
from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtGui import QTextCursor, QShortcut, QKeySequence, QCloseEvent, QFontDatabase

from resources.version import APPLICATION_NAME
from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton
from ui.dialogs.CodeEditor import CodeEditor
from ui.PythonHighlighter import PythonHighlighter
from ui.widgets.ControlElements import DataPlotStudioGroupBox, DataPlotStudioLineEdit, DataPlotStudioListWidget

class ValidationStatus(str, Enum):
    Idle = "idle"
    Success = "success"
    Error = "error"

class OperatorDefinition(NamedTuple):
    label: str
    value: str
    row: int
    column: int

class ComputedColumnDialog(QDialog):
    """Dialog for computing and creating new columns"""

    DialogWidth: int = 900
    DialogHeight: int = 700
    
    OperatorDefinitions: list[OperatorDefinition] = [
        OperatorDefinition("+", " + ", 0, 0),
        OperatorDefinition("-", " - ", 0, 1),
        OperatorDefinition("*", " * ", 0, 2),
        OperatorDefinition("/", " / ", 0, 3),
        OperatorDefinition("% (Mod)", " % ", 0, 4),
        OperatorDefinition("** (Pow)", " ** ", 0, 5),
        OperatorDefinition("==", " == ", 1, 0),
        OperatorDefinition("!=", " != ", 1, 1),
        OperatorDefinition(">", " > ", 1, 2),
        OperatorDefinition("<", " < ", 1, 3),
        OperatorDefinition(">=", " >= ", 1, 4),
        OperatorDefinition("<=", " <= ", 1, 5),
        OperatorDefinition("& (AND)", " & ", 2, 0),
        OperatorDefinition("| (OR)", " | ", 2, 1),
        OperatorDefinition("~ (NOT)", " ~", 2, 2),
        OperatorDefinition("(", "(", 2, 3),
        OperatorDefinition(")", ")", 2, 4),
    ]
    
    def __init__(self, columns: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Computed Column")
        self.columns: list[str] = columns
        self.resize(self.DialogWidth, self.DialogHeight)
        self.setMinimumSize(600, 500)
        self.init_ui()
        self.read_settings()

    def init_ui(self) -> None:
        layout = QVBoxLayout()

        # Input boxes
        input_group = DataPlotStudioGroupBox("Column Details")
        input_layout = QVBoxLayout()

        input_layout.addWidget(QLabel("New Column Name"))
        self.name_input = DataPlotStudioLineEdit()
        self.name_input.setPlaceholderText("e.g., Total_Price")
        self.name_input.setToolTip("Enter a valid, unique Python identifier (no spaces or special characters) as name")
        self.name_input.setClearButtonEnabled(True)
        input_layout.addWidget(self.name_input)

        input_layout.addWidget(QLabel("Expression"))
        expression_layout = QHBoxLayout()
        equals_label = QLabel("=")
        equals_label.setObjectName("equals_label")
        expression_layout.addWidget(equals_label)

        self.expression_input = CodeEditor()
        self.expression_input.setObjectName("computed_column_expression")
        self.expression_input.setPlaceholderText("e.g., Price * Quantity")
        self.expression_input.setToolTip("Construct your mathematical or logical expression here. Columns with spaces must be wrapped in backticks.")
        self.expression_input.setMinimumHeight(80)
        
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.expression_input.setFont(fixed_font)
        
        self.highlighter = PythonHighlighter(self.expression_input.document())
        expression_layout.addWidget(self.expression_input)
        
        clear_expression_button = DataPlotStudioButton("Clear")
        clear_expression_button.setToolTip("Clear the expression editor")
        clear_expression_button.clicked.connect(self._clear_expression)
        expression_layout.addWidget(clear_expression_button, alignment=Qt.AlignmentFlag.AlignTop)

        input_layout.addLayout(expression_layout)

        # Operator butons
        operators_layout = QGridLayout()
        operators_layout.setContentsMargins(0, 5, 0, 5)
        operators_layout.setSpacing(5)

        # three rows of operators: artihmetic, comparison, logical
        for operator in self.OperatorDefinitions:
            operator_button = DataPlotStudioButton(operator.label)
            operator_button.setToolTip(f"Insert '{operator.label}'")
            
            operator_button.clicked.connect(
                lambda checked, v=operator.value: self.insert_text(v)
            )
            operators_layout.addWidget(operator_button, operator.row, operator.column)

        input_layout.addLayout(operators_layout)
        
        self.status_label = QLabel("")
        self.status_label.setObjectName("validation_status_label")
        self.status_label.setMinimumHeight(20)
        self.status_label.setWordWrap(True)
        input_layout.addWidget(self.status_label)

        help_text = QLabel(
            "Use column names exactly as they appear below.\n"
            "If columns have spaces, wrap them in backticks: `Column Name`"
        )
        help_text.setProperty("styleClass", "info_text")
        help_text.setWordWrap(True)
        input_layout.addWidget(help_text)

        input_group.setLayout(input_layout)
        
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.addWidget(input_group)

        self.helpers_splitter = QSplitter(Qt.Orientation.Horizontal)

        column_widget = QWidget()
        column_layout = QVBoxLayout(column_widget)
        column_layout.setContentsMargins(0, 0, 5, 0)

        insert_column_info = QLabel("Available Columns:")
        insert_column_info.setProperty("styleClass", "list_header_info")
        insert_column_info.setWordWrap(True)
        column_layout.addWidget(insert_column_info)
        
        self.column_filter_input = DataPlotStudioLineEdit()
        self.column_filter_input.setPlaceholderText("Search columns...")
        self.column_filter_input.setClearButtonEnabled(True)
        
        self.column_search_timer = QTimer(self)
        self.column_search_timer.setSingleShot(True)
        self.column_search_timer.setInterval(250)
        self.column_search_timer.timeout.connect(self._apply_column_filter)
        self.column_filter_input.textChanged.connect(self.column_search_timer.start)
        self.column_filter_input.returnPressed.connect(self._insert_single_filtered_column)
        
        column_layout.addWidget(self.column_filter_input)
        
        self.column_no_results_label = QLabel("No columns match your search")
        self.column_no_results_label.setProperty("styleClass", "no_results_label")
        self.column_no_results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.column_no_results_label.setHidden(True)
        column_layout.addWidget(self.column_no_results_label)

        self.column_list = DataPlotStudioListWidget()
        self.column_list.setAlternatingRowColors(True)
        self.column_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.column_list.addItems(self.columns)
        self.column_list.itemActivated.connect(self.insert_column_into_expression)
        column_layout.addWidget(self.column_list)

        self.helpers_splitter.addWidget(column_widget)

        # Fcuntoions math
        function_widget = QWidget()
        function_layout = QVBoxLayout(function_widget)
        function_layout.setContentsMargins(5, 0, 0, 0)

        insert_func_info = QLabel("Function Library:")
        insert_func_info.setProperty("styleClass", "list_header_info")
        function_layout.addWidget(insert_func_info)
        
        self.function_filter_input = DataPlotStudioLineEdit()
        self.function_filter_input.setPlaceholderText("Search functions...")
        self.function_filter_input.setClearButtonEnabled(True)
        
        self.function_search_timer = QTimer(self)
        self.function_search_timer.setSingleShot(True)
        self.function_search_timer.setInterval(250)
        self.function_search_timer.timeout.connect(self._apply_function_filter)
        self.function_filter_input.textChanged.connect(self.function_search_timer.start)
        function_layout.addWidget(self.function_filter_input)
        
        self.function_no_results_label = QLabel("No functions match your search")
        self.function_no_results_label.setProperty("styleClass", "no_results_label")
        self.function_no_results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.function_no_results_label.setHidden(True)
        function_layout.addWidget(self.function_no_results_label)

        self.function_tree = QTreeWidget()
        self.function_tree.setHeaderHidden(True)
        self.function_tree.itemActivated.connect(self.insert_function)
        self.populate_functions()
        function_layout.addWidget(self.function_tree)

        self.helpers_splitter.addWidget(function_widget)

        self.helpers_splitter.setStretchFactor(0, 1)
        self.helpers_splitter.setStretchFactor(1, 1)
        
        self.main_splitter.addWidget(self.helpers_splitter)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)

        layout.addWidget(self.main_splitter, 1)

        # Buttons
        button_layout = QHBoxLayout()
        self.create_button = DataPlotStudioButton(
            "Create Column",
            parent=self,
            base_color_hex=ThemeColors.MainColor,
            text_color_hex="white",
            typewriter_effect=True,
        )
        self.create_button.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(self.create_button)

        self.cancel_button = DataPlotStudioButton("Cancel", parent=self)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        self.validation_timer = QTimer(self)
        self.validation_timer.setSingleShot(True)
        self.validation_timer.setInterval(300)
        self.validation_timer.timeout.connect(self._perform_validation)
        
        self.name_input.textChanged.connect(self._queue_validation)
        self.expression_input.textChanged.connect(self._queue_validation)
        self._perform_validation()
        
        # Keyboard shortcuts
        self.submit_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.submit_shortcut.activated.connect(self.validate_and_accept)
        self.submit_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        
        self.focus_func_search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.focus_func_search_shortcut.activated.connect(self.function_filter_input.setFocus)
        self.focus_func_search_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        
        self.focus_col_search_shortcut = QShortcut(QKeySequence("Alt+C"), self)
        self.focus_col_search_shortcut.activated.connect(self.column_filter_input.setFocus)
        self.focus_col_search_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        
        QWidget.setTabOrder(self.name_input, self.expression_input)
        QWidget.setTabOrder(self.expression_input, self.column_filter_input)
        QWidget.setTabOrder(self.column_filter_input, self.column_list)
        QWidget.setTabOrder(self.column_list, self.function_filter_input)
        QWidget.setTabOrder(self.function_filter_input, self.function_tree)
        QWidget.setTabOrder(self.function_tree, self.create_button)
        QWidget.setTabOrder(self.create_button, self.cancel_button)

        self.name_input.setFocus()
    
    def read_settings(self) -> None:
        """Load the saved window geometry and splitter states"""
        settings = QSettings(f"{APPLICATION_NAME}", "ComputedColumnDialog")
        
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        main_splitter_state = settings.value("main_splitter")
        if main_splitter_state:
            self.main_splitter.restoreState(main_splitter_state)
        
        helpers_splitter_state = settings.value("helpers_splitter")
        if helpers_splitter_state:
            self.helpers_splitter.restoreState(helpers_splitter_state)
    
    def write_settings(self) -> None:
        """Save the current window geometry and splitter states."""
        settings = QSettings(f"{APPLICATION_NAME}", "ComputedColumnDialog")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("main_splitter", self.main_splitter.saveState())
        settings.setValue("helpers_splitter", self.helpers_splitter.saveState())
    
    def _confirm_discard(self) -> bool:
        """Prompt for discarding unsaved expressions"""
        if self.expression_input.toPlainText().strip():
            reply = QMessageBox.question(
                self,
                "Discard Changes?",
                "You have an active expression. Are you sure you want to discard it and close?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )
            return reply == QMessageBox.StandardButton.Discard
        return True
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """Ensure settings are saved when the dialog is closed directly (e.g., via the 'X' button)."""
        if not self._confirm_discard():
            event.ignore()
            return
        
        self.write_settings()
        super().closeEvent(event)
    
    def accept(self) -> None:
        """Ensure settings are saved when the dialog is accepted."""
        self.write_settings()
        super().accept()
    
    def reject(self) -> None:
        """Ensure settings are saved when dialog is rejected"""
        if not self._confirm_discard():
            return
        self.write_settings()
        super().reject()
    
    def _clear_expression(self) -> None:
        """Clear the expression editor and immediately return focus to it."""
        self.expression_input.clear()
        self.expression_input.setFocus()
    
    def _queue_validation(self) -> None:
        """Restart the validation timer"""
        self.validation_timer.start()

    def _perform_validation(self) -> None:
        """ enable or disable the submit button based on input presence."""
        name = self.name_input.text().strip()
        expression = self.expression_input.toPlainText().strip()
        
        is_valid = True
        error_message = ""
        error_source = None
        
        if not name:
            is_valid = False
        elif keyword.iskeyword(name):
            is_valid = False
            error_message = f"Error: '{name}' is a reserved Python keyword"
            error_source = "name"
        elif "`" in name:
            is_valid = False
            error_message = "Error: Column names cannot contain backticks"
            error_source = "name"
        elif " " in name:
            is_valid = False
            error_message = "Error: Column names cannot contain spaces. Use underscores (_) instead"
            error_source = "name"
        elif not name.isidentifier():
            is_valid = False
            error_message = f"Error: Column must be a valid Python identifier"
            error_source = "name"
        elif name in self.columns:
            is_valid = False
            error_message = f"Error: Column '{name}' already exists"
            error_source = "name"
        
        if is_valid:
            if not expression:
                is_valid = False
            else:
                backticked_columns = re.findall(r"`([^`]+)`", expression)
                missing_columns = [col for col in backticked_columns if col not in self.columns]
                
                if missing_columns:
                    is_valid = False
                    error_message = f"Error: Column '{missing_columns[0]}' does not exist"
                    error_source = "expression"
                else:
                    try:
                        sanitized_expr = re.sub(r"`[^`]+`", "variable", expression)
                        ast.parse(sanitized_expr)
                        error_message = "Expression is valid"
                    except SyntaxError as syntax_error:
                        is_valid = False
                        line = syntax_error.lineno if syntax_error.lineno else "?"
                        col = syntax_error.offset if syntax_error.offset else "?"
                        msg = syntax_error.msg.capitalize() if syntax_error.msg else "Invalid syntax"
                        error_message = f"Syntax Error: (Line {line}, Col {col}): {msg}"
                        error_source = "expression"
                    except Exception as error:
                        is_valid = False
                        error_message = f"Error: {str(error)}"
                        error_source = "expression"
        
        self.create_button.setEnabled(is_valid)
        
        self.name_input.setProperty("validationState", "error" if error_source == "name" else "default")
        self.name_input.style().unpolish(self.name_input)
        self.name_input.style().polish(self.name_input)
        
        self.expression_input.setProperty("validationState", "error" if error_source == "expression" else "default")
        self.expression_input.style().unpolish(self.expression_input)
        self.expression_input.style().polish(self.expression_input)
        
        if not name and not expression:
            self.status_label.setText("")
            self.status_label.setProperty("status", ValidationStatus.Idle.value)
        elif is_valid:
            self.status_label.setText(error_message)
            self.status_label.setProperty("status", ValidationStatus.Success.value)
        else:
            self.status_label.setText(error_message)
            self.status_label.setProperty("status", ValidationStatus.Error.value)
        
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def populate_functions(self) -> None:
        """Populate the function library with some functions (math, trigs, etc)"""
        functions = {
            "Math": [
                ("abs", "Absolute value"), 
                ("sqrt", "Square root"), 
                ("log", "Natural logarithm"), 
                ("exp", "Exponential"), 
                ("round", "Round to nearest integer"), 
                ("ceil", "Round up to the nearest integer"), 
                ("floor", "Round down to the nearest integer"), 
                ("pow", "Power")
            ],
            "Trigonometry": [
                ("sin", "Sine"), 
                ("cos", "Cosine"), 
                ("tan", "Tangent"), 
                ("degrees", "Convert radians to degrees"), 
                ("radians", "Convert degrees to radians")
            ],
            "String Accessor": [
                (".str.upper()", "Convert strings in the Series to uppercase"),
                (".str.lower()", "Convert strings in the Series to lowercase"),
                (".str.title()", "Convert strings in the Series to titlecase"),
                (".str.strip()", "Remove leading and trailing whitespace"),
                (".str.len()", "Compute the length of each string"),
                (".str.replace('old', 'new')", "Replace occurrences of 'old' with 'new'"),
            ],
        }
        for category, funcs in functions.items():
            parent = QTreeWidgetItem(self.function_tree)
            parent.setText(0, category)
            parent.setExpanded(True)
            for func_name, tooltip in funcs:
                item = QTreeWidgetItem(parent)
                item.setText(0, func_name)
                item.setToolTip(0, tooltip)
    
    def _apply_function_filter(self) -> None:
        """Filter the function tree based on query"""
        search_text = self.function_filter_input.text().strip()
        self.function_tree.clearSelection()
        visible_count = 0
        
        for i in range(self.function_tree.topLevelItemCount()):
            parent_item = self.function_tree.topLevelItem(i)
            parent_visible = False
            
            for j in range(parent_item.childCount()):
                child_item = parent_item.child(j)
                child_matches = search_text in child_item.text(0).lower()
                child_item.setHidden(not child_matches)
                if child_matches:
                    parent_visible = True
                    visible_count += 1
            
            # Show parent if it matches the search text of child
            if search_text in parent_item.text(0).lower():
                parent_visible = True
                # Reveal all children from parent
                for j in range(parent_item.childCount()):
                    parent_item.child(j).setHidden(False)
                    visible_count += 1
            
            parent_item.setHidden(not parent_visible)
            
            if search_text and parent_visible:
                parent_item.setExpanded(True)
        
        self.function_tree.setHidden(visible_count == 0)
        self.function_no_results_label.setHidden(visible_count > 0)

    def insert_function(self, item: QTreeWidgetItem) -> None:
        """Insert the selected function into the expression"""
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())
            return

        func_text = item.text(0)
        
        if not func_text.endswith(")"):
            func_text += "()"
        
        self.insert_text(func_text)
        
    
    def _apply_column_filter(self) -> None:
        """Filter the column list based on input"""
        search_text = self.column_filter_input.text().lower()
        self.column_list.clearSelection()
        visible_count = 0
        
        for i in range(self.column_list.count()):
            item = self.column_list.item(i)
            is_match = search_text in item.text().lower()
            item.setHidden(not is_match)
            if is_match:
                visible_count += 1
        
        self.column_list.setHidden(visible_count == 0)
        self.column_no_results_label.setHidden(visible_count > 0)
    
    def _insert_single_filtered_column(self) -> None:
        """if the signal returnPressed is fired and one col is visible in list. insert that col"""
        visible_items = [self.column_list.item(i) for i in range(self.column_list.count()) if not self.column_list.item(i).isHidden()]
        
        number_of_visible_items = 1
        if len(visible_items) == number_of_visible_items:
            self.insert_column_into_expression(visible_items[0])
            self.column_filter_input.clear()

    def insert_text(self, text: str) -> None:
        """Insert the text at the current cursor position and refocus"""
        cursor = self.expression_input.textCursor()
        
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            if text.endswith("()"):
                cursor.insertText(f"{text[:-1]}{selected_text})")
            elif text.strip() == "(":
                cursor.insertText(f"({selected_text})")
            else:
                cursor.insertText(text)
        else:
            cursor.insertText(text)
            if text.endswith("()") or text.strip() == "(":
                cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, 1)
                self.expression_input.setTextCursor(cursor)
        
        self.expression_input.setFocus()

    def insert_column_into_expression(self, item: QListWidgetItem) -> None:
        """Insert the selected column into the expression with backticks if nessecary"""
        column_name = item.text()

        # Check if string not a valid identifier and if not add backticks
        if not column_name.isidentifier():
            column_name = f"`{column_name}`"

        self.insert_text(f"{column_name} ")

    def validate_and_accept(self) -> None:
        if self.create_button.isEnabled():
            self.accept()
        else:
            QMessageBox.warning(self, "Validation Error", "Please resolve the highlighted errors before creating the column")

    def get_data(self) -> tuple[str, str]:
        return (
            self.name_input.text().strip(),
            self.expression_input.toPlainText().strip(),
        )
