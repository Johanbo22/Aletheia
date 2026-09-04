import logging
from enum import IntEnum
from typing import Final, Optional, Set, TYPE_CHECKING, Tuple

import pandas as pd
from PyQt6.QtCore import QEasingCurve, QTimer, QVariantAnimation
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QToolTip
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseEvent
from matplotlib.collections import PathCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.widgets import SpanSelector

from src.ui.status_bar import LogLevel
from src.ui.widgets.ViewCubeWidget import ViewCubeWidget

if TYPE_CHECKING:
    from src.ui.plot_tab import PlotTab

logger: logging.Logger = logging.getLogger(__name__)

class MouseButtonCodes(IntEnum):
    """Enumeration of Matplotlib integer codes for mouse buttons"""
    LEFT = 1
    MIDDLE = 2
    RIGHT = 3

class PlotTabIndexes(IntEnum):
    """Enumeration of tab pages of the Plot tab interface"""
    APPEARANCE = 1
    CUSTOMIZATION = 4
    ANNOTATION = 5

SUPPORTED_SPAN_PLOT_TYPES: Final[frozenset[str]] = frozenset(
    {"Histogram", "Scatter", "Line", "Stem", "Stairs"}
)
IGNORED_LINE_GIDS: Final[frozenset[str]] = frozenset(
    {"regression_line", "confidence_interval", "error_bar"}
)
ANNOTATION_GID_PREFIX: Final[str] = "annotation_"
TOOLTIP_DELAY_MS: Final[int] = 40
ZOOM_BASE_SCALE: Final[float] = 1.15
CAMERA_ANIMATION_DURATION_MS: Final[int] = 250
CAMERA_ANGLE_DIFF_THRESHOLD_DEG: Final[float] = 15.0

class CanvasInteractionManager:
    """Manages canvas mouse events."""

    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab
        self.span_selector: Optional[SpanSelector] = None
        self._pan_axes: Optional[Axes] = None
        self._pan_start: Optional[Tuple[float, float]] = None
        self._pan_start_xlim: Optional[Tuple[float, float]] = None
        self._pan_start_ylim: Optional[Tuple[float, float]] = None
        self._pan_scale_x: float = 0.0
        self._pan_scale_y: float = 0.0

        self._last_hover_event: Optional[MouseEvent] = None
        self._tooltip_timer: QTimer = QTimer()
        self._tooltip_timer.setSingleShot(True)
        self._tooltip_timer.setInterval(TOOLTIP_DELAY_MS)
        self._tooltip_timer.timeout.connect(self._handle_debounced_tooltip)

        self.view_cube: Optional["ViewCubeWidget"] = None
        self._angle_animation: Optional[QVariantAnimation] = None
        self._animation_frame_count: int = 0
        self._target_azimuth: float = 0.0
        self._target_elevation: float = 0.0

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

        if self.plot_tab.current_plot_type_name not in SUPPORTED_SPAN_PLOT_TYPES:
            self.clear()
            self.span_selector = None
            return

        if self.span_selector is not None:
            if self.span_selector.ax == self.plot_tab.plot_engine.current_ax:
                return

            self.clear()
            self.span_selector = None

        self.setup_brush_and_link()

    def setup_brush_and_link(self) -> None:
        """Sets up the Matplotlib SpanSelector for supported plot types"""
        current_ax: Optional[Axes] = self.plot_tab.plot_engine.current_ax
        if current_ax is None:
            return

        def on_select(xmin: float, xmax: float) -> None:
            self._handle_brush_selection(xmin, xmax)

        self.span_selector = SpanSelector(
            current_ax,
            on_select,
            "horizontal",
            useblit=True,
            props={"alpha": 0.3, "facecolor": "#e74c3c"},
            interactive=True,
            button=MouseButtonCodes.RIGHT
        )

    def _handle_brush_selection(self, xmin: float, xmax: float) -> None:
        """Filters and highlights rows based on selection span"""
        df: pd.DataFrame = self.plot_tab.get_active_dataframe()
        x_col: str = self.plot_tab.view.x_column.currentText()

        if not x_col or x_col not in df.columns:
            return

        try:
            mask = (df[x_col] >= xmin) & (df[x_col] <= xmax)
            selected_indices: Set[int] = set(df[mask].index)
            if not selected_indices:
                return

            self.plot_tab.brush_selection_made.emit(selected_indices)
            self.plot_tab.status_bar.log(
                f"Selected {len(selected_indices)} points", LogLevel.INFO
            )
        except TypeError as err:
            logger.debug("Brush selection failed due to type mismatch: %s", err)

    def on_scroll(self, event) -> None:
        """Handles zoom in/out events via mouse scroll"""
        if not event.inaxes or event.xdata is None or event.ydata is None:
            return

        ax: Axes = event.inaxes
        cur_xlim: Tuple[float, float] = ax.get_xlim()
        cur_ylim: Tuple[float, float] = ax.get_ylim()

        x_range: float = cur_xlim[1] - cur_xlim[0]
        y_range: float = cur_ylim[1] - cur_ylim[0]

        if x_range == 0.0 or y_range == 0.0:
            return

        if event.button == "up":
            scale_factor: float = 1.0 / ZOOM_BASE_SCALE
        elif event.button == "down":
            scale_factor: float = ZOOM_BASE_SCALE
        else:
            scale_factor: float = 1.0

        new_width: float = x_range * scale_factor
        new_height: float = y_range * scale_factor

        relx: float = (cur_xlim[1] - event.xdata) / x_range
        rely: float = (cur_ylim[1] - event.ydata) / y_range

        ax.set_xlim([event.xdata - new_width * (1.0 - relx), event.xdata + new_width * (1.0 * relx)])
        ax.set_ylim([event.ydata - new_height * (1.0 - rely), event.ydata + new_height * rely])

        self.plot_tab.canvas.draw_idle()

    def on_pick(self, event) -> None:
        """Handles pick events to sync UI panels"""
        artist = event.artist

        if self.plot_tab.annotation_manager.handle_pick_event(artist, event):
            return

        ax: Optional[Axes] = self.plot_tab.plot_engine.current_ax
        if ax is None:
            return

        self.plot_tab.custom_tabs.setCurrentIndex(PlotTabIndexes.APPEARANCE)

        if artist == ax.get_title():
            self.plot_tab.view.title_input.setFocus()
        elif artist == ax.xaxis.get_label():
            self.plot_tab.view.xlabel_input.setFocus()
        elif artist == ax.yaxis.get_label():
            self.plot_tab.view.ylabel_input.setFocus()
            self.plot_tab.status_bar.log(f"Selected text element: {artist.get_text()}", LogLevel.INFO)

        elif isinstance(artist, Line2D):
            self._handle_line_pick(artist)

        elif isinstance(artist, Rectangle):
            self._handle_bar_pick(artist)

        elif isinstance(artist, PathCollection):
            self.plot_tab.custom_tabs.setCurrentIndex(PlotTabIndexes.CUSTOMIZATION)
            self.plot_tab.status_bar.log("Selected scatter points", LogLevel.INFO)

    def _handle_line_pick(self, artist: Line2D) -> None:
        """Handle picking of a line2D artist is clicked"""
        if artist.get_gid() in IGNORED_LINE_GIDS:
            return

        self.plot_tab.custom_tabs.setCurrentIndex(PlotTabIndexes.CUSTOMIZATION)
        if not self.plot_tab.view.multiline_custom_check.isChecked():
            self.plot_tab.view.multiline_custom_check.setChecked(True)

        label: str = artist.get_label()
        if not label:
            return

        index: int = self.plot_tab.view.line_selector_combo.findText(label)
        if index >= 0:
            self.plot_tab.view.line_selector_combo.setCurrentIndex(index)
            self.plot_tab.status_bar.log(f"Selected line: {label}", LogLevel.INFO)

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

    def on_mouse_press(self, event: MouseEvent) -> None:
        """Handles the event for mouse pressing for panning and annotation placement"""
        if not event.inaxes:
            return

        if event.button == MouseButtonCodes.RIGHT:
            self._handle_right_click_subplot(event.inaxes)
            return

        if event.button == MouseButtonCodes.MIDDLE:
            self._initiate_panning(event)
            return

        if event.button == MouseButtonCodes.LEFT:
            self._handle_left_click_annotation(event)

    def _handle_right_click_subplot(self, ax: Axes) -> None:
        """Activate the subplot associated with the clicked axis"""
        axes_list = self.plot_tab.plot_engine.axes_flat
        if ax not in axes_list:
            return

        idx: int = axes_list.index(ax)
        if self.plot_tab.view.active_subplot_combo.currentIndex() != idx:
            self.plot_tab.view.active_subplot_combo.setCurrentIndex(idx)
            self.plot_tab.status_bar.log(
                f"Active subplot changed to Plt {idx + 1}", LogLevel.INFO
            )

    def _initiate_panning(self, event: MouseEvent) -> None:
        """Calculate axis scale multipliers for axes panning"""
        ax: Axes = event.inaxes
        self._pan_axes = ax
        self._pan_start = (event.x, event.y)
        self._pan_start_xlim = ax.get_xlim()
        self._pan_start_ylim = ax.get_ylim()

        bbox = ax.bbox
        if bbox.width > 0.0 and bbox.height > 0.0:
            self._pan_scale_x = (self._pan_start_xlim[1] - self._pan_start_xlim[0])
            self._pan_scale_y = (self._pan_start_ylim[1] - self._pan_start_ylim[0])
        else:
            self._pan_scale_x = 0.0
            self._pan_scale_y = 0.0

    def _handle_left_click_annotation(self, event: MouseEvent) -> None:
        """Handle annotation click event"""
        if self.plot_tab.custom_tabs.currentIndex() != PlotTabIndexes.ANNOTATION:
            return

        ax: Optional[Axes] = event.inaxes
        if not ax:
            return

        for text_artist in ax.texts:
            gid = str(text_artist.get_gid() or "")
            if gid.startswith(ANNOTATION_GID_PREFIX):
                contains, _ = text_artist.contains(event)
                if contains:
                    return

        inv = ax.transAxes.inverted()
        norm_x, norm_y = inv.transform((event.x, event.y))
        bounded_x: float = max(0.0, min(1.0, float(norm_x)))
        bounded_y: float = max(0.0, min(1.0, float(norm_y)))

        self.plot_tab.view.annotation_x_spin.setValue(bounded_x)
        self.plot_tab.view.annotation_x_spin.setValue(bounded_y)

    def on_mouse_move(self, event: MouseEvent) -> None:
        """Handles middle-click mouse panning and tooltips"""
        if not event.inaxes:
            self._tooltip_timer.stop()
            if QToolTip.isVisible():
                QToolTip.hideText()
            return

        if self._pan_axes and self._pan_start and event.inaxes == self._pan_axes:
            dx_display: float = event.x - self._pan_start[0]
            dy_display: float = event.y - self._pan_start[1]

            dx_data: float = dx_display * self._pan_scale_x
            dy_data: float = dy_display * self._pan_scale_y

            assert self._pan_start_xlim is not None
            assert self._pan_start_ylim is not None

            self._pan_axes.set_xlim(
                self._pan_start_xlim[0] - dx_data, self._pan_start_xlim[1] - dx_data
            )
            self._pan_axes.set_ylim(
                self._pan_start_ylim[0] - dy_data, self._pan_start_ylim[0] - dy_data
            )
            self.plot_tab.canvas.draw_idle()
            return

        if self.plot_tab.annotation_manager.handle_mouse_move(event):
            return

        self._last_hover_event = event
        self._tooltip_timer.start()

    def _handle_debounced_tooltip(self) -> None:
        """Trigger tooltip display once moouse movement stops"""
        if self._last_hover_event is not None and self._last_hover_event.inaxes:
            self._show_data_tooltip(self._last_hover_event)

    def _show_data_tooltip(self, event: MouseEvent) -> None:
        """Shows coordinate tooltips when hovering over data points"""
        if not event.inaxes:
            return

        tooltip_text: Optional[str] = self._find_line_hit(event)
        if tooltip_text is None:
            tooltip_text = self._find_collection_hit(event)

        if tooltip_text:
            if QToolTip.text() != tooltip_text:
                QToolTip.showText(QCursor.pos(), tooltip_text, self.plot_tab.canvas)
        elif QToolTip.isVisible():
            QToolTip.hideText()

    def _find_line_hit(self, event: MouseEvent) -> Optional[str]:
        """Perform hit detection against Line2D elements"""
        for line in event.inaxes.get_lines():
            contains, index_dict = line.contains(event)
            indices = index_dict.get("ind", [])
            if not contains or len(indices) == 0:
                continue

            point_index: int = indices[0]
            x_value = line.get_xdata()[point_index]
            y_value = line.get_ydata()[point_index]
            return f"X: {x_value}\nY: {y_value}"
        return None

    def _find_collection_hit(self, event: MouseEvent) -> Optional[str]:
        """Perform hit detection against PathCollection elements"""
        for collection in event.inaxes.collections:
            contains, index_dict = collection.contains(event)
            indices = index_dict.get("ind", [])
            if not contains or len(indices) == 0:
                continue

            point_index = indices[0]
            try:
                offsets = collection.get_offsets()
                target_idx: int = point_index if len(offsets) > point_index else 0
                x_value, y_value = offsets[target_idx][0], offsets[target_idx][1]
                return f"X: {x_value}\nY: {y_value}"
            except (IndexError, TypeError) as err:
                logger.debug("Failed extracting collection offsets: %s", err)
        return None

    def on_mouse_release(self, event: MouseEvent) -> None:
        """Handles mouse release event to stop panning or dragging"""
        if event.button == MouseButtonCodes.MIDDLE:
            self._pan_axes = None
            self._pan_start = None
            self._pan_start_xlim = None
            self._pan_start_ylim = None
            self._pan_scale_x = 0.0
            self._pan_scale_y = 0.0
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
        if self._angle_animation is not None:
            self._angle_animation.stop()

        self._target_azimuth = end_az
        self._target_elevation = end_el
        self._animation_frame_count = 0

        self._angle_animation = QVariantAnimation(self.plot_tab)
        self._angle_animation.setStartValue(0.0)
        self._angle_animation.setEndValue(1.0)
        self._angle_animation.setDuration(CAMERA_ANIMATION_DURATION_MS)
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
        self.plot_tab.canvas.draw_idle()
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