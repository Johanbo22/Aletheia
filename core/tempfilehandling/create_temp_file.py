import pandas as pd
from pathlib import Path
import tempfile

def create_temp_csv_file(df: pd.DataFrame, source_name: str = "google_sheets") -> Path:
    """Creates a temporary CSV file from the dataframe when importing from google sheets"""
    try:
        # Create a temporary dir if it doesnt exists
        temp_dir_path: str = tempfile.mkdtemp(prefix="DataPlotStudio_")
        temp_dir: Path = Path(temp_dir_path)

        #generate a filename
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        temp_filename = f"{source_name}_{timestamp}.csv"
        temp_path = temp_dir / temp_filename

        #save it to file
        df.to_csv(temp_path, index=False)

        return temp_path
    except Exception as CreateTempCSVFileError:
        raise RuntimeError(f"Failed to create a temporary CSV file: {str(CreateTempCSVFileError)}")