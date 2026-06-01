from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QTabWidget, QStackedWidget, QGridLayout, QSpinBox, QDoubleSpinBox, QListWidget, QLineEdit, QGroupBox, QComboBox, QPushButton

from ui.icons import IconBuilder
from ui.theme import ThemeColors
from ui.widgets import ToggleSwitch

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

        self._setup_reference_lines_group(scroll_layout)
        scroll_layout.addSpacing(15)
        self._setup_annotation_tools_group(scroll_layout)
        scroll_layout.addSpacing(15)
        self._setup_datatable_group(scroll_layout)
        scroll_layout.addSpacing(15)
        self._setup_annotations_list_group(scroll_layout)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

    def _setup_reference_lines_group(self, parent_layout: QVBoxLayout) -> None:
        tabs = QTabWidget()

        # Lines Tab
        lines_tab = QWidget()
        lines_layout = QVBoxLayout(lines_tab)

        active_label_line = QLabel("Active Lines:")
        lines_layout.addWidget(active_label_line)
        self.reference_lines_list = QListWidget()
        self.reference_lines_list.setToolTip("List of active reference lines on the plot")
        lines_layout.addWidget(self.reference_lines_list)

        lines_toolbar = QHBoxLayout()
        self.add_ref_line_button = QPushButton("+ Add New Line")
        self.add_ref_line_button.setObjectName("MainActionButton")

        self.delete_ref_line_button = QPushButton("- Delete Selected")
        self.delete_ref_line_button.setObjectName("DestructiveButton")
        self.delete_ref_line_button.setEnabled(False)

        self.clear_ref_lines_button = QPushButton("Clear All")
        self.clear_ref_lines_button.setObjectName("DestructiveButton")

        lines_toolbar.addWidget(self.add_ref_line_button)
        lines_toolbar.addWidget(self.delete_ref_line_button)
        lines_toolbar.addWidget(self.clear_ref_lines_button)
        lines_layout.addLayout(lines_toolbar)

        lines_layout.addSpacing(10)
        lines_layout.addWidget(QLabel("<b>Line Properties</b>"))

        lines_editor = QGridLayout()

        lines_editor.addWidget(QLabel("Type:"), 0, 0)
        self.ref_line_type_combo = QComboBox()
        self.ref_line_type_combo.addItems(["Horizontal (axhline)", "Vertical (axvline)", "Diagonal (axline)"])
        lines_editor.addWidget(self.ref_line_type_combo, 0, 1, 1, 3)

        self.ref_line_params_stack = QStackedWidget()

        h_page = QWidget()
        h_layout = QHBoxLayout(h_page)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.addWidget(QLabel("Y Position:"))
        self.ref_line_y_spin = QDoubleSpinBox()
        self.ref_line_y_spin.setRange(-1e9, 1e9)
        self.ref_line_y_spin.setValue(0.0)
        self.ref_line_y_spin.setSingleStep(0.1)
        h_layout.addWidget(self.ref_line_y_spin)
        h_layout.addStretch()
        self.ref_line_params_stack.addWidget(h_page)

        v_page = QWidget()
        v_layout = QHBoxLayout(v_page)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.addWidget(QLabel("X Position:"))
        self.ref_line_x_spin = QDoubleSpinBox()
        self.ref_line_x_spin.setRange(-1e9, 1e9)
        self.ref_line_x_spin.setValue(0.0)
        self.ref_line_x_spin.setSingleStep(0.1)
        v_layout.addWidget(self.ref_line_x_spin)
        v_layout.addStretch()
        self.ref_line_params_stack.addWidget(v_page)

        d_page = QWidget()
        d_layout = QHBoxLayout(d_page)
        d_layout.setContentsMargins(0, 0, 0, 0)
        d_layout.addWidget(QLabel("Slope:"))
        self.ref_line_slope_spin = QDoubleSpinBox()
        self.ref_line_slope_spin.setRange(-1e6, 1e6)
        self.ref_line_slope_spin.setValue(1.0)
        d_layout.addWidget(self.ref_line_slope_spin)
        d_layout.addWidget(QLabel("Intercept:"))
        self.ref_line_intercept_spin = QDoubleSpinBox()
        self.ref_line_intercept_spin.setRange(-1e9, 1e9)
        self.ref_line_intercept_spin.setValue(0.0)
        d_layout.addWidget(self.ref_line_intercept_spin)
        d_layout.addStretch()
        self.ref_line_params_stack.addWidget(d_page)

        lines_editor.addWidget(self.ref_line_params_stack, 1, 0, 1, 4)

        lines_editor.addWidget(QLabel("Color:"), 2, 0)
        color_box = QHBoxLayout()
        color_box.setContentsMargins(0, 0, 0, 0)
        self.ref_line_color_button = QPushButton("Choose", parent=self)
        self.ref_line_color_label = QLabel("Black")
        color_box.addWidget(self.ref_line_color_button)
        color_box.addWidget(self.ref_line_color_label)
        lines_editor.addLayout(color_box, 2, 1)

        lines_editor.addWidget(QLabel("Style:"), 2, 2)
        self.ref_line_style_combo = QComboBox()
        self.ref_line_style_combo.addItems(["solid", "dashed", "dashdot", "dotted"])
        lines_editor.addWidget(self.ref_line_style_combo, 2, 3)

        lines_editor.addWidget(QLabel("Width:"), 3, 0)
        self.ref_line_width_spin = QDoubleSpinBox()
        self.ref_line_width_spin.setRange(0.1, 20.0)
        self.ref_line_width_spin.setValue(1.5)
        self.ref_line_width_spin.setSingleStep(0.1)
        lines_editor.addWidget(self.ref_line_width_spin, 3, 1)

        lines_editor.addWidget(QLabel("Alpha:"), 3, 2)
        self.ref_line_alpha_spin = QDoubleSpinBox()
        self.ref_line_alpha_spin.setRange(0.0, 1.0)
        self.ref_line_alpha_spin.setValue(1.0)
        self.ref_line_alpha_spin.setSingleStep(0.1)
        lines_editor.addWidget(self.ref_line_alpha_spin, 3, 3)

        lines_editor.addWidget(QLabel("Z-Order:"), 4, 0)
        self.ref_line_zorder_spin = QSpinBox()
        self.ref_line_zorder_spin.setRange(-100, 100)
        self.ref_line_zorder_spin.setValue(10)
        self.ref_line_zorder_spin.setToolTip("Higher values draw on top of lower values.")
        lines_editor.addWidget(self.ref_line_zorder_spin, 4, 1)

        lines_editor.addWidget(QLabel("Label:"), 5, 0)
        self.ref_line_label_input = QLineEdit()
        self.ref_line_label_input.setPlaceholderText("Optional label for legend")
        lines_editor.addWidget(self.ref_line_label_input, 5, 1, 1, 3)

        lines_layout.addLayout(lines_editor)

        line_edit_actions = QHBoxLayout()
        self.deselect_ref_line_button = QPushButton("Cancel / Deselect")
        self.deselect_ref_line_button.setEnabled(False)
        self.update_ref_line_button = QPushButton("Apply Changes")
        self.update_ref_line_button.setObjectName("MainActionButton")
        self.update_ref_line_button.setEnabled(False)

        line_edit_actions.addWidget(self.deselect_ref_line_button)
        line_edit_actions.addWidget(self.update_ref_line_button)
        lines_layout.addLayout(line_edit_actions)

        tabs.addTab(lines_tab, "Lines")

        # Spans Tab
        spans_tab = QWidget()
        spans_layout = QVBoxLayout(spans_tab)

        active_label_span = QLabel("Active Spans:")
        spans_layout.addWidget(active_label_span)
        self.reference_spans_list = QListWidget()
        self.reference_spans_list.setToolTip("List of active reference spans on the plot")
        spans_layout.addWidget(self.reference_spans_list)

        spans_toolbar = QHBoxLayout()
        self.add_ref_span_button = QPushButton("+ Add New Span")
        self.add_ref_span_button.setObjectName("MainActionButton")

        self.delete_ref_span_button = QPushButton("- Delete Selected")
        self.delete_ref_span_button.setObjectName("DestructiveButton")
        self.delete_ref_span_button.setEnabled(False)

        self.clear_ref_spans_button = QPushButton("Clear All")
        self.clear_ref_spans_button.setObjectName("DestructiveButton")

        spans_toolbar.addWidget(self.add_ref_span_button)
        spans_toolbar.addWidget(self.delete_ref_span_button)
        spans_toolbar.addWidget(self.clear_ref_spans_button)
        spans_layout.addLayout(spans_toolbar)

        spans_layout.addSpacing(10)
        spans_layout.addWidget(QLabel("<b>Span Properties</b>"))

        spans_editor = QGridLayout()

        spans_editor.addWidget(QLabel("Type:"), 0, 0)
        self.ref_span_type_combo = QComboBox()
        self.ref_span_type_combo.addItems(["Horizontal (axhspan)", "Vertical (axvspan)"])
        spans_editor.addWidget(self.ref_span_type_combo, 0, 1, 1, 3)

        self.ref_span_params_stack = QStackedWidget()

        span_h_page = QWidget()
        span_h_layout = QHBoxLayout(span_h_page)
        span_h_layout.setContentsMargins(0, 0, 0, 0)
        span_h_layout.addWidget(QLabel("Y Min:"))
        self.ref_span_ymin_spin = QDoubleSpinBox()
        self.ref_span_ymin_spin.setRange(-1e9, 1e9)
        self.ref_span_ymin_spin.setValue(0.0)
        span_h_layout.addWidget(self.ref_span_ymin_spin)
        span_h_layout.addWidget(QLabel("Y Max:"))
        self.ref_span_ymax_spin = QDoubleSpinBox()
        self.ref_span_ymax_spin.setRange(-1e9, 1e9)
        self.ref_span_ymax_spin.setValue(1.0)
        span_h_layout.addWidget(self.ref_span_ymax_spin)
        self.ref_span_params_stack.addWidget(span_h_page)

        span_v_page = QWidget()
        span_v_layout = QHBoxLayout(span_v_page)
        span_v_layout.setContentsMargins(0, 0, 0, 0)
        span_v_layout.addWidget(QLabel("X Min:"))
        self.ref_span_xmin_spin = QDoubleSpinBox()
        self.ref_span_xmin_spin.setRange(-1e9, 1e9)
        self.ref_span_xmin_spin.setValue(0.0)
        span_v_layout.addWidget(self.ref_span_xmin_spin)
        span_v_layout.addWidget(QLabel("X Max:"))
        self.ref_span_xmax_spin = QDoubleSpinBox()
        self.ref_span_xmax_spin.setRange(-1e9, 1e9)
        self.ref_span_xmax_spin.setValue(1.0)
        span_v_layout.addWidget(self.ref_span_xmax_spin)
        self.ref_span_params_stack.addWidget(span_v_page)

        spans_editor.addWidget(self.ref_span_params_stack, 1, 0, 1, 4)

        spans_editor.addWidget(QLabel("Color:"), 2, 0)
        span_color_box = QHBoxLayout()
        span_color_box.setContentsMargins(0, 0, 0, 0)
        self.ref_span_color_button = QPushButton("Choose", parent=self)
        self.ref_span_color_label = QLabel("blue")
        span_color_box.addWidget(self.ref_span_color_button)
        span_color_box.addWidget(self.ref_span_color_label)
        spans_editor.addLayout(span_color_box, 2, 1)

        spans_editor.addWidget(QLabel("Alpha:"), 2, 2)
        self.ref_span_alpha_spin = QDoubleSpinBox()
        self.ref_span_alpha_spin.setRange(0.0, 1.0)
        self.ref_span_alpha_spin.setValue(0.3)
        self.ref_span_alpha_spin.setSingleStep(0.1)
        spans_editor.addWidget(self.ref_span_alpha_spin, 2, 3)

        spans_editor.addWidget(QLabel("Z-Order:"), 3, 0)
        self.ref_span_zorder_spin = QSpinBox()
        self.ref_span_zorder_spin.setRange(-100, 100)
        self.ref_span_zorder_spin.setValue(-1)
        self.ref_span_zorder_spin.setToolTip("Background spans should use negative Z-Order")
        spans_editor.addWidget(self.ref_span_zorder_spin, 3, 1)

        spans_editor.addWidget(QLabel("Label:"), 4, 0)
        self.ref_span_label_input = QLineEdit()
        self.ref_span_label_input.setPlaceholderText("Optional label for legend")
        spans_editor.addWidget(self.ref_span_label_input, 4, 1, 1, 3)

        spans_layout.addLayout(spans_editor)

        span_edit_actions = QHBoxLayout()
        self.deselect_ref_span_button = QPushButton("Cancel / Deselect")
        self.deselect_ref_span_button.setEnabled(False)
        self.update_ref_span_button = QPushButton("Apply Changes")
        self.update_ref_span_button.setObjectName("MainActionButton")
        self.update_ref_span_button.setEnabled(False)

        span_edit_actions.addWidget(self.deselect_ref_span_button)
        span_edit_actions.addWidget(self.update_ref_span_button)
        spans_layout.addLayout(span_edit_actions)

        tabs.addTab(spans_tab, "Spans")

        parent_layout.addWidget(tabs)

    def _setup_annotation_tools_group(self, parent_layout: QVBoxLayout) -> None:
        group = QGroupBox("Annotation Tools")
        layout = QVBoxLayout()
        
        tab_widget = QTabWidget()
        
        # Auto Annotations Tab
        auto_tab = QWidget()
        auto_layout = QVBoxLayout(auto_tab)

        self.auto_annotate_check = ToggleSwitch("Annotate All points")
        self.auto_annotate_check.setToolTip("Automatically set text labels to all data points")
        auto_layout.addWidget(self.auto_annotate_check)

        auto_layout.addWidget(QLabel("Label Source Column:"))
        self.auto_annotate_col_combo = QComboBox()
        self.auto_annotate_col_combo.setMinimumHeight(20)
        self.auto_annotate_col_combo.setToolTip("Select the column to use for the point labels")
        self.auto_annotate_col_combo.addItem("Default (Y-value)")
        self.auto_annotate_col_combo.setEnabled(False)
        auto_layout.addWidget(self.auto_annotate_col_combo)
        
        # Font styling settigs
        font_layout = QHBoxLayout()
        
        size_layout = QVBoxLayout()
        size_layout.addWidget(QLabel("Font-size:"))
        self.auto_annotate_fontsize_spin = QSpinBox()
        self.auto_annotate_fontsize_spin.setRange(6, 36)
        self.auto_annotate_fontsize_spin.setValue(10)
        self.auto_annotate_fontsize_spin.setEnabled(False)
        size_layout.addWidget(self.auto_annotate_fontsize_spin)
        
        weight_layout = QVBoxLayout()
        weight_layout.addWidget(QLabel("Font Weight:"))
        self.auto_annotate_weight_combo = QComboBox()
        self.auto_annotate_weight_combo.addItems(["normal", "bold", "heavy", "light"])
        self.auto_annotate_weight_combo.setEnabled(False)
        weight_layout.addWidget(self.auto_annotate_weight_combo)
        
        font_layout.addLayout(size_layout)
        font_layout.addLayout(weight_layout)
        auto_layout.addLayout(font_layout)
        
        # Color options
        auto_layout.addWidget(QLabel("Font Color:"))
        color_layout = QHBoxLayout()
        self.auto_annotate_color_button = QPushButton("Choose", parent=self)
        self.auto_annotate_color_button.setEnabled(False)
        self.auto_annotate_color_label = QLabel("Black")
        color_layout.addWidget(self.auto_annotate_color_button)
        color_layout.addWidget(self.auto_annotate_color_label)
        auto_layout.addLayout(color_layout)
        
        # Position
        offset_layout = QHBoxLayout()
        
        x_offset_layout = QVBoxLayout()
        x_offset_layout.addWidget(QLabel("X Offset"))
        self.auto_annotate_x_offset_spin = QDoubleSpinBox()
        self.auto_annotate_x_offset_spin.setRange(-200.0, 200.0)
        self.auto_annotate_x_offset_spin.setValue(0.0)
        self.auto_annotate_x_offset_spin.setEnabled(False)
        x_offset_layout.addWidget(self.auto_annotate_x_offset_spin)
        
        y_offset_layout = QVBoxLayout()
        y_offset_layout.addWidget(QLabel("Y Offset:"))
        self.auto_annotate_y_offset_spin = QDoubleSpinBox()
        self.auto_annotate_y_offset_spin.setRange(-200.0, 200.0)
        self.auto_annotate_y_offset_spin.setValue(5.0)
        self.auto_annotate_y_offset_spin.setEnabled(False)
        y_offset_layout.addWidget(self.auto_annotate_y_offset_spin)

        rotation_layout = QVBoxLayout()
        rotation_layout.addWidget(QLabel("Rotation (°):"))
        self.auto_annotate_rotation_spin = QSpinBox()
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
        self.textbox_content = QLineEdit()
        self.textbox_content.setMinimumHeight(20)
        self.textbox_content.setPlaceholderText("Enter text for text box")
        textbox_layout.addWidget(self.textbox_content)

        textbox_layout.addWidget(QLabel("Text Box Position:"))
        self.textbox_position_combo = QComboBox()
        self.textbox_position_combo.setMinimumHeight(20)
        self.textbox_position_combo.addItems([
            'upper left', 'upper center', 'upper right', 'center left', 
            'center', 'center right', 'lower left', 'lower center', 'lower right'
        ])
        textbox_layout.addWidget(self.textbox_position_combo)

        textbox_layout.addWidget(QLabel("Text Box Style:"))
        self.textbox_style_combo = QComboBox()
        self.textbox_style_combo.setMinimumHeight(20)
        self.textbox_style_combo.addItems(['round', 'square', 'round,pad=1', 'round4,pad=0.5'])
        self.textbox_style_combo.setItemText(0, 'Rounded')
        self.textbox_style_combo.setItemText(1, 'Square')
        textbox_layout.addWidget(self.textbox_style_combo)

        textbox_layout.addWidget(QLabel("Background Color:"))
        bg_layout = QHBoxLayout()
        self.textbox_bg_button = QPushButton("Choose", parent=self)
        self.textbox_bg_button.setMinimumHeight(20)
        self.textbox_bg_label = QLabel("White")
        bg_layout.addWidget(self.textbox_bg_button)
        bg_layout.addWidget(self.textbox_bg_label)
        textbox_layout.addLayout(bg_layout)

        self.textbox_enable_check = ToggleSwitch("Enable Text Box")
        textbox_layout.addWidget(self.textbox_enable_check)

        textbox_layout.addStretch()
        tab_widget.addTab(textbox_tab, "Text Box")

        # Manual Annotations Tab
        manual_tab = QWidget()
        manual_layout = QVBoxLayout(manual_tab)

        manual_layout.addWidget(QLabel("Annotation Text:"))
        self.annotation_text = QLineEdit()
        self.annotation_text.setPlaceholderText("Enter text to add to plot")
        manual_layout.addWidget(self.annotation_text)

        manual_layout.addWidget(QLabel("X Position (0-1):"))
        self.annotation_x_spin = QDoubleSpinBox()
        self.annotation_x_spin.setMinimumHeight(20)
        self.annotation_x_spin.setRange(0, 1)
        self.annotation_x_spin.setValue(0.5)
        self.annotation_x_spin.setSingleStep(0.05)
        manual_layout.addWidget(self.annotation_x_spin)

        manual_layout.addWidget(QLabel("Y Position (0-1):"))
        self.annotation_y_spin = QDoubleSpinBox()
        self.annotation_y_spin.setMinimumHeight(20)
        self.annotation_y_spin.setRange(0, 1)
        self.annotation_y_spin.setValue(0.5)
        self.annotation_y_spin.setSingleStep(0.05)
        manual_layout.addWidget(self.annotation_y_spin)

        manual_layout.addWidget(QLabel("Font Size:"))
        self.annotation_fontsize_spin = QSpinBox()
        self.annotation_fontsize_spin.setMinimumHeight(20)
        self.annotation_fontsize_spin.setRange(6, 36)
        self.annotation_fontsize_spin.setValue(12)
        manual_layout.addWidget(self.annotation_fontsize_spin)

        manual_layout.addWidget(QLabel("Font Color:"))
        color_layout = QHBoxLayout()
        self.annotation_color_button = QPushButton("Choose", parent=self)
        self.annotation_color_label = QLabel("Black")
        color_layout.addWidget(self.annotation_color_button)
        color_layout.addWidget(self.annotation_color_label)
        manual_layout.addLayout(color_layout)
        
        manual_layout.addWidget(QLabel("Background Color:"))
        background_color_layout = QHBoxLayout()
        self.annotation_bg_color_button = QPushButton("Choose", parent=self)
        self.annotation_bg_color_label = QLabel("wheat")
        background_color_layout.addWidget(self.annotation_bg_color_button)
        background_color_layout.addWidget(self.annotation_bg_color_label)
        manual_layout.addLayout(background_color_layout)

        self.add_annotation_button = QPushButton("Add Annotation")
        self.add_annotation_button.setObjectName("MainActionButton")
        manual_layout.addWidget(self.add_annotation_button)

        manual_layout.addStretch()
        tab_widget.addTab(manual_tab, "Manual Label")

        layout.addWidget(tab_widget)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _setup_datatable_group(self, parent_layout: QVBoxLayout) -> None:
        group = QGroupBox("Data Table")
        layout = QVBoxLayout()

        self.table_enable_check = ToggleSwitch("Show Data Table on plot")
        self.table_enable_check.setChecked(False)
        layout.addWidget(self.table_enable_check)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("Type:"))
        self.table_type_combo = QComboBox()
        self.table_type_combo.addItems(["Summary Stats", "First 5 Rows", "Last 5 Rows", "Correlation Matrix"])
        self.table_type_combo.setEnabled(False)
        self.table_type_combo.setVisible(False)
        controls_layout.addWidget(self.table_type_combo)

        controls_layout.addWidget(QLabel("Placement:"))
        self.table_location_combo = QComboBox()
        self.table_location_combo.addItems(["bottom", "top", "right", "left", "center"])
        self.table_location_combo.setEnabled(False)
        self.table_location_combo.setVisible(False)
        controls_layout.addWidget(self.table_location_combo)
        layout.addLayout(controls_layout)

        settings_layout = QHBoxLayout()
        self.table_auto_font_size_check = ToggleSwitch("Auto Font-Size")
        self.table_auto_font_size_check.setChecked(False)
        self.table_auto_font_size_check.setEnabled(False)
        settings_layout.addWidget(self.table_auto_font_size_check)

        settings_layout.addWidget(QLabel("Font Size:"))
        self.table_font_size_spin = QSpinBox()
        self.table_font_size_spin.setRange(4, 40)
        self.table_font_size_spin.setValue(10)
        self.table_font_size_spin.setEnabled(False)
        self.table_font_size_spin.setVisible(False)
        settings_layout.addWidget(self.table_font_size_spin)

        settings_layout.addWidget(QLabel("Scale:"))
        self.table_scale_spin = QDoubleSpinBox()
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
        group = QGroupBox("Annotations List")
        layout = QVBoxLayout()

        self.annotations_list = QListWidget()
        layout.addWidget(self.annotations_list)

        self.clear_annotations_button = QPushButton("Clear All Annotations")
        self.clear_annotations_button.setObjectName("DestructiveColor")
        layout.addWidget(self.clear_annotations_button)

        group.setLayout(layout)
        parent_layout.addWidget(group)