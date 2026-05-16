from PyQt6.QtWidgets import QWidget, QHBoxLayout
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import pyqtSignal, Qt

from core.resource_loader import get_resource_path
from ui.widgets import DataPlotStudioButton
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
        self.create_new_dataset_button = DataPlotStudioButton(
            "Create a New Dataset",
            parent=self,
            base_color_hex=ThemeColors.MainColor,
            text_color_hex="white",
        )
        self.create_new_dataset_button.setIcon(IconBuilder.build(IconType.NewProject))
        self.create_new_dataset_button.setToolTip("Create a new empty DataFrame")
        self.create_new_dataset_button.clicked.connect(self.create_dataset_requested.emit)
        toolbar_layout.addWidget(self.create_new_dataset_button)

        # Refresh Data Source
        self.data_source_refresh_button = DataPlotStudioButton(
            "Refresh Data",
            parent=self,
            base_color_hex="#27ae60",
            hover_color_hex="#229954",
            text_color_hex="white",
            font_weight="bold",
        )
        self.data_source_refresh_button.setIcon(
            QIcon(get_resource_path("icons/menu_bar/google_sheet.png"))
        )
        self.data_source_refresh_button.setToolTip("Re-import data from your Google Sheets document")
        self.data_source_refresh_button.clicked.connect(self.refresh_data_requested.emit)
        self.data_source_refresh_button.setVisible(False)
        toolbar_layout.addWidget(self.data_source_refresh_button)

        toolbar_layout.addStretch()

        # Python Console
        self.python_console_button = DataPlotStudioButton("", parent=self)
        self.python_console_button.setIcon(QIcon(get_resource_path("icons/menu_bar/python-5.svg")))
        self.python_console_button.setToolTip(
            "Open the Python Console to use commands to directly work with the DataFrame")
        self.python_console_button.clicked.connect(self.python_console_requested.emit)
        toolbar_layout.addWidget(self.python_console_button)

        # Edit Mode Toggle
        self.edit_dataset_toggle_button = DataPlotStudioButton(
            "Edit Mode: OFF",
            parent=self,
            base_color_hex="#95a5a6",
            text_color_hex="white",
        )
        self.edit_dataset_toggle_button.setIcon(IconBuilder.build(IconType.EditModeToggleOff))
        self.edit_dataset_toggle_button.setCheckable(True)
        self.edit_dataset_toggle_button.setToolTip("Toggle to edit data directly in the table")
        self.edit_dataset_toggle_button.clicked.connect(self._handle_edit_toggled)
        toolbar_layout.addWidget(self.edit_dataset_toggle_button)

    def _handle_edit_toggled(self) -> None:
        """
        Handles the visual update for the the edit button and emits the new state
        """
        self.is_editing = self.edit_dataset_toggle_button.isChecked()

        if self.is_editing:
            self.edit_dataset_toggle_button.setText("Edit Mode: ON")
            self.edit_dataset_toggle_button.setIcon(IconBuilder.build(IconType.EditModeToggleOn))
            self.edit_dataset_toggle_button.updateColors(
                base_color_hex="#E74C3C", hover_color_hex="#C0392B"
            )
        else:
            self.edit_dataset_toggle_button.setText("Edit Mode: OFF")
            self.edit_dataset_toggle_button.setIcon(IconBuilder.build(IconType.EditModeToggleOff))
            self.edit_dataset_toggle_button.updateColors(
                base_color_hex="#95A5A6", hover_color_hex="#7F8C8D"
            )
        self.edit_mode_toggled.emit(self.is_editing)

    def set_refresh_visible(self, visible: bool) -> None:
        """
        Shows or hides the Google Sheets refresh button
        """
        self.data_source_refresh_button.setVisible(visible)