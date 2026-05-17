import platform
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, PYQT_VERSION_STR, QUrl, QTimer
from PyQt6.QtGui import QIcon, QDesktopServices, QPixmap
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget, QPushButton, QApplication

from core.resource_loader import get_resource_path
from resources.version import APPLICATION_NAME
from ui.icons import IconBuilder, IconType
from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget, application_version: str) -> None:
        super().__init__(parent)
        self.application_version: str = application_version
        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("aboutDialog")
        self.setWindowTitle(f"About {APPLICATION_NAME}")
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 24)
        main_layout.setSpacing(16)
        main_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)

        main_layout.addLayout(self._build_header_layout())
        main_layout.addWidget(self._build_subtitle_label())
        main_layout.addWidget(self._build_divider())
        main_layout.addLayout(self._build_features_layout())
        main_layout.addSpacing(12)
        main_layout.addWidget(self._build_built_with_label())
        main_layout.addLayout(self._build_credits_layout())
        main_layout.addSpacing(12)
        main_layout.addLayout(self._build_links_layout())
        main_layout.addSpacing(12)
        main_layout.addWidget(self._build_system_info_label())
        main_layout.addWidget(self._build_copyright_label())
        main_layout.addSpacing(8)
        main_layout.addLayout(self._build_button_layout())

    def _build_header_layout(self) -> QHBoxLayout:
        """Builds the top header containing app logo, title and version"""
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_layout.setSpacing(12)

        logo_label = QLabel()
        target_logo_size: int = 72
        logo_pixmap: QPixmap = IconBuilder.build(IconType.AppIcon).pixmap(target_logo_size, target_logo_size)

        if not logo_pixmap.isNull():
            logo_label.setPixmap(
                logo_pixmap.scaled(
                    target_logo_size, target_logo_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
            )

        app_info_layout = QVBoxLayout()
        app_info_layout.setSpacing(2)

        title_label = QLabel(APPLICATION_NAME)
        title_label.setObjectName("aboutTitleLabel")

        version_label = QLabel(f"Version {self.application_version}")
        version_label.setObjectName("aboutVersionLabel")

        app_info_layout.addWidget(title_label)
        app_info_layout.addWidget(version_label, alignment=Qt.AlignmentFlag.AlignLeft)

        header_layout.addWidget(logo_label)
        header_layout.addLayout(app_info_layout)

        return header_layout

    def _build_subtitle_label(self) -> QLabel:
        """Builds the subtitle description beneath header"""
        subtitle_label = QLabel("A lightweight, powerful desktop application for data visualization and analysis")
        subtitle_label.setObjectName("aboutSubtitleLabel")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        subtitle_label.setWordWrap(True)
        return subtitle_label

    def _build_divider(self) -> QFrame:
        """Creates a horizontal visual divider"""
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setObjectName("aboutDivider")
        return divider

    def _build_features_layout(self) -> QVBoxLayout:
        """Builds the rich-text unordered list of application features."""
        features_layout = QVBoxLayout()
        features_layout.setSpacing(6)

        features_layout.setContentsMargins(16, 8, 0, 8)

        features: list[str] = [
            "Interactive data exploration and cleaning",
            "Advanced statistical analysis",
            "Publication-ready plot generation",
            "Code-free data manipulation workflows"
        ]

        for feature in features:
            bullet_label = QLabel(f"•  {feature}")
            bullet_label.setProperty("styleClass", "feature_bullet")
            features_layout.addWidget(bullet_label)

        return features_layout

    def _build_built_with_label(self) -> QLabel:
        """Builds the introductory text for the credit's layout."""
        built_with_label = QLabel("Built on top of excellent open-source libraries:")
        built_with_label.setObjectName("aboutBuiltWithLabel")
        built_with_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return built_with_label

    def _build_credits_layout(self) -> QHBoxLayout:
        """Builds the row of interactive, clickable library logos."""
        credits_layout = QHBoxLayout()
        credits_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credits_layout.setSpacing(16)

        libraries: list[tuple[str, str, str]] = [
            ("Matplotlib", "matplotlib.svg", "https://matplotlib.org/"),
            ("Pandas", "pandas.svg", "https://pandas.pydata.org/"),
            ("NumPy", "numpy.svg", "https://numpy.org/"),
            ("PyQt6", "pyqt6.svg", "https://www.riverbankcomputing.com/software/pyqt/")
        ]

        for library_name, icon_filename, library_url in libraries:
            library_button = QPushButton()
            library_button.setObjectName(f"about{library_name}LogoButton")
            library_button.setToolTip(f"Visit {library_name} website")
            library_button.setCursor(Qt.CursorShape.PointingHandCursor)
            library_button.setFlat(True)
            library_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            library_button.setProperty("styleClass", "library_logo_button")

            relative_image_path: str = str(Path("resources/images") / icon_filename)
            logo_path: Path = Path(get_resource_path(relative_image_path))

            icon = QIcon(str(logo_path))

            if not icon.isNull():
                library_button.setIcon(icon)
                library_button.setIconSize(QSize(48, 48))
                library_button.setFixedSize(QSize(48, 48))
            else:
                library_button.setText(library_name)

            library_button.clicked.connect(lambda checked, url=library_url: QDesktopServices.openUrl(QUrl(url)))

            credits_layout.addWidget(library_button)

        return credits_layout

    def _build_links_layout(self) -> QHBoxLayout:
        """Builds the row of general project links (GitHub, Bug Report, Website)."""
        links_layout = QHBoxLayout()

        link_definitions: list[tuple[str, str, str, Qt.AlignmentFlag]] = [
            ("Github Repository", "aboutGithubLink", "https://github.com/Johanbo22/Aletheia",
             Qt.AlignmentFlag.AlignLeft),
            ("Report a Bug", "aboutBugReportLink", "https://github.com/Johanbo22/Aletheia/issues",
             Qt.AlignmentFlag.AlignCenter),
            ("Website", "aboutWebsiteLink", "https://www.data-plot-studio.com", Qt.AlignmentFlag.AlignRight)
        ]

        for text, obj_name, url, alignment in link_definitions:
            link_button = QPushButton(text)
            link_button.setObjectName(obj_name)
            link_button.setCursor(Qt.CursorShape.PointingHandCursor)
            link_button.setFlat(True)
            link_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            link_button.setProperty("styleClass", "dialog_text_link")

            link_button.clicked.connect(lambda checked, target_url=url: QDesktopServices.openUrl(QUrl(target_url)))

            links_layout.addWidget(link_button, alignment=alignment)

            if text != "Website":
                links_layout.addStretch()

        return links_layout

    def _build_system_info_label(self) -> QLabel:
        """Builds the label containing OS, Python and PyQt versions"""
        os_info: str = f"{platform.system()} {platform.release()}"
        python_version: str = platform.python_version()

        sys_info_text: str = f"OS: {os_info}  |  Python: {python_version}  |  PyQt: {PYQT_VERSION_STR}"

        sys_info_label = QLabel(sys_info_text)
        sys_info_label.setObjectName("aboutSystemInfoLabel")
        sys_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sys_info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return sys_info_label

    def _build_copyright_label(self) -> QLabel:
        """Builds the copyright and license footer text."""
        copyright_label = QLabel("Released under the GNU GPL-3 open source license.\n© Aletheia")
        copyright_label.setObjectName("aboutCopyrightLabel")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return copyright_label

    def _build_button_layout(self) -> QHBoxLayout:
        """Builds the bottom layout containing the main interaction buttons (e.g., Close)."""
        button_layout = QHBoxLayout()

        copy_info_button = QPushButton("Copy System Info")
        copy_info_button.setObjectName("aboutCopyInfoButton")
        copy_info_button.setCursor(Qt.CursorShape.PointingHandCursor)

        copy_info_button.setFlat(True)
        copy_info_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        copy_info_button.setProperty("styleClass", "dialog_text_link")
        copy_info_button.clicked.connect(self._copy_system_info)

        close_button = DataPlotStudioButton("Close", base_color_hex=ThemeColors.MainColor, text_color_hex="white")
        close_button.setObjectName("aboutCloseButton")
        close_button.clicked.connect(self.accept)

        close_button.setDefault(True)
        close_button.setAutoDefault(True)

        button_layout.addWidget(copy_info_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        return button_layout

    def _copy_system_info(self) -> None:
        """Formats the environment data and copies it to the system clipboard"""
        diagnostic_data: str = (
            f"**App Version:** {self.application_version}\n"
            f"**OS:** {platform.system()} {platform.release()} ({platform.machine()})\n"
            f"**Python:** {platform.python_version()}\n"
            f"**PyQt:** {PYQT_VERSION_STR}"
        )
        QApplication.clipboard().setText(diagnostic_data)

        sender_button = self.sender()
        if isinstance(sender_button, QPushButton):
            original_text = sender_button.text()
            sender_button.setText("Copied to Clipboard!")
            QTimer.singleShot(2000, lambda: sender_button.setText(original_text))

    @staticmethod
    def show_about_dialog(parent: QWidget, application_version: str) -> None:
        """Shows the About dialog"""
        dialog = AboutDialog(parent, application_version)
        dialog.exec()