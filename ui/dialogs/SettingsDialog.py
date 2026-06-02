from typing import Any

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFontComboBox, QFormLayout, QLabel, QSpinBox, \
    QTabWidget, QVBoxLayout, QWidget
from PyQt6.QtGui import QFont

from ui.icons import IconBuilder, IconType
from ui.widgets import ToggleSwitch

class SettingsDialog(QDialog):
    """Application settings dialog"""

    def __init__(self, current_settings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(500, 400)
        self.current_settings = current_settings
        self.init_ui()

    def init_ui(self) -> None:
        settings_layout = QVBoxLayout(self)

        setting_tabs = QTabWidget()

        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        general_layout.setSpacing(15)

        self.autosave_check = ToggleSwitch("Enable Autosave")
        self.autosave_check.setChecked(self.current_settings.get("enable_autosave", True))
        self.autosave_check.setToolTip("Automatically save the project at set intervals")
        general_layout.addRow(QLabel("Autosave:"), self.autosave_check)

        self.autosave_interval_spin = QSpinBox()
        self.autosave_interval_spin.setRange(1, 120)
        self.autosave_interval_spin.setSuffix(" minutes")
        self.autosave_interval_spin.setValue(self.current_settings.get("autosave_interval", 5))
        self.autosave_interval_spin.setEnabled(self.autosave_check.isChecked())

        self.autosave_check.toggled.connect(self.autosave_interval_spin.setEnabled)
        general_layout.addRow(QLabel("Autosave Interval:"), self.autosave_interval_spin)

        setting_tabs.addTab(general_tab, IconBuilder.build(IconType.Settings), "General")

        appearance_tab = QWidget()
        appearance_layout = QFormLayout()
        appearance_layout.setSpacing(15)

        self.dark_mode_check = ToggleSwitch("Enable Dark Mode")
        self.dark_mode_check.setChecked(self.current_settings.get("dark_mode", False))
        self.dark_mode_check.setToolTip("Toggle between dark and light themes")
        appearance_layout.addRow(QLabel("Theme:"), self.dark_mode_check)

        self.font_combo = QFontComboBox()
        current_font = self.current_settings.get("font_family", "Consolas")
        self.font_combo.setCurrentFont(QFont(current_font))
        appearance_layout.addRow(QLabel("Font Family:"), self.font_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 32)
        self.font_size_spin.setValue(self.current_settings.get("font_size", 10))
        appearance_layout.addRow(QLabel("Font Size:"), self.font_size_spin)

        appearance_tab.setLayout(appearance_layout)
        setting_tabs.addTab(appearance_tab, IconBuilder.build(IconType.PlotAppearance), "Appearance")

        settings_layout.addWidget(setting_tabs)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        settings_layout.addWidget(button_box)

        self.setLayout(settings_layout)

    def get_settings(self) -> dict[str, Any]:
        return {
            "enable_autosave"  : self.autosave_check.isChecked(),
            "autosave_interval": self.autosave_interval_spin.value(),
            "dark_mode": self.dark_mode_check.isChecked(),
            "font_family": self.font_combo.currentFont().family(),
            "font_size": self.font_size_spin.value()
        }