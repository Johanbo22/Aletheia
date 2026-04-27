import re

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget, QTabWidget

from ui.widgets import DataPlotStudioButton, DataPlotStudioGroupBox, DataPlotStudioLineEdit, DataPlotStudioComboBox
from ui.theme import ThemeColors
from ui.icons import IconBuilder, IconType
from core.resource_loader import get_resource_path

class GoogleSheetsDialog(QDialog):
    """Dialog for importing data from Google Sheets"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import from Google Sheets")
        self.setWindowIcon(QIcon(get_resource_path("icons/menu_bar/google-sheets-logo-icon.svg")))
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setModal(True)
        self.resize(650, 400)
        self.setMinimumWidth(500)
        self.gid = None

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
        self.status_icon.setToolTip("Valid Google Sheet ID detected")
        self.status_icon.hide()
        sheet_id_layout.addWidget(self.status_icon)
        
        self.sheet_id.editTextChanged.connect(self.parse_input)
        connection_form_layout.addRow(sheet_id_label, sheet_id_layout)
        
        # Sheet Name
        sheet_name_label = QLabel("Sheet Name:")
        self.sheet_name = DataPlotStudioLineEdit()
        self.sheet_name.setToolTip("The name of the sheet you want to import data from")
        self.sheet_name.setPlaceholderText("e.g., Sheet1")
        self.sheet_name.setClearButtonEnabled(True)
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
        
        custom_delimiter_hbox = QHBoxLayout()
        custom_delimiter_hbox.addWidget(self.custom_delimiter_input)
        custom_delimiter_hbox.addStretch()
        delimiter_form_layout.addRow("Custom Delimiter:", custom_delimiter_hbox)

        # Decimal separator
        self.decimal_combo = DataPlotStudioComboBox()
        self.decimal_combo.addItems([
            "Dot (.) - UK/US",
            "Comma (,) - European",
        ])
        self.decimal_combo.setCurrentIndex(0)
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

        self.load_history()
        self.sheet_id.setFocus()
    
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
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(help_text)
        msg_box.exec()

    def on_delimiter_changed(self, text) -> None:
        """Handle delimiter selection change"""
        is_custom = (text == "Custom")
        self.custom_delimiter_input.setEnabled(is_custom)
        if is_custom:
            self.custom_delimiter_input.setFocus()

    def parse_input(self, text: str) -> None:
        """Parse the input for URL and extract sheet ID and GID"""
        self.import_button.setEnabled(bool(text.strip()))
        # Regex to match sheet id
        id_match = re.search(r"/d/([a-zA-Z0-9-_]+)", text)
        is_valid_id = False

        if id_match:
            is_valid_id = True
            extracted_id = id_match.group(1)
            if self.sheet_id.currentText() != extracted_id:
                self.sheet_id.blockSignals(True)
                self.sheet_id.setCurrentText(extracted_id)
                self.sheet_id.blockSignals(False)
            
            # Look for a GID
            gid_match = re.search(r"[#&?]gid=([0-9]+)", text)
            if gid_match:
                self.gid = gid_match.group(1)
                # Disable the sheet name as input to avoid a situation where the a sheet name that doesnt match GID is given
                self.sheet_name.setEnabled(False)
                self.sheet_name.clear()
                self.sheet_name.setPlaceholderText(f"Locked: Using GID from URL ({self.gid})")
            else:
                self.gid = None
                self.sheet_name.setEnabled(True)
                self.sheet_name.setPlaceholderText("e.g., Sheet1")
        else:
            if not text.startswith("http"):
                self.gid = None
                self.sheet_name.setEnabled(True)
                self.sheet_name.setPlaceholderText("e.g., Sheet1")
                if len(text.strip()) > 20 and re.match(r"^[a-zA-Z0-9-_]+$", text.strip()):
                    is_valid_id = True
        
        if is_valid_id:
            self.status_icon.setPixmap(QIcon(IconBuilder.build(IconType.Checkmark)).pixmap(20, 20))
            self.status_icon.show()
        else:
            self.status_icon.hide()
        

    def validate_and_accept(self) -> None:
        """Validate inputs before accepting"""
        for widget in [self.sheet_name, self.custom_delimiter_input]:
            widget.setProperty("validationState", "normal")
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        
        if not self.gid and not self.sheet_name.text().strip():
            self.sheet_name.setProperty("validationState", "error")
            self.sheet_name.style().unpolish(self.sheet_name)
            self.sheet_name.style().polish(self.sheet_name)
            self.sheet_name.setFocus()
            QMessageBox.warning(self, "Validation Error", "Please enter a Sheet Name or provide a URL with a 'gid'.")
            return
        
        if self.delimiter_combo.currentText() == "Custom":
            if not self.custom_delimiter_input.text().strip():
                self.custom_delimiter_input.setProperty("validationState", "error")
                self.custom_delimiter_input.style().unpolish(self.custom_delimiter_input)
                self.custom_delimiter_input.style().polish(self.custom_delimiter_input)
                self.custom_delimiter_input.setFocus()
                QMessageBox.warning(self, "Validation Error", "Please enter a single delimiter character.")
                return
        
        self.save_history()
        self.accept()

    def get_inputs(self) -> tuple:
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

        return sheet_id, sheet_name, delimiter, decimal, thousands, self.gid

    def load_history(self) -> None:
        """Load sheet ID history from settings"""
        settings = QSettings("DataPlotStudio", "GoogleSheetsImport")
        history = settings.value("history", [], type=list)

        history = [str(item) for item in history if isinstance(item, (str, int))]

        self.sheet_id.clear()
        self.sheet_id.addItems(history)
        self.sheet_id.setCurrentIndex(-1)
    
    def save_history(self) -> None:
        """Save the current sheet id to history"""
        current_id = self.sheet_id.currentText().strip()
        if not current_id:
            return
        
        settings = QSettings("DataPlotStudio", "GoogleSheetsImport")
        history = settings.value("history", [], type=list)

        history = [str(item) for item in history if isinstance(item, (str, int))]

        if current_id in history:
            history.remove(current_id)
        
        history.insert(0, current_id)
        history = history[:10]

        settings.setValue("history", history)