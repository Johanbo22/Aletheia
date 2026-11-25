import logging
import re
from enum import IntEnum, StrEnum
from pathlib import Path

import keyring
from PyQt6.QtCore import QMimeData, QPoint, QSettings, QThreadPool, Qt
from PyQt6.QtGui import QAction, QColor, QFont, QFontDatabase, QIntValidator, QKeySequence, QPixmap, QShortcut, \
    QSyntaxHighlighter, QTextCharFormat, QTextDocument
from PyQt6.QtWidgets import QButtonGroup, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox, \
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMenu, QMessageBox, QPushButton, QRadioButton, QSplitter, QStackedWidget, \
    QStyle, QTabWidget, QTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget
from keyring.errors import KeyringError, PasswordDeleteError
from sqlalchemy.engine import URL
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ArgumentError

from icons import IconBuilder, IconType
from resources.version import APPLICATION_NAME
from src.controller.database_preview_controller import DatabasePreviewController
from src.core.database_query_preview import PREVIEW_ROW_LIMIT, is_valid_readonly_query
from src.core.global_signals import LogLevel, ToastLevel, global_signals
from src.core.resource_loader import get_resource_path
from src.ui.components.query_preview_panel import QueryPreviewPanel
from src.ui.workers import ColumnMetadata, FetchColumnWorker, FetchSchemaWorker, SchemaTableGroup, TestConnectionWorker

class SchemaNodeType(StrEnum):
    SCHEMA = "schema"
    TABLE = "table"
    COLUMN = "column"
    PLACEHOLDER = "placeholder"

class SchemaTreeRole(IntEnum):
    """Custom Qt.ItemDataRole used to store metadata on schema tree nodes."""
    NODE_TYPE = int(Qt.ItemDataRole.UserRole)
    SCHEMA_NAME = int(Qt.ItemDataRole.UserRole) + 1
    TABLE_NAME = int(Qt.ItemDataRole.UserRole) + 2
    IS_LOADED = int(Qt.ItemDataRole.UserRole) + 3
    USER_EXPANDED = int(Qt.ItemDataRole.UserRole) + 4

LOADING_PLACEHOLDER_TEXT: str = "Loading columns..."
NO_COLUMNS_TEXT: str = "No columns found"
NO_TABLES_TEXT: str = "No tables found"
FAILED_COLUMNS_TEXT: str = "Failed to load columns (collapse and expand to retry)"

SQL_CLAUSE_PRECEDING_KEYWORDS: frozenset[str] = frozenset({
    "SELECT", "FROM", "WHERE", "AND", "OR", "JOIN", "INNER", "LEFT", "RIGHT",
    "OUTER", "FULL", "CROSS", "ON", "BY", "HAVING", "LIMIT", "OFFSET", "AS",
    "WITH", "DISTINCT", "UNION", "ALL", "IN", "IS", "NOT", "CASE", "WHEN",
    "THEN", "ELSE", "VALUES", "TABLE"
})

def format_sql_identifier(name: str) -> str:
    """Quote SQL identifiers that contain spaces symbols or leading digits"""
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        escaped: str = name.replace('"', '""')
        return f'"{escaped}"'
    return name

def format_tree_item_identifier(item: QTreeWidgetItem, *, qualified: bool = True) -> str:
    """Build a quoted SQl identifier string from schema tree"""
    node_type: str = str(item.data(0, SchemaTreeRole.NODE_TYPE) or "")
    if node_type not in (SchemaNodeType.TABLE.value, SchemaNodeType.COLUMN.value):
        return ""

    if not qualified and node_type == SchemaNodeType.COLUMN.value:
        return format_sql_identifier(item.text(0))

    schema_name: str = str(item.data(0, SchemaTreeRole.SCHEMA_NAME) or "")
    table_name: str = str(item.data(0, SchemaTreeRole.TABLE_NAME) or "")

    identifier_parts: list[str] = []
    if schema_name and qualified:
        identifier_parts.append(format_sql_identifier(schema_name))
    identifier_parts.append(format_sql_identifier(table_name))
    if node_type == SchemaNodeType.COLUMN.value:
        identifier_parts.append(format_sql_identifier(item.text(0)))

    return ".".join(identifier_parts)

class SchemaTreeWidget(QTreeWidget):
    """QTreeWidget that serialises dragged schema items as plain-text SQL ids"""

    def mimeTypes(self) -> list[str]:
        types: list[str] = super().mimeTypes()
        if "text/plain" not in types:
            types.append("text/plain")
        return types

    def mimeData(self, items: list[QTreeWidgetItem]) -> QMimeData:
        mime_data: QMimeData = super().mimeData(items)
        identifiers: list[str] = [
            formatted
            for item in items
            if (formatted := format_tree_item_identifier(item))
        ]
        if identifiers:
            mime_data.setText(", ".join(identifiers))
        return mime_data

class SQLSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighting for SQL syntax"""

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#c678dd"))
        self.keyword_format.setFontWeight(QFont.Weight.Bold)

        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#98c379"))

        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#7f848e"))
        self.comment_format.setFontItalic(True)

        keywords: list[str] = [
            "SELECT", "FROM", "WHERE", "AND", "OR", "JOIN", "INNER", "LEFT", "RIGHT",
            "OUTER", "ON", "GROUP BY", "ORDER BY", "HAVING", "LIMIT", "AS", "WITH", "ASC", "DESC"
                                                                                           "OUTER", "FULL", "CROSS", "ON", r"GROUP\s+BY", r"ORDER\s+BY", "HAVING",
            "LIMIT", "OFFSET", "AS", "WITH", "ASC", "DESC", "DISTINCT", "UNION",
            "ALL", "CASE", "WHEN", "THEN", "ELSE", "END", "IN", "IS", "NOT", "NULL",
            "VALUES", "TABLE"
        ]
        self.keyword_patterns = [re.compile(fr"\b{word}\b", re.IGNORECASE) for word in keywords]
        self.string_pattern = re.compile(r"'.*?'|\".*?\"")
        self.comment_pattern = re.compile(r"--[^\n]*|/\*.*?\*/")

    def highlightBlock(self, text: str) -> None:
        for pattern in self.keyword_patterns:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), self.keyword_format)

        for match in self.string_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.string_format)

        for match in self.comment_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.comment_format)

class DatabaseConnectionDialog(QDialog):
    """
    A dialog window for configuring, testing and establishing database connections

    This dialog provides an interface to connect to database engines (PostgreSQL, MySQL, SQLite, DuckDB)
    using either the builder or a URI. It also includes a SQL query editor and a schema viewer
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import from Database")
        self.setWindowIcon(IconBuilder.build(IconType.ImportDatabase))
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)

        self.details: dict[str, str] = {}
        self.settings = QSettings(f"{APPLICATION_NAME}", "DatabaseProfiles")
        self.threadpool = QThreadPool.globalInstance()
        self._active_connection_string: str = ""
        self._pending_column_items: dict[tuple[str, str], QTreeWidgetItem] = {}
        self._connection_generation: int = 0
        self._last_db_type: str = ""
        self._syncing_expanded_state: bool = False

        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget(self)

        self._setup_connection_tab()
        self._setup_query_tab()

        self.tab_widget.addTab(self.connection_tab, "1. Connection Settings")
        self.tab_widget.addTab(self.query_tab, "2. Query && Schema")
        main_layout.addWidget(self.tab_widget)

        self._setup_dialog_actions(main_layout)

        self.on_db_type_changed("SQLite")
        self.on_query_changed()

    def _setup_connection_tab(self) -> None:
        """Starts the connection configuratio tab"""
        self.connection_tab = QWidget()
        layout = QVBoxLayout(self.connection_tab)

        layout.addWidget(self._create_profiles_group())
        layout.addWidget(self._create_connection_setup_group())
        layout.addWidget(self._create_connection_details_group())
        layout.addWidget(self._create_test_connection_wrapper())
        layout.addStretch()

    def _create_profiles_group(self) -> QGroupBox:
        """Builds the saved connections profile group"""
        group = QGroupBox("Saved Connections", parent=self)
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel("Profile:"))
        self.profiles_combo = QComboBox()

        self.profiles_combo.currentIndexChanged.connect(self.load_profile)
        layout.addWidget(self.profiles_combo, 1)

        self.save_profile_button = QPushButton("Save", parent=self)
        self.save_profile_button.setToolTip("Save the current connection details")
        self.save_profile_button.clicked.connect(self.save_profile)
        layout.addWidget(self.save_profile_button)

        self.delete_profile_button = QPushButton("Delete", parent=self)
        self.delete_profile_button.setToolTip("Delete the selected profile")
        self.delete_profile_button.setEnabled(False)
        self.delete_profile_button.clicked.connect(self.delete_profile)
        layout.addWidget(self.delete_profile_button)
        self.populate_profiles()

        return group

    def _create_connection_setup_group(self) -> QGroupBox:
        """Builds the connection mode and database type selection group"""
        self.setup_group = QGroupBox("Connection Mode", parent=self)
        layout = QFormLayout(self.setup_group)

        self.mode_group = QButtonGroup(self)
        mode_radio_layout = QHBoxLayout()

        self.mode_builder_radio = QRadioButton("Connection Builder")
        self.mode_builder_radio.setChecked(True)
        self.mode_builder_radio.toggled.connect(self.toggle_connection_mode)
        self.mode_group.addButton(self.mode_builder_radio)
        mode_radio_layout.addWidget(self.mode_builder_radio)

        self.mode_uri_radio = QRadioButton("Raw Connection URI")
        self.mode_uri_radio.toggled.connect(self.toggle_connection_mode)
        self.mode_group.addButton(self.mode_uri_radio)
        mode_radio_layout.addWidget(self.mode_uri_radio)
        mode_radio_layout.addStretch()

        layout.addRow("Mode:", mode_radio_layout)

        self.db_type_label = QLabel("Database Type:")
        self.db_type_combo = QComboBox()
        self.db_type_combo.addItems(["SQLite", "DuckDB", "PostgreSQL", "MySQL"])
        self.db_type_combo.currentTextChanged.connect(self.on_db_type_changed)
        layout.addRow(self.db_type_label, self.db_type_combo)

        return self.setup_group

    def _create_connection_details_group(self) -> QGroupBox:
        """Builds the stacked widget group containing the inputs for either server or file inputs"""
        self.connection_group = QGroupBox("Connection Details", parent=self)
        layout = QVBoxLayout(self.connection_group)

        self.connection_stack = QStackedWidget(self)
        self.connection_stack.setObjectName("connectionStack")

        self.server_page = self._create_server_page()
        self.file_page = self._create_file_page()
        self.uri_page = self._create_uri_page()

        self.connection_stack.addWidget(self.server_page)
        self.connection_stack.addWidget(self.file_page)
        self.connection_stack.addWidget(self.uri_page)

        layout.addWidget(self.connection_stack)
        return self.connection_group

    def _create_test_connection_wrapper(self) -> QWidget:
        """Builds the layout for the test connection button and status indicators"""
        self.test_connection_wrapper = QWidget()
        layout = QHBoxLayout(self.test_connection_wrapper)
        layout.setContentsMargins(0, 0, 0, 0)

        self.db_icon_label = QLabel()
        self.db_icon_label.setFixedHeight(24)
        self.db_icon_label.setObjectName("db_icon_label")
        layout.addWidget(self.db_icon_label)

        self.connection_status_label = QLabel()
        self.connection_status_label.setObjectName("query_status_label")
        layout.addWidget(self.connection_status_label)

        layout.addStretch()

        self.test_connection_button = QPushButton("Test Connection", parent=self)
        self.test_connection_button.setToolTip("Test connection and load database schema")
        self.test_connection_button.clicked.connect(self.test_connection)
        layout.addWidget(self.test_connection_button)

        self.next_tab_button = QPushButton("Next: Query && Schema", parent=self)
        self.next_tab_button.setToolTip("Switch to the SQL Query and Schema tab")
        self.next_tab_button.clicked.connect(self._go_to_query_tab)
        layout.addWidget(self.next_tab_button)

        return self.test_connection_wrapper

    def _go_to_query_tab(self) -> None:
        """Switches to the qiuery and schema tab and focuses to the SQL editor"""
        self.tab_widget.setCurrentWidget(self.query_tab)
        self.query_editor.setFocus()

    def _setup_query_tab(self) -> None:
        """Initialises the SQL query editor, 5 roow query preview and the schema tree tab"""
        self.query_tab = QWidget()
        layout = QVBoxLayout(self.query_tab)

        self.query_preview_splitter = QSplitter(Qt.Orientation.Vertical)
        self.query_preview_splitter.setChildrenCollapsible(False)
        self.query_preview_splitter.addWidget(self._create_query_editor_group())
        self.query_preview_splitter.addWidget(self._create_query_preview_panel())
        self.query_preview_splitter.setStretchFactor(0, 1)
        self.query_preview_splitter.setStretchFactor(1, 1)
        self.query_preview_splitter.setSizes([250, 310])

        self.editors_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.editors_splitter.setChildrenCollapsible(False)
        self.editors_splitter.addWidget(self.query_preview_splitter)
        self.editors_splitter.addWidget(self._create_schema_viewer_group())

        self.editors_splitter.setStretchFactor(0, 3)
        self.editors_splitter.setStretchFactor(1, 2)

        layout.addWidget(self.editors_splitter, stretch=1)

    def _create_query_preview_panel(self) -> QueryPreviewPanel:
        """Build the 5 record preview and attach the controller"""
        self.query_preview_panel = QueryPreviewPanel(parent=self)
        self.preview_controller = DatabasePreviewController(
            preview_panel=self.query_preview_panel,
            threadpool=self.threadpool,
            parent=self
        )
        self.query_preview_panel.previewRequested.connect(self.preview_current_query)
        return self.query_preview_panel

    def _create_query_editor_group(self) -> QGroupBox:
        """Builds the SQL query text editor group"""
        group = QGroupBox("SQL Query", parent=self)
        layout = QVBoxLayout(group)

        instructions = (
            "Enter your SQL query below. Double-click or drag tables and columns from the schema tree.\n"
            "Supports SELECT statements, CTEs, TABLE and VALUES queries."
        )
        self.info_label = QLabel(instructions)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        self.query_editor = QTextEdit()
        self.query_editor.setObjectName("sqlQueryEditor")
        self.query_editor.setPlaceholderText("SELECT * FROM table_name...")
        self.sql_highlighter = SQLSyntaxHighlighter(self.query_editor.document())

        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        if fixed_font.pointSize() < 10:
            fixed_font.setPointSize(10)
        self.query_editor.setFont(fixed_font)
        font_metrics = self.query_editor.fontMetrics()
        self.query_editor.setTabStopDistance(float(font_metrics.horizontalAdvance(' ') * 4))
        self.query_editor.setMinimumHeight(110)
        self.query_editor.textChanged.connect(self.on_query_changed)
        layout.addWidget(self.query_editor)

        self.query_status_icon = QLabel()
        self.query_status_icon.setFixedSize(16, 16)
        self.query_status_label = QLabel(" ")
        self.query_status_label.setObjectName("query_status_label")

        status_layout = QHBoxLayout()
        status_layout.setSpacing(6)
        status_layout.addWidget(self.query_status_icon)
        status_layout.addWidget(self.query_status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        return group

    def _create_schema_viewer_group(self) -> QGroupBox:
        """Builds the database schema exploration tree group."""
        group = QGroupBox("Database Schema", parent=self)
        layout = QVBoxLayout(group)

        self.load_schema_button = QPushButton("Load Tables and Columns", parent=self)
        self.load_schema_button.setToolTip("Connect to the database and list all tables and columns")
        self.load_schema_button.clicked.connect(self.fetch_schema)
        layout.addWidget(self.load_schema_button)

        self.schema_search_input = QLineEdit(parent=self)
        self.schema_search_input.setPlaceholderText("Filter tables and loaded columns...")
        self.schema_search_input.setToolTip(
            "Filters table names and already-expanded columns. Expand a table first to search its columns"
        )
        self.schema_search_input.setClearButtonEnabled(True)
        self.schema_search_input.textChanged.connect(self.filter_schema_tree)
        self.schema_search_input.setVisible(False)
        layout.addWidget(self.schema_search_input)

        self.schema_tree = SchemaTreeWidget()
        self.schema_tree.setObjectName("databaseSchemaTree")
        self.schema_tree.setHeaderLabels(["Schema / Table / Column", "Type"])
        self.schema_tree.setAlternatingRowColors(True)
        self.schema_tree.setDragEnabled(True)
        self.schema_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.schema_tree.setToolTip(
            "Expand a table to load columns. Double-click, drag or right-click an item to insert it into the query"
        )
        self.schema_tree.itemExpanded.connect(self.on_schema_item_expanded)
        self.schema_tree.itemCollapsed.connect(self.on_schema_item_collapsed)
        self.schema_tree.itemDoubleClicked.connect(self.on_schema_double_clicked)
        self.schema_tree.customContextMenuRequested.connect(self.on_schema_context_menu)
        layout.addWidget(self.schema_tree)

        return group

    def _setup_dialog_actions(self, main_layout: QVBoxLayout) -> None:
        """Builds the bottom button box and shortcut actions."""
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setText("Import")
            ok_button.setObjectName("MainActionButton")
            ok_button.setToolTip("Accept and Import (Ctrl+Enter)")

        self.button_box.accepted.connect(self.on_accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.accept_shortcut_return = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.accept_shortcut_return.activated.connect(self.on_accept)

        self.accept_shortcut_enter = QShortcut(QKeySequence("Ctrl+Enter"), self)
        self.accept_shortcut_enter.activated.connect(self.on_accept)

        self.preview_shortcut_f5 = QShortcut(QKeySequence("F5"), self)
        self.preview_shortcut_f5.activated.connect(self.preview_current_query)

        self.preview_shortcut_return = QShortcut(QKeySequence("Ctrl+Shift+Return"), self)
        self.preview_shortcut_return.activated.connect(self.preview_current_query)

        self.preview_shortcut_enter = QShortcut(QKeySequence("Ctrl+Shift+Enter"), self)
        self.preview_shortcut_enter.activated.connect(self.preview_current_query)

    def _create_server_page(self) -> QWidget:
        """Creates the form layout for server-based databases (PostgreSQL, MySQL)."""
        page = QWidget()
        page.setObjectName("serverDatabasePage")
        layout = QFormLayout(page)

        self.host_label = QLabel("Host:")
        self.host_input = QLineEdit("localhost")
        self.host_input.setObjectName("hostInput")
        self.host_input.textChanged.connect(self.invalidate_connection_state)
        layout.addRow(self.host_label, self.host_input)

        self.port_label = QLabel("Port:")
        self.port_input = QLineEdit()
        self.port_input.setObjectName("portInput")
        self.port_validator = QIntValidator(1, 65535, self)
        self.port_input.setValidator(self.port_validator)
        self.port_input.textChanged.connect(self.invalidate_connection_state)
        layout.addRow(self.port_label, self.port_input)

        self.user_label = QLabel("User:")
        self.user_input = QLineEdit("postgres")
        self.user_input.setObjectName("userInput")
        self.user_input.textChanged.connect(self.invalidate_connection_state)
        layout.addRow(self.user_label, self.user_input)

        self.password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setObjectName("passwordInput")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.textChanged.connect(self.invalidate_connection_state)

        view_icon = IconBuilder.build(IconType.ViewItem)
        self.toggle_password_action = self.password_input.addAction(
            view_icon,
            QLineEdit.ActionPosition.TrailingPosition
        )
        self.toggle_password_action.setToolTip("Show or hide password")
        self.toggle_password_action.triggered.connect(self.toggle_password_visibility)
        layout.addRow(self.password_label, self.password_input)

        self.dbname_label = QLabel("Database:")
        self.dbname_input = QLineEdit("postgres")
        self.dbname_input.setObjectName("dbnameInput")
        self.dbname_input.textChanged.connect(self.invalidate_connection_state)
        layout.addRow(self.dbname_label, self.dbname_input)

        return page

    def _create_file_page(self) -> QWidget:
        """Creates the layout for file-based databases (SQLite, DuckDB)."""
        page = QWidget()
        page.setObjectName("fileDatabasePage")
        layout = QFormLayout(page)

        self.file_db_label = QLabel("Database File:")

        file_layout = QHBoxLayout()
        file_layout.setContentsMargins(0, 0, 0, 0)

        self.file_db_path_input = QLineEdit()
        self.file_db_path_input.setObjectName("fileDbPathInput")
        self.file_db_path_input.setPlaceholderText("Click 'Browse' to select a database file")
        self.file_db_path_input.textChanged.connect(self.invalidate_connection_state)

        self.file_db_browse_button = QPushButton("Browse", parent=self)
        self.file_db_browse_button.setObjectName("fileDbBrowseButton")
        self.file_db_browse_button.clicked.connect(self.browse_file_db)

        file_layout.addWidget(self.file_db_path_input)
        file_layout.addWidget(self.file_db_browse_button)

        layout.addRow(self.file_db_label, file_layout)
        return page

    def _create_uri_page(self) -> QWidget:
        """Creates the layout for raw URI connections."""
        page = QWidget()
        page.setObjectName("uriDatabasePage")
        layout = QFormLayout(page)

        self.uri_label = QLabel("Connection URI:")
        self.uri_input = QLineEdit()
        self.uri_input.setObjectName("uriInput")
        self.uri_input.setPlaceholderText("dialect+driver://username:password@host:port/database")
        self.uri_input.textChanged.connect(self.invalidate_connection_state)

        view_icon = IconBuilder.build(IconType.ViewItem)
        self.toggle_uri_visibility_action = self.uri_input.addAction(
            view_icon,
            QLineEdit.ActionPosition.TrailingPosition
        )
        self.toggle_uri_visibility_action.setToolTip("Show or hide URI credentials")
        self.toggle_uri_visibility_action.triggered.connect(self.toggle_uri_visibility)
        layout.addRow(self.uri_label, self.uri_input)

        return page

    def invalidate_connection_state(self) -> None:
        """Clears the schema, preview and connection status when connection parameters change"""
        self._connection_generation += 1
        if hasattr(self, "preview_controller"):
            self.preview_controller.reset()

        has_status: bool = bool(self.connection_status_label.text())
        has_schema: bool = bool(self._active_connection_string) or self.schema_tree.topLevelItemCount() > 0

        if not has_status and not has_schema:
            return

        self.connection_status_label.clear()
        self.connection_status_label.setProperty("status", "")
        self.connection_status_label.style().unpolish(self.connection_status_label)
        self.connection_status_label.style().polish(self.connection_status_label)

        self.test_connection_button.setEnabled(True)
        self.test_connection_button.setText("Test Connection")
        self.setCursor(Qt.CursorShape.ArrowCursor)

        self.schema_tree.clear()
        self.schema_search_input.clear()
        self.schema_search_input.setVisible(False)
        self.load_schema_button.setEnabled(True)
        self.load_schema_button.setText("Load Tables and Columns")
        self._active_connection_string = ""
        self._pending_column_items.clear()

    def test_connection(self) -> None:
        """
        Tests the configured database connection asynchronously using SQLAlchemy

        Validates the current connection inputs and launches a background worker
        """
        try:
            connection_string: str = self._build_connection_string()
            self._connection_generation += 1
            generation: int = self._connection_generation

            self.setCursor(Qt.CursorShape.WaitCursor)
            self.test_connection_button.setEnabled(False)
            self.test_connection_button.setText("Testing...")

            self.connection_status_label.setText("Connecting...")
            self.connection_status_label.setProperty("status", "")
            self.connection_status_label.style().unpolish(self.connection_status_label)
            self.connection_status_label.style().polish(self.connection_status_label)

            worker = TestConnectionWorker(connection_string)
            worker.signals.finished.connect(
                lambda _ok, gen=generation: self._handle_test_connection_success(gen)
            )
            worker.signals.error.connect(
                lambda err, gen=generation: self._handle_test_connection_error(err, gen)
            )
            self.threadpool.start(worker)
        except ValueError as input_error:
            self._reset_test_ui_state()
            global_signals.request_toast(
                "Input Error", f"Connection failed: {str(input_error)}", ToastLevel.ERROR
            )

    def _reset_test_ui_state(self) -> None:
        """Resets the UI elements for the test connection phase"""
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.test_connection_button.setEnabled(True)
        self.test_connection_button.setText("Test Connection")
        self.connection_status_label.setText("")

    def _handle_test_connection_success(self, generation: int) -> None:
        if generation != self._connection_generation:
            return
        self.on_test_connection_success()

    def _handle_test_connection_error(self, error: Exception | str, generation: int) -> None:
        if generation != self._connection_generation:
            return
        self.on_test_connection_error(error)

    def on_test_connection_success(self) -> None:
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.test_connection_button.setEnabled(True)
        self.test_connection_button.setText("Test Connection")
        self.db_icon_label.setToolTip("Connected")

        self.connection_status_label.setText("Connection successful")
        self.connection_status_label.setProperty("status", "valid")
        self.connection_status_label.style().unpolish(self.connection_status_label)
        self.connection_status_label.style().polish(self.connection_status_label)

        self.fetch_schema()

    def on_test_connection_error(self, error: Exception | str) -> None:
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.test_connection_button.setEnabled(True)
        self.test_connection_button.setText("Test Connection")

        self.connection_status_label.setText("Connection failed")
        self.connection_status_label.setProperty("status", "invalid")
        self.connection_status_label.style().unpolish(self.connection_status_label)
        self.connection_status_label.style().polish(self.connection_status_label)

        global_signals.request_toast(
            "Connection Error",
            f"Could not connect to the database:\n{str(error)}",
            ToastLevel.ERROR
        )

    def fetch_schema(self) -> None:
        """
        Connects to the database asynchronously and populates the schema tree

        Constructs the connection string and uses a background thread to
        fetch tables and columns
        """
        try:
            connection_string: str = self._build_connection_string()
            self._active_connection_string = connection_string
            self._pending_column_items.clear()
            generation: int = self._connection_generation

            self.setCursor(Qt.CursorShape.WaitCursor)
            self.load_schema_button.setEnabled(False)
            self.load_schema_button.setText("Loading schema...")
            self.schema_tree.clear()
            self.schema_search_input.clear()
            self.schema_search_input.setVisible(False)

            worker = FetchSchemaWorker(connection_string=connection_string)
            worker.signals.finished.connect(
                lambda data, gen=generation: self._handle_fetch_schema_success(data, gen)
            )
            worker.signals.error.connect(
                lambda err, gen=generation: self._handle_fetch_schema_error(err, gen)
            )

            self.threadpool.start(worker)
        except ValueError as DatabaseValueError:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            global_signals.request_toast(
                "Connection Details Missing",
                str(DatabaseValueError),
                ToastLevel.WARNING
            )
            global_signals.request_log(
                f"Error fetching schema for database: {str(DatabaseValueError)}",
                "ERROR"
            )

    def _handle_fetch_schema_success(self, schema_data: list[SchemaTableGroup], generation: int) -> None:
        if generation != self._connection_generation:
            return
        self.on_fetch_schema_success(schema_data)

    def _handle_fetch_schema_error(self, error_message: str, generation: int) -> None:
        if generation != self._connection_generation:
            return
        self.on_fetch_schema_error(error_message)

    def _create_table_tree_item(
            self,
            parent: QTreeWidget | QTreeWidgetItem,
            schema_name: str,
            table_name: str,
    ) -> QTreeWidgetItem:
        table_item: QTreeWidgetItem = QTreeWidgetItem(parent)
        table_item.setText(0, table_name)
        table_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        table_item.setData(0, SchemaTreeRole.NODE_TYPE, SchemaNodeType.TABLE.value)
        table_item.setData(0, SchemaTreeRole.SCHEMA_NAME, schema_name)
        table_item.setData(0, SchemaTreeRole.TABLE_NAME, table_name)
        table_item.setData(0, SchemaTreeRole.IS_LOADED, False)
        table_item.setData(0, SchemaTreeRole.USER_EXPANDED, False)

        placeholder: QTreeWidgetItem = QTreeWidgetItem(table_item)
        placeholder.setText(0, LOADING_PLACEHOLDER_TEXT)
        placeholder.setData(0, SchemaTreeRole.NODE_TYPE, SchemaNodeType.PLACEHOLDER.value)
        placeholder.setFlags(Qt.ItemFlag.ItemIsEnabled)
        return table_item

    def on_fetch_schema_success(self, schema_data: list[SchemaTableGroup]) -> None:
        """Populates the schema tree with fetched data"""
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.load_schema_button.setEnabled(True)
        self.load_schema_button.setText("Load Tables and Columns")
        self.schema_search_input.setVisible(True)

        total_tables: int = 0
        for group in schema_data:
            schema_name: str | None = group["schema"]
            tables: list[str] = group["tables"]
            total_tables += len(tables)

            if schema_name is None:
                for table_name in tables:
                    self._create_table_tree_item(self.schema_tree, "", table_name)
                continue

            schema_item: QTreeWidgetItem = QTreeWidgetItem(self.schema_tree)
            schema_item.setText(0, schema_name)
            schema_item.setText(1, f"{len(tables)} table(s)")
            schema_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DriveHDIcon))
            schema_item.setData(0, SchemaTreeRole.NODE_TYPE, SchemaNodeType.SCHEMA.value)
            schema_item.setData(0, SchemaTreeRole.SCHEMA_NAME, schema_name)

            if not tables:
                empty_item: QTreeWidgetItem = QTreeWidgetItem(schema_item)
                empty_item.setText(0, NO_TABLES_TEXT)
                empty_item.setData(0, SchemaTreeRole.NODE_TYPE, SchemaNodeType.PLACEHOLDER.value)
                empty_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                continue

            for table_name in tables:
                self._create_table_tree_item(schema_item, schema_name, table_name)

            if schema_name.lower() in ("public", "main") or len(schema_data) == 1:
                schema_item.setExpanded(True)

        self.schema_tree.resizeColumnToContents(0)
        global_signals.request_toast(
            "Schema Loaded",
            f"Loaded {total_tables} table(s). Expand a table to inspect columns.",
            ToastLevel.SUCCESS,
        )

    def on_schema_item_expanded(self, item: QTreeWidgetItem) -> None:
        """Trigger loading of column when unloaded table is expanded"""
        if item.data(0, SchemaTreeRole.NODE_TYPE) != SchemaNodeType.TABLE.value:
            return
        if not self._syncing_expanded_state:
            item.setData(0, SchemaTreeRole.USER_EXPANDED, True)
        if bool(item.data(0, SchemaTreeRole.IS_LOADED)):
            return
        if not self._active_connection_string:
            return

        schema_name: str = str(item.data(0, SchemaTreeRole.SCHEMA_NAME) or "")
        table_name: str = str(item.data(0, SchemaTreeRole.TABLE_NAME) or "")
        request_key: tuple[str, str] = (schema_name, table_name)

        if request_key in self._pending_column_items:
            return

        self._pending_column_items[request_key] = item
        generation: int = self._connection_generation
        worker: FetchColumnWorker = FetchColumnWorker(
            connection_string=self._active_connection_string,
            table_name=table_name,
            schema_name=schema_name or None,
        )
        worker.signals.columnsLoaded.connect(
            lambda s_name, t_name, cols, gen=generation: self._handle_fetch_columns_success(
                s_name, t_name, cols, gen
            )
        )
        worker.signals.loadFailed.connect(
            lambda s_name, t_name, err, gen=generation: self._handle_fetch_columns_error(
                s_name, t_name, err, gen
            )
        )
        self.threadpool.start(worker)

    def on_schema_item_collapsed(self, item: QTreeWidgetItem) -> None:
        """Track table collapse so search reset restores correct state"""
        if item.data(0, SchemaTreeRole.NODE_TYPE) != SchemaNodeType.TABLE.value:
            return
        if not self._syncing_expanded_state:
            item.setData(0, SchemaTreeRole.USER_EXPANDED, False)

    def _handle_fetch_columns_success(
            self,
            schema_name: str,
            table_name: str,
            columns: list[ColumnMetadata],
            generation: int
    ) -> None:
        if generation != self._connection_generation:
            return
        self.on_fetch_columns_success(schema_name, table_name, columns)

    def _handle_fetch_columns_error(
            self,
            schema_name: str,
            table_name: str,
            error_message: str,
            generation: int
    ) -> None:
        if generation != self._connection_generation:
            return
        self.on_fetch_columns_error(schema_name, table_name, error_message)

    def on_fetch_columns_success(
            self,
            schema_name: str,
            table_name: str,
            columns: list[ColumnMetadata],
    ) -> None:
        table_item: QTreeWidgetItem | None = self._pending_column_items.pop((schema_name, table_name), None)
        if table_item is None or table_item.treeWidget() is not self.schema_tree:
            return

        table_item.takeChildren()
        table_item.setData(0, SchemaTreeRole.IS_LOADED, True)

        if not columns:
            empty_item: QTreeWidgetItem = QTreeWidgetItem(table_item)
            empty_item.setText(0, NO_COLUMNS_TEXT)
            empty_item.setData(0, SchemaTreeRole.NODE_TYPE, SchemaNodeType.PLACEHOLDER.value)
            empty_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            return

        for col in columns:
            col_item: QTreeWidgetItem = QTreeWidgetItem(table_item)
            col_item.setText(0, col["name"])
            col_item.setText(1, col["type"])
            col_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
            col_item.setData(0, SchemaTreeRole.NODE_TYPE, SchemaNodeType.COLUMN.value)
            col_item.setData(0, SchemaTreeRole.SCHEMA_NAME, schema_name)
            col_item.setData(0, SchemaTreeRole.TABLE_NAME, table_name)

        active_search: str = self.schema_search_input.text().strip().lower()
        if active_search:
            self._filter_table_item(table_item, active_search)

    def on_fetch_columns_error(self, schema_name: str, table_name: str, error_message: str) -> None:
        table_item: QTreeWidgetItem | None = self._pending_column_items.pop((schema_name, table_name), None)
        if table_item is not None and table_item.treeWidget() is self.schema_tree:
            table_item.takeChildren()
            err_item: QTreeWidgetItem = QTreeWidgetItem(table_item)
            err_item.setText(0, FAILED_COLUMNS_TEXT)
            err_item.setData(0, SchemaTreeRole.NODE_TYPE, SchemaNodeType.PLACEHOLDER.value)
            err_item.setFlags(Qt.ItemFlag.ItemIsEnabled)

        qualified_name: str = f"{schema_name}.{table_name}" if schema_name else table_name
        global_signals.request_toast(
            "Column Load Error",
            f"Failed to load columns for '{qualified_name}'.",
            ToastLevel.ERROR,
        )
        global_signals.request_log(
            f"Failed to load columns for '{qualified_name}': {error_message}",
            "ERROR",
        )

    def on_fetch_schema_error(self, error_message: str) -> None:
        """Handles errors during asynch schema fetch"""
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.load_schema_button.setEnabled(True)
        self.load_schema_button.setText("Load Tables and Columns")

        global_signals.request_toast(
            "Error",
            f"Failed to fetch schema for the database:\n{error_message}",
            ToastLevel.ERROR
        )
        global_signals.request_log(
            f"Failed to fetch schema for the database:{str(error_message)}",
            "ERROR"
        )

    def _filter_table_item(
            self,
            table_item: QTreeWidgetItem,
            search_term: str,
            force_visible: bool = False
    ) -> bool:
        table_match: bool = force_visible or (search_term in table_item.text(0).lower())
        is_loaded: bool = bool(table_item.data(0, SchemaTreeRole.IS_LOADED))

        if not is_loaded:
            table_item.setHidden(not table_match)
            return table_match

        child_match: bool = False
        for idx in range(table_item.childCount()):
            col_item: QTreeWidgetItem = table_item.child(idx)
            is_col_match: bool = force_visible or (search_term in col_item.text(0).lower())
            col_item.setHidden(not (is_col_match or (table_match or not search_term)))
            if is_col_match:
                child_match = True

        is_visible: bool = table_match or child_match
        table_item.setHidden(not is_visible)

        self._syncing_expanded_state = True
        try:
            if child_match and search_term and not force_visible:
                table_item.setExpanded(True)
            elif not search_term:
                user_expanded: bool = bool(table_item.data(0, SchemaTreeRole.USER_EXPANDED))
                table_item.setExpanded(user_expanded)
        finally:
            self._syncing_expanded_state = False

        return is_visible

    def filter_schema_tree(self, text: str) -> None:
        """
        Filters the schema tree widget based on the search query

        Hides tables and columns that do not match the provided query.
        :param text: The search term to filter for.
        """
        search_term: str = text.lower().strip()

        for i in range(self.schema_tree.topLevelItemCount()):
            top_item: QTreeWidgetItem | None = self.schema_tree.topLevelItem(i)
            if top_item is None:
                continue

            node_type: str = str(top_item.data(0, SchemaTreeRole.NODE_TYPE) or "")
            if node_type != SchemaNodeType.SCHEMA.value:
                self._filter_table_item(top_item, search_term)
                continue

            schema_match: bool = bool(search_term) and (search_term in top_item.text(0).lower())
            any_child_visible: bool = False

            for j in range(top_item.childCount()):
                child_item: QTreeWidgetItem = top_item.child(j)
                if child_item.data(0, SchemaTreeRole.NODE_TYPE) == SchemaNodeType.PLACEHOLDER.value:
                    child_item.setHidden(bool(search_term) and not schema_match)
                    continue
                if self._filter_table_item(child_item, search_term, force_visible=schema_match):
                    any_child_visible = True

            is_schema_visible: bool = (not search_term) or schema_match or any_child_visible
            top_item.setHidden(not is_schema_visible)
            if search_term and is_schema_visible:
                top_item.setExpanded(True)

    @staticmethod
    def _format_sql_identifier(name: str) -> str:
        """Quote SQL identifiers that contain spaces, symbols, or leading digits."""
        return format_sql_identifier(name)

    @staticmethod
    def _should_prepend_command(text_before_cursor: str) -> bool:
        """Determine whether inserting an identifier at the cursor requires a leading comma"""
        stripped: str = text_before_cursor.rstrip()
        if not stripped:
            return False
        if not re.search(r'[\w\'*]$', stripped):
            return False

        last_word_match = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*)$", stripped)
        if last_word_match:
            last_word: str = last_word_match.group(1).upper()
            if last_word in SQL_CLAUSE_PRECEDING_KEYWORDS:
                return False

        return True

    def _insert_identifier_into_query(self, identifier: str) -> None:
        """Insert a formatted SQL identifier at the current cursor position"""
        if not identifier:
            return
        cursor = self.query_editor.textCursor()
        full_text: str = self.query_editor.toPlainText()
        text_before_cursor: str = full_text[:cursor.position()]

        insert_text: str = identifier
        if self._should_prepend_command(text_before_cursor):
            if text_before_cursor.endswith((" ", "\t", "\n")):
                stripped_len: int = len(text_before_cursor.rstrip(" \t"))
                cursor.setPosition(stripped_len)
                cursor.setPosition(len(text_before_cursor), cursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()
                self.query_editor.setTextCursor(cursor)
            insert_text = f", {identifier}"
        elif text_before_cursor and not text_before_cursor[-1].isspace() and text_before_cursor[-1] != "(":
            insert_text = f" {identifier}"

        self.query_editor.insertPlainText(f"{insert_text}")
        self.query_editor.setFocus()

    def on_schema_double_clicked(self, item: QTreeWidgetItem) -> None:
        """Insert the clicked item into the SQL query editor, scaffoleded with SELECT * FROM if empty"""
        node_type: str = str(item.data(0, SchemaTreeRole.NODE_TYPE) or "")
        if node_type not in (SchemaNodeType.TABLE.value, SchemaNodeType.COLUMN.value):
            return

        identifier: str = format_tree_item_identifier(item, qualified=True)
        if not identifier:
            return

        if node_type == SchemaNodeType.TABLE.value and not self.query_editor.toPlainText().strip():
            self.query_editor.setPlainText(f"SELECT * FROM {identifier}")
            cursor = self.query_editor.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.query_editor.setTextCursor(cursor)
            self.query_editor.setFocus()
            return

        self._insert_identifier_into_query(identifier)

    def on_schema_context_menu(self, position: QPoint) -> None:
        """Display a context menu with SQL generation and insertion shortcuts for schemaitems"""
        item: QTreeWidgetItem | None = self.schema_tree.itemAt(position)
        if item is None:
            return

        node_type: str = str(item.data(0, SchemaTreeRole.NODE_TYPE) or "")
        if node_type not in (SchemaNodeType.TABLE.value, SchemaNodeType.COLUMN.value):
            return

        qualified_id: str = format_tree_item_identifier(item, qualified=True)
        menu = QMenu(self)

        if node_type == SchemaNodeType.TABLE.value:
            preview_top_action: QAction = menu.addAction(f"Preview Top {PREVIEW_ROW_LIMIT} Rows")
            menu.addSeparator()
            select_all_action: QAction = menu.addAction(f"SELECT * FROM {qualified_id}")
            select_top_action: QAction = menu.addAction(f"SELECT * FROM {qualified_id} LIMIT 100")
            menu.addSeparator()
            insert_table_action: QAction = menu.addAction("Insert Table Name")

            chosen: QAction | None = menu.exec(self.schema_tree.viewport().mapToGlobal(position))
            if chosen == preview_top_action:
                table_select_sql: str = f"SELECT * FROM {qualified_id}"
                if not self.query_editor.toPlainText().strip():
                    self.query_editor.setPlainText(table_select_sql)
                    self._preview_sql_query(table_select_sql)
                else:
                    self._preview_sql_query(table_select_sql, source_label=qualified_id)
            elif chosen == select_all_action:
                self.query_editor.setPlainText(f"SELECT * FROM {qualified_id}")
                self.query_editor.setFocus()
            elif chosen == select_top_action:
                self.query_editor.setPlainText(f"SELECT * FROM {qualified_id} LIMIT 100")
                self.query_editor.setFocus()
            elif chosen == insert_table_action:
                self._insert_identifier_into_query(qualified_id)
        else:
            unqualified_id: str = format_tree_item_identifier(item, qualified=False)
            insert_col_action: QAction = menu.addAction(f"Insert Column ({unqualified_id})")
            insert_qualified_action: QAction = menu.addAction(f"Insert Qualified ({unqualified_id})")

            chosen = menu.exec(self.schema_tree.viewport().mapToGlobal(position))
            if chosen == insert_col_action:
                self._insert_identifier_into_query(unqualified_id)
            elif chosen == insert_qualified_action:
                self._insert_identifier_into_query(qualified_id)

    def _build_connection_string(self) -> str:
        """
        Constructs a SQLAlchemy-compatible connection string.

        Validates the user input based on database type and connection mode
        and formats the standard URI required by the database engine

        :return: The constructed database connection string
        :raises ValueError: If required details are missing, invalid or file does not exist
        """
        if self.mode_uri_radio.isChecked():
            uri: str = self.uri_input.text().strip()
            if not uri:
                raise ValueError("Please provide a valid Connection URI")
            try:
                make_url(uri)
            except ArgumentError as err:
                raise ValueError(f"Invalid Connection URI format: {err}") from err
            return uri

        db_type: str = self.db_type_combo.currentText()

        if db_type in ("SQLite", "DuckDB"):
            db_path: str = self.file_db_path_input.text().strip()
            if not db_path:
                raise ValueError(f"Please provide a path to the {db_type} database file.")

            path_obj: Path = Path(db_path).expanduser().resolve()
            if not path_obj.exists():
                raise ValueError(f"The {db_type} database file does not exist: '{db_path}'")
            if not path_obj.is_file():
                raise ValueError(f"The {db_type} databasefile is not a file: '{db_path}'")

            prefix: str = "sqlite" if db_type == "SQLite" else "duckdb"
            return f"{prefix}:///{path_obj.as_posix()}"

        host = self.host_input.text().strip()
        port_str = self.port_input.text().strip()
        user = self.user_input.text().strip()
        password = self.password_input.text().strip()
        dbname = self.dbname_input.text().strip()

        if not all([host, port_str, user, dbname]):
            raise ValueError("Please fill in all connection details (Host, Port, User, DatabaseName)")

        try:
            port_num: int = int(port_str)
        except ValueError as err:
            raise ValueError("Port must be a valid integer between 0 and 65535") from err

        driver_map: dict[str, str] = {
            "PostgreSQL": "postgresql+psycopg2",
            "MySQL"     : "mysql+mysqlconnector"
        }
        drivername: str = driver_map.get(db_type, "postgresql+psycopg2")
        url_obj: URL = URL.create(
            drivername=drivername,
            username=user,
            password=password if password else None,
            host=host,
            port=port_num,
            database=dbname
        )
        return url_obj.render_as_string(hide_password=False)

    def preview_current_query(self) -> None:
        """Validate current input and execute the SQL of the query editor to populate the preview"""
        if self.preview_controller.is_loading:
            return

        query: str = self.query_editor.toPlainText().strip()
        if not query:
            self._go_to_query_tab()
            global_signals.request_toast(
                "Query Empty",
                f"Please enter a SQL query to preview the first {PREVIEW_ROW_LIMIT} records",
                ToastLevel.WARNING
            )
            return

        if not self._is_valid_select_query(query):
            self._go_to_query_tab()
            global_signals.request_toast(
                "Invalid Query",
                "The SQL query must be a single read-only SELECT, WITH, TABLE or VALUES query",
                ToastLevel.WARNING
            )
            return

        if self.tab_widget.currentWidget() is not self.query_tab:
            self._go_to_query_tab()

        self._preview_sql_query(query)

    def _preview_sql_query(self, query: str, source_label: str = "") -> None:
        """Build the SQLAlchemy URI and dispatch an asynchronous bounded query preview."""
        try:
            connection_string: str = self._build_connection_string()
        except ValueError as input_err:
            self.tab_widget.setCurrentWidget(self.connection_tab)
            global_signals.request_toast(
                "Connection Details Missing",
                str(input_err),
                ToastLevel.WARNING
            )
            global_signals.request_log(
                f"Query preview blocked due to connection error: {input_err}",
                LogLevel.ERROR
            )
            return

        self.preview_controller.execute_preview(
            connection_string=connection_string,
            query=query,
            source_label=source_label
        )

    def on_query_changed(self) -> None:
        """Validate the query and synch preview availability and state"""
        if hasattr(self, "query_preview_panel"):
            self.query_preview_panel.mark_state_if_populated()

        query: str = self.query_editor.toPlainText().strip()

        if not query:
            self._set_query_status(
                "Query cannot be empty",
                valid=False
            )
            self.preview_controller.set_query_valid(False)
            return

        is_valid: bool = self._is_valid_select_query(query)
        self.preview_controller.set_query_valid(is_valid)

        if is_valid:
            self._set_query_status(
                "Valid query",
                valid=True
            )
        else:
            self._set_query_status(
                "Invalid query (Must be a SELECT, WITH, TABLE, or VALUES query)",
                valid=False
            )

    @staticmethod
    def _is_valid_select_query(query: str) -> bool:
        """Checks if the query entered is a valid read-only data query

        :param query: Raw SQL text from the query editor
        :returns bool: Returns True if the query is a valid read-only query
        """
        return is_valid_readonly_query(query)

    def _set_query_status(self, message: str, *, valid: bool) -> None:
        """Sets the status icon and status label based on whether the expression is valid"""
        style = self.style()

        if valid:
            icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
            status_state = "valid"
        else:
            icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)
            status_state = "invalid"

        self.query_status_icon.setPixmap(icon.pixmap(16, 16))
        self.query_status_label.setText(f"{message}")

        self.query_status_label.setProperty("status", status_state)
        self.query_status_label.style().unpolish(self.query_status_label)
        self.query_status_label.style().polish(self.query_status_label)

        self.query_status_icon.setVisible(True)
        self.query_status_label.setVisible(True)

        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setEnabled(valid)

    def on_db_type_changed(self, db_type: str) -> None:
        """Switches the visible page in the stacked widget based on database type."""
        self.invalidate_connection_state()
        if self.mode_uri_radio.isChecked():
            return

        db_configs: dict[str, dict[str, str | bool]] = {
            "PostgreSQL": {
                "is_file": False,
                "port"   : "5432",
                "user"   : "postgres",
                "dbname" : "postgres",
                "icon"   : "../icons/database_icons/postgresql-inc.svg"
            },
            "MySQL"     : {
                "is_file": False,
                "port"   : "3306",
                "user"   : "root",
                "dbname" : "",
                "icon"   : "../icons/database_icons/mysql-3.svg"
            },
            "DuckDB"    : {
                "is_file"    : True,
                "placeholder": "Click 'Browse' to select a DuckDB file (.db, .duckdb)",
                "icon"       : "../icons/database_icons/duckdb-logo.svg"
            },
            "SQLite"    : {
                "is_file"    : True,
                "placeholder": "Click 'Browse' to select a SQLite file (.db, .sqlite, .sqlite3)",
                "icon"       : "../icons/database_icons/sqlite.svg"
            }
        }

        config: dict[str, str | bool] = db_configs.get(db_type, {})
        prev_config: dict[str, str | bool] = db_configs.get(self._last_db_type, {})
        self._last_db_type = db_type

        if bool(config.get("is_file", False)):
            self.connection_stack.setCurrentWidget(self.file_page)
            self.file_db_path_input.setPlaceholderText(str(config.get("placeholder", "")))
        else:
            self.connection_stack.setCurrentWidget(self.server_page)
            prev_port: str = str(prev_config.get("port", ""))
            prev_user: str = str(prev_config.get("user", ""))
            prev_dbname: str = str(prev_config.get("dbname", ""))

            current_port: str = self.port_input.text().strip()
            if not current_port or current_port == prev_port:
                self.port_input.setText(str(config.get("port", "")))

            current_user: str = self.user_input.text().strip()
            if not current_user or current_user == prev_user:
                self.user_input.setText(str(config.get("user", "")))

            current_dbname: str = self.dbname_input.text().strip()
            if not current_dbname or current_dbname == prev_dbname:
                self.dbname_input.setText(str(config.get("dbname", "")))

        raw_icon: str = str(config.get("icon", ""))
        icon_path: str = get_resource_path(raw_icon) if raw_icon else ""
        if not icon_path or not Path(icon_path).exists():
            icon_path = get_resource_path("../icons/menu_bar/database.svg")

        if Path(icon_path).exists():
            pixmap = QPixmap(icon_path)
            scaled_pixmap = pixmap.scaledToHeight(24, Qt.TransformationMode.SmoothTransformation)
            self.db_icon_label.setPixmap(scaled_pixmap)
            self.db_icon_label.setToolTip(f"{db_type} Database")
        else:
            self.db_icon_label.clear()

    def browse_file_db(self) -> None:
        """Open a file dialog to find a local SQLite or DuckDB database file"""
        current_database_type = self.db_type_combo.currentText()

        filters = "All Files (*)"
        if current_database_type == "SQLite":
            filters = "SQLite Files (*.db *.sqlite *.sqlite3);;All Files (*)"
        elif current_database_type == "DuckDB":
            filters = "DuckDB Files (*.db *.duckdb);;All Files (*)"

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            f"Select {current_database_type} Database file",
            "",
            filters
        )
        if filepath:
            self.file_db_path_input.setText(filepath)

    def on_accept(self) -> None:
        """Validate the input and build connection string before acception"""
        db_type: str = "URI" if self.mode_uri_radio.isChecked() else self.db_type_combo.currentText()
        query: str = self.query_editor.toPlainText().strip()

        if not query:
            self._go_to_query_tab()
            global_signals.request_toast(
                "Query Empty",
                "Please enter a SQL query in the Query & Schema tab",
                ToastLevel.WARNING
            )
            return

        if not self._is_valid_select_query(query):
            self._go_to_query_tab()
            global_signals.request_toast(
                "Invalid Query",
                "The SQL query must be a valid SELECT, WITH, TABLE or VALUES query",
                ToastLevel.WARNING
            )
            return

        try:
            connection_string: str = self._build_connection_string()

            self.details = {
                "db_type"          : db_type,
                "connection_string": connection_string,
                "query"            : query
            }
            self.accept()

        except ValueError as input_error:
            self.tab_widget.setCurrentWidget(self.connection_tab)
            global_signals.request_toast(
                "Input Error", f"{str(input_error)}", ToastLevel.ERROR
            )
            global_signals.request_log(f"Input Error: {str(input_error)}", "ERROR")
        except (OSError, RuntimeError) as conn_err:
            global_signals.request_toast(
                "Connection Error", "Failed to establish connection", ToastLevel.ERROR
            )
            global_signals.request_log(
                f"Failed to establish connection string: {str(conn_err)}", "ERROR"
            )

    def get_details(self) -> tuple[str, str, str]:
        """
        Retrieves the confirmed connection details and query after the dialog is accepted

        :return: A tuple containing the database type, connection string and SQL query
        """
        return (
            self.details.get("db_type"),
            self.details.get("connection_string"),
            self.details.get("query")
        )

    def toggle_connection_mode(self) -> None:
        """Switches the UI states"""
        self.invalidate_connection_state()
        is_uri_mode: bool = self.mode_uri_radio.isChecked()

        self.db_type_combo.setVisible(not is_uri_mode)
        self.db_type_label.setVisible(not is_uri_mode)

        if is_uri_mode:
            self.connection_stack.setCurrentWidget(self.uri_page)
        else:
            self.on_db_type_changed(self.db_type_combo.currentText())

    def populate_profiles(self) -> None:
        self.profiles_combo.blockSignals(True)
        self.profiles_combo.clear()
        self.profiles_combo.addItem("Select a profile...", None)

        self.settings.beginGroup("DatabaseProfiles")
        profiles: list[str] = self.settings.childGroups()
        self.settings.endGroup()

        for profile in profiles:
            self.profiles_combo.addItem(profile, profile)
        self.profiles_combo.blockSignals(False)

        if hasattr(self, "delete_profile_button"):
            self.delete_profile_button.setEnabled(False)

    def save_profile(self) -> None:
        """Save the current connection details to a profile"""
        current_profile: str = str(self.profiles_combo.currentData() or "")
        name, ok = QInputDialog.getText(
            self,
            "Save Profile",
            "Enter profile name",
            QLineEdit.EchoMode.Normal,
            current_profile
        )
        if not ok:
            return

        name = name.strip()
        if not name:
            global_signals.request_toast("Warning", "Profile name cannot be empty", ToastLevel.WARNING)
            return

        is_uri: bool = self.mode_uri_radio.isChecked()
        safe_uri: str = ""
        db_password: str = ""

        if is_uri:
            raw_uri: str = self.uri_input.text().strip()
            if raw_uri:
                try:
                    parsed_url = make_url(raw_uri)
                    db_password = parsed_url.password or ""
                    safe_url = parsed_url.set(password=None)
                    safe_uri = safe_url.render_as_string(hide_password=False)
                except ArgumentError as uri_err:
                    logging.getLogger(__name__).warning("URI Parse Error: %s", uri_err)
                    global_signals.request_toast(
                        "Could Not Parse URI", "Unable to parse the URI given", ToastLevel.WARNING
                    )
                    safe_uri = raw_uri
        else:
            db_password = self.password_input.text()

        data: dict[str, str] = {
            "mode"     : "uri" if is_uri else "builder",
            "uri"      : safe_uri,
            "db_type"  : self.db_type_combo.currentText(),
            "host"     : self.host_input.text(),
            "port"     : self.port_input.text(),
            "user"     : self.user_input.text(),
            "dbname"   : self.dbname_input.text(),
            "file_path": self.file_db_path_input.text()
        }

        self.settings.beginGroup("DatabaseProfiles")
        self.settings.beginGroup(name)
        for key, val in data.items():
            self.settings.setValue(key, val)
        self.settings.endGroup()
        self.settings.endGroup()

        if db_password:
            try:
                keyring.set_password(
                    f"{APPLICATION_NAME}_DB_Profiles", name, db_password
                )
            except KeyringError as keyring_err:
                logging.getLogger(__name__).warning(
                    "Could not store password in system keyring for profile '%s': %s", name, keyring_err
                )
        else:
            try:
                keyring.delete_password(
                    f"{APPLICATION_NAME}_DB_Profiles", name
                )
            except (PasswordDeleteError, KeyringError) as delete_err:
                logging.getLogger(__name__).debug(
                    f"Password for profile '%s' not found during deletion: %s", name, delete_err
                )

        self.populate_profiles()
        index: int = self.profiles_combo.findText(name)
        if index >= 0:
            self.profiles_combo.blockSignals(True)
            self.profiles_combo.setCurrentIndex(index)
            self.profiles_combo.blockSignals(False)
            self.delete_profile_button.setEnabled(True)

        global_signals.request_toast(
            "Profile Saved",
            f"Profile '{name}' saved",
            ToastLevel.SUCCESS
        )

    def load_profile(self) -> None:
        """Load the selected profile"""
        name = self.profiles_combo.currentData()
        has_profile: bool = bool(name)
        if hasattr(self, "delete_profile_button"):
            self.delete_profile_button.setEnabled(has_profile)
        if not name:
            return

        self.settings.beginGroup("DatabaseProfiles")
        self.settings.beginGroup(str(name))

        mode: str = str(self.settings.value("mode", "builder"))
        safe_uri: str = str(self.settings.value("uri", ""))
        db_type: str = str(self.settings.value("db_type", "SQLite"))
        host: str = str(self.settings.value("host", ""))
        port: str = str(self.settings.value("port", ""))
        user: str = str(self.settings.value("user", ""))
        dbname: str = str(self.settings.value("dbname", ""))
        file_path: str = str(self.settings.value("file_path", ""))

        self.settings.endGroup()
        self.settings.endGroup()

        try:
            db_password: str = keyring.get_password(
                f"{APPLICATION_NAME}_DB_Profiles", str(name)
            ) or ""
        except KeyringError as keyring_err:
            logging.getLogger(__name__).warning(
                f"Failed to retrieve password for profile '%s': %s", name, keyring_err
            )
            db_password = ""

        if mode == "uri":
            self.mode_uri_radio.setChecked(True)
            safe_uri = self.settings.value("uri", "")
            if safe_uri and db_password:
                try:
                    parsed_url = make_url(safe_uri)
                    parsed_url = parsed_url.set(password=db_password)
                    final_uri: str = parsed_url.render_as_string(hide_password=False)
                    self.uri_input.setEchoMode(QLineEdit.EchoMode.Password)
                    self.uri_input.setText(final_uri)
                except ArgumentError:
                    self.uri_input.setEchoMode(QLineEdit.EchoMode.Normal)
                    self.uri_input.setText(safe_uri)
            else:
                self.uri_input.setEchoMode(QLineEdit.EchoMode.Normal)
                self.uri_input.setText(safe_uri)
        else:
            self.mode_builder_radio.setChecked(True)
            index: int = self.db_type_combo.findText(db_type)

            if index >= 0:
                self.db_type_combo.setCurrentIndex(index)
            self.on_db_type_changed(db_type)

            self.host_input.setText(host)
            self.port_input.setText(port)
            self.user_input.setText(user)
            self.password_input.setText(db_password)
            self.dbname_input.setText(dbname)
            self.file_db_path_input.setText(file_path)

    def delete_profile(self) -> None:
        """Delete current profile"""
        name = self.profiles_combo.currentData()
        if not name:
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete profile '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.settings.beginGroup("DatabaseProfiles")
            self.settings.remove(str(name))
            self.settings.endGroup()

            try:
                keyring.delete_password(
                    f"{APPLICATION_NAME}_DB_Profiles", str(name)
                )
            except (PasswordDeleteError, KeyringError) as delete_err:
                logging.getLogger(__name__).debug(
                    f"No keyring password to delete for profile '%s': %s", name, delete_err
                )

            self.populate_profiles()
            global_signals.request_toast(
                "Profile Deleted",
                f"Profile '{name}' has been deleted",
                ToastLevel.SUCCESS
            )

    def toggle_password_visibility(self) -> None:
        """Swaps the echo mode for passwords to view the password currently typed"""
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

    def toggle_uri_visibility(self) -> None:
        """Swaps echo mode for uri field"""
        if self.uri_input.echoMode() == QLineEdit.EchoMode.Password:
            self.uri_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.uri_input.setEchoMode(QLineEdit.EchoMode.Password)
