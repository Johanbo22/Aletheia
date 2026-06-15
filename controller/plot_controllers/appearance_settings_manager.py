from typing import TYPE_CHECKING

from ui.widgets import ColorBlindnessEffect

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab

class AppearanceSettingsManager:
    """
    Manages UI interactions for grid visibility,
    spine visibility, and colorblindness simulation modes
    """

    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab
        self.view = plot_tab.view
        self.status_bar = plot_tab.status_bar
        self.canvas = plot_tab.canvas

    def connect_signals(self) -> None:
        """Connect UI signals for appearance and grid elements."""
        self.view.individual_spines_check.stateChanged.connect(self.toggle_individual_spines)
        self.view.all_spines_btn.clicked.connect(self.preset_all_spines)
        self.view.box_only_btn.clicked.connect(self.preset_box_only)
        self.view.no_spines_btn.clicked.connect(self.preset_no_spines)
        self.view.colorblind_check.stateChanged.connect(self.update_colorblind_simulation)
        self.view.colorblind_type_combo.currentTextChanged.connect(self.update_colorblind_simulation)

        self.view.grid_check.stateChanged.connect(self.on_grid_toggle)
        self.view.independent_grid_check.stateChanged.connect(self.on_independent_grid_toggle)
        self.view.legend_check.stateChanged.connect(self.plot_tab.on_legend_toggle)

    def toggle_individual_spines(self) -> None:
        """Toggles the customization of spines for each."""
        checked = self.view.individual_spines_check.isChecked()
        self.view.individual_spines_container.setVisible(checked)
        self.plot_tab.on_style_changed()

    def preset_all_spines(self) -> None:
        """Preset: Show all spines."""
        self.view.top_spine_visible_check.setChecked(True)
        self.view.bottom_spine_visible_check.setChecked(True)
        self.view.left_spine_visible_check.setChecked(True)
        self.view.right_spine_visible_check.setChecked(True)
        self.status_bar.log("Applied preset: All Spines", "INFO")
        self.plot_tab.on_style_changed()

    def preset_box_only(self) -> None:
        """Preset: Show only left and bottom spines."""
        self.view.top_spine_visible_check.setChecked(False)
        self.view.bottom_spine_visible_check.setChecked(True)
        self.view.left_spine_visible_check.setChecked(True)
        self.view.right_spine_visible_check.setChecked(False)
        self.status_bar.log("Applied preset: Box Only", "INFO")
        self.plot_tab.on_style_changed()

    def preset_no_spines(self) -> None:
        """Preset: Hide all spines."""
        self.view.top_spine_visible_check.setChecked(False)
        self.view.bottom_spine_visible_check.setChecked(False)
        self.view.left_spine_visible_check.setChecked(False)
        self.view.right_spine_visible_check.setChecked(False)
        self.status_bar.log("Applied preset: No Spines", "INFO")
        self.plot_tab.on_style_changed()

    def on_grid_toggle(self) -> None:
        """Handle grid checkbox toggle."""
        is_enabled = self.view.grid_check.isChecked()
        self.view.global_grid_group.setVisible(is_enabled)
        self.view.grid_which_type_combo.setEnabled(is_enabled)
        self.view.grid_axis_combo.setEnabled(is_enabled)
        self.view.independent_grid_check.setEnabled(is_enabled)

        if not is_enabled:
            self.view.grid_axis_tab.setVisible(False)
            self.view.independent_grid_check.setChecked(False)
        self.plot_tab.on_style_changed()

    def on_independent_grid_toggle(self) -> None:
        """Handle independent customization of axis grids toggle."""
        is_independent = self.view.independent_grid_check.isChecked()
        self.view.grid_which_type_combo.setEnabled(not is_independent)
        self.view.grid_axis_combo.setEnabled(not is_independent)
        self.plot_tab.on_style_changed()

    def update_colorblind_simulation(self) -> None:
        """Applies or removes the SVG filter effect from canvas."""
        if self.view.colorblind_check.isChecked():
            sim_type = self.view.colorblind_type_combo.currentText()
            effect = ColorBlindnessEffect(sim_type)
            self.canvas.setGraphicsEffect(effect)
            self.status_bar.log(f"Color blindness mode enabled: {sim_type}", "INFO")
        else:
            self.canvas.setGraphicsEffect(None)
            self.status_bar.log("Color blindness mode disabled", "INFO")
        self.plot_tab.on_style_changed()
