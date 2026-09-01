from PyQt6.QtWidgets import QMessageBox

from src.controller.data_controllers.base_data_controller import BaseDataController
from src.core.global_signals import global_signals
from src.ui.dialogs import (
    ComputedColumnDialog,
    RegexReplaceDialog,
    RenameColumnDialog,
    SplitColumnDialog
)
from src.ui.status_bar import LogLevel
from src.ui.widgets.ToastNotification import ToastLevel

class ColumnController(BaseDataController):
    """
    Sub-controller handling column-level operations
    """

    def __init__(self, data_handler, status_bar, view, subset_manager) -> None:
        super().__init__(data_handler, status_bar, view, subset_manager)
        self.hidden_columns: set[str] = set()

    def set_column_visibility(self, column_name: str, visible: bool) -> None:
        """Set the visibility of a single column"""
        if visible:
            self.hidden_columns.discard(column_name)
        else:
            self.hidden_columns.add(column_name)
        self.apply_column_visibility()

    def show_all_columns(self) -> None:
        """Show all columns in the table view"""
        self.hidden_columns.clear()
        self.apply_column_visibility()

    def hide_all_columns(self) -> None:
        """Hide all columns in the table view"""
        if self.data_handler.df is not None:
            self.hidden_columns = set(self.data_handler.df.columns)
        self.apply_column_visibility()

    def apply_column_visibility(self) -> None:
        """Applies hidden state of columns to the main data view"""
        if self.data_handler.df is None or self.view.data_table is None:
            return

        df_cols = list(self.data_handler.df.columns)
        self.hidden_columns = {col for col in self.hidden_columns if col in df_cols}

        for idx, col in enumerate(df_cols):
            is_hidden = col in self.hidden_columns
            self.view.data_table.setColumnHidden(idx, is_hidden)

    def drop_column(self) -> None:
        """Drop selected columns from the dataset."""
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
                    level=LogLevel.SUCCESS,
                )
            except Exception as e:
                self.status_bar.log(f"Failed to drop columns: {str(e)}", LogLevel.ERROR)
                global_signals.request_toast("Error", "Failed to drop columns", ToastLevel.ERROR)

    def rename_column(self) -> None:
        """Rename the selected column."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        selected_columns = self.view.operations_panel.get_selected_columns()

        if not selected_columns:
            self.status_bar.log("No column selected", LogLevel.WARNING)
            return

        if len(selected_columns) > 1:
            global_signals.request_toast(
                "Selection Warning", "Please select only one column to rename", ToastLevel.WARNING
            )
            return

        old_name = selected_columns[0]
        existing_columns = self.data_handler.df.columns.tolist()

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
                    level=LogLevel.SUCCESS,
                )
            except Exception as e:
                self.status_bar.log(f"Failed to rename column: {str(e)}", LogLevel.ERROR)

    def duplicate_column(self) -> None:
        """Duplicate the selected column."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

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
            self.status_bar.log_action(
                f"Duplicated '{col_name}' to '{new_col_name}'",
                details={"original_column": col_name, "new_column": new_col_name, "operation": "duplicate_column"},
                level=LogLevel.SUCCESS
            )
        except Exception as e:
            self.status_bar.log(f"Failed to duplicate column: {str(e)}", LogLevel.ERROR)
            global_signals.request_toast("Error", "Failed to duplicate column", ToastLevel.ERROR)

    def open_computed_column_dialog(self) -> None:
        """Opens the dialog to create a new column via a mathematical or logical formula."""
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
                global_signals.toast_requested.emit(
                    "Success", f"Computed a new column '{new_column}' of type '{data_type}'", ToastLevel.SUCCESS, 4000
                )

                self.status_bar.log_action(
                    f"Created column '{new_column}' = {expression}",
                    details={"new_column": new_column, "expression": expression, "operation": "computed_column"},
                    level=LogLevel.SUCCESS,
                )
            except Exception as e:
                self.status_bar.log(f"Failed to create and calculate new column: {str(e)}", LogLevel.ERROR)
                global_signals.toast_requested.emit(
                    "Error", "Failed to create and calculate new column", ToastLevel.ERROR, 4000
                )

    def change_column_type(self) -> None:
        """Change the internal pandas data type of the selected column."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        selected_columns = self.view.operations_panel.get_selected_columns()
        if not selected_columns:
            self.status_bar.log("No Column Selected", LogLevel.WARNING)
            return

        if len(selected_columns) > 1:
            global_signals.request_toast(
                "Selection Warning", "Please select only one column to change datatype", ToastLevel.WARNING
            )
            return

        column = selected_columns[0]
        type_str = self.view.operations_panel.get_target_datatype()

        # Route standard UI types to backend types
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

            self.data_handler.clean_data("change_data_type", column=column, new_type=target_type)
            self.view.refresh_data_view()

            new_type = str(self.data_handler.df[column].dtype)
            self.status_bar.log_action(
                f"Changed datatype of '{column}' from {old_type} to {new_type}",
                details={"column": column, "old_type": old_type, "new_type": new_type, "operation": "change_data_type"},
                level=LogLevel.SUCCESS,
            )
        except Exception as e:
            error_msg = f"Failed to convert '{column}' to {target_type}: {str(e)}"
            global_signals.request_toast(
                "Conversion Error", f"Failed to convert '{column}' to {target_type}", ToastLevel.ERROR
            )
            self.status_bar.log(error_msg, LogLevel.ERROR)
            self.view.refresh_data_view()

    def apply_text_manipulation(self) -> None:
        """Apply a standard text operation (e.g. trim, lower) to the selected string column."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        selected_columns = self.view.operations_panel.get_selected_columns()
        if not selected_columns:
            self.status_bar.log("No Column Selected", LogLevel.WARNING)
            global_signals.request_toast("No Column Selected", "Please select a column", ToastLevel.WARNING)
            return

        if len(selected_columns) > 1:
            global_signals.request_toast(
                "Selection Warning", "Please Select only one column for text manipulation", ToastLevel.WARNING
            )
            return

        column = selected_columns[0]
        selected_operation = self.view.operations_panel.get_text_operation()

        operation_map = {
            "Trim Whitespace"         : "strip",
            "Trim leading whitespace" : "lstrip",
            "Trim trailing whitespace": "rstrip",
            "Convert to lowercase"    : "lower",
            "Convert to UPPERCASE"    : "upper",
            "Convert to Title Case"   : "title",
            "Capitalize First Letter" : "capitalize",
        }

        operation = operation_map.get(selected_operation)
        if not operation:
            self.status_bar.log(f"Unknown text operation requested: '{selected_operation}'", LogLevel.ERROR)
            return

        try:
            self.data_handler.clean_data("text_manipulation", column=column, operation=operation)
            self.view.refresh_data_view()
            self.status_bar.log_action(
                f"Applied text operation: '{selected_operation}' to '{column}'",
                details={"column": column, "operation": operation, "type": "text_manipulation"},
                level=LogLevel.SUCCESS,
            )
        except Exception as e:
            global_signals.request_toast("Error", "Error applying text manipulation", ToastLevel.ERROR)
            self.status_bar.log(f"Text manipulation failed: {str(e)}", LogLevel.ERROR)

    def open_split_column_dialog(self) -> None:
        """Open the dialog to split a single column into multiple using a delimiter."""
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
                global_signals.request_toast("Error", "Failed to split column", ToastLevel.ERROR)

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
                    "regex_replace", column=column, pattern=pattern, replacement=replacement
                )
                self.view.refresh_data_view()
            except Exception as error:
                self.view.status_bar.log(f"Regex operation failed: {str(error)}", LogLevel.ERROR)
                global_signals.request_toast("Error", "Regex operation failed", ToastLevel.ERROR)

    def extract_date_component(self) -> None:
        """Extracts date components (Year, Month, etc.) into a new column."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        source_col, component = self.view.operations_panel.get_date_extraction_parameters()
        if not source_col or not component:
            global_signals.request_toast(
                "Missing Input", "Please select both a column and a date component to extract", ToastLevel.WARNING
            )
            return

        try:
            self.data_handler.clean_data("extract_date_component", column=source_col, component=component)
            self.view.refresh_data_view()
            self.status_bar.log_action(
                f"Extracted '{component}' from '{source_col}'",
                details={"source_column": source_col, "component": component, "operation": "extract_date_component"},
                level=LogLevel.SUCCESS
            )
        except Exception as e:
            self.status_bar.log(f"Date extraction failed: {str(e)}", LogLevel.ERROR)
            global_signals.request_toast("Date Extraction Error", "Failed to extract date component", ToastLevel.ERROR)

    def calculate_date_difference(self) -> None:
        """Calculates the time duration between two date columns."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        start_col, end_col, unit = self.view.operations_panel.get_date_diff_parameters()
        if not start_col or not end_col:
            global_signals.request_toast("Missing Input", "Please select two columns", ToastLevel.WARNING)
            return
        if start_col == end_col:
            global_signals.request_toast("Invalid Selection", "The two columns cannot be the same", ToastLevel.WARNING)
            return

        try:
            self.data_handler.clean_data("calculate_date_difference", start_column=start_col, end_column=end_col,
                                         unit=unit)
            self.view.refresh_data_view()

            self.status_bar.log_action(
                f"Calculated duration between '{start_col}' and '{end_col}' in {unit}",
                details={
                    "start_column": start_col,
                    "end_column"  : end_col,
                    "unit"        : unit,
                    "operation"   : "calculate_date_difference"
                },
                level=LogLevel.SUCCESS
            )
        except Exception as e:
            self.status_bar.log(f"Date calculation failed: {str(e)}", LogLevel.ERROR)
            global_signals.request_toast("Calculation Error", "Failed to calculate duration difference",
                                         ToastLevel.ERROR)
