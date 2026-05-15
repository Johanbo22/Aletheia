# core/project_manager.py
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
from resources.version import APPLICATION_VERSION, PROJECT_EXTENSION, DATA_EXTENSION
import zipfile
import json
import sqlite3
import tempfile
import io

class ProjectManager:
    
    PROJECT_EXTENSION = PROJECT_EXTENSION
    DATA_EXTENSION = DATA_EXTENSION
    APPLICATION_VERSION = APPLICATION_VERSION
    
    def __init__(self) -> None:
        self.current_project_path: Optional[Path] = None
        self.project_data: Dict[str, Any] = {}
        
        # Workspace and autosave configurations
        self.autosave_dir: Path = Path.home() / ".dataplotstudio"
        self.autosave_dir.mkdir(parents=True, exist_ok=True)
        self.autosave_path: Path = self.autosave_dir / "DataPlotStudioAutosave.dps"
    
    def new_project(self) -> None:
        
        self.current_project_path = None
        self.project_data = {
            "metadata": {
                "version": self.APPLICATION_VERSION,
                "name": "Untitled Project"
            },
            "data": None,
            "plot_config": {},
            "operations": []
        }
    
    def save_project(self, project_data: Dict[str, Any], filepath: str) -> str:
        
        if not filepath:
            raise ValueError("A valid filepath must be provided to save the project")
        
        filepath_obj = Path(filepath)
        if not filepath_obj.suffix == self.PROJECT_EXTENSION:
            filepath_obj = filepath_obj.with_suffix(self.PROJECT_EXTENSION)
        try:
            self._create_dps_package(project_data, filepath_obj)
            self.current_project_path = filepath_obj
            return str(filepath_obj)
        except Exception as SaveProjectError:
            raise RuntimeError(f"Error packing project files: {str(SaveProjectError)}") from SaveProjectError
    
    def _create_dps_package(self, project_data: Dict[str, Any], filepath_obj: Path) -> None:
        """
        Serializes and archives project data, configurations and metadata into a .dps zip package

        :param project_data: The active dict of the project to be serialized
        :param filepath_obj: Destination file path for the package
        """
        save_data: Dict[str, Any] = project_data.copy()
        dataframe: Optional[pd.DataFrame] = save_data.pop("data", None) if isinstance(save_data.get("data"), pd.DataFrame) else None
        
        with zipfile.ZipFile(filepath_obj, "w", zipfile.ZIP_DEFLATED) as zip_package:
            
            # Extract raw data using parquet
            if dataframe is not None:
                parquet_buffer = io.BytesIO()
                dataframe.to_parquet(parquet_buffer, engine="pyarrow", index=True)
                zip_package.writestr("data.parquet",parquet_buffer.getvalue())
            
            # archive plotting configs which are .json files
            plot_config_data: str = json.dumps(save_data.get("plot_config", {}))
            zip_package.writestr("plot_config.json", plot_config_data)
            
            # archive operation logs as json files
            operations_log_data: str = json.dumps(save_data.get("operations", []))
            zip_package.writestr("operations_log.json", operations_log_data)
            
            # create the metadata file as a SQLITE database
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
                db_path: Path = Path(temp_db.name)
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE session_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """)
                metadata: Dict[str, Any] = save_data.get("metadata", {})
                for key, value in metadata.items():
                    key_str: str = str(key)
                    if "credential" in key_str.lower() or "token" in key_str.lower():
                        value = "[REDACTED]"
                    cursor.execute("INSERT INTO session_metadata (key, value) VALUES (?, ?)", (key_str, str(value)))
                conn.commit()
                conn.close()

                zip_package.write(db_path, arcname="session.db")
            finally:
                db_path.unlink(missing_ok=True)
    
    def auto_save(self, project_data: Dict[str, Any]) -> None:
        """
        Serializes the current state of the autosave file
        to prevent data loss
        """
        temp_autosave_path: Path = self.autosave_path.with_suffix(".dps.tmp")
        try:
            self._create_dps_package(project_data, temp_autosave_path)
            temp_autosave_path.replace(self.autosave_path)
        except Exception:
            if temp_autosave_path.exists():
                try:
                    temp_autosave_path.unlink()
                except OSError:
                    pass
    
    def has_autosave(self) -> bool:
        return self.autosave_path.exists() and self.autosave_path.is_file()

    def recover_autosave(self) -> Dict[str, Any]:
        try:
            return self.load_project(str(self.autosave_path))
        except Exception as RecoveryError:
            self.cleanup_autosave()
            raise RuntimeError(f"Auto-save file is corrupted and has been deleted: {RecoveryError}") from RecoveryError

    def cleanup_autosave(self) -> None:
        """
        Removes the autosave file upon normal
        application exit or discarding project
        """
        try:
            if self.has_autosave():
                self.autosave_path.unlink()
        except OSError:
            pass
        
    def _load_dataframe(self, parquet_buffer: io.BytesIO) -> pd.DataFrame:
        """
        Attempts to load a parquet buffer into a GeoDataFrame,
        falling back to standard Pandas DataFrame

        :param parquet_buffer: The in-memory byte buffer of the parquet file
        :return: The parsed DataFrame
        """
        try:
            import geopandas as gpd
            try:
                return gpd.read_parquet(parquet_buffer)
            except ValueError:
                parquet_buffer.seek(0)
        except ImportError:
            pass

        return pd.read_parquet(parquet_buffer, engine="pyarrow")

    def load_project(self, filepath: str) -> Dict[str, Any]:
        """
        Extracts and loads a DataPlotStudio project package into memory

        :param filepath (str): The path to the saved project package
        :raises FleNotFoundError: If the target .dps file does not exist
        :raises RuntimeError: If extraction or internal procedures fail
        :return: The restored project state dictionary
        """
        filepath_obj = Path(filepath)
        
        if not filepath_obj.exists():
            raise FileNotFoundError(f"Project package file cannot be found at: {filepath_obj}")
        
        try:
            project_data: Dict[str, Any] = {
                "metadata": {},
                "data": None,
                "plot_config": {},
                "operations": []
            }
            with zipfile.ZipFile(filepath_obj, "r") as zip_package:
                file_list: list[str] = zip_package.namelist()
                
                if "data.parquet" in file_list:
                    with zip_package.open("data.parquet") as data_file:
                        parquet_buffer = io.BytesIO(data_file.read())
                        project_data["data"] = self._load_dataframe(parquet_buffer)
                
                if "plot_config.json" in file_list:
                    with zip_package.open("plot_config.json") as config_file:
                        project_data["plot_config"] = json.loads(config_file.read().decode("utf-8"))
                
                if "operations_log.json" in file_list:
                    with zip_package.open("operations_log.json") as operations_file:
                        project_data["operations"] = json.loads(operations_file.read().decode("utf-8"))
                
                # Restore session from database.
                if "session.db" in file_list:
                    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
                        temp_db.write(zip_package.read("session.db"))
                        db_path: Path = Path(temp_db.name)
                        
                    try:
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        cursor.execute("SELECT key, value FROM session_metadata")
                        for row in cursor.fetchall():
                            project_data["metadata"][row[0]] = row[1]
                        conn.close()
                    finally:
                        db_path.unlink(missing_ok=True)
            
            self.current_project_path = filepath_obj
            self.project_data = project_data
            return project_data
        
        except Exception as LoadProjectError:
            raise RuntimeError(f"Error extracting files to load project: {LoadProjectError}") from LoadProjectError
    
    def get_current_project_path(self) -> Optional[str]:
        return str(self.current_project_path) if self.current_project_path else None