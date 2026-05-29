# ui/plot_tab_ui.py

from PyQt6.QtWidgets import (
    QSplitter, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFontComboBox, QStackedWidget, QToolBox, QFrame, QGraphicsDropShadowEffect, QStackedLayout, QPushButton 
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QEvent, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QKeySequence, QColor
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from core.resource_loader import get_resource_path
from ui.theme import ThemeColors
from ui.components.plot_settings_panel import PlotSettingsPanel
from ui.icons import IconBuilder, IconType

class PlotTabUI(QWidget):
    """"""
    def __init__(self) -> None:
        super().__init__()
    
    def init_ui(self, canvas: FigureCanvas, toolbar: NavigationToolbar) -> None:
        main_layout = QHBoxLayout(self)
        
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)
        
        self.canvas = canvas
        canvas_index = 1
        self.toolbar = toolbar
        self.toolbar.setObjectName("MatplotlibToolbar")
        tools_to_remove = ["Subplots", "Save"]
        for action in self.toolbar.actions():
            if hasattr(action, "text") and callable(action.text):
                if action.text() in tools_to_remove:
                    self.toolbar.removeAction(action)
        
        self.canvas_container = QFrame()
        self.canvas_container.setObjectName("CanvasContainer")
        
        self.canvas_stack = QStackedLayout(self.canvas_container)
        self.canvas_stack.setContentsMargins(0, 0, 0, 0)
        self.canvas_stack.addWidget(self.canvas)
        
        self.empty_state_view = QWebEngineView()
        self.empty_state_view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.web_view = self.empty_state_view
        self.canvas_stack.addWidget(self.empty_state_view)
        
        self.canvas_stack.setCurrentWidget(self.empty_state_view)
        
        shadow_effect = QGraphicsDropShadowEffect(self)
        shadow_effect.setBlurRadius(20)
        shadow_effect.setColor(QColor(0, 0, 0, 30))
        shadow_effect.setOffset(0, 4)
        self.canvas_container.setGraphicsEffect(shadow_effect)
        self.canvas.figure.patch.set_alpha(0.0)
        
        left_layout.addWidget(self.toolbar)
        left_layout.addWidget(self.canvas_container, 1)
        
        right_layout = QVBoxLayout()
        
        self.settings_panel = PlotSettingsPanel(parent=self)
        self.custom_tabs = self.settings_panel.custom_tabs
        
        for name, obj in vars(self.settings_panel).items():
            if isinstance(obj, (QWidget, QToolBox, QFontComboBox)) and not name.startswith("_"):
                setattr(self, name, obj)
            if name in ["las_latex"]:
                setattr(self, name, obj)
        
        right_layout.addWidget(self.settings_panel, 1)
        
        # Buttons at bottom
        button_layout = QHBoxLayout()
        
        self.plot_button = QPushButton("Generate Plot")
        self.plot_button.setObjectName("MainActionButton")
        self.plot_button.setMinimumHeight(40)
        self.plot_button.setIcon(IconBuilder.build(IconType.GeneratePlot))
        self.plot_button.setShortcut(QKeySequence("Ctrl+Return"))

        self.save_plot_button = QPushButton("Save Plot")
        self.save_plot_button.setMinimumHeight(40)
        self.save_plot_button.setIcon(IconBuilder.build(IconType.SavePlot))
        self.save_plot_button.setToolTip("Export the current plot to PNG, PDF or SVG")
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.setMinimumHeight(40)
        self.clear_button.setIcon(IconBuilder.build(IconType.ClearPlot))
        
        self.editor_button = QPushButton("Open Python Editor")
        self.editor_button.setMinimumHeight(40)
        self.editor_button.setIcon(IconBuilder.build(IconType.OpenPythonEditor))
        self.editor_button.setToolTip("Open the code editor to view/write python code for the plot.")
        
        button_layout.addWidget(self.plot_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.editor_button)
        button_layout.addWidget(self.save_plot_button)
        
        right_layout.addLayout(button_layout)
        
        # Set layouts
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        
        # Create splitter
        splitter: QSplitter = self._create_splitter(left_widget, right_widget)
        main_layout.addWidget(splitter)
        
        self.setLayout(main_layout)
    
    def _create_splitter(self, left, right) -> QSplitter:
        """Create a splitter for resizable panels"""
        from PyQt6.QtWidgets import QSplitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([700, 300])
        return splitter