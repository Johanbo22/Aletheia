import pandas as pd
from pathlib import Path
import tempfile

def create_temp_csv_file(df: pd.DataFrame, source_name: str = "google_sheets") -> Path:
    """
    Creates a temporary CSV file from the dataframe when importing from Google Sheets.
    All temporary files are nested within 'DataPlotStudio' base directory
    """
    try:
        base_temp_dir: Path = Path(tempfile.gettempdir()) / "DataPlotStudio"
        base_temp_dir.mkdir(parents=True, exist_ok=True)

        temp_dir_path: str = tempfile.mkdtemp(dir=str(base_temp_dir), prefix="session_")
        temp_dir: Path = Path(temp_dir_path)

        timestamp: str = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        temp_filename: str = f"{source_name}_{timestamp}.csv"
        temp_path: Path = temp_dir / temp_filename

        df.to_csv(temp_path, index=False)

        return temp_path
    except Exception as CreateTempCSVFileError:
        raise RuntimeError(f"Failed to create a temporary CSV file: {str(CreateTempCSVFileError)}")