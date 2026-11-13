from typing import Callable, Optional

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractButton, QMessageBox

from src.controller.data_controllers.base_data_controller import BaseDataController
from src.core.global_signals import global_signals
from src.ui.dialogs import FillMissingDialog, OutlierDetectionDialog
from src.ui.status_bar import LogLevel
from src.ui.widgets.ToastNotification import ToastLevel

class CleaningController(BaseDataController):
    """
    Subcontroller dedicated to dataset cleaning operations
    Missing values, duplicates, outlier detections, normalization
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._preview_msg_box: Optional[QMessageBox] = None

    def _prompt_row_removal_preview(
            self,
            row_indices: set[int],
            empty_message: str,
            prompt_text: str,
            cancel_log: str,
            on_confirm_callback: Callable[[], None]
    ) -> None:
        """Highlights target rows in the table view and display a confirmation box prompt telling how many rows are
        affected"""
        if self._preview_msg_box is not None:
            self._preview_msg_box.close()

        if not row_indices:
            global_signals.request_toast("Info", empty_message, ToastLevel.INFO)
            return

        table_model = self.view.data_table.model()
        if table_model is not None:
            table_model.set_highlighted_rows(row_indices)

        self._preview_msg_box = QMessageBox(self.view)
        self._preview_msg_box.setIcon(QMessageBox.Icon.Question)
        self._preview_msg_box.setWindowTitle("Confirm Removal")
        self._preview_msg_box.setText(prompt_text)
        self._preview_msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        self._preview_msg_box.setWindowModality(Qt.WindowModality.NonModal)

        def handle_response(button: QAbstractButton) -> None:
            current_model = self.view.data_table.model()
            if current_model is not None:
                current_model.set_highlighted_rows(set())

            if self._preview_msg_box and (
                    self._preview_msg_box.standardButton(button) == QMessageBox.StandardButton.Yes
            ):
                on_confirm_callback()
            else:
                self.status_bar.log(cancel_log, LogLevel.INFO)

            if self._preview_msg_box is not None:
                self._preview_msg_box.deleteLater()
                self._preview_msg_box = None

        self._preview_msg_box.buttonClicked.connect(handle_response)
        self._preview_msg_box.show()

    def remove_duplicates(self) -> None:
        if self.data_handler.df is None:
            return

        try:
            df = self.data_handler.df
            duplicate_mask = df.duplicated(keep="first")
            duplicate_indices: set[int] = set(df.index[duplicate_mask].tolist())
            self._prompt_row_removal_preview(
                row_indices=duplicate_indices,
                empty_message="No duplicate rows found",
                prompt_text=f"Found {len(duplicate_indices)} duplicate row(s) (highlighted in red)",
                cancel_log="Remove duplicates cancelled",
                on_confirm_callback=self._execute_remove_duplicates,
            )
        except (ValueError, KeyError, TypeError) as err:
            self.status_bar.log(
                f"Faled to prepare dubplicate row preview: {err}", LogLevel.ERROR
            )

    def _execute_remove_duplicates(self) -> None:
        try:
            before = len(self.data_handler.df)
            self.data_handler.clean_data("drop_duplicates")
            after = len(self.data_handler.df)

            self.view.refresh_data_view()

            self.status_bar.log_action(
                f"Removed {before - after:,} duplicate row(s)",
                details={"rows_removed": before - after, "operation": "drop_duplicates"},
                level="SUCCESS"
            )
        except Exception as e:
            self.status_bar.log(f"Failed to remove duplicates: {str(e)}", LogLevel.ERROR)

    def drop_missing(self) -> None:
        if self.data_handler.df is None:
            return

        try:
            df = self.data_handler.df
            missing_mask = df.isnull().any(axis=1)
            missing_indices: set[int] = set(df.index[missing_mask].tolist())
            self._prompt_row_removal_preview(
                row_indices=missing_indices,
                empty_message="No rows with missing values found",
                prompt_text=f"Found {len(missing_indices)} row(s) with missing values",
                cancel_log="Drop missing cancelled",
                on_confirm_callback=self._execute_drop_missing,
            )
        except (ValueError, KeyError, TypeError) as err:
            self.status_bar.log(
                f"Failed to prepare missing values preview: {err}", LogLevel.ERROR
            )

    def _execute_drop_missing(self) -> None:
        try:
            before = len(self.data_handler.df)
            self.data_handler.clean_data("drop_missing")
            removed = before - len(self.data_handler.df)

            self.view.refresh_data_view()
            self.status_bar.log_action(
                f"Dropped {removed:,} row(s) with missing values",
                details={"rows_removed": removed, "operation": "drop_missing"},
                level="SUCCESS",
            )
        except Exception as e:
            self.status_bar.log(f"Failed to drop missing values: {str(e)}", LogLevel.ERROR)

    def drop_empty_columns(self) -> None:
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        cols_before = len(self.data_handler.df.columns)
        try:
            self.data_handler.clean_data("drop_empty_columns")
            removed = cols_before - len(self.data_handler.df.columns)

            if removed == 0:
                global_signals.request_toast("Info", "No completely empty columns found", ToastLevel.INFO)
                return

            self.view.refresh_data_view()
            self.status_bar.log_action(
                f"Dropped {removed} empty column(s)",
                details={"columns_removed": removed, "operation": "drop_empty_columns"},
                level=LogLevel.SUCCESS
            )
        except Exception as e:
            self.status_bar.log(f"Failed to drop empty columns: {str(e)}", LogLevel.ERROR)

    def fill_missing(self) -> None:
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        try:
            columns = list(self.data_handler.df.columns)
            dialog = FillMissingDialog(columns, df=self.data_handler.df, parent=self.view)

            if dialog.exec():
                config = dialog.get_config()
                missing_before = self.data_handler.df.isnull().sum().sum()

                self.data_handler.clean_data(
                    "fill_missing", column=config["column"],
                    method=config["method"], value=config["value"]
                )

                missing_after = self.data_handler.df.isnull().sum().sum()
                self.view.refresh_data_view()

                self.status_bar.log_action(
                    f"Filled {missing_before - missing_after:,} missing values in {config['column']}",
                    details={"operation": "fill_missing"},
                    level="SUCCESS"
                )
        except Exception as e:
            self.status_bar.log(f"Failed 'Fill Missing values': {str(e)}", LogLevel.ERROR)

    def open_outlier_dialog(self, method: str) -> None:
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        dialog = OutlierDetectionDialog(self.data_handler, method, self.view)
        if dialog.exec():
            self.view.refresh_data_view()
            self.status_bar.log_action(
                f"Removed {len(dialog.outlier_indices)} outliers using {method}",
                details={"method": method, "operation": "remove_outliers"},
                level="SUCCESS"
            )

    def _confirm_integer_to_float_conversion(self, selected_columns: list[str]) -> bool:
        """Check if any selected columns are int type and ask to convert to float before doing normalisation"""

        df: Optional[pd.DataFrame] = self.data_handler.df
        if df is None:
            return False

        int_columns: list[str] = [
            col for col in selected_columns
            if col in df.columns and pd.api.types.is_integer_dtype(df[col].dtype)
        ]
        if not int_columns:
            return True

        col_names_str: str = ", ".join(f"'{col}'" for col in int_columns)
        message: str = (
            f"The following selected column(s) have an integer datatype: {col_names_str}.\n\n"
            "These columns will be converted to float before normalisation.\n"
            "Do you want to continue?"
        )
        reply: QMessageBox.StandardButton = QMessageBox.question(
            self.view,
            "Convert integer to float",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            self.status_bar.log("Normalisation cancelled", LogLevel.INFO)
            return False

        for col in int_columns:
            self.data_handler.clean_data("change_data_type", column=col, new_type="float")
        return True

    def apply_normalization(self) -> None:
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        selected_columns: list[str] = self.view.operations_panel.get_selected_columns()
        if not selected_columns:
            global_signals.request_toast(
                "No Columns Selected", "You have not selected a column", ToastLevel.WARNING
            )
            return

        if not self._confirm_integer_to_float_conversion(selected_columns):
            return

        method_display: str = self.view.operations_panel.get_normalization_method()
        method_map: dict[str, str] = {
            "Min-Max" : "min_max",
            "Standard": "standard",
            "Median"  : "quantile",
        }
        method: str = next(
            (val for key, val in method_map.items() if method_display.startswith(key)), "min_max"
        )
        try:
            self.data_handler.clean_data("normalize", columns=selected_columns, method=method)
            self.view.refresh_data_view()
            self.status_bar.log_action(
                f"Applied {method_display} to {len(selected_columns)} column(s)",
                details={
                    "method"   : method,
                    "operation": "normalize_data"
                },
                level=LogLevel.SUCCESS
            )
            global_signals.request_toast(
                "Success", "Normalization applied", ToastLevel.SUCCESS
            )
        except TypeError as err:
            self.status_bar.log(f"Normalization type error: {str(err)}", LogLevel.ERROR)
            global_signals.request_toast(
                "Normalization Error",
                "Selected columns must contain numeric data for normalization",
                ToastLevel.ERROR
            )
        except (ValueError, KeyError, RuntimeError) as err:
            self.status_bar.log(f"Normalization failed: {str(err)}", LogLevel.ERROR)
            global_signals.request_toast(
                "Normalization Error",
                "Failed to normalize selected columns",
                ToastLevel.ERROR
            )
