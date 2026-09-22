from typing import Callable

from PyQt6.QtCore import QTimer

from src.controller.data_controllers.base_data_controller import BaseDataController
from src.core.global_signals import global_signals
from src.ui.dialogs import FilterAdvancedDialog
from src.ui.status_bar import LogLevel
from src.ui.widgets.ToastNotification import ToastLevel

class FilterController(BaseDataController):
    """
    Sub-controller for handling data filters and filter dialogs

    Manages the quick filter operation and the opening of the
    advanced filter dialog window. Also handles the clearing of active filters
    """

    def __init__(self, data_handler, status_bar, view, subset_manager=None) ->None:
        super().__init__(data_handler, status_bar, view, subset_manager)
        self._preview_timer = QTimer(self.view)
        self._preview_timer.setSingleShot(True)
        timer_interval: int = 300
        self._preview_timer.setInterval(timer_interval)
        self._preview_timer.timeout.connect(self._execute_filter_preview)

    def apply_filter(self) -> None:
        """Apply a quick single-condition filter to the data."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        try:
            column, condition, value = self.view.operations_panel.get_filter_parameters()

            if not column or not condition:
                global_signals.request_toast(
                    "Validation Error", "Please specify both a column and a condition",
                    ToastLevel.WARNING
                )
                return

            if isinstance(value, str):
                try:
                    if "." in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass

            self.update_filter_preview_live()
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
                level=LogLevel.SUCCESS,
            )

            self.view.operations_panel.filtering_tab.set_filter_active_state(
                True, f"Active: {column} {condition} '{value}'"
            )
        except (ValueError, TypeError, KeyError) as e:
            self.status_bar.log(f"Failed to execute 'Filter': {str(e)}", LogLevel.ERROR)
            global_signals.request_toast("Filter Error", "Failed to apply filter", ToastLevel.ERROR)

    def clear_filters(self, reset_callback: Callable[[], None]) -> None:
        """Clear active filters by delegating back to the main reset data routine."""
        if self.data_handler.df is None:
            return

        reset_callback()
        self.view.operations_panel.filtering_tab.clear_filter_preview()
        self.status_bar.log("Filters cleared and data reset to original state", LogLevel.INFO)

    def update_filter_preview_live(self) -> None:
        if self.data_handler.df is None:
            return

        self._preview_timer.start()

    def _execute_filter_preview(self) -> None:
        """Calculate and display the impact of the current filter on the dataset"""
        if self.data_handler.df is None:
            return

        try:
            column, condition, value = self.view.operations_panel.filtering_tab.get_filter_parameters()

            if not column or not condition:
                self.view.operations_panel.filtering_tab.clear_filter_preview()
                return

            total_count: int = len(self.data_handler.df)
            filtered_df = self.data_handler._mutator.filter_data(
                self.data_handler.df.copy(deep=False),
                column=column,
                condition=condition,
                value=value
            )
            filtered_count: int = len(filtered_df)

            self.view.operations_panel.filtering_tab.update_filter_preview(filtered_count, total_count)
        except (ValueError, TypeError, KeyError):
            self.view.operations_panel.filtering_tab.clear_filter_preview()

    def open_advanced_filter(self) -> None:
        """Open the advanced filter dialog to apply complex/multiple conditions."""
        if self.data_handler.df is None:
            self.no_data_loaded_toast()
            return

        dialog = FilterAdvancedDialog(self.data_handler, self.view)
        if dialog.exec():
            result = dialog.get_filters()
            filters = result.get("filters", [])

            if not filters:
                return

            try:
                total_count = len(self.data_handler.df)
                filtered_df = self.data_handler._mutator.filter_data(
                    self.data_handler.df.copy(deep=False),
                    advanced_filters=filters
                )
                filtered_count = len(filtered_df)
                self.view.operations_panel.filtering_tab.update_filter_preview(filtered_count, total_count)

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
            except (ValueError, TypeError, KeyError) as e:
                self.status_bar.log(f"Error applying filter: {str(e)}", LogLevel.ERROR)
                global_signals.request_toast("Filter Error", "Error applying filter to data", ToastLevel.ERROR)
