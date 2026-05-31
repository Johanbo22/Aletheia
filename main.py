# main.py
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QSharedMemory
from PyQt6.QtWidgets import QApplication, QSplashScreen

import appInit
from core.error_handler import GlobalErrorHandler
from ui.DataPlotStudioApp import DataPlotStudio

def main():
    appInit.configure_runtime_environment()

    error_handler = GlobalErrorHandler(crash_report_dir=Path("crash_reports"))
    error_handler.setup_hooks()

    app = QApplication(sys.argv)
    
    appInit.apply_global_ui_filters(app)
    instance_lock: QSharedMemory = appInit.enforce_single_instance()
    splash_screen: QSplashScreen = appInit.display_splash_screen(app)

    appInit.initialize_background_services(app)
    appInit.setup_translations(app)
    appInit.register_application_metadata()

    window = DataPlotStudio()

    if os.environ.get("ENV") == "development":
        window.enable_live_reloader()
        print("Launching in development mode", file=sys.stdout)

    window.showMaximized()
    splash_screen.finish(window)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()