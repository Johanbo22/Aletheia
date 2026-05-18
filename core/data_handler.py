import atexit
import pandas as pd
from pathlib import Path
from typing import Any, Dict, Optional, Union, Callable, List
import numpy as np

from core.data_io_manager import DataIOManager
from core.data_mutator import DataMutator, DataOperation, FillMethod, StatisticalTest
from core.history_manager import HistoryManager

class DataHandler:
    """
    Data handling bridge to connect submanagers API with rest of application
    """
    FrequencyMap = DataMutator.FrequencyMap
    
    def __init__(self) -> None:
        self._io = DataIOManager()
        self._mutator = DataMutator()
        self._history = HistoryManager()
        
        self.df: Optional[pd.DataFrame] = None
        self.original_df: Optional[pd.DataFrame] = None
        
        atexit.register(self.cleanup_temp_files)
    
    @property
    def file_path(self) -> Optional[Path]:
        return self._io.file_path
    
    @property
    def temp_csv_path(self) -> Optional[Path]:
        return self._io.temp_csv_path
    
    @property
    def is_temp_file(self) -> bool:
        return self._io.is_temp_file
    
    @property
    def sort_state(self) -> Optional[tuple]:
        return self._history.sort_state
    
    @sort_state.setter
    def sort_state(self, value: Optional[tuple]) -> None:
        self._history.sort_state = value
        
    @property
    def operation_log(self) -> List[Dict[str, Any]]:
        return self._history.operation_log
    
    @operation_log.setter
    def operation_log(self, value: List[Dict[str, Any]]) -> None:
        self._history.operation_log = value
    
    @property
    def undo_stack(self):
        return self._history.undo_stack
    
    @property
    def redo_stack(self):
        return self._history.redo_stack
    
    @property
    def max_history_memory_bytes(self) -> int:
        return self._history.max_history_memory_bytes
    
    @max_history_memory_bytes.setter
    def max_history_memory_bytes(self, value: int) -> None:
        self._history.max_history_memory_bytes = value
        
    @property
    def memory_update_callback(self) -> Optional[Callable]:
        return self._history.memory_update_callback
    
    @memory_update_callback.setter
    def memory_update_callback(self, value: Optional[Callable]) -> None:
        self._history.memory_update_callback = value
        
    @property
    def last_gsheet_id(self): 
        return self._io.last_gsheet_id
    @property
    def last_gsheet_name(self): 
        return self._io.last_gsheet_name
    @property
    def last_gsheet_delimiter(self): 
        return self._io.last_gsheet_delimiter
    @property
    def last_gsheet_decimal(self): 
        return self._io.last_gsheet_decimal
    @property
    def last_gsheet_thousands(self): 
        return self._io.last_gsheet_thousands
    @property
    def last_gsheet_gid(self): 
        return self._io.last_gsheet_gid
    
    @property
    def last_db_connection_string(self): 
        return self._io.last_db_connection_string
    @property
    def last_db_query(self): 
        return self._io.last_db_query
    
    def _reset_history(self) -> None:
        self._history.clear()
    
    def cleanup_temp_files(self) -> None:
        self._io.cleanup_temp_files()
    
    def read_file(self, filepath: str) -> pd.DataFrame:
        return self._io.read_file(filepath)
    
    def import_file(self, filepath: str) -> pd.DataFrame:
        df = self._io.import_file(filepath)
        self.df = df
        self.original_df = df.copy()
        self._reset_history()
        return self.df
    
    def import_google_sheets(self, sheet_id: str, sheet_name: str, delimiter: str = ",", decimal: str = ".", thousands: str = None, gid: str = None) -> pd.DataFrame:
        df, _ = self._io.import_google_sheets(
            sheet_id=sheet_id,
            sheet_name=sheet_name,
            delimiter=delimiter,
            decimal=decimal,
            thousands=thousands,
            gid=gid
        )
        self.df = df
        self.original_df = df.copy()
        self._reset_history()
        return self.df
    
    def import_from_database(self, connection_string: str, query: str) -> pd.DataFrame:
        df, _ = self._io.import_from_database(connection_string, query)
        self.df = df
        self.original_df = df.copy()
        self._reset_history()
        return self.df
    
    def refresh_google_sheets(self) -> pd.DataFrame:
        if not self._io.is_google_sheet_import():
            raise ValueError("No history of a Google Sheets import")
        
        params = self._io.get_google_sheets_refresh_params()
        thousands_param = (None if params["thousands"] in [None, "None", ""] else params["thousands"])
        
        return self.import_google_sheets(sheet_id=params["sheet_id"], sheet_name=params["sheet_name"], delimiter=params["delimiter"], decimal=params["decimal"], thousands=thousands_param, gid=params["gid"])
    
    def create_empty_dataframe(self, rows: int, columns: int, column_names: List[str] = None, fill_value: Any = None) -> pd.DataFrame:
        try:
            self._save_state()
            
            if not column_names:
                column_names = [f"Column_{i + 1}" for i in range(columns)]
            
            if fill_value is None or (isinstance(fill_value, str) and fill_value == "NaN"):
                data = np.full((rows, len(column_names)), np.nan)
            else:
                data = np.full((rows, len(column_names)), fill_value)
            
            self.df = pd.DataFrame(data, index=range(rows), columns=column_names)
            self.original_df = self.df.copy()
            
            self._io.file_path = None
            self._io.is_temp_file = False
            self._io.last_gsheet_id = None
            self._io.last_gsheet_name = None
            self._io.last_db_connection_string = None
            self._io.last_db_query = None
            self._reset_history()
            return self.df
        except Exception as CreateEmptyDataframeError:
            raise Exception(f"Error creating DataFrame: {str(CreateEmptyDataframeError)}")
    
    def export_data(self, filepath: str, format: str = "csv", include_index: bool = False) -> None:
        self._io.export_data(self.df, filepath, format=format, include_index=include_index)
    
    def export_google_sheets(self, credentials_path: str, sheet_id: str, sheet_name: str = "Sheet1") -> bool:
        result = self._io.export_google_sheets(self.df, credentials_path, sheet_id, sheet_name)
        self._history.operation_log.append({
            "type": "export_google_sheets",
            "sheet_id": sheet_id,
            "sheet_name": sheet_name,
        })
        return result
    
    def has_google_sheet_import(self) -> bool:
        return self._io.has_google_sheet_import()
    
    def has_google_sheets_import(self) -> bool:
        return self._io.is_google_sheet_import()
    
    def get_data_source(self) -> Dict[str, Any]:
        info = self._io.get_data_source_info()
        info["has_data"] = self.df is not None
        return info
    
    def get_data_info(self) -> Dict[str, Any]:
        if self.df is None:
            return {}
        return {
            "shape": self.df.shape,
            "columns": list(self.df.columns),
            "dtypes": self.df.dtypes.to_dict(),
            "missing_values": self.df.isnull().sum().to_dict(),
            "statistics": self.df.describe().to_dict(),
            "memory_usage": self.df.memory_usage(deep=True).to_dict(),
        }
    
    def _save_state(self) -> None:
        self._history.save_state(self.df)
        
    def undo(self) -> bool:
        restored_df, success = self._history.undo(self.df)
        if success:
            self.df = restored_df
        return success
    
    def redo(self) -> bool:
        restored_df, success = self._history.redo(self.df)
        if success:
            self.df = restored_df
        return success
    
    def can_undo(self) -> bool:
        return self._history.can_undo()

    def can_redo(self) -> bool:
        return self._history.can_redo()
    
    def reset_data(self) -> None:
        if self.original_df is not None:
            self._reset_history()
            self.df = self.original_df.copy()
    
    def jump_to_history_index(self, target_index: int) -> None:
        current_index = len(self._history.undo_stack)
        if target_index == current_index:
            return

        if target_index < current_index:
            for _ in range(current_index - target_index):
                if not self.undo():
                    break
        else:
            for _ in range(target_index - current_index):
                if not self.redo():
                    break
    
    def get_history_info(self) -> Dict[str, Any]:
        return self._history.get_history_info()

    def export_pipeline_macro(self, filepath: str) -> None:
        self._history.export_pipeline_macro(filepath)
    
    def apply_pipeline_macro(self, macro_source: "str | list") -> None:
        if self.df is None:
            raise ValueError("No data loaded to apply")

        operations = self._history.load_pipeline_macro(macro_source)

        df_backup = self.df.copy()
        log_backup = self._history.operation_log.copy()
        redo_backup = self._history.redo_stack.copy()
        current_op_type = "Unknown"

        try:
            for op in operations:
                current_op_type = op.get("type", "unknown")
                if current_op_type == "unknown":
                    continue

                kwargs = {k: v for k, v in op.items() if k != "type"}

                if current_op_type == "filter":
                    self.filter_data(
                        column=kwargs.get("column"),
                        condition=kwargs.get("condition"),
                        value=kwargs.get("value"),
                    )
                elif current_op_type == "filter_multiple":
                    self.filter_data(advanced_filters=kwargs.get("filters"))
                elif current_op_type == "sort":
                    self.sort_data(
                        column=kwargs.get("column"),
                        ascending=kwargs.get("ascending", True),
                    )
                elif current_op_type == "computed_column":
                    self.create_computed_column(
                        new_column_name=kwargs.get("new_column"),
                        expression=kwargs.get("expression"),
                    )
                elif current_op_type == "aggregate":
                    self.aggregate_data(
                        group_by=kwargs.get("group_by", []),
                        agg_config=kwargs.get("agg_config", {}),
                        date_grouping=kwargs.get("date_grouping", {}),
                        rename_mapping=kwargs.get("rename_mapping", None)
                    )
                elif current_op_type == "melt":
                    self.melt_data(
                        id_vars=kwargs.get("id_vars", []),
                        value_vars=kwargs.get("value_vars", []),
                        var_name=kwargs.get("var_name", "variable"),
                        value_name=kwargs.get("value_name", "value"),
                    )
                elif current_op_type == "pivot":
                    self.pivot_data(
                        index=kwargs.get("index", []),
                        columns=kwargs.get("columns", ""),
                        values=kwargs.get("values", []),
                        aggfunc=kwargs.get("aggfunc", "mean"),
                    )
                elif current_op_type == "bin_column":
                    self.bin_column(
                        column=kwargs.get("column"),
                        new_column_name=kwargs.get("new_column"),
                        method=kwargs.get("method"),
                        bins=kwargs.get("bins"),
                        labels=kwargs.get("labels"),
                    )
                elif current_op_type == "update_cell":
                    self.update_cell(
                        row_index=kwargs.get("row"),
                        column_index=kwargs.get("col"),
                        value=kwargs.get("value"),
                    )
                elif current_op_type in ["merge", "concatenate", "export_google_sheets"]:
                    continue
                else:
                    self.clean_data(action=current_op_type, **kwargs)

        except Exception as e:
            self.df = df_backup
            self._history.operation_log = log_backup
            self._history.redo_stack = redo_backup
            raise Exception(
                f"Macro execution aborted. Data rolled back to original state.\n"
                f"Reason: Failed on operation '{current_op_type}' -> {str(e)}"
            )
    
    def run_statistical_test(self, test_type: "Union[StatisticalTest, str]", col1: str, col2: str) -> Dict[str, Any]:
        return self._mutator.run_statistical_test(self.df, test_type, col1, col2)
    
    def detect_outliers(self, method: str, columns: List[str], **kwargs) -> List[int]:
        return self._mutator.detect_outliers(self.df, method, columns, **kwargs)

    def _apply_changes(self, changed_df: pd.DataFrame, log_entry: Dict[str, Any], new_sort_state: Optional[tuple] = None) -> pd.DataFrame:
        self.df = changed_df
        self._history.operation_log.append(log_entry)
        if new_sort_state is not None:
            self._history.sort_state = new_sort_state
        return self.df
    
    def update_cell(self, row_index: int, column_index: int, value: Any) -> None:
        if self.df is None:
            return
        self._save_state()
        changed_df = self._mutator.update_cell(self.df, row_index, column_index, value)
        self._apply_changes(changed_df, {"type": "update_cell", "row": row_index, "col": column_index, "value": value})
        
    def filter_data(self, column: str = None, condition: str = None, value: Any = None, advanced_filters: List[Dict] = None) -> pd.DataFrame:
        if self.df is None:
            raise ValueError("No data loaded")
        self._save_state()
        changed_df = self._mutator.filter_data(
            self.df,
            column=column,
            condition=condition,
            value=value,
            advanced_filters=advanced_filters,
        )
        if advanced_filters:
            log_entry = {"type": "filter_multiple", "filters": advanced_filters}
        else:
            log_entry = {"type": "filter", "column": column, "condition": condition, "value": value}
        return self._apply_changes(changed_df, log_entry)

    def apply_filter(self, filter_config: Dict[str, Any]) -> pd.DataFrame:
        if not isinstance(filter_config, dict):
            raise ValueError("Filter configuration must be a dictionary")
        if filter_config.get("logic") == "COMPLEX":
            return self.filter_data(advanced_filters=filter_config.get("filters", []))
        return self.df
    
    def sort_data(self, column: str, ascending: bool = True) -> pd.DataFrame:
        if self.df is None:
            raise ValueError("No data loaded")
        if self._history.sort_state == (column, ascending):
            return self.df
        try:
            self._save_state()
            changed_df, new_sort_state = self._mutator.sort_data(
                self.df, column, ascending, self._history.sort_state
            )
            return self._apply_changes(
                changed_df,
                {"type": "sort", "column": column, "ascending": ascending},
                new_sort_state=new_sort_state,
            )
        except Exception as SortDataError:
            raise Exception(f"Error sorting data: {str(SortDataError)}")
    
    def aggregate_data(self, group_by: List[str], agg_config: Dict[str, Union[str, List[str]]], date_grouping: Dict[str, str], rename_mapping: Optional[Dict[str, str]] = None) -> pd.DataFrame:
        if self.df is None:
            raise ValueError("No data loaded")
        self._save_state()
        changed_df = self._mutator.aggregate_data(self.df, group_by, agg_config, date_grouping, rename_mapping)
        self._history.sort_state = None
        return self._apply_changes(
            changed_df,
            {
                "type": "aggregate",
                "group_by": group_by,
                "agg_config": agg_config,
                "date_grouping": date_grouping,
                "rename_mapping": rename_mapping
            },
            new_sort_state=None,
        )

    def preview_aggregation(self, group_by: List[str], agg_config: Dict[str, Union[str, List[str]]], date_grouping: Dict[str, str] = None, limit: int = 5,) -> pd.DataFrame:
        return self._mutator.preview_aggregation(
            self.df, group_by, agg_config, date_grouping, limit
        )
    
    def melt_data(self, id_vars: List[str], value_vars: List[str], var_name: str, value_name: str,) -> pd.DataFrame:
        if self.df is None:
            raise ValueError("No data loaded")
        self._save_state()
        changed_df = self._mutator.melt_data(self.df, id_vars, value_vars, var_name, value_name)
        self._history.sort_state = None
        return self._apply_changes(
            changed_df,
            {
                "type": "melt",
                "id_vars": id_vars,
                "value_vars": value_vars,
                "var_name": var_name,
                "value_name": value_name,
            },
            new_sort_state=None,
        )
    
    def pivot_data(self, index: List[str], columns: str, values: List[str], aggfunc: str) -> pd.DataFrame:
        if self.df is None:
            raise ValueError("No data loaded")
        self._save_state()
        changed_df = self._mutator.pivot_data(self.df, index, columns, values, aggfunc)
        return self._apply_changes(
            changed_df,
            {"type": "pivot", "index": index, "columns": columns, "values": values, "aggfunc": aggfunc},
            new_sort_state=None,
        )

    def merge_data(self, right_df: pd.DataFrame, how: str, left_on: List[str], right_on: List[str], suffixes: tuple = ("_left", "_right"),) -> pd.DataFrame:
        if self.df is None:
            raise ValueError("No active data to merge with.")
        self._save_state()
        changed_df = self._mutator.merge_data(self.df, right_df, how, left_on, right_on, suffixes)
        return self._apply_changes(
            changed_df,
            {"type": "merge", "how": how, "left_on": left_on, "right_on": right_on, "suffixes": suffixes},
            new_sort_state=None,
        )

    def concatenate_data(self, other_df: pd.DataFrame, ignore_index: bool = True) -> pd.DataFrame:
        if self.df is None:
            raise ValueError("No active data to append to")
        self._save_state()
        changed_df = self._mutator.concatenate_data(self.df, other_df, ignore_index)
        return self._apply_changes(
            changed_df,
            {"type": "concatenate", "ignore_index": ignore_index},
            new_sort_state=None,
        )

    def create_computed_column(self, new_column_name: str, expression: str) -> pd.DataFrame:
        if self.df is None:
            raise ValueError("No data loaded")
        self._save_state()
        changed_df = self._mutator.create_computed_column(self.df, new_column_name, expression)
        return self._apply_changes(
            changed_df,
            {"type": "computed_column", "new_column": new_column_name, "expression": expression},
        )

    def bin_column(self, column: str, new_column_name: str, method: str, bins: Any, labels: List[str] = None, right_inclusive: bool = True, drop_original: bool = False) -> pd.DataFrame:
        if self.df is None:
            raise ValueError("No data loaded")
        self._save_state()
        changed_df = self._mutator.bin_column(
            self.df, column, new_column_name, method, bins, labels, right_inclusive, drop_original
        )
        return self._apply_changes(
            changed_df,
            {
                "type": "bin_column",
                "column": column,
                "new_column": new_column_name,
                "method": method,
                "bins": bins,
                "labels": labels,
            },
        )

    def clean_data(self, action: "DataOperation | str", **kwargs) -> pd.DataFrame:
        """Dispatch a cleaning/mutation action via the DataMutator registry."""
        if self.df is None:
            raise ValueError("No data loaded")
        try:
            self._save_state()
            changed_df, new_sort_state = self._mutator.clean_data(
                self.df, action, self._history.sort_state, **kwargs
            )
            if isinstance(action, str):
                action_value = action
            else:
                action_value = action.value
            return self._apply_changes(
                changed_df,
                {"type": action_value, **kwargs},
                new_sort_state=new_sort_state,
            )
        except Exception as CleanDataError:
            raise Exception(f"Error cleaning data: {str(CleanDataError)}")