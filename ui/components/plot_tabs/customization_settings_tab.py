from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QDoubleSpinBox, QGroupBox, QHBoxLayout, QLabel, QLayout, QPushButton, \
    QScrollArea, QSlider, QSpinBox, QTabWidget, QVBoxLayout, QWidget

from ui.widgets import ToggleSwitch

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

        spinbox: QSpinBox | QDoubleSpinBox
        for spinbox in self.findChildren(QSpinBox) + self.findChildren(QDoubleSpinBox):
            spinbox.setKeyboardTracking(False)

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

        group = QGroupBox("Line Properties")
        group_layout = QVBoxLayout()

        self.multiline_custom_check = ToggleSwitch("Per-line customization")
        self.multiline_custom_check.setToolTip("Toggle to customize each line object individually")
        self.multiline_custom_check.setChecked(False)
        group_layout.addWidget(self.multiline_custom_check)

        self.line_selector_label = QLabel("Select Line to customize")
        self.line_selector_label.setVisible(False)
        group_layout.addWidget(self.line_selector_label)

        self.line_selector_combo = QComboBox()
        self.line_selector_combo.setToolTip("Select the line to customize")
        self.line_selector_combo.setVisible(False)
        group_layout.addWidget(self.line_selector_combo)

        group_layout.addWidget(QLabel("Line Width:"))
        self.linewidth_spin = QDoubleSpinBox()
        self.linewidth_spin.setToolTip("Set the width / thickness of the line")
        self.linewidth_spin.setRange(0.5, 5.0)
        self.linewidth_spin.setValue(1.5)
        self.linewidth_spin.setSingleStep(0.1)
        group_layout.addWidget(self.linewidth_spin)

        group_layout.addWidget(QLabel("Line Style:"))
        self.linestyle_combo = QComboBox()
        self.linestyle_combo.setToolTip("Select the specific style of the line")
        self.linestyle_combo.addItems(['-', '--', '-.', ':', 'None'])
        self.linestyle_combo.setItemText(0, 'Solid')
        self.linestyle_combo.setItemText(1, 'Dashed')
        self.linestyle_combo.setItemText(2, 'Dash-dot')
        self.linestyle_combo.setItemText(3, 'Dotted')
        group_layout.addWidget(self.linestyle_combo)

        group_layout.addWidget(QLabel("Line Color:"))
        color_layout = QHBoxLayout()
        self.line_color_button = QPushButton("Choose", parent=self)
        self.line_color_button.setToolTip("Open a color menu to select the color of the line")
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

        self.multibar_custom_check = ToggleSwitch("Per-bar customization")
        self.multibar_custom_check.setToolTip("Toggle to enable customizations of individual bar series")
        self.multibar_custom_check.setChecked(False)
        bar_layout.addWidget(self.multibar_custom_check)

        self.bar_selector_label = QLabel("Select Bar Series to Customize")
        self.bar_selector_label.setVisible(False)
        bar_layout.addWidget(self.bar_selector_label)

        self.bar_selector_combo = QComboBox()
        self.bar_selector_combo.setToolTip("Select the bar series to customize")
        self.bar_selector_combo.setVisible(False)
        bar_layout.addWidget(self.bar_selector_combo)

        self.bar_patch_label = QLabel("Select Individual Bar to Customize")
        self.bar_patch_label.setVisible(False)
        self.bar_patch_label.setToolTip("Select a specific bar within the series to customize individually")
        bar_layout.addWidget(self.bar_patch_label)

        self.bar_patch_combo = QComboBox()
        self.bar_patch_combo.setVisible(False)
        self.bar_patch_combo.setToolTip("Select the specific bar/patch within the series to customize")
        bar_layout.addWidget(self.bar_patch_combo)

        bar_layout.addWidget(QLabel("Bar Width:"))
        self.bar_width_spin = QDoubleSpinBox()
        self.bar_width_spin.setToolTip(
            "Set the width the bars.\nThis will also determine how close the bars are to each other")
        self.bar_width_spin.setRange(0.1, 1.0)
        self.bar_width_spin.setValue(0.8)
        self.bar_width_spin.setSingleStep(0.05)
        bar_layout.addWidget(self.bar_width_spin)

        bar_layout.addWidget(QLabel("Bar Color:"))
        color_layout = QHBoxLayout()
        self.bar_color_button = QPushButton("Choose Color", parent=self)
        self.bar_color_button.setToolTip("Open a color menu to select the color for the bar itself")
        self.bar_color_label = QLabel("Auto")
        color_layout.addWidget(self.bar_color_button)
        color_layout.addWidget(self.bar_color_label)
        bar_layout.addLayout(color_layout)

        bar_layout.addWidget(QLabel("Bar Edge Color:"))
        edge_color_layout = QHBoxLayout()
        self.bar_edge_button = QPushButton("Choose", parent=self)
        self.bar_edge_button.setToolTip("Open a color menu to select the color of the bar outline")
        self.bar_edge_label = QLabel("Auto")
        edge_color_layout.addWidget(self.bar_edge_button)
        edge_color_layout.addWidget(self.bar_edge_label)
        bar_layout.addLayout(edge_color_layout)

        bar_layout.addWidget(QLabel("Bar Edge Width:"))
        self.bar_edge_width_spin = QDoubleSpinBox()
        self.bar_edge_width_spin.setToolTip("Set the width / thickness of the bar outline")
        self.bar_edge_width_spin.setRange(0, 3)
        self.bar_edge_width_spin.setValue(1)
        self.bar_edge_width_spin.setSingleStep(0.1)
        bar_layout.addWidget(self.bar_edge_width_spin)

        bar_layout.addStretch()
        tab_widget.addTab(bar_tab, "Bar Properties")

        hist_tab = QWidget()
        hist_layout = QVBoxLayout(hist_tab)

        hist_layout.addWidget(QLabel("Number of Bins:"))
        self.histogram_bins_spin = QSpinBox()
        self.histogram_bins_spin.setToolTip(
            "Set the number of bins.\n\nBins are the equal of unequal intervals into which a total range of continuous data is divided")
        self.histogram_bins_spin.setRange(5, 200)
        self.histogram_bins_spin.setValue(30)
        hist_layout.addWidget(self.histogram_bins_spin)

        self.histogram_show_normal_check = ToggleSwitch("Overlay a Normal Distribution Curve")
        self.histogram_show_normal_check.setToolTip(
            "Display a fitted normal distribution curve to compare your histogram against a theoretical bell shape")
        self.histogram_show_normal_check.setChecked(False)
        hist_layout.addWidget(self.histogram_show_normal_check)

        self.histogram_show_kde_check = ToggleSwitch("Overlay Kernel Density Estimate")
        self.histogram_show_kde_check.setToolTip(
            "Display a kernel density estimate to see a smoothed, continuous approximation of the data distribution")
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

        self.scatter_group = QGroupBox("Scatter Plot Analysis")
        scatter_layout = QVBoxLayout()

        self.regression_line_check = ToggleSwitch("Show Regresssion Line")
        self.regression_line_check.setToolTip(
            "Toggle to display a fitted least-squares regression line to visualize the trend")
        scatter_layout.addWidget(self.regression_line_check)

        self.regression_settings_container = QWidget()
        regression_settings_layout = QVBoxLayout(self.regression_settings_container)
        regression_settings_layout.setContentsMargins(0, 0, 0, 0)

        regression_settings_layout.addWidget(QLabel("Regression Type:"))
        self.regression_type_combo = QComboBox()
        self.regression_type_combo.setToolTip(
            "Select the type of regression analysis to calculate and visualize the regression line")
        self.regression_type_combo.addItems(["Linear", "Polynomial", "Exponential", "Logarithmic"])
        regression_settings_layout.addWidget(self.regression_type_combo)

        self.poly_degree_label = QLabel("Polynomial Degree:")
        regression_settings_layout.addWidget(self.poly_degree_label)
        self.poly_degree_spin = QSpinBox()
        self.poly_degree_spin.setToolTip("Set the degree of the polynomial used in the regression fit.")
        self.poly_degree_spin.setRange(2, 10)
        self.poly_degree_spin.setValue(2)
        regression_settings_layout.addWidget(self.poly_degree_spin)

        # Internal callback to toggle visibility of polynomial degree components cleanly
        def toggle_poly_degree() -> None:
            is_poly = self.regression_type_combo.currentText() == "Polynomial"
            self.poly_degree_label.setVisible(is_poly)
            self.poly_degree_spin.setVisible(is_poly)

        self.regression_type_combo.currentTextChanged.connect(toggle_poly_degree)
        toggle_poly_degree()

        self.confidence_interval_check = ToggleSwitch("Show 95% confidence interval")
        self.confidence_interval_check.setToolTip(
            "Toggle to display the 95% confidence interval band around the regression line to indicate the uncertainty of the estimated fit.")
        regression_settings_layout.addWidget(self.confidence_interval_check)

        self.confidence_level_container = QWidget()
        confidence_layout = QHBoxLayout(self.confidence_level_container)
        confidence_layout.setContentsMargins(0, 0, 0, 0)
        confidence_layout.addWidget(QLabel("Confidence Level (%):"))
        self.confidence_level_spin = QSpinBox()
        self.confidence_level_spin.setToolTip("Select the degree of confidence to display around the regression line")
        self.confidence_level_spin.setRange(80, 99)
        self.confidence_level_spin.setValue(95)
        self.confidence_level_spin.setSuffix(" %")
        confidence_layout.addWidget(self.confidence_level_spin)
        regression_settings_layout.addWidget(self.confidence_level_container)

        def toggle_confidence_level_combobox() -> None:
            self.confidence_level_container.setVisible(self.confidence_interval_check.isChecked())

        self.confidence_interval_check.stateChanged.connect(toggle_confidence_level_combobox)
        toggle_confidence_level_combobox()

        self.show_r2_check = ToggleSwitch("Show R² score")
        self.show_r2_check.setToolTip(
            "Toggle to display the coefficient of determination (R²) to quantify how well the regression model explains the variance in the data")
        self.show_r2_check.setChecked(False)
        regression_settings_layout.addWidget(self.show_r2_check)

        self.show_rmse_check = ToggleSwitch("Show Root Mean Square Error (RMSE)")
        self.show_rmse_check.setToolTip(
            "Toggle to display the RMSE value to quantify the average magnitude of the model's prediction errors")
        regression_settings_layout.addWidget(self.show_rmse_check)

        self.show_equation_check = ToggleSwitch("Show Regression Equation")
        self.show_equation_check.setToolTip(
            "Toggle to display the fitted regression equation to see the mathematical form the model used to describe the data.")
        regression_settings_layout.addWidget(self.show_equation_check)

        scatter_layout.addWidget(self.regression_settings_container)

        def toggle_regression_settings() -> None:
            self.regression_settings_container.setVisible(self.regression_line_check.isChecked())

        self.regression_line_check.stateChanged.connect(toggle_regression_settings)
        toggle_regression_settings()

        self.scatter_group.setLayout(scatter_layout)
        layout.addWidget(self.scatter_group)
        layout.addStretch()

        self.advanced_stack_layout.addWidget(self.page_scatter)

    def _setup_pie_page(self) -> None:
        self.page_pie = QWidget()
        layout = QVBoxLayout(self.page_pie)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)

        self.pie_group = QGroupBox("Pie Chart Properties")
        pie_layout = QVBoxLayout()

        self.pie_show_percentages_check = ToggleSwitch("Show % on slices")
        self.pie_show_percentages_check.setToolTip(
            "Toggle to display the percentage each slice amounts to of the total pie")
        self.pie_show_percentages_check.setChecked(False)
        pie_layout.addWidget(self.pie_show_percentages_check)

        pie_layout.addWidget(QLabel("Start Angle (degrees):"))
        self.pie_start_angle_spin = QSpinBox()
        self.pie_start_angle_spin.setToolTip(
            "Change the initial angle of the pie chart.\nThis will rotate the pie around its own axis")
        self.pie_start_angle_spin.setRange(0, 360)
        self.pie_start_angle_spin.setValue(0)
        pie_layout.addWidget(self.pie_start_angle_spin)

        self.pie_explode_check = ToggleSwitch("Explode First Slice")
        self.pie_explode_check.setToolTip("Toggle to make the first row be detached from the rest of the pie")
        self.pie_explode_check.setChecked(False)
        pie_layout.addWidget(self.pie_explode_check)

        pie_layout.addWidget(QLabel("Explode Distance:"))
        self.pie_explode_distance_spin = QDoubleSpinBox()
        self.pie_explode_distance_spin.setToolTip(
            "Change how far the first row should be detached from the rest of the pie")
        self.pie_explode_distance_spin.setRange(0.0, 0.5)
        self.pie_explode_distance_spin.setValue(0.1)
        self.pie_explode_distance_spin.setSingleStep(0.05)
        pie_layout.addWidget(self.pie_explode_distance_spin)

        self.pie_shadow_check = ToggleSwitch("Add Shadow")
        self.pie_shadow_check.setToolTip("Toggle to display a drop-shadow on the pie chart")
        self.pie_shadow_check.setChecked(False)
        pie_layout.addWidget(self.pie_shadow_check)

        self.pie_donut_check = ToggleSwitch("Donut Chart")
        self.pie_donut_check.setToolTip("Toggle to transform the pie chart into a donut chart")
        self.pie_donut_check.setChecked(False)
        pie_layout.addWidget(self.pie_donut_check)

        self.pie_donut_container = QWidget()
        donut_layout = QHBoxLayout(self.pie_donut_container)
        donut_layout.setContentsMargins(0, 0, 0, 0)

        self.pie_donut_width_label = QLabel("Donut Ring Width:")
        donut_layout.addWidget(self.pie_donut_width_label)

        self.pie_donut_width_spin = QDoubleSpinBox()
        self.pie_donut_width_spin.setToolTip(
            "Set the width donut ring.\nHigher number more closely resembles a pie chart. Lower number has a thinner ring")
        self.pie_donut_width_spin.setRange(0.1, 0.9)
        self.pie_donut_width_spin.setValue(0.3)
        self.pie_donut_width_spin.setSingleStep(0.05)
        donut_layout.addWidget(self.pie_donut_width_spin)

        pie_layout.addWidget(self.pie_donut_container)

        def toggle_donut_width() -> None:
            self.pie_donut_container.setVisible(self.pie_donut_check.isChecked())

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
        self.marker_group = QGroupBox("Marker Properties")
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Marker Shape:"))
        self.marker_combo = QComboBox()
        self.marker_combo.setToolTip("Select the shape of the markers")
        self.marker_combo.addItems(['None', 'o', 's', '^', 'v', 'D', '*', '+', 'x', '|', '_', 'p', 'H', 'h'])
        layout.addWidget(self.marker_combo)

        layout.addWidget(QLabel("Marker Size:"))
        self.marker_size_spin = QSpinBox()
        self.marker_size_spin.setToolTip("Set the size of the marker")
        self.marker_size_spin.setRange(2, 20)
        self.marker_size_spin.setValue(6)
        layout.addWidget(self.marker_size_spin)

        layout.addWidget(QLabel("Marker Color:"))
        color_layout = QHBoxLayout()
        self.marker_color_button = QPushButton("Choose", parent=self)
        self.marker_color_button.setToolTip("Open a color menu to select the color of the marker")
        self.marker_color_label = QLabel("Auto")
        color_layout.addWidget(self.marker_color_button)
        color_layout.addWidget(self.marker_color_label)
        layout.addLayout(color_layout)

        layout.addWidget(QLabel("Marker Edge Color:"))
        edge_layout = QHBoxLayout()
        self.marker_edge_button = QPushButton("Choose", parent=self)
        self.marker_edge_button.setToolTip("Open a color menu to select the color of the marker outline")
        self.marker_edge_label = QLabel("Auto")
        edge_layout.addWidget(self.marker_edge_button)
        edge_layout.addWidget(self.marker_edge_label)
        layout.addLayout(edge_layout)

        layout.addWidget(QLabel("Marker Edge Width:"))
        self.marker_edge_width_spin = QDoubleSpinBox()
        self.marker_edge_width_spin.setToolTip("Set the thickness of the marker's outline")
        self.marker_edge_width_spin.setRange(0, 3)
        self.marker_edge_width_spin.setValue(1)
        self.marker_edge_width_spin.setSingleStep(0.1)
        layout.addWidget(self.marker_edge_width_spin)

        self.marker_group.setLayout(layout)
        parent_layout.addWidget(self.marker_group)

    def _setup_error_bars_group(self, parent_layout: QVBoxLayout) -> None:
        self.error_bars_group = QGroupBox("Error Bars")
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Error Bar Type:"))
        self.error_bars_combo = QComboBox()
        self.error_bars_combo.setToolTip("Select which type error bar to be displayed for each point in the data")
        self.error_bars_combo.addItems(["None", "Standard Deviation", "Standard Error"])
        layout.addWidget(self.error_bars_combo)

        layout.addWidget(QLabel("Color:"))
        color_layout = QHBoxLayout()
        self.error_bar_color_button = QPushButton("Choose", parent=self)
        self.error_bar_color_button.setToolTip("Open a color menu to select the color of the error bar")
        self.error_bar_color_label = QLabel("Black")
        color_layout.addWidget(self.error_bar_color_button)
        color_layout.addWidget(self.error_bar_color_label)
        layout.addLayout(color_layout)

        layout.addWidget(QLabel("Line Width:"))
        self.error_bar_linewidth_spin = QDoubleSpinBox()
        self.error_bar_linewidth_spin.setToolTip("Set the thickness of the line inbetween the caps")
        self.error_bar_linewidth_spin.setRange(0.1, 5.0)
        self.error_bar_linewidth_spin.setValue(1.5)
        self.error_bar_linewidth_spin.setSingleStep(0.1)
        layout.addWidget(self.error_bar_linewidth_spin)

        layout.addWidget(QLabel("Cap Size:"))
        self.error_bar_capsize_spin = QDoubleSpinBox()
        self.error_bar_capsize_spin.setToolTip("Set the length of the caps at the top of the error bar")
        self.error_bar_capsize_spin.setRange(0.0, 20.0)
        self.error_bar_capsize_spin.setValue(4.0)
        self.error_bar_capsize_spin.setSingleStep(0.5)
        layout.addWidget(self.error_bar_capsize_spin)

        layout.addWidget(QLabel("Transparency:"))
        self.error_bar_alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self.error_bar_alpha_slider.setToolTip("Set the transparency of the error bars")
        self.error_bar_alpha_slider.setRange(10, 100)
        self.error_bar_alpha_slider.setValue(50)
        self.error_bar_alpha_label = QLabel("50%")

        layout.addWidget(self.error_bar_alpha_slider)
        layout.addWidget(self.error_bar_alpha_label)

        layout.addWidget(QLabel("Z-Order:"))
        self.error_bar_zorder_spin = QSpinBox()
        self.error_bar_zorder_spin.setToolTip(
            "Set the drawing order of error bars relative to other elements. Higher values place error bars on top; lower values push them behind")
        self.error_bar_zorder_spin.setRange(-10, 100)
        self.error_bar_zorder_spin.setValue(10)
        layout.addWidget(self.error_bar_zorder_spin)

        self.error_bars_group.setLayout(layout)
        parent_layout.addWidget(self.error_bars_group)

    def _setup_transparency_group(self, parent_layout: QVBoxLayout) -> None:
        group = QGroupBox("Transparency")
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Alpha/Transparency:"))
        self.alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self.alpha_slider.setToolTip(
            "Set the transparency of the data drawn on the canvas.\nThis does not affect external customizations")
        self.alpha_slider.setRange(10, 100)
        self.alpha_slider.setValue(100)
        layout.addWidget(self.alpha_slider)

        self.alpha_label = QLabel("100%")
        layout.addWidget(self.alpha_label)

        group.setLayout(layout)
        parent_layout.addWidget(group)
