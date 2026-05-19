import pandas as pd
import requests
from io import StringIO
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from duckdb import connect
from sqlalchemy import create_engine
from sqlalchemy.sql import text

from core.tempfilehandling.cleanup_temp_files import cleanup_temp_csv_files
from core.tempfilehandling.create_temp_file import create_temp_csv_file

try:
    import geopandas as gpd
except ImportError:
    gpd = None
    
class SupportedExtensions(str, Enum):
    EXCEL = ".xlsx"
    EXCEL_OLD = ".xls"
    CSV = ".csv"
    TXT = ".txt"
    JSON = ".json"
    GEOJSON = ".geojson"
    SHP = ".shp"
    GPKG = ".gpkg"
    SHX = ".shx"
    
class DataIOManager:
    """
    A manager that handles all file, Google Sheet, database import/export operations
    Also handles all file source information
    """
    
    def __init__(self) -> None:
        self.file_path: Optional[Path] = None
        self.temp_csv_path: Optional[Path] = None
        self.is_temp_file: bool = False
        
        # Google Sheets creds cache
        self.last_gsheet_id: Optional[str] = None
        self.last_gsheet_name: Optional[str] = None
        self.last_gsheet_delimiter: Optional[str] = None
        self.last_gsheet_decimal: Optional[str] = None
        self.last_gsheet_thousands: Optional[str] = None
        self.last_gsheet_gid: Optional[str] = None
        
        # Database credens cache
        self.last_db_connection_string: Optional[str] = None
        self.last_db_query: Optional[str] = None
    
    def _reset_import_state(self) -> None:
        """Resets the cached states for Google Sheets and databases"""
        self.last_gsheet_id = None
        self.last_gsheet_name = None
        self.last_gsheet_delimiter = None
        self.last_gsheet_decimal = None
        self.last_gsheet_thousands = None
        self.last_gsheet_id = None
        self.last_db_connection_string = None
        self.last_db_query = None
        
    # Two methods for manage temp-files
    def cleanup_temp_files(self) -> None:
        """Delete the current temporary CSV file, if it exists"""
        cleanup_temp_csv_files(self.temp_csv_path)
        self.temp_csv_path = None
        self.is_temp_file = False
    
    def _maybe_cleanup_temp_files_on_import(self) -> None:
        """Delete any existing temp file before a new import"""
        if self.is_temp_file:
            self.cleanup_temp_files()
    
    def _attempt_datetime_conversion(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Attempt to convert string/object columns to datetime automatically
        Uses a 100-row sample to detect date-like columns while avoiding false
        positives on pure num strings\n
        :param dataframe (pd.DataFrame): The DataFrame to process.
        :return pd.DataFrame: The DataFrame with converted datetime columns where applicable.
        """
        if dataframe is None or dataframe.empty:
            return dataframe
        
        object_columns = dataframe.select_dtypes(include=["object", "string"]).columns
        for col in object_columns:
            non_null_series = dataframe[col].dropna()
            if non_null_series.empty:
                continue
            sample = non_null_series.head(100)
            
            try:
                pd.to_numeric(sample, errors="raise")
                continue
            except (TypeError, ValueError):
                pass
            try:
                sampled_converted = pd.to_datetime(sample, errors="coerce")
                if sampled_converted.isna().any():
                    continue
                
                converted_series = pd.to_datetime(dataframe[col], errors="coerce")
                original_missing_count = dataframe[col].isna().sum()
                new_missing_count = converted_series.isna().sum()
                
                if original_missing_count == new_missing_count:
                    dataframe[col] = converted_series
            except (ValueError, TypeError, Exception):
                pass
        return dataframe
    
    def _read_local_file(self, path: Path) -> pd.DataFrame:
        """
        Internal method to parse a supported file into a DataFrame
        
        :param path: Path object pointing to the file
        :return pd.DataFrame: the parsed DataFrame.
        :raises ValueError: if the file extension is unsupported or rejected
        :raises ImportError: if spatial packages are missing
        """
        extension = path.suffix.lower()
        
        if extension in (SupportedExtensions.EXCEL.value, SupportedExtensions.EXCEL_OLD.value):
            return pd.read_excel(path)
        
        if extension == SupportedExtensions.CSV.value:
            return self._parse_delimited_file(path, is_tab_separated=False)
        
        if extension == SupportedExtensions.TXT.value:
            return self._parse_delimited_file(path, is_tab_separated=True)
        
        if extension == SupportedExtensions.JSON.value:
            return pd.read_json(path)
        
        if extension in (SupportedExtensions.GEOJSON.value, SupportedExtensions.SHP.value, SupportedExtensions.GPKG.value):
            if gpd is None:
                raise ImportError("Geopandas is not installed. Please install GeoPandas to load spatial data")
            return gpd.read_file(path)
        
        if extension == SupportedExtensions.SHX.value:
            raise ValueError("This is a shapefile index (.shx) file.\nPlease open the shapefile (.shp) instead")
        
        raise ValueError(f"Unsupported file format: {extension}")
    
    def _parse_delimited_file(self, path: Path, is_tab_separated: bool) -> pd.DataFrame:
        """
        Attempts to parse CSV/TXT files using DuckDB first, falling back to pandas if failed
        
        :param path: File path to load
        :param is_tab_separated: True if tab_separated, False if comma-separated
        :return pd.DataFrame: The parsed DataFrame
        """
        duckdb_query = "SELECT * FROM read_csv_auto(?, ignore_errors=true)"
        if is_tab_separated:
            duckdb_query = "SELECT * FROM read_csv_auto(?, delim='\t', ignore_errors=True)"
        
        try:
            with connect(database=":memory:", read_only=False) as con:
                arrow_table = con.execute(duckdb_query, [path.as_posix()]).arrow()
                return arrow_table.to_pandas(types_mapper=pd.ArrowDtype)
        except Exception:
            pass
        
        separator = "\t" if is_tab_separated else ","
        try:
            return pd.read_csv(path, sep=separator, engine="pyarrow", dtype_backend="pyarrow")
        except Exception:
            return pd.read_csv(path, sep=separator, engine="c", dtype_backend="pyarrow", on_bad_lines="skip")
    
    def read_file(self, filepath: str) -> pd.DataFrame:
        """
        Read a file and return a DataFrame without modifying its state
        
        :param filepath: Path to the file
        :return pd.DataFrame: The loaded read-only data
        """
        try:
            return self._read_local_file(Path(filepath))
        except Exception as error:
            raise Exception(f"Error reading file: {str(error)}")
    
    def import_file(self, filepath: str) -> pd.DataFrame:
        """
        Imports a file and updates the IO state
        
        :param filepath: Path to the file to import
        :return pd.DataFrame: The loaded and converted DataFrame object
        """
        self._maybe_cleanup_temp_files_on_import()
        path = Path(filepath)
        
        try:
            df = self._read_local_file(path)
            df = self._attempt_datetime_conversion(df)
            
            # Update source tracking
            self.file_path = path
            self.is_temp_file = False
            self._reset_import_state()
            
            return df
        except Exception as error:
            raise Exception(f"Error importing file: {str(error)}")
    
    def import_google_sheets(self, sheet_id: str, sheet_name: str, delimiter: str = ",", decimal: str = ".", thousands: Optional[str] = None, gid: Optional[str] = None) -> tuple[pd.DataFrame, Path]:
        """
        Imports data from a Google Sheet using either sheet_id/sheetName or GID from URL.
        
        :param sheet_id: A unique ID for the current sheet workbook.
        :param sheet_name: The target sheet name.
        :param delimiter: CSV delimiter used in the export URL.
        :param decimal: Decimal separator.
        :param thousands: Thousands separator.
        :param gid: Numeric sheet GID.
        :return Tuple[pd.DataFrame, Path]: the loaded DataFrame and path to the created temp CSV file.
        """
        self._maybe_cleanup_temp_files_on_import()
        
        if not sheet_id:
            raise ValueError("Sheet ID cannot be empty.")
        if not sheet_name and not gid:
            sheet_name = "Sheet1"
        
        sheet_id = sheet_id.strip()
        sheet_name = sheet_name.strip() if sheet_name else None
        gid = str(gid).strip() if gid else None
        
        self._reset_import_state
        self.last_gsheet_id = sheet_id
        self.last_gsheet_name = sheet_name
        self.last_gsheet_delimiter = delimiter
        self.last_gsheet_decimal = decimal
        self.last_gsheet_thousands = thousands
        self.last_gsheet_gid = gid
        
        base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq"
        params = {"tqx": "out:csv"}
        if gid:
            params["gid"] = gid
        elif sheet_name:
            params["sheet"] = sheet_name
            
        try:
            response: requests.Response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise Exception("Connection timeout: Google Sheets took too long to respond.\n\nTry again in a moment")
        except requests.exceptions.ConnectionError:
            raise Exception("Connection Error: Unable to connect to Google Sheets.\n\nCheck your internet connection")
        except requests.exceptions.HTTPError as error:
            self._handle_google_sheets_http_error(error)
        except Exception as error:
            raise Exception(f"Unexpected error during Google Sheets request:\n{str(error)}")
        
        if not response.text or len(response.text) <= 10:
            self._raise_empty_sheet_error(sheet_name, gid)
        
        try:
            df = pd.read_csv(
                StringIO(response.text),
                sep=delimiter,
                decimal=decimal,
                thousands=thousands,
                encoding="utf-8",
                on_bad_lines="error",
                engine="python"
            )
        except Exception as parse_error:
            raise ValueError(f"Google Sheets Parsing Failed: {str(parse_error)}")
        
        if df is None or df.empty:
            self._raise_empty_sheet_error(sheet_name, gid)
        
        df = self._attempt_datetime_conversion(df)
        
        name_slug = gid if gid else sheet_name
        safe_sheet_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(name_slug))
        temp_path = create_temp_csv_file(df, f"gsheet_{safe_sheet_name}")
        
        self.temp_csv_path = temp_path
        self.file_path = temp_path
        self.is_temp_file = True
        
        return df, temp_path
    
    def _handle_google_sheets_http_error(self, error: requests.exceptions.HTTPError) -> None:
        """Translates the HTTP errors"""
        if error.response is None:
            raise Exception(f"HTTP Error: {str(error)}")
        
        status = error.response.status_code
        if status == 404:
            raise Exception(
                "Sheet not found (404)\n\nPossible Causes:\n"
                "- Sheet ID is incorrect\n- Sheet has been deleted\n"
                "- Sheet is not publicaly accessible\n\n"
                "Double-check the Sheet ID and verify sharing settings"
            )
        if status == 403:
            raise Exception(
                "Permission Denied (403)\n\nThe Sheet is not publically accessible.\n\n"
                "To fix:\n1. Open the Google Sheet\n2. Click 'Share' (top-right)\n"
                "3. Select 'Anyone with the link'\n4. Choose 'Viewer' of higher\n"
                "5. Try importing again"
            )
        raise Exception(f"HTTP Error {status}: {str(error)}")
    
    def _raise_empty_sheet_error(self, sheet_name: Optional[str], gid: Optional[str]) -> None:
        """Raises an formatted error for empty or inaccessible sheets"""
        if sheet_name and not gid:
            message += f"\n\nNote: Please verify the sheet name '{sheet_name}' matches"
        raise ValueError(message)
        
    
    def import_from_database(self, connection_string: str, query: str, max_rows: int = 1000000) -> Tuple[pd.DataFrame, Path]:
        """
        Import data from a database using SQLAlchemy.
        
        :param connection_string: The SQLAlchemy connection url.
        :param query: SQL query to be executed.
        :param max_rows: Maximum allowed rows before truncating to prevent memory exhaustion.
        :return Tuple[pd.DataFrame, Path]: The loaded DataFrame and path to the created temp CSV.
        """
        self._maybe_cleanup_temp_files_on_import()
        
        if not connection_string or not query:
            raise ValueError("A connection string and a query are needed to import data from a database")
        
        self._reset_import_state()
        self.last_db_connection_string = connection_string
        self.last_db_query = query
        self.file_path = None
        self.is_temp_file = False
        
        chunks: List[pd.DataFrame] = []
        total_rows = 0
        chunk_size = 50000
        hit_limit = False
        
        try:
            engine = create_engine(connection_string)
            with engine.connect() as connection:
                for chunk in pd.read_sql_query(text(query), connection, chunksize=chunk_size):
                    chunks.append(chunk)
                    total_rows += len(chunk)
                    
                    if total_rows >= max_rows:
                        hit_limit = True
                        break
        except ImportError:
            raise Exception(
                "SQLAlchemy or database driver not installed.\n"
                "Please install 'sqlalchemy and appropriate drivers (e.g., 'psycopg2-binary')'"
            )
        except Exception as error:
            self._reset_import_state()
            raise Exception(f"Database import filed:\n{str(error)}")
        
        if not chunks:
            raise ValueError("Query returned no data.")
        
        df = pd.concat(chunks, ignore_index=True)
        
        if hit_limit:
            print(f"Warning: Query truncated at {max_rows} rows to prevent memory exhaustion")
            
        df = self._attempt_datetime_conversion(df)
        
        temp_path = create_temp_csv_file(df, "db_import")
        self.temp_csv_path = temp_path
        self.file_path = temp_path
        self.is_temp_file = True
        
        return df, temp_path
    
    def export_data(self, df: pd.DataFrame, filepath: str, format: str = "csv", include_index: bool = False) -> None:
        """
        Export a dataframe to a local file
        :param df (pd.DataFrame): The DataFrame to export
        :param filepath (str): Destination path
        :param format (str): The file format of the file
        :param include_index (bool): Whether to write the row index
        """
        if df is None:
            raise ValueError("No data loaded")
        try:
            if format == "csv":
                df.to_csv(filepath, index=include_index)
            elif format == "xlsx":
                df.to_excel(filepath, index=include_index)
            elif format == "json":
                if include_index:
                    df.to_json(filepath, orient="columns", indent=4)
                else:
                    df.to_json(filepath, orient="records", indent=4)
        except Exception as ExportDataError:
            raise Exception(f"Error exporting data: {str(ExportDataError)}")
    
    def export_google_sheets(self, df: pd.DataFrame, credentials_path: str, sheet_id: str, sheet_name: str = "Sheet1") -> bool:
        """
        Export a DataFrame to a Google Sheet using a service-account file\n
        :param df (pd.DataFrame): The Dataframe to export
        :param credentials_path (str): Path to the service-account JSON key
        :param sheet_id (str): Target Google Sheet ID
        :param sheet_name (str): Target worksheet name
        :return bool: True on success
        """
        if df is None:
            raise ValueError("No data loaded to export.")

        try:
            import gspread
            from gspread.auth import service_account

            api_scopes: List[str] = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]

            client = service_account(filename=credentials_path, scopes=api_scopes)
            spreadsheet = client.open_by_key(sheet_id)

            try:
                worksheet = spreadsheet.worksheet(sheet_name)
            except gspread.exceptions.WorksheetNotFound:
                required_rows: int = len(df) + 100
                required_cols: int = len(df.columns) + 10
                worksheet = spreadsheet.add_worksheet(
                    title=sheet_name, rows=required_rows, cols=required_cols
                )

            sanitized_df: pd.DataFrame = df.fillna("")
            export_payload: List[List[Any]] = (
                [sanitized_df.columns.values.tolist()] + sanitized_df.values.tolist()
            )

            worksheet.clear()
            worksheet.update(values=export_payload, range_name="A1")
            return True

        except ImportError:
            raise ImportError(
                "The gspread library is required to export to Google Sheets.\n"
                "Please install it first."
            )
        except Exception as ExportError:
            error_message: str = str(ExportError).replace(
                str(credentials_path), "[REDACTED_CREDENTIALS_PATH]"
            )
            raise Exception(f"Failed to export data to Google Sheets:\n{error_message}")
    
    def has_google_sheet_import(self) -> bool:
        """Return True if the last import was from Google Sheets"""
        return self.last_gsheet_id is not None and self.last_gsheet_name is not None
    
    def is_google_sheet_import(self) -> bool:
        """Return True if a Google Sheet refresh is possible"""
        return bool(self.last_gsheet_id and (self.last_gsheet_name or self.last_gsheet_gid))
    
    def get_data_source_info(self) -> Dict[str, Any]:
        """Returns a snapshot of the current import-source"""
        return {
            "file_path": str(self.file_path) if self.file_path else None,
            "is_temp_file": self.is_temp_file,
            "temp_csv_path": str(self.temp_csv_path) if self.temp_csv_path else None,
            "last_db_connection_string": self.last_db_connection_string,
            "last_db_query": self.last_db_query,
        }
    
    def get_google_sheets_refresh_params(self) -> Dict[str, Any]:
        """Returns the cached Google Sheets params needed for refreshing data"""
        return {
            "sheet_id": self.last_gsheet_id,
            "sheet_name": self.last_gsheet_name,
            "delimiter": self.last_gsheet_delimiter,
            "decimal": self.last_gsheet_decimal,
            "thousands": self.last_gsheet_thousands,
            "gid": self.last_gsheet_gid,
        }