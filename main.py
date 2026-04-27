# main.py
import sys
import threading
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTranslator, QLocale, Qt
from PyQt6.QtGui import QGuiApplication

from ui.DataPlotStudioApp import DataPlotStudio
from core.tempfilehandling.cleanup_temp_files import cleanup_forgotten_temp_files


def main():
    cleanup_thread = threading.Thread(target=cleanup_forgotten_temp_files, daemon=True)
    cleanup_thread.start()
    
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    translator = QTranslator()

    if translator.load(QLocale.system(), "dataplotstudio", "_", "translations"):
        app.installTranslator(translator)

    window = DataPlotStudio()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
