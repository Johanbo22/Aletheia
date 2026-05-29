# ui/dialogs/ComputedColumnDialog.py
import ast
import keyword
import re
import json
from enum import Enum
from typing import NamedTuple

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QAbstractItemView, QGridLayout, QTreeWidget, QTreeWidgetItem, QSplitter, QWidget, QListWidgetItem, QSizePolicy
from PyQt6.QtCore import QModelIndex, QPoint, Qt, QTimer, QSettings, QEvent, QObject
from PyQt6.QtGui import QAction, QTextCursor, QShortcut, QKeySequence, QCloseEvent, QFontDatabase

from resources.version import APPLICATION_NAME
from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton
from ui.dialogs.CodeEditor import CodeEditor
from ui.PythonHighlighter import PythonHighlighter
from ui.widgets.ControlElements import DataPlotStudioGroupBox, DataPlotStudioLineEdit, DataPlotStudioListWidget, DataPlotStudioMenu
from ui.dialogs.AddCustomFunctionDialog import AddCustomFunctionDialog
from ui.widgets.CustomFunctionDelegate import CustomFunctionDelegate

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

    CustomFunctionsSettingsKey: str = "custom_functions"
    
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
        self.column_no_results_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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

        function_search_layout = QHBoxLayout()
        function_search_layout.setContentsMargins(0, 0, 0, 0)
        function_search_layout.setSpacing(5)
        function_search_layout.addWidget(self.function_filter_input)

        self.add_custom_func_btn = DataPlotStudioButton("+", padding="4px")
        self.add_custom_func_btn.setToolTip("Create a new custom function snippet")
        self.add_custom_func_btn.setFixedWidth(35)
        self.add_custom_func_btn.clicked.connect(self._add_custom_function)
        function_search_layout.addWidget(self.add_custom_func_btn)

        function_layout.addLayout(function_search_layout)
        
        self.function_no_results_label = QLabel("No functions match your search")
        self.function_no_results_label.setProperty("styleClass", "no_results_label")
        self.function_no_results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.function_no_results_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.function_no_results_label.setHidden(True)
        function_layout.addWidget(self.function_no_results_label)

        self.function_tree = QTreeWidget()
        self.function_tree.setObjectName("ComputedColumnFunctionTree")
        self.function_tree.setHeaderHidden(True)
        self.function_tree.setAlternatingRowColors(True)
        self.function_tree.itemActivated.connect(self.insert_function)

        # Context menu for deleting custom functions
        self.function_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.function_tree.customContextMenuRequested.connect(self._show_function_context_menu)

        self.function_tree.setMouseTracking(True)
        self.function_tree.viewport().setMouseTracking(True)

        self.custom_delegate = CustomFunctionDelegate(self.function_tree)
        self.custom_delegate.edit_requested.connect(self._edit_custom_function_by_index)
        self.custom_delegate.delete_requested.connect(self._delete_custom_function_by_index)
        self.function_tree.setItemDelegate(self.custom_delegate)
        self.function_tree.viewport().installEventFilter(self)

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

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Unset the cursor if the mouse leaves the function tree viewport to prevent a stuck cursor"""
        if watched == self.function_tree.viewport() and event.type() == QEvent.Type.Leave:
            self.function_tree.viewport().unsetCursor()
        return super().eventFilter(watched, event)
    
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
        self.function_tree.clear()
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
        custom_funcs = self._load_custom_functions()
        for func in custom_funcs:
            cat = func.get("category", "Custom Functions")
            if cat not in functions:
                functions[cat] = []
            functions[cat].append((func["name"], func["desc"], func["snippet"]))

        for category, funcs in functions.items():
            parent = QTreeWidgetItem(self.function_tree)
            parent.setText(0, category)
            parent.setExpanded(True)
            for func_data in funcs:
                if len(func_data) == 2:
                    func_name, tooltip = func_data
                    snippet = func_name
                    is_custom = False
                else:
                    func_name, tooltip, snippet = func_data
                    is_custom = True

                item = QTreeWidgetItem(parent)
                item.setText(0, func_name)
                item.setToolTip(0, tooltip)
                item.setData(0, Qt.ItemDataRole.UserRole, snippet)
                item.setData(0, Qt.ItemDataRole.UserRole + 1, is_custom)

    def _load_custom_functions(self) -> list[dict[str, str]]:
        """Loads custom functions from the settings"""
        settings = QSettings(f"{APPLICATION_NAME}", "ComputedColumnDialog")
        data = settings.value(self.CustomFunctionsSettingsKey, "[]")
        try:
            funcs = json.loads(data)
            for f in funcs:
                if "category" not in f:
                    f["category"] = "Custom Functions"
            return funcs
        except json.JSONDecodeError:
            return []

    def _save_custom_function(self, name: str, category: str, desc: str, snippet: str) -> None:
        """Saves a custom function snippet to settings"""
        funcs = self._load_custom_functions()

        for func in funcs:
            if func["name"] == name:
                func["category"] = category
                func["desc"] = desc
                func["snippet"] = snippet
                break
        else:
            funcs.append({"name": name, "category": category, "desc": desc, "snippet": snippet})

        settings = QSettings(f"{APPLICATION_NAME}", "ComputedColumnDialog")
        settings.setValue(self.CustomFunctionsSettingsKey, json.dumps(funcs))
        self.populate_functions()

    def _delete_custom_function(self, name: str) -> None:
        """Deletes a custom function from settings"""
        reply = QMessageBox.question(
            self, "Delete Custom Function",
            f"Are you sure you want to delete the custom function '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            funcs = self._load_custom_functions()
            filtered_funcs = [f for f in funcs if f["name"] != name]

            settings = QSettings(f"{APPLICATION_NAME}", "ComputedColumnDialog")
            settings.setValue(self.CustomFunctionsSettingsKey, json.dumps(filtered_funcs))
            self.populate_functions()

    def _add_custom_function(self) -> None:
        """Opens the AddCustomFunctionDialog and saves a new custom function snippet"""
        funcs = self._load_custom_functions()
        categories = sorted(list(set(f.get("category", "Custom Functions") for f in funcs)))
        built_in = ["Math", "Trigonometry", "String Accessor"]
        all_categories = sorted(list(set(categories + built_in)))
        
        dialog = AddCustomFunctionDialog(existing_categories=all_categories, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, category, desc, snippet = dialog.get_function_data()
            self._save_custom_function(name, category, desc, snippet)

    def _edit_custom_function_by_index(self, index: QModelIndex) -> None:
        """Wrapper to translate model index from delegate into a tree item to edit function"""
        item = self.function_tree.itemFromIndex(index)
        if item:
            self._edit_custom_function(item)

    def _delete_custom_function_by_index(self, index: QModelIndex) -> None:
        """Wrapper to translate model index from delegate into a tree item to delete function"""
        item = self.function_tree.itemFromIndex(index)
        if item:
            self._delete_custom_function(item.text(0))

    def _edit_custom_function(self, item: QTreeWidgetItem) -> None:
        """Opens the AddCustomFunctionDialog to edit an existing custom functions snippet"""
        old_name = item.text(0)
        old_desc = item.toolTip(0)
        old_snippet = item.data(0, Qt.ItemDataRole.UserRole)
        old_category = item.parent().text(0) if item.parent() else "Custom Functions"
        
        funcs = self._load_custom_functions()
        categories = sorted(list(set(f.get("category", "Custom Functions") for f in funcs)))
        built_in = ["Math", "Trigonometry", "String Accessor"]
        all_categories = sorted(list(set(categories + built_in)))

        dialog = AddCustomFunctionDialog(existing_categories=all_categories, parent=self)
        dialog.setWindowTitle("Edit Custom Function")
        dialog.save_button.setText("Save Changes")

        dialog.name_input.setText(old_name)
        dialog.category_input.setCurrentText(old_category)
        dialog.desc_input.setText(old_desc)
        dialog.snippet_input.setPlainText(old_snippet)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name, new_category, new_desc, new_snippet = dialog.get_function_data()
            funcs = self._load_custom_functions()

            for func in funcs:
                if func["name"] == old_name:
                    func["name"] = new_name
                    func["category"] = new_category
                    func["desc"] = new_desc
                    func["snippet"] = new_snippet
                    break
            else:
                funcs.append({"name": new_name, "category": new_category, "desc": new_desc, "snippet": new_snippet})
            settings = QSettings(f"{APPLICATION_NAME}", "ComputedColumnDialog")
            settings.setValue(self.CustomFunctionsSettingsKey, json.dumps(funcs))
            self.populate_functions()

    def _show_function_context_menu(self, position: QPoint) -> None:
        """Displays the context menu for tree items, allowing for deletion of custom functions"""
        item = self.function_tree.itemAt(position)

        # Must ignore clicks on empty space or parents
        if not item or item.childCount() > 0:
            return

        is_custom = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if is_custom:
            menu = DataPlotStudioMenu(self.function_tree)

            edit_action = QAction("Edit Custom Function", self)
            edit_action.triggered.connect(lambda: self._edit_custom_function(item))
            menu.addAction(edit_action)

            delete_action = QAction("Delete Custom Function", self)
            delete_action.triggered.connect(lambda: self._delete_custom_function(item.text(0)))
            menu.addAction(delete_action)
            menu.exec(self.function_tree.viewport().mapToGlobal(position))
    
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
        """Insert the selected function or snippet into the expression"""
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())
            return

        snippet = item.data(0, Qt.ItemDataRole.UserRole)
        is_custom = item.data(0, Qt.ItemDataRole.UserRole + 1)

        if is_custom:
            self.insert_text(f"{snippet}")
        else:
            if not snippet.endswith(")"):
                snippet += "()"
            self.insert_text(snippet)
    
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
