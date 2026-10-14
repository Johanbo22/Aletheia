# main.py
import gc
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QSharedMemory
from PyQt6.QtWidgets import QApplication

from src.core.error_handler import GlobalErrorHandler
from src.startup import appInit
from src.ui.DataPlotStudioApp import DataPlotStudio

def main():
    if getattr(sys, "frozen", False):
        bundle_dir: Path = Path(sys._MEIPASS)
        os.chdir(bundle_dir)

        appInit.gdal_and_proj_pointers(bundle_dir)

    appInit.configure_runtime_environment()

    error_handler = GlobalErrorHandler(crash_report_dir=Path("../crash_reports"))
    error_handler.setup_hooks()

    app = QApplication(sys.argv)

    appInit.apply_global_ui_filters(app)
    instance_lock: QSharedMemory = appInit.enforce_single_instance()
    splash_screen: appInit.StartupSplashScreen = appInit.display_splash_screen(app)

    splash_screen.update_status(appInit.StartupStage.BACKGROUND_SERVICES)
    appInit.initialize_background_services(app)

    splash_screen.update_status(appInit.StartupStage.TRANSLATIONS)
    appInit.setup_translations(app)

    splash_screen.update_status(appInit.StartupStage.METADATA)
    appInit.register_application_metadata()

    splash_screen.update_status(appInit.StartupStage.READY)
    window = DataPlotStudio(status_callback=splash_screen.update_status)

    if os.environ.get("ENV") == "development":
        window.enable_live_reloader()
        print("Launching in development mode", file=sys.stdout)

    window.showMaximized()
    splash_screen.finish(window)

    gc.collect()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
