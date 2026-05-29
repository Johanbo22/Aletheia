from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import pyqtSignal, Qt

from core.resource_loader import get_resource_path
from ui.icons import IconBuilder, IconType
from ui.theme import ThemeColors

class DataViewToolbar(QWidget):
    """
    Toolbar containing actions for the data view
    """
    create_dataset_requested = pyqtSignal()
    refresh_data_requested = pyqtSignal()
    python_console_requested = pyqtSignal()
    edit_mode_toggled = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.is_editing: bool = False
        self._init_ui()

    def _init_ui(self) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        toolbar_layout = QHBoxLayout(self)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)

        # Create dataset
        self.create_new_dataset_button = QPushButton("Create New Dataset")
        self.create_new_dataset_button.setObjectName("MainActionButton")
        self.create_new_dataset_button.setIcon(IconBuilder.build(IconType.NewProject))
        self.create_new_dataset_button.setToolTip("Create a new empty DataFrame")
        self.create_new_dataset_button.clicked.connect(self.create_dataset_requested.emit)
        toolbar_layout.addWidget(self.create_new_dataset_button)

        # Refresh Data Source
        self.data_source_refresh_button = QPushButton("Refresh Data")
        self.data_source_refresh_button.setObjectName("GoogleSheetReImport")
        self.data_source_refresh_button.setIcon(
            QIcon(get_resource_path("icons/menu_bar/google_sheet.png"))
        )
        self.data_source_refresh_button.setToolTip("Re-import data from your Google Sheets document")
        self.data_source_refresh_button.clicked.connect(self.refresh_data_requested.emit)
        self.data_source_refresh_button.setVisible(False)
        toolbar_layout.addWidget(self.data_source_refresh_button)

        toolbar_layout.addStretch()

        # Python Console
        self.python_console_button = QPushButton("", parent=self)
        self.python_console_button.setIcon(QIcon(get_resource_path("icons/menu_bar/python-5.svg")))
        self.python_console_button.setToolTip(
            "Open the Python Console to use commands to directly work with the DataFrame")
        self.python_console_button.clicked.connect(self.python_console_requested.emit)
        toolbar_layout.addWidget(self.python_console_button)

        # Edit Mode Toggle
        self.edit_dataset_toggle_button = QPushButton("Edit Mode: OFF", parent=self)
        self.edit_dataset_toggle_button.setObjectName("EditModeButton")
        self.edit_dataset_toggle_button.setIcon(IconBuilder.build(IconType.EditModeToggleOff))
        self.edit_dataset_toggle_button.setCheckable(True)
        self.edit_dataset_toggle_button.setToolTip("Toggle to edit data directly in the table")
        self.edit_dataset_toggle_button.clicked.connect(self._handle_edit_toggled)
        toolbar_layout.addWidget(self.edit_dataset_toggle_button)

    def _handle_edit_toggled(self) -> None:
        """
        Handles the visual update for the the edit button and emits the new state.
        Color state is handled by CSS via the :checked pseudo-class.
        """
        self.is_editing = self.edit_dataset_toggle_button.isChecked()

        if self.is_editing:
            self.edit_dataset_toggle_button.setText("Edit Mode: ON")
            self.edit_dataset_toggle_button.setIcon(IconBuilder.build(IconType.EditModeToggleOn))
        else:
            self.edit_dataset_toggle_button.setText("Edit Mode: OFF")
            self.edit_dataset_toggle_button.setIcon(IconBuilder.build(IconType.EditModeToggleOff))
        self.edit_mode_toggled.emit(self.is_editing)

    def set_refresh_visible(self, visible: bool) -> None:
        """
        Shows or hides the Google Sheets refresh button
        """
        self.data_source_refresh_button.setVisible(visible)