from typing import Any, Dict, TYPE_CHECKING

from PyQt6.QtGui import QColor
from matplotlib.colors import to_hex

from controller.plot_controllers.color_manager import ColorManager

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab

class SeriesCustomizationManager:
    """
    Manages the individual customization of line and bar series
    """

    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab
        self.view = plot_tab.view
        self.plot_engine = plot_tab.plot_engine

        self.line_customizations: Dict[str, Any] = {}
        self.bar_customizations: Dict[str, Any] = {}

    def connect_signals(self) -> None:
        """Connects the signals from the UI"""
        self.view.multiline_custom_check.stateChanged.connect(self.toggle_line_selector)
        self.view.line_selector_combo.currentTextChanged.connect(self.on_line_selected)
        self.view.multibar_custom_check.stateChanged.connect(self.toggle_bar_selector)
        self.view.bar_selector_combo.currentTextChanged.connect(self.on_bar_selected)
        self.view.bar_edge_width_spin.valueChanged.connect(self.update_bar_customization_live)

    def toggle_bar_selector(self) -> None:
        """Show/hide bar selection to customize more than one bar series object"""
        is_enabled = self.view.multibar_custom_check.isChecked()
        self.view.bar_selector_label.setVisible(is_enabled)
        self.view.bar_selector_combo.setVisible(is_enabled)

        if is_enabled:
            self._initialize_all_bar_customizations()
            self.update_bar_selector()
        self.plot_tab.on_style_changed()

    def _initialize_all_bar_customizations(self) -> None:
        """Initialize customizations dictionary for all bars with their current visual state"""
        if not self.plot_engine.current_ax or not self.plot_engine.current_ax.containers:
            return

        for i, container in enumerate(self.plot_engine.current_ax.containers):
            if not hasattr(container, "patches") or not container.patches:
                continue
            label = container.get_label()
            if not label or label.startswith("_"):
                label = f"Bar Series {i + 1}"

            if label not in self.bar_customizations:
                patch = container.patches[0]
                self.bar_customizations[label] = {
                    "facecolor": to_hex(patch.get_facecolor()) if patch.get_facecolor() else None,
                    "edgecolor": to_hex(patch.get_edgecolor()) if patch.get_edgecolor() else None,
                    "linewidth": patch.get_linewidth(),
                    "alpha"    : patch.get_alpha() if patch.get_alpha() is not None else 1.0
                }

    def update_bar_selector(self, preserve_selection: bool = False) -> None:
        """Update the bar selection tool with the current patches in the plot"""
        current_text = self.view.bar_selector_combo.currentText()
        self.view.bar_selector_combo.blockSignals(True)
        self.view.bar_selector_combo.clear()

        if self.plot_engine.current_ax and self.plot_engine.current_ax.containers:
            for i, container in enumerate(self.plot_engine.current_ax.containers):
                label = container.get_label()

                if not label or label.startswith("_"):
                    label = f"Bar Series {i + 1}"
                self.view.bar_selector_combo.addItem(label, userData=container)

        self.view.bar_selector_combo.blockSignals(False)

        if preserve_selection and current_text:
            idx = self.view.bar_selector_combo.findText(current_text)
            if idx >= 0:
                self.view.bar_selector_combo.setCurrentIndex(idx)
                return

        if self.view.bar_selector_combo.count() > 0:
            self.on_bar_selected(self.view.bar_selector_combo.currentText())

    def on_bar_selected(self, bar_name: str) -> None:
        """Load settings for a selected bar series"""
        if not self.view.multibar_custom_check.isChecked():
            return

        container = self.view.bar_selector_combo.currentData()

        if not container or not hasattr(container, "patches") or not container.patches:
            return

        patch = container.patches[0]

        # Load facecolor
        facecolor = to_hex(patch.get_facecolor()) if patch.get_facecolor() else "#000000"
        self.plot_tab.bar_color = facecolor
        self.view.bar_color_label.setText(facecolor)
        ColorManager.update_button_color_swatch(self.view.bar_color_button, QColor(self.plot_tab.bar_color))

        # Load edge
        edgecolor = to_hex(patch.get_edgecolor()) if patch.get_edgecolor() else "#000000"
        self.plot_tab.bar_edge_color = edgecolor
        self.view.bar_edge_label.setText(edgecolor)
        ColorManager.update_button_color_swatch(self.view.bar_edge_button, QColor(self.plot_tab.bar_edge_color))

        # Load the bar edge width
        self.view.bar_edge_width_spin.blockSignals(True)
        self.view.bar_edge_width_spin.setValue(patch.get_linewidth() or 0.0)
        self.view.bar_edge_width_spin.blockSignals(False)

        # Load alpha
        alpha = patch.get_alpha() if patch.get_alpha() is not None else 1.0
        self.view.alpha_slider.blockSignals(True)
        self.view.alpha_slider.setValue(int(alpha * 100))
        self.view.alpha_slider.blockSignals(False)
        self.view.alpha_label.setText(f"{int(alpha * 100)}%")

    def update_bar_customization_live(self) -> None:
        """Saves the current temporary bar settings if a bar is selected"""
        if not self.view.multibar_custom_check.isChecked():
            return

        bar_name = self.view.bar_selector_combo.currentText()
        if not bar_name:
            return

        custom = self.bar_customizations.get(bar_name, {})
        custom["facecolor"] = self.plot_tab.bar_color
        custom["edgecolor"] = self.plot_tab.bar_edge_color
        custom["linewidth"] = self.view.bar_edge_width_spin.value()
        custom["alpha"] = self.view.alpha_slider.value() / 100.0

        self.bar_customizations[bar_name] = custom

    def toggle_line_selector(self) -> None:
        """Show/enable line selection"""
        is_enabled = self.view.multiline_custom_check.isChecked()
        self.view.line_selector_label.setVisible(is_enabled)
        self.view.line_selector_combo.setVisible(is_enabled)

        if is_enabled:
            self._initialize_all_line_customizations()
            self.update_line_selector()
        self.plot_tab.on_style_changed()

    def _initialize_all_line_customizations(self) -> None:
        """Initialize customizations dict for all lines with their current state."""
        if not self.plot_engine.current_ax:
            return
        lines = [l for l in self.plot_engine.current_ax.get_lines() if
                 l.get_gid() not in ["regression_line", "confidence_interval", "error_bar"]]
        for i, line in enumerate(lines):
            line_name = line.get_label() if not line.get_label().startswith("_") else f"Line {i + 1}"
            if line_name not in self.line_customizations:
                self.line_customizations[line_name] = {
                    "linewidth"      : line.get_linewidth(),
                    "linestyle"      : line.get_linestyle(),
                    "color"          : to_hex(line.get_color()) if line.get_color() else None,
                    "marker"         : line.get_marker(),
                    "markersize"     : line.get_markersize(),
                    "markerfacecolor": to_hex(line.get_markerfacecolor()) if line.get_markerfacecolor() else None,
                    "markeredgecolor": to_hex(line.get_markeredgecolor()) if line.get_markeredgecolor() else None,
                    "markeredgewidth": line.get_markeredgewidth(),
                    "alpha"          : line.get_alpha() if line.get_alpha() is not None else 1.0
                }

    def update_line_customization_live(self) -> None:
        """Save the current settings for the selected line."""
        if not self.view.multiline_custom_check.isChecked():
            return
        line_name = self.view.line_selector_combo.currentText()
        if not line_name:
            return

        linestyle_map = {"Solid": "-", "Dashed": "--", "Dash-dot": "-.", "Dotted": ":"}
        linestyle_val = linestyle_map.get(self.view.linestyle_combo.currentText(), "-")
        custom = self.line_customizations.get(line_name, {})
        custom.update({
            "linewidth"      : self.view.linewidth_spin.value(),
            "linestyle"      : linestyle_val,
            "color"          : self.plot_tab.line_color,
            "marker"         : self.view.marker_combo.currentText(),
            "markersize"     : self.view.marker_size_spin.value(),
            "markerfacecolor": self.plot_tab.marker_color,
            "markeredgecolor": self.plot_tab.marker_edge_color,
            "markeredgewidth": self.view.marker_edge_width_spin.value(),
            "alpha"          : self.view.alpha_slider.value() / 100.0,
        })
        self.line_customizations[line_name] = custom

    def update_line_selector(self, preserve_selection: bool = False) -> None:
        """Update the line selection with the current lines in current_ax."""
        current_text = self.view.line_selector_combo.currentText()
        self.view.line_selector_combo.blockSignals(True)
        self.view.line_selector_combo.clear()

        if self.plot_engine.current_ax:
            lines = [l for l in self.plot_engine.current_ax.get_lines() if
                     l.get_gid() not in ["regression_line", "confidence_interval", "error_bar"]]
            for i, line in enumerate(lines):
                label = line.get_label()
                if label.startswith("_"):
                    label = f"Line {i + 1}"
                self.view.line_selector_combo.addItem(label, userData=i)
        self.view.line_selector_combo.blockSignals(False)

        if preserve_selection and current_text:
            idx = self.view.line_selector_combo.findText(current_text)
            if idx >= 0:
                self.view.line_selector_combo.setCurrentIndex(idx)
                return

        if self.view.line_selector_combo.count() > 0:
            self.on_line_selected(self.view.line_selector_combo.currentText())

    def on_line_selected(self, line_name: str) -> None:
        """Load settings for a selected line."""
        if not self.view.multiline_custom_check.isChecked():
            return

        if not self.plot_engine.current_ax:
            return

        # Get line idx
        line_idx = self.view.line_selector_combo.currentData()
        if line_idx is None:
            return

        lines = [l for l in self.plot_engine.current_ax.get_lines() if
                 l.get_gid() not in ["regression_line", "confidence_interval", "error_bar"]]

        if line_idx < len(lines):
            line = lines[line_idx]

            # Load current line properties
            self.view.linewidth_spin.blockSignals(True)
            self.view.linewidth_spin.setValue(line.get_linewidth())
            self.view.linewidth_spin.blockSignals(False)

            linestyle_map_reverse = {"-": "Solid", "--": "Dashed", "-.": "Dash-dot", ":": "Dotted"}
            current_style = linestyle_map_reverse.get(line.get_linestyle(), "Solid")
            self.view.linestyle_combo.blockSignals(True)
            self.view.linestyle_combo.setCurrentText(current_style)
            self.view.linestyle_combo.blockSignals(False)

            # Load color
            color = line.get_color()
            hex_color = to_hex(color) if color else "#000000"
            self.plot_tab.line_color = hex_color
            self.view.line_color_label.setText(self.plot_tab.line_color)
            ColorManager.update_button_color_swatch(self.view.line_color_button, QColor(self.plot_tab.line_color))

            # Load markers
            marker = line.get_marker()
            marker_text = marker if marker not in ["None", " ", "", None] else "None"
            self.view.marker_combo.blockSignals(True)
            self.view.marker_combo.setCurrentText(marker_text)
            self.view.marker_combo.blockSignals(False)

            self.view.marker_size_spin.blockSignals(True)
            self.view.marker_size_spin.setValue(int(line.get_markersize() or 0))
            self.view.marker_size_spin.blockSignals(False)

            # Load alpha
            alpha = line.get_alpha() if line.get_alpha() is not None else 1.0
            self.view.alpha_slider.blockSignals(True)
            self.view.alpha_slider.setValue(int(alpha * 100))
            self.view.alpha_slider.blockSignals(False)
            self.view.alpha_label.setText(f"{int(alpha * 100)}%")

    def clear_customizations(self) -> None:
        """Clears all stored series customizations"""
        self.line_customizations.clear()
        self.bar_customizations.clear()
