import pytest
import pandas as pd

from PyQt6.QtCore import Qt
from pytestqt.qtbot import QtBot

from core.data_handler import DataHandler
from ui.dialogs.AggregationDialog import AggregationDialog

@pytest.fixture
def dummy_data_handler() -> DataHandler:
    """
    Creates a DataHandler instance pre-populated with a dummy DataFrame
    containing both categorical, numeric, and multiple datetime columns
    """
    handler = DataHandler()
    handler.df = pd.DataFrame({
        "category_col": ["A", "B", "A", "B", "C"],
        "numeric_col": [10, 20, 30, 40, 50],
        "date_col_1": pd.date_range("2023-01-01", periods=5, freq="D"),
        "date_col_2": pd.date_range("2023-01-01", periods=5, freq="ME")
    })
    return handler

def test_dynamic_date_grouping_comboboxes(qtbot: QtBot, dummy_data_handler: DataHandler) -> None:
    """
    Tests the independent frequency selection lifecycle for dynamic datetime comboboxes.
    Verifies that temporal dropdowns are correctly spawned, state is preserved during
    subsequent selections, and distinct values are properly extracted into the config
    """
    dialog = AggregationDialog(dummy_data_handler)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)

    # State validation
    assert not dialog.date_group_frame.isVisible(), "Date group frame should initially be hidden"
    assert len(dialog.date_freq_combos) == 0, "No combo boxes should be generated initially"

    # non datetime column selection
    cat_items = dialog.group_by_list_view.findItems("category_col", Qt.MatchFlag.MatchExactly)
    assert cat_items, "Mock column 'category_col' not found in UI list"
    cat_items[0].setSelected(True)
    dialog.on_group_selection_change()

    assert not dialog.date_group_frame.isVisible(), "Date group frame must remain for non-datetime columns"
    assert len(dialog.date_freq_combos) == 0, "Combobox dictionary must remain empty"

    # First datetime sleection
    date_items_1 = dialog.group_by_list_view.findItems("date_col_1", Qt.MatchFlag.MatchExactly)
    date_items_1[0].setSelected(True)
    dialog.on_group_selection_change()

    assert dialog.date_group_frame.isVisible(), "Date group frame must be visible after selecting a datetime column."
    assert len(dialog.date_freq_combos) == 1, "Exactly one combo box should be dynamically generated."
    assert "date_col_1" in dialog.date_freq_combos, "Combo box must be tracked by column name."

    # Change the current value of the first dropdown before triggering a layout rebuild
    dialog.date_freq_combos["date_col_1"].setCurrentText("Month")

    date_items_2 = dialog.group_by_list_view.findItems("date_col_2", Qt.MatchFlag.MatchExactly)
    date_items_2[0].setSelected(True)
    dialog.on_group_selection_change()

    assert len(dialog.date_freq_combos) == 2, "A second combo box must be generated."
    assert dialog.date_freq_combos[
               "date_col_1"].currentText() == "Month", "Previous combo box state was not preserved after layout rebuild."

    # Configure the second datetime column independently
    dialog.date_freq_combos["date_col_2"].setCurrentText("Year")

    # Verify that the backend mapping parses independent temporal selections correctly
    group_cols, agg_config, date_grouping = dialog.get_current_config()

    assert "date_col_1" in date_grouping
    assert "date_col_2" in date_grouping
    assert date_grouping[
               "date_col_1"] == "Month", "Configuration did not capture the independent frequency for date_col_1."
    assert date_grouping[
               "date_col_2"] == "Year", "Configuration did not capture the independent frequency for date_col_2."