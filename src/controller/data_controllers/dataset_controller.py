from pathlib import Path
from typing import Optional

import pandas as pd
from PyQt6.QtCore import QThreadPool, Qt
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from src.controller.data_controllers.base_data_controller import BaseDataController
from src.core.global_signals import global_signals
from src.ui.dialogs import CreateDatasetDialog, ProgressDialog
from src.ui.dialogs.ExportDialog import ExportConfig, ExportDialog
from src.ui.status_bar import LogLevel
from src.ui.widgets.ToastNotification import ToastLevel
from src.ui.workers import GoogleSheetsImportWorker

class DatasetController(BaseDataController):
    """
    Sub-controller managing:
    - Dataset creation
    - External source refresh (mainly Google Sheets)
    - Export data
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.rows_before_refresh = 0
        self.progress_dialog: Optional[ProgressDialog] = None

    def create_new_dataset(self) -> None:
        try:
            dialog = CreateDatasetDialog(self.view)
            if not dialog.exec():
                return

            params = dialog.get_dataset_parameters()
            fill_display = "Missing Values (NaN)" if params["fill_value"] == "NaN" else f"'{params['fill_value']}'"

            confirm = QMessageBox.question(
                self.view,
                "Confirm Dataset Creation",
                f"Create a new dataset with the following?\n\n"
                f"- Dimensions: {params['rows']:,} rows x {params['columns']:,} columns\n"
                f"- Initial Data State: {fill_display}\n\n"
                f"Warning: This will clear the current data view entirely.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                self.data_handler.create_empty_dataframe(
                    params["rows"], params["columns"],
                    column_names=params["column_names"], fill_value=params["fill_value"]
                )
                self.view.toolbar.set_refresh_visible(False)
                self.view.refresh_data_view()
                self.status_bar.log(f"Created New dataset: ({params['rows']}x{params['columns']})", LogLevel.SUCCESS)
                global_signals.request_toast(
                    "Created New Dataset",
                    f"Created a new dataset with {params['rows']} rows x {params['columns']} columns",
                    ToastLevel.SUCCESS
                )
        except (ValueError, TypeError, RuntimeError, MemoryError) as e:
            global_signals.request_toast(
                "Error", "Failed to create dataset", ToastLevel.ERROR
            )
            self.status_bar.log(f"Failed to create dataset: {str(e)}", LogLevel.ERROR)

    def refresh_google_sheets(self) -> None:
        if not self.data_handler.has_google_sheets_import():
            global_signals.request_toast(
                "Warning", "No Google Sheets import data found", ToastLevel.WARNING
            )
            return

        reply = QMessageBox.question(
            self.view,
            "Confirm Data Refresh",
            "Refreshing from Google Sheets will overwrite the current dataset.\n"
            "Any modifications will be lost.\n\nAre you sure you want to proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return

        self._execute_sheet_refresh()

    def _execute_sheet_refresh(self) -> None:
        """Internal execution of the worker thread for refreshing sheets."""
        sheet_id = self.data_handler.last_gsheet_id
        thousands = self.data_handler.last_gsheet_thousands
        thousands_param = None if thousands in [None, "None", ""] else thousands

        self.progress_dialog = ProgressDialog(
            title="Refreshing Google Sheets Data",
            message=f"Reconnecting to {sheet_id}",
            parent=self.view
        )
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()

        self.rows_before_refresh = len(self.data_handler.df) if self.data_handler.df is not None else 0

        worker = GoogleSheetsImportWorker(
            self.data_handler,
            sheet_id,
            self.data_handler.last_gsheet_name,
            self.data_handler.last_gsheet_delimiter,
            self.data_handler.last_gsheet_decimal,
            thousands_param,
            self.data_handler.last_gsheet_gid
        )
        worker.signals.progress.connect(self.progress_dialog.update_progress)
        worker.signals.finished.connect(self.on_refresh_google_sheets_finished)
        worker.signals.error.connect(self.on_refresh_google_sheets_error)

        QThreadPool.globalInstance().start(worker)

    def on_refresh_google_sheets_finished(self, df: pd.DataFrame) -> None:
        if self.progress_dialog:
            self.progress_dialog.close()

        self.data_handler.df = df

        rows_after = len(df)
        rows_diff = rows_after - self.rows_before_refresh

        self.view.refresh_data_view()
        sheet_identifier = self.data_handler.last_gsheet_name or f"GID: {self.data_handler.last_gsheet_gid}"

        self.status_bar.log_action(
            f"Refreshed Google Sheets data: {self.data_handler.last_gsheet_id}",
            details={
                "sheet_name"  : sheet_identifier,
                "rows_changed": rows_diff,
                "operation"   : "refresh_google_sheets"
            },
            level="SUCCESS"
        )
        global_signals.request_toast("Success", "Google Sheets data refreshed", ToastLevel.SUCCESS)

    def on_refresh_google_sheets_error(self, error: Exception) -> None:
        if self.progress_dialog:
            self.progress_dialog.close()

        self.status_bar.log(f"Failed to refresh Google Sheets: {str(error)}", LogLevel.ERROR)
        global_signals.request_toast(
            "Error",
            "Failed to refresh Google Sheets. Check connection or sharing settings.",
            ToastLevel.ERROR
        )

    def export_data(self) -> None:
        if self.data_handler.df is None:
            global_signals.request_toast("Warning", "No data to export", ToastLevel.WARNING)
            return

        selected_rows, selected_cols = self.view.get_selection_state()
        dialog = ExportDialog(
            self.view, data_handler=self.data_handler,
            selected_rows=selected_rows, selected_columns=selected_cols
        )

        if dialog.exec():
            config: ExportConfig = dialog.get_export_config()
            df_to_export = self._prepare_export_dataframe(config, selected_rows)

            if df_to_export is None:
                return

            if config.to_clipboard:
                self._export_to_clipboard(df_to_export, config.include_index)
            else:
                self._export_to_file(df_to_export, config)

    def _prepare_export_dataframe(self, config: ExportConfig, selected_rows: list[int]) -> Optional[pd.DataFrame]:
        df = self.data_handler.df

        if config.selected_rows_only:
            if not selected_rows:
                global_signals.request_toast("Warning", "No rows selected for export", ToastLevel.WARNING)
                return None
            try:
                df = df.iloc[selected_rows]
            except IndexError as e:
                self.status_bar.log(f"Row slicing error: {str(e)}", LogLevel.ERROR)
                global_signals.request_toast("Error", "Row bounds error during export", ToastLevel.ERROR)
                return None

        if config.specific_columns:
            if not config.selected_columns:
                global_signals.request_toast("Warning", "No columns selected", ToastLevel.WARNING)
                return None
            df = df[config.selected_columns]

        return df

    def _export_to_clipboard(self, df: pd.DataFrame, include_index: bool) -> None:
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            df.to_clipboard(excel=True, index=include_index)
            rows, cols = df.shape
            global_signals.request_toast("Copied", f"Copied {rows:,} rows x {cols:,} cols to clipboard")
            self.status_bar.log("Exported to Clipboard", LogLevel.SUCCESS)
        except Exception as e:
            self.status_bar.log(f"Clipboard export failed: {str(e)}", LogLevel.ERROR)
            global_signals.request_toast("Error", "Clipboard copy failed", ToastLevel.ERROR)
        finally:
            QApplication.restoreOverrideCursor()

    def _export_to_file(self, df: pd.DataFrame, config: ExportConfig) -> None:
        format_config = ExportDialog.EXPORT_CONFIG.get(config.format, {})
        filepath, _ = QFileDialog.getSaveFileName(
            self.view, "Export Data", f"export{format_config.get('ext', '')}", format_config.get("filter", "")
        )

        if not filepath:
            return

        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            method_name = format_config.get("method")
            if not method_name:
                raise ValueError(f"No export method defined for {config.format}")

            export_kwargs = format_config.get("kwargs", {}).copy()
            if config.format == "JSON":
                export_kwargs["orient"] = "columns" if config.include_index else "records"
            else:
                export_kwargs["index"] = config.include_index

            export_func = getattr(df, method_name)
            export_func(filepath, **export_kwargs)

            global_signals.request_toast("Success", f"Exported to {Path(filepath).name}", ToastLevel.SUCCESS)
            self.status_bar.log(f"Export complete to {filepath}", LogLevel.SUCCESS)

        except Exception as e:
            self.status_bar.log(f"Export failed: {str(e)}", LogLevel.ERROR)
            global_signals.request_toast("Error", "File export failed", ToastLevel.ERROR)
        finally:
            QApplication.restoreOverrideCursor()
