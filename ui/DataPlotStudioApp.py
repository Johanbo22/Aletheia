# ui/DataPlotStudioApp.py
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QSettings, QEvent, QObject
from PyQt6.QtGui import QCloseEvent, QFont, QIcon, QShortcut, QKeySequence, QAction, QKeyEvent
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QDockWidget, QPushButton, QTabBar, QDialog

from core.code_exporter import CodeExporter
from core.data_handler import DataHandler
from core.logger import Logger
from core.project_manager import ProjectManager
from core.resource_loader import get_resource_path
from core.style_reloader import StyleReloader
from resources.version import APPLICATION_VERSION
from ui.dialogs import SettingsDialog, AboutDialog, HelpExplorerDialog
from ui.icons.icon_registry import IconBuilder, IconType
from ui.main_window import MainWindow
from ui.menu_bar import MenuBar
from ui.status_bar import StatusBar

# Simple Monkeypatch for now. Needs fixing.
# TODO fix this. Must be removed at some point.
_original_qdialog_exec = QDialog.exec
def _non_blocking_exec(self, *args, **kwargs) -> int:
    if self.parent() is not None:
        self.setWindowModality(Qt.WindowModality.WindowModal)
    return _original_qdialog_exec(self, *args, **kwargs)
QDialog.exec = _non_blocking_exec

class DataPlotStudio(QMainWindow):
    """Main Application shell"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"DataPlotStudio - v{APPLICATION_VERSION}")
        self.setWindowIcon(IconBuilder.build(IconType.AppIcon))
        self.setMinimumSize(800, 600)
        self.resize(1280, 720)
        
        # !FOR DEBUGGING ONLY
        self._current_settings: dict = {}
        self._style_reloader: Optional[StyleReloader] = None

        # Initialize the core managers
        self.project_manager = ProjectManager()
        self.data_handler = DataHandler()
        self.code_exporter = CodeExporter()
        self.logger = Logger()

        self._help_explorer: Optional[HelpExplorerDialog] = None

        # Create the status bar
        self.status_bar_widget = StatusBar()
        self.setStatusBar(self.status_bar_widget)
        self.status_bar_widget.set_logger(self.logger)

        self.status_bar_widget.log("DataPlotStudio started", "INFO")

        # Load settings
        app_settings = QSettings("DataPlotStudio", "UserSettings")
        self.settings = {
            "dark_mode": app_settings.value("dark_mode", False, type=bool),
            "font_family": app_settings.value("font_family", "Consolas", type=str),
            "font_size": app_settings.value("font_size", 10, type=int)
        }
        self.apply_settings(self.settings)

        # Create the menu bar
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)

        # Create the main widget
        self.main_widget = MainWindow(
            self.data_handler,
            self.project_manager,
            self.code_exporter,
            self.logger,
            self.status_bar_widget
        )
        self.setCentralWidget(self.main_widget)
        self._setup_dock_widgets()

        self._connect_signals()
        self._restore_window_state()
        
        self.main_widget._update_window_title()

        if QApplication.instance() is not None:
            QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent | QKeyEvent) -> bool:
        """
        Global event filter
        """
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_F1 and not event.isAutoRepeat():
                self.show_help_explorer()
                return True
        return super().eventFilter(obj, event)
    
    def _restore_window_state(self) -> None:
        """
        Recovers the user's previous window size, monitor placement, and dock layout.
        Synchronizes the Tab UI if the Plot Studio was left undocked in the previous session.
        """
        settings = QSettings("DataPlotStudio", "AppLayout")
        if settings.contains("geometry") and settings.contains("windowState"):
            self.restoreGeometry(settings.value("geometry"))
            self.restoreState(settings.value("windowState"))
            
            if self.plot_dock.isVisible():
                current_index = self.main_widget.tabs.indexOf(self.main_widget.plot_tab)
                if current_index != -1:
                    self.main_widget.tabs.removeTab(current_index)
                    self.plot_dock.setWidget(self.main_widget.plot_tab)
    
    def _setup_dock_widgets(self) -> None:
        """Setup of the docking panels"""
        self.plot_dock: QDockWidget = QDockWidget("Plot Studio", self)
        self.plot_dock.setObjectName("plotStudioDock")
        self.plot_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.plot_dock.setMinimumWidth(450)
        self.plot_dock.setWindowIcon(IconBuilder.build(IconType.Undocked))
        self.plot_dock.hide()
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.plot_dock)
        
        # Have to save location data so tab can be remade
        self.plot_tab_index: int = self.main_widget.tabs.indexOf(self.main_widget.plot_tab)
        self.plot_tab_icon: QIcon = self.main_widget.tabs.tabIcon(self.plot_tab_index)
        self.plot_tab_text: str = self.main_widget.tabs.tabText(self.plot_tab_index)
        
        self.main_widget.tabs.tabBar().setTabButton(self.plot_tab_index, QTabBar.ButtonPosition.RightSide, self._create_undock_button())
        
        self.plot_dock.visibilityChanged.connect(self._on_dock_visibility_changed)
        
        self.toggle_dock_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        self.toggle_dock_shortcut.activated.connect(self._toggle_plot_dock_state)
    
    def _toggle_plot_dock_state(self) -> None:
        if self.plot_dock.isVisible():
            self.plot_dock.close()
        else:
            self._undock_plot_tab()
    
    def _create_undock_button(self) -> QPushButton:
        # Need to create button again because pointer is destroyed when tab is self.main_widget.tabs.removeTab(current_index)
        btn = QPushButton()
        btn.setIcon(IconBuilder.build(IconType.Docked))
        btn.setObjectName("undockTabButton")
        btn.setToolTip("Undock Plot Studio to side panel")
        btn.setFlat(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(24, 24)
        btn.clicked.connect(self._undock_plot_tab)
        return btn
        
    def _undock_plot_tab(self) -> None:
        """Removes the plot tab from the QTabWidget and places it into the QDockWidget."""
        current_index = self.main_widget.tabs.indexOf(self.main_widget.plot_tab)
        if current_index != -1:
            self.main_widget.tabs.removeTab(current_index)
            self.plot_dock.setWidget(self.main_widget.plot_tab)
            self.plot_dock.show()
            
            self.plot_dock.raise_()
            self.plot_dock.activateWindow()
            self.main_widget.plot_tab.setFocus()
    
    def _on_dock_visibility_changed(self, visible: bool) -> None:
        """Restores the plot widget back to a standard tab when the dock is closed."""
        if not visible and self.plot_dock.widget() == self.main_widget.plot_tab:
            self.plot_dock.setWidget(None)
            
            new_index = self.main_widget.tabs.addTab(self.main_widget.plot_tab, self.plot_tab_icon, self.plot_tab_text)
            self.main_widget.tabs.tabBar().setTabButton(new_index, QTabBar.ButtonPosition.RightSide, self._create_undock_button())
            self.main_widget.tabs.setCurrentIndex(new_index)
    
    def _connect_signals(self) -> None:
        """Routing signals to the main widget"""
        self.main_widget.window_title_changed.connect(self.setWindowTitle)
        self.main_widget.data_tab.request_python_console.connect(self.main_widget.open_python_console)
        self.main_widget.data_tab.request_open_settings.connect(self.open_settings)
        
        # Window state signals
        window_menu = self.menuBar().addMenu("&Window")
        window_menu.setProperty("styleClass", "dpsMenu")
        reset_layout_action = QAction("Reset Window Layout", self)
        reset_layout_action.setShortcut(QKeySequence("Ctrl+Shift+R"))
        reset_layout_action.setToolTip("Restores all docks and tabs to their default position")
        reset_layout_action.triggered.connect(self._reset_window_layout)
        window_menu.addAction(reset_layout_action)
        
        #File menu
        self.menu_bar.file_new.triggered.connect(self.main_widget.new_project)
        self.menu_bar.file_open.triggered.connect(self.main_widget.open_project)
        self.menu_bar.file_save.triggered.connect(self.main_widget.save_project)
        self.menu_bar.file_save_as.triggered.connect(self.main_widget.save_project_as)
        self.menu_bar.import_file.triggered.connect(self.main_widget.import_file)
        self.menu_bar.import_sheets.triggered.connect(self.main_widget.import_google_sheets)
        self.menu_bar.import_database.triggered.connect(self.main_widget.import_from_database)

        # Export menu
        self.menu_bar.export_code.triggered.connect(self.main_widget.export_code)
        self.menu_bar.export_logs.triggered.connect(self.main_widget.export_logs)
        self.menu_bar.export_data_action.triggered.connect(self.main_widget.export_data_dialog)
        self.menu_bar.export_sheets_action.triggered.connect(self.main_widget.export_google_sheets)

        # Edit menu
        self.menu_bar.undo_action.triggered.connect(self.main_widget.undo)
        self.menu_bar.redo_action.triggered.connect(self.main_widget.redo)
        self.menu_bar.python_console_action.triggered.connect(self.main_widget.open_python_console)

        # View menu
        self.menu_bar.zoom_in_action.triggered.connect(self.main_widget.zoom_in)
        self.menu_bar.zoom_out_action.triggered.connect(self.main_widget.zoom_out)

        # App level
        self.menu_bar.settings_action.triggered.connect(self.open_settings)
        self.menu_bar.about_action.triggered.connect(self.show_about)
        self.menu_bar.explore_help_action.triggered.connect(self.show_help_explorer)
    
    def _reset_window_layout(self) -> None:
        """Panic button for lost docks: returns the UI to a tabbed starting state."""
        self.plot_dock.close()
        self.plot_dock.setFloating(False)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.plot_dock)
        self.status_bar_widget.log("Window layout reset to default", "INFO")
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """Checks for unsaved changes before exiting"""
        
        def save_layout():
            """Helper to save UI state before the application teardown."""
            settings = QSettings("DataPlotStudio", "AppLayout")
            settings.setValue("geometry", self.saveGeometry())
            settings.setValue("windowState", self.saveState())
        
        if hasattr(self.main_widget, "unsaved_changes") and self.main_widget.unsaved_changes:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save the current project before exiting?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            if reply == QMessageBox.StandardButton.Save:
                if self.main_widget.save_project():
                    save_layout()
                    event.accept()
                else:
                    event.ignore()
            elif reply == QMessageBox.StandardButton.Discard:
                save_layout()
                event.accept()
            else:
                event.ignore()
        else:
            save_layout()
            event.accept()
    
    def open_settings(self) -> None:
        """Opens the settings dialog"""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            new_settings = dialog.get_settings()
            self.settings.update(new_settings)
            
            app_settings = QSettings("DataPlotStudio", "UserSettings")
            for key, value in self.settings.items():
                app_settings.setValue(key, value)
            self.apply_settings(self.settings)
            self.status_bar_widget.log("Settings updated", "INFO")
    
    def show_about(self) -> None:
        """Shows the About dialog box"""
        AboutDialog.show_about_dialog(
            parent=self,
            application_version=self.project_manager.APPLICATION_VERSION
        )

    def show_help_explorer(self) -> None:
        """
        Shows the Help Explorer dialog
        Can be viewed from anywhere and acts like an independent window
        """
        if self._help_explorer is None:
            self._help_explorer = HelpExplorerDialog(None)
            self._help_explorer.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self._help_explorer.show()
        self._help_explorer.raise_()
        self._help_explorer.activateWindow()
    
    def apply_settings(self, settings: dict) -> None:
        """Apply the settings to main app loop"""
        self._current_settings = settings
        font = QFont(settings["font_family"], settings["font_size"])
        QApplication.setFont(font)

        base_css: str = ""
        styles_dir: Path = Path(get_resource_path("ui/styles"))
        
        if settings["dark_mode"]:
            base_css = self.get_dark_theme()
        else:
            light_stylesheet_paths: list[Path] = []
            if styles_dir.exists() and styles_dir.is_dir():
                for css_file in styles_dir.rglob("*.css"):
                    if css_file.name != "dark_theme.css":
                        light_stylesheet_paths.append(css_file)
            base_css = self.load_stylesheets(light_stylesheet_paths)
        
        if QApplication.instance() is not None:
            QApplication.instance().setStyleSheet(base_css)
    
    def enable_live_reloader(self) -> None:
        styles_dir: Path = Path(get_resource_path("ui/styles"))
        self._style_reloader = StyleReloader(
            styles_dir=styles_dir,
            reload_callback=self.reload_styles,
            parent=self
        )
    
    def reload_styles(self) -> None:
        if not self._current_settings:
            return
        self.apply_settings(self._current_settings)
        self.status_bar_widget.log("Styles reloaded", "INFO")
    
    def get_dark_theme(self):
        dark_theme_path: Path = Path(get_resource_path("ui/styles/dark_theme.css"))
        return self.load_stylesheets([dark_theme_path])

    @classmethod
    def load_stylesheets(cls, absolute_paths: list[Path]) -> str:
        combined_css: str = ""
        for path in absolute_paths:
            if path.exists() and path.is_file():
                try:
                    combined_css += path.read_text(encoding="utf-8") + "\n"
                except Exception as err:
                    print(f"Failed to read stylesheet {path.name}: {err}")
        
        return combined_css