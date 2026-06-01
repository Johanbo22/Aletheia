import json
import tempfile
from enum import Enum, auto
from functools import lru_cache
from pathlib import Path

from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QByteArray

from ui.theme import ThemeColors


class IconType(Enum):
    """
    Enum of all icons available
    """
    #### Data Operations icons
    Filter = auto()
    AdvancedFilter = auto()
    ClearFilter = auto()
    RemoveDuplicates = auto()
    DropMissingValues = auto()
    FillMissingValues = auto()
    DropColumn = auto()
    RenameColumn = auto()
    DuplicateColumn = auto()
    Calculator = auto()
    ChangeDataType = auto()
    TextOperation = auto()
    DataTransform = auto()
    EditColumns = auto()
    DataCleaning = auto()
    Sort = auto()
    PivotData = auto()
    DatetimeTools = auto()
    History = auto()
    
    #### File operations/menu ops
    OpenProject = auto()
    SaveProject = auto()
    SaveProjectAs = auto()
    NewProject = auto()
    ImportFile = auto()
    ImportGoogleSheets = auto()
    ExportFle = auto()
    ExportGoogleSheets = auto()
    ImportDatabase = auto()
    Quit = auto()
    
    # Plot operation icons
    GeneratePlot = auto()
    SavePlot = auto()
    ClearPlot = auto()
    OpenPythonEditor = auto()
    PlotGeneralOptions = auto()
    PlotAppearance = auto()
    PlotAxes = auto()
    PlotLegendGrid = auto()
    PlotCustomization = auto()
    PlotAnnotations = auto()
    PlotGeospatial = auto()
    
    # Main UI icons
    PlotTabIcon = auto()
    DataExplorerIcon = auto()
    ExploreStatisticsIcon = auto()
    Undo = auto()
    Redo = auto()
    Settings = auto()
    ZoomIn = auto()
    ZoomOut = auto()
    Information = auto()
    RefreshItem = auto()
    ViewItem = auto()
    DeleteItem = auto()
    EditModeToggleOn = auto()
    EditModeToggleOff = auto()
    Checkmark = auto()
    Locked = auto()
    Unlocked = auto()
    Docked = auto()
    Undocked = auto()
    Copy = auto()
    Help = auto()
    Search = auto()
    UpArrow = auto()
    DownArrow = auto()
    Close = auto()
    Menu = auto()
    AppIcon = auto()
    Connect = auto()
    BugReport = auto()

@lru_cache(maxsize=1)
def _load_icon_database() -> dict[str, str | list[str]]:
    """
    Loads SVG icon path strings from JSON file.
    Cached into memory to only load once per an Aletheia lifecycle
    
    :return: A dictionary mapping IconType to their SVG path data
    """
    json_path = Path(__file__).resolve().parent.parent.parent / "resources" / "icon_data.json"
    
    if not json_path.exists():
        return {}
    with json_path.open("r", encoding="utf-8") as file:
        return json.load(file)

def _get_icon_content(icon_type: IconType) -> str | tuple[str, str]:
    """
    Retrieves the SVG path data for a specific IconType from the JSON database.

    :param icon_type: The IconType enum member to fetch data for.
    :return: A string containing the SVG path(s), or a tuple of (viewBox, path) if specified.
    """
    icon_db = _load_icon_database()
    icon_data = icon_db.get(icon_type.name, "")
    
    if isinstance(icon_data, list) and len(icon_data) == 2:
        return (icon_data[0], icon_data[1])
    return icon_data

class IconBuilder:
    """
    Registry and Builder for QIcons using dynamic SVG templates.
    """
    SVG_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="{vbox}" width="{res}" height="{res}" fill="{color}">
        {content}
    </svg>"""
    
    @classmethod
    def build(cls, icon_type: IconType, resolution: int = 960, color: str = None) -> QIcon:
        """
        Builds a QIcon from the given IconType.
        If color is None, falls back to the application's primary text color.
        """
        if icon_type == IconType.AppIcon:
            return cls._build_native_app_icon(resolution)
        if color is None:
            color = ThemeColors.TEXT_PRIMARY.name()
        
        icon_data = _get_icon_content(icon_type=icon_type)
        
        # Fallback to a basic geometric shape if path not yet added 
        if not icon_data:
            vbox = "0 -960 960 960"
            content = '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>'
        else:
            if isinstance(icon_data, tuple) and len(icon_data) == 2:
                vbox, content = icon_data
            else:
                vbox = "0 -960 960 960"
                content = icon_data
        svg_str = cls.SVG_TEMPLATE.format(color=color, content=content, res=resolution, vbox=vbox)
        
        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(svg_str.encode("utf-8")), "SVG")
        
        # Generate disabled icons pixmap automatically
        disabled_color = ThemeColors.TEXT_DISABLED.name()
        disabled_svg_str = cls.SVG_TEMPLATE.format(color=disabled_color, content=content, res=resolution, vbox=vbox)
        disabled_pixmap = QPixmap()
        disabled_pixmap.loadFromData(QByteArray(disabled_svg_str.encode("utf-8")), "SVG")
        
        icon = QIcon()
        icon.addPixmap(pixmap, QIcon.Mode.Normal, QIcon.State.Off)
        icon.addPixmap(disabled_pixmap, QIcon.Mode.Disabled, QIcon.State.Off)
        
        return icon
    
    @classmethod
    def _build_native_app_icon(cls, resolution: int = 512) -> QIcon:
        from PyQt6.QtGui import QPainter, QRadialGradient, QColor, QPen, QBrush, QGuiApplication, QPolygonF
        from PyQt6.QtCore import Qt, QPointF
        import math
        
        pixmap = QPixmap(resolution, resolution)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        core_color = QColor("#1A73E8")
        accent_color = QColor("#FFFFFF")
        background_tint = QColor(core_color.red(), core_color.green(), core_color.blue(), 30)
        
        center = QPointF(resolution / 2, resolution / 2)
        base_radius = resolution * 0.42
        
        glow = QRadialGradient(center, base_radius)
        glow.setColorAt(0.0, background_tint)
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, base_radius, base_radius)
        
        layers = 3
        points_per_layer = 6
        nodes = []
        
        for layer in range(1, layers + 1):
            layer_radius = (base_radius / layers) * layer
            layer_nodes = []
            angle_offset = (math.pi / 12) * layer 
            
            for i in range(points_per_layer):
                angle = angle_offset + (i * (2 * math.pi / points_per_layer))
                jitter = (layer_radius * 0.12) if layer == layers and i % 2 == 0 else 0
                
                x = center.x() + (layer_radius + jitter) * math.cos(angle)
                y = center.y() + (layer_radius + jitter) * math.sin(angle)
                layer_nodes.append(QPointF(x, y))
            nodes.append(layer_nodes)
            
        edge_pen = QPen(QColor(core_color.red(), core_color.green(), core_color.blue(), 120), resolution * 0.012)
        edge_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(edge_pen)
        
        for layer_idx, layer_nodes in enumerate(nodes):
            poly = QPolygonF(layer_nodes)
            painter.drawPolygon(poly)
            
            if layer_idx > 0:
                inner_nodes = nodes[layer_idx - 1]
                for i, node in enumerate(layer_nodes):
                    painter.drawLine(node, inner_nodes[i])
                    painter.drawLine(node, inner_nodes[(i + 1) % points_per_layer])
        
        for node in nodes[0]:
            painter.drawLine(center, node)
            
        painter.setPen(Qt.PenStyle.NoPen)
        
        for layer_idx, layer_nodes in enumerate(nodes):
            for i, node in enumerate(layer_nodes):
                node_size = resolution * (0.045 if layer_idx == layers - 1 else 0.025)
                color = accent_color if (i + layer_idx) % 2 == 0 else core_color
                painter.setBrush(QBrush(color))
                painter.drawEllipse(node, node_size, node_size)
                
        core_grad = QRadialGradient(center, resolution * 0.09)
        core_grad.setColorAt(0.0, Qt.GlobalColor.white)
        core_grad.setColorAt(0.3, accent_color)
        core_grad.setColorAt(1.0, core_color)
        painter.setBrush(QBrush(core_grad))
        painter.drawEllipse(center, resolution * 0.09, resolution * 0.09)
        
        painter.end()
        
        icon = QIcon()
        icon.addPixmap(pixmap, QIcon.Mode.Normal, QIcon.State.Off)
        return icon
    
    @classmethod
    def build_stylesheet_icon_path(cls, icon_type: IconType, color: str = None) -> str:
        """
        Bypasses Qt's CSS parser bugs by writing the dynamically colored SVG
        to the OS temporary directory and returning the absolute file path.
        """
        if color is None:
            color = ThemeColors.TEXT_PRIMARY.name()
            
        icon_data = _get_icon_content(icon_type=icon_type)
        
        if not icon_data:
            vbox = "0 -960 960 960"
            content = '<path d="M478-240q21 0 35.5-14.5T528-290q0-21-14.5-35.5T478-340q-21 0-35.5 14.5T428-290q0 21 14.5 35.5T478-240Zm-36-154h74q0-33 7.5-52t42.5-52q26-26 41-49.5t15-56.5q0-56-41-86t-97-30q-57 0-92.5 30T342-618l66 26q5-18 25.5-39t53.5-21q32 0 48 17.5t16 38.5q0 20-12 37.5T506-526q-34 29-45 53.5T442-394Zm38 314q-83 0-156-31.5T197-197q-54-54-85.5-127T80-480q0-83 31.5-156T197-763q54-54 127-85.5T480-880q83 0 156 31.5T763-763q54 54 85.5 127T880-480q0 83-31.5 156T763-197q-54 54-127 85.5T480-80Zm0-80q134 0 227-93t93-227q0-134-93-227t-227-93q-134 0-227 93t-93 227q0 134 93 227t227 93Zm0-320Z"/>'
        else:
            if isinstance(icon_data, tuple) and len(icon_data) == 2:
                vbox, content = icon_data
            else:
                vbox = "0 -960 960 960"
                content = icon_data
                
        # Generate the raw SVG XML
        svg_str = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vbox}" fill="{color}">{content}</svg>'
        
        safe_color = color.replace("#", "")
        file_name = f"dps_{icon_type.name}_{safe_color}.svg"
        file_path = Path(tempfile.gettempdir()) / file_name
        
        if not file_path.exists():
            file_path.write_text(svg_str, encoding="utf-8")
                
        return file_path.as_posix()