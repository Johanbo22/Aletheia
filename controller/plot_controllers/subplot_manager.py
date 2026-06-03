from typing import Dict, Any, Optional, TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab

class SubplotManager:
    """Manages subplot layouts, active subplot tracking, and subplot grid configs"""

    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab
        self.view = plot_tab.view
        self.status_bar = plot_tab.status_bar
        self.plot_engine = plot_tab.plot_engine
        self.selection_overlay = plot_tab.selection_overlay

        # State tracking for frozen data for subplots
        self.subplot_data_configs: Dict[int, Dict[str, Any]] = {}

    def connect_signals(self) -> None:
        self.view.grid_designer.layout_applied.connect(self.apply_custom_grid_layout)
        self.view.active_subplot_combo.currentIndexChanged.connect(self.on_active_subplot_changed)
        self.view.add_subplots_check.stateChanged.connect(self.on_subplot_active)

    def on_subplot_active(self) -> None:
        """Activates the subplot group for visibility"""
        subplots_enabled: bool = self.view.add_subplots_check.isChecked()
        self.view.subplot_group.setVisible(subplots_enabled)
        
        if not subplots_enabled:
            self.plot_tab.clear_plot()

    def apply_custom_grid_layout(self, rows: int, cols: int, custom_grid: list) -> None:
        """Apply custom GridSpec layout to the current subplot context"""
        sharex = self.view.subplot_sharex_check.isChecked()
        sharey = self.view.subplot_sharey_check.isChecked()

        confirmation = QMessageBox.question(
            self.plot_tab, "Update Layout",
            "Updating subplot layout will clear all existing plots on the canvas.\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirmation == QMessageBox.StandardButton.Yes:
            try:
                self.plot_engine.setup_layout(rows=rows, cols=cols, sharex=sharex, sharey=sharey, custom_grid=custom_grid)

                max_plots = len(custom_grid)
                self.view.active_subplot_combo.blockSignals(True)
                self.view.active_subplot_combo.clear()

                for i in range(max_plots):
                    self.view.active_subplot_combo.addItem(f"Plot {i + 1}")
                self.view.active_subplot_combo.blockSignals(False)

                self.clear_configs()
                self.plot_tab.canvas.draw()

                # Trigger the overlay update
                self.on_active_subplot_changed(0)

                self.status_bar.log(f"Subplot layout updated to {rows}x{cols} with {max_plots} plots", "INFO")
            except Exception as layout_err:
                self.status_bar.log(f"Failed to apply custom grid layout: {str(layout_err)}", "ERROR")

    def on_active_subplot_changed(self, index: int) -> None:
        """Changes the index of the active subplot"""
        if index >= 0:
            self.plot_engine.set_active_subplot(index)
            self.update_overlay()
            self.status_bar.log(f"Active subplot set to: {index + 1}", "INFO")

    def update_overlay(self, is_resize: bool = False) -> None:
        """Recalculates the geometry and overlay widgets"""
        geometry = self.plot_engine.get_active_axis_geometry()

        if geometry:
            x, y, w, h = geometry
            current_text = self.view.active_subplot_combo.currentText()
            self.selection_overlay.update_info(current_text, (x, y, w, h), is_resize=is_resize)

    def save_config(self, index: int, config: Dict[str, Any]) -> None:
        """Saves the data state for a specific subplot"""
        self.subplot_data_configs[index] = config

    def get_config(self, index: int) -> Optional[Dict[str, Any]]:
        """Retrieves a data state for a specific subplot"""
        return self.subplot_data_configs.get(index)

    def clear_configs(self) -> None:
        """Clear all subplot configs"""
        self.subplot_data_configs.clear()