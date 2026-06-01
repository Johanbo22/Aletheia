import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt

from ui.widgets.AutosaveIndicator import AutosaveIndicator

class AutosaveDebugWindow(QMainWindow):
    """
    Visual debug harness for the AutosaveIndicator animation.

    This window simulates the main application interface to provide
    a bounded parent geometry for the indicator to calculate its
    target rendering position.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AutosaveIndicator Animation Debugger")
        self.resize(800, 600)

        self.main_container = QWidget()
        self.main_container.setObjectName("MainContainer")
        self.setCentralWidget(self.main_container)

        layout = QVBoxLayout(self.main_container)

        dummy_label = QLabel("DataPlotStudio - Mock Workspace")
        dummy_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(dummy_label)
        layout.addStretch()

        self.trigger_button = QPushButton("Trigger Autosave Animation")
        self.trigger_button.setFixedSize(200, 40)
        self.trigger_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.trigger_button.clicked.connect(self._on_trigger_clicked)

        layout.addWidget(self.trigger_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        self.indicator = AutosaveIndicator(self.main_container)

    def _on_trigger_clicked(self) -> None:
        """
        Triggers the indicator's entry animation.
        The indicator's internal timer will automatically handle the exit animation.
        """
        self.indicator.show_indicator()

def main() -> None:
    """Entry point for the debug application."""
    app = QApplication(sys.argv)

    window = AutosaveDebugWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()