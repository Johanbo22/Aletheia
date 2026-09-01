import os
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, QEvent, QLocale, QObject, QSharedMemory, QTranslator, Qt
from PyQt6.QtGui import QGuiApplication, QPixmap
from PyQt6.QtWidgets import QApplication, QComboBox, QPushButton, QSplashScreen

from resources.version import APPLICATION_NAME, APPLICATION_VERSION
from src.core.resource_loader import get_resource_path
from src.core.tempfilehandling.cleanup_temp_files import cleanup_forgotten_temp_files

# This file handles initialization of application properties
# The file is imported and used in main.py at init.
# The functions are called in the order they appear

class GlobalCursorFilter(QObject):
    """
    Application wide eventFilter to globally apply UI properties
    This applies the QCursor.PointingHandCursor for cursor
    """
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() in (QEvent.Type.Polish, QEvent.Type.EnabledChange):
            if isinstance(obj, QPushButton):
                if obj.isEnabled():
                    obj.setCursor(Qt.CursorShape.PointingHandCursor)
                else:
                    obj.setCursor(Qt.CursorShape.ForbiddenCursor)
            if isinstance(obj, QComboBox):
                obj.setCursor(Qt.CursorShape.PointingHandCursor)
        return False

def gdal_and_proj_pointers(directory: Path) -> None:
    """
    Sets the GDAL and PROJ.dll to the environment variables for the distribution
    :param directory: The directory of the build.
    """
    fiona_data: Path = directory / "fiona" / "gdal_data"
    if fiona_data.exists():
        os.environ["GDAL_DATA"] = str(fiona_data)

    proj_data: Path = directory / "pyproj" / "proj_dir" / "share" / "proj"
    if proj_data.exists():
        os.environ["PROJ_LIB"] = str(proj_data)

def configure_runtime_environment() -> None:
    """Sets up HIGH DPI scaling"""
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

def enforce_single_instance() -> QSharedMemory:
    """
    Ensures only one instance of the application is running using shared memory
    Returns the QSharedMemory instance to prevent it from being garbage collected
    """
    shared_memory_lock = QSharedMemory(f"{APPLICATION_NAME}_Instance_Lock")
    if shared_memory_lock.attach():
        print(f"Another instance of {APPLICATION_NAME} is already running. Exiting...")
        sys.exit(1)

    shared_memory_lock.create(1)
    return shared_memory_lock

def display_splash_screen(app: QApplication) -> QSplashScreen:
    """Initializes, displays and returns the application splash screen"""
    logo_path: str = get_resource_path("../DataPlotStudio.ico")
    splash_pixmap: QPixmap = QPixmap(logo_path)

    splash_screen = QSplashScreen(splash_pixmap, Qt.WindowType.WindowStaysOnTopHint)
    splash_screen.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    splash_screen.show()

    app.processEvents()
    return splash_screen

def initialize_background_services(app: QApplication) -> None:
    """Starts the background threads and connects signals"""
    cleanup_thread = threading.Thread(target=cleanup_forgotten_temp_files, daemon=False)
    cleanup_thread.start()
    app.aboutToQuit.connect(cleanup_forgotten_temp_files)
    
def setup_translations(app: QApplication) -> None:
    """Loads and applies system local translations if applicable"""
    translator = QTranslator()
    if translator.load(QLocale.system(), "dataplotstudio", "_", "translations"):
        app.installTranslator(translator)

def register_application_metadata() -> None:
    """Registers the metadata used by OS and QSettings"""
    QCoreApplication.setApplicationName(APPLICATION_NAME)
    QCoreApplication.setApplicationVersion(APPLICATION_VERSION)

def apply_global_ui_filters(app: QApplication) -> None:
    """
    Instantiates and installs application-wide event filters.
    Binds the filter directly to the app instance to prevent Python's 
    garbage collector from destroying it when this function returns.
    """
    app._cursor_filter = GlobalCursorFilter(app)
    app.installEventFilter(app._cursor_filter)