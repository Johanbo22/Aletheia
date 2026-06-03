import importlib.util
import logging
import sys
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPainter, QColor, QFont

from core.resource_loader import get_resource_path

def load_help_animation_widget(topic_id: str) -> QWidget:
    """Loads and instantiates a help animation widget by a topic ID"""
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    clean_filename = f"{str(topic_id).lower()}.py"
    anim_path_obj = project_root / "resources" / "help_animations" / clean_filename
    anim_path = get_resource_path(str(anim_path_obj))

    if not Path(anim_path).exists():
        logging.getLogger(__name__).warning(f"HelpAnimationLoader: Animation file missing at {anim_path}")
        return _create_animation_placeholder(f"No animation found for '{topic_id}'")

    module_name = f"anim_{topic_id}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, anim_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            if hasattr(module, "Animation"):
                animation_instance = module.Animation()
                if isinstance(animation_instance, QWidget):
                    return animation_instance
    except Exception as e:
        logging.getLogger(__name__).error(f"HelpAnimationLoader: Error loading {anim_path}: {e}")
        sys.modules.pop(module_name, None)

    return _create_animation_placeholder("Preview Unavailable")

def _create_animation_placeholder(text: str) -> QLabel:
    """Creates a fallback label when an animation fails to load."""
    lbl = QLabel(text)
    lbl.setFixedSize(450, 300)
    lbl.setObjectName("help_animation_placeholder")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setWordWrap(True)
    return lbl

class HelpAnimationEngine(QWidget):
    """
    Class for Help dialog animations
    This is the engine that handles the animation loop, framerate and sizing
    """

    def __init__(self, parent=None, fps=60, duration_ms=4000):
        super().__init__(parent)
        self.setFixedSize(550, 350)

        self.fps = fps
        self.duration_ms = duration_ms
        self.current_time_ms = 0

        # Timer Setyp
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_loop)
        self.timer.start(1000 // self.fps)

        # Styling constants for animations
        self.bg_color = QColor("#2B2B2B")
        self.text_color = QColor("#ffffff")
        self.accent_color = QColor("#4a90e2")
        self.highlight_color = QColor("#e74c3c")
        self.success_color = QColor("#2ecc71")

        # Font Setup
        self.font_main = QFont("Segoe UI", 10)
        self.font_bold = QFont("Segoe UI", 10, QFont.Weight.Bold)
        self.font_small = QFont("Segoe UI", 9)
    
    def _update_loop(self):
        """Function that handles internal loop of animation"""
        self.current_time_ms += (1000 // self.fps)
        if self.current_time_ms > self.duration_ms:
            self.current_time_ms = 0
        
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate the progress from 0.0 to 1.0
        progress = self.current_time_ms / self.duration_ms

        self.draw_animation(painter, progress)

    def draw_animation(self, painter: QPainter, progress: float):
        """
        This method is overriden by the animation it self
        """
        pass

    def get_eased_progress(self, progress, start, end):
        """Help to map the global progress to a subinterval"""
        if progress < start: return 0.0
        if progress > end: return 1.0
        return (progress - start) / (end - start)

    def lerp_color(self, c1: QColor, c2: QColor, t: float) -> QColor:
        """
        Linear interpolation between two colors
        """
        if t <= 0: return c1
        if t >= 1: return c2

        r = c1.red() + (c2.red() - c1.red()) * t
        g = c1.green() + (c2.green() - c1.green()) * t
        b = c1.blue() + (c2.blue() - c1.blue()) * t

        return QColor(int(r), int(g), int(b))