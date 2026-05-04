import pandas as pd
import requests
from io import StringIO
from pathlib import Path
from typing import Optional, Dict, Any, List

from duckdb import connect
from sqlalchemy import create_engine
from sqlalchemy.sql import text

from core.tempfilehandling.cleanup_temp_files import cleanup_temp_csv_files
from core.tempfilehandling.create_temp_file import create_temp_csv_file

try:
    import geopandas as gpd
except ImportError:
    gpd = None
    
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
    
    def read_file(self, filepath: str) -> pd.DataFrame:
        """
        Read a file and return a DataFrame without modifying its state\n
        :param filepath (str): Path to the file
        :return pd.DataFrame: The loaded data
        """
        path = Path(filepath)
        extension = path.suffix.lower()
        
        try:
            if extension in [".xlsx", ".xls"]:
                return pd.read_excel(filepath)
            elif extension == ".csv":
                con = connect()
                try:
                    arrow_table = con.execute(
                        "SELECT * FROM read_csv_auto(?, ignore_errors=true)",
                        [path.as_posix()],
                    ).arrow()
                    return arrow_table.to_pandas(types_mapper=pd.ArrowDtype)
                except Exception as DuckDBError:
                    try:
                        return pd.read_csv(filepath, engine="pyarrow", dtype_backend="pyarrow")
                    except Exception as PyArrowError:
                        return pd.read_csv(
                            filepath, engine="c", dtype_backend="pyarrow", on_bad_lines="skip"
                        )
                finally:
                    con.close()
            elif extension == ".txt":
                con = connect()
                try:
                    arrow_table = con.execute(
                        "SELECT * FROM read_csv_auto(?, delim='\\t', ignore_errors=true)",
                        [path.as_posix()],
                    ).arrow()
                    return arrow_table.to_pandas(types_mapper=pd.ArrowDtype)
                except Exception as DuckDBError:
                    try:
                        return pd.read_csv(filepath, sep="\t", engine="pyarrow", dtype_backend="pyarrow")
                    except Exception as PyArrowError:
                        return pd.read_csv(
                            filepath, sep="\t", engine="c", dtype_backend="pyarrow", on_bad_lines="skip"
                        )
                finally:
                    con.close()
            elif extension == ".json":
                return pd.read_json(filepath)
            elif extension in [".geojson", ".shp", ".gpkg"]:
                if gpd is None:
                    raise ImportError(
                        "GeoPandas is not installed. Please install GeoPandas to load spatial data"
                    )
                return gpd.read_file(filepath)
            elif extension == ".shx":
                raise ValueError(
                    "This is a shapefile index (.shx) file.\n"
                    "Please open the shapefile (.shp) instead"
                )
            else:
                raise ValueError(f"Unsupported file format: {extension}")
        except Exception as ReadFileError:
            raise Exception(f"Error reading file: {str(ReadFileError)}")
        
    def import_file(self, filepath: str) -> pd.DataFrame:
        """
        Imports a file\n
        :param filepath (str): Path to file to import
        :return pd.DataFrame: the loaded and converted dataframe
        """
        self._maybe_cleanup_temp_files_on_import()
        
        path = Path(filepath)
        extension = path.suffix.lower()
        try:
            if extension in [".xlsx", ".xls"]:
                df = pd.read_excel(filepath)
            elif extension == ".csv":
                con = connect(database=":memory:", read_only=False)
                try:
                    arrow_table = con.execute(
                        "SELECT * FROM read_csv_auto(?, ignore_errors=true)",
                        [path.as_posix()],
                    ).arrow()
                    df = arrow_table.to_pandas(types_mapper=pd.ArrowDtype)
                except Exception as ImportFileError:
                    try:
                        df = pd.read_csv(filepath, engine="pyarrow", dtype_backend="pyarrow")
                    except Exception as PyArrowError:
                        df = pd.read_csv(
                            filepath, engine="c", dtype_backend="pyarrow", on_bad_lines="skip"
                        )
                finally:
                    con.close()
            elif extension == ".txt":
                con = connect(database=":memory:", read_only=False)
                try:
                    arrow_table = con.execute(
                        "SELECT * FROM read_csv_auto(?, delim='\t', ignore_errors=true)",
                        [path.as_posix()],
                    ).arrow()
                    df = arrow_table.to_pandas(types_mapper=pd.ArrowDtype)
                except Exception as ImportFileError:
                    try:
                        df = pd.read_csv(filepath, sep="\t", engine="pyarrow", dtype_backend="pyarrow")
                    except Exception as PyArrowError:
                        df = pd.read_csv(
                            filepath, sep="\t", engine="c", dtype_backend="pyarrow", on_bad_lines="skip"
                        )
                finally:
                    con.close()
            elif extension == ".json":
                df = pd.read_json(filepath)
            elif extension in [".geojson", ".shp", ".gpkg"]:
                if gpd is None:
                    raise ImportError(
                        "GeoPandas is not installed. Please install GeoPandas to load spatial data"
                    )
                df = gpd.read_file(filepath)
            elif extension == ".shx":
                raise ValueError(
                    "This is a shapefile index (.shx) file.\n"
                    "Please open the shapefile (.shp) file instead."
                )
            else:
                raise ValueError(f"Unsupported file format: {extension}")
            
            df = self._attempt_datetime_conversion(df)
            # Update source tracking
            self.file_path = path
            self.is_temp_file = False
            self.last_gsheet_id = None
            self.last_gsheet_name = None
            self.last_gsheet_delimiter = None
            self.last_gsheet_decimal = None
            self.last_gsheet_thousands = None
            self.last_gsheet_gid = None
            self.last_db_connection_string = None
            self.last_db_query = None
            return df
        except Exception as ImportFileError:
            raise Exception(f"Error importing file: {str(ImportFileError)}")
    
    def import_google_sheets(self, sheet_id: str, sheet_name: str, delimiter: str = ",", decimal: str = ".", thousands: str = None, gid: str = None) -> tuple[pd.DataFrame, Path]:
        """
        Imports data from a Google Sheet using either sheet_id/sheetName or GID from URL\n
        :param sheet_id (str): A unique ID for the current sheet workbook
        :param sheet_name (str): The target sheet name
        :param delimiter (str): CSV delimiter used in the export URL
        :param decimal (str): Decimal separator
        :param thousands (str): Thousands separator
        :param gid (str): Numeric sheet GID
        :return tuple[pd.DataFrame, Path]: the loaded DataFrame and path to the created temp CSV file
        """
        self._maybe_cleanup_temp_files_on_import()
        try:
            if not sheet_id:
                raise ValueError("Sheet ID cannot be empty")
            if not sheet_name and not gid:
                sheet_name = "Sheet1"

            sheet_id = sheet_id.strip()
            if sheet_name:
                sheet_name = sheet_name.strip()
            if gid:
                gid = str(gid).strip()

            # Cache credentials
            self.last_gsheet_id = sheet_id
            self.last_gsheet_name = sheet_name
            self.last_gsheet_delimiter = delimiter
            self.last_gsheet_decimal = decimal
            self.last_gsheet_thousands = thousands
            self.last_gsheet_gid = gid
            self.last_db_connection_string = None
            self.last_db_query = None

            base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq"
            params = {"tqx": "out:csv"}
            if gid:
                params["gid"] = gid
            else:
                params["sheet"] = sheet_name
                
            df = None
            last_error = None
            try:
                response: requests.Response = requests.get(base_url, params=params, timeout=10)
                response.raise_for_status()
                if response.text and len(response.text) > 10:
                    df = pd.read_csv(
                        StringIO(response.text),
                        sep=delimiter,
                        decimal=decimal,
                        thousands=thousands,
                        encoding="utf-8",
                        on_bad_lines="error",
                        engine="python",
                    )
            except Exception as GoogleSheetsImportError:
                last_error = GoogleSheetsImportError
            if df is None or len(df) == 0:
                if last_error:
                    raise ValueError(f"Google Sheet Import Failed: {str(last_error)}")
                message = "The sheet appears to be empty or inaccessible"
                if sheet_name and not gid:
                    message += f"\n\nNote: Please verify the sheet name '{sheet_name}' matches exactly"
                raise ValueError(message)
            df = self._attempt_datetime_conversion(df)
            # Create a temp CSV so saving/export logic works uniformly
            name_slug = gid if gid else sheet_name
            safe_sheet_name = "".join(
                c if c.isalnum() or c in ("-", "_") else "_" for c in str(name_slug)
            )
            temp_path = create_temp_csv_file(df, f"gsheet_{safe_sheet_name}")
            self.temp_csv_path = temp_path
            self.file_path = temp_path
            self.is_temp_file = True
            return df, temp_path
        except requests.exceptions.Timeout:
            raise Exception(
                "Connection timeout: Google Sheets took too long to respond.\n\n"
                "Try again in a moment or check your internet connection."
            )
        except requests.exceptions.ConnectionError:
            raise Exception(
                "Connection error: Unable to connect to Google Sheets.\n\n"
                "Check your internet connection."
            )
        except requests.exceptions.HTTPError as GoogleSheetsHTTPError:
            if GoogleSheetsHTTPError.response.status_code == 404:
                raise Exception(
                    "Sheet not found (404)\n\nPossible causes:\n"
                    "• Sheet ID is incorrect\n• Sheet has been deleted\n"
                    "• Sheet is not publicly accessible\n\n"
                    "Double-check the Sheet ID and verify sharing settings."
                )
            elif GoogleSheetsHTTPError.response.status_code == 403:
                raise Exception(
                    "Permission denied (403)\n\nThe sheet is not publicly accessible.\n\n"
                    "To fix:\n1. Open the Google Sheet\n2. Click 'Share' (top right)\n"
                    "3. Select 'Anyone with the link'\n4. Choose 'Viewer' or higher\n"
                    "5. Try importing again"
                )
            else:
                raise Exception(
                    f"HTTP Error {GoogleSheetsHTTPError.response.status_code}: "
                    f"{str(GoogleSheetsHTTPError)}"
                )
        except ValueError as InvalidInputError:
            raise Exception(f"Invalid input or empty sheet:\n{str(InvalidInputError)}")
        except Exception as ImportGoogleSheetsError:
            error_msg = str(ImportGoogleSheetsError)
            raise Exception(
                f"Error importing Google Sheet:\n{error_msg}\n\n"
                f"Verification checklist:\n- Sheet ID is correct\n"
                f"- Sheet name matches exactly (case-sensitive)\n"
                f"- Sheet is shared publicly\n- Internet connection is active\n"
                f"- Try with Sheet1 first"
            )
    
    def import_from_database(self, connection_string: str, query: str, max_rows: int = 1000000) -> tuple[pd.DataFrame, Path]:
        """
        Import data from a database using SQLAlchemy\n
        :param connection_string (str): The SQLAlchemy connection url
        :param query (str): SQL query to be executed
        :return tuple[pd.DataFrame, Path]: The loaded DataFrame and path to the created temp CSV
        """
        self._maybe_cleanup_temp_files_on_import()

        try:
            if not connection_string or not query:
                raise ValueError(
                    "A connection string and a query are needed to import from a database."
                )

            self.last_db_connection_string = connection_string
            self.last_db_query = query
            self.last_gsheet_id = None
            self.last_gsheet_name = None
            self.file_path = None
            self.is_temp_file = False
            
            chunks = []
            total_rows = 0
            chunk_size = 50000
            hit_limit = False

            engine = create_engine(connection_string)
            with engine.connect() as connection:
                for chunk in pd.read_sql_query(text(query), connection, chunksize=chunk_size):
                    chunks.append(chunk)
                    total_rows += len(chunk)
                    
                    if total_rows >= max_rows:
                        hit_limit = True
                        break
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

        except ImportError:
            raise Exception(
                "SQLAlchemy or database driver is not installed.\n"
                "Please install 'sqlalchemy' and appropriate drivers (e.g., 'psycopg2-binary')."
            )
        except Exception as ImportDatabaseError:
            self.last_db_connection_string = None
            self.last_db_query = None
            raise Exception(f"Database import failed:\n{str(ImportDatabaseError)}")
    
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