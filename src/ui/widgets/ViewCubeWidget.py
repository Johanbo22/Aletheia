import math
from typing import Optional, Tuple

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QMouseEvent, QPaintEvent, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QWidget

class ViewCubeWidget(QWidget):
    """
    A custom widget that renders an interactive 3D ViewCube.
    This widget provides visual feedback of the current camera orientation and allows
    to interactively rotate a 3D plot by dragging or clicking faces to snap

    Signals emitted:
        view_angle_changed(azimuth, elevation): emitted when the drag is released or a face is clicked
    """

    faceColorX = pyqtProperty(QColor)
    faceColorY = pyqtProperty(QColor)
    faceColorZ = pyqtProperty(QColor)

    view_angle_changed = pyqtSignal(float, float)

    DEFAULT_FACE_X = QColor(200, 100, 100, 255)
    DEFAULT_FACE_Y = QColor(100, 200, 100, 255)
    DEFAULT_FACE_Z = QColor(100, 100, 200, 255)

    CUBE_SIZE = 120
    FACE_PADDING = 4

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(140, 140)

        self._faceColorX = QColor(self.DEFAULT_FACE_X)
        self._faceColorY = QColor(self.DEFAULT_FACE_Y)
        self._faceColorZ = QColor(self.DEFAULT_FACE_Z)

        self._azimuth = -60.0
        self._elevation = 30.0

        self._target_azimuth = self._azimuth
        self._target_elevation = self._elevation

        self.is_dragging = False
        self._last_mouse_pos: Optional[Tuple[int, int]] = None
        self._clicked_face: Optional[str] = None

        self._hovered_face: Optional[str] = None
        self._drawn_faces: list[Tuple[str, QPolygonF]] = []

        self._home_rect = QRectF()
        self._hovered_home = False

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(self.CUBE_SIZE + 50, self.CUBE_SIZE + 50)

        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setObjectName("viewCube")

        self.setProperty("faceColorX", self._faceColorX)
        self.setProperty("faceColorY", self._faceColorY)
        self.setProperty("faceColorZ", self._faceColorZ)

    ###
    ### Getters for face colors
    ###

    def getFaceColorX(self) -> QColor:
        return self._faceColorX

    def setFaceColorX(self, color: QColor) -> None:
        if self._faceColorX != color:
            self._faceColorX = QColor(color)
            self.update()

    def getFaceColorY(self) -> QColor:
        return self._faceColorY

    def setFaceColorY(self, color: QColor) -> None:
        if self._faceColorY != color:
            self._faceColorY = QColor(color)
            self.update()

    def getFaceColorZ(self) -> QColor:
        return self._faceColorZ

    def setFaceColorZ(self, color: QColor) -> None:
        if self._faceColorZ != color:
            self._faceColorZ = QColor(color)
            self.update()

    faceColorX = pyqtProperty(QColor, fget=getFaceColorX, fset=setFaceColorX)
    faceColorY = pyqtProperty(QColor, fget=getFaceColorY, fset=setFaceColorY)
    faceColorZ = pyqtProperty(QColor, fget=getFaceColorZ, fset=setFaceColorZ)

    ###
    ### ViewCube API
    ###

    def _project_3d_to_2d(self, x: float, y: float, z: float, cx: float, cy: float) -> Tuple[float, float, float]:
        """Projects 3D coordinates to a 2D plane based on current azimuth and elevation"""
        azimuth_radians = math.radians(self._azimuth)
        elevation_radians = math.radians(self._elevation)

        x1 = x * math.cos(azimuth_radians) - y * math.sin(azimuth_radians)
        y1 = x * math.sin(azimuth_radians) + y * math.cos(azimuth_radians)

        y2 = y1 * math.cos(elevation_radians) - z * math.sin(elevation_radians)
        z2 = y1 * math.sin(elevation_radians) + z * math.cos(elevation_radians)

        return cx + x1, cy - y2, z2

    def set_angles(self, azimuth: float, elevation: float, emit_signal: bool = False) -> None:
        """
        Update the ViewCube to reflect new camera angles

        :param azimuth: Azimuth angle in degrees
        :param elevation: Elevation angle in degrees
        :param emit_signal: If True, emit view_angle_changed signal
        """
        self._azimuth = azimuth % 360
        self._elevation = max(-90, min(90, elevation))
        self._target_azimuth = self._azimuth
        self._target_elevation = self._elevation
        self.update()

        if emit_signal:
            self.view_angle_changed.emit(self._azimuth, self._elevation)

    def get_angles(self) -> Tuple[float, float]:
        """Return current (azimuth, elevation) angles"""
        return self._azimuth, self._elevation

    def snap_to_face(self, face: str) -> None:
        """
        Snap to an orthographic view based on the clicked face.

        Face mappings:
            'Z+' (Top):     elevation = 90°, azimuth = -90°
            'Z-' (Bottom):  elevation = -90°, azimuth = -90°
            'Y+' (Front):   elevation = 0°, azimuth = 0°
            'Y-' (Back):    elevation = 0°, azimuth = 180°
            'X+' (Right):   elevation = 0°, azimuth = 90°
            'X-' (Left):    elevation = 0°, azimuth = -90°

        :param face: Face identifier ('X+', 'X-', 'Y+', 'Y-', 'Z+', 'Z-')
        """
        snap_angles = {
            'Z+': (-90, 90),
            'Z-': (-90, -90),
            'Y+': (0, 0),
            'Y-': (180, 0),
            'X+': (90, 0),
            'X-': (-90, 0),
        }

        if face in snap_angles:
            az, el = snap_angles[face]
            self.set_angles(az, el, emit_signal=True)

    ###
    ### Event Handlers
    ###

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press for dragging and face clicking"""
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._home_rect.contains(event.position()):
            self.set_angles(-60, 30, emit_signal=True)
            event.accept()
            return

        self.is_dragging = True
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self._last_mouse_pos = (event.position().x(), event.position().y())

        clicked_face = self._hit_test(event.position().x(), event.position().y())
        if clicked_face:
            self._clicked_face = clicked_face
        else:
            self._clicked_face = None

        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse drag to rotate the cube"""
        is_hovering_home: bool = self._home_rect.contains(event.position())
        if is_hovering_home != self._hovered_home:
            self._hovered_home = is_hovering_home
            if not self.is_dragging:
                self.setCursor(
                    Qt.CursorShape.PointingHandCursor
                    if is_hovering_home
                    else Qt.CursorShape.OpenHandCursor
                )
            self.update()

        if not self.is_dragging:
            current_hovered = self._hit_test(event.position().x(), event.position().y())
            if current_hovered != self._hovered_face:
                self._hovered_face = current_hovered
                self.update()

        if not self.is_dragging or self._last_mouse_pos is None:
            return

        current_x = event.position().x()
        current_y = event.position().y()

        dx = current_x - self._last_mouse_pos[0]
        dy = current_y - self._last_mouse_pos[1]

        if abs(dx) > 2 or abs(dy) > 2:
            self._clicked_face = None

        sensitivity = 0.5
        self._azimuth = (self._azimuth - dx * sensitivity) % 360
        self._elevation = max(-90, min(90, self._elevation + dy * sensitivity))

        self._last_mouse_pos = (current_x, current_y)
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release to finalize rotation or trigger snap"""
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if not self.is_dragging:
            event.accept()
            return

        self.is_dragging = False

        if self._hovered_home:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)

        if self._clicked_face:
            self.snap_to_face(self._clicked_face)
            self._clicked_face = None
        else:
            self.view_angle_changed.emit(self._azimuth, self._elevation)

        self._last_mouse_pos = None
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Double-clicking resets to default view"""
        if event.button() != Qt.MouseButton.LeftButton:
            return

        self.set_angles(-60, 30, emit_signal=True)
        event.accept()

    ###
    ### Painting: Contains the methods for drawing the cube, support axes  and also the collision detection for faces
    ###

    def paintEvent(self, event: QPaintEvent) -> None:
        """Render the 3D cube"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2

        self._draw_cube(painter, cx, cy)
        self._draw_axes(painter, 35.0, float(self.height() - 35))
        self._draw_home_icon(painter)

    def _draw_home_icon(self, painter: QPainter) -> None:
        """
        Draws a Home icon in the top right of the widget to reset the view with a button reset instead of mouseDoubleClickEvent signal
        """
        self._home_rect = QRectF(self.width() - 30, 10, 20, 20)

        is_hovered = getattr(self, "_hovered_home", False)
        color = QColor(30, 144, 255) if is_hovered else QColor(150, 150, 150, 180)

        painter.setPen(QPen(
            color, 2.0,
            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin
        ))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        cx = self._home_rect.center().x()
        cy = self._home_rect.center().y()

        painter.drawPolyline(QPolygonF([
            QPointF(cx - 7, cy + 1),
            QPointF(cx, cy - 6),
            QPointF(cx + 7, cy + 1),
        ]))
        painter.drawPolyline(QPolygonF([
            QPointF(cx - 5, cy),
            QPointF(cx - 5, cy + 7),
            QPointF(cx + 5, cy + 7),
            QPointF(cx + 5, cy),
        ]))

    def _draw_axes(self, painter: QPainter, cx: float, cy: float) -> None:
        """
        Draws a 3D axes triad that rotates in sync with the camera
        """
        azimuth_radians = math.radians(self._azimuth)
        elevation_radians = math.radians(self._elevation)

        axis_length: float = 20.0

        axes_3d = [
            ("X", (axis_length, 0, 0), QColor(255, 80, 80)),
            ("Y", (0, axis_length, 0), QColor(80, 255, 80)),
            ("Z", (0, 0, axis_length), QColor(80, 150, 255)),
        ]

        origin_x, origin_y, origin_z = self._project_3d_to_2d(0, 0, 0, cx, cy)

        projected = []
        for label, (x, y, z), color in axes_3d:
            px, py, pz = self._project_3d_to_2d(x, y, z, cx, cy)
            projected.append((label, px, py, pz, color))

        projected.sort(key=lambda item: item[3])

        font = QFont("Consolas", 8, QFont.Weight.Bold)
        painter.setFont(font)

        for label, px, py, pz, color in projected:
            painter.setPen(QPen(color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(origin_x, origin_y), QPointF(px, py))

            painter.setPen(QPen(color))
            offset_x = (px - origin_x) * 0.4
            offset_y = (py - origin_y) * 0.4

            painter.drawText(
                QRectF(px + offset_x - 10, py + offset_y - 10, 20, 20),
                Qt.AlignmentFlag.AlignCenter,
                label
            )

    def _draw_cube(self, painter: QPainter, cx: float, cy: float) -> None:
        """
        Draws the isometric cube projection
        """
        cube_half_size = self.CUBE_SIZE / 3

        # Define 8 cube vertices in 3D space (centered at origin)
        vertices_3d = [
            (-cube_half_size, -cube_half_size, -cube_half_size),  # 0: back-bottom-left
            (cube_half_size, -cube_half_size, -cube_half_size),  # 1: back-bottom-right
            (cube_half_size, cube_half_size, -cube_half_size),  # 2: back-top-right
            (-cube_half_size, cube_half_size, -cube_half_size),  # 3: back-top-left
            (-cube_half_size, -cube_half_size, cube_half_size),  # 4: front-bottom-left
            (cube_half_size, -cube_half_size, cube_half_size),  # 5: front-bottom-right
            (cube_half_size, cube_half_size, cube_half_size),  # 6: front-top-right
            (-cube_half_size, cube_half_size, cube_half_size),  # 7: front-top-left
        ]

        vertices_2d = []
        for x, y, z in vertices_3d:
            px, py, pz = self._project_3d_to_2d(x, y, z, cx, cy)
            vertices_2d.append((px, py, pz))

        faces = [
            ([0, 1, 2, 3], 'Y-', 'BACK', self._faceColorY, (0, -1, 0)),
            ([4, 5, 6, 7], 'Y+', 'FRONT', self._faceColorY, (0, 1, 0)),
            ([0, 4, 7, 3], 'X-', 'LEFT', self._faceColorX, (-1, 0, 0)),
            ([1, 5, 6, 2], 'X+', 'RIGHT', self._faceColorX, (1, 0, 0)),
            ([3, 2, 6, 7], 'Z+', 'TOP', self._faceColorZ, (0, 0, 1)),
            ([0, 1, 5, 4], 'Z-', 'BTM', self._faceColorZ, (0, 0, -1)),
        ]

        def face_depth(face_data):
            indices, _, _, _, _ = face_data
            avg_z = sum(vertices_2d[i][2] for i in indices) / 4
            return avg_z

        sorted_faces = sorted(faces, key=face_depth)

        self._drawn_faces.clear()

        for indices, face_id, display_label, color_getter, normal in sorted_faces:
            if color_getter == self._faceColorX:
                color = self.faceColorX
            elif color_getter == self._faceColorY:
                color = self._faceColorY
            else:
                color = self._faceColorZ

            if self._hovered_face == face_id:
                color = color.lighter(115)

            poly = QPolygonF([QPointF(vertices_2d[i][0], vertices_2d[i][1]) for i in indices])
            self._drawn_faces.append((face_id, poly))

            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 1.5))
            painter.drawPolygon(poly)

            center_x = sum(vertices_2d[i][0] for i in indices) / 4
            center_y = sum(vertices_2d[i][1] for i in indices) / 4

            painter.setPen(QPen(Qt.GlobalColor.white))
            font = QFont("Consolas", 10, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(
                QRectF(center_x - 30, center_y - 15, 60, 30),
                Qt.AlignmentFlag.AlignCenter,
                display_label
            )

    def _hit_test(self, x: float, y: float) -> Optional[str]:
        """
        Determine which face was clicked using geometric intersection
        Iterates through the drawn faces in reverse Z-order

        :param x: Mouse X position
        :param y: Mouse Y position
        :return: Face identifier or None
        """
        point = QPointF(x, y)

        for face_id, poly in reversed(self._drawn_faces):
            if poly.containsPoint(point, Qt.FillRule.WindingFill):
                return face_id
        return None
