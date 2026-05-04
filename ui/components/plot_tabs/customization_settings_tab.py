from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QLayout, QTabWidget
from PyQt6.QtCore import Qt

from ui.theme import ThemeColors
from ui.widgets import AutoResizingStackedWidget, DataPlotStudioToggleSwitch, DataPlotStudioButton
from ui.widgets.ControlElements import DataPlotStudioComboBox, DataPlotStudioDoubleSpinBox, DataPlotStudioGroupBox, DataPlotStudioSlider, DataPlotStudioSpinBox

class CustomizationSettingsTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        scroll_widget = QWidget()
        scroll_widget.setObjectName("ScrollContent")
        scroll_layout = QVBoxLayout(scroll_widget)

        # Dynamic plot-type specific stack
        self._setup_dynamic_stack(scroll_layout)
        scroll_layout.addSpacing(15)

        # Global advanced settings
        self._setup_marker_group(scroll_layout)
        scroll_layout.addSpacing(15)
        self._setup_error_bars_group(scroll_layout)
        scroll_layout.addSpacing(15)
        self._setup_transparency_group(scroll_layout)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

    def _setup_dynamic_stack(self, parent_layout: QVBoxLayout) -> None:
        """Sets up the stacked widget that swaps UI parameters based on plot type."""
        self.advanced_stack = QWidget()
        self.advanced_stack_layout = QVBoxLayout(self.advanced_stack)
        self.advanced_stack_layout.setContentsMargins(0, 0, 0, 0)
        self.advanced_stack_layout.setSpacing(15)

        self._setup_line_page()
        self._setup_bar_hist_page()
        self._setup_scatter_page()
        self._setup_pie_page()
        self._setup_empty_page()

        parent_layout.addWidget(self.advanced_stack)

    def _setup_line_page(self) -> None:
        self.page_line = QWidget()
        layout = QVBoxLayout(self.page_line)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)

        group = DataPlotStudioGroupBox("Line Properties")
        group_layout = QVBoxLayout()

        self.multiline_custom_check = DataPlotStudioToggleSwitch("Enable per-line customization")
        self.multiline_custom_check.setChecked(False)
        group_layout.addWidget(self.multiline_custom_check)

        self.line_selector_label = QLabel("Select Line to customize")
        self.line_selector_label.setVisible(False)
        group_layout.addWidget(self.line_selector_label)

        self.line_selector_combo = DataPlotStudioComboBox()
        self.line_selector_combo.setVisible(False)
        group_layout.addWidget(self.line_selector_combo)

        group_layout.addWidget(QLabel("Line Width:"))
        self.linewidth_spin = DataPlotStudioDoubleSpinBox()
        self.linewidth_spin.setRange(0.5, 5.0)
        self.linewidth_spin.setValue(1.5)
        self.linewidth_spin.setSingleStep(0.1)
        group_layout.addWidget(self.linewidth_spin)

        group_layout.addWidget(QLabel("Line Style:"))
        self.linestyle_combo = DataPlotStudioComboBox()
        self.linestyle_combo.addItems(['-', '--', '-.', ':', 'None'])
        self.linestyle_combo.setItemText(0, 'Solid')
        self.linestyle_combo.setItemText(1, 'Dashed')
        self.linestyle_combo.setItemText(2, 'Dash-dot')
        self.linestyle_combo.setItemText(3, 'Dotted')
        group_layout.addWidget(self.linestyle_combo)

        group_layout.addWidget(QLabel("Line Color:"))
        color_layout = QHBoxLayout()
        self.line_color_button = DataPlotStudioButton("Choose", parent=self)
        self.line_color_label = QLabel("Auto")
        color_layout.addWidget(self.line_color_button)
        color_layout.addWidget(self.line_color_label)
        group_layout.addLayout(color_layout)

        group.setLayout(group_layout)
        layout.addWidget(group)
        layout.addStretch()
        
        self.advanced_stack_layout.addWidget(self.page_line)

    def _setup_bar_hist_page(self) -> None:
        self.page_bar_hist = QWidget()
        layout = QVBoxLayout(self.page_bar_hist)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)

        tab_widget = QTabWidget()

        bar_tab = QWidget()
        bar_layout = QVBoxLayout(bar_tab)

        self.multibar_custom_check = DataPlotStudioToggleSwitch("Enable per-bar customization")
        self.multibar_custom_check.setChecked(False)
        bar_layout.addWidget(self.multibar_custom_check)

        self.bar_selector_label = QLabel("Select Bar Series to Customize")
        self.bar_selector_label.setVisible(False)
        bar_layout.addWidget(self.bar_selector_label)

        self.bar_selector_combo = DataPlotStudioComboBox()
        self.bar_selector_combo.setVisible(False)
        bar_layout.addWidget(self.bar_selector_combo)

        bar_layout.addWidget(QLabel("Bar Width:"))
        self.bar_width_spin = DataPlotStudioDoubleSpinBox()
        self.bar_width_spin.setRange(0.1, 1.0)
        self.bar_width_spin.setValue(0.8)
        self.bar_width_spin.setSingleStep(0.05)
        bar_layout.addWidget(self.bar_width_spin)

        bar_layout.addWidget(QLabel("Bar Color:"))
        color_layout = QHBoxLayout()
        self.bar_color_button = DataPlotStudioButton("Choose Color", parent=self)
        self.bar_color_label = QLabel("Auto")
        color_layout.addWidget(self.bar_color_button)
        color_layout.addWidget(self.bar_color_label)
        bar_layout.addLayout(color_layout)

        bar_layout.addWidget(QLabel("Bar Edge Color:"))
        edge_color_layout = QHBoxLayout()
        self.bar_edge_button = DataPlotStudioButton("Choose", parent=self)
        self.bar_edge_label = QLabel("Auto")
        edge_color_layout.addWidget(self.bar_edge_button)
        edge_color_layout.addWidget(self.bar_edge_label)
        bar_layout.addLayout(edge_color_layout)

        bar_layout.addWidget(QLabel("Bar Edge Width:"))
        self.bar_edge_width_spin = DataPlotStudioDoubleSpinBox()
        self.bar_edge_width_spin.setRange(0, 3)
        self.bar_edge_width_spin.setValue(1)
        self.bar_edge_width_spin.setSingleStep(0.1)
        bar_layout.addWidget(self.bar_edge_width_spin)

        bar_layout.addStretch()
        tab_widget.addTab(bar_tab, "Bar Properties")

        hist_tab = QWidget()
        hist_layout = QVBoxLayout(hist_tab)

        hist_layout.addWidget(QLabel("Number of Bins:"))
        self.histogram_bins_spin = DataPlotStudioSpinBox()
        self.histogram_bins_spin.setRange(5, 200)
        self.histogram_bins_spin.setValue(30)
        hist_layout.addWidget(self.histogram_bins_spin)

        self.histogram_show_normal_check = DataPlotStudioToggleSwitch("Overlay a Normal Distribution Curve")
        self.histogram_show_normal_check.setChecked(False)
        hist_layout.addWidget(self.histogram_show_normal_check)

        self.histogram_show_kde_check = DataPlotStudioToggleSwitch("Overlay Kernel Density Estimate")
        self.histogram_show_kde_check.setChecked(False)
        hist_layout.addWidget(self.histogram_show_kde_check)
        
        hist_layout.addStretch()
        tab_widget.addTab(hist_tab, "Histogram Properties")

        layout.addWidget(tab_widget)
        layout.addStretch()

        self.advanced_stack_layout.addWidget(self.page_bar_hist)

    def _setup_scatter_page(self) -> None:
        self.page_scatter = QWidget()
        layout = QVBoxLayout(self.page_scatter)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)

        self.scatter_group = DataPlotStudioGroupBox("Scatter Plot Analysis")
        scatter_layout = QVBoxLayout()

        self.regression_line_check = DataPlotStudioToggleSwitch("Show Linear Regresssion Line")
        scatter_layout.addWidget(self.regression_line_check)
        
        scatter_layout.addWidget(QLabel("Regression Type:"))
        self.regression_type_combo = DataPlotStudioComboBox()
        self.regression_type_combo.addItems(["Linear", "Polynomial", "Exponential", "Logarithmic"])
        scatter_layout.addWidget(self.regression_type_combo)
        
        self.poly_degree_label = QLabel("Polynomial Degree:")
        scatter_layout.addWidget(self.poly_degree_label)
        self.poly_degree_spin = DataPlotStudioSpinBox()
        self.poly_degree_spin.setRange(2, 10)
        self.poly_degree_spin.setValue(2)
        scatter_layout.addWidget(self.poly_degree_spin)
        
        # Internal callback to toggle visibility of polynomial degree components cleanly
        def toggle_poly_degree() -> None:
            is_poly = self.regression_type_combo.currentText() == "Polynomial"
            self.poly_degree_label.setVisible(is_poly)
            self.poly_degree_spin.setVisible(is_poly)
        
        self.regression_type_combo.currentTextChanged.connect(toggle_poly_degree)
        toggle_poly_degree()

        self.confidence_interval_check = DataPlotStudioToggleSwitch("Show 95% confidence interval")
        scatter_layout.addWidget(self.confidence_interval_check)

        self.show_r2_check = DataPlotStudioToggleSwitch("Show R² score")
        self.show_r2_check.setChecked(False)
        scatter_layout.addWidget(self.show_r2_check)

        self.show_rmse_check = DataPlotStudioToggleSwitch("Show Root Mean Square Error (RMSE)")
        scatter_layout.addWidget(self.show_rmse_check)

        self.show_equation_check = DataPlotStudioToggleSwitch("Show Regression Equation")
        scatter_layout.addWidget(self.show_equation_check)

        scatter_layout.addWidget(QLabel("Confidence Level (%):"))
        self.confidence_level_spin = DataPlotStudioSpinBox()
        self.confidence_level_spin.setRange(80, 99)
        self.confidence_level_spin.setValue(95)
        scatter_layout.addWidget(self.confidence_level_spin)

        self.scatter_group.setLayout(scatter_layout)
        layout.addWidget(self.scatter_group)
        layout.addStretch()

        self.advanced_stack_layout.addWidget(self.page_scatter)

    def _setup_pie_page(self) -> None:
        self.page_pie = QWidget()
        layout = QVBoxLayout(self.page_pie)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)

        self.pie_group = DataPlotStudioGroupBox("Pie Chart Properties")
        pie_layout = QVBoxLayout()

        self.pie_show_percentages_check = DataPlotStudioToggleSwitch("Show % on slices")
        self.pie_show_percentages_check.setChecked(False)
        pie_layout.addWidget(self.pie_show_percentages_check)

        pie_layout.addWidget(QLabel("Start Angle (degress):"))
        self.pie_start_angle_spin = DataPlotStudioSpinBox()
        self.pie_start_angle_spin.setRange(0, 360)
        self.pie_start_angle_spin.setValue(0)
        pie_layout.addWidget(self.pie_start_angle_spin)

        self.pie_explode_check = DataPlotStudioToggleSwitch("Explode First Slice")
        self.pie_explode_check.setChecked(False)
        pie_layout.addWidget(self.pie_explode_check)

        pie_layout.addWidget(QLabel("Explode Distance:"))
        self.pie_explode_distance_spin = DataPlotStudioDoubleSpinBox()
        self.pie_explode_distance_spin.setRange(0.0, 0.5)
        self.pie_explode_distance_spin.setValue(0.1)
        self.pie_explode_distance_spin.setSingleStep(0.05)
        pie_layout.addWidget(self.pie_explode_distance_spin)

        self.pie_shadow_check = DataPlotStudioToggleSwitch("Add Shadow")
        self.pie_shadow_check.setChecked(False)
        pie_layout.addWidget(self.pie_shadow_check)
        
        self.pie_donut_check = DataPlotStudioToggleSwitch("Donut Chart")
        self.pie_donut_check.setChecked(False)
        pie_layout.addWidget(self.pie_donut_check)
        
        self.pie_donut_width_label = QLabel("Donut Ring Width:")
        pie_layout.addWidget(self.pie_donut_width_label)
        
        self.pie_donut_width_spin = DataPlotStudioDoubleSpinBox()
        self.pie_donut_width_spin.setRange(0.1, 0.9)
        self.pie_donut_width_spin.setValue(0.3)
        self.pie_donut_width_spin.setSingleStep(0.05)
        pie_layout.addWidget(self.pie_donut_width_spin)
        
        def toggle_donut_width() -> None:
            is_donut = self.pie_donut_check.isChecked()
            self.pie_donut_width_label.setVisible(is_donut)
            self.pie_donut_width_spin.setVisible(is_donut)
        
        self.pie_donut_check.stateChanged.connect(toggle_donut_width)
        toggle_donut_width()

        self.pie_group.setLayout(pie_layout)
        layout.addWidget(self.pie_group)
        layout.addStretch()

        self.advanced_stack_layout.addWidget(self.page_pie)

    def _setup_empty_page(self) -> None:
        """A fallback empty page for unhandled plot types to prevent artifacting."""
        self.page_empty = QWidget()
        layout = QVBoxLayout(self.page_empty)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        self.advanced_stack_layout.addWidget(self.page_empty)

    def _setup_marker_group(self, parent_layout: QVBoxLayout) -> None:
        self.marker_group = DataPlotStudioGroupBox("Marker Properties")
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Marker Shape:"))
        self.marker_combo = DataPlotStudioComboBox()
        self.marker_combo.addItems(['None', 'o', 's', '^', 'v', 'D', '*', '+', 'x', '|', '_', 'p', 'H', 'h'])
        layout.addWidget(self.marker_combo)

        layout.addWidget(QLabel("Marker Size:"))
        self.marker_size_spin = DataPlotStudioSpinBox()
        self.marker_size_spin.setRange(2, 20)
        self.marker_size_spin.setValue(6)
        layout.addWidget(self.marker_size_spin)

        layout.addWidget(QLabel("Marker Color:"))
        color_layout = QHBoxLayout()
        self.marker_color_button = DataPlotStudioButton("Choose", parent=self)
        self.marker_color_label = QLabel("Auto")
        color_layout.addWidget(self.marker_color_button)
        color_layout.addWidget(self.marker_color_label)
        layout.addLayout(color_layout)

        layout.addWidget(QLabel("Marker Edge Color:"))
        edge_layout = QHBoxLayout()
        self.marker_edge_button = DataPlotStudioButton("Choose", parent=self)
        self.marker_edge_label = QLabel("Auto")
        edge_layout.addWidget(self.marker_edge_button)
        edge_layout.addWidget(self.marker_edge_label)
        layout.addLayout(edge_layout)

        layout.addWidget(QLabel("Marker Edge Width:"))
        self.marker_edge_width_spin = DataPlotStudioDoubleSpinBox()
        self.marker_edge_width_spin.setRange(0, 3)
        self.marker_edge_width_spin.setValue(1)
        self.marker_edge_width_spin.setSingleStep(0.1)
        layout.addWidget(self.marker_edge_width_spin)

        self.marker_group.setLayout(layout)
        parent_layout.addWidget(self.marker_group)

    def _setup_error_bars_group(self, parent_layout: QVBoxLayout) -> None:
        self.error_bars_group = DataPlotStudioGroupBox("Error Bars")
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Error Bar Type:"))
        self.error_bars_combo = DataPlotStudioComboBox()
        self.error_bars_combo.addItems(["None", "Standard Deviation", "Standard Error", "Custom"])
        layout.addWidget(self.error_bars_combo)
        
        layout.addWidget(QLabel("Color:"))
        color_layout = QHBoxLayout()
        self.error_bar_color_button = DataPlotStudioButton("Choose", parent=self)
        self.error_bar_color_label = QLabel("Black")
        color_layout.addWidget(self.error_bar_color_button)
        color_layout.addWidget(self.error_bar_color_label)
        layout.addLayout(color_layout)
        
        layout.addWidget(QLabel("Line Width:"))
        self.error_bar_linewidth_spin = DataPlotStudioDoubleSpinBox()
        self.error_bar_linewidth_spin.setRange(0.1, 5.0)
        self.error_bar_linewidth_spin.setValue(1.5)
        self.error_bar_linewidth_spin.setSingleStep(0.1)
        layout.addWidget(self.error_bar_linewidth_spin)

        layout.addWidget(QLabel("Cap Size:"))
        self.error_bar_capsize_spin = DataPlotStudioDoubleSpinBox()
        self.error_bar_capsize_spin.setRange(0.0, 20.0)
        self.error_bar_capsize_spin.setValue(4.0)
        self.error_bar_capsize_spin.setSingleStep(0.5)
        layout.addWidget(self.error_bar_capsize_spin)

        layout.addWidget(QLabel("Transparency:"))
        self.error_bar_alpha_slider = DataPlotStudioSlider(Qt.Orientation.Horizontal)
        self.error_bar_alpha_slider.setRange(10, 100)
        self.error_bar_alpha_slider.setValue(50)
        self.error_bar_alpha_label = QLabel("50%")

        layout.addWidget(self.error_bar_alpha_slider)
        layout.addWidget(self.error_bar_alpha_label)

        layout.addWidget(QLabel("Z-Order:"))
        self.error_bar_zorder_spin = DataPlotStudioSpinBox()
        self.error_bar_zorder_spin.setRange(-10, 100)
        self.error_bar_zorder_spin.setValue(10)
        layout.addWidget(self.error_bar_zorder_spin)
        
        self.error_bars_group.setLayout(layout)
        parent_layout.addWidget(self.error_bars_group)

    def _setup_transparency_group(self, parent_layout: QVBoxLayout) -> None:
        group = DataPlotStudioGroupBox("Transparency")
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Alpha/Transparency:"))
        self.alpha_slider = DataPlotStudioSlider(Qt.Orientation.Horizontal)
        self.alpha_slider.setRange(10, 100)
        self.alpha_slider.setValue(100)
        layout.addWidget(self.alpha_slider)

        self.alpha_label = QLabel("100%")
        layout.addWidget(self.alpha_label)

        group.setLayout(layout)
        parent_layout.addWidget(group)