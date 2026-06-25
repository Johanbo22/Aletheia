from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from controller.data_controllers.base_data_controller import BaseDataController
from core.global_signals import global_signals
from ui.dialogs import (
    AppendDialog,
    BinningDialog,
    ColumnReorderDialog,
    MeltDialog,
    MergeDialog,
    PercentageChangeDialog,
    PivotDialog,
    RollingWindowDialog,
    ShiftDataDialog,
)
from ui.status_bar import LogLevel
from ui.widgets.ToastNotification import ToastLevel

class TransformationController(BaseDataController):
    """
    Sub-controller handling dataframe data reshaping and transformations
    """

    def open_binning_dialog(self) -> None:
        """Opens the dialog to create discretised buckets from a continuous numeric column."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        numeric_cols = self.data_handler.df.select_dtypes(include=["number"]).columns.tolist()
        if not numeric_cols:
            global_signals.request_toast(
                "No Numeric Data", "This dataset contains no numeric columns suitable for binning", ToastLevel.WARNING
            )
            return

        dialog = BinningDialog(numeric_cols, self.data_handler.df, parent=self.view)
        if dialog.exec():
            config = dialog.get_config()
            if config:
                try:
                    self.data_handler.bin_column(
                        column=config["column"],
                        new_column_name=config["new_column"],
                        method=config["method"],
                        bins=config["bins"],
                        labels=config["labels"],
                        right_inclusive=config.get("right_inclusive", True),
                        drop_original=config.get("drop_original", False)
                    )
                    self.view.refresh_data_view()

                    method_display = "Quantile" if config["method"] == "qcut" else "Uniform/Custom"
                    bins_display = len(config["bins"]) - 1 if isinstance(config["bins"], list) else config["bins"]

                    self.status_bar.log_action(
                        f"Binned '{config['column']}' -> '{config['new_column']}'",
                        details={
                            "source_column": config["column"],
                            "new_column"   : config["new_column"],
                            "method"       : method_display,
                            "bins"         : bins_display,
                            "operation"    : "bin_column"
                        },
                        level=LogLevel.SUCCESS
                    )
                except Exception as e:
                    global_signals.request_toast("Binning Error", "Failed to bin column", ToastLevel.ERROR)
                    self.status_bar.log(f"Binning failed: {str(e)}", LogLevel.ERROR)

    def open_melt_dialog(self) -> None:
        """Opens the dialog to restructure the DataFrame from wide to long format."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        dialog = MeltDialog(self.data_handler.df, self.view)
        if dialog.exec():
            config = dialog.get_config()
            try:
                reply = QMessageBox.question(
                    self.view,
                    "Confirm Melt",
                    "Melting will restructure your entire dataset.\n\n"
                    "Are you sure you want to proceed?\n(You can Undo this operation later)",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    before_shape = self.data_handler.df.shape
                    self.data_handler.melt_data(
                        id_vars=config["id_vars"],
                        value_vars=config["value_vars"],
                        var_name=config["var_name"],
                        value_name=config["value_name"],
                    )
                    after_shape = self.data_handler.df.shape
                    self.view.refresh_data_view()

                    self.status_bar.log_action(
                        f"Melted data: {before_shape} -> {after_shape}",
                        details={
                            "id_vars"     : config["id_vars"],
                            "value_vars"  : config["value_vars"],
                            "shape_before": before_shape,
                            "shape_after" : after_shape,
                            "operation"   : "melt",
                        },
                        level=LogLevel.SUCCESS,
                    )
            except Exception as e:
                global_signals.request_toast("Error", "Failed to melt data", ToastLevel.ERROR)
                self.status_bar.log(f"Melt failed: {str(e)}", LogLevel.ERROR)

    def open_pivot_dialog(self) -> None:
        """Opens the dialog to restructure the DataFrame into a pivot table."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        dialog = PivotDialog(self.data_handler.df, self.view)
        if dialog.exec():
            config = dialog.get_config()
            try:
                reply = QMessageBox.question(
                    self.view,
                    "Confirm Pivot",
                    "Pivoting will restructure your entire dataset.\n\nAre you sure you want to proceed?\n",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    before_shape = self.data_handler.df.shape
                    self.data_handler.pivot_data(
                        index=config["index"], columns=config["columns"],
                        values=config["values"], aggfunc=config["aggfunc"]
                    )
                    after_shape = self.data_handler.df.shape
                    self.view.refresh_data_view()

                    self.status_bar.log_action(
                        f"Pivoted data: {before_shape} -> {after_shape}",
                        details={
                            "index"       : config["index"],
                            "columns"     : config["columns"],
                            "values"      : config["values"],
                            "aggfunc"     : config["aggfunc"],
                            "shape_before": before_shape,
                            "shape_after" : after_shape,
                            "operation"   : "pivot",
                        },
                        level=LogLevel.SUCCESS
                    )
            except Exception as e:
                global_signals.request_toast("Error", "Failed to pivot data", ToastLevel.ERROR)
                self.status_bar.log(f"Pivot Failed: {str(e)}", LogLevel.ERROR)

    def open_merge_dialog(self) -> None:
        """Opens the dialog for joining two datasets based on a common key."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        dialog = MergeDialog(self.data_handler, self.view)
        if dialog.exec():
            config = dialog.get_config()
            try:
                rows_before = len(self.data_handler.df)
                self.data_handler.merge_data(
                    right_df=config["right_df"],
                    how=config["how"],
                    left_on=config["left_on"],
                    right_on=config["right_on"],
                    suffixes=config["suffixes"]
                )
                rows_after = len(self.data_handler.df)
                self.view.refresh_data_view()

                self.status_bar.log_action(
                    f"Merged data ({config['how']})",
                    details={"how"      : config["how"], "rows_before": rows_before, "rows_after": rows_after,
                             "operation": "merge"},
                    level=LogLevel.SUCCESS
                )
            except Exception as e:
                global_signals.request_toast("Error", "Failed to merge datasets", ToastLevel.ERROR)
                self.status_bar.log(f"Merge failed: {str(e)}", LogLevel.ERROR)

    def open_append_dialog(self) -> None:
        """Opens the dialog to concatenate rows from another dataset into the current one."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        dialog = AppendDialog(self.data_handler, self.view)
        if dialog.exec():
            config = dialog.get_config()
            try:
                rows_before = len(self.data_handler.df)
                self.data_handler.concatenate_data(other_df=config["other_df"], ignore_index=config["ignore_index"])
                rows_after = len(self.data_handler.df)
                self.view.refresh_data_view()

                self.status_bar.log_action(
                    f"Appended {rows_after - rows_before:,} rows of data",
                    details={"rows_before": rows_before, "rows_after": rows_after,
                             "rows_added" : rows_after - rows_before, "operation": "concatenate"},
                    level=LogLevel.SUCCESS
                )
            except Exception as e:
                global_signals.request_toast("Error", "Failed to append datasets", ToastLevel.ERROR)
                self.status_bar.log(f"Append failed: {str(e)}", LogLevel.ERROR)

    def open_rolling_window_dialog(self) -> None:
        """Opens the dialog to configure and apply a rolling window operation over sequential data."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        numeric_cols = self.data_handler.df.select_dtypes(include=["number"]).columns.tolist()
        if not numeric_cols:
            global_signals.request_toast(
                "No Numeric Data", "This dataset contains no numeric columns suitable for rolling window",
                ToastLevel.WARNING
            )
            return

        dialog = RollingWindowDialog(self.data_handler.df, self.view)
        if dialog.exec():
            config = dialog.get_config()
            try:
                self.data_handler.clean_data(
                    action="rolling_window",
                    column=config["column"],
                    window=config["window"],
                    operation=config["operation"],
                    new_column=config["new_column"]
                )
                self.view.refresh_data_view()

                self.status_bar.log_action(
                    f"Applied {config['window']}-period rolling {config['operation']} on '{config['column']}'",
                    details={
                        "column"    : config["column"],
                        "window"    : config["window"],
                        "operation" : config["operation"],
                        "new_column": config["new_column"],
                    },
                    level=LogLevel.SUCCESS
                )
            except Exception as e:
                self.status_bar.log(f"Failed to apply rolling window: {str(e)}", LogLevel.ERROR)
                global_signals.request_toast("Error", "Failed to apply rolling window", ToastLevel.ERROR)

    def open_shift_dialog(self) -> None:
        """Opens the dialog to apply a lag or lead shift operation."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        dialog = ShiftDataDialog(self.data_handler.df, self.view)
        if dialog.exec():
            config = dialog.get_config()
            try:
                self.data_handler.clean_data(
                    action="shift_data",
                    column=config["column"],
                    periods=config["periods"],
                    fill_value=config["fill_value"],
                    new_column=config["new_column"]
                )
                self.view.refresh_data_view()

                self.status_bar.log_action(
                    f"Applied {config['periods']}-period shift on '{config['column']}'",
                    details={
                        "column"    : config["column"],
                        "periods"   : config["periods"],
                        "fill_value": config["fill_value"],
                        "new_column": config["new_column"],
                        "operation" : "shift_data"
                    },
                    level=LogLevel.SUCCESS
                )
            except Exception as e:
                self.status_bar.log(f"Failed to apply shift: {str(e)}", LogLevel.ERROR)
                global_signals.request_toast("Error", "Failed to apply shift", ToastLevel.ERROR)

    def open_pct_change_dialog(self) -> None:
        """Opens the dialog to calculate sequential percentage changes."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        numeric_cols = self.data_handler.df.select_dtypes(include=["number"]).columns.tolist()
        if not numeric_cols:
            global_signals.request_toast(
                "No Numeric Data", "This dataset contains no numeric columns suitable for percentage change",
                ToastLevel.WARNING
            )
            return

        dialog = PercentageChangeDialog(self.data_handler.df, self.view)
        if dialog.exec():
            config = dialog.get_config()
            try:
                self.data_handler.clean_data(
                    action="percentage_change",
                    column=config["column"],
                    periods=config["periods"],
                    fill_method=config["fill_method"],
                    new_column=config["new_column"]
                )
                self.view.refresh_data_view()

                self.status_bar.log_action(
                    f"Applied {config['periods']}-period percentage change on '{config['column']}'",
                    details={
                        "column"     : config["column"],
                        "periods"    : config["periods"],
                        "fill_method": config["fill_method"],
                        "new_column" : config["new_column"],
                        "operation"  : "percentage_change"
                    },
                    level=LogLevel.SUCCESS
                )
            except Exception as e:
                self.status_bar.log(f"Failed to calculate percentage change: {str(e)}", LogLevel.ERROR)
                global_signals.request_toast("Error", "Failed to calculate percentage change", ToastLevel.ERROR)

    def open_column_reorder_dialog(self) -> None:
        """Opens the dialog for reordering the active dataset's columns."""
        if self.data_handler.df is None or self.data_handler.df.empty:
            self.status_bar.log("No data available to reorder", LogLevel.WARNING)
            self.no_data_loaded_toast()
            return

        dialog = ColumnReorderDialog(df=self.data_handler.df, parent=self.view)
        if dialog.exec():
            new_order = dialog.get_new_order()

            # Avoid dispatching identical history events
            if new_order != list(self.data_handler.df.columns):
                try:
                    self.data_handler.clean_data(action="reorder_columns", new_order=new_order)
                    self.status_bar.log("Columns have been reordered", LogLevel.SUCCESS)
                    self.view.refresh_data_view()
                except Exception as e:
                    self.status_bar.log(f"Failed to reorder columns: {str(e)}", LogLevel.ERROR)

    def apply_sort(self) -> None:
        """Applies permanent (DataHandler level) sorting to the current data view."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        column, order_text = self.view.operations_panel.get_sort_parameters()
        if not column:
            return

        ascending = (order_text == "Ascending")

        try:
            col_index = -1 if column == "[Index]" else list(self.data_handler.df.columns).index(column)
            order = Qt.SortOrder.AscendingOrder if ascending else Qt.SortOrder.DescendingOrder

            self.view.data_table.sortByColumn(col_index, order)
            self.view.refresh_data_view(reload_model=False)

            direction = "ascending" if ascending else "descending"
            self.status_bar.log_action(
                f"Sorted data by '{column}' ({direction})",
                details={"column": column, "direction": direction, "operation": "sort"},
                level=LogLevel.SUCCESS,
            )
        except ValueError:
            pass
        except Exception as e:
            self.status_bar.log(f"Sort failed: {str(e)}", LogLevel.ERROR)
            global_signals.request_toast("Error", "Failed to sort data", ToastLevel.ERROR)