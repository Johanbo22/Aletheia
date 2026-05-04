import re
from typing import NamedTuple, Optional

from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget, QTabWidget, QFrame

from ui.widgets import DataPlotStudioButton
from ui.theme import ThemeColors
from ui.icons import IconBuilder, IconType
from core.resource_loader import get_resource_path
from ui.widgets.ControlElements import DataPlotStudioComboBox, DataPlotStudioGroupBox, DataPlotStudioLineEdit

class GoogleSheetsImportConfig(NamedTuple):
    """Payload for Google Sheets import config"""
    sheet_id: str
    sheet_name: str
    delimiter: str
    decimal_separator: str
    thousands_separator: Optional[str]
    gid: Optional[str]

class GoogleSheetsDialog(QDialog):
    """Dialog for importing data from Google Sheets"""
    
    _SHEET_ID_PATTERN = re.compile(r"/d/([a-zA-Z0-0-_]+)")
    _GID_PATTERN = re.compile(r"[#&?]gid=([0-9]+)")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import from Google Sheets")
        self.setWindowIcon(QIcon(get_resource_path("icons/menu_bar/google-sheets-logo-icon.svg")))
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setModal(True)
        self.resize(650, 400)
        self.setMinimumWidth(500)
        self.gid = None
        self._is_current_id_valid = False

        self.init_ui()

    def init_ui(self) -> None:
        """Initialize dialog UI"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        self.tab_widget = QTabWidget()
        connection_tab = QWidget()
        connection_layout_main = QVBoxLayout(connection_tab)
        connection_layout_main.setContentsMargins(20, 20, 20, 20)
        connection_layout_main.setSpacing(15)
        
        header_layout = QHBoxLayout()
        # Info label
        info_label = QLabel("Enter your Google Sheets details below")
        info_label.setObjectName("google_sheets_info_label")
        header_layout.addWidget(info_label)
        
        # A timer to prevent lag on user typing
        self._parse_timer = QTimer(self)
        self._parse_timer.setSingleShot(True)
        self._parse_timer.setInterval(300)
        self._parse_timer.timeout.connect(self._execute_parsing)
        
        header_layout.addStretch()
        
        self.help_button = DataPlotStudioButton("How to Import?", parent=self)
        self.help_button.setToolTip("View instructions for importing Google Sheets data")
        self.help_button.setIcon(IconBuilder.build(IconType.Information))
        self.help_button.clicked.connect(self.show_instructions)
        header_layout.addWidget(self.help_button)
        
        connection_layout_main.addLayout(header_layout)
        
        # Form layout for inputs
        connection_group = DataPlotStudioGroupBox("Connection Details", parent=self)
        connection_form_layout = QFormLayout()
        connection_form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # Shee ID
        sheet_id_label = QLabel("Google Sheet Link or Sheet ID:")
        self.sheet_id = DataPlotStudioComboBox()
        self.sheet_id.setEditable(True)
        self.sheet_id.setToolTip("Paste the full Google Sheets URL or the unique Sheet ID")
        self.sheet_id.lineEdit().setPlaceholderText("Paste URL (e.g., https://docs.google.com/.../edit#gid=0) or ID")
        self.sheet_id.lineEdit().setClearButtonEnabled(True)
        self.sheet_id.setMinimumWidth(350)
        self.sheet_id.editTextChanged.connect(self.parse_input)
        
        sheet_id_layout = QHBoxLayout()
        sheet_id_layout.setContentsMargins(0, 0, 0, 0)
        sheet_id_layout.addWidget(self.sheet_id)
        
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(20, 20)
        self.status_icon.setScaledContents(True)
        
        icon_size_policy = self.status_icon.sizePolicy()
        icon_size_policy.setRetainSizeWhenHidden(True)
        self.status_icon.setSizePolicy(icon_size_policy)
        self.status_icon.hide()
        sheet_id_layout.addWidget(self.status_icon)
        
        self.sheet_id.editTextChanged.connect(self._on_input_changed)
        self.sheet_id.lineEdit().returnPressed.connect(self._on_return_pressed)
        connection_form_layout.addRow(sheet_id_label, sheet_id_layout)
        
        # Sheet Name
        sheet_name_label = QLabel("Sheet Name:")
        self.sheet_name = DataPlotStudioLineEdit()
        self.sheet_name.setToolTip("The name of the sheet you want to import data from")
        self.sheet_name.setPlaceholderText("e.g., Sheet1")
        self.sheet_name.setClearButtonEnabled(True)
        self.sheet_name.textChanged.connect(self._update_import_button_state)
        self.sheet_name.textChanged.connect(lambda: self._clear_validation_state(self.sheet_name))
        self.sheet_name.returnPressed.connect(self._on_return_pressed)
        connection_form_layout.addRow(sheet_name_label, self.sheet_name)
        
        connection_group.setLayout(connection_form_layout)
        connection_layout_main.addWidget(connection_group)
        connection_layout_main.addStretch()
        
        self.tab_widget.addTab(connection_tab, QIcon(IconBuilder.build(IconType.Connect)), "Connection")
        
        # Advanced Settings Tab
        advanced_tab = QWidget()
        advanced_layout_main = QVBoxLayout(advanced_tab)
        advanced_layout_main.setContentsMargins(20, 20, 20, 20)
        advanced_layout_main.setSpacing(15)

        delimiter_group = DataPlotStudioGroupBox("CSV Delimiter Settings", parent=self)
        delimiter_layout = QVBoxLayout()

        delimiter_info = QLabel("Google Sheets exports data as a CSV. Choose the delimiter used in your region.")
        delimiter_info.setWordWrap(True)
        delimiter_info.setProperty("styleClass", "muted_text")
        delimiter_layout.addWidget(delimiter_info)

        # Delimiter settings box
        delimiter_form_layout = QFormLayout()

        self.delimiter_combo = DataPlotStudioComboBox()
        self.delimiter_combo.addItems([
            "Comma (,) - Standard",
            "Semicolon (;) - European",
            "Tab (\\t) - Tab-separated",
            "Pipe (|) - Pipe-separated",
            "Space ( ) - Space-separated",
            "Custom"
        ])
        self.delimiter_combo.setCurrentIndex(0)
        self.delimiter_combo.currentTextChanged.connect(self.on_delimiter_changed)
        delimiter_form_layout.addRow("Delimiter:", self.delimiter_combo)

        # Custom delimiter
        self.custom_delimiter_input = DataPlotStudioLineEdit()
        self.custom_delimiter_input.setPlaceholderText("Enter single character")
        self.custom_delimiter_input.setMaxLength(1)
        self.custom_delimiter_input.setEnabled(False)
        self.custom_delimiter_input.setMaximumWidth(150)
        self.custom_delimiter_input.textChanged.connect(lambda: self._clear_validation_state(self.custom_delimiter_input))
        
        custom_delimiter_hbox = QHBoxLayout()
        custom_delimiter_hbox.addWidget(self.custom_delimiter_input)
        custom_delimiter_hbox.addStretch()
        delimiter_form_layout.addRow("Custom Delimiter:", custom_delimiter_hbox)
        
        parsing_separator = QFrame()
        parsing_separator.setFrameShape(QFrame.Shape.HLine)
        parsing_separator.setProperty("styleClass", "horizontal_divider")
        delimiter_form_layout.addRow(parsing_separator)

        # Decimal separator
        self.decimal_combo = DataPlotStudioComboBox()
        self.decimal_combo.addItems([
            "Dot (.) - UK/US",
            "Comma (,) - European",
        ])
        self.decimal_combo.setCurrentIndex(0)
        self.decimal_combo.setToolTip("Select the character used for decimals")
        delimiter_form_layout.addRow("Decimal Separator:", self.decimal_combo)

        # Thousands separator
        self.thousands_combo = DataPlotStudioComboBox()
        self.thousands_combo.addItems([
            "None",
            "Comma (,) - US Style",
            "Dot (.) - European",
            "Space ( ) - International"
        ])
        self.thousands_combo.setCurrentIndex(0)
        self.thousands_combo.setToolTip("Select the character used to group thousands")
        delimiter_form_layout.addRow("Thousands Separator:", self.thousands_combo)

        delimiter_layout.addLayout(delimiter_form_layout)
        delimiter_group.setLayout(delimiter_layout)
        advanced_layout_main.addWidget(delimiter_group)
        advanced_layout_main.addStretch()

        self.tab_widget.addTab(advanced_tab, QIcon(IconBuilder.build(IconType.Settings)), "Advanced Settings")
        
        main_layout.addWidget(self.tab_widget)
        
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(10, 5, 10, 10)
        button_layout.addStretch()

        self.import_button = DataPlotStudioButton("Import", base_color_hex=ThemeColors.MainColor, text_color_hex="white", parent=self)
        self.import_button.setDefault(True)
        self.import_button.setMinimumWidth(100)
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(self.import_button)

        cancel_button = DataPlotStudioButton("Cancel", parent=self)
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        main_layout.addWidget(button_container)
        self.setLayout(main_layout)

        self._setup_tab_order()
        self.load_history()
        self.sheet_id.setFocus()
    
    def _setup_tab_order(self) -> None:
        """Define tab order for keyboard navigation"""
        self.setTabOrder(self.sheet_id, self.sheet_name)
        self.setTabOrder(self.sheet_name, self.delimiter_combo)
        self.setTabOrder(self.delimiter_combo, self.custom_delimiter_input)
        self.setTabOrder(self.custom_delimiter_input, self.decimal_combo)
        self.setTabOrder(self.decimal_combo, self.thousands_combo)
        self.setTabOrder(self.thousands_combo, self.import_button)
    
    def show_instructions(self) -> None:
        help_text = (
            "<b>How to use Google Sheets Import:</b><br><br>"
            "1. Open your Google Sheet in a browser.<br>"
            "2. Copy the ID from the URL:<br>"
            "&nbsp;&nbsp;&nbsp;<span style='color: #888888;'>docs.google.com/spreadsheets/d/<b>[SHEET_ID]</b>/edit</span><br>"
            "3. Check the sheet tab name (bottom left corner).<br>"
            "4. <b>IMPORTANT:</b> Share the sheet publicly<br>"
            "&nbsp;&nbsp;&nbsp;<i>(File → Share → \"Anyone with the link\")</i>.<br>"
            "5. If needed, configure delimiters in the <b>Advanced Settings</b> tab.<br>"
            "6. Paste the ID and sheet name into the connection dialog."
        )
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Google Sheets Import Instructions")
        msg_box.setObjectName("blue_help_box")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(help_text)
        msg_box.exec()
    
    def _on_input_changed(self, text: str) -> None:
        """Triggers the timer when text changes to prevent sutter"""
        self._pending_parse_text = text
        self._parse_timer.start()
    
    def _execute_parsing(self) -> None:
        """Executes parsing after timer deboucne"""
        self.parse_input(self._pending_parse_text)
        self._update_import_button_state()
    
    def _on_return_pressed(self) -> None:
        """Submit form with Key_Return if all validations are met"""
        if self.import_button.isEnabled():
            self.validate_and_accept()
    
    def _update_import_button_state(self) -> None:
        """Enable the import button only when required fields are populated"""
        has_name_or_gid = bool(self.gid) or bool(self.sheet_name.text().strip())
        self.import_button.setEnabled(self._is_current_id_valid and has_name_or_gid)

    def on_delimiter_changed(self, text) -> None:
        """Handle delimiter selection change"""
        is_custom = (text == "Custom")
        self.custom_delimiter_input.setEnabled(is_custom)
        if is_custom:
            self.custom_delimiter_input.clear()
            self.custom_delimiter_input.setFocus()
    
    def _clear_validation_state(self, widget: QWidget) -> None:
        """Clears the visual error state from widget"""
        if widget.property("validationState") == "error":
            widget.setProperty("validationState", "normal")
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def parse_input(self, text: str) -> None:
        """Parse the input for URL and extract sheet ID and GID"""
        clean_text = text.strip()
        
        # Regex to match sheet id
        id_match = self._SHEET_ID_PATTERN.search(clean_text)
        is_valid_id = False
        
        if id_match:
            is_valid_id = True
            extracted_id = id_match.group(1)
            if self.sheet_id.currentText() != extracted_id:
                self.sheet_id.blockSignals(True)
                self.sheet_id.setCurrentText(extracted_id)
                self.sheet_id.blockSignals(False)
            
            # Look for a GID
            gid_match = self._GID_PATTERN.search(clean_text)
            if gid_match:
                self.gid = gid_match.group(1)
                # Disable sheet name as input to avoid a situation where a sheet name that doesnt match GID is given
                self.sheet_name.setEnabled(False)
                self.sheet_name.clear()
                self.sheet_name.setPlaceholderText(f"Using GID from URL ({self.gid})")
                self.sheet_name.setToolTip("A GID was detected in the URL. Manual sheet name input has been disabled")
            else:
                self.gid = None
                self.sheet_name.setEnabled(True)
                self.sheet_name.setPlaceholderText("e.g., Sheet1")
                self.sheet_name.setToolTip("The name of the sheet you want to import data from")
        else:
            if not clean_text.startswith("http"):
                self.gid = None
                self.sheet_name.setEnabled(True)
                self.sheet_name.setPlaceholderText("e.g., Sheet1")
                self.sheet_name.setToolTip("The name of the sheet you want to import data from")
                if len(clean_text) > 20 and re.match(r"^[a-zA-Z0-9-_]+$", clean_text):
                    is_valid_id = True
        
        self._is_current_id_valid = is_valid_id
        
        if is_valid_id:
            self.status_icon.setPixmap(QIcon(IconBuilder.build(IconType.Checkmark)).pixmap(20, 20))
            self.status_icon.setToolTip("Valid Google Sheet ID")
            self.status_icon.show()
        elif clean_text:
            self.status_icon.setPixmap(QIcon(IconBuilder.build(IconType.Information)).pixmap(20, 20))
            self.status_icon.setToolTip("Invalid Google Sheets URL or ID format. Please verify your input.")
            self.status_icon.show()
        else:
            self.status_icon.hide()
        
    def reject(self) -> None:
        """Reject override to ensure resources are cleaned up when dialog is destroyed"""
        if self._parse_timer.isActive():
            self._parse_timer.stop()
        super().reject()

    def validate_and_accept(self) -> None:
        """Validate inputs before accepting"""
        cleaned_sheet_name = self.sheet_name.text().strip()
        if self.sheet_name.text() != cleaned_sheet_name:
            self.sheet_name.blockSignals(True)
            self.sheet_name.setText(cleaned_sheet_name)
            self.sheet_name.blockSignals(False)
            
        for widget in [self.sheet_name, self.custom_delimiter_input]:
            if widget.property("validationState") != "normal":
                widget.setProperty("validationState", "error")
                widget.style().unpolish(widget)
                widget.style().polish(widget)
        
        if not self.gid and not self.sheet_name.text():
            self._route_validation_error(
                widget=self.sheet_name,
                tab_index=0,
                error_message="Please enter a Sheet Name or provide a URl with a 'gid'"
            )
            return
        
        if self.delimiter_combo.currentText() == "Custom":
            if not self.custom_delimiter_input.text().strip():
                self._route_validation_error(
                    widget=self.custom_delimiter_input,
                    tab_index=1,
                    error_message="Please enter a single custom delimiter character"
                )
                return
        
        self.save_history()
        self.accept()
    
    def _route_validation_error(self, widget: QWidget, tab_index: int, error_message: str) -> None:
        """Highlights the offending widget, switches parent tab and grants it focus"""
        widget.setProperty("validationState", "error")
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        
        # Force the tab containing the rror
        if self.tab_widget.currentIndex() != tab_index:
            self.tab_widget.setCurrentIndex(tab_index)
        
        widget.setFocus()
        QMessageBox.warning(self, "Validation Error", error_message)

    def get_inputs(self) -> GoogleSheetsImportConfig:
        """Return the sheet ID and name and delimiter settings"""
        sheet_id = self.sheet_id.currentText().strip()
        sheet_name = self.sheet_name.text().strip()

        #delimiter
        delimiter_text = self.delimiter_combo.currentText()
        if delimiter_text.startswith("Comma"):
            delimiter = ","
        elif delimiter_text.startswith("Semicolon"):
            delimiter = ";"
        elif delimiter_text.startswith("Tab"):
            delimiter = "\t"
        elif delimiter_text.startswith("Pipe"):
            delimiter = "|"
        elif delimiter_text.startswith("Space"):
            delimiter = " "
        elif delimiter_text == "Custom":
            delimiter = self.custom_delimiter_input.text().strip()
        else:
            delimiter = ","

        #get decimal separator
        decimal_text = self.decimal_combo.currentText()
        decimal = "," if decimal_text.startswith("Comma") else "."

        # get thousands sep
        thousands_text = self.thousands_combo.currentText()
        if thousands_text.startswith("None"):
            thousands = None
        elif thousands_text.startswith("Comma"):
            thousands = ","
        elif thousands_text.startswith("Dot"):
            thousands = "."
        elif thousands_text.startswith("Space"):
            thousands = " "
        else:
            thousands = None

        return GoogleSheetsImportConfig(
            sheet_id=sheet_id,
            sheet_name=sheet_name,
            delimiter=delimiter,
            decimal_separator=decimal,
            thousands_separator=thousands,
            gid=self.gid
        )

    def load_history(self) -> None:
        """Load sheet ID history from settings"""
        settings = QSettings("DataPlotStudio", "GoogleSheetsImport")
        history = settings.value("history", [], type=list)
        raw_history_names = settings.value("history_names", {}, type=dict)

        history = [str(item) for item in history if isinstance(item, (str, int))]
        self._history_names = {key: val for key, val in raw_history_names.items() if key in history}

        self.sheet_id.blockSignals(True)
        self.sheet_id.clear()
        self.sheet_id.addItems(history)
        self.sheet_id.setCurrentIndex(-1)
        self.sheet_id.blockSignals(False)
        
        self.sheet_id.activated.connect(self._auto_fill_sheet_name)
    
    def _auto_fill_sheet_name(self, index: int) -> None:
        """Populate the sheet name if it already is associated with a Sheet ID"""
        selected_id = self.sheet_id.itemText(index)
        if selected_id in self._history_names and self.sheet_name.isEnabled():
            self.sheet_name.setText(self._history_names[selected_id])
    
    def save_history(self) -> None:
        """Save the current sheet id to history"""
        current_id = self.sheet_id.currentText().strip()
        current_name = self.sheet_name.text().strip()
        
        if not current_id:
            return
        
        settings = QSettings("DataPlotStudio", "GoogleSheetsImport")
        history = settings.value("history", [], type=list)
        history_names = settings.value("history_names", {}, type=dict)

        history = [str(item) for item in history if isinstance(item, (str, int))]

        if current_id in history:
            history.remove(current_id)
        
        history.insert(0, current_id)
        history = history[:10]

        self._history_names = {key: val for key, val in history_names.items() if key in history}
        
        if current_name:
            history_names[current_id] = current_name

        settings.setValue("history", history)
        settings.setValue("history_names", history_names)