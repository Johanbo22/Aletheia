import weakref
from typing import TYPE_CHECKING

from src.controller.data_controllers.aggregation_controller import AggregationController
from src.controller.data_controllers.cleaning_controller import CleaningController
from src.controller.data_controllers.column_controller import ColumnController
from src.controller.data_controllers.dataset_controller import DatasetController
from src.controller.data_controllers.filter_controller import FilterController
from src.controller.data_controllers.history_controller import HistoryController
from src.controller.data_controllers.stats_controller import StatsController
from src.controller.data_controllers.subset_controller import SubsetController
from src.controller.data_controllers.transformation_controller import TransformationController
from src.core.aggregation_manager import AggregationManager
from src.core.data_handler import DataHandler
from src.core.global_signals import global_signals
from src.core.help_manager import HelpManager
from src.core.subset_manager import SubsetManager
from src.ui.dialogs import HelpDialog
from src.ui.status_bar import LogLevel
from src.ui.widgets.ToastNotification import ToastLevel

if TYPE_CHECKING:
    from src.ui.data_tab import DataTab
    from src.ui.status_bar import StatusBar

class DataTabController:
    """
    Controller for the DataTab\n
    Handles data operations, dialogs and updating the data view.

    This controller acts as an entry-point for sublevel controllers access for UI,
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
        self.column_controller = ColumnController(data_handler, status_bar, view, subset_manager)
        self.transformation_controller = TransformationController(data_handler, status_bar, view, subset_manager)
        self.aggregation_controller = AggregationController(data_handler, status_bar, view, subset_manager)
        self.subset_controller = SubsetController(data_handler, status_bar, view, subset_manager)
        self.filter_controller = FilterController(data_handler, status_bar, view, subset_manager)
        self.history_controller = HistoryController(data_handler, status_bar, view, subset_manager)

    @property
    def view(self) -> "DataTab":
        return self._view()

    @staticmethod
    def no_data_loaded_toast() -> None:
        global_signals.request_toast(
            "No Data", "Please load data first",
            ToastLevel.WARNING
        )

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

    def apply_filter(self) -> None:
        """Apply filter to data"""
        self.filter_controller.apply_filter()

    def clear_filters(self):
        """Clear filters by resetting the data to original state"""
        self.filter_controller.clear_filters(reset_callback=self.history_controller.reset_data)

    def open_advanced_filter(self):
        """Open advanced filter dialog"""
        self.filter_controller.open_advanced_filter()

    def drop_column(self):
        """Drop selected column"""
        self.column_controller.drop_column()

    def rename_column(self):
        """Rename selected column"""
        self.column_controller.rename_column()

    def duplicate_column(self) -> None:
        """Duplicate the selected column"""
        self.column_controller.duplicate_column()

    def open_computed_column_dialog(self):
        """Opens the dialog to create a new column from a formula"""
        self.column_controller.open_computed_column_dialog()

    def change_column_type(self):
        """Change the data type of the selected column"""
        self.column_controller.change_column_type()

    def apply_text_manipulation(self):
        """Apply the requested text manipulation to the selected column"""
        self.column_controller.apply_text_manipulation()

    def open_split_column_dialog(self) -> None:
        self.column_controller.open_split_column_dialog()

    def open_regex_replace_dialog(self) -> None:
        """Open the dialog to configure and apply regex text replacement."""
        self.column_controller.open_regex_replace_dialog()

    def set_column_visibility(self, column_name: str, visible: bool) -> None:
        """Set column visibility state."""
        self.column_controller.set_column_visibility(column_name, visible)

    def show_all_columns(self) -> None:
        """Show all columns in the table."""
        self.column_controller.show_all_columns()

    def hide_all_columns(self) -> None:
        """Hide all columns in the table."""
        self.column_controller.hide_all_columns()

    def extract_date_component(self):
        """Extracts date components into a new column"""
        self.column_controller.extract_date_component()

    def calculate_date_difference(self):
        """Calculates the time difference between two date columns"""
        self.column_controller.calculate_date_difference()

    def open_binning_dialog(self):
        self.transformation_controller.open_binning_dialog()

    def open_aggregation_dialog(self):
        """Open aggregation dialog"""
        self.aggregation_controller.open_aggregation_dialog()

    def refresh_saved_agg_list(self):
        """Refreshes the list of saved aggs"""
        self.aggregation_controller.refresh_saved_agg_list()

    def on_saved_agg_selected(self, item):
        """Handle selection of saved aggs"""
        self.aggregation_controller.on_saved_agg_selected(item)

    def view_saved_aggregations(self):
        """View the current selected agg in the table"""
        self.aggregation_controller.view_saved_aggregations()

    def restore_aggregation_view(self):
        """Restore the data view to the unaggregated state"""
        self.aggregation_controller.restore_aggregation_view()

    def delete_saved_aggregation(self):
        """Delete a saved aggregation"""
        self.aggregation_controller.delete_saved_aggregation()

    def open_melt_dialog(self):
        """Opens the melt data dialog"""
        self.transformation_controller.open_melt_dialog()

    def open_pivot_dialog(self):
        """Opens the pivot table dialog"""
        self.transformation_controller.open_pivot_dialog()

    def open_merge_dialog(self):
        """Opens the dialog for merging data"""
        self.transformation_controller.open_merge_dialog()

    def open_append_dialog(self) -> None:
        """Opens the dialog to configure and execute data concatenation."""
        self.transformation_controller.open_append_dialog()

    def open_rolling_window_dialog(self) -> None:
        """Opens the dialog to configure and apply a rolling window operation"""
        self.transformation_controller.open_rolling_window_dialog()

    def open_shift_dialog(self) -> None:
        """Opens the dialog to configure and apply a shift (lag/lead) operation"""
        self.transformation_controller.open_shift_dialog()

    def open_pct_change_dialog(self) -> None:
        """Opens the dialog to configure and apply a percentage change calculation"""
        self.transformation_controller.open_pct_change_dialog()

    def open_column_reorder_dialog(self) -> None:
        """Opens the dialog for reordering columns"""
        self.transformation_controller.open_column_reorder_dialog()

    def apply_sort(self):
        """Apply a permanent sorting to data"""
        self.transformation_controller.apply_sort()

    def quick_create_subsets(self):
        """Quick create subsets from column values"""
        self.subset_controller.quick_create_subsets()

    def refresh_active_subsets(self):
        """Refresh the list of active subsets"""
        self.subset_controller.refresh_active_subsets()

    def view_subset_quick(self):
        """Quick view of selected subset"""
        self.subset_controller.view_subset_quick()

    def open_subset_manager(self):
        """Open the subset manager dialog"""
        self.subset_controller.open_subset_manager()

    def handle_plot_request(self, subset_name: str):
        """Handle the signal from SubsetManagerDialog to plot the selected subset"""
        self.subset_controller.handle_plot_request(subset_name)

    def inject_subset_to_dataframe(self):
        """Insert the selected subset into the active dataframe view."""
        self.subset_controller.inject_subset_to_dataframe()

    def restore_original_dataframe(self):
        """Restore the original DataFrame into the Active Data View of the Data Table"""
        self.subset_controller.restore_original_dataframe()

    def reset_data(self) -> None:
        """Reset data to original state"""
        self.history_controller.reset_data()

    def jump_to_history_state(self, target_node_id: str) -> None:
        """Jumps to a state node in the history tree"""
        self.history_controller.jump_to_history_state(target_node_id=target_node_id)

    def on_history_clicked(self, item):
        """Handles the click of a history entry from the history widget"""
        self.history_controller.on_history_clicked(item)

    def save_pipeline_macro(self) -> None:
        """Saves the current data operations to a JSON file"""
        self.history_controller.save_pipeline_macro()

    def load_pipeline_macro(self) -> None:
        """Loads a JSON macro file and executes the pipeline on the currently active DataFrame."""
        self.history_controller.load_pipeline_macro()

    def run_statistical_test_from_selection(self) -> None:
        """Handles the selection of columns and trigger a statistical test or opens the workspace"""
        self.stats_controller.run_statistical_test_from_selection()

    def export_data(self) -> None:
        """Handles exporting the dataframe to a file or clipboard"""
        self.dataset_controller.export_data()
