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

    DEFAULT_FACE_X = QColor(200, 100, 100, 180)
    DEFAULT_FACE_Y = QColor(100, 200, 100, 180)
    DEFAULT_FACE_Z = QColor(100, 100, 200, 180)

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

        self._is_draggin = False
        self._last_mouse_pos: Optional[Tuple[int, int]] = None

        self._clicked_face: Optional[str] = None

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(self.CUBE_SIZE + 20, self.CUBE_SIZE + 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
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

        self._is_draggin = True
        self._last_mouse_pos = (event.position().x(), event.pos().y())

        clicked_face = self._hit_test(event.position().x(), event.position().y())
        if clicked_face:
            self._clicked_face = clicked_face
        else:
            self._clicked_face = None

        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse drag to rotate the cube"""
        if not self._is_draggin or self._last_mouse_pos is None:
            return

        current_x = event.position().x()
        current_y = event.position().y()

        dx = current_x - self._last_mouse_pos[0]
        dy = current_y - self._last_mouse_pos[1]

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

        self._is_draggin = False

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
    ### Painting
    ###

    def paintEvent(self, event: QPaintEvent) -> None:
        """Render the 3D cube"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2

        self._draw_cube(painter, cx, cy)

    def _draw_cube(self, painter: QPainter, cx: float, cy: float) -> None:
        """
        Draws the isometric cube projection
        """
        azimuth_radians = math.radians(self._azimuth)
        elevation_radians = math.radians(self._elevation)

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
            x1 = x * math.cos(azimuth_radians) - y * math.sin(azimuth_radians)
            y1 = x * math.sin(azimuth_radians) + y * math.cos(azimuth_radians)

            y2 = y1 * math.cos(elevation_radians) - z * math.sin(elevation_radians)
            z2 = y1 * math.sin(elevation_radians) + z * math.cos(elevation_radians)

            px = x1
            py = y2 * 0.05

            vertices_2d.append((cx + px, cy - py))

        faces = [
            ([0, 1, 2, 3], 'Y-', self._faceColorY, (0, -1, 0)),
            ([4, 5, 6, 7], 'Y+', self._faceColorY, (0, 1, 0)),
            ([0, 4, 7, 3], 'X-', self._faceColorX, (-1, 0, 0)),
            ([1, 5, 6, 2], 'X+', self._faceColorX, (1, 0, 0)),
            ([3, 2, 6, 7], 'Z+', self._faceColorZ, (0, 0, 1)),
            ([0, 1, 5, 4], 'Z-', self._faceColorZ, (0, 0, -1)),
        ]

        def face_depth(face_data):
            indices, _, _, _ = face_data
            avg_z = sum(vertices_2d[i][1] for i in indices) / 4
            return avg_z

        sorted_faces = sorted(faces, key=face_depth)

        for indices, label, color_getter, normal in sorted_faces:
            if color_getter == self._faceColorX:
                color = self.faceColorX
            elif color_getter == self._faceColorY:
                color = self._faceColorY
            else:
                color = self._faceColorZ

            poly = QPolygonF([QPointF(vertices_2d[i][0], vertices_2d[i][1]) for i in indices])

            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 1.5))
            painter.drawPolygon(poly)

            center_x = sum(vertices_2d[i][0] for i in indices) / 4
            center_y = sum(vertices_2d[i][1] for i in indices) / 4

            painter.setPen(QPen(Qt.GlobalColor.white))
            font = QFont("Consolas", 10, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(
                QRectF(center_x - 10, center_y - 10, 20, 20),
                Qt.AlignmentFlag.AlignCenter,
                label[0]
            )

    def _hit_test(self, x: float, y: float) -> Optional[str]:
        """
        Determine which face was clicked
        :return: Face identifier or None
        """
        cx = self.width() / 2
        cy = self.height() / 2

        dx = x - cx
        dy = y - cy

        norm_x = dx / (self.CUBE_SIZE / 2)
        norm_y = dy / (self.CUBE_SIZE / 2)

        azimuth_radians = math.radians(self._azimuth)
        elevation_radians = math.radians(self._elevation)

        local_x = norm_x * math.cos(-azimuth_radians) - norm_y * math.sin(-azimuth_radians)
        local_y = norm_x * math.sin(-azimuth_radians) + norm_y * math.cos(-azimuth_radians)

        abs_x = abs(local_x)
        abs_y = abs(local_y)

        if abs(elevation_radians) > math.radians(45):
            return "Z+" if self._elevation > 0 else "Z-"
        elif abs_x > abs_y and abs_x > 0.3:
            return "X+" if local_x > 0 else "X-"
        elif abs_y > 0.3:
            return "Y+" if local_y > 0 else "Y-"

        return None
