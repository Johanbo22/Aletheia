from typing import Dict, Any, TYPE_CHECKING, Union
if TYPE_CHECKING:
    from ui.plot_tab import PlotTab
    from ui.components.plot_settings_panel import PlotSettingsPanel
from PyQt6.QtGui import QFont
from resources.version import APPLICATION_VERSION

class PlotConfigManager:
    """
    Manages the extraction and loading of plot configurations and themes
    For usage in the PlotTab and redirects of main plotting engine.
    """
    def __init__(self, plot_tab_instance: Union["PlotTab", "PlotSettingsPanel"]) -> None:
        self.pt = plot_tab_instance
    
    def get_config(self) -> Dict[str, Any]:
        """Get the current plot configuration"""
        config = {
            "version": APPLICATION_VERSION,
            "plot_type": self.pt.current_plot_type_name,
            "basic": self._get_basic_config(),
            "appearance": self._get_appearance_config(),
            "axes": self._get_axes_config(),
            "legend": self._get_legend_config(),
            "grid": self._get_grid_config(),
            "advanced": self._get_advanced_config(),
            "annotations": self._get_annotations_config(),
            "geospatial": self._get_geospatial_config()
        }
        return config
    
    def load_config(self, config: Dict[str, Any]) -> None:
        """Load the plot configuration"""
        try:
            if "plot_type" in config:
                self.pt.plot_type.blockSignals(True)
                self.pt._select_plot_in_toolbox(config["plot_type"])
                self.pt.plot_type.blockSignals(False)
                self.pt.on_plot_type_changed(config["plot_type"])
            if "basic" in config: self._load_basic_config(config["basic"])
            if "appearance" in config: self._load_appearance_config(config["appearance"])
            if "axes" in config: self._load_axes_config(config["axes"])
            if "legend" in config: self._load_legend_config(config["legend"])
            if "grid" in config: self._load_grid_config(config["grid"])
            if "advanced" in config: self._load_advanced_config(config["advanced"])
            if "annotations" in config: self._load_annotations_config(config["annotations"])
            if "geospatial" in config: self._load_geospatial_config(config["geospatial"])

        except Exception as error:
            import logging
            logging.error(f"Failed to load configuration: {error}")
            raise
    
    def get_theme_config(self) -> Dict[str, Any]:
        """Get configuration formatted for themes"""
        theme_data = {
            "appearance": self._get_appearance_config(),
            "axes": self._get_axes_config(),
            "legend": self._get_legend_config(),
            "grid": self._get_grid_config(),
            "advanced": self._get_advanced_config()
        }

        if "axes" in theme_data:
            theme_data["axes"]["x_axis"]["auto_limits"] = True
            theme_data["axes"]["y_axis"]["auto_limits"] = True
            theme_data["axes"]["x_axis"]["min"] = 0
            theme_data["axes"]["x_axis"]["max"] = 1
            theme_data["axes"]["y_axis"]["min"] = 0
            theme_data["axes"]["y_axis"]["max"] = 1
        
        return theme_data

    def _get_basic_config(self) -> Dict[str, Any]:
        return {
            "x_column": self.pt.x_column.currentText(),
            "y_columns": self.pt.get_selected_y_columns(),
            "z_column": getattr(self.pt, "z_column", None) and self.pt.z_column.currentText(),
            "multi_y_checked": self.pt.multi_y_check.isChecked(),
            "hue_column": self.pt.hue_column.currentText(),
            "use_subset": self.pt.use_subset_check.isChecked(),
            "subset_name": self.pt.subset_combo.currentData(),
            "secondary_y_enabled": self.pt.secondary_y_check.isChecked(),
            "secondary_y_column": self.pt.secondary_y_column.currentText(),
            "secondary_plot_type": self.pt.secondary_plot_type_combo.currentText(),
            "quick_filter": self.pt.quick_filter_input.text(),
            "subplots": {
                "enabled": self.pt.add_subplots_check.isChecked(),
                "rows": self.pt.view.grid_designer.rows_spin.value(),
                "cols": self.pt.view.grid_designer.cols_spin.value(),
                "sharex": self.pt.subplot_sharex_check.isChecked(),
                "sharey": self.pt.subplot_sharey_check.isChecked(),
                "freeze_data": self.pt.freeze_data_check.isChecked()
            }
        }

    def _get_appearance_config(self) -> Dict[str, Any]:
        return {
            "font_family": self.pt.font_family_combo.currentFont().family(),
            "usetex": self.pt.usetex_checkbox.isChecked(),
            "colorblind": {
                "enabled": self.pt.colorblind_check.isChecked(),
                "type": self.pt.colorblind_type_combo.currentText()
            },
            "viewing_angles": {
                "elevation": getattr(self.pt, "camera_elevation_spin", None) and self.pt.camera_elevation_spin.value(),
                "azimuth": getattr(self.pt, "camera_azimuth_spin", None) and self.pt.camera_azimuth_spin.value(),
            },
            "title": {
                "enabled": self.pt.title_check.isChecked(),
                "text": self.pt.title_input.text(),
                "size": self.pt.title_size_spin.value(),
                "weight": self.pt.title_weight_combo.currentText(),
                "location": self.pt.title_position_combo.currentText(),
            },
            "xlabel": {
                "enabled": self.pt.xlabel_check.isChecked(),
                "text": self.pt.xlabel_input.text(),
                "size": self.pt.xlabel_size_spin.value(),
                "weight": self.pt.xlabel_weight_combo.currentText(),
            },
            "ylabel": {
                "enabled": self.pt.ylabel_check.isChecked(),
                "text": self.pt.ylabel_input.text(),
                "size": self.pt.ylabel_size_spin.value(),
                "weight": self.pt.ylabel_weight_combo.currentText(),
            },
            "zlabel": {
                "enabled": self.pt.zlabel_check.isChecked(),
                "text": self.pt.zlabel_input.text(),
                "size": self.pt.zlabel_size.value(),
                "weight": self.pt.zlabel_weight.currentText(),
            },
            "spines": {
                "individual": self.pt.individual_spines_check.isChecked(),
                "global_width": self.pt.global_spine_width_spin.value(),
                "global_color": self.pt.global_spine_color,
                "top": {
                    "visible": self.pt.top_spine_visible_check.isChecked(),
                    "width": self.pt.top_spine_width_spin.value(),
                    "color": self.pt.top_spine_color,
                },
                "bottom": {
                    "visible": self.pt.bottom_spine_visible_check.isChecked(),
                    "width": self.pt.bottom_spine_width_spin.value(),
                    "color": self.pt.bottom_spine_color,
                },
                "left": {
                    "visible": self.pt.left_spine_visible_check.isChecked(),
                    "width": self.pt.left_spine_width_spin.value(),
                    "color": self.pt.left_spine_color,
                },
                "right": {
                    "visible": self.pt.right_spine_visible_check.isChecked(),
                    "width": self.pt.right_spine_width_spin.value(),
                    "color": self.pt.right_spine_color,
                },
            },
            "figure": {
                "width": self.pt.width_spin.value(),
                "height": self.pt.height_spin.value(),
                "dpi": self.pt.dpi_spin.value(),
                "bg_color": self.pt.bg_color,
                "face_facecolor": self.pt.face_color,
                "palette": self.pt.palette_combo.currentText(),
                "tight_layout": self.pt.tight_layout_check.isChecked(),
                "style": self.pt.style_combo.currentText(),
            }
        }
    
    def _get_axes_config(self) -> Dict[str, Any]:
        return {
            "x_axis": {
                "auto_limits": self.pt.x_auto_check.isChecked(),
                "invert": self.pt.x_invert_axis_check.isChecked(),
                "top_axis": self.pt.x_top_axis_check.isChecked(),
                "min": self.pt.x_min_spin.value(),
                "max": self.pt.x_max_spin.value(),
                "tick_label_size": self.pt.xtick_label_size_spin.value(),
                "tick_rotation": self.pt.xtick_rotation_spin.value(),
                "max_ticks": self.pt.x_max_ticks_spin.value(),
                "minor_ticks_enabled": self.pt.x_show_minor_ticks_check.isChecked(),
                "major_tick_direction": self.pt.x_major_tick_direction_combo.currentText(),
                "major_tick_width": self.pt.x_major_tick_width_spin.value(),
                "minor_tick_direction": self.pt.x_minor_tick_direction_combo.currentText(),
                "minor_tick_width": self.pt.x_minor_tick_width_spin.value(),
                "scale": self.pt.x_scale_combo.currentText(),
                "display_units": self.pt.x_display_units_combo.currentText()
            },
            "y_axis": {
                "auto_limits": self.pt.y_auto_check.isChecked(),
                "invert": self.pt.y_invert_axis_check.isChecked(),
                "min": self.pt.y_min_spin.value(),
                "max": self.pt.y_max_spin.value(),
                "tick_label_size": self.pt.ytick_label_size_spin.value(),
                "tick_rotation": self.pt.ytick_rotation_spin.value(),
                "max_ticks": self.pt.y_max_ticks_spin.value(),
                "minor_ticks_enabled": self.pt.y_show_minor_ticks_check.isChecked(),
                "major_tick_direction": self.pt.y_major_tick_direction_combo.currentText(),
                "major_tick_width": self.pt.y_major_tick_width_spin.value(),
                "minor_tick_direction": self.pt.y_minor_tick_direction_combo.currentText(),
                "minor_tick_width": self.pt.y_minor_tick_width_spin.value(),
                "scale": self.pt.y_scale_combo.currentText(),
                "display_units": self.pt.y_display_units_combo.currentText()
            },
            "z_axis": {
                "auto_limits": getattr(self.pt, "z_auto_check", None) and self.pt.z_auto_check.isChecked(),
                "invert": getattr(self.pt, "z_invert_axis_check", None) and self.pt.z_invert_axis_check.isChecked(),
                "min": getattr(self.pt, "z_min_spin", None) and self.pt.z_min_spin.value(),
                "max": getattr(self.pt, "z_max_spin", None) and self.pt.z_max_spin.value(),
                "tick_label_size": getattr(self.pt, "ztick_label_size_spin", None) and self.pt.ztick_label_size_spin.value(),
                "tick_rotation": getattr(self.pt, "ztick_rotation_spin", None) and self.pt.ztick_rotation_spin.value(),
                "max_ticks": getattr(self.pt, "z_max_ticks_spin", None) and self.pt.z_max_ticks_spin.value(),
                "minor_ticks_enabled": getattr(self.pt, "z_show_minor_ticks_check", None) and self.pt.z_show_minor_ticks_check.isChecked(),
                "major_tick_direction": getattr(self.pt, "z_major_tick_direction_combo", None) and self.pt.z_major_tick_direction_combo.currentText(),
                "major_tick_width": getattr(self.pt, "z_major_tick_width_spin", None) and self.pt.z_major_tick_width_spin.value(),
                "minor_tick_direction": getattr(self.pt, "z_minor_tick_direction_combo", None) and self.pt.z_minor_tick_direction_combo.currentText(),
                "minor_tick_width": getattr(self.pt, "z_minor_tick_width_spin", None) and self.pt.z_minor_tick_width_spin.value(),
                "scale": getattr(self.pt, "z_scale_combo", None) and self.pt.z_scale_combo.currentText(),
                "display_units": getattr(self.pt, "z_display_units_combo", None) and self.pt.z_display_units_combo.currentText()
            },
            "flip_axes": self.pt.flip_axes_check.isChecked(),
            "datetime": {
                "enabled": self.pt.custom_datetime_check.isChecked(),
                "x_format_preset": self.pt.x_datetime_format_combo.currentText(),
                "x_format_custom": self.pt.x_custom_datetime_input.text(),
                "y_format_preset": self.pt.y_datetime_format_combo.currentText(),
                "y_format_custom": self.pt.y_custom_datetime_format_input.text(),
            }
        }
    
    def _get_legend_config(self) -> Dict[str, Any]:
        return {
            "enabled": self.pt.legend_check.isChecked(),
            "location": self.pt.legend_loc_combo.currentText(),
            "title": self.pt.legend_title_input.text(),
            "custom_labels": self.pt.legend_labels_input.text(),
            "font_size": self.pt.legend_size_spin.value(),
            "title_font_size": self.pt.legend_title_size_spin.value(),
            "columns": self.pt.legend_columns_spin.value(),
            "column_spacing": self.pt.legend_colspace_spin.value(),
            "frame": self.pt.legend_frame_check.isChecked(),
            "fancy_box": self.pt.legend_fancybox_check.isChecked(),
            "shadow": self.pt.legend_shadow_check.isChecked(),
            "bg_color": self.pt.legend_bg_color,
            "edge_color": self.pt.legend_edge_color,
            "edge_width": self.pt.legend_edge_width_spin.value(),
            "alpha": self.pt.legend_alpha_slider.value() / 100.0,
        }
    
    def _get_grid_config(self) -> Dict[str, Any]:
        return {
            "enabled": self.pt.grid_check.isChecked(),
            "independent_axes": self.pt.independent_grid_check.isChecked(),
            "global": {
                "which": self.pt.grid_which_type_combo.currentText(),
                "axis": self.pt.grid_axis_combo.currentText(),
                "color": self.pt.global_grid_color,
                "alpha": self.pt.global_grid_alpha_slider.value() / 100.0,
            },
            "x_major": {
                "enabled": self.pt.x_major_grid_check.isChecked(),
                "style": self.pt.x_major_grid_style_combo.currentText(),
                "width": self.pt.x_major_grid_linewidth_spin.value(),
                "color": self.pt.x_major_grid_color,
                "alpha": self.pt.x_major_grid_alpha_slider.value() / 100.0,
            },
            "x_minor": {
                "enabled": self.pt.x_minor_grid_check.isChecked(),
                "style": self.pt.x_minor_grid_style_combo.currentText(),
                "width": self.pt.x_minor_grid_linewidth_spin.value(),
                "color": self.pt.x_minor_grid_color,
                "alpha": self.pt.x_minor_grid_alpha_slider.value() / 100.0,
            },
            "y_major": {
                "enabled": self.pt.y_major_grid_check.isChecked(),
                "style": self.pt.y_major_grid_style_combo.currentText(),
                "width": self.pt.y_major_grid_linewidth_spin.value(),
                "color": self.pt.y_major_grid_color,
                "alpha": self.pt.y_major_grid_alpha_slider.value() / 100.0,
            },
            "y_minor": {
                "enabled": self.pt.y_minor_grid_check.isChecked(),
                "style": self.pt.y_minor_grid_style_combo.currentText(),
                "width": self.pt.y_minor_grid_linewidth_spin.value(),
                "color": self.pt.y_minor_grid_color,
                "alpha": self.pt.y_minor_grid_alpha_slider.value() / 100.0,
            },
        }
    
    def _get_advanced_config(self) -> Dict[str, Any]:
        linestyle_map = {'Solid': '-', 'Dashed': '--', 'Dash-dot': '-.', 'Dotted': ':', 'None': 'None'}
        return {
            "multi_line_custom": self.pt.multiline_custom_check.isChecked(),
            "line_customizations": self.pt.line_customizations,
            "global_line": {
                "width": self.pt.linewidth_spin.value(),
                "style": linestyle_map.get(self.pt.linestyle_combo.currentText(), "-"),
                "color": self.pt.line_color,
            },
            "global_marker": {
                "shape": self.pt.marker_combo.currentText(),
                "size": self.pt.marker_size_spin.value(),
                "color": self.pt.marker_color,
                "edge_color": self.pt.marker_edge_color,
                "edge_width": self.pt.marker_edge_width_spin.value(),
            },
            "multi_bar_custom": self.pt.multibar_custom_check.isChecked(),
            "bar_customizations": self.pt.bar_customizations,
            "global_bar": {
                "width": self.pt.bar_width_spin.value(),
                "color": self.pt.bar_color,
                "edge_color": self.pt.bar_edge_color,
                "edge_width": self.pt.bar_edge_width_spin.value(),
            },
            "histogram": {
                "bins": self.pt.histogram_bins_spin.value(),
                "show_normal": self.pt.histogram_show_normal_check.isChecked(),
                "show_kde": self.pt.histogram_show_kde_check.isChecked(),
            },
            "global_alpha": self.pt.alpha_slider.value() / 100.0,
            "global_error_bar": {
                "type": self.pt.error_bars_combo.currentText(),
                "color": self.pt.error_bar_color,
                "linewidth": self.pt.error_bar_linewidth_spin.value(),
                "capsize": self.pt.error_bar_capsize_spin.value(),
                "alpha": self.pt.error_bar_alpha_slider.value() / 100.0,
                "zorder": self.pt.error_bar_zorder_spin.value(),
            },
            "scatter": {
                "show_regression": self.pt.regression_line_check.isChecked(),
                "show_ci": self.pt.confidence_interval_check.isChecked(),
                "show_r2": self.pt.show_r2_check.isChecked(),
                "show_rmse": self.pt.show_rmse_check.isChecked(),
                "show_equation": self.pt.show_equation_check.isChecked(),
                "error_bars": self.pt.error_bars_combo.currentText(),
                "ci_level": self.pt.confidence_level_spin.value(),
            },
            "pie": {
                "show_percentages": self.pt.pie_show_percentages_check.isChecked(),
                "start_angle": self.pt.pie_start_angle_spin.value(),
                "explode_first": self.pt.pie_explode_check.isChecked(),
                "explode_distance": self.pt.pie_explode_distance_spin.value(),
                "shadow": self.pt.pie_shadow_check.isChecked(),
                "donut_enabled": self.pt.pie_donut_check.isChecked(),
                "donut_width": self.pt.pie_donut_width_spin.value()
            },
        }
    
    def _get_annotations_config(self) -> Dict[str, Any]:
        return {
            "text_annotations": self.pt.annotation_manager.annotations,
            "reference_lines": self.pt.reference_line_manager.get_config(),
            "auto_annotate": {
                "enabled": self.pt.auto_annotate_check.isChecked(),
                "column": self.pt.auto_annotate_col_combo.currentText()
            },
            "textbox": {
                "enabled": self.pt.textbox_enable_check.isChecked(),
                "content": self.pt.textbox_content.text(),
                "position": self.pt.textbox_position_combo.currentText(),
                "style": self.pt.textbox_style_combo.currentText(),
                "bg_color": self.pt.textbox_bg_color,
            },
            "table": {
                "enabled": self.pt.table_enable_check.isChecked(),
                "type": self.pt.table_type_combo.currentText(),
                "location": self.pt.table_location_combo.currentText(),
                "auto_font_size": self.pt.table_auto_font_size_check.isChecked(),
                "fontsize": self.pt.table_font_size_spin.value(),
                "scale": self.pt.table_scale_spin.value()
            }
        }

    def _get_geospatial_config(self) -> Dict[str, Any]:
        return {
            "target_crs": self.pt.geo_target_crs_input.text(),
            "basemap": {
                "enabled": self.pt.geo_basemap_check.isChecked(),
                "source": self.pt.geo_basemap_style_combo.currentText()
            },
            "choropleth": {
                "scheme": self.pt.geo_scheme_combo.currentText(),
                "k": self.pt.geo_k_spin.value()
            },
            "legend": {
                "enabled": self.pt.geo_legend_check.isChecked(),
                "location": self.pt.geo_legend_loc_combo.currentText(),
                "use_divider": self.pt.geo_use_divider_check.isChecked(),
                "cax_enabled": self.pt.geo_cax_check.isChecked(),
                "axis_off": self.pt.geo_axis_off_check.isChecked()
            },
            "missing_data": {
                "label": self.pt.geo_missing_label_input.text(),
                "color": self.pt.geo_missing_color,
                "hatch": self.pt.geo_hatch_combo.currentText()
            },
            "boundary": {
                "enabled": self.pt.geo_boundary_check.isChecked(),
                "color": self.pt.geo_edge_color,
                "linewidth": self.pt.geo_linewidth_spin.value()
            }
        }

    def _load_basic_config(self, config: dict):
        self.pt.x_column.setCurrentText(config.get("x_column", ""))
        self.pt.quick_filter_input.setText(config.get("quick_filter", ""))
        
        if hasattr(self.pt, "z_column"):
            self.pt.z_column.setCurrentText(config.get("z_column", ""))

        # Multi Y config
        multi_y = config.get("multi_y_checked", False)
        self.pt.multi_y_check.setChecked(multi_y)
        self.pt.toggle_multi_y()

        y_cols = config.get("y_columns") or []
        if multi_y:
            self.pt.y_columns_list.clearSelection()
            for i in range(self.pt.y_columns_list.count()):
                item = self.pt.y_columns_list.item(i)
                if item.text() in y_cols:
                    item.setSelected(True)
        else:
            if y_cols:
                self.pt.y_column.setCurrentText(y_cols[0])
        
        self.pt.hue_column.setCurrentText(config.get("hue_column", "None"))

        # secondary y config
        sec_y_enabled = config.get("secondary_y_enabled", False)
        self.pt.secondary_y_check.setChecked(sec_y_enabled)
        self.pt._toggle_secondary_input(sec_y_enabled)
        if sec_y_enabled:
            self.pt.secondary_y_column.setCurrentText(config.get("secondary_y_column", ""))
            self.pt.secondary_plot_type_combo.setCurrentText(config.get("secondary_plot_type", "Line"))

        # Subsets
        use_subset = config.get("use_subset", False)
        self.pt.use_subset_check.setChecked(use_subset)
        if use_subset:
            subset_name = config.get("subset_name")
            if subset_name:
                index = self.pt.subset_combo.findData(subset_name)
                if index >= 0:
                    self.pt.subset_combo.setCurrentIndex(index)
        self.pt.use_subset()
                
        sub_conf = config.get("subplots", {})
        self.pt.add_subplots_check.setChecked(sub_conf.get("enabled", False))
        self.pt.subplot_sharex_check.setChecked(sub_conf.get("sharex", False))
        self.pt.subplot_sharey_check.setChecked(sub_conf.get("sharey", False))
        self.pt.freeze_data_check.setChecked(sub_conf.get("freeze_data", False))
        
    def _load_appearance_config(self, config: dict):
        # Font
        if "font_family" in config:
            self.pt.font_family_combo.setCurrentFont(QFont(config["font_family"]))
        self.pt.usetex_checkbox.setChecked(config.get("usetex", False))

        # Viewing angles
        viewing_angles = config.get("viewing_angles", {})
        if hasattr(self.pt, "camera_elevation_spin") and "elevation" in viewing_angles:
            self.pt.camera_elevation_spin.setValue(float(viewing_angles.get("elevation", 30)))
        if hasattr(self.pt, "camera_azimuth_spin") and "azimuth" in viewing_angles:
            self.pt.camera_azimuth_spin.setValue(float(viewing_angles.get("azimuth", -60)))
        
        # Colorblind mode
        cb_conf = config.get("colorblind", {})
        self.pt.colorblind_check.setChecked(cb_conf.get("enabled", False))
        self.pt.colorblind_type_combo.setCurrentText(cb_conf.get("type", "Protanopia (No Red)"))
        
        # Title
        title_conf = config.get("title", {})
        self.pt.title_check.setChecked(title_conf.get("enabled", False))
        self.pt.title_input.setText(title_conf.get("text", ""))
        self.pt.title_size_spin.setValue(int(title_conf.get("size", 12)))
        self.pt.title_weight_combo.setCurrentText(title_conf.get("weight", "normal"))
        self.pt.title_position_combo.setCurrentText(title_conf.get("location", "center"))

        # Labels
        x_label_conf = config.get("xlabel", {})
        self.pt.xlabel_check.setChecked(x_label_conf.get("enabled", False))
        self.pt.xlabel_input.setText(x_label_conf.get("text", ""))
        self.pt.xlabel_size_spin.setValue(int(x_label_conf.get("size", 10)))
        self.pt.xlabel_weight_combo.setCurrentText(x_label_conf.get("weight", "normal"))

        y_label_conf = config.get("ylabel", {})
        self.pt.ylabel_check.setChecked(y_label_conf.get("enabled", False))
        self.pt.ylabel_input.setText(y_label_conf.get("text", ""))
        self.pt.ylabel_size_spin.setValue(int(y_label_conf.get("size", 10)))
        self.pt.ylabel_weight_combo.setCurrentText(y_label_conf.get("weight", "normal"))
        
        z_label_conf = config.get("zlabel", {})
        self.pt.zlabel_check.setChecked(z_label_conf.get("enabled", True))
        self.pt.zlabel_input.setText(z_label_conf.get("text", ""))
        self.pt.zlabel_size.setValue(int(z_label_conf.get("size", 10)))
        self.pt.zlabel_weight.setCurrentText(z_label_conf.get("weight", "normal"))

        # Spines
        spines = config.get("spines", {})
        self.pt.individual_spines_check.setChecked(spines.get("individual", False))
        self.pt.global_spine_width_spin.setValue(int(spines.get("global_width", 1.0)))
        
        g_color = spines.get("global_color", "black")
        self.pt.global_spine_color = g_color
        if hasattr(self.pt, "global_spine_color_label"):
            self.pt.global_spine_color_label.setText(g_color)
            self.pt.global_spine_color_button.updateColors(base_color_hex=g_color)

        for side, ctrl_check, width_spin, color_attr, btn in [
            ("top", self.pt.top_spine_visible_check, self.pt.top_spine_width_spin, "top_spine_color", self.pt.top_spine_color_button),
            ("bottom", self.pt.bottom_spine_visible_check, self.pt.bottom_spine_width_spin, "bottom_spine_color", self.pt.bottom_spine_color_button),
            ("left", self.pt.left_spine_visible_check, self.pt.left_spine_width_spin, "left_spine_color", self.pt.left_spine_color_button),
            ("right", self.pt.right_spine_visible_check, self.pt.right_spine_width_spin, "right_spine_color", self.pt.right_spine_color_button)
        ]:
            if side in spines:
                s_conf = spines[side]
                ctrl_check.setChecked(s_conf.get("visible", True))
                width_spin.setValue(float(s_conf.get("width", 1.0)))
                color = s_conf.get("color", "black")
                setattr(self.pt, color_attr, color)
                btn.updateColors(base_color_hex=color)
        
        # Figure settings
        fig_conf = config.get("figure", {})
        self.pt.width_spin.setValue(int(fig_conf.get("width", 10)))
        self.pt.height_spin.setValue(int(fig_conf.get("height", 6)))
        self.pt.dpi_spin.setValue(int(fig_conf.get("dpi", 100)))

        if "bg_color" in fig_conf:
            self.pt.bg_color = fig_conf["bg_color"] or "white"
            self.pt.bg_color_label.setText(self.pt.bg_color)
            self.pt.bg_color_button.updateColors(base_color_hex=self.pt.bg_color)
        
        if "face_facecolor" in fig_conf:
            self.pt.face_color = fig_conf["face_facecolor"] or "white"
            self.pt.face_color_label.setText(self.pt.face_color)
            self.pt.face_color_button.updateColors(self.pt.face_color)
        
        self.pt.palette_combo.setCurrentText(fig_conf.get("palette", "viridis"))
        self.pt.tight_layout_check.setChecked(fig_conf.get("tight_layout", True))
        self.pt.style_combo.setCurrentText(fig_conf.get("style", "default"))
    
    def _load_axes_config(self, config: dict):
        # X axis
        x_conf = config.get("x_axis", {})
        self.pt.x_auto_check.setChecked(x_conf.get("auto_limits", True))
        self.pt.x_invert_axis_check.setChecked(x_conf.get("invert", False))
        self.pt.x_top_axis_check.setChecked(x_conf.get("top_axis", False))
        self.pt.x_min_spin.setValue(float(x_conf.get("min", 0.0)))
        self.pt.x_max_spin.setValue(float(x_conf.get("max", 1.0)))
        self.pt.xtick_label_size_spin.setValue(int(x_conf.get("tick_label_size", 10)))
        self.pt.xtick_rotation_spin.setValue(int(x_conf.get("tick_rotation", 0)))
        self.pt.x_max_ticks_spin.setValue(int(x_conf.get("max_ticks", 10)))
        self.pt.x_show_minor_ticks_check.setChecked(x_conf.get("minor_ticks_enabled", False))
        self.pt.x_major_tick_direction_combo.setCurrentText(x_conf.get("major_tick_direction", "out"))
        self.pt.x_major_tick_width_spin.setValue(float(x_conf.get("major_tick_width", 0.8)))
        self.pt.x_minor_tick_direction_combo.setCurrentText(x_conf.get("minor_tick_direction", "out"))
        self.pt.x_minor_tick_width_spin.setValue(float(x_conf.get("minor_tick_width", 0.6)))
        self.pt.x_scale_combo.setCurrentText(x_conf.get("scale", "linear"))
        self.pt.x_display_units_combo.setCurrentText(x_conf.get("display_units", "None"))

        # Y Axis
        y_conf = config.get("y_axis", {})
        self.pt.y_auto_check.setChecked(y_conf.get("auto_limits", True))
        self.pt.y_invert_axis_check.setChecked(y_conf.get("invert", False))
        self.pt.y_min_spin.setValue(float(y_conf.get("min", 0.0)))
        self.pt.y_max_spin.setValue(float(y_conf.get("max", 1.0)))
        self.pt.ytick_label_size_spin.setValue(int(y_conf.get("tick_label_size", 10)))
        self.pt.ytick_rotation_spin.setValue(int(y_conf.get("tick_rotation", 0)))
        self.pt.y_max_ticks_spin.setValue(int(y_conf.get("max_ticks", 10)))
        self.pt.y_show_minor_ticks_check.setChecked(y_conf.get("minor_ticks_enabled", False))
        self.pt.y_major_tick_direction_combo.setCurrentText(y_conf.get("major_tick_direction", "out"))
        self.pt.y_major_tick_width_spin.setValue(float(y_conf.get("major_tick_width", 0.8)))
        self.pt.y_minor_tick_direction_combo.setCurrentText(y_conf.get("minor_tick_direction", "out"))
        self.pt.y_minor_tick_width_spin.setValue(float(y_conf.get("minor_tick_width", 0.6)))
        self.pt.y_scale_combo.setCurrentText(y_conf.get("scale", "linear"))
        self.pt.y_display_units_combo.setCurrentText(y_conf.get("display_units", "None"))
        
        # Z-axis
        z_conf = config.get("z_axis", {})
        if hasattr(self.pt, "z_auto_check"):
            self.pt.z_auto_check.setChecked(z_conf.get("auto_limits", True))
            self.pt.z_invert_axis_check.setChecked(z_conf.get("invert", False))
            self.pt.z_min_spin.setValue(float(z_conf.get("min", 0.0)))
            self.pt.z_max_spin.setValue(float(z_conf.get("max", 1.0)))
            self.pt.ztick_label_size_spin.setValue(int(z_conf.get("tick_label_size", 10)))
            self.pt.ztick_rotation_spin.setValue(int(z_conf.get("tick_rotation", 0)))
            self.pt.z_max_ticks_spin.setValue(int(z_conf.get("max_ticks", 10)))
            self.pt.z_show_minor_ticks_check.setChecked(z_conf.get("minor_ticks_enabled", False))
            self.pt.z_major_tick_direction_combo.setCurrentText(z_conf.get("major_tick_direction", "out"))
            self.pt.z_major_tick_width_spin.setValue(float(z_conf.get("major_tick_width", 0.8)))
            self.pt.z_minor_tick_direction_combo.setCurrentText(z_conf.get("minor_tick_direction", "out"))
            self.pt.z_minor_tick_width_spin.setValue(float(z_conf.get("minor_tick_width", 0.6)))
            self.pt.z_scale_combo.setCurrentText(z_conf.get("scale", "linear"))
            self.pt.z_display_units_combo.setCurrentText(z_conf.get("display_units", "None"))

        self.pt.flip_axes_check.setChecked(config.get("flip_axes", False))

        # Datetime
        dt_conf = config.get("datetime", {})
        self.pt.custom_datetime_check.setChecked(dt_conf.get("enabled", False))
        self.pt.x_datetime_format_combo.setCurrentText(dt_conf.get("x_format_preset", "Auto"))
        self.pt.x_custom_datetime_input.setText(dt_conf.get("x_format_custom", ""))
        self.pt.y_datetime_format_combo.setCurrentText(dt_conf.get("y_format_preset", "Auto"))
        self.pt.y_custom_datetime_format_input.setText(dt_conf.get("y_format_custom", ""))
        self.pt.toggle_datetime_format()

    def _load_legend_config(self, config: dict):
        self.pt.legend_check.setChecked(config.get("enabled", True))
        self.pt.legend_loc_combo.setCurrentText(config.get("location", "best"))
        self.pt.legend_title_input.setText(config.get("title", ""))
        self.pt.legend_labels_input.setText(config.get("custom_labels", ""))
        self.pt.legend_size_spin.setValue(int(config.get("font_size", 10)))
        self.pt.legend_title_size_spin.setValue(int(config.get("title_font_size", 12)))
        self.pt.legend_columns_spin.setValue(int(config.get("columns", 1)))
        self.pt.legend_colspace_spin.setValue(float(config.get("column_spacing", 0.5)))
        self.pt.legend_frame_check.setChecked(config.get("frame", True))
        self.pt.legend_fancybox_check.setChecked(config.get("fancy_box", True))
        self.pt.legend_shadow_check.setChecked(config.get("shadow", False))
        self.pt.legend_edge_width_spin.setValue(float(config.get("edge_width", 0.8)))
        
        self.pt.legend_bg_color = config.get("bg_color") or "white"
        self.pt.legend_bg_label.setText(self.pt.legend_bg_color)
        self.pt.legend_bg_button.updateColors(base_color_hex=self.pt.legend_bg_color)
        
        self.pt.legend_edge_color = config.get("edge_color") or "black"
        self.pt.legend_edge_label.setText(self.pt.legend_edge_color)
        self.pt.legend_edge_button.updateColors(base_color_hex=self.pt.legend_edge_color)
        
        alpha = config.get("alpha", 0.8)
        self.pt.legend_alpha_slider.setValue(int(alpha * 100))

        self.pt.on_legend_toggle()

    def _load_grid_config(self, config: dict):
        self.pt.grid_check.setChecked(config.get("enabled", False))
        self.pt.independent_grid_check.setChecked(config.get("independent_axes", False))

        # Global settings
        glob = config.get("global", {})
        self.pt.grid_which_type_combo.setCurrentText(glob.get("which", "major"))
        self.pt.grid_axis_combo.setCurrentText(glob.get("axis", "both"))
        self.pt.global_grid_alpha_slider.setValue(int(glob.get("alpha", 0.5) * 100))
        
        g_color = glob.get("color", "gray")
        self.pt.global_grid_color = g_color
        if hasattr(self.pt.view, "global_grid_color_label"):
            self.pt.view.global_grid_color_label.setText(g_color)
            self.pt.view.global_grid_color_button.updateColors(base_color_hex=g_color)

        # A function to color buttons correctly
        def load_grid_section(prefix, conf):
            getattr(self.pt, f"{prefix}_grid_check").setChecked(conf.get("enabled", False))
            getattr(self.pt, f"{prefix}_grid_style_combo").setCurrentText(conf.get("style", "-"))
            getattr(self.pt, f"{prefix}_grid_linewidth_spin").setValue(float(conf.get("width", 0.8)))
            getattr(self.pt, f"{prefix}_grid_alpha_slider").setValue(int(conf.get("alpha", 0.5) * 100))

            color = conf.get("color", "gray")
            setattr(self.pt, f"{prefix}_grid_color", color)
            getattr(self.pt, f"{prefix}_grid_color_label").setText(color)
            getattr(self.pt, f"{prefix}_grid_color_button").updateColors(base_color_hex=color)
        
        if "x_major" in config: load_grid_section("x_major", config["x_major"])
        if "x_minor" in config: load_grid_section("x_minor", config["x_minor"])
        if "y_major" in config: load_grid_section("y_major", config["y_major"])
        if "y_minor" in config: load_grid_section("y_minor", config["y_minor"])
        
        self.pt.on_grid_toggle()
    
    def _load_advanced_config(self, config: dict):
        self.pt.multiline_custom_check.setChecked(config.get("multi_line_custom", False))
        self.pt.line_customizations = config.get("line_customizations", {})
        
        gl = config.get("global_line") or {}
        self.pt.linewidth_spin.setValue(float(gl.get("width", 1.5)))
        
        # Reverse map linestyle
        style_map = {'-': 'Solid', '--': 'Dashed', '-.': 'Dash-dot', ':': 'Dotted', 'None': 'None'}
        self.pt.linestyle_combo.setCurrentText(style_map.get(gl.get("style", "-"), "Solid"))
        
        self.pt.line_color = gl.get("color") or "blue"
        self.pt.line_color_label.setText(self.pt.line_color)
        self.pt.line_color_button.updateColors(base_color_hex=self.pt.line_color)
        
        gm = config.get("global_marker") or {}
        self.pt.marker_combo.setCurrentText(gm.get("shape", "None"))
        self.pt.marker_size_spin.setValue(int(gm.get("size", 6)))
        self.pt.marker_edge_width_spin.setValue(float(gm.get("edge_width", 1.0)))
        
        self.pt.marker_color = gm.get("color") or "blue"
        self.pt.marker_color_label.setText(self.pt.marker_color)
        self.pt.marker_color_button.updateColors(base_color_hex=self.pt.marker_color)
        
        self.pt.marker_edge_color = gm.get("edge_color") or "black"
        self.pt.marker_edge_label.setText(self.pt.marker_edge_color)
        self.pt.marker_edge_button.updateColors(base_color_hex=self.pt.marker_edge_color)
        
        self.pt.multibar_custom_check.setChecked(config.get("multi_bar_custom", False))
        self.pt.bar_customizations = config.get("bar_customizations", {})
        
        gb = config.get("global_bar") or {}
        self.pt.bar_width_spin.setValue(float(gb.get("width", 0.8)))
        self.pt.bar_edge_width_spin.setValue(float(gb.get("edge_width", 1.0)))
        
        self.pt.bar_color = gb.get("color") or "blue"
        self.pt.bar_color_label.setText(self.pt.bar_color)
        self.pt.bar_color_button.updateColors(base_color_hex=self.pt.bar_color)
        
        self.pt.bar_edge_color = gb.get("edge_color") or "black"
        self.pt.bar_edge_label.setText(self.pt.bar_edge_color)
        self.pt.bar_edge_button.updateColors(base_color_hex=self.pt.bar_edge_color)
        
        hist = config.get("histogram") or {}
        self.pt.histogram_bins_spin.setValue(int(hist.get("bins", 30)))
        self.pt.histogram_show_normal_check.setChecked(hist.get("show_normal", False))
        self.pt.histogram_show_kde_check.setChecked(hist.get("show_kde", False))
        
        self.pt.alpha_slider.setValue(int(config.get("global_alpha", 1.0) * 100))
        
        geb = config.get("global_error_bar") or {}
        if geb:
            self.pt.error_bars_combo.setCurrentText(geb.get("type", "None"))
            self.pt.error_bar_color = geb.get("color", "black")
            if hasattr(self.pt.view, "error_bar_color_label"):
                self.pt.view.error_bar_color_label.setText(self.pt.error_bar_color)
                self.pt.view.error_bar_color_button.updateColors(base_color_hex=self.pt.error_bar_color)
            if hasattr(self.pt.view, "error_bar_linewidth_spin"):
                self.pt.view.error_bar_linewidth_spin.setValue(float(geb.get("linewidth", 1.5)))
                self.pt.view.error_bar_capsize_spin.setValue(float(geb.get("capsize", 4.0)))
                self.pt.view.error_bar_alpha_slider.setValue(int(geb.get("alpha", 0.5) * 100))
                self.pt.view.error_bar_zorder_spin.setValue(int(geb.get("zorder", 10)))
        elif "scatter" in config and "error_bars" in config["scatter"]:
            self.pt.error_bars_combo.setCurrentText(config["scatter"].get("error_bars", "None"))
        
        scat = config.get("scatter") or {}
        self.pt.regression_line_check.setChecked(scat.get("show_regression", False))
        self.pt.confidence_interval_check.setChecked(scat.get("show_ci", False))
        self.pt.show_r2_check.setChecked(scat.get("show_r2", False))
        self.pt.show_rmse_check.setChecked(scat.get("show_rmse", False))
        self.pt.show_equation_check.setChecked(scat.get("show_equation", False))
        self.pt.error_bars_combo.setCurrentText(scat.get("error_bars", "None"))
        self.pt.confidence_level_spin.setValue(int(scat.get("ci_level", 95)))
        
        pie = config.get("pie") or {}
        self.pt.pie_show_percentages_check.setChecked(pie.get("show_percentages", True))
        self.pt.pie_start_angle_spin.setValue(int(pie.get("start_angle", 0)))
        self.pt.pie_explode_check.setChecked(pie.get("explode_first", False))
        self.pt.pie_explode_distance_spin.setValue(float(pie.get("explode_distance", 0.1)))
        self.pt.pie_shadow_check.setChecked(pie.get("shadow", False))
        self.pt.pie_donut_check.setChecked(pie.get("donut_enabled", False))
        self.pt.pie_donut_width_spin.setValue(float(pie.get("donut_width", 0.3)))

        self.pt.toggle_line_selector()
        self.pt.toggle_bar_selector()

    def _load_annotations_config(self, config: dict):
        # Text Annotations
        self.pt.annotations = config.get("text_annotations") or []
        self.pt.annotations_list.clear()
        for ann in self.pt.annotations:
            self.pt.annotations_list.addItem(f"{ann['text']} @ ({ann['x']:.2f}, {ann['y']:.2f})")

        # Reference lines
        ref_lines_cfg = config.get("reference_lines") or []
        self.pt.reference_line_manager.load_config(ref_lines_cfg)
        
        # Auto annotations
        auto_ann = config.get("auto_annotate") or {}
        self.pt.auto_annotate_check.setChecked(auto_ann.get("enabled", False))
        self.pt.auto_annotate_col_combo.setCurrentText(auto_ann.get("column", "Default (Y-value)"))
        
        # Textbox
        tb = config.get("textbox") or {}
        self.pt.textbox_enable_check.setChecked(tb.get("enabled", False))
        self.pt.textbox_content.setText(tb.get("content", ""))
        self.pt.textbox_position_combo.setCurrentText(tb.get("position", "upper right"))
        self.pt.textbox_style_combo.setCurrentText(tb.get("style", "Rounded"))
        
        self.pt.textbox_bg_color = tb.get("bg_color") or "white"
        self.pt.textbox_bg_label.setText(self.pt.textbox_bg_color)
        self.pt.textbox_bg_button.updateColors(base_color_hex=self.pt.textbox_bg_color)
        
        # Table
        tab = config.get("table") or {}
        self.pt.table_enable_check.setChecked(tab.get("enabled", False))
        self.pt.table_type_combo.setCurrentText(tab.get("type", "Summary Stats"))
        self.pt.table_location_combo.setCurrentText(tab.get("location", "bottom"))
        self.pt.table_auto_font_size_check.setChecked(tab.get("auto_font_size", True))
        self.pt.table_font_size_spin.setValue(int(tab.get("fontsize", 10)))
        self.pt.table_scale_spin.setValue(float(tab.get("scale", 1.2)))
        
        self.pt.toggle_table_controls()
    
    def _load_geospatial_config(self, config: dict) -> None:
        self.pt.geo_target_crs_input.setText(config.get("target_crs", ""))
        
        bmap = config.get("basemap", {})
        self.pt.geo_basemap_check.setChecked(bmap.get("enabled", False))
        self.pt.geo_basemap_style_combo.setCurrentText(bmap.get("source", "OpenStreetMap"))
        
        choro = config.get("choropleth", {})
        self.pt.geo_scheme_combo.setCurrentText(choro.get("scheme", "None"))
        self.pt.geo_k_spin.setValue(int(choro.get("k", 5)))
        
        leg = config.get("legend", {})
        self.pt.geo_legend_check.setChecked(leg.get("enabled", False))
        self.pt.geo_legend_loc_combo.setCurrentText(leg.get("location", "vertical"))
        self.pt.geo_use_divider_check.setChecked(leg.get("use_divider", False))
        self.pt.geo_cax_check.setChecked(leg.get("cax_enabled", False))
        self.pt.geo_axis_off_check.setChecked(leg.get("axis_off", False))
        
        missing = config.get("missing_data", {})
        self.pt.geo_missing_label_input.setText(missing.get("label", ""))
        self.pt.geo_missing_color = missing.get("color", "lightgray")
        if hasattr(self.pt, "geo_missing_color_label"):
            self.pt.geo_missing_color_label.setText(self.pt.geo_missing_color)
            self.pt.geo_missing_color_btn.updateColors(base_color_hex=self.pt.geo_missing_color)
        self.pt.geo_hatch_combo.setCurrentText(missing.get("hatch", "None"))
        
        bound = config.get("boundary", {})
        self.pt.geo_boundary_check.setChecked(bound.get("enabled", False))
        self.pt.geo_edge_color = bound.get("color", "black")
        if hasattr(self.pt, "geo_edge_color_label"):
            self.pt.geo_edge_color_label.setText(self.pt.geo_edge_color)
            self.pt.geo_edge_color_btn.updateColors(base_color_hex=self.pt.geo_edge_color)
        self.pt.geo_linewidth_spin.setValue(float(bound.get("linewidth", 1.0)))