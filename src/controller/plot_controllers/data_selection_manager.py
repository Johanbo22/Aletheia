from typing import List, Optional, TYPE_CHECKING

import pandas as pd
from PyQt6.QtWidgets import QComboBox, QListWidget

from src.ui.widgets.DatatypeChip import DtypeChipCreator

if TYPE_CHECKING:
    from src.ui.plot_tab import PlotTab

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
        prepend_items = [prepend_item] if prepend_item else None
        DtypeChipCreator.sync_combobox(combo, self.data_handler.df, items, prepend_items=prepend_items)

    def _sync_list_widget(self, list_widget: QListWidget, items: List[str], selected_items: List[str]) -> None:
        """Sync a QListWidget while maintaining multi selection"""
        DtypeChipCreator.sync_list_widget(list_widget, self.data_handler.df, items, selected_items)

    def toggle_secondary_input(self, enabled: bool) -> None:
        """Toggle secondary Y-axis inputs visibility and state."""
        is_enabled = bool(enabled)
        self.view.secondary_y_column.setEnabled(is_enabled)
        if hasattr(self.view, "secondary_plot_type_combo"):
            self.view.secondary_plot_type_combo.setEnabled(is_enabled)
        if hasattr(self.view, "secondary_zorder_check"):
            self.view.secondary_zorder_check.setEnabled(is_enabled)
        self.type_manager.update_customization_visibility(self.plot_tab.current_plot_type_name)

    def adapt_selection_for_plot_type(self, plot_type: str) -> None:
        """
        Adapt column selection to satisfy requirements of the chosen plot type

        This method inspects the active DataFrame s dtypes and reassigns if the current
        selections does not match target plots data types

        :param plot_type: The name identifier of the target plot
        """
        df = self.data_handler.df
        if df is None or df.empty:
            return

        numeric_cols: list[str] = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
        all_cols: list[str] = list(df.columns)
        if not all_cols:
            return

        self._block_column_signals(True)
        try:
            self._adjust_columns_for_target_type(plot_type, df, numeric_cols, all_cols)
        finally:
            self._block_column_signals(False)

    def _block_column_signals(self, block: bool) -> None:
        """Block or unblock the x/y/z axis selection widgets"""
        self.view.x_column.blockSignals(block)
        self.view.y_column.blockSignals(block)
        self.view.z_column.blockSignals(block)
        self.view.y_columns_list.blockSignals(block)
        self.view.multi_y_check.blockSignals(block)

    def _adjust_columns_for_target_type(self, plot_type: str, df: pd.DataFrame, numeric_cols: list[str],
                                        all_cols: list[str]) -> None:
        plots_3d = {"3D Scatter", "3D Line", "3D Surface"}
        plots_gridded = {"Image Show (imshow)", "pcolormesh", "PColormesh", "Contour", "Contourf"}
        plots_vector = {"Barbs", "Quiver", "Streamplot"}
        plots_strict_numeric_2d = {
            "Scatter", "Hexbin", "2D Density", "2D Histogram", "Stem", "Stairs", "Triplot"
        }
        plots_numeric_y = {
            "Line", "Bar", "Area", "Box", "Violin", "Pie", "Histogram", "KDE", "ECDF", "Stackplot"
        }

        if plot_type in plots_3d:
            self._adapt_3d_columns(numeric_cols)
        elif plot_type in plots_gridded:
            self._adapt_multi_y_columns(numeric_cols, all_cols, min_count=2)
        elif plot_type in plots_vector:
            self._adapt_multi_y_columns(numeric_cols, all_cols, min_count=3)
        elif plot_type in plots_strict_numeric_2d:
            self._adapt_strict_numeric_2d(df, numeric_cols)
        elif plot_type in plots_numeric_y:
            self._adapt_numeric_y(numeric_cols)

    def _adapt_3d_columns(self, numeric_cols: list[str]) -> None:
        """Assign available numeric columns across X, Y and Z axes"""
        if not numeric_cols:
            return

        if self.view.x_column.currentText() not in numeric_cols:
            self.view.x_column.setCurrentText(numeric_cols[0])

        if self.view.y_column.currentText() not in numeric_cols:
            y_target = numeric_cols[1] if len(numeric_cols) > 1 else numeric_cols[0]
            self.view.y_column.setCurrentText(y_target)

        if self.view.z_column.currentText() not in numeric_cols:
            z_target = numeric_cols[2] if len(numeric_cols) > 2 else numeric_cols[0]
            self.view.z_column.setCurrentText(z_target)

    def _adapt_multi_y_columns(self, numeric_cols: list[str], all_cols: list[str], min_count: int) -> None:
        """Activates the multi y column mode and selects the minimum required quantity of series"""
        source_cols = numeric_cols if len(numeric_cols) >= min_count else all_cols
        if len(source_cols) < min_count:
            return

        self.view.multi_y_check.setChecked(True)
        self.view.y_column.setVisible(False)
        self.view.y_columns_list.setVisible(True)

        selected_items = [item.text() for item in self.view.y_columns_list.selectedItems()]
        valid_selection = [col for col in selected_items if col in source_cols]

        if len(valid_selection) < min_count:
            self.view.y_columns_list.clearSelection()
            target_cols = set(source_cols[:min_count])
            for i in range(self.view.y_columns_list.count()):
                item = self.view.y_columns_list.item(i)
                if item and item.text() in target_cols:
                    item.setSelected(True)

    def _adapt_strict_numeric_2d(self, df: pd.DataFrame, numeric_cols: list[str]) -> None:
        """Ensure X is numeric or datetime and Y is numeric"""
        if not numeric_cols:
            return

        current_x = self.view.x_column.currentText()
        is_valid_x = current_x in df.columns and (
                pd.api.types.is_numeric_dtype(df[current_x]) or pd.api.types.is_datetime64_any_dtype(df[current_x]))
        if not is_valid_x:
            self.view.x_column.setCurrentText(numeric_cols[0])

        current_y = self.view.y_column.currentText()
        if current_y not in numeric_cols:
            chosen_x = self.view.x_column.currentText()
            y_target = numeric_cols[1] if (len(numeric_cols) > 1 and numeric_cols[0] == chosen_x) else numeric_cols[0]
            self.view.y_column.setCurrentText(y_target)

    def _adapt_numeric_y(self, numeric_cols: list[str]) -> None:
        """Ensure primary y series contains numeric columns"""
        if not numeric_cols:
            return

        if self.view.y_column.currentText() not in numeric_cols:
            self.view.y_column.setCurrentText(numeric_cols[0])
