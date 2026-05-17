from PyQt6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLabel, QVBoxLayout, QFormLayout, QGridLayout
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QPixmap

from pathlib import Path

from resources.version import APPLICATION_NAME
from ui.icons.icon_registry import IconBuilder, IconType
from ui.theme import ThemeColors
from ui.widgets import DataPlotStudioButton
from ui.widgets.ControlElements import DataPlotStudioCheckBox, DataPlotStudioComboBox, DataPlotStudioDoubleSpinBox, DataPlotStudioGroupBox, DataPlotStudioSpinBox

class PlotExportDialog(QDialog):
    """Dialog for exporting plots"""

    def __init__(self, current_dpi: int = 100, preview_pixmap: QPixmap | None = None, fig_width: float = 8.0, fig_height: float = 6.0, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Save Plot")
        self.setModal(True)
        self.resize(720, 420)
        
        self.settings = QSettings(f"{APPLICATION_NAME}", "PlotExportPreferences")
        
        self.fallback_dpi: int = current_dpi
        self.preview_pixmap: QPixmap | None = preview_pixmap
        self.initial_fig_width: float = fig_width
        self.initial_fig_height: float = fig_height
        self.aspect_ratio: float = fig_width / fig_height if fig_height else 1.0
        self.filepath: str | None = None
        
        self.init_ui()
        self._load_preferences()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        content_layout = QHBoxLayout()
        
        # Preview image
        preview_group = DataPlotStudioGroupBox("Preivew", parent=self)
        preview_layout = QVBoxLayout()
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(300, 250)
        
        if self.preview_pixmap is not None:
            scaled_pixmap: QPixmap = self.preview_pixmap.scaled(
                300, 250,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled_pixmap)
        else:
            self.preview_label.setText("No Preview Available")
            
        preview_layout.addWidget(self.preview_label)
        preview_group.setLayout(preview_layout)
        content_layout.addWidget(preview_group)
        
        settings_layout_main = QVBoxLayout()
        settings_group = DataPlotStudioGroupBox("Export Settings", parent=self)
        settings_inner_layout = QVBoxLayout()

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.format_combo = DataPlotStudioComboBox()
        self.format_combo.addItems(["PNG", "JPEG", "PDF", "SVG", "TIFF", "EPS", "PS", "RAW", "RGBA"])
        form_layout.addRow("Format:", self.format_combo)
        
        dim_layout = QGridLayout()
        dim_layout.setContentsMargins(0, 0, 0, 0)
        
        self.width_spin = DataPlotStudioDoubleSpinBox()
        self.width_spin.setRange(1.0, 50.0)
        self.width_spin.setSingleStep(0.5)
        self.width_spin.setValue(self.initial_fig_width)
        self.width_spin.setToolTip("Target width in inches.")
        
        self.height_spin = DataPlotStudioDoubleSpinBox()
        self.height_spin.setRange(1.0, 50.0)
        self.height_spin.setSingleStep(0.5)
        self.height_spin.setValue(self.initial_fig_height)
        self.height_spin.setToolTip("Target height in inches.")
        
        self.lock_aspect_ratio_check = DataPlotStudioButton("")
        self.lock_aspect_ratio_check.setIcon(IconBuilder.build(IconType.Locked))
        self.lock_aspect_ratio_check.setCheckable(True)
        self.lock_aspect_ratio_check.setChecked(True)
        self.lock_aspect_ratio_check.setFixedWidth(40)
        self.lock_aspect_ratio_check.setToolTip("Aspect Ratio is locked")
        
        
        dim_layout.addWidget(QLabel("Width:"), 0, 0)
        dim_layout.addWidget(self.width_spin, 0, 1)
        dim_layout.addWidget(QLabel("in"), 0, 2)
        
        dim_layout.addWidget(QLabel("Height:"), 1, 0)
        dim_layout.addWidget(self.height_spin, 1, 1)
        dim_layout.addWidget(QLabel("in"), 1, 2)
        
        dim_layout.addWidget(self.lock_aspect_ratio_check, 0, 3, 2, 1, Qt.AlignmentFlag.AlignVCenter)
        
        form_layout.addRow("Size:", dim_layout)

        # DPI settings
        self.dpi_spin = DataPlotStudioSpinBox()
        self.dpi_spin.setRange(50, 1200)
        self.dpi_spin.setValue(self.fallback_dpi)
        self.dpi_spin.setToolTip("Dots Per Inch (Resolution). Higher is sharper but increases file size.")
        form_layout.addRow("DPI:", self.dpi_spin)
        
        self.output_size_label = QLabel()
        form_layout.addRow("Output Size:", self.output_size_label)

        settings_inner_layout.addLayout(form_layout)
        settings_inner_layout.addSpacing(10)

        # Transparency
        self.transparent_check = DataPlotStudioCheckBox("Transparent Background")
        self.transparent_check.setCheckable(True)
        self.transparent_check.setChecked(False)
        self.transparent_check.setToolTip("Save with a transparent background (PNG/PDF/SVG/TIFF)")
        settings_inner_layout.addWidget(self.transparent_check)
        
        self.tight_layout_check = DataPlotStudioCheckBox("Tight Bounding Box")
        self.tight_layout_check.setCheckable(True)
        self.tight_layout_check.setChecked(True)
        self.tight_layout_check.setToolTip("Automatically trim excess margins around the exported plot.")
        settings_inner_layout.addWidget(self.tight_layout_check)

        settings_group.setLayout(settings_inner_layout)
        settings_layout_main.addWidget(settings_group)
        settings_layout_main.addStretch()

        content_layout.addLayout(settings_layout_main)
        main_layout.addLayout(content_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        export_button = DataPlotStudioButton("Save", base_color_hex=ThemeColors.MainColor, parent=self)
        export_button.setMinimumWidth(120)
        export_button.clicked.connect(self.on_save_clicked)
        button_layout.addWidget(export_button)

        cancel_button = DataPlotStudioButton("Cancel", parent=self)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        self._on_format_changed(self.format_combo.currentText())
        
        self.dpi_spin.valueChanged.connect(self._update_output_size_label)
        self.width_spin.valueChanged.connect(self._on_width_changed)
        self.height_spin.valueChanged.connect(self._on_height_changed)
        self.lock_aspect_ratio_check.toggled.connect(self._on_lock_toggled)
        self._update_output_size_label()
    
    def _on_lock_toggled(self, checked: bool) -> None:
        if checked:
            self.lock_aspect_ratio_check.setIcon(IconBuilder.build(IconType.Locked))
            self.lock_aspect_ratio_check.setToolTip("Aspect Ratio is locked")
            
            if self.height_spin.value() > 0:
                self.aspect_ratio = self.width_spin.value() / self.height_spin.value()
        else:
            self.lock_aspect_ratio_check.setIcon(IconBuilder.build(IconType.Unlocked))
            self.lock_aspect_ratio_check.setToolTip("Aspect Ratio is unlocked")
    
    def _on_width_changed(self, value: float) -> None:
        if self.lock_aspect_ratio_check.isChecked():
            self.height_spin.blockSignals(True)
            self.height_spin.setValue(value / self.aspect_ratio)
            self.height_spin.blockSignals(False)
        self._update_output_size_label()
    
    def _on_height_changed(self, value: float) -> None:
        if self.lock_aspect_ratio_check.isChecked():
            self.width_spin.blockSignals(True)
            self.width_spin.setValue(value * self.aspect_ratio)
            self.width_spin.blockSignals(False)
        self._update_output_size_label()
    
    def _update_output_size_label(self) -> None:
        dpi: int = self.dpi_spin.value()
        px_width: int = int(self.width_spin.value() * dpi)
        px_height: int = int(self.height_spin.value() * dpi)
        total_pixels: int = px_width * px_height

        if total_pixels > 100_000_000:
            self.output_size_label.setText(f"<span style='color: #e74c3c; font-weight: bold;'>{px_width} x {px_height} px (Warning: Extremely large file)</span>")
        else:
            self.output_size_label.setText(f"{px_width} x {px_height} px")
        
    def _load_preferences(self) -> None:
        """Load the user's last used export settings."""
        last_format = self.settings.value("last_format", "PNG")
        idx = self.format_combo.findText(last_format, Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            self.format_combo.setCurrentIndex(idx)
        
        last_dpi = self.settings.value("last_dpi", self.fallback_dpi, type=int)
        self.dpi_spin.setValue(last_dpi)
        
        last_transparent = self.settings.value("last_transparent", False, type=bool)
        if self.transparent_check.isEnabled():
            self.transparent_check.setChecked(last_transparent)
        
        last_tight = self.settings.value("last_tight_layout", True, type=bool)
        self.tight_layout_check.setChecked(last_tight)
    
    def _save_preferences(self) -> None:
        self.settings.setValue("last_format", self.format_combo.currentText())
        self.settings.setValue("last_dpi", self.dpi_spin.value())
        self.settings.setValue("last_transparent", self.transparent_check.isChecked())
        self.settings.setValue("last_tight_layout", self.tight_layout_check.isChecked())
    
    def _on_format_changed(self, format_text: str) -> None:
        fmt: str = format_text.lower()
        
        supports_transparency: bool = fmt in ["png", "pdf", "svg", "tiff", "eps", "ps", "rgba"]
        
        self.transparent_check.setEnabled(supports_transparency)
        if not supports_transparency:
            self.transparent_check.setChecked(False)
            self.transparent_check.setToolTip(f"{format_text} images does not support transparent backgrounds.")
        else:
            self.transparent_check.setToolTip(f"Save {format_text} with a transparent background")
    
    def on_save_clicked(self) -> None:
        extension = self.format_combo.currentText().lower()
        if extension == "jpeg": extension = "jpg"
        if extension == "tiff": extension = "tif"

        filters = {
            "png": "PNG Image (*.png)",
            "pdf": "PDF Document (*.pdf)",
            "svg": "SVG Image (*.svg)",
            "jpg": "JPEG Image (*.jpg)",
            "eps": "Encapsulated PostScript (*.eps)",
            "tif": "TIFF Image (*.tif)",
            "ps": "PostScript (*.ps)",
            "raw": "Raw Image (*.raw)",
            "rgba": "RGBA Image (*rgba)"
        }
        last_dir = self.settings.value("last_export_dir", str(Path.home()))
        default_path = str(Path(last_dir) / f"plot.{extension}")
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Plot",
            default_path,
            filters.get(extension, "All Files (*)")
        )
        if filepath:
            self.filepath = filepath
            self.settings.setValue("last_export_dir", str(Path(filepath).parent))
            self._save_preferences()
            self.accept()
    
    def get_config(self) -> dict[str, str | int | float | bool | None]:
        return {
            "filepath": self.filepath,
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "dpi": self.dpi_spin.value(),
            "transparent": self.transparent_check.isChecked(),
            "tight_layout": self.tight_layout_check.isChecked(),
            "format": self.format_combo.currentText().lower()
        }