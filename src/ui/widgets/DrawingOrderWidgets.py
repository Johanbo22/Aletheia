import logging
from typing import Sequence

from PyQt6.QtCore import QEasingCurve, QEvent, QItemSelectionModel, QPoint, QPropertyAnimation, QSortFilterProxyModel, \
    Qt, pyqtSignal
from PyQt6.QtGui import QDropEvent, QEnterEvent, QIcon, QKeyEvent, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QAbstractItemView, QFrame, QGraphicsDropShadowEffect, QLineEdit, QListView, QPushButton, \
    QVBoxLayout, QWidget

from src.controller.plot_controllers.drawing_order_manager import PlotLayerItem

logger = logging.getLogger(__name__)

# Custom ItemDataRole for the MPL artistID
LAYER_ID_ROLE = Qt.ItemDataRole.UserRole + 1
BASE_LABEL_ROLE = Qt.ItemDataRole.UserRole + 2
ZORDER_ROLE = Qt.ItemDataRole.UserRole + 3

class DrawingOrderFloatingActionButton(QPushButton):
    """
    A floating action button that triggers the Drawing Order popup menu
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("drawingOrderFAB")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Open drawing order list")

        self.setIcon(QIcon("../icons/data_operations/arrow-down-up.svg"))

        self._collapsed_width = 45
        self._expanded_width = 170

        self.setMinimumSize(self._collapsed_width, self._collapsed_width)
        self.setMaximumSize(self._collapsed_width, self._collapsed_width)

        self._animation = QPropertyAnimation(self, b"minimumWidth")
        animation_duration: int = 150
        self._animation.setDuration(animation_duration)
        self._animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._animation.valueChanged.connect(self.setMaximumWidth)

    def enterEvent(self, event: QEnterEvent) -> None:
        """Animate expansion on hover and reveal text"""
        super().enterEvent(event)
        self._animation.stop()
        self._animation.setStartValue(self.width())
        self._animation.setEndValue(self._expanded_width)
        self.setText(" Drawing Order")
        self._animation.start()

    def leaveEvent(self, event: QEvent) -> None:
        """Animate collapse on hover and hide the text"""
        super().leaveEvent(event)
        self._animation.stop()
        self._animation.setStartValue(self.width())
        self._animation.setEndValue(self._collapsed_width)
        self.setText("")
        self._animation.start()

class DraggableLayerList(QListView):
    """
    Custom QListView that handles drag-and-drop and keyboard reordering
    """
    userDroppedItem = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setAlternatingRowColors(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def dropEvent(self, event: QDropEvent) -> None:
        """Catch the completion of a drag and drop event"""
        super().dropEvent(event)
        self.userDroppedItem.emit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Intercept Alt+Up and Alt+Down to move the row in the model
        Standard up/down keys are passed to super to change selection instead of moving row
        :param event:
        """
        move_row_up: int = -1
        move_row_down: int = 1
        modifiers = event.modifiers()
        if modifiers == Qt.KeyboardModifier.AltModifier:
            if event.key() == Qt.Key.Key_Up:
                self._move_selected_row(move_row_up)
                event.accept()
                return
            if event.key() == Qt.Key.Key_Down:
                self._move_selected_row(move_row_down)
                event.accept()
                return

        super().keyPressEvent(event)

    def _move_selected_row(self, offset: int) -> None:
        """
        Move the currently selected item up or down in the source model
        :param offset: Direction to move as index value offsets
        """
        proxy = self.model()
        if not isinstance(proxy, QSortFilterProxyModel):
            return

        selection = self.selectionModel().selectedIndexes()
        if not selection:
            return

        proxy_idx = selection[0]
        source_idx = proxy.mapToSource(proxy_idx)
        source_model = proxy.sourceModel()

        current_row = source_idx.row()
        target_row = current_row + offset

        if not (0 <= target_row < source_model.rowCount()):
            return

        items = source_model.takeRow(current_row)
        insert_row = target_row if offset < 0 else target_row
        source_model.insertRow(insert_row, items)

        new_source_idx = source_model.index(insert_row, 0)
        new_proxy_idx = proxy.mapFromSource(new_source_idx)
        self.selectionModel().setCurrentIndex(
            new_proxy_idx,
            QItemSelectionModel.SelectionFlag.ClearAndSelect
        )
        self.userDroppedItem.emit()

class DrawingOrderPopup(QFrame):
    """
    Non-modal popup containing the z order list and a search bar
    """
    layerVisibilityToggled = pyqtSignal(str, bool)
    layerOrderChanged = pyqtSignal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("drawingOrderPopup")
        self.setVisible(False)

        self._animation = QPropertyAnimation(self, b"pos")
        self._animation_duration: int = 250

        self._setup_ui()
        self._setup_models()

    def _setup_ui(self) -> None:
        self.setMinimumSize(250, 300)
        self.setMaximumSize(300, 400)

        # Elevate widget with a shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(Qt.GlobalColor.black)
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)

        self._search_bar = QLineEdit()
        self._search_bar.setObjectName("drawingOrderSearch")
        self._search_bar.setPlaceholderText("Search elements...")
        self._search_bar.setClearButtonEnabled(True)

        self._list_view = DraggableLayerList()
        self._list_view.setObjectName("drawingOrderList")

        self._layout.addWidget(self._search_bar)
        self._layout.addWidget(self._list_view)

    def _setup_models(self) -> None:
        """Start up the data models and proxy filtering models"""
        self._model = QStandardItemModel(self)
        self._model.itemChanged.connect(self._on_item_changed)

        self._proxy_model = QSortFilterProxyModel(self)
        self._proxy_model.setSourceModel(self._model)
        self._proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._proxy_model.setFilterRole(Qt.ItemDataRole.DisplayRole)

        self._search_bar.textChanged.connect(self._proxy_model.setFilterRegularExpression)
        self._list_view.setModel(self._proxy_model)
        self._list_view.userDroppedItem.connect(self._on_user_dropped_item)

    def toggle_popup(self, anchor_widget: QWidget) -> None:
        """
        Toggles the popup visibility with a slide animation relative to the anchor widget
        :param anchor_widget: The widget to anchor the popup to
        """
        if self.isVisible():
            self._animate_close(anchor_widget)
        else:
            self._animate_open(anchor_widget)

    def _get_target_pos(self, anchor_widget: QWidget) -> QPoint:
        """
        Calculates the resting position of the popup anchored to the target widget
        """
        global_pos = anchor_widget.mapToGlobal(QPoint(0, 0))
        if self.parentWidget():
            local_pos = self.parentWidget().mapToGlobal(global_pos)
            parent_rect = self.parentWidget().rect()
        else:
            local_pos = global_pos
            parent_rect = None

        width = self.width() if self.width() >= 250 else 250
        height = self.height() if self.height() >= 300 else 300

        x = local_pos.x() + anchor_widget.width() - width
        y = local_pos.y() - height - 10

        if parent_rect and y < 0:
            y = local_pos.y() + anchor_widget.height() + 10

        if parent_rect:
            if x < 0:
                x = 10
            elif x + width > parent_rect.width():
                x = parent_rect.width() - width - 10

        return QPoint(x, y)

    def _get_start_pos(self, anchor_widget: QWidget) -> QPoint:
        """Calculate the starting position of the popup"""
        global_pos = anchor_widget.mapToGlobal(QPoint(0, 0))
        if self.parentWidget():
            local_pos = self.parentWidget().mapFromGlobal(global_pos)
        else:
            local_pos = global_pos

        width = self.width() if self.width() >= 250 else 250

        x = local_pos.x() + (anchor_widget.width() // 2) - (width // 2)
        y = local_pos.y() + (anchor_widget.height() // 2)

        return QPoint(x, y)

    def _animate_open(self, anchor_widget: QWidget) -> None:
        """Play the slide in animation"""
        self._animation.stop()

        target_pos = self._get_target_pos(anchor_widget)
        start_pos = self._get_start_pos(anchor_widget)

        self.move(start_pos)
        self.setVisible(True)
        self.raise_()

        self._animation.setDuration(self._animation_duration)
        self._animation.setStartValue(start_pos)
        self._animation.setEndValue(target_pos)
        self._animation.setEasingCurve(QEasingCurve.Type.OutBack)

        try:
            self._animation.finished.disconnect()
        except TypeError:
            pass

        self._animation.start()

    def _animate_close(self, anchor_widget: QWidget) -> None:
        """Play the slide-out animation pulling back into the anchor and hide."""
        self._animation.stop()

        target_pos = self._get_start_pos(anchor_widget)
        start_pos = self.pos()

        self._animation.setDuration(self._animation_duration)
        self._animation.setStartValue(start_pos)
        self._animation.setEndValue(target_pos)
        self._animation.setEasingCurve(QEasingCurve.Type.InBack)

        try:
            self._animation.finished.disconnect()
        except TypeError:
            pass

        self._animation.finished.connect(self.hide)
        self._animation.start()

    def populate_layers(self, layers: Sequence[PlotLayerItem]) -> None:
        """
        Receives a PlotLayerItem data struct from the controller and renders them
        :param layers:  Sequence of PlotLayerItem sorted by their zorder
        """
        current_ids = []
        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            if item:
                current_ids.append(item.data(LAYER_ID_ROLE))

        new_ids = [layer.layer_id for layer in layers]

        if current_ids and current_ids == new_ids:
            try:
                self._model.itemChanged.disconnect(self._on_item_changed)
            except TypeError:
                pass

            for row, layer in enumerate(layers):
                item = self._model.item(row)
                if item:
                    check_state = Qt.CheckState.Checked if layer.is_visible else Qt.CheckState.Unchecked
                    if item.checkState() != check_state:
                        item.setCheckState(check_state)

                    item.setData(layer.zorder, ZORDER_ROLE)
                    base_label = item.data(BASE_LABEL_ROLE) or layer.label
                    display_text = (f"{base_label} (Z: {layer.zorder:.0f})")

                    item.setText(display_text)
                    item.setToolTip(display_text)

            self._model.itemChanged.connect(self._on_item_changed)
            return

        try:
            self._model.itemChanged.disconnect(self._on_item_changed)
        except TypeError:
            pass

        self._model.clear()

        for layer in layers:
            display_text = f"{layer.label} (Z: {layer.zorder:.0f})"
            item = QStandardItem(layer.icon, display_text)
            item.setToolTip(display_text)

            item.setCheckable(True)
            check_state = Qt.CheckState.Checked if layer.is_visible else Qt.CheckState.Unchecked
            item.setCheckState(check_state)

            item.setEditable(False)
            item.setDragEnabled(True)
            item.setDropEnabled(False)

            item.setData(layer.layer_id, LAYER_ID_ROLE)
            item.setData(layer.label, BASE_LABEL_ROLE)
            item.setData(layer.zorder, ZORDER_ROLE)

            self._model.appendRow(item)

        self._model.itemChanged.connect(self._on_item_changed)

    def _on_item_changed(self, item: QStandardItem) -> None:
        """Handle the visibility toggle triggering"""
        layer_id = item.data(LAYER_ID_ROLE)
        is_visible = (item.checkState() == Qt.CheckState.Checked)
        self.layerVisibilityToggled.emit(layer_id, is_visible)

    def _on_user_dropped_item(self) -> None:
        """Extract the new top to bottom order and emit the update signal"""
        ordered_ids: list[str] = []
        current_zorders: list[float] = []

        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            if item:
                z_val = item.data(ZORDER_ROLE)
                current_zorders.append(float(z_val) if z_val is not None else 0.0)

        current_zorders.sort(reverse=True)

        try:
            self._model.itemChanged.disconnect(self._on_item_changed)
        except TypeError:
            pass

        epsilon_step = 1e-5

        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            if item:
                layer_id = item.data(LAYER_ID_ROLE)
                ordered_ids.append(layer_id)

                if row < len(current_zorders):
                    base_z = round(current_zorders[row], 3)
                    strict_zorder = base_z - (row * epsilon_step)
                    base_label = item.data(BASE_LABEL_ROLE) or "Layer"

                    display_text = (f"{base_label} (Z: {strict_zorder:.0f})")

                    item.setData(strict_zorder, ZORDER_ROLE)
                    item.setText(display_text)
                    item.setToolTip(display_text)

        self._model.itemChanged.connect(self._on_item_changed)

        if ordered_ids:
            self.layerOrderChanged.emit(ordered_ids)
