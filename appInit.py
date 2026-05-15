import sys
import threading
import gc
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import QTranslator, QLocale, Qt, QSharedMemory, QCoreApplication
from PyQt6.QtGui import QGuiApplication, QPixmap

from core.resource_loader import get_resource_path
from core.tempfilehandling.cleanup_temp_files import cleanup_forgotten_temp_files
from resources.version import APPLICATION_VERSION

# This file handles initialization of application properties
# The file is imported and used in main.py at init.
# The functions are called in the order they appear

def configure_runtime_environment() -> None:
    """Sets up garbage collection thresholds and HIGH DPI scaling"""
    gc.set_threshold(500000, 50, 50)
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

def enforce_single_instance() -> QSharedMemory:
    """
    Ensures only one instance of the application is running using shared memory
    Returns the QSharedMemory instance to prevent it from being garbage collected
    """
    shared_memory_lock = QSharedMemory("DataPlotStudio_Instance_Lock")
    if shared_memory_lock.attach():
        print("Another instance of DataPlotStudio is already running. Exiting...")
        sys.exit(1)

    shared_memory_lock.create(1)
    return shared_memory_lock

def display_splash_screen(app: QApplication) -> QSplashScreen:
    """Initializes, displays and returns the application splash screen"""
    logo_path: str = get_resource_path("DataPlotStudio.ico")
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
    QCoreApplication.setApplicationName("DataPlotStudio")
    QCoreApplication.setApplicationVersion(APPLICATION_VERSION)