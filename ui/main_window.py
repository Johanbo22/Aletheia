#ui/main_window.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFileDialog, QMessageBox, QApplication, QTabWidget)
from PyQt6.QtCore import QThreadPool, pyqtSlot, QTimer, pyqtSignal, QSettings
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from pathlib import Path
import traceback


from resources.version import APPLICATION_NAME, APPLICATION_VERSION, SCRIPT_FILE_NAME, LOG_FILE_NAME
from core.subset_manager import SubsetManager
from ui.workers import FileImportWorker, GoogleSheetsImportWorker
from ui.data_tab import DataTab
from ui.plot_tab import PlotTab
from ui.widgets.AutosaveIndicator import AutosaveIndicator
from core.data_handler import DataHandler
from core.project_manager import ProjectManager
from core.code_exporter import CodeExporter
from core.logger import Logger
from ui.status_bar import StatusBar
from ui.dialogs import (ProgressDialog, GoogleSheetsDialog, DatabaseConnectionDialog, ExportDialog, GoogleSheetsExportDialog, ConsoleDialog)
from ui.animations import (FileImportAnimation, FailedAnimation, SavedProjectAnimation, GoogleSheetsImportAnimation, DatabaseImportAnimation, ProjectOpenAnimation, ScriptLogExportAnimation, ExportFileAnimation)
from ui.icons import IconBuilder, IconType

class MainWindow(QWidget):
    """Main widget"""

    window_title_changed = pyqtSignal(str)
    
    def __init__(self, data_handler: DataHandler, project_manager: ProjectManager, code_exporter: CodeExporter, logger: Logger, status_bar: StatusBar):
        super().__init__()

        self.data_handler = data_handler
        self.project_manager = project_manager
        self.code_exporter = code_exporter
        self.logger = logger
        self.status_bar = status_bar
        
        self.subset_manager = SubsetManager()

        self.threadpool = QThreadPool()
        self.data_handler.memory_update_callback = self.status_bar.update_memory_usage

        self.progress_dialog: ProgressDialog | None = None
        self._temp_import_filepath: str | None = None
        self._temp_import_filesize: float = 0.0

        self.setAcceptDrops(True)

        self._unsaved_changes: bool = False
        self.init_ui()

        self._connect_subset_managers()
        
        # Setup of autosave timers
        self.autosave_interval_ms: int = 5 * 60 * 1000
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self._perform_autosave)
        self.autosave_timer.start(self.autosave_interval_ms)
        self.autosave_indicator = AutosaveIndicator(self)
        
        QTimer.singleShot(0, self._check_recovery)
    
    def init_ui(self) -> None:
        """Init the main ui"""
        layout = QVBoxLayout()

        # Creation of the main Tab widget
        self.tabs = QTabWidget()

        # Data tab
        data_icon = IconBuilder.build(IconType.DataExplorerIcon)
        data_explorer_name = "Data Explorer"
        self.data_tab = DataTab(self.data_handler, self.status_bar, self.subset_manager)

        # Welcome page signals
        self.data_tab.request_open_project.connect(self.open_project)
        self.data_tab.request_import_file.connect(self.import_file)
        self.data_tab.request_recent_project.connect(self.open_recent_project)
        self.data_tab.request_import_sheets.connect(self.import_google_sheets)
        self.data_tab.request_import_db.connect(self.import_from_database)
        self.data_tab.request_quit.connect(QApplication.instance().quit)
        self.data_tab.data_modified.connect(self._mark_as_unsaved)
        
        self.tabs.addTab(self.data_tab, data_icon, data_explorer_name)

        # Plot tab
        plot_icon = IconBuilder.build(IconType.PlotTabIcon)
        plot_tab_name = "Plot Studio"
        self.plot_tab = PlotTab(self.data_handler, self.status_bar)
        self.plot_tab.brush_selection_made.connect(self._on_brush_selection_made)
        self.tabs.addTab(self.plot_tab, plot_icon, plot_tab_name)

        layout.addWidget(self.tabs)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)
        
    @pyqtSlot(set)
    def _on_brush_selection_made(self, indices: set) -> None:
        """Handle the selection from PlotTab and hightlight data in the table"""
        if self.data_tab.data_table.model() is not None:
            self.data_tab.data_table.model().set_highlighted_rows(indices)
            
            data_tab_index = self.tabs.indexOf(self.data_tab)
            if self.tabs.currentIndex() != data_tab_index:
                self.tabs.setCurrentIndex(data_tab_index)
            
            if indices:
                first_index = min(indices)
                model_index = self.data_tab.data_table.model().index(first_index, 0)
                self.data_tab.data_table.scrollTo(model_index)
                self.status_bar.log(f"Highlighted {len(indices)} selected rows in Data Explorer", "SUCCESS")
    
    def _connect_subset_managers(self) -> None:
        """Connect the subset manager used in both DataTab and PlotTab"""
        self.plot_tab.set_subset_manager(self.subset_manager)
        self.data_tab.set_plot_tab(self.plot_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change events"""
        if self.tabs.widget(index) == self.plot_tab:
            self.plot_tab.refresh_subset_list()
    
    @pyqtSlot()
    def _perform_autosave(self) -> None:
        """
        Executes the autosave if there are unsaved changes
        """
        if self.unsaved_changes and self.data_handler.df is not None:
            self.autosave_indicator.show_indicator()
            QApplication.processEvents()
            self.project_manager.auto_save(self.get_project_data())
    
    @pyqtSlot()
    def _check_recovery(self) -> None:
        """
        Checks for an existing autosave file and
        prompts to recovery after a crash
        """
        if self.project_manager.has_autosave():
            reply = QMessageBox.question(
                self, 
                "Recover Project",
                "Last session was not existed properly. Would you like to recover the unsaved data?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    project_data = self.project_manager.recover_autosave()
                    self.load_project(project_data)
                    self.status_bar.log("Session recovered", "SUCCESS")
                    self.unsaved_changes = True
                except Exception as err:
                    QMessageBox.warning(self, "Recovery Failed", f"Could not recover the session: {str(err)}")
                    self.project_manager.cleanup_autosave()
            else:
                self.project_manager.cleanup_autosave()
        
            
    def _mark_as_unsaved(self) -> None:
        if self.data_handler.df is not None:
            self.unsaved_changes = True
    
    @property
    def unsaved_changes(self) -> bool:
        return self._unsaved_changes
    
    @unsaved_changes.setter
    def unsaved_changes(self, state: bool) -> None:
        self._unsaved_changes = state
        self._update_window_title()
    
    def _update_window_title(self) -> None:
        if self.data_handler.df is None:
            title = f"{APPLICATION_NAME} - v{APPLICATION_VERSION}"
        else:
            project_path = self.project_manager.get_current_project_path()
            if project_path:
                project_name = Path(project_path).name
                base_title = f"{APPLICATION_NAME} - {project_name}"
            else:
                base_title = f"{APPLICATION_NAME} - Untitled Project"
            
            indicator = " *" if self._unsaved_changes else ""
            title = f"{base_title}{indicator}"
        
        self.window_title_changed.emit(title)
        
        top_level = self.window()
        if top_level and top_level != self:
            top_level.setWindowTitle(title)
    
    def _update_recent_projects(self, filepath: str) -> None:
        if not filepath:
            return
        
        settings = QSettings(f"{APPLICATION_NAME}", "RecentProjects")
        recent_files = settings.value("recent_files", [])
        
        if isinstance(recent_files, str):
            recent_files = [recent_files]
        
        standardized_path = str(Path(filepath).absolute())
        
        if standardized_path in recent_files:
            recent_files.remove(standardized_path)
        
        recent_files.insert(0, standardized_path)
        recent_files = recent_files[:10]
        
        settings.setValue("recent_files", recent_files)

    def new_project(self):
        """Creates a new project"""
        if self._confirm_discard_changes():
            self.project_manager.new_project()
            self.project_manager.cleanup_autosave()
            self.clear_all()
            
            # Create an empty dataframe (0x0) to start the table view
            # Forces an update of the UI to switch from the welcome screen to project screen
            self.data_handler.create_empty_dataframe(0, 0)
            self.data_tab.refresh_data_view()
            self.unsaved_changes = False
            self.status_bar.log("New Project Created")
    
    def open_project(self) -> None:
        """Open an existing project"""
        if self._confirm_discard_changes():
            filepath, _ = QFileDialog.getOpenFileName(
                self,
                "Open Project",
                "",
                f"{APPLICATION_NAME} Portable Files (*{self.project_manager.PROJECT_EXTENSION})"
            )
            if filepath:
                self._load_project_from_path(filepath)
    
    def open_recent_project(self, filepath: str) -> None:
        if self._confirm_discard_changes():
            if Path(filepath).exists():
                self._load_project_from_path(filepath)
            else:
                QMessageBox.warning(self, "File Not Found", f"The project file could not be found:\n{filepath}")
    
    def _load_project_from_path(self, filepath: str) -> None:
        """Helper method to load project data and handle animations."""
        try:
            project = self.project_manager.load_project(filepath)
            self.load_project(project)
            self.status_bar.log(f"Project loaded: {filepath}")
            self._update_recent_projects(filepath)

            self.open_project_animation = ProjectOpenAnimation(message="Project Opened")
            self.open_project_animation.start(target_widget=self)
        
        except Exception as LoadProjectError:
            QMessageBox.critical(self, "Error", f"Failed to load project: {str(LoadProjectError)}")
            traceback.print_exc()
    
    def load_project(self, project_data: dict) -> None:
        """load project data into the UI"""
        if "data" in project_data and project_data["data"] is not None:
            self.data_handler.df = project_data["data"]
            self.data_handler.original_df = project_data["data"].copy()
            self.data_tab.refresh_data_view()
            self.plot_tab.update_column_combo()
            self.status_bar.update_data_stats(self.data_handler.df)
    
        if "plot_config" in project_data:
            self.plot_tab.load_config(project_data["plot_config"])
        
        if "subsets" in project_data and project_data["subsets"] is not None:
            self.subset_manager.import_subsets(project_data["subsets"])
            self.data_tab.controller.refresh_active_subsets()
            self.plot_tab.refresh_subset_list()
        
        # Automatically generate the plot based on the loaded configs
        self.plot_tab.generate_plot()
        
        self._unsaved_changes = False

    def save_project(self) -> bool:
        """Saves the current project"""
        return self._perform_save(force_dialog=False)
    
    def save_project_as(self) -> bool:
        """Saves current project as a new file"""
        return self._perform_save(force_dialog=True)
    
    def _perform_save(self, force_dialog: bool) -> bool:
        try:
            project_data = self.get_project_data()

            filepath = self.project_manager.get_current_project_path()
            if force_dialog or not filepath:
                filepath, _ = QFileDialog.getSaveFileName(
                    self,
                    "Save Project Package",
                    "",
                    f"{APPLICATION_NAME} Portable Files (*{self.project_manager.PROJECT_EXTENSION});;All Files (*)"
                )
                if not filepath:
                    return False
                
            saved_path = self.project_manager.save_project(project_data, filepath)

            self.saved_animation = SavedProjectAnimation("Project Saved", parent=None)
            self.saved_animation.start(target_widget=self)

            if saved_path:
                self._unsaved_changes = False
                self.project_manager.cleanup_autosave()
                op_name = "save_project_as" if force_dialog else "save_project"
                self.status_bar.log_action(f"Project Saved: {Path(saved_path).name}",details={"filepath": saved_path, "operation": op_name}, level="SUCCESS")
                self._update_recent_projects(saved_path)

                return True
            return False
        
        except Exception as SaveProjectError:
            if "cancelled" in str(SaveProjectError).lower():
                return False
            self.failed_operation_animation = FailedAnimation("Save failed", parent=None)
            self.failed_operation_animation.start(target_widget=self)
            QMessageBox.critical(self, "Save Error", f"Failed to save project: {str(SaveProjectError)}")
            self.status_bar.log(f"Save failed: {str(SaveProjectError)}", "ERROR")
            return False
    
    def get_project_data(self) -> dict:
        """Get the project data for saving"""
        return {
            "data": self.data_handler.df,
            "plot_config": self.plot_tab.get_config(),
            "subsets": self.subset_manager.export_subsets(),
            "metadata": {"version": APPLICATION_VERSION, "name": f"{APPLICATION_NAME} Project"}
        }
        
    def open_python_console(self) -> None:
        if self.data_handler.df is None:
            QMessageBox.warning(self, "Warning", "Please load data before opening the console.")
            return

        self.console_dialog = ConsoleDialog(self.data_handler, self._on_console_sync, self)
        self.console_dialog.show()
    
    def _on_console_sync(self) -> None:
        self.data_tab.refresh_data_view()
        self.plot_tab.update_column_combo()
        self.unsaved_changes = True
        self.status_bar.update_data_stats(self.data_handler.df)
    
    def clear_all(self) -> None:
        """Clear all data"""
        self.data_handler.df = None
        self.data_handler.original_df = None
        self.data_tab.clear()
        self.plot_tab.clear()
        self.subset_manager.subsets.clear()
        self.subset_manager.clear_cache()
        self.data_tab.controller.refresh_active_subsets()
        self.plot_tab.refresh_subset_list()
        self.status_bar.update_data_stats(None)
    
    def _confirm_discard_changes(self) -> bool:
        """Returns True if its safe to proceed, False if not"""
        if self._unsaved_changes:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Do you want to save before proceeding?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            if reply == QMessageBox.StandardButton.Save:
                return self.save_project()
            elif reply == QMessageBox.StandardButton.Cancel:
                return False
        
        return True

    def closeEvent(self, event) -> None:
        if self._confirm_discard_changes():
            self.project_manager.cleanup_autosave()
            event.accept()
        else:
            event.ignore()
    
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "autosave_indicator") and self.autosave_indicator.isVisible():
            self.autosave_indicator.move(self.rect().width() - self.autosave_indicator.width() - 20, 20)
    
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle the drag event for filre imports"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                filepath = Path(urls[0].toLocalFile())
                valid_extensions = {".csv", ".xlsx", ".xls", ".txt", ".json", ".geojson", ".shp", ".gpkg"}
                if filepath.suffix.lower() in valid_extensions:
                    event.accept()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle the dropped event as import file"""
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            filepath = urls[0].toLocalFile()
            self.load_file_from_path(filepath)
    
    def load_file_from_path(self, filepath: str) -> None:
        """Process and import file from a path string"""
        path = Path(filepath)
        file_size_kb = path.stat().st_size / 1024
        self._temp_import_filepath = filepath
        self._temp_import_filesize = file_size_kb

        self.status_bar.show_progress(True)
        self.status_bar.set_progress(0)

        self.progress_dialog = None
        if file_size_kb > 500:
            self.progress_dialog = ProgressDialog(
                title="Importing data", message=f"Loading {path.name}...", parent=self
            )
            self.progress_dialog.show()
            self.progress_dialog.update_progress(10, "Reading file")
        else:
            self.status_bar.log(f"Importing. {filepath}...")
        
        worker = FileImportWorker(self.data_handler, filepath)
        worker.signals.finished.connect(self._on_import_finished)
        worker.signals.error.connect(self._on_import_error)
        worker.signals.progress.connect(self._on_import_progress)

        self.import_file_animation = FileImportAnimation(parent=None, message="Imported File")
        self.import_file_animation.start(target_widget=self)
        self.threadpool.start(worker)
    
    def import_file(self) -> None:
        """Import a data file"""
        geospatial_filter = "Geospatial Files (*.geojson *.shp *gpkg)"
        data_filter = "Data Files (*.csv *.xlsx *.xls *.txt *.json)"
        all_files_filter = "All Files (*)"
        file_filter = f"{data_filter};;{geospatial_filter};;{all_files_filter}"
        
        filepath, _ = QFileDialog.getOpenFileName(self, "Import Data File", "", file_filter)
        if filepath:
            self.load_file_from_path(filepath)
    
    @pyqtSlot(int, str)
    def _on_import_progress(self, percentage: int, message: str) -> None:
        self.status_bar.set_progress(percentage)
        if self.progress_dialog:
            self.progress_dialog.update_progress(percentage, message)
            QApplication.processEvents()
    
    @pyqtSlot(object)
    def _on_import_finished(self, loaded_dataframe) -> None:
        self.status_bar.show_progress(False)
        if self.progress_dialog:
            self.progress_dialog.update_progress(90, "Updating Interface")
        self.data_tab.refresh_data_view()
        self.plot_tab.update_column_combo()
        self._unsaved_changes = True
        self.status_bar.update_data_stats(loaded_dataframe)
        
        self.tabs.setCurrentWidget(self.data_tab)

        if self.progress_dialog:
            self.progress_dialog.update_progress(100, "Complete")
            QTimer.singleShot(300, self.progress_dialog.accept)
            self.progress_dialog = None
        
        path = Path(self._temp_import_filepath)
        self.status_bar.log_action(f"Imported {path.name}", level="SUCCESS", details={"filename": path.name, "rows": loaded_dataframe.shape[0],"columns": loaded_dataframe.shape[1]})
        self._temp_import_filepath = None
    
    @pyqtSlot(Exception)
    def _on_import_error(self, error: Exception) -> None:
        self.status_bar.show_progress(False)
        if self.progress_dialog:
            self.progress_dialog.accept()
            self.progress_dialog = None
        QMessageBox.critical(self, "Error", f"Failed to import file: {str(error)}")
        self.status_bar.log(f"Import failed: {str(error)}", "ERROR")
        self._temp_import_filepath = None

    def import_google_sheets(self) -> None:
        """Import from Google Sheets"""
        try:
            dialog = GoogleSheetsDialog(self)
            if dialog.exec():
                inputs = dialog.get_inputs()
                gid = None
                if len(inputs) == 6:
                    sheet_id, sheet_name, delimiter, decimal, thousands, gid = inputs
                elif len(inputs) == 5:
                    sheet_id, sheet_name, delimiter, decimal, thousands = inputs
                else:
                    if len(inputs) >= 2:
                        sheet_id, sheet_name = inputs[0], inputs[1]
                        delimiter, decimal, thousands = ",", ".", None
                    else:
                        QMessageBox.warning(self, "Error", "Invalid input from dialog")
                        return
                
                if not sheet_id and not sheet_name:
                    QMessageBox.warning(self, "Input Error", "Sheet ID is required")
                    return
                
                self.status_bar.show_progress(True)
                self.status_bar.set_progress(0)

                display_name = sheet_name if sheet_name else f"Sheet (GID: {gid})"
                
                self.progress_dialog = ProgressDialog(title="Importing from Google Sheets", message=f"Connecting to {display_name}...", parent=self)
                self.progress_dialog.show()

                worker = GoogleSheetsImportWorker(self.data_handler, sheet_id, sheet_name, delimiter, decimal, thousands, gid)
                worker.signals.progress.connect(self._on_import_progress)
                worker.signals.finished.connect(lambda df: self._on_google_sheet_import_finished(df, display_name))
                worker.signals.error.connect(self._on_import_error)
                self.threadpool.start(worker)
        
        except Exception as OpenGoogleSheetDialogError:
            QMessageBox.critical(self, "Error", f"Failed to open Google Sheets Import Dialog: {str(OpenGoogleSheetDialogError)}")
            traceback.print_exc()
    
    @pyqtSlot(object, str)
    def _on_google_sheet_import_finished(self, loaded_dataframe, sheet_name) -> None:
        self.status_bar.show_progress(False)
        if self.progress_dialog:
            self.progress_dialog.update_progress(90, "Updating Interface")
        self.data_tab.refresh_data_view()
        self.plot_tab.update_column_combo()
        self._unsaved_changes = True

        self.status_bar.update_data_stats(loaded_dataframe)
        
        self.tabs.setCurrentWidget(self.data_tab)

        if self.progress_dialog:
            self.progress_dialog.update_progress(100, "Complete")
            QTimer.singleShot(300, self.progress_dialog.accept)
            self.progress_dialog = None
        
        self.status_bar.log_action(
            f"Imported Google Sheet document: {sheet_name}", level="SUCCESS",
            details={
                "sheet_name": sheet_name, "rows": loaded_dataframe.shape[0], "columns": loaded_dataframe.shape[1]
            }
        )
        self.google_sheets_import_animation = GoogleSheetsImportAnimation(parent=None, message="Google Sheet Import")
        self.google_sheets_import_animation.start(target_widget=self)
    
    def import_from_database(self) -> None:
        """Import data from a database connection"""
        try:
            dialog = DatabaseConnectionDialog(self)
            if dialog.exec():
                db_type, connection_string, query = dialog.get_details()
                if not connection_string or not query:
                    QMessageBox.warning(self, "Input Error", "Invalid connection details or query")
                    return
                
                self.status_bar.show_progress(True)
                self.status_bar.set_progress(10)
                
                self.progress_dialog = ProgressDialog(title=f"Importing from {db_type}", message="Connecting...", parent=self)
                self.progress_dialog.show()
                self.progress_dialog.update_progress(10, "Connecting...")
                QApplication.processEvents()

                self.data_handler.import_from_database(connection_string, query)

                self.status_bar.set_progress(90)

                self.progress_dialog.update_progress(90, "Updating Interface")
                self.data_tab.refresh_data_view()
                self.plot_tab.update_column_combo()
                self._unsaved_changes = True
                self.status_bar.update_data_stats(self.data_handler.df)

                self.status_bar.set_progress(100)
                self.status_bar.show_progress(False)

                self.progress_dialog.update_progress(100, "Complete")
                QTimer.singleShot(300, self.progress_dialog.accept)
                self.progress_dialog = None

                self.status_bar.log_action(f"Imported from {db_type} database", level="SUCCESS", details={"db_type": db_type, "rows": self.data_handler.df.shape[0]})
                self.import_database_animation = DatabaseImportAnimation(parent=None, message="Database Import", db_type=db_type)
                self.import_database_animation.start(target_widget=self)
        
        except Exception as ImportDatabaseError:
            if self.progress_dialog:
                self.progress_dialog.accept()
                self.progress_dialog = None
            QMessageBox.critical(self, "Import Error", f"Failed to import from database:\n\n{str(ImportDatabaseError)}")
            traceback.print_exc()
    
    def export_code(self) -> None:
        """Export data manipulation and plotting code"""
        if self.data_handler.df is None:
            QMessageBox.warning(
                self,
                "Warning",
                "No data loaded. Please load data first"
            )
            return
        
        source_info = self.data_handler.get_data_source()
        data_filepath = source_info.get("file_path")
        is_temp = source_info.get("is_temp_file", False)

        if not data_filepath:
            QMessageBox.warning(
                self,
                "Warning",
                "No data source filepath found"
            )
            return
        
        if is_temp:
            if QMessageBox.question(
                self,
                "Google Sheet Source",
                "Data source is temporary. Continue?",QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Cancel:
                return
        
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Export code")
        dialog.setText("What would you like to export?")
        button_data = dialog.addButton("Data Only", QMessageBox.ButtonRole.YesRole)
        button_plot = dialog.addButton("Data + Plot", QMessageBox.ButtonRole.NoRole)
        dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()

        plot_config = {}
        export_type = ""
        if dialog.clickedButton() == button_data:
            export_type = "Data Only"
        elif dialog.clickedButton() == button_plot:
            export_type = "Data + Plot"
            plot_config = self.plot_tab.get_config()
        else:
            return
        
        filepath, _ = QFileDialog.getSaveFileName(self, "Export as Python Script", f"{SCRIPT_FILE_NAME}.py", "Python Files (*.py)")
        if filepath:
            try:
                script = self.code_exporter.generate_full_script(
                    df=self.data_handler.df,
                    data_filepath=str(data_filepath),
                    source_info=source_info,
                    data_operations=self.data_handler.operation_log,
                    plot_config=plot_config,
                    export_type=export_type
                )
                with open(filepath, "w", encoding="utf-8") as script_file:
                    script_file.write(script)
                
                self.status_bar.log_action(f"Exported script: {Path(filepath).name}", level="SUCCESS", details={"type": export_type})
                QMessageBox.information(self, "Success", f"Script exported to {filepath}")
                self.python_export_animation = ScriptLogExportAnimation(parent=self, message="Script Exported", operation_type="python")
                self.python_export_animation.start(target_widget=self)
            except Exception as ExportPythonScriptError:
                QMessageBox.critical(self, "Error", f"Failed to export code: {str(ExportPythonScriptError)}")
                traceback.print_exc()
    
    def export_logs(self) -> None:
        """Export session log"""
        filepath, _ = QFileDialog.getSaveFileName(self, "Export Log", f"{LOG_FILE_NAME}.log", "Log Files (*.log);;Text Files (*.txt)")
        if filepath:
            try:
                detailed = QMessageBox.question(
                    self,
                    "Export Log",
                    "Include detailed timestamps?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes
                self.logger.export_logs(filepath, detailed)
                self.status_bar.log(f"Log exported to {filepath}")
                self.export_log_animation = ScriptLogExportAnimation(parent=self, message="Logs Exported", operation_type="log")
                self.export_log_animation.start(target_widget=self)

            except Exception as ExportLogError:
                QMessageBox.critical(self, "Error", f"Failed to export log: {str(ExportLogError)}")
                traceback.print_exc()
    
    def export_data_dialog(self) -> None:
        """Export the dataframe to a new file"""
        if self.data_handler.df is None:
            QMessageBox.warning(self, "Warning", "No Data to export")
            return

        selected_rows, selected_cols = self.data_tab.get_selection_state()
        dialog = ExportDialog(self, data_handler=self.data_handler, selected_rows=selected_rows, selected_columns=selected_cols)
        if dialog.exec():
            config = dialog.get_export_config()
            if config["filepath"]:
                try:
                    self.status_bar.log(f"Export complete to {config['filepath']}")
                    if not config.get("to_clipboard", False):
                        self.export_animation = ExportFileAnimation(parent=self, message="Export complete", extension=config["format"])
                        self.export_animation.start(target_widget=self)
                except Exception as ExportDataError:
                    QMessageBox.critical(self, "Error", f"Failed to export data: {str(ExportDataError)}")
                    traceback.print_exc()
    
    def export_google_sheets(self) -> None:
        if self.data_handler.df is None:
            QMessageBox.warning(self, "Warning", "No data loaded. Please load data before attempting an export.")
            return
        
        dialog = GoogleSheetsExportDialog(self)
        if dialog.exec():
            credentials_path, sheet_id, sheet_name = dialog.get_inputs()
            
            self.status_bar.show_progress(True)
            self.status_bar.set_progress(20)
            self.progress_dialog = ProgressDialog(
                title="Google Sheets Export", 
                message="Authenticating and uploading data...", 
                parent=self
            )
            self.progress_dialog.show()
            QApplication.processEvents()
            try:
                success: bool = self.data_handler.export_google_sheets(
                    credentials_path=credentials_path,
                    sheet_id=sheet_id,
                    sheet_name=sheet_name
                )
                if success:
                    self.status_bar.set_progress(100)
                    self.progress_dialog.update_progress(100, "Upload Complete")
                    QMessageBox.information(self, "Export Successful", f"Data was successfully pushed to worksheet: '{sheet_name}'.")
                    self.status_bar.log_action("Exported data to Google Sheets", level="SUCCESS", details={"sheet_id": sheet_id})
            
            except Exception as ExportSheetsError:
                QMessageBox.critical(self, "Export Error", f"An error occurred during export:\n\n{str(ExportSheetsError)}")
                traceback.print_exc()
            finally:
                self.status_bar.show_progress(False)
                if self.progress_dialog:
                    self.progress_dialog.accept()
                    self.progress_dialog = None
    
    def undo(self) -> None:
        if self.data_handler.undo():
            self.data_tab.refresh_data_view()
            self.status_bar.log("Undo: Previous state restored")
        else:
            self.status_bar.log("Nothing to undo")
    
    def redo(self) -> None:
        if self.data_handler.redo():
            self.data_tab.refresh_data_view()
            self.status_bar.log("Redo: Action restored")
        else:
            self.status_bar.log("Nothing to redo")
    
    def zoom_in(self) -> None:
        if self.tabs.currentWidget() != self.plot_tab:
            QMessageBox.information(self, "Info", "Zoom only works in Plot Studio")
            return
        
        fig = self.plot_tab.plot_engine.current_figure
        w, h = fig.get_size_inches()
        fig.set_size_inches(min(w * 1.1, 20), min(h * 1.1, 20))
        self.plot_tab.canvas.draw()
        self.status_bar.log("Zoomed in")
    
    def zoom_out(self) -> None:
        if self.tabs.currentWidget() != self.plot_tab:
            QMessageBox.information(self, "Info", "Zoom only works in Plot Studio")
            return
        
        fig = self.plot_tab.plot_engine.current_figure
        w, h = fig.get_size_inches()
        fig.set_size_inches(max(w * 0.9, 4), max(h * 0.9, 3))
        self.plot_tab.canvas.draw()
        self.status_bar.log("Zoomed out")