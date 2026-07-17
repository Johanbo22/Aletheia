from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QFrame, QGroupBox, QHBoxLayout, QLabel, QListWidget, QPushButton, QScrollArea, \
    QTabWidget, QToolBox, QVBoxLayout, QWidget

from ui.widgets import AutoResizingStackedWidget, QuickFilterEdit, ToggleSwitch

class GeneralSettingsTab(QWidget):
    help_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setProperty("styleClass", "transparent_scroll_area")

        scroll_widget = QWidget()
        scroll_widget.setObjectName("TransparentScrollContent")
        scroll_layout = QVBoxLayout(scroll_widget)

        self._setup_plot_type_group(scroll_layout)
        self._setup_subplot_group(scroll_layout)
        scroll_layout.addSpacing(10)
        self._setup_data_configuration_group(scroll_layout)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

    def _setup_plot_type_group(self, parent_layout: QVBoxLayout) -> None:
        self.plot_type_group = QGroupBox("Plot Type")
        layout = QVBoxLayout()

        self.current_plot_label = QLabel("Selected Plot: None")
        self.current_plot_label.setProperty("styleClass", "section_header")
        layout.addWidget(self.current_plot_label)

        self.plot_type = QToolBox()
        self.plot_type.setObjectName("plot_type_toolbox")
        self.plot_type.setMinimumHeight(350)
        layout.addWidget(self.plot_type)

        self.add_subplots_check = ToggleSwitch("Add subplots")
        self.add_subplots_check.setToolTip("Add additional axes to the figure to create multiple plots.")
        self.add_subplots_check.setChecked(False)
        layout.addWidget(self.add_subplots_check)

        self.use_subset_check = ToggleSwitch("Use Subset")
        self.use_subset_check.setToolTip("Toggle this to allow the engine to render data from your configured subsets.")
        self.use_subset_check.setChecked(False)
        layout.addWidget(self.use_subset_check)

        self.plot_type_group.setLayout(layout)
        parent_layout.addWidget(self.plot_type_group)

    def _setup_subplot_group(self, parent_layout: QVBoxLayout) -> None:
        self.subplot_group = QGroupBox("Subplot Configuration")
        self.subplot_group.setVisible(False)
        layout = QVBoxLayout()

        info = QLabel(
            "Design your subplot layout here. For a simple grid, just change the rows/columns.\n"
            "To create complex dashboard layouts, select multiple cells and click 'Merge Cells'."
        )
        info.setProperty("styleClass", "info_text")
        info.setWordWrap(True)
        layout.addWidget(info)

        from ui.widgets.GridSpecDesigner import GridSpecDesignerWidget
        self.grid_designer = GridSpecDesignerWidget(self)
        layout.addWidget(self.grid_designer)

        share_layout = QHBoxLayout()
        self.subplot_sharex_check = ToggleSwitch("Share X-axis")
        self.subplot_sharex_check.setToolTip("Toggle this to have the top rows share the X-axis with the bottom rows.")
        share_layout.addWidget(self.subplot_sharex_check)

        self.subplot_sharey_check = ToggleSwitch("Share Y-axis")
        self.subplot_sharey_check.setToolTip(
            "Toggle this to have the right most columns share the Y-axis with the left most columns")
        share_layout.addWidget(self.subplot_sharey_check)
        layout.addLayout(share_layout)

        self.subplot_sharex_check.toggled.connect(self._sync_grid_axes)
        self.subplot_sharey_check.toggled.connect(self._sync_grid_axes)

        active_layout = QHBoxLayout()
        active_layout.addWidget(QLabel("Active Subplot:"))
        self.active_subplot_combo = QComboBox()
        self.active_subplot_combo.setToolTip(
            "Click the plot to be the current active subplot.\nRefer to the configuration above to determine the plot number.")
        self.active_subplot_combo.addItem("Plot 1")
        active_layout.addWidget(self.active_subplot_combo, 1)
        layout.addLayout(active_layout)

        self.freeze_data_check = ToggleSwitch("Freeze Data Selection for Subplots")
        self.freeze_data_check.setToolTip("Toggle to freeze the data selection for the current active subplot.")
        layout.addWidget(self.freeze_data_check)

        self.subplot_group.setLayout(layout)
        parent_layout.addWidget(self.subplot_group)

        self.add_subplots_check.toggled.connect(self.subplot_group.setVisible)

    def _sync_grid_axes(self, *args) -> None:
        """Passes the active toggle states down to the visual designer widget."""
        if hasattr(self, 'grid_designer'):
            sharex = self.subplot_sharex_check.isChecked()
            sharey = self.subplot_sharey_check.isChecked()
            self.grid_designer.set_shared_axes(sharex, sharey)

    def _setup_data_configuration_group(self, parent_layout: QVBoxLayout) -> None:
        group = QGroupBox("Data Configuration")
        layout = QVBoxLayout()

        tab_widget = QTabWidget()
        tab_widget.setMinimumHeight(320)

        var_tab = QWidget()
        var_layout = QVBoxLayout(var_tab)

        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("X Column:"))
        self.x_column = QComboBox()
        self.x_column.setToolTip("Select the column to be the X-axis values")
        x_layout.addWidget(self.x_column, 1)
        var_layout.addLayout(x_layout)

        var_layout.addWidget(QLabel("Y Column(s):"))

        y_toggles_layout = QHBoxLayout()
        y_toggles_layout.setContentsMargins(0, 0, 0, 0)
        self.multi_y_check = ToggleSwitch("Multiple Y Columns")
        self.multi_y_check.setToolTip("Toggle this to have multiple Y-axis values rendered on the plot")
        self.stacked_bars_check = ToggleSwitch("Stack (Bar/Area)")
        self.stacked_bars_check.setToolTip("Toggle to render a single bar chart with multiple values per bar")
        y_toggles_layout.addWidget(self.multi_y_check)
        y_toggles_layout.addWidget(self.stacked_bars_check)
        y_toggles_layout.addStretch()
        var_layout.addLayout(y_toggles_layout)

        self.y_stack = AutoResizingStackedWidget()

        self.y_column = QComboBox()
        self.y_column.setToolTip("Select the column to be the Y-axis values")
        self.y_stack.addWidget(self.y_column)

        self.y_columns_list = QListWidget()
        self.y_columns_list.setToolTip("Select the columns to be the Y-axis values")
        self.y_columns_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.y_columns_list.setMinimumHeight(100)
        self.y_columns_list.setVisible(False)
        self.y_stack.addWidget(self.y_columns_list)

        var_layout.addWidget(self.y_stack)

        multi_btns = QHBoxLayout()
        multi_btns.setContentsMargins(0, 0, 0, 0)

        self.multi_y_info = QLabel("Tip: Hold Ctrl/Cmd")
        self.multi_y_info.setProperty("styleClass", "muted_text")
        self.multi_y_info.setVisible(False)
        multi_btns.addWidget(self.multi_y_info)

        multi_btns.addStretch()

        self.select_all_y_btn = QPushButton("Select All", parent=self)
        self.select_all_y_btn.setToolTip("Select all available columns as Y-axis values")
        self.select_all_y_btn.setVisible(False)
        self.clear_all_y_btn = QPushButton("Clear All", parent=self)
        self.clear_all_y_btn.setToolTip("Deselect all selected columns as Y-axis values.")
        self.clear_all_y_btn.setMinimumHeight(28)
        self.clear_all_y_btn.setVisible(False)
        multi_btns.addWidget(self.select_all_y_btn)
        multi_btns.addWidget(self.clear_all_y_btn)
        var_layout.addLayout(multi_btns)

        self.multi_y_check.toggled.connect(self._on_multi_y_toggled)

        self.z_column_widget = QWidget()
        z_layout = QHBoxLayout(self.z_column_widget)
        z_layout.setContentsMargins(0, 0, 0, 0)
        z_layout.addWidget(QLabel("Z Column:"))
        self.z_column = QComboBox()
        self.z_column.setToolTip("Selec the column to be the Z-axis values")
        z_layout.addWidget(self.z_column, 1)
        var_layout.addWidget(self.z_column_widget)
        self.z_column_widget.setVisible(False)

        var_layout.addWidget(QLabel("Hue/Group:"))
        self.hue_column = QComboBox()
        self.hue_column.setToolTip("Select the column to color based on the value of another column")
        self.hue_column.addItem("None")
        var_layout.addWidget(self.hue_column)

        var_layout.addStretch()
        tab_widget.addTab(var_tab, "Variables")

        sec_tab = QWidget()
        sec_layout = QVBoxLayout(sec_tab)

        self.secondary_y_check = ToggleSwitch("Enable Secondary Y-Axis")
        self.secondary_y_check.setToolTip("Enable a secondary Y-axis")
        sec_layout.addWidget(self.secondary_y_check)

        sec_layout.addWidget(QLabel("Secondary Y Column:"))
        self.secondary_y_column = QComboBox()
        self.secondary_y_column.setToolTip("Select the column to be rendered on the secondary Y-axis")
        self.secondary_y_column.setEnabled(False)
        sec_layout.addWidget(self.secondary_y_column)

        sec_layout.addWidget(QLabel("Secondary Plot Type:"))
        self.secondary_plot_type_combo = QComboBox()
        self.secondary_plot_type_combo.setToolTip("Select the plot type to which the secondary Y-axis should have.")
        self.secondary_plot_type_combo.setEnabled(False)
        self.secondary_plot_type_combo.addItems(["Line", "Scatter", "Bar", "Area"])
        sec_layout.addWidget(self.secondary_plot_type_combo)

        self.secondary_y_check.toggled.connect(self.secondary_y_column.setEnabled)
        self.secondary_y_check.toggled.connect(self.secondary_plot_type_combo.setEnabled)

        sec_layout.addStretch()
        tab_widget.addTab(sec_tab, "Secondary Axis")

        filter_tab = QWidget()
        filter_layout = QVBoxLayout(filter_tab)

        filter_layout.addWidget(QLabel("Quick Filter:"))
        self.quick_filter_input = QuickFilterEdit()
        self.quick_filter_input.setToolTip(
            "Provide a query to filter your the plotted data without changing the dataset")
        self.quick_filter_input.setPlaceholderText("e.g. value > 100 or category == 'A'")
        filter_layout.addWidget(self.quick_filter_input)

        filter_layout.addSpacing(10)

        subset_info = QLabel("Plot a specific subset of your data. Enable 'Use Subset' in the Plot Type group above.")
        subset_info.setWordWrap(True)
        subset_info.setProperty("styleClass", "info_text")
        filter_layout.addWidget(subset_info)

        self.subset_combo = QComboBox()
        self.subset_combo.setToolTip(
            "If you have created subsets of your data, you can enable the engine to use a subset instead of your entire dataset")
        self.subset_combo.addItem("(Full Dataset)")
        self.subset_combo.setEnabled(False)
        filter_layout.addWidget(self.subset_combo)

        self.use_subset_check.stateChanged.connect(self.subset_combo.setEnabled)

        self.refresh_subsets_btn = QPushButton("Refresh Subset List", parent=self)
        self.refresh_subsets_btn.setToolTip("Click to refresh the list of available subsets")
        filter_layout.addWidget(self.refresh_subsets_btn)

        filter_layout.addStretch()
        tab_widget.addTab(filter_tab, "Filters and Subsets")

        layout.addWidget(tab_widget)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _on_multi_y_toggled(self, is_multi: bool) -> None:
        self.y_stack.setCurrentIndex(1 if is_multi else 0)
        self.select_all_y_btn.setVisible(is_multi)
        self.clear_all_y_btn.setVisible(is_multi)
        self.multi_y_info.setVisible(is_multi)
