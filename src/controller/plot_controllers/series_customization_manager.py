from typing import Any, Dict, TYPE_CHECKING

from PyQt6.QtGui import QColor
from matplotlib.colors import to_hex

from src.controller.plot_controllers.color_manager import ColorManager

if TYPE_CHECKING:
    from src.ui.plot_tab import PlotTab

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
        self.view.bar_edge_width_spin.valueChanged.connect(self.plot_tab.on_style_changed)

        self.view.linewidth_spin.valueChanged.connect(self.update_line_customization_live)
        self.view.linewidth_spin.valueChanged.connect(self.plot_tab.on_style_changed)

        self.view.linestyle_combo.currentTextChanged.connect(self.update_line_customization_live)
        self.view.linestyle_combo.currentTextChanged.connect(self.plot_tab.on_style_changed)

        self.view.marker_combo.currentTextChanged.connect(self.update_line_customization_live)
        self.view.marker_combo.currentTextChanged.connect(self.plot_tab.on_style_changed)

        self.view.marker_size_spin.valueChanged.connect(self.update_line_customization_live)
        self.view.marker_size_spin.valueChanged.connect(self.plot_tab.on_style_changed)

        self.view.marker_edge_width_spin.valueChanged.connect(self.update_line_customization_live)
        self.view.marker_edge_width_spin.valueChanged.connect(self.plot_tab.on_style_changed)

        self.view.alpha_slider.valueChanged.connect(self.update_line_customization_live)
        self.view.alpha_slider.valueChanged.connect(self.update_bar_customization_live)
        self.view.alpha_slider.valueChanged.connect(self.plot_tab.on_style_changed)

        original_on_style_changed = self.plot_tab.on_style_changed

        def wrapped_on_style_changed() -> None:
            self.update_line_customization_live()
            self.update_bar_customization_live()
            original_on_style_changed()
            self._force_apply_customizations()

        self.plot_tab.on_style_changed = wrapped_on_style_changed

    def _force_apply_customizations(self) -> None:
        if self.view.multiline_custom_check.isChecked():
            for label, line in self._get_all_lines():
                if label in self.line_customizations:
                    custom = self.line_customizations[label]
                    if custom.get("linewidth") is not None:
                        line.set_linewidth(custom["linewidth"])
                    if custom.get("linestyle") is not None:
                        line.set_linestyle(custom["linestyle"])
                    if custom.get("color") is not None:
                        line.set_color(custom["color"])
                    if custom.get("marker") is not None:
                        line.set_marker(custom["marker"])
                    if custom.get("markersize") is not None:
                        line.set_markersize(custom["markersize"])
                    if custom.get("markerfacecolor") is not None:
                        line.set_markerfacecolor(custom["markerfacecolor"])
                    if custom.get("markeredgecolor") is not None:
                        line.set_markeredgecolor(custom["markeredgecolor"])
                    if custom.get("markeredgewidth") is not None:
                        line.set_markeredgewidth(custom["markeredgewidth"])
                    if custom.get("alpha") is not None:
                        line.set_alpha(custom["alpha"])

        if self.view.multibar_custom_check.isChecked():
            for label, container in self._get_all_bar_containers():
                if label in self.bar_customizations:
                    custom = self.bar_customizations[label]
                    if hasattr(container, "patches"):
                        for patch in container.patches:
                            if custom.get("facecolor") is not None:
                                patch.set_facecolor(custom["facecolor"])
                            if custom.get("edgecolor") is not None:
                                patch.set_edgecolor(custom["edgecolor"])
                            if custom.get("linewidth") is not None:
                                patch.set_linewidth(custom["linewidth"])
                            if custom.get("alpha") is not None:
                                patch.set_alpha(custom["alpha"])

        canvas = getattr(self.plot_engine, 'canvas', None)
        if canvas is None and hasattr(self.plot_engine, 'figure'):
            canvas = self.plot_engine.figure.canvas

        if canvas:
            canvas.draw_idle()

    def toggle_bar_selector(self) -> None:
        """Show/hide bar selection to customize more than one bar series object"""
        is_enabled = self.view.multibar_custom_check.isChecked()
        self.view.bar_selector_label.setVisible(is_enabled)
        self.view.bar_selector_combo.setVisible(is_enabled)

        if is_enabled:
            self._initialize_all_bar_customizations()
            self.update_bar_selector()
        self.plot_tab.on_style_changed()

    def _get_all_bar_containers(self) -> list[tuple[str, Any]]:
        """Gets all the bar containers and their labels across all axes"""
        results = []
        axes = [self.plot_engine.current_ax]
        if getattr(self.plot_engine, "secondary_ax", None):
            axes.append(self.plot_engine.secondary_ax)

        global_idx = 0
        for ax in axes:
            if not ax or not ax.containers:
                continue

            handles, labels = ax.get_legend_handles_labels()

            for i, container in enumerate(ax.containers):
                if not hasattr(container, "patches") or not container.patches:
                    continue

                label = container.get_label()
                if not label or label.startswith("_"):
                    label = labels[i] if i < len(labels) else f"Bar Series {global_idx + 1}"

                results.append((label, container))
                global_idx += 1

        return results

    def _initialize_all_bar_customizations(self) -> None:
        """Initialize customizations dictionary for all bars with their current visual state"""
        for label, container in self._get_all_bar_containers():
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

        for label, container in self._get_all_bar_containers():
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
        custom = self.bar_customizations.get(bar_name, {})

        # Load facecolor
        if "facecolor" in custom:
            facecolor = custom["facecolor"]
        else:
            facecolor = to_hex(patch.get_facecolor()) if patch.get_facecolor() else "#000000"

        self.plot_tab.bar_color = facecolor
        self.view.bar_color_label.setText(facecolor)
        ColorManager.update_button_color_swatch(self.view.bar_color_button, QColor(self.plot_tab.bar_color))

        # Load edge
        if "edgecolor" in custom:
            edgecolor = custom["edgecolor"]
        else:
            edgecolor = to_hex(patch.get_edgecolor()) if patch.get_edgecolor() else "#000000"

        self.plot_tab.bar_edge_color = edgecolor
        self.view.bar_edge_label.setText(edgecolor)
        ColorManager.update_button_color_swatch(self.view.bar_edge_button, QColor(self.plot_tab.bar_edge_color))

        # Load the bar edge width
        self.view.bar_edge_width_spin.blockSignals(True)
        self.view.bar_edge_width_spin.setValue(custom.get("linewidth", patch.get_linewidth() or 0.0))
        self.view.bar_edge_width_spin.blockSignals(False)

        # Load alpha
        if "alpha" in custom:
            alpha = custom["alpha"]
        else:
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

    def _get_all_lines(self) -> list[tuple[str, Any]]:
        """Helper to get all valid lines and their labels across all axes."""
        results = []
        axes = [self.plot_engine.current_ax]
        if getattr(self.plot_engine, 'secondary_ax', None):
            axes.append(self.plot_engine.secondary_ax)

        global_idx = 0
        for ax in axes:
            if not ax:
                continue

            lines = [l for l in ax.get_lines() if
                     l.get_gid() not in ["regression_line", "confidence_interval", "error_bar"]]

            for i, line in enumerate(lines):
                label = line.get_label()
                if not label or label.startswith("_"):
                    label = f"Line {global_idx + 1}"

                results.append((label, line))
                global_idx += 1

        return results

    def _initialize_all_line_customizations(self) -> None:
        """Initialize customizations dict for all lines with their current state."""
        for label, line in self._get_all_lines():
            if label not in self.line_customizations:
                self.line_customizations[label] = {
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

        for label, line in self._get_all_lines():
            self.view.line_selector_combo.addItem(label, userData=line)

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

        line = self.view.line_selector_combo.currentData()
        if line is None:
            return

        custom = self.line_customizations.get(line_name, {})

        # Load current line properties prioritizing saved custom attributes
        self.view.linewidth_spin.blockSignals(True)
        self.view.linewidth_spin.setValue(custom.get("linewidth", line.get_linewidth()))
        self.view.linewidth_spin.blockSignals(False)

        linestyle_map_reverse = {"-": "Solid", "--": "Dashed", "-.": "Dash-dot", ":": "Dotted"}
        current_style = linestyle_map_reverse.get(custom.get("linestyle", line.get_linestyle()), "Solid")

        self.view.linestyle_combo.blockSignals(True)
        self.view.linestyle_combo.setCurrentText(current_style)
        self.view.linestyle_combo.blockSignals(False)

        # Load color
        if "color" in custom:
            hex_color = custom["color"]
        else:
            color = line.get_color()
            hex_color = to_hex(color) if color else "#000000"

        self.plot_tab.line_color = hex_color
        self.view.line_color_label.setText(self.plot_tab.line_color)
        ColorManager.update_button_color_swatch(self.view.line_color_button, QColor(self.plot_tab.line_color))

        # Load markers
        if "marker" in custom:
            marker_text = custom["marker"]
        else:
            marker = line.get_marker()
            marker_text = marker if marker not in ["None", " ", "", None] else "None"

        self.view.marker_combo.blockSignals(True)
        self.view.marker_combo.setCurrentText(marker_text)
        self.view.marker_combo.blockSignals(False)

        self.view.marker_size_spin.blockSignals(True)
        self.view.marker_size_spin.setValue(int(custom.get("markersize", line.get_markersize() or 0)))
        self.view.marker_size_spin.blockSignals(False)

        # Load alpha
        if "alpha" in custom:
            alpha = custom["alpha"]
        else:
            alpha = line.get_alpha() if line.get_alpha() is not None else 1.0

        self.view.alpha_slider.blockSignals(True)
        self.view.alpha_slider.setValue(int(alpha * 100))
        self.view.alpha_slider.blockSignals(False)
        self.view.alpha_label.setText(f"{int(alpha * 100)}%")

    def clear_customizations(self) -> None:
        """Clears all stored series customizations"""
        self.line_customizations.clear()
        self.bar_customizations.clear()