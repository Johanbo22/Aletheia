import base64
import html
import weakref
from io import BytesIO
from pathlib import Path
from typing import Optional, TYPE_CHECKING

import matplotlib.pyplot as plt
import pandas as pd
from PyQt6.QtCore import QThreadPool, Qt
from PyQt6.QtWidgets import QApplication, QDialog, QFileDialog, QInputDialog, QMessageBox

from core.aggregation_manager import AggregationManager
from core.data_handler import DataHandler
from core.global_signals import global_signals
from core.help_manager import HelpManager
from core.resource_loader import get_resource_path
from core.subset_manager import SubsetManager
from ui.animations import AggregationAnimation, CalculationAnimation, DataFilterAnimation, DataTypeChangeAnimation, \
    DropColumnAnimation, DropMissingValueAnimation, ExportFileAnimation, FailedAnimation, FileImportAnimation, \
    FillMissingValuesAnimation, MeltDataAnimation, NewDataFrameAnimation, OutlierDetectionAnimation, RemoveRowAnimation, \
    RenameColumnAnimation, ResetToOriginalStateAnimation, SubsetDataAnimation
from ui.dialogs import AggregationDialog, AppendDialog, BinningDialog, ColumnReorderDialog, ComputedColumnDialog, \
    CreateDatasetDialog, FillMissingDialog, FilterAdvancedDialog, HelpDialog, MacroPreviewDialog, MeltDialog, \
    MergeDialog, OutlierDetectionDialog, PercentageChangeDialog, PivotDialog, ProgressDialog, RegexReplaceDialog, \
    RenameColumnDialog, RollingWindowDialog, ShiftDataDialog, SplitColumnDialog, SubsetDataViewer
from ui.dialogs.ExportDialog import ExportConfig, ExportDialog
from ui.status_bar import LogLevel
from ui.widgets.ToastNotification import ToastLevel
from ui.workers import AutoCreateSubsetsWorker, GoogleSheetsImportWorker
from controller.data_controllers.dataset_controller import DatasetController
from controller.data_controllers.cleaning_controller import CleaningController
from controller.data_controllers.stats_controller import StatsController

if TYPE_CHECKING:
    from ui.data_tab import DataTab
    from ui.status_bar import StatusBar

class DataTabController:
    """
    Controller for the DataTab\n
    Handles data operations, dialogs and updating the data view.
    """

    def __init__(self, data_handler: DataHandler, status_bar: "StatusBar", view: "DataTab",
                 subset_manager: SubsetManager):
        self.data_handler = data_handler
        self.status_bar = status_bar
        self._view = weakref.ref(view)
        self.subset_manager = subset_manager

        # Managers
        self.aggregation_manager = AggregationManager()
        self.help_manager = HelpManager()

        self.dataset_controller = DatasetController(data_handler, status_bar, view, subset_manager)
        self.cleaning_controller = CleaningController(data_handler, status_bar, view, subset_manager)
        self.stats_controller = StatsController(data_handler, status_bar, view, subset_manager)

    @property
    def view(self) -> "DataTab":
        return self._view()

    @staticmethod
    def no_data_loaded_toast() -> None:
        global_signals.request_toast(
            "No Data", "Please load data first",
            ToastLevel.WARNING
        )

    def create_new_dataset(self) -> None:
        """Creates a new empty dataset"""
        self.dataset_controller.create_new_dataset()

    def refresh_google_sheets(self):
        """Refreshes data from the last imported google sheets document"""
        self.dataset_controller.refresh_google_sheets()

    def remove_duplicates(self) -> None:
        """Remove duplicate rows"""
        self.cleaning_controller.remove_duplicates()

    def drop_missing(self):
        """Drop rows with missing values"""
        self.cleaning_controller.drop_missing()

    def drop_empty_columns(self) -> None:
        self.cleaning_controller.drop_empty_columns()

    def fill_missing(self):
        """Fill missing values"""
        self.cleaning_controller.fill_missing()

    def open_outlier_dialog(self, method):
        """Opens the outlier detection dialog"""
        self.cleaning_controller.open_outlier_dialog(method)

    def apply_normalization(self) -> None:
        """Apply the selected normalization method to the selected column"""
        self.cleaning_controller.apply_normalization()

    def apply_filter(self):
        """Apply filter to data"""
        try:
            # Accessing widgets from the view's operations panel
            column, condition, value = self.view.operations_panel.get_filter_parameters()

            try:
                if "." in value:
                    value = float(value)
                else:
                    value = int(value)
            except ValueError:
                pass

            before = len(self.data_handler.df)
            self.data_handler.filter_data(column, condition, value)
            after = len(self.data_handler.df)
            removed = before - after

            self.view.refresh_data_view()

            self.status_bar.log_action(
                f"Filter: {column} {condition} '{value}' -> {removed:,} rows removed",
                details={
                    "column"      : column,
                    "condition"   : condition,
                    "value"       : value,
                    "rows_before" : before,
                    "rows_after"  : after,
                    "rows_removed": removed,
                    "operation"   : "filter",
                },
                level="SUCCESS",
            )

            self.view.operations_panel.filtering_tab.set_filter_active_state(
                True, f"Active: {column} {condition} '{value}'"
            )
        except Exception as ApplyFilterError:
            self.status_bar.log(
                f"Failed to execute 'Filter': {str(ApplyFilterError)}", LogLevel.ERROR
            )

    def clear_filters(self):
        """Clear filters by resetting the data to original state"""
        if self.data_handler.df is None:
            return

        self.reset_data()
        self.status_bar.log("Filters cleared and data reset to original state", LogLevel.INFO)

    def open_advanced_filter(self):
        """Open advanced filter dialog"""
        if self.data_handler.df is None:
            global_signals.request_toast(
                "No Data", "Please load data first", ToastLevel.WARNING
            )
            return

        dialog = FilterAdvancedDialog(self.data_handler, self.view)
        if dialog.exec():
            result = dialog.get_filters()
            filters = result.get("filters", [])

            if not filters:
                return

            try:
                self.data_handler.filter_data(advanced_filters=filters)

                formatted_parts = []
                for i, f_dict in enumerate(filters):
                    col = f_dict.get("column", "")
                    cond = f_dict.get("condition", "")
                    val = f_dict.get("value", "")

                    expr = f"{col} {cond} '{val}'"

                    if i == 0:
                        formatted_parts.append(expr)
                    else:
                        op = f_dict.get("logical_op") or filters[i - 1].get("logical_op") or "AND"
                        formatted_parts.append(f"{op} {expr}")

                formatted_filters = " ".join(formatted_parts)

                self.view.refresh_data_view()
                self.status_bar.log(f"Filters applied to data: {formatted_filters}", LogLevel.SUCCESS)
                global_signals.request_toast(
                    "Filter Applied", f"Filters applied to data:\n{formatted_filters}", ToastLevel.SUCCESS
                )
                self.view.operations_panel.filtering_tab.set_filter_active_state(
                    True, f"Active: {formatted_filters}"
                )
            except Exception as FilterError:
                self.status_bar.log(f"Error applying filter: {str(FilterError)}", LogLevel.ERROR)
                global_signals.request_toast(
                    "Filter Error", "Error applying filter to data", ToastLevel.ERROR
                )

    def drop_column(self):
        """Drop selected column"""
        if self.data_handler.df is None:
            return

        cols_to_drop = self.view.operations_panel.get_selected_columns()
        if not cols_to_drop:
            self.status_bar.log("No columns selected to drop", LogLevel.WARNING)
            global_signals.request_toast(
                "No Columns Selected", "Please select at least one column to drop", ToastLevel.WARNING
            )
            return

        msg = f"Are you sure you want to drop {len(cols_to_drop)} column(s)?\n\n"
        msg += ", ".join(cols_to_drop[:5])
        if len(cols_to_drop) > 5:
            msg += "..."

        confirm = QMessageBox.question(
            self.view,
            "Confirm Drop",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                cols_before = len(self.data_handler.df.columns)
                self.data_handler.clean_data("drop_column", columns=cols_to_drop)

                cols_after = len(self.data_handler.df.columns)
                self.view.refresh_data_view()

                self.status_bar.log_action(
                    f"Dropped {len(cols_to_drop)} columns",
                    details={
                        "columns"       : cols_to_drop,
                        "columns_before": cols_before,
                        "columns_after" : cols_after,
                        "operation"     : "drop_column",
                    },
                    level="SUCCESS",
                )
            except Exception as DropColumnError:
                self.status_bar.log(
                    f"Failed to drop columns: {str(DropColumnError)}", LogLevel.ERROR
                )
                global_signals.request_toast(
                    "Error", "Failed to drop columns", ToastLevel.ERROR
                )

    def rename_column(self):
        """Rename selected column"""
        selected_columns = self.view.operations_panel.get_selected_columns()

        if not selected_columns:
            self.status_bar.log("No column selected", LogLevel.WARNING)
            return

        old_name = selected_columns[0]

        existing_columns = self.data_handler.df.columns.tolist() if self.data_handler.df is not None else []
        dialog = RenameColumnDialog(old_name, existing_columns=existing_columns, parent=self.view)
        if dialog.exec():
            new_name = dialog.get_new_name()
            try:
                self.data_handler.clean_data(
                    "rename_column", old_name=old_name, new_name=new_name
                )

                self.view.refresh_data_view()
                self.status_bar.log_action(
                    f"Renamed '{old_name}' -> '{new_name}'",
                    details={
                        "old_name" : old_name,
                        "new_name" : new_name,
                        "operation": "rename_column",
                    },
                    level="SUCCESS",
                )
            except Exception as RenameColumnError:
                self.status_bar.log(
                    f"Failed to rename column: {str(RenameColumnError)}", LogLevel.ERROR
                )

    def duplicate_column(self) -> None:
        """Duplicate the selected column"""
        selected_columns = self.view.operations_panel.get_selected_columns()

        if not selected_columns:
            self.status_bar.log("No column selected", LogLevel.WARNING)
            return
        if len(selected_columns) > 1:
            global_signals.request_toast(
                "Selection Warning", "Please select only one column to duplicate", ToastLevel.WARNING
            )
            return

        col_name = selected_columns[0]
        new_col_name = f"{col_name}_copy"

        counter = 1
        while new_col_name in self.data_handler.df.columns:
            new_col_name = f"{col_name}_copy_{counter}"
            counter += 1

        try:
            self.data_handler.clean_data("duplicate_column", column=col_name, new_column=new_col_name)
            self.view.refresh_data_view()
            self.status_bar.log_action(f"Duplicated '{col_name}' to '{new_col_name}'",
                                       details={"original_column": col_name, "new_column": new_col_name,
                                                "operation"      : "duplicate_column"}, level=LogLevel.SUCCESS)
        except Exception as DuplicateColumnError:
            self.status_bar.log(f"Failed to duplicate column: {str(DuplicateColumnError)}", LogLevel.ERROR)
            global_signals.request_toast(
                "Error", "Failed to duplicate column", ToastLevel.ERROR
            )

    def open_computed_column_dialog(self):
        """Opens the dialog to create a new column from a formula"""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        columns = list(self.data_handler.df.columns)
        dialog = ComputedColumnDialog(columns, self.view)

        if dialog.exec():
            new_column, expression, data_type = dialog.get_data()
            try:
                self.data_handler.create_computed_column(new_column, expression)

                if data_type != "Auto-infer":
                    self.data_handler.clean_data("change_data_type", column=new_column, new_type=data_type)

                self.view.refresh_data_view()
                global_signals.toast_requested.emit(f"Success",
                                                    f"Computed a new column '{new_column}' of type '{data_type}'",
                                                    ToastLevel.SUCCESS, 4000)

                self.status_bar.log_action(
                    f"Created column '{new_column}' = {expression}",
                    details={
                        "new_column": new_column,
                        "expression": expression,
                        "operation" : "computed_column",
                    },
                    level="SUCCESS",
                )
            except Exception as ComputedColumnError:
                self.status_bar.log(
                    f"Failed to create and calculate new column: {str(ComputedColumnError)}",
                    LogLevel.ERROR,
                )
                global_signals.toast_requested.emit(f"Error", f"Failed to create and calculate new column",
                                                    ToastLevel.ERROR, 4000)

    def change_column_type(self):
        """Change the data type of the selected column"""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        selected_columns = self.view.operations_panel.get_selected_columns()
        if not selected_columns:
            self.status_bar.log("No Column Selected", LogLevel.WARNING)
            return

        if len(selected_columns) > 1:
            global_signals.request_toast(
                "Selection Warning",
                "Please select only one column to change datatype",
                ToastLevel.WARNING
            )
            return

        column = selected_columns[0]

        type_str = self.view.operations_panel.get_target_datatype()

        # mapping the datatypes
        if type_str.startswith("string"):
            target_type = "string"
        elif type_str.startswith("integer"):
            target_type = "int"
        elif type_str.startswith("float"):
            target_type = "float"
        elif type_str.startswith("category"):
            target_type = "category"
        elif type_str.startswith("datetime"):
            target_type = "datetime"
        else:
            self.status_bar.log(f"Unknown DataType: {type_str}", LogLevel.ERROR)
            return

        try:
            old_type = str(self.data_handler.df[column].dtype)

            # Warning for potential data loss
            if target_type in ["int", "float", "datetime"]:
                reply = QMessageBox.question(
                    self.view,
                    "Confirm DataType Conversion",
                    f"Attempting to convert column: '{column}' to {target_type}.\n\n"
                    f"This may fail or result in data loss.\n"
                    f"Invalid values will be converted to 'NaN'.\n\nContinue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    self.status_bar.log("Data Type conversion cancelled", LogLevel.WARNING)
                    return

                self.data_handler.clean_data(
                    "change_data_type", column=column, new_type=target_type
                )
                self.view.refresh_data_view()

                new_type = str(self.data_handler.df[column].dtype)

                self.status_bar.log_action(
                    f"Changed datatype of '{column}' from {old_type} to {new_type}",
                    details={
                        "column"   : column,
                        "old_type" : old_type,
                        "new_type" : new_type,
                        "operation": "change_data_type",
                    },
                    level=LogLevel.SUCCESS,
                )
        except Exception as ChangeColumnDataTypeError:
            error_msg = f"Failed to convert '{column}' to {target_type}: {str(ChangeColumnDataTypeError)}"
            global_signals.request_toast(
                "Conversion Error", f"Failed to convert '{column}' to {target_type}", ToastLevel.ERROR
            )
            self.status_bar.log(error_msg, LogLevel.ERROR)
            self.view.refresh_data_view()

    def apply_text_manipulation(self):
        """Apply the requested text manipulation to the selected column"""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        selected_columns = self.view.operations_panel.get_selected_columns()
        if not selected_columns:
            self.status_bar.log("No Column Selected", LogLevel.WARNING)
            global_signals.request_toast(
                "No Column Selected", "Please select a column", ToastLevel.WARNING
            )
            return

        if len(selected_columns) > 1:
            global_signals.request_toast(
                "Selection Warning",
                "Please Select only one column for text manipulation",
                ToastLevel.WARNING
            )
            return

        column = selected_columns[0]
        selected_operation = self.view.operations_panel.get_text_operation()

        operation_map = {
            "Trim Whitespace"         : "strip",
            "Trim leading whitespace" : "lstrip",
            "Trim trailing whitepsace": "rstrip",
            "Convert to lowercase"    : "lower",
            "Convert to UPPERCASE"    : "upper",
            "Convert to Title Case"   : "title",
            "Capitalize First Letter" : "capitalize",
        }

        operation = operation_map.get(selected_operation)

        try:
            self.data_handler.clean_data(
                "text_manipulation", column=column, operation=operation
            )
            self.view.refresh_data_view()
            self.status_bar.log_action(
                f"Applied text operation: '{selected_operation}' to '{column}'",
                details={
                    "column"   : column,
                    "operation": operation,
                    "type"     : "text_manipulation",
                },
                level="SUCCESS",
            )

            self.status_bar.log(
                f"Successfully applied '{selected_operation}' to column '{column}'",
                LogLevel.SUCCESS,
            )

        except Exception as TextManipulationError:
            global_signals.request_toast(
                "Error", "Error applying text manipulation", ToastLevel.ERROR
            )
            self.status_bar.log(
                f"Text manipulation failed: {str(TextManipulationError)}", LogLevel.ERROR
            )

    def open_split_column_dialog(self) -> None:
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        columns = list(self.data_handler.df.columns)
        dialog = SplitColumnDialog(columns, self.view)

        if dialog.exec():
            column, delimiter, new_cols = dialog.get_parameters()
            try:
                self.data_handler.clean_data("split_column", column=column, delimiter=delimiter, new_columns=new_cols)
                self.view.refresh_data_view()
            except Exception as error:
                self.view.status_bar.log(f"Failed to split column: {str(error)}", LogLevel.ERROR)
                global_signals.request_toast(
                    "Error", "Failed to split column", ToastLevel.ERROR
                )

    def open_regex_replace_dialog(self) -> None:
        """Open the dialog to configure and apply regex text replacement."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        columns = list(self.data_handler.df.columns)
        dialog = RegexReplaceDialog(columns, self.view)

        if dialog.exec():
            column, pattern, replacement = dialog.get_parameters()
            try:
                self.data_handler.clean_data(
                    "regex_replace",
                    column=column,
                    pattern=pattern,
                    replacement=replacement
                )
                self.view.refresh_data_view()
            except Exception as error:
                self.view.status_bar.log(f"Regex operation failed: {str(error)}", LogLevel.ERROR)
                global_signals.request_toast(
                    "Error", "Regex operation failed", ToastLevel.ERROR
                )

    def extract_date_component(self):
        """Extracts date components into a new column"""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        source_col, component = self.view.operations_panel.get_date_extraction_parameters()
        if not source_col or not component:
            global_signals.request_toast(
                "Missing Input",
                "Please select both a column and a date component to extract",
                ToastLevel.WARNING
            )
            return

        try:
            self.data_handler.clean_data("extract_date_component", column=source_col, component=component)
            self.view.refresh_data_view()
            self.status_bar.log_action(
                f"Extracted '{component}' from '{source_col}'",
                details={
                    "source_column": source_col,
                    "component"    : component,
                    "operation"    : "extract_date_component"
                }, level=LogLevel.SUCCESS
            )
            self.status_bar.log(f"Extracted {component} from {source_col}", LogLevel.SUCCESS)
        except Exception as ExtractError:
            self.status_bar.log(f"Date extraction failed: {str(ExtractError)}", LogLevel.ERROR)
            global_signals.request_toast(
                "Date Extraction Error", "Failed to extract date component", ToastLevel.ERROR
            )

    def calculate_date_difference(self):
        """Calculates the time difference between two date columns"""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        start_col, end_col, unit = self.view.operations_panel.get_date_diff_parameters()
        if not start_col or not end_col:
            global_signals.request_toast(
                "Missing Input", "Please select two columns", ToastLevel.WARNING
            )
            return
        if start_col == end_col:
            global_signals.request_toast(
                "Invalid Selection", "The two columns cannot be the same", ToastLevel.WARNING
            )
            return

        try:
            self.data_handler.clean_data("calculate_date_difference", start_column=start_col, end_column=end_col, unit=unit)
            self.view.refresh_data_view()

            self.status_bar.log_action(
                f"Calculated duration between '{start_col}' and '{end_col}' in {unit}",
                details={
                    "start_column": start_col,
                    "end_column"  : end_col,
                    "unit"        : unit,
                    "operation"   : "calculate_date_difference"
                }, level=LogLevel.SUCCESS
            )
            self.status_bar.log(f"Calculated duration in {unit}", LogLevel.SUCCESS)
        except Exception as CalcError:
            self.status_bar.log(f"Date calculation failed: {str(CalcError)}", LogLevel.ERROR)
            global_signals.request_toast(
                "Calculation Error", "Failed to calculate duration difference", ToastLevel.ERROR
            )

    def open_binning_dialog(self):
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        numeric_cols = self.data_handler.df.select_dtypes(include=["number"]).columns.tolist()
        df = self.data_handler.df

        if not numeric_cols:
            global_signals.request_toast(
                "No Numeric Data", "This dataset contains no numeric columns suitable for binning",
                ToastLevel.WARNING
            )
            return

        dialog = BinningDialog(numeric_cols, df, parent=self.view)
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
                        level=LogLevel.SUCCESS)
                except Exception as BinError:
                    global_signals.request_toast(
                        "Binning Error", "Failed to bin column", ToastLevel.ERROR
                    )
                    self.status_bar.log(f"Binning failed: {str(BinError)}", LogLevel.ERROR)

    def open_aggregation_dialog(self):
        """Open aggregation dialog"""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        dialog = AggregationDialog(self.data_handler, self.view)
        if dialog.exec():
            config = dialog.get_aggregation_config()
            try:
                self.data_handler.reset_data()

                group_cols = config["group_by"]
                agg_config = config["agg_config"]
                date_grouping = config.get("date_grouping")
                agg_name = config.get("aggregation_name", "")
                rename_mapping = config.get("rename_mapping")

                self.data_handler.aggregate_data(group_cols, agg_config, date_grouping, rename_mapping)
                result_df = self.data_handler.df.copy()

                # ask the user if they want ot save this agg
                if agg_name:
                    try:
                        desc_parts = [
                            f"{func}({col})" for col, func in agg_config.items()
                        ]
                        description = f"Aggregated: {', '.join(desc_parts)} by {', '.join(group_cols)}"

                        self.aggregation_manager.save_aggregation(
                            name=agg_name,
                            description=description,
                            group_by=group_cols,
                            agg_config=agg_config,
                            date_grouping=date_grouping,
                            result_df=result_df,
                            rename_mapping=config.get("rename_mapping")
                        )
                        self.refresh_saved_agg_list()
                        self.status_bar.log(f"Saved aggregation: {agg_name}", LogLevel.SUCCESS)
                    except ValueError as SaveAggregationDialogError:
                        global_signals.request_toast(
                            "Error", "Aggregation data not found", ToastLevel.ERROR
                        )
                        self.status_bar.log(
                            f"Failed to save aggregation. Aggregation data is not found: {str(SaveAggregationDialogError)}",
                            LogLevel.ERROR
                        )

                self.view.refresh_data_view()

                group_by_str = ", ".join(group_cols)

                self.status_bar.log_action(
                    f"Aggregated data by [{group_by_str}]",
                    details={
                        "group_by_columns": group_cols,
                        "agg_config"      : agg_config,
                        "date_grouping"   : date_grouping,
                        "result_rows"     : len(self.data_handler.df),
                        "operation"       : "aggregate",
                        "saved"           : bool(agg_name),
                    },
                    level=LogLevel.SUCCESS,
                )
            except Exception as AggregationDialogError:
                global_signals.request_toast(
                    "Error", "Aggregating data failed", ToastLevel.ERROR
                )
                self.status_bar.log(
                    f"Aggregation failed: {str(AggregationDialogError)}", LogLevel.ERROR
                )

    def refresh_saved_agg_list(self):
        """Refreshes the list of saved aggs"""
        try:
            agg_names = self.aggregation_manager.list_aggregations()
            data_list = []

            if agg_names:
                for name in agg_names:
                    agg = self.aggregation_manager.get_aggregation(name)
                    if agg:
                        data_list.append((name, agg.row_count))

            self.view.operations_panel.update_saved_aggregation_list(data_list)
        except Exception as RefreshAggregationListError:
            print(
                f"Warning: Could not refresh aggregation list: {str(RefreshAggregationListError)}"
            )

    def on_saved_agg_selected(self, item):
        """Handle selection of saved aggs"""
        enabled = (item is not None and item.data(Qt.ItemDataRole.UserRole) is not None)
        self.view.operations_panel.set_aggregation_buttons_enabled(enabled)

    def view_saved_aggregations(self):
        """View the current selected agg in the table"""
        agg_name = self.view.operations_panel.get_selected_saved_aggregation()
        if not agg_name:
            return

        try:
            agg_df = self.aggregation_manager.get_aggregation_df(agg_name)
            if agg_df is None:
                global_signals.request_toast(
                    "Error", "Aggregation data not found", ToastLevel.ERROR
                )
                self.status_bar.log(f"Error in viewing aggregation. Aggregation data is not found", LogLevel.ERROR)
                return

            # storing state
            if (
                    not hasattr(self.data_handler, "pre_agg_view_df")
                    or self.data_handler.pre_agg_view_df is None
            ):
                self.data_handler.pre_agg_view_df = self.data_handler.df.copy()

            self.data_handler.df = agg_df.copy()
            self.data_handler.viewing_aggregation_name = agg_name
            self.data_handler.inserted_subset_name = None
            self.view.refresh_data_view()

            agg = self.aggregation_manager.get_aggregation(agg_name)
            self.status_bar.log_action(
                f"Viewing saved aggregation: {agg_name}",
                details={
                    "aggregation_name": agg_name,
                    "rows"            : len(agg_df),
                    "columns"         : len(agg_df.columns),
                    "operation"       : "view_saved_aggregation",
                },
                level=LogLevel.INFO,
            )
            global_signals.request_toast(
                "Aggregation Loaded", f"Now viewing aggregation: {agg_name}"
            )
        except Exception as ViewAggregationError:
            global_signals.request_toast(
                "Error", "Failed to view aggregation", ToastLevel.ERROR
            )
            self.status_bar.log(f"Failed to view aggregation: {str(ViewAggregationError)}", LogLevel.ERROR)

    def delete_saved_aggregation(self):
        """Delete a saved aggregation"""
        agg_name = self.view.operations_panel.get_selected_saved_aggregation()
        if not agg_name:
            return

        reply = QMessageBox.question(
            self.view,
            "Confirm Delete",
            f"Are you sure you want to delete the saved aggregation '{agg_name}'?\n\n"
            "This will not affect your current data view.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.aggregation_manager.delete_aggregation(agg_name):
                self.refresh_saved_agg_list()
                self.view.operations_panel.set_aggregation_buttons_enabled(False)
                self.status_bar.log(f"Deleted aggregation: {agg_name}", LogLevel.SUCCESS)

    def open_melt_dialog(self):
        """Opens the melt data dialog"""
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
                    "Are you sure you want to proceed?\n"
                    "(You can Undo this operation later)",
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
            except Exception as MeltDataError:
                global_signals.request_toast(
                    "Error", "Failed to melt data", ToastLevel.ERROR
                )
                self.status_bar.log(f"Melt failed: {str(MeltDataError)}", LogLevel.ERROR)

    def open_pivot_dialog(self):
        """Opens the pivot table dialog"""
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
                    "Pivoting will restructure your entire dataset.\n\n"
                    "Are you sure you want to proceed?\n",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    before_shape = self.data_handler.df.shape

                    self.data_handler.pivot_data(index=config["index"], columns=config["columns"],
                                                 values=config["values"], aggfunc=config["aggfunc"])
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
            except Exception as PivotDataError:
                global_signals.request_toast(
                    "Error", "Failed to pivot data", ToastLevel.ERROR
                )
                self.status_bar.log(f"Pivot Failed: {str(PivotDataError)}", LogLevel.ERROR)

    def open_merge_dialog(self):
        """Opens the dialog for merging data"""
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
                    details={
                        "how"        : config["how"],
                        "rows_before": rows_before,
                        "rows_after" : rows_after,
                        "operation"  : "merge"
                    },
                    level=LogLevel.SUCCESS
                )
            except Exception as MergeError:
                global_signals.request_toast(
                    "Error", "Failed to merge datasets", ToastLevel.ERROR
                )
                self.status_bar.log(f"Merge failed: {str(MergeError)}", LogLevel.ERROR)

    def open_append_dialog(self) -> None:
        """Opens the dialog to configure and execute data concatenation."""
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
                    details={
                        "rows_before": rows_before,
                        "rows_after" : rows_after,
                        "rows_added" : rows_after - rows_before,
                        "operation"  : "concatenate"
                    },
                    level=LogLevel.SUCCESS
                )
            except Exception as AppendError:
                global_signals.request_toast(
                    "Error", "Failed to append datasets", ToastLevel.ERROR
                )
                self.status_bar.log(f"Append failed: {str(AppendError)}", LogLevel.ERROR)

    def open_rolling_window_dialog(self) -> None:
        """Opens the dialog to configure and apply a rolling window operation"""
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
                        "operation" : "rolling_window"
                    },
                    level=LogLevel.SUCCESS
                )
            except Exception as error:
                self.status_bar.log(f"Failed to apply rolling window: {str(error)}", LogLevel.ERROR)
                global_signals.request_toast(
                    "Error", "Failed to apply rolling window", ToastLevel.ERROR
                )

    def open_shift_dialog(self) -> None:
        """Opens the dialog to configure and apply a shift (lag/lead) operation"""
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
            except Exception as error:
                self.status_bar.log(f"Failed to apply shift: {str(error)}", LogLevel.ERROR)
                global_signals.request_toast(
                    "Error", "Failed to apply shift", ToastLevel.ERROR
                )

    def open_pct_change_dialog(self) -> None:
        """Opens the dialog to configure and apply a percentage change calculation"""
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
            except Exception as error:
                self.status_bar.log(f"Failed to calculate percentage change: {str(error)}", LogLevel.ERROR)
                global_signals.request_toast(
                    "Error", "Failed to calculate percentage change", ToastLevel.ERROR
                )

    def open_column_reorder_dialog(self) -> None:
        """Opens the dialog for reordering columns"""
        if self.data_handler.df is None or self.data_handler.df.empty:
            self.status_bar.log("No data available to reorder", LogLevel.WARNING)
            self.no_data_loaded_toast()
            return

        dialog = ColumnReorderDialog(df=self.data_handler.df, parent=self.view)

        if dialog.exec():
            new_order = dialog.get_new_order()

            # Preventing updates to history states if the order was not changed at all
            if new_order != list(self.data_handler.df.columns):
                try:
                    self.data_handler.clean_data(
                        action="reorder_columns",
                        new_order=new_order
                    )
                    self.status_bar.log("Columns have been reordered", LogLevel.SUCCESS)
                    self.view.refresh_data_view()
                except Exception as error:
                    self.status_bar.log(f"Failed to reorder columns: {str(error)}", LogLevel.ERROR)

    def apply_sort(self):
        """Apply a permanent sorting to data"""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        column, order_text = self.view.operations_panel.get_sort_parameters()
        if not column:
            return

        ascending = (order_text == "Ascending")

        try:
            if column == "[Index]":
                col_index = -1
            else:
                col_index = list(self.data_handler.df.columns).index(column)
            order = (
                Qt.SortOrder.AscendingOrder
                if ascending
                else Qt.SortOrder.DescendingOrder
            )

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
        except Exception as SortError:
            self.status_bar.log(f"Sort failed: {str(SortError)}", LogLevel.ERROR)
            global_signals.request_toast(
                "Error", "Failed to sort data", ToastLevel.ERROR
            )

    def quick_create_subsets(self):
        """Quick create subsets from column values"""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        column = self.view.operations_panel.get_quick_subset_column()
        if not column:
            global_signals.request_toast(
                "Feature Not Available", "Subset feature has not been fully loaded", ToastLevel.ERROR
            )
            return

        if not column:
            global_signals.request_toast(
                "No Column Selected", "Please select a column", ToastLevel.WARNING
            )
            return

        unique_count = self.data_handler.df[column].nunique()

        reply = QMessageBox.question(
            self.view,
            "Confirm",
            f"Create {unique_count} subsets (one per unique value in '{column}')?\n\n"
            f"This is useful for analyzing data by groups (e.g., by location, category, etc.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.progress_dialog = ProgressDialog(title="Auto-Creatin subsets",
                                                  message=f"Creating subsets from '{column}'...", parent=self.view)
            self.progress_dialog.setModal(True)
            self.progress_dialog.show()

            worker = AutoCreateSubsetsWorker(self.subset_manager, self.data_handler.df, column)
            worker.signals.progress.connect(self.progress_dialog.update_progress)
            worker.signals.finished.connect(
                lambda created: self._on_quick_create_subsets_finished(created, column, unique_count))
            worker.signals.error.connect(self._on_quick_create_subsets_error)

            QThreadPool.globalInstance().start(worker)

    def _on_quick_create_subsets_finished(self, created: list, column: str, unique_count: int) -> None:
        if hasattr(self, "progress_dialog"):
            self.progress_dialog.close()

        self.refresh_active_subsets()

        self.status_bar.log_action(f"Created {len(created)} subsets from column '{column}'",
                                   details={
                                       "column"         : column,
                                       "subsets_created": len(created),
                                       "unique_values"  : unique_count,
                                       "operation"      : "auto_create_subsets",
                                   },
                                   level="SUCCESS", )
        global_signals.request_toast(
            "Success", f"Created {len(created)} subsets from column '{column}'", ToastLevel.SUCCESS
        )

    def _on_quick_create_subsets_error(self, error: Exception) -> None:
        """Callback for when subset auto-creation fails in the background"""
        if hasattr(self, "progress_dialog"):
            self.progress_dialog.close()

        self.status_bar.log(
            f"Failed to create subsets: {str(error)}", LogLevel.ERROR
        )
        global_signals.request_toast(
            "Error", "Failed to create subsets", ToastLevel.ERROR
        )

    def refresh_active_subsets(self):
        """Refresh the list of active subsets"""
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            subset_data = []

            if self.data_handler.df is not None:
                for name in self.subset_manager.list_subsets():
                    try:
                        self.subset_manager.apply_subset(self.data_handler.df, name)
                    except Exception as ApplySubsetError:
                        self.status_bar.log(f"Warning: Could not apply subset {name}: {str(ApplySubsetError)}",
                                            LogLevel.WARNING)

            for name in self.subset_manager.list_subsets():
                subset = self.subset_manager.get_subset(name)
                row_text = (
                    f"{subset.row_count} rows" if subset.row_count > 0 else "? rows"
                )
                subset_data.append((name, row_text))
            self.view.operations_panel.update_active_subsets_list(subset_data)
        except Exception as RefreshSubsetListError:
            self.status_bar.log(f"Warning: Could not refresh subset list: {RefreshSubsetListError}", LogLevel.ERROR)
        finally:
            QApplication.restoreOverrideCursor()

    def view_subset_quick(self):
        """Quick view of selected subset"""
        name = self.view.operations_panel.get_selected_active_subset()
        if not name:
            return

        try:
            subset_df = self.subset_manager.apply_subset(self.data_handler.df, name)
            viewer = SubsetDataViewer(subset_df, name, self.view)
            viewer.exec()
        except Exception as ViewSubsetError:
            self.status_bar.log(f"Error viewing subset: {str(ViewSubsetError)}", LogLevel.ERROR)
            global_signals.request_toast(
                "Error", f"Failed to view subset '{name}'", ToastLevel.ERROR
            )

    def open_subset_manager(self):
        """Open the subset manager dialog"""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        try:
            from ui.dialogs import SubsetManagerDialog
            dialog = SubsetManagerDialog(self.subset_manager, self.data_handler, self.view)
            # Request redirection to index 1
            dialog.plot_subset_requested.connect(self.handle_plot_request)

            dialog.exec()
            # Refresh the subset list after dialog closes
            self.refresh_active_subsets()

        except Exception as OpenSubsetManagerError:
            self.status_bar.log(f"Failed to open subset manager dialog: {str(OpenSubsetManagerError)}", LogLevel.ERROR)
            global_signals.request_toast(
                "Error", "Failed to open subset manager dialog", ToastLevel.ERROR
            )

    def handle_plot_request(self, subset_name: str):
        """Handle the signal from SubsetManagerDialog to plot the selected subset"""
        if not self.view.plot_tab:
            global_signals.request_toast(
                "Error", "Plot tab reference is missing. Cannot switch tabs", ToastLevel.ERROR
            )
            self.status_bar.log("Plot tab reference not set", LogLevel.ERROR)
            return

        try:
            self.view.plot_tab.activate_subset(subset_name)
            self.view.switch_to_plot_tab()

        except Exception as PlotRequestError:
            self.status_bar.log(
                f"Failed to switch to plotting tab: {str(PlotRequestError)}", LogLevel.ERROR
            )
            global_signals.request_toast(
                "Error", "Failed to activate the plot tab", ToastLevel.ERROR
            )

    def inject_subset_to_dataframe(self):
        """Insert the selected subset into the active dataframe view."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        # get the selected subset
        subset_name = self.view.operations_panel.get_selected_active_subset()
        if not subset_name:
            global_signals.request_toast(
                "No Subset Selected", "Please select a subset to apply to the current data view",
                ToastLevel.WARNING
            )
            return

        reply = QMessageBox.question(
            self.view,
            "Confirm",
            f"Are you sure you want to insert the subset: '{subset_name}' into the active DataFrame\n\n"
            f"This will temporarily replace the current data view.\n"
            f"You can restore the original data view by pressing the 'Revert to Original Data View'",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # we need to store the original df first.
            if (
                    not hasattr(self.data_handler, "pre_insert_df")
                    or self.data_handler.pre_insert_df is None
            ):
                self.data_handler.pre_insert_df = self.data_handler.df.copy()
                self.data_handler.inserted_subset_name = None

            subset_df = self.subset_manager.apply_subset(
                self.data_handler.df, subset_name, use_cache=False
            )

            self.data_handler.df = subset_df.copy()
            self.data_handler.inserted_subset_name = subset_name

            self.view.refresh_data_view()

            self.view.operations_panel.set_injection_status_ui(is_subset_active=True, subset_name=subset_name)
            self.view.operations_panel.subsets_tab.restore_original_btn.setEnabled(True)
            self.view.operations_panel.subsets_tab.inject_subset_btn.setEnabled(False)

            self.status_bar.log_action(
                f"Inserted the subset: '{subset_name}' into the active DataFrame",
                details={
                    "subset_name"  : subset_name,
                    "subset_rows"  : len(subset_df),
                    "original_rows": len(self.data_handler.pre_insert_df),
                    "operation"    : "insert_subset_into_active_data_view",
                },
                level="SUCCESS",
            )

            global_signals.request_toast(
                "Insert Complete", f"Subset '{subset_name}' has been inserted into the active DataFrame",
                ToastLevel.SUCCESS
            )

        except Exception as InsertSubsetIntoDataFrameError:
            self.status_bar.log(
                f"Failed to insert the subset: {str(InsertSubsetIntoDataFrameError)}",
                LogLevel.ERROR,
            )
            global_signals.request_toast(
                "Error", "Failed to insert subset", ToastLevel.ERROR
            )

    def restore_original_dataframe(self):
        """Restore the original DataFrame into the Active Data View of the Data Table"""
        if (
                not hasattr(self.data_handler, "pre_insert_df")
                or self.data_handler.pre_insert_df is None
        ):
            global_signals.request_toast(
                "Nothing to Restore", "No inserted subset to restore from", ToastLevel.WARNING
            )
            return

        try:
            subset_name = getattr(self.data_handler, "inserted_subset_name", "Unknown")
            original_rows = len(self.data_handler.pre_insert_df)

            self.data_handler.df = self.data_handler.pre_insert_df.copy()
            self.data_handler.pre_insert_df = None
            self.data_handler.inserted_subset_name = None

            self.view.refresh_data_view()

            self.view.operations_panel.set_injection_status_ui(is_subset_active=False)

            self.status_bar.log_action(
                f"Restored original DataFrame (from subset '{subset_name}')",
                details={
                    "previous_subset": subset_name,
                    "restored_rows"  : original_rows,
                    "operation"      : "restore_original",
                },
                level="SUCCESS",
            )

            global_signals.request_toast(
                "Restore Complete", f"Original DataFrame has been restored.\nRestored: {original_rows:,} rows"
            )
        except Exception as RestoreOriginalDataFrameError:
            self.status_bar.log(
                f"Failed to restore original data: {str(RestoreOriginalDataFrameError)}",
                LogLevel.ERROR,
            )
            global_signals.request_toast(
                "Error", "Failed to restore original data", ToastLevel.ERROR
            )

    def reset_data(self):
        """Reset data to original state"""

        reply = QMessageBox.question(
            self.view,
            "Confirm Reset",
            "Are you sure you want to reset the data to its original state?\n\n"
            "This will discard all changes, "
            "restore the original dataset and delete all history.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.No:
            self.status_bar.log("Data reset cancelled", LogLevel.INFO)
            return

        try:
            rows_before = (
                len(self.data_handler.df) if self.data_handler.df is not None else 0
            )
            cols_before = (
                len(self.data_handler.df.columns)
                if self.data_handler.df is not None
                else 0
            )

            self.data_handler.reset_data()

            if hasattr(self.data_handler, "pre_insert_df"):
                self.data_handler.pre_insert_df = None
            if hasattr(self.data_handler, "inserted_subset_name"):
                self.data_handler.inserted_subset_name = None

            if hasattr(self.data_handler, "viewing_aggregation_name"):
                self.data_handler.viewing_aggregation_name = None
            if hasattr(self.data_handler, "pre_agg_view_df"):
                self.data_handler.pre_agg_view_df = None

            if hasattr(self.view, "operations_panel"):
                self.view.operations_panel.set_injection_status_ui(is_subset_active=False)

            self.view.operations_panel.filtering_tab.set_filter_active_state(False)

            rows_after = (
                len(self.data_handler.df) if self.data_handler.df is not None else 0
            )
            cols_after = (
                len(self.data_handler.df.columns)
                if self.data_handler.df is not None
                else 0
            )

            self.view.refresh_data_view()
            global_signals.request_toast(
                "Data Reset to Original State",
                "Data has been reset to show the original data",
                ToastLevel.SUCCESS
            )
            self.status_bar.log_action(
                "Data reset to original state",
                details={
                    "rows_restored": rows_after - rows_before,
                    "cols_restored": cols_after - cols_before,
                    "final_rows"   : rows_after,
                    "final_cols"   : cols_after,
                    "operation"    : "reset_data",
                },
                level="SUCCESS",
            )
        except Exception as ResetDataError:
            self.status_bar.log(f"Failed to reset data: {str(ResetDataError)}", LogLevel.ERROR)
            global_signals.request_toast("Reset Data Error", "Failed to reset data", ToastLevel.ERROR)

    def show_help_dialog(self, topic_id: str = None):
        """Displays the help dialog for a specific topic"""
        if not isinstance(topic_id, str):
            pass

        try:
            title, description, link = self.help_manager.get_help_topic(topic_id)

            if title:
                dialog = HelpDialog(self.view, topic_id, title, description, link)
                dialog.exec()
            else:
                global_signals.request_toast(
                    "Help Not Found", f"No help topic found for '{topic_id}'", ToastLevel.WARNING
                )
        except Exception as ShowHelpDialogError:
            self.status_bar.log(
                f"Error displaying help dialog: {str(ShowHelpDialogError)}", LogLevel.ERROR
            )
            global_signals.request_toast(
                "Help Error", "Could not load help content. See log for details", ToastLevel.ERROR
            )

    def jump_to_history_state(self, target_node_id: str) -> None:
        """Jumps to a state node in the history tree"""
        try:
            self.data_handler.jump_to_history_index(target_node_id)
            self.view.refresh_data_view()

            self.view.operations_panel.select_history_item_by_index(target_node_id)
        except Exception as HistoryError:
            self.status_bar.log(f"Failed to go to state: {str(HistoryError)}", LogLevel.ERROR)

    def on_history_clicked(self, item):
        """Handles the click of a history entry from the history widget"""
        if not item:
            return

        target_index = item.data(Qt.ItemDataRole.UserRole)
        self.jump_to_history_state(target_index)

    def save_pipeline_macro(self) -> None:
        """Saves the current data operations to a JSON file"""
        if not self.data_handler.operation_log:
            global_signals.request_toast(
                "No Operations Logged", "There are no data operations in the history to save as a macro",
                ToastLevel.WARNING
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self.view,
            "Save Macro",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            try:
                self.data_handler.export_pipeline_macro(file_path)
                self.status_bar.log(f"Macro saved to {file_path}", LogLevel.SUCCESS)
            except Exception as err:
                self.status_bar.log(f"Failed to save pipeline macro: {str(err)}", LogLevel.ERROR)

    def load_pipeline_macro(self) -> None:
        """Loads a JSON macro file and executes the pipeline on the currently active DataFrame."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self.view,
            "Load Macro",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            preview_dialog = MacroPreviewDialog(filepath=file_path, parent=self.view)
            if preview_dialog.exec() == QDialog.DialogCode.Accepted:
                ops_to_execute = preview_dialog.get_selected_operations()
                try:
                    self.data_handler.apply_pipeline_macro(ops_to_execute)
                    self.view.refresh_data_view()
                    self.status_bar.log(f"Applied pipeline macro from {file_path}", LogLevel.SUCCESS)
                except Exception as err:
                    self.status_bar.log(f"Applying macro failed: {str(err)}", LogLevel.ERROR)
                    global_signals.request_toast(
                        "Error", "Macro Execution Failed", ToastLevel.ERROR
                    )

    def run_statistical_test_from_selection(self) -> None:
        """Handles the selection of columns and trigger a statistical test or opens the workspace"""
        self.stats_controller.run_statistical_test_from_selection()

    def export_data(self) -> None:
        """Handles exporting the dataframe to a file or clipboard"""
        self.dataset_controller.export_data()