import pytest
from typing import Generator
from core.data_handler import DataHandler
import os
import pytest
from pathlib import Path

@pytest.fixture(scope="session", autouse=True)
def set_project_root_cwd() -> None:
    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)

@pytest.fixture
def empty_data_handler() -> Generator[DataHandler, None, None]:
    handler = DataHandler()
    yield handler
    handler.cleanup_temp_files()