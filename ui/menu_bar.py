# ui/menu_bar.py
from PyQt6.QtWidgets import QMenuBar, QWidget
from PyQt6.QtGui import QAction, QIcon
from core.resource_loader import get_resource_path
from ui.widgets.ControlElements import DataPlotStudioMenu
from ui.icons import IconBuilder, IconType

class MenuBar(QMenuBar):
    """Custom menu bar for the application"""
    
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        
        # File Menu
        file_menu = DataPlotStudioMenu(self.tr("&File"), self)
        self.addMenu(file_menu)
        
        self.file_new = QAction(IconBuilder.build(IconType.NewProject),self.tr("&New Project"), parent)
        self.file_new.setShortcut("Ctrl+N")
        self.file_new.setToolTip(self.tr("Create a new project from scratch"))
        file_menu.addAction(self.file_new)
        
        self.file_open = QAction(IconBuilder.build(IconType.OpenProject), self.tr("&Open Project"), parent)
        self.file_open.setShortcut("Ctrl+O")
        self.file_open.setToolTip(self.tr("Open an exisiting project"))
        file_menu.addAction(self.file_open)
        
        self.file_save = QAction(IconBuilder.build(IconType.SaveProject), self.tr("&Save Project"), parent)
        self.file_save.setShortcut("Ctrl+S")
        self.file_save.setToolTip(self.tr("Save the current project"))
        file_menu.addAction(self.file_save)

        self.file_save_as = QAction(IconBuilder.build(IconType.SaveProjectAs), self.tr("Save Project As..."), parent)
        self.file_save_as.setShortcut("Ctrl+Shift+S")
        file_menu.addAction(self.file_save_as)
        
        file_menu.addSeparator()
        import_submenu: DataPlotStudioMenu = DataPlotStudioMenu(self.tr("&Import"), self)
        file_menu.addMenu(import_submenu)
        
        self.import_file = QAction(IconBuilder.build(IconType.ImportFile), self.tr("&Import from &Local File..."), parent)
        self.import_file.setShortcut("Ctrl+I")
        self.import_file.setToolTip(self.tr("Import data from a file on your computer"))
        import_submenu.addAction(self.import_file)
        
        self.import_sheets = QAction(IconBuilder.build(IconType.ImportGoogleSheets), self.tr("&Import from Google Sheets..."), parent)
        self.import_sheets.setToolTip(self.tr("Import data from Google Sheet"))
        import_submenu.addAction(self.import_sheets)

        self.import_database = QAction(IconBuilder.build(IconType.ImportDatabase), self.tr("Import from &Database..."), parent)
        self.import_database.setToolTip(self.tr("Import data from a database (SQLite, PostgreSQL, MySQL)"))
        import_submenu.addAction(self.import_database)
        
        file_menu.addSeparator()
        
        export_submenu: DataPlotStudioMenu = DataPlotStudioMenu(self.tr("&Export"), self)
        file_menu.addMenu(export_submenu)
        
        self.export_data_action = QAction(IconBuilder.build(IconType.ExportFle), self.tr("Export &Data..."), parent)
        self.export_data_action.setToolTip(self.tr("Export the current data view into a new file"))
        export_submenu.addAction(self.export_data_action)
        
        self.export_sheets_action = QAction(IconBuilder.build(IconType.ExportGoogleSheets), self.tr("Export to Google &Sheets..."), parent)
        self.export_sheets_action.setToolTip(self.tr("Export the current data directly to a cloud Google Sheet"))
        export_submenu.addAction(self.export_sheets_action)
        
        self.export_code = QAction(QIcon(get_resource_path("icons/menu_bar/python-5.svg")), self.tr("&Export to Python (.py) file..."), parent)
        self.export_code.setShortcut("Ctrl+E")
        self.export_code.setToolTip(self.tr("Export the data manipulation and plotting code to an external Python (.py) file"))
        export_submenu.addAction(self.export_code)
        
        self.export_logs = QAction(QIcon(get_resource_path("icons/menu_bar/export_log.png")), self.tr("&Export Log file..."), parent)
        self.export_logs.setToolTip(self.tr("Export the .log file to view the logging of your session"))
        export_submenu.addAction(self.export_logs)
        
        file_menu.addSeparator()
        
        self.exit_action = QAction(IconBuilder.build(IconType.Quit), self.tr("E&xit"), parent)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.setToolTip(self.tr("Exit the program"))
        self.exit_action.triggered.connect(parent.close)
        file_menu.addAction(self.exit_action)
        
        # Edit Menu
        edit_menu = DataPlotStudioMenu(self.tr("&Edit"), self)
        self.addMenu(edit_menu)
        
        self.undo_action = QAction(IconBuilder.build(IconType.Undo), self.tr("&Undo"), parent)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.setToolTip(self.tr("Undo the last action"))
        edit_menu.addAction(self.undo_action)
        
        self.redo_action = QAction(IconBuilder.build(IconType.Redo), self.tr("&Redo"), parent)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.setToolTip(self.tr("Redo the previous action"))
        edit_menu.addAction(self.redo_action)
        
        edit_menu.addSeparator()
        self.python_console_action = QAction(QIcon(get_resource_path("icons/menu_bar/python-5.svg")), self.tr("Python &Console"), parent)
        self.python_console_action.setShortcut("Ctrl+`")
        self.python_console_action.setToolTip(self.tr("Open the Python console for direct data manipulation of the DataFrame"))
        edit_menu.addAction(self.python_console_action)

        edit_menu.addSeparator()
        self.settings_action = QAction(IconBuilder.build(IconType.Settings), self.tr("&Settings"), parent)
        self.settings_action.setShortcut("Ctrl+,")
        self.settings_action.setToolTip(self.tr("Configure application preferences"))
        edit_menu.addAction(self.settings_action)
        
        # View Menu
        view_menu = DataPlotStudioMenu(self.tr("&View"), self)
        self.addMenu(view_menu)
        
        self.zoom_in_action = QAction(IconBuilder.build(IconType.ZoomIn), self.tr("Zoom &In"), parent)
        self.zoom_in_action.setShortcut("Ctrl++")
        self.zoom_in_action.setToolTip(self.tr("Zoom into the plot"))
        view_menu.addAction(self.zoom_in_action)
        
        self.zoom_out_action = QAction(IconBuilder.build(IconType.ZoomOut), self.tr("Zoom &Out"), parent)
        self.zoom_out_action.setShortcut("Ctrl+-")
        self.zoom_out_action.setToolTip(self.tr("Zoom out from the plot"))
        view_menu.addAction(self.zoom_out_action)
        
        # Help Menu
        help_menu = DataPlotStudioMenu(self.tr("&Help"), self)
        self.addMenu(help_menu)
        
        self.about_action = QAction(IconBuilder.build(IconType.Information), self.tr("&About"), parent)
        self.about_action.setToolTip(self.tr("View application information and version"))
        help_menu.addAction(self.about_action)
        
        self.explore_help_action = QAction(IconBuilder.build(IconType.Help), self.tr("Help Explorer"), parent)
        self.explore_help_action.setShortcut("F1")
        self.explore_help_action.setStatusTip("Open the Help Explorer menu")
        help_menu.addAction(self.explore_help_action)