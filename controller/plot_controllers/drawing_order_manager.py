import logging
from dataclasses import dataclass
from typing import Sequence

import matplotlib.colors as mcolors
from PyQt6.QtCore import QObject, QRect, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.collections import Collection, PathCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class PlotLayerItem:
    """
    Immutable data structure representing a user-facing artist
    that is drawn on the canvas

    :param layer_id: Unique identifier derived from the artist label or GID
    :param label: A label for the list UI
    :param zorder: Current internal z-order value
    :param is_visible: Whether or not the artist is drawn
    :param icon: Visual representation of the artist
    """
    layer_id: str
    label: str
    zorder: float
    is_visible: bool
    icon: QIcon

class DrawingOrderManager(QObject):
    """
    Controller responsible for bridging the Matplotlib aristst and the drawing order widget

    Extracts artists, generates the UI representation and applies z-order
    and visibility changes to the canvas
    """
    # Emits this signal when canvas redraw is requested
    requestCanvasRedraw = pyqtSignal()

    def __init__(self, debounce_interval_ms: int = 150) -> None:
        """
        :param debounce_interval_ms: Milliseconds to wait before emitting requestCanvasRedraw
        """
        super().__init__()
        self._current_axes: Axes | None = None
        self._tracked_artists: dict[str, Artist] = {}

        self._redraw_timer: QTimer = QTimer(self)
        self._redraw_timer.setSingleShot(True)
        self._redraw_timer.setInterval(debounce_interval_ms)
        self._redraw_timer.timeout.connect(self.requestCanvasRedraw.emit)

    def extract_layers(self, ax: Axes) -> list[PlotLayerItem]:
        """
        Scans the axes for axes bound artists maps them and returns them as sorted layers

        :param ax: The Maplotlib axes to scan
        :return: A list of PlotLayerItems which is sorted by zorder
        """
        self._current_axes = ax
        self._tracked_artists.clear()

        layers: list[PlotLayerItem] = []

        artists = ax.lines + ax.collections + ax.patches + ax.texts

        for artist in artists:
            if not self._is_user_facing_artist(artist):
                continue

            layer_id = self._determine_layer_id(artist)
            if not layer_id:
                continue

            self._tracked_artists[layer_id] = artist

            label = artist.get_label()
            if not label or label.startswith("_nolegend_"):
                label = f"{type(artist).__name__} ({layer_id})"

            icon = self._generate_icon_for_artist(artist)

            layers.append(
                PlotLayerItem(
                    layer_id=layer_id,
                    label=label,
                    zorder=artist.get_zorder(),
                    is_visible=artist.get_visible(),
                    icon=icon
                )
            )

        layers.sort(key=lambda item: item.zorder, reverse=True)
        return layers

    def set_layer_visibility(self, layer_id: str, is_visible: bool) -> None:
        """
        Toggle the visibility of a specific layer and queue a redraw

        :param layer_id: The ID of the layer to toggle
        :param is_visible: The new visibility state
        """
        artist = self._tracked_artists.get(layer_id)
        if not artist:
            logger.warning(f"Cannot change visibility of: Layer {layer_id} not found")
            return

        if artist.get_visible() != is_visible:
            artist.set_visible(is_visible)
            self._redraw_timer.start()

    def apply_new_order(self, ordered_layer_ids: Sequence[str]) -> None:
        """
        Apply a new Z order to the artists based on the provided IDs
        Index 0 is max z order of list

        :param ordered_layer_ids:
        :return:
        """
        if not self._current_axes:
            return

        base_zorder = 100.0

        for index, layer_id in enumerate(ordered_layer_ids):
            artist = self._tracked_artists.get(layer_id)
            if not artist:
                logger.warning(f"Cannot set order: Layer {layer_id} not found")
                continue

            new_zorder = base_zorder - index
            if artist.get_zorder() != new_zorder:
                artist.set_zorder(new_zorder)

        self._redraw_timer.start()

    def _is_user_facing_artist(self, artist: Artist) -> bool:
        """
        Filter out background patches, spines, ticks and internal Matplotlib elements
        """
        if isinstance(artist, Patch) and artist == self._current_axes.patch:
            return False

        if type(artist).__name__ in ("Spine", "XAxis", "YAxis", "Text"):
            if type(artist).__name__ == "Text" and artist.get_gid() and "annotation" in artist.get_gid():
                return True
            return False

        return isinstance(artist, (Line2D, Collection, Patch))

    def _determine_layer_id(self, artist: Artist) -> str | None:
        """Extract an unique layer ID for the artist"""
        gid = artist.get_gid()
        if gid:
            return gid

        label = artist.get_label()
        if label and not label.startswith("_nolegend_"):
            return label

        return f"unnamed_artist_{id(artist)}"

    def _generate_icon_for_artist(self, artist: Artist) -> QIcon:
        """
        Generate a Qt icon representing the artist's visual style.
        """
        icon_size = 24
        pixmap = QPixmap(icon_size, icon_size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRect(2, 2, icon_size - 4, icon_size - 4)

        try:
            if isinstance(artist, Line2D):
                self._draw_line_icon(painter, artist, rect)
            elif isinstance(artist, Patch):
                self._draw_patch_icon(painter, artist, rect)
            elif isinstance(artist, Collection):
                self._draw_collection_icon(painter, artist, rect)
            else:
                self._draw_fallback_icon(painter, rect)
        except Exception as e:
            logger.debug(f"Failed to draw icon for {artist}: {e}")
            self._draw_fallback_icon(painter, rect)
        finally:
            painter.end()

        return QIcon(pixmap)

    def _draw_line_icon(self, painter: QPainter, artist: Line2D, rect: QRect) -> None:
        """Draws a representation of a Line2D object"""
        color = self._mpl_color_to_qcolor(artist.get_color())

        if artist.get_linestyle() in ("None", "none", "", None) and artist.get_marker() not in (
        "None", "none", "", None):
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            center = rect.center()
            painter.drawEllipse(center, rect.width() // 3, rect.width() // 3)
            return

        pen = QPen(color, max(2, min(5, int(artist.get_linewidth()))))
        painter.setPen(pen)
        painter.drawLine(rect.centerLeft(), rect.centerRight())

    def _draw_patch_icon(self, painter: QPainter, artist: Patch, rect: QRect) -> None:
        """Draws a representation of a Patch"""
        face_color = self._mpl_color_to_qcolor(artist.get_facecolor())
        edge_color = self._mpl_color_to_qcolor(artist.get_edgecolor())

        painter.setBrush(QBrush(face_color))
        pen = QPen(edge_color, max(1, int(artist.get_linewidth() or 1)))
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 4.0, 4.0)

    def _draw_collection_icon(self, painter: QPainter, artist: Collection, rect: QRect) -> None:
        """Draws a representation of a Collection"""
        color = QColor(100, 100, 100)

        face_colors = artist.get_facecolor()
        if len(face_colors) > 0:
            color = self._mpl_color_to_qcolor(face_colors[0])

        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)

        if isinstance(artist, PathCollection):
            center = rect.center()
            painter.drawEllipse(center, rect.width() // 3, rect.width() // 3)
        else:
            painter.drawRect(rect)

    def _draw_fallback_icon(self, painter: QPainter, rect: QRect) -> None:
        """Draws a generic placeholder icon if the artist style cannot be resolved."""
        painter.setBrush(QBrush(QColor(150, 150, 150)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(rect.center(), rect.width() // 4, rect.width() // 4)

    def _mpl_color_to_qcolor(self, mpl_color: any) -> QColor:
        """Converts any matplotlib color format to a QColor"""
        try:
            rgba = mcolors.to_rgba(mpl_color)
            return QColor(
                int(rgba[0] * 255),
                int(rgba[1] * 255),
                int(rgba[2] * 255),
                int(rgba[3] * 255),
            )
        except (ValueError, TypeError):
            return QColor(Qt.GlobalColor.gray)
