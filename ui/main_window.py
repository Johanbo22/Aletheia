# ui/main_window.py
import json
from pathlib import Path

from PyQt6.QtCore import QSettings, QThreadPool, QTimer, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (QApplication, QFileDialog, QMessageBox, QTabWidget, QVBoxLayout, QWidget)

from controller.toast_manager import ToastManager
from core.code_exporter import CodeExporter
from core.data_handler import DataHandler
from core.global_signals import global_signals
from core.logger import Logger
from core.project_manager import ProjectManager
from core.subset_manager import SubsetManager
from icons import IconBuilder, IconType
from resources.version import APPLICATION_NAME, APPLICATION_VERSION, LOG_FILE_NAME, SCRIPT_FILE_NAME
from ui.animations import (DatabaseImportAnimation, FailedAnimation, FileImportAnimation, GoogleSheetsImportAnimation,
                           ScriptLogExportAnimation)
from ui.data_tab import DataTab
from ui.dialogs import (ConsoleDialog, DatabaseConnectionDialog, GoogleSheetsDialog, GoogleSheetsExportDialog,
                        ProgressDialog)
from ui.plot_tab import PlotTab
from ui.status_bar import LogLevel, StatusBar
from ui.widgets.AutosaveIndicator import AutosaveIndicator
from ui.widgets.ToastNotification import ToastLevel
from ui.workers import FileImportWorker, GoogleSheetsImportWorker

class MainWindow(QWidget):
    """Main widget"""

    window_title_changed = pyqtSignal(str)

    def __init__(self, data_handler: DataHandler, project_manager: ProjectManager, code_exporter: CodeExporter,
                 logger: Logger, status_bar: StatusBar):
        super().__init__()

        self.data_handler = data_handler
        self.project_manager = project_manager
        self.code_exporter = code_exporter
        self.logger = logger
        self.status_bar = status_bar

        self.subset_manager = SubsetManager()

        self.threadpool = QThreadPool.globalInstance()
        self.data_handler.memory_update_callback = self.status_bar.update_memory_usage

        self.progress_dialog: ProgressDialog | None = None
        self._temp_import_filepath: str | None = None
        self._temp_import_filesize: float = 0.0

        self.setAcceptDrops(True)

        self._unsaved_changes: bool = False
        self.init_ui()

        self._connect_subset_managers()

        # Setup of autosave timers
        self.autosave_enabled: bool = True
        self.autosave_interval_ms: int = 5 * 60 * 1000
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self._perform_autosave)
        self.autosave_timer.start(self.autosave_interval_ms)
        self.autosave_indicator = AutosaveIndicator(self)

        QTimer.singleShot(0, self._check_recovery)
        self.toast_manager = ToastManager(self)
        global_signals.toast_requested.connect(self.show_toast)
        global_signals.log_requested.connect(self.status_bar.log)

    def show_toast(self, title: str, message: str, level: ToastLevel = ToastLevel.INFO,
                   duration_ms: int = 4000) -> None:
        """
        Public method to dispatch toast notifications safely.
        Components should use signals connected to this slot rather than
        instantiating toasts themselves.
        """
        self.toast_manager.show_toast(title, message, level, duration_ms)

    def apply_autosave_settings(self, settings: dict) -> None:
        """
        Applies system-level configurations related to autosaving to the main loop
        """
        self.autosave_enabled = settings.get("enable_autosave", True)
        interval_minutes = settings.get("autosave_interval", 5)

        self.autosave_interval_ms = interval_minutes * 60 * 1000
        if self.autosave_enabled:
            self.autosave_timer.start(self.autosave_interval_ms)
        else:
            self.autosave_timer.stop()
            self.project_manager.cleanup_autosave()

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
        self.data_tab.request_switch_to_plot.connect(lambda: self.tabs.setCurrentWidget(self.plot_tab))

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
        self._update_tab_visibility()

    def _update_tab_visibility(self) -> None:
        """Hides the tab bar if no data is loaded"""
        has_data = self.data_handler.df is not None
        self.tabs.tabBar().setVisible(has_data)

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
                self.status_bar.log(f"Highlighted {len(indices)} selected rows in Data Explorer", LogLevel.SUCCESS)

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
        if not getattr(self, "autosave_enabled", True):
            return
        if self.unsaved_changes and self.data_handler.df is not None:
            try:
                self.autosave_indicator.show_indicator()
                QApplication.processEvents()
                self.project_manager.auto_save(self.get_project_data())
            except Exception as e:
                self.status_bar.log(f"Autosave failed: {str(e)}", LogLevel.ERROR)
            finally:
                QApplication.processEvents()

    @pyqtSlot()
    def _check_recovery(self) -> None:
        """
        Checks for an existing autosave file and
        prompts to recovery after a crash
        """
        if self.project_manager.has_autosave():
            reply_box = QMessageBox(self)
            reply_box.setWindowTitle("Recover Project")
            reply_box.setText("It looks like the application closed unexpectedly during your last session.")
            reply_box.setInformativeText("Would you like to recover your unsaved work?")
            reply_box.setIcon(QMessageBox.Icon.Information)

            recover_btn = reply_box.addButton("Recover Session", QMessageBox.ButtonRole.AcceptRole)
            discard_btn = reply_box.addButton("Discard Autosave", QMessageBox.ButtonRole.DestructiveRole)
            reply_box.setDefaultButton(recover_btn)
            reply_box.exec()

            if reply_box.clickedButton() == recover_btn:
                try:
                    project_data = self.project_manager.recover_autosave()
                    self.load_project(project_data)
                    self.status_bar.log("Session recovered", LogLevel.SUCCESS)
                    self.show_toast("Session Recovered", "Project recovered from latest autosave", ToastLevel.SUCCESS)
                    self.unsaved_changes = True
                except Exception as err:
                    self.show_toast(
                        "Recovery Failed",
                        "The session data could not be recovered.\nThe corrupted autosave will be deleted",
                        ToastLevel.ERROR
                    )
                    self.status_bar.log(f"Session data could not be recovered: {str(err)}", LogLevel.ERROR)
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
                source_info = self.data_handler.get_data_source()
                if source_info and source_info.get("file_path"):
                    file_name = Path(source_info.get("file_path")).name
                    base_title = f"{APPLICATION_NAME} - {file_name} (Unsaved Project)"
                elif source_info and source_info.get("type") == "google_sheets":
                    sheet_name = source_info.get("sheet_name", "Unknown Sheet")
                    base_title = f"{APPLICATION_NAME} - {sheet_name} (Google Sheets)"
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
        elif isinstance(recent_files, tuple):
            recent_files = list(recent_files)
        elif isinstance(recent_files, list):
            recent_files = list(recent_files) if recent_files else []

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
            self._update_tab_visibility()

    def open_project(self) -> None:
        """Open an existing project"""
        if self._confirm_discard_changes():
            settings = QSettings(f"{APPLICATION_NAME}", "Preferences")
            last_dir = settings.value("last_project_dir", "")
            filepath, _ = QFileDialog.getOpenFileName(
                self,
                "Open Project",
                last_dir,
                f"{APPLICATION_NAME} Portable Files (*{self.project_manager.PROJECT_EXTENSION})"
            )
            if filepath:
                settings.setValue("last_project_dir", str(Path(filepath).parent))
                self._load_project_from_path(filepath)

    def open_recent_project(self, filepath: str) -> None:
        if self._confirm_discard_changes():
            if Path(filepath).exists():
                self._load_project_from_path(filepath)
            else:
                self.show_toast(
                    "File Not Found", "The project file could not be found", ToastLevel.WARNING
                )

    def _load_project_from_path(self, filepath: str) -> None:
        """Helper method to load project data and handle animations."""
        try:
            project = self.project_manager.load_project(filepath)
            self.load_project(project)
            self.status_bar.log(f"Project loaded: {filepath}", LogLevel.SUCCESS)
            self._update_recent_projects(filepath)

            self.show_toast("Project Opened", "Project loaded", ToastLevel.SUCCESS)

        except Exception as LoadProjectError:
            self.show_toast("Load Project Error", "Failed to load project from file", ToastLevel.ERROR)
            self.status_bar.log(f"Failed to load project: {str(LoadProjectError)}", LogLevel.ERROR)

    def load_project(self, project_data: dict) -> None:
        """Load project data into the UI"""
        metadata = project_data.get("metadata", {})
        source_info_json = metadata.get("data_source_info")

        if source_info_json:
            try:
                source_info = json.loads(source_info_json)
                self.data_handler._io.set_data_source_info(source_info)
            except Exception as error:
                self.status_bar.log(f"Warning: Could not restore data source info: {str(error)}", LogLevel.ERROR)

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
        self.plot_tab.generation_manager.generate_plot()

        self._unsaved_changes = False
        self._update_tab_visibility()

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

            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            saved_path = self.project_manager.save_project(project_data, filepath)
            QApplication.processEvents()

            self.show_toast("Project saved", f"Project saved to {filepath}", ToastLevel.SUCCESS)

            if saved_path:
                self._unsaved_changes = False
                self.project_manager.cleanup_autosave()
                op_name = "save_project_as" if force_dialog else "save_project"
                self.status_bar.log_action(f"Project Saved: {Path(saved_path).name}",
                                           details={"filepath": saved_path, "operation": op_name},
                                           level=LogLevel.SUCCESS)
                self._update_recent_projects(saved_path)

                return True
            return False

        except Exception as SaveProjectError:
            if "cancelled" in str(SaveProjectError).lower():
                return False
            FailedAnimation("Save failed", parent=None).start(target_widget=self)
            self.show_toast(
                "Save Project Error", "Failed to save project", ToastLevel.ERROR
            )
            self.status_bar.log(f"Save failed: {str(SaveProjectError)}", LogLevel.ERROR)
            return False
        finally:
            QApplication.restoreOverrideCursor()

    def get_project_data(self) -> dict:
        """Get the project data for saving"""
        source_info = self.data_handler.get_data_source()
        return {
            "data"       : self.data_handler.df,
            "plot_config": self.plot_tab.get_config(),
            "subsets"    : self.subset_manager.export_subsets(),
            "metadata"   : {
                "version"         : APPLICATION_VERSION,
                "name"            : f"{APPLICATION_NAME} Project",
                "data_source_info": json.dumps(source_info),

            }
        }

    def open_python_console(self) -> None:
        if self.data_handler.df is None:
            self.show_toast(
                "No Data", "Please load data before opening the console window", ToastLevel.WARNING
            )
            return

        if hasattr(self, "console_dialog") and self.console_dialog is not None and self.console_dialog.isVisible():
            self.console_dialog.raise_()
            self.console_dialog.activateWindow()

        self.console_dialog = ConsoleDialog(self.data_handler, self._on_console_sync, self)
        self.console_dialog.show()

    def _on_console_sync(self) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.data_tab.refresh_data_view()
            self.plot_tab.update_column_combo()
            self.unsaved_changes = True
            self.status_bar.update_data_stats(self.data_handler.df)
            self._update_tab_visibility()
            self.show_toast("Console Sync", "Workspace synchronized with console state", ToastLevel.INFO, 3000)
        finally:
            QApplication.restoreOverrideCursor()

    def clear_all(self) -> None:
        """Clear all data"""
        if self.data_handler.df is not None:
            if self._unsaved_changes:
                if not self._confirm_discard_changes():
                    return
            else:
                reply_box = QMessageBox(self)
                reply_box.setWindowTitle("Confirm Clear Workspace")
                reply_box.setText("Are you sure you want to clear all data, subsets, and plot configurations?")
                reply_box.setInformativeText("This action cannot be undone")
                reply_box.setIcon(QMessageBox.Icon.Warning)
                reply_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                reply_box.setDefaultButton(QMessageBox.StandardButton.No)
                reply = reply_box.exec()

                if reply == QMessageBox.StandardButton.No:
                    return

        self.data_handler.df = None
        self.data_handler.original_df = None
        self.data_tab.clear()
        self.plot_tab.clear()
        self.subset_manager.subsets.clear()
        self.subset_manager.clear_cache()
        self.data_tab.controller.refresh_active_subsets()
        self.plot_tab.refresh_subset_list()
        self.status_bar.update_data_stats(None)
        self._update_tab_visibility()

        self.unsaved_changes = False
        self.status_bar.log("Workspace cleared", LogLevel.INFO)

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
        """
        Handle the drag enter event for file imports and project loading
        """
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                filepath = Path(urls[0].toLocalFile())
                valid_extensions = {".csv", ".xlsx", ".xls", ".txt", ".json", ".geojson", ".shp", ".gpkg"}

                project_ext = self.project_manager.PROJECT_EXTENSION.lower()
                valid_extensions.add(project_ext)

                if filepath.suffix.lower() in valid_extensions:
                    self.activateWindow()
                    event.setDropAction(Qt.DropAction.CopyAction)
                    event.accept()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle the dropped event as import file"""
        if not self._confirm_discard_changes():
            event.ignore()
            return

        urls = event.mimeData().urls()
        if urls:
            if len(urls) > 1:
                self.show_toast(
                    "Multiple Files Dropped",
                    "Only the first file will be loaded",
                    ToastLevel.INFO
                )

            if urls[0].isLocalFile():
                filepath = urls[0].toLocalFile()
                path_obj = Path(filepath)
                project_ext = self.project_manager.PROJECT_EXTENSION.lower()

                if path_obj.suffix.lower() == project_ext:
                    self._load_project_from_path(filepath)
                else:
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

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

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

        settings = QSettings(f"{APPLICATION_NAME}", "Preferences")
        last_dir = settings.value("last_import_dir", "")

        filepath, _ = QFileDialog.getOpenFileName(self, "Import Data File", last_dir, file_filter)
        if filepath:
            settings.setValue("last_import_dir", str(Path(filepath).parent))
            self.load_file_from_path(filepath)

    @pyqtSlot(int, str)
    def _on_import_progress(self, percentage: int, message: str) -> None:
        self.status_bar.set_progress(percentage)
        if self.progress_dialog:
            self.progress_dialog.update_progress(percentage, message)
            QApplication.processEvents()

    @pyqtSlot(object)
    def _on_import_finished(self, loaded_dataframe) -> None:
        QApplication.restoreOverrideCursor()
        self.status_bar.show_progress(False)
        if self.progress_dialog:
            self.progress_dialog.update_progress(90, "Updating Interface")
        self.data_tab.refresh_data_view()
        self.plot_tab.update_column_combo()
        self._unsaved_changes = True
        self.status_bar.update_data_stats(loaded_dataframe)
        self._update_tab_visibility()

        self.tabs.setCurrentWidget(self.data_tab)

        if self.progress_dialog:
            self.progress_dialog.update_progress(100, "Complete")
            QTimer.singleShot(300, self.progress_dialog.accept)
            self.progress_dialog = None

        path = Path(self._temp_import_filepath)
        self.status_bar.log_action(f"Imported {path.name}", level="SUCCESS",
                                   details={"filename": path.name, "rows": loaded_dataframe.shape[0],
                                            "columns" : loaded_dataframe.shape[1]})
        self._temp_import_filepath = None

    @pyqtSlot(Exception)
    def _on_import_error(self, error: Exception) -> None:
        QApplication.restoreOverrideCursor()
        self.status_bar.show_progress(False)
        if self.progress_dialog:
            self.progress_dialog.accept()
            self.progress_dialog.deleteLater()
            self.progress_dialog = None

        self.show_toast("Error", "Failed to import file", ToastLevel.ERROR)
        self.status_bar.log(f"Import failed: {str(error)}", LogLevel.ERROR)
        self._temp_import_filepath = None

    def import_google_sheets(self) -> None:
        """Import from Google Sheets"""
        try:
            dialog = GoogleSheetsDialog(self)
            if dialog.exec():
                config = dialog.get_inputs()

                sheet_id = config.sheet_id
                sheet_name = config.sheet_name
                delimiter = config.delimiter
                decimal = config.decimal_separator
                thousands = config.thousands_separator
                gid = config.gid

                self.status_bar.show_progress(True)
                self.status_bar.set_progress(0)

                display_name = sheet_name if sheet_name else f"Sheet (GID: {gid})"

                self.progress_dialog = ProgressDialog(title="Importing from Google Sheets",
                                                      message=f"Connecting to {display_name}...", parent=self)
                self.progress_dialog.show()

                worker = GoogleSheetsImportWorker(self.data_handler, sheet_id, sheet_name, delimiter, decimal,
                                                  thousands, gid)
                worker.signals.progress.connect(self._on_import_progress)
                worker.signals.finished.connect(lambda df: self._on_google_sheet_import_finished(df, display_name))
                worker.signals.error.connect(self._on_import_error)
                self.threadpool.start(worker)

        except Exception as OpenGoogleSheetsDialogError:
            self.show_toast(
                "Error", "Failed to open Google Sheets Import Dialog", ToastLevel.ERROR
            )
            self.status_bar.log(f"Failed to open Google Sheets Import Dialog: {str(OpenGoogleSheetsDialogError)}",
                                LogLevel.ERROR)

    @pyqtSlot(object, str)
    def _on_google_sheet_import_finished(self, loaded_dataframe, sheet_name) -> None:
        self.status_bar.show_progress(False)
        if self.progress_dialog:
            self.progress_dialog.update_progress(90, "Updating Interface")
        self.data_tab.refresh_data_view()
        self.plot_tab.update_column_combo()
        self._unsaved_changes = True

        self.status_bar.update_data_stats(loaded_dataframe)
        self._update_tab_visibility()

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
        self.show_toast("Google Sheet Import", "Data imported from Google Sheets", ToastLevel.SUCCESS)
        GoogleSheetsImportAnimation(parent=None, message="Google Sheet Import").start(target_widget=self)

    def import_from_database(self) -> None:
        """Import data from a database connection"""
        try:
            dialog = DatabaseConnectionDialog(self)
            if dialog.exec():
                db_type, connection_string, query = dialog.get_details()

                self.status_bar.show_progress(True)
                self.status_bar.set_progress(10)

                self.progress_dialog = ProgressDialog(title=f"Importing from {db_type}", message="Connecting...",
                                                      parent=self)
                self.progress_dialog.show()
                self.progress_dialog.update_progress(10, "Connecting and executing query...")
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                QApplication.processEvents()

                try:
                    self.data_handler.import_from_database(connection_string, query)
                finally:
                    QApplication.restoreOverrideCursor()

                self.status_bar.set_progress(90)

                self.progress_dialog.update_progress(90, "Updating Interface")
                self.data_tab.refresh_data_view()
                self.plot_tab.update_column_combo()
                self._unsaved_changes = True
                self.status_bar.update_data_stats(self.data_handler.df)
                self._update_tab_visibility()

                self.status_bar.set_progress(100)
                self.status_bar.show_progress(False)

                self.progress_dialog.update_progress(100, "Complete")
                QTimer.singleShot(300, self.progress_dialog.accept)
                self.progress_dialog = None

                self.status_bar.log_action(f"Imported from {db_type} database", level="SUCCESS",
                                           details={"db_type": db_type, "rows": self.data_handler.df.shape[0]})
                self.show_toast(
                    "Import from Database", f"Imported data from {db_type} database", ToastLevel.SUCCESS
                )
                DatabaseImportAnimation(parent=None, message="Database Import", db_type=db_type).start(
                    target_widget=self)

        except Exception as ImportDatabaseError:
            if self.progress_dialog:
                self.progress_dialog.accept()
                self.progress_dialog = None

            self.show_toast(
                "Database Import Error", "Failed to import data from database", ToastLevel.ERROR
            )
            self.status_bar.log(f"Failed to import data from database: {str(ImportDatabaseError)}", LogLevel.ERROR)

    def export_code(self) -> None:
        """Export data manipulation and plotting code"""
        if self.data_handler.df is None:
            self.show_toast(
                "No Data", "Please load data before attempting to export a script", ToastLevel.WARNING
            )
            return

        source_info = self.data_handler.get_data_source()
        data_filepath = source_info.get("file_path")
        is_temp = source_info.get("is_temp_file", False)

        if not data_filepath:
            reply = QMessageBox.question(
                self,
                "No data file",
                "No local data source file was found. The exported script may lack a direct file-loading step. Continue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return

        if is_temp:
            reply = QMessageBox.question(
                self,
                "Temporary Data Source",
                "This data was imported from a temporary source.\n\n"
                "The exported Python Script will lack a direct file-loading step and will require you to manually insert the path to your local data.\n\n"
                "Do you wish to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Cancel:
                return

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setWindowTitle("Export Python Script")
        dialog.setText("Choose the components to include in the exported Python script:")
        dialog.setInformativeText(
            "* Data Pipeline Only: Exports data loading and transformation steps.\n"
            "* Data + Plotting Logic: Includes both data steps and current plot configurations."
        )

        button_data = dialog.addButton("Data Pipeline Only", QMessageBox.ButtonRole.YesRole)
        button_plot = dialog.addButton("Data + Plotting logic", QMessageBox.ButtonRole.NoRole)
        dialog.addButton(QMessageBox.StandardButton.Cancel)
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

        filepath, _ = QFileDialog.getSaveFileName(self, "Export as Python Script", f"{SCRIPT_FILE_NAME}.py",
                                                  "Python Files (*.py)")
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

                self.status_bar.log_action(f"Exported script: {Path(filepath).name}", level="SUCCESS",
                                           details={"type": export_type})

                self.show_toast(
                    "Export success", f"Exported script to {filepath}", ToastLevel.SUCCESS
                )
                ScriptLogExportAnimation(parent=self, message="Script Exported", operation_type="python").start(
                    target_widget=self)
            except Exception as ExportPythonScriptError:
                self.show_toast(
                    "Export Error", "Failed to export code to file", ToastLevel.ERROR
                )
                self.status_bar.log(f"Failed to export code: {str(ExportPythonScriptError)}", LogLevel.ERROR)

    def export_logs(self) -> None:
        """Export session log"""
        filepath, _ = QFileDialog.getSaveFileName(self, "Export Log", f"{LOG_FILE_NAME}.log",
                                                  "Log Files (*.log);;Text Files (*.txt)")
        if filepath:
            try:
                detailed = QMessageBox.question(
                    self,
                    "Export Log",
                    "Include detailed timestamps?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                ) == QMessageBox.StandardButton.Yes
                self.logger.export_logs(filepath, detailed)

                self.show_toast(
                    "Log Export Successful", f"Log exported to {filepath}", ToastLevel.SUCCESS
                )
                self.status_bar.log(f"Log exported to {filepath}", LogLevel.SUCCESS)
                ScriptLogExportAnimation(parent=self, message="Logs Exported", operation_type="log").start(
                    target_widget=self)

            except Exception as ExportLogError:
                self.show_toast(
                    "Error", "Failed to export log to file", ToastLevel.ERROR
                )
                self.status_bar.log(f"Failed to export log: {str(ExportLogError)}", LogLevel.ERROR)

    def export_data_dialog(self) -> None:
        """Export the dataframe to a new file"""
        self.data_tab.controller.export_data()

    def export_google_sheets(self) -> None:
        if self.data_handler.df is None:
            self.show_toast("No Data", "Please load data before attempting an export to Google Sheets",
                            ToastLevel.WARNING)
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

                    self.show_toast(
                        "Export Successful", f"Data was pushed to worksheet '{sheet_name}'", ToastLevel.SUCCESS
                    )
                    self.status_bar.log_action("Exported data to Google Sheets", level="SUCCESS",
                                               details={"sheet_id": sheet_id})

            except Exception as ExportSheetsError:
                if self.progress_dialog:
                    self.progress_dialog.accept()
                    self.progress_dialog = None
                self.show_toast(
                    "Export Error", "An error occurted while exporting data to Google Sheets", ToastLevel.ERROR
                )
                self.status_bar.log(f"Failed to export to Google Sheets: {str(ExportSheetsError)}", LogLevel.ERROR)
            finally:
                self.status_bar.show_progress(False)
                if self.progress_dialog:
                    QTimer.singleShot(300, self.progress_dialog.accept)
                    self.progress_dialog = None

    def undo(self) -> None:
        if self.data_handler.undo():
            self.data_tab.refresh_data_view()
            self.plot_tab.update_column_combo()
            self.plot_tab.on_data_changed()
            self.status_bar.update_data_stats(self.data_handler.df)
            self.unsaved_changes = True
            self.status_bar.log("Undo: Previous state restored")
        else:
            self.show_toast("History", "Reached beginning of history. Nothing to undo", ToastLevel.INFO,
                            duration_ms=2000)
            self.status_bar.log("Nothing to undo")

    def redo(self) -> None:
        if self.data_handler.redo():
            self.data_tab.refresh_data_view()
            self.plot_tab.update_column_combo()
            self.plot_tab.on_data_changed()
            self.status_bar.update_data_stats(self.data_handler.df)
            self.unsaved_changes = True
            self.status_bar.log("Redo: Action restored")
        else:
            self.show_toast("History", "Nothing to redo", ToastLevel.INFO, duration_ms=2000)
            self.status_bar.log("Nothing to redo")

    def zoom_in(self) -> None:
        """Zooms into the canvas"""
        if not self.plot_tab.isVisible():
            return

        fig = self.plot_tab.plot_engine.current_figure
        w, h = fig.get_size_inches()
        fig.set_size_inches(min(w * 1.1, 20), min(h * 1.1, 20))
        self.plot_tab.canvas.draw()
        self.status_bar.log("Canvas Zoomed In", LogLevel.INFO)

    def zoom_out(self) -> None:
        """Zooms out of the canvas"""
        if not self.plot_tab.isVisible():
            return

        fig = self.plot_tab.plot_engine.current_figure
        w, h = fig.get_size_inches()
        fig.set_size_inches(max(w * 0.9, 4), max(h * 0.9, 3))
        self.plot_tab.canvas.draw()
        self.status_bar.log("Canvas Zoomed Out", LogLevel.INFO)

    def zoom_reset(self) -> None:
        """
        Resets the plot zoom to default starting dimensions
        """
        if not self.plot_tab.isVisible():
            return

        DEFAULT_WIDTH_INCHES: float = 12.0
        DEFAULT_HEIGHT_INCHES: float = 8.0

        fig = self.plot_tab.plot_engine.current_figure
        fig.set_size_inches(DEFAULT_WIDTH_INCHES, DEFAULT_HEIGHT_INCHES)
        self.plot_tab.canvas.draw()
        self.status_bar.log("Zoom Reset to Default", LogLevel.INFO)
