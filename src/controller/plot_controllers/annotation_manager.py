import ast
import json
from typing import Any, Dict, List, TYPE_CHECKING

import pandas as pd
from PyQt6.QtCore import QPoint, QTimer, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QColorDialog, QListWidgetItem
from matplotlib.text import Text

from src.controller.plot_controllers.color_manager import ColorManager
from src.core.global_signals import ToastLevel, global_signals
from src.ui.dialogs.ArrowCheatSheetDialog import ArrowCheatSheetDialog
from src.ui.status_bar import LogLevel
from src.ui.widgets.ContextualAnnotationToolbar import ContextualAnnotationToolbar

if TYPE_CHECKING:
    from src.ui.plot_tab import PlotTab

class AnnotationManager:
    """Manages manual and auto annotations and Drag and drop on canvas features"""

    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab
        self.view = plot_tab.view
        self.status_bar = plot_tab.status_bar
        self.plot_engine = plot_tab.plot_engine
        self.canvas = plot_tab.canvas

        # State tracking
        self.annotations: List[Dict[str, Any]] = []
        self.dragged_annotation = None
        self._bg_cache = None
        self.ignore_next_click: bool = False
        self._is_updating_ui: bool = False

        debounce_interval_milliseconds: int = 100
        self._redraw_timer: QTimer = QTimer(self.plot_tab)
        self._redraw_timer.setSingleShot(True)
        self._redraw_timer.setInterval(debounce_interval_milliseconds)
        self._redraw_timer.timeout.connect(self.plot_tab.on_style_changed)

        text_typing_delay: int = 750
        self._text_typing_timer: QTimer = QTimer(self.plot_tab)
        self._text_typing_timer.setSingleShot(True)
        self._text_typing_timer.setInterval(text_typing_delay)
        self._text_typing_timer.timeout.connect(self.update_active_annotation)

        self.annotation_color: str = "black"
        self.annotation_bg_color: str = "wheat"
        self.auto_annotation_color: str = "black"

        self.context_toolbar = ContextualAnnotationToolbar(self.plot_tab)
        self.context_toolbar.styleChanged.connect(self._update_annotations_from_toolbar)
        self.context_toolbar.deleteRequested.connect(self._delete_annotation_from_toolbar)

    def connect_signals(self) -> None:
        self.view.annotation_color_button.clicked.connect(self.choose_annotation_color)
        self.view.annotation_bg_color_button.clicked.connect(self.choose_annotation_bg_color)
        self.view.auto_annotate_check.clicked.connect(self.toggle_auto_annotate)
        self.view.auto_annotate_color_button.clicked.connect(self.choose_auto_annotate_color)
        self.view.add_annotation_button.clicked.connect(self.add_annotation)
        self.view.annotations_tab.deselect_annotation_button.clicked.connect(self.deselect_annotation)
        self.view.annotations_list.itemSelectionChanged.connect(self.on_annotation_selection_changed)
        self.view.annotations_list.itemChanged.connect(self.on_annotation_item_changed)
        self.view.clear_annotations_button.clicked.connect(self.clear_annotations)

        self.view.annotation_text.editingFinished.connect(self.update_active_annotation)
        self.view.annotation_x_spin.valueChanged.connect(self.update_active_annotation)
        self.view.annotation_y_spin.valueChanged.connect(self.update_active_annotation)
        self.view.annotation_fontsize_spin.valueChanged.connect(self.update_active_annotation)

        self.view.annotations_tab.annotation_boxstyle_combo.currentTextChanged.connect(self.update_active_annotation)
        self.view.annotations_tab.annotation_bg_alpha_slider.valueChanged.connect(self.update_active_annotation)

        self.view.annotations_tab.arrow_enable_check.stateChanged.connect(self._toggle_arrow_inputs)
        self.view.annotations_tab.arrow_enable_check.stateChanged.connect(self.update_active_annotation)
        self.view.annotations_tab.arrow_x_spin.valueChanged.connect(self.update_active_annotation)
        self.view.annotations_tab.arrow_y_spin.valueChanged.connect(self.update_active_annotation)
        self.view.annotations_tab.arrow_preset_combo.currentTextChanged.connect(self._toggle_arrow_inputs)
        self.view.annotations_tab.arrow_preset_combo.currentTextChanged.connect(self.update_active_annotation)
        self.view.annotations_tab.custom_arrow_edit.textChanged.connect(self._text_typing_timer.start)
        self.view.annotations_tab.arrow_help_button.clicked.connect(self.show_arrow_cheat_sheet)

        self.view.annotations_tab.annotation_locator.textPositionChanged.connect(self._on_locator_text_changed)
        self.view.annotations_tab.annotation_locator.targetPositionChanged.connect(self._on_locator_target_changed)

        for widget in [self.view.auto_annotate_fontsize_spin, self.view.auto_annotate_x_offset_spin,
                       self.view.auto_annotate_y_offset_spin, self.view.auto_annotate_rotation_spin]:
            widget.valueChanged.connect(self.plot_tab.on_style_changed)
        self.view.auto_annotate_weight_combo.currentTextChanged.connect(self.plot_tab.on_style_changed)

        self.view.textbox_enable_check.stateChanged.connect(self.plot_tab.on_style_changed)
        self.view.textbox_content.textChanged.connect(self.plot_tab.on_style_changed)
        self.view.textbox_position_combo.currentTextChanged.connect(self.plot_tab.on_style_changed)
        self.view.textbox_style_combo.currentTextChanged.connect(self.plot_tab.on_style_changed)

    def choose_annotation_color(self) -> None:
        color = QColorDialog.getColor(
            initial=QColor(self.annotation_color),
            parent=self.plot_tab,
            title="Select Text Color",
            options=QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        if color.isValid():
            self.annotation_color = color.name(QColor.NameFormat.HexArgb) if color.alpha() < 255 else color.name()
            self.view.annotation_color_label.setText(self.annotation_color)
            ColorManager.update_button_color_swatch(self.view.annotation_color_button, QColor(self.annotation_color))
            self.update_active_annotation()
            self.plot_tab.on_style_changed()

    def choose_annotation_bg_color(self) -> None:
        color = QColorDialog.getColor(
            initial=QColor(self.annotation_bg_color),
            parent=self.plot_tab,
            title="Select Background Color",
            options=QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        if color.isValid():
            self.annotation_bg_color = color.name(QColor.NameFormat.HexArgb) if color.alpha() < 255 else color.name()
            self.view.annotation_bg_color_label.setText(self.annotation_bg_color)
            ColorManager.update_button_color_swatch(self.view.annotation_bg_color_button,
                                                    QColor(self.annotation_bg_color))
            self.update_active_annotation()
            self.plot_tab.on_style_changed()

    def choose_auto_annotate_color(self) -> None:
        color = QColorDialog.getColor(
            initial=QColor(self.auto_annotation_color),
            parent=self.plot_tab,
            title="Select Auto-Annotation Color",
            options=QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        if color.isValid():
            self.auto_annotation_color = color.name(QColor.NameFormat.HexArgb) if color.alpha() < 255 else color.name()
            self.view.auto_annotate_color_label.setText(self.auto_annotation_color)
            ColorManager.update_button_color_swatch(self.view.auto_annotate_color_button,
                                                    QColor(self.auto_annotation_color))

            self.plot_tab.on_style_changed()

    def toggle_auto_annotate(self) -> None:
        """Toggles the automatic annotation of data points on the canvas"""
        is_enabled = self.view.auto_annotate_check.isChecked()
        for widget in [self.view.auto_annotate_col_combo, self.view.auto_annotate_fontsize_spin,
                       self.view.auto_annotate_weight_combo, self.view.auto_annotate_color_button,
                       self.view.auto_annotate_x_offset_spin, self.view.auto_annotate_y_offset_spin,
                       self.view.auto_annotate_rotation_spin]:
            widget.setEnabled(is_enabled)
        self.plot_tab.on_style_changed()

    def _toggle_arrow_inputs(self, state: int) -> None:
        """Toggles the enable state of arrow inputs based on the ToggleSwitch state id"""
        is_enabled = self.view.annotations_tab.arrow_enable_check.isChecked()
        self.view.annotations_tab.arrow_x_spin.setEnabled(is_enabled)
        self.view.annotations_tab.arrow_y_spin.setEnabled(is_enabled)
        self.view.annotations_tab.arrow_preset_combo.setEnabled(is_enabled)

        preset = self.view.annotations_tab.arrow_preset_combo.currentText()
        show_custom = is_enabled and (preset == "Custom")
        self.view.annotations_tab.custom_arrow_container.setVisible(show_custom)

        if show_custom and not self.view.annotations_tab.custom_arrow_edit.toPlainText():
            seed_dict = {"arrowstyle": "->", "color": "gray", "connectionstyle": "arc3,rad=0.2"}
            formatted_text = json.dumps(seed_dict, indent=4)

            self.view.annotations_tab.custom_arrow_edit.blockSignals(True)
            self.view.annotations_tab.custom_arrow_edit.setPlainText(formatted_text)
            self.view.annotations_tab.custom_arrow_edit.blockSignals(False)

    def _on_locator_text_changed(self, x: float, y: float) -> None:
        """Triggered while a Text Node is dragged"""
        if self._is_updating_ui:
            return

        self._is_updating_ui = True
        self.view.annotation_x_spin.setValue(x)
        self.view.annotation_y_spin.setValue(y)
        self._is_updating_ui = False

        self.update_active_annotation()

    def _on_locator_target_changed(self, x: float, y: float) -> None:
        """Triggered while a Text Node is dragged"""
        if self._is_updating_ui:
            return

        self._is_updating_ui = True
        self.view.annotations_tab.arrow_x_spin.setValue(x)
        self.view.annotations_tab.arrow_y_spin.setValue(y)
        self._is_updating_ui = False

        self.update_active_annotation()

    def show_arrow_cheat_sheet(self) -> None:
        """Displays a modal dialog with a table of valid Matplotlib annotation values"""
        self._cheat_sheet_dialog = ArrowCheatSheetDialog(self.view.annotations_tab)
        self._cheat_sheet_dialog.show()
        self._cheat_sheet_dialog.raise_()
        self._cheat_sheet_dialog.activateWindow()

    def add_annotation(self) -> None:
        """Adds a new annotation to the list of active annotations"""
        text = self.view.annotation_text.text().strip()
        if not text:
            global_signals.request_toast(
                "Missing Text", "Please enter text for the annotation", ToastLevel.WARNING
            )
            return

        annotation = {
            "text"           : text,
            "x"              : self.view.annotation_x_spin.value(),
            "y"              : self.view.annotation_y_spin.value(),
            "fontsize"       : self.view.annotation_fontsize_spin.value(),
            "color"          : self.annotation_color,
            "bg_color"       : self.annotation_bg_color,
            "boxstyle"       : self.view.annotations_tab.annotation_boxstyle_combo.currentText(),
            "box_alpha"      : self.view.annotations_tab.annotation_bg_alpha_slider.value() / 100.0,
            "has_arrow"      : self.view.annotations_tab.arrow_enable_check.isChecked(),
            "arrow_x"        : self.view.annotations_tab.arrow_x_spin.value(),
            "arrow_y"        : self.view.annotations_tab.arrow_y_spin.value(),
            "arrow_preset"   : self.view.annotations_tab.arrow_preset_combo.currentText(),
            "arrow_dict_text": self.view.annotations_tab.custom_arrow_edit.toPlainText()
        }

        self.annotations.append(annotation)

        item = QListWidgetItem(f"{text} @ ({annotation['x']:.2f}, {annotation['y']:.2f})")
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked)

        self._is_updating_ui = True
        self.view.annotations_list.addItem(item)
        self.view.annotation_text.clear()
        self.view.annotations_list.clearSelection()
        self._is_updating_ui = False

        self.status_bar.log(f"Added an annotation: {text}")
        self.plot_tab.on_style_changed()

    def update_active_annotation(self, *args: Any) -> None:
        """Updates the selected annotation's properties when the UI parameters change"""
        if self._is_updating_ui:
            return

        has_arrow = self.view.annotations_tab.arrow_enable_check.isChecked()
        x = self.view.annotation_x_spin.value()
        y = self.view.annotation_y_spin.value()
        arrow_x = self.view.annotations_tab.arrow_x_spin.value()
        arrow_y = self.view.annotations_tab.arrow_y_spin.value()

        self.view.annotations_tab.annotation_locator.set_arrow_enabled(has_arrow)
        self.view.annotations_tab.annotation_locator.set_text_color(QColor(self.annotation_color))
        self.view.annotations_tab.annotation_locator.set_text_pos(x, y)
        if has_arrow:
            self.view.annotations_tab.annotation_locator.set_target_pos(arrow_x, arrow_y)

        selected_items = self.view.annotations_list.selectedItems()
        if not selected_items:
            return

        index: int = self.view.annotations_list.row(selected_items[0])
        if 0 <= index < len(self.annotations):
            ann = self.annotations[index]
            new_text = self.view.annotation_text.text().strip()

            if not new_text:
                return

            ann["text"] = new_text
            ann["x"] = x
            ann["y"] = y
            ann["fontsize"] = self.view.annotation_fontsize_spin.value()
            ann["color"] = self.annotation_color
            ann["bg_color"] = self.annotation_bg_color
            ann["boxstyle"] = self.view.annotations_tab.annotation_boxstyle_combo.currentText()
            ann["box_alpha"] = self.view.annotations_tab.annotation_bg_alpha_slider.value() / 100.0
            ann["has_arrow"] = has_arrow
            ann["arrow_x"] = arrow_x
            ann["arrow_y"] = arrow_y
            ann["arrow_preset"] = self.view.annotations_tab.arrow_preset_combo.currentText()
            ann["arrow_dict_text"] = self.view.annotations_tab.custom_arrow_edit.toPlainText()

            self._is_updating_ui = True
            selected_items[0].setText(f"{ann['text']} @ ({ann['x']:.2f}, {ann['y']:.2f})")
            self._is_updating_ui = False

            self._redraw_timer.start()

    def deselect_annotation(self) -> None:
        """Clears the current annotation selection to allow adding a new one"""
        self.view.annotations_list.clearSelection()
        self.view.annotation_text.clear()

    def on_annotation_item_changed(self, item: QListWidgetItem) -> None:
        """Handles the toggling of annotation visibility via list checking"""
        if self._is_updating_ui:
            return

        index = self.view.annotations_list.row(item)
        if 0 <= index < len(self.annotations):
            is_visible = (item.checkState() == Qt.CheckState.Checked)
            if self.annotations[index].get("visible", True) != is_visible:
                self.annotations[index]["visible"] = is_visible
                self.plot_tab.on_style_changed()

    def on_annotation_selection_changed(self) -> None:
        """The selection of an annotation from the list"""
        selected_items = self.view.annotations_list.selectedItems()
        if not selected_items:
            self.view.add_annotation_button.setEnabled(True)
            self.view.annotations_tab.deselect_annotation_button.setEnabled(False)
            return

        self.view.add_annotation_button.setEnabled(False)
        self.view.annotations_tab.deselect_annotation_button.setEnabled(True)

        item = selected_items[0]
        index = self.view.annotations_list.row(item)
        if 0 <= index < len(self.annotations):
            self._is_updating_ui = True

            ann = self.annotations[index]
            self.view.annotation_text.setText(ann["text"])
            self.view.annotation_x_spin.setValue(ann["x"])
            self.view.annotation_y_spin.setValue(ann["y"])
            self.view.annotation_fontsize_spin.setValue(ann["fontsize"])

            self.annotation_color = ann["color"]
            self.view.annotation_color_label.setText(self.annotation_color)

            self.annotation_bg_color = ann.get("bg_color", "wheat")
            self.view.annotation_bg_color_label.setText(self.annotation_bg_color)
            ColorManager.update_button_color_swatch(self.view.annotation_bg_color_button,
                                                    QColor(self.annotation_bg_color))

            self.view.annotations_tab.annotation_boxstyle_combo.setCurrentText(ann.get("boxstyle", "round"))
            self.view.annotations_tab.annotation_bg_alpha_slider.setValue(int(ann.get("box_alpha", 1.0) * 100))

            has_arrow = ann.get("has_arrow", False)
            self.view.annotations_tab.arrow_enable_check.setChecked(has_arrow)
            self.view.annotations_tab.arrow_x_spin.setValue(ann.get("arrow_x", 0.5))
            self.view.annotations_tab.arrow_y_spin.setValue(ann.get("arrow_y", 0.4))
            self.view.annotations_tab.arrow_preset_combo.setCurrentText(ann.get("arrow_preset", "Subtle Pointer"))
            self.view.annotations_tab.custom_arrow_edit.setPlainText(ann.get("arrow_dict_text", ""))
            self._toggle_arrow_inputs(has_arrow)

            self.view.annotations_tab.annotation_locator.set_arrow_enabled(has_arrow)
            self.view.annotations_tab.annotation_locator.set_text_color(QColor(self.annotation_color))
            self.view.annotations_tab.annotation_locator.set_text_pos(ann.get("x", 0.5), ann.get("y", 0.5))
            if has_arrow:
                self.view.annotations_tab.annotation_locator.set_target_pos(ann.get("arrow_x", 0.5),
                                                                            ann.get("arrow_y", 0.4))

            self._is_updating_ui = False
            self._redraw_timer.start()

    def clear_annotations(self) -> None:
        """Deletes all annotations from the list"""
        self.annotations.clear()

        self._is_updating_ui = True
        self.view.annotations_list.clear()
        self.view.annotation_text.clear()
        self._is_updating_ui = False
        self.status_bar.log(f"Cleared all annotations")
        self.plot_tab.on_style_changed()

    def show_annotation_toolbar(self, index: int, global_pos: QPoint) -> None:
        """Spawns the annotation toolbar"""
        if 0 <= index < len(self.annotations):
            ann_data = self.annotations[index]
            self.context_toolbar.load_annotations(index, ann_data)
            self.context_toolbar.show_at_clamped(global_pos)

    def _update_annotations_from_toolbar(self, index: int, new_data: dict) -> None:
        """Updates the annotation data when using the toolbar"""
        if 0 <= index < len(self.annotations):
            self.annotations[index].update(new_data)
            if index < self.view.annotations_list.count():
                self._is_updating_ui = True
                item = self.view.annotations_list.item(index)
                x, y = self.annotations[index]["x"], self.annotations[index]["y"]
                text = self.annotations[index]["text"]
                item.setText(f"{text} @ ({x:.2f}, {y:.2f})")
                self._is_updating_ui = False
            self.plot_tab.on_style_changed()

    def _delete_annotation_from_toolbar(self, index: int) -> None:
        """Deletes an annotation when using the toolbar"""
        if 0 <= index < len(self.annotations):
            del self.annotations[index]
            item = self.view.annotations_list.takeItem(index)
            del item
            self.view.annotation_text.clear()
            self.plot_tab.on_style_changed()

    def apply_annotations(self, df: pd.DataFrame, x_col: str, y_cols: list[str]) -> None:
        """Applies text annotations to the canvas"""
        if not self.plot_engine.current_ax:
            return

        # Cleanup existing annotations
        texts_to_remove = [text for text in self.plot_engine.current_ax.texts if
                           text.get_gid() and (str(text.get_gid()).startswith("annotation_") or str(
                               text.get_gid()) == "auto_annotation")]
        for text in texts_to_remove:
            try:
                text.remove()
            except ValueError:
                pass

        # Manual annotations
        for i, ann in enumerate(self.annotations):
            if not ann.get("visible", True):
                continue

            font_kwargs = {}
            if "fontfamily" in ann:
                font_kwargs["fontfamily"] = ann["fontfamily"]

            box_style = ann.get("boxstyle", "round")
            bbox_props = dict(
                boxstyle=box_style,
                facecolor=ann.get("bg_color", "wheat"),
                alpha=ann.get("box_alpha", 1.0)
            )

            has_arrow = ann.get("has_arrow", False)
            if has_arrow:
                preset = ann.get("arrow_preset", "Subtle Pointer")
                if preset == "Aggressive Red Arrow":
                    arrow_props = dict(arrowstyle="fancy", color="red", connectionstyle="arc3,rad=0.1")
                elif preset == "Curved Highlight":
                    arrow_props = dict(arrowstyle="-[", color="blue", connectionstyle="angle3,angleA=0,angleB=-90")
                elif preset == "Straight Line":
                    arrow_props = dict(arrowstyle="-", color="black", connectionstyle="arc3,rad=0.0")
                elif preset == "Custom":
                    dict_text = ann.get("arrow_dict_text", "").strip()
                    try:
                        arrow_props = ast.literal_eval(dict_text) if dict_text else {}
                        if not isinstance(arrow_props, dict):
                            arrow_props = dict(arrowstyle="->", color="gray")
                    except Exception:
                        arrow_props = dict(arrowstyle="->", color="gray")
                else:
                    arrow_props = dict(arrowstyle="->", color="gray", connectionstyle="arc3,rad=0.2")

                self.plot_engine.current_ax.annotate(
                    ann["text"],
                    xy=(ann.get("arrow_x", 0.5), ann.get("arrow_y", 0.4)),
                    xycoords='axes fraction',
                    xytext=(ann["x"], ann["y"]),
                    textcoords='axes fraction',
                    fontsize=ann["fontsize"],
                    color=ann["color"],
                    fontweight=ann.get("fontweight", "normal"),
                    fontstyle=ann.get("fontstyle", "normal"),
                    ha=ann.get("ha", "center"), va=ann.get("va", "center"),
                    bbox=bbox_props,
                    arrowprops=arrow_props,
                    picker=True, gid=f"annotation_{i}",
                    **font_kwargs
                )
            else:
                self.plot_engine.current_ax.text(
                    ann["x"], ann["y"], ann["text"],
                    transform=self.plot_engine.current_ax.transAxes,
                    fontsize=ann["fontsize"],
                    color=ann["color"],
                    fontweight=ann.get("fontweight", "normal"),
                    fontstyle=ann.get("fontstyle", "normal"),
                    ha=ann.get("ha", "center"), va=ann.get("va", "center"),
                    bbox=bbox_props,
                    picker=True, gid=f"annotation_{i}",
                    **font_kwargs
                )

        # Auto Annotations
        if self.view.auto_annotate_check.isChecked() and df is not None and x_col and y_cols:
            try:
                label_choice = self.view.auto_annotate_col_combo.currentText()
                is_flipped = self.view.flip_axes_check.isChecked()
                y_col_target = y_cols[0]

                # Filter missing values to prevent rendering invisible "nan" values
                cols_to_check = [x_col, y_col_target]
                if label_choice != "Default (Y-value)" and label_choice in df.columns:
                    cols_to_check.append(label_choice)

                df_clean = df.dropna(subset=cols_to_check)

                MAX_POINTS = 500
                if len(df) > MAX_POINTS:
                    self.status_bar.log(f"Auto-annotations is limited to first {MAX_POINTS} points for performance")
                    df_to_annotate = df_clean.iloc[:MAX_POINTS]
                else:
                    df_to_annotate = df

                font_size = self.view.auto_annotate_fontsize_spin.value()
                font_weight = self.view.auto_annotate_weight_combo.currentText()
                font_color = getattr(self, "auto_annotation_color", "black")
                x_offset = self.view.auto_annotate_x_offset_spin.value()
                y_offset = self.view.auto_annotate_y_offset_spin.value()
                rotation = self.view.auto_annotate_rotation_spin.value()

                x_arr = df_to_annotate[x_col].values
                y_arr = df_to_annotate[y_col_target].values

                if label_choice == "Default (Y-value)":
                    labels_arr = y_arr
                else:
                    labels_arr = df_to_annotate[label_choice].values

                for x_val, y_val, raw_label in zip(x_arr, y_arr, labels_arr):
                    if label_choice == "Default (Y-value)":
                        text = f"{raw_label:.2f}" if isinstance(raw_label, (int, float)) else str(raw_label)
                    else:
                        text = str(raw_label)

                    # apply
                    coordinates = (y_val, x_val) if is_flipped else (x_val, y_val)
                    self.plot_engine.current_ax.annotate(
                        text,
                        coordinates,
                        xytext=(x_offset, y_offset),
                        textcoords="offset points",
                        fontsize=font_size,
                        fontweight=font_weight,
                        color=font_color,
                        rotation=rotation,
                        gid="auto_annotation"
                    )
            except Exception as err:
                self.status_bar.log(f"Error applying annotations: {str(err)}", LogLevel.ERROR)

    def handle_pick_event(self, artist, event) -> bool:
        """Handles selecting an annotation text object on the canvas"""
        if isinstance(artist, Text):
            gid = artist.get_gid()
            if gid and str(gid).startswith("annotation_"):
                self.dragged_annotation = artist
                self.ignore_next_click = True

                if self.plot_tab.style_update_timer.isActive():
                    self.plot_tab.style_update_timer.stop()

                self.dragged_annotation.set_animated(True)
                self.canvas.draw()

                if self.plot_engine.current_ax:
                    self._bg_cache = self.canvas.copy_from_bbox(self.plot_engine.current_ax.bbox)
                    self.plot_engine.current_ax.draw_artist(self.dragged_annotation)
                    self.canvas.blit(self.plot_engine.current_ax.bbox)

                annotation_tab_index = 5
                self.plot_tab.custom_tabs.setCurrentIndex(annotation_tab_index)
                try:
                    idx = int(gid.split("_")[1])
                    if idx < self.view.annotations_list.count():
                        self.view.annotations_list.setCurrentRow(idx)
                        self.status_bar.log(f"Selected annotation: {artist.get_text()}", LogLevel.INFO)

                        mouse_event = getattr(event, "mouseevent", None)
                        is_dbclick = getattr(mouse_event, "dblclick", False)

                        if is_dbclick and hasattr(event, "guiEvent") and event.guiEvent is not None:
                            global_pos = event.guiEvent.globalPosition().toPoint()
                            global_pos.setY(global_pos.y() - 50)
                            self.show_annotation_toolbar(idx, global_pos)
                except ValueError:
                    pass
                return True
        return False

    def handle_mouse_move(self, event) -> bool:
        """Handles the dragging of an annotation across the canvas"""
        if self.dragged_annotation:
            ax = self.plot_engine.current_ax
            inv = ax.transAxes.inverted()
            x, y = inv.transform((event.x, event.y))

            self.dragged_annotation.set_position((x, y))

            if self._bg_cache and ax:
                if self.dragged_annotation.figure is None:
                    self.dragged_annotation.set_figure(self.plot_engine.current_figure)
                self.canvas.restore_region(self._bg_cache)
                ax.draw_artist(self.dragged_annotation)
                self.canvas.blit(ax.bbox)
            else:
                self.canvas.draw_idle()

            self.view.annotation_x_spin.blockSignals(True)
            self.view.annotation_y_spin.blockSignals(True)
            self.view.annotation_x_spin.setValue(x)
            self.view.annotation_y_spin.setValue(y)
            self.view.annotation_x_spin.blockSignals(False)
            self.view.annotation_y_spin.blockSignals(False)
            return True
        return False

    def handle_mouse_release(self, event) -> bool:
        """Handles the drop position of an annotation when mouse-click is released"""
        if self.dragged_annotation:
            gid = self.dragged_annotation.get_gid()
            if gid and gid.startswith("annotation_"):
                try:
                    idx = int(gid.split("_")[1])
                    if 0 <= idx < len(self.annotations):
                        pos = self.dragged_annotation.get_position()
                        self.annotations[idx]["x"] = pos[0]
                        self.annotations[idx]["y"] = pos[1]

                        if idx < self.view.annotations_list.count():
                            self._is_updating_ui = True
                            item = self.view.annotations_list.item(idx)
                            item.setText(f"{self.annotations[idx]['text']} @ ({pos[0]:.2f}, {pos[1]:.2f})")
                            self._is_updating_ui = False

                        self.status_bar.log(f"Moved annotation to ({pos[0]:.2f}, {pos[1]:.2f})", LogLevel.INFO)
                except ValueError:
                    pass

            self.dragged_annotation.set_animated(False)
            self._bg_cache = None
            self.dragged_annotation = None
            self.canvas.draw_idle()
            self.plot_tab.on_style_changed()
            return True
        return False
