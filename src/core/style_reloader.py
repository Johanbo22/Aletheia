import logging
from pathlib import Path
from typing import Callable
from PyQt6.QtCore import QObject, QFileSystemWatcher, QTimer

logger = logging.getLogger(__name__)

class StyleReloader(QObject):
    def __init__(self, styles_dir: Path, reload_callback: Callable[[], None], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._styles_dir: Path = styles_dir
        self._reload_callback: Callable[[], None] = reload_callback
        self._file_watcher: QFileSystemWatcher = QFileSystemWatcher(self)
        self._debounce_timer: QTimer = QTimer(self)
        
        self._setup_debounce_timer()
        self._initialize_watcher()
    
    def _setup_debounce_timer(self) -> None:
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(150)
        self._debounce_timer.timeout.connect(self._execute_reload)
    
    def _initialize_watcher(self) -> None:
        if not self._styles_dir.exists() or not self._styles_dir.is_dir():
            logger.warning(f"Style directory '{self._styles_dir}' not found")
            return
        
        self._register_css_files()
        
        self._file_watcher.fileChanged.connect(self._on_style_file_changed)
        self._file_watcher.directoryChanged.connect(self._on_directory_changed)
        
        logger.info(f"StyleReloader initialized. Watching '{self._styles_dir.name}'")
        
    def _register_css_files(self) -> None:
        self._file_watcher.addPath(str(self._styles_dir))
        
        for style_file in self._styles_dir.rglob("*.css"):
            file_path_str: str = str(style_file)
            if file_path_str not in self._file_watcher.files():
                self._file_watcher.addPath(file_path_str)
    
    def _on_directory_changed(self) -> None:
        self._register_css_files()
        self._trigger_reload()
    
    def _on_style_file_changed(self, file_path: str) -> None:
        changed_file: Path = Path(file_path)
        logger.debug(f"File modification detected: {changed_file.name}")
        self._trigger_reload()
    
    def _trigger_reload(self) -> None:
        self._debounce_timer.start()
        
    def _execute_reload(self) -> None:
        logger.info("Executing style reloading")
        self._reload_callback()