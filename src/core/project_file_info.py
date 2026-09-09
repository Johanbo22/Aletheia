"""
A read only inspection of .ath project files

These functions are to gather the metadata at runtime before ProjectManager.load_project takes over.
"""

import io
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pyarrow.parquet as pq

@dataclass(frozen=True)
class ProjectFileMetadata:
    """A shapshot of the disk info of a .ath project file"""
    size_bytes: int
    modified_timestamp: float
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    error: Optional[str] = None

def _count_pandas_index_columns(schema_metadata: Optional[dict]) -> int:
    """
    Counts how many of a parquet file's columns are a saved pandas index.

    RangeIndex is described as a dict not stored as column. A named index is stored
    and is counted towards total column count

    :param schema_metadata: The raw metadata attached to the parquet schema of the dataframe
    :return: The number of columns that hold index data
    """
    if not schema_metadata:
        return 0

    pandas_metadata_raw = schema_metadata.get(b"pandas")
    if not pandas_metadata_raw:
        return 0

    try:
        pandas_metadata = json.loads(pandas_metadata_raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return 0

    index_columns = pandas_metadata.get("index_columns", [])
    return sum(1 for entry in index_columns if isinstance(entry, str))

def _read_shape_from_package(filepath_obj: Path) -> tuple[Optional[int], Optional[int]]:
    """
    Reads parquet footer of packaged data to recover the rows and column counts without loading the dataframe

    :param filepath_obj: Path to the .ath project package
    :return: A (row_count, column_count) tuple, values are None if unavailable
    """
    with zipfile.ZipFile(filepath_obj, "r") as zip_package:
        if "data.parquet" not in zip_package.namelist():
            return None, None

        buffer = io.BytesIO(zip_package.read("data.parquet"))
        parquet_file = pq.ParquetFile(buffer)

        index_column_count = _count_pandas_index_columns(parquet_file.schema_arrow.metadata)
        column_count = max(parquet_file.metadata.num_columns - index_column_count, 0)
        return parquet_file.metadata.num_rows, column_count

def gather_project_file_metadata(filepath: str) -> ProjectFileMetadata:
    """
    Collects on disk size and timestamps and also data shape for the project file

    :param filepath: Path to the .ath project package
    :return: ProjectFileMetadata with error if reading fails
    """
    filepath_obj = Path(filepath)
    stat_result = filepath_obj.stat()

    try:
        row_count, column_count = _read_shape_from_package(filepath_obj)
        return ProjectFileMetadata(
            size_bytes=stat_result.st_size,
            modified_timestamp=stat_result.st_mtime,
            row_count=row_count,
            column_count=column_count
        )
    except Exception as ReadShapeError:
        return ProjectFileMetadata(
            size_bytes=stat_result.st_size,
            modified_timestamp=stat_result.st_mtime,
            error=str(ReadShapeError)
        )

def format_file_size(size_bytes: int) -> str:
    """Re formats the byt count into a string"""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024

    return f"{size:.1f} {unit}"

def format_saved_timestamp(timestamp: float) -> str:
    """Re formats a POSIX_timestamp into a datesime string"""
    try:
        return datetime.fromtimestamp(timestamp).strftime("%b %d, %Y at %I:%M %p")
    except (OverflowError, OSError, ValueError):
        return "Unknown"
