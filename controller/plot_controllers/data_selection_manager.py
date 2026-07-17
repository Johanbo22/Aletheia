from typing import List, Optional, TYPE_CHECKING

from PyQt6.QtWidgets import QComboBox, QListWidget

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
            self.view.basic_tab.stacked_bars_check.blockSignals(True)
            self.view.basic_tab.stacked_bars_check.setChecked(False)
            self.view.basic_tab.stacked_bars_check.blockSignals(False)

            selected_multi = self.view.y_columns_list.selectedItems()
            if selected_multi:
                self.view.y_column.setCurrentText(selected_multi[0].text())
        else:
            if self.view.y_column.currentText():
                current_y = self.view.y_column.currentText()
                for i in range(self.view.y_columns_list.count()):
                    if self.view.y_columns_list.item(i).text() == current_y:
                        self.view.y_columns_list.item(i).setSelected(True)
                        break

        self.plot_tab.on_data_changed()

    def toggle_stacked_bars(self) -> None:
        """Handle toggle of stacked bars check."""
        if self.view.basic_tab.stacked_bars_check.isChecked() and not self.view.multi_y_check.isChecked():
            self.view.multi_y_check.setChecked(True)
        else:
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

        y_col_text = self.view.y_column.currentText()
        return [y_col_text] if y_col_text else []

    def update_column_combo(self) -> None:
        """Update column ComboBoxes with available columns."""
        if self.data_handler.df is None or len(self.data_handler.df.columns) == 0:
            return

        columns = list(self.data_handler.df.columns)
        self.view.quick_filter_input.set_columns(columns)

        prev_x = self.view.x_column.currentText()
        prev_y = self.view.y_column.currentText()
        prev_z = self.view.z_column.currentText()
        prev_hue = self.view.hue_column.currentText()
        prev_sec_y = self.view.secondary_y_column.currentText()
        prev_multi_y = [item.text() for item in self.view.y_columns_list.selectedItems()]

        self._sync_combo(self.view.x_column, columns)
        self._sync_combo(self.view.y_column, columns)
        self._sync_combo(self.view.z_column, columns)
        self._sync_combo(self.view.secondary_y_column, columns)
        self._sync_combo(self.view.hue_column, columns, prepend_item="None")
        self._sync_combo(self.view.auto_annotate_col_combo, columns, prepend_item="Default (Y-value)")

        self._sync_list_widget(self.view.y_columns_list, columns, prev_multi_y)

        curr_x = self.view.x_column.currentText()
        curr_y = self.view.y_column.currentText()
        curr_z = self.view.z_column.currentText()
        curr_hue = self.view.hue_column.currentText()
        curr_sec_y = self.view.secondary_y_column.currentText()
        curr_multi_y = [item.text() for item in self.view.y_columns_list.selectedItems()]

        changed = (
                prev_x != curr_x or
                prev_y != curr_y or
                prev_hue != curr_hue or
                prev_sec_y != curr_sec_y
        )

        if self.view.multi_y_check.isChecked():
            changed = changed or (prev_multi_y != curr_multi_y)
        else:
            changed = changed or (prev_y != curr_y)

        if changed:
            self.plot_tab.on_data_changed()

    def _sync_combo(self, combo: QComboBox, items: List[str], prepend_item: Optional[str] = None) -> None:
        """Sync comboboxes while maintaining selection"""
        current_text = combo.currentText()
        combo.blockSignals(True)
        combo.clear()

        if prepend_item:
            combo.addItem(prepend_item)

        combo.addItems(items)

        first_item_index: int = 0
        if current_text in items:
            combo.setCurrentText(current_text)
        elif prepend_item and current_text == prepend_item:
            combo.setCurrentText(prepend_item)
        elif prepend_item:
            combo.setCurrentIndex(first_item_index)

        combo.blockSignals(False)

    def _sync_list_widget(self, list_widget: QListWidget, items: List[str], selected_items: List[str]) -> None:
        """Sync a QListWidget while maintaining multi selection"""
        list_widget.blockSignals(True)
        list_widget.clear()

        for item_text in items:
            list_widget.addItem(item_text)
            if item_text in selected_items:
                item = list_widget.item(list_widget.count() - 1)
                item.setSelected(item)

        list_widget.blockSignals(False)

    def toggle_secondary_input(self, enabled: bool) -> None:
        """Toggle secondary Y-axis inputs visibility and state."""
        is_enabled = bool(enabled)
        self.view.secondary_y_column.setEnabled(is_enabled)
        if hasattr(self.view, "secondary_plot_type_combo"):
            self.view.secondary_plot_type_combo.setEnabled(is_enabled)
        if hasattr(self.view, "secondary_zorder_check"):
            self.view.secondary_zorder_check.setEnabled(is_enabled)
        self.type_manager.update_customization_visibility(self.plot_tab.current_plot_type_name)
