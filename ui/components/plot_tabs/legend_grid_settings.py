from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QDoubleSpinBox, QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, \
    QScrollArea, QSizePolicy, QSlider, QSpinBox, QTabWidget, QVBoxLayout, QWidget

from ui.widgets import ToggleSwitch

class LegendGridSettingstab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_widget = QWidget()
        scroll_widget.setObjectName("ScrollContent")
        scroll_layout = QVBoxLayout(scroll_widget)

        self._setup_legend_config_group(scroll_layout)
        scroll_layout.addSpacing(10)
        self._setup_gridlines_group(scroll_layout)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
    
    def _setup_legend_config_group(self, parent_layout: QVBoxLayout) -> None:
        group = QGroupBox("Legend")
        layout = QVBoxLayout()
        
        self.legend_check = ToggleSwitch("Show Legend")
        self.legend_check.setToolTip("Toggle the visibility of the legend")
        self.legend_check.setChecked(False)
        layout.addWidget(self.legend_check)
        
        self.legend_tab_widget = QTabWidget()
        self.legend_tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.legend_tab_widget.setVisible(False)
        
        self.legend_check.toggled.connect(self.legend_tab_widget.setVisible)
        
        layout_tab = QWidget()
        layout_tab_layout = QVBoxLayout(layout_tab)
        
        layout_tab_layout.addWidget(QLabel("Legend Placement:"))
        self.legend_loc_combo = QComboBox()
        self.legend_loc_combo.setToolTip(
            "Determine the placement of the legend on the canvas.\n'Best' calculates the most optimal position based on what is drawn")
        self.legend_loc_combo.addItems(['best', 'upper right', 'upper left', 'lower left', 'lower right', 
            'right', 'center left', 'center right', 'lower center', 'upper center', 'center'])
        layout_tab_layout.addWidget(self.legend_loc_combo)
        
        legend_title_row_layout = QHBoxLayout()
        
        title_col_layout = QVBoxLayout()
        title_col_layout.addWidget(QLabel("Legend Title:"))
        self.legend_title_input = QLineEdit()
        self.legend_title_input.setToolTip("Enter the text for the legend title")
        self.legend_title_input.setPlaceholderText("Enter legend title")
        title_col_layout.addWidget(self.legend_title_input)
        
        size_col_layout = QVBoxLayout()
        size_col_layout.addWidget(QLabel("Title Font Size:"))
        self.legend_title_size_spin = QSpinBox()
        self.legend_title_size_spin.setToolTip("Change the font size of the legend title")
        self.legend_title_size_spin.setRange(5, 50)
        self.legend_title_size_spin.setValue(12)
        size_col_layout.addWidget(self.legend_title_size_spin)
        
        legend_title_row_layout.addLayout(title_col_layout)
        legend_title_row_layout.addLayout(size_col_layout)
        
        layout_tab_layout.addLayout(legend_title_row_layout)
        
        custom_label_row_layout = QHBoxLayout()
        
        labels_input_layout = QVBoxLayout()
        labels_input_layout.addWidget(QLabel("Custom Labels:"))
        self.legend_labels_input = QLineEdit()
        self.legend_labels_input.setToolTip(
            "Add custom labels to the legend objects.\nUse semicolons to separate labels.")
        self.legend_labels_input.setPlaceholderText("E.g. Group A; Group B; Group C")
        labels_input_layout.addWidget(self.legend_labels_input)
        
        label_size_layout = QVBoxLayout()
        label_size_layout.addWidget(QLabel("Labels Font Size:"))
        self.legend_size_spin = QSpinBox()
        self.legend_size_spin.setToolTip("Change the font size of the legend labels")
        self.legend_size_spin.setRange(5, 50)
        self.legend_size_spin.setValue(10)
        label_size_layout.addWidget(self.legend_size_spin)
        
        custom_label_row_layout.addLayout(labels_input_layout)
        custom_label_row_layout.addLayout(label_size_layout)
        
        layout_tab_layout.addLayout(custom_label_row_layout)
        
        layout_tab_layout.addWidget(QLabel("Number of Columns:"))
        self.legend_columns_spin = QSpinBox()
        self.legend_columns_spin.setToolTip("Determine the amount of columns to use to order the legend entries")
        self.legend_columns_spin.setRange(1, 5)
        self.legend_columns_spin.setValue(1)
        layout_tab_layout.addWidget(self.legend_columns_spin)
        
        layout_tab_layout.addWidget(QLabel("Column Spacing"))
        self.legend_colspace_spin = QDoubleSpinBox()
        self.legend_colspace_spin.setToolTip("Set the amount of space inbetween the columns of legend entries")
        self.legend_colspace_spin.setRange(0.5, 5.0)
        self.legend_colspace_spin.setValue(1.0)
        self.legend_colspace_spin.setSingleStep(0.1)
        layout_tab_layout.addWidget(self.legend_colspace_spin)
        
        layout_tab_layout.addStretch()
        self.legend_tab_widget.addTab(layout_tab, "Layout and Text")
        
        # Box styling options
        box_tab = QWidget()
        box_layout = QVBoxLayout(box_tab)
        
        self.legend_frame_check = ToggleSwitch("Show Frame")
        self.legend_frame_check.setToolTip("Toggle the visibility of the outer frame of the legend box")
        self.legend_frame_check.setChecked(True)
        box_layout.addWidget(self.legend_frame_check)
        
        self.legend_fancybox_check = ToggleSwitch("Fancy Box")
        self.legend_fancybox_check.setToolTip("Toggle to set the corners of the legend to be rounded")
        self.legend_fancybox_check.setChecked(False)
        box_layout.addWidget(self.legend_fancybox_check)
        
        self.legend_shadow_check = ToggleSwitch("Show Shadow")
        self.legend_shadow_check.setToolTip("Toggle the visibility of a drop shadow of the legend frame.")
        self.legend_shadow_check.setChecked(False)
        box_layout.addWidget(self.legend_shadow_check)

        initial_frame_state = self.legend_frame_check.isChecked()
        self.legend_fancybox_check.setEnabled(initial_frame_state)
        self.legend_shadow_check.setEnabled(initial_frame_state)

        self.legend_frame_check.toggled.connect(self.legend_fancybox_check.setEnabled)
        self.legend_frame_check.toggled.connect(self.legend_shadow_check.setEnabled)

        box_layout.addWidget(QLabel("Background Color:"))
        bg_layout = QHBoxLayout()
        self.legend_bg_button = QPushButton("Choose Color", parent=self)
        self.legend_bg_button.setToolTip("Select the color of the background of the legend box")
        self.legend_bg_label = QLabel("White")
        bg_layout.addWidget(self.legend_bg_button)
        bg_layout.addWidget(self.legend_bg_label)
        box_layout.addLayout(bg_layout)

        box_layout.addWidget(QLabel("Frame Color:"))
        edge_layout = QHBoxLayout()
        self.legend_edge_button = QPushButton("Choose Color", parent=self)
        self.legend_edge_button.setToolTip("Select the color of the legend frame")
        self.legend_edge_label = QLabel("Black")
        edge_layout.addWidget(self.legend_edge_button)
        edge_layout.addWidget(self.legend_edge_label)
        box_layout.addLayout(edge_layout)

        box_layout.addWidget(QLabel("Frame Width:"))
        self.legend_edge_width_spin = QDoubleSpinBox()
        self.legend_edge_width_spin.setToolTip("Set the thickness of the legend frame")
        self.legend_edge_width_spin.setRange(0.5, 3.0)
        self.legend_edge_width_spin.setValue(1.0)
        self.legend_edge_width_spin.setSingleStep(0.1)
        box_layout.addWidget(self.legend_edge_width_spin)
        
        box_layout.addWidget(QLabel("Box Alpha:"))
        self.legend_alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self.legend_alpha_slider.setToolTip(
            "Set the transparency of the entire legend box.\nN.B. Does not affect the legend entries")
        self.legend_alpha_slider.setRange(10, 100)
        self.legend_alpha_slider.setValue(100)
        box_layout.addWidget(self.legend_alpha_slider)
        
        self.legend_alpha_label = QLabel("100%")
        box_layout.addWidget(self.legend_alpha_label)
        
        box_layout.addStretch()
        self.legend_tab_widget.addTab(box_tab, "Legend Style")
        
        layout.addWidget(self.legend_tab_widget)
        group.setLayout(layout)
        parent_layout.addWidget(group)


    def _setup_gridlines_group(self, parent_layout: QVBoxLayout) -> None:
        group = QGroupBox("Gridlines")
        layout = QVBoxLayout()

        self.grid_check = ToggleSwitch("Show Gridlines")
        self.grid_check.setToolTip("Toggle the visibility of gridlines on the plot")
        layout.addWidget(self.grid_check)
        layout.addSpacing(10)

        self.grid_settings_container = QWidget()
        grid_settings_layout = QVBoxLayout(self.grid_settings_container)
        grid_settings_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_settings_container.setVisible(False)
        self.grid_check.toggled.connect(self.grid_settings_container.setVisible)

        # Global grid
        self.global_grid_group = QGroupBox("Global Gridline Settings")
        global_layout = QVBoxLayout()

        global_layout.addWidget(QLabel("Type:"))
        self.grid_which_type_combo = QComboBox()
        self.grid_which_type_combo.addItems(["major", "minor", "both"])
        self.grid_which_type_combo.setToolTip("major = Primary gridlines\nminor = Secondary gridlines\nboth = All gridlines")
        self.grid_which_type_combo.setEnabled(False)
        global_layout.addWidget(self.grid_which_type_combo)

        global_layout.addWidget(QLabel("Axis:"))
        self.grid_axis_combo = QComboBox()
        self.grid_axis_combo.addItems(["both", "x", "y"])
        self.grid_axis_combo.setToolTip("Choose which axis to show gridlines")
        global_layout.addWidget(self.grid_axis_combo)

        global_layout.addWidget(QLabel("Linestyle:"))
        self.global_grid_style_combo = QComboBox()
        self.global_grid_style_combo.setToolTip("Change the line style for all gridlines")
        self.global_grid_style_combo.addItems(["Solid (-)", "Dashed (--)", "Dash-dot (-.)", "Dotted (:)"])
        self.global_grid_style_combo.setCurrentIndex(0)
        global_layout.addWidget(self.global_grid_style_combo)

        global_layout.addWidget(QLabel("Linewidth"))
        self.global_grid_linewidth_spin = QDoubleSpinBox()
        self.global_grid_linewidth_spin.setToolTip("Set the width of all gridlines")
        self.global_grid_linewidth_spin.setRange(0.1, 5.0)
        self.global_grid_linewidth_spin.setValue(0.8)
        self.global_grid_linewidth_spin.setSingleStep(0.1)
        global_layout.addWidget(self.global_grid_linewidth_spin)
        
        global_layout.addWidget(QLabel("Grid Color:"))
        global_color_layout = QHBoxLayout()
        self.global_grid_color_button = QPushButton("Choose Color", parent=self)
        self.global_grid_color_button.setToolTip("Select the color of the gridlines")
        self.global_grid_color_label = QLabel("Auto")
        global_color_layout.addWidget(self.global_grid_color_button)
        global_color_layout.addWidget(self.global_grid_color_label)
        global_layout.addLayout(global_color_layout)

        global_layout.addWidget(QLabel("Grid Alpha:"))
        self.global_grid_alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self.global_grid_alpha_slider.setToolTip("Set the transparency of all the gridlines")
        self.global_grid_alpha_slider.setRange(10, 100)
        self.global_grid_alpha_slider.setValue(100)
        global_layout.addWidget(self.global_grid_alpha_slider)
        self.global_grid_alpha_label = QLabel("100%")
        global_layout.addWidget(self.global_grid_alpha_label)

        self.global_grid_group.setLayout(global_layout)
        layout.addWidget(self.global_grid_group)

        # Independent grids
        self.independent_grid_check = ToggleSwitch("Individual Gridline Customization")
        self.independent_grid_check.setToolTip("Toggle to customize each gridline type individually")
        self.independent_grid_check.setChecked(False)
        layout.addWidget(self.independent_grid_check)

        self.grid_axis_tab = QTabWidget()
        self.grid_axis_tab.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.grid_axis_tab.setVisible(False)
        
        self.independent_grid_check.toggled.connect(self.grid_axis_tab.setVisible)
        self.independent_grid_check.toggled.connect(
            lambda checked: self.global_grid_group.setVisible(not checked)
        )

        # X-Axis Tab
        x_grid_tab = QWidget()
        x_grid_layout = QVBoxLayout(x_grid_tab)
        
        self.x_major_grid_check, self.x_major_grid_style_combo, self.x_major_grid_linewidth_spin, \
        self.x_major_grid_color_button, self.x_major_grid_color_label, self.x_major_grid_alpha_slider, \
        self.x_major_grid_alpha_label = self._create_grid_config_ui(
            "X-axis Major Gridlines", True, 0, 0.8, "Gray", 75, x_grid_layout
        )

        self.x_minor_grid_check, self.x_minor_grid_style_combo, self.x_minor_grid_linewidth_spin, \
        self.x_minor_grid_color_button, self.x_minor_grid_color_label, self.x_minor_grid_alpha_slider, \
        self.x_minor_grid_alpha_label = self._create_grid_config_ui(
            "X-axis Minor Gridlines", False, 3, 0.5, "Light Gray", 30, x_grid_layout
        )
        x_grid_layout.addStretch()
        self.grid_axis_tab.addTab(x_grid_tab, "X-Axis Gridlines")

        # Y-Axis Tab
        y_grid_tab = QWidget()
        y_grid_layout = QVBoxLayout(y_grid_tab)
        
        self.y_major_grid_check, self.y_major_grid_style_combo, self.y_major_grid_linewidth_spin, \
        self.y_major_grid_color_button, self.y_major_grid_color_label, self.y_major_grid_alpha_slider, \
        self.y_major_grid_alpha_label = self._create_grid_config_ui(
            "Y-Axis Major Gridlines", True, 0, 0.8, "Gray", 75, y_grid_layout
        )

        self.y_minor_grid_check, self.y_minor_grid_style_combo, self.y_minor_grid_linewidth_spin, \
        self.y_minor_grid_color_button, self.y_minor_grid_color_label, self.y_minor_grid_alpha_slider, \
        self.y_minor_grid_alpha_label = self._create_grid_config_ui(
            "Y-Axis Minor Gridlines", False, 3, 0.5, "Light Gray", 30, y_grid_layout
        )
        y_grid_layout.addStretch()
        self.grid_axis_tab.addTab(y_grid_tab, "Y-Axis Gridlines")

        grid_settings_layout.addWidget(self.grid_axis_tab)
        grid_settings_layout.addStretch()

        layout.addWidget(self.grid_settings_container)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _create_grid_config_ui(
        self, title: str, default_check: bool, default_style_idx: int, 
        default_width: float, default_color: str, default_alpha: int, parent_layout: QVBoxLayout
    ) -> tuple:
        group = QGroupBox(title)
        layout = QVBoxLayout()

        check = ToggleSwitch(f"Show {title.lower().replace('-axis', '').replace(' gridlines', '')} gridlines")
        check.setChecked(default_check)
        layout.addWidget(check)

        layout.addWidget(QLabel("Linestyle:"))
        style_combo = QComboBox()
        style_combo.setToolTip("Change the line style for the gridline")
        style_combo.addItems(["-", "--", "-.", ":"])
        style_combo.setItemText(0, "Solid (-)")
        style_combo.setItemText(1, "Dashed (--)")
        style_combo.setItemText(2, "Dash-dot (-.)")
        style_combo.setItemText(3, "Dotted (:)")
        style_combo.setCurrentIndex(default_style_idx)
        layout.addWidget(style_combo)

        layout.addWidget(QLabel("Linewidth:"))
        width_spin = QDoubleSpinBox()
        width_spin.setToolTip("Set the width of the gridline")
        width_spin.setRange(0.1, 5.0)
        width_spin.setValue(default_width)
        width_spin.setSingleStep(0.1)
        layout.addWidget(width_spin)

        layout.addWidget(QLabel("Color:"))
        color_layout = QHBoxLayout()
        color_btn = QPushButton("Choose Color", parent=self)
        color_btn.setToolTip("Set the color of the gridlines")
        color_label = QLabel(default_color)
        color_layout.addWidget(color_btn)
        color_layout.addWidget(color_label)
        layout.addLayout(color_layout)

        layout.addWidget(QLabel("Alpha:"))
        alpha_slider = QSlider(Qt.Orientation.Horizontal)
        alpha_slider.setToolTip("Set the transparency of the gridline")
        alpha_slider.setRange(10, 100)
        alpha_slider.setValue(default_alpha)
        layout.addWidget(alpha_slider)
        alpha_label = QLabel(f"{default_alpha}%")
        layout.addWidget(alpha_label)

        group.setLayout(layout)
        parent_layout.addWidget(group)

        return check, style_combo, width_spin, color_btn, color_label, alpha_slider, alpha_label