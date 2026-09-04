import json
import logging
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QFontDatabase, QPaintEvent, QPainter, QPen
from PyQt6.QtWidgets import QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox, \
    QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QScrollArea, QSplitter, QVBoxLayout, QWidget

from src.core.global_signals import LogLevel, ToastLevel, global_signals
from src.ui.PythonHighlighter import DefaultColorScheme, PythonHighlighter, SyntaxCategory

logger = logging.getLogger(__name__)

PREDEFINED_SCHEMES: Dict[str, Dict[SyntaxCategory, str]] = {
    "Default (Dracula)": DefaultColorScheme,
    "Light Theme"      : {
        SyntaxCategory.Keyword    : "#0000ff",
        SyntaxCategory.Builtin    : "#795e26",
        SyntaxCategory.Self_Cls   : "#0000ff",
        SyntaxCategory.Decorator  : "#af00db",
        SyntaxCategory.String     : "#a31515",
        SyntaxCategory.Docstring  : "#008000",
        SyntaxCategory.Number     : "#098658",
        SyntaxCategory.Function   : "#795e26",
        SyntaxCategory.ClassName  : "#267f99",
        SyntaxCategory.MagicMethod: "#795e26",
        SyntaxCategory.Operator   : "#000000",
        SyntaxCategory.Comment    : "#008000"
    },
    "Solarized Dark"   : {
        SyntaxCategory.Keyword    : "#859900",
        SyntaxCategory.Builtin    : "#b58900",
        SyntaxCategory.Self_Cls   : "#268bd2",
        SyntaxCategory.Decorator  : "#d33682",
        SyntaxCategory.String     : "#2aa198",
        SyntaxCategory.Docstring  : "#586e75",
        SyntaxCategory.Number     : "#d33682",
        SyntaxCategory.Function   : "#268bd2",
        SyntaxCategory.ClassName  : "#b58900",
        SyntaxCategory.MagicMethod: "#cb4b16",
        SyntaxCategory.Operator   : "#839496",
        SyntaxCategory.Comment    : "#586e75"
    }
}

class ColorPickerButton(QPushButton):
    """
    An interactive button that triggers a QColorDialog and reports color changes
    """
    color_changed = pyqtSignal(str)

    def __init__(self, initial_color: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._color: str = initial_color
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(40, 24)
        self.setProperty("isColorPicker", True)
        self.setToolTip(f"Current color: {self._color}")
        self.clicked.connect(self._choose_color)

    def get_color(self) -> str:
        """Return the current hex color string"""
        return self._color

    def set_color(self, color: str, emit_signal: bool = True) -> None:
        """
        Update the button color and tooltip

        :param color: Hex color string
        :param emit_signal: Whether to emit the color_changed signal.
        """
        if self._color != color:
            self._color = color
            self.setToolTip(f"Current color: {self._color}")
            self.update()
            if emit_signal:
                self.color_changed.emit(self._color)

    def paintEvent(self, event: QPaintEvent) -> None:
        """PaintEvent for drawing color button"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        border_color = QColor("#222222") if self.underMouse() else QColor("#555555")

        painter.setBrush(QBrush(QColor(self._color)))
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(rect, 4, 4)
        painter.end()

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self.window(), "Select Color for this syntax token")
        if color.isValid():
            self.set_color(color.name())

class SyntaxHighlightSettingsDialog(QDialog):
    """
    Dialog to customize the syntax highlighting colors
    """

    def __init__(self, current_scheme: Dict[SyntaxCategory, str], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Syntax Highlighting Settings")
        self.resize(860, 540)
        self.setMinimumSize(700, 450)
        self.setObjectName("syntax_highlight_settings_dialog")

        self._initial_scheme: Dict[SyntaxCategory, str] = current_scheme.copy()
        self.color_buttons: Dict[SyntaxCategory, ColorPickerButton] = {}
        self._is_syncing_theme: bool = False

        self._init_ui(current_scheme)
        self._match_current_scheme_to_theme(current_scheme)
        self._update_preview_background()

    def _init_ui(self, current_scheme: Dict[SyntaxCategory, str]) -> None:
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        controls_widget = self._create_controls_group(current_scheme)
        preview_widget = self._create_preview_group(current_scheme)

        splitter.addWidget(controls_widget)
        splitter.addWidget(preview_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        main_layout.addWidget(splitter)
        self._setup_button_box(main_layout)

    def _create_controls_group(self,
                               current_scheme: Dict[SyntaxCategory, str]
                               ) -> QGroupBox:
        controls_widget = QGroupBox("Color Scheme")
        controls_widget.setMinimumWidth(280)
        controls_layout = QVBoxLayout(controls_widget)

        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Preset Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("theme_preset_combo")
        self.theme_combo.addItems(["Custom"] + list(PREDEFINED_SCHEMES.keys()))
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        controls_layout.addLayout(theme_layout)

        management_layout = QHBoxLayout()
        self.import_btn = QPushButton("Import JSON")
        self.import_btn.clicked.connect(self._import_theme)

        self.export_btn = QPushButton("Export JSON")
        self.export_btn.clicked.connect(self._export_theme)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setToolTip("Reset to the default theme")
        self.reset_btn.clicked.connect(self._reset_to_default)

        management_layout.addWidget(self.import_btn)
        management_layout.addWidget(self.export_btn)
        management_layout.addWidget(self.reset_btn)
        controls_layout.addLayout(management_layout)

        controls_layout.addWidget(self._create_scrollable_form(current_scheme))
        return controls_widget

    def _create_scrollable_form(self, current_scheme: Dict[SyntaxCategory, str]) -> QScrollArea:
        scroll_area = QScrollArea()
        scroll_area.setProperty("styleClass", "transparent_scroll_area")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        form_container = QWidget()
        form_layout = QFormLayout(form_container)
        form_layout.setVerticalSpacing(8)

        category: SyntaxCategory
        for category in SyntaxCategory:
            btn = ColorPickerButton(current_scheme.get(category, "#ffffff"), form_container)
            btn.color_changed.connect(self._on_custom_color_picked)
            self.color_buttons[category] = btn
            form_layout.addRow(f"{category.value}:", btn)

        scroll_area.setWidget(form_container)
        return scroll_area

    def _create_preview_group(self, current_scheme: Dict[SyntaxCategory, str]) -> QGroupBox:
        preview_widget = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_widget)

        self.preview_editor = QPlainTextEdit()
        self.preview_editor.setReadOnly(True)
        self.preview_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.preview_editor.setObjectName("syntax_preview_editor")

        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.preview_editor.setFont(font)

        self.preview_highlighter = PythonHighlighter(
            self.preview_editor.document(), current_scheme
        )
        self.preview_editor.setPlainText(self._get_preview_text())
        preview_layout.addWidget(self.preview_editor)

        return preview_widget

    def _setup_button_box(self, layout: QVBoxLayout) -> None:
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _get_preview_text(self) -> str:
        """Returns a sample python code covering the syntax tokens"""
        return (
            "import pandas as pd\n\n"
            "@dataclass\n"
            "class PlotGenerator:\n"
            "    \"\"\"\n"
            "    Handles custom plotting routines.\n"
            "    \"\"\"\n"
            "    def __init__(self, data: pd.DataFrame):\n"
            "        self.data = data\n"
            "        self.is_ready = True\n"
            "        self._count = 0\n\n"
            "    def generate(self, title: str = \"Plot\") -> None:\n"
            "        # Validate data before plotting\n"
            "        if self.data is None or len(self.data) == 0:\n"
            "            raise ValueError('Data cannot be empty')\n\n"
            "        print(f\"Generating {title}...\")\n"
            "        for idx, row in enumerate(self.data.iterrows()):\n"
            "            self._count += 1\n"
            "            match self._count:\n"
            "                case 1:\n"
            "                    pass\n"
        )

    def _update_live_preview(self) -> None:
        new_scheme = self.get_color_scheme()
        self.preview_highlighter.set_color_scheme(new_scheme)
        self._update_preview_background()

    def _update_preview_background(self) -> None:
        """Adjusts the background of the preview to help visibility"""
        is_light_theme = self.theme_combo.currentText() == "Light Theme"
        theme_mode = "light" if is_light_theme else "dark"

        if self.preview_editor.property("themeMode") != theme_mode:
            self.preview_editor.setProperty("themeMode", theme_mode)
            self.preview_editor.style().unpolish(self.preview_editor)
            self.preview_editor.style().polish(self.preview_editor)

    def _on_custom_color_picked(self, new_color: str = "") -> None:
        """Handles state transitions when a user manually picks a new color"""
        if self._is_syncing_theme:
            return

        if self.theme_combo.currentText() != "Custom":
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentText("Custom")
            self.theme_combo.blockSignals(False)
        self._update_live_preview()

    def _match_current_scheme_to_theme(self, current_scheme: Dict[SyntaxCategory, str]) -> None:
        """
        Restarts the combobox index based on signature
        """
        for theme_name, theme_scheme in PREDEFINED_SCHEMES.items():
            if current_scheme == theme_scheme:
                self.theme_combo.blockSignals(True)
                self.theme_combo.setCurrentText(theme_name)
                self.theme_combo.blockSignals(False)
                return

        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentText("Custom")
        self.theme_combo.blockSignals(False)

    def _on_theme_changed(self, theme_name: str) -> None:
        """
        Handles the signal for a theme change and updates the buttons and their color scheme

        :param theme name: The name of the theme selected
        """
        if theme_name not in PREDEFINED_SCHEMES:
            return

        self._is_syncing_theme = True
        theme_scheme = PREDEFINED_SCHEMES[theme_name]

        for category, btn in self.color_buttons.items():
            btn.set_color(theme_scheme[category], emit_signal=False)
        self._is_syncing_theme = False
        self._update_live_preview()

    def _reset_to_default(self) -> None:
        self.theme_combo.setCurrentText("Default (Dracula)")

    def _export_theme(self) -> None:
        """Exports the current color scheme to a JSON file."""
        safe_theme_name = self.theme_combo.currentText().replace(" ", "_").lower()
        default_file_name = f"{safe_theme_name}_syntax.json"

        file_path_str, _ = QFileDialog.getSaveFileName(
            self, "Export Syntax Theme", default_file_name, "JSON Files (*.json)"
        )
        if not file_path_str:
            return

        export_path = Path(file_path_str)
        try:
            scheme: Dict[SyntaxCategory, str] = self.get_color_scheme()
            export_data: Dict[str, str] = {category.value: color for category, color in scheme.items()}

            with export_path.open("w", encoding="utf-8") as file:
                json.dump(export_data, file, indent=4)

            global_signals.request_toast(
                "Export Successful", f"Theme saved to:\n{export_path.name}", ToastLevel.SUCCESS
            )
        except OSError as err:
            global_signals.request_toast(
                "Export Error", f"Failed to export syntax theme:\n{err}", ToastLevel.ERROR
            )
            global_signals.request_log(
                f"Failed to export theme to file: {str(err)}", LogLevel.ERROR
            )

    def _import_theme(self) -> None:
        """Imports a JSON theme file and applies it"""
        file_path_str, _ = QFileDialog.getOpenFileName(
            self, "Import Syntax Theme", "", "JSON Files (*.json)"
        )

        if not file_path_str:
            return

        import_path: Path = Path(file_path_str)
        try:
            with import_path.open('r', encoding='utf-8') as file:
                import_data: dict = json.load(file)

            imported_count = 0
            for category_string, color in import_data.items():
                try:
                    category = SyntaxCategory(category_string)
                    if category in self.color_buttons:
                        self.color_buttons[category].set_color(color, emit_signal=False)
                        imported_count += 1
                except ValueError:
                    continue

            if imported_count == 0:
                global_signals.request_toast(
                    "No Valid Syntax", "No valid syntax categories found in the file", ToastLevel.WARNING
                )
                return

            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentText("Custom")
            self.theme_combo.blockSignals(False)
            self._update_live_preview()
            global_signals.request_toast(
                "Import Successful", f"Imported {imported_count} color settings", ToastLevel.SUCCESS
            )

        except (json.JSONDecodeError, ValueError) as err:
            global_signals.request_toast(
                "Invalid JSON", f"Unable to parse JSON file: {err}", ToastLevel.ERROR
            )
        except OSError as err:
            global_signals.request_toast(
                "Import Error", f"Failed to read file:\n{err}", ToastLevel.ERROR
            )
            global_signals.request_log(
                f"Failed to read theme file: {err}", LogLevel.ERROR
            )

    def get_color_scheme(self) -> Dict[SyntaxCategory, str]:
        """Return the user defined color scheme dict"""
        return {cat: btn.get_color() for cat, btn in self.color_buttons.items()}
