import json
from pathlib import Path
from typing import Dict, Any, TYPE_CHECKING
import traceback

from PyQt6.QtWidgets import QMessageBox, QInputDialog

from ui.dialogs.PlotConfigEditorDialog import PlotConfigEditorDialog

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab
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
        self.refresh_theme_list()
    
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
    
    def get_theme_config(self) -> Dict[str, Any]:
        """Fetch the current plot configuration to be saved as a theme"""
        theme_data = {
            "appearance": self.config_manager._get_appearance_config(),
            "axes": self.config_manager._get_axes_config(),
            "legend": self.config_manager._get_legend_config(),
            "grid": self.config_manager._get_grid_config(),
            "advanced": self.config_manager._get_advanced_config()
        }
        if "axes" in theme_data:
            theme_data["axes"]["x_axis"]["auto_limits"] = True
            theme_data["axes"]["y_axis"]["auto_limits"] = True
            theme_data["axes"]["x_axis"]["min"] = 0
            theme_data["axes"]["x_axis"]["max"] = 1
            theme_data["axes"]["y_axis"]["min"] = 0
            theme_data["axes"]["y_axis"]["max"] = 1
        
        return theme_data

    def save_custom_theme(self) -> None:
        """Save the current settings to a JSON file"""
        text, ok = QInputDialog.getText(self.plot_tab, "Save theme", "Enter theme name")
        if ok and text:
            if text in self.default_theme_names:
                QMessageBox.warning(self.plot_tab, "Action Denied", f"'{text}' is the name of a default theme. Please choose another name")
                return
            
            filename = "".join(x for x in text if x.isalnum() or x in " _-") + ".json"
            filepath = self.theme_dir / filename
            theme_data = self.get_theme_config()
            
            try:
                with open(filepath, "w") as file:
                    json.dump(theme_data, file, indent=4)
                self.status_bar.log(f"Theme '{text}' saved", "SUCCESS")
                self.refresh_theme_list()
                
                index = self.view.theme_combo.findText(text)
                if index >= 0:
                    self.view.theme_combo.setCurrentIndex(index)
            
            except Exception as SaveThemeError:
                self.status_bar.log(f"Failed to save theme: {SaveThemeError}", "ERROR")
                QMessageBox.critical(self.plot_tab, "Error", f"Could not save theme: {str(SaveThemeError)}")
    
    def apply_selected_theme(self) -> None:
        """Load and apply the selected theme"""
        theme_file = self.view.theme_combo.currentData()
        if not theme_file:
            return
        
        filepath = self.theme_dir / theme_file
        if not filepath.exists():
            self.status_bar.log(f"Theme file not found: {filepath}", "ERROR")
            return
        
        try:
            with open(filepath, "r") as file:
                theme_config = json.load(file)
                
            if "appearance" in theme_config: self.config_manager._load_appearance_config(theme_config["appearance"])
            if "axes" in theme_config: self.config_manager._load_axes_config(theme_config["axes"])
            if "legend" in theme_config: self.config_manager._load_legend_config(theme_config["legend"])
            if "grid" in theme_config: self.config_manager._load_grid_config(theme_config["grid"])
            if "advanced" in theme_config: self.config_manager._load_advanced_config(theme_config["advanced"])
            
            self.status_bar.log(f"Theme '{self.view.theme_combo.currentText()}' applied", "SUCCESS")
            
            if self.plot_tab.data_handler.df is not None:
                self.plot_tab.generate_plot()
        
        except Exception as ApplyThemeError:
            self.status_bar.log(f"Failed to load theme: {ApplyThemeError}", "ERROR")
            QMessageBox.critical(self.plot_tab, "Error", f"Could not load theme: {str(ApplyThemeError)}")
            traceback.print_exc()
    
    def delete_custom_theme(self) -> None:
        """Delete the selected theme"""
        theme_file = self.view.theme_combo.currentData()
        theme_name = self.view.theme_combo.currentText()
        
        if not theme_file or theme_name == "Select a theme...":
            return
        
        clean_name = theme_file.replace(".json", "")
        if clean_name in self.default_theme_names:
            QMessageBox.warning(self, "Action Denied", f"'{theme_name}' is a default theme and cannot be deleted")
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
                    self.status_bar.log(f"Theme '{theme_name}' deleted", "INFO")
            except Exception as DeleteThemeError:
                self.status_bar.log(f"Failed to delete theme: {DeleteThemeError}", "ERROR")
    
    def edit_custom_theme(self) -> None:
        """Opens the PlotConfigEditorDialog for the selected theme"""
        theme_file = self.view.theme_combo.currentData()
        theme_name = self.view.theme_combo.currentText()

        if not theme_file or theme_name == "Select a theme...":
            return
        
        filepath = self.theme_dir / theme_file
        if not filepath.exists():
            return
        
        try:
            with open(filepath, "r") as file:
                content = json.load(file)
            
            clean_name = theme_file.replace(".json", "")
            is_protected = clean_name in self.default_theme_names
            
            dialog = PlotConfigEditorDialog(theme_name, content, is_protected, self.plot_tab)
            if dialog.exec():
                new_content = dialog.final_content
                
                if is_protected and dialog.new_theme_name:
                    save_name = dialog.new_theme_name
                    filename = "".join(x for x in save_name if x.isalnum() or x in " _-") + ".json"
                    save_path = self.theme_dir / filename
                else:
                    save_name = theme_name
                    save_path = filepath
                
                with open(save_path, "w") as file:
                    json.dump(new_content, file, indent=4)
                    
                self.status_bar.log(f"Theme '{save_name}' updated", "SUCCESS")
                self.refresh_theme_list()
                
                index = self.view.theme_combo.findText(save_name)
                if index >= 0:
                    self.view.theme_combo.setCurrentIndex(index)
        except Exception as EditThemeJSONError:
            self.status_bar.log(f"Failed to edit theme: {EditThemeJSONError}", "ERROR")
            QMessageBox.critical(self.plot_tab, "Error", f"Could not edit theme: {str(EditThemeJSONError)}")