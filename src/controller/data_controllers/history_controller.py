from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox

from src.controller.data_controllers.base_data_controller import BaseDataController
from src.core.global_signals import global_signals
from src.ui.dialogs import MacroPreviewDialog
from src.ui.status_bar import LogLevel
from src.ui.widgets.ToastNotification import ToastLevel

class HistoryController(BaseDataController):
    """
    Sub-controller handling data history state mapping and macro exeuction
    Manages Macro execution, using the pipeline viewer to jump between states
    as well as the reset_data method to reset the entire data view.
    """

    def jump_to_history_state(self, target_node_id: str) -> None:
        """Jumps the active data view to a specific state node in the history tree."""
        try:
            self.data_handler.jump_to_history_index(target_node_id)
            self.view.refresh_data_view()
            self.view.operations_panel.select_history_item_by_index(target_node_id)
        except Exception as e:
            self.status_bar.log(f"Failed to go to state: {str(e)}", LogLevel.ERROR)

    def on_history_clicked(self, item) -> None:
        """Handles the UI selection of a history entry."""
        if not item:
            return

        target_index = item.data(Qt.ItemDataRole.UserRole)
        self.jump_to_history_state(target_index)

    def save_pipeline_macro(self) -> None:
        """Saves the current sequence of data operations to a JSON file."""
        if not self.data_handler.operation_log:
            global_signals.request_toast(
                "No Operations Logged", "There are no data operations in the history to save as a macro",
                ToastLevel.WARNING
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self.view, "Save Macro", "", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            try:
                self.data_handler.export_pipeline_macro(file_path)
                self.status_bar.log(f"Macro saved to {file_path}", LogLevel.SUCCESS)
            except Exception as err:
                self.status_bar.log(f"Failed to save pipeline macro: {str(err)}", LogLevel.ERROR)

    def load_pipeline_macro(self) -> None:
        """Loads a JSON macro file and executes the saved pipeline on the active DataFrame."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self.view, "Load Macro", "", "JSON Files (*.json);;All Files (*)"
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
                    global_signals.request_toast("Error", "Macro Execution Failed", ToastLevel.ERROR)

    def _clear_handler_volatile_state(self) -> None:
        """Clears internal state attributes on the data handler during hard resets"""
        volatile_attrs = [
            "pre_insert_df",
            "inserted_subset_name",
            "viewing_aggregation_name",
            "pre_agg_view_df"
        ]
        for attr in volatile_attrs:
            if hasattr(self.data_handler, attr):
                setattr(self.data_handler, attr, None)

    def reset_data(self) -> None:
        """Reset data back to the original unmodified root dataset state."""
        reply = QMessageBox.question(
            self.view,
            "Confirm Reset",
            "Are you sure you want to reset the data to its original state?\n\n"
            "This will discard all changes, restore the original dataset and delete all history.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.No:
            self.status_bar.log("Data reset cancelled", LogLevel.INFO)
            return

        try:
            rows_before = len(self.data_handler.df) if self.data_handler.df is not None else 0
            cols_before = len(self.data_handler.df.columns) if self.data_handler.df is not None else 0

            self.data_handler.reset_data()
            self._clear_handler_volatile_state()

            self.view.operations_panel.set_injection_status_ui(is_subset_active=False)
            self.view.operations_panel.filtering_tab.set_filter_active_state(False)

            rows_after = len(self.data_handler.df) if self.data_handler.df is not None else 0
            cols_after = len(self.data_handler.df.columns) if self.data_handler.df is not None else 0

            self.view.refresh_data_view()
            global_signals.request_toast(
                "Data Reset to Original State", "Data has been reset to show the original data", ToastLevel.SUCCESS
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
                level=LogLevel.SUCCESS,
            )
        except Exception as e:
            self.status_bar.log(f"Failed to reset data: {str(e)}", LogLevel.ERROR)
            global_signals.request_toast("Reset Data Error", "Failed to reset data", ToastLevel.ERROR)
