from typing import Callable

from controller.data_controllers.base_data_controller import BaseDataController
from core.global_signals import global_signals
from ui.dialogs import FilterAdvancedDialog
from ui.status_bar import LogLevel
from ui.widgets.ToastNotification import ToastLevel

class FilterController(BaseDataController):
    """
    Sub-controller for handling data filters and filter dialogs

    Manages the quick filter operation and the opening of the
    advanced filter dialog window. Also handles the clearing of active filters
    """

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
        self.status_bar.log("Filters cleared and data reset to original state", LogLevel.INFO)

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
