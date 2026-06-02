from typing import Dict, Any, List, TYPE_CHECKING

from PyQt6.QtWidgets import QColorDialog, QMessageBox, QListWidgetItem
from PyQt6.QtGui import QColor

from ui.managers.plot_tab_managers import ColorManager

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab

class ReferenceSpanManager:
    """
    Manages reference spans on the plot canvas
    Handles drawing horizontal (axhspan) and vertical (axvspan) shaded areas
    """
    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab
        self.view = plot_tab.view
        self.status_bar = plot_tab.status_bar
        self.plot_engine = plot_tab.plot_engine
        self.canvas = plot_tab.canvas

        # State tracking of spans
        self.reference_spans: List[Dict[str, Any]] = []
        self.selected_ref_span_index: int = -1

        # Default styling
        self.ref_span_color: str = "blue"

    def connect_signals(self) -> None:
        """Connects the UI signals to methods for this Manager"""
        self.view.annotations_tab.add_ref_span_button.clicked.connect(self.add_reference_span)
        self.view.annotations_tab.clear_ref_spans_button.clicked.connect(self.clear_all_reference_spans)
        self.view.annotations_tab.reference_spans_list.itemClicked.connect(self.on_reference_span_selected)
        self.view.annotations_tab.update_ref_span_button.clicked.connect(self.update_selected_reference_span)
        self.view.annotations_tab.delete_ref_span_button.clicked.connect(self.delete_selected_reference_span)
        self.view.annotations_tab.deselect_ref_span_button.clicked.connect(self.deselect_reference_span)

        self.view.annotations_tab.ref_span_color_button.clicked.connect(self.choose_ref_span_color)
        self.view.annotations_tab.ref_span_type_combo.currentTextChanged.connect(self.on_ref_span_type_changed)

    def choose_ref_span_color(self) -> None:
        """Opens the color dialog for choosing a color for the reference span"""
        color = QColorDialog.getColor(
            initial=QColor(self.ref_span_color),
            parent=self.plot_tab,
            title="Select Reference Span Color",
            options=QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        if color.isValid():
            self.ref_span_color = color.name()
            self.view.annotations_tab.ref_span_color_label.setText(self.ref_span_color)
            ColorManager.update_button_color_swatch(
                self.view.annotations_tab.ref_span_color_button, QColor(self.ref_span_color)
            )

    def add_reference_span(self) -> None:
        """Adds a reference span based on the current selected type"""
        ref_span_type_text = self.view.annotations_tab.ref_span_type_combo.currentText()
        alpha = self.view.annotations_tab.ref_span_alpha_spin.value()
        zorder = self.view.annotations_tab.ref_span_zorder_spin.value()
        label = self.view.annotations_tab.ref_span_label_input.text().strip() or None

        ref_span_data: Dict[str, Any] = {
            "color": self.ref_span_color,
            "alpha": alpha,
            "zorder": zorder,
            "label": label,
        }

        list_text = ""
        status_text = ""

        if ref_span_type_text == "Horizontal (axhspan)":
            ymin = self.view.annotations_tab.ref_span_ymin_spin.value()
            ymax = self.view.annotations_tab.ref_span_ymax_spin.value()
            ref_span_data.update({"type": "hspan", "ymin": ymin, "ymax": ymax})
            list_text = f"hspan: ymin={ymin:.2f}, ymax={ymax:.2f}"
            status_text =f"Added horizontal span between y={ymin:.2f} and y={ymax:.2f}"

        elif ref_span_type_text == "Vertical (axvspan)":
            xmin = self.view.annotations_tab.ref_span_xmin_spin.value()
            xmax = self.view.annotations_tab.ref_span_xmax_spin.value()
            ref_span_data.update({"type": "vspan", "xmin": xmin, "xmax": xmax})
            list_text = f"vspan: xmin={xmin:.2f}, xmax={xmax:.2f}"
            status_text = f"Added vertical span between x={xmin:.2f} and x={xmax:.2f}"

        self.reference_spans.append(ref_span_data)
        self._add_to_reference_spans_list(list_text)
        self.status_bar.log(status_text)
        self.plot_tab.on_style_changed()

    def _add_to_reference_spans_list(self, text: str) -> None:
        """Adds an entry to the reference spans list widget"""
        self.view.annotations_tab.reference_spans_list.addItem(text)

    def on_reference_span_selected(self, item: QListWidgetItem) -> None:
        """Handle selection of a reference span from the list"""
        index = self.view.annotations_tab.reference_spans_list.row(item)
        if 0 <= index < len(self.reference_spans):
            self.selected_ref_span_index = index
            ref_span = self.reference_spans[index]

            self._populate_editor_from_ref_span(ref_span)

            self.view.annotations_tab.update_ref_span_button.setEnabled(True)
            self.view.annotations_tab.delete_ref_span_button.setEnabled(True)
            self.view.annotations_tab.deselect_ref_span_button.setEnabled(True)
            self.view.annotations_tab.add_ref_span_button.setEnabled(False)
            self.status_bar.log(f"Selected reference span: {ref_span['type']}")

    def deselect_reference_span(self) -> None:
        """Deselects the current span and returns the UI to creation mode"""
        self.view.annotations_tab.reference_spans_list.clearSelection()
        self.selected_ref_span_index = -1
        self.view.annotations_tab.update_ref_span_button.setEnabled(False)
        self.view.annotations_tab.delete_ref_span_button.setEnabled(False)
        self.view.annotations_tab.deselect_ref_span_button.setEnabled(False)
        self.view.annotations_tab.add_ref_span_button.setEnabled(True)
        self.status_bar.log("Deselected Reference span")

    def _populate_editor_from_ref_span(self, ref_span: Dict[str, Any]) -> None:
        """Populates the editor UI with the selected reference span's properties"""
        type_map = {"hspan": "Horizontal (axhspan)", "vspan": "Vertical (axvspan)"}
        self.view.annotations_tab.ref_span_type_combo.setCurrentText(type_map.get(ref_span["type"], "Horizontal (axhspan)"))

        if ref_span["type"] == "hspan":
            self.view.annotations_tab.ref_span_ymin_spin.setValue(ref_span.get("ymin", 0.0))
            self.view.annotations_tab.ref_span_ymax_spin.setValue(ref_span.get("ymax", 1.0))
        elif ref_span["type"] == "vspan":
            self.view.annotations_tab.ref_span_xmin_spin.setValue(ref_span.get("xmin", 0.0))
            self.view.annotations_tab.ref_span_xmax_spin.setValue(ref_span.get("xmax", 1.0))

        self.ref_span_color = ref_span.get("color", "blue")
        self.view.annotations_tab.ref_span_color_label.setText(self.ref_span_color)
        ColorManager.update_button_color_swatch(
            self.view.annotations_tab.ref_span_color_button, QColor(self.ref_span_color)
        )

        self.view.annotations_tab.ref_span_alpha_spin.setValue(ref_span.get("alpha", 0.3))
        self.view.annotations_tab.ref_span_label_input.setText(ref_span.get("label", "") or "")
        self.view.annotations_tab.ref_span_zorder_spin.setValue(ref_span.get("zorder", -1))

    def update_selected_reference_span(self) -> None:
        """Updates the selected reference span with new properties"""
        if self.selected_ref_span_index < 0 or self.selected_ref_span_index >= len(self.reference_spans):
            QMessageBox.warning(self.plot_tab, "Warning", "No reference span selected")
            return

        ref_span_type_text = self.view.annotations_tab.ref_span_type_combo.currentText()
        type_map = {"Horizontal (axhspan)": "hspan", "Vertical (axvspan)": "vspan"}
        new_type = type_map.get(ref_span_type_text, "hspan")

        label = self.view.annotations_tab.ref_span_label_input.text().strip() or None

        updated_data = {
            "type": new_type,
            "color": self.ref_span_color,
            "alpha": self.view.annotations_tab.ref_span_alpha_spin.value(),
            "zorder": self.view.annotations_tab.ref_span_zorder_spin.value(),
            "label": label
        }

        if new_type == "hspan":
            updated_data["ymin"] = self.view.annotations_tab.ref_span_ymin_spin.value()
            updated_data["ymax"] = self.view.annotations_tab.ref_span_ymax_spin.value()
            list_text = f"hspan: ymin={updated_data['ymin']:.2f}, ymax={updated_data['ymax']:.2f}"
        elif new_type == "vspan":
            updated_data["xmin"] = self.view.annotations_tab.ref_span_xmin_spin.value()
            updated_data["xmax"] = self.view.annotations_tab.ref_span_xmax_spin.value()
            list_text = f"vspan: xmin={updated_data['xmin']:.2f}, xmax={updated_data['xmax']:.2f}"

        self.reference_spans[self.selected_ref_span_index] = updated_data
        self.view.annotations_tab.reference_spans_list.item(self.selected_ref_span_index).setText(list_text)

        self.status_bar.log(f"Updated reference span at index: {self.selected_ref_span_index}")
        self.plot_tab.on_style_changed()

    def delete_selected_reference_span(self) -> None:
        """Deletes the selected reference span"""
        if self.selected_ref_span_index < 0 or self.selected_ref_span_index >= len(self.reference_spans):
            QMessageBox.warning(self.plot_tab, "Warning", "No reference span selected")
            return

        del self.reference_spans[self.selected_ref_span_index]
        self.view.annotations_tab.reference_spans_list.takeItem(self.selected_ref_span_index)

        self.selected_ref_span_index = -1
        self.view.annotations_tab.update_ref_span_button.setEnabled(False)
        self.view.annotations_tab.delete_ref_span_button.setEnabled(False)

        self.status_bar.log("Deleted reference span")
        self.plot_tab.on_style_changed()

    def clear_all_reference_spans(self) -> None:
        """Clears all the reference spans from the plot"""
        self.reference_spans.clear()
        self.view.annotations_tab.reference_spans_list.clear()
        self.selected_ref_span_index = -1
        self.view.annotations_tab.update_ref_span_button.setEnabled(False)
        self.view.annotations_tab.delete_ref_span_button.setEnabled(False)
        self.status_bar.log("Cleared all reference spans")
        self.plot_tab.on_style_changed()

    def on_ref_span_type_changed(self, type_text: str) -> None:
        """
        Handles changes to the reference span type selector
        Sets the currentIndex of the StackedWidget to the according type
        """
        if type_text == "Horizontal (axhspan)":
            self.view.annotations_tab.ref_span_params_stack.setCurrentIndex(0)
            self.view.annotations_tab.add_ref_span_button.setText("Add Horizontal Span")
        elif type_text == "Vertical (axvspan)":
            self.view.annotations_tab.ref_span_params_stack.setCurrentIndex(1)
            self.view.annotations_tab.add_ref_span_button.setText("Add Vertical Span")

    def apply_reference_spans(self) -> None:
        """Apply the reference spans to the plot"""
        if not self.plot_engine.current_ax:
            return

        lines_to_remove = []
        for child in self.plot_engine.current_ax.get_children():
            gid = child.get_gid()
            if gid and str(gid).startswith("ref_span"):
                lines_to_remove.append(child)

        for span in lines_to_remove:
            try:
                span.remove()
            except ValueError:
                pass

        for i, ref_span in enumerate(self.reference_spans):
            span_type = ref_span["type"]
            kwargs = {
                "facecolor": ref_span.get("color", "blue"),
                "alpha": ref_span.get("alpha", 0.3),
                "zorder": ref_span.get("zorder", -1),
                "label": ref_span.get("label"),
                "gid": f"ref_span_{i}",
                "edgecolor": "none"
            }
            if span_type == "hspan":
                self.plot_engine.current_ax.axhspan(
                    ymin=ref_span.get("ymin", 0.0),
                    ymax=ref_span.get("ymax", 1.0),
                    **kwargs
                )
            elif span_type == "vspan":
                self.plot_engine.current_ax.axvspan(
                    xmin=ref_span.get("xmin", 0.0),
                    xmax=ref_span.get("xmax", 1.0),
                    **kwargs
                )

    def get_config(self) -> List[Dict[str, Any]]:
        """Get the current reference span configuration for saving and exporting"""
        return self.reference_spans.copy()

    def load_config(self, config: List[Dict[str, Any]]) -> None:
        """Load reference spans configuration from saved data"""
        self.clear_all_reference_spans()
        for ref_span in config:
            self.reference_spans.append(ref_span.copy())

            span_type = ref_span.get("type", "hspan")
            if span_type == "hspan":
                list_text = f"hspan: ymin={ref_span.get('ymin', 0.0):.2f}, ymax={ref_span.get('ymax', 1.0):.2f}"
            elif span_type == "vspan":
                list_text = f"vspan: xmin={ref_span.get('xmin', 0.0):.2f}, xmax={ref_span.get('xmax', 1.0):.2f}"

            self._add_to_reference_spans_list(list_text)

        self.plot_tab.on_style_changed()