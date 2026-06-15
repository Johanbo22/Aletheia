from typing import TYPE_CHECKING

import numpy as np

from core.global_signals import global_signals
from ui.widgets.ToastNotification import ToastLevel

if TYPE_CHECKING:
    from ui.plot_tab import PlotTab

class PlotTableManager:
    """
    Manages the generation and customization of data tables overlaid on the plot interface
    """

    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab
        self.view = plot_tab.view
        self.plot_engine = plot_tab.plot_engine
        self.status_bar = plot_tab.status_bar

    def connect_signals(self) -> None:
        """Connect signals for the annotations tab table properties."""
        self.view.table_enable_check.stateChanged.connect(self.toggle_table_controls)
        self.view.table_auto_font_size_check.stateChanged.connect(self.toggle_table_font_controls)

        self.view.table_enable_check.stateChanged.connect(self.plot_tab.on_style_changed)
        self.view.table_type_combo.currentTextChanged.connect(self.plot_tab.on_style_changed)
        self.view.table_location_combo.currentTextChanged.connect(self.plot_tab.on_style_changed)
        self.view.table_auto_font_size_check.stateChanged.connect(self.plot_tab.on_style_changed)
        self.view.table_font_size_spin.valueChanged.connect(self.plot_tab.on_style_changed)
        self.view.table_scale_spin.valueChanged.connect(self.plot_tab.on_style_changed)

    def toggle_table_controls(self) -> None:
        """Enables and disables table controls"""
        enabled = self.view.table_enable_check.isChecked()
        self.view.table_type_combo.setEnabled(enabled)
        self.view.table_type_combo.setVisible(enabled)
        self.view.table_location_combo.setEnabled(enabled)
        self.view.table_location_combo.setVisible(enabled)

        self.view.table_auto_font_size_check.setEnabled(enabled)
        self.view.table_scale_spin.setEnabled(enabled)
        self.view.table_scale_spin.setVisible(enabled)

        use_auto = self.view.table_auto_font_size_check.isChecked()
        self.view.table_font_size_spin.setEnabled(enabled and not use_auto)
        self.view.table_font_size_spin.setVisible(enabled and not use_auto)

    def toggle_table_font_controls(self) -> None:
        """Toggle manual font spinbox on and off"""
        use_auto = self.view.table_auto_font_size_check.isChecked()
        self.view.table_font_size_spin.setEnabled(not use_auto)
        self.view.table_font_size_spin.setVisible(not use_auto)

    def apply_table(self) -> None:
        """Generate the table and add it to the plot"""
        if self.plot_engine.current_ax:
            for table in list(self.plot_engine.current_ax.tables):
                try:
                    table.remove()
                except Exception:
                    pass

        if not self.view.table_enable_check.isChecked():
            return

        df = self.plot_tab.get_active_dataframe()
        if df is None:
            return

        try:
            table_type = self.view.table_type_combo.currentText()
            x_col = self.view.x_column.currentText()
            y_cols = self.plot_tab.get_selected_y_columns()

            cols_to_use = []
            if x_col:
                cols_to_use.append(x_col)
            cols_to_use.extend(y_cols)

            if cols_to_use and all(column in df.columns for column in cols_to_use):
                target_df = df[cols_to_use]
            else:
                target_df = df.select_dtypes(include=[np.number])

            if table_type == "Summary Stats":
                data = target_df.describe().round(2)
            elif table_type == "First 5 Rows":
                data = target_df.head(5)
            elif table_type == "Last 5 Rows":
                data = target_df.tail(5)
            elif table_type == "Correlation Matrix":
                data = target_df.corr().round(2)
            else:
                data = target_df.head()

            loc = self.view.table_location_combo.currentText()
            auto_font = self.view.table_auto_font_size_check.isChecked()
            fontsize = self.view.table_font_size_spin.value()
            scale = self.view.table_scale_spin.value()

            self.plot_engine.add_table(
                data,
                loc=loc,
                auto_font_size=auto_font,
                fontsize=fontsize,
                scale_factor=scale
            )

        except Exception as PlotTableError:
            global_signals.toast_requested.emit("Error", "Failed to add table to plot", ToastLevel.ERROR, 4000)
            self.status_bar.log(f"Failed to add table to plot: {str(PlotTableError)}", "ERROR")
