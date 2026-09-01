from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QPainter, QPalette
from PyQt6.QtWidgets import QApplication, QLineEdit, QStyle, QStyleOptionViewItem, QStyledItemDelegate, QWidget

class DataTableDelegate(QStyledItemDelegate):
    """
    Custom delegate for rendering dataTable items

    This delegate provides a performant styling using QStyle drawing
    """
    def __init__(self, parent=None, horizontal_padding: int = 8):
        super().__init__(parent)
        self.horizontal_padding = horizontal_padding
    
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        painter.save()
        painter.setClipRect(opt.rect)

        bg_brush = opt.backgroundBrush
        if bg_brush.style() != Qt.BrushStyle.NoBrush:
            painter.fillRect(opt.rect, bg_brush)
        elif opt.features & QStyleOptionViewItem.ViewItemFeature.Alternate:
            painter.fillRect(opt.rect, opt.palette.alternateBase())
        else:
            painter.fillRect(opt.rect, opt.palette.base())

        is_selected = opt.state & QStyle.StateFlag.State_Selected
        if is_selected:
            painter.fillRect(opt.rect, opt.palette.highlight())

        border_color = opt.palette.color(QPalette.ColorGroup.Normal, QPalette.ColorRole.Text)
        border_color.setAlpha(20)
        painter.setPen(border_color)
        bottom_y = opt.rect.bottom()
        painter.drawLine(opt.rect.left(), bottom_y, opt.rect.right(), bottom_y)

        padded_rect = opt.rect.adjusted(self.horizontal_padding, 0, -self.horizontal_padding, 0)

        if opt.features & QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator:
            style = opt.widget.style() if opt.widget else QApplication.style()
            check_rect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemCheckIndicator, opt, opt.widget)

            check_opt = QStyleOptionViewItem(opt)
            check_opt.rect = check_rect
            check_opt.state &= ~QStyle.StateFlag.State_HasFocus
            style.drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorItemViewItemCheck, check_opt, painter, opt.widget)

            padded_rect.setLeft(check_rect.right() + self.horizontal_padding)

        if opt.text:
            if is_selected:
                painter.setPen(opt.palette.highlightedText().color())
            else:
                painter.setPen(opt.palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Text))

            painter.setFont(opt.font)

            align = int(opt.displayAlignment) | Qt.TextFlag.TextSingleLine

            painter.drawText(padded_rect, align, opt.text)

        painter.restore()

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        """
        Instantiates the editor widget for a given cell

        This overrides the default implementation to intercept the created editor
        of a QLineEdit and configure it for precise alignment and styling of the Table.

        :param parent: The parent widget of the editor
        :param option: The style options for the item view
        :param index: The model index of the item being edited
        :return: The configured editor widget (QWidget)
        """
        editor = super().createEditor(parent, option, index)

        if isinstance(editor, QLineEdit):
            editor.setObjectName("tableCellEditor")

            editor.setFrame(False)

        return editor

    def updateEditorGeometry(self, editor: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """
        Updates the geometry of the editor to match the cell
        Maps the editor's geometry to the cell's layout rectangle

        :param editor: The editor widget to resize
        :param option: The style options containing the cell's bounding rect
        :param index: The model index of the item being edited
        """
        editor.setGeometry(option.rect)
