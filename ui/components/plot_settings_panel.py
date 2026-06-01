from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QHBoxLayout, QLineEdit, QPushButton, QGroupBox, QLabel, QGraphicsOpacityEffect
from PyQt6.QtGui import QIcon, QShortcut, QKeySequence
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve

from core.help_manager import HelpManager
from ui.dialogs import HelpDialog
from ui.icons import IconBuilder, IconType

class PlotSettingsPanel(QWidget):
    """
    Component handling the right-hand settings panel for PlotTab.
    Encapsulates all configuration tabs: General, Appearance, Axes, Legend, etc.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.help_manager = HelpManager()
        self._is_searching = False
        self._tab_visibility_snapshot = {}
        self._groupbox_visibility_snapshot = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        self.settings_search_input = QLineEdit()
        self.settings_search_input.setObjectName("settingsSearchInput")
        self.settings_search_input.setPlaceholderText("Search settings (e.g., 'Spines')")
        self.settings_search_input.setClearButtonEnabled(True)
        self.settings_search_input.textChanged.connect(self._filter_settings)
        header_layout.addWidget(self.settings_search_input)
        self.setup_animation_for_search_bar()
        self.setup_search_bar_shortcuts()

        layout.addLayout(header_layout)

        self.custom_tabs = QTabWidget()

        # TAB 1: BASIC
        from ui.components.plot_tabs.general_settings_tab import GeneralSettingsTab
        self.basic_tab = GeneralSettingsTab(self)
        basic_tab_icon = QIcon(IconBuilder.build(IconType.PlotGeneralOptions))
        self.custom_tabs.addTab(self.basic_tab, basic_tab_icon, "General")
        
        self._expose_general_tab_widgets()

        # TAB 2: APPEARANCE
        from ui.components.plot_tabs.appearance_settings_tab import AppearanceSettingsTab
        self.appearance_tab_widget = AppearanceSettingsTab(self)
        appearance_tab_icon = QIcon(IconBuilder.build(IconType.PlotAppearance))
        self.custom_tabs.addTab(self.appearance_tab_widget, appearance_tab_icon, "Appearance")
        
        self._expose_appearance_tab_widgets()

        # TAB 3: AXES
        from ui.components.plot_tabs.axes_settings_tab import AxesSettingsTab
        self.axes_tab = AxesSettingsTab(self)
        axes_tab_icon = QIcon(IconBuilder.build(IconType.PlotAxes))
        self.custom_tabs.addTab(self.axes_tab, axes_tab_icon, "Axes")
        
        self._expose_axes_tab_widgets()

        # TAB 4: LEGEND and GRID
        from ui.components.plot_tabs.legend_grid_settings import LegendGridSettingstab
        self.legend_tab = LegendGridSettingstab(self)
        legend_tab_icon = QIcon(IconBuilder.build(IconType.PlotLegendGrid))
        self.custom_tabs.addTab(self.legend_tab, legend_tab_icon, "Legend and Grid")
        
        self._expose_legend_grid_tab_widgets()

        # TAB 5: ADVANCED / Customization
        from ui.components.plot_tabs.customization_settings_tab import CustomizationSettingsTab
        self.customization_tab = CustomizationSettingsTab(self)
        advanced_tab_icon = QIcon(IconBuilder.build(IconType.PlotCustomization))
        self.custom_tabs.addTab(self.customization_tab, advanced_tab_icon, "Customization")
        
        self._expose_customization_tab_widgets()

        # TAB 6: ANNOTATIONS
        from ui.components.plot_tabs.annotations_settings_tab import AnnotationsSettingsTab
        self.annotations_tab = AnnotationsSettingsTab(self)
        annotations_tab_icon = QIcon(IconBuilder.build(IconType.PlotAnnotations))
        self.custom_tabs.addTab(self.annotations_tab, annotations_tab_icon, "Annotations")
        
        self._expose_annotations_tab_widgets()

        # TAB 7: GEO
        from ui.components.plot_tabs.geospatial_settings_tab import GeospatialSettingsTab
        self.geospatial_tab = GeospatialSettingsTab(self)
        geospatial_tab_icon = QIcon(IconBuilder.build(IconType.PlotGeospatial))
        self.custom_tabs.addTab(self.geospatial_tab, geospatial_tab_icon, "GeoSpatial")
        
        self._expose_geospatial_tab_widgets()

        layout.addWidget(self.custom_tabs)

    def setup_animation_for_search_bar(self) -> None:
        """Setups the opacity and slide animations for the settings search"""
        self.opacity_effect = QGraphicsOpacityEffect(self.settings_search_input)
        self.opacity_effect.setOpacity(0.0)
        self.settings_search_input.setGraphicsEffect(self.opacity_effect)

        animation_duration: int = 200
        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_animation.setDuration(animation_duration)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.slide_animation = QPropertyAnimation(self.settings_search_input, b"maximumHeight")
        self.slide_animation.setDuration(animation_duration)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.settings_search_input.setMaximumHeight(0)
        self.settings_search_input.setVisible(False)

    def setup_search_bar_shortcuts(self) -> None:
        """Sets up the keyboard shortcuts for activating and closing settings searching"""
        self.search_shortcut = QShortcut(QKeySequence(QKeySequence.StandardKey.Find), self)
        self.search_shortcut.activated.connect(self.open_search)

        self.close_shortcut = QShortcut(QKeySequence("Esc"), self.settings_search_input)
        self.close_shortcut.activated.connect(self.close_search)
    
    def _expose_general_tab_widgets(self) -> None:
        self.plot_type_group = self.basic_tab.plot_type_group
        self.current_plot_label = self.basic_tab.current_plot_label
        self.plot_type = self.basic_tab.plot_type
        self.add_subplots_check = self.basic_tab.add_subplots_check
        self.use_subset_check = self.basic_tab.use_subset_check
        
        self.subplot_group = self.basic_tab.subplot_group
        self.grid_designer = self.basic_tab.grid_designer
        self.subplot_sharex_check = self.basic_tab.subplot_sharex_check
        self.subplot_sharey_check = self.basic_tab.subplot_sharey_check
        
        self.active_subplot_combo = self.basic_tab.active_subplot_combo
        self.freeze_data_check = self.basic_tab.freeze_data_check
        
        self.x_column = self.basic_tab.x_column
        self.multi_y_check = self.basic_tab.multi_y_check
        self.y_column = self.basic_tab.y_column
        self.y_columns_list = self.basic_tab.y_columns_list
        self.z_column = self.basic_tab.z_column
        self.z_column_widget = self.basic_tab.z_column_widget
        self.select_all_y_btn = self.basic_tab.select_all_y_btn
        self.clear_all_y_btn = self.basic_tab.clear_all_y_btn
        self.multi_y_info = self.basic_tab.multi_y_info
        
        self.secondary_y_check = self.basic_tab.secondary_y_check
        self.secondary_y_column = self.basic_tab.secondary_y_column
        self.secondary_plot_type_combo = self.basic_tab.secondary_plot_type_combo
        
        self.quick_filter_input = self.basic_tab.quick_filter_input
        
        self.subset_combo = self.basic_tab.subset_combo
        self.refresh_subsets_btn = self.basic_tab.refresh_subsets_btn
        
        self.hue_column = self.basic_tab.hue_column

        self.basic_tab.help_requested.connect(self.show_help_dialog)

    def _expose_appearance_tab_widgets(self) -> None:
        """
        Exposes widgets from the encapsulated AppearanceSettingsTab.
        """
        app_tab = self.appearance_tab_widget
        
        # Themes
        self.theme_combo = app_tab.theme_combo
        self.load_theme_button = app_tab.load_theme_button
        self.save_theme_button = app_tab.save_theme_button
        self.edit_theme_button = app_tab.edit_theme_button
        self.delete_theme_button = app_tab.delete_theme_button
        
        # Font
        self.font_family_combo = app_tab.font_family_combo
        self.usetex_checkbox = app_tab.usetex_checkbox
        
        # Title
        self.title_check = app_tab.title_check
        self.title_input = app_tab.title_input
        self.title_size_spin = app_tab.title_size_spin
        self.title_weight_combo = app_tab.title_weight_combo
        self.title_position_combo = app_tab.title_position_combo
        
        # X/Y Labels
        self.xlabel_check = app_tab.xlabel_check
        self.xlabel_input = app_tab.xlabel_input
        self.xlabel_size_spin = app_tab.xlabel_size_spin
        self.xlabel_weight_combo = app_tab.xlabel_weight_combo
        
        self.ylabel_check = app_tab.ylabel_check
        self.ylabel_input = app_tab.ylabel_input
        self.ylabel_size_spin = app_tab.ylabel_size_spin
        self.ylabel_weight_combo = app_tab.ylabel_weight_combo
        
        self.zlabel_widget = app_tab.z_label_widget
        self.zlabel_check = app_tab.zlabel_check
        self.zlabel_input = app_tab.zlabel_input
        self.zlabel_size = app_tab.zlabel_size_spin
        self.zlabel_weight = app_tab.zlabel_weight
        
        # Spines
        self.all_spines_btn = app_tab.all_spines_btn
        self.box_only_btn = app_tab.box_only_btn
        self.no_spines_btn = app_tab.no_spines_btn
        
        self.global_spine_width_spin = app_tab.global_spine_width_spin
        self.global_spine_color_button = app_tab.global_spine_color_button
        self.global_spine_color_label = app_tab.global_spine_color_label
        
        self.individual_spines_check = app_tab.individual_spines_check
        self.individual_spines_container = app_tab.individual_spines_container
        
        self.top_spine_visible_check = app_tab.top_spine_visible_check
        self.top_spine_width_spin = app_tab.top_spine_width_spin
        self.top_spine_color_button = app_tab.top_spine_color_button
        self.top_spine_color_label = app_tab.top_spine_color_label
        
        self.bottom_spine_visible_check = app_tab.bottom_spine_visible_check
        self.bottom_spine_width_spin = app_tab.bottom_spine_width_spin
        self.bottom_spine_color_button = app_tab.bottom_spine_color_button
        self.bottom_spine_color_label = app_tab.bottom_spine_color_label
        
        self.left_spine_visible_check = app_tab.left_spine_visible_check
        self.left_spine_width_spin = app_tab.left_spine_width_spin
        self.left_spine_color_button = app_tab.left_spine_color_button
        self.left_spine_color_label = app_tab.left_spine_color_label
        
        self.right_spine_visible_check = app_tab.right_spine_visible_check
        self.right_spine_width_spin = app_tab.right_spine_width_spin
        self.right_spine_color_button = app_tab.right_spine_color_button
        self.right_spine_color_label = app_tab.right_spine_color_label
        
        # Figure 
        self.width_spin = app_tab.width_spin
        self.height_spin = app_tab.height_spin
        self.dpi_spin = app_tab.dpi_spin
        self.bg_color_button = app_tab.bg_color_button
        self.bg_color_label = app_tab.bg_color_label
        self.face_color_button = app_tab.face_color_button
        self.face_color_label = app_tab.face_color_label
        self.palette_combo = app_tab.palette_combo
        
        # 3D Camera Group
        self.camera_3d_group = app_tab.camera_3d_group
        self.camera_elevation_spin = app_tab.camera_elevation_spin
        self.camera_azimuth_spin = app_tab.camera_azimuth_spin
        
        # Accessibility and Style
        self.colorblind_check = app_tab.colorblind_check
        self.colorblind_type_combo = app_tab.colorblind_type_combo
        self.tight_layout_check = app_tab.tight_layout_check
        self.style_combo = app_tab.style_combo

        # Route signals
        app_tab.help_requested.connect(self.show_help_dialog)

    def _expose_axes_tab_widgets(self) -> None:
        """
        Exposes widgets from the encapsulated AxesSettingsTab.
        """
        axes_t = self.axes_tab

        # X-axis Options
        self.x_auto_check = axes_t.x_auto_check
        self.x_invert_axis_check = axes_t.x_invert_axis_check
        self.x_top_axis_check = axes_t.x_top_axis_check
        self.x_min_spin = axes_t.x_min_spin
        self.x_max_spin = axes_t.x_max_spin
        self.xtick_label_size_spin = axes_t.xtick_label_size_spin
        self.xtick_rotation_spin = axes_t.xtick_rotation_spin
        self.x_max_ticks_spin = axes_t.x_max_ticks_spin
        self.x_show_minor_ticks_check = axes_t.x_show_minor_ticks_check
        self.x_major_tick_direction_combo = axes_t.x_major_tick_direction_combo
        self.x_major_tick_width_spin = axes_t.x_major_tick_width_spin
        self.x_minor_tick_direction_combo = axes_t.x_minor_tick_direction_combo
        self.x_minor_tick_width_spin = axes_t.x_minor_tick_width_spin
        self.x_scale_combo = axes_t.x_scale_combo
        self.x_display_units_combo = axes_t.x_display_units_combo

        # Y-axis Options
        self.y_auto_check = axes_t.y_auto_check
        self.y_invert_axis_check = axes_t.y_invert_axis_check
        self.y_min_spin = axes_t.y_min_spin
        self.y_max_spin = axes_t.y_max_spin
        self.ytick_label_size_spin = axes_t.ytick_label_size_spin
        self.ytick_rotation_spin = axes_t.ytick_rotation_spin
        self.y_max_ticks_spin = axes_t.y_max_ticks_spin
        self.y_show_minor_ticks_check = axes_t.y_show_minor_ticks_check
        self.y_major_tick_direction_combo = axes_t.y_major_tick_direction_combo
        self.y_major_tick_width_spin = axes_t.y_major_tick_width_spin
        self.y_minor_tick_direction_combo = axes_t.y_minor_tick_direction_combo
        self.y_minor_tick_width_spin = axes_t.y_minor_tick_width_spin
        self.y_scale_combo = axes_t.y_scale_combo
        self.y_display_units_combo = axes_t.y_display_units_combo
        
        # Z-axis Options
        self.axis_tab_widget = axes_t.axis_tab_widget
        self.z_tab = axes_t.z_tab
        self.z_auto_check = axes_t.z_auto_check
        self.z_invert_axis_check = axes_t.z_invert_axis_check
        self.z_min_spin = axes_t.z_min_spin
        self.z_max_spin = axes_t.z_max_spin
        self.ztick_label_size_spin = axes_t.ztick_label_size_spin
        self.ztick_rotation_spin = axes_t.ztick_rotation_spin
        self.z_max_ticks_spin = axes_t.z_max_ticks_spin
        self.z_show_minor_ticks_check = axes_t.z_show_minor_ticks_check
        self.z_major_tick_direction_combo = axes_t.z_major_tick_direction_combo
        self.z_major_tick_width_spin = axes_t.z_major_tick_width_spin
        self.z_minor_tick_direction_combo = axes_t.z_minor_tick_direction_combo
        self.z_minor_tick_width_spin = axes_t.z_minor_tick_width_spin
        self.z_scale_combo = axes_t.z_scale_combo
        self.z_display_units_combo = axes_t.z_display_units_combo

        # Orientation
        self.flip_axes_check = axes_t.flip_axes_check

        # Datetime formatting
        self.custom_datetime_check = axes_t.custom_datetime_check
        
        self.format_x_datetime_label = axes_t.format_x_datetime_label
        self.x_datetime_format_combo = axes_t.x_datetime_format_combo
        self.custom_x_axis_format_label = axes_t.custom_x_axis_format_label
        self.x_custom_datetime_input = axes_t.x_custom_datetime_input
        
        self.format_y_datetime_label = axes_t.format_y_datetime_label
        self.y_datetime_format_combo = axes_t.y_datetime_format_combo
        self.custom_y_axis_format_label = axes_t.custom_y_axis_format_label
        self.y_custom_datetime_format_input = axes_t.y_custom_datetime_format_input
        self.format_help = axes_t.format_help

    def _expose_legend_grid_tab_widgets(self) -> None:
        """
        Exposes widgets from the encapsulated LegendGridSettingsTab.
        """
        lg_tab = self.legend_tab

        # Legend
        self.legend_check = lg_tab.legend_check
        self.legend_loc_combo = lg_tab.legend_loc_combo
        self.legend_title_input = lg_tab.legend_title_input
        self.legend_labels_input = lg_tab.legend_labels_input
        self.legend_size_spin = lg_tab.legend_size_spin
        self.legend_title_size_spin = lg_tab.legend_title_size_spin
        self.legend_columns_spin = lg_tab.legend_columns_spin
        self.legend_colspace_spin = lg_tab.legend_colspace_spin

        # Legend Box Styling
        self.legend_frame_check = lg_tab.legend_frame_check
        self.legend_fancybox_check = lg_tab.legend_fancybox_check
        self.legend_shadow_check = lg_tab.legend_shadow_check
        self.legend_bg_button = lg_tab.legend_bg_button
        self.legend_bg_label = lg_tab.legend_bg_label
        self.legend_edge_button = lg_tab.legend_edge_button
        self.legend_edge_label = lg_tab.legend_edge_label
        self.legend_edge_width_spin = lg_tab.legend_edge_width_spin
        self.legend_alpha_slider = lg_tab.legend_alpha_slider
        self.legend_alpha_label = lg_tab.legend_alpha_label

        # Grids
        self.grid_check = lg_tab.grid_check
        self.global_grid_group = lg_tab.global_grid_group
        self.grid_which_type_combo = lg_tab.grid_which_type_combo
        self.grid_axis_combo = lg_tab.grid_axis_combo
        self.global_grid_color_button = lg_tab.global_grid_color_button
        self.global_grid_color_label = lg_tab.global_grid_color_label
        self.global_grid_alpha_slider = lg_tab.global_grid_alpha_slider
        self.global_grid_alpha_label = lg_tab.global_grid_alpha_label
        
        self.independent_grid_check = lg_tab.independent_grid_check
        self.grid_axis_tab = lg_tab.grid_axis_tab

        # Independent grids: X Major
        self.x_major_grid_check = lg_tab.x_major_grid_check
        self.x_major_grid_style_combo = lg_tab.x_major_grid_style_combo
        self.x_major_grid_linewidth_spin = lg_tab.x_major_grid_linewidth_spin
        self.x_major_grid_color_button = lg_tab.x_major_grid_color_button
        self.x_major_grid_color_label = lg_tab.x_major_grid_color_label
        self.x_major_grid_alpha_slider = lg_tab.x_major_grid_alpha_slider
        self.x_major_grid_alpha_label = lg_tab.x_major_grid_alpha_label

        # Independent grids: X Minor
        self.x_minor_grid_check = lg_tab.x_minor_grid_check
        self.x_minor_grid_style_combo = lg_tab.x_minor_grid_style_combo
        self.x_minor_grid_linewidth_spin = lg_tab.x_minor_grid_linewidth_spin
        self.x_minor_grid_color_button = lg_tab.x_minor_grid_color_button
        self.x_minor_grid_color_label = lg_tab.x_minor_grid_color_label
        self.x_minor_grid_alpha_slider = lg_tab.x_minor_grid_alpha_slider
        self.x_minor_grid_alpha_label = lg_tab.x_minor_grid_alpha_label

        # Independent grids: Y Major
        self.y_major_grid_check = lg_tab.y_major_grid_check
        self.y_major_grid_style_combo = lg_tab.y_major_grid_style_combo
        self.y_major_grid_linewidth_spin = lg_tab.y_major_grid_linewidth_spin
        self.y_major_grid_color_button = lg_tab.y_major_grid_color_button
        self.y_major_grid_color_label = lg_tab.y_major_grid_color_label
        self.y_major_grid_alpha_slider = lg_tab.y_major_grid_alpha_slider
        self.y_major_grid_alpha_label = lg_tab.y_major_grid_alpha_label

        # Independent grids: Y Minor
        self.y_minor_grid_check = lg_tab.y_minor_grid_check
        self.y_minor_grid_style_combo = lg_tab.y_minor_grid_style_combo
        self.y_minor_grid_linewidth_spin = lg_tab.y_minor_grid_linewidth_spin
        self.y_minor_grid_color_button = lg_tab.y_minor_grid_color_button
        self.y_minor_grid_color_label = lg_tab.y_minor_grid_color_label
        self.y_minor_grid_alpha_slider = lg_tab.y_minor_grid_alpha_slider
        self.y_minor_grid_alpha_label = lg_tab.y_minor_grid_alpha_label
    
    def _expose_customization_tab_widgets(self) -> None:
        """
        Exposes widgets from the encapsulated CustomizationSettingsTab.
        """
        cust_tab = self.customization_tab

        # Stack references
        self.advanced_stack = cust_tab.advanced_stack
        self.page_line = cust_tab.page_line
        self.page_bar_hist = cust_tab.page_bar_hist
        self.page_scatter = cust_tab.page_scatter
        self.page_pie = cust_tab.page_pie
        self.page_empty = cust_tab.page_empty

        # Line Properties
        self.multiline_custom_check = cust_tab.multiline_custom_check
        self.line_selector_label = cust_tab.line_selector_label
        self.line_selector_combo = cust_tab.line_selector_combo
        self.linewidth_spin = cust_tab.linewidth_spin
        self.linestyle_combo = cust_tab.linestyle_combo
        self.line_color_button = cust_tab.line_color_button
        self.line_color_label = cust_tab.line_color_label

        # Bar and Histogram Properties
        self.histogram_bins_spin = cust_tab.histogram_bins_spin
        self.histogram_show_normal_check = cust_tab.histogram_show_normal_check
        self.histogram_show_kde_check = cust_tab.histogram_show_kde_check
        
        self.multibar_custom_check = cust_tab.multibar_custom_check
        self.bar_selector_label = cust_tab.bar_selector_label
        self.bar_selector_combo = cust_tab.bar_selector_combo
        self.bar_width_spin = cust_tab.bar_width_spin
        self.bar_color_button = cust_tab.bar_color_button
        self.bar_color_label = cust_tab.bar_color_label
        self.bar_edge_button = cust_tab.bar_edge_button
        self.bar_edge_label = cust_tab.bar_edge_label
        self.bar_edge_width_spin = cust_tab.bar_edge_width_spin

        # Scatter Properties
        self.scatter_group = cust_tab.scatter_group
        self.regression_line_check = cust_tab.regression_line_check
        self.regression_type_combo = cust_tab.regression_type_combo
        self.poly_degree_label = cust_tab.poly_degree_label
        self.poly_degree_spin = cust_tab.poly_degree_spin
        self.confidence_interval_check = cust_tab.confidence_interval_check
        self.show_r2_check = cust_tab.show_r2_check
        self.show_rmse_check = cust_tab.show_rmse_check
        self.show_equation_check = cust_tab.show_equation_check
        self.confidence_level_spin = cust_tab.confidence_level_spin

        # Pie Properties
        self.pie_group = cust_tab.pie_group
        self.pie_show_percentages_check = cust_tab.pie_show_percentages_check
        self.pie_start_angle_spin = cust_tab.pie_start_angle_spin
        self.pie_explode_check = cust_tab.pie_explode_check
        self.pie_explode_distance_spin = cust_tab.pie_explode_distance_spin
        self.pie_shadow_check = cust_tab.pie_shadow_check
        self.pie_donut_check = cust_tab.pie_donut_check
        self.pie_donut_width_spin = cust_tab.pie_donut_width_spin

        # Marker Properties
        self.marker_group = cust_tab.marker_group
        self.marker_combo = cust_tab.marker_combo
        self.marker_size_spin = cust_tab.marker_size_spin
        self.marker_color_button = cust_tab.marker_color_button
        self.marker_color_label = cust_tab.marker_color_label
        self.marker_edge_button = cust_tab.marker_edge_button
        self.marker_edge_label = cust_tab.marker_edge_label
        self.marker_edge_width_spin = cust_tab.marker_edge_width_spin

        # Error Bars Properties
        self.error_bars_group = cust_tab.error_bars_group
        self.error_bars_combo = cust_tab.error_bars_combo
        self.error_bar_color_button = cust_tab.error_bar_color_button
        self.error_bar_linewidth_spin = cust_tab.error_bar_linewidth_spin
        self.error_bar_capsize_spin = cust_tab.error_bar_capsize_spin
        self.error_bar_alpha_slider = cust_tab.error_bar_alpha_slider
        self.error_bar_zorder_spin = cust_tab.error_bar_zorder_spin
        self.error_bar_color_label = cust_tab.error_bar_color_label
        self.error_bar_alpha_label = cust_tab.error_bar_alpha_label

        # Transparency Properties
        self.alpha_slider = cust_tab.alpha_slider
        self.alpha_label = cust_tab.alpha_label
    
    def _expose_annotations_tab_widgets(self) -> None:
        """
        Exposes widgets from the encapsulated AnnotationsSettingsTab.
        """
        ann_tab = self.annotations_tab

        # Reference lines
        self.reference_lines_list = ann_tab.reference_lines_list
        self.add_ref_line_button = ann_tab.add_ref_line_button
        self.clear_ref_lines_button = ann_tab.clear_ref_lines_button
        self.ref_line_type_combo = ann_tab.ref_line_type_combo
        self.ref_line_y_spin = ann_tab.ref_line_y_spin
        self.ref_line_x_spin = ann_tab.ref_line_x_spin
        self.ref_line_slope_spin = ann_tab.ref_line_slope_spin
        self.ref_line_intercept_spin = ann_tab.ref_line_intercept_spin
        self.ref_line_color_button = ann_tab.ref_line_color_button
        self.ref_line_color_label = ann_tab.ref_line_color_label
        self.ref_line_style_combo = ann_tab.ref_line_style_combo
        self.ref_line_width_spin = ann_tab.ref_line_width_spin
        self.ref_line_alpha_spin = ann_tab.ref_line_alpha_spin
        self.ref_line_label_input = ann_tab.ref_line_label_input
        self.update_ref_line_button = ann_tab.update_ref_line_button
        self.delete_ref_line_button = ann_tab.delete_ref_line_button

        # Manual Annotations
        self.annotation_text = ann_tab.annotation_text
        self.annotation_x_spin = ann_tab.annotation_x_spin
        self.annotation_y_spin = ann_tab.annotation_y_spin
        self.annotation_fontsize_spin = ann_tab.annotation_fontsize_spin
        self.annotation_color_button = ann_tab.annotation_color_button
        self.annotation_color_label = ann_tab.annotation_color_label
        self.annotation_bg_color_button = ann_tab.annotation_bg_color_button
        self.annotation_bg_color_label = ann_tab.annotation_bg_color_label
        self.add_annotation_button = ann_tab.add_annotation_button

        # Auto Annotations
        self.auto_annotate_check = ann_tab.auto_annotate_check
        self.auto_annotate_col_combo = ann_tab.auto_annotate_col_combo
        self.auto_annotate_fontsize_spin = ann_tab.auto_annotate_fontsize_spin
        self.auto_annotate_weight_combo = ann_tab.auto_annotate_weight_combo
        self.auto_annotate_color_button = ann_tab.auto_annotate_color_button
        self.auto_annotate_color_label = ann_tab.auto_annotate_color_label
        self.auto_annotate_x_offset_spin = ann_tab.auto_annotate_x_offset_spin
        self.auto_annotate_y_offset_spin = ann_tab.auto_annotate_y_offset_spin
        self.auto_annotate_rotation_spin = ann_tab.auto_annotate_rotation_spin

        # Text Box
        self.textbox_content = ann_tab.textbox_content
        self.textbox_position_combo = ann_tab.textbox_position_combo
        self.textbox_style_combo = ann_tab.textbox_style_combo
        self.textbox_bg_button = ann_tab.textbox_bg_button
        self.textbox_bg_label = ann_tab.textbox_bg_label
        self.textbox_enable_check = ann_tab.textbox_enable_check

        # Data Table
        self.table_enable_check = ann_tab.table_enable_check
        self.table_type_combo = ann_tab.table_type_combo
        self.table_location_combo = ann_tab.table_location_combo
        self.table_auto_font_size_check = ann_tab.table_auto_font_size_check
        self.table_font_size_spin = ann_tab.table_font_size_spin
        self.table_scale_spin = ann_tab.table_scale_spin

        # Annotations List
        self.annotations_list = ann_tab.annotations_list
        self.clear_annotations_button = ann_tab.clear_annotations_button

    def _expose_geospatial_tab_widgets(self) -> None:
        """
        Exposes widgets from the encapsulated GeospatialSettingsTab.
        """
        geo_tab = self.geospatial_tab
        
        # Projection and Basemap
        self.geo_target_crs_input = geo_tab.geo_target_crs_input
        self.geo_basemap_check = geo_tab.geo_basemap_check
        self.geo_basemap_style_combo = geo_tab.geo_basemap_style_combo
        
        # Choropleth
        self.geo_scheme_combo = geo_tab.geo_scheme_combo
        self.geo_k_spin = geo_tab.geo_k_spin
        
        # Legend and Axes
        self.geo_legend_check = geo_tab.geo_legend_check
        self.geo_legend_loc_combo = geo_tab.geo_legend_loc_combo
        self.geo_use_divider_check = geo_tab.geo_use_divider_check
        self.geo_cax_check = geo_tab.geo_cax_check
        self.geo_axis_off_check = geo_tab.geo_axis_off_check
        
        # Missing Data
        self.geo_missing_label_input = geo_tab.geo_missing_label_input
        self.geo_missing_color_btn = geo_tab.geo_missing_color_btn
        self.geo_missing_color_label = geo_tab.geo_missing_color_label
        self.geo_missing_color = geo_tab.geo_missing_color
        self.geo_hatch_combo = geo_tab.geo_hatch_combo
        
        # Boundaries
        self.geo_boundary_check = geo_tab.geo_boundary_check
        self.geo_edge_color_btn = geo_tab.geo_edge_color_btn
        self.geo_edge_color_label = geo_tab.geo_edge_color_label
        self.geo_edge_color = geo_tab.geo_edge_color
        self.geo_linewidth_spin = geo_tab.geo_linewidth_spin

    def show_help_dialog(self, topic_id: str):
        try:
            title, description, link = self.help_manager.get_help_topic(topic_id)

            if title:
                dialog = HelpDialog(self, topic_id, title, description, link)
                dialog.exec()
            else:
                # Fallback if no specific topic found
                pass
        except Exception:
            pass

    def open_search(self) -> None:
        """Displays the search bar with the slide animation and focuses input"""
        self.settings_search_input.setVisible(True)
        self.opacity_animation.stop()
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)

        self.slide_animation.stop()
        self.slide_animation.setStartValue(0)
        target_height: int = max(self.settings_search_input.sizeHint().height(), 28)
        self.slide_animation.setEndValue(target_height)

        self.opacity_animation.start()
        self.slide_animation.start()

        self.settings_search_input.setFocus()
        self.settings_search_input.selectAll()

    def close_search(self) -> None:
        """Hides the search bar with a slide animation and clears the input"""
        self.opacity_animation.stop()
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)

        self.slide_animation.stop()
        self.slide_animation.setStartValue(self.settings_search_input.height())
        self.slide_animation.setEndValue(0)
        self.slide_animation.finished.connect(self._on_close_animation_finished)

        self.opacity_animation.start()
        self.slide_animation.start()

    def _on_close_animation_finished(self) -> None:
        """Called when the close animation finished to hide the widget"""
        self.slide_animation.finished.disconnect(self._on_close_animation_finished)
        self.settings_search_input.hide()
        self.settings_search_input.clear()
    
    def _filter_settings(self, search_text: str) -> None:
        """
        Filters the visibility of setings group boxes across all tabs
        """
        search_lower = search_text.lower()
        
        if not search_lower:
            if self._is_searching:
                self._restore_visibility()
                self._is_searching = False
            return
        
        if not self._is_searching:
            self._snapshot_visibility()
            self._is_searching = True
        
        first_match_index = -1
        current_tab_has_match = False
        
        for i in range(self.custom_tabs.count()):
            tab_widget = self.custom_tabs.widget(i)
            
            if not self._tab_visibility_snapshot.get(i, True):
                self.custom_tabs.setTabVisible(i, False)
                continue
            
            tab_has_match = self._apply_filter_to_widget(tab_widget, search_lower)
            
            self.custom_tabs.setTabVisible(i, tab_has_match)
            
            if tab_has_match:
                if first_match_index == -1:
                    first_match_index = i
                if i == self.custom_tabs.currentIndex():
                    current_tab_has_match = True
        if not current_tab_has_match and first_match_index != -1:
            self.custom_tabs.setCurrentIndex(first_match_index)
    
    def _apply_filter_to_widget(self, parent_widget: QWidget, search_text: str) -> bool:
        """Recursively checks QGroupBox elements within a widget to hide or show them
        based on their titles or the text of their enclosed children."""
        any_match_in_tab = False
        
        for group_box in parent_widget.findChildren(QGroupBox):
            if not self._groupbox_visibility_snapshot.get(id(group_box), True):
                group_box.setVisible(False)
                continue
            has_match = search_text in group_box.title().lower()
            
            if not has_match:
                for child in group_box.findChildren(QWidget):
                    if isinstance(child, QLabel) and search_text in child.text().lower():
                        has_match = True
                        break
                    
                    if hasattr(child, "text") and callable(child.text):
                        child_text = child.text()
                        if isinstance(child_text, str) and search_text in child_text.lower():
                            has_match = True
                            break
            
            group_box.setVisible(has_match)
            if has_match:
                any_match_in_tab = True
        return any_match_in_tab

    def _snapshot_visibility(self) -> None:
        self._tab_visibility_snapshot.clear()
        for i in range(self.custom_tabs.count()):
            self._tab_visibility_snapshot[i] = self.custom_tabs.isTabVisible(i)
        
        self._groupbox_visibility_snapshot.clear()
        for group_box in self.findChildren(QGroupBox):
            self._groupbox_visibility_snapshot[id(group_box)] = not group_box.isHidden()
    
    def _restore_visibility(self) -> None:
        for i in range(self.custom_tabs.count()):
            is_visible = self._tab_visibility_snapshot.get(i, True)
            self.custom_tabs.setTabVisible(i, is_visible)
        
        for group_box in self.findChildren(QGroupBox):
            is_visible = self._groupbox_visibility_snapshot.get(id(group_box), True)
            group_box.setVisible(is_visible)