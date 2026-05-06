from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QTabWidget
from PyQt6.QtCore import pyqtSignal

from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioToggleSwitch
from ui.widgets.ControlElements import DataPlotStudioComboBox, DataPlotStudioDoubleSpinBox, DataPlotStudioGroupBox, DataPlotStudioLineEdit, DataPlotStudioSpinBox

class AxesSettingsTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
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

        self._setup_axes_group(scroll_layout)
        scroll_layout.addSpacing(15)
        self._setup_axis_orientation_group(scroll_layout)
        scroll_layout.addSpacing(15)
        self._setup_datetime_formatting_group(scroll_layout)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

    def _setup_axes_group(self, parent_layout: QVBoxLayout) -> None:
        group = DataPlotStudioGroupBox("Axis Options")
        layout = QVBoxLayout()
        
        self.axis_tab_widget = QTabWidget()

        # X-Axi
        x_tab = QWidget()
        x_layout = QVBoxLayout(x_tab)

        x_layout.addWidget(QLabel("X-axis - Auto Limit:"))
        self.x_auto_check = DataPlotStudioToggleSwitch("Auto")
        self.x_auto_check.setChecked(True)
        x_layout.addWidget(self.x_auto_check)

        self.x_invert_axis_check = DataPlotStudioToggleSwitch("Invert X-axis")
        self.x_invert_axis_check.setChecked(False)
        self.x_invert_axis_check.setToolTip("Reverses the direction of data on the x-axis")
        x_layout.addWidget(self.x_invert_axis_check)

        self.x_top_axis_check = DataPlotStudioToggleSwitch("Move X-axis to top")
        self.x_top_axis_check.setChecked(False)
        self.x_top_axis_check.setToolTip("Moves the x-axis ticks and labels to the top of the plot")
        x_layout.addWidget(self.x_top_axis_check)

        x_layout.addWidget(QLabel("X Min:"))
        self.x_min_spin = DataPlotStudioDoubleSpinBox()
        self.x_min_spin.setRange(-1000000, 1000000)
        self.x_min_spin.setEnabled(False)
        x_layout.addWidget(self.x_min_spin)

        x_layout.addWidget(QLabel("X Max:"))
        self.x_max_spin = DataPlotStudioDoubleSpinBox()
        self.x_max_spin.setRange(-1000000, 1000000)
        self.x_max_spin.setEnabled(False)
        x_layout.addWidget(self.x_max_spin)

        x_layout.addWidget(QLabel("X-axis Tick Label Size:"))
        self.xtick_label_size_spin = DataPlotStudioSpinBox()
        self.xtick_label_size_spin.setRange(6, 20)
        self.xtick_label_size_spin.setValue(10)
        x_layout.addWidget(self.xtick_label_size_spin)

        x_layout.addWidget(QLabel("X-axis Tick Rotation:"))
        self.xtick_rotation_spin = DataPlotStudioSpinBox()
        self.xtick_rotation_spin.setRange(-90, 90)
        self.xtick_rotation_spin.setValue(0)
        x_layout.addWidget(self.xtick_rotation_spin)

        x_layout.addWidget(QLabel("Max Number of Ticks"))
        self.x_max_ticks_spin = DataPlotStudioSpinBox()
        self.x_max_ticks_spin.setRange(3, 50)
        self.x_max_ticks_spin.setValue(10)
        self.x_max_ticks_spin.setToolTip("Maximum number of tick labels on the x-axis")
        x_layout.addWidget(self.x_max_ticks_spin)

        x_layout.addSpacing(5)
        
        self.x_show_minor_ticks_check = DataPlotStudioToggleSwitch("Show Minor X-axis Ticks")
        self.x_show_minor_ticks_check.setChecked(False)
        self.x_show_minor_ticks_check.setToolTip("Display the minor tick marks and labels on the x-axis")
        x_layout.addWidget(self.x_show_minor_ticks_check)

        x_layout.addSpacing(5)

        x_layout.addWidget(QLabel("X-axis major Tick Direction:"))
        self.x_major_tick_direction_combo = DataPlotStudioComboBox()
        self.x_major_tick_direction_combo.addItems(["out", "in", "inout"])
        self.x_major_tick_direction_combo.setToolTip("Direction of the major tick marks")
        x_layout.addWidget(self.x_major_tick_direction_combo)

        x_layout.addWidget(QLabel("X-axis Major Tick Width"))
        self.x_major_tick_width_spin = DataPlotStudioDoubleSpinBox()
        self.x_major_tick_width_spin.setRange(0.1, 5.0)
        self.x_major_tick_width_spin.setValue(1.0)
        self.x_major_tick_width_spin.setSingleStep(0.1)
        self.x_major_tick_width_spin.setToolTip("Width/thickness of the major tick marks")
        x_layout.addWidget(self.x_major_tick_width_spin)

        x_layout.addWidget(QLabel("X-axis Minor Tick Direction"))
        self.x_minor_tick_direction_combo = DataPlotStudioComboBox()
        self.x_minor_tick_direction_combo.addItems(["out", "in", "inout"])
        self.x_minor_tick_direction_combo.setToolTip("Direction of the minor tick marks")
        x_layout.addWidget(self.x_minor_tick_direction_combo)

        x_layout.addWidget(QLabel("X-axis Minor Tick Width"))
        self.x_minor_tick_width_spin = DataPlotStudioDoubleSpinBox()
        self.x_minor_tick_width_spin.setRange(0.1, 5.0)
        self.x_minor_tick_width_spin.setValue(0.5)
        self.x_minor_tick_width_spin.setSingleStep(0.1)
        self.x_minor_tick_width_spin.setToolTip("Width/thickness of minor tick marks")
        x_layout.addWidget(self.x_minor_tick_width_spin)

        x_layout.addWidget(QLabel("X Scale:"))
        self.x_scale_combo = DataPlotStudioComboBox()
        self.x_scale_combo.addItems(['linear', 'log', 'symlog'])
        x_layout.addWidget(self.x_scale_combo)

        x_layout.addSpacing(5)
        x_layout.addWidget(QLabel("X-axis Display Units:"))
        self.x_display_units_combo = DataPlotStudioComboBox()
        self.x_display_units_combo.addItems(["None", "Hundreds (100s)", "Thousands", "Millions", "Billions"])
        self.x_display_units_combo.setToolTip("Format axis labels to display in units")
        x_layout.addWidget(self.x_display_units_combo)
        
        x_layout.addStretch()
        self.axis_tab_widget.addTab(x_tab, "X-Axis")

        # Y-Axis
        y_tab = QWidget()
        y_layout = QVBoxLayout(y_tab)
        
        y_layout.addWidget(QLabel("Y-axis - Auto Limit:"))
        self.y_auto_check = DataPlotStudioToggleSwitch("Auto")
        self.y_auto_check.setChecked(True)
        y_layout.addWidget(self.y_auto_check)

        self.y_invert_axis_check = DataPlotStudioToggleSwitch("Invert Y-axis")
        self.y_invert_axis_check.setChecked(False)
        self.y_invert_axis_check.setToolTip("Reverses the direction of data on the y-axis")
        y_layout.addWidget(self.y_invert_axis_check)

        y_layout.addWidget(QLabel("Y Min:"))
        self.y_min_spin = DataPlotStudioDoubleSpinBox()
        self.y_min_spin.setRange(-1000000, 1000000)
        self.y_min_spin.setEnabled(False)
        y_layout.addWidget(self.y_min_spin)

        y_layout.addWidget(QLabel("Y Max:"))
        self.y_max_spin = DataPlotStudioDoubleSpinBox()
        self.y_max_spin.setRange(-1000000, 1000000)
        self.y_max_spin.setEnabled(False)
        y_layout.addWidget(self.y_max_spin)

        y_layout.addWidget(QLabel("Y-axis Tick Label Size:"))
        self.ytick_label_size_spin = DataPlotStudioSpinBox()
        self.ytick_label_size_spin.setRange(6, 20)
        self.ytick_label_size_spin.setValue(10)
        y_layout.addWidget(self.ytick_label_size_spin)

        y_layout.addWidget(QLabel("Y-axis Tick Rotation:"))
        self.ytick_rotation_spin = DataPlotStudioSpinBox()
        self.ytick_rotation_spin.setRange(-90, 90)
        self.ytick_rotation_spin.setValue(0)
        y_layout.addWidget(self.ytick_rotation_spin)

        y_layout.addWidget(QLabel("Max Number of Ticks"))
        self.y_max_ticks_spin = DataPlotStudioSpinBox()
        self.y_max_ticks_spin.setRange(3, 50)
        self.y_max_ticks_spin.setValue(10)
        self.y_max_ticks_spin.setToolTip("Maximum number of tick labels on the y-axis")
        y_layout.addWidget(self.y_max_ticks_spin)

        y_layout.addSpacing(5)
        
        self.y_show_minor_ticks_check = DataPlotStudioToggleSwitch("Show Y-axis Minor Ticks")
        self.y_show_minor_ticks_check.setChecked(False)
        self.y_show_minor_ticks_check.setToolTip("Display the minor tick marks and labels on yhe y-axis")
        y_layout.addWidget(self.y_show_minor_ticks_check)

        y_layout.addSpacing(5)

        y_layout.addWidget(QLabel("Y-axis Major Tick Direction:"))
        self.y_major_tick_direction_combo = DataPlotStudioComboBox()
        self.y_major_tick_direction_combo.addItems(["out", "in", "inout"])
        self.y_major_tick_direction_combo.setToolTip("Direction of the major tick marks on the Y-axis")
        y_layout.addWidget(self.y_major_tick_direction_combo)

        y_layout.addWidget(QLabel("Y-axis Major Tick Width:"))
        self.y_major_tick_width_spin = DataPlotStudioDoubleSpinBox()
        self.y_major_tick_width_spin.setRange(0.1, 5.0)
        self.y_major_tick_width_spin.setValue(1.0)
        self.y_major_tick_width_spin.setSingleStep(0.1)
        self.y_major_tick_width_spin.setToolTip("Width/thickness of the major tick marks")
        y_layout.addWidget(self.y_major_tick_width_spin)

        y_layout.addWidget(QLabel("Y-axis Minor Tick Direction"))
        self.y_minor_tick_direction_combo = DataPlotStudioComboBox()
        self.y_minor_tick_direction_combo.addItems(["out", "in", "inout"])
        self.y_minor_tick_direction_combo.setToolTip("Direction of the minor tick marks on the Y-axis")
        y_layout.addWidget(self.y_minor_tick_direction_combo)

        y_layout.addWidget(QLabel("Y-axis Minor Tick Width:"))
        self.y_minor_tick_width_spin = DataPlotStudioDoubleSpinBox()
        self.y_minor_tick_width_spin.setRange(0.1, 5.0)
        self.y_minor_tick_width_spin.setValue(0.5)
        self.y_minor_tick_width_spin.setSingleStep(0.1)
        self.y_minor_tick_width_spin.setToolTip("Width/thickness of minor tick marks")
        y_layout.addWidget(self.y_minor_tick_width_spin)

        y_layout.addWidget(QLabel("Y Scale:"))
        self.y_scale_combo = DataPlotStudioComboBox()
        self.y_scale_combo.addItems(['linear', 'log', 'symlog'])
        y_layout.addWidget(self.y_scale_combo)

        y_layout.addSpacing(5)
        y_layout.addWidget(QLabel("Y-axis Display Units"))
        self.y_display_units_combo = DataPlotStudioComboBox()
        self.y_display_units_combo.addItems(["None", "Hundreds (100s)", "Thousands", "Millions", "Billions"])
        self.y_display_units_combo.setToolTip("Format axis labels to display in units")
        y_layout.addWidget(self.y_display_units_combo)
        
        y_layout.addStretch()
        self.axis_tab_widget.addTab(y_tab, "Y-Axis")
        
        # Z-Axis
        self.z_tab = QWidget()
        z_layout = QVBoxLayout(self.z_tab)
        
        z_layout.addWidget(QLabel("Z-axis - Auto Limit:"))
        self.z_auto_check = DataPlotStudioToggleSwitch("Auto")
        self.z_auto_check.setChecked(True)
        z_layout.addWidget(self.z_auto_check)

        self.z_invert_axis_check = DataPlotStudioToggleSwitch("Invert Z-axis")
        self.z_invert_axis_check.setChecked(False)
        self.z_invert_axis_check.setToolTip("Reverses the direction of data on the z-axis")
        z_layout.addWidget(self.z_invert_axis_check)

        z_layout.addWidget(QLabel("Z Min:"))
        self.z_min_spin = DataPlotStudioDoubleSpinBox()
        self.z_min_spin.setRange(-1000000, 1000000)
        self.z_min_spin.setEnabled(False)
        z_layout.addWidget(self.z_min_spin)

        z_layout.addWidget(QLabel("Z Max:"))
        self.z_max_spin = DataPlotStudioDoubleSpinBox()
        self.z_max_spin.setRange(-1000000, 1000000)
        self.z_max_spin.setEnabled(False)
        z_layout.addWidget(self.z_max_spin)

        z_layout.addWidget(QLabel("Z-axis Tick Label Size:"))
        self.ztick_label_size_spin = DataPlotStudioSpinBox()
        self.ztick_label_size_spin.setRange(6, 20)
        self.ztick_label_size_spin.setValue(10)
        z_layout.addWidget(self.ztick_label_size_spin)

        z_layout.addWidget(QLabel("Z-axis Tick Rotation:"))
        self.ztick_rotation_spin = DataPlotStudioSpinBox()
        self.ztick_rotation_spin.setRange(-90, 90)
        self.ztick_rotation_spin.setValue(0)
        z_layout.addWidget(self.ztick_rotation_spin)

        z_layout.addWidget(QLabel("Max Number of Ticks"))
        self.z_max_ticks_spin = DataPlotStudioSpinBox()
        self.z_max_ticks_spin.setRange(3, 50)
        self.z_max_ticks_spin.setValue(10)
        self.z_max_ticks_spin.setToolTip("Maximum number of tick labels on the z-axis")
        z_layout.addWidget(self.z_max_ticks_spin)

        z_layout.addSpacing(5)
        
        self.z_show_minor_ticks_check = DataPlotStudioToggleSwitch("Show Z-axis Minor Ticks")
        self.z_show_minor_ticks_check.setChecked(False)
        self.z_show_minor_ticks_check.setToolTip("Display the minor tick marks and labels on the z-axis")
        z_layout.addWidget(self.z_show_minor_ticks_check)

        z_layout.addSpacing(5)

        z_layout.addWidget(QLabel("Z-axis Major Tick Direction:"))
        self.z_major_tick_direction_combo = DataPlotStudioComboBox()
        self.z_major_tick_direction_combo.addItems(["out", "in", "inout"])
        self.z_major_tick_direction_combo.setToolTip("Direction of the major tick marks on the Z-axis")
        z_layout.addWidget(self.z_major_tick_direction_combo)

        z_layout.addWidget(QLabel("Z-axis Major Tick Width:"))
        self.z_major_tick_width_spin = DataPlotStudioDoubleSpinBox()
        self.z_major_tick_width_spin.setRange(0.1, 5.0)
        self.z_major_tick_width_spin.setValue(1.0)
        self.z_major_tick_width_spin.setSingleStep(0.1)
        self.z_major_tick_width_spin.setToolTip("Width/thickness of the major tick marks")
        z_layout.addWidget(self.z_major_tick_width_spin)

        z_layout.addWidget(QLabel("Z-axis Minor Tick Direction"))
        self.z_minor_tick_direction_combo = DataPlotStudioComboBox()
        self.z_minor_tick_direction_combo.addItems(["out", "in", "inout"])
        self.z_minor_tick_direction_combo.setToolTip("Direction of the minor tick marks on the Z-axis")
        z_layout.addWidget(self.z_minor_tick_direction_combo)

        z_layout.addWidget(QLabel("Z-axis Minor Tick Width:"))
        self.z_minor_tick_width_spin = DataPlotStudioDoubleSpinBox()
        self.z_minor_tick_width_spin.setRange(0.1, 5.0)
        self.z_minor_tick_width_spin.setValue(0.5)
        self.z_minor_tick_width_spin.setSingleStep(0.1)
        self.z_minor_tick_width_spin.setToolTip("Width/thickness of minor tick marks")
        z_layout.addWidget(self.z_minor_tick_width_spin)

        z_layout.addWidget(QLabel("Z Scale:"))
        self.z_scale_combo = DataPlotStudioComboBox()
        self.z_scale_combo.addItems(['linear', 'log', 'symlog'])
        z_layout.addWidget(self.z_scale_combo)

        z_layout.addSpacing(5)
        z_layout.addWidget(QLabel("Z-axis Display Units"))
        self.z_display_units_combo = DataPlotStudioComboBox()
        self.z_display_units_combo.addItems(["None", "Hundreds (100s)", "Thousands", "Millions", "Billions"])
        self.z_display_units_combo.setToolTip("Format axis labels to display in units")
        z_layout.addWidget(self.z_display_units_combo)
        
        z_layout.addStretch()

        layout.addWidget(self.axis_tab_widget)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _setup_axis_orientation_group(self, parent_layout: QVBoxLayout) -> None:
        group = DataPlotStudioGroupBox("Axis Orientation")
        layout = QVBoxLayout()

        self.flip_axes_check = DataPlotStudioToggleSwitch("Flip Axis (Swap X and Y axis)")
        self.flip_axes_check.setChecked(False)
        layout.addWidget(self.flip_axes_check)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _setup_datetime_formatting_group(self, parent_layout: QVBoxLayout) -> None:
        group = DataPlotStudioGroupBox("DateTime Formatting")
        layout = QVBoxLayout()

        self.custom_datetime_check = DataPlotStudioToggleSwitch("Enable Custom formatting of DateTime Axis")
        self.custom_datetime_check.setChecked(False)
        layout.addWidget(self.custom_datetime_check)

        self.datetime_tab_widget = QTabWidget()
        self.datetime_tab_widget.setVisible(False)
        self.datetime_tab_widget.setMinimumHeight(160)
        
        self.custom_datetime_check.toggled.connect(self.datetime_tab_widget.setVisible)

        # X-Axis DateTime 
        x_tab = QWidget()
        x_layout = QVBoxLayout(x_tab)
        
        self.format_x_datetime_label = QLabel("Format:")
        x_layout.addWidget(self.format_x_datetime_label)
        
        self.x_datetime_format_combo = DataPlotStudioComboBox()
        self.x_datetime_format_combo.setMinimumHeight(20)
        self._populate_datetime_combo(self.x_datetime_format_combo)
        x_layout.addWidget(self.x_datetime_format_combo)
        
        x_layout.addSpacing(5)

        self.custom_x_axis_format_label = QLabel("Custom Format String:")
        x_layout.addWidget(self.custom_x_axis_format_label)
        
        self.x_custom_datetime_input = DataPlotStudioLineEdit()
        self.x_custom_datetime_input.setMinimumHeight(20)
        self.x_custom_datetime_input.setPlaceholderText("e.g. %d/%m/%Y %H:%M")
        self._apply_datetime_tooltip(self.x_custom_datetime_input)
        x_layout.addWidget(self.x_custom_datetime_input)
        
        x_layout.addStretch()
        self.datetime_tab_widget.addTab(x_tab, "X-Axis")

        #Y-Axis DateTime Tab
        y_tab = QWidget()
        y_layout = QVBoxLayout(y_tab)
        
        self.format_y_datetime_label = QLabel("Format:")
        y_layout.addWidget(self.format_y_datetime_label)
        
        self.y_datetime_format_combo = DataPlotStudioComboBox()
        self.y_datetime_format_combo.setMinimumHeight(20)
        self._populate_datetime_combo(self.y_datetime_format_combo)
        y_layout.addWidget(self.y_datetime_format_combo)
        
        y_layout.addSpacing(5)

        self.custom_y_axis_format_label = QLabel("Custom Format String:")
        y_layout.addWidget(self.custom_y_axis_format_label)
        
        self.y_custom_datetime_format_input = DataPlotStudioLineEdit()
        self.y_custom_datetime_format_input.setMinimumHeight(20)
        self.y_custom_datetime_format_input.setPlaceholderText("e.g. %d/%m/%Y %H:%M")
        self._apply_datetime_tooltip(self.y_custom_datetime_format_input)
        y_layout.addWidget(self.y_custom_datetime_format_input)
        
        y_layout.addStretch()
        self.datetime_tab_widget.addTab(y_tab, "Y-Axis")

        layout.addWidget(self.datetime_tab_widget)

        # Format Help
        self.format_help = QLabel(
            "<b>Common Format Codes:</b><br>"
            "<font size='2'>"
            "%Y = 2024 (4-digit year)<br>"
            "%y = 24 (2-digit year)<br>"
            "%m = 01-12 (month)<br>"
            "%d = 01-31 (day)<br>"
            "%H = 00-23 (hour 24h)<br>"
            "%I = 01-12 (hour 12h)<br>"
            "%M = 00-59 (minute)<br>"
            "%S = 00-59 (second)<br>"
            "%p = AM/PM<br>"
            "%b = Jan, Feb... (short month)<br>"
            "%B = January, February... (full month)<br>"
            "%a = Mon, Tue... (short day)<br>"
            "%A = Monday, Tuesday... (full day)"
            "</font>"
        )
        self.format_help.setVisible(False)
        self.format_help.setWordWrap(True)
        self.format_help.setProperty("styleClass", "help_box")
        layout.addWidget(self.format_help)
        self.custom_datetime_check.toggled.connect(self.format_help.setVisible)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _populate_datetime_combo(self, combo: DataPlotStudioComboBox) -> None:
        """Helper to append standardized datetime formats to combos"""
        combo.addItems([
            "Auto",
            "%Y-%m-%d (2024-01-15)",
            "%d/%m/%Y (15/01/2024)",
            "%m/%d/%Y (01/15/2024)",
            "%Y/%m/%d (2024/01/15)",
            "%d-%m-%Y (15-01-2024)",
            "%d/%m/%y (15/01/24)",
            "%m/%d/%y (01/15/24)",
            "%b %d, %Y (Jan 15, 2024)",
            "%d %b %Y (15 Jan 2024)",
            "%B %d, %Y (January 15, 2024)",
            "%Y-%m-%d %H:%M (2024-01-15 14:30)",
            "%d/%m/%Y %H:%M (15/01/2024 14:30)",
            "%Y-%m-%d %H:%M:%S (2024-01-15 14:30:45)",
            "%H:%M (14:30)",
            "%H:%M:%S (14:30:45)",
            "%I:%M %p (02:30 PM)",
            "%Y-W%W (2024-W03)",
            "%Y-Q%q (2024-Q1)",
            "Custom"
        ])

    def _apply_datetime_tooltip(self, widget: DataPlotStudioLineEdit) -> None:
        """Helper to append standardized tooltip helper to text fields"""
        widget.setToolTip(
            "Use strftime format codes:\n"
            "%Y = Year (4-digit), %y = Year (2-digit)\n"
            "%m = Month (01-12), %B = Month name, %b = Short month\n"
            "%d = Day (01-31)\n"
            "%H = Hour (00-23), %I = Hour (01-12)\n"
            "%M = Minute (00-59), %S = Second (00-59)\n"
            "%p = AM/PM\n"
            "%A = Weekday name, %a = Short weekday\n"
            "%W = Week number"
        )