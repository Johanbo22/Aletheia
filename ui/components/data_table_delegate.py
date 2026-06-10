from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QStyle, QApplication
from PyQt6.QtCore import Qt, QModelIndex, QObject
from PyQt6.QtGui import QPainter, QPen, QBrush, QPalette

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