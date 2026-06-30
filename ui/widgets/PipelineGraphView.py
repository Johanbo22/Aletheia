from typing import Any, Callable, Dict, List, Optional

from PyQt6.QtCore import QEasingCurve, QParallelAnimationGroup, QPoint, QPointF, QPropertyAnimation, QRectF, \
    QSequentialAnimationGroup, QTimer, QVariantAnimation, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QFontMetrics, QKeyEvent, QMouseEvent, QPainter, QPainterPath, QPen, \
    QPixmap, QWheelEvent
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QGraphicsObject, QGraphicsPathItem, QGraphicsScene, \
    QGraphicsSceneContextMenuEvent, QGraphicsSceneHoverEvent, QGraphicsSceneMouseEvent, QGraphicsView, \
    QStyleOptionGraphicsItem, QWidget

OP_COLORS = {
    "origin"        : "#10b981",
    "filter"        : "#f59e0b",
    "cleaning"      : "#EF4444",
    "transformation": "#8b5cf6",
    "subset"        : "#06b6d4",
    "aggregation"   : "#f97316",
    "datetime"      : "#ec4899",
    "unknown"       : "#38b82f6"
}

class FlowEdgeItem(QGraphicsPathItem):
    """Custom path item that renders a solid base and an animated flowing dashed line on top for active paths"""

    def __init__(self, path: QPainterPath, target_node_id: str, is_active_path: bool, parent=None) -> None:
        super().__init__(path, parent)
        self.target_node_id = target_node_id
        self.is_active_path = is_active_path
        self.dash_offset = 0.0
        self.setZValue(-2)

        self._update_pens()

    def _update_pens(self) -> None:
        if self.is_active_path:
            self.base_pen = QPen(QColor("#93c5fd"), 2.5, Qt.PenStyle.SolidLine)
            self.flow_pen = QPen(QColor("#2563eb"), 2.5, Qt.PenStyle.CustomDashLine)
            self.flow_pen.setDashPattern([3, 12])
        else:
            self.base_pen = QPen(QColor("#cbd5e1"), 2.0, Qt.PenStyle.DashLine)
            self.flow_pen = None

    def set_active(self, is_active: bool) -> None:
        if self.is_active_path != is_active:
            self.is_active_path = is_active
            self._update_pens()
            self.update()

    def advance_flow(self, delta: float) -> None:
        """Called by view timer to animate the flow offset"""
        if self.is_active_path and self.flow_pen:
            self.dash_offset -= delta
            if self.dash_offset < -1000:
                self.dash_offset += 1000
            self.flow_pen.setDashOffset(self.dash_offset)
            self.update()

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(self.base_pen)
        painter.drawPath(self.path())

        if self.is_active_path and self.flow_pen:
            painter.setPen(self.flow_pen)
            painter.drawPath(self.path())

class FocusHighlightItem(QGraphicsObject):
    def __init__(self, width: float, height: float, parent=None):
        super().__init__(parent)
        self.width = width
        self.height = height

        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setColor(QColor(0, 0, 0, 30))
        self.shadow.setBlurRadius(18)
        self.shadow.setOffset(0, 5)
        self.setGraphicsEffect(self.shadow)
        self.setZValue(-1)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width, self.height)

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

    def paint(self, painter: QPainter, option, widget) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), 8, 8)

        painter.fillPath(path, QBrush(QColor("#EFF6FF")))
        painter.setPen(QPen(QColor("#3b82f6"), 1.5))
        painter.drawPath(path)

class GraphNode(QGraphicsObject):
    clicked = pyqtSignal(str)
    hover_entered = pyqtSignal(str)
    hover_left = pyqtSignal(str)
    context_menu_requested = pyqtSignal(str, QPoint)

    def __init__(self, node_id: str, label: str, operation: dict, is_active: bool, is_undone: bool, parent=None):
        super().__init__(parent)
        self.node_id = node_id
        self.label = label
        self.operation = operation
        self.is_active = is_active
        self.is_undone = is_undone
        self.is_hovered = False

        self.op_type = self.operation.get("type", "unknown").lower() if self.operation else "origin"

        self.width = 260.0
        self.height = 48.0

        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Cache node rendering to prevent repaint during scrolling
        self.setCacheMode(QGraphicsObject.CacheMode.DeviceCoordinateCache)
        # Setting origin to center for better animation
        self.setTransformOriginPoint(self.width / 2.0, self.height / 2.0)

        if self.operation:
            details = "".join(f"<li><b>{k}</b>: {v}</li>" for k, v in self.operation.items() if k != "type")
            self.setToolTip(
                f"<div style='padding: 4px; color: #F8FAFC;'>"
                f"<b style='color: #FFFFFF; font-size: 13px;'>{self.label}</b><br><br>"
                f"<b>Operation Details:</b><br>"
                f"<ul style='margin-top: 4px; margin-bottom: 0px;'>{details}</ul>"
                f"</div>"
            )
        else:
            self.setToolTip(
                f"<div style='color: #F8FAFC;'>"
                f"<b style='color: #FFFFFF; font-size: 13px;'>{self.label}</b><br><br>"
                f"Original imported data state</div>"
            )

        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setColor(QColor(0, 0, 0, 25))
        self.setGraphicsEffect(self.shadow)

        self._update_styling()

    def boundingRect(self) -> QRectF:
        """Required for QGraphicsObject rendering and collision."""
        return QRectF(0, 0, self.width, self.height)

    def shape(self) -> QPainterPath:
        """Provides precise bounds for hover and click detection."""
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), 8, 8)
        return path

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

    def _update_styling(self):
        """Updates colors and shadow elevation based on state and hover."""
        base_dot = QColor(OP_COLORS.get(self.op_type, OP_COLORS["unknown"]))

        if self.is_active:
            self.bg_color = QColor(219, 234, 254, 150) if self.is_hovered else QColor(Qt.GlobalColor.transparent)
            self.border_color = QColor(Qt.GlobalColor.transparent)
            self.text_color = QColor("#1E3A8A")
            self.dot_color = base_dot
            self.shadow.setEnabled(False)
        elif self.is_undone:
            self.bg_color = QColor("#F8FAFC") if not self.is_hovered else QColor("#F1F5F9")
            self.border_color = QColor("#CBD5E1")
            self.text_color = QColor("#94A3B8")
            self.dot_color = self.border_color
            self.shadow.setEnabled(self.is_hovered)
        else:
            self.bg_color = QColor("#FFFFFF") if not self.is_hovered else QColor("#F8FAFC")
            self.border_color = QColor("#94A3B8")
            self.text_color = QColor("#334155")
            self.dot_color = base_dot
            self.shadow.setEnabled(True)

        if not self.is_active:
            if self.is_hovered:
                self.shadow.setBlurRadius(18)
                self.shadow.setOffset(0, 5)
            else:
                self.shadow.setBlurRadius(10)
                self.shadow.setOffset(0, 3)

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent):
        self.is_hovered = True
        self._update_styling()
        self.update()
        self.hover_entered.emit(self.node_id)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent):
        self.is_hovered = False
        self._update_styling()
        self.update()
        self.hover_left.emit(self.node_id)
        super().hoverLeaveEvent(event)

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        self.context_menu_requested.emit(self.node_id, event.screenPos())
        event.accept()

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setScale(0.98)
            if self.shadow.isEnabled():
                self.shadow.setOffset(0, 1)
                self.shadow.setBlurRadius(4)
                self.update()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setScale(1.0)
            self._update_styling()
            self.update()

            if self.boundingRect().contains(event.pos()):
                self.clicked.emit(self.node_id)

            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def paint(self, painter: QPainter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), 8, 8)

        painter.fillPath(path, QBrush(self.bg_color))

        pen = QPen(self.border_color, 1.5)
        if self.is_undone and not self.is_active:
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawPath(path)

        dot_radius = 4.5
        dot_x = 18.0
        dot_y = self.height / 2

        painter.setBrush(QBrush(self.dot_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(dot_x, dot_y), dot_radius, dot_radius)

        if self.is_active:
            badge_w, badge_h = 44, 18
            badge_x = self.width - badge_w - 10
            badge_y = (self.height - badge_h) / 2

            badge_path = QPainterPath()
            badge_path.addRoundedRect(QRectF(badge_x, badge_y, badge_w, badge_h), 6, 6)
            painter.fillPath(badge_path, QBrush(QColor("#DBEAFE")))

            painter.setFont(QFont("Inter", 8, QFont.Weight.Bold))
            painter.setPen(QColor("#1D4ED8"))
            painter.drawText(QRectF(badge_x, badge_y, badge_w, badge_h), Qt.AlignmentFlag.AlignCenter, "Active")

        font = QFont("Inter", 9)
        if self.is_active:
            font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(self.text_color)

        metrics = QFontMetrics(font)
        text_width_limit = int(self.width - 95) if self.is_active else int(self.width - 45)
        elided_text = metrics.elidedText(self.label, Qt.TextElideMode.ElideRight, text_width_limit)

        text_rect = metrics.boundingRect(elided_text)
        x = 34.0
        y = (self.height + text_rect.height()) / 2 - metrics.descent()

        painter.drawText(QPointF(x, y), elided_text)

class PipelineGraphView(QGraphicsView):
    """A visual node-based representation of the data transformation history."""
    node_selected = pyqtSignal(str)
    node_context_menu = pyqtSignal(str, QPoint)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.graph_scene = QGraphicsScene(self)
        self.setScene(self.graph_scene)

        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.TextAntialiasing |
            QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)

        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setObjectName("PipelineGraphView")
        self.setProperty("styleClass", "transparent_scroll_area")

        self.nodes: List[GraphNode] = []
        self.edges: List[FlowEdgeItem] = []
        self.focus_selector = None
        self.current_id = ""
        self._scroll_animation = None
        self._pill_animation = None

        self._zoom_level: int = 0
        self._zoom_min: int = -4
        self._zoom_max: int = 6

        self._is_middle_dragging: bool = False
        self._last_mouse_pos: Optional[QPointF] = None
        self._middle_click_pos: Optional[QPointF] = None

        self._background_brush: Optional[QBrush] = None
        self._create_background_brush()

        self._flow_timer = QTimer(self)
        self._flow_timer.timeout.connect(self._advance_edge_flow)
        self._flow_timer.start(40)

        self._current_nodes_dict: Dict[str, Any] = {}
        self._focused_path: List[str] = []
        self._current_fade_factor: float = 0.0

        focus_animation_duration: int = 250
        self._focus_anim = QVariantAnimation(self)
        self._focus_anim.setDuration(focus_animation_duration)
        self._focus_anim.valueChanged.connect(self._apply_focus_fade)

        self._entrance_group = QParallelAnimationGroup(self)

    def _apply_focus_fade(self, factor: float) -> None:
        """Drives the opacity of non-focused elements to dimmer"""
        self._current_fade_factor = factor
        dim_node_op = 1.0 - (0.7 * factor)
        dim_edge_op = 1.0 - (0.85 * factor)

        for node in self.nodes:
            if node.node_id not in self._focused_path:
                node.setOpacity(dim_node_op)
        for edge in self.edges:
            if edge.target_node_id not in self._focused_path:
                edge.setOpacity(dim_edge_op)

    def _on_node_hover_entered(self, node_id: str) -> None:
        if self._entrance_group.state() == QPropertyAnimation.State.Running:
            return

        self._focused_path = self._get_path_to_root(self._current_nodes_dict, node_id)
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
        grid_size = 20
        dot_radius = 1.0

        pixmap = QPixmap(grid_size, grid_size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#CBD5E1"))
        painter.drawEllipse(QPointF(grid_size / 2.0, grid_size / 2.0), dot_radius, dot_radius)
        painter.end()

        self._background_brush = QBrush(pixmap)

    def _set_view_center(self, center: QPointF):
        self.centerOn(center)

    def _get_view_center(self) -> QPointF:
        return self.mapToScene(self.viewport().rect().center())

    viewCenter = pyqtProperty(QPointF, fget=_get_view_center, fset=_set_view_center)

    def center_on_animated(self, item: QGraphicsObject):
        if self._scroll_animation:
            self._scroll_animation.stop()

        self._scroll_animation = QPropertyAnimation(self, b"viewCenter", self)
        self._scroll_animation.setDuration(500)
        self._scroll_animation.setStartValue(self.viewCenter)
        self._scroll_animation.setEndValue(item.sceneBoundingRect().center())
        self._scroll_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._scroll_animation.start()

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        """Paints the background using cached brush"""
        painter.fillRect(rect, QColor("#F8FAFC"))
        if self._background_brush:
            painter.fillRect(rect, self._background_brush)

    def _get_path_to_root(self, nodes_dict: Dict[str, Any], start_node_id: str) -> List[str]:
        """Helper to trace the path back to the root node."""
        path = []
        curr = start_node_id
        while curr:
            path.append(curr)
            node = nodes_dict.get(curr)
            curr = node.parent_id if node else None
        return path

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            zoom_in_factor = 1.15
            zoom_out_factor = 1.0 / zoom_in_factor

            is_zooming_in = event.angleDelta().y() > 0

            if is_zooming_in and self._zoom_level >= self._zoom_max:
                return
            if not is_zooming_in and self._zoom_level <= self._zoom_min:
                return

            old_scene_pos = self.mapToScene(event.position().toPoint())

            if is_zooming_in:
                self._zoom_level += 1
                self.scale(zoom_in_factor, zoom_in_factor)
            else:
                self._zoom_level -= 1
                self.scale(zoom_out_factor, zoom_out_factor)

            new_scene_pos = self.mapToScene(event.position().toPoint())
            delta = new_scene_pos - old_scene_pos
            self.translate(delta.x(), delta.y())

            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_middle_dragging = True
            self._last_mouse_pos = event.position()
            self._middle_click_pos = event.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_middle_dragging and self._last_mouse_pos is not None:
            delta = event.position() - self._last_mouse_pos

            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()

            h_bar.setValue(int(h_bar.value() - delta.x()))
            v_bar.setValue(int(v_bar.value() - delta.y()))

            self._last_mouse_pos = event.position()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton and self._is_middle_dragging:
            self._is_middle_dragging = False
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

            if self._middle_click_pos is not None:
                distance = (event.position() - self._middle_click_pos).manhattanLength()
                if distance < 5.0:
                    self.resetTransform()
                    if self.nodes and 0 <= self.current_index < len(self.nodes):
                        self.center_on_animated(self.nodes[self.current_index])

            self._last_mouse_pos = None
            self._middle_click_pos = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_F:
            scene_rect = self.graph_scene.itemsBoundingRect()
            scene_rect.adjust(-20, -20, 20, 20)
            self.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)
            event.accept()
        else:
            super().keyPressEvent(event)

    def build_graph(self, nodes_dict: Dict[str, Any], root_id: str, current_node_id: str, format_func: Callable):
        """Constructs nodes and paths for the entire operation pipeline."""
        if len(self.nodes) == len(nodes_dict):
            self._update_selection_in_place(nodes_dict, current_node_id)
            return

        self._current_nodes_dict = nodes_dict
        self.graph_scene.clear()
        self.nodes.clear()
        self.edges.clear()
        self.focus_selector = None

        self.current_id = current_node_id
        active_node_item = None

        vertical_spacing = 75.0
        horizontal_spacing = 300.0

        positions = {}

        def calculate_positions(node_id: str, depth: int, branch_index: int):
            x_pos = 20.0 + (branch_index * horizontal_spacing)
            y_pos = 20.0 + (depth * vertical_spacing)
            positions[node_id] = (x_pos, y_pos, depth)

            node_data = nodes_dict.get(node_id)
            if not node_data:
                return

            for i, child_id in enumerate(node_data.children_ids):
                child_branch = branch_index if i == len(node_data.children_ids) - 1 else branch_index + (i + 1)
                calculate_positions(child_id, depth + 1, child_branch)

        calculate_positions(root_id, depth=0, branch_index=0)

        max_x, max_y = 0.0, 0.0
        self._entrance_group.clear()

        for node_id, (x_pos, y_pos, depth) in positions.items():
            node_data = nodes_dict[node_id]
            is_active = (node_id == current_node_id)
            is_undone = node_id not in self._get_path_to_root(nodes_dict,
                                                              current_node_id) and node_id != current_node_id

            label = "Initial Data" if node_id == root_id else format_func(node_data.diff_record.metadata)
            graph_node = GraphNode(node_id, label, getattr(node_data.diff_record, 'metadata', {}), is_active, is_undone)

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

            max_x = max(max_x, x_pos)
            max_y = max(max_y, y_pos)

            if node_data.parent_id and node_data.parent_id in positions:
                px, py, _ = positions[node_data.parent_id]
                path = QPainterPath()

                start_pt = QPointF(px + graph_node.width / 2, py + graph_node.height)
                end_pt = QPointF(x_pos + graph_node.width / 2, y_pos)

                path.moveTo(start_pt)
                ctrl1 = QPointF(start_pt.x(), start_pt.y() + (vertical_spacing / 2))
                ctrl2 = QPointF(end_pt.x(), end_pt.y() - (vertical_spacing / 2))
                path.cubicTo(ctrl1, ctrl2, end_pt)

                is_active_path = is_active or node_id in self._get_path_to_root(nodes_dict, current_node_id)
                edge = FlowEdgeItem(path, node_id, is_active_path)

                self.graph_scene.addItem(edge)
                self.edges.append(edge)

            anim_pos = QPropertyAnimation(graph_node, b"animated_pos")
            anim_pos.setStartValue(QPointF(x_pos, y_pos + 20))
            anim_pos.setEndValue(QPointF(x_pos, y_pos))
            anim_pos.setDuration(450)
            anim_pos.setEasingCurve(QEasingCurve.Type.OutBack)

            anim_op = QPropertyAnimation(graph_node, b"animated_opacity")
            anim_op.setStartValue(0.0)
            anim_op.setEndValue(1.0)
            anim_op.setDuration(350)

            node_anim_group = QParallelAnimationGroup(self)
            node_anim_group.addAnimation(anim_pos)
            node_anim_group.addAnimation(anim_op)

            delay = depth * 60
            if delay > 0:
                seq_group = QSequentialAnimationGroup(self)
                seq_group.addPause(delay)
                seq_group.addAnimation(node_anim_group)
                self._entrance_group.addAnimation(seq_group)
            else:
                self._entrance_group.addAnimation(node_anim_group)

        self.setSceneRect(0, 0, max_x + 300, max_y + 100)

        if active_node_item:
            target_x, target_y, target_depth = positions[current_node_id]
            self.focus_selector = FocusHighlightItem(260.0, 48.0)

            start_pos = QPointF(target_x, target_y + 20)
            end_pos = QPointF(target_x, target_y)

            self.focus_selector.setPos(start_pos)
            self.focus_selector.setOpacity(0.0)
            self.graph_scene.addItem(self.focus_selector)

            anim_pill_pos = QPropertyAnimation(self.focus_selector, b"animated_pos")
            anim_pill_pos.setStartValue(start_pos)
            anim_pill_pos.setEndValue(end_pos)
            anim_pill_pos.setDuration(450)
            anim_pill_pos.setEasingCurve(QEasingCurve.Type.OutBack)

            anim_pill_op = QPropertyAnimation(self.focus_selector, b"animated_opacity")
            anim_pill_op.setStartValue(0.0)
            anim_pill_op.setEndValue(1.0)
            anim_pill_op.setDuration(350)

            pill_group = QParallelAnimationGroup(self)
            pill_group.addAnimation(anim_pill_pos)
            pill_group.addAnimation(anim_pill_op)

            delay = target_depth * 60
            if delay > 0:
                seq_group = QSequentialAnimationGroup(self)
                seq_group.addPause(delay)
                seq_group.addAnimation(pill_group)
                self._entrance_group.addAnimation(seq_group)
            else:
                self._entrance_group.addAnimation(pill_group)

            self.center_on_animated(active_node_item)

        self._entrance_group.start()

    def _handle_node_clicked(self, node_id: str) -> None:
        if self.current_id != node_id:
            QTimer.singleShot(20, lambda: self.node_selected.emit(node_id))

    def _update_selection_in_place(self, nodes_dict: Dict[str, Any], new_node_id: str):
        if not self.nodes or not self.focus_selector:
            return

        old_pos = self.focus_selector.pos()
        new_pos = None
        self.current_id = new_node_id

        active_path = self._get_path_to_root(nodes_dict, new_node_id)

        for node in self.nodes:
            node.is_active = (node.node_id == new_node_id)
            node.is_undone = (node.node_id not in active_path and node.node_id != new_node_id)
            node._update_styling()
            node.update()

            if node.is_active:
                new_pos = node.pos()

        for edge in self.edges:
            is_active_path: bool = (edge.target_node_id in active_path) or (edge.target_node_id == new_node_id)
            edge.set_active(is_active_path)

        if old_pos is not None and new_pos is not None and old_pos != new_pos:
            if self._pill_animation:
                self._pill_animation.stop()

            self._pill_animation = QPropertyAnimation(self.focus_selector, b"animated_pos", self)
            self._pill_animation.setDuration(500)
            self._pill_animation.setStartValue(old_pos)
            self._pill_animation.setEndValue(new_pos)
            self._pill_animation.setEasingCurve(QEasingCurve.Type.OutBack)
            self._pill_animation.start()

        for node in self.nodes:
            if node.node_id == new_node_id:
                self.center_on_animated(node)
                break
