from typing import Any, Callable, Dict, List, Optional, Tuple

from PyQt6.QtCore import QEasingCurve, QParallelAnimationGroup, QPoint, QPointF, QPropertyAnimation, QRectF, \
    QSequentialAnimationGroup, QTimer, QVariantAnimation, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QFontMetrics, QHideEvent, QKeyEvent, QMouseEvent, QPainter, QPainterPath, \
    QPen, \
    QPixmap, QShowEvent, QWheelEvent
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QGraphicsItem, QGraphicsObject, QGraphicsPathItem, \
    QGraphicsScene, \
    QGraphicsSceneContextMenuEvent, QGraphicsSceneHoverEvent, QGraphicsSceneMouseEvent, QGraphicsView, \
    QScrollBar, QStyleOptionGraphicsItem, QWidget

OP_COLORS_MAP: dict[str, QColor] = {
    "origin"        : QColor("#10b981"),
    "filter"        : QColor("#f59e0b"),
    "cleaning"      : QColor("#EF4444"),
    "transformation": QColor("#8b5cf6"),
    "subset"        : QColor("#06b6d4"),
    "aggregation"   : QColor("#f97316"),
    "datetime"      : QColor("#ec4899"),
    "unknown"       : QColor("#3b82f6"),
}

class FlowEdgeItem(QGraphicsPathItem):
    """Custom path item that renders a solid base and an animated flowing dashed line on top for active paths"""

    BASE_ACTIVE_PEN: QPen = QPen(QColor("#93c5fd"), 2.5, Qt.PenStyle.SolidLine)
    BASE_INACTIVE_PEN: QPen = QPen(QColor("#94a3b8"), 2.0, Qt.PenStyle.DashLine)
    FLOW_COLOR: QColor = QColor("#2563eb")
    DASH_PATTERN: list[float] = [3.0, 12.0]

    def __init__(self, path: QPainterPath, target_node_id: str, is_active_path: bool,
                 parent: Optional[QGraphicsItem] = None) -> None:
        super().__init__(path, parent)
        self.target_node_id: str = target_node_id
        self.is_active_path: bool = is_active_path
        self.dash_offset: float = 0.0
        self.base_pen: QPen = self.BASE_INACTIVE_PEN
        self.flow_pen: Optional[QPen] = None

        self.setZValue(-2.0)
        self._update_pens()

    def _update_pens(self) -> None:
        """Updates internal pen references when selection status changes"""
        if self.is_active_path:
            self.base_pen = self.BASE_ACTIVE_PEN
            self.flow_pen = QPen(self.FLOW_COLOR, 2.5, Qt.PenStyle.CustomDashLine)
            self.flow_pen.setDashPattern(self.DASH_PATTERN)
        else:
            self.base_pen = self.BASE_INACTIVE_PEN
            self.flow_pen = None

    def set_active(self, is_active: bool) -> None:
        """
        Updates the active status of the edge connector

        :param is_active: True if this edge lies on the active pipeline branch
        """
        if self.is_active_path == is_active:
            return
        self.is_active_path = is_active
        self._update_pens()
        self.update()

    def advance_flow(self, delta: float) -> None:
        """
        Updates the dash offset property to animate line movement

        :param delta: Fractional offset step
        """
        if not self.is_active_path or self.flow_pen is None:
            return
        self.dash_offset -= delta
        if self.dash_offset < -1000.0:
            self.dash_offset += 1000.0
        self.flow_pen.setDashOffset(self.dash_offset)
        self.update()

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None) -> None:
        """Paints the static ptah and animated overlay without modifying the global render hints"""
        painter.setPen(self.base_pen)
        painter.drawPath(self.path())
        if self.is_active_path and self.flow_pen is not None:
            painter.setPen(self.flow_pen)
            painter.drawPath(self.path())

class FocusHighlightItem(QGraphicsObject):
    """
    Renders an animated glowing pill behind the currently active node
    """

    BG_BRUSH: QBrush = QBrush(QColor("#EFF6FF"))
    BORDER_PEN: QPen = QPen(QColor("#3b82f6"), 1.5)
    CORNER_RADIUS: float = 8.0

    def __init__(self, width: float, height: float, parent: Optional[QGraphicsItem] = None) -> None:
        super().__init__(parent)
        self.width: float = width
        self.height: float = height
        self._bounding_rect: QRectF = QRectF(0.0, 0.0, self.width, self.height)

        self.shadow: QGraphicsDropShadowEffect = QGraphicsDropShadowEffect()
        self.shadow.setColor(QColor(0, 0, 0, 30))
        self.shadow.setBlurRadius(18.0)
        self.shadow.setOffset(0.0, 5.0)
        self.setGraphicsEffect(self.shadow)
        self.setCacheMode(QGraphicsItem.CacheMode.ItemCoordinateCache)
        self.setZValue(-1.0)

    def boundingRect(self) -> QRectF:
        """Returns the pre-allocated item boundary"""
        return self._bounding_rect

    def _set_pos(self, pos: QPointF):
        self.setPos(pos)

    def _get_pos(self) -> QPointF:
        return self.pos()

    animated_pos = pyqtProperty(QPointF, fget=_get_pos, fset=_set_pos)

    def _set_opacity(self, opacity: float):
        self.setOpacity(opacity)

    def _get_opacity(self) -> float:
        return self.opacity()

    animated_opacity = pyqtProperty(float, fget=_get_opacity, fset=_set_opacity)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None) -> None:
        """Paints the focus rectangle"""
        painter.setBrush(self.BG_BRUSH)
        painter.setPen(self.BORDER_PEN)
        painter.drawRoundedRect(self._bounding_rect, self.CORNER_RADIUS, self.CORNER_RADIUS)

class GraphNode(QGraphicsObject):
    """
    Visual representation of a single operation in the data pipeline

    Handles state styling and interaction events on the node of the graph.
    """
    clicked = pyqtSignal(str)
    hover_entered = pyqtSignal(str)
    hover_left = pyqtSignal(str)
    context_menu_requested = pyqtSignal(str, QPoint)

    NODE_WIDTH: float = 260.0
    NODE_HEIGHT: float = 48.0
    CORNER_RADIUS: float = 8.0
    DOT_RADIUS: float = 4.5
    DOT_X: float = 18.0

    FONT_UUID: QFont = QFont("Inter", 7)
    FONT_LABEL: QFont = QFont("Inter", 9)
    FONT_LABEL_BOLD: QFont = QFont("Inter", 9, QFont.Weight.Bold)
    FONT_BADGE: QFont = QFont("Inter", 8, QFont.Weight.Bold)

    COLOR_BADGE_BG: QColor = QColor("#DBEAFE")
    COLOR_BADGE_TEXT: QColor = QColor("#1D4ED8")
    COLOR_UUID_ACTIVE: QColor = QColor("#60a5fa")
    COLOR_UUID_INACTIVE: QColor = QColor("#94a3b8")
    COLOR_TEXT_ACTIVE: QColor = QColor("#1E3A8A")
    COLOR_TEXT_UNDONE: QColor = QColor("#94A3B8")
    COLOR_TEXT_DEFAULT: QColor = QColor("#334155")
    COLOR_BG_HOVER: QColor = QColor("#F8FAFC")
    COLOR_BG_WHITE: QColor = QColor("#FFFFFF")
    COLOR_BG_ACTIVE_HOVER: QColor = QColor(219, 234, 254, 150)
    COLOR_BORDER_UNDONE: QColor = QColor("#CBD5E1")
    COLOR_BORDER_DEFAULT: QColor = QColor("#94A3B8")

    def __init__(self, node_id: str, label: str, operation: dict, is_active: bool, is_undone: bool, ) -> None:
        super().__init__(None)
        self.node_id: str = node_id
        self.label: str = label
        self.operation: dict = operation
        self.is_active: bool = is_active
        self.is_undone: bool = is_undone
        self.is_hovered: bool = False

        self.op_type: str = self.operation.get("type", "unknown").lower() if self.operation else "origin"
        self._short_uuid: str = self.node_id[-8:] if self.node_id else ""
        self._bounding_rect: QRectF = QRectF(0.0, 0.0, self.NODE_WIDTH, self.NODE_HEIGHT)
        self._shape_path: QPainterPath = QPainterPath()
        self._shape_path.addRoundedRect(self._bounding_rect, self.CORNER_RADIUS, self.CORNER_RADIUS)

        badge_w, badge_h = 44.0, 18.0
        badge_x: float = self.NODE_WIDTH - badge_w - 10.0
        badge_y: float = (self.NODE_HEIGHT - badge_h) / 2.0
        self._badge_rect: QRectF = QRectF(badge_x, badge_y, badge_w, badge_h)

        self._elided_label: str = ""
        self._label_pos_y: float = 0.0
        self._bg_brush: QBrush = QBrush()
        self._border_pen: QPen = QPen()
        self._dot_brush: QBrush = QBrush()
        self.text_color: QColor = self.COLOR_TEXT_DEFAULT

        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCacheMode(QGraphicsItem.CacheMode.ItemCoordinateCache)
        self.setTransformOriginPoint(self.NODE_WIDTH / 2.0, self.NODE_HEIGHT / 2.0)

        self.shadow: QGraphicsDropShadowEffect = QGraphicsDropShadowEffect()
        self.shadow.setColor(QColor(0, 0, 0, 25))
        self.shadow.setBlurRadius(10.0)
        self.shadow.setOffset(0.0, 3.0)
        self.setGraphicsEffect(self.shadow)

        self._setup_tooltip()
        self._update_styling()

        self._update_styling()

    def boundingRect(self) -> QRectF:
        """Returns the pre-calculated node geometry rectangle"""
        return self._bounding_rect

    def shape(self) -> QPainterPath:
        """Returns the bounding path for hover and click events"""
        return self._shape_path

    def _setup_tooltip(self) -> None:
        """Constructs the HTML tooltip text"""
        if self.operation:
            items_html: str = "".join(
                f"<li><b>{k}</b>: {v}</li>" for k, v in self.operation.items() if k != "type"
            )
            self.setToolTip(
                f"<div style='padding: 4px; color: #F8FAFC;'>"
                f"<b style='color: #FFFFFF; font-size: 13px;'>{self.label}</b><br><br>"
                f"<b>Operation Details:</b><br>"
                f"<ul style='margin-top: 4px; margin-bottom: 0px;'>{items_html}</ul>"
                f"</div>"
            )
            return
        self.setToolTip(
            f"<div style='color: #F8FAFC;'>"
            f"<b style='color: #FFFFFF; font-size: 13px;'>{self.label}</b><br><br>"
            f"Original imported data state</div>"
        )

    def _set_pos(self, pos: QPointF):
        self.setPos(pos)

    def _get_pos(self) -> QPointF:
        return self.pos()

    animated_pos = pyqtProperty(QPointF, fget=_get_pos, fset=_set_pos)

    def _set_opacity(self, opacity: float):
        self.setOpacity(opacity)

    def _get_opacity(self) -> float:
        return self.opacity()

    animated_opacity = pyqtProperty(float, fget=_get_opacity, fset=_set_opacity)

    def _update_styling(self) -> None:
        """Updates colors and shadow elevation based on state and hover."""
        base_dot = QColor(OP_COLORS_MAP.get(self.op_type, OP_COLORS_MAP["unknown"]))

        if self.is_active:
            bg_color = self.COLOR_BG_ACTIVE_HOVER if self.is_hovered else QColor(Qt.GlobalColor.transparent)
            self._border_pen = QPen(Qt.GlobalColor.transparent)
            self.text_color = self.COLOR_TEXT_ACTIVE
            self._dot_brush = QBrush(base_dot)
            self.shadow.setEnabled(False)
        elif self.is_undone:
            bg_color = self.COLOR_BG_HOVER if self.is_hovered else self.COLOR_BG_WHITE
            self._border_pen = QPen(self.COLOR_BORDER_UNDONE, 1.5, Qt.PenStyle.DashLine)
            self.text_color = self.COLOR_TEXT_UNDONE
            self._dot_brush = QBrush(self.COLOR_BORDER_UNDONE)
            self.shadow.setEnabled(self.is_hovered)
        else:
            bg_color = self.COLOR_BG_HOVER if self.is_hovered else self.COLOR_BG_WHITE
            self._border_pen = QPen(self.COLOR_BORDER_DEFAULT, 1.5, Qt.PenStyle.SolidLine)
            self.text_color = self.COLOR_TEXT_DEFAULT
            self._dot_brush = QBrush(base_dot)
            self.shadow.setEnabled(True)

        self._bg_brush = QBrush(bg_color)
        if not self.is_active:
            self.shadow.setOffset(0.0, 5.0 if self.is_hovered else 3.0)

        self._update_text_metrics()

    def _update_text_metrics(self) -> None:
        """Calculates text clipping position"""
        font: QFont = self.FONT_LABEL_BOLD if self.is_active else self.FONT_LABEL
        metrics: QFontMetrics = QFontMetrics(font)
        limit: int = int(self.NODE_WIDTH - 95) if self.is_active else int(self.NODE_WIDTH - 45)
        self._elided_label = metrics.elidedText(self.label, Qt.TextElideMode.ElideRight, limit)

        text_rect: QRectF = QRectF(metrics.boundingRect(self._elided_label))
        self._label_pos_y = (self.NODE_HEIGHT + text_rect.height()) / 2.0 - metrics.descent()

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.is_hovered = True
        self._update_styling()
        self.update()
        self.hover_entered.emit(self.node_id)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.is_hovered = False
        self._update_styling()
        self.update()
        self.hover_left.emit(self.node_id)
        super().hoverLeaveEvent(event)

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        self.context_menu_requested.emit(self.node_id, event.screenPos())
        event.accept()

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setScale(0.98)
            if self.shadow.isEnabled():
                self.shadow.setOffset(0.0, 1.0)
                self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setScale(1.0)
            self._update_styling()
            self.update()
            if self._bounding_rect.contains(event.pos()):
                self.clicked.emit(self.node_id)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None) -> None:
        painter.setPen(self._border_pen)
        painter.setBrush(self._bg_brush)
        painter.drawRoundedRect(self._bounding_rect, self.CORNER_RADIUS, self.CORNER_RADIUS)

        painter.setFont(self.FONT_UUID)
        painter.setPen(self.COLOR_UUID_ACTIVE if self.is_active else self.COLOR_UUID_INACTIVE)
        painter.drawText(QPointF(12.0, 14.0), self._short_uuid)

        painter.setBrush(self._dot_brush)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(self.DOT_X, self.NODE_HEIGHT / 2.0), self.DOT_RADIUS, self.DOT_RADIUS)

        if self.is_active:
            painter.setBrush(self.COLOR_BADGE_BG)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self._badge_rect, 6.0, 6.0)
            painter.setFont(self.FONT_BADGE)
            painter.setPen(self.COLOR_BADGE_TEXT)
            painter.drawText(self._badge_rect, Qt.AlignmentFlag.AlignCenter, "Active")

        painter.setFont(self.FONT_LABEL_BOLD if self.is_active else self.FONT_LABEL)
        painter.setPen(self.text_color)
        painter.drawText(QPointF(34.0, self._label_pos_y), self._elided_label)

class PipelineGraphView(QGraphicsView):
    """A visual node-based representation of the data transformation history."""
    node_selected = pyqtSignal(str)
    node_context_menu = pyqtSignal(str, QPoint)

    GRID_SIZE: int = 20
    DOT_RADIUS: float = 1.0
    GRID_BG_COLOR: QColor = QColor("#f8fafc")
    GRID_DOT_COLOR: QColor = QColor("#cbd5e1")
    NODE_VERTICAL_SPACING: float = 75.0
    NODE_HORIZONTAL_SPACING: float = 300.0

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.graph_scene: QGraphicsScene = QGraphicsScene(self)
        self.setScene(self.graph_scene)

        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.TextAntialiasing |
            QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)

        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setObjectName("PipelineGraphView")
        self.setProperty("styleClass", "transparent_scroll_area")

        self.nodes: List[GraphNode] = []
        self.edges: List[FlowEdgeItem] = []
        self._active_edges: List[FlowEdgeItem] = []
        self.focus_selector: Optional[FocusHighlightItem] = None
        self.current_id: str = ""

        self._scroll_animation: QPropertyAnimation = QPropertyAnimation(self, b"viewCenter", self)
        self._scroll_animation.setDuration(400)
        self._scroll_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self._pill_animation: Optional[QPropertyAnimation] = None

        self._zoom_level: int = 0
        self._zoom_min: int = -4
        self._zoom_max: int = 6

        self._is_middle_dragging: bool = False
        self._last_mouse_pos: Optional[QPointF] = None
        self._middle_click_pos: Optional[QPointF] = None

        self._background_brush: Optional[QBrush] = None
        self._create_background_brush()

        self._flow_timer: QTimer = QTimer(self)
        self._flow_timer.timeout.connect(self._advance_edge_flow)

        self._current_nodes_dict: Dict[str, Any] = {}
        self._focused_path_set: set[str] = set()
        self._current_fade_factor: float = 0.0

        focus_animation_duration: int = 200
        self._focus_anim: QVariantAnimation = QVariantAnimation(self)
        self._focus_anim.setDuration(focus_animation_duration)
        self._focus_anim.valueChanged.connect(self._apply_focus_fade)

        self._entrance_group: QParallelAnimationGroup = QParallelAnimationGroup(self)

    def showEvent(self, event: QShowEvent) -> None:
        """Starts the animation loop when the widget becomes visible"""
        super().showEvent(event)
        self._evaluate_flow_timer_state()

    def hideEvent(self, event: QHideEvent) -> None:
        """Stops the flow animation when widget is hidden"""
        super().hideEvent(event)
        self._flow_timer.stop()

    def _evaluate_flow_timer_state(self) -> None:
        """Controls flow timers lifecycle based on the amount of active FlowEdges and the visibility of the widget"""
        has_active: bool = len(self._active_edges) > 0
        if self.isVisible() and has_active and not self._flow_timer.isActive():
            self._flow_timer.start(40)
        elif (not self.isVisible() or not has_active) and self._flow_timer.isActive():
            self._flow_timer.stop()

    def _apply_focus_fade(self, factor: float) -> None:
        """Drives the opacity of non-focused elements to dimmer"""
        self._current_fade_factor = factor
        if factor <= 0.001:
            for node in self.nodes:
                node.setOpacity(1.0)
            for edge in self.edges:
                edge.setOpacity(1.0)
            return

        dim_node_op: float = 1.0 - (0.7 * factor)
        dim_edge_op: float = 1.0 - (0.85 * factor)

        for node in self.nodes:
            if node.node_id not in self._focused_path_set:
                node.setOpacity(dim_node_op)
        for edge in self.edges:
            if edge.target_node_id not in self._focused_path_set:
                edge.setOpacity(dim_edge_op)

    def _on_node_hover_entered(self, node_id: str) -> None:
        if self._entrance_group.state() == QPropertyAnimation.State.Running:
            return

        path_list: List[str] = self._get_path_to_root(self._current_nodes_dict, node_id)
        self._focused_path_set = set(path_list)

        self._focus_anim.stop()
        self._focus_anim.setStartValue(self._current_fade_factor)
        self._focus_anim.setEndValue(1.0)
        self._focus_anim.start()

    def _on_node_hover_left(self, node_id: str) -> None:
        if self._entrance_group.state() == QPropertyAnimation.State.Running:
            return

        self._focus_anim.stop()
        self._focus_anim.setStartValue(self._current_fade_factor)
        self._focus_anim.setEndValue(0.0)
        self._focus_anim.start()

    def _on_node_context_menu(self, node_id: str, pos: QPoint) -> None:
        self.node_context_menu.emit(node_id, pos)

    def _advance_edge_flow(self) -> None:
        """Ticks the dash offset for active edges to create a flowing animation"""
        for edge in self.edges:
            edge.advance_flow(0.8)

    def _create_background_brush(self) -> None:
        """Generates a reusable brush for background rendering"""
        pixmap: QPixmap = QPixmap(self.GRID_SIZE, self.GRID_SIZE)
        pixmap.fill(self.GRID_BG_COLOR)

        painter: QPainter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.GRID_DOT_COLOR)
        painter.drawEllipse(
            QPointF(self.GRID_SIZE / 2.0, self.GRID_SIZE / 2.0),
            self.DOT_RADIUS,
            self.DOT_RADIUS
        )
        painter.end()
        self._background_brush = QBrush(pixmap)

    def _set_view_center(self, center: QPointF):
        self.centerOn(center)

    def _get_view_center(self) -> QPointF:
        return self.mapToScene(self.viewport().rect().center())

    viewCenter: pyqtProperty = pyqtProperty(QPointF, fget=_get_view_center, fset=_set_view_center)

    def center_on_animated(self, item: QGraphicsObject):
        if self._scroll_animation.state() == QPropertyAnimation.State.Running:
            self._scroll_animation.stop()

        self._scroll_animation.setStartValue(self.viewCenter)
        self._scroll_animation.setEndValue(item.sceneBoundingRect().center())
        self._scroll_animation.start()

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        """Paints the background using cached brush"""
        if self._background_brush is not None:
            painter.fillRect(rect, self._background_brush)
        else:
            painter.fillRect(rect, self.GRID_BG_COLOR)

    def _get_path_to_root(self, nodes_dict: Dict[str, Any], start_node_id: str) -> List[str]:
        """Helper to trace the path back to the root node."""
        path: list[str | None] = []
        curr: Optional[str] = start_node_id
        while curr:
            path.append(curr)
            node = nodes_dict.get(curr)
            curr = node.parent_id if node else None
        return path

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            is_zooming_in: bool = event.angleDelta().y() > 0
            if (is_zooming_in and self._zoom_level >= self._zoom_max) or (
                    not is_zooming_in and self._zoom_level <= self._zoom_min):
                return

            zoom_factor: float = 1.15 if is_zooming_in else (1.0 / 1.15)
            self._zoom_level += 1 if is_zooming_in else -1
            self.scale(zoom_factor, zoom_factor)

            event.accept()
            return
        super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_middle_dragging = True
            self._last_mouse_pos = event.position()
            self._middle_click_pos = event.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_middle_dragging and self._last_mouse_pos is not None:
            delta: QPointF | None = event.position() - self._last_mouse_pos

            h_bar: Optional[QScrollBar] = self.horizontalScrollBar()
            v_bar: Optional[QScrollBar] = self.verticalScrollBar()

            if h_bar is not None:
                h_bar.setValue(int(h_bar.value() - delta.x()))
            if v_bar is not None:
                v_bar.setValue(int(v_bar.value() - delta.y()))

            self._last_mouse_pos = event.position()

            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton and self._is_middle_dragging:
            self._is_middle_dragging = False
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

            if self._middle_click_pos is not None:
                distance: float = (event.position() - self._middle_click_pos).manhattanLength()
                if distance < 5.0:
                    self.resetTransform()
                    active_node: Optional[GraphNode] = next(
                        (n for n in self.nodes if n.node_id == self.current_id), None
                    )
                    if active_node is not None:
                        self.center_on_animated(active_node)

            self._last_mouse_pos = None
            self._middle_click_pos = None

            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_F:
            scene_rect: QRectF | None = self.graph_scene.itemsBoundingRect()
            scene_rect.adjust(-20, -20, 20, 20)
            self.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)
            event.accept()
            return
        super().keyPressEvent(event)

    def _calculate_tree_layout(self, nodes_dict: Dict[str, Any], root_id: str) -> Dict[str, Tuple[float, float, int]]:
        """
        Calculates the 2D spatial layout and depth for the graph

        :param nodes_dict: State dictionary mapping node IDs to node data
        :param root_id: The ID_of the origin node
        :return: A dictionary mapping the node IDs to a tuple of (x, y, depth)
        """
        positions: Dict[str, Tuple[float, float, int]] = {}

        def calculate_positions(node_id: str, depth: int, branch_index: int) -> None:
            x_pos: float = 20.0 + (branch_index * self.NODE_HORIZONTAL_SPACING)
            y_pos: float = 20.0 + (depth * self.NODE_VERTICAL_SPACING)
            positions[node_id] = (x_pos, y_pos, depth)

            node_data: Optional[Any] = nodes_dict.get(node_id)
            if not node_data:
                return

            for i, child_id in enumerate(node_data.children_ids):
                child_branch: int = branch_index if i == len(node_data.children_ids) - 1 else branch_index + (i + 1)
                calculate_positions(child_id, depth + 1, child_branch)

        calculate_positions(root_id, depth=0, branch_index=0)
        return positions

    def _setup_focus_selector(self, target_x: float, target_y: float, target_depth: int) -> None:
        """
        Initializes and sequences the entrance animation for the focus highlight pill

        :param target_x: The target X coordinate for the pill animation
        :param target_y: The target Y coordinate for the pill animation
        :param target_depth: The depth of the node for animation sequencing
        """
        self.focus_selector = FocusHighlightItem(GraphNode.NODE_WIDTH, GraphNode.NODE_HEIGHT)

        start_pos: QPointF = QPointF(target_x, target_y + 20)
        end_pos: QPointF = QPointF(target_x, target_y)

        self.focus_selector.setPos(start_pos)
        self.focus_selector.setOpacity(0.0)
        self.graph_scene.addItem(self.focus_selector)

        anim_pos = QPropertyAnimation(self.focus_selector, b"animated_pos")
        anim_pos.setStartValue(start_pos)
        anim_pos.setEndValue(end_pos)
        anim_pos.setDuration(400)
        anim_pos.setEasingCurve(QEasingCurve.Type.OutBack)

        anim_op = QPropertyAnimation(self.focus_selector, b"animated_opacity")
        anim_op.setStartValue(0.0)
        anim_op.setEndValue(1.0)
        anim_op.setDuration(300)

        pill_group = QParallelAnimationGroup(self)
        pill_group.addAnimation(anim_pos)
        pill_group.addAnimation(anim_op)

        delay: int = min(target_depth * 40, 240)
        if delay > 0:
            seq_group = QSequentialAnimationGroup(self)
            seq_group.addPause(delay)
            seq_group.addAnimation(pill_group)
            self._entrance_group.addAnimation(seq_group)
            return
        self._entrance_group.addAnimation(pill_group)

    def _prepare_build_state(self, nodes_dict: Dict[str, Any], current_node_id: str) -> None:
        """Stops any running animations and flushes the scene caches"""
        if self._entrance_group.state() == QPropertyAnimation.State.Running:
            self._entrance_group.stop()
        if self._pill_animation and self._pill_animation.state() == QPropertyAnimation.State.Running:
            self._pill_animation.stop()
        if self._focus_anim.state() == QVariantAnimation.State.Running:
            self._focus_anim.stop()

        self._current_nodes_dict = nodes_dict
        self.graph_scene.clear()
        self.nodes.clear()
        self.edges.clear()
        self._active_edges.clear()
        self.focus_selector = None
        self.current_id = current_node_id
        self._entrance_group.clear()

    def _create_edge_item(self, p_pos: Tuple[float, float, int], c_pos: Tuple[float, float, int], child_id: str,
                          is_active: bool) -> FlowEdgeItem:
        """Constructs and returns a cubic Bézier curve connectection between parent and children node items"""
        path: QPainterPath = QPainterPath()
        start_pt = QPointF(p_pos[0] + GraphNode.NODE_WIDTH / 2.0, p_pos[1] + GraphNode.NODE_HEIGHT)
        end_pt = QPointF(c_pos[0] + GraphNode.NODE_WIDTH / 2.0, c_pos[1])

        ctrl1 = QPointF(start_pt.x(), start_pt.y() + (self.NODE_VERTICAL_SPACING / 2.0))
        ctrl2 = QPointF(end_pt.x(), end_pt.y() - (self.NODE_VERTICAL_SPACING / 2.0))

        path.moveTo(start_pt)
        path.cubicTo(ctrl1, ctrl2, end_pt)
        return FlowEdgeItem(path, child_id, is_active)

    def _animate_node_entrance(self, node: GraphNode, x_pos: float, y_pos: float, depth: int) -> None:
        anim_pos = QPropertyAnimation(node, b"animated_pos")
        anim_pos.setStartValue(QPointF(x_pos, y_pos + 20.0))
        anim_pos.setEndValue(QPointF(x_pos, y_pos))
        anim_pos.setDuration(400)
        anim_pos.setEasingCurve(QEasingCurve.Type.OutBack)

        anim_op = QPropertyAnimation(node, b"animated_opacity")
        anim_op.setStartValue(0.0)
        anim_op.setEndValue(1.0)
        anim_op.setDuration(300)

        group = QParallelAnimationGroup(self)
        group.addAnimation(anim_pos)
        group.addAnimation(anim_op)

        delay: int = min(depth * 40, 240)
        if delay > 0:
            seq = QSequentialAnimationGroup(self)
            seq.addPause(delay)
            seq.addAnimation(group)
            self._entrance_group.addAnimation(seq)
            return
        self._entrance_group.addAnimation(group)

    def build_graph(self, nodes_dict: Dict[str, Any], root_id: str, current_node_id: str,
                    format_func: Callable) -> None:
        """
        Constructs nodes and paths for the entire operation graph view.

        :param nodes_dict: State dictionary mapping node IDs to node objects
        :param root_id: The ID of the origin node
        :param current_node_id: The currently active step in the graph
        :param format_func: Callable to format the node metadata for display
        """
        current_node_ids: set[str] = {node.node_id for node in self.nodes}
        if current_node_ids and current_node_ids == set(nodes_dict.keys()):
            self._update_selection_in_place(nodes_dict, current_node_id)
            return

        self._prepare_build_state(nodes_dict, current_node_id)
        positions: Dict[str, tuple[float, float, int]] = self._calculate_tree_layout(nodes_dict, root_id)
        active_path_set: set[str] = set(self._get_path_to_root(nodes_dict, current_node_id))
        active_node_item: Optional[GraphNode] = None
        max_x, max_y = 0.0, 0.0

        for node_id, (x_pos, y_pos, depth) in positions.items():
            node_data = nodes_dict[node_id]
            is_active: bool = node_id == current_node_id
            is_undone: bool = (node_id not in active_path_set) and (not is_active)

            label: str = "Initial Data" if node_id == root_id else format_func(node_data.diff_record.metadata)
            graph_node = GraphNode(node_id, label, getattr(node_data.diff_record, "metadata", {}), is_active, is_undone)

            graph_node.hover_entered.connect(self._on_node_hover_entered)
            graph_node.hover_left.connect(self._on_node_hover_left)
            graph_node.context_menu_requested.connect(self._on_node_context_menu)
            graph_node.clicked.connect(self._handle_node_clicked)

            graph_node.setPos(x_pos, y_pos + 20)
            graph_node.setOpacity(0.0)

            self.graph_scene.addItem(graph_node)
            self.nodes.append(graph_node)

            if is_active:
                active_node_item = graph_node

            max_x: float = max(max_x, x_pos)
            max_y: float = max(max_y, y_pos)

            if node_data.parent_id and node_data.parent_id in positions:
                is_active_path: bool = is_active or (node_id in active_path_set)
                edge: FlowEdgeItem = self._create_edge_item(
                    positions[node_data.parent_id],
                    (x_pos, y_pos, depth),
                    node_id,
                    is_active_path
                )
                self.graph_scene.addItem(edge)
                self.edges.append(edge)
                if is_active_path:
                    self._active_edges.append(edge)

            self._animate_node_entrance(graph_node, x_pos, y_pos, depth)

        self.setSceneRect(0.0, 0.0, max_x + 300.0, max_y + 100.0)

        if active_node_item:
            target_x, target_y, target_depth = positions[current_node_id]
            self._setup_focus_selector(target_x, target_y, target_depth)
            self.center_on_animated(active_node_item)

        self._evaluate_flow_timer_state()
        self._entrance_group.start()

    def _handle_node_clicked(self, node_id: str) -> None:
        if self.current_id != node_id:
            QTimer.singleShot(20, lambda: self.node_selected.emit(node_id))

    def _update_selection_in_place(self, nodes_dict: Dict[str, Any], new_node_id: str) -> None:
        if not self.nodes or not self.focus_selector:
            return

        old_pos: QPointF = self.focus_selector.pos()
        new_pos: Optional[QPointF] = None
        self.current_id = new_node_id
        active_path_set: set[str] = set(self._get_path_to_root(nodes_dict, new_node_id))
        active_node_item: Optional[GraphNode] = None

        for node in self.nodes:
            is_active: bool = node.node_id == new_node_id
            is_undone: bool = (node.node_id not in active_path_set) and (not is_active)
            if node.is_active != is_active or node.is_undone != is_undone:
                node.is_active = is_active
                node.is_undone = is_undone
                node._update_styling()
                node.update()

            if node.is_active:
                new_pos = node.pos()
                active_node_item = node

        self._active_edges.clear()
        for edge in self.edges:
            is_active_edge: bool = edge.target_node_id in active_path_set
            edge.set_active(is_active_edge)
            if is_active_edge:
                self._active_edges.append(edge)

        self._evaluate_flow_timer_state()

        if old_pos is not None and new_pos is not None and old_pos != new_pos:
            if self._pill_animation:
                self._pill_animation.stop()

            self._pill_animation = QPropertyAnimation(self.focus_selector, b"animated_pos", self)
            self._pill_animation.setDuration(400)
            self._pill_animation.setStartValue(old_pos)
            self._pill_animation.setEndValue(new_pos)
            self._pill_animation.setEasingCurve(QEasingCurve.Type.OutBack)
            self._pill_animation.start()

        if active_node_item is not None:
            self.center_on_animated(active_node_item)
