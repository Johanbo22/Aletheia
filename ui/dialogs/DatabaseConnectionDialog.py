from PyQt6.QtGui import QIcon, QPixmap, QFontDatabase, QIntValidator, QShortcut, QKeySequence, QSyntaxHighlighter, QTextCharFormat, QColor, QTextDocument, QFont
from PyQt6.QtCore import Qt, QThreadPool, QSettings
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QTextEdit, QVBoxLayout, QWidget, QStyle, QTreeWidget, QTreeWidgetItem, QSplitter, QRadioButton, QButtonGroup, QInputDialog

from pathlib import Path
import re
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from core.resource_loader import get_resource_path
from ui.widgets import DataPlotStudioButton, DataPlotStudioGroupBox, DataPlotStudioLineEdit, DataPlotStudioComboBox, DataPlotStudioRadioButton
from ui.icons import IconBuilder, IconType
from ui.workers import TestConnectionWorker, FetchSchemaWorker

class SQLSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighting for SQL syntax"""
    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#c678dd"))
        self.keyword_format.setFontWeight(QFont.Weight.Bold)
        
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#98c379"))
        
        keywords = [
            "SELECT", "FROM", "WHERE", "AND", "OR", "JOIN", "INNER", "LEFT", "RIGHT", 
            "OUTER", "ON", "GROUP BY", "ORDER BY", "HAVING", "LIMIT", "AS", "WITH", "ASC", "DESC"
        ]
        self.keyword_patterns = [re.compile(fr'\b{word}\b', re.IGNORECASE) for word in keywords]
        self.string_pattern = re.compile(r"'.*?'|\".*?\"")
    
    def highlightBlock(self, text: str) -> None:
        for match in self.string_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.string_format)
        
        for pattern in self.keyword_patterns:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), self.keyword_format)

class DatabaseConnectionDialog(QDialog):
    """Dialog class for establishing a database connection and setup query"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import from Database")
        self.setWindowIcon(IconBuilder.build(IconType.ImportDatabase))
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)

        self.details = {}

        self.settings = QSettings("DataPlotStudio", "DatabaseProfiles")
        self.threadpool = QThreadPool.globalInstance()

        main_layout = QVBoxLayout(self)

        # Profile selection
        profiles_group = DataPlotStudioGroupBox("Saved Connections", parent=self)
        profiles_layout = QHBoxLayout()

        profiles_layout.addWidget(QLabel("Profile:"))
        self.profiles_combo = DataPlotStudioComboBox()
        self.populate_profiles()
        self.profiles_combo.currentIndexChanged.connect(self.load_profile)
        profiles_layout.addWidget(self.profiles_combo, 1)

        self.save_profile_button = DataPlotStudioButton("Save", parent=self)
        self.save_profile_button.setToolTip("Save the current connection details")
        self.save_profile_button.clicked.connect(self.save_profile)
        profiles_layout.addWidget(self.save_profile_button)

        self.delete_profile_button = DataPlotStudioButton("Delete", parent=self)
        self.delete_profile_button.setToolTip("Delete selected profile")
        self.delete_profile_button.clicked.connect(self.delete_profile)
        profiles_layout.addWidget(self.delete_profile_button)

        profiles_group.setLayout(profiles_layout)
        main_layout.addWidget(profiles_group)

        # Connection mode
        self.setup_group = DataPlotStudioGroupBox("Connection Setup", parent=self)
        setup_layout = QFormLayout(self.setup_group)
        
        self.mode_group = QButtonGroup(self)
        mode_radio_layout = QHBoxLayout()

        self.mode_builder_radio = DataPlotStudioRadioButton("Connection Builder")
        self.mode_builder_radio.setChecked(True)
        self.mode_builder_radio.toggled.connect(self.toggle_connection_mode)
        self.mode_group.addButton(self.mode_builder_radio)
        mode_radio_layout.addWidget(self.mode_builder_radio)

        self.mode_uri_radio = DataPlotStudioRadioButton("Raw Connection URI")
        self.mode_uri_radio.toggled.connect(self.toggle_connection_mode)
        self.mode_group.addButton(self.mode_uri_radio)
        mode_radio_layout.addWidget(self.mode_uri_radio)
        mode_radio_layout.addStretch()
        
        setup_layout.addRow("Connection Mode:", mode_radio_layout)

        #type selection
        self.db_type_label = QLabel("Database Type:")
        self.db_type_combo = DataPlotStudioComboBox()
        self.db_type_combo.addItems(["SQLite","DuckDB", "PostgreSQL", "MySQL"])
        self.db_type_combo.currentTextChanged.connect(self.on_db_type_changed)
        setup_layout.addRow(self.db_type_label, self.db_type_combo)
        
        main_layout.addWidget(self.setup_group)

        #connection details
        self.connection_group = DataPlotStudioGroupBox("Connection Details", parent=self)
        connection_group_layout = QVBoxLayout(self.connection_group)
        self.connection_layout = QFormLayout()
        connection_group_layout.addLayout(self.connection_layout)

        self.host_label = QLabel("Host:")
        self.host_input = DataPlotStudioLineEdit("localhost")
        self.connection_layout.addRow(self.host_label, self.host_input)

        self.port_label = QLabel("Port:")
        self.port_input = DataPlotStudioLineEdit()
        self.port_validator = QIntValidator(1, 65535, self)
        self.port_input.setValidator(self.port_validator)
        self.connection_layout.addRow(self.port_label, self.port_input)

        self.user_label = QLabel("User:")
        self.user_input = DataPlotStudioLineEdit("postgres")
        self.connection_layout.addRow(self.user_label, self.user_input)

        self.password_label = QLabel("Password:")
        self.password_input = DataPlotStudioLineEdit()
        self.password_input.setEchoMode(DataPlotStudioLineEdit.EchoMode.Password)
        
        view_icon = IconBuilder.build(IconType.ViewItem)
        self.toggle_password_action = self.password_input.addAction(view_icon, DataPlotStudioLineEdit.ActionPosition.TrailingPosition)
        self.toggle_password_action.triggered.connect(self.toggle_password_visibility)
        self.connection_layout.addRow(self.password_label, self.password_input)

        self.dbname_label = QLabel("Database:")
        self.dbname_input = DataPlotStudioLineEdit("postgres")
        self.connection_layout.addRow(self.dbname_label, self.dbname_input)

        #raw uri
        self.uri_label = QLabel("Connection URI:")
        self.uri_input = DataPlotStudioLineEdit()
        self.uri_input.setPlaceholderText("dialect+driver://username:password@host:port/database")
        self.uri_input.setVisible(False)
        self.uri_label.setVisible(False)
        self.connection_layout.addRow(self.uri_label, self.uri_input)

        # SQLITE and duckDB specific
        self.file_db_layout = QHBoxLayout()
        self.file_db_layout.setContentsMargins(0, 0, 0, 0)
        self.file_db_label = QLabel("Database File:")
        self.file_db_path_input = DataPlotStudioLineEdit()
        self.file_db_path_input.setPlaceholderText("Click 'Browse' to select a database file")
        self.file_db_browse_button = DataPlotStudioButton("Browse", parent=self)
        self.file_db_browse_button.clicked.connect(self.browse_file_db)
        self.file_db_layout.addWidget(self.file_db_path_input)
        self.file_db_layout.addWidget(self.file_db_browse_button)
        self.file_db_widget = QWidget()
        self.file_db_widget.setLayout(self.file_db_layout)
        self.connection_layout.addRow(self.file_db_label, self.file_db_widget)

        # A test connection button
        self.test_connection_wrapper = QWidget()
        test_connection_layout = QHBoxLayout(self.test_connection_wrapper)
        test_connection_layout.setContentsMargins(0, 0, 0, 0)

        # Database icons
        self.db_icon_label = QLabel()
        self.db_icon_label.setFixedHeight(24)
        self.db_icon_label.setObjectName("db_icon_label")
        test_connection_layout.addWidget(self.db_icon_label)
        
        self.connection_status_label = QLabel()
        self.connection_status_label.setObjectName("query_status_label")
        test_connection_layout.addWidget(self.connection_status_label)

        test_connection_layout.addStretch()

        self.test_connection_button = DataPlotStudioButton("Test Connection", parent=self)
        self.test_connection_button.clicked.connect(self.test_connection)
        test_connection_layout.addWidget(self.test_connection_button)

        connection_group_layout.addWidget(self.test_connection_wrapper)

        main_layout.addWidget(self.connection_group)

        # Editor grouping with a splitter instead of hardlocked widgets
        self.editors_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Query editor
        query_group = DataPlotStudioGroupBox("SQL Query", parent=self)
        query_layout = QVBoxLayout()
        instructions = (
            "Enter your SQL query below. You can select specific columns and join tables.\n"
            "Supports standard SELECT statements and CTEs."
        )
        self.info_label = QLabel(instructions)
        self.info_label.setWordWrap(True)
        query_layout.addWidget(self.info_label)
        
        self.query_editor = QTextEdit()
        self.query_editor.setPlaceholderText("SELECT * FROM table_name ...")
        
        self.sql_highlighter = SQLSyntaxHighlighter(self.query_editor.document())
        
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        if fixed_font.pointSize() < 10:
            fixed_font.setPointSize(10)
        self.query_editor.setFont(fixed_font)
        self.query_editor.setMinimumHeight(150)
        query_layout.addWidget(self.query_editor)

        #query validation
        self.query_status_icon = QLabel()
        self.query_status_icon.setFixedSize(16, 16)
        self.query_status_label = QLabel(" ")
        self.query_status_label.setObjectName("query_status_label")

        status_layout = QHBoxLayout()
        status_layout.setSpacing(6)
        status_layout.addWidget(self.query_status_icon)
        status_layout.addWidget(self.query_status_label)
        status_layout.addStretch()
        query_layout.addLayout(status_layout)

        query_group.setLayout(query_layout)
        self.editors_splitter.addWidget(query_group)

        # Schema viewer
        schema_group = DataPlotStudioGroupBox("Database Schema", parent=self)
        schema_layout = QVBoxLayout()

        self.load_schema_button = DataPlotStudioButton("Load Tables and Columns", parent=self)
        self.load_schema_button.setToolTip("Connect to the database and list all tables and columns")
        self.load_schema_button.clicked.connect(self.fetch_schema)
        schema_layout.addWidget(self.load_schema_button)
        
        # Search bar for schema tree
        self.schema_search_input = DataPlotStudioLineEdit(parent=self)
        self.schema_search_input.setPlaceholderText("Search tables and columns...")
        self.schema_search_input.textChanged.connect(self.filter_schema_tree)
        self.schema_search_input.setVisible(False)
        schema_layout.addWidget(self.schema_search_input)

        self.schema_tree = QTreeWidget()
        self.schema_tree.setHeaderLabels(["Table / Column", "Type"])
        self.schema_tree.setAlternatingRowColors(True)
        self.schema_tree.setDragEnabled(True)
        self.schema_tree.setToolTip("Double-click or drag an item to insert it into the query")
        self.schema_tree.itemDoubleClicked.connect(self.on_schema_double_clicked)
        schema_layout.addWidget(self.schema_tree)

        schema_group.setLayout(schema_layout)
        self.editors_splitter.addWidget(schema_group)

        # Set sizes for splitter. query is larger than schema
        self.editors_splitter.setStretchFactor(0, 3)
        self.editors_splitter.setStretchFactor(1, 2)

        main_layout.addWidget(self.editors_splitter, stretch=1)

        #buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setToolTip("Accept and Import (Ctrl+Enter)")
        
        self.button_box.accepted.connect(self.on_accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        
        self.accept_shortcut_return = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.accept_shortcut_return.activated.connect(self.on_accept)
        
        self.accept_shortcut_enter = QShortcut(QKeySequence("Ctrl+Enter"), self)
        self.accept_shortcut_enter.activated.connect(self.on_accept)

        self.query_editor.textChanged.connect(self.on_query_changed)

        self.on_db_type_changed("SQLite")
        self.on_query_changed()
    
    def test_connection(self) -> None:
        """Tests the database connection before loading the schema"""
        try:
            self.setCursor(Qt.CursorShape.WaitCursor)
            self.test_connection_button.setEnabled(False)
            self.test_connection_button.setText("Testing...")
            self.db_icon_label.setText("Testing...")
            
            self.connection_status_label.setText("Connecting...")
            self.connection_status_label.setProperty("status", "")
            self.connection_status_label.style().unpolish(self.connection_status_label)
            self.connection_status_label.style().polish(self.connection_status_label)

            connection_string = self._build_connection_string()

            worker = TestConnectionWorker(connection_string)
            worker.signals.finished.connect(self.on_test_connection_success)
            worker.signals.error.connect(self.on_test_connection_error)

            self.threadpool.start(worker)
        
        except ValueError as InputError:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.test_connection_button.setEnabled(True)
            self.test_connection_button.setText("Test Connection")
            self.db_icon_label.clear()
            self.connection_status_label.setText("")
            QMessageBox.warning(self, "Input Error", str(InputError))

    def on_test_connection_success(self) -> None:
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.test_connection_button.setEnabled(True)
        self.test_connection_button.setText("Test Connection")
        self.db_icon_label.setToolTip("Connected")
        
        self.connection_status_label.setText("Connection successful")
        self.connection_status_label.setProperty("status", "valid")
        self.connection_status_label.style().unpolish(self.connection_status_label)
        self.connection_status_label.style().polish(self.connection_status_label)
    
    def on_test_connection_error(self, error) -> None:
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.test_connection_button.setEnabled(True)
        self.test_connection_button.setText("Test Connection")
        
        self.connection_status_label.setText("Connection failed")
        self.connection_status_label.setProperty("status", "invalid")
        self.connection_status_label.style().unpolish(self.connection_status_label)
        self.connection_status_label.style().polish(self.connection_status_label)
        
        QMessageBox.critical(self, "Connection Failed", f"Could not connect to the database:\n{str(error)}")

    def fetch_schema(self) -> None:
        """Connects to the DB asynch and populates tree"""
        try:
            connection_string = self._build_connection_string()
            
            self.setCursor(Qt.CursorShape.WaitCursor)
            self.load_schema_button.setEnabled(False)
            self.load_schema_button.setText("Loading schema...")
            self.schema_tree.clear()
            self.schema_search_input.clear()
            self.schema_search_input.setVisible(False)
            
            worker = FetchSchemaWorker(connection_string=connection_string)
            worker.signals.finished.connect(self.on_fetch_schema_success)
            worker.signals.error.connect(self.on_fetch_schema_error)
            
            self.threadpool.start(worker)
        except ValueError as DatabaseValueError:
            QMessageBox.warning(self, "Input Error", str(DatabaseValueError))
    
    def on_fetch_schema_success(self, schema_data: list[dict]) -> None:
        """Populates the schema tree with fetched data"""
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.load_schema_button.setEnabled(True)
        self.load_schema_button.setText("Load Tables and Columns")
        
        self.schema_search_input.setVisible(True)
        
        for table_info in schema_data:
            table = table_info["table"]
            columns = table_info["columns"]
            
            table_item = QTreeWidgetItem(self.schema_tree)
            table_item.setText(0, table)
            table_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
            
            if not columns:
                err_item = QTreeWidgetItem(table_item)
                err_item.setText(0, "No columns found")
                continue
            
            for col in columns:
                col_item = QTreeWidgetItem(table_item)
                col_name = col.get("name", "Unknown")
                col_type = col.get("type", "Unknown")
                
                col_item.setText(0, str(col_name))
                col_item.setText(1, str(col_type))
                col_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        
        if len(schema_data) <= 15:
            self.schema_tree.expandAll()
    
    def on_fetch_schema_error(self, error_message: str) -> None:
        """Handles errors during asynch schema fetch"""
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.load_schema_button.setEnabled(True)
        self.load_schema_button.setText("Load Tables and Columns")
        QMessageBox.critical(self, "Connection Error", f"Failed to fetch schema:\n{error_message}")
    
    def filter_schema_tree(self, text: str) -> None:
        """Filters the schema tree on a search query"""
        search_term = text.lower().strip()
        
        for i in range(self.schema_tree.topLevelItemCount()):
            table_item = self.schema_tree.topLevelItem(i)
            table_match = search_term in table_item.text(0).lower()
            
            child_match = False
            for j in range(table_item.childCount()):
                col_item = table_item.child(j)
                if search_term in col_item.text(0).lower():
                    col_item.setHidden(False)
                    child_match = True
                else:
                    col_item.setHidden(True)
            
            table_item.setHidden(not (table_match or child_match))
            
            if child_match and search_term:
                table_item.setExpanded(True)
            elif not search_term:
                table_item.setExpanded(False)
    
    def on_schema_double_clicked(self, item: QTreeWidgetItem) -> None:
        """Insert the clicked ite text into the query"""
        def format_identifier(name: str) -> str:
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
                return f'"{name}"'
            return name
        
        parent = item.parent()
        
        # If the item has a parent, its a column
        if parent:
            table_name = format_identifier(parent.text(0))
            col_name = format_identifier(item.text(0))
            insert_text = f"{table_name}.{col_name}"
        else:
            insert_text = format_identifier(item.text(0))
        
        self.query_editor.insertPlainText(insert_text + " ")
        self.query_editor.setFocus()

    def _build_connection_string(self) -> str:
        """Constructs the connection string from inputs"""
        # URI mode
        if self.mode_uri_radio.isChecked():
            uri = self.uri_input.text().strip()
            if not uri:
                raise ValueError("Please provide a valid Connection URI")
            return uri

        db_type = self.db_type_combo.currentText()

        connection_string = ""

        if db_type in ["SQLite", "DuckDB"]:
            db_path = self.file_db_path_input.text().strip()
            if not db_path:
                raise ValueError(f"Please provide a path to the {db_type} database file.")
            
            db_path_abs = Path(db_path).resolve().as_posix()
            prefix = "sqlite" if db_type == "SQLite" else "duckdb"
            connection_string = f"{prefix}:///{db_path_abs}"
        
        else:
            host = self.host_input.text().strip()
            port = self.port_input.text().strip()
            user = self.user_input.text().strip()
            password = self.password_input.text().strip()
            dbname = self.dbname_input.text().strip()

            if not all([host, port, user, dbname]):
                raise ValueError("Please fill in all connection details (Host, Port, User, DatabaseName)")
            
            if db_type == "PostgreSQL":
                connection_string = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
            elif db_type == "MySQL":
                connection_string = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{dbname}"
        
        return connection_string

    def on_query_changed(self) -> None:
        """Validate the query"""
        query = self.query_editor.toPlainText().strip()

        if not query:
            self._set_query_status(
                "Query cannot be empty",
                valid=False
            )
            return
        
        if self._is_valid_select_query(query):
            self._set_query_status(
                "Valid query",
                valid=True
            )
        else:
            self._set_query_status(
                "Invalid query (Must be a SELECT statement or WITH clause)",
                valid=False
            )
    
    def _is_valid_select_query(self, query: str) -> bool:
        """Checks if the query entered matches expression rules

        Args:
            query (str): Takes the query from te query text box

        Returns:
            bool: Returns True if the query is valid
        """
        query = re.sub(r"^\s*(--.*\n|/\*.*?\*/\s*)*", "", query, flags=re.S).strip()

        starts_valid = query.lower().startswith("select") or query.lower().startswith("with")
        has_select = bool(re.search(r"\bselect\b", query, re.IGNORECASE))
        has_from = bool(re.search(r"\bfrom\b", query, re.IGNORECASE))

        return starts_valid and has_select and has_from
    
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

    def on_db_type_changed(self, db_type: str) -> None:
        """Show or hide fields based on db type"""
        if self.mode_uri_radio.isChecked():
            return

        is_file_db = (db_type in ["SQLite", "DuckDB"])

        #toggle server fields
        self.host_label.setVisible(not is_file_db)
        self.host_input.setVisible(not is_file_db)
        self.port_label.setVisible(not is_file_db)
        self.port_input.setVisible(not is_file_db)
        self.user_label.setVisible(not is_file_db)
        self.user_input.setVisible(not is_file_db)
        self.password_label.setVisible(not is_file_db)
        self.password_input.setVisible(not is_file_db)
        self.dbname_label.setVisible(not is_file_db)
        self.dbname_input.setVisible(not is_file_db)

        #toggle SQLITE fields
        self.file_db_label.setVisible(is_file_db)
        self.file_db_widget.setVisible(is_file_db)

        #set defaults on port and usr
        if db_type == "PostgreSQL":
            self.port_input.setText("5432")
            self.user_input.setText("postgres")
            self.dbname_input.setText("postgres")
        elif db_type == "MySQL":
            self.port_input.setText("3306")
            self.user_input.setText("root")
            self.dbname_input.setText("")
        elif db_type == "DuckDB":
            self.file_db_path_input.setPlaceholderText("Click 'Browse' to select a DuckDB file (.db, .duckdb)")
        elif db_type == "SQLite":
            self.file_db_path_input.setPlaceholderText("Click 'Browse' to select a SQLite file (.db, .sqlite, .sqlite3)")

        # Update the icon
        icon_map = {
            "SQLite": "icons/database_icons/sqlite.svg",
            "DuckDB": "icons/database_icons/duckdb-logo.svg",
            "PostgreSQL": "icons/database_icons/postgresql-inc.svg",
            "MySQL": "icons/database_icons/mysql-3.svg"
        }
        icon_path = icon_map.get(db_type, "")

        if not Path(icon_path).exists():
            icon_path = get_resource_path("icons/menu_bar/database.svg")
        
        if Path(icon_path).exists():
            pixmap = QPixmap(icon_path)
            scaled_pixmap = pixmap.scaledToHeight(24, Qt.TransformationMode.SmoothTransformation)
            self.db_icon_label.setPixmap(scaled_pixmap)
            self.db_icon_label.setToolTip(f"{db_type} Database")
        else:
            self.db_icon_label.clear()

    def browse_file_db(self) -> None:
        """Open a file dialog to find a local SQLite database file"""
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
        db_type = self.db_type_combo.currentText()
        query = self.query_editor.toPlainText().strip()
        
        if not query:
            QMessageBox.warning(self, "Input Error", "Please enter a SQL Query")
            return
        
        if not (query.lower().startswith("select") or query.lower().startswith("with")):
            QMessageBox.warning(
                self,
                "Invalid Query Syntax",
                "The SQL query must be a 'SELECT' statement or start with 'WITH'"
            )
            return
        
        try:
            connection_string = self._build_connection_string()

            self.details = {
                "db_type": db_type,
                "connection_string": connection_string,
                "query": query
            }
            self.accept()
        
        except ValueError as InputError:
            QMessageBox.warning(self, "Input Error", str(InputError))
        except Exception as AcceptDatabaseConnectionError:
            QMessageBox.critical(self, "Error", f"Failed to establis a proper connection string: {str(AcceptDatabaseConnectionError)}")

    def get_details(self) -> tuple[str | None, str | None, str | None]:
        """Returns the connection string and query"""
        return self.details.get("db_type"), self.details.get("connection_string"), self.details.get("query")
    
    def toggle_connection_mode(self) -> None:
        """Switches the UI states"""
        is_uri_mode = self.mode_uri_radio.isChecked()

        self.uri_label.setVisible(is_uri_mode)
        self.uri_input.setVisible(is_uri_mode)

        builder_visible = not is_uri_mode

        self.db_type_combo.setVisible(builder_visible)
        self.db_type_label.setVisible(builder_visible)

        if is_uri_mode:
            self.host_label.setVisible(False)
            self.host_input.setVisible(False)
            self.port_label.setVisible(False)
            self.port_input.setVisible(False)
            self.user_label.setVisible(False)
            self.user_input.setVisible(False)
            self.password_label.setVisible(False)
            self.password_input.setVisible(False)
            self.dbname_label.setVisible(False)
            self.dbname_input.setVisible(False)
            self.file_db_label.setVisible(False)
            self.file_db_widget.setVisible(False)
        else:
            self.on_db_type_changed(self.db_type_combo.currentText())
    
    def populate_profiles(self) -> None:
        self.profiles_combo.blockSignals(True)
        self.profiles_combo.clear()
        self.profiles_combo.addItem("Select a profile...", None)

        self.settings.beginGroup("DatabaseProfiles")
        profiles = self.settings.childGroups()
        self.settings.endGroup()

        for profile in profiles:
            self.profiles_combo.addItem(profile, profile)
        self.profiles_combo.blockSignals(False)
    
    def save_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Profile", "Enter profile name")
        if ok and name:
            if not name.strip():
                QMessageBox.warning(self, "Error", "Profile name cannot be empty")
                return
            
            is_uri = self.mode_uri_radio.isChecked()
            data = {
                "mode": "uri" if is_uri else "builder",
                "uri": self.uri_input.text(),
                "db_type": self.db_type_combo.currentText(),
                "host": self.host_input.text(),
                "port": self.port_input.text(),
                "user": self.user_input.text(),
                "password": "",
                "dbname": self.dbname_input.text(),
                "file_path": self.file_db_path_input.text()
            }

            self.settings.beginGroup("DatabaseProfiles")
            self.settings.beginGroup(name)
            for key, val in data.items():
                self.settings.setValue(key, val)
            self.settings.endGroup()
            self.settings.endGroup()

            self.populate_profiles()
            index = self.profiles_combo.findText(name)
            if index >= 0:
                self.profiles_combo.setCurrentIndex(index)
            
            QMessageBox.information(self, "Saved", f"Profile '{name}' saved")
    
    def load_profile(self) -> None:
        """Load the selected profile"""
        name = self.profiles_combo.currentData()
        if not name:
            return
        
        self.settings.beginGroup("DatabaseProfiles")
        self.settings.beginGroup(name)

        mode = self.settings.value("mode", "builder")

        if mode == "uri":
            self.mode_uri_radio.setChecked(True)
            self.uri_input.setText(self.settings.value("uri", ""))
        else:
            self.mode_builder_radio.setChecked(True)
            db_type = self.settings.value("db_type", "SQLite")
            index = self.db_type_combo.findText(db_type)
            if index >= 0:
                self.db_type_combo.setCurrentIndex(index)
            
            self.host_input.setText(self.settings.value("host", ""))
            self.port_input.setText(self.settings.value("port", ""))
            self.user_input.setText(self.settings.value("user", ""))
            self.password_input.clear()
            self.dbname_input.setText(self.settings.value("dbname", ""))
            self.file_db_path_input.setText(self.settings.value("file_path", ""))

            self.on_db_type_changed(db_type)
        
        self.settings.endGroup()
        self.settings.endGroup()
    
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
            self.settings.remove(name)
            self.settings.endGroup()
            self.populate_profiles()
    
    def toggle_password_visibility(self) -> None:
        """Swaps the echo mode for passwords to view the password currently typed"""
        if self.password_input.echoMode() == DataPlotStudioLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(DataPlotStudioLineEdit.EchoMode.Normal)
        else:
            self.password_input.setEchoMode(DataPlotStudioLineEdit.EchoMode.Password)