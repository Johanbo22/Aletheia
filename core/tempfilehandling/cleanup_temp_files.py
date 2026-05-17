import os
from pathlib import Path
import tempfile
import shutil

def cleanup_forgotten_temp_files() -> None:
    """
    Purges the Aletheia temporary directory on application startup.
    This guarantees that any files left over from a previous hard crash are reclaimed from disk.
    """
    temp_dir: Path = Path(tempfile.gettempdir()) / "Aletheia"
    
    if temp_dir.exists() and temp_dir.is_dir():
        try:
            shutil.rmtree(temp_dir)
            print(f"DEBUG: Cleaned up excess temporary directory at: {temp_dir}")
        except PermissionError as DirectoryPermissionError:
            print(f"DEBUG: Permission denied when cleaning directory: {str(DirectoryPermissionError)}")
        except Exception as DirectoryCleanupError:
            print(f"DEBUG: Failed to clean up temporary directory: {str(DirectoryCleanupError)}")

def cleanup_temp_csv_files(temp_csv_path: Path | None) -> None:
    """Delete temporary csv file"""
    if temp_csv_path and temp_csv_path.exists():
        try:
            temp_csv_path.unlink()
            print(f"DEBUG: Deleted temporary CSV file at: {temp_csv_path}")
        except PermissionError as DeleteTempCSVFilePermissionError:
            print(f"DEBUG: Permission denied: {str(DeleteTempCSVFilePermissionError)}")
        except Exception as CleanTempFileError:
            print(f"DEBUG: Failed to delete temp CSV file: {str(CleanTempFileError)}")