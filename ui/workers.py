from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot, QThread
import pandas as pd
import numpy as np


from core.data_handler import DataHandler
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.subset_manager import SubsetManager


class WorkerSignals(QObject):
    """
    Defines the signal from a running worker thread
    signals are:

    finished
        object: data (pd.DataFrame)
    error
        Exception: The exception object
    log
        str: A message to log
    """
    finished = pyqtSignal(object)
    error = pyqtSignal(Exception)
    log = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    
class AggregationWorker(QRunnable):
    """Worker for performing data aggregation"""
    def __init__(self, data_handler: DataHandler, group_by: list[str], agg_config: dict[str, str], date_grouping: dict[str, str]) -> None:
        super().__init__()
        self.data_handler = data_handler
        self.group_by = group_by
        self.agg_config = agg_config
        self.date_grouping = date_grouping
        self.signals = WorkerSignals()
    
    @pyqtSlot()
    def run(self):
        try:
            self.signals.progress.emit(10, "Preparing Aggregation...")
            self.signals.log.emit(f"Starting background aggregation task with {len(self.group_by)} groups...")
            result_df = self.data_handler.preview_aggregation(group_by=self.group_by, agg_config=self.agg_config, date_grouping=self.date_grouping, limit=None)
            
            self.signals.progress.emit(100, "Aggregation complete")
            self.signals.log.emit("Background aggregation task completed successfully.")
            self.signals.finished.emit(result_df)
        except Exception as AggWorkerError:
            self.signals.log.emit(f"Aggregation worker failed: {str(AggWorkerError)}")
            self.signals.error.emit(AggWorkerError)

class FilterWorker(QRunnable):
    """Worker for applying filters"""
    
    def __init__(self, data_handler: DataHandler, filter_config: dict):
        super().__init__()
        self.data_handler = data_handler
        self.filter_config = filter_config
        self.signals = WorkerSignals()
    
    @pyqtSlot()
    def run(self):
        try:
            self.signals.progress.emit(10, "Applying filters...")
            
            result_df = self.data_handler.apply_filter(self.filter_config)
            self.signals.progress.emit(100, "Filtering complete")
            self.signals.finished.emit(result_df)
        except Exception as Error:
            self.signals.error.emit(Error)

class FileImportWorker(QRunnable):
    """The worker thread for importing files"""

    def __init__(self, data_handler: DataHandler, filepath: str):
        super().__init__()
        self.data_handler = data_handler
        self.filepath = filepath
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            self.signals.progress.emit(10, "Reading file...")
            self.data_handler.import_file(self.filepath)

            self.signals.progress.emit(70, "Processing data...")
            self.signals.finished.emit(self.data_handler.df)
        except Exception as RunError:
            self.signals.error.emit(RunError)


class GoogleSheetsImportWorker(QRunnable):
    """Worker thread for imports using Google Sheets"""
    def __init__(self, data_handler: DataHandler, sheet_id: str, sheet_name: str, delimiter: str, decimal: str, thousands: str, gid: str = None):
        super().__init__()
        self.data_handler = data_handler
        self.sheet_id = sheet_id
        self.sheet_name = sheet_name
        self.delimiter = delimiter
        self.decimal = decimal
        self.thousands = thousands
        self.gid = gid
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            self.signals.progress.emit(10, "Connecting to Google Sheets...")
            self.data_handler.import_google_sheets(
                self.sheet_id,
                self.sheet_name,
                delimiter=self.delimiter,
                decimal=self.decimal,
                thousands=self.thousands,
                gid=self.gid
            )

            self.signals.progress.emit(70, "Processing data...")
            self.signals.finished.emit(self.data_handler.df)
        except Exception as RunError:
            self.signals.error.emit(RunError)

class TestConnectionWorker(QRunnable):
    """Worker to test database connections"""

    def __init__(self, connection_string: str):
        super().__init__()
        self.connection_string = connection_string
        self.signals = WorkerSignals()
    
    @pyqtSlot()
    def run(self):
        try:
            self.signals.progress.emit(10, "Connecting...")
            engine = create_engine(self.connection_string)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.signals.progress.emit(100, "Connection Successful")
            self.signals.finished.emit(True)
        except Exception as ConnectionError:
            self.signals.error.emit(ConnectionError)

class FetchSchemaWorkerSignals(QObject):
    """Signals for the FetchSchemaWorker"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

class FetchSchemaWorker(QRunnable):
    """Worker thread to fetch database schema asynch"""
    def __init__(self, connection_string: str) -> None:
        super().__init__()
        self.connection_string = connection_string
        self.signals = FetchSchemaWorkerSignals()
    
    def run(self) -> None:
        engine = None
        try:
            engine = create_engine(self.connection_string)
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            schema_data = []
            
            for table in table_names:
                columns = []
                try:
                    columns = inspector.get_columns(table)
                except SQLAlchemyError as InspectorError:
                    if "sqlite" in self.connection_string.lower():
                        try:
                            with engine.connect() as conn:
                                result = conn.execute(text(f'PRAGMA table_info("{table}")'))
                                columns = [{"name": row[1], "type": row[2]} for row in result]
                        except SQLAlchemyError as FallbackError:
                            print(f"Fallback inspection failed for {table}: {FallbackError}")
                schema_data.append({"table": table, "columns": columns})
            
            self.signals.finished.emit(schema_data)
        except Exception as err:
            self.signals.error.emit(err)
        finally:
            if engine is not None:
                engine.dispose()

class AutoCreateSubsetsWorker(QRunnable):
    """Worker thread for auto-creating and applying subsets"""
    
    def __init__(self, subset_manager: "SubsetManager", df, column: str):
        super().__init__()
        self.subset_manager = subset_manager
        self.df = df
        self.column = column
        self.signals = WorkerSignals()
    
    @pyqtSlot()
    def run(self):
        try:
            self.signals.progress.emit(10, f"Auto-creating subsets")
            created = self.subset_manager.create_subset_from_unique_values(self.df, self.column)
            
            total = len(created)
            if total == 0:
                self.signals.progress.emit(100, "No new subsets created.")
                self.signals.finished.emit(created)
                return
            
            for i, name in enumerate(created):
                progress = 10 + int((i / total) * 85)
                self.signals.progress.emit(progress, f"Applying subset {i+1} of {total}: {name}...")
                
                self.subset_manager.apply_subset(self.df, name)
            
            self.signals.progress.emit(100, "Finalizing...")
            self.signals.finished.emit(created)
        except Exception as Error:
            self.signals.error.emit(Error)

class PlotDataPrepWorker(QRunnable):
    def __init__(self, df: pd.DataFrame, plot_type: str, x_col: str, y_cols: list[str], quick_filter: str):
        super().__init__()
        self.df = df
        self.plot_type = plot_type
        self.x_col = x_col
        self.y_cols = y_cols
        self.quick_filter = quick_filter
        self.signals = WorkerSignals()
        
    def _is_datetime_column(self, data: pd.Series) -> bool:
        if pd.api.types.is_datetime64_any_dtype(data):
            return True
        if data.dtype == "object":
            if data.empty:
                return False
            sample_val = data.dropna().head(1)
            if sample_val.empty:
                return False
            val = sample_val.iloc[0]
            if not isinstance(val, str):
                return False
            try:
                pd.to_datetime(val, utc=True)
                return True
            except (ValueError, TypeError):
                return False
        return False
    
    @pyqtSlot()
    def run(self):
        try:
            self.signals.progress.emit(10, "Copying data...")
            processed_df = self.df.copy()
            
            if self.quick_filter:
                self.signals.progress.emit(20, f"Applying quick filter: {self.quick_filter}...")
                processed_df = processed_df.query(self.quick_filter)
                if processed_df.empty:
                    raise ValueError(f"The filter '{self.quick_filter}' returned an empty dataset")
            
            self.signals.progress.emit(50, "Sampling data...")
            MAX_PLOT_POINTS = 500_000
            PLOTS_TO_SAMPLE = ["Scatter", "Line", "2D Density", "Hexbin", "Stem", "Stairs", "Eventplot", "ECDF", "2D Histogram", "Tricontour", "Tricontourf", "Tripcolor", "Triplot"]

            if len(processed_df) > MAX_PLOT_POINTS and self.plot_type in PLOTS_TO_SAMPLE:
                self.signals.log.emit(f"Dataset is too large ({len(processed_df)} rows) for '{self.plot_type}'. Plotting a random sample of {MAX_PLOT_POINTS:,} points.")
                processed_df = processed_df.sample(n=MAX_PLOT_POINTS, random_state=42)
            
            self.signals.progress.emit(75, "Converting datetime columns...")
            if self.x_col and self.x_col in processed_df.columns:
                if self._is_datetime_column(processed_df[self.x_col]):
                    if not pd.api.types.is_datetime64_any_dtype(processed_df[self.x_col]):
                        processed_df[self.x_col] = pd.to_datetime(processed_df[self.x_col], utc=True, errors="coerce")
                        self.signals.log.emit(f"Converted column '{self.x_col}' to datetime format.")
            if self.y_cols:
                for y_col in self.y_cols:
                    if y_col and y_col in processed_df.columns:
                        if self._is_datetime_column(processed_df[y_col]):
                            if not pd.api.types.is_datetime64_any_dtype(processed_df[y_col]):
                                processed_df[y_col] = pd.to_datetime(processed_df[y_col], utc=True, errors="coerce")
                                self.signals.log.emit(f"Converted column '{y_col}' to datetime format.")
            self.signals.progress.emit(100, "Data preparation complete.")
            self.signals.finished.emit(processed_df)
        except Exception as e:
            self.signals.error.emit(e)

class SearchWorker(QThread):
    finished_search = pyqtSignal(object, int)
    
    def __init__(self, df, search_text, token, parent=None) -> None:
        super().__init__(parent)
        self.df = df
        self.search_text = search_text
        self.token = token
    
    def run(self) -> None:
        matches = []
        if self.df is None or self.df.empty or not self.search_text:
            self.finished_search.emit(matches, self.token)
            return
        
        search_text_lower = str(self.search_text).lower()
        try:
            for col_index, col_name in enumerate(self.df.columns):
                col_series_str = self.df[col_name].astype(str)
                mask = col_series_str.str.contains(search_text_lower, case=False, regex=False, na=False)
                
                matched_row_indices = np.where(mask)[0]

                for row_idx in matched_row_indices:
                    matches.append((int(row_idx), col_index))

            matches.sort(key=lambda x: (x[0], x[1]))
            self.finished_search.emit(matches, self.token)
                
        except Exception:
            self.finished_search.emit([], self.token)