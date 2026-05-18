import pytest
import pandas as pd
from core.data_handler import DataHandler, DataOperation

def test_create_empty_dataframe(empty_data_handler: DataHandler) -> None:
    target_rows: int = 5
    target_columns: int = 3
    expected_columns: list[str] = ["ID", "Name", "Value"]
    
    resulting_dataframe: pd.DataFrame = empty_data_handler.create_empty_dataframe(
        rows=target_rows,
        columns=target_columns,
        column_names=expected_columns
    )
    assert isinstance(resulting_dataframe, pd.DataFrame)
    assert resulting_dataframe.shape == (target_rows, target_columns)
    assert list(resulting_dataframe.columns) == expected_columns
    
    assert empty_data_handler.file_path is None
    assert empty_data_handler.is_temp_file is False
    assert len(empty_data_handler.undo_stack) == 0
    assert len(empty_data_handler.redo_stack) == 0

def test_sort_data_ascending(empty_data_handler: DataHandler) -> None:
    """
    Test that sorting a DataFrame by a specific column in ascending order works correctly
    and that the operation is logged in the internal state.
    """
    # Arrange
    test_data: dict[str, list[int]] = {"ID": [3, 1, 2], "Value": [30, 10, 20]}
    empty_data_handler.df = pd.DataFrame(test_data)
    
    # Act
    sorted_dataframe: pd.DataFrame = empty_data_handler.sort_data(column="ID", ascending=True)
    
    # Assert
    expected_order: list[int] = [1, 2, 3]
    assert sorted_dataframe["ID"].tolist() == expected_order
    
    # Verify state tracking
    assert empty_data_handler.sort_state == ("ID", True)
    assert len(empty_data_handler.operation_log) == 1
    assert empty_data_handler.operation_log[0]["type"] == "sort"

def test_sort_data_raises_error_on_missing_column(empty_data_handler: DataHandler) -> None:
    """
    Test that attempting to sort by a non-existent column raises the appropriate ValueError.
    """
    # Arrange
    empty_data_handler.df = pd.DataFrame({"ID": [1, 2, 3]})
    invalid_column_name: str = "NonExistentColumn"

    # Act & Assert
    with pytest.raises(Exception) as expected_error:
        empty_data_handler.sort_data(column=invalid_column_name)
    
    assert "Error sorting data" in str(expected_error.value)
    assert invalid_column_name in str(expected_error.value)

def test_split_column_success(empty_data_handler: DataHandler) -> None:
    """
    Test that a string column is correctly split into multiple columns using a delimiter.
    """
    # Arrange
    test_data: dict[str, list[str]] = {"FullName": ["John Doe", "Jane Smith", "Alice Jones"]}
    empty_data_handler.df = pd.DataFrame(test_data)
    
    # Act
    resulting_dataframe: pd.DataFrame = empty_data_handler.clean_data(
        action=DataOperation.SPLIT_COLUMN,
        column="FullName",
        delimiter=" ",
        new_columns=["FirstName", "LastName"]
    )
    
    # Assert
    assert "FirstName" in resulting_dataframe.columns
    assert "LastName" in resulting_dataframe.columns
    assert resulting_dataframe["FirstName"].tolist() == ["John", "Jane", "Alice"]
    assert resulting_dataframe["LastName"].tolist() == ["Doe", "Smith", "Jones"]

def test_split_column_missing_column(empty_data_handler: DataHandler) -> None:
    """
    Test that splitting a non-existent column raises an error.
    """
    # Arrange
    empty_data_handler.df = pd.DataFrame({"ID": [1, 2, 3]})
    
    # Act & Assert
    with pytest.raises(Exception) as expected_error:
        empty_data_handler.clean_data(
            action=DataOperation.SPLIT_COLUMN,
            column="NonExistent",
            delimiter=" ",
            new_columns=["Col1", "Col2"]
        )
    assert "not found in the dataset" in str(expected_error.value)

def test_regex_replace_success(empty_data_handler: DataHandler) -> None:
    """
    Test that regex replacement correctly substitutes matched patterns in a string column.
    """
    # Arrange
    test_data: dict[str, list[str]] = {"ProductCode": ["PRD-123-X", "PRD-456-Y", "PRD-789-Z"]}
    empty_data_handler.df = pd.DataFrame(test_data)
    
    # Act
    resulting_dataframe: pd.DataFrame = empty_data_handler.clean_data(
        action=DataOperation.REGEX_REPLACE,
        column="ProductCode",
        pattern=r"\d+",
        replacement="000"
    )
    
    # Assert
    expected_values: list[str] = ["PRD-000-X", "PRD-000-Y", "PRD-000-Z"]
    assert resulting_dataframe["ProductCode"].tolist() == expected_values

def test_regex_replace_missing_pattern(empty_data_handler: DataHandler) -> None:
    """
    Test that regex replacement raises an error if the pattern is missing.
    """
    # Arrange
    empty_data_handler.df = pd.DataFrame({"TextCol": ["A1", "B2"]})
    
    # Act & Assert
    with pytest.raises(Exception) as expected_error:
        empty_data_handler.clean_data(
            action=DataOperation.REGEX_REPLACE,
            column="TextCol",
            pattern="",
            replacement="X"
        )
    assert "regex pattern are required" in str(expected_error.value)

def test_aggregate_data_multiple_functions(empty_data_handler: DataHandler) -> None:
    """
    Test that aggregating data with multiple functions for a single column
    correctly calculates the metrics and flattens the resulting MultiIndex column
    """
    test_data: dict[str, list[any]] = {
        "Category": ["A", "A", "B", "B"],
        "Sales": [10, 20, 10, 30]
    }
    empty_data_handler.df = pd.DataFrame(test_data)

    group_by_cols: list[str] = ["Category"]
    aggregation_config: dict[str, list[str]] = {"Sales": ["sum", "mean", "max"]}

    resulting_dataframe: pd.DataFrame = empty_data_handler.aggregate_data(
        group_by=group_by_cols,
        agg_config=aggregation_config,
        date_grouping={}
    )

    expected_columns: list[str] = ["Category", "Sales_sum", "Sales_mean", "Sales_max"]
    assert list(resulting_dataframe.columns) == expected_columns

    category_a: pd.Series = resulting_dataframe[resulting_dataframe["Category"] == "A"].iloc[0]
    assert category_a["Sales_sum"] == 30
    assert category_a["Sales_mean"] == 15.0
    assert category_a["Sales_max"] == 20

    category_b: pd.Series = resulting_dataframe[resulting_dataframe["Category"] == "B"].iloc[0]
    assert category_b["Sales_sum"] == 40
    assert category_b["Sales_mean"] == 20.0
    assert category_b["Sales_max"] == 30