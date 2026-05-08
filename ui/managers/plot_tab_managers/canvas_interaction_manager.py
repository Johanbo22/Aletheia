from typing import TYPE_CHECKING, Optional, Tuple, Set

from PyQt6.QtWidgets import QToolTip
from PyQt6.QtGui import QCursor
from matplotlib.widgets import SpanSelector
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.collections import PathCollection
import pandas as pd

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab

class CanvasInteractionManager:
    """Manages canvas mouse events."""

    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab
        self.span_selector: Optional[SpanSelector] = None
        self._pan_axes = None
        self._pan_start: Optional[Tuple[float, float]] = None
        self._pan_start_xlim: Optional[Tuple[float, float]] = None
        self._pan_start_ylim: Optional[Tuple[float, float]] = None

        self._connect_canvas_events()

    def _connect_canvas_events(self) -> None:
        """Binds matplotlibs canvas event to CanvasInteractionManager methods"""
        canvas = self.plot_tab.canvas
        canvas.mpl_connect("pick_event", self.on_pick)
        canvas.mpl_connect("scroll_event", self.on_scroll)
        canvas.mpl_connect("button_press_event", self.on_mouse_press)
        canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        canvas.mpl_connect("button_release_event", self.on_mouse_release)
        canvas.mpl_connect("draw_event", self.on_draw_event)

    def on_draw_event(self, event) -> None:
        """Handles the drawing on canvas to link data points using brush selection feature"""
        if not self.plot_tab.plot_engine.current_ax:
            return

        if self.span_selector is not None:
            if self.span_selector.ax == self.plot_tab.plot_engine.current_ax:
                return
            else:
                self.span_selector = None

        self.setup_brush_and_link()

    def setup_brush_and_link(self) -> None:
        """Sets up the Matplotlib SpanSelector for supported plot types"""
        if not self.plot_tab.plot_engine.current_ax:
            return

        supported_plots = ["Histogram", "Scatter", "Line", "Stem", "Stairs"]
        if self.plot_tab.current_plot_type_name not in supported_plots:
            self.span_selector = None
            return

        def on_select(xmin: float, xmax: float) -> None:
            self._handle_brush_selection(xmin, xmax)

        right_mouse_button = 3
        self.span_selector = SpanSelector(
            self.plot_tab.plot_engine.current_ax,
            on_select,
            "horizontal",
            useblit=True,
            props=dict(alpha=0.3, facecolor="#e74c3c"),
            interactive=True,
            button=right_mouse_button
        )

    def _handle_brush_selection(self, xmin: float, xmax: float) -> None:
        """Filters and highlights rows based on selection span"""
        df: pd.DataFrame = self.plot_tab.get_active_dataframe()
        x_col = self.plot_tab.view.x_column.currentText()

        if not x_col or x_col not in df.columns:
            return

        mask = (df[x_col] >= xmin) & (df[x_col] <= xmax)
        selected_indices: Set[int] = set(df[mask].index)

        if selected_indices:
            self.plot_tab.brush_selection_made.emit(selected_indices)
            self.plot_tab.status_bar.log(f"Selected {len(selected_indices)} points", "INFO")

    def on_scroll(self, event) -> None:
        """Handles zoom in/out events via mouse scroll"""
        if not event.inaxes:
            return

        ax = event.inaxes
        base_scale = 1.15
        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()

        if event.button == "up":
            scale_factor = 1 / base_scale
        elif event.button == "down":
            scale_factor = base_scale
        else:
            scale_factor = 1

        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

        relx = (cur_xlim[1] - event.xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - event.ydata) / (cur_ylim[1] - cur_ylim[0])

        ax.set_xlim([event.xdata - new_width * (1 - relx), event.xdata + new_width * relx])
        ax.set_ylim([event.ydata - new_height * (1 - rely), event.ydata + new_height * rely])

        self.plot_tab.canvas.draw_idle()

    def on_pick(self, event) -> None:
        """Handles pick events to sync UI panels"""
        artist = event.artist

        if self.plot_tab.annotation_manager.handle_pick_event(artist, event):
            return

        index_of_appearance_tab = 1
        self.plot_tab.custom_tabs.setCurrentIndex(index_of_appearance_tab)
        ax = self.plot_tab.plot_engine.current_ax

        if artist == ax.get_title():
            self.plot_tab.view.title_input.setFocus()
        elif artist == ax.xaxis.get_label():
            self.plot_tab.view.xlabel_input.setFocus()
        elif artist == ax.yaxis.get_label():
            self.plot_tab.view.ylabel_input.setFocus()
            self.plot_tab.status_bar.log(f"Selected text element: {artist.get_text()}", "INFO")

        elif isinstance(artist, Line2D):
            if artist.get_gid() in ["regression_line", "confidence_interval", "error_bar"]:
                return

            index_of_customization_tab = 4
            self.plot_tab.custom_tabs.setCurrentIndex(index_of_customization_tab)
            if not self.plot_tab.view.multiline_custom_check.isChecked():
                self.plot_tab.view.multiline_custom_check.setChecked(True)

            label = artist.get_label()
            if label:
                index = self.plot_tab.view.line_selector_combo.findText(label)
                if index >= 0:
                    self.plot_tab.view.line_selector_combo.setCurrentIndex(index)
                    self.plot_tab.status_bar.log(f"Selected line: {label}", "INFO")

        elif isinstance(artist, Rectangle):
            self._handle_bar_pick(artist)

        elif isinstance(artist, PathCollection):
            index_of_customization_tab = 4
            self.plot_tab.custom_tabs.setCurrentIndex(index_of_customization_tab)
            self.plot_tab.status_bar.log("Selected scatter points", "INFO")

    def _handle_bar_pick(self, artist: Rectangle) -> None:
        """Handle picking a bar chart rectangle"""
        found_container = None
        ax = self.plot_tab.plot_engine.current_ax
        if ax and ax.containers:
            for container in ax.containers:
                if artist in container:
                    found_container = container
                    break

        if found_container:
            if hasattr(self.plot_tab, "custom_tabs"):
                self.plot_tab.custom_tabs.setCurrentIndex(4)

            if not self.plot_tab.view.multibar_custom_check.isChecked():
                self.plot_tab.view.multibar_custom_check.setChecked(True)

            for i in range(self.plot_tab.view.bar_selector_combo.count()):
                if self.plot_tab.view.bar_selector_combo.itemData(i) == found_container:
                    self.plot_tab.view.bar_selector_combo.setCurrentIndex(i)
                    label = self.plot_tab.view.bar_selector_combo.itemText(i)
                    self.plot_tab.status_bar.log(f"Selected bar series: {label}", "INFO")
                    break

    def on_mouse_press(self, event) -> None:
        """Handles the event for mouse pressing for panning and annotation placement"""
        if not event.inaxes:
            return

        right_mouse_click = 3
        middle_mouse_click = 2
        left_mouse_click = 1

        if event.button == right_mouse_click:
            if event.inaxes in self.plot_tab.plot_engine.axes_flat:
                idx = self.plot_tab.plot_engine.axes_flat.index(event.inaxes)
                self.plot_tab.view.active_subplot_combo.setCurrentIndex(idx)
                self.plot_tab.status_bar.log(f"Active subplot changed to Plot {idx + 1}.", "INFO")
            return

        if event.button == middle_mouse_click:
            self._pan_axes = event.inaxes
            self._pan_start = (event.x, event.y)
            self._pan_start_xlim = self._pan_axes.get_xlim()
            self._pan_start_ylim = self._pan_axes.get_ylim()

        if event.button != left_mouse_click:
            return

        # Check if user is placing an annotation
        annotation_tab_index = 5
        if self.plot_tab.custom_tabs.currentIndex() == annotation_tab_index:
            ax = self.plot_tab.plot_engine.current_ax
            if ax:
                inv = ax.transAxes.inverted()
                x, y = inv.transform((event.x, event.y))

                x = max(0.0, min(1.0, x))
                y = max(0.0, min(1.0, y))

                self.plot_tab.view.annotation_x_spin.setValue(x)
                self.plot_tab.view.annotation_y_spin.setValue(y)

    def on_mouse_move(self, event) -> None:
        """Handles middle-click mouse panning and tooltips"""
        if not event.inaxes:
            QToolTip.hideText()
            return

        if self._pan_axes and self._pan_start and event.inaxes == self._pan_axes:
            inv = self._pan_axes.transData.inverted()
            start_data = inv.transform(self._pan_start)
            current_data = inv.transform((event.x, event.y))

            dx_data = current_data[0] - start_data[0]
            dy_data = current_data[1] - start_data[1]

            self._pan_axes.set_xlim(self._pan_start_xlim[0] - dx_data, self._pan_start_xlim[1] - dx_data)
            self._pan_axes.set_ylim(self._pan_start_ylim[0] - dy_data, self._pan_start_ylim[1] - dy_data)
            self.plot_tab.canvas.draw_idle()

        if self.plot_tab.annotation_manager.handle_mouse_move(event):
            return

        self._show_data_tooltip(event)

    def _show_data_tooltip(self, event) -> None:
        """Shows coordinate tooltips when hovering over data points"""
        found_point = False

        # Check lines
        for line in event.inaxes.get_lines():
            cont, ind = line.contains(event)
            if cont and len(ind.get("ind", [])) > 0:
                idx = ind["ind"][0]
                x_val = line.get_xdata()[idx]
                y_val = line.get_ydata()[idx]
                text = f"X: {x_val:.4g}\nY: {y_val:.4g}" if isinstance(x_val, (int, float)) else f"X: {x_val}\nY: {y_val:.4g}"
                QToolTip.showText(QCursor.pos(), text, self.plot_tab.canvas)
                found_point = True
                break

        # Check collections
        if not found_point:
            for collection in event.inaxes.collections:
                cont, ind = collection.contains(event)
                if cont and len(ind.get("ind", [])) > 0:
                    idx = ind["ind"][0]
                    offsets = collection.get_offsets()[idx]
                    x_val, y_val = offsets[0], offsets[1]
                    text = f"X: {x_val:.4g}\nY: {y_val:.4g}"
                    QToolTip.showText(QCursor.pos(), text, self.plot_tab.canvas)
                    found_point = True
                    break

        if not found_point:
            QToolTip.hideText()

    def on_mouse_release(self, event) -> None:
        """Handles mouse release event to stop panning or dragging"""
        middle_mouse_click = 2
        if event.button == middle_mouse_click:
            self._pan_axes = None
            self._pan_start = None
            self._pan_start_xlim = None
            self._pan_start_ylim = None
            return

        self.plot_tab.annotation_manager.handle_mouse_relase(event)

    def clear(self) -> None:
        """Clears the canvas interaction state"""
        if self.span_selector is not None:
            if hasattr(self.span_selector, "clear"):
                self.span_selector.clear()
            elif hasttr(self.span_selector, "set_visible"):
                self.span_selector.set_visible(False)