from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFontComboBox, QFrame, QTabWidget
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
import shutil
from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioToggleSwitch, DataPlotStudioButton, HelpIcon, ColormapButton
from ui.widgets.ControlElements import DataPlotStudioComboBox, DataPlotStudioDoubleSpinBox, DataPlotStudioGroupBox, DataPlotStudioLineEdit, DataPlotStudioSpinBox

class AppearanceSettingsTab(QWidget):
    help_requested = pyqtSignal(str)
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.has_latex: bool = shutil.which("latex") is not None
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setProperty("styleClass", "transparent_scroll_area")

        scroll_widget = QWidget()
        scroll_widget.setObjectName("TransparentScrollContent")
        scroll_layout = QVBoxLayout(scroll_widget)

        self._setup_theme_group(scroll_layout)
        scroll_layout.addSpacing(15)
        self._setup_font_group(scroll_layout)
        scroll_layout.addSpacing(15)
        self._setup_title_group(scroll_layout)
        self._setup_labels_group(scroll_layout)
        self._setup_spines_group(scroll_layout)
        self._setup_figure_group(scroll_layout)
        self._setup_accessibility_group(scroll_layout)
        self._setup_layout_style_group(scroll_layout)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

    def _setup_theme_group(self, parent_layout: QVBoxLayout) -> None:
        group = DataPlotStudioGroupBox("Theme Manager")
        layout = QVBoxLayout()

        info = QLabel("Save or load custom visual styles")
        info.setProperty("styleClass", "info_text")
        layout.addWidget(info)

        load_layout = QHBoxLayout()
        load_layout.addWidget(QLabel("Select Theme:"))
        self.theme_combo = DataPlotStudioComboBox()
        self.theme_combo.addItem("Select a theme...")
        load_layout.addWidget(self.theme_combo, 1)

        self.load_theme_button = DataPlotStudioButton("Apply theme", parent=self)
        self.load_theme_button.setToolTip("Apply the selected theme to the current plot")
        load_layout.addWidget(self.load_theme_button)
        layout.addLayout(load_layout)

        controls_layout = QHBoxLayout()
        self.save_theme_button = DataPlotStudioButton("Save Current Theme", parent=self)
        self.save_theme_button.setToolTip("Save the current visual settings to a JSON file")
        controls_layout.addWidget(self.save_theme_button)

        self.edit_theme_button = DataPlotStudioButton("Edit JSON", parent=self)
        self.edit_theme_button.setToolTip("Edit the JSON file of the selected theme")
        controls_layout.addWidget(self.edit_theme_button)

        self.delete_theme_button = DataPlotStudioButton("Delete theme", parent=self, base_color_hex=ThemeColors.DestructiveColor)
        controls_layout.addWidget(self.delete_theme_button)
        layout.addLayout(controls_layout)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _setup_font_group(self, parent_layout: QVBoxLayout) -> None:
        group = DataPlotStudioGroupBox("Font Settings")
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Font Family:"))
        self.font_family_combo = QFontComboBox()
        self.font_family_combo.setCurrentFont(QFont("Arial"))
        layout.addWidget(self.font_family_combo)

        latex_layout = QHBoxLayout()
        self.usetex_checkbox = DataPlotStudioToggleSwitch("Enable Latex Rendering")
        self.usetex_checkbox.setChecked(False)
        self.usetext_help = HelpIcon("latex_rendering")
        self.usetext_help.clicked.connect(lambda: self.help_requested.emit("latex_rendering"))
        
        latex_layout.addWidget(self.usetex_checkbox)
        latex_layout.addWidget(self.usetext_help)

        if not self.has_latex:
            self.usetex_checkbox.setEnabled(False)
            self.usetex_checkbox.setToolTip("LaTeX installation not found in system PATH.\n"
                                            "Please install TeX Live (Linux/Windows) or MacTeX (macOS)\n"
                                            "and ensure 'latex' is in your PATH to enable this feature.")
        else:
            self.usetex_checkbox.setToolTip("Render text using LaTeX for mathematical formatting.\n"
                                            "Example: $\\alpha > \\beta$")
            
        layout.addLayout(latex_layout)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _setup_title_group(self, parent_layout: QVBoxLayout) -> None:
        group = DataPlotStudioGroupBox("Title Options")
        layout = QVBoxLayout()
        
        self.title_check = DataPlotStudioToggleSwitch("Show Title")
        self.title_check.setChecked(True)
        layout.addWidget(self.title_check)

        layout.addWidget(QLabel("Title:"))
        self.title_input = DataPlotStudioLineEdit()
        self.title_input.setPlaceholderText("Enter plot title")
        layout.addWidget(self.title_input)

        layout.addWidget(QLabel("Title Size:"))
        self.title_size_spin = DataPlotStudioSpinBox()
        self.title_size_spin.setRange(8, 32)
        self.title_size_spin.setValue(14)
        layout.addWidget(self.title_size_spin)

        layout.addWidget(QLabel("Title Font Weight:"))
        self.title_weight_combo = DataPlotStudioComboBox()
        self.title_weight_combo.addItems(["normal", "bold", "light", "heavy"])
        self.title_weight_combo.setCurrentText("bold")
        layout.addWidget(self.title_weight_combo)

        layout.addWidget(QLabel("Title Position:"))
        self.title_position_combo = DataPlotStudioComboBox()
        self.title_position_combo.addItems(["center", "left", "right"])
        self.title_position_combo.setCurrentText("center")
        layout.addWidget(self.title_position_combo)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _setup_labels_group(self, parent_layout: QVBoxLayout) -> None:
        group = DataPlotStudioGroupBox("Axis Label Options")
        layout = QVBoxLayout()
        
        tab_widget = QTabWidget()
        
        # X axis tab
        x_tab = QWidget()
        x_layout = QVBoxLayout(x_tab)
        
        self.xlabel_check = DataPlotStudioToggleSwitch("Show X Label")
        self.xlabel_check.setChecked(True)
        x_layout.addWidget(self.xlabel_check)
        
        x_layout.addWidget(QLabel("X Label:"))
        self.xlabel_input = DataPlotStudioLineEdit()
        self.xlabel_input.setPlaceholderText("X axis label")
        x_layout.addWidget(self.xlabel_input)
        
        x_layout.addWidget(QLabel("X Label Font-size:"))
        self.xlabel_size_spin = DataPlotStudioSpinBox()
        self.xlabel_size_spin.setRange(5, 32)
        self.xlabel_size_spin.setValue(12)
        x_layout.addWidget(self.xlabel_size_spin)
        
        x_layout.addWidget(QLabel("X Label Font Weight"))
        self.xlabel_weight_combo = DataPlotStudioComboBox()
        self.xlabel_weight_combo.addItems(["normal", "bold", "light", "heavy"])
        self.xlabel_weight_combo.setCurrentText("normal")
        x_layout.addWidget(self.xlabel_weight_combo)
        
        x_layout.addStretch()
        tab_widget.addTab(x_tab, "X-Axis")
        
        y_tab = QWidget()
        y_layout = QVBoxLayout(y_tab)
        
        self.ylabel_check = DataPlotStudioToggleSwitch("Show Y Label")
        self.ylabel_check.setChecked(True)
        y_layout.addWidget(self.ylabel_check)

        y_layout.addWidget(QLabel("Y Label:"))
        self.ylabel_input = DataPlotStudioLineEdit()
        self.ylabel_input.setPlaceholderText("Y axis label")
        y_layout.addWidget(self.ylabel_input)

        y_layout.addWidget(QLabel("Y Label Font-size:"))
        self.ylabel_size_spin = DataPlotStudioSpinBox()
        self.ylabel_size_spin.setRange(5, 32)
        self.ylabel_size_spin.setValue(12)
        y_layout.addWidget(self.ylabel_size_spin)

        y_layout.addWidget(QLabel("Y Label Font Weight:"))
        self.ylabel_weight_combo = DataPlotStudioComboBox()
        self.ylabel_weight_combo.addItems(["normal", "bold", "light", "heavy"])
        self.ylabel_weight_combo.setCurrentText("normal")
        y_layout.addWidget(self.ylabel_weight_combo)
        
        y_layout.addStretch()
        tab_widget.addTab(y_tab, "Y-Axis")
        
        layout.addWidget(tab_widget)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _setup_spines_group(self, parent_layout: QVBoxLayout) -> None:
        group = DataPlotStudioGroupBox("Plot Spines (Borders)")
        layout = QVBoxLayout()

        info = QLabel("Customize the four borders (spines) of the plotting axes")
        info.setProperty("styleClass", "info_text")
        layout.addWidget(info)
        layout.addSpacing(10)

        presets_label = QLabel("Quick Presets")
        presets_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(presets_label)

        presets_btn_layout = QHBoxLayout()
        self.all_spines_btn = DataPlotStudioButton("All Spines", parent=self)
        self.all_spines_btn.setToolTip("Show all four spines")
        presets_btn_layout.addWidget(self.all_spines_btn)

        self.box_only_btn = DataPlotStudioButton("Box Only", parent=self)
        self.box_only_btn.setToolTip("Show only left and bottom spines")
        presets_btn_layout.addWidget(self.box_only_btn)

        self.no_spines_btn = DataPlotStudioButton("No Spines", parent=self)
        self.no_spines_btn.setToolTip("Hide all spines")
        presets_btn_layout.addWidget(self.no_spines_btn)
        layout.addLayout(presets_btn_layout)
        layout.addSpacing(15)

        global_label = QLabel("Global Spine Settings")
        global_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(global_label)

        global_layout = QHBoxLayout()
        global_layout.addWidget(QLabel("Line Width:"))
        self.global_spine_width_spin = DataPlotStudioDoubleSpinBox()
        self.global_spine_width_spin.setRange(0.1, 5.0)
        self.global_spine_width_spin.setValue(1.0)
        self.global_spine_width_spin.setSingleStep(0.1)
        global_layout.addWidget(self.global_spine_width_spin)

        global_layout.addWidget(QLabel("Color:"))
        self.global_spine_color_button = DataPlotStudioButton("Choose", parent=self)
        self.global_spine_color_label = QLabel("Black")
        global_layout.addWidget(self.global_spine_color_label)
        global_layout.addWidget(self.global_spine_color_button)
        layout.addLayout(global_layout)
        layout.addSpacing(10)

        self.individual_spines_check = DataPlotStudioToggleSwitch("Customize spines individually")
        self.individual_spines_check.setChecked(False)
        self.individual_spines_check.setToolTip("Enabled to set visibility, width and color of the four spines individually")
        layout.addWidget(self.individual_spines_check)

        self.individual_spines_container = QWidget()
        self.individual_spines_container.setVisible(False)
        indiv_layout = QVBoxLayout(self.individual_spines_container)
        indiv_layout.setContentsMargins(0, 0, 0, 0)

        spine_tabs = QTabWidget()
        
        # Top Spine
        top_tab = QWidget()
        top_layout = QVBoxLayout(top_tab)
        self.top_spine_visible_check, self.top_spine_width_spin, self.top_spine_color_button, self.top_spine_color_label = self._create_spine_ui("Top Spine", top_layout)
        top_layout.addStretch()
        spine_tabs.addTab(top_tab, "Top")

        # Bottom Spine
        bottom_tab = QWidget()
        bottom_layout = QVBoxLayout(bottom_tab)
        self.bottom_spine_visible_check, self.bottom_spine_width_spin, self.bottom_spine_color_button, self.bottom_spine_color_label = self._create_spine_ui("Bottom Spine", bottom_layout)
        bottom_layout.addStretch()
        spine_tabs.addTab(bottom_tab, "Bottom")

        # Left Spine
        left_tab = QWidget()
        left_layout = QVBoxLayout(left_tab)
        self.left_spine_visible_check, self.left_spine_width_spin, self.left_spine_color_button, self.left_spine_color_label = self._create_spine_ui("Left Spine", left_layout)
        left_layout.addStretch()
        spine_tabs.addTab(left_tab, "Left")

        # Right Spine
        right_tab = QWidget()
        right_layout = QVBoxLayout(right_tab)
        self.right_spine_visible_check, self.right_spine_width_spin, self.right_spine_color_button, self.right_spine_color_label = self._create_spine_ui("Right Spine", right_layout)
        right_layout.addStretch()
        spine_tabs.addTab(right_tab, "Right")

        indiv_layout.addWidget(spine_tabs)
        layout.addWidget(self.individual_spines_container)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _create_spine_ui(self, title: str, parent_layout: QVBoxLayout) -> tuple:
        """Helper to create repetitive spine configurations."""
        vis_check = DataPlotStudioToggleSwitch(f"Show {title}")
        vis_check.setChecked(True)
        parent_layout.addWidget(vis_check)

        parent_layout.addWidget(QLabel("Line Width:"))
        width_spin = DataPlotStudioDoubleSpinBox()
        width_spin.setRange(0.1, 5.0)
        width_spin.setValue(1.0)
        width_spin.setSingleStep(0.1)
        parent_layout.addWidget(width_spin)

        parent_layout.addWidget(QLabel("Color:"))
        color_layout = QHBoxLayout()
        color_btn = DataPlotStudioButton("Choose Color", parent=self)
        color_btn.setMinimumHeight(28)
        color_label = QLabel("Black")
        color_layout.addWidget(color_btn)
        color_layout.addWidget(color_label)
        parent_layout.addLayout(color_layout)

        return vis_check, width_spin, color_btn, color_label

    def _setup_figure_group(self, parent_layout: QVBoxLayout) -> None:
        self.figure_size_group = DataPlotStudioGroupBox("Figure Settings")
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Figure Width:"))
        self.width_spin = DataPlotStudioSpinBox()
        self.width_spin.setRange(4, 20)
        self.width_spin.setValue(12)
        layout.addWidget(self.width_spin)

        layout.addWidget(QLabel("Figure Height:"))
        self.height_spin = DataPlotStudioSpinBox()
        self.height_spin.setRange(4, 20)
        self.height_spin.setValue(8)
        layout.addWidget(self.height_spin)

        self.dpi_spin = DataPlotStudioSpinBox()
        self.dpi_spin.setRange(50, 300)
        self.dpi_spin.setValue(100)
        layout.addWidget(self.dpi_spin)

        layout.addWidget(QLabel("Background Color:"))
        bg_layout = QHBoxLayout()
        self.bg_color_button = DataPlotStudioButton("Choose Color", parent=self)
        self.bg_color_label = QLabel("White")
        bg_layout.addWidget(self.bg_color_button)
        bg_layout.addWidget(self.bg_color_label)
        layout.addLayout(bg_layout)

        layout.addWidget(QLabel("Plot Area Color"))
        face_layout = QHBoxLayout()
        self.face_color_button = DataPlotStudioButton("Choose Color", parent=self)
        self.face_color_label = QLabel("White")
        face_layout.addWidget(self.face_color_button)
        face_layout.addWidget(self.face_color_label)
        layout.addLayout(face_layout)

        layout.addWidget(QLabel("Color Palette / Colormap:"))
        self.palette_combo = ColormapButton(parent=self)
        self.palette_combo.setToolTip("Click to search and select a colormap")
        layout.addWidget(self.palette_combo)

        self.figure_size_group.setLayout(layout)
        parent_layout.addWidget(self.figure_size_group)

    def _setup_accessibility_group(self, parent_layout: QVBoxLayout) -> None:
        group = DataPlotStudioGroupBox("Accessibility")
        layout = QVBoxLayout()
        
        self.colorblind_check = DataPlotStudioToggleSwitch("Enable Color Blindness Mode")
        self.colorblind_check.setToolTip("Applies an SVG filter to simulate color-blindness on the canvas")
        layout.addWidget(self.colorblind_check)
        
        self.colorblind_type_combo = DataPlotStudioComboBox()
        self.colorblind_type_combo.addItems([
            "Protanopia (No Red)",
            "Deuteranopia (No Green)",
            "Tritanopia (No Blue)",
            "Achromatopsia (Monochromacy)"
        ])
        layout.addWidget(self.colorblind_type_combo)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _setup_layout_style_group(self, parent_layout: QVBoxLayout) -> None:
        # Appended into figure_size_group logic originally, but better placed cleanly at the end.
        layout = self.figure_size_group.layout()
        layout.addWidget(QLabel("Layout:"))
        self.tight_layout_check = DataPlotStudioToggleSwitch("Tight Layout")
        self.tight_layout_check.setChecked(True)
        layout.addWidget(self.tight_layout_check)

        layout.addWidget(QLabel("Style:"))
        self.style_combo = DataPlotStudioComboBox()
        self.style_combo.addItems(['default', 'ggplot', 'seaborn', 'dark_background', 'bmh'])
        layout.addWidget(self.style_combo)