from typing import Optional, TYPE_CHECKING, TypedDict

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem, QMessageBox

from src.controller.data_controllers.base_data_controller import BaseDataController
from src.core.aggregation_manager import AggregationManager
from src.core.global_signals import global_signals
from src.ui.dialogs import AggregationDialog
from src.ui.status_bar import LogLevel
from src.ui.widgets.ToastNotification import ToastLevel

if TYPE_CHECKING:
    from src.core.data_handler import DataHandler
    from src.core.subset_manager import SubsetManager
    from src.ui.data_tab import DataTab
    from src.ui.status_bar import StatusBar

class AggregationConfig(TypedDict, total=False):
    group_by: list[str]
    agg_config: dict[str, str]
    date_grouping: Optional[dict[str, str]]
    aggregation_name: str
    rename_mapping: Optional[dict[str, str]]

class AggregationController(BaseDataController):
    """
    Sub-controller for handling data aggregations
    Manages the creation, saving, loading, and viewing of data aggregations
    """

    def __init__(self,
                 data_handler: "DataHandler",
                 status_bar: "StatusBar",
                 view: "DataTab",
                 subset_manager: Optional["SubsetManager"] = None) -> None:
        super().__init__(data_handler, status_bar, view, subset_manager)
        self.aggregation_manager: AggregationManager = AggregationManager()

    def open_aggregation_dialog(self) -> None:
        """Open aggregation dialog to configure and apply grouping."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        if getattr(self.data_handler, "viewing_aggregation_name", None):
            global_signals.request_toast(
                "Action Denied",
                "Please restore the data view before creating a new aggregation",
                ToastLevel.WARNING
            )
            return

        if not hasattr(self.data_handler, "pre_agg_view_df") or self.data_handler.pre_agg_view_df is None:
            self.data_handler.pre_agg_view_df = self.data_handler.df.copy()

        dialog: AggregationDialog = AggregationDialog(self.data_handler, self.view)
        if dialog.exec():
            self._apply_and_save_aggregation(dialog.get_aggregation_config())
        else:
            if hasattr(self.data_handler, "pre_agg_view_df") and self.data_handler.pre_agg_view_df is not None:
                self.data_handler.df = self.data_handler.pre_agg_view_df.copy()
                self.data_handler.pre_agg_view_df = None
                self.view.refresh_data_view()

    def _apply_and_save_aggregation(self, config: AggregationConfig) -> None:
        """Applies the aggregation configuration and optionally saves it"""
        try:

            if not hasattr(self.data_handler, "pre_agg_view_df") or self.data_handler.pre_agg_view_df is None:
                self.data_handler.pre_agg_view_df = self.data_handler.df.copy()

            self.data_handler.reset_data()

            group_cols: list[str] = config.get("group_by", [])
            agg_config: dict[str, str] = config.get("agg_config", {})
            date_grouping: Optional[dict[str, str]] = config.get("date_grouping")
            agg_name: str = config.get("aggregation_name", "")
            rename_mapping: Optional[dict[str, str]] = config.get("rename_mapping")

            self.data_handler.aggregate_data(
                group_cols, agg_config, date_grouping, rename_mapping
            )

            self.data_handler.viewing_aggregation_name = agg_name if agg_name else "Unsaved Aggregation"
            self.data_handler.inserted_subset_name = None

            if agg_name:
                self._save_aggregation_configuration(
                    agg_name, group_cols, agg_config, date_grouping, rename_mapping
                )

            self.view.refresh_data_view()
            self._log_aggregation_success(group_cols, agg_config, date_grouping, agg_name)

        except Exception as e:
            if hasattr(self.data_handler, "pre_agg_view_df") and self.data_handler.pre_agg_view_df is not None:
                self.data_handler.df = self.data_handler.pre_agg_view_df.copy()
                self.data_handler.pre_agg_view_df = None
                self.data_handler.viewing_aggregation_name = None

            global_signals.request_toast("Error", "Aggregating data failed", ToastLevel.ERROR)
            self.status_bar.log(f"Aggregation failed: {str(e)}", LogLevel.ERROR)
            if self.data_handler.df is not None:
                self.view.refresh_data_view()

    def _save_aggregation_configuration(self, agg_name: str, group_cols: list[str], agg_config: dict[str, str],
                                        date_grouping: Optional[dict[str, str]],
                                        rename_mapping: Optional[dict[str, str]]) -> None:
        """Saves the active aggregation configuration to the manager"""
        try:
            desc_parts: list[str] = [f"{func}({col})" for col, func in agg_config.items()]
            description: str = f"Aggregated: {', '.join(desc_parts)} by {', '.join(group_cols)}"
            result_df: pd.DataFrame = self.data_handler.df.copy()

            self.aggregation_manager.save_aggregation(
                name=agg_name,
                description=description,
                group_by=group_cols,
                agg_config=agg_config,
                date_grouping=date_grouping,
                result_df=result_df,
                rename_mapping=rename_mapping
            )
            self.refresh_saved_agg_list()
            self.status_bar.log(f"Saved aggregation: {agg_name}", LogLevel.SUCCESS)
        except ValueError as e:
            global_signals.request_toast(
                "Warning",
                f"An aggregation named '{agg_name}' already exists", ToastLevel.WARNING
            )
            self.status_bar.log(f"Failed to save aggregation: {str(e)}", LogLevel.ERROR)

    def _log_aggregation_success(self, group_cols: list[str], agg_config: dict[str, str],
                                 date_grouping: Optional[dict[str, str]], agg_name: str) -> None:
        """Logs the successful aggregation"""
        group_by_str: str = ", ".join(group_cols)
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
            level=LogLevel.SUCCESS
        )

    def refresh_saved_agg_list(self) -> None:
        """Refreshes the UI list of saved aggregations."""
        try:
            agg_names: list[str] = self.aggregation_manager.list_aggregations()
            data_list: list[tuple[str, int]] = []

            if agg_names:
                for name in agg_names:
                    agg = self.aggregation_manager.get_aggregation(name)
                    if agg:
                        data_list.append((name, agg.row_count))

            self.view.operations_panel.update_saved_aggregation_list(data_list)
        except Exception as e:
            self.status_bar.log(f"Warning: Could not refresh aggregation list: {str(e)}", LogLevel.WARNING)

    def on_saved_agg_selected(self, item: Optional[QListWidgetItem]) -> None:
        """Handle selection of saved aggs in the UI table."""
        enabled: bool = (item is not None and item.data(Qt.ItemDataRole.UserRole) is not None)
        self.view.operations_panel.set_aggregation_buttons_enabled(enabled)

    def view_saved_aggregations(self) -> None:
        """View the currently selected aggregation in the main data table."""
        agg_name: Optional[str] = self.view.operations_panel.get_selected_saved_aggregation()
        if not agg_name:
            return

        try:
            agg_df: Optional[pd.DataFrame] = self.aggregation_manager.get_aggregation_df(agg_name)
            if agg_df is None:
                global_signals.request_toast("Error", "Aggregation data not found", ToastLevel.ERROR)
                self.status_bar.log("Error in viewing aggregation. Data is not found", LogLevel.ERROR)
                return

            # Store the current state if not already viewing an aggregation
            if not hasattr(self.data_handler, "pre_agg_view_df") or self.data_handler.pre_agg_view_df is None:
                self.data_handler.pre_agg_view_df = self.data_handler.df.copy()

            self.view.data_table.setModel(None)
            if hasattr(self.view, "model") and self.view.model is not None:
                self.view.model.deleteLater()
                del self.view.model

            self.data_handler.df = agg_df.copy()
            self.data_handler.viewing_aggregation_name = agg_name
            self.data_handler.inserted_subset_name = None
            self.view.refresh_data_view(emit_modified=False)

            self.status_bar.log_action(
                f"Viewing saved aggregation: {agg_name}",
                details={"aggregation_name": agg_name,
                         "rows"            : len(agg_df),
                         "columns"         : len(agg_df.columns),
                         "operation"       : "view_saved_aggregation"},
                level=LogLevel.INFO,
            )
            global_signals.request_toast("Aggregation Loaded", f"Now viewing aggregation: {agg_name}")
        except Exception as e:
            global_signals.request_toast("Error", "Failed to view aggregation", ToastLevel.ERROR)
            self.status_bar.log(f"Failed to view aggregation: {str(e)}", LogLevel.ERROR)

    def restore_aggregation_view(self) -> None:
        """Restore the data view back to the unaggregated state"""
        if not getattr(self.data_handler, "viewing_aggregation_name", None):
            global_signals.request_toast("Info", "You are not currently viewing an aggregation", ToastLevel.INFO)
            return

        try:
            if hasattr(self.data_handler, "pre_agg_view_df") and self.data_handler.pre_agg_view_df is not None:
                self.data_handler.df = self.data_handler.pre_agg_view_df.copy()
                self.data_handler.pre_agg_view_df = None
                self.data_handler.viewing_aggregation_name = None
                self.data_handler.inserted_subset_name = None

                self.view.data_table.setModel(None)
                if hasattr(self.view, "model") and self.view.model is not None:
                    self.view.model.deleteLater()
                    del self.view.model

                self.view.refresh_data_view(emit_modified=False)

                self.status_bar.log_action(
                    "Restored data view from aggregation",
                    details={"operation": "restore_aggregation_view"},
                    level=LogLevel.INFO,
                )
                global_signals.request_toast("View Restored", "Restored to the unaggregated data view.")
            else:
                global_signals.request_toast("Error", "No previous data state to restore.", ToastLevel.ERROR)

        except Exception as e:
            global_signals.request_toast("Error", "Failed to restore view.", ToastLevel.ERROR)
            self.status_bar.log(f"Failed to restore view: {str(e)}", LogLevel.ERROR)

    def delete_saved_aggregation(self) -> None:
        """Delete a saved aggregation from the internal manager."""
        agg_name: Optional[str] = self.view.operations_panel.get_selected_saved_aggregation()
        if not agg_name:
            return

        is_currently_viewing: bool = getattr(self.data_handler, "viewing_aggregation_name", None) == agg_name

        warning_text: str = f"Are you sure you want to delete the saved aggregation: '{agg_name}'?"
        if is_currently_viewing:
            warning_text += "\n\nNote: You are currently viewing this aggregation. Deleting it will restore the original data view"
        else:
            warning_text += "\n\nThis will not affect your current data view"

        reply: QMessageBox.StandardButton = QMessageBox.question(
            self.view,
            "Confirm Delete",
            warning_text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.aggregation_manager.delete_aggregation(agg_name):
                if is_currently_viewing:
                    self.restore_aggregation_view()

                self.refresh_saved_agg_list()
                self.view.operations_panel.set_aggregation_buttons_enabled(False)
                self.status_bar.log(f"Deleted aggregation: {agg_name}", LogLevel.SUCCESS)
                self.view.data_modified.emit()
