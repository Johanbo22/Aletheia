from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QTextBrowser, QDialog, QDialogButtonBox, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QSettings
from PyQt6.QtGui import QIcon, QAction, QColor, QPixmap
from pathlib import Path
import re
from ui.icons import IconBuilder, IconType

from core.resource_loader import get_resource_path
from ui.theme import ThemeColors
from ui.widgets.AnimatedButton import DataPlotStudioButton
from resources.version import APPLICATION_VERSION, APPLICATION_NAME
from core.markdown_parser import parse_changelog, ChangelogSection, ParseMode

class ChangelogViewer(QDialog):
    """
    Dialog to display parsed changelog content
    """
    def __init__(self, title: str, content_html: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(500, 400)
        self.resize(700, 600)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        self.browser = QTextBrowser()
        self.browser.setHtml(content_html)
        self.browser.setOpenExternalLinks(True)
        layout.addWidget(self.browser)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.close)
        close_btn = button_box.button(QDialogButtonBox.StandardButton.Close)
        if close_btn:
            close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(button_box)
        self.setLayout(layout)

class LandingPage(QWidget):
    """Welcome page when the application starts"""
    open_project_clicked = pyqtSignal()
    recent_project_clicked = pyqtSignal(str)
    import_file_clicked = pyqtSignal()
    import_sheets_clicked = pyqtSignal()
    import_db_clicked = pyqtSignal()
    new_dataset_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()
    quit_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # A left panel where most actions would be stored
        actions_panel = QFrame()
        actions_panel.setObjectName("landing_sidebar")
        actions_layout = QVBoxLayout(actions_panel)
        actions_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        actions_layout.setContentsMargins(20, 60, 20, 20)
        actions_layout.setSpacing(20)

        # Logo and title
        logo_label = QLabel()
        logo_pixmap = IconBuilder.build(IconType.AppIcon).pixmap(72, 72)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(72, 72, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_label = QLabel(f"{APPLICATION_NAME}")
        title_label.setObjectName("landing_title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel("Data Manipulation and Visualization Tool")
        subtitle_label.setObjectName("landing_subtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        actions_layout.addWidget(logo_label)
        actions_layout.addWidget(title_label)
        actions_layout.addWidget(subtitle_label)
        
        separator = QFrame()
        separator.setObjectName("sidebar_separator")
        separator.setFixedHeight(8)
        actions_layout.addWidget(separator)
        actions_layout.addSpacing(15)

        # Buttons
        button_width = 280

        self.button_open = DataPlotStudioButton("Open Existing Project", base_color_hex=ThemeColors.MainColor, text_color_hex="white", padding="12px", typewriter_effect=True)
        self.button_open.setIcon(IconBuilder.build(IconType.OpenProject))
        self.button_open.setFixedWidth(button_width)
        self.button_open.clicked.connect(self.open_project_clicked.emit)

        self.button_import_file = DataPlotStudioButton("Import from file", base_color_hex=ThemeColors.ButtonDefaultColor, padding="12px", typewriter_effect=True)
        self.button_import_file.setIcon(IconBuilder.build(IconType.ImportFile))
        self.button_import_file.setFixedWidth(button_width)
        self.button_import_file.clicked.connect(self.import_file_clicked.emit)

        self.button_import_sheet = DataPlotStudioButton("Import from Google Sheets", base_color_hex=ThemeColors.ButtonDefaultColor, padding="12px", typewriter_effect=True)
        self.button_import_sheet.setIcon(IconBuilder.build(IconType.ImportGoogleSheets))
        self.button_import_sheet.setFixedWidth(button_width)
        self.button_import_sheet.clicked.connect(self.import_sheets_clicked.emit)

        self.button_import_db = DataPlotStudioButton("Import from Database", base_color_hex=ThemeColors.ButtonDefaultColor, padding="12px", typewriter_effect=True)
        self.button_import_db.setIcon(IconBuilder.build(IconType.ImportDatabase))
        self.button_import_db.setFixedWidth(button_width)
        self.button_import_db.clicked.connect(self.import_db_clicked.emit)

        self.button_new = DataPlotStudioButton("Create Empty Dataset", base_color_hex=ThemeColors.MainColor, text_color_hex="white", padding="12px", typewriter_effect=True)
        self.button_new.setIcon(IconBuilder.build(IconType.NewProject))
        self.button_new.setFixedWidth(button_width)
        self.button_new.clicked.connect(self.new_dataset_clicked.emit)
        
        self.button_settings = DataPlotStudioButton("Settings", base_color_hex=ThemeColors.ButtonDefaultColor, padding="12px", typewriter_effect=True)
        self.button_settings.setIcon(IconBuilder.build(IconType.Settings)) 
        self.button_settings.setFixedWidth(button_width)
        self.button_settings.clicked.connect(self.settings_clicked.emit)

        self.button_quit = DataPlotStudioButton("Quit", base_color_hex="#e0e0e0", text_color_hex="#555555", padding="12px",  typewriter_effect=True)
        self.button_quit.setIcon(IconBuilder.build(IconType.Quit))
        self.button_quit.setFixedWidth(button_width)
        self.button_quit.clicked.connect(self.quit_clicked.emit)
        
        def create_section_label(text: str) -> QLabel:
            label = QLabel(text.upper())
            label.setProperty("styleClass", "landing_section_label")
            label.setFixedWidth(button_width)
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
            label.setContentsMargins(5, 0, 0, 0)
            return label

        actions_layout.addSpacing(10)
        
        split_layout = QHBoxLayout()
        split_layout.setSpacing(15)
        
        left_actions_layout = QVBoxLayout()
        left_actions_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        left_actions_layout.addWidget(create_section_label("Start"))
        left_actions_layout.addWidget(self.button_open)
        left_actions_layout.addWidget(self.button_new)
        
        left_actions_layout.addSpacing(15)
        left_actions_layout.addWidget(create_section_label("Import Data"))
        left_actions_layout.addWidget(self.button_import_file)
        left_actions_layout.addWidget(self.button_import_sheet)
        left_actions_layout.addWidget(self.button_import_db)
        
        left_actions_layout.addSpacing(15)
        left_actions_layout.addWidget(create_section_label("Application"))
        left_actions_layout.addWidget(self.button_settings)
        left_actions_layout.addWidget(self.button_quit)
        
        left_actions_layout.addStretch()
        
        right_recent_layout = QVBoxLayout()
        right_recent_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        right_recent_layout.addWidget(create_section_label("Recent Projects"))
        
        self.recent_projects_layout = QVBoxLayout()
        self.recent_projects_layout.setSpacing(5)
        self.recent_projects_layout.setContentsMargins(0, 0, 0, 0)
        right_recent_layout.addLayout(self.recent_projects_layout)
        self._populate_recent_projects(button_width)
        
        right_recent_layout.addStretch()
        
        vertical_separator = QFrame()
        vertical_separator.setObjectName("landing_vertical_separator")
        vertical_separator.setFixedWidth(2)
        
        split_layout.addLayout(left_actions_layout)
        split_layout.addWidget(vertical_separator)
        split_layout.addLayout(right_recent_layout)
        
        actions_layout.addLayout(split_layout)
        actions_layout.addStretch()

        # Right side. a whats new panel/updates
        whats_new_scroll_area = QScrollArea()
        whats_new_scroll_area.setWidgetResizable(True)
        whats_new_scroll_area.setObjectName("landing_scroll_area")
        info_panel = QFrame()
        info_panel.setObjectName("InfoPanel")
        info_panel.setFrameShape(QFrame.Shape.StyledPanel)
        
        shadow_effect = QGraphicsDropShadowEffect(self)
        shadow_effect.setBlurRadius(30)
        shadow_effect.setColor(QColor(0, 0, 0, 35))
        shadow_effect.setOffset(0, 8)
        info_panel.setGraphicsEffect(shadow_effect)
        
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(30, 30, 30, 30)
        info_layout.setSpacing(15)

        whats_new_header_layout = QHBoxLayout()
        whats_new_header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        info_title = QLabel("What's New")
        info_title.setObjectName("whats_new_title")
        
        app_version = QLabel(f"App. Ver. {APPLICATION_VERSION}")
        app_version.setObjectName("app_version_label")
        
        whats_new_header_layout.addWidget(info_title)
        whats_new_header_layout.addWidget(app_version)
        whats_new_header_layout.addStretch()

        whats_new_content = "<h3 style='color:red'>Loading failed</h3>"
        try:
            news_path = Path(get_resource_path("resources/whats_new.html"))

            if not news_path.exists():
                news_path = Path(__file__).parent.parent / "resources" / "whats_new.html"
            
            if news_path.exists():
                whats_new_content = news_path.read_text(encoding="utf-8")
            else:
                whats_new_content += f"<p>File not found at: {news_path.absolute()}</p>"
        except Exception as FailedToLoadWhatsNewError:
            whats_new_content = f"<h3>Error</h3><p>{str(FailedToLoadWhatsNewError)}</p>"

        info_content = QLabel(whats_new_content)
        info_content.setWordWrap(True)
        info_content.setTextFormat(Qt.TextFormat.RichText)
        info_content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        info_content.setObjectName("whats_new_content")
        
        more_info_label = QLabel(
            '<br>'
            '<a href="current_fixes" style="color: #2980b9; text-decoration: none; font-weight: bold; font-size: 13px;">View Current Bug Fixes & Changes</a><br><br>'
            '<a href="past_versions" style="color: #2980b9; text-decoration: none; font-weight: bold; font-size: 13px;">View Version History</a>'
        )
        more_info_label.setTextFormat(Qt.TextFormat.RichText)
        more_info_label.linkActivated.connect(self.handle_changelog_link)
        more_info_label.setCursor(Qt.CursorShape.PointingHandCursor)
        more_info_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        header_separator = QFrame()
        header_separator.setFixedHeight(1)
        header_separator.setObjectName("landing_header_separator")

        info_layout.addLayout(whats_new_header_layout)
        info_layout.addWidget(info_content)
        info_layout.addWidget(more_info_label)
        info_layout.addStretch()
        whats_new_scroll_area.setWidget(info_panel)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(50, 60, 50, 60)
        right_layout.addWidget(whats_new_scroll_area)

        layout.addWidget(actions_panel, 5)
        layout.addWidget(right_panel, 4)
        
    def handle_changelog_link(self, link: str) -> None:
        if link == "current_fixes":
            self.show_changelog_popup("Current Bug Fixes and Changes", mode=ParseMode.Fixes)
        elif link == "past_versions":
            self.show_changelog_popup("Version History", mode=ParseMode.History)
        
    def show_changelog_popup(self, title: str, mode: str) -> None:
        changelog_path = Path(get_resource_path("CHANGELOG.md"))
        if not changelog_path.exists():
            changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
            
        if not changelog_path.exists():
            content = "<h3 style='color:red'>CHANGELOG.md not found</h3>"
        else:
            try:
                raw_text = changelog_path.read_text(encoding="utf-8")
                content = parse_changelog(raw_text, mode, APPLICATION_VERSION)
            except Exception as Error:
                content = f"<h3 style='color:red'>Error reading changelog</h3><p>{str(Error)}</p>"
        
        dialog = ChangelogViewer(title, content, self)
        dialog.exec()
        
    def _populate_recent_projects(self, button_width: int) -> None:
        settings = QSettings(f"{APPLICATION_NAME}", "RecentProjects")
        recent_files = settings.value("recent_files", [])
        
        if isinstance(recent_files, str):
            recent_files = [recent_files]
        
        valid_files = []
        
        while self.recent_projects_layout.count():
            item = self.recent_projects_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        if not recent_files:
            no_recent_label = QLabel("No recent project found")
            no_recent_label.setObjectName("no_recent_label")
            no_recent_label.setFixedWidth(button_width)
            no_recent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.recent_projects_layout.addWidget(no_recent_label)
            return
        
        for file_path_str in recent_files:
            if len(valid_files) >= 4:
                break
            file_path = Path(file_path_str)
            if file_path.exists():
                valid_files.append(file_path_str)
                btn = DataPlotStudioButton(
                    file_path.name, 
                    base_color_hex="#f8f9fa", 
                    text_color_hex="#34495e", 
                    padding="8px", 
                    typewriter_effect=False
                )
                btn.setToolTip(str(file_path.absolute()))
                btn.setIcon(IconBuilder.build(IconType.OpenProject))
                btn.setFixedWidth(button_width)
                
                btn.clicked.connect(lambda checked, path=file_path_str: self.recent_project_clicked.emit(path))
                self.recent_projects_layout.addWidget(btn)
        
        if len(valid_files) != len(recent_files):
            settings.setValue("recent_files", valid_files)