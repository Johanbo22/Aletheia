from typing import Any

from ui.theme import ThemeColors
from ui.widgets.AnimatedCheckBox import DataPlotStudioCheckBox
from ui.dialogs import CodeEditor
from ui.PythonHighlighter import PythonHighlighter

import sys
import ast
from PyQt6.QtCore import Qt, pyqtSignal, QSettings, QEvent, QPoint
from PyQt6.QtGui import QTextCursor, QColor, QFont, QFontMetrics, QShortcut, QKeySequence, QFontDatabase
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QPlainTextEdit, QMenu, QSplitter, QTreeWidget, QTreeWidgetItem, QWidget, QApplication


from datetime import datetime

from ui.widgets import DataPlotStudioButton, DataPlotStudioComboBox, DataPlotStudioLineEdit
from ui.animations.PlotGeneratedAnimation import PlotGeneratedAnimation

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

class StreamRedirector:
    """Redirects stdout/stderr to a plain text widget from the code editor"""
    def __init__(self, widget: QPlainTextEdit, original_stream, color: str = None):
        self.widget = widget
        self.original_stream = original_stream
        self.color = color
        
    def write(self, text) -> int:
        text_str = str(text)
        if self.original_stream:
            self.original_stream.write(text_str)
            
        
        cursor = self.widget.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        if self.color:
            fmt = cursor.charFormat()
            original_format = cursor.charFormat()
            fmt.setForeground(QColor(self.color))
            cursor.setCharFormat(fmt)
            cursor.insertText(text_str)
            cursor.setCharFormat(original_format)
        else:
            cursor.insertText(text_str)
        
        self.widget.setTextCursor(cursor)
        self.widget.ensureCursorVisible()
        
        QApplication.processEvents()
        
        return len(text_str)
    
    def flush(self) -> None:
        self.original_stream.flush()


class ScriptEditorDialog(QDialog):
    """A dialog for editing and running custom python plotting scripts"""

    run_script_signal = pyqtSignal(str)
    _has_warning_untrusted: bool = False

    def __init__(self, initial_code: str = "", df=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Python Console")
        self.resize(1100, 750)
        self.setModal(False)

        self.df = df
        self.script_history: list[dict[str, str]] = []
        self.run_counter: int = 0
        self.is_code_modified: bool = False
        self.default_template: str = initial_code if initial_code else "def create_plot(df):\n    # Create your custom plot here\n    pass\n"

        self.console_history: list[str] = []
        self.console_history_idx: int = 0
        
        self.console_namespace: dict[str, Any] = {
            "df": self.df,
            "plt": plt,
            "pd": pd,
            "np": np
        }
        
        self.init_ui(initial_code)
        
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        self.stdout_redirector = StreamRedirector(self.console_output, self.original_stdout, color="#f8f8f2")
        self.stderr_redirector = StreamRedirector(self.console_output, self.original_stderr, color="#ff5555")
        
        sys.stdout = self.stdout_redirector
        sys.stderr = self.stderr_redirector
        
        self.read_settings()
    
    def read_settings(self) -> None:
        """Restores the window size, position, and splitter layout from previous sessions."""
        settings = QSettings("DataPlotStudio", "ScriptEditor")
        saved_geometry = settings.value("geometry")
        if saved_geometry:
            self.restoreGeometry(saved_geometry)
        
        saved_h_splitter = settings.value("horizontal_splitter_state")
        if saved_h_splitter and hasattr(self, "horizontal_splitter"):
            self.horizontal_splitter.restoreState(saved_h_splitter)
        
        saved_v_splitter = settings.value("vertical_splitter_state")
        if saved_v_splitter and hasattr(self, "vertical_splitter"):
            self.vertical_splitter.restoreState(saved_v_splitter)
    
    def write_settings(self) -> None:
        """Saves the current window layout preferences to the system registry/config."""
        settings = QSettings("DataPlotStudio", "ScriptEditor")
        settings.setValue("geometry", self.saveGeometry())
        if hasattr(self, "horizontal_splitter"):
            settings.setValue("horizontal_splitter_state", self.horizontal_splitter.saveState())
        if hasattr(self, "vertical_splitter"):
            settings.setValue("vertical_splitter_state", self.vertical_splitter.saveState())
    
    def eventFilter(self, source, event: QEvent) -> bool:
        if source == self.console_output and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                if self.console_history and self.console_history_idx > 0:
                    self.console_history_idx -= 1
                    self._replace_console_input(self.console_history[self.console_history_idx])
                return True

            elif event.key() == Qt.Key.Key_Down:
                if self.console_history and self.console_history_idx < len(self.console_history) - 1:
                    self.console_history_idx += 1
                    self._replace_console_input(self.console_history[self.console_history_idx])
                elif self.console_history_idx == len(self.console_history) - 1:
                    self.console_history_idx = len(self.console_history)
                    self._replace_console_input("")
                return True
            
            
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                cursor = self.console_output.textCursor()
                cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                
                raw_line = cursor.selectedText()
                command: str = raw_line.replace(">>>", "", 1).strip() if raw_line.startswith(">>>") else raw_line.strip()
                
                if command in ("help", "?"):
                    self._add_to_history(command)
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    self.console_output.setTextCursor(cursor)
                    print("\nDataPlotStudio Script Editor Help")
                    print("This console allows you to execute Python commands")
                    print("The current DataFrame is accessible via the 'df' command")
                    print("Type your script in the editor above and click 'Run Script' to execute")
                    print("Remember to never run any untrusted code as this can harm your computer.")
                    return True
                elif command:
                    self._add_to_history(command)
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    self.console_output.setTextCursor(cursor)
                    print("")
                    try:
                        try:
                            result = eval(command, globals(), self.console_namespace)
                            if result is not None:
                                print(result)
                        except SyntaxError:
                            exec(command, globals(), self.console_namespace)
                    except Exception as execution_error:
                        self._print_error(f"Error: {execution_error}")
                    
                    self.update_variable_explorer()
                    self._append_console_prompt()
                    return True
                else:
                    # if commmand is empty, moving to new line and a new prompt
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    self.console_output.setTextCursor(cursor)
                    print("")
                    self._append_console_prompt()
                    return True
        return super().eventFilter(source, event)
    
    def _add_to_history(self, command: str) -> None:
        if not self.console_history or self.console_history[-1] != command:
            self.console_history.append(command)
        self.console_history_idx = len(self.console_history)
    
    def _replace_console_input(self, new_text: str) -> None:
        cursor = self.console_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.KeepAnchor)
        
        line_text = cursor.selectedText()
        if line_text.startswith(">>>"):
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            prompt_len = len(">>> ") if line_text.startswith(">>> ") else len(">>>")
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, prompt_len)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        
        cursor.insertText(new_text)
        self.console_output.setTextCursor(cursor)
        
    def _print_error(self, error_message: str) -> None:
        cursor = self.console_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        fmt = cursor.charFormat()
        original_format = cursor.charFormat()
        
        fmt.setForeground(QColor("#ff5555"))
        cursor.setCharFormat(fmt)
        
        cursor.insertText(f"{error_message}\n")
        
        cursor.setCharFormat(original_format)
        self.console_output.setTextCursor(cursor)
        self.console_output.ensureCursorVisible()
        
    def closeEvent(self, event):
        """
        Intercepts the dialog close event to restore system streams and 
        warn the user if there are unsaved code modifications.
        """
        if self.is_code_modified and not self.auto_sync_check.isChecked():
            reply = QMessageBox.question(
                self, 
                "Unsaved Changes",
                "You have modified the script. Are you sure you want to close without running?\n"
                "Any unexecuted changes will be lost.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            ) 
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        
        self.write_settings()
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        super().closeEvent(event)

    def init_ui(self, code):
        layout = QVBoxLayout()
        self.setLayout(layout)

        #header and information
        info_layout = QHBoxLayout()
        info_label = QLabel("<b>Script</b><br>Edit the <code>create_plot(df)</code> function below. Click the 'Run' button to update the plot.")
        info_label.setProperty("styleClass", "info_text")
        info_layout.addWidget(info_label)
        layout.addLayout(info_layout)

        #security
        security_label = QLabel("Warning: Executing untrusted Python code can be dangerous and can harm your computer\nOnly run code you trust.")
        security_label.setObjectName("script_security_label")
        layout.addWidget(security_label)

        #tools
        toolbar = QHBoxLayout()
        self.auto_sync_check = DataPlotStudioCheckBox("Auto-update from GUI (This will overwrite changes)")
        self.auto_sync_check.setChecked(True)
        self.auto_sync_check.setToolTip("If checked, changing settings from the GUI will overwrite the code here")
        toolbar.addWidget(self.auto_sync_check)
        
        # snippets menu
        toolbar.addSpacing(10)
        self.snippet_button = DataPlotStudioButton("Insert Snippet", parent=self, typewriter_effect=True)
        self.snippet_button.setProperty("menu_button", "true")
        self.snippet_button.setFixedWidth(130)
        self.snippet_button.setToolTip("Insert common plotting code snippets")
        self.snippet_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.snippet_menu = QMenu(self)
        self.snippet_menu.setObjectName("script_snippet_menu")
        
        self.theme_button = DataPlotStudioButton("Theme Settings", parent=self, typewriter_effect=True)
        self.theme_button.setToolTip("Customize Python syntax highlighting colors")
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.setFixedWidth(130)
        self.theme_button.clicked.connect(self.open_theme_settings)
        toolbar.addWidget(self.theme_button)
        
        categorized_snippets: dict[str, dict[str, str]] = {
            "Reference Lines": {
                "Vertical Reference Line": "ax.axvline(x=0, color='red', linestyle='--', linewidth=1.5, label='Ref Line')\n",
                "Horizontal Reference Line": "ax.axhline(y=0, color='blue', linestyle=':', linewidth=1.5, label='Threshold')\n",
                "Diagonal Line": "ax.plot([0, 1], [0, 1], linestyle='-.', color='gray', linewidth=1.2)\n",
                "Custom Line Segment": "ax.plot([0.2, 0.8], [0.1, 0.9], color='black', linewidth=2.0)\n",
            },
            "Highlights & Regions": {
                "Highlight Vertical Region": "ax.axvspan(xmin=0, xmax=1, color='yellow', alpha=0.2)\n",
                "Highlight Horizontal Region": "ax.axhspan(ymin=0, ymax=1, color='green', alpha=0.2)\n",
            },
            "Markers": {
                "Star Marker": "ax.scatter(x=[0.5], y=[0.5], marker='*', s=200, color='gold')\n",
                "Cross Marker": "ax.scatter(x=[0.2], y=[0.8], marker='x', s=100, color='red')\n",
            }
        }
        
        for category_name, snippets in categorized_snippets.items():
            sub_menu = self.snippet_menu.addMenu(category_name)
            for name, code_snippet in snippets.items():
                action = sub_menu.addAction(name)
                action.triggered.connect(lambda checked, c=code_snippet: self.insert_snippet_into_code(c))
            
        self.snippet_button.setMenu(self.snippet_menu)
        toolbar.addWidget(self.snippet_button)

        toolbar.addSpacing(20)
        toolbar.addWidget(QLabel("History:"))
        self.history_combo = DataPlotStudioComboBox()
        self.history_combo.setMinimumWidth(400)
        self.history_combo.addItem("Select to restore...")
        self.history_combo.activated.connect(self.on_history_selected)
        toolbar.addWidget(self.history_combo)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        #editor
        self.editor = CodeEditor()
        self.editor.setObjectName("script_code_editor")
        self.editor.setPlainText(code if code else "")
        self.editor.setMinimumHeight(400)
        
        editor_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        editor_font.setPointSize(11)
        editor_font.setStyleHint(QFont.StyleHint.Monospace)
        self.editor.setFont(editor_font)
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        
        font_metrics = QFontMetrics(editor_font)
        self.editor.setTabStopDistance(font_metrics.horizontalAdvance(" ")*4)
        
        self.comment_shortcut = QShortcut(QKeySequence("Ctrl+Shift+7"), self.editor)
        self.comment_shortcut.activated.connect(self.toggle_comments)
        
        self.run_selection_shortcut = QShortcut(QKeySequence("Ctrl+E"), self.editor)
        self.run_selection_shortcut.activated.connect(self.run_selected_code)
        
        self.zoom_in_shortcut = QShortcut(QKeySequence.StandardKey.ZoomIn, self)
        self.zoom_in_shortcut.activated.connect(lambda: self.adjust_font_size(1))
        self.zoom_out_shortcut = QShortcut(QKeySequence.StandardKey.ZoomOut, self)
        self.zoom_out_shortcut.activated.connect(lambda: self.adjust_font_size(-1))
        self.zoom_reset_shortcut = QShortcut(QKeySequence("Ctrl+0"), self)
        self.zoom_reset_shortcut.activated.connect(lambda: self.adjust_font_size(0, reset=True))

        # add python syntax highlighnign
        self.highlighter = PythonHighlighter(self.editor.document())
        self._load_syntax_theme()
        layout.addWidget(self.editor, 3)
        
        # Splitter for variable panel and editor (left and right)
        self.horizontal_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.horizontal_splitter.addWidget(self.editor)
        
        variable_panel = QVBoxLayout()
        variable_panel.setContentsMargins(0, 0, 0, 0)
        var_header_layout = QHBoxLayout()
        
        self.variable_search_bar = DataPlotStudioLineEdit()
        self.variable_search_bar.setObjectName("script_variable_search")
        self.variable_search_bar.setPlaceholderText("Search Columns...")
        self.variable_search_bar.textChanged.connect(self.filter_variables)
        var_header_layout.addWidget(self.variable_search_bar)
        
        self.clear_vars_button = DataPlotStudioButton("Clear Variables", parent=self)
        self.clear_vars_button.setToolTip("Clear all custom variables fro memory")
        self.clear_vars_button.clicked.connect(self.clear_all_variables)
        var_header_layout.addWidget(self.clear_vars_button)
        
        variable_panel.addLayout(var_header_layout)
        
        self.variable_explorer = self.create_variable_explorer()
        variable_panel.addWidget(self.variable_explorer)
        
        variable_container_widget = QWidget()
        variable_container_widget.setLayout(variable_panel)
        
        self.horizontal_splitter.addWidget(variable_container_widget)
        
        self.horizontal_splitter.setStretchFactor(0, 3)
        self.horizontal_splitter.setStretchFactor(1, 1)
        
        self.vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self.vertical_splitter.addWidget(self.horizontal_splitter)
        
        # console pane
        console_container = QWidget()
        console_layout = QVBoxLayout()
        console_layout.setContentsMargins(0, 0, 0, 0)
        
        console_header_layout = QHBoxLayout()
        console_header_layout.addWidget(QLabel("Console Output:"))
        console_header_layout.addStretch()
        
        self.reset_script_button = DataPlotStudioButton("Reset Script", parent=self)
        self.reset_script_button.setToolTip("Reset the editor to the default template")
        self.reset_script_button.clicked.connect(self.reset_script_to_default)
        console_header_layout.addWidget(self.reset_script_button)
        
        self.clear_console_button = DataPlotStudioButton("Clear Console", parent=self)
        self.clear_console_button.setToolTip("Clear the console")
        self.clear_console_button.clicked.connect(self.clear_console)
        console_header_layout.addWidget(self.clear_console_button)
        
        console_layout.addLayout(console_header_layout)
        
        self.console_output = QPlainTextEdit()
        self.console_output.setObjectName("script_console_output")
        self.console_output.setReadOnly(False)
        self.console_output.installEventFilter(self)
        console_layout.addWidget(self.console_output)
        
        console_container.setLayout(console_layout)
        self.vertical_splitter.addWidget(console_container)
        
        self.vertical_splitter.setStretchFactor(0, 4)
        self.vertical_splitter.setStretchFactor(1, 1)
        
        layout.addWidget(self.vertical_splitter, 1)
    
        #buttons
        button_layout = QHBoxLayout()
        self.run_button = DataPlotStudioButton("Run Script", parent=self, base_color_hex=ThemeColors.MainColor, text_color_hex="white", padding="6px", typewriter_effect=True)
        self.run_button.setMinimumHeight(40)
        self.run_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_button.setShortcut("Ctrl+Shift+Return")
        self.run_button.setToolTip("Click to run the script and update the plot\nShortcut 'Ctrl+Shift+Enter'")
        self.run_button.clicked.connect(self.on_run_clicked)
        button_layout.addWidget(self.run_button)

        self.close_button = DataPlotStudioButton("Close", parent=self, typewriter_effect=True)
        self.close_button.setMinimumHeight(40)
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)
        
        self.editor.textChanged.connect(self.on_text_changed)
        
        self._append_console_prompt()
        self.update_variable_explorer()
    
    def _append_console_prompt(self) -> None:
        cursor = self.console_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(">>> ")
        self.console_output.setTextCursor(cursor)
    
    def _load_syntax_theme(self) -> None:
        """Loads the custom syntax highlighting theme from QSettings"""
        from ui.PythonHighlighter import SyntaxCategory, DefaultColorScheme
        settings = QSettings("DataPlotStudio", "SyntaxHighlighting")
        
        saved_scheme: dict[SyntaxCategory, str] = {}
        for category in SyntaxCategory:
            color = settings.value(category.value, DefaultColorScheme[category])
            saved_scheme[category] = color
        
        self.highlighter.set_color_scheme(saved_scheme)
    
    def open_theme_settings(self) -> None:
        from ui.dialogs.SyntaxHighlightSettingsDialog import SyntaxHighlightSettingsDialog
        dialog = SyntaxHighlightSettingsDialog(self.highlighter.color_scheme, self)
        if dialog.exec():
            new_scheme = dialog.get_color_scheme()
            self.highlighter.set_color_scheme(new_scheme)
            
            settings = QSettings("DataPlotStudio", "SyntaxHighlighting")
            for category, color in new_scheme.items():
                settings.setValue(category.value, color)
        
    def create_variable_explorer(self) -> QTreeWidget:
        """
        Creates a side panel widget showing variables in scope from active dataframe
        Context menus for code insertion as well as double click event handling to cursor position
        """
        tree = QTreeWidget()
        tree.setObjectName("script_variable_explorer")
        tree.setHeaderLabels(["Variable", "Info"])
        tree.setColumnWidth(0, 160)
        tree.setIndentation(15)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.show_explorer_context_menu)
        tree.itemDoubleClicked.connect(self.on_explorer_double_click)

        return tree
    
    def update_variable_explorer(self) -> None:
        self.variable_explorer.clear()
        
        for var_name, var_value in self.console_namespace.items():
            # Modules, function and internal values are filtered
            if var_name.startswith("_") or type(var_value).__name__ in ("module", "function", "builtin_function_or_method", "type"):
                continue
            
            root = QTreeWidgetItem(self.variable_explorer)
            root.setText(0, str(var_name))
            root.setText(1, type(var_value).__name__)
            root.setExpanded(True)
            root.setData(0, Qt.ItemDataRole.UserRole, str(var_name))
            
            # Specific variables to the current df
            if isinstance(var_value, pd.DataFrame):
                shape_item = QTreeWidgetItem(root)
                shape_item.setText(0, "Shape")
                shape_item.setText(1, str(var_value.shape))
                
                cols_root = QTreeWidgetItem(root)
                cols_root.setText(0, "Columns")
                cols_root.setText(1, f"{len(var_value.columns)}")
                
                for col in var_value.columns:
                    col_name = str(col)
                    series = var_value[col]
                    
                    col_item = QTreeWidgetItem(cols_root)
                    col_item.setText(0, col_name)
                    col_item.setText(1, str(series.dtype))
                    col_item.setData(0, Qt.ItemDataRole.UserRole, f"'{col_name}'")
            elif isinstance(var_value, (pd.Series, list, dict, set, tuple, str)):
                try:
                    len_item = QTreeWidgetItem(root)
                    len_item.setText(0, "Length")
                    len_item.setText(1, str(len(var_value)))
                    if isinstance(var_value, str) or (isinstance(var_value, (list, tuple, set)) and len(var_value) <= 10):
                        val_item = QTreeWidgetItem(root)
                        val_item.setText(0, "Value")
                        val_item.setText(1, str(var_value))
                except Exception as err:
                    print(err)
            elif isinstance(var_value, (int, float, bool)):
                val_item = QTreeWidgetItem(root)
                val_item.setText(0, "Value")
                val_item.setText(1, str(var_value))
        
        static_vars = self.get_editor_static_variables()
        if static_vars:
            static_root = QTreeWidgetItem(self.variable_explorer)
            static_root.setText(0, "Declared (Run to submit)")
            static_root.setText(1, "Current Scope")
            static_root.setExpanded(True)
            
            for var_name in sorted(static_vars):
                item = QTreeWidgetItem(static_root)
                item.setText(0, var_name)
                item.setText(1, "Unknown (Run to inspect)")
                item.setData(0, Qt.ItemDataRole.UserRole, str(var_name))
        
        self.filter_variables(self.variable_search_bar.text())
            
    
    def filter_variables(self, search_text: str) -> None:
        """
        Filters the variable explorer tree based on the user's search input.
        Hides columns that do not match the search string (case-insensitive).
        """
        if not hasattr(self, "variable_explorer") or self.variable_explorer.topLevelItemCount() == 0:
            return
        
        search_text_lower: str = search_text.lower()
        
        for i in range(self.variable_explorer.topLevelItemCount()):
            root_item: QTreeWidgetItem | None = self.variable_explorer.topLevelItem(i)
            
            columns_node: QTreeWidgetItem | None = None
            for j in range(root_item.childCount()):
                if root_item.child(j).text(0) == "Columns":
                    columns_node = root_item.child(j)
                    break
            
            if columns_node:
                for k in range(columns_node.childCount()):
                    col_item = columns_node.child(k)
                    col_name: str = col_item.text(0).lower()
                    col_item.setHidden(search_text_lower not in col_name)
    
    def on_explorer_double_click(self, item: QTreeWidgetItem, column: int):
        """
        Insert the items variable into editor on double click event
        """
        text_to_insert = item.data(0, Qt.ItemDataRole.UserRole)
        if text_to_insert:
            self.insert_snippet_into_code(text_to_insert)
    
    def show_explorer_context_menu(self, position: QPoint):
        """Show the context menu for variable items"""
        item = self.variable_explorer.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        menu.setObjectName("script_snippet_menu")
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        node_text = item.text(0)
        
        if data:
            action_insert = menu.addAction(f"Insert {data}")
            action_insert.triggered.connect(lambda: self.insert_snippet_into_code(data))
            
            if not item.parent():
                protected_vars = {"df", "plt", "pd", "np"}
                if data not in protected_vars:
                    menu.addSeparator()
                    action_delete = menu.addAction(f"Delete Variable '{data}'")
                    action_delete.triggered.connect(lambda: self._delete_console_variable(data))
            
            if item.parent() and item.parent().text(0) == "Columns":
                parent_var_name = item.parent().parent().text(0)
                
                df_access = f"{parent_var_name}[{data}]"
                action_df = menu.addAction(f"Insert {df_access}")
                action_df.triggered.connect(lambda: self.insert_snippet_into_code(df_access))
        
        if node_text == "Columns" and item.parent():
            parent_var_name = item.parent().text(0)
            target_df = self.console_namespace.get(parent_var_name)
            
            if isinstance(target_df, pd.DataFrame):
                col_list_str: str = "[" + ", ".join([f"'{col}'" for col in target_df.columns]) + "]"
                action_list = menu.addAction("Insert as List [...]")
                action_list.triggered.connect(lambda: self.insert_snippet_into_code(col_list_str))

        if not menu.isEmpty():
            menu.exec(self.variable_explorer.viewport().mapToGlobal(position))
    
    def insert_snippet_into_code(self, code: str) -> None:
        """Inserts the snippet code into the code editor at cursor position"""
        cursor = self.editor.textCursor()
        cursor.insertText(code)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()
        
        if self.auto_sync_check.isChecked():
            self.auto_sync_check.setChecked(False)
        
    def _delete_console_variable(self, var_name: str) -> None:
        if var_name in self.console_namespace:
            del self.console_namespace[var_name]
            print(f"\n[Deleted variable: {var_name}]")
            self._append_console_prompt()
            self.update_variable_explorer()
    
    def clear_all_variables(self) -> None:
        reply = QMessageBox.question(
            self, "Clear Variables",
            "Are you sure you want to delete all custom variables?\n",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            protected_vars = {"df", "plt", "pd", "np"}
            keys_to_delete = [k for k in self.console_namespace.keys() if k not in protected_vars]
            
            for k in keys_to_delete:
                del self.console_namespace[k]
            
            print(f"\n[Cleared {len(keys_to_delete)} variables]")
            self._append_console_prompt()
            self.update_variable_explorer()
    
    def adjust_font_size(self, delta: int, reset: bool = False) -> None:
        default_size = 11
        for widget in (self.editor, self.console_output):
            font = widget.font()
            if reset:
                font.setPointSize(default_size)
            else:
                new_size = max(6, min(font.pointSize() + delta, 36))
                font.setPointSize(new_size)
            widget.setFont(font)

    def on_text_changed(self):
        """Tracker to to see if user modified code to prevent unwanted changes"""
        if not self.is_code_modified:
            self.setWindowTitle("Pyton Console *")
        self.is_code_modified = True
        # set the autosync to off so the user does not lose data
        if self.auto_sync_check.isChecked() and self.editor.hasFocus():
            self.auto_sync_check.setChecked(False)
        
        current_static_vars = self.get_editor_static_variables()
        if not hasattr(self, "_last_static_vars") or self._last_static_vars != current_static_vars:
            self._last_static_vars = current_static_vars
            self.update_variable_explorer()
    
    def get_editor_static_variables(self) -> set[str]:
        code: str = self.editor.toPlainText()
        variables: set[str] = set()
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            variables.add(target.id)
                        elif isinstance(target, (ast.Tuple, ast.List)):
                            for elt in target.elts:
                                if isinstance(elt, ast.Name):
                                    variables.add(elt.id)
                elif isinstance(node, ast.AnnAssign):
                    if isinstance(node.target, ast.Name):
                        variables.add(node.target.id)
        except SyntaxError:
            pass
        
        return {v for v in variables if v not in self.console_namespace and not v.startswith("_")}
    
    def toggle_comments(self) -> None:
        """Toggles Python comments (#) on the currently selected lines."""
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        
        start_block: int = self.editor.document().findBlock(cursor.selectionStart()).blockNumber()
        end_block: int = self.editor.document().findBlock(cursor.selectionEnd()).blockNumber()
        
        # Determine if we are commenting or uncommenting based on the first line
        comment_symbol = "#"
        first_block_text: str = self.editor.document().findBlockByNumber(start_block).text().lstrip()
        is_uncommenting: bool = first_block_text.startswith(comment_symbol)
        
        for i in range(start_block, end_block, 1):
            block = self.editor.document().findBlockByNumber(i)
            text: str = block.text()
            
            # Resposition cursor to the start of the current block
            cursor.setPosition(block.position())
            if is_uncommenting:
                idx: int = text.find(comment_symbol)
                if idx != -1:
                    cursor.setPosition(block.position() + idx)
                    cursor.deleteChar()
                    
                    space = " "
                    if len(text) > idx + 1 and text[idx + 1] == space:
                        cursor.deleteChar()
            else:
                cursor.insertText(comment_symbol)
        
        cursor.endEditBlock()
    
    def clear_console(self) -> None:
        self.console_output.clear()
        self._append_console_prompt()
        
    def run_selected_code(self) -> None:
        """Executes the highlighted text block within the editor"""
        cursor = self.editor.textCursor()
        has_selection: bool = cursor.hasSelection()
        
        if not has_selection:
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            
        selected_text: str = cursor.selectedText()
        if not selected_text.strip():
            if not has_selection:
                cursor.clearSelection()
                cursor.movePosition(QTextCursor.MoveOperation.Down)
                self.editor.setTextCursor(cursor)
            return
            
        selected_text = selected_text.replace('\u2029', '\n')
        
        action_label = "Selection" if has_selection else "Line"
        print(f"\n[Running {action_label}]\n{selected_text}")
        
        try:
            if not has_selection:
                try:
                    result = eval(selected_text.strip(), globals(), self.console_namespace)
                    if result is not None:
                        print(result)
                except SyntaxError:
                    exec(selected_text, globals(), self.console_namespace)
            else:
                exec(selected_text, globals(), self.console_namespace)
        except Exception as execution_error:
            self._print_error(f"Error executing {action_label.lower()}: {execution_error}")
            
        self.update_variable_explorer()
        self._append_console_prompt()
        
        if not has_selection:
            cursor.clearSelection()
            cursor.movePosition(QTextCursor.MoveOperation.Down)
            self.editor.setTextCursor(cursor)
    
    def reset_script_to_default(self) -> None:
        reply = QMessageBox.question(
            self,
            "Reset Script",
            "Are you sure you want to reset the script to its default state?\nAll unsaved edits will be lost",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.editor.setPlainText(self.default_template)
            self.is_code_modified = False
            self.setWindowTitle("Python Console")
            self.auto_sync_check.setChecked(False)
    
    def goto_error_line(self, line_number: int) -> None:
        """
        Moves the editor's cursor to the specified line number and highlights it 
        to help the user quickly locate syntax errors.
        """
        if not line_number:
            return
        
        # Qt text blocks are 0-indexed, but AST is 1-indexed
        block = self.editor.document().findBlockByNumber(line_number - 1)
        if block.isValid():
            cursor = QTextCursor(block)
            # Hightlight the entire block with the error
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            
            self.editor.setTextCursor(cursor)
            self.editor.setFocus()

    def update_code(self, new_code: str) -> None:
        """Update the code from the GUI"""
        if self.auto_sync_check.isChecked():
            self.editor.blockSignals(True)
            cursor = self.editor.textCursor()
            scroll = self.editor.verticalScrollBar().value()
            self.editor.setPlainText(new_code)
            self.editor.setTextCursor(cursor)
            self.editor.verticalScrollBar().setValue(scroll)
            self.editor.blockSignals(False)

    def on_run_clicked(self) -> None:
        """Validate and emit code"""
        code: str = self.editor.toPlainText()
        
        try:
            tree = ast.parse(code)
        except SyntaxError as syntaxerror:
            sys.stderr.write(str(syntaxerror) + "\n")
            if syntaxerror.lineno:
                self.goto_error_line(syntaxerror.lineno)
            QMessageBox.critical(self, "Syntax Error", f"Cannot run script due to syntax error:\n{syntaxerror}")
            return

        if not ScriptEditorDialog._has_warning_untrusted:
            warning_reply = QMessageBox.warning(
                self,
                "Security Warning",
                "You are about to execute custom Python code.\n\n"
                "Running untrusted code can compromise your system and data. "
                "Ensure you trust the source of this script before proceeding.\n\n"
                "Do you want to run this code?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if warning_reply == QMessageBox.StandardButton.No:
                return
            ScriptEditorDialog._has_warning_untrusted = True

        self.save_to_history(code)

        self.run_script_signal.emit(code)
        
        # Reset the modified flag since current code is now executed
        self.is_code_modified = False
        self.setWindowTitle("Python Console")

        self.run_script_animation = PlotGeneratedAnimation(parent=self, message="Run Script")
        self.run_script_animation.start(target_widget=self)

    def save_to_history(self, code: str) -> None:
        """Save the current code to a list, cannot go more than 5, """
        #no saving dups
        if self.script_history and self.script_history[-1]["code"] == code:
            return

        self.run_counter += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        label = f"Edition: #{self.run_counter} - {timestamp}"

        self.script_history.append({'code': code, 'label': label})

        #max 5 copyes
        MAX_HISTORY_ITEMS: int = 5
        if len(self.script_history) > MAX_HISTORY_ITEMS:
            self.script_history.pop(0)

        self.update_history_combo()

    def update_history_combo(self):
        """update the box of code history"""
        self.history_combo.blockSignals(True)
        self.history_combo.clear()
        self.history_combo.addItem(f"Select to restore ({len(self.script_history)} available editions)...")

        #reverse order neweest first
        for item in reversed(self.script_history):
            self.history_combo.addItem(item["label"], item["code"])

        self.history_combo.blockSignals(False)

    def on_history_selected(self, index):
        """Restore the selected edition"""
        if index == 0: return

        code = self.history_combo.currentData()
        if code:
            reply = QMessageBox.question(
                self, "Restore Version",
                "Do you want to restore this version?\nCurrent code in the editor will be replaced.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.editor.setPlainText(code)
                self.auto_sync_check.setChecked(False)
                self.history_combo.setCurrentIndex(0)