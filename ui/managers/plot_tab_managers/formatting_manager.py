import traceback
from typing import TYPE_CHECKING, Dict, Any, Optional

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator, FuncFormatter, AutoMinorLocator, NullLocator
if TYPE_CHECKING:
    from ui.plot_tab import PlotTab
    import pandas as pd

class PlotFormattingManager:
    """Manages all matplotlib axis, figure, and styling formatting for the PlotTab."""

    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab

    def build_general_kwargs(self, plot_type: str, x_col: str, y_cols: list[str], hue: Optional[str]) -> Dict[str, Any]:
        """Build the general plotting kwargs."""
        plots_supporting_hue = ["Scatter", "Line", "Bar", "Violin", "2D Density", "Box", "Count Plot", "Histogram", "3D Scatter", "3D Line"]
        y_label_text = self.determine_y_label(plot_type, y_cols)

        general_kwargs = {
            "title": self.plot_tab.view.title_input.text() or plot_type,
            "xlabel": self.plot_tab.view.xlabel_input.text() or x_col,
            "ylabel": self.plot_tab.view.ylabel_input.text() or y_label_text,
            "legend": self.plot_tab.view.legend_check.isChecked()
        }

        if plot_type in ["3D Scatter", "3D Line", "3D Surface"]:
            z_col_text = self.plot_tab.view.z_column.currentText()
            general_kwargs["z_column"] = z_col_text
            general_kwargs["zlabel"] = self.plot_tab.view.zlabel_input.text() or z_col_text
            general_kwargs["elevation"] = self.plot_tab.view.camera_elevation_spin.value(),
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

    def determine_y_label(self, plot_type: str, y_cols: list[str]) -> str:
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
            "scheme": scheme_text if scheme_text != "None" else None,
            "k": self.plot_tab.view.geo_k_spin.value(),
            "cmap": self.plot_tab.view.palette_combo.currentText(),
            "legend": self.plot_tab.view.geo_legend_check.isChecked(),
            "legend_kwds": {
                "loc": "best",
                "orientation": self.plot_tab.view.geo_legend_loc_combo.currentText()
            },
            "use_divider": self.plot_tab.view.geo_use_divider_check.isChecked(),
            "cax_enabled": self.plot_tab.view.geo_cax_check.isChecked(),
            "axis_off": self.plot_tab.view.geo_axis_off_check.isChecked(),
            "missing_kwds": {
                "color": self.plot_tab.geo_missing_color,
                "label": self.plot_tab.view.geo_missing_label_input.text(),
                "hatch": hatch_text if hatch_text != "None" else None
            },
            "edgecolor": self.plot_tab.geo_edge_color,
            "linewidth": self.plot_tab.view.geo_linewidth_spin.value(),
            "target_crs": target_crs,
            "add_basemap": add_basemap,
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
            self.plot_tab.status_bar.log(f"Could not apply plotting style. {str(error)}", "WARNING")
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
            except Exception as error:
                self.plot_tab.status_bar.log(f"Z-Scale update ignore: {error}", "WARNING")

    def apply_plot_formatting(self, progress_dialog: Any, x_col: str, y_cols: list[str], axes_flipped: bool, font_family: str, general_kwargs: dict, active_df: 'pd.DataFrame') -> None:
        """Master method to apply all formatting steps."""
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
            self.plot_tab.status_bar.log(f"Could not apply tick formatting: {str(e)}", "WARNING")

        if progress_dialog:
            self.plot_tab._update_progress(progress_dialog, 70, "Applying formatting")

        if not axes_flipped:
            self.apply_plot_appearance(x_col, y_cols, font_family, general_kwargs)

        if progress_dialog:
            self.plot_tab._update_progress(progress_dialog, 75, "Applying customizations")
        self.apply_plot_customizations()

        if progress_dialog:
            self.plot_tab._update_progress(progress_dialog, 80, "Adding legend and gridlines")
        self.apply_legend_and_grid(general_kwargs, font_family)
        self.apply_spines_customization()

        if progress_dialog:
            self.plot_tab._update_progress(progress_dialog, 85, "Adding annotations")

        self.plot_tab._apply_annotations(active_df, x_col, y_cols)
        self.apply_tick_customization()
        self.apply_textbox()

        if progress_dialog:
            self.plot_tab._update_progress(progress_dialog, 95, "Adding data table")
        self.plot_tab._apply_table()

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
        linewidth = self.plot_tab.view.linewidth_spin.value()
        linestyle = self.plot_tab.view.linestyle_combo.currentText()
        marker = self.plot_tab.view.marker_combo.currentText()
        marker_size = self.plot_tab.view.marker_size_spin.value()
        line_color = self.plot_tab.line_color
        marker_color = self.plot_tab.marker_color
        marker_edge_color = self.plot_tab.marker_edge_color
        marker_edge_width = self.plot_tab.view.marker_edge_width_spin.value()
        bar_color = self.plot_tab.bar_color
        bar_edge_color = self.plot_tab.bar_edge_color
        bar_edge_width = self.plot_tab.view.bar_edge_width_spin.value()

        linestyle_map = {'Solid': '-', 'Dashed': '--', 'Dash-dot': '-.', 'Dotted': ':'}
        linestyle_val = linestyle_map.get(linestyle, linestyle)
        marker_val = "None" if marker == "None" else marker

        if self.plot_tab.view.multiline_custom_check.isChecked():
            lines = [l for l in self.plot_tab.plot_engine.current_ax.get_lines() if l.get_gid() not in ["regression_line", "confidence_interval", "error_bar"]]
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
                    if linestyle_val != "None":
                        line.set_linestyle(linestyle_val)
                    line.set_linewidth(linewidth)
                    if line_color:
                        line.set_color(line_color)
                    if marker_val != "None":
                        line.set_marker(marker_val)
                        line.set_markersize(marker_size)
                        if marker_color:
                            line.set_markerfacecolor(marker_color)
                        if marker_edge_color:
                            line.set_markeredgecolor(marker_edge_color)
                        line.set_markeredgewidth(marker_edge_width)
                    line.set_alpha(alpha)
        else:
            for line in self.plot_tab.plot_engine.current_ax.get_lines():
                if line.get_gid() in ["regression_line", "confidence_interval", "error_bar"]:
                    continue
                if linestyle_val != "None":
                    line.set_linestyle(linestyle_val)
                    line.set_linewidth(linewidth)
                if line_color:
                    line.set_color(line_color)
                if marker_val != "None":
                    line.set_marker(marker_val)
                    line.set_markersize(marker_size)
                    if marker_color:
                        line.set_markerfacecolor(marker_color)
                    if marker_edge_color:
                        line.set_markeredgecolor(marker_edge_color)
                        line.set_markeredgewidth(marker_edge_width)
                line.set_alpha(alpha)

        for collection in self.plot_tab.plot_engine.current_ax.collections:
            if collection.get_gid() in ["confidence_interval", "error_bar"]:
                continue
            collection.set_alpha(alpha)
            if marker_color:
                collection.set_facecolor(marker_color)
            if marker_edge_color:
                collection.set_edgecolor(marker_edge_color)

        if self.plot_tab.view.multibar_custom_check.isChecked():
            if self.plot_tab.plot_engine.current_ax and self.plot_tab.plot_engine.current_ax.containers:
                for i, container in enumerate(self.plot_tab.plot_engine.current_ax.containers):
                    if not hasattr(container, "patches") or not container.patches:
                        continue

                    label = container.get_label()
                    if not label or label.startswith("_"):
                        handles, labels = self.plot_tab.plot_engine.current_ax.get_legend_handles_labels()
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
                            patch.set_alpha(alpha)
                            if bar_color:
                                patch.set_facecolor(bar_color)
                            if bar_edge_color:
                                patch.set_edgecolor(bar_edge_color)
                            patch.set_linewidth(bar_edge_width)
        else:
            for patch in self.plot_tab.plot_engine.current_ax.patches:
                patch.set_alpha(alpha)
                if bar_color:
                    patch.set_facecolor(bar_color)
                if bar_edge_color:
                    patch.set_edgecolor(bar_edge_color)
                patch.set_linewidth(bar_edge_width)

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
            custom_labels = [l.strip() for l in custom_labels_str.split(",")]
            for i in range(min(len(labels), len(custom_labels))):
                if custom_labels[i]:
                    labels[i] = custom_labels[i]

        legend_kwargs = {
            "loc": self.plot_tab.view.legend_loc_combo.currentText(),
            "fontsize": self.plot_tab.view.legend_size_spin.value(),
            "title_fontsize": self.plot_tab.view.legend_title_size_spin.value(),
            "ncol": self.plot_tab.view.legend_columns_spin.value(),
            "columnspacing": self.plot_tab.view.legend_colspace_spin.value(),
            "frameon": self.plot_tab.view.legend_frame_check.isChecked(),
            "fancybox": self.plot_tab.view.legend_fancybox_check.isChecked(),
            "shadow": self.plot_tab.view.legend_shadow_check.isChecked(),
            "framealpha": self.plot_tab.view.legend_alpha_slider.value() / 100.0,
            "facecolor": self.plot_tab.legend_bg_color,
            "edgecolor": self.plot_tab.legend_edge_color
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
        except Exception as e:
            self.plot_tab.status_bar.log(f"Failed to apply legend: {e}", "WARNING")

    def apply_gridlines_customizations(self) -> None:
        """Apply gridlines customizations."""
        if not self.plot_tab.view.grid_check.isChecked():
            self.plot_tab.plot_engine.current_ax.grid(False)
            return

        self.plot_tab.plot_engine.current_ax.grid(True)

        if self.plot_tab.view.independent_grid_check.isChecked():
            grid_style_map = {"Solid (-)": "-", "Dashed (--)": "--", "Dash-dot (-.)": "-.", "Dotted (:)": ":"}

            style = grid_style_map.get(self.plot_tab.view.x_major_grid_style_combo.currentText(), "-")
            self.plot_tab.plot_engine.current_ax.grid(
                visible=self.plot_tab.view.x_major_grid_check.isChecked(), which="major", axis="x",
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
            else:
                self.plot_tab.plot_engine.current_ax.grid(visible=False, which="minor", axis="x")

            style = grid_style_map.get(self.plot_tab.view.y_major_grid_style_combo.currentText(), "-")
            self.plot_tab.plot_engine.current_ax.grid(
                visible=self.plot_tab.view.y_major_grid_check.isChecked(), which="major", axis="y",
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
                self.plot_tab.plot_engine.current_ax.grid(visible=False, which="minor", axis="y")
        else:
            which_type = self.plot_tab.view.grid_which_type_combo.currentText()
            axis = self.plot_tab.view.grid_axis_combo.currentText()
            self.plot_tab.plot_engine.current_ax.grid(
                visible=True, which=which_type, axis=axis,
                color=self.plot_tab.global_grid_color, alpha=self.plot_tab.view.global_grid_alpha_slider.value() / 100.0
            )

    def apply_tick_customization(self) -> None:
        """Apply tick label formatting and rotations."""
        self.plot_tab.plot_engine.current_ax.tick_params(
            axis="x", labelsize=self.plot_tab.view.xtick_label_size_spin.value(),
            direction=self.plot_tab.view.x_major_tick_direction_combo.currentText(),
            width=self.plot_tab.view.x_major_tick_width_spin.value(), which="major"
        )
        self.plot_tab.plot_engine.current_ax.tick_params(
            axis="y", labelsize=self.plot_tab.view.ytick_label_size_spin.value(),
            direction=self.plot_tab.view.y_major_tick_direction_combo.currentText(),
            width=self.plot_tab.view.y_major_tick_width_spin.value(), which="major"
        )

        if hasattr(self.plot_tab.plot_engine.current_ax, "zaxis"):
            self.plot_tab.plot_engine.current_ax.tick_params(
                axis="z", labelsize=self.plot_tab.view.ztick_label_size_spin.value(),
                direction=self.plot_tab.view.z_major_tick_direction_combo.currentText(),
                width=self.plot_tab.view.z_major_tick_width_spin.value(), which="major"
            )

        if self.plot_tab.view.x_top_axis_check.isChecked():
            self.plot_tab.plot_engine.current_ax.xaxis.tick_top()
            self.plot_tab.plot_engine.current_ax.xaxis.set_label_position("top")
        else:
            self.plot_tab.plot_engine.current_ax.xaxis.tick_bottom()
            self.plot_tab.plot_engine.current_ax.xaxis.set_label_position("bottom")

        needs_x_minor = self.plot_tab.view.x_show_minor_ticks_check.isChecked()
        needs_y_minor = self.plot_tab.view.y_show_minor_ticks_check.isChecked()
        needs_z_minor = hasattr(self.plot_tab.view,
                                "z_show_minor_ticks_check") and self.plot_tab.view.z_show_minor_ticks_check.isChecked()

        if self.plot_tab.view.grid_check.isChecked():
            if self.plot_tab.view.independent_grid_check.isChecked():
                if self.plot_tab.view.x_minor_grid_check.isChecked(): needs_x_minor = True
                if self.plot_tab.view.y_minor_grid_check.isChecked(): needs_y_minor = True
            else:
                which = self.plot_tab.view.grid_which_type_combo.currentText()
                axis = self.plot_tab.view.grid_axis_combo.currentText()
                if which in ["minor", "both"]:
                    if axis in ["x", "both"]: needs_x_minor = True
                    if axis in ["y", "both"]: needs_y_minor = True
                    if hasattr(self.plot_tab.plot_engine.current_ax, "zaxis") and axis == "both": needs_z_minor = True

        try:
            if needs_x_minor:
                if type(self.plot_tab.plot_engine.current_ax.xaxis.get_major_locator()).__name__ in ["AutoLocator", "MaxNLocator"]:
                    self.plot_tab.plot_engine.current_ax.xaxis.set_minor_locator(AutoMinorLocator())
            else:
                self.plot_tab.plot_engine.current_ax.xaxis.set_minor_locator(NullLocator())

            if needs_y_minor:
                if type(self.plot_tab.plot_engine.current_ax.yaxis.get_major_locator()).__name__ in ["AutoLocator", "MaxNLocator"]:
                    self.plot_tab.plot_engine.current_ax.yaxis.set_minor_locator(AutoMinorLocator())
            else:
                self.plot_tab.plot_engine.current_ax.yaxis.set_minor_locator(NullLocator())

            if hasattr(self.plot_tab.plot_engine.current_ax, "zaxis"):
                if needs_z_minor:
                    if type(self.plot_tab.plot_engine.current_ax.zaxis.get_major_locator()).__name__ in ["AutoLocator", "MaxNLocator"]:
                        self.plot_tab.plot_engine.current_ax.zaxis.set_minor_locator(AutoMinorLocator())
                else:
                    self.plot_tab.plot_engine.current_ax.zaxis.set_minor_locator(NullLocator())
        except Exception as e:
            self.plot_tab.status_bar.log(f"Warning mapping minor locators: {str(e)}", "WARNING")

        if self.plot_tab.view.x_show_minor_ticks_check.isChecked():
            self.plot_tab.plot_engine.current_ax.tick_params(
                axis="x", which="minor", bottom=True, top=self.plot_tab.view.x_top_axis_check.isChecked(),
                direction=self.plot_tab.view.x_minor_tick_direction_combo.currentText(),
                width=self.plot_tab.view.x_minor_tick_width_spin.value()
            )
        else:
            self.plot_tab.plot_engine.current_ax.tick_params(axis="x", which="minor", bottom=False, top=False)

        if self.plot_tab.view.y_show_minor_ticks_check.isChecked():
            self.plot_tab.plot_engine.current_ax.tick_params(
                axis="y", which="minor", left=True, right=False,
                direction=self.plot_tab.view.y_minor_tick_direction_combo.currentText(),
                width=self.plot_tab.view.y_minor_tick_width_spin.value()
            )
        else:
            self.plot_tab.plot_engine.current_ax.tick_params(axis="y", which="minor", left=False, right=False)

        if hasattr(self.plot_tab.plot_engine.current_ax, "zaxis") and hasattr(self.plot_tab.view,  "z_show_minor_ticks_check"):
            if self.plot_tab.view.z_show_minor_ticks_check.isChecked():
                self.plot_tab.plot_engine.current_ax.tick_params(
                    axis="z", which="minor", direction=self.plot_tab.view.z_minor_tick_direction_combo.currentText(),
                    width=self.plot_tab.view.z_minor_tick_width_spin.value()
                )
            else:
                self.plot_tab.plot_engine.current_ax.tick_params(axis="z", which="minor")

        try:
            x_unit_str = self.plot_tab.view.x_display_units_combo.currentText()
            if x_unit_str != "None":
                x_formatter = self.create_axis_formatter(x_unit_str)
                if x_formatter: self.plot_tab.plot_engine.current_ax.xaxis.set_major_formatter(x_formatter)

            y_unit_str = self.plot_tab.view.y_display_units_combo.currentText()
            if y_unit_str != "None":
                y_formatter = self.create_axis_formatter(y_unit_str)
                if y_formatter: self.plot_tab.plot_engine.current_ax.yaxis.set_major_formatter(y_formatter)

            if hasattr(self.plot_tab.plot_engine.current_ax, "zaxis") and hasattr(self.plot_tab.view, "z_display_units_combo"):
                z_unit_str = self.plot_tab.view.z_display_units_combo.currentText()
                if z_unit_str != "None":
                    z_formatter = self.create_axis_formatter(z_unit_str)
                    if z_formatter: self.plot_tab.plot_engine.current_ax.zaxis.set_major_formatter(z_formatter)
        except Exception as e:
            self.plot_tab.status_bar.log(f"Failed to apply display units: {str(e)}", "WARNING")

        if self.plot_tab.view.custom_datetime_check.isChecked():
            format_map = {
                "YYYY-MM-DD": "%Y-%m-%d", "MM/DD/YYYY": "%m/%d/%Y", "DD/MM/YYYY": "%d/%m/%Y",
                "YYYY/MM/DD": "%Y/%m/%d", "DD-MM-YYYY": "%d-%m-%Y", "Mon DD, YYYY": "%b %d, %Y",
                "DD Mon YYYY": "%d %b %Y", "YYYY-MM": "%Y-%m", "MM-YYYY": "%m-%Y",
                "HH:MM:SS": "%H:%M:%S", "YYYY-MM-DD HH:MM": "%Y-%m-%d %H:%M"
            }

            x_fmt_name = self.plot_tab.view.x_datetime_format_combo.currentText()
            if x_fmt_name and x_fmt_name != "None":
                fmt_str = self.plot_tab.view.x_custom_datetime_input.text() if x_fmt_name == "Custom" else format_map.get(
                    x_fmt_name)
                if fmt_str:
                    try:
                        self.plot_tab.plot_engine.current_ax.xaxis.set_major_formatter(mdates.DateFormatter(fmt_str))
                        self.plot_tab.plot_engine.current_ax.xaxis.set_major_locator(
                            mdates.AutoDateLocator(minticks=4, maxticks=15))
                    except Exception:
                        pass

            y_fmt_name = self.plot_tab.view.y_datetime_format_combo.currentText()
            if y_fmt_name and y_fmt_name != "None":
                fmt_str = self.plot_tab.view.y_custom_datetime_format_input.text() if y_fmt_name == "Custom" else format_map.get(
                    y_fmt_name)
                if fmt_str:
                    try:
                        self.plot_tab.plot_engine.current_ax.yaxis.set_major_formatter(mdates.DateFormatter(fmt_str))
                        self.plot_tab.plot_engine.current_ax.yaxis.set_major_locator(
                            mdates.AutoDateLocator(minticks=4, maxticks=15))
                    except Exception:
                        pass

        plt.setp(self.plot_tab.plot_engine.current_ax.get_xticklabels(), rotation=self.plot_tab.view.xtick_rotation_spin.value())
        plt.setp(self.plot_tab.plot_engine.current_ax.get_yticklabels(), rotation=self.plot_tab.view.ytick_rotation_spin.value())
        if hasattr(self.plot_tab.plot_engine.current_ax, "zaxis"):
            plt.setp(self.plot_tab.plot_engine.current_ax.get_zticklabels(), rotation=self.plot_tab.view.ztick_rotation_spin.value())

        if self.plot_tab.view.x_invert_axis_check.isChecked():
            if not self.plot_tab.plot_engine.current_ax.xaxis_inverted(): self.plot_tab.plot_engine.current_ax.invert_xaxis()
        else:
            if self.plot_tab.plot_engine.current_ax.xaxis_inverted(): self.plot_tab.plot_engine.current_ax.invert_xaxis()

        if self.plot_tab.view.y_invert_axis_check.isChecked():
            if not self.plot_tab.plot_engine.current_ax.yaxis_inverted(): self.plot_tab.plot_engine.current_ax.invert_yaxis()
        else:
            if self.plot_tab.plot_engine.current_ax.yaxis_inverted(): self.plot_tab.plot_engine.current_ax.invert_yaxis()

        if hasattr(self.plot_tab.plot_engine.current_ax, "zaxis"):
            if self.plot_tab.view.z_invert_axis_check.isChecked():
                if not self.plot_tab.plot_engine.current_ax.zaxis_inverted(): self.plot_tab.plot_engine.current_ax.invert_zaxis()
            else:
                if self.plot_tab.plot_engine.current_ax.zaxis_inverted(): self.plot_tab.plot_engine.current_ax.invert_zaxis()

    def apply_textbox(self) -> None:
        """Apply custom floating textbox."""
        if not self.plot_tab.plot_engine.current_ax: return

        for text_artist in list(self.plot_tab.plot_engine.current_ax.texts):
            if text_artist.get_gid() == "custom_textbox":
                try:
                    text_artist.remove()
                except:
                    pass

        if self.plot_tab.view.textbox_enable_check.isChecked():
            textbox_text = self.plot_tab.view.textbox_content.text().strip()
            if textbox_text:
                style_map = {
                    "Rounded": "round", "Square": "square",
                    "round,pad=1": "round,pad=1", "round4,pad=0.5": "round4,pad=0.5"
                }
                style = style_map.get(self.plot_tab.view.textbox_style_combo.currentText(), "round")

                position_coords = {
                    "upper left": (0.05, 0.95), "upper center": (0.5, 0.95), "upper right": (0.95, 0.95),
                    "center left": (0.05, 0.5), "center": (0.5, 0.5), "center right": (0.95, 0.5),
                    "lower left": (0.05, 0.05), "lower center": (0.5, 0.05), "lower right": (0.95, 0.05)
                }

                position_name = self.plot_tab.view.textbox_position_combo.currentText()
                x, y = position_coords.get(position_name, (0.5, 0.5))

                ha_map = {"upper left": "left", "center left": "left", "lower left": "left", "upper center": "center",
                          "center": "center", "lower center": "center", "upper right": "right", "center right": "right",
                          "lower right": "right"}
                va_map = {"upper left": "top", "upper center": "top", "upper right": "top", "center left": "center",
                          "center": "center", "center right": "center", "lower left": "bottom",
                          "lower center": "bottom", "lower right": "bottom"}

                self.plot_tab.plot_engine.current_ax.text(
                    x, y, textbox_text, transform=self.plot_tab.plot_engine.current_ax.transAxes,
                    fontsize=11, verticalalignment=va_map.get(position_name, "center"),
                    horizontalalignment=ha_map.get(position_name, "center"),
                    bbox=dict(boxstyle=style, facecolor=self.plot_tab.textbox_bg_color, alpha=0.8, pad=1),
                    gid="custom_textbox"
                )

    def create_axis_formatter(self, unit_str: str) -> Optional[FuncFormatter]:
        """Create a matplotlib FuncFormatter based on the selected unit."""

        def formatter(x, pos):
            try:
                if unit_str == "Hundreds (100s)":
                    return f"{x / 1e2:.1f}H"
                elif unit_str == "Thousands":
                    val = x / 1e3
                    return f"{val / 1e3:.1f}M" if abs(val) >= 1000 else f"{val:.1f}K"
                elif unit_str == "Millions":
                    val = x / 1e6
                    return f"{val / 1e3:.1f}B" if abs(val) >= 1000 else f"{val:.1f}M"
                elif unit_str == "Billions":
                    return f"{x / 1e9:.1f}B"
                else:
                    return f"{x:g}"
            except (ValueError, TypeError):
                return f"{x:g}"

        return FuncFormatter(formatter) if unit_str != "None" else None

    def apply_spines_customization(self) -> None:
        """Apply spines customization."""
        if not self.plot_tab.plot_engine.current_ax: return
        try:
            spines = self.plot_tab.plot_engine.current_ax.spines
            is_individual = self.plot_tab.view.individual_spines_check.isChecked()

            global_width = self.plot_tab.view.global_spine_width_spin.value()
            global_color = self.plot_tab.global_spine_color

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

            for key, vis_check, width_spin, color_attr in spine_map:
                if key not in spines: continue
                if vis_check.isChecked():
                    spines[key].set_visible(True)
                    spines[key].set_linewidth(width_spin.value() if is_individual else global_width)
                    spines[key].set_edgecolor(
                        getattr(self.plot_tab, color_attr, "black") if is_individual else global_color)
                else:
                    spines[key].set_visible(False)
        except Exception as e:
            self.plot_tab.status_bar.log(f"Failed to apply spine customization: {str(e)}", "ERROR")
            traceback.print_exc()