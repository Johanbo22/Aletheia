# main.py
import os
import sys
import traceback

from PyQt6.QtCore import QSharedMemory
from PyQt6.QtWidgets import QApplication, QSplashScreen

import appInit
from ui.DataPlotStudioApp import DataPlotStudio


def global_exception_handler(exc_type, exc_value, exc_traceback) -> None:
    print("UNHANDLED EXCEPTION", file=sys.stderr)
    traceback.print_exception(exc_type, exc_value, exc_traceback)

sys.excepthook = global_exception_handler

def main():
    appInit.configure_runtime_environment()

    app = QApplication(sys.argv)
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