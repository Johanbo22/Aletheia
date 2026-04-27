import numpy as np
from enum import Enum
from PyQt6.QtWidgets import QGraphicsEffect
from PyQt6.QtGui import QImage, QPainter, QPixmap
from PyQt6.QtCore import Qt, QObject

class ColorBlindnessType(str, Enum):
    Protanopia = "Protanopia (No Red)"
    Deuteranopia = "Deuteranopia (No Green)"
    Tritanopia = "Tritanopia (No Blue)"
    Achromatopsia = "Achromatopsia (Monochromacy)"

class ColorBlindnessEffect(QGraphicsEffect):
    """
    A QGraphicsEffect that applies a color matrix transformation
    to simulate color blindness
    """
    
    # Standard SVG color matricies for CBS
    MATRICES: dict[ColorBlindnessType, np.ndarray] = {
        ColorBlindnessType.Protanopia: np.array([
            [0.567, 0.433, 0.000],
            [0.558, 0.442, 0.000],
            [0.000, 0.242, 0.758]
        ]),
        ColorBlindnessType.Deuteranopia: np.array([
            [0.625, 0.375, 0.000],
            [0.700, 0.300, 0.000],
            [0.000, 0.300, 0.700]
        ]),
        ColorBlindnessType.Tritanopia: np.array([
            [0.950, 0.050, 0.000],
            [0.000, 0.433, 0.567],
            [0.000, 0.475, 0.525]
        ]),
        ColorBlindnessType.Achromatopsia: np.array([
            [0.299, 0.587, 0.114],
            [0.299, 0.587, 0.114],
            [0.299, 0.587, 0.114]
        ])
    }
    
    def __init__(self, simulation_type: ColorBlindnessType | str = ColorBlindnessType.Protanopia, parent: QObject | None = None):
        super().__init__(parent)
        self.simulation_type = ColorBlindnessType(simulation_type) if isinstance(simulation_type, str) else simulation_type
        
        # Caching to avoid CPU overusage
        self._cached_pixmap: QPixmap | None = None
        self._last_source_cache_key: int | None = None
        self._last_sim_type: ColorBlindnessType | None = None
    
    def set_simulation_type(self, sim_type: ColorBlindnessType | str) -> None:
        """Update the simulaton type to trigger redrawEvent"""
        new_type = ColorBlindnessType(sim_type) if isinstance(sim_type, str) else sim_type
        if self.simulation_type != new_type:
            self.simulation_type = new_type
            self.update()
    
    def draw(self, painter: QPainter) -> None:
        """Applies the color matrix to a pixmap"""
        pixmap, offset = self.sourcePixmap(Qt.CoordinateSystem.LogicalCoordinates)
        if pixmap.isNull():
            return
        
        current_cache_key = pixmap.cacheKey()
        
        if (self._cached_pixmap is not None and self._last_source_cache_key == current_cache_key and self._last_sim_type == self.simulation_type):
            painter.drawPixmap(offset, self._cached_pixmap)
            return
        
        original_image = pixmap.toImage()
        processed_image = self._apply_color_blindness_filter(original_image)
        
        self._cached_pixmap = QPixmap.fromImage(processed_image)
        self._last_source_cache_key = current_cache_key
        self._last_sim_type = self.simulation_type
        
        painter.drawPixmap(offset, self._cached_pixmap)
    
    def _apply_color_blindness_filter(self, original_image: QImage) -> QImage:
        """
        Transforms the image pixels using the selected color blindness matrix
        """
        original_image.convertTo(QImage.Format.Format_RGB32)
        device_pixel_ratio = original_image.devicePixelRatio()
        
        image_pointer = original_image.bits()
        image_pointer.setsize(original_image.sizeInBytes())
        
        image_data_array = np.array(image_pointer).reshape((original_image.height(), original_image.width(), 4))
        color_matrix = self.MATRICES.get(self.simulation_type, np.eye(3))
        
        rgb_chanels = image_data_array[:, :, :3]
        red_channel = rgb_chanels[:, :, 2]
        green_channel = rgb_chanels[:, :, 1]
        blue_channel = rgb_chanels[:, :, 0]
        
        image_shape = red_channel.shape
        flattened_pixels = np.vstack([red_channel.ravel(), green_channel.ravel(), blue_channel.ravel()])
        
        transformed_pixels = color_matrix @ flattened_pixels
        transformed_pixels = np.clip(transformed_pixels, 0, 255).astype(np.uint8)
        
        image_data_array[:, :, 2] = transformed_pixels[0].reshape(image_shape)
        image_data_array[:, :, 1] = transformed_pixels[1].reshape(image_shape)
        image_data_array[:, :, 0] = transformed_pixels[2].reshape(image_shape)
        
        processed_image = QImage(
            image_data_array.data,
            original_image.width(),
            original_image.height(),
            original_image.bytesPerLine(),
            QImage.Format.Format_RGB32
        )
        processed_image.setDevicePixelRatio(device_pixel_ratio)
        return processed_image