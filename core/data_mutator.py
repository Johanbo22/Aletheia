"""
Data Mutator module for data transformations and manipulation operations

This module provides the DataMutator class which handles various data operations
on pandas DataFrames. This modules API redirects to DataHandler to bridge
"""

import keyword
import logging
import re
import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum
from functools import wraps

try:
    from scipy import stats
    from sklearn.ensemble import IsolationForest
except ImportError:
    stats = None
    IsolationForest = None

logger = logging.getLogger(__name__)

def require_dataframe(func: Callable) -> Callable:
    """Ensures the provided dataframe is not None"""
    @wraps(func)
    def wrapper(self, df: pd.DataFrame, *args, **kwargs) -> Any:
        if df is None:
            raise ValueError("No data is loaded")
        return func(self, df, *args, **kwargs)
    return wrapper

class StatisticalTest(str, Enum):
    T_TEST = "t-test"
    ANOVA = "anova"
    PEARSON = "pearson"

class DataOperation(str, Enum):
    DROP_DUPLICATES = "drop_duplicates"
    DROP_MISSING = "drop_missing"
    FILL_MISSING = "fill_missing"
    DROP_COLUMN = "drop_column"
    RENAME_COLUMN = "rename_column"
    CHANGE_DATA_TYPE = "change_data_type"
    TEXT_MANIPULATION = "text_manipulation"
    SPLIT_COLUMN = "split_column"
    REGEX_REPLACE = "regex_replace"
    REMOVE_ROWS = "remove_rows"
    CLIP_OUTLIERS = "clip_outliers"
    DUPLICATE_COLUMN = "duplicate_column"
    NORMALIZE = "normalize"
    EXTRACT_DATE_COMPONENT = "extract_date_component"
    CALCULATE_DATE_DIFFERENCE = "calculate_date_difference"
    FLAG_OUTLIERS = "flag_outliers"
    REORDER_COLUMNS = "reorder_columns"
    DROP_EMPTY_COLUMNS = "drop_empty_columns"
    ROLLING_WINDOW = "rolling_window"
    SHIFT_DATA = "shift_data"
    PERCENTAGE_CHANGE = "percentage_change"

class FillMethod(str, Enum):
    MEAN = "mean"
    MEDIAN = "median"
    MODE = "mode"
    FFILL = "ffill"
    BFILL = "bfill"
    STATIC_VALUE = "static_value"
    LINEAR = "linear"
    TIME = "time"
###
# Quantile functions
def q25(x: pd.Series) -> float:
    return x.quantile(0.25)
def q75(x: pd.Series) -> float:
    return x.quantile(0.75)
def q90(x: pd.Series) -> float:
    return x.quantile(0.90)
QUANTILE_FUNCS: Dict[str, Callable] = {
    "q25": q25,
    "q75": q75,
    "q90": q90
}
def resolve_agg_config(agg_config: Dict[str, Union[str, List[str]]]) -> Dict[str, Union[Any, List[Any]]]:
    """Resolves string aggregation functions to callable functions where necessary."""
    resolved: Dict[str, Union[Any, List[Any]]] = {}
    for col, funcs in agg_config.items():
        if isinstance(funcs, list):
            resolved[col] = [QUANTILE_FUNCS.get(f, f) for f in funcs]
        else:
            resolved[col] = QUANTILE_FUNCS.get(funcs, funcs)
    return resolved

class DataMutator:
    """
    Class dedicated to performing transformations on a DataFrame
    
    All public methods receive the DataFrame they should operate on and
    return the changed DataFrame. They also return the updated sort_state
    when the operation may invalidate it so callers can propagate the change.
    """
    FrequencyMap: Dict[str, str] = {
        "Year": "YE",
        "Quarter": "QE",
        "Month": "ME",
        "Week": "W",
        "Day": "D",
    }
    def __init__(self) -> None:
        self._operation_registry: Dict[DataOperation, Any] = {
            DataOperation.DROP_DUPLICATES: self._drop_duplicates,
            DataOperation.DROP_MISSING: self._drop_missing,
            DataOperation.FILL_MISSING: self._fill_missing,
            DataOperation.DROP_COLUMN: self._drop_column,
            DataOperation.RENAME_COLUMN: self._rename_column,
            DataOperation.CHANGE_DATA_TYPE: self._change_data_type,
            DataOperation.TEXT_MANIPULATION: self._text_manipulation,
            DataOperation.SPLIT_COLUMN: self._split_column,
            DataOperation.REGEX_REPLACE: self._regex_replace,
            DataOperation.REMOVE_ROWS: self._remove_rows,
            DataOperation.CLIP_OUTLIERS: self._clip_outliers,
            DataOperation.DUPLICATE_COLUMN: self._duplicate_column,
            DataOperation.NORMALIZE: self._normalize_data,
            DataOperation.EXTRACT_DATE_COMPONENT: self._extract_date_component,
            DataOperation.CALCULATE_DATE_DIFFERENCE: self._calculate_date_difference,
            DataOperation.FLAG_OUTLIERS: self._flag_outliers,
            DataOperation.REORDER_COLUMNS: self._reorder_columns,
            DataOperation.DROP_EMPTY_COLUMNS: self._drop_empty_columns,
            DataOperation.ROLLING_WINDOW: self._apply_rolling_window,
            DataOperation.SHIFT_DATA: self._apply_shift,
            DataOperation.PERCENTAGE_CHANGE: self._apply_pct_change
        }

    @require_dataframe
    def clean_data(self, df: pd.DataFrame, action: "DataOperation | str", sort_state: Optional[tuple], **kwargs) -> tuple[pd.DataFrame, Optional[tuple]]:
        """
        Caller for the cleaning/transformation action via operaton registry\n
        :param df (pd.DataFrame): The DataFrame to work on
        :param action (DataOperation): A DataOperation to execute
        :param sort_state (Optional[tuple]): Current sort state
        :param **kwargs: Arguments forwarded to each action 
        :return (changed_df, updated_sort_state):
        """
        if isinstance(action, str):
            try:
                action = DataOperation(action)
            except ValueError:
                raise ValueError(f"Unsupported operation: {action}")

        if action not in self._operation_registry:
            raise ValueError(f"Unknown operation; not in registry: {action}")

        try:
            handler_method = self._operation_registry[action]
            df, sort_state = handler_method(df=df, sort_state=sort_state, **kwargs)
            return df, sort_state
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error cleaning data: {e}", exc_info=True)
            raise

    def _cast_cell_value(self, value: Any, column_name: str, column_datatype: Any) -> Any:
        """
        Casts a value to the target column's datatype

        :param value: The raw value to cast
        :param column_name: The name of the column
        :param column_datatype: The pandas datatype of the target column
        :return: The casted value
        """
        if value is None:
            return None

        if pd.api.types.is_integer_dtype(column_datatype):
            try:
                return int(value)
            except ValueError:
                pass

            try:
                return int(float(value))
            except ValueError:
                raise ValueError(f"Value '{value}' is not a valid integer for column '{column_name}'")

        elif pd.api.types.is_float_dtype(column_datatype):
            try:
                return float(value)
            except ValueError:
                raise ValueError(f"Value '{value}' is not a valid float for column '{column_name}'")

        elif pd.api.types.is_bool_dtype(column_datatype):
            if isinstance(value, str):
                return value.lower() in ("true", "1", "t", "yes", "y")
            return bool(value)

        return value

    @require_dataframe
    def update_cell(self, df: pd.DataFrame, row_index: int, column_index: int, value: Any) -> pd.DataFrame:
        """
        Update a single cell in the DataTableModel and forcing value to match column datatype

        :param df (pd.DataFrame): the DataFrame to change
        :param row_index (int): Row positon
        :param column_index (int): Column Position
        :param value (Any): The new cell value
        :return (pd.DataFrame): The changed DataFrame
        """
        try:
            column_name = df.columns[column_index]
            column_datatype = df[column_name].dtype

            casted_value = self._cast_cell_value(value, column_name, column_datatype)
            df.iat[row_index, column_index] = casted_value
            return df
        except (ValueError, IndexError, TypeError) as e:
            logger.error(f"Error updating cell: {e}", exc_info=True)
            raise

    @require_dataframe
    def filter_data(self, df: pd.DataFrame, column: str = None, condition: str = None, value: Any = None, advanced_filters: List[Dict] = None) -> pd.DataFrame:
        """
        Filter data based on a single condition or multiple filters\n
        :param df (pd.DataFrame): The DataFrame to filter
        :param column (str): Column to apply filter to
        :param condition (str): Comparison operator string
        :param value (Any): Value to compare against
        :param advanced_filters (List[Dict]): List of filter dicts for multi-conditional queries
        :return (pd.DataFrame): The filtered DataFrame
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"df is {type(df)}, expected pandas DataFrame")

        try:
            if advanced_filters:
                query_parts: List[str] = []
                query_params: Dict[str, Any] = {}
                for i, item in enumerate(advanced_filters):
                    logic = item.get("operator", "")
                    col = item["column"]
                    cond = item["condition"]
                    val = item["value"]

                    if col not in df.columns:
                        raise KeyError(f"Column '{col}' not found in DataFrame")

                    if cond == "Is Null":
                        clause = f"`{col}`.isna()"
                    elif cond == "Is Not Null":
                        clause = f"`{col}`.notna()"
                    else:
                        param_key = f"val_{i}"
                        query_params[param_key] = val
                        if cond == "contains":
                            clause = (
                                f"`{col}`.astype(str).str.contains"
                                f"(@query_params['{param_key}'], na=False)"
                            )
                        else:
                            clause = f"`{col}` {cond} @query_params['{param_key}']"

                    if logic:
                        query_parts.append(f" {logic.lower()} ")
                    query_parts.append(clause)

                full_query = "".join(query_parts)
                if full_query:
                    df = df.query(full_query, engine="python")
                return df

            if not column and not condition:
                return df

            if column not in df.columns:
                raise KeyError(f"Column '{column}' not found in DataFrame")

            col_dtype = df[column].dtype
            try:
                if pd.api.types.is_integer_dtype(col_dtype):
                    value = int(value)
                elif pd.api.types.is_float_dtype(col_dtype):
                    value = float(value)
                elif pd.api.types.is_object_dtype(col_dtype):
                    value = str(value)
            except (ValueError, TypeError):
                pass

            if condition == ">":
                df = df[df[column] > value]
            elif condition == "<":
                df = df[df[column] < value]
            elif condition == "==":
                df = df[df[column] == value]
            elif condition == "!=":
                df = df[df[column] != value]
            elif condition == ">=":
                df = df[df[column] >= value]
            elif condition == "<=":
                df = df[df[column] <= value]
            elif condition == "contains":
                df = df[df[column].astype(str).str.contains(str(value), na=False)]
            elif condition == "in":
                if not isinstance(value, (list, tuple, set)):
                    value = [value]
                df = df[df[column].isin(value)]
            else:
                raise ValueError(f"Unknown filter condition: {condition}")

            return df

        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Error filtering data: {e}", exc_info=True)
            raise

    @require_dataframe
    def sort_data(self, df: pd.DataFrame, column: str, ascending: bool = True, current_sort_state: Optional[tuple] = None) -> tuple[pd.DataFrame, tuple]:
        """
        Sort df by column\n
        :param df (pd.DataFrame): DataFrame to target
        :param column (str): Column to sort
        :param ascending (bool): Is Sort order ascending
        :param current_sort_state (Optional[tuple]): The current sort of the df
        :return (tuple[pd.DataFrame, tuple]): sorted_df, new_sort_state
        """
        if current_sort_state == (column, ascending):
            return df, current_sort_state

        try:
            if column not in df.columns:
                raise ValueError(f"Column '{column}' not found")

            df = df.sort_values(by=column, ascending=ascending)
            new_sort_state = (column, ascending)
            return df, new_sort_state
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Error sorting data: {e}", exc_info=True)
            raise

    @require_dataframe
    def aggregate_data(self, df: pd.DataFrame, group_by: List[str], agg_config: Dict[str, Union[str, List[str]]], date_grouping: Dict[str, str], rename_mapping: Optional[Dict[str, str]] = None) -> pd.DataFrame:
        """
        Aggregate df with per column aggregation functions and optional datetime grouping
        """
        try:
            groupers = []
            for col in group_by:
                if date_grouping and col in date_grouping:
                    freq_name = date_grouping[col]
                    pandas_freq = self.FrequencyMap.get(freq_name)
                    if pandas_freq:
                        groupers.append(pd.Grouper(key=col, freq=pandas_freq))
                    else:
                        groupers.append(col)
                else:
                    groupers.append(col)

            if not groupers:
                raise ValueError("No valid grouping columns provided")

            resolved_agg_config = resolve_agg_config(agg_config)
            df = df.groupby(groupers).agg(resolved_agg_config).reset_index()

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [f"{str(col[0])}_{str(col[1])}" if len(col) > 1 and col[1] else str(col[0]) for col in df.columns]
            
            if rename_mapping:
                df = df.rename(columns=rename_mapping)

            return df
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Error aggregating data: {e}", exc_info=True)
            raise

    def preview_aggregation(self, df: pd.DataFrame, group_by: List[str], agg_config: Dict[str, Union[str, List[str]]], date_grouping: Dict[str, str] = None, limit: int = 5, rename_mapping: Optional[Dict[str, str]] = None) -> pd.DataFrame:
        """
        Previews an aggregation without modifying the source DataFrame
        """
        if df is None:
            return pd.DataFrame()

        try:
            groupers = []
            for col in group_by:
                if date_grouping and col in date_grouping:
                    pandas_freq = self.FrequencyMap.get(date_grouping[col])
                    if pandas_freq:
                        groupers.append(pd.Grouper(key=col, freq=pandas_freq))
                    else:
                        groupers.append(col)
                else:
                    groupers.append(col)

            if not groupers or not agg_config:
                return pd.DataFrame()

            resolved_agg_config = resolve_agg_config(agg_config)
            preview_df = df.groupby(groupers).agg(resolved_agg_config).reset_index()

            if isinstance(preview_df.columns, pd.MultiIndex):
                preview_df.columns = [f"{str(col[0])}_{str(col[1])}" if len(col) > 1 and col[1] else str(col[0]) for col in preview_df.columns]

            if rename_mapping:
                preview_df = preview_df.rename(columns=rename_mapping)

            return preview_df.head(limit)
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Preview Calculation failed: {e}", exc_info=True)
            raise

    # DATA TRANSFORMATIONS
    @require_dataframe
    def melt_data(self, df: pd.DataFrame, id_vars: List[str], value_vars: List[str], var_name: str, value_name: str) -> pd.DataFrame:
        """Unpivoting a df from a wide to a long format"""
        try:
            v_vars = value_vars if value_vars else None
            df = pd.melt(df, id_vars=id_vars, value_vars=v_vars, var_name=var_name, value_name=value_name)
            return df
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Error melting data: {e}", exc_info=True)
            raise

    @require_dataframe
    def pivot_data(self, df: pd.DataFrame, index: List[str], columns: str, values: List[str], aggfunc: str) -> pd.DataFrame:
        """Creates a pivot table from a DataFrame"""
        try:
            df = pd.pivot_table(df, index=index, columns=columns, values=values, aggfunc=aggfunc).reset_index()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [f"{str(col[0])}_{str(col[1])}" if len(col) > 1 and col[1] else str(col[0]) for col in df.columns]
            df.columns.name = None
            return df
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Error pivoting data: {e}", exc_info=True)
            raise

    @require_dataframe
    def merge_data(self, df: pd.DataFrame, right_df: pd.DataFrame, how: str, left_on: List[str], right_on: List[str], suffixes: tuple = ("_left", "_right")) -> pd.DataFrame:
        """Merge the df with another df"""
        try:
            df = pd.merge(df, right_df, how=how, left_on=left_on, right_on=right_on, suffixes=suffixes)
            return df
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Merge operation failed: {e}", exc_info=True)
            raise

    @require_dataframe
    def concatenate_data(self, df: pd.DataFrame, other_df: pd.DataFrame, ignore_index: bool = True) -> pd.DataFrame:
        """Append rows from other_d* to df"""
        try:
            df = pd.concat([df, other_df], ignore_index=ignore_index)
            return df
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Concatenate operation failed: {e}", exc_info=True)
            raise

    @require_dataframe
    def create_computed_column(self, df: pd.DataFrame, new_column_name: str, expression: str) -> pd.DataFrame:
        """Add a column whose values are derived from a pandas eval expression"""
        try:
            if not new_column_name or not str(new_column_name).strip():
                raise ValueError("New column name cannot be empty")

            clean_name = str(new_column_name).strip()
            if clean_name in df.columns:
                raise ValueError(f"Column '{clean_name}' already exists")
            if keyword.iskeyword(clean_name):
                raise ValueError(
                    f"'{clean_name}' is a reserved Python keyword and cannot be used as a column name"
                )
            if "`" in clean_name:
                raise ValueError("Column names cannot contain backticks (`)")

            df[new_column_name] = df.eval(expression)
            return df
        except (ValueError, KeyError, TypeError, SyntaxError) as e:
            logger.error(f"Error computing and creating new column: {e}", exc_info=True)
            raise

    @require_dataframe
    def bin_column(self, df: pd.DataFrame, column: str, new_column_name: str, method: str, bins: Any, labels: List[str] = None, right_inclusive: bool = True, drop_original: bool = False) -> pd.DataFrame:
        """
        Bin a continuous variable into categorical buckets\n
        :param df (pd.DataFrame): The DataFrame to change
        :param column (str): The Target numerical column
        :param method (str): 'cut' for value-based, 'qcut' for quantile-based
        :param bins (Any): Number of bins or explicit bin edges
        :param labels (List[str]): Optional labels for the bins
        :param right_inclusive (bool): Whether intervals are closed on the right
        :param drop_original (bool): Whether to drop the tartget column after binning
        :return (pd.DataFrame):
        """
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found")
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise TypeError(f"Column '{column}' must be numeric for binning")

        try:
            if method == "qcut":
                df[new_column_name] = pd.qcut(df[column], q=bins, labels=labels, duplicates="drop")
            else:
                df[new_column_name] = pd.cut(df[column], bins=bins, labels=labels, include_lowest=True, right=right_inclusive)

            if not isinstance(df[new_column_name].dtype, pd.CategoricalDtype):
                df[new_column_name] = df[new_column_name].astype("category")

            if drop_original and column != new_column_name:
                df = df.drop(columns=[column])

            return df
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Error binning column: {e}", exc_info=True)
            raise

    @require_dataframe
    def run_statistical_test(self, df: pd.DataFrame, test_type: "Union[StatisticalTest, str]", col1: str, col2: str) -> Dict[str, Any]:
        """
        Run a statistical test on two numerical columns
        Supports T-test, ANOVA and Pearson corr test\n
        :param df (pd.DataFrame): The DataFrame to analyse
        :param test_type (StatisticalTest): A StatisticalTest type
        :param col1 (str): Name of the first column
        :param col2 (str): Name of the second column
        :return dict with keys (Dict[str, Any]): test, statistics, p_value, interpretation 
        """
        if not stats:
            raise ImportError(
                "The 'scipy' library is not installed. "
                "Scipy is required to perform any statistical tests"
            )
        if col1 not in df.columns or col2 not in df.columns:
            raise ValueError(f"Columns: '{col1}' or '{col2}' not found in the dataset")

        if isinstance(test_type, str):
            try:
                test_type = StatisticalTest(test_type.lower())
            except ValueError:
                raise ValueError(f"Unrecognized test type: {test_type}")

        data = df[[col1, col2]].dropna()
        if data.empty:
            raise ValueError("Insufficient data to perform test after dropping missing values")

        if test_type == StatisticalTest.T_TEST:
            stat, p_val = stats.ttest_ind(data[col1], data[col2])
            test_name = "Independent T-Test"
            sig = (
                "is a statistically significant difference"
                if p_val < 0.05
                else "is no statistically significant difference"
            )
            interpretation = (
                f"The T-Test compares the means of the two columns. "
                f"With a p-value of {p_val:.4e}, there <b>{sig}</b> between the means "
                f"of '{col1}' and '{col2}' at the typical 5% significance level (alpha = 0.05)."
            )
        elif test_type == StatisticalTest.ANOVA:
            stat, p_val = stats.f_oneway(data[col1], data[col2])
            test_name = "One-Way ANOVA"
            sig = (
                "is a statistically significant difference"
                if p_val < 0.05
                else "is no statistically significant difference"
            )
            interpretation = (
                f"ANOVA tests if the means of the groups are equal. "
                f"With a p-value of {p_val:.4e}, there <b>{sig}</b> between the means "
                f"of '{col1}' and '{col2}'. "
                f"(Note: for two groups, this is mathematically equivalent to the "
                f"Independent T-Test)."
            )
        elif test_type == StatisticalTest.PEARSON:
            stat, p_val = stats.pearsonr(data[col1], data[col2])
            test_name = "Pearson Correlation"
            sig = "significant" if p_val < 0.05 else "not significant"
            strength = (
                "strong" if abs(stat) >= 0.7 else "moderate" if abs(stat) >= 0.3 else "weak"
            )
            direction = "positive" if stat > 0 else "negative"
            interpretation = (
                f"Pearson measures the linear relationship between the two variables. "
                f"The correlation coefficient (r = {stat:.4f}) indicates a "
                f"<b>{strength} {direction}</b> relationship. "
                f"The p-value ({p_val:.4e}) shows this correlation is <b>{sig}</b>."
            )
        else:
            raise ValueError(f"Unrecognized test type: {test_type}")

        return {
            "test": test_name,
            "statistic": float(stat),
            "p_value": float(p_val),
            "interpretation": interpretation,
        }

    def detect_outliers(self, df: pd.DataFrame, method: str, columns: List[str], **kwargs) -> List[int]:
        """
        Detect outlier row indices in the *df*\n
        :param df (pd.DataFrame): DataFrame to analyse
        :param method (str): 'z_score', 'iqr', 'isolation_forest'
        :param columns (List[str]): Numeric column names
        :param **kwargs: Threshold, multuplier contamination 
        :return List[int]: Sorted list of row indices identified as outliers
        """
        if df is None:
            return []

        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.empty:
            raise ValueError("No numeric data is available to do outlier detection.")

        outlier_indices = set()

        if method == "z_score":
            threshold = kwargs.get("threshold", 3.0)
            if not stats:
                raise ImportError(
                    "Scipy is not installed. Scipy is required to perform Z-score analysis"
                )
            for column in columns:
                if column in numeric_df.columns:
                    col_data = df[column]
                    if isinstance(col_data, pd.DataFrame):
                        col_data = col_data.iloc[:, 0]
                    col_data = col_data.dropna()
                    if col_data.empty:
                        continue
                    z_scores = np.abs(stats.zscore(col_data.to_numpy()))
                    outliers = col_data.index[z_scores > threshold]
                    outlier_indices.update(outliers)

        elif method == "iqr":
            multiplier = kwargs.get("multiplier", 1.5)
            for column in columns:
                if column in numeric_df.columns:
                    col_data = df[column]
                    if isinstance(col_data, pd.DataFrame):
                        col_data = col_data.iloc[:, 0]
                    Q1 = col_data.quantile(0.25)
                    Q3 = col_data.quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - multiplier * IQR
                    upper_bound = Q3 + multiplier * IQR
                    outliers = col_data[
                        (col_data < lower_bound) | (col_data > upper_bound)
                    ].index.tolist()
                    outlier_indices.update(outliers)

        elif method == "isolation_forest":
            contamination = kwargs.get("contamination", 0.1)
            if not IsolationForest:
                raise ImportError(
                    "SciKit-learn not installed. "
                    "SciKit-learn is required to perform an Isolation Forest Analysis"
                )
            data_to_fit = df[columns].select_dtypes(include=[np.number]).fillna(0)
            if not data_to_fit.empty:
                clf = IsolationForest(contamination=contamination, random_state=42)
                preds = clf.fit_predict(data_to_fit)
                outliers = data_to_fit.index[preds == -1].tolist()
                outlier_indices.update(outliers)

        return sorted(list(outlier_indices))

    def _drop_duplicates(self, df: pd.DataFrame, sort_state, **kwargs):
        return df.drop_duplicates(), sort_state

    def _drop_missing(self, df: pd.DataFrame, sort_state, **kwargs):
        return df.dropna(), sort_state

    def _fill_missing(self, df: pd.DataFrame, sort_state, **kwargs):
        raw_method = kwargs.get("method", FillMethod.FFILL)
        try:
            method = FillMethod(raw_method) if isinstance(raw_method, str) else raw_method
        except ValueError:
            method = raw_method

        column = kwargs.get("column", "All Columns")
        val = kwargs.get("value", None)
        group_by = kwargs.get("group_by", None)

        target_cols = [c for c in (df.columns if column in ("All Columns", None) else [column]) if c != group_by]

        if method == FillMethod.TIME and not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("Time interpolation requires the dataframe to be a DatetimeIndex")

        is_grouped = bool(group_by and group_by in df.columns)

        for col in target_cols:
            is_num = pd.api.types.is_numeric_dtype(df[col])
            if method in (FillMethod.MEAN, FillMethod.MEDIAN, FillMethod.LINEAR, FillMethod.TIME) and not is_num:
                continue

            obj = df.groupby(group_by)[col] if is_grouped else df[col]

            if method == FillMethod.STATIC_VALUE:
                fill_val = val
                if is_num and isinstance(val, str):
                    try:
                        fill_val = float(val) if "." in val else int(val)
                    except ValueError:
                        pass
                df[col] = df[col].fillna(fill_val)
            elif method in (FillMethod.MEAN, FillMethod.MEDIAN):
                stat_name = "mean" if method == FillMethod.MEAN else "median"
                stat = obj.transform(stat_name) if is_grouped else getattr(df[col], stat_name)()
                df[col] = df[col].fillna(stat)
            elif method == FillMethod.MODE:
                if is_grouped:
                    df[col] = obj.transform(lambda x: x.fillna(x.mode().iloc[0] if not x.mode().empty else x))
                else:
                    modes = df[col].mode()
                    if not modes.empty:
                        df[col] = df[col].fillna(modes.iloc[0])
            elif method == FillMethod.FFILL:
                df[col] = obj.ffill()
            elif method == FillMethod.BFILL:
                df[col] = obj.bfill()
            elif method in (FillMethod.LINEAR, FillMethod.TIME):
                df[col] = df[col].interpolate(method=method.value)
        return df, sort_state

    def _drop_column(self, df: pd.DataFrame, sort_state, **kwargs):
        cols_to_drop = []
        if "columns" in kwargs:
            val = kwargs["columns"]
            cols_to_drop.extend(val if isinstance(val, list) else [val])
        if "column" in kwargs:
            cols_to_drop.append(kwargs["column"])
        cols_to_drop = list(set(cols_to_drop))

        if cols_to_drop:
            df = df.drop(columns=cols_to_drop)
            if sort_state and sort_state[0] in cols_to_drop:
                sort_state = None

        return df, sort_state

    def _rename_column(self, df: pd.DataFrame, sort_state, **kwargs):
        old_name = kwargs.get("old_name")
        new_name = kwargs.get("new_name")

        if old_name not in df.columns:
            raise ValueError(f"Column '{old_name}' does not exist in the dataset")
        if not new_name or not str(new_name).strip():
            raise ValueError("New column name cannot be empty or whitespace only.")

        clean_new_name = str(new_name).strip()
        if clean_new_name != old_name and clean_new_name in df.columns:
            raise ValueError(f"Column: '{clean_new_name}' already exists in the dataset")
        if keyword.iskeyword(clean_new_name):
            raise ValueError(
                f"'{clean_new_name}' is a reserved Python keyword and cannot be used as a column name"
            )
        if "`" in clean_new_name:
            raise ValueError("Column names cannot contain backticks (`)")

        df = df.rename(columns={old_name: new_name})
        return df, sort_state

    def _change_data_type(self, df: pd.DataFrame, sort_state, **kwargs):
        column = kwargs.get("column")
        new_type = kwargs.get("new_type")

        if not column or not new_type:
            raise ValueError("Column and new data type are needed to change data type")

        if new_type == "string":
            df[column] = df[column].astype(pd.StringDtype())
        elif new_type == "int":
            df[column] = pd.to_numeric(df[column], errors="coerce").astype(pd.Int64Dtype())
        elif new_type == "float":
            df[column] = pd.to_numeric(df[column], errors="coerce").astype(pd.Float64Dtype())
        elif new_type == "category":
            df[column] = df[column].astype("category")
        elif new_type == "datetime":
            df[column] = pd.to_datetime(df[column], errors="coerce")
        else:
            raise ValueError(f"Unsupported data type conversion: {new_type}")

        return df, sort_state

    def _text_manipulation(self, df: pd.DataFrame, sort_state, **kwargs):
        column = kwargs.get("column")
        operation = kwargs.get("operation")

        if not column and not operation:
            raise ValueError("Column and operation are required for text manipulation")
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found")

        try:
            if not (
                pd.api.types.is_string_dtype(df[column])
                or pd.api.types.is_object_dtype(df[column])
            ):
                raise TypeError("Column does not support string operations")

            op_map = {
                "lower": df[column].str.lower,
                "upper": df[column].str.upper,
                "title": df[column].str.title,
                "capitalize": df[column].str.capitalize,
                "strip": df[column].str.strip,
                "lstrip": df[column].str.lstrip,
                "rstrip": df[column].str.rstrip,
            }
            if operation not in op_map:
                raise ValueError(f"Unsupported text operation: {operation}")
            df[column] = op_map[operation]()
        except (AttributeError, TypeError):
            raise ValueError(
                f"Column '{column}' is not a text column. "
                f"Please convert it to 'string' first using 'Change Data Type'"
            )

        return df, sort_state

    def _split_column(self, df: pd.DataFrame, sort_state, **kwargs):
        column: str = kwargs.get("column")
        delimiter: str = kwargs.get("delimiter", " ")
        new_columns: list = kwargs.get("new_columns")

        if not column or not new_columns:
            raise ValueError("Column and new columns are required for splitting")
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found in the dataset")

        try:
            split_df = df[column].astype(str).str.split(delimiter, expand=True)
            for index, new_col_name in enumerate(new_columns):
                df[new_col_name] = split_df[index] if index < split_df.shape[1] else None
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Error splitting column '{column}': {e}", exc_info=True)
            raise

        return df, sort_state

    def _regex_replace(self, df: pd.DataFrame, sort_state, **kwargs):
        column: str = kwargs.get("column")
        pattern: str = kwargs.get("pattern")
        replacement: str = kwargs.get("replacement", "")

        if not column or not pattern:
            raise ValueError("Column and regex pattern are required for replacement")
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found in the dataset")

        try:
            df[column] = df[column].astype(str).str.replace(pattern, replacement, regex=True)
        except (ValueError, KeyError, TypeError, re.error) as e:
            logger.error(f"Error applying regex replacement to '{column}': {e}", exc_info=True)
            raise

        return df, sort_state

    def _remove_rows(self, df: pd.DataFrame, sort_state, **kwargs):
        rows_to_remove = kwargs.get("rows")
        if rows_to_remove:
            df = df.drop(index=rows_to_remove).reset_index(drop=True)
        return df, sort_state

    def _clip_outliers(self, df: pd.DataFrame, sort_state, **kwargs):
        method = kwargs.get("method")
        columns = kwargs.get("columns")

        if not method or not columns:
            raise ValueError("Method and columns are required for clipping outliers")

        if method == "z_score":
            threshold = kwargs.get("threshold", 3.0)
            if not stats:
                raise ImportError("Scipy is not installed. Scipy is required for Z-Score")
            for col in columns:
                if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                    col_data = df[col].dropna()
                    if col_data.empty:
                        continue
                    mean = col_data.mean()
                    std = col_data.std()
                    df[col] = df[col].clip(lower=mean - threshold * std, upper=mean + threshold * std)

        elif method == "iqr":
            multiplier = kwargs.get("multiplier", 1.5)
            for col in columns:
                if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                    Q1 = df[col].quantile(0.25)
                    Q3 = df[col].quantile(0.75)
                    IQR = Q3 - Q1
                    df[col] = df[col].clip(
                        lower=Q1 - multiplier * IQR, upper=Q3 + multiplier * IQR
                    )
        else:
            raise ValueError(f"Clipping is not supported for method: {method}")

        return df, sort_state

    def _duplicate_column(self, df: pd.DataFrame, sort_state, **kwargs):
        col = kwargs.get("column")
        new_col = kwargs.get("new_column")
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found")
        df[new_col] = df[col].copy()
        return df, sort_state

    def _normalize_data(self, df: pd.DataFrame, sort_state, **kwargs):
        columns: list = kwargs.get("columns", [])
        method: str = kwargs.get("method", "min_max")

        if not columns:
            raise ValueError("No columns specified for normalization")

        for col in columns:
            if col not in df.columns:
                raise ValueError(f"Column '{col}' not found.")
            if not pd.api.types.is_numeric_dtype(df[col]):
                raise TypeError(f"Column '{col}' must be numeric to perform normalization")

            col_data = df[col]
            if method == "min_max":
                min_val = col_data.min()
                max_val = col_data.max()
                if max_val != min_val:
                    df[col] = (col_data - min_val) / (max_val - min_val)
            elif method == "standard":
                mean_val = col_data.mean()
                std_val = col_data.std()
                if std_val != 0:
                    df[col] = (col_data - mean_val) / std_val
            elif method == "quantile":
                median_val = col_data.median()
                q75 = col_data.quantile(0.75)
                q25 = col_data.quantile(0.25)
                iqr = q75 - q25
                if iqr != 0:
                    df[col] = (col_data - median_val) / iqr
            else:
                raise ValueError(f"Unsupported normalization method: {method}")

        return df, sort_state

    def _extract_date_component(self, df: pd.DataFrame, sort_state, **kwargs):
        column: str = kwargs.get("column")
        component = kwargs.get("component")

        if not column or not component:
            raise ValueError("Column and datetime component are required.")
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found")

        if not pd.api.types.is_datetime64_any_dtype(df[column]):
            try:
                df[column] = pd.to_datetime(df[column], errors="coerce")
                if df[column].isna().all():
                    raise ValueError(f"Column '{column}' could not be converted to datetime")
            except Exception as error:
                raise ValueError(
                    f"Column '{column}' cannot be converted to datetime: {str(error)}"
                )

        safe_component = component.replace(" ", "_")
        new_col_name = f"{column}_{safe_component}"
        component_map = {
            "Year": lambda s: s.dt.year.astype("Int64"),
            "Month": lambda s: s.dt.month.astype("Int64"),
            "Month Name": lambda s: s.dt.month_name(),
            "Day": lambda s: s.dt.day.astype("Int64"),
            "Day of Week": lambda s: s.dt.day_name(),
            "Quarter": lambda s: s.dt.quarter.astype("Int64"),
            "Hour": lambda s: s.dt.hour.astype("Int64"),
        }
        if component not in component_map:
            raise ValueError(f"Unsupported date component: {component}")
        df[new_col_name] = component_map[component](df[column])

        return df, sort_state

    def _calculate_date_difference(self, df: pd.DataFrame, sort_state, **kwargs):
        col_start = kwargs.get("start_column")
        col_end = kwargs.get("end_column")
        unit = kwargs.get("unit", "Days")

        if not col_start or not col_end:
            raise ValueError("Start and End columns are required")

        for col in [col_start, col_end]:
            if col not in df.columns:
                raise ValueError(f"Column '{col}' not found")
            if not pd.api.types.is_datetime64_any_dtype(df[col]):
                try:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                except Exception:
                    raise ValueError(f"Column '{col}' must be a datetime column")

        diff_series = df[col_end] - df[col_start]
        raw_col = f"Diff_{unit}_{col_end}_vs_{col_start}"
        new_col = "".join(c if c.isalnum() or c == "_" else "" for c in raw_col)

        unit_map = {
            "Days": lambda s: s.dt.days,
            "Hours": lambda s: s.dt.total_seconds() / 3600,
            "Minutes": lambda s: s.dt.total_seconds() / 60,
            "Seconds": lambda s: s.dt.total_seconds(),
            "Weeks": lambda s: s.dt.days / 7,
        }
        if unit not in unit_map:
            raise ValueError(f"Unsupported date difference unit: {unit}")
        df[new_col] = unit_map[unit](diff_series)

        return df, sort_state

    def _flag_outliers(self, df: pd.DataFrame, sort_state, **kwargs):
        rows = kwargs.get("rows")
        new_column_name = kwargs.get("new_column_name", "is_outlier")

        if not new_column_name:
            raise ValueError("A new column name is required before flagging outliers")
        if new_column_name in df.columns:
            raise ValueError(f"Column name '{new_column_name}' already exists")

        df[new_column_name] = False
        if rows:
            mask = df.index.isin(rows)
            df.loc[mask, new_column_name] = True

        return df, sort_state

    def _reorder_columns(self, df: pd.DataFrame, sort_state: Optional[tuple], **kwargs) -> tuple[pd.DataFrame, Optional[tuple]]:
        """
        Reorders the columns of the DataFrame
        Validates that no columns are dropped during the reordreing
        """
        new_order: list[str] = kwargs.get("new_order", [])

        if not new_order:
            raise ValueError("A new column order must be provided")

        # Verify that the new col order has the same cols as before
        missing_cols = set(df.columns) - set(new_order)
        extra_cols = set(new_order) - set(df.columns)

        if missing_cols or extra_cols:
            raise ValueError(f"Column mismatch. Missing: {missing_cols}, Extra: {extra_cols}")

        # Reindex the df with the new ordered list
        df = df[new_order]

        return df, sort_state

    def _drop_empty_columns(self, df: pd.DataFrame, sort_state: Optional[tuple], **kwargs) -> tuple[pd.DataFrame, Optional[tuple]]:
        """Removes columns where all values are missing"""
        cols_to_drop: list[str] = df.columns[df.isna().all()].tolist()
        if cols_to_drop:
            df = df.drop(columns=cols_to_drop)
            if sort_state and sort_state[0] in cols_to_drop:
                sort_state = None
        return df, sort_state

    def _apply_rolling_window(self, df: pd.DataFrame, sort_state: Optional[tuple], **kwargs) -> tuple[pd.DataFrame, Optional[tuple]]:
        """Applies a rolling window operations to a numeric column

        Args:
            df (pd.DataFrame): Input dataframe
            sort_state (Optional[tuple]): Current sort state

        Returns:
            tuple[pd.DataFrame, Optional[tuple]]: New dataframe, Sort state if changed
        """
        column: str = kwargs.get("column")
        window: int = kwargs.get("window", 3)
        operation: str = kwargs.get("operation", "mean")
        new_column: str = kwargs.get("new_column")
        center: bool = kwargs.get("center", False)
        min_periods: Optional[int] = kwargs.get("min_periods", None)

        if not column or column not in df.columns:
            raise ValueError(f"Column '{column}' not found")
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise TypeError(f"Column '{column}' must be a numeric column to perform rolling window operation")

        if not new_column:
            new_column = f"{column}_rolling_{window}_{operation}"

        if new_column in df.columns and new_column != column:
            raise ValueError(f"Column '{column}' already exists")

        rolling_obj = df[column].rolling(window=window, center=center, min_periods=min_periods)

        if operation == "mean":
            df[new_column] = rolling_obj.mean()
        elif operation == "sum":
            df[new_column] = rolling_obj.sum()
        elif operation == "min":
            df[new_column] = rolling_obj.min()
        elif operation == "max":
            df[new_column] = rolling_obj.max()
        elif operation == "std":
            df[new_column] = rolling_obj.std()
        elif operation == "median":
            df[new_column] = rolling_obj.median()
        else:
            raise ValueError(f"Unsupported rolling operation: {operation}")

        return df, sort_state

    def _apply_shift(self, df: pd.DataFrame, sort_state: Optional[tuple], **kwargs) -> tuple[pd.DataFrame, Optional[tuple]]:
        """Applies a shift operation on a column

        Args:
            df (pd.DataFrame): Input dataframe
            sort_state (Optional[tuple]): Current sort state

        Returns:
            tuple[pd.DataFrame, Optional[tuple]]: New dataframe, Sort state if changed
        """
        column: str = kwargs.get("column")
        periods: int = kwargs.get("periods", 1)
        fill_value: Any = kwargs.get("fill_value", None)
        new_column: Optional[str] = kwargs.get("new_column")

        if not column or column not in df.columns:
            raise ValueError(f"Column '{column}' not found")

        if not new_column:
            new_column = f"{column}_shifted_{periods}"

        if new_column in df.columns and new_column != column:
            raise ValueError(f"Column '{new_column}' already exists")

        df[new_column] = df[column].shift(periods=periods, fill_value=fill_value)

        return df, sort_state

    def _apply_pct_change(self, df: pd.DataFrame, sort_state: Optional[tuple], **kwargs) -> tuple[pd.DataFrame, Optional[tuple]]:
        """Calculates the percentage change between the current and a prior element.

        Args:
            df (pd.DataFrame): Input dataframe
            sort_state (Optional[tuple]): Current sort state

        Returns:
            tuple[pd.DataFrame, Optional[tuple]]: New dataframe, Sort state if changed
        """
        column: str = kwargs.get("column")
        periods: int = kwargs.get("periods", 1)
        fill_method: str = kwargs.get("fill_method", "pad")
        new_column: Optional[str] = kwargs.get("new_column")

        if not column or column not in df.columns:
            raise ValueError(f"Column '{column}' not found")
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise TypeError(f"Column '{column}' must be a numeric column to calculate percentage change")

        if not new_column:
            new_column = f"{column}_pct_change_{periods}"

        if new_column in df.columns and new_column != column:
            raise ValueError(f"Column '{new_column}' already exists")

        try:
            df[new_column] = df[column].pct_change(periods=periods, fill_method=fill_method)
        except TypeError:
            temp_col = df[column].ffill() if fill_method in ['pad', 'ffill'] else df[column].bfill() if fill_method in ['backfill', 'bfill'] else df[column]
            df[new_column] = temp_col.pct_change(periods=periods)

        return df, sort_state