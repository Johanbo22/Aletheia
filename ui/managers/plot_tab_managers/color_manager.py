from typing import TYPE_CHECKING, Optional

from PyQt6.QtWidgets import QColorDialog, QLabel, QPushButton
from PyQt6.QtGui import QColor, QPixmap, QPainter, QIcon, QPen
from PyQt6.QtCore import Qt


if TYPE_CHECKING:
    from ui.plot_tab import PlotTab

class ColorManager:
    """
    Manages all color selection and storage for plot elements
    """
    def __init__(self, plot_tab: "PlotTab") -> None:
        self.plot_tab = plot_tab

    def connect_signals(self) -> None:
        """Connect all signals for color selections"""
        # Spine colors
        self.plot_tab.view.global_spine_color_button.clicked.connect(self.choose_global_spine_color)
        self.plot_tab.view.top_spine_color_button.clicked.connect(self.choose_top_spine_color)
        self.plot_tab.view.bottom_spine_color_button.clicked.connect(self.choose_bottom_spine_color)
        self.plot_tab.view.left_spine_color_button.clicked.connect(self.choose_left_spine_color)
        self.plot_tab.view.right_spine_color_button.clicked.connect(self.choose_right_spine_color)

        # Grid colors
        self.plot_tab.view.global_grid_color_button.clicked.connect(self.choose_global_grid_color)
        self.plot_tab.view.x_major_grid_color_button.clicked.connect(self.choose_x_major_grid_color)
        self.plot_tab.view.x_minor_grid_color_button.clicked.connect(self.choose_x_minor_grid_color)
        self.plot_tab.view.y_major_grid_color_button.clicked.connect(self.choose_y_major_grid_color)
        self.plot_tab.view.y_minor_grid_color_button.clicked.connect(self.choose_y_minor_grid_color)

        # Plot element colors
        self.plot_tab.view.line_color_button.clicked.connect(self.choose_line_color)
        self.plot_tab.view.marker_color_button.clicked.connect(self.choose_marker_color)
        self.plot_tab.view.marker_edge_button.clicked.connect(self.choose_marker_edge_color)
        self.plot_tab.view.bar_color_button.clicked.connect(self.choose_bar_color)
        self.plot_tab.view.bar_edge_button.clicked.connect(self.choose_bar_edge_color)
        self.plot_tab.view.error_bar_color_button.clicked.connect(self.choose_error_bar_color)

        # Background and legend colors
        self.plot_tab.view.bg_color_button.clicked.connect(self.choose_bg_color)
        self.plot_tab.view.face_color_button.clicked.connect(self.choose_face_color)
        self.plot_tab.view.textbox_bg_button.clicked.connect(self.choose_textbox_bg_color)
        self.plot_tab.view.legend_bg_button.clicked.connect(self.choose_legend_bg_color)
        self.plot_tab.view.legend_edge_button.clicked.connect(self.choose_legend_edge_color)

        # Geospatial colors
        self.plot_tab.view.geo_missing_color_btn.clicked.connect(self.choose_geo_missing_color)
        self.plot_tab.view.geo_edge_color_btn.clicked.connect(self.choose_geo_edge_color)

    def _get_color(self, current_color_hex: str, parent=None) -> Optional[str]:
        """Opens a color dialog and returns the selected color hex or None if the operation is cancelled"""
        color = QColorDialog.getColor(QColor(current_color_hex), parent or self.plot_tab)
        if color.isValid():
            return color.name()
        return None
    
    @staticmethod
    def update_button_color_swatch(button: QPushButton, color: QColor, swatch_size: int = 16) -> None:
        """
        Dynamically generates a solid-color pixmap and applies it as the button's icon.
        This provides a visual color indicator without violating strict QSS separation of concerns.

        :param button: The standard QPushButton target.
        :param color: The QColor selected by the user.
        :param swatch_size: The squared pixel size of the generated QPixmap.
        """
        pixmap = QPixmap(swatch_size, swatch_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(color)
        
        border_color = QColor("#000000") if color.lightnessF() > 0.8 else QColor("#ffffff")
        border_pen = QPen(border_color)
        border_pen.setWidth(1)
        border_pen.setCosmetic(True)
        painter.setPen(border_pen)
        
        painter.drawRect(0, 0, swatch_size - 1, swatch_size - 1)
        painter.end()
        
        button.setIcon(QIcon(pixmap))

    def _update_color_button(self, button: QPushButton, label: QLabel, color_hex: str) -> None:
        """Updates the button and the associated label"""
        label.setText(color_hex)
        self.update_button_color_swatch(button, QColor(color_hex))

    def choose_global_spine_color(self) -> None:
        """Open color picker for global spine color."""
        color = self._get_color(self.plot_tab.global_spine_color)
        if color:
            self.plot_tab.global_spine_color = color
            self._update_color_button(
                self.plot_tab.view.global_spine_color_button,
                self.plot_tab.view.global_spine_color_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_top_spine_color(self) -> None:
        """Open color picker for top spine color."""
        color = self._get_color(self.plot_tab.top_spine_color)
        if color:
            self.plot_tab.top_spine_color = color
            self._update_color_button(
                self.plot_tab.view.top_spine_color_button,
                self.plot_tab.view.top_spine_color_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_bottom_spine_color(self) -> None:
        """Open color picker for bottom spine color."""
        color = self._get_color(self.plot_tab.bottom_spine_color)
        if color:
            self.plot_tab.bottom_spine_color = color
            self._update_color_button(
                self.plot_tab.view.bottom_spine_color_button,
                self.plot_tab.view.bottom_spine_color_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_left_spine_color(self) -> None:
        """Open color picker for left spine color."""
        color = self._get_color(self.plot_tab.left_spine_color)
        if color:
            self.plot_tab.left_spine_color = color
            self._update_color_button(
                self.plot_tab.view.left_spine_color_button,
                self.plot_tab.view.left_spine_color_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_right_spine_color(self) -> None:
        """Open color picker for right spine color."""
        color = self._get_color(self.plot_tab.right_spine_color)
        if color:
            self.plot_tab.right_spine_color = color
            self._update_color_button(
                self.plot_tab.view.right_spine_color_button,
                self.plot_tab.view.right_spine_color_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_global_grid_color(self) -> None:
        """Open color picker for global gridlines."""
        color = self._get_color(self.plot_tab.global_grid_color)
        if color:
            self.plot_tab.global_grid_color = color
            self._update_color_button(
                self.plot_tab.view.global_grid_color_button,
                self.plot_tab.view.global_grid_color_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_x_major_grid_color(self) -> None:
        """Open color picker for x-axis major gridlines."""
        color = self._get_color(self.plot_tab.x_major_grid_color)
        if color:
            self.plot_tab.x_major_grid_color = color
            self._update_color_button(
                self.plot_tab.view.x_major_grid_color_button,
                self.plot_tab.view.x_major_grid_color_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_x_minor_grid_color(self) -> None:
        """Open color picker for x-axis minor gridlines."""
        color = self._get_color(self.plot_tab.x_minor_grid_color)
        if color:
            self.plot_tab.x_minor_grid_color = color
            self._update_color_button(
                self.plot_tab.view.x_minor_grid_color_button,
                self.plot_tab.view.x_minor_grid_color_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_y_major_grid_color(self) -> None:
        """Open color picker for y-axis major gridlines."""
        color = self._get_color(self.plot_tab.y_major_grid_color)
        if color:
            self.plot_tab.y_major_grid_color = color
            self._update_color_button(
                self.plot_tab.view.y_major_grid_color_button,
                self.plot_tab.view.y_major_grid_color_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_y_minor_grid_color(self) -> None:
        """Open color picker for y-axis minor gridlines."""
        color = self._get_color(self.plot_tab.y_minor_grid_color)
        if color:
            self.plot_tab.y_minor_grid_color = color
            self._update_color_button(
                self.plot_tab.view.y_minor_grid_color_button,
                self.plot_tab.view.y_minor_grid_color_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_line_color(self) -> None:
        """Open color picker for line color."""
        color = self._get_color(self.plot_tab.line_color or "#000000")
        if color:
            self.plot_tab.line_color = color
            self._update_color_button(
                self.plot_tab.view.line_color_button,
                self.plot_tab.view.line_color_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_marker_color(self) -> None:
        """Open color picker for marker color."""
        color = self._get_color(self.plot_tab.marker_color or "#000000")
        if color:
            self.plot_tab.marker_color = color
            self._update_color_button(
                self.plot_tab.view.marker_color_button,
                self.plot_tab.view.marker_color_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_marker_edge_color(self) -> None:
        """Open color picker for marker edge color."""
        color = self._get_color(self.plot_tab.marker_edge_color or "#000000")
        if color:
            self.plot_tab.marker_edge_color = color
            self._update_color_button(
                self.plot_tab.view.marker_edge_button,
                self.plot_tab.view.marker_edge_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_bar_color(self) -> None:
        """Open color picker for bar color."""
        color = self._get_color(self.plot_tab.bar_color or "#000000")
        if color:
            self.plot_tab.bar_color = color
            self._update_color_button(
                self.plot_tab.view.bar_color_button,
                self.plot_tab.view.bar_color_label,
                color
            )
            self.plot_tab._update_bar_customization_live()
            self.plot_tab.on_style_changed()

    def choose_bar_edge_color(self) -> None:
        """Open color picker for bar edge color."""
        color = self._get_color(self.plot_tab.bar_edge_color or "#000000")
        if color:
            self.plot_tab.bar_edge_color = color
            self._update_color_button(
                self.plot_tab.view.bar_edge_button,
                self.plot_tab.view.bar_edge_label,
                color
            )
            self.plot_tab._update_bar_customization_live()
            self.plot_tab.on_style_changed()

    def choose_error_bar_color(self) -> None:
        """Open color picker for error bar color."""
        color = self._get_color(self.plot_tab.error_bar_color)
        if color:
            self.plot_tab.error_bar_color = color
            self._update_color_button(
                self.plot_tab.view.error_bar_color_button,
                self.plot_tab.view.error_bar_color_label,
                color
            )
            self.plot_tab.on_data_changed()

    def choose_bg_color(self) -> None:
        """Open color picker for background color."""
        color = self._get_color(self.plot_tab.bg_color)
        if color:
            self.plot_tab.bg_color = color
            self._update_color_button(
                self.plot_tab.view.bg_color_button,
                self.plot_tab.view.bg_color_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_face_color(self) -> None:
        """Open color picker for face color."""
        color = self._get_color(self.plot_tab.face_color)
        if color:
            self.plot_tab.face_color = color
            self._update_color_button(
                self.plot_tab.view.face_color_button,
                self.plot_tab.view.face_color_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_textbox_bg_color(self) -> None:
        """Open color picker for text box background."""
        color = self._get_color(self.plot_tab.textbox_bg_color)
        if color:
            self.plot_tab.textbox_bg_color = color
            self._update_color_button(
                self.plot_tab.view.textbox_bg_button,
                self.plot_tab.view.textbox_bg_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_legend_bg_color(self) -> None:
        """Open color picker for legend background."""
        color = self._get_color(self.plot_tab.legend_bg_color)
        if color:
            self.plot_tab.legend_bg_color = color
            self._update_color_button(
                self.plot_tab.view.legend_bg_button,
                self.plot_tab.view.legend_bg_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_legend_edge_color(self) -> None:
        """Open color picker for legend edge color."""
        color = self._get_color(self.plot_tab.legend_edge_color)
        if color:
            self.plot_tab.legend_edge_color = color
            self._update_color_button(
                self.plot_tab.view.legend_edge_button,
                self.plot_tab.view.legend_edge_label,
                color
            )
            self.plot_tab.on_style_changed()

    def choose_geo_missing_color(self) -> None:
        """Open color picker for geospatial missing data color."""
        color = self._get_color(self.plot_tab.geo_missing_color or "#D3D3D3")
        if color:
            self.plot_tab.geo_missing_color = color
            self._update_color_button(
                self.plot_tab.view.geo_missing_color_btn,
                self.plot_tab.view.geo_missing_color_label,
                color
            )
            self.plot_tab._on_geospatial_projection_changed()

    def choose_geo_edge_color(self) -> None:
        """Open color picker for geospatial edge color."""
        color = self._get_color(self.plot_tab.geo_edge_color or "#000000")
        if color:
            self.plot_tab.geo_edge_color = color
            self._update_color_button(
                self.plot_tab.view.geo_edge_color_btn,
                self.plot_tab.view.geo_edge_color_label,
                color
            )
            self.plot_tab._on_geospatial_projection_changed()