from typing import Dict, Any
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFormLayout, QAbstractItemView, QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QWidget, QPushButton, QMessageBox, QMenu, QApplication, QSpinBox, QLineEdit, QComboBox
from PyQt6.QtCore import Qt, QRegularExpression, QPoint, QEvent, QObject
from PyQt6.QtGui import QFont, QColor, QRegularExpressionValidator, QKeyEvent

from ui.theme import ThemeColors
from ui.icons import IconBuilder, IconType

class CreateDatasetDialog(QDialog):
    """
    Dialog for configuring parameters when creating a new empty dataset.
    Allows specifying row count, column count, and customizing column names.
    """
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create New Dataset")
        self.setWindowIcon(IconBuilder.build(IconType.NewProject))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.resize(850, 580)
        
        self._default_prefix: str = "Column"
        
        self.init_ui()
    
    def init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(24)
        main_layout.setContentsMargins(28, 28, 28, 28)
        
        header_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(IconBuilder.build(IconType.DataExplorerIcon).pixmap(48, 48))
        
        icon_label.setScaledContents(True)
        icon_label.setFixedSize(48, 48)
        
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        
        title_label = QLabel("Configure New Dataset")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        subtitle_label = QLabel("Define initial dimensions, initial cell states and customize column names")
        subtitle_label.setProperty("styleClass", "muted_text")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        
        header_layout.addWidget(icon_label)
        header_layout.addSpacing(16)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        left_card = QFrame()
        left_card.setObjectName("PanelFrame")
        left_card.setMaximumWidth(320)
        
        controls_layout = QVBoxLayout(left_card)
        controls_layout.setContentsMargins(20, 20, 20, 20)
        controls_layout.setSpacing(24)
        
        config_section = QVBoxLayout()
        config_section.setSpacing(12)
        
        config_label = QLabel("Dataset Configuration")
        config_label.setObjectName("SectionHeaderLabel")
        controls_layout.addWidget(config_label)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(16)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        self.rows_spinbox = QSpinBox()
        self.rows_spinbox.setRange(1, 1_000_000)
        self.rows_spinbox.setValue(10)
        self.rows_spinbox.setSuffix(" rows")
        self.rows_spinbox.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.rows_spinbox.setGroupSeparatorShown(True)
        self.rows_spinbox.setMinimumHeight(34)
        self.rows_spinbox.setToolTip("Specify the total number of rows to create")
        
        self.cols_spinbox = QSpinBox()
        self.cols_spinbox.setRange(1, 1_000)
        self.cols_spinbox.setValue(3)
        self.cols_spinbox.setSuffix(" columns")
        self.cols_spinbox.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.cols_spinbox.setGroupSeparatorShown(True)
        self.cols_spinbox.setMinimumHeight(34)
        self.cols_spinbox.setKeyboardTracking(False)
        self.cols_spinbox.setToolTip("Specify the total number of columns to create")
        self.cols_spinbox.valueChanged.connect(self._on_column_count_changed)
        
        self.fill_combo = QComboBox()
        self.fill_combo.setMinimumHeight(34)
        self.fill_combo.addItems(["NaN (Missing Data)", "0 (Zeroes)", "1 (Ones)", '"" (Empty String)'])
        self.fill_combo.setToolTip("Select the initial data state for all cells in the new dataset")
        
        form_layout.addRow("Number of &Rows:", self.rows_spinbox)
        form_layout.addRow("Number of &Columns:", self.cols_spinbox)
        form_layout.addRow("Initial &Fill State:", self.fill_combo)
        
        # Warning label for very large datasets
        self.memory_warning_label = QLabel("Large Dataset: May consume significant memory")
        self.memory_warning_label.setProperty("styleClass", "warning_info_text")
        self.memory_warning_label.hide()
        self.memory_warning_label.setWordWrap(True)
        config_section.addWidget(self.memory_warning_label)
        
        config_section.addLayout(form_layout)
        controls_layout.addLayout(config_section)
        
        gen_section = QVBoxLayout()
        gen_section.setSpacing(8)
        
        gen_label = QLabel("Bulk Naming")
        gen_label.setObjectName("SectionHeaderLabel")
        gen_section.addWidget(gen_label)
        
        gen_desc = QLabel("Set a &prefix to auto-generate names")
        gen_desc.setProperty("styleClass", "muted_text")
        gen_section.addWidget(gen_desc)
        
        prefix_layout = QHBoxLayout()
        prefix_layout.setSpacing(8)
        self.prefix_input = QLineEdit()
        gen_desc.setBuddy(self.prefix_input)
        self.prefix_input.setText(self._default_prefix)
        self.prefix_input.setPlaceholderText("e.g. Var")
        self.prefix_input.setMinimumHeight(34)
        self.prefix_input.setClearButtonEnabled(True)
        self.prefix_input.setToolTip("Prefix must start with a letter and contain only alphanumerical characters or underscores")
        
        prefix_regex = QRegularExpression(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
        prefix_validator = QRegularExpressionValidator(prefix_regex)
        self.prefix_input.setValidator(prefix_validator)
        
        self.btn_apply_prefix = QPushButton("Apply", parent=self)
        self.btn_apply_prefix.setIcon(IconBuilder.build(IconType.EditColumns))
        self.btn_apply_prefix.setMinimumHeight(34)
        self.btn_apply_prefix.clicked.connect(self._apply_prefix_to_table)
        self.prefix_input.returnPressed.connect(self.btn_apply_prefix.click)
        
        prefix_layout.addWidget(self.prefix_input)
        prefix_layout.addWidget(self.btn_apply_prefix)
        gen_section.addLayout(prefix_layout)
        
        controls_layout.addLayout(gen_section)
        controls_layout.addStretch()
        content_layout.addWidget(left_card, stretch=4)
        
        right_card = QFrame()
        right_card.setObjectName("PanelFrame")
        
        table_layout = QVBoxLayout(right_card)
        table_layout.setContentsMargins(20, 20, 20, 20)
        table_layout.setSpacing(12)
        
        self.table_label = QLabel("Column Name Editor:")
        self.table_label.setObjectName("SectionHeaderLabel")
        table_layout.addWidget(self.table_label)
        
        self.col_table = QTableWidget(0, 1)
        self.col_table.setObjectName("CreateDatasetColumnTable")
        self.col_table.setFrameShape(QFrame.Shape.NoFrame)
        self.col_table.setHorizontalHeaderLabels(["Column Name"])
        self.col_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.col_table.verticalHeader().setDefaultSectionSize(36)
        self.col_table.setAlternatingRowColors(True)
        self.col_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        
        self.col_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked |
            QAbstractItemView.EditTrigger.EditKeyPressed |
            QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        
        self.col_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.col_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        
        self.col_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.col_table.customContextMenuRequested.connect(self._show_table_context_menu)
        self.col_table.installEventFilter(self)
        
        self.col_table.itemChanged.connect(self._validate_schema)
        table_layout.addWidget(self.col_table)
        
        content_layout.addWidget(right_card, stretch=5)
        main_layout.addLayout(content_layout)
        
        separator = QFrame()
        separator.setObjectName("DialogSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        main_layout.addWidget(separator)
        
        btn_layout = QHBoxLayout()
        
        self.btn_reset = QPushButton("Reset Defaults", parent=self)
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setProperty("styleClass", "destructive")
        self.btn_reset.setIcon(IconBuilder.build(IconType.Redo))
        self.btn_reset.setToolTip("Warning: This will overwrite any custom column names.")
        self.btn_reset.clicked.connect(self._reset_defaults)
        
        self.btn_cancel = QPushButton("Cancel", parent=self)
        self.btn_cancel.setIcon(IconBuilder.build(IconType.DeleteItem))
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_create = QPushButton("Create Dataset")
        self.btn_create.setObjectName("MainActionButton")
        self.btn_create.setIcon(IconBuilder.build(IconType.Checkmark))
        self.btn_create.setMinimumWidth(160)
        self.btn_create.setDefault(True)
        self.btn_create.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addSpacing(12)
        btn_layout.addWidget(self.btn_create)
        
        main_layout.addLayout(btn_layout)
        
        self.rows_spinbox.setFocus()
        
        # Tab order
        self.setTabOrder(self.rows_spinbox, self.cols_spinbox)
        self.setTabOrder(self.cols_spinbox, self.fill_combo)
        self.setTabOrder(self.fill_combo, self.prefix_input)
        self.setTabOrder(self.prefix_input, self.btn_apply_prefix)
        self.setTabOrder(self.btn_apply_prefix, self.col_table)
        self.setTabOrder(self.col_table, self.btn_reset)
        self.setTabOrder(self.btn_reset, self.btn_cancel)
        self.setTabOrder(self.btn_cancel, self.btn_create)
        
        self.rows_spinbox.valueChanged.connect(self._evaluate_dataset_scale)
        self._on_column_count_changed(self.cols_spinbox.value())
        self._evaluate_dataset_scale()
    
    def _evaluate_dataset_scale(self, *args) -> None:
        """Evaluates the total cell count and displays a warning if memory usage might be high"""
        total_cells = self.rows_spinbox.value() * self.cols_spinbox.value()
        if total_cells > 1_000_000:
            self.memory_warning_label.show()
        else:
            self.memory_warning_label.hide()
        
    def _on_column_count_changed(self, target_cols: int) -> None:
        """Updates table rows based on requestsx"""
        self.table_label.setText(f"Column Name Editor: ({target_cols} Columns):")
        
        current_rows = self.col_table.rowCount()
        prefix = self.prefix_input.text().strip() or self._default_prefix
        
        self.col_table.blockSignals(True)
        if target_cols > current_rows:
            self.col_table.setRowCount(target_cols)
            for i in range(current_rows, target_cols):
                item = QTableWidgetItem(f"{prefix}_{i+1}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.col_table.setItem(i, 0, item)
            self.col_table.scrollToBottom()
        elif target_cols < current_rows:
            self.col_table.setRowCount(target_cols)
        self.col_table.blockSignals(False)
        self._validate_schema()
    
    def _apply_prefix_to_table(self) -> None:
        prefix = self.prefix_input.text().strip() or self._default_prefix
        self.col_table.blockSignals(True)
        for i in range(self.col_table.rowCount()):
            item = self.col_table.item(i, 0)
            if item:
                item.setText(f"{prefix}_{i+1}")
        self.col_table.blockSignals(False)
        self._validate_schema()
        
    def _show_table_context_menu(self, position: QPoint) -> None:
        menu = QMenu(self.col_table)
        
        action_reset = menu.addAction("Reset Names to Prefix")
        action_reset.setIcon(IconBuilder.build(IconType.Redo))
        
        action_clear = menu.addAction("Clear All Names")
        action_clear.setIcon(IconBuilder.build(IconType.DeleteItem))
        
        selected_action = menu.exec(self.col_table.viewport().mapToGlobal(position))
        
        if selected_action == action_reset:
            self._apply_prefix_to_table()
        elif selected_action == action_clear:
            self.col_table.blockSignals(True)
            for i in range(self.col_table.rowCount()):
                item = self.col_table.item(i, 0)
                if item:
                    item.setText("")
            self.col_table.blockSignals(False)
            self._validate_schema()
    
    def _reset_defaults(self) -> None:
        self.prefix_input.setText(self._default_prefix)
        self.rows_spinbox.setValue(10)
        self.cols_spinbox.setValue(3)
        self.fill_combo.setCurrentIndex(0)
        self._apply_prefix_to_table()
    
    def eventFilter(self, watched: QObject, event: QEvent | QKeyEvent) -> bool:
        if watched is self.col_table and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                current_item = self.col_table.currentItem()
                if current_item:
                    self.col_table.blockSignals(True)
                    current_item.setText("")
                    self.col_table.blockSignals(False)
                    self._validate_schema()
                return True
        return super().eventFilter(watched, event)
    
    def _validate_schema(self, *args) -> None:
        """Hlighlighs duplicate column names in table"""
        seen = set()
        has_issues = False
        
        self.col_table.blockSignals(True)
        for i in range(self.col_table.rowCount()):
            item = self.col_table.item(i, 0)
            if not item:
                continue
            
            raw_text = item.text()
            clean_text = raw_text.strip()
            
            if raw_text != clean_text:
                item.setText(clean_text)
            
            if not clean_text:
                item.setForeground(QColor("#e74c3c"))
                item.setToolTip("Column name cannot be empty. Will be auto-named")
                has_issues = True
            elif clean_text in seen:
                item.setForeground(QColor("#e74c3c"))
                item.setToolTip("Duplicate detected. Will be auto-resolved")
                has_issues = True
            else:
                item.setForeground(QColor("#2c3e50"))
                item.setToolTip("")
                seen.add(clean_text)
        self.col_table.blockSignals(False)
        
        if has_issues:
            self.btn_create.setText("Create (Auto-Resolve Issues)")
        else:
            self.btn_create.setText("Create Dataset")
    
    def get_dataset_parameters(self) -> Dict[str, Any]:
        col_names = []
        for i in range(self.col_table.rowCount()):
            item = self.col_table.item(i, 0)
            text = item.text().strip() if item else ""
            col_names.append(text if text else f"Unnamed_{i+1}")
        
        seen = set()
        unique_col_names = []
        for name in col_names:
            final_name = name
            counter = 1
            while final_name in seen:
                final_name = f"{name}_{counter}"
                counter += 1
            seen.add(final_name)
            unique_col_names.append(final_name)
        
        fill_text = self.fill_combo.currentText()
        if fill_text.startswith("0"):
            fill_val = 0
        elif fill_text.startswith("1"):
            fill_val = 1
        elif fill_text.startswith('""'):
            fill_val = ""
        else:
            fill_val = "NaN"
        
        return {
            "rows": self.rows_spinbox.value(),
            "columns": self.cols_spinbox.value(),
            "column_names": unique_col_names,
            "fill_value": fill_val
        }
    
    def reject(self) -> None:
        prefix = self.prefix_input.text().strip() or self._default_prefix
        has_custom_edits = False
        
        # Check if user has deviated from the auto-generated prefixes
        for i in range(self.col_table.rowCount()):
            item = self.col_table.item(i, 0)
            if item and item.text().strip() != f"{prefix}_{i+1}":
                has_custom_edits = True
                break
        
        if has_custom_edits:
            reply = QMessageBox.question(
                self, 
                "Discar Changes?",
                "You have manually edited column names. Are you sure you want to cancel and discard your changes?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        super().reject()
    
    def accept(self) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            super().accept()
        finally:
            QApplication.restoreOverrideCursor()