# ui/plot_tab.py
from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING

from PyQt6.QtCore import QThreadPool, QTimer, pyqtSignal
from PyQt6.QtWidgets import QMessageBox
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from controller.plot_controllers import (AnnotationManager, AppearanceSettingsManager, CanvasInteractionManager,
                                         ColorManager, DataSelectionManager, PlotExportManager, PlotFormattingManager,
                                         PlotTableManager, PlotTypeManager, ReferenceLineManager, ReferenceSpanManager,
                                         ScriptManager, SeriesCustomizationManager, SubplotManager, ThemeManager)
from controller.plot_controllers.plot_generation_manager import PlotGenerationManager
from core.code_exporter import CodeExporter
from core.data_handler import DataHandler
from core.global_signals import ToastLevel, global_signals
from core.plot_config_manager import PlotConfigManager
from core.plot_engine import PlotEngine
from ui.plot_tab_ui import PlotTabUI
from ui.status_bar import LogLevel, StatusBar
from ui.widgets.SubplotOverlay import SubplotOverlay

if TYPE_CHECKING:
    from ui.plot_tab_ui import PlotSettingsPanel

class PlotTab(PlotTabUI):
    """Tab for creating and customizing plots"""

    brush_selection_made = pyqtSignal(set)

    @property
    def line_customizations(self) -> Dict[str, Any]:
        return self.series_customization_manager.line_customizations

    @line_customizations.setter
    def line_customizations(self, value: Dict[str, Any]) -> None:
        self.series_customization_manager.line_customizations = value

    @property
    def bar_customizations(self) -> Dict[str, Any]:
        return self.series_customization_manager.bar_customizations

    @bar_customizations.setter
    def bar_customizations(self, value: Dict[str, Any]) -> None:
        self.series_customization_manager.bar_customizations = value

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

        # Create canvas and toolbar
        self.plot_engine.create_figure()
        canvas = FigureCanvas(self.plot_engine.get_figure())
        toolbar = NavigationToolbar(canvas, self)

        self.init_ui(canvas, toolbar)

        self.view = self.settings_panel
        self.type_manager = PlotTypeManager(self)
        self.export_manager = PlotExportManager(self)

        # populate box in general tab with icons
        self.type_manager.populate_plot_toolbox()

        self.selection_overlay = SubplotOverlay(self.canvas)
        self.canvas.mpl_connect("resize_event", self.on_canvas_resize)

        # Initialize the plot tab managers
        self.theme_manager = ThemeManager(self)
        self.subplot_manager = SubplotManager(self)
        self.annotation_manager = AnnotationManager(self)
        self.reference_line_manager = ReferenceLineManager(self)
        self.reference_span_manager = ReferenceSpanManager(self)
        self.canvas_interaction_manager = CanvasInteractionManager(self)
        self.formatting_manager = PlotFormattingManager(self)
        self.color_manager = ColorManager(self)
        self.series_customization_manager = SeriesCustomizationManager(self)
        self.table_manager = PlotTableManager(self)
        self.data_selection_manager = DataSelectionManager(self)
        self.appearance_settings_manager = AppearanceSettingsManager(self)
        self.generation_manager = PlotGenerationManager(self)

        # Load initial data
        self.update_column_combo()
        self.type_manager.select_plot_in_toolbox("Line", log=False)
        self.set_empty_state_greeting()

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
        self.plot_button.clicked.connect(lambda _: self.generation_manager.generate_plot(animate=True))
        self.editor_button.clicked.connect(self.script_manager.open_script_editor)
        self.clear_button.clicked.connect(self.clear)
        self.save_plot_button.clicked.connect(self.export_manager.save_plot_image)

        # editor sync
        self.view.x_column.currentTextChanged.connect(self.script_manager.sync_script_if_open)

    def _connect_basic_tab_signals(self) -> None:
        """Connect signals for the General tab """
        self.data_selection_manager.connect_signals()

        self.view.x_column.currentTextChanged.connect(self.on_data_changed)
        self.view.y_column.currentTextChanged.connect(self.on_data_changed)
        self.view.y_columns_list.itemSelectionChanged.connect(self.on_data_changed)
        self.view.hue_column.currentTextChanged.connect(self.on_data_changed)
        self.view.subset_combo.currentIndexChanged.connect(self.on_data_changed)
        self.view.quick_filter_input.returnPressed.connect(self.on_data_changed)
        self.view.z_column.currentTextChanged.connect(self.on_data_changed)

        self.view.secondary_y_check.stateChanged.connect(self.on_data_changed)
        self.view.secondary_y_column.currentTextChanged.connect(self.on_data_changed)
        self.view.secondary_plot_type_combo.currentTextChanged.connect(self.on_data_changed)

        self.subplot_manager.connect_signals()

        self.view.use_subset_check.stateChanged.connect(self.use_subset)
        self.view.secondary_plot_type_combo.currentTextChanged.connect(
            lambda _: self.type_manager.update_customization_visibility(self.current_plot_type_name))

    def _connect_appearance_tab_signals(self) -> None:
        """Connect signals for the Appearance tab"""
        self.appearance_settings_manager.connect_signals()

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
        self.view.top_spine_visible_check.stateChanged.connect(self.on_style_changed)
        self.view.bottom_spine_visible_check.stateChanged.connect(self.on_style_changed)
        self.view.left_spine_visible_check.stateChanged.connect(self.on_style_changed)
        self.view.right_spine_visible_check.stateChanged.connect(self.on_style_changed)
        self.view.palette_combo.currentTextChanged.connect(self._on_palette_changed)

        self.view.camera_elevation_spin.valueChanged.connect(self.on_style_changed)
        self.view.camera_azimuth_spin.valueChanged.connect(self.on_style_changed)

    def _connect_axes_tab_signals(self) -> None:
        """Connect signals for the Axes tab"""
        self.view.x_auto_check.stateChanged.connect(
            lambda: self.view.x_min_spin.setEnabled(not self.view.x_auto_check.isChecked()))
        self.view.x_auto_check.stateChanged.connect(
            lambda: self.view.x_max_spin.setEnabled(not self.view.x_auto_check.isChecked()))
        self.view.y_auto_check.stateChanged.connect(
            lambda: self.view.y_min_spin.setEnabled(not self.view.y_auto_check.isChecked()))
        self.view.y_auto_check.stateChanged.connect(
            lambda: self.view.y_max_spin.setEnabled(not self.view.y_auto_check.isChecked()))
        self.view.z_auto_check.stateChanged.connect(
            lambda: self.view.z_min_spin.setEnabled(not self.view.z_auto_check.isChecked()))
        self.view.z_auto_check.stateChanged.connect(
            lambda: self.view.z_max_spin.setEnabled(not self.view.z_auto_check.isChecked()))

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
        self.view.x_minor_tick_direction_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.y_minor_tick_direction_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.x_minor_tick_width_spin.valueChanged.connect(self.on_style_changed)
        self.view.y_minor_tick_width_spin.valueChanged.connect(self.on_style_changed)
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
        self.view.legend_alpha_slider.valueChanged.connect(lambda v: self.view.legend_alpha_label.setText(f"{v}%"))
        self.view.global_grid_alpha_slider.valueChanged.connect(
            lambda v: self.view.global_grid_alpha_label.setText(f"{v}%"))
        self.view.x_major_grid_alpha_slider.valueChanged.connect(
            lambda v: self.view.x_major_grid_alpha_label.setText(f"{v}%"))
        self.view.x_minor_grid_alpha_slider.valueChanged.connect(
            lambda v: self.view.x_minor_grid_alpha_label.setText(f"{v}%"))
        self.view.y_major_grid_alpha_slider.valueChanged.connect(
            lambda v: self.view.y_major_grid_alpha_label.setText(f"{v}%"))
        self.view.y_minor_grid_alpha_slider.valueChanged.connect(
            lambda v: self.view.y_minor_grid_alpha_label.setText(f"{v}%"))

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

        self.view.legend_tab.global_grid_style_combo.currentTextChanged.connect(self.on_style_changed)
        self.view.legend_tab.global_grid_linewidth_spin.valueChanged.connect(self.on_style_changed)

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
        self.series_customization_manager.connect_signals()
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
        self.view.error_bar_alpha_slider.valueChanged.connect(
            lambda v: self.view.error_bar_alpha_label.setText(f"{v}%"))
        self.view.error_bar_alpha_slider.valueChanged.connect(self.on_data_changed)
        self.view.error_bar_zorder_spin.valueChanged.connect(self.on_data_changed)

    def _connect_annotation_tab_signals(self) -> None:
        """Connect signals for the Annotations tab"""
        self.annotation_manager.connect_signals()
        self.reference_line_manager.connect_signals()
        self.reference_span_manager.connect_signals()
        self.table_manager.connect_signals()

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

    def toggle_individual_spines(self) -> None:
        """Toggles the customization of spines for each"""
        self.appearance_settings_manager.toggle_individual_spines()

    def use_subset(self) -> None:
        """Active subset on change"""
        subset_enabled = self.view.use_subset_check.isChecked()
        self.on_data_changed()

    def on_canvas_resize(self, event: Any) -> None:
        self.subplot_manager.update_overlay(is_resize=True)
        self.formatting_manager.setup_plot_figure(clear=False)
        self.canvas.draw_idle()

    def activate_subset(self, subset_name: str):
        """Activates the 'Use Subset' checkbox and selects the selected subset"""
        if not self.subset_manager:
            global_signals.request_toast(
                "Cannot Activate Subset", "Subset Manager is not loaded", ToastLevel.ERROR
            )
            self.status_bar.log("Cannot activate subset: SubsetManager not available", LogLevel.ERROR)
            return

        self.refresh_subset_list()

        target_index = -1
        for i in range(self.view.subset_combo.count()):
            item_data = self.view.subset_combo.itemData(i)
            if item_data == subset_name:
                target_index = i
                break

        if target_index == -1:
            global_signals.request_toast(
                "Cannot activate subset", f"Subset '{subset_name}' not found", ToastLevel.WARNING
            )
            self.status_bar.log(f"Cannot activate subset: Subset '{subset_name}' not found", LogLevel.WARNING)
            return

        self.view.use_subset_check.setChecked(True)
        self.view.subset_combo.setCurrentIndex(target_index)

        global_signals.request_toast(
            "Activated Subset",
            f"Activated the '{subset_name}' for plotting",
            ToastLevel.INFO
        )
        self.status_bar.log_action(
            f"Activated subset: '{subset_name}' for plotting",
            details={"subset_name": subset_name, "source": "DataTab"},
            level=LogLevel.INFO
        )

    def set_subset_manager(self, subset_manager) -> None:
        """Set the subset manager reference"""
        self.subset_manager = subset_manager
        self.refresh_subset_list()

    def refresh_subset_list(self):
        """Refresh the list of available subsets"""
        if not self.subset_manager:
            global_signals.request_toast("Warning", "Subset manager not available", ToastLevel.WARNING)
            self.status_bar.log("Warning: Subset manager not available", LogLevel.WARNING)
            return

        if not hasattr(self, 'subset_combo'):
            global_signals.request_toast("Warning", "Subset UI is not loaded", ToastLevel.WARNING)
            self.status_bar.log("Warning: Subset combobox not initialized", LogLevel.WARNING)
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
                global_signals.request_toast("Info", f"Refreshed subset list: {subset_count} subsets available",
                                             ToastLevel.INFO)
                self.status_bar.log(f"Refreshed subset list: {subset_count} subsets available", LogLevel.INFO)
        except Exception as RefreshSubsetListError:
            self.status_bar.log(f"Error: Could not refresh subset list: {str(RefreshSubsetListError)}", LogLevel.ERROR)
            global_signals.request_toast("Subset Error", "Failed to refresh the list of subsets", ToastLevel.ERROR)

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
            self.status_bar.log("Subset manager not available, using full dataset", LogLevel.WARNING)
            return self.data_handler.df

        # Get selected subset name
        subset_name = self.view.subset_combo.currentData()
        if not subset_name:
            return self.data_handler.df

        # Try to apply subset
        try:
            subset_df = self.subset_manager.apply_subset(self.data_handler.df, subset_name)
            self.status_bar.log(f"Using subset: {subset_name} ({len(subset_df)} rows)", LogLevel.INFO)
            return subset_df
        except Exception as ApplySubsetToActiveDataFrameError:
            self.status_bar.log(f"Failed to apply subset, using full dataset: {str(ApplySubsetToActiveDataFrameError)}",
                                LogLevel.WARNING)
            global_signals.request_toast("Warning", "Using full dataset instead of subset", ToastLevel.WARNING)
            return self.data_handler.df

    def on_grid_toggle(self) -> None:
        """Handle grid checkbox toggle"""
        self.appearance_settings_manager.on_grid_toggle()

    def on_legend_toggle(self) -> None:
        """Handle legend UI visibility"""
        self.on_style_changed()

    def on_independent_grid_toggle(self):
        """Handle indepeendent customization of axis grids toggle"""
        self.appearance_settings_manager.on_independent_grid_toggle()

    def toggle_multi_y(self):
        """Toggle between multi and single y slections"""
        self.data_selection_manager.toggle_multi_y()

    def toggle_stacked_bars(self) -> None:
        """Handle toggle of stacked bars check"""
        self.data_selection_manager.toggle_stacked_bars()

    def select_all_y_columns(self):
        """Select all availalbe ycols"""
        self.data_selection_manager.select_all_y_columns()

    def clear_all_y_columns(self):
        """Clear all selected ycols"""
        self.data_selection_manager.clear_all_y_columns()

    def get_selected_y_columns(self):
        """Get list of selected ycols"""
        return self.data_selection_manager.get_selected_y_columns()

    def update_colorblind_simulation(self) -> None:
        """Applies or removes the SVG filter effect from canvas"""
        self.appearance_settings_manager.update_colorblind_simulation()

    def preset_all_spines(self):
        """Preset: Show all spines"""
        self.appearance_settings_manager.preset_all_spines()

    def preset_box_only(self):
        """Preset: Show only left and buttom spines"""
        self.appearance_settings_manager.preset_box_only()

    def preset_no_spines(self):
        """Preset: Hide all spines"""
        self.appearance_settings_manager.preset_no_spines()

    def update_column_combo(self):
        """Update column ComboBoxes with available columns"""
        self.data_selection_manager.update_column_combo()

    def toggle_table_controls(self) -> None:
        """Enable and disable table controls for the user"""
        self.table_manager.toggle_table_controls()

    def toggle_table_font_controls(self) -> None:
        self.table_manager.toggle_table_font_controls()

    def on_data_changed(self) -> None:
        """Handle data column selection change"""
        if self._is_clearing:
            return

        df = self.get_active_dataframe()
        if df is None or df.empty:
            return

        self._is_data_dirty = True

        df = self.get_active_dataframe()
        if df is not None and len(df) <= self.AUTO_UPDATE_THRESHOLD:
            self.style_update_timer.start()
        else:
            self._is_data_dirty = True
            self.selection_overlay.show_update_required(True)
            self.status_bar.log("Data change detected. Click 'Generate Plot' to update.", LogLevel.INFO)

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
            self.series_customization_manager.update_line_customization_live()
        if self.view.multibar_custom_check.isChecked():
            self.series_customization_manager.update_bar_customization_live()
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
            self.generation_manager.generate_plot(animate=False)
            return

        cached_df = getattr(self, '_cached_active_df', None)
        if cached_df is None:
            return

        current_subplot_index, _ = self.generation_manager._get_subplot_config()
        x_col = self.view.x_column.currentText()
        y_cols = self.get_selected_y_columns()
        hue = self.view.hue_column.currentText() if self.view.hue_column.currentText() != "None" else None
        subset_name = self.view.subset_combo.currentData() if self.view.use_subset_check.isChecked() else None
        quick_filter = self.view.quick_filter_input.text().strip()

        config = {
            "plot_type"   : self.current_plot_type_name,
            "x_col"       : x_col,
            "y_cols"      : y_cols,
            "hue"         : hue,
            "subset_name" : subset_name,
            "quick_filter": quick_filter
        }

        self.generation_manager.generate_main_plot(
            active_df=cached_df,
            subplot_index=current_subplot_index,
            config=config,
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

        # enable the custom input if custom is selected from the box
        if is_enabled:
            self.view.x_custom_datetime_input.setEnabled(self.view.x_datetime_format_combo.currentText() == "Custom")
            self.view.y_custom_datetime_format_input.setEnabled(
                self.view.y_datetime_format_combo.currentText() == "Custom")

    def on_x_datetime_format_changed(self, text) -> None:
        """Handle x-axis format change"""
        self.view.x_custom_datetime_input.setEnabled(text == "Custom")
        self.on_data_changed()

    def on_y_datetime_format_changed(self, text) -> None:
        """Handle y-axis format change"""
        self.view.x_custom_datetime_input.setEnabled(text == "Custom")
        self.on_data_changed()

    def _update_progress(self, progress_dialog, value, message):
        """Update the progress dialog anc check for cancellation"""
        if progress_dialog:
            progress_dialog.update_progress(value, message)
            if progress_dialog.is_cancelled():
                self.status_bar.log("Plot generation cancelled", LogLevel.WARNING)
                raise InterruptedError("User cancelled")

    def _apply_annotations(self, df=None, x_col=None, y_cols=None):
        """Apply text annotations and reference lines"""
        self.annotation_manager.apply_annotations(df, x_col, y_cols)
        self.reference_line_manager.apply_reference_lines()
        self.reference_span_manager.apply_reference_spans()

    def clear_plot(self) -> None:
        """Clear the plot"""
        if self._last_data_signature is not None or self.current_plot_type_name != "Line":
            reply_box = QMessageBox(self)
            reply_box.setWindowTitle("Clear Plot")
            reply_box.setText("Are you sure you want to clear the current plot?")
            reply_box.setInformativeText("All formatting, annotations and customizations will be lost")
            reply_box.setIcon(QMessageBox.Icon.Warning)
            reply_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            reply_box.setDefaultButton(QMessageBox.StandardButton.No)
            if reply_box.exec() == QMessageBox.StandardButton.No:
                return

        self._is_clearing = True
        self.style_update_timer.stop()
        self.plot_engine.clear_plot()

        self._last_data_signature = None
        self._last_viz_signature = None
        self._cached_active_df = None
        self._is_data_dirty = False

        self.view.active_subplot_combo.blockSignals(True)
        self.view.quick_filter_input.blockSignals(True)

        self.view.active_subplot_combo.clear()
        self.view.active_subplot_combo.addItem("Plot 1")
        self.view.quick_filter_input.clear()

        self.view.active_subplot_combo.blockSignals(False)
        self.view.quick_filter_input.blockSignals(False)

        self.canvas.draw()
        if hasattr(self, "canvas_stack") and hasattr(self, "empty_state_view"):
            self.canvas_stack.setCurrentWidget(self.empty_state_view)

        self.selection_overlay.hide()

        self.series_customization_manager.clear_customizations()

        self.annotation_manager.clear_annotations()
        self.reference_line_manager.clear_all_reference_lines()
        self.subplot_manager.clear_configs()

        self.status_bar.log_action(
            "Plot cleared",
            details={"operation": "clear_plot"},
            level="INFO"
        )
        QTimer.singleShot(100, lambda: setattr(self, "_is_clearing", False))

    def _toggle_secondary_input(self, enabled: bool):
        self.data_selection_manager.toggle_secondary_input(enabled)

    def load_config(self, config: dict) -> None:
        """Load plot configuration"""
        try:
            self.config_manager.load_config(config)
            self.status_bar.log("Plot Config loaded", LogLevel.INFO)
        except Exception as LoadConfigError:
            self.status_bar.log(f"Error loading plot config from saved project: {str(LoadConfigError)}", LogLevel.ERROR)

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
                self.status_bar.log("Plotting Studio Greeting HTML File not found", LogLevel.ERROR)
                greeting_html = "<div style='text-align: center; font-family: sans-serif; padding: 40px; color: #64748b;'><h2>Plot Studio</h2><p>Design and customize your visualizations.</p></div>"
        except Exception as ReadGreetingError:
            self.status_bar.log(f"Failed to load greeting HTML: {str(ReadGreetingError)}", LogLevel.ERROR)
            greeting_html = "<div style='text-align: center; font-family: sans-serif; padding: 40px; color: #64748b;'><h2>Plot Studio</h2></div>"

        if hasattr(self, "empty_state_view") and self.empty_state_view is not None:
            self.empty_state_view.setHtml(greeting_html)
