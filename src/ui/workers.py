import logging
import socket
import time
from typing import Any, TYPE_CHECKING, TypedDict

import numpy as np
import pandas as pd
from PyQt6.QtCore import QObject, QRunnable, QThread, pyqtSignal, pyqtSlot
from sqlalchemy import Engine, Inspector, create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from icons import IconType
from src.core.data_handler import DataHandler
from src.core.project_file_info import ProjectFileMetadata, gather_project_file_metadata

if TYPE_CHECKING:
    from src.core.project_manager import ProjectManager
    from src.core.subset_manager import SubsetManager

logger: logging.Logger = logging.getLogger(__name__)

class AutosaveWorker(QRunnable):
    """
    Worker thread for background project autosaves

    Executes the ProjectManager.auto_save operation async to prevent
    block of main GUI thread.
    This is mainly for large datasets, but will execute on all saves.
    """

    def __init__(self, project_manager: "ProjectManager", project_data: dict[str, Any]) -> None:
        super().__init__()
        self.project_manager = project_manager
        self.project_data = project_data
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            self.project_manager.auto_save(self.project_data)
            self.signals.finished.emit(None)
        except Exception as err:
            self.signals.error.emit(err)

class WorkerSignals(QObject):
    """
    Defines the signal from a running worker thread
    signals are:

    finished
        object: data (pd.DataFrame)
    success
        object: data (pd.DataFrame), str: filepath
    error
        Exception: The exception object
    error_object
        object: the error as an object and not Exception
    log
        str: A message to log
    """
    finished = pyqtSignal(object)
    success = pyqtSignal(object, str)
    error = pyqtSignal(Exception)
    error_object = pyqtSignal(object)
    log = pyqtSignal(str)
    progress = pyqtSignal(int, str)

class FileReaderWorker(QRunnable):
    """
    Worker thread to handle synchronous file reading
    """

    def __init__(self, data_handler: DataHandler, file_path: str) -> None:
        super().__init__()
        self.data_handler = data_handler
        self.file_path = file_path
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            df = self.data_handler.read_file(self.file_path)
            self.signals.success.emit(df, self.file_path)
        except Exception as err:
            self.signals.error_object.emit(err)

class AggregationWorker(QRunnable):
    """Worker for performing data aggregation"""

    def __init__(self, data_handler: DataHandler, group_by: list[str], agg_config: dict[str, str],
                 date_grouping: dict[str, str], rename_mapping: dict[str, str] | None = None) -> None:
        super().__init__()
        self.data_handler = data_handler
        self.group_by = group_by
        self.agg_config = agg_config
        self.date_grouping = date_grouping
        self.rename_mapping = rename_mapping
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            self.signals.progress.emit(10, "Preparing Aggregation...")
            self.signals.log.emit(f"Starting background aggregation task with {len(self.group_by)} groups...")
            result_df = self.data_handler.aggregate_data(group_by=self.group_by, agg_config=self.agg_config,
                                                         date_grouping=self.date_grouping,
                                                         rename_mapping=self.rename_mapping)

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

    def __init__(self, data_handler: DataHandler, sheet_id: str, sheet_name: str, delimiter: str, decimal: str,
                 thousands: str, gid: str = None):
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

    def __init__(self, connection_string: str) -> None:
        super().__init__()
        self.connection_string: str = connection_string
        self.signals: WorkerSignals = WorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        engine: Engine | None = None
        try:
            self.signals.progress.emit(10, "Connecting...")
            engine = create_engine(self.connection_string)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            self.signals.progress.emit(100, "Connection Successful")
            self.signals.finished.emit(True)
        except (SQLAlchemyError, ValueError, OSError, RuntimeError) as conn_err:
            self.signals.error.emit(conn_err)
        finally:
            if engine is not None:
                engine.dispose()

SYSTEM_SCHEMA_NAMES: frozenset[str] = frozenset({
    "information_schema",
    "pg_catalog",
    "pg_toast",
    "mysql",
    "performance_schema",
    "sys",
    "temp"
})
SYSTEM_SCHEMA_PREFIXES: tuple[str, ...] = ("pg_toast", "pg_temp_")
MULTI_SCHEMA_DIALECTS: frozenset[str] = frozenset({"postgresql", "duckdb"})

class SchemaTableGroup(TypedDict):
    schema: str | None
    tables: list[str]

class ColumnMetadata(TypedDict):
    name: str
    type: str

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

    @staticmethod
    def is_user_schema(schema_name: str) -> bool:
        lowered: str = schema_name.lower()
        if lowered in SYSTEM_SCHEMA_NAMES:
            return False
        return not lowered.startswith(SYSTEM_SCHEMA_PREFIXES)

    @staticmethod
    def _sort_schemas(schemas: list[str]) -> list[str]:
        priority: dict[str, int] = {"public": 0, "main": 1}
        return sorted(schemas, key=lambda name: (priority.get(name.lower(), 2), name.lower()))

    def _collect_multi_schema_tables(self, inspector: Inspector) -> list[SchemaTableGroup]:
        raw_schemas: list[str] = inspector.get_schema_names()
        user_schemas: list[str] = self._sort_schemas(
            [name for name in raw_schemas if self.is_user_schema(name)]
        )
        schema_groups: list[SchemaTableGroup] = []

        for schema_name in user_schemas:
            try:
                tables: list[str] = sorted(inspector.get_table_names(schema=schema_name))
                schema_groups.append({"schema": schema_name, "tables": tables})
            except SQLAlchemyError as err:
                logger.warning("Skipping inaccessible schema '%s': %s", schema_name, err)

        return schema_groups

    def run(self) -> None:
        engine: Engine | None = None
        try:
            engine = create_engine(self.connection_string)
            inspector: Inspector = inspect(engine)

            if engine.dialect.name in MULTI_SCHEMA_DIALECTS:
                schema_groups: list[SchemaTableGroup] = self._collect_multi_schema_tables(inspector)
            else:
                tables: list[str] = sorted(inspector.get_table_names())
                schema_groups = [{"schema": None, "tables": tables}]

            self.signals.finished.emit(schema_groups)
        except (SQLAlchemyError, ValueError, OSError, RuntimeError) as err:
            self.signals.error.emit(str(err))
        finally:
            if engine is not None:
                engine.dispose()

class FetchColumnWorkerSignals(QObject):
    """Signals emitted by FetchColumnWorker during loading"""
    columnsLoaded = pyqtSignal(str, str, list)
    loadFailed = pyqtSignal(str, str, str)

class FetchColumnWorker(QRunnable):
    """
    Worker thread to fetch column metadata for a single table on demand
    """

    def __init__(self, connection_string: str, table_name: str, schema_name: str | None) -> None:
        super().__init__()
        self.connection_string: str = connection_string
        self.table_name: str = table_name
        self.schema_name: str | None = schema_name
        self.signals: FetchColumnWorkerSignals = FetchColumnWorkerSignals()

    def _inspect_sqlite_pragma(self, engine: Engine) -> list[ColumnMetadata]:
        escaped_table: str = self.table_name.replace('"', '""')
        with engine.connect() as conn:
            result = conn.execute(text(f'PRAGMA table_info("{escaped_table}")'))
            return [{"name": str(row[1]), "type": str(row[2])} for row in result]

    @pyqtSlot()
    def run(self) -> None:
        engine: Engine | None = None
        schema_key: str = self.schema_name or ""
        try:
            engine = create_engine(self.connection_string)
            inspector: Inspector = inspect(engine)
            columns: list[ColumnMetadata] = []

            try:
                raw_columns = inspector.get_columns(self.table_name, schema=self.schema_name)
                columns = [
                    {"name": str(col.get("name", "Unknown")), "type": str(col.get("type", "Unknown"))}
                    for col in raw_columns
                ]
            except SQLAlchemyError as inspect_err:
                if engine.dialect.name != "sqlite":
                    raise
                logger.warning(
                    "SQLAlchemy reflection failed for '%s', using PRAGMA fallback: %s",
                    self.table_name, inspect_err)
                columns = self._inspect_sqlite_pragma(engine)

            self.signals.columnsLoaded.emit(schema_key, self.table_name, columns)
        except (SQLAlchemyError, ValueError, OSError, RuntimeError) as err:
            logger.error("Failed to fetch columns for '%s.%s': %s", schema_key, self.table_name, err)
            self.signals.loadFailed.emit(schema_key, self.table_name, str(err))
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
                self.signals.progress.emit(progress, f"Applying subset {i + 1} of {total}: {name}...")

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

            sample_vals = data.dropna().head(3)
            if sample_vals.empty:
                return False
            for val in sample_vals:
                if not isinstance(val, str):
                    return False
                if val.replace(".", "", 1).isdigit():
                    return False
                try:
                    pd.to_datetime(val, utc=True)
                except (ValueError, TypeError):
                    return False
            return True
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
            PLOTS_TO_SAMPLE = ["Scatter", "Line", "2D Density", "Hexbin", "Stem", "Stairs", "Eventplot", "ECDF",
                               "2D Histogram", "Tricontour", "Tricontourf", "Tripcolor", "Triplot"]

            if len(processed_df) > MAX_PLOT_POINTS and self.plot_type in PLOTS_TO_SAMPLE:
                self.signals.log.emit(
                    f"Dataset is too large ({len(processed_df)} rows) for '{self.plot_type}'. Plotting a random sample of {MAX_PLOT_POINTS:,} points.")
                processed_df = processed_df.sample(n=MAX_PLOT_POINTS, random_state=42).sort_index()

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

class ProjectMetadataWorkerSignals(QObject):
    # Gives the file_path, ProjectFileMetadata
    finished = pyqtSignal(str, object)

class ProjectMetadataWorker(QRunnable):
    """
    Worker thread to gather recent project preview metadata
    """

    def __init__(self, file_path: str) -> None:
        super().__init__()
        self.file_path = file_path
        self.signals = ProjectMetadataWorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            metadata: ProjectFileMetadata = gather_project_file_metadata(self.file_path)
        except Exception as MetadataError:
            metadata = ProjectFileMetadata(size_bytes=0, modified_timestamp=0.0, error=str(MetadataError))
        self.signals.finished.emit(self.file_path, metadata)

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
            for col_index in range(self.df.shape[1]):
                col_series = self.df.iloc[:, col_index]

                if pd.api.types.is_object_dtype(col_series) or pd.api.types.is_string_dtype(col_series):
                    mask = col_series.str.contains(search_text_lower, case=False, regex=False, na=False)
                else:
                    mask = col_series.astype(str).str.contains(search_text_lower, case=False, regex=False, na=False)

                matched_row_indices = np.where(mask)[0]
                for row_idx in matched_row_indices:
                    matches.append((int(row_idx), col_index))

            matches.sort(key=lambda x: (x[0], x[1]))
            self.finished_search.emit(matches, self.token)
        except Exception:
            self.finished_search.emit([], self.token)

class InternetConnectionCheckSignals(QObject):
    finished = pyqtSignal(object)

class InternetConnectionCheckWorker(QRunnable):
    """Worker thread to check internet connection status"""

    def __init__(self) -> None:
        super().__init__()
        self.signals = InternetConnectionCheckSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            start_time = time.time()
            socket.create_connection(("8.8.8.8", 53), timeout=1.5)
            latency = time.time() - start_time
            if latency < 0.05:
                status = IconType.InternetHigh
            elif latency < 0.15:
                status = IconType.InternetMedium
            elif latency < 0.5:
                status = IconType.InternetLow
            else:
                status = IconType.InternetProblem
        except OSError:
            status = IconType.InternetOff
        self.signals.finished.emit(status)
