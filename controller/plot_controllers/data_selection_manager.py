from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab

class DataSelectionManager:
    """
    Manages the UI logic for selecting columns,
    configuring multiple y axes and secondary inputs
    """

    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab
        self.view = plot_tab.view
        self.data_handler = plot_tab.data_handler
        self.type_manager = plot_tab.type_manager

    def connect_signals(self) -> None:
        """Connect signals related to data selection controls."""
        self.view.multi_y_check.stateChanged.connect(self.toggle_multi_y)
        self.view.basic_tab.stacked_bars_check.stateChanged.connect(self.toggle_stacked_bars)
        self.view.select_all_y_btn.clicked.connect(self.select_all_y_columns)
        self.view.clear_all_y_btn.clicked.connect(self.clear_all_y_columns)
        self.view.secondary_y_check.stateChanged.connect(lambda state: self.toggle_secondary_input(bool(state)))

    def toggle_multi_y(self) -> None:
        """Toggle between multi and single y selections."""
        is_multi = self.view.multi_y_check.isChecked()

        self.view.y_column.setVisible(not is_multi)
        self.view.y_columns_list.setVisible(is_multi)
        self.view.select_all_y_btn.setVisible(is_multi)
        self.view.clear_all_y_btn.setVisible(is_multi)
        self.view.multi_y_info.setVisible(is_multi)

        if not is_multi:
            self.view.basic_tab.stacked_bars_check.setChecked(False)

        if is_multi and self.view.y_column.currentText():
            current_y = self.view.y_column.currentText()
            for i in range(self.view.y_columns_list.count()):
                if self.view.y_columns_list.item(i).text() == current_y:
                    self.view.y_columns_list.item(i).setSelected(True)
                    break
        self.plot_tab.on_data_changed()

    def toggle_stacked_bars(self) -> None:
        """Handle toggle of stacked bars check."""
        if self.view.basic_tab.stacked_bars_check.isChecked():
            self.view.multi_y_check.setChecked(True)
        self.plot_tab.on_data_changed()

    def select_all_y_columns(self) -> None:
        """Select all available ycols."""
        self.view.y_columns_list.selectAll()
        self.plot_tab.on_data_changed()

    def clear_all_y_columns(self) -> None:
        """Clear all selected ycols."""
        self.view.y_columns_list.clearSelection()
        self.plot_tab.on_data_changed()

    def get_selected_y_columns(self) -> List[str]:
        """Get list of selected ycols."""
        if self.view.multi_y_check.isChecked():
            selected_items = self.view.y_columns_list.selectedItems()
            return [item.text() for item in selected_items]
        else:
            y_col_text = self.view.y_column.currentText()
            return [y_col_text] if y_col_text else []

    def update_column_combo(self) -> None:
        """Update column ComboBoxes with available columns."""
        if self.data_handler.df is None or len(self.data_handler.df.columns) == 0:
            return

        columns = list(self.data_handler.df.columns)
        self.view.quick_filter_input.set_columns(columns)

        current_x = self.view.x_column.currentText()
        current_y = self.view.y_column.currentText()
        current_z = self.view.z_column.currentText()
        current_hue = self.view.hue_column.currentText()
        current_secondary_y = self.view.secondary_y_column.currentText()
        current_auto_annoate = self.view.auto_annotate_col_combo.currentText()
        current_multi_y = []
        if self.view.multi_y_check.isChecked():
            current_multi_y = [item.text() for item in self.view.y_columns_list.selectedItems()]

        self.view.x_column.blockSignals(True)
        self.view.y_column.blockSignals(True)
        self.view.z_column.blockSignals(True)
        self.view.hue_column.blockSignals(True)
        self.view.secondary_y_column.blockSignals(True)
        self.view.y_columns_list.blockSignals(True)
        self.view.auto_annotate_col_combo.blockSignals(True)

        self.view.x_column.clear()
        self.view.x_column.addItems(columns)
        if current_x in columns:
            self.view.x_column.setCurrentText(current_x)

        self.view.y_column.clear()
        self.view.y_column.addItems(columns)
        if current_y in columns:
            self.view.y_column.setCurrentText(current_y)

        self.view.z_column.clear()
        self.view.z_column.addItems(columns)
        if current_z in columns:
            self.view.z_column.setCurrentText(current_z)

        self.view.secondary_y_column.clear()
        self.view.secondary_y_column.addItems(columns)
        if current_secondary_y in columns:
            self.view.secondary_y_column.setCurrentText(current_secondary_y)

        self.view.y_columns_list.clear()
        for col in columns:
            self.view.y_columns_list.addItem(col)
            if col in current_multi_y:
                item = self.view.y_columns_list.item(self.view.y_columns_list.count() - 1)
                item.setSelected(True)

        self.view.hue_column.clear()
        self.view.hue_column.addItem("None")
        self.view.hue_column.addItems(columns)
        if current_hue in columns:
            self.view.hue_column.setCurrentText(current_hue)
        else:
            self.view.hue_column.setCurrentIndex(0)

        self.view.auto_annotate_col_combo.clear()
        self.view.auto_annotate_col_combo.addItem("Default (Y-value)")
        self.view.auto_annotate_col_combo.addItems(columns)

        if current_auto_annoate in columns:
            self.view.auto_annotate_col_combo.setCurrentText(current_auto_annoate)
        elif current_auto_annoate == "Default (Y-value)":
            self.view.auto_annotate_col_combo.setCurrentIndex(0)

        self.view.x_column.blockSignals(False)
        self.view.y_column.blockSignals(False)
        self.view.z_column.blockSignals(False)
        self.view.hue_column.blockSignals(False)
        self.view.secondary_y_column.blockSignals(False)
        self.view.y_columns_list.blockSignals(False)
        self.view.auto_annotate_col_combo.blockSignals(False)

        if current_x != self.view.x_column.currentText() or current_y != self.view.y_column.currentText():
            self.plot_tab.on_data_changed()

    def toggle_secondary_input(self, enabled: bool) -> None:
        """Toggle secondary Y-axis inputs visibility and state."""
        is_enabled = bool(enabled)
        self.view.secondary_y_column.setEnabled(is_enabled)
        if hasattr(self.view, "secondary_plot_type_combo"):
            self.view.secondary_plot_type_combo.setEnabled(is_enabled)
        if hasattr(self.view, "secondary_zorder_check"):
            self.view.secondary_zorder_check.setEnabled(is_enabled)
        self.type_manager.update_customization_visibility(self.plot_tab.current_plot_type_name)
