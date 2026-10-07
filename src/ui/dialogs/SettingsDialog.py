from typing import Any

from PyQt6.QtCore import QThreadPool, QUrl, Qt
from PyQt6.QtGui import QDesktopServices, QFont
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFontComboBox, QFormLayout, QLabel, QPushButton, QSpinBox, \
    QTabWidget, QVBoxLayout, QWidget

from icons import IconBuilder, IconType
from resources.version import APPLICATION_VERSION
from src.core.global_signals import ToastLevel, global_signals
from src.core.version_checker import RELEASES_PAGE_URL, VersionCheckWorker
from src.ui.widgets import ToggleSwitch

class SettingsDialog(QDialog):
    """Application settings dialog"""

    def __init__(self, current_settings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(500, 400)
        self.current_settings = current_settings
        self._version_check_worker = None
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

        about_tab = QWidget()
        about_layout = QFormLayout(about_tab)
        about_layout.setSpacing(15)

        self.version_label = QLabel(f"Installed version: v{APPLICATION_VERSION}")
        self.version_label.setObjectName("app_version_label")
        about_layout.addRow(QLabel("Version:"), self.version_label)

        update_row = QVBoxLayout()
        update_row.setSpacing(10)

        self.check_update_button = QPushButton("Check for update")
        self.check_update_button.setIcon(IconBuilder.build(IconType.RefreshItem))
        self.check_update_button.setToolTip(
            "Check the for a newer release of Aletheia"
        )
        self.check_update_button.clicked.connect(self._on_check_update_clicked)
        update_row.addWidget(self.check_update_button)

        self.update_status_label = QLabel("")
        self.update_status_label.setObjectName("update_status_label")
        self.update_status_label.setWordWrap(True)
        self.update_status_label.setTextFormat(Qt.TextFormat.RichText)
        self.update_status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.update_status_label.setOpenExternalLinks(True)
        update_row.addWidget(self.update_status_label)
        update_row.addStretch()

        about_layout.addRow(QLabel("Updates:"), update_row)

        setting_tabs.addTab(about_tab, IconBuilder.build(IconType.Information), "About && Updates")

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
            "dark_mode"        : self.dark_mode_check.isChecked(),
            "font_family"      : self.font_combo.currentFont().family(),
            "font_size"        : self.font_size_spin.value()
        }

    def _on_check_update_clicked(self) -> None:
        """Requests a version check"""
        if self._version_check_worker is not None:
            return

        self.check_update_button.setEnabled(False)
        self.check_update_button.setText("Checking...")
        self.update_status_label.setText("Connecting to GitHub...")

        worker = VersionCheckWorker(APPLICATION_VERSION)
        worker.signals.check_completed.connect(self._on_version_check_completed)
        worker.signals.error_object.connect(self._on_version_check_failed)
        self._version_check_worker = worker

        QThreadPool.globalInstance().start(worker)

    def _reset_check_button(self) -> None:
        """Re enables and resets the check button after a request has been completed"""
        self.check_update_button.setEnabled(True)
        self.check_update_button.setText("Check for updates")
        self._version_check_worker = None

    def _on_version_check_completed(self, update_available: bool, latest_tag: str, installed_tag: str) -> None:
        """Handles the result from the version check"""
        self._reset_check_button()

        if update_available:
            self.update_status_label.setText(
                f'Update available! <a href="{RELEASES_PAGE_URL}">v{latest_tag}</a> was released. '
                f"You are running v{installed_tag}."
            )
            self.update_status_label.setProperty("updateState", "available")
            global_signals.request_toast(
                "Update Available",
                f"Aletheia v{latest_tag} is available. You are running v{installed_tag}.",
                ToastLevel.INFO,
                duration_ms=6000
            )
        else:
            self.update_status_label.setText(
                f"You are up to date (v{installed_tag} matches the latest release)."
            )
            self.update_status_label.setProperty("updateState", "uptodate")
            global_signals.request_toast(
                "Up to Date",
                f"Aletheia v{installed_tag} is the latest version.",
                ToastLevel.SUCCESS
            )

        self.update_status_label.style().unpolish(self.update_status_label)
        self.update_status_label.style().polish(self.update_status_label)

    def _on_version_check_failed(self, error: object) -> None:
        """Handles a failed version check"""
        self._reset_check_button()
        self.update_status_label.setText(f"Update check failed: {error}")
        self.update_status_label.setProperty("updateState", "error")
        self.update_status_label.style().unpolish(self.update_status_label)
        self.update_status_label.style().polish(self.update_status_label)

        global_signals.request_toast(
            "Update Check Failed",
            f"Could not check for updates: {error}",
            ToastLevel.WARNING
        )

    def _open_releases_page(self) -> None:
        """Opens the GitHub release page in the default browser"""
        QDesktopServices.openUrl(QUrl(RELEASES_PAGE_URL))
