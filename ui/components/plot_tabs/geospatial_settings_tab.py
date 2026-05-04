from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QTabWidget
from ui.widgets import DataPlotStudioToggleSwitch, DataPlotStudioButton
from ui.widgets.ControlElements import DataPlotStudioComboBox, DataPlotStudioDoubleSpinBox, DataPlotStudioGroupBox, DataPlotStudioLineEdit, DataPlotStudioSpinBox

class GeospatialSettingsTab(QWidget):
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

        self._setup_geospatial_tabs(scroll_layout)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
    def _setup_geospatial_tabs(self, parent_layout: QVBoxLayout) -> None:
        group = DataPlotStudioGroupBox("Geospatial Configuration")
        layout = QVBoxLayout()
        
        tab_widget = QTabWidget()
        tab_widget.setMinimumHeight(350)
        
        # Map projectsion tab
        proj_tab = QWidget()
        proj_layout = QVBoxLayout(proj_tab)
        
        proj_layout.addWidget(QLabel("Target Coordinate System:"))
        self.geo_target_crs_input = DataPlotStudioLineEdit()
        self.geo_target_crs_input.setPlaceholderText("Leave empty to keep original coordinate system")
        self.geo_target_crs_input.setToolTip("Enter an EPSG code (e.g., EPSG:3857 for Web Mercator) to reproject map")
        proj_layout.addWidget(self.geo_target_crs_input)
        
        proj_layout.addSpacing(10)
        
        self.geo_basemap_check = DataPlotStudioToggleSwitch("Add background Basemap")
        self.geo_basemap_check.setToolTip("Overlay data on top of a web map tile.\nRequires an internet connection")
        proj_layout.addWidget(self.geo_basemap_check)
        
        proj_layout.addWidget(QLabel("Basemap Source:"))
        self.geo_basemap_style_combo = DataPlotStudioComboBox()
        self.geo_basemap_style_combo.addItems([
            "OpenStreetMap",
            "CartoDB Positron",
            "CartoDB DarkMatter",
            "Esri Satellite",
            "Esri Street"
        ])
        self.geo_basemap_style_combo.setToolTip("Select the provider for the basemap tile")
        proj_layout.addWidget(self.geo_basemap_style_combo)
        
        proj_layout.addStretch()
        tab_widget.addTab(proj_tab, "Projection and Basemap")
        
        #chloropleth options
        choro_tab = QWidget()
        choro_layout = QVBoxLayout(choro_tab)
        
        choro_layout.addWidget(QLabel("Classification Scheme:"))
        self.geo_scheme_combo = DataPlotStudioComboBox()
        self.geo_scheme_combo.addItems([
            "None", "quantiles", "equal_interval", "fisher_jenks", "natural_breaks", "box_plot", "breaks"
        ])
        choro_layout.addWidget(self.geo_scheme_combo)
        
        choro_layout.addWidget(QLabel("Number of classes:"))
        self.geo_k_spin = DataPlotStudioSpinBox()
        self.geo_k_spin.setRange(2, 20)
        self.geo_k_spin.setValue(5)
        choro_layout.addWidget(self.geo_k_spin)
        
        choro_layout.addSpacing(10)
        choro_layout.addWidget(QLabel("Missing Data Label"))
        self.geo_missing_label_input = DataPlotStudioLineEdit()
        self.geo_missing_label_input.setPlaceholderText("NaN")
        choro_layout.addWidget(self.geo_missing_label_input)
        
        choro_layout.addWidget(QLabel("Missing Data Color:"))
        color_layout = QHBoxLayout()
        self.geo_missing_color_btn = DataPlotStudioButton("Choose Color", parent=self)
        self.geo_missing_color_label = QLabel("Light Gray")
        self.geo_missing_color: str = "lightgray"
        
        color_layout.addWidget(self.geo_missing_color_btn)
        color_layout.addWidget(self.geo_missing_color_label)
        choro_layout.addLayout(color_layout)
        
        choro_layout.addWidget(QLabel("Hatch Pattern:"))
        self.geo_hatch_combo = DataPlotStudioComboBox()
        self.geo_hatch_combo.addItems(["None", "/", "\\", "|", "-", "+", "x", "o", "O", ".", "*"])
        choro_layout.addWidget(self.geo_hatch_combo)
        
        choro_layout.addStretch()
        tab_widget.addTab(choro_tab, "Choropleth Configuration")

        #  Legen Boundary Tab
        style_tab = QWidget()
        style_layout = QVBoxLayout(style_tab)

        self.geo_legend_check = DataPlotStudioToggleSwitch("Show Map Legend")
        style_layout.addWidget(self.geo_legend_check)
        
        self.geo_legend_loc_combo = DataPlotStudioComboBox()
        self.geo_legend_loc_combo.addItems(["vertical", "horizontal"])
        style_layout.addWidget(self.geo_legend_loc_combo)

        self.geo_use_divider_check = DataPlotStudioToggleSwitch("Use Divider")
        self.geo_use_divider_check.setToolTip("Use mpl_toolkits divider to align legend")
        style_layout.addWidget(self.geo_use_divider_check)

        self.geo_cax_check = DataPlotStudioToggleSwitch("Plot on Separate CAX")
        self.geo_cax_check.setToolTip("Plot legend/colorbar on a separate axis")
        style_layout.addWidget(self.geo_cax_check)

        self.geo_axis_off_check = DataPlotStudioToggleSwitch("Turn Off Axis")
        self.geo_axis_off_check.setChecked(False)
        style_layout.addWidget(self.geo_axis_off_check)
        
        style_layout.addSpacing(10)
        self.geo_boundary_check = DataPlotStudioToggleSwitch("Plot Boundary Only")
        style_layout.addWidget(self.geo_boundary_check)

        style_layout.addWidget(QLabel("Edge Color:"))
        bound_color_layout = QHBoxLayout()
        self.geo_edge_color_btn = DataPlotStudioButton("Choose", parent=self)
        self.geo_edge_color_label = QLabel("Black")
        self.geo_edge_color: str = "black"
        
        bound_color_layout.addWidget(self.geo_edge_color_btn)
        bound_color_layout.addWidget(self.geo_edge_color_label)
        style_layout.addLayout(bound_color_layout)

        style_layout.addWidget(QLabel("Line Width:"))
        self.geo_linewidth_spin = DataPlotStudioDoubleSpinBox()
        self.geo_linewidth_spin.setRange(0.1, 10.0)
        self.geo_linewidth_spin.setValue(1.0)
        style_layout.addWidget(self.geo_linewidth_spin)

        style_layout.addStretch()
        tab_widget.addTab(style_tab, "Style and Legend")

        layout.addWidget(tab_widget)
        group.setLayout(layout)
        parent_layout.addWidget(group)