from PyQt6.QtCore import QPoint, QSize, Qt
from PyQt6.QtGui import QColor, QCursor, QIcon, QMouseEvent, QPaintEvent, QPainter, QPen
from PyQt6.QtWidgets import QCheckBox, QComboBox, QCompleter, QDoubleSpinBox, QGroupBox, QLineEdit, QListWidget, QMenu, QRadioButton, QSlider, QSpinBox, QStyle, QStyleOptionSlider, QToolButton, QToolTip

from core.resource_loader import get_resource_path


class DataPlotStudioMenu(QMenu):
    """Custom QMenu"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setProperty("styleClass", "dpsMenu")


class DataPlotStudioSpinBox(QSpinBox):
    """A QSpinBox with animated border color on hover/focus."""
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("styleClass", "dpsSpinBox")


class DataPlotStudioSlider(QSlider):
    """New qslider"""

    def __init__(self, orientation: Qt.Orientation = Qt.Orientation.Horizontal, parent=None) -> None:
        if not isinstance(orientation, Qt.Orientation):
            parent = orientation
            orientation = Qt.Orientation.Horizontal

        super().__init__(orientation, parent)
        self.setProperty("styleClass", "dpsSlider")

        if orientation == Qt.Orientation.Horizontal:
            pass

        if orientation == Qt.Orientation.Horizontal:
            self.setMinimumHeight(40)
        else:
            self.setMinimumWidth(40)

        if self.tickPosition() == QSlider.TickPosition.NoTicks:
            self.setTickPosition(QSlider.TickPosition.TicksBelow)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handles mouse press events to jump the slider's value
        to the absolute position of the users click
        """
        if event.button() == Qt.MouseButton.LeftButton:
            style_option = QStyleOptionSlider()
            self.initStyleOption(style_option)

            # Get coordinates and span based on orientation
            if self.orientation() == Qt.Orientation.Horizontal:
                click_position: int = event.pos().x()
                slider_span: int = self.width()
            else:
                click_position: int = event.pos().y()
                slider_span: int = self.height()

            new_value: int = self.style().sliderValueFromPosition(
                self.minimum(),
                self.maximum(),
                click_position,
                slider_span,
                style_option.upsideDown
            )
            self.setValue(new_value)
            event.accept()

        super().mousePressEvent(event)

        # also show the tooltip for the value
        if self.isEnabled():
            self._show_value_tooltip()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Update tooltip position and value while dragging"""
        super().mouseMoveEvent(event)
        self._show_value_tooltip()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Hide tooltip on release"""
        super().mouseReleaseEvent(event)
        QToolTip.hideText()

    def _show_value_tooltip(self) -> None:
        """Update the text, position of the tooltip for the value"""
        val_str = str(self.value())

        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        style = self.style()

        handle_rect = style.subControlRect(
            QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderHandle, self
        )

        if handle_rect.isValid():
            global_pos = self.mapToGlobal(handle_rect.center())
            tooltip_pos = global_pos - QPoint(0, 35)
            QToolTip.showText(tooltip_pos, val_str, self)
        else:
            QToolTip.showText(QCursor.pos(), val_str, self)


    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Custom paint to draw tick marks on groove
        """
        super().paintEvent(event)

        tick_pos = self.tickPosition()
        if tick_pos == QSlider.TickPosition.NoTicks:
            return

        painter = QPainter(self)
        painter.setPen(QPen(QColor("#a0a0a0"), 1))

        # Determine tickinterval
        interval = self.tickInterval()
        if interval == 0:
            interval = self.pageStep()

        if interval <= 0:
            return

        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        style = self.style()

        groove_rect = style.subControlRect(
            QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderGroove, self
        )

        val = self.minimum()
        max_val = self.maximum()
        steps = (max_val - val) / interval
        if steps > 1000:
            interval = (max_val - val) // 100

        if val > max_val:
            return

        while val <= max_val:
            temp_opt = QStyleOptionSlider(opt)
            temp_opt.sliderPosition = val
            temp_opt.sliderValue = val

            handle_rect = style.subControlRect(
                QStyle.ComplexControl.CC_Slider, temp_opt, QStyle.SubControl.SC_SliderHandle, self
            )

            center = handle_rect.center()

            if self.orientation() == Qt.Orientation.Horizontal:

                if tick_pos in (QSlider.TickPosition.TicksAbove, QSlider.TickPosition.TicksBothSides):
                    painter.drawLine(center.x(), center.y() - 10, center.x(), center.y() - 15)

                if tick_pos in (QSlider.TickPosition.TicksBelow, QSlider.TickPosition.TicksBothSides):
                    painter.drawLine(center.x(), center.y() + 10, center.x(), center.y() + 15)

            else:
                if tick_pos in (QSlider.TickPosition.TicksLeft, QSlider.TickPosition.TicksBothSides):
                    painter.drawLine(center.x() - 10, center.y(), center.x() - 15, center.y())

                if tick_pos in (QSlider.TickPosition.TicksRight, QSlider.TickPosition.TicksBothSides):
                    painter.drawLine(center.x() + 10, center.y(), center.x() + 15, center.y())

            val += interval


class DataPlotStudioRadioButton(QRadioButton):
    """A QRadioButton with animated border color on hover/focus."""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setProperty("styleClass", "dpsRadioButton")


class DataPlotStudioListWidget(QListWidget):
    """Targets the object for a general list widget style"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("dpsListWidget")


class DataPlotStudioLineEdit(QLineEdit):
    """A QLineEdit with the DPS styleClass"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setProperty("styleClass", "dpsLineEdit")


class DataPlotStudioGroupBox(QGroupBox):
    """GroupBox animation on hover"""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(title, parent)
        self.setProperty("styleClass", "dpsGroupBox")


class DataPlotStudioDoubleSpinBox(QDoubleSpinBox):
    """A QDoubleSpinBox with animated border color on hover/focus."""
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("styleClass", "dpsSpinBox")


class DataPlotStudioComboBox(QComboBox):
    """Custom Combobox with a search functionality using a QSortFilterProxyModel"""
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("styleClass", "dpsComboBox")

        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        completer = self.completer()
        if completer:
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.popup().setObjectName("dpsComboBoxPopup")

        self.lineEdit().setPlaceholderText("Select or search...")

        self._clear_button: QToolButton = QToolButton(self)
        self._clear_button.setObjectName("dpsComboBoxClearButton")
        self._clear_button.setIcon(QIcon(get_resource_path("icons/clean.svg"))) # TODO: Update this icon
        self._clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_button.setToolTip("Clear selection")
        self._clear_button.clicked.connect(self.clear_selection)
        self._clear_button.hide()

    def clear_selection(self) -> None:
        self.setCurrentIndex(-1)
        self.setEditText("")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        button_size: QSize = self._clear_button.sizeHint()
        x_pos: int = self.width() - button_size.width() - 25
        y_pos: int = (self.height() - button_size.height()) // 2
        self._clear_button.move(x_pos, y_pos)

    def enterEvent(self, event) -> None:
        if self.currentIndex() != -1:
            self._clear_button.show()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if not self._clear_button.underMouse() and not self.hasFocus():
            self._clear_button.hide()
        super().leaveEvent(event)

    def focusInEvent(self, event) -> None:
        if self.currentIndex() != -1:
            self._clear_button.show()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        if not self.underMouse():
            self._clear_button.hide()
        if event is not None:
            super().focusOutEvent(event)


class DataPlotStudioCheckBox(QCheckBox):
    """A reusable QCheckBox with DPS styling attatched."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setProperty("styleClass", "dpsCheckBox")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_accessibility_metadata(self, name: str, description: str = "") -> None:
        self.setAccessibleName(name)
        if description:
            self.setAccessibleDescription(description)
            self.setToolTip(description)