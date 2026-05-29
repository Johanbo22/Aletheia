from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QStyle, QApplication
from PyQt6.QtCore import Qt, QEvent, pyqtSignal, QModelIndex, QRect, QAbstractItemModel
from PyQt6.QtGui import QPainter, QMouseEvent

from ui.icons import IconBuilder, IconType

class CustomFunctionDelegate(QStyledItemDelegate):
    """
    Custom delegate for painting inline Edit and Delete icons on hover
    for custom function items in a QTreeWidget
    """
    edit_requested = pyqtSignal(QModelIndex)
    delete_requested = pyqtSignal(QModelIndex)

    ICON_SIZE = 16
    PADDING = 6

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.edit_icon = IconBuilder.build(IconType.EditModeToggleOn)
        self.delete_icon = IconBuilder.build(IconType.DeleteItem)

    def _get_icon_rects(self, option: QStyleOptionViewItem, index: QModelIndex) -> tuple[QRect, QRect]:
        """Calculates the layout geometry for the edit and delete icons"""
        style = option.widget.style() if option.widget else QApplication.style()
        text_rect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, option, option.widget)

        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        text_width = option.fontMetrics.horizontalAdvance(text)

        y_center = option.rect.top() + (option.rect.height() - self.ICON_SIZE) // 2

        edit_x = text_rect.left() + text_width + (self.PADDING * 2)
        edit_rect = QRect(edit_x, y_center, self.ICON_SIZE, self.ICON_SIZE)

        delete_x = edit_rect.right() + self.PADDING
        delete_rect = QRect(delete_x, y_center, self.ICON_SIZE, self.ICON_SIZE)

        return edit_rect, delete_rect

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Paints the standard item and overlays icons if hovered and custom"""
        super().paint(painter, option, index)

        is_custom = index.data(Qt.ItemDataRole.UserRole + 1)
        if not is_custom:
            return

        if option.state & QStyle.StateFlag.State_MouseOver:
            edit_rect, delete_rect = self._get_icon_rects(option, index)
            self.edit_icon.paint(painter, edit_rect)
            self.delete_icon.paint(painter, delete_rect)

    def editorEvent(self, event: QEvent, model: QAbstractItemModel, option: QStyleOptionViewItem, index: QModelIndex) -> bool:
        """Intercepts mouse events over the painted icons to trigger action"""
        is_custom = index.data(Qt.ItemDataRole.UserRole + 1)

        if event.type() == QEvent.Type.MouseMove and option.widget:
            mouse_event: QMouseEvent = event
            if is_custom:
                edit_rect, delete_rect = self._get_icon_rects(option, index)
                if edit_rect.contains(mouse_event.pos()) or delete_rect.contains(mouse_event.pos()):
                    option.widget.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
                else:
                    option.widget.viewport().unsetCursor()
            else:
                option.widget.viewport().unsetCursor()

        if not is_custom:
            return super().editorEvent(event, model, option, index)

        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease, QEvent.Type.MouseButtonDblClick):
            mouse_event: QMouseEvent = event
            edit_rect, delete_rect = self._get_icon_rects(option, index)

            if edit_rect.contains(mouse_event.pos()) or delete_rect.contains(mouse_event.pos()):
                if event.type() == QEvent.Type.MouseButtonRelease:
                    if edit_rect.contains(mouse_event.pos()):
                        self.edit_requested.emit(index)
                    elif delete_rect.contains(mouse_event.pos()):
                        self.delete_requested.emit(index)

                return True
        return super().editorEvent(event, model, option, index)