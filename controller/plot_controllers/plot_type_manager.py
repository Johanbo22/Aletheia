import threading
from typing import Dict, List, TYPE_CHECKING

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QListWidget, QListWidgetItem

from core.resource_loader import get_resource_path

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab

class PlotTypeManager:
    """
    Controller responsible for managing the plot type selection toolbox
    and controlling the UI visibility based on the selected plot type.
    """

    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab
        self.view = plot_tab.view
        self.plot_engine = plot_tab.plot_engine
        self.status_bar = plot_tab.status_bar

        self.plot_categories: Dict[str, List[str]] = {
            "Basic and Relational": ["Line", "Scatter", "Bar", "Area", "Pie", "Stem", "Stairs"],
            "Distribution"        : ["Histogram", "Box", "Violin", "KDE", "ECDF", "Count Plot", "Eventplot"],
            "2D and Gridded": ["Heatmap", "Hexbin", "2D Density", "2D Histogram", "Image Show (imshow)",
                                     "pcolormesh", "Contour", "Contourf", "Stackplot"],
            "Vector Fields"       : ["Barbs", "Quiver", "Streamplot"],
            "Triangulation"       : ["Tricontour", "Tricontourf", "Tripcolor", "Triplot"],
            "3D"                  : ["3D Line", "3D Scatter", "3D Surface"],
            "Geospatial"          : ["GeoSpatial"]
        }
        self.category_lists: List[QListWidget] = []

    def populate_plot_toolbox(self) -> None:
        """Populates the side toolbox with available plot types grouped by category"""
        while self.view.plot_type.count() > 0:
            self.view.plot_type.removeItem(0)

        self.category_lists.clear()
        for category, plot_names in self.plot_categories.items():
            list_widget = QListWidget()
            list_widget.setViewMode(QListWidget.ViewMode.IconMode)
            list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
            list_widget.setMovement(QListWidget.Movement.Static)

            list_widget.setGridSize(QSize(105, 105))
            list_widget.setSpacing(8)
            list_widget.setIconSize(QSize(48, 48))

            list_widget.itemClicked.connect(self.on_plot_list_item_clicked)

            for plot_name in plot_names:
                if plot_name in self.plot_engine.AVAILABLE_PLOTS:
                    icon_key = self.plot_engine.AVAILABLE_PLOTS[plot_name]
                    icon_path = get_resource_path(f"icons/plot_tab/plots/{icon_key}.png")

                    item = QListWidgetItem(QIcon(icon_path), plot_name)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    item.setToolTip(self.plot_engine.PLOT_DESCRIPTIONS.get(plot_name, ""))
                    list_widget.addItem(item)
            self.view.plot_type.addItem(list_widget, category)
            self.category_lists.append(list_widget)

    def on_plot_list_item_clicked(self, item: QListWidgetItem) -> None:
        """Slot to handle plot type selection from the toolbox list"""
        if not item:
            return

        plot_type = item.text()
        self.plot_tab.current_plot_type_name = plot_type
        self.view.current_plot_label.setText(f"Selected Plot: {plot_type}")

        for list_w in self.category_lists:
            if list_w != item.listWidget():
                list_w.clearSelection()

        self._on_plot_type_changed(plot_type)
        self.plot_tab.on_data_changed()
        self.plot_tab.script_manager.sync_script_if_open()

    def select_plot_in_toolbox(self, plot_type_name: str, log: bool = True) -> None:
        """Select a plot type in the toolbox"""
        self.plot_tab.current_plot_type_name = plot_type_name
        self.view.current_plot_label.setText(f"Selected Plot: {plot_type_name}")

        for i, (category, names) in enumerate(self.plot_categories.items()):
            if plot_type_name in names:
                self.view.plot_type.setCurrentIndex(i)
                list_widget = self.category_lists[i]

                items = list_widget.findItems(plot_type_name, Qt.MatchFlag.MatchExactly)
                if items:
                    list_widget.setCurrentItem(items[0])
                    for list_w in self.category_lists:
                        if list_w != list_widget:
                            list_w.clearSelection()
                    self._on_plot_type_changed(plot_type_name, log=log)
                    self.plot_tab.on_data_changed()
                    self.plot_tab.script_manager.sync_script_if_open()
                break

    def _on_plot_type_changed(self, plot_type: str, log: bool = True) -> None:
        """Adjusts the UI configurations when switching to a new plot type"""
        if log:
            self.status_bar.log(f"Plot type changed to: {plot_type}")

        custom_tabs = self.view.custom_tabs
        for i in range(custom_tabs.count()):
            if "geo" in custom_tabs.tabText(i).lower():
                custom_tabs.setTabVisible(i, plot_type == "GeoSpatial")
                break

        if plot_type == "GeoSpatial":
            def _pre_import_geo_deps():
                try:
                    import mapclassify
                    import contextily
                except ImportError:
                    pass

            threading.Thread(target=_pre_import_geo_deps, daemon=True).start()

        self.update_customization_visibility(plot_type)

        stacked_supported = ["Bar", "Area"]
        self.view.basic_tab.stacked_bars_check.setVisible(plot_type in stacked_supported)
        if plot_type not in stacked_supported:
            self.view.basic_tab.stacked_bars_check.setChecked(False)

        multi_y_supported = [
            "Line", "Bar", "Area", "Box", "Stackplot", "Eventplot", "Contour",
            "Contourf", "Barbs", "Quiver", "Streamplot", "Tricontour",
            "Tricontourf", "Tripcolor", "Triplot"
        ]
        if plot_type in multi_y_supported:
            self.view.multi_y_check.setEnabled(True)
            self.view.multi_y_check.setToolTip("")
        else:
            self.view.multi_y_check.setEnabled(False)
            self.view.multi_y_check.setChecked(False)
            self.view.multi_y_check.setToolTip(f"{plot_type} plots do not support multiple y columns")

        dual_axis_supported = ["Line", "Bar", "Scatter", "Area"]
        if plot_type in dual_axis_supported:
            self.view.secondary_y_check.setEnabled(True)
        else:
            self.view.secondary_y_check.setChecked(False)
            self.view.secondary_y_check.setEnabled(False)

        plots_without_hue = [
            "Pie", "KDE", "Count Plot", "Stackplot", "Eventplot",
            "Image Show (imshow)", "pcolormesh", "Contour", "Contourf", "Tricontour",
            "Tricontourf", "Tripcolor", "Triplot", "2D Histogram", "ECDF", "Stairs", "Stem",
            "Barbs", "Quiver", "Streamplot", "GeoSpatial"
        ]
        self.view.hue_column.setEnabled(plot_type not in plots_without_hue)
        if plot_type in plots_without_hue:
            self.view.hue_column.setCurrentIndex(0)

        incompatible_plots = [
            "Histogram", "Pie", "Heatmap", "KDE", "Stackplot",
            "Image Show (imshow)", "pcolormesh", "Contour", "Contourf", "Barbs", "Quiver",
            "Streamplot", "Tricontour", "Tricontourf", "Tripcolor", "Triplot", "2D Histogram",
            "ECDF", "GeoSpatial", "3D Scatter", "3D Line", "3D Surface"
        ]
        self.view.flip_axes_check.setEnabled(plot_type not in incompatible_plots)
        if plot_type in incompatible_plots:
            self.view.flip_axes_check.setChecked(False)

    def update_customization_visibility(self, primary_plot_type: str) -> None:
        """Toggles visibility of customization tabs and input parameters."""
        line_plots = ["Line", "Area", "Step", "Stairs", "3D Line", "KDE"]
        bar_plots = ["Bar", "Count Plot", "Stem"]
        hist_plots = ["Histogram", "Box", "Violin"]
        scatter_plots = ["Scatter", "3D Scatter"]
        pie_plots = ["Pie"]

        active_plot_types = [primary_plot_type]

        if self.view.secondary_y_check.isChecked() and self.view.secondary_y_check.isEnabled():
            active_plot_types.append(self.view.secondary_plot_type_combo.currentText())

        show_line = False
        show_bar_hist = False
        show_scatter = False
        show_pie = False
        show_markers = False
        show_error_bars = False

        for p_type in active_plot_types:
            if p_type in line_plots:
                show_line = True
                show_markers = True
                if p_type != "3D Line":
                    show_error_bars = True
            elif p_type in hist_plots:
                show_bar_hist = True
                if p_type == "Histogram":
                    show_line = True
                if p_type in ["Box", "Violin"]:
                    show_error_bars = True
            elif p_type in bar_plots:
                show_bar_hist = True
                show_error_bars = True
            elif p_type in scatter_plots:
                show_scatter = True
                show_markers = True
                if p_type != "3D Scatter":
                    show_error_bars = True
            elif p_type in pie_plots:
                show_pie = True

        self.view.page_line.setVisible(show_line)
        self.view.page_bar_hist.setVisible(show_bar_hist)
        self.view.page_scatter.setVisible(show_scatter)
        self.view.page_pie.setVisible(show_pie)
        self.view.page_empty.setVisible(not any([show_line, show_bar_hist, show_scatter, show_pie]))

        self.view.marker_group.setVisible(show_markers)
        self.view.error_bars_group.setVisible(show_error_bars)

        bar_width_supported = any(p in bar_plots for p in active_plot_types)
        if bar_width_supported:
            self.view.bar_width_spin.setEnabled(True)
            self.view.bar_width_spin.setToolTip(
                "Set the width the bars.\nThis will also determine how close the bars are to each other")
        else:
            self.view.bar_width_spin.setEnabled(False)
            self.view.bar_width_spin.setToolTip("Bar width customization is not supported for histograms")

        is_3d = primary_plot_type in ["3D Scatter", "3D Line", "3D Surface"]
        self.view.z_column_widget.setVisible(is_3d)
        self.view.camera_3d_group.setVisible(is_3d)
        self.view.zlabel_widget.setVisible(is_3d)

        self.plot_tab.view_cube.setVisible(is_3d)

        if is_3d:
            self.view.tight_layout_check.setChecked(False)
            self.view.tight_layout_check.setEnabled(False)
            self.view.tight_layout_check.setToolTip("Tight layout is not supported for 3D plots")
        else:
            self.view.tight_layout_check.setEnabled(True)
            self.view.tight_layout_check.setToolTip("")

        z_tab_idx = self.view.axis_tab_widget.indexOf(self.view.z_tab)
        if is_3d and z_tab_idx == -1:
            self.view.axis_tab_widget.addTab(self.view.z_tab, "Z-Axis")
        else:
            if not is_3d and z_tab_idx != -1:
                self.view.axis_tab_widget.removeTab(z_tab_idx)

        unsupported_3d_tick_controls = [
            "x_major_tick_direction_combo", "x_major_tick_width_spin",
            "y_major_tick_direction_combo", "y_major_tick_width_spin",
            "z_major_tick_direction_combo", "z_major_tick_width_spin",
            "x_minor_tick_direction_combo", "x_minor_tick_width_spin",
            "y_minor_tick_direction_combo", "y_minor_tick_width_spin",
            "z_minor_tick_direction_combo", "z_minor_tick_width_spin"
        ]
        for control_name in unsupported_3d_tick_controls:
            if hasattr(self.view, control_name):
                control_widget = getattr(self.view, control_name)
                control_widget.setEnabled(not is_3d)
                if is_3d:
                    control_widget.setToolTip(
                        "Tick direction and width customization are not supported in 3D rendered plots")
                else:
                    control_widget.setToolTip("")
