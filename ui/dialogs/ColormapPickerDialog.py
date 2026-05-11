import matplotlib
from functools import lru_cache
from PyQt6.QtCore import QSize, Qt, QSettings, QEvent, QObject, QTimer
from PyQt6.QtGui import QBrush, QColor, QIcon, QLinearGradient, QPainter, QPixmap, QCloseEvent, QResizeEvent, QKeyEvent
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QListWidgetItem, QVBoxLayout, QFrame, QSpinBox, QSizePolicy

from ui.widgets.ControlElements import DataPlotStudioCheckBox
from ui.widgets.ControlElements import DataPlotStudioLineEdit, DataPlotStudioListWidget


class ColormapPickerDialog(QDialog):

    COLORMAP_CATEGORIES = {
        "Perceptually Uniform": ["viridis", "plasma", "inferno", "magma", "cividis"],
        "Sequential": ["Greys", "Purples", "Blues", "Greens", "Oranges", "Reds","YlOrBr", "YlOrRd", "OrRd", "PuRd", "RdPu", "BuPu","GnBu", "PuBu", "YlGnBu", "PuBuGn", "BuGn", "YlGn"],
        "Diverging": ["PiYG", "PRGn", "BrBG", "PuOr", "RdGy", "RdBu","RdYlBu", "RdYlGn", "Spectral", "coolwarm", "bwr", "seismic"],
        "Qualitative": ["Pastel1", "Pastel2", "Paired", "Accent","Dark2", "Set1", "Set2", "Set3", "tab10", "tab20", "tab20b", "tab20c"],
        "Cyclic": ["twilight", "twilight_shifted", "hsv"],
        "Miscellaneous": ["flag", "prism", "ocean", "gist_earth", "terrain","gist_stern", "gnuplot", "gnuplot2", "CMRmap","cubehelix", "brg", "gist_rainbow", "rainbow", "jet", "nipy_spectral", "gist_ncar"]
    }

    def __init__(self, current_colormap=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select colormap")
        self.setObjectName("colormapPickerDialog")
        self.setModal(True)
        self.resize(400, 600)

        is_reversed = False
        if current_colormap and current_colormap.endswith("_r"):
            self.selected_colormap = current_colormap[:-2]
            is_reversed = True
        else:
            self.selected_colormap = current_colormap
        
        self._final_selected_colormap = current_colormap
        self.colormap_to_category = {}
        for category, maps in self.COLORMAP_CATEGORIES.items():
            for m in maps:
                self.colormap_to_category[m] = category

        layout = QVBoxLayout(self)

        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_label.setObjectName("colormapSearchLabel")
        
        self.search_input = DataPlotStudioLineEdit()
        self.search_input.setObjectName("colormapSearchInput")
        self.search_input.setPlaceholderText("Type to filter...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._filter_items)
        
        options_layout = QHBoxLayout()

        self.reverse_check = DataPlotStudioCheckBox("Reverse colormap")
        self.reverse_check.setObjectName("colormapReverseCheckBox")
        self.reverse_check.setToolTip("Flips the gradient direction")
        self.reverse_check.toggled.connect(self._on_item_selection_changed)
        self.reverse_check.setChecked(is_reversed)
        
        self.grayscale_check = DataPlotStudioCheckBox("Grayscale test")
        self.grayscale_check.setObjectName("colormapGrayscaleCheckBox")
        self.grayscale_check.setToolTip("Preivew hos this colormap translates to black-and-white printing")
        self.grayscale_check.toggled.connect(self._on_item_selection_changed)
        
        self.discrete_check = DataPlotStudioCheckBox("Discrete")
        self.discrete_check.setObjectName("colormapDiscreteCheckBox")
        self.discrete_check.setToolTip("Preview the colormap with quantile colorbands")
        self.discrete_check.toggled.connect(self._on_item_selection_changed)
        
        self.discrete_spinbox = QSpinBox()
        self.discrete_spinbox.setObjectName("colormapDiscreteSpinBox")
        self.discrete_spinbox.setRange(2, 30)
        self.discrete_spinbox.setValue(10)
        self.discrete_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.discrete_spinbox.setFixedWidth(60)
        self.discrete_spinbox.setToolTip("Number of discrete color bins")
        self.discrete_spinbox.setEnabled(False)
        self.discrete_spinbox.valueChanged.connect(self._on_item_selection_changed)
        self.discrete_check.toggled.connect(self.discrete_spinbox.setEnabled)
        
        options_layout.addWidget(self.reverse_check)
        options_layout.addWidget(self.grayscale_check)
        options_layout.addWidget(self.discrete_check)
        options_layout.addWidget(self.discrete_spinbox)
        options_layout.addStretch()

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        layout.addLayout(options_layout)
        
        self.empty_search_label = QLabel("No colormaps found matching your search")
        self.empty_search_label.setObjectName("colormapEmptySearchLabel")
        self.empty_search_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_search_label.setHidden(True)
        layout.addWidget(self.empty_search_label)

        self.list_widget = DataPlotStudioListWidget()
        self.list_widget.setObjectName("colormapListWidget")
        self.list_widget.setIconSize(QSize(100, 20))
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setSpacing(2)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.itemSelectionChanged.connect(self._on_item_selection_changed)
        layout.addWidget(self.list_widget)
        
        self.preview_container = QFrame()
        self.preview_container.setObjectName("colormapPreviewContainer")
        self.preview_container.setFrameShape(QFrame.Shape.StyledPanel)
        self.preview_container.setHidden(True)
        
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(8, 8, 8, 8)

        preview_header_layout = QHBoxLayout()        
        self.category_label = QLabel("")
        self.category_label.setObjectName("colormapCategoryLabel")
        self.category_label.setProperty("class", "metadata-label")
        
        self.name_label = QLabel("")
        self.name_label.setObjectName("colormapNameLabel")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        font = self.name_label.font()
        font.setBold(True)
        self.name_label.setFont(font)
        
        preview_header_layout.addWidget(self.category_label)
        preview_header_layout.addWidget(self.name_label)
        preview_layout.addLayout(preview_header_layout)
        
        gradient_layout = QHBoxLayout()
        self.low_label = QLabel("Low")
        self.low_label.setObjectName("colormapLowLabel")
        self.low_label.setProperty("styleClass", "muted_text")
        
        self.preview_label = QLabel()
        self.preview_label.setObjectName("colormapPreviewLabel")
        self.preview_label.setMinimumSize(1, 40)
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.high_label = QLabel("High")
        self.high_label.setObjectName("colormapHighLabel")
        self.high_label.setProperty("styleClass", "muted_text")
        
        gradient_layout.addWidget(self.low_label)
        gradient_layout.addWidget(self.preview_label, stretch=1)
        gradient_layout.addWidget(self.high_label)
        
        preview_layout.addLayout(gradient_layout)
        layout.addWidget(self.preview_container)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.setObjectName("colormapButtonBox")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        layout.addWidget(self.button_box)

        icon_update_interval_ms = 200
        self._icon_update_timer = QTimer(self)
        self._icon_update_timer.setSingleShot(True)
        self._icon_update_timer.setInterval(icon_update_interval_ms)
        self._icon_update_timer.timeout.connect(self._apply_list_icon_updates)
        self._pending_icon_state: tuple[bool, bool, int] = (False, False, 0)

        self._populate_colormaps()

        if current_colormap:
            items = self.list_widget.findItems(current_colormap, Qt.MatchFlag.MatchExactly)
            valid_items = [i for i in items if i.data(Qt.ItemDataRole.UserRole) != "header"]
            if valid_items:
                self.list_widget.setCurrentItem(valid_items[0])
                valid_items[0].setSelected(True)
                self.list_widget.scrollToItem(valid_items[0])
        
        self._filter_items("")
        self.search_input.setFocus()
        self.search_input.installEventFilter(self)

        settings = QSettings("DataPlotStudio", "ColormapPicker")
        if settings.value("geometry"):
            self.restoreGeometry(settings.value("geometry"))

    def closeEvent(self, event: QCloseEvent) -> None:
        """Save geometry when the dialog is closed"""
        settings = QSettings("DataPlotStudio", "ColormapPicker")
        settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Ensure the preview gradient stretches when the window is resized"""
        super().resizeEvent(event)
        if event.size().width() != event.oldSize().width():
            if not self.preview_container.isHidden():
                self._on_item_selection_changed()
    
    def eventFilter(self, source: QObject, event: QEvent | QKeyEvent) -> bool:
        if source is self.search_input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Down:
                self.list_widget.setFocus()
                if not self.list_widget.selectedItems():
                    for i in range(self.list_widget.count()):
                        item = self.list_widget.item(i)
                        if not item.isHidden() and item.data(Qt.ItemDataRole.UserRole) != "header":
                            self.list_widget.setCurrentItem(item)
                            item.setSelected(True)
                            break
                return True
            elif event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
                if self.button_box.button(QDialogButtonBox.StandardButton.Ok).isEnabled():
                    self.accept()
                    return True
        return super().eventFilter(source, event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            if self.button_box.button(QDialogButtonBox.StandardButton.Ok).isEnabled():
                self.accept()
                return
        super().keyPressEvent(event)
    
    def _on_item_selection_changed(self) -> None:
        selected_items = self.list_widget.selectedItems()
        has_valid_selection = bool(selected_items and selected_items[0].data(Qt.ItemDataRole.UserRole) != "header")
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(has_valid_selection)

        is_reversed = self.reverse_check.isChecked()
        is_grayscale = self.grayscale_check.isChecked()
        discrete_steps = self.discrete_spinbox.value() if self.discrete_check.isChecked() else 0

        sender = self.sender()
        if sender in (self.reverse_check, self.grayscale_check, self.discrete_check, self.discrete_spinbox):
            self._update_list_icons(is_reversed, is_grayscale, discrete_steps)

        if has_valid_selection:
            colormap_name = selected_items[0].text()

            category = self.colormap_to_category.get(colormap_name, "Custom / Other")
            self.category_label.setText(f"Category: {category}")
            self.name_label.setText(colormap_name)

            if is_reversed:
                self.low_label.setText("High")
                self.high_label.setText("Low")
            else:
                self.low_label.setText("Low")
                self.high_label.setText("High")

            target_width = max(150, self.preview_container.width())
            target_height = 40

            preview_pixmap = self.generate_preview_pixmap(colormap_name, target_width, target_height, is_reversed, is_grayscale, discrete_steps)
            self.preview_label.setPixmap(preview_pixmap)
            self.preview_container.setHidden(False)
        else:
            self.preview_container.setHidden(True)

    def _update_list_icons(self, is_reversed: bool, is_grayscale: bool, discrete_steps: int) -> None:
        """Triggers a debounced update of the list icons to prevent UI stuttering"""
        self._pending_icon_state = (is_reversed, is_grayscale, discrete_steps)
        self._icon_update_timer.start()

    def _apply_list_icon_updates(self) -> None:
        """Updates all list icons to reflect current modifier state"""
        is_reversed, is_grayscale, discrete_steps = self._pending_icon_state
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == "colormap":
                colormap_name = item.text()
                icon = self.generate_icon(colormap_name, is_reversed, is_grayscale, discrete_steps)
                item.setIcon(icon)
    
    def accept(self) -> None:
        """An override to accept() to save a selected colormap to Settings"""
        # First we get the basename of the colormap
        # Without _r 
        # Use the list as reference?
        selected_items = self.list_widget.selectedItems()
        
        if selected_items and selected_items[0].data(Qt.ItemDataRole.UserRole) == "header":
            return
        base_name = selected_items[0].text()
        
        ## Save the basename to the setings history.
        # the reverse checkbox is a separate colormap
        if base_name:
            self._save_recent_colormap(base_name)
            if self.reverse_check.isChecked():
                self._final_selected_colormap = f"{base_name}_r"
            else:
                self._final_selected_colormap = base_name
        else:
            self._final_selected_colormap = self.selected_colormap

        settings = QSettings("DataPlotStudio", "ColormapPicker")
        settings.setValue("geometry", self.saveGeometry())
        
        super().accept()
    
    def _save_recent_colormap(self, name: str) -> None:
        """Saves the colormap to the QSettings history"""
        settings = QSettings("DataPlotStudio", "ColormapPicker")
        recents = settings.value("recent_colormaps", [], type=list)
        
        if name in recents:
            recents.remove(name)
        
        recents.insert(0, name)
        
        # Keep only 5
        recents = recents[:5]
        settings.setValue("recent_colormaps", recents)

    def _populate_colormaps(self) -> None:
        """Populates the list with colormaps"""
        try:
            all_maps = set([m for m in matplotlib.colormaps if not m.endswith("_r")])
        except Exception:
            all_maps = {"viridis", "plasma", "inferno", "magma"}
        
        added_maps = set()

        def add_header(text: str):
            item = QListWidgetItem()
            item.setText(text)
            item.setData(Qt.ItemDataRole.UserRole, "header")
            item.setFlags(Qt.ItemFlag.NoItemFlags)

            font = item.font()
            font.setBold(True)
            font.setPointSize(10)
            item.setFont(font)

            item.setForeground(QBrush(QColor("black")))
            item.setBackground(QBrush(QColor("#FFFFFF")))
            item.setSizeHint(QSize(0, 25))
            self.list_widget.addItem(item)
        
        settings = QSettings("DataPlotStudio", "ColormapPicker")
        recents = settings.value("recent_colormaps", [], type=list)
        valid_recents = [r for r in recents if r in all_maps]
        
        if valid_recents:
            add_header("Recently Used")
            for name in valid_recents:
                self._add_colormap_item(name)

        for category, maps_list in self.COLORMAP_CATEGORIES.items():
            available_in_cat = [m for m in maps_list if m in all_maps]
            if available_in_cat:
                add_header(category)
                for name in available_in_cat:
                    self._add_colormap_item(name)
                    added_maps.add(name)
        
        remaining = sorted(list(all_maps - added_maps))
        if remaining:
            add_header("Other")
            for name in remaining:
                self._add_colormap_item(name)
    
    def _add_colormap_item(self, name: str) -> None:
        """Creates and adds the colormap to the list"""
        item = QListWidgetItem(name)
        item.setData(Qt.ItemDataRole.UserRole, "colormap")

        item.setSizeHint(QSize(0, 24))

        is_reversed = self.reverse_check.isChecked()
        is_grayscale = self.grayscale_check.isChecked()
        discrete_steps = self.discrete_spinbox.value() if self.discrete_check.isChecked() else 0

        icon = self.generate_icon(name, is_reversed, is_grayscale, discrete_steps)
        item.setIcon(icon)
        self.list_widget.addItem(item)

    @staticmethod
    @lru_cache(maxsize=512)
    def generate_icon(colormap_name: str, is_reversed: bool = False, is_grayscale: bool = False, discrete_steps: int = 0) -> QIcon:
        """Method to generate an icon that matches the color gradient of the matplotlib colormaps"""
        width = 100
        height = 20
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        try:
            colormap = matplotlib.colormaps[colormap_name]

            if discrete_steps > 0:
                band_width = width / discrete_steps
                painter.setPen(Qt.PenStyle.NoPen)

                for i in range(discrete_steps):
                    position = (i + 0.5) / discrete_steps
                    color_pos = 1.0 - position if is_reversed else position
                    rgba = colormap(color_pos)

                    if is_grayscale:
                        luminance = (0.299 * rgba[0]) + (0.587 * rgba[1]) + (0.114 * rgba[2])
                        color = QColor.fromRgbF(luminance, luminance, luminance, 1.0)
                    else:
                        color = QColor.fromRgbF(rgba[0], rgba[1], rgba[2], 1.0)

                    painter.setBrush(QBrush(color))
                    painter.drawRect(int(i * band_width), 0, int(band_width) + 1, height)
            else:
                gradient = QLinearGradient(0, 0, width, 0)
                steps = 40
                for i in range(steps + 1):
                    position = i / steps
                    color_pos = 1.0 - position if is_reversed else position
                    rgba = colormap(color_pos)

                    if is_grayscale:
                        luminance = (0.299 * rgba[0]) + (0.587 * rgba[1]) + (0.114 * rgba[2])
                        color = QColor.fromRgbF(luminance, luminance, luminance, 1.0)
                    else:
                        color = QColor.fromRgbF(rgba[0], rgba[1], rgba[2], 1.0)

                    gradient.setColorAt(position, color)

                painter.setBrush(QBrush(gradient))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(0, 0, width, height)
        except Exception as error:
            painter.setBrush(QBrush(Qt.GlobalColor.gray))
            painter.drawRect(0, 0, width, height)
            print(f"Failed to generate icon for {colormap_name}: {error}")
        finally:
            painter.end()
        return QIcon(pixmap)

    @staticmethod
    def generate_preview_pixmap(
        colormap_name: str,
        width: int,
        height: int,
        is_reversed: bool = False, 
        is_grayscale: bool = False, 
        discrete_steps: int = 0
        ) -> QPixmap:

        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        try:
            colormap = matplotlib.colormaps[colormap_name]
            
            if discrete_steps > 0:
                band_width = width / discrete_steps
                painter.setPen(Qt.PenStyle.NoPen)
                
                for i in range(discrete_steps):
                    position = (i + 0.5) / discrete_steps
                    color_pos = 1.0 - position if is_reversed else position
                    rgba = colormap(color_pos)
                    
                    if is_grayscale:
                        luminance = (0.299 * rgba[0]) + (0.587 * rgba[1]) + (0.114 * rgba[2])
                        color = QColor.fromRgbF(luminance, luminance, luminance, 1.0)
                    else:
                        color = QColor.fromRgbF(rgba[0], rgba[1], rgba[2], 1.0)
                        
                    painter.setBrush(QBrush(color))
                    painter.drawRect(int(i * band_width), 0, int(band_width) + 1, height)
            else:
                gradient = QLinearGradient(0, 0, width, 0)
                steps = 100
                for i in range(steps + 1):
                    position = i / steps
                    color_pos = 1.0 - position if is_reversed else position
                    rgba = colormap(color_pos)
                    
                    if is_grayscale:
                        luminance = (0.299 * rgba[0]) + (0.587 * rgba[1]) + (0.114 * rgba[2])
                        color = QColor.fromRgbF(luminance, luminance, luminance, 1.0)
                    else:
                        color = QColor.fromRgbF(rgba[0], rgba[1], rgba[2], 1.0)
                        
                    gradient.setColorAt(position, color)

                painter.setBrush(QBrush(gradient))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(0, 0, width, height)
                
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(Qt.PenStyle.SolidLine)
            painter.drawRect(0, 0, width - 1, height - 1)

        except Exception as error:
            painter.setBrush(QBrush(Qt.GlobalColor.gray))
            painter.drawRect(0, 0, width, height)
            print(f"Failed to generate preview for {colormap_name}: {error}")
        finally:
            painter.end()
        return pixmap

    def _filter_items(self, text: str) -> None:
        """Filters the items list. Show header with one or more childs"""
        search_text = text.lower()
        current_header = None
        header_has_visible_child = False
        visible_colormap_count = 0
        first_visible_item = None
        header_is_match = False

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            role = item.data(Qt.ItemDataRole.UserRole)

            if role == "header":
                if current_header:
                    current_header.setHidden(not header_has_visible_child)
                
                current_header = item
                header_has_visible_child = False
                header_is_match = search_text in item.text().lower()
                item.setHidden(False)
            else:
                is_match = search_text in item.text().lower() or header_is_match
                item.setHidden(not is_match)

                if is_match:
                    header_has_visible_child = True
                    visible_colormap_count += 1
                    if first_visible_item is None:
                        first_visible_item = item
        
        if current_header:
            current_header.setHidden(not header_has_visible_child)
        
        self.empty_search_label.setHidden(visible_colormap_count > 0)

        if text and first_visible_item:
            self.list_widget.setCurrentItem(first_visible_item)
            first_visible_item.setSelected(True)
        elif not text and self.list_widget.selectedItems():
            self.list_widget.scrollToItem(self.list_widget.selectedItems()[0])

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Handles double click"""
        if item.data(Qt.ItemDataRole.UserRole) == "header":
            return
        
        self.selected_colormap = item.text()
        self.accept()

    def get_selected_colormap(self) -> str:
        """Returns the selected colormap name with an appending _r if the reverse checkbox is checked"""
        return self._final_selected_colormap