from typing import Optional, Set, TYPE_CHECKING, Tuple

import pandas as pd
from PyQt6.QtCore import QEasingCurve, QVariantAnimation
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QToolTip
from matplotlib.collections import PathCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.widgets import SpanSelector

from src.ui.status_bar import LogLevel
from src.ui.widgets.ViewCubeWidget import ViewCubeWidget

if TYPE_CHECKING:
    from src.ui.plot_tab import PlotTab
    from src.ui.widgets.ViewCubeWidget import ViewCubeWidget

class CanvasInteractionManager:
    """Manages canvas mouse events."""

    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab
        self.span_selector: Optional[SpanSelector] = None
        self._pan_axes = None
        self._pan_start: Optional[Tuple[float, float]] = None
        self._pan_start_xlim: Optional[Tuple[float, float]] = None
        self._pan_start_ylim: Optional[Tuple[float, float]] = None

        self.view_cube: Optional["ViewCubeWidget"] = None
        self._angle_animation: Optional[QVariantAnimation] = None
        self._animation_frame_count = 0
        self._target_azimuth = 0.0
        self._target_elevation = 0.0

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

        supported_plots = {"Histogram", "Scatter", "Line", "Stem", "Stairs"}
        if self.plot_tab.current_plot_type_name not in supported_plots:
            self.clear()
            self.span_selector = None
            return

        if self.span_selector is not None:
            if self.span_selector.ax == self.plot_tab.plot_engine.current_ax:
                return
            else:
                self.clear()
                self.span_selector = None

        self.setup_brush_and_link()

    def setup_brush_and_link(self) -> None:
        """Sets up the Matplotlib SpanSelector for supported plot types"""
        if not self.plot_tab.plot_engine.current_ax:
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

        try:
            mask = (df[x_col] >= xmin) & (df[x_col] <= xmax)
            selected_indices: Set[int] = set(df[mask].index)

            if selected_indices:
                self.plot_tab.brush_selection_made.emit(selected_indices)
                self.plot_tab.status_bar.log(f"Selected {len(selected_indices)} points", LogLevel.INFO)
        except TypeError:
            pass

    def on_scroll(self, event) -> None:
        """Handles zoom in/out events via mouse scroll"""
        if not event.inaxes or event.xdata is None or event.ydata is None:
            return

        ax = event.inaxes
        base_scale = 1.15
        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()

        x_range = cur_xlim[1] - cur_xlim[0]
        y_range = cur_ylim[1] - cur_ylim[0]

        if x_range == 0 or y_range == 0:
            return

        if event.button == "up":
            scale_factor = 1 / base_scale
        elif event.button == "down":
            scale_factor = base_scale
        else:
            scale_factor = 1

        new_width = x_range * scale_factor
        new_height = y_range * scale_factor

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

        ax = self.plot_tab.plot_engine.current_ax
        if not ax:
            return

        index_of_appearance_tab = 1
        self.plot_tab.custom_tabs.setCurrentIndex(index_of_appearance_tab)

        if artist == ax.get_title():
            self.plot_tab.view.title_input.setFocus()
        elif artist == ax.xaxis.get_label():
            self.plot_tab.view.xlabel_input.setFocus()
        elif artist == ax.yaxis.get_label():
            self.plot_tab.view.ylabel_input.setFocus()
            self.plot_tab.status_bar.log(f"Selected text element: {artist.get_text()}", LogLevel.INFO)

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
                    self.plot_tab.status_bar.log(f"Selected line: {label}", LogLevel.INFO)

        elif isinstance(artist, Rectangle):
            self._handle_bar_pick(artist)

        elif isinstance(artist, PathCollection):
            index_of_customization_tab = 4
            self.plot_tab.custom_tabs.setCurrentIndex(index_of_customization_tab)
            self.plot_tab.status_bar.log("Selected scatter points", LogLevel.INFO)

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
                    self.plot_tab.status_bar.log(f"Selected bar series: {label}", LogLevel.INFO)
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
                if self.plot_tab.view.active_subplot_combo.currentIndex() != idx:
                    self.plot_tab.view.active_subplot_combo.setCurrentIndex(idx)
                    self.plot_tab.status_bar.log(f"Active subplot changed to Plot {idx + 1}.", LogLevel.INFO)
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
                is_clicking_annotation = False
                for text_artist in ax.texts:
                    if text_artist.get_gid() and str(text_artist.get_gid()).startswith("annotation_"):
                        contains, _ = text_artist.contains(event)
                        if contains:
                            is_clicking_annotation = True
                            break

                if not is_clicking_annotation:
                    inv = ax.transAxes.inverted()
                    x, y = inv.transform((event.x, event.y))

                    x = max(0.0, min(1.0, x))
                    y = max(0.0, min(1.0, y))

                    self.plot_tab.view.annotation_x_spin.setValue(x)
                    self.plot_tab.view.annotation_y_spin.setValue(y)

    def on_mouse_move(self, event) -> None:
        """Handles middle-click mouse panning and tooltips"""
        if not event.inaxes:
            if QToolTip.isVisible():
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
            return

        if self.plot_tab.annotation_manager.handle_mouse_move(event):
            return

        self._show_data_tooltip(event)

    def _show_data_tooltip(self, event) -> None:
        """Shows coordinate tooltips when hovering over data points"""
        found_point = False
        tooltip_text = ""

        def format_coord(val) -> str:
            try:
                return f"{float(val):.4g}"
            except (ValueError, TypeError):
                return str(val)

        # Check lines
        for line in event.inaxes.get_lines():
            cont, ind = line.contains(event)
            if cont and len(ind.get("ind", [])) > 0:
                idx = ind["ind"][0]
                x_val = line.get_xdata()[idx]
                y_val = line.get_ydata()[idx]
                tooltip_text = f"X: {format_coord(x_val)}\nY: {format_coord(y_val)}"
                found_point = True
                break

        # Check collections
        if not found_point:
            for collection in event.inaxes.collections:
                cont, ind = collection.contains(event)
                if cont and len(ind.get("ind", [])) > 0:
                    idx = ind["ind"][0]
                    try:
                        offsets = collection.get_offsets()
                        offset_idx = idx if len(offsets) > idx else 0
                        x_val, y_val = offsets[offset_idx][0], offsets[offset_idx][1]
                        tooltip_text = f"X: {format_coord(x_val)}\nY: {format_coord(y_val)}"
                        found_point = True
                        break
                    except (IndexError, TypeError):
                        pass

        if found_point:
            if QToolTip.text() != tooltip_text:
                QToolTip.showText(QCursor.pos(), tooltip_text, self.plot_tab.canvas)
        else:
            if QToolTip.isVisible():
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

        self.plot_tab.annotation_manager.handle_mouse_release(event)

    def clear(self) -> None:
        """Clears the canvas interaction state"""
        if self.span_selector is not None:
            if hasattr(self.span_selector, "disconnect_events"):
                self.span_selector.disconnect_events()
            if hasattr(self.span_selector, "clear"):
                self.span_selector.clear()
            elif hasattr(self.span_selector, "set_visible"):
                self.span_selector.set_visible(False)

    def setup_view_cube(self, view_cube: "ViewCubeWidget") -> None:

        self.view_cube = view_cube
        view_cube.view_angle_changed.connect(self._on_view_cube_angle_changed)

        self._sync_view_cube_from_plot()

    def _sync_view_cube_from_plot(self) -> None:
        """Updates the ViewCube angles to match the plot orientaiton"""
        if self.view_cube is None:
            return

        ax = self.plot_tab.plot_engine.current_ax
        if ax is None or not hasattr(ax, "azim"):
            return

        azim = getattr(ax, "azim", -60)
        elev = getattr(ax, "elev", 30)

        self.view_cube.set_angles(azim, elev, emit_signal=False)

    def _on_view_cube_angle_changed(self, azimuth: float, elevation: float) -> None:
        """
        Handle angle change from ViewCube

        :param azimuth: Target azimuth angle
        :param elevation: Target elevation angle
        """
        current_azimuth = self._target_azimuth
        current_elevation = self._target_elevation

        angle_diff = abs(azimuth - current_azimuth) + abs(elevation - current_elevation)

        if angle_diff > 15:
            self._animate_camera_transition(current_azimuth, current_elevation, azimuth, elevation)
        else:
            self._apply_camera_angles(azimuth, elevation)

    def _animate_camera_transition(self, start_az: float, start_el: float, end_az: float, end_el: float) -> None:
        """
        Animate camera transition using QVariantAnimation.

        :param start_az: Starting azimuth
        :param start_el: Starting elevation
        :param end_az: Ending azimuth
        :param end_el: Ending elevation
        """
        self._target_azimuth = end_az
        self._target_elevation = end_el
        self._animation_frame_count = 0

        self._angle_animation = QVariantAnimation(self.plot_tab)
        self._angle_animation.setStartValue(0.0)
        self._angle_animation.setEndValue(1.0)
        self._angle_animation.setDuration(250)
        self._angle_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._angle_animation.valueChanged.connect(
            lambda t: self._on_animation_step(t, start_az, start_el, end_az, end_el)
        )
        self._angle_animation.finished.connect(self.on_animation_finished)

        self._angle_animation.start()

    def _on_animation_step(self, t: float, start_az: float, start_el: float, end_az: float, end_el: float) -> None:
        """
        Handle animation step
        Interpolate angles and update plot.

        :param t: Animation progress (0.0 to 1.0)
        :param start_az: Starting azimuth
        :param start_el: Starting elevation
        :param end_az: Ending azimuth
        :param end_el: Ending elevation
        """
        self._animation_frame_count += 1
        if self._animation_frame_count % 3 != 0:
            return

        current_azimuth = start_az + (end_az - start_az) * t
        current_elevation = start_el + (end_el - start_el) * t

        self._apply_camera_angles(current_azimuth, current_elevation)

    def _apply_camera_angles(self, azimuth: float, elevation: float) -> None:
        """
        Apply camera angles to 3D axes and update the UI

        :param azimuth: Azimuth angle to apply
        :param elevation: Elevation angle to apply
        """
        ax = self.plot_tab.plot_engine.current_ax
        if ax is None or not hasattr(ax, "azim"):
            return

        azimuth %= 360
        elevation = max(-90, min(90, elevation))

        ax.view_init(elev=elevation, azim=azimuth)

        self.plot_tab.view.camera_azimuth_spin.blockSignals(True)
        self.plot_tab.view.camera_azimuth_spin.setValue(azimuth)
        self.plot_tab.view.camera_azimuth_spin.blockSignals(False)

        self.plot_tab.view.camera_elevation_spin.blockSignals(True)
        self.plot_tab.view.camera_elevation_spin.setValue(elevation)
        self.plot_tab.view.camera_elevation_spin.blockSignals(False)

        self.plot_tab.canvas.draw_idle()

    def on_animation_finished(self) -> None:
        """Handle animation completeion"""
        self._apply_camera_angles(self._target_azimuth, self._target_elevation)
        self.plot_tab.canvas.draw()
        self._angle_animation = None

    def on_canvas_button_release_3d(self, event) -> None:
        if self.view_cube is None:
            return

        ax = self.plot_tab.plot_engine.current_ax
        if ax is None or not hasattr(ax, 'azim'):
            return

        azim = getattr(ax, 'azim', -60)
        elev = getattr(ax, 'elev', 30)

        self.view_cube.set_angles(azim, elev, emit_signal=False)

        self._target_azimuth = azim
        self._target_elevation = elev
