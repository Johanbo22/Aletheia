from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QToolBox, QFrame, QTabWidget, QListWidget, QGroupBox, QComboBox, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal

from ui.widgets import ToggleSwitch, QuickFilterEdit

class GeneralSettingsTab(QWidget):
    help_requested = pyqtSignal(str)
    
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        
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
        self.add_subplots_check.setChecked(False)
        layout.addWidget(self.add_subplots_check)

        self.use_subset_check = ToggleSwitch("Use Subset")
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
        share_layout.addWidget(self.subplot_sharex_check)

        self.subplot_sharey_check = ToggleSwitch("Share Y-axis")
        share_layout.addWidget(self.subplot_sharey_check)
        layout.addLayout(share_layout)
        
        self.subplot_sharex_check.toggled.connect(self._sync_grid_axes)
        self.subplot_sharey_check.toggled.connect(self._sync_grid_axes)

        active_layout = QHBoxLayout()
        active_layout.addWidget(QLabel("Active Subplot:"))
        self.active_subplot_combo = QComboBox()
        self.active_subplot_combo.addItem("Plot 1")
        active_layout.addWidget(self.active_subplot_combo, 1)
        layout.addLayout(active_layout)

        self.freeze_data_check = ToggleSwitch("Freeze Data Selection for Subplots")
        layout.addWidget(self.freeze_data_check)

        self.subplot_group.setLayout(layout)
        parent_layout.addWidget(self.subplot_group)
    
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
        x_layout.addWidget(self.x_column, 1)
        var_layout.addLayout(x_layout)

        y_lbl_layout = QHBoxLayout()
        y_lbl_layout.addWidget(QLabel("Y Column(s):"))
        y_lbl_layout.addStretch()
        self.multi_y_check = ToggleSwitch("Multiple Y Columns")
        y_lbl_layout.addWidget(self.multi_y_check)
        var_layout.addLayout(y_lbl_layout)

        self.y_column = QComboBox()
        var_layout.addWidget(self.y_column)

        self.y_columns_list = QListWidget()
        self.y_columns_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.y_columns_list.setMaximumHeight(100)
        self.y_columns_list.setVisible(False)
        var_layout.addWidget(self.y_columns_list)

        multi_btns = QHBoxLayout()
        self.select_all_y_btn = QPushButton("Select All", parent=self)
        self.select_all_y_btn.setVisible(False)
        self.clear_all_y_btn = QPushButton("Clear All", parent=self)
        self.clear_all_y_btn.setMinimumHeight(28)
        self.clear_all_y_btn.setVisible(False)
        multi_btns.addWidget(self.select_all_y_btn)
        multi_btns.addWidget(self.clear_all_y_btn)
        var_layout.addLayout(multi_btns)

        self.multi_y_info = QLabel("Tip: Hold Ctrl/Cmd to select multiple columns")
        self.multi_y_info.setProperty("styleClass", "muted_text")
        self.multi_y_info.setVisible(False)
        var_layout.addWidget(self.multi_y_info)
        
        self.z_column_widget = QWidget()
        z_layout = QHBoxLayout(self.z_column_widget)
        z_layout.setContentsMargins(0, 0, 0, 0)
        z_layout.addWidget(QLabel("Z Column:"))
        self.z_column = QComboBox()
        z_layout.addWidget(self.z_column, 1)
        var_layout.addWidget(self.z_column_widget)
        self.z_column_widget.setVisible(False)

        var_layout.addWidget(QLabel("Hue/Group:"))
        self.hue_column = QComboBox()
        self.hue_column.addItem("None")
        var_layout.addWidget(self.hue_column)
        
        var_layout.addStretch()
        tab_widget.addTab(var_tab, "Variables")

        sec_tab = QWidget()
        sec_layout = QVBoxLayout(sec_tab)
        
        self.secondary_y_check = ToggleSwitch("Enable Secondary Y-Axis")
        sec_layout.addWidget(self.secondary_y_check)
        
        sec_layout.addWidget(QLabel("Secondary Y Column:"))
        self.secondary_y_column = QComboBox()
        self.secondary_y_column.setEnabled(False)
        sec_layout.addWidget(self.secondary_y_column)

        sec_layout.addWidget(QLabel("Secondary Plot Type:"))
        self.secondary_plot_type_combo = QComboBox()
        self.secondary_plot_type_combo.setEnabled(False)
        self.secondary_plot_type_combo.addItems(["Line", "Scatter", "Bar", "Area"])
        sec_layout.addWidget(self.secondary_plot_type_combo)
        
        sec_layout.addStretch()
        tab_widget.addTab(sec_tab, "Secondary Axis")

        filter_tab = QWidget()
        filter_layout = QVBoxLayout(filter_tab)
        
        filter_layout.addWidget(QLabel("Quick Filter:"))
        self.quick_filter_input = QuickFilterEdit()
        self.quick_filter_input.setPlaceholderText("e.g. value > 100 or category == 'A'")
        filter_layout.addWidget(self.quick_filter_input)
        
        filter_layout.addSpacing(10)
        
        subset_info = QLabel("Plot a specific subset of your data. Enable 'Use Subset' in the Plot Type group above.")
        subset_info.setWordWrap(True)
        subset_info.setProperty("styleClass", "info_text")
        filter_layout.addWidget(subset_info)

        self.subset_combo = QComboBox()
        self.subset_combo.addItem("(Full Dataset)")
        self.subset_combo.setEnabled(False)
        filter_layout.addWidget(self.subset_combo)

        self.use_subset_check.stateChanged.connect(
            lambda state: self.subset_combo.setEnabled(state == Qt.CheckState.Checked.value)
        )

        self.refresh_subsets_btn = QPushButton("Refresh Subset List", parent=self)
        filter_layout.addWidget(self.refresh_subsets_btn)
        
        filter_layout.addStretch()
        tab_widget.addTab(filter_tab, "Filters and Subsets")

        layout.addWidget(tab_widget)
        group.setLayout(layout)
        parent_layout.addWidget(group)