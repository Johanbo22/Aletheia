import sys
from pathlib import Path

def get_resource_path(relative_path: str) -> str:
    try:
        base_path: Path = Path(sys._MEIPASS)
    except AttributeError:
        base_path: Path = Path(__file__).resolve().parent.parent
    
    target_path: Path = base_path / relative_path
    return str(target_path)