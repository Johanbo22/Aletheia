from typing import Optional

from PyQt6.QtCore import QThreadPool, Qt
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.controller.data_controllers.base_data_controller import BaseDataController
from src.core.global_signals import global_signals
from src.ui.dialogs import ProgressDialog, SubsetDataViewer
from src.ui.status_bar import LogLevel
from src.ui.widgets.ToastNotification import ToastLevel
from src.ui.workers import AutoCreateSubsetsWorker

class SubsetController(BaseDataController):
    """
    Sub-controller handling data subsets
    Manages the creation, apply the subsets to the data view and the
    instantiation of the SubsetManagerDialog window
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.progress_dialog: Optional[ProgressDialog] = None
        self._current_subset_col: str = ""
        self._current_subset_count: int = 0

    def quick_create_subsets(self) -> None:
        """Quick create subsets grouped by unique values in a specific column."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        column = self.view.operations_panel.get_quick_subset_column()
        if not column:
            global_signals.request_toast("No Column Selected", "Please select a column", ToastLevel.WARNING)
            return

        unique_count = self.data_handler.df[column].nunique()

        reply = QMessageBox.question(
            self.view,
            "Confirm",
            f"Create {unique_count} subsets (one per unique value in '{column}')?\n\n",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._current_subset_col = column
            self._current_subset_count = unique_count

            self.progress_dialog = ProgressDialog(
                title="Auto-Creating subsets", message=f"Creating subsets from '{column}'...", parent=self.view
            )
            self.progress_dialog.setModal(True)
            self.progress_dialog.show()

            worker = AutoCreateSubsetsWorker(self.subset_manager, self.data_handler.df, column)
            worker.signals.progress.connect(self.progress_dialog.update_progress)
            worker.signals.finished.connect(self._on_quick_create_subsets_finished)
            worker.signals.error.connect(self._on_quick_create_subsets_error)

            QThreadPool.globalInstance().start(worker)

    def _on_quick_create_subsets_finished(self, created: list) -> None:
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog.deleteLater()
            self.progress_dialog = None

        column = self._current_subset_col
        unique_count = self._current_subset_count

        self.refresh_active_subsets()

        self.status_bar.log_action(
            f"Created {len(created)} subsets from column '{column}'",
            details={
                "column"   : column, "subsets_created": len(created), "unique_values": unique_count,
                "operation": "auto_create_subsets"
            },
            level=LogLevel.SUCCESS,
        )
        global_signals.request_toast("Success", f"Created {len(created)} subsets from column '{column}'",
                                     ToastLevel.SUCCESS)

    def _on_quick_create_subsets_error(self, error: Exception) -> None:
        """Callback for when subset auto-creation fails in the background."""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog.deleteLater()
            self.progress_dialog = None

        self.status_bar.log(f"Failed to create subsets: {str(error)}", LogLevel.ERROR)
        global_signals.request_toast("Error", "Failed to create subsets", ToastLevel.ERROR)

    def refresh_active_subsets(self) -> None:
        """Refresh the UI list of active subsets dynamically."""
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            subset_data = []

            for name in self.subset_manager.list_subsets():
                subset = self.subset_manager.get_subset(name)
                row_text = f"{subset.row_count} rows" if subset.row_count > 0 else "? rows"
                subset_data.append((name, row_text))

            self.view.operations_panel.update_active_subsets_list(subset_data)
        except Exception as e:
            self.status_bar.log(f"Warning: Could not refresh subset list: {e}", LogLevel.ERROR)
        finally:
            QApplication.restoreOverrideCursor()

    def view_subset_quick(self) -> None:
        """Opens a quick view modal of the selected subset."""
        name = self.view.operations_panel.get_selected_active_subset()
        if not name:
            return

        try:
            subset_df = self.subset_manager.apply_subset(self.data_handler.df, name)
            viewer = SubsetDataViewer(subset_df, name, self.view)
            viewer.exec()
        except Exception as e:
            self.status_bar.log(f"Error viewing subset: {str(e)}", LogLevel.ERROR)
            global_signals.request_toast("Error", f"Failed to view subset '{name}'", ToastLevel.ERROR)

    def open_subset_manager(self) -> None:
        """Open the subset manager dialog for explicit management and visualization."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        try:
            from src.ui.dialogs import SubsetManagerDialog
            dialog = SubsetManagerDialog(self.subset_manager, self.data_handler, self.view)
            dialog.plot_subset_requested.connect(self.handle_plot_request)

            dialog.exec()
            self.refresh_active_subsets()
        except Exception as e:
            self.status_bar.log(f"Failed to open subset manager dialog: {str(e)}", LogLevel.ERROR)
            global_signals.request_toast("Error", "Failed to open subset manager dialog", ToastLevel.ERROR)

    def handle_plot_request(self, subset_name: str) -> None:
        """Handle the signal from SubsetManagerDialog to plot the selected subset."""
        if not self.view.plot_tab:
            global_signals.request_toast("Error", "Plot tab reference is missing. Cannot switch tabs", ToastLevel.ERROR)
            self.status_bar.log("Plot tab reference not set", LogLevel.ERROR)
            return

        try:
            self.view.plot_tab.activate_subset(subset_name)
            self.view.switch_to_plot_tab()
        except Exception as e:
            self.status_bar.log(f"Failed to switch to plotting tab: {str(e)}", LogLevel.ERROR)
            global_signals.request_toast("Error", "Failed to activate the plot tab", ToastLevel.ERROR)

    def inject_subset_to_dataframe(self) -> None:
        """Insert the selected subset into the active dataframe view temporarily."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        subset_name = self.view.operations_panel.get_selected_active_subset()
        if not subset_name:
            global_signals.request_toast(
                "No Subset Selected", "Please select a subset to apply to the current data view", ToastLevel.WARNING
            )
            return

        try:
            if not hasattr(self.data_handler, "pre_insert_df") or self.data_handler.pre_insert_df is None:
                self.data_handler.pre_insert_df = self.data_handler.df.copy()
                self.data_handler.inserted_subset_name = None
                base_df = self.data_handler.df
            else:
                base_df = self.data_handler.pre_insert_df

            subset_df = self.subset_manager.apply_subset(base_df, subset_name, use_cache=False)

            self.data_handler.df = subset_df.copy()
            self.data_handler.inserted_subset_name = subset_name

            self.view.refresh_data_view()

            self.view.operations_panel.set_injection_status_ui(is_subset_active=True, subset_name=subset_name)
            self.view.operations_panel.subsets_tab.restore_original_btn.setEnabled(True)
            self.view.operations_panel.subsets_tab.inject_subset_btn.setEnabled(False)

            self.status_bar.log_action(
                f"Inserted the subset: '{subset_name}' into the active DataFrame",
                details={
                    "subset_name"  : subset_name, "subset_rows": len(subset_df),
                    "original_rows": len(self.data_handler.pre_insert_df),
                    "operation"    : "insert_subset_into_active_data_view",
                },
                level=LogLevel.SUCCESS,
            )
            global_signals.request_toast(
                "Insert Complete", f"Subset '{subset_name}' has been inserted into the active DataFrame",
                ToastLevel.SUCCESS
            )

        except Exception as e:
            self.status_bar.log(f"Failed to insert the subset: {str(e)}", LogLevel.ERROR)
            global_signals.request_toast("Error", "Failed to insert subset", ToastLevel.ERROR)

    def restore_original_dataframe(self) -> None:
        """Restore the original DataFrame view after a subset was injected."""
        if not hasattr(self.data_handler, "pre_insert_df") or self.data_handler.pre_insert_df is None:
            global_signals.request_toast("Nothing to Restore", "No inserted subset to restore from", ToastLevel.WARNING)
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
                details={"previous_subset": subset_name, "restored_rows": original_rows,
                         "operation"      : "restore_original"},
                level=LogLevel.SUCCESS,
            )
            global_signals.request_toast(
                "Restore Complete", f"Original DataFrame has been restored.\nRestored: {original_rows:,} rows"
            )
        except Exception as e:
            self.status_bar.log(f"Failed to restore original data: {str(e)}", LogLevel.ERROR)
            global_signals.request_toast("Error", "Failed to restore original data", ToastLevel.ERROR)
