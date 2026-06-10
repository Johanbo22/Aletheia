import json
from pathlib import Path
from typing import Dict

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton, QComboBox, QColorDialog, QDialogButtonBox, QPlainTextEdit, QGroupBox, QSplitter, QFileDialog, QMessageBox, QWidget, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFontDatabase, QFont, QPaintEvent, QPainter, QBrush, QPen

from ui.PythonHighlighter import SyntaxCategory, DefaultColorScheme, PythonHighlighter

PREDEFINED_SCHEMES: Dict[str, Dict[SyntaxCategory, str]] = {
    "Default (Dracula)": DefaultColorScheme,
    "Light Theme": {
        SyntaxCategory.Keyword: "#0000ff",
        SyntaxCategory.Builtin: "#795e26",
        SyntaxCategory.Self_Cls: "#0000ff",
        SyntaxCategory.Decorator: "#af00db",
        SyntaxCategory.String: "#a31515",
        SyntaxCategory.Docstring: "#008000",
        SyntaxCategory.Number: "#098658",
        SyntaxCategory.Function: "#795e26",
        SyntaxCategory.ClassName: "#267f99",
        SyntaxCategory.MagicMethod: "#795e26",
        SyntaxCategory.Operator: "#000000",
        SyntaxCategory.Comment: "#008000"
    },
    "Solarized Dark": {
        SyntaxCategory.Keyword: "#859900",
        SyntaxCategory.Builtin: "#b58900",
        SyntaxCategory.Self_Cls: "#268bd2",
        SyntaxCategory.Decorator: "#d33682",
        SyntaxCategory.String: "#2aa198",
        SyntaxCategory.Docstring: "#586e75",
        SyntaxCategory.Number: "#d33682",
        SyntaxCategory.Function: "#268bd2",
        SyntaxCategory.ClassName: "#b58900",
        SyntaxCategory.MagicMethod: "#cb4b16",
        SyntaxCategory.Operator: "#839496",
        SyntaxCategory.Comment: "#586e75"
    }
}

class ColorPickerButton(QPushButton):
    
    color_changed = pyqtSignal(str)
    
    def __init__(self, initial_color: str, parent=None) -> None:
        super().__init__(parent)
        self._color: str = initial_color
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(40, 24)
        self.setProperty("isColorPicker", True)
        self.clicked.connect(self._choose_color)
    
    def get_color(self) -> str:
        return self._color
    
    def set_color(self, color: str, emit_signal: bool = True) -> None:
        if self._color != color:
            self._color = color
            self.update()
            if emit_signal:
                self.color_changed.emit(self._color)
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """PaintEvent for drawing color button"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)

        painter.setBrush(QBrush(QColor(self._color)))
        painter.setPen(QPen(QColor("#555555"), 1))
        painter.drawRoundedRect(rect, 4, 4)

        painter.end()
    
    def _choose_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self.window(), "Select Syntax Color")
        if color.isValid():
            self.set_color(color.name())
    
class SyntaxHighlightSettingsDialog(QDialog):
    """
    Dialog to customize the syntax highlighting colors
    """
    def __init__(self, current_scheme: Dict[SyntaxCategory, str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Syntax Highlighting Settings")
        self.resize(800, 500)
        self.setObjectName("syntax_highlight_settings_dialog")
    
        self.color_buttons: Dict[SyntaxCategory, ColorPickerButton] = {}
        self._init_ui(current_scheme)
    
    def _init_ui(self, current_scheme: Dict[SyntaxCategory, str]) -> None:
        main_layout = QVBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        controls_widget = QGroupBox("Color Scheme")
        controls_layout = QVBoxLayout(controls_widget)
        
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Predefined Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("theme_preset_combo")
        self.theme_combo.addItems(["Custom"] + list(PREDEFINED_SCHEMES.keys()))
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        controls_layout.addLayout(theme_layout)
        
        management_layout = QHBoxLayout()
        self.import_btn = QPushButton("Import JSON")
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_btn.clicked.connect(self._import_theme)
        
        self.export_btn = QPushButton("Export JSON")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self._export_theme)
        
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setToolTip("Reset to Default (Dracula) Theme")
        self.reset_btn.clicked.connect(self._reset_to_default)
        
        management_layout.addWidget(self.import_btn)
        management_layout.addWidget(self.export_btn)
        management_layout.addWidget(self.reset_btn)
        controls_layout.addLayout(management_layout)

        scroll_area = QScrollArea()
        scroll_area.setProperty("styleClass", "transparent_scroll_area")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        form_container = QWidget()
        form_layout = QFormLayout(form_container)
        form_layout.setVerticalSpacing(8)

        for category in SyntaxCategory:
            btn = ColorPickerButton(current_scheme.get(category, "#ffffff"))
            
            btn.color_changed.connect(self._on_custom_color_picked)
            
            self.color_buttons[category] = btn
            form_layout.addRow(category.value + ":", btn)

        scroll_area.setWidget(form_container)
        controls_layout.addWidget(scroll_area)

        splitter.addWidget(controls_widget)
        
        preview_widget = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_widget)
        
        self.preview_editor = QPlainTextEdit()
        self.preview_editor.setReadOnly(True)
        self.preview_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.preview_editor.setObjectName("syntax_preview_editor")
        
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.preview_editor.setFont(font)
        
        self.preview_highlighter = PythonHighlighter(self.preview_editor.document(), current_scheme)
        
        self.preview_editor.setPlainText(self._get_preview_text())
        preview_layout.addWidget(self.preview_editor)
        
        splitter.addWidget(preview_widget)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        
        main_layout.addWidget(splitter)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        
        self._match_current_scheme_to_theme(current_scheme)
        self._update_preview_background()
        
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

        self.preview_editor.setProperty("themeMode", theme_mode)
        self.preview_editor.style().unpolish(self.preview_editor)
        self.preview_editor.style().polish(self.preview_editor)

    def _on_custom_color_picked(self, new_color: str = "") -> None:
        """Handles state transitions when a user manually picks a new color"""
        if self.theme_combo.currentText() != "Custom":
            self.theme_combo.setCurrentText("Custom")
        self._update_live_preview()

    def _match_current_scheme_to_theme(self, current_scheme: Dict[SyntaxCategory, str]) -> None:
        """
        Restarts the combobox index based on signature
        """
        for theme_name, theme_scheme in PREDEFINED_SCHEMES.items():
            if current_scheme == theme_scheme:
                self.theme_combo.setCurrentText(theme_name)
                return
        self.theme_combo.setCurrentText("Custom")
    
    def _on_theme_changed(self, theme_name: str) -> None:
        if theme_name in PREDEFINED_SCHEMES:
            theme_scheme = PREDEFINED_SCHEMES[theme_name]
            for category, btn in self.color_buttons.items():
                btn.set_color(theme_scheme[category], emit_signal=False)
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
        
        try:
            scheme: Dict[SyntaxCategory, str] = self.get_color_scheme()
            export_data: Dict[str, str] = {category.value: color for category, color in scheme.items()}
            
            export_path: Path = Path(file_path_str)
            with export_path.open("w", encoding="utf-8") as file:
                json.dump(export_data, file, indent=4)
            
            QMessageBox.information(self, "Export Successful", f"Theme saved to:\n{export_path.name}")
        except Exception as err:
            QMessageBox.critical(self, "Export Error", f"Failed to export theme:\n{err}")
    
    def _import_theme(self) -> None:
        """Imports a JSON theme file and applies it"""
        file_path_str, _ = QFileDialog.getOpenFileName(
            self, "Import Syntax Theme", "", "JSON Files (*.json)"
        )
        
        if not file_path_str:
            return
            
        try:
            import_path: Path = Path(file_path_str)
            with import_path.open('r', encoding='utf-8') as file:
                import_data: dict = json.load(file)

            imported_count = 0
            for cat_str, color in import_data.items():
                try:
                    category = SyntaxCategory(cat_str)
                    if category in self.color_buttons:
                        self.color_buttons[category].set_color(color, emit_signal=False)
                        imported_count += 1
                except ValueError:
                    continue

            if imported_count == 0:
                QMessageBox.warning(self, "Import Warning", "No valid syntax categories found in the file.")
                return
            
            self.theme_combo.setCurrentText("Custom")
            self._update_live_preview()
            QMessageBox.information(self, "Import Successful", f"Successfully imported {imported_count} color settings.")
            
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Import Error", "The selected file is not a valid JSON document.")
        except Exception as err:
            QMessageBox.critical(self, "Import Error", f"Failed to import theme:\n{err}")
    
    def get_color_scheme(self) -> Dict[SyntaxCategory, str]:
        return {cat: btn.get_color() for cat, btn in self.color_buttons.items()}
    