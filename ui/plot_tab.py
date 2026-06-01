# ui/plot_tab.py
import threading
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING

import pandas as pd
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from matplotlib.colors import to_hex
from PyQt6.QtWidgets import QColorDialog, QApplication, QMessageBox, QListWidgetItem, QListWidget
from PyQt6.QtCore import QTimer, QSize, Qt, pyqtSignal, QThreadPool
from PyQt6.QtGui import QColor, QIcon

from core.plot_engine import PlotEngine
from core.data_handler import DataHandler
from core.resource_loader import get_resource_path
from core.code_exporter import CodeExporter
from core.plot_config_manager import PlotConfigManager
from ui.SubplotOverlay import SubplotOverlay
from ui.animations import SavePlotAnimation, PlotGeneratedAnimation, PlotClearedAnimation
from ui.status_bar import StatusBar
from ui.dialogs import ProgressDialog, PlotExportDialog
from ui.plot_tab_ui import PlotTabUI
from ui.managers.plot_tab_managers import ThemeManager, ScriptManager, SubplotManager, AnnotationManager, CanvasInteractionManager, PlotFormattingManager, ReferenceLineManager, ColorManager
from ui.widgets import ColorBlindnessEffect
if TYPE_CHECKING:
    from ui.plot_tab_ui import PlotSettingsPanel

class PlotTab(PlotTabUI):
    """Tab for creating and customizing plots"""
    
    brush_selection_made = pyqtSignal(set)
    
    def __init__(self, data_handler: DataHandler, status_bar: StatusBar, subset_manager=None) -> None:
        super().__init__()
        
        self.view: PlotSettingsPanel | None = None
        self.data_handler: DataHandler = data_handler
        self.status_bar: StatusBar = status_bar
        self.subset_manager = subset_manager
        if self.subset_manager:
            self.refresh_subset_list()
        self.plot_engine = PlotEngine()
        self.current_config = {}
        self.code_exporter = CodeExporter()
        self.script_manager = ScriptManager(self)

        self.current_plot_type_name = "Line"
        self.dragged_annotation = None
        self.ignore_next_click = False
        self._pan_axes = None
        self._pan_start = None
        self._pan_start_xlim = None
        self._pan_start_ylim = None
        self.config_manager = PlotConfigManager(self)
        self.thread_pool = QThreadPool.globalInstance()
        
        self._is_data_dirty = False
        self._is_clearing = False
        self.AUTO_UPDATE_THRESHOLD = 2000
        self.style_update_timer = QTimer()
        self.style_update_timer.setSingleShot(True)
        self.style_update_timer.setInterval(300)
        self.style_update_timer.timeout.connect(self._fast_render)
        
        self.bg_color = "white"
        self.face_color = "white"

        self.global_spine_color = "black"
        self.top_spine_color = "black"
        self.bottom_spine_color = "black"
        self.left_spine_color = "black"
        self.right_spine_color = "black"

        self.line_color = None
        self.marker_color = None
        self.marker_edge_color = None
        self.bar_color = None
        self.bar_edge_color = None
        self.annotation_color = "black"
        self.annotation_bg_color = "wheat"
        self.auto_annotation_color = "black"
        self.textbox_bg_color = "white"
        self.legend_bg_color = "white"
        self.legend_edge_color = "black"
        self.global_grid_color = "gray"
        self.x_major_grid_color = "gray"
        self.x_minor_grid_color = "lightgray"
        self.y_major_grid_color = "gray"
        self.y_minor_grid_color = "lightgray"
        self.geo_missing_color = "lightgray"
        self.geo_edge_color = "black"
        self.error_bar_color = "black"

        self.line_customizations = {}
        self.bar_customizations = {}
        
        # Categories
        self.plot_categories = {
            "Basic and Relational": ["Line", "Scatter", "Bar", "Area", "Pie", "Stem", "Stairs"],
            "Distribution": ["Histogram", "Box", "Violin", "KDE", "ECDF", "Count Plot", "Eventplot"],
            "2D, Gridded and 3D": ["Heatmap", "Hexbin", "2D Density", "2D Histogram", "Image Show (imshow)", "pcolormesh", "Contour", "Contourf", "Stackplot", "3D Line", "3D Scatter", "3D Surface"],
            "Vector Fields": ["Barbs", "Quiver", "Streamplot"],
            "Triangulation": ["Tricontour", "Tricontourf", "Tripcolor", "Triplot"],
            "Geospatial": ["GeoSpatial"]
        }
        
        # Create canvas and toolbar
        self.plot_engine.create_figure()
        canvas = FigureCanvas(self.plot_engine.get_figure())
        toolbar = NavigationToolbar(canvas, self)
        
        self.init_ui(canvas, toolbar)
        
        self.view = self.settings_panel
        
        #populate box in general tab with icons
        #
        self._populate_plot_toolbox()

        self.selection_overlay = SubplotOverlay(self.canvas)
        self.canvas.mpl_connect("resize_event", self.on_canvas_resize)
        
        # Load initial data
        self.update_column_combo()
        
        self._select_plot_in_toolbox("Line")
        
        self.set_empty_state_greeting()

        # Initialize the plot tab managers
        self.theme_manager = ThemeManager(self)
        self.subplot_manager = SubplotManager(self)
        self.annotation_manager = AnnotationManager(self)
        self.reference_line_manager = ReferenceLineManager(self)
        self.canvas_interaction_manager = CanvasInteractionManager(self)
        self.formatting_manager = PlotFormattingManager(self)
        self.color_manager = ColorManager(self)
        
        # Caching
        self._last_data_signature = None
        self._last_viz_signature = None
        self._cached_active_df = None
        
        # Connect all signals to their logic methods
        self._connect_signals()

    def _connect_signals(self) -> None:
        """Connect all UI widget signals to their logic"""
        self._connect_main_controls()
        self._connect_basic_tab_signals()
        self._connect_appearance_tab_signals()
        self._connect_axes_tab_signals()
        self._connect_legend_grid_tab_signals()
        self._connect_advanced_tab_signals()
        self._connect_annotation_tab_signals()
        self._connect_geospatial_tab_signals()
        self._connect_theme_controls()
    
    def _connect_main_controls(self) -> None:
        """Connect the main action buttons and canvas events"""
        #  Main Buttons 
        self.plot_button.clicked.connect(self.generate_plot)
        self.editor_button.clicked.connect(self.script_manager.open_script_editor)
        self.clear_button.clicked.connect(self.clear_plot)
        self.save_plot_button.clicked.connect(self.save_plot_image)

        #editor sync
        self.view.x_column.currentTextChanged.connect(self.script_manager.sync_script_if_open)
    
    def _connect_basic_tab_signals(self) -> None:
        """Connect signals for the General tab """
        self.view.multi_y_check.stateChanged.connect(self.toggle_multi_y)
        self.view.select_all_y_btn.clicked.connect(self.select_all_y_columns)
        self.view.clear_all_y_btn.clicked.connect(self.clear_all_y_columns)
        
        self.view.x_column.currentTextChanged.connect(self.on_data_changed)
        self.view.y_column.currentTextChanged.connect(self.on_data_changed)
        self.view.y_columns_list.itemSelectionChanged.connect(self.on_data_changed)
        self.view.hue_column.currentTextChanged.connect(self.on_data_changed)
        self.view.subset_combo.currentIndexChanged.connect(self.on_data_changed)
        self.view.quick_filter_input.returnPressed.connect(self.on_data_changed)
        self.view.z_column.currentTextChanged.connect(self.on_data_changed)

        self.subplot_manager.connect_signals()

        self.view.use_subset_check.stateChanged.connect(self.use_subset)
        self.view.secondary_y_check.stateChanged.connect(lambda state: self._toggle_secondary_input(bool(state)))
        self.view.secondary_plot_type_combo.currentTextChanged.connect(lambda _: self._update_customization_visibility(self.current_plot_type_name))
    
    def _connect_appearance_tab_signals(self) -> None:
        """Connect signals for the Appearance tab"""
        self.view.individual_spines_check.stateChanged.connect(self.toggle_individual_spines)
        self.view.all_spines_btn.clicked.connect(self.preset_all_spines)
        self.view.box_only_btn.clicked.connect(self.preset_box_only)
        self.view.no_spines_btn.clicked.connect(self.preset_no_spines)
        self.view.width_spin.valueChanged.connect(lambda: self.formatting_manager.setup_plot_figure(clear=False))
        self.view.height_spin.valueChanged.connect(lambda: self.formatting_manager.setup_plot_figure(clear=False))
        self.view.colorblind_check.stateChanged.connect(self.update_colorblind_simulation)
        self.view.colorblind_type_combo.currentTextChanged.connect(self.update_colorblind_simulation)
        
        self.view.title_input.textChanged.connect(self.on_style_changed)
        self.view.title_size_spin.valueChanged.connect(self.on_style_changed)
        self.view.title_weight_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.title_position_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.title_check.stateChanged.connect(self.on_style_changed)
        
        self.view.xlabel_input.textChanged.connect(self.on_style_changed)
        self.view.xlabel_size_spin.valueChanged.connect(self.on_style_changed)
        self.view.xlabel_weight_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.xlabel_check.stateChanged.connect(self.on_style_changed)
        
        self.view.ylabel_input.textChanged.connect(self.on_style_changed)
        self.view.ylabel_size_spin.valueChanged.connect(self.on_style_changed)
        self.view.ylabel_weight_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.ylabel_check.stateChanged.connect(self.on_style_changed)
        
        self.view.zlabel_check.stateChanged.connect(self.on_style_changed)
        self.view.zlabel_input.textChanged.connect(self.on_style_changed)
        self.view.zlabel_size.valueChanged.connect(self.on_style_changed)
        self.view.zlabel_weight.currentTextChanged.connect(self.on_style_changed)
        
        self.view.font_family_combo.currentFontChanged.connect(self.on_style_changed)
        self.view.style_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.global_spine_width_spin.valueChanged.connect(self.on_style_changed)
        self.view.top_spine_width_spin.valueChanged.connect(self.on_style_changed)
        self.view.bottom_spine_width_spin.valueChanged.connect(self.on_style_changed)
        self.view.left_spine_width_spin.valueChanged.connect(self.on_style_changed)
        self.view.right_spine_width_spin.valueChanged.connect(self.on_style_changed)
        self.view.palette_combo.currentTextChanged.connect(self._on_palette_changed)
        
        self.view.camera_elevation_spin.valueChanged.connect(self.on_style_changed)
        self.view.camera_azimuth_spin.valueChanged.connect(self.on_style_changed)
    
    def _connect_axes_tab_signals(self) -> None:
        """Connect signals for the Axes tab"""
        self.view.x_auto_check.stateChanged.connect(lambda: self.view.x_min_spin.setEnabled(not self.view.x_auto_check.isChecked()))
        self.view.x_auto_check.stateChanged.connect(lambda: self.view.x_max_spin.setEnabled(not self.view.x_auto_check.isChecked()))
        self.view.y_auto_check.stateChanged.connect(lambda: self.view.y_min_spin.setEnabled(not self.view.y_auto_check.isChecked()))
        self.view.y_auto_check.stateChanged.connect(lambda: self.view.y_max_spin.setEnabled(not self.view.y_auto_check.isChecked()))
        self.view.z_auto_check.stateChanged.connect(lambda: self.view.z_min_spin.setEnabled(not self.view.z_auto_check.isChecked()))
        self.view.z_auto_check.stateChanged.connect(lambda: self.view.z_max_spin.setEnabled(not self.view.z_auto_check.isChecked()))
        
        self.view.custom_datetime_check.stateChanged.connect(self.toggle_datetime_format)
        self.view.custom_datetime_check.stateChanged.connect(self.on_data_changed)
        self.view.x_datetime_format_combo.currentTextChanged.connect(self.on_x_datetime_format_changed)
        self.view.y_datetime_format_combo.currentTextChanged.connect(self.on_y_datetime_format_changed)
        self.view.x_custom_datetime_input.textChanged.connect(self.on_data_changed)
        self.view.y_custom_datetime_format_input.textChanged.connect(self.on_data_changed)
        
        self.view.flip_axes_check.stateChanged.connect(self.on_data_changed)
        self.view.x_auto_check.stateChanged.connect(self.on_style_changed)
        self.view.y_auto_check.stateChanged.connect(self.on_style_changed)
        self.view.x_min_spin.valueChanged.connect(self.on_style_changed)
        self.view.x_max_spin.valueChanged.connect(self.on_style_changed)
        self.view.y_min_spin.valueChanged.connect(self.on_style_changed)
        self.view.y_max_spin.valueChanged.connect(self.on_style_changed)
        self.view.xtick_label_size_spin.valueChanged.connect(self.on_style_changed)
        self.view.ytick_label_size_spin.valueChanged.connect(self.on_style_changed)
        self.view.xtick_rotation_spin.valueChanged.connect(self.on_style_changed)
        self.view.ytick_rotation_spin.valueChanged.connect(self.on_style_changed)
        self.view.x_max_ticks_spin.valueChanged.connect(self.on_style_changed)
        self.view.y_max_ticks_spin.valueChanged.connect(self.on_style_changed)
        self.view.x_show_minor_ticks_check.stateChanged.connect(self.on_style_changed)
        self.view.y_show_minor_ticks_check.stateChanged.connect(self.on_style_changed)
        self.view.x_major_tick_direction_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.y_major_tick_direction_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.x_major_tick_width_spin.valueChanged.connect(self.on_style_changed)
        self.view.y_major_tick_width_spin.valueChanged.connect(self.on_style_changed)
        self.view.x_scale_combo.currentTextChanged.connect(self.on_data_changed)
        self.view.y_scale_combo.currentTextChanged.connect(self.on_data_changed)
        self.view.z_scale_combo.currentTextChanged.connect(self.on_data_changed)
        self.view.x_display_units_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.y_display_units_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.z_display_units_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.x_top_axis_check.stateChanged.connect(self.on_style_changed)
        self.view.x_invert_axis_check.stateChanged.connect(self.on_style_changed)
        self.view.y_invert_axis_check.stateChanged.connect(self.on_style_changed)
        self.view.z_invert_axis_check.stateChanged.connect(self.on_style_changed)
        
        self.view.z_auto_check.stateChanged.connect(self.on_style_changed)
        self.view.z_min_spin.valueChanged.connect(self.on_style_changed)
        self.view.z_max_spin.valueChanged.connect(self.on_style_changed)
        self.view.ztick_label_size_spin.valueChanged.connect(self.on_style_changed)
        self.view.ztick_rotation_spin.valueChanged.connect(self.on_style_changed)
        self.view.z_max_ticks_spin.valueChanged.connect(self.on_style_changed)
        self.view.z_show_minor_ticks_check.stateChanged.connect(self.on_style_changed)
        self.view.z_major_tick_direction_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.z_major_tick_width_spin.valueChanged.connect(self.on_style_changed)
        self.view.z_minor_tick_direction_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.z_minor_tick_width_spin.valueChanged.connect(self.on_style_changed)
        
    def _connect_legend_grid_tab_signals(self) -> None:
        """Connect signals for the Legend and Grid tab"""
        self.view.legend_check.stateChanged.connect(self.on_legend_toggle)
        self.view.legend_alpha_slider.valueChanged.connect(lambda v: self.view.legend_alpha_label.setText(f"{v}%"))
        self.view.grid_check.stateChanged.connect(self.on_grid_toggle)
        self.view.global_grid_alpha_slider.valueChanged.connect(lambda v: self.view.global_grid_alpha_label.setText(f"{v}%"))
        self.view.independent_grid_check.stateChanged.connect(self.on_independent_grid_toggle)
        self.view.x_major_grid_alpha_slider.valueChanged.connect(lambda v: self.view.x_major_grid_alpha_label.setText(f"{v}%"))
        self.view.x_minor_grid_alpha_slider.valueChanged.connect(lambda v: self.view.x_minor_grid_alpha_label.setText(f"{v}%"))
        self.view.y_major_grid_alpha_slider.valueChanged.connect(lambda v: self.view.y_major_grid_alpha_label.setText(f"{v}%"))
        self.view.y_minor_grid_alpha_slider.valueChanged.connect(lambda v: self.view.y_minor_grid_alpha_label.setText(f"{v}%"))
        
        self.view.legend_loc_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.legend_title_input.textChanged.connect(self.on_style_changed)
        self.view.legend_title_size_spin.valueChanged.connect(self.on_style_changed)
        self.view.legend_labels_input.textChanged.connect(self.on_style_changed)
        self.view.legend_size_spin.valueChanged.connect(self.on_style_changed)
        self.view.legend_columns_spin.valueChanged.connect(self.on_style_changed)
        self.view.legend_colspace_spin.valueChanged.connect(self.on_style_changed)
        self.view.legend_frame_check.stateChanged.connect(self.on_style_changed)
        self.view.legend_fancybox_check.stateChanged.connect(self.on_style_changed)
        self.view.legend_shadow_check.stateChanged.connect(self.on_style_changed)
        self.view.legend_edge_width_spin.valueChanged.connect(self.on_style_changed)
        self.view.legend_alpha_slider.valueChanged.connect(self.on_style_changed)
        self.view.grid_which_type_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.grid_axis_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.global_grid_alpha_slider.valueChanged.connect(self.on_style_changed)
        self.view.x_major_grid_check.stateChanged.connect(self.on_style_changed)
        self.view.x_major_grid_style_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.x_major_grid_linewidth_spin.valueChanged.connect(self.on_style_changed)
        self.view.x_major_grid_alpha_slider.valueChanged.connect(self.on_style_changed)
        self.view.x_minor_grid_check.stateChanged.connect(self.on_style_changed)
        self.view.x_minor_grid_style_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.x_minor_grid_linewidth_spin.valueChanged.connect(self.on_style_changed)
        self.view.x_minor_grid_alpha_slider.valueChanged.connect(self.on_style_changed)
        self.view.y_major_grid_check.stateChanged.connect(self.on_style_changed)
        self.view.y_major_grid_style_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.y_major_grid_linewidth_spin.valueChanged.connect(self.on_style_changed)
        self.view.y_major_grid_alpha_slider.valueChanged.connect(self.on_style_changed)
        self.view.y_minor_grid_check.stateChanged.connect(self.on_style_changed)
        self.view.y_minor_grid_style_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.y_minor_grid_linewidth_spin.valueChanged.connect(self.on_style_changed)
        self.view.y_minor_grid_alpha_slider.valueChanged.connect(self.on_style_changed)
        
    def _connect_advanced_tab_signals(self) -> None:
        """Connect signals for the customization tab"""
        self.view.multiline_custom_check.stateChanged.connect(self.toggle_line_selector)
        self.view.line_selector_combo.currentTextChanged.connect(self.on_line_selected)
        self.view.multibar_custom_check.stateChanged.connect(self.toggle_bar_selector)
        self.view.bar_selector_combo.currentTextChanged.connect(self.on_bar_selected)
        self.view.bar_edge_width_spin.valueChanged.connect(self._update_bar_customization_live)
        self.view.alpha_slider.valueChanged.connect(lambda v: self.view.alpha_label.setText(f"{v}%"))
        
        # Style connections
        self.view.linewidth_spin.valueChanged.connect(self.on_style_changed)
        self.view.linestyle_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.marker_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.marker_size_spin.valueChanged.connect(self.on_style_changed)
        self.view.marker_edge_width_spin.valueChanged.connect(self.on_style_changed)
        self.view.alpha_slider.valueChanged.connect(self.on_style_changed)
        
        # Data connections
        self.view.histogram_bins_spin.valueChanged.connect(self.on_data_changed)
        self.view.histogram_show_normal_check.stateChanged.connect(self.on_data_changed)
        self.view.histogram_show_kde_check.stateChanged.connect(self.on_data_changed)
        self.view.bar_width_spin.valueChanged.connect(self.on_data_changed)
        self.view.regression_line_check.stateChanged.connect(self.on_data_changed)
        self.view.regression_type_combo.currentTextChanged.connect(self.on_data_changed)
        self.view.poly_degree_spin.valueChanged.connect(self.on_data_changed)
        self.view.confidence_interval_check.stateChanged.connect(self.on_data_changed)
        self.view.show_r2_check.stateChanged.connect(self.on_data_changed)
        self.view.show_rmse_check.stateChanged.connect(self.on_data_changed)
        self.view.show_equation_check.stateChanged.connect(self.on_data_changed)
        self.view.confidence_level_spin.valueChanged.connect(self.on_data_changed)
        self.view.pie_show_percentages_check.stateChanged.connect(self.on_data_changed)
        self.view.pie_start_angle_spin.valueChanged.connect(self.on_data_changed)
        self.view.pie_explode_check.stateChanged.connect(self.on_data_changed)
        self.view.pie_explode_distance_spin.valueChanged.connect(self.on_data_changed)
        self.view.pie_shadow_check.stateChanged.connect(self.on_data_changed)
        self.view.pie_donut_check.stateChanged.connect(self.on_data_changed)
        self.view.pie_donut_width_spin.valueChanged.connect(self.on_data_changed)
        self.view.error_bars_combo.currentTextChanged.connect(self.on_data_changed)

        self.view.error_bar_linewidth_spin.valueChanged.connect(self.on_data_changed)
        self.view.error_bar_capsize_spin.valueChanged.connect(self.on_data_changed)
        self.view.error_bar_alpha_slider.valueChanged.connect(lambda v: self.view.error_bar_alpha_label.setText(f"{v}%"))
        self.view.error_bar_alpha_slider.valueChanged.connect(self.on_data_changed)
        self.view.error_bar_zorder_spin.valueChanged.connect(self.on_data_changed)
        
    def _connect_annotation_tab_signals(self) -> None:
        """Connect signals for the Annotations tab"""
        self.annotation_manager.connect_signals()
        self.reference_line_manager.connect_signals()
        self.view.table_enable_check.stateChanged.connect(self.on_style_changed)
        self.view.table_type_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.table_location_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.table_auto_font_size_check.stateChanged.connect(self.on_style_changed)
        self.view.table_font_size_spin.valueChanged.connect(self.on_style_changed)
        self.view.table_scale_spin.valueChanged.connect(self.on_style_changed)

    def _connect_geospatial_tab_signals(self) -> None:
        """Connect signals for the Geospatial tab"""
        self.view.geo_scheme_combo.currentTextChanged.connect(self._on_geospatial_projection_changed)
        self.view.geo_k_spin.valueChanged.connect(self._on_geospatial_projection_changed)
        self.view.geo_legend_check.stateChanged.connect(self._on_geospatial_projection_changed)
        self.view.geo_legend_loc_combo.currentTextChanged.connect(self._on_geospatial_projection_changed)
        self.view.geo_use_divider_check.stateChanged.connect(self._on_geospatial_projection_changed)
        self.view.geo_cax_check.stateChanged.connect(self._on_geospatial_projection_changed)
        self.view.geo_axis_off_check.stateChanged.connect(self._on_geospatial_projection_changed)
        self.view.geo_missing_label_input.textChanged.connect(self._on_geospatial_projection_changed)
        self.view.geo_hatch_combo.currentTextChanged.connect(self._on_geospatial_projection_changed)
        self.view.geo_boundary_check.stateChanged.connect(self._on_geospatial_projection_changed)
        self.view.geo_linewidth_spin.valueChanged.connect(self._on_geospatial_projection_changed)
        self.view.geo_target_crs_input.editingFinished.connect(self._on_geospatial_projection_changed)
        self.view.geo_basemap_check.stateChanged.connect(self._on_geospatial_projection_changed)
        self.view.geo_basemap_style_combo.currentTextChanged.connect(self._on_geospatial_projection_changed)

    def _connect_theme_controls(self) -> None:
        """Connect signals for Theme management"""
        self.theme_manager.connect_signals()
        self.color_manager.connect_signals()
    
    def showEvent(self, event) -> None:
        """Triggered on tab visibility. Clears selectons from plot"""
        super().showEvent(event)
        
        if getattr(self, "is_data_dirty", False):
            df = self.get_active_dataframe()
            if df is not None and len(df) <= self.AUTO_UPDATE_THRESHOLD:
                self.style_update_timer.start()
            elif hasattr(self, "selection_overlay"):
                self.selection_overlay.show_update_required(True)

        if self.canvas_interaction_manager.span_selector is not None:
            if hasattr(self.canvas_interaction_manager.span_selector, "clear"):
                self.canvas_interaction_manager.span_selector.clear()
            elif hasattr(self.canvas_interaction_manager.span_selector, "set_visible"):
                self.canvas_interaction_manager.span_selector.set_visible(False)
            
            if hasattr(self, "canvas") and self.canvas is not None:
                self.canvas.draw_idle()

    def _populate_plot_toolbox(self):
        while self.view.plot_type.count() > 0:
            self.view.plot_type.removeItem(0)
        
        self.category_lists = []
        for category, plot_names in self.plot_categories.items():
            list_widget = QListWidget()
            list_widget.setViewMode(QListWidget.ViewMode.IconMode)
            list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
            list_widget.setMovement(QListWidget.Movement.Static)
            
            list_widget.setGridSize(QSize(105, 100))
            list_widget.setSpacing(8)
            list_widget.setIconSize(QSize(48, 48))

            list_widget.itemClicked.connect(self._on_plot_list_item_clicked)

            for plot_name in plot_names:
                if plot_name in self.plot_engine.AVAILABLE_PLOTS:
                    icon_key = self.plot_engine.AVAILABLE_PLOTS[plot_name]
                    icon_path = get_resource_path(f"icons/plot_tab/plots/{icon_key}.png")

                    item = QListWidgetItem(QIcon(icon_path), plot_name)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    item.setToolTip(self.plot_engine.PLOT_DESCRIPTIONS.get(plot_name, ""))
                    list_widget.addItem(item)
            
            self.view.plot_type.addItem(list_widget, category)
            self.category_lists.append(list_widget)
    
    def _on_plot_list_item_clicked(self, item):
        if not item: return

        plot_type = item.text()
        self.current_plot_type_name = plot_type
        self.view.current_plot_label.setText(f"Selected Plot: {plot_type}")

        for list_w in self.category_lists:
            if list_w != item.listWidget():
                list_w.clearSelection()
        
        self.on_plot_type_changed(plot_type)
        self.on_data_changed()
        self.script_manager.sync_script_if_open()
    
    def _select_plot_in_toolbox(self, plot_type_name):
        self.current_plot_type_name = plot_type_name
        self.current_plot_label.setText(f"Selected Plot: {plot_type_name}")

        for i, (category, names) in enumerate(self.plot_categories.items()):
            if plot_type_name in names:
                self.view.plot_type.setCurrentIndex(i)
                list_widget = self.category_lists[i]

                items = list_widget.findItems(plot_type_name, Qt.MatchFlag.MatchExactly)
                if items:
                    list_widget.setCurrentItem(items[0])
                    for list_w in self.category_lists:
                        if list_w != list_widget:
                            list_w.clearSelection()
                    self.on_plot_type_changed(plot_type_name)
                break
    
    def toggle_individual_spines(self):
        """Toggles the customization of spines for each"""
        checked  = self.view.individual_spines_check.isChecked()
        self.view.individual_spines_container.setVisible(checked)
        self.on_style_changed()
    
    def use_subset(self):
        """Active subset on change"""
        subset_enabled = self.view.use_subset_check.isChecked()
    
    def on_canvas_resize(self, event):
        self.subplot_manager.update_overlay(is_resize=True)
        self.formatting_manager.setup_plot_figure(clear=False)
        self.canvas.draw_idle()

    def save_plot_image(self) -> None:
        """Save the plot to a file. This is the quick method for most common choices: png, pdf, and svg files"""
        if self.plot_engine.current_figure is None:
            QMessageBox.warning(self, "Warning", "No plot available to save")
            return
        
        try:
            default_export_dpi = 300
            
            overlay_was_visible: bool = False
            if hasattr(self, "selection_overlay") and self.selection_overlay.isVisible():
                overlay_was_visible = True
                self.selection_overlay.hide()
                
            preview_pixmap = self.canvas.grab()
            if overlay_was_visible:
                self.selection_overlay.show()
            
            fig_width, fig_height = self.plot_engine.current_figure.get_size_inches()
            
            dialog = PlotExportDialog(current_dpi=default_export_dpi, preview_pixmap=preview_pixmap, fig_width=fig_width, fig_height=fig_height, parent=self)
            if dialog.exec():
                config = dialog.get_config()
                filepath: str | None = config.get("filepath")

                if filepath:
                    kwargs = {
                        "dpi": config["dpi"],
                        "bbox_inches": "tight" if config["tight_layout"] else None,
                        "transparent": config["transparent"]
                    }
                    if not config["transparent"]:
                        kwargs["facecolor"] = self.bg_color
                    
                    original_size = self.plot_engine.current_figure.get_size_inches()
                    target_size = (config["width"], config["height"])
                    
                    try:
                        self.plot_engine.current_figure.set_size_inches(*target_size)
                        self.plot_engine.current_figure.savefig(filepath, **kwargs)
                    finally:
                        self.plot_engine.current_figure.set_size_inches(*original_size)
                        self.canvas.draw_idle()
                SavePlotAnimation(self).start(self)
                self.status_bar.log_action(f"Plot saved to {filepath}", level="SUCCESS")
                QMessageBox.information(self, "Success", f"Plot saved successfully to:\n{filepath}")
        except PermissionError:
            self.status_bar.log("Permission denied: Target file might be open in another program.", "ERROR")
            QMessageBox.critical(
                self, 
                "Save Error", 
                "Cannot save the file.\n\nIf you are trying to overwrite an existing file (like a PDF), please ensure it is closed in your viewer/editor before saving."
            )
        except Exception as ExportPlotAsImageError:
            self.status_bar.log(f"Failed to save plot: {str(ExportPlotAsImageError)}", "ERROR")
            QMessageBox.critical(self, "Save Error", f"Could not save plot:\n{str(ExportPlotAsImageError)}")
            traceback.print_exc()

    def activate_subset(self, subset_name: str):
        """Activates the 'Use Subset' checkbox and selects the selected subset"""
        if not self.subset_manager:
            self.status_bar.log("Cannot activate subset: SubsetManager not available", "ERROR")
            return
        
        self.refresh_subset_list()

        target_index = -1
        for i in range(self.view.subset_combo.count()):
            item_data = self.view.subset_combo.itemData(i)
            if item_data == subset_name:
                target_index = i
                break
        
        if target_index == -1:
            self.status_bar.log(f"Cannot activate subset: Subset '{subset_name}' not found", "WARNING")
            return

        self.view.use_subset_check.setChecked(True)
        self.view.subset_combo.setCurrentIndex(target_index)

        self.status_bar.log_action(
            f"Activated subset: '{subset_name}' for ploting",
            details={"subset_name": subset_name, "source": "DataTab"},
            level="INFO"
        )

    def set_subset_manager(self, subset_manager) -> None:
        """Set the subset manager reference"""
        self.subset_manager = subset_manager
        self.refresh_subset_list()

    def refresh_subset_list(self):
        """Refresh the list of available subsets"""
        if not self.subset_manager:
            self.status_bar.log("Warning: Subset manager not available", "WARNING")
            return
        
        if not hasattr(self, 'subset_combo'):
            self.status_bar.log("Warning: Subset combobox not initialized", "WARNING")
            return
        
        try:
            self.view.subset_combo.blockSignals(True)
            self.view.subset_combo.clear()
            self.view.subset_combo.addItem("(Full Dataset)")
            
            for name in self.subset_manager.list_subsets():
                subset = self.subset_manager.get_subset(name)
                self.view.subset_combo.addItem(f"{name} ({subset.row_count} rows)", userData=name)
            
            self.view.subset_combo.blockSignals(False)
            
            subset_count = len(self.subset_manager.list_subsets())
            if subset_count > 0:
                self.status_bar.log(f"Refreshed subset list: {subset_count} subsets available", "INFO")
        except Exception as RefreshSubsetListError:
            print(f"Warning: Could not refresh subset list: {RefreshSubsetListError}")
    
    def get_active_dataframe(self):
        """Get the active dataframe (full dataset or selected subset)"""
        # Check if subset UI exists
        if not hasattr(self.view, 'use_subset_check') or not hasattr(self.view, 'subset_combo'):
            return self.data_handler.df
        
        # Check if user wants to use subset
        if not self.view.use_subset_check.isChecked():
            return self.data_handler.df
        
        # Check if subset manager is available
        if not self.subset_manager:
            self.status_bar.log("Subset manager not available, using full dataset", "WARNING")
            return self.data_handler.df
        
        # Get selected subset name
        subset_name = self.view.subset_combo.currentData()
        if not subset_name:
            return self.data_handler.df
        
        # Try to apply subset
        try:
            subset_df = self.subset_manager.apply_subset(self.data_handler.df, subset_name)
            self.status_bar.log(f"Using subset: {subset_name} ({len(subset_df)} rows)", "INFO")
            return subset_df
        except Exception as ApplySubsetToActiveDataFrameError:
            self.status_bar.log(f"Failed to apply subset, using full dataset: {str(ApplySubsetToActiveDataFrameError)}", "WARNING")
            return self.data_handler.df
        
    
    def toggle_bar_selector(self) -> None:
        """Show/hide bar selection to customize more than one bar"""
        is_enabled = self.view.multibar_custom_check.isChecked()
        self.view.bar_selector_label.setVisible(is_enabled)
        self.view.bar_selector_combo.setVisible(is_enabled)

        if is_enabled:
            self._initialize_all_bar_customizations()
            self.update_bar_selector()
        self.on_style_changed()
    
    def _initialize_all_bar_customizations(self) -> None:
        """Initialize customizations dictionary for all bars with their current visual state."""
        if not self.plot_engine.current_ax or not self.plot_engine.current_ax.containers:
            return
        
        for i, container in enumerate(self.plot_engine.current_ax.containers):
            if not hasattr(container, "patches") or not container.patches:
                continue
            label = container.get_label()
            if not label or label.startswith("_"):
                handles, labels = self.plot_engine.current_ax.get_legend_handles_labels()
                label = labels[i] if i < len(labels) else f"Bar Series {i+1}"
            
            if label not in self.bar_customizations:
                patch = container.patches[0]
                self.bar_customizations[label] = {
                    "facecolor": to_hex(patch.get_facecolor()) if patch.get_facecolor() else None,
                    "edgecolor": to_hex(patch.get_edgecolor()) if patch.get_edgecolor() else None,
                    "linewidth": patch.get_linewidth(),
                    "alpha": patch.get_alpha() if patch.get_alpha() is not None else 1.0
                }
    def update_bar_selector(self, preserve_selection: bool = False) -> None:
        """Update the bar selection tool with the current patches in the plot"""
        current_text = self.view.bar_selector_combo.currentText()
        self.view.bar_selector_combo.blockSignals(True)
        self.view.bar_selector_combo.clear()

        if self.plot_engine.current_ax and self.plot_engine.current_ax.containers:
            for i, container in enumerate(self.plot_engine.current_ax.containers):
                label = container.get_label()

                if not label or label.startswith("_"):
                    handles, labels = self.plot_engine.current_ax.get_legend_handles_labels()
                    if i < len(labels):
                        label = labels[i]
                    else:
                        label = f"Bar Series {i+1}"
                self.view.bar_selector_combo.addItem(label, userData=container)
        
        self.view.bar_selector_combo.blockSignals(False)

        if preserve_selection and current_text:
            idx = self.view.bar_selector_combo.findText(current_text)
            if idx >= 0:
                self.view.bar_selector_combo.setCurrentIndex(idx)
                return

        if self.view.bar_selector_combo.count() > 0:
            self.on_bar_selected(self.view.bar_selector_combo.currentText())
    
    def on_bar_selected(self, bar_name: str) -> None:
        """Load settings for a selected bar series"""
        if not self.view.multibar_custom_check.isChecked():
            return
        
        container = self.view.bar_selector_combo.currentData()

        if not container or not hasattr(container, "patches") or not container.patches:
            return
        
        patch = container.patches[0]

        #load color
        facecolor = to_hex(patch.get_facecolor())
        if facecolor:
            self.bar_color = facecolor
            self.view.bar_color_label.setText(facecolor)
            ColorManager.update_button_color_swatch(self.view.bar_color_button, QColor(self.bar_color))
        
        #edge color
        edgecolor = to_hex(patch.get_edgecolor())
        if edgecolor:
            self.bar_edge_color = edgecolor
            self.view.bar_edge_label.setText(edgecolor)
            ColorManager.update_button_color_swatch(self.view.bar_edge_button, QColor(self.bar_edge_color))

        #load the bar edge width
        self.view.bar_edge_width_spin.blockSignals(True)
        self.view.bar_edge_width_spin.setValue(patch.get_linewidth())
        self.view.bar_edge_width_spin.blockSignals(False)
        
        alpha = patch.get_alpha()
        if alpha is not None:
            self.view.alpha_slider.blockSignals(True)
            self.view.alpha_slider.setValue(int(alpha * 100))
            self.view.alpha_slider.blockSignals(False)
            self.view.alpha_label.setText(f"{int(alpha * 100)}%")
    
    def _update_bar_customization_live(self) -> None:
        """Saves the current temporary bar settings to self.bar_customizations if a bar series is selected"""
        if not self.view.multibar_custom_check.isChecked():
            return
        
        bar_name = self.view.bar_selector_combo.currentText()
        if not bar_name:
            return
        
        custom = self.bar_customizations.get(bar_name, {})
        custom["facecolor"] = self.bar_color
        custom["edgecolor"] = self.bar_edge_color
        custom["linewidth"] = self.view.bar_edge_width_spin.value()
        custom["alpha"] = self.view.alpha_slider.value() / 100.0

        self.bar_customizations[bar_name] = custom

    def on_grid_toggle(self) -> None:
        """Handle grid checkbox toggle"""
        is_enabled = self.view.grid_check.isChecked()
        self.view.global_grid_group.setVisible(is_enabled)
        self.view.grid_which_type_combo.setEnabled(is_enabled)
        self.view.grid_axis_combo.setEnabled(is_enabled)
        self.view.independent_grid_check.setEnabled(is_enabled)

        if not is_enabled:
            self.view.grid_axis_tab.setVisible(False)
            self.view.independent_grid_check.setChecked(False)
        self.on_style_changed()
    
    def on_legend_toggle(self) -> None:
        """Handle legend UI visibility"""
        self.on_style_changed()

    
    def on_independent_grid_toggle(self):
        """Handle indepeendent customization of axis grids toggle"""
        is_independent = self.view.independent_grid_check.isChecked()

        #disable global control when independent axis controls are enabeld
        self.view.grid_which_type_combo.setEnabled(not is_independent)
        self.view.grid_axis_combo.setEnabled(not is_independent)
        self.on_style_changed()
    
    def toggle_multi_y(self):
        """Toggle between multi and single y slections"""
        is_multi = self.view.multi_y_check.isChecked()

        #show appropiate widgets
        self.view.y_column.setVisible(not is_multi)
        self.view.y_columns_list.setVisible(is_multi)
        self.view.select_all_y_btn.setVisible(is_multi)
        self.view.clear_all_y_btn.setVisible(is_multi)
        self.view.multi_y_info.setVisible(is_multi)

        #wen swhichtng to multi ycols, select the current ycol
        if is_multi and self.view.y_column.currentText():
            current_y = self.view.y_column.currentText()
            for i in range(self.view.y_columns_list.count()):
                if self.view.y_columns_list.item(i).text() == current_y:
                    self.view.y_columns_list.item(i).setSelected(True)
                    break
        self.on_data_changed()
    
    def select_all_y_columns(self):
        """Select all availalbe ycols"""
        self.view.y_columns_list.selectAll()
        self.on_data_changed()
    
    def clear_all_y_columns(self):
        """Clear all selected ycols"""
        self.view.y_columns_list.clearSelection()
        self.on_data_changed()
    
    def get_selected_y_columns(self):
        """Get list of selected ycols"""
        if self.view.multi_y_check.isChecked():
            selected_items = self.view.y_columns_list.selectedItems()
            return [item.text() for item in selected_items]
        else:
            y_col_text = self.view.y_column.currentText()
            return [y_col_text] if y_col_text else []
    
    def update_colorblind_simulation(self) -> None:
        """Applies or removes the SVG filter effect from canvas"""
        if self.view.colorblind_check.isChecked():
            sim_type = self.view.colorblind_type_combo.currentText()
            effect = ColorBlindnessEffect(sim_type)
            self.canvas.setGraphicsEffect(effect)
            self.status_bar.log(f"Color blindness mode enabled: {sim_type}", "INFO")
        else:
            self.canvas.setGraphicsEffect(None)
            self.status_bar.log("Color blindess mode disabled", "INFO")
        self.on_style_changed()

    def toggle_line_selector(self) -> None:
        """Show/enable line selection"""
        is_enabled = self.view.multiline_custom_check.isChecked()
        self.view.line_selector_label.setVisible(is_enabled)
        self.view.line_selector_combo.setVisible(is_enabled)

        if is_enabled:
            self._initialize_all_line_customizations()
            self.update_line_selector()
        self.on_style_changed()
    
    def _initialize_all_line_customizations(self) -> None:
        """Initialize customizations dict for all lines with their current state"""
        if not self.plot_engine.current_ax:
            return
        lines = [l for l in self.plot_engine.current_ax.get_lines() if l.get_gid() not in ["regression_line", "confidence_interval", "error_bar"]]
        for i, line in enumerate(lines):
            line_name = line.get_label() if not line.get_label().startswith("_") else f"Line {i+1}"
            if line_name not in self.line_customizations:
                self.line_customizations[line_name] = {
                    'linewidth': line.get_linewidth(),
                    'linestyle': line.get_linestyle(),
                    'color': to_hex(line.get_color()) if line.get_color() else None,
                    'marker': line.get_marker(),
                    'markersize': line.get_markersize(),
                    'markerfacecolor': to_hex(line.get_markerfacecolor()) if line.get_markerfacecolor() else None,
                    'markeredgecolor': to_hex(line.get_markeredgecolor()) if line.get_markeredgecolor() else None,
                    'markeredgewidth': line.get_markeredgewidth(),
                    'alpha': line.get_alpha() if line.get_alpha() is not None else 1.0
                }
    def _update_line_customization_live(self) -> None:
        """Save the current settings for the selected line"""
        if not self.view.multiline_custom_check.isChecked():
            return
        line_name = self.view.line_selector_combo.currentText()
        if not line_name:
            return
        
        linestyle_map = {'Solid': '-', 'Dashed': '--', 'Dash-dot': '-.', 'Dotted': ':'}
        linestyle_val = linestyle_map.get(self.view.linestyle_combo.currentText(), '-')
        custom = self.line_customizations.get(line_name, {})
        custom.update({
            'linewidth': self.view.linewidth_spin.value(),
            'linestyle': linestyle_val,
            'color': self.line_color,
            'marker': self.view.marker_combo.currentText(),
            'markersize': self.view.marker_size_spin.value(),
            'markerfacecolor': self.marker_color,
            'markeredgecolor': self.marker_edge_color,
            'markeredgewidth': self.view.marker_edge_width_spin.value(),
            'alpha': self.view.alpha_slider.value() / 100.0,
        })
        self.line_customizations[line_name] = custom
    
    def update_line_selector(self, preserve_selection: bool = False) -> None:
        """Update the line selection with the ucrrent lines in current_ax"""
        current_text = self.view.line_selector_combo.currentText()
        self.view.line_selector_combo.blockSignals(True)
        self.view.line_selector_combo.clear()
        
        if self.plot_engine.current_ax:
            lines = [l for l in self.plot_engine.current_ax.get_lines() if l.get_gid() not in ["regression_line", "confidence_interval", "error_bar"]]
            for i, line in enumerate(lines):
                label = line.get_label()
                if label.startswith("_"):
                    label = f"Line {i+1}"
                self.view.line_selector_combo.addItem(label, userData=i)
        self.view.line_selector_combo.blockSignals(False)
        
        if preserve_selection and current_text:
            idx = self.view.line_selector_combo.findText(current_text)
            if idx >= 0:
                self.view.line_selector_combo.setCurrentIndex(idx)
                return
            
        if self.view.line_selector_combo.count() > 0:
            self.on_line_selected(self.view.line_selector_combo.currentText())
    
    def on_line_selected(self, line_name):
        """Load settings for a selected line"""
        if not self.view.multiline_custom_check.isChecked():
            return
        
        if not self.plot_engine.current_ax:
            return
        
        #get line idx
        line_idx = self.view.line_selector_combo.currentData()
        if line_idx is None:
            return
        
        lines = [l for l in self.plot_engine.current_ax.get_lines() if l.get_gid() not in ["regression_line", "confidence_interval", "error_bar"]]

        if line_idx < len(lines):
            line = lines[line_idx]

            #load current line props
            self.view.linewidth_spin.blockSignals(True)
            self.view.linewidth_spin.setValue(line.get_linewidth())
            self.view.linewidth_spin.blockSignals(False)

            linestyle_map_reverse = {"-": "Solid", "--": "Dashed", "-.": "Dash-dot", ":": "Dotted"}
            current_style = linestyle_map_reverse.get(line.get_linestyle(), "Solid")
            self.view.linestyle_combo.blockSignals(True)
            self.view.linestyle_combo.setCurrentText(current_style)
            self.view.linestyle_combo.blockSignals(False)

            #load color
            color = line.get_color()
            if color:
                self.line_color = to_hex(color)
                self.view.line_color_label.setText(self.line_color)
                ColorManager.update_button_color_swatch(self.view.line_color_button, QColor(self.line_color))

            #load markers
            marker = line.get_marker()
            if marker and marker != "None":
                self.view.marker_combo.blockSignals(True)
                self.view.marker_combo.setCurrentText(marker)
                self.view.marker_combo.blockSignals(False)

                self.view.marker_size_spin.blockSignals(True)
                self.view.marker_size_spin.setValue(int(line.get_markersize()))
                self.view.marker_size_spin.blockSignals(False)
                
            alpha = line.get_alpha()
            if alpha is not None:
                self.view.alpha_slider.blockSignals(True)
                self.view.alpha_slider.setValue(int(alpha * 100))
                self.view.alpha_slider.blockSignals(False)
                self.view.alpha_label.setText(f"{int(alpha * 100)}%")
    
    def preset_all_spines(self):
        """Preset: Show all spines"""
        self.view.top_spine_visible_check.setChecked(True)
        self.view.bottom_spine_visible_check.setChecked(True)
        self.view.left_spine_visible_check.setChecked(True)
        self.view.right_spine_visible_check.setChecked(True)
        self.status_bar.log("Applied preset: All Spines", "INFO")
        self.on_style_changed()

    def preset_box_only(self):
        """Preset: Show only left and buttom spines"""
        self.view.top_spine_visible_check.setChecked(False)
        self.view.bottom_spine_visible_check.setChecked(True)
        self.view.left_spine_visible_check.setChecked(True)
        self.view.right_spine_visible_check.setChecked(False)
        self.status_bar.log("Applied preset: Box Only", "INFO")
        self.on_style_changed()

    def preset_no_spines(self):
        """Preset: Hide all spines"""
        self.view.top_spine_visible_check.setChecked(False)
        self.view.bottom_spine_visible_check.setChecked(False)
        self.view.left_spine_visible_check.setChecked(False)
        self.view.right_spine_visible_check.setChecked(False)
        self.status_bar.log("Applied preset: No Spines", "INFO")
        self.on_style_changed()
    
    def update_column_combo(self):
        """Update column ComboBoxes with available columns"""
        if self.data_handler.df is None or len(self.data_handler.df.columns) == 0:
            return
        
        columns = list(self.data_handler.df.columns)
        self.view.quick_filter_input.set_columns(columns)

        # Preserve the current selection
        current_x = self.view.x_column.currentText()
        current_y = self.view.y_column.currentText()
        current_z = self.view.z_column.currentText()
        current_hue = self.view.hue_column.currentText()
        current_secondary_y = self.view.secondary_y_column.currentText()
        current_auto_annoate = self.view.auto_annotate_col_combo.currentText()
        current_multi_y = []
        if self.view.multi_y_check.isChecked():
            current_multi_y = [item.text() for item in self.view.y_columns_list.selectedItems()]

        # Block signals to prevent triggering callbacks
        self.view.x_column.blockSignals(True)
        self.view.y_column.blockSignals(True)
        self.view.z_column.blockSignals(True)
        self.view.hue_column.blockSignals(True)
        self.view.secondary_y_column.blockSignals(True)
        self.view.y_columns_list.blockSignals(True)
        self.view.auto_annotate_col_combo.blockSignals(True)
        
        #update xcol
        self.view.x_column.clear()
        self.view.x_column.addItems(columns)
        if current_x in columns:
            self.view.x_column.setCurrentText(current_x)

        #update singleular ycol
        self.view.y_column.clear()
        self.view.y_column.addItems(columns)
        if current_y in columns:
            self.view.y_column.setCurrentText(current_y)
        
        # update zcol
        self.view.z_column.clear()
        self.view.z_column.addItems(columns)
        if current_z in columns:
            self.view.z_column.setCurrentText(current_z)

        #update secondary y col
        self.view.secondary_y_column.clear()
        self.view.secondary_y_column.addItems(columns)
        if current_secondary_y in columns:
            self.view.secondary_y_column.setCurrentText(current_secondary_y)

        #update more ycols
        self.view.y_columns_list.clear()
        for col in columns:
            self.view.y_columns_list.addItem(col)
            if col in current_multi_y:
                item = self.view.y_columns_list.item(self.view.y_columns_list.count() - 1)
                item.setSelected(True)
        
        #update hue
        self.view.hue_column.clear()
        self.view.hue_column.addItem("None")
        self.view.hue_column.addItems(columns)
        if current_hue in columns:
            self.view.hue_column.setCurrentText(current_hue)
        else:
            self.view.hue_column.setCurrentIndex(0)

        #update auto annotations
        self.view.auto_annotate_col_combo.clear()
        self.view.auto_annotate_col_combo.addItem("Default (Y-value)")
        self.view.auto_annotate_col_combo.addItems(columns)

        if current_auto_annoate in columns:
            self.view.auto_annotate_col_combo.setCurrentText(current_auto_annoate)
        elif current_auto_annoate == "Default (Y-value)":
            self.view.auto_annotate_col_combo.setCurrentIndex(0)
        
        # Unblock signals
        self.view.x_column.blockSignals(False)
        self.view.y_column.blockSignals(False)
        self.view.z_column.blockSignals(False)
        self.view.hue_column.blockSignals(False)
        self.view.secondary_y_column.blockSignals(False)
        self.view.y_columns_list.blockSignals(False)
        self.view.auto_annotate_col_combo.blockSignals(False)

        if current_x != self.view.x_column.currentText() or current_y != self.view.y_column.currentText():
            self.on_data_changed()
    
    def toggle_table_controls(self):
        """Enable and disable table controls for the user"""
        enabled = self.view.table_enable_check.isChecked()
        self.view.table_type_combo.setEnabled(enabled)
        self.view.table_type_combo.setVisible(enabled)
        self.view.table_location_combo.setEnabled(enabled)
        self.view.table_location_combo.setVisible(enabled)

        self.view.table_auto_font_size_check.setEnabled(enabled)
        self.view.table_scale_spin.setEnabled(enabled)
        self.view.table_scale_spin.setVisible(enabled)

        self.view.table_font_size_spin.setEnabled(enabled and not self.view.table_auto_font_size_check.isChecked())
        self.view.table_font_size_spin.setVisible(enabled and not self.view.table_auto_font_size_check.isChecked())
    
    def toggle_table_font_controls(self):
        self.view.table_font_size_spin.setEnabled(not self.view.table_auto_font_size_check.isChecked())
        self.view.table_font_size_spin.setVisible(not self.view.table_auto_font_size_check.isChecked())

    def _apply_table(self):
        """Generate the table and add it to the plot"""
        if self.plot_engine.current_ax:
            for table in list(self.plot_engine.current_ax.tables):
                try:
                    table.remove()
                except Exception:
                    pass
        if not self.view.table_enable_check.isChecked():
            return
        
        df = self.get_active_dataframe()
        if df is None:
            return
        
        try:
            table_type = self.view.table_type_combo.currentText()
            x_col = self.view.x_column.currentText()
            y_cols = self.get_selected_y_columns()

            cols_to_use = []
            if x_col: cols_to_use.append(x_col)
            cols_to_use.extend(y_cols)

            if cols_to_use and all(column in df.columns for column in cols_to_use):
                target_df = df[cols_to_use]
            else:
                target_df = df.select_dtypes(include=[np.number])
            
            match table_type:
                case "Summary Stats":
                    data = target_df.describe().round(2)
                case "First 5 Rows":
                    data = target_df.head(5)
                case "Last 5 Rows":
                    data = target_df.tail(5)
                case "Correlation Matrix":
                    data = target_df.corr().round(2)
                case _:
                    data = target_df.head()
            
            loc = self.view.table_location_combo.currentText()
            auto_font = self.view.table_auto_font_size_check.isChecked()
            fontsize = self.view.table_font_size_spin.value()
            scale = self.view.table_scale_spin.value()

            self.plot_engine.add_table(
                data,
                loc=loc,
                auto_font_size=auto_font,
                fontsize=fontsize,
                scale_factor=scale
            )
    
        
        except Exception as PlotTableError:
            self.status_bar.log(f"Failed to add table to plot: {str(PlotTableError)}", "WARNING")
    
    def on_plot_type_changed(self, plot_type: str, log: bool = True):
        """Handle plot type change"""
        if log:
            self.status_bar.log(f"Plot type changed to: {plot_type}")
        
        self.view.custom_tabs.setTabVisible(6, plot_type == "GeoSpatial")
        if plot_type == "GeoSpatial":
            def _pre_import_geo_deps():
                try:
                    import mapclassify
                except ImportError:
                    pass
                try:
                    import contextily
                except ImportError:
                    pass
            threading.Thread(target=_pre_import_geo_deps, daemon=True).start()

        self._update_customization_visibility(plot_type)


        #plots with multiple ycols
        multi_y_supported = ["Line", "Bar", "Area", "Box", "Stackplot", "Eventplot", "Contour", "Contourf", "Barbs", "Quiver", "Streamplot", "Tricontour", "Tricontourf", "Tripcolor", "Triplot"]

        #enabled based on plottype
        if plot_type in multi_y_supported:
            self.view.multi_y_check.setEnabled(True)
            self.view.multi_y_check.setToolTip("")
        else:
            self.view.multi_y_check.setEnabled(False)
            self.view.multi_y_check.setChecked(False)
            self.view.multi_y_check.setToolTip(f"{plot_type} plots do not support multiple y columns")
        
        #Disbale plots with no dual yaxis support
        dual_axis_supported = ["Line", "Bar", "Scatter", "Area"]
        if plot_type in dual_axis_supported:
            self.view.secondary_y_check.setEnabled(True)
        else:
            self.view.secondary_y_check.setChecked(False)
            self.view.secondary_y_check.setEnabled(False)

        #disable hue for certain plots
        plots_without_hue: list[str] = [
            "Pie", "KDE", "Count Plot", "Stackplot", "Eventplot",
            "Image Show (imshow)", "pcolormesh", "Contour", "Contourf", "Tricontour",
            "Tricontourf", "Tripcolor", "Triplot", "2D Histogram", "ECDF", "Stairs", "Stem",
            "Barbs", "Quiver", "Streamplot", "GeoSpatial"
        ]
        self.view.hue_column.setEnabled(plot_type not in plots_without_hue)

        if plot_type in plots_without_hue:
            self.view.hue_column.setCurrentText("None")

        #disable flipping axes on certain plots
        incompatible_plots: list[str] = [
            "Histogram", "Pie", "Heatmap", "KDE", "Stackplot",
            "Image Show (imshow)", "pcolormesh", "Contour", "Contourf", "Barbs", "Quiver",
            "Streamplot", "Tricontour", "Tricontourf", "Tripcolor", "Triplot", "2D Histogram", "ECDF", "GeoSpatial", "3D Scatter", "3D Line", "3D Surface"
        ]
        self.view.flip_axes_check.setEnabled(plot_type not in incompatible_plots)
        if plot_type in incompatible_plots:
            self.view.flip_axes_check.setChecked(False)
    
    def _update_customization_visibility(self, primary_plot_type: str) -> None:
        """
        Updates visibility of customization options based on active plot types
        """
        line_plots = ["Line", "Area", "Step", "Stairs", "3D Line"]
        bar_plots = ["Bar", "Count Plot", "Stem"]
        hist_plots = ["Histogram", "Box", "Violin"]
        scatter_plots = ["Scatter", "3D Scatter"]
        pie_plots = ["Pie"]
        
        active_plot_types = [primary_plot_type]
        
        if self.view.secondary_y_check.isChecked() and self.view.secondary_y_check.isEnabled():
            active_plot_types.append(self.view.secondary_plot_type_combo.currentText())
            
        show_line = False
        show_bar_hist = False
        show_scatter = False
        show_pie = False
        
        show_markers = False
        show_error_bars = False
        
        for p_type in active_plot_types:
            if p_type in line_plots:
                show_line = True
                show_markers = True
                if p_type != "3D Line":
                    show_error_bars = True
            elif p_type in hist_plots:
                show_bar_hist = True
                if p_type in ["Box", "Violin"]:
                    show_error_bars = True
            elif p_type in bar_plots:
                show_bar_hist = True
                show_error_bars = True
            elif p_type in scatter_plots:
                show_scatter = True
                show_markers = True
                if p_type != "3D Scatter":
                    show_error_bars = True
            elif p_type in pie_plots:
                show_pie = True
        
        self.view.page_line.setVisible(show_line)
        self.view.page_bar_hist.setVisible(show_bar_hist)
        self.view.page_scatter.setVisible(show_scatter)
        self.view.page_pie.setVisible(show_pie)
        self.view.page_empty.setVisible(not any([show_line, show_bar_hist, show_scatter, show_pie]))
        
        self.view.marker_group.setVisible(show_markers)
        self.view.error_bars_group.setVisible(show_error_bars)
        
        # 3d settings
        is_3d  = primary_plot_type in ["3D Scatter", "3D Line", "3D Surface"]
        self.view.z_column_widget.setVisible(is_3d)
        self.view.camera_3d_group.setVisible(is_3d)
        self.view.zlabel_widget.setVisible(is_3d)

        # Disable tight layout for 3D plots
        if is_3d:
            self.view.tight_layout_check.setChecked(False)
            self.view.tight_layout_check.setEnabled(False)
            self.view.tight_layout_check.setToolTip("Tight layout is not supported for 3D plots")
        else:
            self.view.tight_layout_check.setEnabled(True)
            self.view.tight_layout_check.setToolTip("")
        
        z_tab_idx = self.view.axis_tab_widget.indexOf(self.view.z_tab)
        if is_3d and z_tab_idx == -1:
            self.view.axis_tab_widget.addTab(self.view.z_tab, "Z-Axis")
        else:
            self.view.axis_tab_widget.removeTab(z_tab_idx)
        
        # Tick formatting controls to be disabled at 3D plots
        unsupported_3d_tick_controls: list[str] = [
            "x_major_tick_direction_combo", "x_major_tick_width_spin",
            "y_major_tick_direction_combo", "y_major_tick_width_spin",
            "z_major_tick_direction_combo", "z_major_tick_width_spin",
            "x_minor_tick_direction_combo", "x_minor_tick_width_spin",
            "y_minor_tick_direction_combo", "y_minor_tick_width_spin",
            "z_minor_tick_direction_combo", "z_minor_tick_width_spin"
        ]
        for control_name in unsupported_3d_tick_controls:
            if hasattr(self.view, control_name):
                control_widget = getattr(self.view, control_name)
                control_widget.setEnabled(not is_3d)

                if is_3d:
                    control_widget.setToolTip("Tick direction and width customization are not supported in 3D rendered plots")
                else:
                    control_widget.setToolTip("")

    def on_data_changed(self):
        """Handle data column selection change"""
        if self._is_clearing:
            return
        self._is_data_dirty = True
        
        df = self.get_active_dataframe()
        if df is not None and len(df) <= self.AUTO_UPDATE_THRESHOLD:
            self.style_update_timer.start()
        else:
            self._is_data_dirty = True
            self.selection_overlay.show_update_required(True)
            self.status_bar.log("Data change detected. Click 'Generate Plot' to update.", "WARNING")
    
    def on_style_changed(self) -> None:
        if self._is_clearing:
            return
        if self._is_data_dirty:
            return
        if self.dragged_annotation is not None:
            return
        if not self.isVisible():
            self._is_data_dirty = True
            return
        if self.view.multiline_custom_check.isChecked():
            self._update_line_customization_live()
        if self.view.multibar_custom_check.isChecked():
            self._update_bar_customization_live()
        if self.style_update_timer:
            self.style_update_timer.start()
    
    def _on_palette_changed(self, text: str) -> None:
        if self._is_clearing:
            return
        self._last_data_signature = None
        self.on_data_changed()
    
    def _on_geospatial_projection_changed(self, *args) -> None:
        if self._is_clearing:
            return
        self._last_data_signature = None
        self.on_data_changed()

    def _fast_render(self) -> None:
        if self._is_clearing:
            return
        if not self.isVisible():
            self._is_data_dirty = True
            return
        if getattr(self, '_is_data_dirty', False):
            self.generate_plot()
            return

        cached_df = getattr(self, '_cached_active_df', None)
        if cached_df is None:
            return
        
        current_subplot_index, _ = self._get_subplot_config()
        x_col = self.view.x_column.currentText()
        y_cols = self.get_selected_y_columns()
        hue = self.view.hue_column.currentText() if self.view.hue_column.currentText() != "None" else None
        subset_name = self.view.subset_combo.currentData() if self.view.use_subset_check.isChecked() else None
        quick_filter = self.view.quick_filter_input.text().strip()

        self._generate_main_plot(
            active_df=cached_df,
            plot_type=self.current_plot_type_name,
            x_col=x_col,
            y_cols=y_cols,
            hue=hue,
            subset_name=subset_name,
            current_subplot_index=current_subplot_index,
            quick_filter=quick_filter,
            keep_data=True,
            animate=False
        )

    def toggle_datetime_format(self):
        """Enabled/disable formating ctrsl for datetime"""
        is_enabled = self.view.custom_datetime_check.isChecked()
        self.view.x_datetime_format_combo.setEnabled(is_enabled)
        self.view.x_datetime_format_combo.setVisible(is_enabled)
        self.view.format_x_datetime_label.setVisible(is_enabled)
        self.view.custom_x_axis_format_label.setVisible(is_enabled)
        self.view.x_custom_datetime_input.setVisible(is_enabled)

        self.view.y_datetime_format_combo.setEnabled(is_enabled)
        self.view.y_datetime_format_combo.setVisible(is_enabled)
        self.view.format_y_datetime_label.setVisible(is_enabled)
        self.view.custom_y_axis_format_label.setVisible(is_enabled)
        self.view.y_custom_datetime_format_input.setVisible(is_enabled)

        self.view.format_help.setVisible(is_enabled)

        #enable the custom input if custom is selected from the box
        if is_enabled:
            self.view.x_custom_datetime_input.setEnabled(self.view.x_datetime_format_combo.currentText() == "Custom")
            self.view.y_custom_datetime_format_input.setEnabled(self.view.y_datetime_format_combo.currentText() == "Custom")
    
    def on_x_datetime_format_changed(self, text) -> None:
        """Handle x-axis format change"""
        self.view.x_custom_datetime_input.setEnabled(text == "Custom")
        self.on_data_changed()
    
    def on_y_datetime_format_changed(self, text) -> None:
        """Handle y-axis format change"""
        self.view.x_custom_datetime_input.setEnabled(text == "Custom")
        self.on_data_changed()
    
    def generate_plot(self):
        """Generate plot based on current settings"""
        if self._is_clearing:
            return
        if not self.isVisible():
            self._is_data_dirty = True
            return
        if not self._validate_data_loaded():
            return

        # Get data configuration
        current_subplot_index, frozen_config = self._get_subplot_config()
        active_df, x_col, y_cols, hue, subset_name, quick_filter = self._resolve_data_config(current_subplot_index, frozen_config)

        if not self._validate_active_dataframe(active_df):
            return
        
        plot_type = self.current_plot_type_name
        axes_flipped = self.view.flip_axes_check.isChecked()
        x_scale, y_scale = self.view.x_scale_combo.currentText(), self.view.y_scale_combo.currentText()

        x_dt_fmt = self.view.x_datetime_format_combo.currentText() if self.view.custom_datetime_check.isChecked() else None
        y_dt_fmt = self.view.y_datetime_format_combo.currentText() if self.view.custom_datetime_check.isChecked() else None
        x_dt_custom = self.view.x_custom_datetime_input.text() if x_dt_fmt == "Custom" else None
        y_dt_custom = self.view.y_custom_datetime_format_input.text() if y_dt_fmt == "Custom" else None
        
        data_params = [
            id(active_df),
            active_df.shape,
            plot_type,
            x_col,
            tuple(y_cols) if y_cols else None,
            subset_name,
            quick_filter,
            axes_flipped,
            x_scale,
            y_scale,
            x_dt_fmt,
            y_dt_fmt,
            x_dt_custom,
            y_dt_custom
        ]
        current_data_signature = tuple(data_params)
        if (hasattr(self, "_last_data_signature") and self._last_data_signature == current_data_signature and hasattr(self, "_cached_active_df") and self._cached_active_df is not None):
            self.status_bar.log("Using cached data for plotting", "INFO")
            self._generate_main_plot(
                self._cached_active_df, plot_type, x_col, y_cols, hue, subset_name, current_subplot_index, quick_filter, keep_data=True
            )
            return

        self._last_data_signature = current_data_signature
        
        self.status_bar.log("Preparing data in background...", "INFO")
        self._prep_progress_dialog = ProgressDialog(title="Preparing Data", message="Initializing background task...", parent=self)
        self._prep_progress_dialog.show()
        
        from ui.workers import PlotDataPrepWorker
        worker = PlotDataPrepWorker(active_df, plot_type, x_col, y_cols, quick_filter)
        worker.signals.progress.connect(self._prep_progress_dialog.update_progress)
        worker.signals.log.connect(lambda msg: self.status_bar.log(msg, "INFO"))
        worker.signals.error.connect(self._on_prep_error)
        worker.signals.finished.connect(
            lambda processed_df: self._on_prep_finished(
                processed_df, plot_type, x_col, y_cols, hue, subset_name, current_subplot_index, quick_filter
            )
        )
        self.thread_pool.start(worker)
    
    def _on_prep_error(self, error: Exception) -> None:
        """Handle errors from the background data preparation worker."""
        if hasattr(self, "_prep_progress_dialog") and self._prep_progress_dialog:
            self._prep_progress_dialog.accept()
        self.status_bar.log(f"Data preparation failed: {str(error)}", "ERROR")
        QMessageBox.critical(self, "Data Preparation Error", f"An error occurred during data processing:\n{str(error)}")

    def _on_prep_finished(self, processed_df: pd.DataFrame, plot_type: str, x_col: str, y_cols: list[str], hue: str, subset_name: str, current_subplot_index: int, quick_filter: str) -> None:
        """Called when background data preparation completes successfully."""
        if hasattr(self, "_prep_progress_dialog") and self._prep_progress_dialog:
            self._prep_progress_dialog.accept()
            
        self._cached_active_df = processed_df
        self._generate_main_plot(
            processed_df, plot_type, x_col, y_cols, hue, subset_name, current_subplot_index, quick_filter, keep_data=False
        )
    
    def _apply_quick_filter(self, df: pd.DataFrame, query: str) -> Optional[pd.DataFrame]:
        """Apply a pandas query to the dataframe"""
        try:
            filtered_df = df.query(query)
            if filtered_df.empty:
                QMessageBox.warning(self, "Empty Result", f"The filter {query} returned an empty dataset")
                self.status_bar.log(f"Filter {query} returned 0 rows", "WARNING")
                return None
            self.status_bar.log(f"Quick Filter applied: {query} ({len(df)} -> {len(filtered_df)} rows)", "INFO")
            return filtered_df
        except Exception as QuickFilterError:
            error_message = f"Invaid Quick Filter expression:\n{str(QuickFilterError)}"
            self.status_bar.log(f"Quick Filter error: {str(QuickFilterError)}", "ERROR")
            QMessageBox.critical(self, "Filter Error", error_message)
    
    def _validate_data_loaded(self) -> bool:
        """Check if data is loaded"""
        if self.data_handler.df is None:
            self.status_bar.log("No data loaded", "WARNING")
            QMessageBox.warning(self, "Warning", "No data loaded")
            return False
        return True
    
    def _get_subplot_config(self):
        """Get current subplot configuration"""
        current_subplot_index = self.view.active_subplot_combo.currentIndex()
        if current_subplot_index < 0:
            current_subplot_index = 0

        frozen_config = None
        if self.view.freeze_data_check.isChecked() and self.view.add_subplots_check.isChecked():
            frozen_config = self.subplot_manager.get_config(current_subplot_index)

        return current_subplot_index, frozen_config

    def _resolve_data_config(self, current_subplot_index, frozen_config: dict):
        """Resovle data configeration from frozen config"""
        if frozen_config:
            x_col = frozen_config.get("x_col")
            y_cols = frozen_config.get("y_cols")
            hue = frozen_config.get("hue")
            subset_name = frozen_config.get("subset_name")
            quick_filter = frozen_config.get("quick_filter", "")
            active_df = self._restore_frozen_data(subset_name)
            self.status_bar.log(f"Using data config for plot {current_subplot_index + 1}", "INFO")
        else:
            active_df = self.get_active_dataframe()
            x_col = self.view.x_column.currentText()
            y_cols = self.get_selected_y_columns()
            hue = (self.view.hue_column.currentText() if self.view.hue_column.currentText() != "None" else None)
            subset_name = (self.view.subset_combo.currentData() if self.view.use_subset_check.isChecked() else None)
            quick_filter = self.view.quick_filter_input.text().strip()

        return active_df, x_col, y_cols, hue, subset_name, quick_filter

    def _restore_frozen_data(self, subset_name):
        """Restore data from a frozen subset"""
        if subset_name:
            try:
                if self.subset_manager:
                    return self.subset_manager.apply_subset(
                        self.data_handler.df, subset_name
                    )
                else:
                    self.status_bar.log("Subset Manager not initialized, using full dataset", "WARNING")
                    return self.data_handler.df
            except Exception as UseSubsetError:
                self.status_bar.log(f"Could not restore subset '{subset_name}'. Error: {str(UseSubsetError)}", "ERROR")
                return self.data_handler.df
        else:
            return self.data_handler.df
        
    def _validate_active_dataframe(self, active_df) -> bool:
        """Validates the active dataframe (check if has data or nah)"""
        if active_df is None or len(active_df) == 0:
            QMessageBox.warning(self, "Warning", "Selected data is empty")
            return False
        return True
    
    def _generate_main_plot(self, active_df, plot_type, x_col, y_cols, hue, subset_name, current_subplot_index, quick_filter="", keep_data=False, animate=True):
        """Generate plot using matplotlib settings"""
        data_size = len(self.data_handler.df)
        show_progress = (data_size > 1000 and not keep_data)
        progress_dialog = None

        try:
            progress_dialog = self._init_progress_dialog(show_progress, data_size)

            if not keep_data:
                if not self._validate_plot_requirements(plot_type, x_col, y_cols):
                    return

                self._update_progress(progress_dialog, 10, "Preparing Data")

            #Build config
            axes_flipped = self.view.flip_axes_check.isChecked()
            font_family = self.view.font_family_combo.currentText()

            self._update_progress(progress_dialog, 20, "Building Plot Configuration")

            general_kwargs = self.formatting_manager.build_general_kwargs(plot_type, x_col, y_cols, hue)
            plot_kwargs = self.formatting_manager.build_plot_specific_kwargs(plot_type)

            # Setup plot
            if not keep_data:
                self._update_progress(progress_dialog, 30, "Clearing Previous plot")
                self.formatting_manager.setup_plot_figure(clear=True)
            else:
                self.formatting_manager.setup_plot_figure(clear=False)

            self._update_progress(progress_dialog, 35, "Setting plot style")
            self.formatting_manager.apply_plot_style()
            self.formatting_manager.set_axis_limit_and_scales()

            # Create
            if not keep_data:
                self._update_progress(progress_dialog, 40, f"Creating {plot_type} plot")

                if not self._execute_plot_strategy(plot_type, active_df, x_col, y_cols, axes_flipped, font_family, plot_kwargs, general_kwargs):
                    if progress_dialog:
                        progress_dialog.accept()
                    return

            # Apply formatting and customizations
            self.formatting_manager.apply_plot_formatting(progress_dialog, x_col, y_cols, axes_flipped, font_family, general_kwargs, active_df)

            # Finalize
            self._update_progress(progress_dialog, 98, "Finishing up")
            self._finalize_plot(current_subplot_index, x_col, y_cols, hue, subset_name, quick_filter, is_fast_render=keep_data)

            # Log
            if not keep_data:
                self._log_plot_message(plot_type, x_col, y_cols, hue, subset_name, active_df, quick_filter)
            self._update_progress(progress_dialog, 100, "Complete")
            if progress_dialog:
                QTimer.singleShot(300, progress_dialog.accept)
            self._is_data_dirty = False

            if animate:
                PlotGeneratedAnimation(parent=self, message="Plot Generated").start(target_widget=self)
        except InterruptedError:
            self.status_bar.log(f"Plot generation cancelled", "INFO")
            if progress_dialog:
                progress_dialog.accept()
        except Exception as CreateMainPlotError:
            if progress_dialog:
                progress_dialog.accept()
            QMessageBox.critical(self, "Error", f"Failed to create plot: {str(CreateMainPlotError)}")
            self.status_bar.log(f"Plot generation failed: {str(CreateMainPlotError)}", "ERROR")
            traceback.print_exc()
        finally:
            if progress_dialog and progress_dialog.isVisible():
                progress_dialog.accept()

    
    def _init_progress_dialog(self, show_progress, data_size):
        """Initizalixze the progress dialog"""
        if show_progress:
            progress_dialog = ProgressDialog(
                title="Generating plot",
                message=f"Processing {data_size:,} data points",
                parent=self
            )
            progress_dialog.show()
            progress_dialog.update_progress(5, "Initializing plotting engine")
            QApplication.processEvents()
            return progress_dialog
        return None
    
    def _update_progress(self, progress_dialog, value, message):
        """Update the progress dialog anc check for cancellation"""
        if progress_dialog:
            progress_dialog.update_progress(value, message)
            if progress_dialog.is_cancelled():
                self.status_bar.log("Plot generation cancelled", "WARNING")
                raise InterruptedError("User cancelled")
    
    def _validate_plot_requirements(self, plot_type, x_col, y_cols) -> bool:
        """Validate the required are data is available"""
        plots_no_x = ["Box", "Histogram", "KDE", "Heatmap", "Pie", "ECDF", "Eventplot", "GeoSpatial"]

        plots_no_y = ["Count Plot", "Heatmap", "GeoSpatial"]
        plots_gridded = ["Image Show (imshow)", "pcolormesh", "Contour", "Contourf"]
        plots_vector = ["Barbs", "Quiver", "Streamplot"]
        plots_triangulation_z = ["Tricontour", "Tricontourf", "Tripcolor"]
        plots_triangulation_no_z = ["Triplot"]

        if not x_col and plot_type not in plots_no_x:
            QMessageBox.warning(self, "Warninig", f"Please select an X column for {plot_type}")
            return False
        
        if not y_cols and plot_type not in plots_no_y:
            QMessageBox.warning(self, "Warning", f"Please select at least one Y column for {plot_type}.")
            return False

        if plot_type in plots_gridded and len(y_cols) < 2:
            QMessageBox.warning(self, "Warning", f"{plot_type} requires 2 Y columns: (Y-position, Z-value)")
            return False

        if plot_type in plots_vector and len(y_cols) < 3:
            QMessageBox.warning(self, "Warning", f"{plot_type} requires 3 Y columns: (Y-position, U-component, V-component)")
            return False
        
        if plot_type in plots_triangulation_z and len(y_cols) < 2:
            QMessageBox.warning(self, "Warning", f"{plot_type} requires 2 Y columns: (Y-position, Z-value)")
            return False

        if plot_type in plots_triangulation_no_z and len(y_cols) < 1:
            QMessageBox.warning(self, "Warning", f"{plot_type} requires at least one Y columns: (Y-position)")
            return False
        
        return True

    def _execute_plot_strategy(self, plot_type, active_df, x_col, y_cols, axes_flipped, font_family, plot_kwargs, general_kwargs):
        """Executes the correct plotting strategy"""
        
        original_df = self.data_handler.df
        self.data_handler.df = active_df

        try:
            error_message = self.plot_engine.execute_strategy(
                plot_type=plot_type,
                plot_tab=self,
                x_col=x_col,
                y_cols=y_cols,
                axes_flipped=axes_flipped,
                font_family=font_family,
                plot_kwargs=plot_kwargs,
                general_kwargs=general_kwargs
            )

            if error_message:
                QMessageBox.warning(self, "Warning", error_message)
                return False

            return True
        finally:
            self.data_handler.df = original_df
    
    def _finalize_plot(self, current_subplot_index, x_col, y_cols, hue, subset_name, quick_filter, is_fast_render=False) -> None:
        """Finalize plot and save configs"""
        try:
            if self.view.tight_layout_check.isChecked():
                self.plot_engine.finalize_layout()
        except Exception as TightLayoutError:
            self.status_bar.log(f"Tight layout not applied due to error: {str(TightLayoutError)}", "ERROR")
        
        self.canvas.draw()
        
        if hasattr(self, "canvas_stack") and hasattr(self, "canvas"):
            self.canvas_stack.setCurrentWidget(self.canvas)

        if not is_fast_render:
            self.subplot_manager.update_overlay()

        if self.view.add_subplots_check.isChecked():
            self.subplot_manager.save_config(current_subplot_index, {
            "x_col": x_col,
            "y_cols": y_cols,
            "hue": hue,
            "subset_name": subset_name,
            "quick_filter": quick_filter
        })
        
        if self.view.multiline_custom_check.isChecked():
            self.update_line_selector(preserve_selection=True)
        if self.view.multibar_custom_check.isChecked():
            self.update_bar_selector(preserve_selection=True)
            
        self.script_manager.sync_script_if_open()

    def _log_plot_message(self, plot_type, x_col, y_cols, hue, subset_name, active_df, quick_filter=""):
        """Log plot generation to log"""
        plot_details = {
            "plot_type": plot_type,
            "x_column": x_col,
            "y_column": str(y_cols),
            "data_points": len(self.data_handler.df),
            "annotations": len(self.annotation_manager.annotations)
        }

        if hue:
            plot_details["hue"] = hue

        if quick_filter:
            plot_details["filter"] = quick_filter

        if self.view.use_subset_check.isChecked() and subset_name:
            plot_details["subset"] = subset_name
            plot_details["subset_rows"] = len(active_df)
            plot_details["total_rows"] = len(self.data_handler.df)
        
        status_message = f"{plot_type} plot created"
        if self.view.use_subset_check.isChecked() and subset_name:
            status_message += f" (Subset: {subset_name})"
        if len(self.annotation_manager.annotations) > 0:
            status_message += f" with {len(self.annotation_manager.annotations)} annotations"
        
        self.status_bar.log_action(status_message, details=plot_details, level="SUCCESS")

    def _apply_annotations(self, df=None, x_col=None, y_cols=None):
        """Apply text annotations and reference lines"""
        self.annotation_manager.apply_annotations(df, x_col, y_cols)
        self.reference_line_manager.apply_reference_lines()

    def clear_plot(self) -> None:
        """Clear the plot"""
        self._is_clearing = True
        self.style_update_timer.stop()
        self.plot_engine.clear_plot()

        self._last_data_signature = None
        self._last_viz_signature = None
        self._cached_active_df = None
        self._is_data_dirty = False

        self.view.active_subplot_combo.blockSignals(True)
        self.view.quick_filter_input.clear()

        self.view.active_subplot_combo.clear()
        self.view.active_subplot_combo.addItem("Plot 1")
        self.view.quick_filter_input.clear()

        self.view.active_subplot_combo.blockSignals(False)
        self.view.quick_filter_input.blockSignals(False)

        self.canvas.draw()
        if hasattr(self, "canvas_stack") and hasattr(self, "empty_state_view"):
            self.canvas_stack.setCurrentWidget(self.empty_state_view)
        
        self.selection_overlay.hide()

        if self.line_customizations is not None:
            self.line_customizations.clear()
        else:
            self.line_customizations = {}

        if self.bar_customizations is not None:
            self.bar_customizations.clear()
        else:
            self.bar_customizations = {}

        self.annotation_manager.clear_annotations()
        self.reference_line_manager.clear_all_reference_lines()
        self.subplot_manager.clear_configs()

        self.plot_clear_animation = PlotClearedAnimation(parent=None, message="Plot Cleared")
        self.plot_clear_animation.start(target_widget=self)

        self.status_bar.log_action(
            "Plot cleared",
            details={"operation": "clear_plot"},
            level="INFO"
        )
        QTimer.singleShot(100, lambda: setattr(self, "_is_clearing", False))
    
    def _toggle_secondary_input(self, enabled: bool):
        is_enabled = bool(enabled)

        self.view.secondary_y_column.setEnabled(is_enabled)
        if hasattr(self.view, "secondary_plot_type_combo"):
            self.view.secondary_plot_type_combo.setEnabled(is_enabled)
        if hasattr(self.view, "secondary_zorder_check"):
            self.view.secondary_zorder_check.setEnabled(is_enabled)
        self._update_customization_visibility(self.current_plot_type_name)
    
    def load_config(self, config: dict) -> None:
        """Load plot configuration"""
        try:
            self.config_manager.load_config(config)
            self.status_bar.log("Plot Config loaded", "INFO")
        except Exception as LoadConfigError:
            self.status_bar.log(f"Error loading plot config from saved project: {str(LoadConfigError)}")
            traceback.print_exc()

    def get_config(self) -> Dict[str, Any]:
        """Get current plot configuration"""
        return self.config_manager.get_config()

    def clear(self) -> None:
        """Clear all plot data"""
        self.clear_plot()
        self.view.title_input.blockSignals(True)
        self.view.xlabel_input.blockSignals(True)
        self.view.ylabel_input.blockSignals(True)
        
        self.view.title_input.clear()
        self.view.xlabel_input.clear()
        self.view.ylabel_input.clear()
        
        self.view.title_input.blockSignals(False)
        self.view.xlabel_input.blockSignals(False)
        self.view.ylabel_input.blockSignals(False)

    def set_empty_state_greeting(self) -> None:
        try:
            greeting_path = Path.cwd() / "resources" / "plot_studio_greeting.html"
            if greeting_path.exists():
                with open(greeting_path, "r", encoding="utf-8") as file:
                    greeting_html = file.read()
            else:
                self.status_bar.log("Plotting Studio Greeting HTML File not found", "ERROR")
                greeting_html = "<div style='text-align: center; font-family: sans-serif; padding: 40px; color: #64748b;'><h2>Plot Studio</h2><p>Design and customize your visualizations.</p></div>"
        except Exception as ReadGreetingError:
            self.status_bar.log(f"Failed to load greeting HTML: {str(ReadGreetingError)}", "ERROR")
            greeting_html = "<div style='text-align: center; font-family: sans-serif; padding: 40px; color: #64748b;'><h2>Plot Studio</h2></div>"
            
        if hasattr(self, "empty_state_view") and self.empty_state_view is not None:
            self.empty_state_view.setHtml(greeting_html)