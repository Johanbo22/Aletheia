from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

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

    def remove_duplicates(self) -> None:
        if self.data_handler.df is None:
            return
        if self._preview_msg_box is not None:
            self._preview_msg_box.close()

        try:
            df = self.data_handler.df
            duplicate_mask = df.duplicated(keep="first")
            duplicate_indices = set(df.index[duplicate_mask].tolist())

            if not duplicate_indices:
                global_signals.request_toast("Info", "No duplicate rows found", ToastLevel.INFO)
                return

            if self.view.data_table.model() is not None:
                self.view.data_table.model().set_highlighted_rows(duplicate_indices)

            self._preview_msg_box = QMessageBox(self.view)
            self._preview_msg_box.setIcon(QMessageBox.Icon.Question)
            self._preview_msg_box.setWindowTitle("Confirm Removal")
            self._preview_msg_box.setText(f"Found {len(duplicate_indices)} duplicate row(s) (highlighted).")
            self._preview_msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            self._preview_msg_box.setWindowModality(Qt.WindowModality.NonModal)

            def handle_response(button) -> None:
                if self.view.data_table.model() is not None:
                    self.view.data_table.model().set_highlighted_rows(set())

                if self._preview_msg_box.standardButton(button) == QMessageBox.StandardButton.Yes:
                    self._execute_remove_duplicates()
                else:
                    self.status_bar.log("Remove duplicates cancelled.", LogLevel.INFO)

                self._preview_msg_box.deleteLater()
                self._preview_msg_box = None

            self._preview_msg_box.buttonClicked.connect(handle_response)
            self._preview_msg_box.show()

        except Exception as e:
            self.status_bar.log(f"Failed to prepare duplicate preview {str(e)}", LogLevel.ERROR)

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
        if self._preview_msg_box is not None:
            self._preview_msg_box.close()

        try:
            df = self.data_handler.df
            missing_mask = df.isnull().any(axis=1)
            missing_indices = set(df.index[missing_mask].tolist())

            if not missing_indices:
                global_signals.request_toast("Info", "No rows with missing values found", ToastLevel.INFO)
                return

            if self.view.data_table.model() is not None:
                self.view.data_table.model().set_highlighted_rows(missing_indices)

            self._preview_msg_box = QMessageBox(self.view)
            self._preview_msg_box.setIcon(QMessageBox.Icon.Question)
            self._preview_msg_box.setWindowTitle("Confirm Removal")
            self._preview_msg_box.setText(f"Found {len(missing_indices)} row(s) with missing values.")
            self._preview_msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            self._preview_msg_box.setWindowModality(Qt.WindowModality.NonModal)

            def handle_response(button) -> None:
                if self.view.data_table.model() is not None:
                    self.view.data_table.model().set_highlighted_rows(set())

                if self._preview_msg_box.standardButton(button) == QMessageBox.StandardButton.Yes:
                    self._execute_drop_missing()
                else:
                    self.status_bar.log("Drop missing cancelled.", LogLevel.INFO)

                self._preview_msg_box.deleteLater()
                self._preview_msg_box = None

            self._preview_msg_box.buttonClicked.connect(handle_response)
            self._preview_msg_box.show()

        except Exception as e:
            self.status_bar.log(f"Failed to prepare missing values preview: {str(e)}", LogLevel.ERROR)

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

    def apply_normalization(self) -> None:
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        selected_columns = self.view.operations_panel.get_selected_columns()
        if not selected_columns:
            global_signals.request_toast("Warning", "No columns selected", ToastLevel.WARNING)
            return

        method_display = self.view.operations_panel.get_normalization_method()
        method_map = {"Min-Max": "min_max", "Standard": "standard", "Median": "quantile"}
        method = next((v for k, v in method_map.items() if method_display.startswith(k)), "min_max")

        try:
            self.data_handler.clean_data("normalize", columns=selected_columns, method=method)
            self.view.refresh_data_view()
            self.status_bar.log_action(
                f"Applied {method_display} to {len(selected_columns)} column(s)",
                details={"method": method, "operation": "normalize_data"}, level="SUCCESS"
            )
            global_signals.request_toast("Success", "Normalization applied", ToastLevel.SUCCESS)
        except TypeError as e:
            self.status_bar.log(f"Normalization type error: {str(e)}", LogLevel.ERROR)
            global_signals.request_toast("Error", "Type Error during Normalization", ToastLevel.ERROR)
        except Exception as e:
            self.status_bar.log(f"Normalization failed: {str(e)}", LogLevel.ERROR)
