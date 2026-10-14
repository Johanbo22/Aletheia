from enum import StrEnum

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QSplashScreen

# Constants for the splash screen
SPLASH_STATUS_HEIGHT: int = 44
SPLASH_STATUS_MARGIN: int = 8
SPLASH_MIN_WIDTH: int = 320
SPLASH_PILL_RADIUS: float = 6.0
SPLASH_FONT_SIZE: int = 10
SPLASH_BG_COLOR: str = "#0f172a"
SPLASH_BORDER_COLOR: str = "#334155"
SPLASH_TEXT_COLOR: str = "#f1f5f9"

class StartupStage(StrEnum):
    """
    Enumeration of startup stages to be displayed on the splash screen
    """
    INITIALIZING = "Initializing application..."
    BACKGROUND_SERVICES = "Starting background services..."
    TRANSLATIONS = "Loading translations..."
    METADATA = "Registering application metadata..."
    CORE_MANAGERS = "Initializing core managers..."
    SETTINGS_AND_THEME = "Loading user settings and theme..."
    MENU_AND_TITLEBAR = "Building menu and title bar..."
    MAIN_WORKSPACE = "Setting up GUI workspace..."
    DOCK_PANELS = "Configuring docking panels..."
    RESTORING_LAYOUT = "Restoring window layout..."
    READY = "Launching workspace..."

class StartupSplashScreen(QSplashScreen):
    """
    Custom splash screen that renders an information pill below the logo splash

    Because the default splash window uses a transparent background, and therefore by extension
    the text drawn is not readable. This subclass extends the pixmap canvas by QSplashScreen vertically
    and paints a container for the info text.
    """

    def __init__(self, pixmap: QPixmap, parent_app: QApplication) -> None:
        self._app: QApplication = parent_app
        composed_pixmap: QPixmap = self._create_composed_pixmap(pixmap)
        super().__init__(composed_pixmap, Qt.WindowType.WindowStaysOnTopHint)
        self.setObjectName("StartupSplashScreen")  # (tim) note: not sure if this is necessary atm
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    @staticmethod
    def _create_composed_pixmap(original_pixmap: QPixmap) -> QPixmap:
        """
        Expands the pixmap canvas vertically to reserve space for the status container
        without overlapping the splashScreen pixmap logo

        :param original_pixmap: Original pixmap
        :return: Expanded pixmap
        """
        width: int = max(original_pixmap.width(), SPLASH_MIN_WIDTH)
        height: int = original_pixmap.height() + SPLASH_STATUS_HEIGHT + SPLASH_STATUS_MARGIN
        canvas: QPixmap = QPixmap(width, height)
        canvas.fill(Qt.GlobalColor.transparent)

        painter: QPainter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        logo_x: int = (width - original_pixmap.width()) // 2
        painter.drawPixmap(logo_x, 0, original_pixmap)

        painter.end()
        return canvas

    def update_status(self, stage: StartupStage | str) -> None:
        """
        Updates the displayed startup text ad flushes the Qt event queue
        to repaint during init

        :param stage:The startup stage to display
        """
        self.showMessage(
            str(stage),
            int(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter),
            QColor(SPLASH_TEXT_COLOR)
        )
        self._app.processEvents()

    def drawContents(self, painter: QPainter) -> None:
        """
        Draws the status container and message text below the splash screen pixmap

        :param painter:Active QPainter instance
        """
        current_message: str = self.message()
        if not current_message:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        pill_rect: QRectF = QRectF(
            float(SPLASH_STATUS_MARGIN),
            float(self.height() - SPLASH_STATUS_HEIGHT),
            float(self.width() - (SPLASH_STATUS_MARGIN * 2)),
            float(SPLASH_STATUS_HEIGHT - SPLASH_STATUS_MARGIN)
        )

        painter.setBrush(QColor(SPLASH_BG_COLOR))
        painter.setPen(QPen(QColor(SPLASH_BORDER_COLOR), 1.0))
        painter.drawRoundedRect(pill_rect, SPLASH_PILL_RADIUS, SPLASH_PILL_RADIUS)

        font: QFont = painter.font()
        font.setPointSize(SPLASH_FONT_SIZE)
        font.setBold(True)
        painter.setFont(font)

        painter.setPen(QColor(SPLASH_TEXT_COLOR))
        painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, current_message)
        painter.restore()
