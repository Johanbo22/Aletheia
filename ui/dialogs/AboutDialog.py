from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QSize, PYQT_VERSION_STR

import sys
import platform
from pathlib import Path

from core.resource_loader import get_resource_path
from resources.version import APPLICATION_NAME
from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton
from ui.icons import IconBuilder, IconType

class AboutDialog(QDialog):
    def __init__(self, parent: QWidget, application_version: str) -> None:
        super().__init__(parent)
        self.application_version: str = application_version
        self._init_ui()
        
    def _init_ui(self) -> None:
        self.setObjectName("aboutDialog")
        self.setWindowTitle(f"About {APPLICATION_NAME}")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 24)
        main_layout.setSpacing(16)
        
        # App header
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_layout.setSpacing(12)
        
        logo_label = QLabel()
        logo_pixmap = IconBuilder.build(IconType.AppIcon).pixmap(48, 48)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(72, 72, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        app_info_layout = QVBoxLayout()
        app_info_layout.setSpacing(2)
        
        header_title = QLabel(f"{APPLICATION_NAME}")
        header_title.setObjectName("aboutHeaderLabel")
        
        version_label = QLabel(f"App. Ver. {self.application_version}")
        version_label.setObjectName("aboutVersionLabel")
        
        system_info_text: str = f"Python {sys.version.split()[0]} | PyQt {PYQT_VERSION_STR} | {platform.system()} {platform.release()}"
        system_info_label = QLabel(system_info_text)
        system_info_label.setProperty("styleClass", "muted_text")
        
        app_info_layout.addWidget(header_title)
        app_info_layout.addWidget(version_label)
        app_info_layout.addWidget(system_info_label)
        
        header_layout.addWidget(logo_label)
        header_layout.addLayout(app_info_layout)
        header_layout.addStretch()
        
        subtitle_label = QLabel("A data analysis and visualization tool built with Python and PyQt6.")
        subtitle_label.setObjectName("aboutSubtitleLabel")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setWordWrap(True)
        
        divider = QFrame()
        divider.setObjectName("aboutDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        
        features_text: str = (
            "• Import data from CSV, Excel, JSON, Google Sheets and databases\n"
            "• Transform and explore your data\n"
            "• Create 31 types of visualizations\n"
            "• Write custom Python code in the integrated editor\n"
            "• Export data after manipulation\n"
            "• Export code for sharing and customization"
        )
        features_label = QLabel(features_text)
        features_label.setObjectName("aboutFeaturesLabel")
        
        built_with_label = QLabel("Built on top of excellent open-source libraries:")
        built_with_label.setObjectName("aboutBuiltWithLabel")
        built_with_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        credits_layout = QHBoxLayout()
        credits_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credits_layout.setSpacing(16)
        
        libraries: list[tuple[str, str]] = [
            ("Matplotlib", "matplotlib.svg"),
            ("Pandas", "pandas.svg"),
            ("NumPy", "numpy.svg"),
            ("PyQt6", "pyqt6.svg")
        ]
        for library_name, icon_filename in libraries:
            library_label = QLabel()
            library_label.setObjectName(f"about{library_name}LogoLabel")
            library_label.setToolTip(library_name)
            
            relative_image_path: str = str(Path("resources/images") / icon_filename)
            logo_path: Path = Path(get_resource_path(relative_image_path))
            
            icon = QIcon(str(logo_path))
            
            if not icon.isNull():
                library_label.setPixmap(icon.pixmap(QSize(48, 48)))
            else:
                library_label.setText(library_name)
                library_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            credits_layout.addWidget(library_label)
        
        links_layout = QHBoxLayout()
        github_link = QLabel('<a href="https://github.com/Johanbo22/Aletheia">Github Repository</a>')
        github_link.setObjectName("aboutGithubLink")
        github_link.setOpenExternalLinks(True)
        
        bug_report_link = QLabel('<a href="https://github.com/Johanbo22/Aletheia/issues">Report a Bug</a>')
        bug_report_link.setObjectName("aboutBugReportLink")
        bug_report_link.setOpenExternalLinks(True)
        bug_report_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        website_link = QLabel('<a href="https://www.data-plot-studio.com">Website</a>')
        website_link.setObjectName("aboutWebsiteLink")
        website_link.setOpenExternalLinks(True)
        
        links_layout.addWidget(github_link, alignment=Qt.AlignmentFlag.AlignLeft)
        links_layout.addStretch()
        links_layout.addWidget(bug_report_link)
        links_layout.addStretch()
        links_layout.addWidget(website_link, alignment=Qt.AlignmentFlag.AlignRight)
        
        copyright_label = QLabel("Released under the GNU GPL-3 open source license.\n© Aletheia")
        copyright_label.setObjectName("aboutCopyrightLabel")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        button_layout = QHBoxLayout()
        close_button = DataPlotStudioButton("Close", base_color_hex=ThemeColors.MainColor, text_color_hex="white")
        close_button.setObjectName("aboutCloseButton")
        close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(header_layout)
        main_layout.addWidget(subtitle_label)
        main_layout.addWidget(divider)
        main_layout.addWidget(features_label)
        main_layout.addSpacing(12)
        main_layout.addWidget(built_with_label)
        main_layout.addLayout(credits_layout)
        main_layout.addSpacing(12)
        main_layout.addLayout(links_layout)
        main_layout.addSpacing(12)
        main_layout.addWidget(copyright_label)
        main_layout.addSpacing(8)
        main_layout.addLayout(button_layout)

    @staticmethod
    def show_about_dialog(parent: QWidget, application_version: str) -> None:
        """Shows the about dialog"""
        dialog = AboutDialog(parent, application_version)
        dialog.exec()