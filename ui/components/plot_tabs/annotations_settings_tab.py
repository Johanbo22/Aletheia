from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QTabWidget

from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioToggleSwitch, DataPlotStudioButton
from ui.widgets.ControlElements import DataPlotStudioComboBox, DataPlotStudioDoubleSpinBox, DataPlotStudioGroupBox, DataPlotStudioLineEdit, DataPlotStudioListWidget
from ui.widgets.ControlElements import DataPlotStudioSpinBox

class AnnotationsSettingsTab(QWidget):
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

        self._setup_annotation_tools_group(scroll_layout)
        scroll_layout.addSpacing(15)
        self._setup_datatable_group(scroll_layout)
        scroll_layout.addSpacing(15)
        self._setup_annotations_list_group(scroll_layout)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

    def _setup_annotation_tools_group(self, parent_layout: QVBoxLayout) -> None:
        group = DataPlotStudioGroupBox("Annotation Tools")
        layout = QVBoxLayout()
        
        tab_widget = QTabWidget()
        tab_widget.setMinimumHeight(350)
        
        # Auto Annotations Tab
        auto_tab = QWidget()
        auto_layout = QVBoxLayout(auto_tab)

        self.auto_annotate_check = DataPlotStudioToggleSwitch("Annotate All points")
        self.auto_annotate_check.setToolTip("Automatically set text labels to all data points")
        auto_layout.addWidget(self.auto_annotate_check)

        auto_layout.addWidget(QLabel("Label Source Column:"))
        self.auto_annotate_col_combo = DataPlotStudioComboBox()
        self.auto_annotate_col_combo.setMinimumHeight(20)
        self.auto_annotate_col_combo.setToolTip("Select the column to use for the point labels")
        self.auto_annotate_col_combo.addItem("Default (Y-value)")
        self.auto_annotate_col_combo.setEnabled(False)
        auto_layout.addWidget(self.auto_annotate_col_combo)
        
        # Font styling settigs
        font_layout = QHBoxLayout()
        
        size_layout = QVBoxLayout()
        size_layout.addWidget(QLabel("Font-size:"))
        self.auto_annotate_fontsize_spin = DataPlotStudioSpinBox()
        self.auto_annotate_fontsize_spin.setRange(6, 36)
        self.auto_annotate_fontsize_spin.setValue(10)
        self.auto_annotate_fontsize_spin.setEnabled(False)
        size_layout.addWidget(self.auto_annotate_fontsize_spin)
        
        weight_layout = QVBoxLayout()
        weight_layout.addWidget(QLabel("Font Weight:"))
        self.auto_annotate_weight_combo = DataPlotStudioComboBox()
        self.auto_annotate_weight_combo.addItems(["normal", "bold", "heavy", "light"])
        self.auto_annotate_weight_combo.setEnabled(False)
        weight_layout.addWidget(self.auto_annotate_weight_combo)
        
        font_layout.addLayout(size_layout)
        font_layout.addLayout(weight_layout)
        auto_layout.addLayout(font_layout)
        
        # Color options
        auto_layout.addWidget(QLabel("Font Color:"))
        color_layout = QHBoxLayout()
        self.auto_annotate_color_button = DataPlotStudioButton("Choose", parent=self)
        self.auto_annotate_color_button.setEnabled(False)
        self.auto_annotate_color_label = QLabel("Black")
        color_layout.addWidget(self.auto_annotate_color_button)
        color_layout.addWidget(self.auto_annotate_color_label)
        auto_layout.addLayout(color_layout)
        
        # Position
        offset_layout = QHBoxLayout()
        
        x_offset_layout = QVBoxLayout()
        x_offset_layout.addWidget(QLabel("X Offset"))
        self.auto_annotate_x_offset_spin = DataPlotStudioDoubleSpinBox()
        self.auto_annotate_x_offset_spin.setRange(-200.0, 200.0)
        self.auto_annotate_x_offset_spin.setValue(0.0)
        self.auto_annotate_x_offset_spin.setEnabled(False)
        x_offset_layout.addWidget(self.auto_annotate_x_offset_spin)
        
        y_offset_layout = QVBoxLayout()
        y_offset_layout.addWidget(QLabel("Y Offset:"))
        self.auto_annotate_y_offset_spin = DataPlotStudioDoubleSpinBox()
        self.auto_annotate_y_offset_spin.setRange(-200.0, 200.0)
        self.auto_annotate_y_offset_spin.setValue(5.0)
        self.auto_annotate_y_offset_spin.setEnabled(False)
        y_offset_layout.addWidget(self.auto_annotate_y_offset_spin)

        rotation_layout = QVBoxLayout()
        rotation_layout.addWidget(QLabel("Rotation (°):"))
        self.auto_annotate_rotation_spin = DataPlotStudioSpinBox()
        self.auto_annotate_rotation_spin.setRange(-360, 360)
        self.auto_annotate_rotation_spin.setValue(0)
        self.auto_annotate_rotation_spin.setEnabled(False)
        rotation_layout.addWidget(self.auto_annotate_rotation_spin)
        
        offset_layout.addLayout(x_offset_layout)
        offset_layout.addLayout(y_offset_layout)
        offset_layout.addLayout(rotation_layout)
        auto_layout.addLayout(offset_layout)
        
        auto_layout.addStretch()
        tab_widget.addTab(auto_tab, "Data Points")

        # Text Box Tab
        textbox_tab = QWidget()
        textbox_layout = QVBoxLayout(textbox_tab)

        textbox_layout.addWidget(QLabel("Text Box Content:"))
        self.textbox_content = DataPlotStudioLineEdit()
        self.textbox_content.setMinimumHeight(20)
        self.textbox_content.setPlaceholderText("Enter text for text box")
        textbox_layout.addWidget(self.textbox_content)

        textbox_layout.addWidget(QLabel("Text Box Position:"))
        self.textbox_position_combo = DataPlotStudioComboBox()
        self.textbox_position_combo.setMinimumHeight(20)
        self.textbox_position_combo.addItems([
            'upper left', 'upper center', 'upper right', 'center left', 
            'center', 'center right', 'lower left', 'lower center', 'lower right'
        ])
        textbox_layout.addWidget(self.textbox_position_combo)

        textbox_layout.addWidget(QLabel("Text Box Style:"))
        self.textbox_style_combo = DataPlotStudioComboBox()
        self.textbox_style_combo.setMinimumHeight(20)
        self.textbox_style_combo.addItems(['round', 'square', 'round,pad=1', 'round4,pad=0.5'])
        self.textbox_style_combo.setItemText(0, 'Rounded')
        self.textbox_style_combo.setItemText(1, 'Square')
        textbox_layout.addWidget(self.textbox_style_combo)

        textbox_layout.addWidget(QLabel("Background Color:"))
        bg_layout = QHBoxLayout()
        self.textbox_bg_button = DataPlotStudioButton("Choose", parent=self)
        self.textbox_bg_button.setMinimumHeight(20)
        self.textbox_bg_label = QLabel("White")
        bg_layout.addWidget(self.textbox_bg_button)
        bg_layout.addWidget(self.textbox_bg_label)
        textbox_layout.addLayout(bg_layout)

        self.textbox_enable_check = DataPlotStudioToggleSwitch("Enable Text Box")
        textbox_layout.addWidget(self.textbox_enable_check)

        textbox_layout.addStretch()
        tab_widget.addTab(textbox_tab, "Text Box")

        # Manual Annotations Tab
        manual_tab = QWidget()
        manual_layout = QVBoxLayout(manual_tab)

        manual_layout.addWidget(QLabel("Annotation Text:"))
        self.annotation_text = DataPlotStudioLineEdit()
        self.annotation_text.setMinimumHeight(20)
        self.annotation_text.setPlaceholderText("Enter text to add to plot")
        manual_layout.addWidget(self.annotation_text)

        manual_layout.addWidget(QLabel("X Position (0-1):"))
        self.annotation_x_spin = DataPlotStudioDoubleSpinBox()
        self.annotation_x_spin.setMinimumHeight(20)
        self.annotation_x_spin.setRange(0, 1)
        self.annotation_x_spin.setValue(0.5)
        self.annotation_x_spin.setSingleStep(0.05)
        manual_layout.addWidget(self.annotation_x_spin)

        manual_layout.addWidget(QLabel("Y Position (0-1):"))
        self.annotation_y_spin = DataPlotStudioDoubleSpinBox()
        self.annotation_y_spin.setMinimumHeight(20)
        self.annotation_y_spin.setRange(0, 1)
        self.annotation_y_spin.setValue(0.5)
        self.annotation_y_spin.setSingleStep(0.05)
        manual_layout.addWidget(self.annotation_y_spin)

        manual_layout.addWidget(QLabel("Font Size:"))
        self.annotation_fontsize_spin = DataPlotStudioSpinBox()
        self.annotation_fontsize_spin.setMinimumHeight(20)
        self.annotation_fontsize_spin.setRange(6, 36)
        self.annotation_fontsize_spin.setValue(12)
        manual_layout.addWidget(self.annotation_fontsize_spin)

        manual_layout.addWidget(QLabel("Font Color:"))
        color_layout = QHBoxLayout()
        self.annotation_color_button = DataPlotStudioButton("Choose", parent=self)
        self.annotation_color_button.setMinimumHeight(20)
        self.annotation_color_label = QLabel("Black")
        color_layout.addWidget(self.annotation_color_button)
        color_layout.addWidget(self.annotation_color_label)
        manual_layout.addLayout(color_layout)
        
        manual_layout.addWidget(QLabel("Background Color:"))
        background_color_layout = QHBoxLayout()
        self.annotation_bg_color_button = DataPlotStudioButton("Choose", parent=self)
        self.annotation_bg_color_label = QLabel("wheat")
        background_color_layout.addWidget(self.annotation_bg_color_button)
        background_color_layout.addWidget(self.annotation_bg_color_label)
        manual_layout.addLayout(background_color_layout)

        self.add_annotation_button = DataPlotStudioButton("Add Annotation", parent=self, base_color_hex=ThemeColors.MainColor, text_color_hex="white")
        self.add_annotation_button.setMinimumHeight(20)
        manual_layout.addWidget(self.add_annotation_button)

        manual_layout.addStretch()
        tab_widget.addTab(manual_tab, "Manual Label")

        layout.addWidget(tab_widget)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _setup_datatable_group(self, parent_layout: QVBoxLayout) -> None:
        group = DataPlotStudioGroupBox("Data Table")
        layout = QVBoxLayout()

        self.table_enable_check = DataPlotStudioToggleSwitch("Show Data Table on plot")
        self.table_enable_check.setChecked(False)
        layout.addWidget(self.table_enable_check)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("Type:"))
        self.table_type_combo = DataPlotStudioComboBox()
        self.table_type_combo.addItems(["Summary Stats", "First 5 Rows", "Last 5 Rows", "Correlation Matrix"])
        self.table_type_combo.setEnabled(False)
        self.table_type_combo.setVisible(False)
        controls_layout.addWidget(self.table_type_combo)

        controls_layout.addWidget(QLabel("Placement:"))
        self.table_location_combo = DataPlotStudioComboBox()
        self.table_location_combo.addItems(["bottom", "top", "right", "left", "center"])
        self.table_location_combo.setEnabled(False)
        self.table_location_combo.setVisible(False)
        controls_layout.addWidget(self.table_location_combo)
        layout.addLayout(controls_layout)

        settings_layout = QHBoxLayout()
        self.table_auto_font_size_check = DataPlotStudioToggleSwitch("Auto Font-Size")
        self.table_auto_font_size_check.setChecked(False)
        self.table_auto_font_size_check.setEnabled(False)
        settings_layout.addWidget(self.table_auto_font_size_check)

        settings_layout.addWidget(QLabel("Font Size:"))
        self.table_font_size_spin = DataPlotStudioSpinBox()
        self.table_font_size_spin.setRange(4, 40)
        self.table_font_size_spin.setValue(10)
        self.table_font_size_spin.setEnabled(False)
        self.table_font_size_spin.setVisible(False)
        settings_layout.addWidget(self.table_font_size_spin)

        settings_layout.addWidget(QLabel("Scale:"))
        self.table_scale_spin = DataPlotStudioDoubleSpinBox()
        self.table_scale_spin.setRange(0.5, 5.0)
        self.table_scale_spin.setValue(1.2)
        self.table_scale_spin.setSingleStep(0.1)
        self.table_scale_spin.setEnabled(False)
        self.table_scale_spin.setVisible(False)
        settings_layout.addWidget(self.table_scale_spin)

        layout.addLayout(settings_layout)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _setup_annotations_list_group(self, parent_layout: QVBoxLayout) -> None:
        group = DataPlotStudioGroupBox("Annotations List")
        layout = QVBoxLayout()

        self.annotations_list = DataPlotStudioListWidget()
        layout.addWidget(self.annotations_list)

        self.clear_annotations_button = DataPlotStudioButton("Clear All Annotations", parent=self, base_color_hex=ThemeColors.DestructiveColor, text_color_hex="white")
        layout.addWidget(self.clear_annotations_button)

        group.setLayout(layout)
        parent_layout.addWidget(group)