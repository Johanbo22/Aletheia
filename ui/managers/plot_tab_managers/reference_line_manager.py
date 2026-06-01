from typing import Dict, Any, List, TYPE_CHECKING

import matplotlib.pyplot as plt
from PyQt6.QtWidgets import QColorDialog, QMessageBox, QListWidgetItem
from PyQt6.QtGui import QColor

from ui.managers.plot_tab_managers.color_manager import ColorManager

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab

class ReferenceLineManager:
    """
    Manages references lines on the plot canvas
    Manages the horizontal (hline), vertical (vline) and
    general infinite lines drawn by axline
    """
    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab
        self.view = plot_tab.view
        self.status_bar = plot_tab.status_bar
        self.plot_engine = plot_tab.plot_engine
        self.canvas = plot_tab.canvas

        # State tracking of the reference lines
        self.reference_lines: List[Dict[str, Any]] = []
        self.selected_ref_line_index: int = -1

        # Default styling of the reference lines
        self.ref_line_color: str = "black"

    def connect_signals(self) -> None:
        """Connect UI signals to methods"""
        self.view.add_ref_line_button.clicked.connect(self.add_reference_line)
        self.view.clear_ref_lines_button.clicked.connect(self.clear_all_reference_lines)
        self.view.reference_lines_list.itemClicked.connect(self.on_reference_line_selected)
        self.view.update_ref_line_button.clicked.connect(self.update_selected_reference_line)
        self.view.delete_ref_line_button.clicked.connect(self.delete_selected_reference_line)

        self.view.ref_line_color_button.clicked.connect(self.choose_ref_line_color)
        self.view.ref_line_type_combo.currentTextChanged.connect(self.on_ref_line_type_changed)

    def choose_ref_line_color(self) -> None:
        """Open a color dialog for reference line color selection"""
        color = QColorDialog.getColor(
            initial=QColor(self.ref_line_color),
            parent=self.plot_tab,
            title="Select Reference Line Color",
            options=QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        if color.isValid():
            self.ref_line_color = color.name()
            self.view.ref_line_color_label.setText(self.ref_line_color)
            ColorManager.update_button_color_swatch(self.view.ref_line_color_button, QColor(self.ref_line_color))
            
    def add_reference_line(self) -> None:
        """Adds a reference line based on the currently selected type in the type selection"""
        ref_line_type_text = self.view.ref_line_type_combo.currentText()
        line_style = self._get_matplotlib_linestyle(self.view.ref_line_style_combo.currentText())
        line_width = self.view.ref_line_width_spin.value()
        alpha = self.view.ref_line_alpha_spin.value()
        label = self.view.ref_line_label_input.text().strip() or None

        ref_line_data: Dict[str, Any] = {
            "color": self.ref_line_color,
            "linestyle": line_style,
            "linewidth": line_width,
            "alpha": alpha,
            "label": label
        }
        list_text = ""
        status_text = ""

        if ref_line_type_text == "Horizontal (axhline)":
            y_pos = self.view.ref_line_y_spin.value()
            ref_line_data.update({"type": "hline", "y": y_pos})
            list_text = f"hline: y={y_pos:.2f}"
            status_text = f"Added horizontal reference line at y={y_pos:.2f}"

        elif ref_line_type_text == "Vertical (axvline)":
            x_pos = self.view.ref_line_x_spin.value()
            ref_line_data.update({"type": "vline", "x": x_pos})
            list_text = f"vline: x={x_pos:.2f}"
            status_text = f"Added vertical reference line at x={x_pos:.2f}"

        elif ref_line_type_text == "Diagonal (axline)":
            slope = self.view.ref_line_slope_spin.value()
            intercept = self.view.ref_line_intercept_spin.value()
            ref_line_data.update({"type": "axline", "slope": slope, "intercept": intercept})
            list_text = f"axline: slope={slope:.2f}, intercept={intercept:.2f}"
            status_text = f"Added diagonal reference line (slope={slope:.2f}, intercept={intercept:.2f})"

        self.reference_lines.append(ref_line_data)
        self._add_to_reference_lines_list(list_text)
        self.status_bar.log(status_text)
        self.plot_tab.on_style_changed()

    def _add_to_reference_lines_list(self, text: str) -> None:
        """Adds an entry to the reference lines list widget"""
        self.view.reference_lines_list.addItem(text)

    def on_reference_line_selected(self, item: QListWidgetItem) -> None:
        """Handle selection of a reference line from the list"""
        index = self.view.reference_lines_list.row(item)
        if 0 <= index < len(self.reference_lines):
            self.selected_ref_line_index = index
            ref_line = self.reference_lines[index]

            # Update the UI to reflect the selected line
            self._populate_editor_from_ref_line(ref_line)

            self.view.update_ref_line_button.setEnabled(True)
            self.view.delete_ref_line_button.setEnabled(True)

            self.status_bar.log(f"Selected reference line: {ref_line['type']}")

    def _populate_editor_from_ref_line(self, ref_line: Dict[str, Any]) -> None:
        """Populate the editor UI with the selected reference line's properties"""
        type_map = {"hline": "Horizontal (axhline)", "vline": "Vertical (axvline)", "axline": "Diagonal (axline)"}
        self.view.ref_line_type_combo.setCurrentText(type_map.get(ref_line["type"], "Horizontal (axhline)"))

        if ref_line["type"] == "hline":
            self.view.ref_line_y_spin.setValue(ref_line.get("y", 0.0))
        elif ref_line["type"] == "vline":
            self.view.ref_line_x_spin.setValue(ref_line.get("x", 0.0))
        elif ref_line["type"] == "axline":
            self.view.ref_line_slope_spin.setValue(ref_line.get("slope", 1.0))
            self.view.ref_line_intercept_spin.setValue(ref_line.get("intercept", 0.0))

        self.ref_line_color = ref_line.get("color", "black")
        self.view.ref_line_color_label.setText(self.ref_line_color)
        ColorManager.update_button_color_swatch(self.view.ref_line_color_button, QColor(self.ref_line_color))

        mpl_to_ui_style = {"-": "solid", "--": "dashed", "-.": "dashdot", ":": "dotted"}
        self.view.ref_line_style_combo.setCurrentText(mpl_to_ui_style.get(ref_line.get("linestyle", "-"), "solid"))

        self.view.ref_line_width_spin.setValue(ref_line.get("linewidth", 1.5))
        self.view.ref_line_alpha_spin.setValue(ref_line.get("alpha", 1.0))
        self.view.ref_line_label_input.setText(ref_line.get("label", "") or "")

    def update_selected_reference_line(self) -> None:
        """Updates the currently selected reference line with new properties"""
        if self.selected_ref_line_index < 0 or self.selected_ref_line_index >= len(self.reference_lines):
            QMessageBox.warning(self.plot_tab, "Warning", "No reference line selected")
            return

        ref_line_type_text = self.view.ref_line_type_combo.currentText()
        type_map = {"Horizontal (axhline)": "hline", "Vertical (axvline)": "vline", "Diagonal (axline)": "axline"}
        new_type = type_map.get(ref_line_type_text, "hline")

        line_style = self._get_matplotlib_linestyle(self.view.ref_line_style_combo.currentText())
        label = self.view.ref_line_label_input.text().strip() or None

        updated_data = {
            "type": new_type,
            "color": self.ref_line_color,
            "linestyle": line_style,
            "linewidth": self.view.ref_line_width_spin.value(),
            "alpha": self.view.ref_line_alpha_spin.value(),
            "label": label
        }

        if new_type == "hline":
            updated_data["y"] = self.view.ref_line_y_spin.value()
        elif new_type == "vline":
            updated_data["x"] = self.view.ref_line_x_spin.value()
        elif new_type == "axline":
            updated_data["slope"] = self.view.ref_line_slope_spin.value()
            updated_data["intercept"] = self.view.ref_line_intercept_spin.value()

        self.reference_lines[self.selected_ref_line_index] = updated_data

        # Also update the item text in the list to reflect the changes
        if new_type == "hline":
            list_text = f"hline: y={updated_data['y']:.2f}"
        elif new_type == "vline":
            list_text = f"vline: x={updated_data['x']:.2f}"
        else:
            list_text = f"axline: slope={updated_data['slope']:.2f}, intercept={updated_data['intercept']:.2f}"

        self.view.reference_lines_list.item(self.selected_ref_line_index).setText(list_text)

        self.status_bar.log(f"Updated reference line at index {self.selected_ref_line_index}")
        self.plot_tab.on_style_changed()

    def delete_selected_reference_line(self) -> None:
        """Delete the currently selected reference line"""
        if self.selected_ref_line_index < 0 or self.selected_ref_line_index >= len(self.reference_lines):
            QMessageBox.warning(self.plot_tab, "Warning", "No reference line selected")
            return

        del self.reference_lines[self.selected_ref_line_index]
        self.view.reference_lines_list.takeItem(self.selected_ref_line_index)

        self.selected_ref_line_index = -1
        self.view.update_ref_line_button.setEnabled(False)
        self.view.delete_ref_line_button.setEnabled(False)

        self.status_bar.log("Deleted reference line")
        self.plot_tab.on_style_changed()

    def clear_all_reference_lines(self) -> None:
        """Clear all reference lines from the plot"""
        self.reference_lines.clear()
        self.view.reference_lines_list.clear()
        self.selected_ref_line_index = -1
        self.view.update_ref_line_button.setEnabled(False)
        self.view.delete_ref_line_button.setEnabled(False)
        self.status_bar.log("Cleared all reference lines")
        self.plot_tab.on_style_changed()

    def on_ref_line_type_changed(self, type_text: str) -> None:
        """Handle changes to the reference line type selector"""
        if type_text == "Horizontal (axhline)":
            self.view.annotations_tab.ref_line_params_stack.setCurrentIndex(0)
            self.view.add_ref_line_button.setText("Add Horizontal Line")
        elif type_text == "Vertical (axvline)":
            self.view.annotations_tab.ref_line_params_stack.setCurrentIndex(1)
            self.view.add_ref_line_button.setText("Add Vertical Line")
        elif type_text == "Diagonal (axline)":
            self.view.annotations_tab.ref_line_params_stack.setCurrentIndex(2)
            self.view.add_ref_line_button.setText("Add Diagonal Line")

    def apply_reference_lines(self) -> None:
        """Apply all reference lines to the current plot"""
        if not self.plot_engine.current_ax:
            return

        lines_to_remove = []
        for child in self.plot_engine.current_ax.get_children():
            gid = child.get_gid()
            if gid and str(gid).startswith("ref_line"):
                lines_to_remove.append(child)

        for line in lines_to_remove:
            try:
                line.remove()
            except ValueError:
                pass

        for i, ref_line in enumerate(self.reference_lines):
            ref_type = ref_line["type"]
            kwargs = {
                "color": ref_line.get("color", "black"),
                "linestyle": ref_line.get("linestyle", "-"),
                "linewidth": ref_line.get("linewidth", 1.5),
                "alpha": ref_line.get("alpha", 1.0),
                "label": ref_line.get("label"),
                "gid": f"ref_line_{i}"
            }
            if ref_type == "hline":
                self.plot_engine.current_ax.axhline(y=ref_line.get("y", 0.0), **kwargs)
            elif ref_type == "vline":
                self.plot_engine.current_ax.axvline(x=ref_line.get("x", 0.0), **kwargs)
            elif ref_type == "axline":
                slope = ref_line.get("slope", 1.0)
                intercept = ref_line.get("intercept", 0.0)
                self.plot_engine.current_ax.axline(
                    (0, intercept),
                    slope=slope,
                    **kwargs
                )

    def _get_matplotlib_linestyle(self, style_name: str) -> str:
        """Converts the UI names to matplotlib linestyle string identifier"""
        style_map = {
            "solid": "-",
            "dashed": "--",
            "dashdot": "-.",
            "dotted": ":"
        }
        return style_map.get(style_name, "-")

    def get_config(self) -> List[Dict[str, Any]]:
        """Get the current reference line configuration for saving and exporting"""
        return self.reference_lines.copy()

    def load_config(self, config: List[Dict[str, Any]]) -> None:
        """Load reference lines configuration from saved data"""
        self.clear_all_reference_lines()
        for ref_line in config:
            self.reference_lines.append(ref_line.copy())

            ref_type = ref_line.get("type", "hline")
            if ref_type == "hline":
                list_text = f"hline: y={ref_line.get('y', 0.0):.2f}"
            elif ref_type == "vline":
                list_text = f"vline: x={ref_line.get('x', 0.0):.2f}"
            else:
                list_text = f"axline: slope={ref_line.get('slope', 1.0):.2f}, intercept={ref_line.get('intercept', 0.0):.2f}"

            self._add_to_reference_lines_list(list_text)

        self.plot_tab.on_style_changed()