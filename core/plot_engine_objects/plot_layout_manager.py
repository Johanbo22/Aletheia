from typing import Any, Dict, List, Optional, TYPE_CHECKING, Tuple

import matplotlib.pyplot as plt
import numpy as np
from PyQt6.QtCore import QPointF
from matplotlib.figure import Figure

if TYPE_CHECKING:
    from core.plot_engine import PlotEngine

class PlotLayoutManager:
    """
    Manages the Matplotlib figures, axes geometries, layouts and 3D projections
    """

    def __init__(self, engine: "PlotEngine") -> None:
        self.engine = engine

    def create_figure(self, figsize: Tuple[float, float] = (10, 6), dpi: int = 100) -> Figure:
        """Creates a new matplotlib figure and clears the previous one"""
        if self.engine.current_figure is not None:
            plt.close(self.engine.current_figure)
        self.engine.current_figure = Figure(figsize=figsize, dpi=dpi)
        self.setup_layout(1, 1)
        return self.engine.current_figure

    def finalize_layout(self) -> None:
        """Finalize the layout"""
        if self.engine.current_figure is not None:
            self.engine.current_figure.tight_layout()

    def setup_layout(self, rows: int = 1, cols: int = 1, sharex: bool = False, sharey: bool = False,
                     custom_grid: Optional[List[Tuple[int, int, int, int]]] = None) -> None:
        """Setup subplot layout gridspec or uniform grids"""
        if self.engine.current_figure is None:
            return

        self.engine.current_figure.clear()
        self.engine._sharex = sharex
        self.engine._sharey = sharey

        if custom_grid:
            self.engine.axes_flat = []
            grid_spec = self.engine.current_figure.add_gridspec(rows, cols)
            base_ax_x = None
            base_ax_y = None

            for index, (r_start, r_end, c_start, c_end) in enumerate(custom_grid):
                subplot_kwargs: Dict[str, Any] = {}
                if sharex and base_ax_x is not None:
                    subplot_kwargs["sharex"] = base_ax_x
                if sharey and base_ax_y is not None:
                    subplot_kwargs["sharey"] = base_ax_y

                ax = self.engine.current_figure.add_subplot(grid_spec[r_start:r_end, c_start:c_end], **subplot_kwargs)
                self.engine.axes_flat.append(ax)

                if index == 0:
                    base_ax_x = ax
                    base_ax_y = ax
        else:
            axes = self.engine.current_figure.subplots(rows, cols, sharex=sharex, sharey=sharey)
            if isinstance(axes, np.ndarray):
                self.engine.axes_flat = axes.flatten().tolist()
            else:
                self.engine.axes_flat = [axes]

        if not self.engine.axes_flat:
            self.engine.current_figure.tight_layout()
            return

        self.engine.current_ax = self.engine.axes_flat[0]

        if sharex or sharey:
            for ax in self.engine.axes_flat:
                self._apply_axis_sharing_visibility(ax, sharex, sharey)

        self.engine.current_figure.tight_layout()

    def set_active_subplot(self, index: int) -> None:
        """Set the active subplot based on index"""
        if 0 <= index < len(self.engine.axes_flat):
            self.engine.current_ax = self.engine.axes_flat[index]

    def clear_current_axis(self) -> None:
        """Clear the active subplot"""
        if not self.engine.current_ax:
            return

        self._remove_axis_colorbars(self.engine.current_ax)

        self.engine.current_ax.set_axes_locator = None
        self.engine.current_ax.clear()

    def _remove_axis_colorbars(self, ax: Any) -> None:
        """
        Removes colorbars and their associated axes from a given subplot
        :param ax: The matplotlib subplot axis to remove colorbar from
        """
        if getattr(ax, "_cbar_obj", None) is not None:
            try:
                ax._cbar_obj.remove()
            except (ValueError, AttributeError, TypeError):
                self.engine.logger.debug("Failed to remove colorbar object")
            ax._cbar_obj = None

        cax = getattr(ax, "_cax", None)
        if cax is not None:
            try:
                if self.engine.current_figure and cax in self.engine.current_figure.axes:
                    self.engine.current_figure.delaxes(cax)
                elif hasattr(cax, "remove"):
                    cax.remove()
            except (ValueError, AttributeError, TypeError):
                self.engine.logger.debug("Failed to remove colorbar axis")
            ax._cax = None

    def clear_axes(self) -> None:
        """Clears the entire active subplot and handles secondary axes removal globally."""
        if self.engine.secondary_ax:
            try:
                self.engine.secondary_ax.remove()
            except (ValueError, AttributeError, TypeError):
                self.engine.logger.debug("Failed to remove secondary axis")
            self.engine.secondary_ax = None

        self.clear_current_axis()

        for coll in self.engine.current_ax.collections:
            if hasattr(coll, "colorbar") and coll.colorbar is not None:
                try:
                    coll.colorbar.remove()
                except (ValueError, AttributeError, TypeError):
                    self.engine.logger.debug("Failed to remove collection colobar")

        for img in self.engine.current_ax.images:
            if hasattr(img, "colorbar") and img.colorbar is not None:
                try:
                    img.colorbar.remove()
                except (ValueError, AttributeError, TypeError):
                    self.engine.logger.debug("Failed to remove image colorbar")

        sharex = getattr(self.engine, "_sharex", False)
        sharey = getattr(self.engine, "_sharey", False)

        if sharex or sharey:
            for ax in self.engine.axes_flat:
                self._apply_axis_sharing_visibility(ax, sharex, sharey)

    def _apply_axis_sharing_visibility(self, ax: Any, sharex: bool, sharey: bool) -> None:
        """
        Hide inner tick labels when axes are shared to avoid visual clutter

        :param ax: The matplotlib subplot axis to update
        :param sharex: Boolean indicating if X axes are shared
        :param sharey: Boolean indicating if Y axes are shared
        """
        if not hasattr(ax, "get_subplotspec"):
            return

        ss = ax.get_subplotspec()
        if ss is None:
            return

        if sharex and not ss.is_last_row():
            for label in ax.get_xticklabels(which="both"):
                label.set_visible(False)
            offset_text = ax.xaxis.get_offset_text()
            if offset_text is not None:
                offset_text.set_visible(False)
            ax.set_xlabel("")

        if sharey and not ss.is_first_row():
            for label in ax.get_yticklabels(which="both"):
                label.set_visible(False)
            offset_text = ax.yaxis.get_offset_text()
            if offset_text is not None:
                offset_text.set_visible(False)
            ax.set_ylabel("")

    def ensure_projection(self, is_3d: bool) -> None:
        """Replaces the current axis with 3D or 2D projection"""
        if not self.engine.current_ax or not self.engine.current_figure:
            return

        current_is_3d = hasattr(self.engine.current_ax, "zaxis")
        if current_is_3d == is_3d:
            return

        geometry = self.engine.current_ax.get_subplotspec()
        try:
            idx = self.engine.axes_flat.index(self.engine.current_ax)
        except ValueError:
            idx = -1

        self.engine.current_figure.delaxes(self.engine.current_ax)

        if is_3d:
            self.engine.current_ax = self.engine.current_figure.add_subplot(geometry, projection="3d")
        else:
            self.engine.current_ax = self.engine.current_figure.add_subplot(geometry)

        if idx >= 0:
            self.engine.axes_flat[idx] = self.engine.current_ax

    def get_active_axis_geometry(self) -> Optional[Tuple[int, int, int, int]]:
        """Calculate the Qt geometry for the active axis relative to the current canvas"""
        if not self.engine.current_ax or not self.engine.current_figure:
            return None

        dpr = 1.0
        canvas = self.engine.current_figure.canvas
        if canvas and hasattr(canvas, "devicePixelRatio"):
            dpr = canvas.devicePixelRatio()

        try:
            trans = self.engine.current_ax.transAxes
            p0 = trans.transform([0, 0])
            p1 = trans.transform([1, 1])

            x0, y0 = p0
            x1, y1 = p1

            fig_height_px = self.engine.current_figure.bbox.height

            px_x = x0
            px_y = fig_height_px - y1
            px_w = x1 - x0
            px_h = y1 - y0

            x = px_x / dpr
            y = px_y / dpr
            w = px_w / dpr
            h = px_h / dpr

        except (AttributeError, ValueError, TypeError) as e:
            self.engine.logger.debug(f"Falling back to bbox geometry calculation due to: {e}")
            bbox = self.engine.current_ax.get_position()
            width_in, height_in = self.engine.current_figure.get_size_inches()
            dpi = self.engine.current_figure.get_dpi()

            fig_width_px = width_in * dpi
            fig_height_px = height_in * dpi

            px_x = bbox.x0 * fig_width_px
            px_w = bbox.width * fig_width_px
            px_h = bbox.height * fig_height_px
            px_y = fig_height_px - (bbox.y1 * fig_height_px)

            x = px_x / dpr
            y = px_y / dpr
            w = px_w / dpr
            h = px_h / dpr

        if canvas:
            global_pos = canvas.mapToGlobal(QPointF(x, y)).toPoint()
            x, y = global_pos.x(), global_pos.y()

        return int(x), int(y), int(w), int(h)
