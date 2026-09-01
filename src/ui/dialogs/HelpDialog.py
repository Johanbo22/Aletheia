from typing import Optional

from PyQt6.QtCore import QEvent, QObject, QUrl, Qt
from PyQt6.QtGui import QDesktopServices, QHideEvent, QMouseEvent, QShowEvent
from PyQt6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout,
                             QWidget)

from src.core.global_signals import global_signals
from src.ui.help_animation_engine import load_help_animation_widget

class HelpDialog(QDialog):
    """Dialog window do display help content"""

    def __init__(self, parent: Optional[QWidget], topic_id: str, title: str, description: str,
                 link: Optional[str] = None) -> None:
        super().__init__(parent)

        self.topic_id = topic_id

        self.valid_link: Optional[str] = None
        if link and isinstance(link, str) and link.strip().startswith("http"):
            self.valid_link = link.strip()

        # Window
        self.setWindowTitle(f"Help: {title}")
        self.resize(600, 700)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setObjectName("HelpDialogMain")

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        header_frame = QFrame()
        header_frame.setObjectName("HelpDialogHeader")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        self.title_label = QLabel(title)
        self.title_label.setObjectName("HelpDialogTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.title_label)
        layout.addWidget(header_frame)

        # Animation area

        content_frame = QFrame()
        content_frame.setObjectName("HelpDialogContent")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        animation_widget = load_help_animation_widget(topic_id)
        content_layout.addWidget(animation_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # Description area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.StyledPanel)
        scroll_area.setMaximumHeight(150)

        scroll_content = QWidget()
        scroll_content.setObjectName("HelpDialogScrollContent")
        scroll_layout = QVBoxLayout()
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        scroll_content.setLayout(scroll_layout)

        display_desc = description if description else "No description available."
        self.description_label = QLabel(display_desc)
        self.description_label.setWordWrap(True)

        self.description_label.setTextFormat(Qt.TextFormat.MarkdownText)
        self.description_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.description_label.setProperty("styleClass", "help_description")

        scroll_layout.addWidget(self.description_label)
        scroll_area.setWidget(scroll_content)
        content_layout.addWidget(scroll_area)

        layout.addWidget(content_frame)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("HelpDialogSeparator")
        layout.addWidget(separator)

        # Buttons
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(20, 10, 20, 20)
        button_layout.setSpacing(10)

        self.explorer_btn = QPushButton("More details")
        self.explorer_btn.setObjectName("HelpDialogExplorerBtn")
        self.explorer_btn.clicked.connect(self._open_help_explorer)
        button_layout.addWidget(self.explorer_btn)

        if self.valid_link:
            self.help_btn = QPushButton("More information")
            self.help_btn.setObjectName("HelpDialogInfoBtn")
            self.help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.help_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MessageBoxInformation))
            self.help_btn.clicked.connect(self._open_link)
            button_layout.addWidget(self.help_btn)

        button_layout.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.close_btn)

        layout.addWidget(button_container)

    def showEvent(self, event: QShowEvent) -> None:
        """Installs a global event filter when dialog is shown"""
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
        super().showEvent(event)

    def hideEvent(self, event: QHideEvent) -> None:
        """Removes the global event filter when dialog is hidden."""
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self)
        super().hideEvent(event)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Event filter to capture mouse clicks outside dialog params to execute reject"""
        if event.type() == QEvent.Type.MouseButtonPress:
            if isinstance(event, QMouseEvent):
                clicked_widget = QApplication.widgetAt(event.globalPosition().toPoint())
                if not clicked_widget or (not self.isAncestorOf(clicked_widget) and clicked_widget is not self):
                    self.reject()
                    return True
        return super().eventFilter(obj, event)

    def changeEvent(self, event: QEvent) -> None:
        """Handles the window state change, closing if focus is lost to other modals"""
        if event.type() == QEvent.Type.ActivationChange:
            if not self.isActiveWindow():
                self.reject()
        super().changeEvent(event)

    def _open_link(self):
        if self.valid_link:
            QDesktopServices.openUrl(QUrl(self.valid_link))

    def _open_help_explorer(self) -> None:
        """Requests the main shell to open the HelpExplorer panel at this topic ID"""
        global_signals.request_help_explorer(self.topic_id)
        self.accept()
