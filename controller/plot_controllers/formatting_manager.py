from typing import Any, Dict, Optional, TYPE_CHECKING

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from controller.plot_controllers.tick_formatting_manager import TickFormattingManager
from core.global_signals import ToastLevel, global_signals
from ui.status_bar import LogLevel

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab
    import pandas as pd

class PlotFormattingManager:
    """Manages all matplotlib axis, figure, and styling formatting for the PlotTab."""

    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab
        self.tick_manager = TickFormattingManager(plot_tab)

    def build_general_kwargs(self, plot_type: str, x_col: str, y_cols: list[str], hue: Optional[str]) -> Dict[str, Any]:
        """Build the general plotting kwargs."""
        plots_supporting_hue = ["Scatter", "Line", "Bar", "Violin", "2D Density", "Box", "Count Plot", "Histogram",
                                "3D Scatter", "3D Line"]
        y_label_text = self.determine_y_label(plot_type, y_cols)

        general_kwargs = {
            "title" : self.plot_tab.view.title_input.text() or plot_type,
            "xlabel": self.plot_tab.view.xlabel_input.text() or x_col,
            "ylabel": self.plot_tab.view.ylabel_input.text() or y_label_text,
            "legend": self.plot_tab.view.legend_check.isChecked()
        }

        if plot_type in ["3D Scatter", "3D Line", "3D Surface"]:
            z_col_text = self.plot_tab.view.z_column.currentText()
            general_kwargs["z_column"] = z_col_text
            general_kwargs["zlabel"] = self.plot_tab.view.zlabel_input.text() or z_col_text
            general_kwargs["elevation"] = self.plot_tab.view.camera_elevation_spin.value()
            general_kwargs["azimuth"] = self.plot_tab.view.camera_azimuth_spin.value()

        if self.plot_tab.view.secondary_y_check.isChecked() and self.plot_tab.view.secondary_y_check.isEnabled():
            general_kwargs["secondary_y"] = self.plot_tab.view.secondary_y_column.currentText()
            general_kwargs["secondary_plot_type"] = self.plot_tab.view.secondary_plot_type_combo.currentText()

        cmap = self.plot_tab.view.palette_combo.currentText()
        if cmap and cmap != "None":
            if plot_type in ["Bar", "Box", "Violin", "Count Plot"]:
                general_kwargs["palette"] = cmap
            else:
                general_kwargs["cmap"] = cmap

        if hue and plot_type in plots_supporting_hue:
            general_kwargs["hue"] = hue

        return general_kwargs

    @staticmethod
    def determine_y_label(plot_type: str, y_cols: list[str]) -> str:
        """Determine the ylabel based on the input plot type"""
        plots_gridded = ["Image Show (imshow)", "pcolormesh", "Contour", "Contourf"]
        plots_vector = ["Barbs", "Quiver", "Streamplot"]
        plots_triangulation = ["Tricontour", "Tricontourf", "Tripcolor", "Triplot"]
        plots_no_x = ["Box", "Histogram", "KDE", "Heatmap", "Pie", "ECDF", "Eventplot", "GeoSpatial"]

        if plot_type in plots_gridded or plot_type in plots_vector or plot_type in plots_triangulation:
            return y_cols[0] if y_cols else "Value"
        elif plot_type in plots_no_x:
            return y_cols[0] if y_cols else "Value"
        elif len(y_cols) == 1:
            return y_cols[0]
        else:
            return str(y_cols)

    def build_plot_specific_kwargs(self, plot_type: str) -> Dict[str, Any]:
        """Build plot specific kwargs."""
        if plot_type == "GeoSpatial":
            return self.build_geospatial_kwargs()
        return {}

    def build_geospatial_kwargs(self) -> Dict[str, Any]:
        """Builds kwargs specific to the Geospatial plotting routine."""
        scheme_text = self.plot_tab.view.geo_scheme_combo.currentText()
        hatch_text = self.plot_tab.view.geo_hatch_combo.currentText()
        target_crs_input = getattr(self.plot_tab, "geo_target_crs_input", None)
        target_crs = target_crs_input.text() if target_crs_input else None

        basemap_check = getattr(self.plot_tab, "geo_basemap_check", None)
        add_basemap = basemap_check.isChecked() if basemap_check else False

        basemap_combo = getattr(self.plot_tab, "geo_basemap_style_combo", None)
        basemap_source = basemap_combo.currentText() if basemap_combo else "OpenStreetMap"

        kwargs = {
            "scheme"        : scheme_text if scheme_text != "None" else None,
            "k"             : self.plot_tab.view.geo_k_spin.value(),
            "cmap"          : self.plot_tab.view.palette_combo.currentText(),
            "legend"        : self.plot_tab.view.geo_legend_check.isChecked(),
            "legend_kwds"   : {
                "loc"        : "best",
                "orientation": self.plot_tab.view.geo_legend_loc_combo.currentText()
            },
            "use_divider"   : self.plot_tab.view.geo_use_divider_check.isChecked(),
            "cax_enabled"   : self.plot_tab.view.geo_cax_check.isChecked(),
            "axis_off"      : self.plot_tab.view.geo_axis_off_check.isChecked(),
            "missing_kwds"  : {
                "color": self.plot_tab.geo_missing_color,
                "label": self.plot_tab.view.geo_missing_label_input.text(),
                "hatch": hatch_text if hatch_text != "None" else None
            },
            "edgecolor"     : self.plot_tab.geo_edge_color,
            "linewidth"     : self.plot_tab.view.geo_linewidth_spin.value(),
            "target_crs"    : target_crs,
            "add_basemap"   : add_basemap,
            "basemap_source": basemap_source
        }
        if self.plot_tab.view.geo_boundary_check.isChecked():
            kwargs["facecolor"] = "none"
        return kwargs

    def setup_plot_figure(self, clear: bool = True) -> None:
        """Sets up the plot figure with current settings"""
        if clear:
            self.plot_tab.plot_engine.clear_current_axis()

        target_width_inch = self.plot_tab.view.width_spin.value()
        target_height_inch = self.plot_tab.view.height_spin.value()

        canvas_width = self.plot_tab.canvas.width()
        canvas_height = self.plot_tab.canvas.height()

        if canvas_width <= 0:
            canvas_width = 800
        if canvas_height <= 0:
            canvas_height = 600

        dpi_w = canvas_width / target_width_inch
        dpi_h = canvas_height / target_height_inch

        calculated_dpi = max(min(dpi_w, dpi_h), 10)

        self.plot_tab.plot_engine.current_figure.set_size_inches(target_width_inch, target_height_inch)
        self.plot_tab.plot_engine.current_figure.set_dpi(calculated_dpi)
        self.plot_tab.plot_engine.current_figure.set_facecolor(self.plot_tab.bg_color)

    def apply_plot_style(self) -> None:
        """Apply global plotting styles"""
        try:
            plt.style.use(self.plot_tab.view.style_combo.currentText())
            self.plot_tab.plot_engine.current_figure.set_facecolor(self.plot_tab.bg_color)
            self.plot_tab.plot_engine.current_ax.set_facecolor(self.plot_tab.face_color)
        except Exception as error:
            self.plot_tab.status_bar.log(f"Could not apply plotting style. {str(error)}", LogLevel.WARNING)
            self.plot_tab.plot_engine.current_ax.set_facecolor(self.plot_tab.face_color)

    def set_axis_limit_and_scales(self) -> None:
        """Set axis limits and scales"""
        if not self.plot_tab.view.x_auto_check.isChecked():
            self.plot_tab.plot_engine.current_ax.set_xlim(
                self.plot_tab.view.x_min_spin.value(), self.plot_tab.view.x_max_spin.value()
            )
        if not self.plot_tab.view.y_auto_check.isChecked():
            self.plot_tab.plot_engine.current_ax.set_ylim(
                self.plot_tab.view.y_min_spin.value(), self.plot_tab.view.y_max_spin.value()
            )

        if hasattr(self.plot_tab.plot_engine.current_ax, "zaxis") and not self.plot_tab.view.z_auto_check.isChecked():
            self.plot_tab.plot_engine.current_ax.set_zlim(
                self.plot_tab.view.z_min_spin.value(), self.plot_tab.view.z_max_spin.value()
            )

        target_x_scale = self.plot_tab.view.x_scale_combo.currentText()
        if self.plot_tab.plot_engine.current_ax.get_xscale() != target_x_scale:
            self.plot_tab.plot_engine.current_ax.set_xscale(target_x_scale)

        target_y_scale = self.plot_tab.view.y_scale_combo.currentText()
        if self.plot_tab.plot_engine.current_ax.get_yscale() != target_y_scale:
            self.plot_tab.plot_engine.current_ax.set_yscale(target_y_scale)

        if hasattr(self.plot_tab.plot_engine.current_ax, "zaxis"):
            target_z_scale = self.plot_tab.view.z_scale_combo.currentText()
            try:
                self.plot_tab.plot_engine.current_ax.set_zscale(target_z_scale)
            except ValueError as error:
                self.plot_tab.status_bar.log(f"Unsupported Z-Scale '{target_z_scale}': {error}", LogLevel.WARNING)

    def apply_plot_formatting(self, progress_dialog: Any, x_col: str, y_cols: list[str],
                              general_kwargs: dict, active_df: 'pd.DataFrame') -> None:
        """Master method to apply all formatting steps."""
        axes_flipped = self.plot_tab.view.flip_axes_check.isChecked()
        font_family = self.plot_tab.view.font_family_combo.currentText()

        try:
            allowed_locators = ["AutoLocator", "MaxNLocator", "LinearLocator", "MultipleLocator"]
            x_locator_name = type(self.plot_tab.plot_engine.current_ax.xaxis.get_major_locator()).__name__
            if x_locator_name in allowed_locators:
                self.plot_tab.plot_engine.current_ax.xaxis.set_major_locator(
                    MaxNLocator(nbins=self.plot_tab.view.x_max_ticks_spin.value()))

            y_locator_name = type(self.plot_tab.plot_engine.current_ax.yaxis.get_major_locator()).__name__
            if y_locator_name in allowed_locators:
                self.plot_tab.plot_engine.current_ax.yaxis.set_major_locator(
                    MaxNLocator(nbins=self.plot_tab.view.y_max_ticks_spin.value()))

            if hasattr(self.plot_tab.plot_engine.current_ax, "zaxis"):
                z_locator_name = type(self.plot_tab.plot_engine.current_ax.zaxis.get_major_locator()).__name__
                if z_locator_name in allowed_locators:
                    self.plot_tab.plot_engine.current_ax.zaxis.set_major_locator(
                        MaxNLocator(nbins=self.plot_tab.view.z_max_ticks_spin.value()))
        except Exception as e:
            self.plot_tab.status_bar.log(f"Could not apply tick formatting: {str(e)}", LogLevel.WARNING)

        if progress_dialog:
            self.plot_tab._update_progress(progress_dialog, 70, "Applying formatting")

        if not axes_flipped:
            self.apply_plot_appearance(x_col, y_cols, font_family, general_kwargs)

        if progress_dialog:
            self.plot_tab._update_progress(progress_dialog, 72, "Applying annotations...")
        self.plot_tab._apply_annotations(active_df, x_col, y_cols)

        if progress_dialog:
            self.plot_tab._update_progress(progress_dialog, 75, "Applying customizations")
        self.apply_plot_customizations()

        if progress_dialog:
            self.plot_tab._update_progress(progress_dialog, 80, "Adding legend and gridlines")
        self.apply_legend_and_grid(general_kwargs, font_family)
        self.apply_spines_customization()

        self.tick_manager.apply_tick_customization()
        self.apply_textbox()

        if progress_dialog:
            self.plot_tab._update_progress(progress_dialog, 95, "Adding data table")
        self.plot_tab.table_manager.apply_table()

    def apply_plot_appearance(self, x_col: str, y_cols: list[str], font_family: str, general_kwargs: dict) -> None:
        """Apply title, fonts and label settings"""
        for label in self.plot_tab.plot_engine.current_ax.get_xticklabels():
            label.set_fontfamily(font_family)
        for label in self.plot_tab.plot_engine.current_ax.get_yticklabels():
            label.set_fontfamily(font_family)

        if self.plot_tab.view.title_check.isChecked():
            self.plot_tab.plot_engine.current_ax.set_title("", loc="left")
            self.plot_tab.plot_engine.current_ax.set_title("", loc="center")
            self.plot_tab.plot_engine.current_ax.set_title("", loc="right")

            title_text = self.plot_tab.view.title_input.text() or general_kwargs.get("title", "Plot")
            self.plot_tab.plot_engine.current_ax.set_title(
                title_text,
                fontsize=self.plot_tab.view.title_size_spin.value(),
                fontweight=self.plot_tab.view.title_weight_combo.currentText(),
                fontfamily=font_family,
                loc=self.plot_tab.view.title_position_combo.currentText()
            )
        else:
            self.plot_tab.plot_engine.current_ax.set_title("")
            self.plot_tab.plot_engine.current_ax.set_title("", loc='left')
            self.plot_tab.plot_engine.current_ax.set_title("", loc='right')

        if self.plot_tab.view.xlabel_check.isChecked():
            xlabel_text = self.plot_tab.view.xlabel_input.text() or general_kwargs.get("xlabel", "")
            self.plot_tab.plot_engine.current_ax.set_xlabel(
                xlabel_text,
                fontsize=self.plot_tab.view.xlabel_size_spin.value(),
                fontweight=self.plot_tab.view.xlabel_weight_combo.currentText(),
                fontfamily=font_family
            )
        else:
            self.plot_tab.plot_engine.current_ax.set_xlabel("")

        if self.plot_tab.view.ylabel_check.isChecked():
            ylabel_text = self.plot_tab.view.ylabel_input.text() or general_kwargs.get("ylabel", "")
            self.plot_tab.plot_engine.current_ax.set_ylabel(
                ylabel_text,
                fontsize=self.plot_tab.view.ylabel_size_spin.value(),
                fontweight=self.plot_tab.view.ylabel_weight_combo.currentText(),
                fontfamily=font_family
            )
        else:
            self.plot_tab.plot_engine.current_ax.set_ylabel("")

        if hasattr(self.plot_tab.plot_engine.current_ax, "zaxis"):
            if self.plot_tab.view.zlabel_check.isChecked():
                zlabel_text = self.plot_tab.view.zlabel_input.text() or general_kwargs.get("zlabel", "")
                self.plot_tab.plot_engine.current_ax.set_zlabel(
                    zlabel_text,
                    fontsize=self.plot_tab.view.zlabel_size.value(),
                    fontweight=self.plot_tab.view.zlabel_weight.currentText(),
                    fontfamily=font_family
                )
            else:
                self.plot_tab.plot_engine.current_ax.set_zlabel("")

            elev = general_kwargs.get("elevation")
            azim = general_kwargs.get("azimuth")
            if elev is not None and azim is not None:
                self.plot_tab.plot_engine.current_ax.view_init(elev=elev, azim=azim)

    def apply_plot_customizations(self) -> None:
        """Apply customizations to lines, markers, bars etc."""
        alpha = self.plot_tab.view.alpha_slider.value() / 100.0

        self._apply_line_customizations(alpha)
        self._apply_collection_customizations(alpha)
        self._apply_bar_customizations(alpha)
        self._apply_error_bar_customizations()

    def _apply_error_bar_customizations(self) -> None:
        """Applies styling to error bars in the current axes"""
        if not self.plot_tab.plot_engine.current_ax:
            return

        error_bar_color = getattr(self.plot_tab, "error_bar_color", "black")
        error_bar_linewidth = self.plot_tab.view.error_bar_linewidth_spin.value()
        error_bar_alpha = self.plot_tab.view.error_bar_alpha_slider.value() / 100.0
        error_bar_zorder = self.plot_tab.view.error_bar_zorder_spin.value()

        for line in self.plot_tab.plot_engine.current_ax.get_lines():
            if line.get_gid() == "error_bar":
                line.set_color(error_bar_color)
                line.set_linewidth(error_bar_linewidth)
                line.set_alpha(error_bar_alpha)
                line.set_zorder(error_bar_zorder)

        for collection in self.plot_tab.plot_engine.current_ax.collections:
            if collection.get_gid() == "error_bar":
                collection.set_color(error_bar_color)
                collection.set_linewidth(error_bar_linewidth)
                collection.set_alpha(error_bar_alpha)
                collection.set_zorder(error_bar_zorder)

    def _apply_line_customizations(self, alpha: float) -> None:
        """Applies style formatting to all line objects in the current axes"""
        if self.plot_tab.view.multiline_custom_check.isChecked():
            self._apply_individual_lines(alpha)
        else:
            self._apply_global_lines(alpha)

    def _apply_global_lines(self, alpha: float) -> None:
        """Applies default global line style to all non-special lines"""
        for line in self.plot_tab.plot_engine.current_ax.get_lines():
            gid = line.get_gid()
            if gid and (gid in ["regression_line", "confidence_interval", "error_bar"] or str(gid).startswith(
                    "ref_line") or str(gid).startswith("ref_span")):
                continue
            self._apply_default_line_style(line, alpha)

    def _apply_individual_lines(self, alpha: float) -> None:
        """Applies custom line styles per line when multi-line is enabled"""
        lines = []
        for line in self.plot_tab.plot_engine.current_ax.get_lines():
            gid = line.get_gid()
            if gid and (gid in ["regression_line", "confidence_interval", "error_bar"] or str(gid).startswith(
                    "ref_line") or str(gid).startswith("ref_span")):
                continue
            lines.append(line)

        for i, line in enumerate(lines):
            line_name = line.get_label() if not line.get_label().startswith("_") else f"Line {i + 1}"
            if line_name in self.plot_tab.line_customizations:
                custom = self.plot_tab.line_customizations[line_name]
                if "linestyle" in custom and custom["linestyle"] != "None":
                    line.set_linestyle(custom["linestyle"])
                if "linewidth" in custom:
                    line.set_linewidth(custom["linewidth"])
                if "color" in custom and custom["color"]:
                    line.set_color(custom["color"])
                if "marker" in custom and custom["marker"] != "None":
                    line.set_marker(custom["marker"])
                    if "markersize" in custom:
                        line.set_markersize(custom["markersize"])
                    if "markerfacecolor" in custom and custom["markerfacecolor"]:
                        line.set_markerfacecolor(custom["markerfacecolor"])
                    if "markeredgecolor" in custom and custom["markeredgecolor"]:
                        line.set_markeredgecolor(custom["markeredgecolor"])
                    if "markeredgewidth" in custom:
                        line.set_markeredgewidth(custom["markeredgewidth"])
                if "alpha" in custom:
                    line.set_alpha(custom["alpha"])
            else:
                self._apply_default_line_style(line, alpha)

    def _apply_default_line_style(self, line: Any, alpha: float) -> None:
        """Helper to apply the globally set line and marker styling to a given line"""
        linestyle_map = {"Solid": "-", "Dashed": "--", "Dash-dot": "-.", "Dotted": ":"}
        linestyle_val = linestyle_map.get(self.plot_tab.view.linestyle_combo.currentText(), "-")
        linewidth = self.plot_tab.view.linewidth_spin.value()
        marker = self.plot_tab.view.marker_combo.currentText()
        marker_val = "None" if marker == "None" else marker

        if linestyle_val != "None":
            line.set_linestyle(linestyle_val)
            line.set_linewidth(linewidth)
        if self.plot_tab.line_color:
            line.set_color(self.plot_tab.line_color)

        if marker_val != "None":
            line.set_marker(marker_val)
            line.set_markersize(self.plot_tab.view.marker_size_spin.value())
            if self.plot_tab.marker_color:
                line.set_markerfacecolor(self.plot_tab.marker_color)
            if self.plot_tab.marker_edge_color:
                line.set_markeredgecolor(self.plot_tab.marker_edge_color)
                line.set_markeredgewidth(self.plot_tab.view.marker_edge_width_spin.value())
        line.set_alpha(alpha)

    def _apply_collection_customizations(self, alpha: float) -> None:
        """Applies styling to collection objects like scatter plots"""
        for collection in self.plot_tab.plot_engine.current_ax.collections:
            gid = collection.get_gid()
            if gid and (gid in ["confidence_interval", "error_bar"] or str(gid).startswith("ref_line") or str(
                    gid).startswith("ref_span")):
                continue
            collection.set_alpha(alpha)
            if self.plot_tab.marker_color:
                collection.set_facecolor(self.plot_tab.marker_color)
            if self.plot_tab.marker_edge_color:
                collection.set_edgecolor(self.plot_tab.marker_edge_color)

    def _apply_bar_customizations(self, alpha: float) -> None:
        """Applies styling to bar plots based on user settings"""
        if self.plot_tab.view.multibar_custom_check.isChecked():
            self._apply_individual_bars(alpha)
        else:
            self._apply_global_bars(alpha)

    def _apply_global_bars(self, alpha: float) -> None:
        """Applies default bar styles globally to all patches"""
        for patch in self.plot_tab.plot_engine.current_ax.patches:
            gid = patch.get_gid()
            if gid and (str(gid).startswith("ref_line") or str(gid).startswith("ref_span")):
                continue
            self._apply_default_bar_style(patch, alpha)

    def _apply_individual_bars(self, alpha: float) -> None:
        """Applies custom bar styles per bar series."""
        ax = self.plot_tab.plot_engine.current_ax
        if not (ax and ax.containers):
            return

        for i, container in enumerate(ax.containers):
            if not hasattr(container, "patches") or not container.patches:
                continue

            label = container.get_label()
            if not label or label.startswith("_"):
                handles, labels = ax.get_legend_handles_labels()
                label = labels[i] if i < len(labels) else f"Bar Series {i + 1}"

            if label in self.plot_tab.bar_customizations:
                custom = self.plot_tab.bar_customizations[label]
                for patch in container.patches:
                    if "facecolor" in custom and custom["facecolor"]:
                        patch.set_facecolor(custom["facecolor"])
                    if "edgecolor" in custom and custom["edgecolor"]:
                        patch.set_edgecolor(custom["edgecolor"])
                    if "linewidth" in custom:
                        patch.set_linewidth(custom["linewidth"])
                    patch.set_alpha(custom.get("alpha", alpha))
            else:
                for patch in container.patches:
                    self._apply_default_bar_style(patch, alpha)

    def _apply_default_bar_style(self, patch: Any, alpha: float) -> None:
        """Helper to apply the globally set bar styling to a given patch."""
        patch.set_alpha(alpha)
        if self.plot_tab.bar_color:
            patch.set_facecolor(self.plot_tab.bar_color)
        if self.plot_tab.bar_edge_color:
            patch.set_edgecolor(self.plot_tab.bar_edge_color)
        patch.set_linewidth(self.plot_tab.view.bar_edge_width_spin.value())

    def apply_legend_and_grid(self, general_kwargs: dict, font_family: str) -> None:
        """Apply legend and gridlines."""
        if general_kwargs.get("legend", True):
            self.apply_legend(font_family)
        elif self.plot_tab.plot_engine.current_ax.get_legend():
            self.plot_tab.plot_engine.current_ax.get_legend().set_visible(False)

        if self.plot_tab.view.grid_check.isChecked():
            self.apply_gridlines_customizations()
        else:
            self.plot_tab.plot_engine.current_ax.grid(False)

    def apply_legend(self, font_family: str) -> None:
        """Configure the legend."""
        if not self.plot_tab.view.legend_check.isChecked():
            if self.plot_tab.plot_engine.current_ax.get_legend():
                self.plot_tab.plot_engine.current_ax.get_legend().set_visible(False)
            return

        handles, labels = self.plot_tab.plot_engine.current_ax.get_legend_handles_labels()
        if self.plot_tab.plot_engine.secondary_ax:
            handles2, labels2 = self.plot_tab.plot_engine.secondary_ax.get_legend_handles_labels()
            handles.extend(handles2)
            labels.extend(labels2)

        if not handles:
            return

        custom_labels_str = self.plot_tab.view.legend_labels_input.text().strip()
        if custom_labels_str:
            custom_labels = [label.strip() for label in custom_labels_str.split(";")]
            for i in range(min(len(labels), len(custom_labels))):
                if custom_labels[i]:
                    labels[i] = custom_labels[i]

        legend_kwargs = {
            "loc"           : self.plot_tab.view.legend_loc_combo.currentText(),
            "fontsize"      : self.plot_tab.view.legend_size_spin.value(),
            "title_fontsize": self.plot_tab.view.legend_title_size_spin.value(),
            "ncol"          : self.plot_tab.view.legend_columns_spin.value(),
            "columnspacing" : self.plot_tab.view.legend_colspace_spin.value(),
            "frameon"       : self.plot_tab.view.legend_frame_check.isChecked(),
            "fancybox"      : self.plot_tab.view.legend_fancybox_check.isChecked(),
            "shadow"        : self.plot_tab.view.legend_shadow_check.isChecked(),
            "framealpha"    : self.plot_tab.view.legend_alpha_slider.value() / 100.0,
            "facecolor"     : self.plot_tab.legend_bg_color,
            "edgecolor"     : self.plot_tab.legend_edge_color
        }

        try:
            legend = self.plot_tab.plot_engine.current_ax.legend(handles, labels, **legend_kwargs)
            if legend and legend.get_frame():
                legend.get_frame().set_linewidth(self.plot_tab.view.legend_edge_width_spin.value())
            if self.plot_tab.view.legend_title_input.text().strip():
                legend.set_title(self.plot_tab.view.legend_title_input.text().strip())
            for text in legend.get_texts():
                text.set_fontfamily(font_family)
            if legend.get_title():
                legend.get_title().set_fontfamily(font_family)
        except (TypeError, ValueError) as e:
            self.plot_tab.status_bar.log(f"Failed to apply legend: {e}", LogLevel.WARNING)

    def apply_gridlines_customizations(self) -> None:
        """Apply gridlines customizations."""
        self.plot_tab.plot_engine.current_ax.grid(False, which="both", axis="both")

        if not self.plot_tab.view.grid_check.isChecked():
            return

        grid_style_map = {"Solid (-)": "-", "Dashed (--)": "--", "Dash-dot (-.)": "-.", "Dotted (:)": ":"}

        if self.plot_tab.view.independent_grid_check.isChecked():
            if self.plot_tab.view.x_minor_grid_check.isChecked() or self.plot_tab.view.y_minor_grid_check.isChecked():
                self.plot_tab.plot_engine.current_ax.minorticks_on()
            else:
                self.plot_tab.plot_engine.current_ax.minorticks_off()

            if self.plot_tab.view.x_major_grid_check.isChecked():
                style = grid_style_map.get(self.plot_tab.view.x_major_grid_style_combo.currentText(), "-")
                self.plot_tab.plot_engine.current_ax.grid(
                    visible=True, which="major", axis="x",
                    linestyle=style, linewidth=self.plot_tab.view.x_major_grid_linewidth_spin.value(),
                    color=self.plot_tab.x_major_grid_color,
                    alpha=self.plot_tab.view.x_major_grid_alpha_slider.value() / 100.0
                )

            if self.plot_tab.view.x_minor_grid_check.isChecked():
                style = grid_style_map.get(self.plot_tab.view.x_minor_grid_style_combo.currentText(), ":")
                self.plot_tab.plot_engine.current_ax.grid(
                    visible=True, which="minor", axis="x",
                    linestyle=style, linewidth=self.plot_tab.view.x_minor_grid_linewidth_spin.value(),
                    color=self.plot_tab.x_minor_grid_color,
                    alpha=self.plot_tab.view.x_minor_grid_alpha_slider.value() / 100.0
                )

            if self.plot_tab.view.y_major_grid_check.isChecked():
                style = grid_style_map.get(self.plot_tab.view.y_major_grid_style_combo.currentText(), "-")
                self.plot_tab.plot_engine.current_ax.grid(
                    visible=True, which="major", axis="y",
                    linestyle=style, linewidth=self.plot_tab.view.y_major_grid_linewidth_spin.value(),
                    color=self.plot_tab.y_major_grid_color,
                    alpha=self.plot_tab.view.y_major_grid_alpha_slider.value() / 100.0
                )

            if self.plot_tab.view.y_minor_grid_check.isChecked():
                style = grid_style_map.get(self.plot_tab.view.y_minor_grid_style_combo.currentText(), ":")
                self.plot_tab.plot_engine.current_ax.grid(
                    visible=True, which="minor", axis="y",
                    linestyle=style, linewidth=self.plot_tab.view.y_minor_grid_linewidth_spin.value(),
                    color=self.plot_tab.y_minor_grid_color,
                    alpha=self.plot_tab.view.y_minor_grid_alpha_slider.value() / 100.0
                )
        else:
            which_type = self.plot_tab.view.grid_which_type_combo.currentText()
            axis = self.plot_tab.view.grid_axis_combo.currentText()

            if which_type in ["minor", "both"]:
                self.plot_tab.plot_engine.current_ax.minorticks_on()
            else:
                self.plot_tab.plot_engine.current_ax.minorticks_off()

            style = grid_style_map.get(self.plot_tab.view.legend_tab.global_grid_style_combo.currentText(), "-")
            width = self.plot_tab.view.legend_tab.global_grid_linewidth_spin.value()

            self.plot_tab.plot_engine.current_ax.grid(
                visible=True, which=which_type, axis=axis,
                linestyle=style, linewidth=width,
                color=self.plot_tab.global_grid_color, alpha=self.plot_tab.view.global_grid_alpha_slider.value() / 100.0
            )

    def apply_textbox(self) -> None:
        """Apply custom floating textbox."""
        if not self.plot_tab.plot_engine.current_ax:
            return

        for text_artist in list(self.plot_tab.plot_engine.current_ax.texts):
            if text_artist.get_gid() == "custom_textbox":
                try:
                    text_artist.remove()
                except Exception as error:
                    self.plot_tab.status_bar.log(f"Failed to remove previous textbox: {str(error)}", LogLevel.WARNING)
                    global_signals.request_toast(
                        "Textbox Warning", "Failed to remove previous textbox", ToastLevel.WARNING
                    )

        if self.plot_tab.view.textbox_enable_check.isChecked():
            textbox_text = self.plot_tab.view.textbox_content.text().strip()
            if textbox_text:
                style_map = {
                    "Rounded"    : "round", "Square": "square",
                    "round,pad=1": "round,pad=1", "round4,pad=0.5": "round4,pad=0.5"
                }
                style = style_map.get(self.plot_tab.view.textbox_style_combo.currentText(), "round")

                position_coords = {
                    "upper left" : (0.05, 0.95), "upper center": (0.5, 0.95), "upper right": (0.95, 0.95),
                    "center left": (0.05, 0.5), "center": (0.5, 0.5), "center right": (0.95, 0.5),
                    "lower left" : (0.05, 0.05), "lower center": (0.5, 0.05), "lower right": (0.95, 0.05)
                }

                position_name = self.plot_tab.view.textbox_position_combo.currentText()
                x, y = position_coords.get(position_name, (0.5, 0.5))

                ha_map = {"upper left"  : "left", "center left": "left", "lower left": "left", "upper center": "center",
                          "center"      : "center", "lower center": "center", "upper right": "right",
                          "center right": "right",
                          "lower right" : "right"}
                va_map = {"upper left"  : "top", "upper center": "top", "upper right": "top", "center left": "center",
                          "center"      : "center", "center right": "center", "lower left": "bottom",
                          "lower center": "bottom", "lower right": "bottom"}

                self.plot_tab.plot_engine.current_ax.text(
                    x, y, textbox_text, transform=self.plot_tab.plot_engine.current_ax.transAxes,
                    fontsize=11, verticalalignment=va_map.get(position_name, "center"),
                    horizontalalignment=ha_map.get(position_name, "center"),
                    bbox=dict(boxstyle=style, facecolor=self.plot_tab.textbox_bg_color, alpha=0.8, pad=1),
                    gid="custom_textbox"
                )

    def apply_spines_customization(self) -> None:
        """Apply spines customization."""
        if not self.plot_tab.plot_engine.current_ax:
            return

        if hasattr(self.plot_tab.plot_engine.current_ax, "zaxis"):
            return

        try:
            is_individual = self.plot_tab.view.individual_spines_check.isChecked()

            global_width = self.plot_tab.view.global_spine_width_spin.value()
            global_color = getattr(self.plot_tab, "global_spine_color", "black")

            spine_map = [
                ("top", self.plot_tab.view.top_spine_visible_check, self.plot_tab.view.top_spine_width_spin,
                 "top_spine_color"),
                ("bottom", self.plot_tab.view.bottom_spine_visible_check, self.plot_tab.view.bottom_spine_width_spin,
                 "bottom_spine_color"),
                ("left", self.plot_tab.view.left_spine_visible_check, self.plot_tab.view.left_spine_width_spin,
                 "left_spine_color"),
                ("right", self.plot_tab.view.right_spine_visible_check, self.plot_tab.view.right_spine_width_spin,
                 "right_spine_color")
            ]

            axes_to_style = [self.plot_tab.plot_engine.current_ax]
            if getattr(self.plot_tab.plot_engine, "secondary_ax", None):
                axes_to_style.append(self.plot_tab.plot_engine.secondary_ax)

            for ax in axes_to_style:
                if hasattr(ax, "zaxis"):
                    continue

                spines = ax.spines
                for key, vis_check, width_spin, color_attr in spine_map:
                    if key not in spines:
                        continue

                    if vis_check.isChecked():
                        spines[key].set_visible(True)
                        spines[key].set_linewidth(width_spin.value() if is_individual else global_width)
                        spines[key].set_edgecolor(
                            getattr(self.plot_tab, color_attr, "black") if is_individual else global_color)
                    else:
                        spines[key].set_visible(False)
                        tick_kwargs = {key: False, f"label{key}": False}
                        ax.tick_params(axis="both", which="both", **tick_kwargs)
        except (AttributeError, KeyError) as e:
            self.plot_tab.status_bar.log(f"Failed to apply spine customization: {str(e)}", LogLevel.ERROR)
