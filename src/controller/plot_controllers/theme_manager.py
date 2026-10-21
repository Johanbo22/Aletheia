import json
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QInputDialog, QMessageBox

from src.core.global_signals import ToastLevel, global_signals
from src.ui.dialogs.PlotConfigEditorDialog import PlotConfigEditorDialog
from src.ui.status_bar import LogLevel

if TYPE_CHECKING:
    from src.ui.plot_tab import PlotTab

class ThemeManager:
    """Manages loading, saving, editing and applying JSON plot themes"""

    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab
        self.view = plot_tab.view
        self.status_bar = plot_tab.status_bar
        self.config_manager = plot_tab.config_manager

        self.theme_dir = Path.cwd() / "resources" / "themes"
        self.theme_dir.mkdir(parents=True, exist_ok=True)
        self.default_theme_names = ["Dark Mode", "Publication_Ready", "Presentation_Big", "Default"]

    def connect_signals(self) -> None:
        self.view.load_theme_button.clicked.connect(self.apply_selected_theme)
        self.view.save_theme_button.clicked.connect(self.save_custom_theme)
        self.view.edit_theme_button.clicked.connect(self.edit_custom_theme)
        self.view.delete_theme_button.clicked.connect(self.delete_custom_theme)
        self.view.theme_combo.currentTextChanged.connect(self._on_theme_selection_changed)
        self.refresh_theme_list()
        self._on_theme_selection_changed(self.view.theme_combo.currentText())

    def _on_theme_selection_changed(self, text: str) -> None:
        """
        Enable or disable the theme action buttons based on the selection

        :param text: The currently selected text in the combo box
        """
        is_valid_theme = text != "Select a theme..." and bool(text)
        self.view.edit_theme_button.setEnabled(is_valid_theme)
        self.view.load_theme_button.setEnabled(is_valid_theme)
        self.view.delete_theme_button.setEnabled(is_valid_theme)

    def refresh_theme_list(self) -> None:
        """Scans the theme directory to update the theme selection box"""
        self.view.theme_combo.blockSignals(True)
        self.view.theme_combo.clear()
        self.view.theme_combo.addItem("Select a theme...")

        if self.theme_dir.exists():
            themes = [file.name for file in self.theme_dir.glob("*.json")]
            for theme in sorted(themes):
                self.view.theme_combo.addItem(theme.replace(".json", ""), userData=theme)

        self.view.theme_combo.blockSignals(False)

    def _write_theme_file(self, theme_name: str, theme_data: dict[str, object], filepath: Path | None = None) -> None:
        """Write theme configuration data to disk and select it in the UI"""
        if filepath is None:
            safe_filename: str = "".join(
                char for char in theme_name if char.isalnum() or "_-"
            ) + ".json"
            filepath = self.theme_dir / safe_filename

        indent_level: int = 4
        with filepath.open("w", encoding="utf-8") as file:
            json.dump(theme_data, file, indent=indent_level)

        self.refresh_theme_list()
        index: int = self.view.theme_combo.findText(theme_name)
        if index >= 0:
            self.view.theme_combo.setCurrentIndex(index)

    def save_custom_theme(self) -> None:
        """Save the current settings to a JSON file"""
        text, ok = QInputDialog.getText(
            self.plot_tab,
            "Save Theme",
            "Enter theme name"
        )
        if not ok or not text:
            return

        if text in self.default_theme_names:
            global_signals.request_toast(
                "Action Denied",
                f"'{text}' is the name of a default theme. Please choose another name",
                ToastLevel.WARNING
            )
            return

        theme_data: dict[str, object] = self.config_manager.get_theme_config()
        try:
            self._write_theme_file(text, theme_data)
            self.status_bar.log(f"Theme '{text}' saved", LogLevel.SUCCESS)
        except OSError as save_error:
            self.status_bar.log(
                f"Failed to save theme: {save_error}", LogLevel.ERROR
            )
            global_signals.request_toast(
                "Error", "Could not save theme", ToastLevel.ERROR
            )

    def apply_selected_theme(self) -> None:
        """Load and apply the selected theme"""
        theme_file: str | None = self.view.theme_combo.currentData()
        if not theme_file:
            return

        filepath: Path = self.theme_dir / theme_file
        if not filepath.exists():
            self.status_bar.log(
                f"Theme file not found: {filepath}", LogLevel.ERROR
            )
            return

        try:
            with filepath.open("r", encoding="utf-8") as file:
                theme_config: dict[str, object] = json.load(file)

            self.config_manager.load_config(theme_config)
            self.status_bar.log(
                f"Theme '{self.view.theme_combo.currentText()}' applied", LogLevel.SUCCESS
            )

            if self.plot_tab.data_handler.df is not None:
                self.plot_tab.generation_manager.generate_plot()
        except (OSError, json.JSONDecodeError, ValueError, KeyError) as apply_error:
            self.status_bar.log(
                f"Failed to load theme: {apply_error}", LogLevel.ERROR
            )
            global_signals.request_toast(
                "Error", "Could not load theme", ToastLevel.ERROR
            )

    def delete_custom_theme(self) -> None:
        """Delete the selected theme"""
        theme_file = self.view.theme_combo.currentData()
        theme_name = self.view.theme_combo.currentText()

        if not theme_file or theme_name == "Select a theme...":
            return

        clean_name = theme_file.replace(".json", "")
        if clean_name in self.default_theme_names:
            global_signals.request_toast(
                "Action Denied", f"'{theme_name}' is a default theme and cannot be deleted", ToastLevel.WARNING
            )
            return

        confirm = QMessageBox.question(
            self.plot_tab, "Confirm Delete?", f"Are you sure you want to delete theme '{theme_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                filepath = self.theme_dir / theme_file
                if filepath.exists():
                    filepath.unlink()
                    self.refresh_theme_list()
                    self.status_bar.log(f"Theme '{theme_name}' deleted", LogLevel.INFO)
            except Exception as DeleteThemeError:
                self.status_bar.log(f"Failed to delete theme: {DeleteThemeError}", LogLevel.ERROR)

    def edit_custom_theme(self) -> None:
        """Opens the PlotConfigEditorDialog for the selected theme"""
        theme_file = self.view.theme_combo.currentData()
        theme_name = self.view.theme_combo.currentText()
        placeholder_text_for_theme_name: str = "Select a theme..."

        if not theme_file or theme_name == placeholder_text_for_theme_name:
            return

        filepath = self.theme_dir / theme_file
        if not filepath.exists():
            return

        try:
            with filepath.open("r", encoding="utf-8") as file:
                content: dict[str, object] = json.load(file)

            clean_name: str = theme_file.replace(".json", "")
            is_protected: bool = clean_name in self.default_theme_names

            dialog = PlotConfigEditorDialog(theme_name, content, is_protected, self.plot_tab)
            if not dialog.exec() or dialog.final_content is None:
                return

            if is_protected and dialog.new_theme_name:
                save_name: str = dialog.new_theme_name
                target_path: Path | None = None
            else:
                save_name = theme_name
                target_path = filepath

            self._write_theme_file(save_name, dialog.final_content, target_path)
            self.status_bar.log(
                f"Theme '{save_name}' updated", LogLevel.INFO
            )
        except (OSError, json.JSONDecodeError) as edit_error:
            self.status_bar.log(
                f"Failed to edit theme: {edit_error}", LogLevel.ERROR
            )
            global_signals.request_toast(
                "Error", "Could not edit theme", ToastLevel.ERROR
            )
