from dataclasses import dataclass

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import QWidget

from src.ui.help_animation_engine import HelpAnimationEngine

@dataclass(frozen=True)
class HistoryNodeSpec:
    node_id: str
    hash_str: str
    label: str
    rect: QRectF
    dot_color: QColor
    parent_id: str

@dataclass(frozen=True)
class NodeRenderStyle:
    bg_color: QColor
    border_pen: QPen
    hash_color: QColor
    label_color: QColor
    dot_color: QColor
    badge_opacity: float

# Layout and Timing Constants
ANIMATION_DURATION_MS: int = 9000
ANIMATION_FPS: int = 60
GRID_SPACING: int = 20
NODE_WIDTH: float = 165.0
NODE_HEIGHT: float = 44.0
NODE_RADIUS: float = 6.0
BADGE_WIDTH: float = 42.0
BADGE_HEIGHT: float = 16.0
DOT_RADIUS: float = 4.0

class Animation(HelpAnimationEngine):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            parent,
            fps=ANIMATION_FPS,
            duration_ms=ANIMATION_DURATION_MS
        )

        self.c_bg: QColor = QColor("#2b2b2b")
        self.c_grid_dot: QColor = QColor("#3d3d3d")
        self.c_node_bg: QColor = QColor("#1e1e1e")
        self.c_node_active_bg: QColor = QColor("#1e293b")
        self.c_border_in_path: QColor = QColor("#64748b")
        self.c_border_active: QColor = QColor("#3b82f6")
        self.c_border_undone: QColor = QColor("#444444")

        self.c_text_main: QColor = QColor("#e0e0e0")
        self.c_text_active: QColor = QColor("#93c5fd")
        self.c_text_undone: QColor = QColor("#777777")
        self.c_hash_active: QColor = QColor("#60a5fa")
        self.c_hash_inactive: QColor = QColor("#888888")

        self.c_badge_bg: QColor = QColor("#1d4ed8")
        self.c_badge_text: QColor = QColor("#ffffff")

        self.c_edge_active_base: QColor = QColor("#93c5fd")
        self.c_edge_flow: QColor = QColor("#2563eb")
        self.c_edge_inactive: QColor = QColor("#555555")

        self.c_dot_origin: QColor = QColor("#10b981")
        self.c_dot_filter: QColor = QColor("#f59e0b")
        self.c_dot_undone: QColor = QColor("#555555")

        self.font_hash: QFont = QFont("Consolas", 7)
        self.font_badge: QFont = QFont("Segoe UI", 7, QFont.Weight.Bold)
        self.font_label: QFont = QFont("Segoe UI", 8)
        self.font_label_bold: QFont = QFont("Segoe UI", 8, QFont.Weight.Bold)

        self.nodes: dict[str, HistoryNodeSpec] = self._build_node_specs()

    def _build_node_specs(self) -> dict[str, HistoryNodeSpec]:
        return {
            "root"   : HistoryNodeSpec(
                node_id="root",
                hash_str="eb0c40f1",
                label="Initial Data",
                rect=QRectF(20.0, 25.0, NODE_WIDTH, NODE_HEIGHT),
                dot_color=self.c_dot_origin,
                parent_id=""
            ),
            "europe" : HistoryNodeSpec(
                node_id="europe",
                hash_str="502a4df7",
                label="Filter: 'Europe'",
                rect=QRectF(20.0, 115.0, NODE_WIDTH, NODE_HEIGHT),
                dot_color=self.c_dot_filter,
                parent_id="root"
            ),
            "africa" : HistoryNodeSpec(
                node_id="africa",
                hash_str="4292fb79",
                label="Filter: 'Africa'",
                rect=QRectF(195.0, 115.0, NODE_WIDTH, NODE_HEIGHT),
                dot_color=self.c_dot_filter,
                parent_id="root"
            ),
            "east"   : HistoryNodeSpec(
                node_id="east",
                hash_str="147ae99f",
                label="Filter: 'East...'",
                rect=QRectF(195.0, 205.0, NODE_WIDTH, NODE_HEIGHT),
                dot_color=self.c_dot_filter,
                parent_id="africa"
            ),
            "central": HistoryNodeSpec(
                node_id="central",
                hash_str="ed3b4b7e",
                label="Filter: 'Central'",
                rect=QRectF(365.0, 205.0, NODE_WIDTH, NODE_HEIGHT),
                dot_color=self.c_dot_filter,
                parent_id="africa"
            ),
        }

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        painter.fillRect(self.rect(), self.c_bg)
        self._draw_dot_grid(painter)

        p_switch_1: float = self.get_eased_progress(progress, 0.25, 0.40)
        p_switch_2: float = self.get_eased_progress(progress, 0.60, 0.75)
        dash_offset: float = -(progress * 180.0)

        self._draw_all_edges(painter, p_switch_1, p_switch_2, dash_offset)
        self._draw_all_nodes(painter, p_switch_1, p_switch_2)
        self._draw_cursor_and_clicks(painter, progress, p_switch_1, p_switch_2)
        self._draw_caption(painter, progress)

    def _draw_dot_grid(self, painter: QPainter) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.c_grid_dot)

        width: int = self.width()
        height: int = self.height() - 45
        radius: float = 1.0

        for x in range(10, width, GRID_SPACING):
            for y in range(10, height, GRID_SPACING):
                painter.drawEllipse(QPointF(float(x), float(y)), radius, radius)

    @staticmethod
    def _get_node_weights(
            node_id: str,
            p_switch_1: float,
            p_switch_2: float
    ) -> tuple[float, float]:
        if node_id == "root":
            return 0.0, 1.0
        if node_id == "east":
            weight: float = 1.0 - p_switch_1
            return weight, weight
        if node_id == "europe":
            weight = p_switch_1 * (1.0 - p_switch_2)
            return weight, weight
        if node_id == "africa":
            path_w: float = (1.0 - p_switch_1) + (p_switch_1 * p_switch_2)
            return 0.0, max(0.0, min(1.0, path_w))
        if node_id == "central":
            return p_switch_2, p_switch_2
        return 0.0, 0.0

    def _draw_all_edges(
            self,
            painter: QPainter,
            p_switch_1: float,
            p_switch_2: float,
            dash_offset: float
    ) -> None:
        for node_id, spec in self.nodes.items():
            if not spec.parent_id:
                continue
            parent_spec: HistoryNodeSpec = self.nodes[spec.parent_id]
            _, path_weight = self._get_node_weights(node_id, p_switch_1, p_switch_2)
            self._draw_single_edge(
                painter,
                parent_spec.rect,
                spec.rect,
                path_weight,
                dash_offset
            )

    def _draw_single_edge(
            self,
            painter: QPainter,
            parent_rect: QRectF,
            child_rect: QRectF,
            path_weight: float,
            dash_offset: float
    ) -> None:
        start_pt = QPointF(parent_rect.center().x(), parent_rect.bottom())
        end_pt = QPointF(child_rect.center().x(), child_rect.top())
        mid_y: float = (start_pt.y() + end_pt.y()) / 2.0

        path = QPainterPath()
        path.moveTo(start_pt)
        path.cubicTo(
            QPointF(start_pt.x(), mid_y),
            QPointF(end_pt.x(), mid_y),
            end_pt
        )

        painter.setBrush(Qt.BrushStyle.NoBrush)

        if path_weight < 1.0:
            inactive_pen = QPen(self.c_edge_inactive, 1.8, Qt.PenStyle.DashLine)
            painter.setPen(inactive_pen)
            painter.drawPath(path)

        if path_weight > 0.01:
            painter.save()
            painter.setOpacity(path_weight)

            base_pen = QPen(self.c_edge_active_base, 2.5, Qt.PenStyle.SolidLine)
            painter.setPen(base_pen)
            painter.drawPath(path)

            flow_pen = QPen(self.c_edge_flow, 2.5, Qt.PenStyle.CustomDashLine)
            flow_pen.setDashPattern([3.0, 9.0])
            flow_pen.setDashOffset(dash_offset)
            painter.setPen(flow_pen)
            painter.drawPath(path)

            painter.restore()

    def _draw_all_nodes(
            self,
            painter: QPainter,
            p_switch_1: float,
            p_switch_2: float
    ) -> None:
        for node_id, spec in self.nodes.items():
            active_w, path_w = self._get_node_weights(node_id, p_switch_1, p_switch_2)
            style: NodeRenderStyle = self._compute_node_style(spec, active_w, path_w)
            self._draw_single_node(painter, spec, style, active_w > 0.5)

    def _compute_node_style(
            self,
            spec: HistoryNodeSpec,
            active_w: float,
            path_w: float
    ) -> NodeRenderStyle:
        bg_color: QColor = self.lerp_color(
            self.c_node_bg,
            self.c_node_active_bg,
            active_w
        )
        border_color: QColor = self.lerp_color(
            self.c_border_undone,
            self.c_border_in_path,
            path_w
        )
        border_color = self.lerp_color(border_color, self.c_border_active, active_w)

        pen_style: Qt.PenStyle = (
            Qt.PenStyle.DashLine if path_w < 0.5 else Qt.PenStyle.SolidLine
        )
        pen_width: float = 2.0 if active_w > 0.5 else 1.5
        border_pen = QPen(border_color, pen_width, pen_style)

        hash_color: QColor = self.lerp_color(
            self.c_hash_inactive,
            self.c_hash_active,
            active_w
        )
        label_color: QColor = self.lerp_color(
            self.c_text_undone,
            self.c_text_main,
            path_w
        )
        label_color = self.lerp_color(label_color, self.c_text_active, active_w)

        dot_color: QColor = self.lerp_color(
            self.c_dot_undone,
            spec.dot_color,
            path_w
        )

        return NodeRenderStyle(
            bg_color=bg_color,
            border_pen=border_pen,
            hash_color=hash_color,
            label_color=label_color,
            dot_color=dot_color,
            badge_opacity=active_w
        )

    def _draw_single_node(
            self,
            painter: QPainter,
            spec: HistoryNodeSpec,
            style: NodeRenderStyle,
            is_bold: bool
    ) -> None:
        rect: QRectF = spec.rect
        painter.setBrush(style.bg_color)
        painter.setPen(style.border_pen)
        painter.drawRoundedRect(rect, NODE_RADIUS, NODE_RADIUS)

        painter.setFont(self.font_hash)
        painter.setPen(style.hash_color)
        painter.drawText(QPointF(rect.left() + 8.0, rect.top() + 12.0), spec.hash_str)

        dot_center = QPointF(rect.left() + 13.0, rect.top() + 29.0)
        painter.setBrush(style.dot_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(dot_center, DOT_RADIUS, DOT_RADIUS)

        painter.setFont(self.font_label_bold if is_bold else self.font_label)
        painter.setPen(style.label_color)
        label_rect = QRectF(
            rect.left() + 24.0,
            rect.top() + 18.0,
            rect.width() - 30.0,
            22.0
        )
        painter.drawText(
            label_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            spec.label
        )

        if style.badge_opacity > 0.01:
            self._draw_active_badge(painter, rect, style.badge_opacity)

    def _draw_active_badge(
            self,
            painter: QPainter,
            node_rect: QRectF,
            opacity: float
    ) -> None:
        painter.save()
        painter.setOpacity(opacity)

        badge_rect = QRectF(
            node_rect.right() - BADGE_WIDTH - 6.0,
            node_rect.top() + 6.0,
            BADGE_WIDTH,
            BADGE_HEIGHT
        )
        painter.setBrush(self.c_badge_bg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(badge_rect, 4.0, 4.0)

        painter.setFont(self.font_badge)
        painter.setPen(self.c_badge_text)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "Active")

        painter.restore()

    def _draw_cursor_and_clicks(
            self,
            painter: QPainter,
            progress: float,
            p_switch_1: float,
            p_switch_2: float
    ) -> None:
        pt_east: QPointF = self.nodes["east"].rect.center()
        pt_europe: QPointF = self.nodes["europe"].rect.center()
        pt_central: QPointF = self.nodes["central"].rect.center()

        move_1: float = self.get_eased_progress(progress, 0.12, 0.25)
        move_2: float = self.get_eased_progress(progress, 0.48, 0.60)

        if progress < 0.45:
            cursor_x: float = pt_east.x() + (pt_europe.x() - pt_east.x()) * move_1
            cursor_y: float = pt_east.y() + (pt_europe.y() - pt_east.y()) * move_1
        else:
            cursor_x = pt_europe.x() + (pt_central.x() - pt_europe.x()) * move_2
            cursor_y = pt_europe.y() + (pt_central.y() - pt_europe.y()) * move_2

        cursor_pos = QPointF(cursor_x + 20.0, cursor_y + 8.0)

        if 0.0 < p_switch_1 < 1.0:
            self._draw_click_ripple(painter, cursor_pos, p_switch_1)
        if 0.0 < p_switch_2 < 1.0:
            self._draw_click_ripple(painter, cursor_pos, p_switch_2)

        self._draw_cursor_arrow(painter, cursor_pos)

    def _draw_click_ripple(
            self,
            painter: QPainter,
            center: QPointF,
            ripple_prog: float
    ) -> None:
        painter.save()
        radius: float = 4.0 + (18.0 * ripple_prog)
        alpha: float = 1.0 - ripple_prog

        color = QColor(self.c_border_active)
        color.setAlphaF(alpha)

        painter.setPen(QPen(color, 2.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius, radius)
        painter.restore()

    @staticmethod
    def _draw_cursor_arrow(painter: QPainter, tip: QPointF) -> None:
        painter.save()
        poly = QPolygonF([
            tip,
            QPointF(tip.x(), tip.y() + 15.0),
            QPointF(tip.x() + 4.0, tip.y() + 11.5),
            QPointF(tip.x() + 7.5, tip.y() + 17.5),
            QPointF(tip.x() + 9.5, tip.y() + 16.5),
            QPointF(tip.x() + 6.0, tip.y() + 10.5),
            QPointF(tip.x() + 11.0, tip.y() + 10.5),
        ])
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#111111"), 1.2))
        painter.drawPolygon(poly)
        painter.restore()

    def _draw_caption(self, painter: QPainter, progress: float) -> None:
        painter.setFont(self.font_main)
        painter.setPen(self.c_text_main)

        if progress < 0.22:
            text = "Active path flows from 'Initial Data' to the 'Active' node."
        elif progress < 0.55:
            text = "Click any node to jump directly to another branch."
        else:
            text = "Each branch preserves a unique sequence of operations."

        caption_rect = QRectF(0.0, 295.0, float(self.width()), 30.0)
        painter.drawText(caption_rect, Qt.AlignmentFlag.AlignCenter, text)
