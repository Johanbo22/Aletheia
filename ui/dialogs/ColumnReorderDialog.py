import pandas as pd
from PyQt6.QtCore import Qt, QEvent, QTimer, QVariantAnimation, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QFont, QColor, QBrush, QMouseEvent
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QFrame, \
    QPushButton, QHBoxLayout, QGraphicsDropShadowEffect, QSizePolicy, QApplication, QLineEdit

from core.resource_loader import get_resource_path
from ui.icons.icon_registry import IconBuilder, IconType
from ui.theme import ThemeColors


class ColumnReorderDialog(QDialog):
    """
    Dialog for reordering columns of the dataframe
    An interactive widget to drag-n-drop columns
    """
    def __init__(self, df: pd.DataFrame, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Reorder Columns")
        self.setObjectName("ColumnReorderDialog")
        self.setMinimumSize(900, 600)
        self.df = df
        self._original_columns: list[str] = list(df.columns)
        self._animations: list[QVariantAnimation] = []

        self._highlighted_header_item: QTableWidgetItem | None = None
        self._highlighted_original_font: QFont | None = None
        self._highlighted_cells: list[QTableWidgetItem] = []
        self._reset_btn_original_text: str = "Reset Order"
        self._reset_btn_original_icon: QIcon | None = None

        # A search timer for the search input to prevent scrolling on large datasets during each keystroke
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._perform_search)

        # A reset timer for the reset button to prevent a crash if the dialog is accepted before btn is allowed to reset
        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.setInterval(1500)
        self._reset_timer.timeout.connect(self._revert_reset_button)

        # An auto-scrolling timer to prevent the slow scroll
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.setInterval(16)
        self._auto_scroll_timer.timeout.connect(self._do_auto_scroll)
        self._scroll_speed: int = 0

        self.init_ui()
        
    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setSpacing(15)
        
        info_layout = QHBoxLayout()
        info_layout.setSpacing(8)
        info_icon = QLabel()
        info_icon.setPixmap(QIcon(get_resource_path("icons/menu_bar/info.svg")).pixmap(20, 20))
        info_layout.addWidget(info_icon)
        
        info_label = QLabel("Drag and drop the column headers below horizontally to reorder the Dataframe")
        info_label.setObjectName("ColumnReorderInfoLabel")
        info_label.setProperty("styleClass", "info_text")
        info_layout.addWidget(info_label)
        
        top_bar_layout.addLayout(info_layout)
        top_bar_layout.addStretch()
                
        # Search and jump to feature for wide datasets
        search_layout = QHBoxLayout()
        search_layout.setSpacing(5)
        search_icon = QLabel()
        search_icon.setPixmap(IconBuilder.build(IconType.Filter).pixmap(16, 16))
        search_layout.addWidget(search_icon)
        
        self.search_input = QLineEdit()
        self.search_input.setObjectName("ColumnReorderSearchInput")
        self.search_input.setPlaceholderText("Search column...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMaximumWidth(220)
        self.search_input.textChanged.connect(self._search_timer.start)
        search_layout.addWidget(self.search_input)
        
        top_bar_layout.addLayout(search_layout)
        
        layout.addLayout(top_bar_layout)
        
        # DataFrame "mimics" table setup
        self.table_mimic = QTableWidget()
        self.table_mimic.setObjectName("ColumnReorderMimicTable")
        self.table_mimic.setFrameShape(QFrame.Shape.NoFrame)
        self.table_mimic.setShowGrid(False)
        self.table_mimic.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table_mimic.setMinimumHeight(200)
        self.table_mimic.setAutoScroll(False)
        
        table_shadow_effect = QGraphicsDropShadowEffect(self)
        table_shadow_effect.setBlurRadius(15)
        table_shadow_effect.setColor(QColor(0, 0, 0, 30))
        table_shadow_effect.setOffset(0, 4)
        self.table_mimic.setGraphicsEffect(table_shadow_effect)
        
        self.table_mimic.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_mimic.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table_mimic.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table_mimic.setAlternatingRowColors(True)
        self.table_mimic.verticalHeader().setVisible(False)
        self.table_mimic.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        
        # Horiztonal heaeder moving abity
        self.header = self.table_mimic.horizontalHeader()
        self.header.setSectionsMovable(True)
        self.header.setHighlightSections(True)
        self.header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.header.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        self.header.setMinimumSectionSize(90)
        self.header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        self.header.viewport().installEventFilter(self)
        self.header.sectionMoved.connect(self.update_header_labels)
        
        self._populate_table()
        self.update_header_labels()
        layout.addWidget(self.table_mimic)
        
        # actions buttons
        bottom_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("Reset Order")
        self.reset_btn.setObjectName("ColumnReorderResetBtn")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setIcon(IconBuilder.build(IconType.RefreshItem))
        self.reset_btn.setToolTip("Revert the columns to their original order")
        self.reset_btn.clicked.connect(self.reset_order)
        bottom_layout.addWidget(self.reset_btn)
        
        bottom_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel", parent=self)
        self.cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(self.cancel_btn)
        
        self.apply_btn = QPushButton("Apply Column Order")
        self.apply_btn.setObjectName("MainActionButton")
        self.apply_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.apply_btn)
        
        layout.addLayout(bottom_layout)
    
    def eventFilter(self, source, event: QEvent | QMouseEvent) -> bool:
        if hasattr(self, "header") and source is self.header.viewport():
            if event.type() == QEvent.Type.MouseButtonPress:
                self.header.setCursor(Qt.CursorShape.ClosedHandCursor)
            elif event.type() == QEvent.Type.MouseMove:
                if event.buttons() & Qt.MouseButton.LeftButton:
                    pos_x = event.pos().x()
                    viewport_width = self.header.viewport().width()
                    scroll_margin = 40

                    if pos_x < scroll_margin:
                        self._scroll_speed = -int(max(1, (scroll_margin - pos_x) / 2))
                        if not self._auto_scroll_timer.isActive():
                            self._auto_scroll_timer.start()
                    elif pos_x > viewport_width - scroll_margin:
                        self._scroll_speed = int(max(1, (pos_x - (viewport_width - scroll_margin)) / 2))
                        if not self._auto_scroll_timer.isActive():
                            self._auto_scroll_timer.start()
                    else:
                        self._auto_scroll_timer.stop()
                        self._scroll_speed = 0
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self.header.setCursor(Qt.CursorShape.OpenHandCursor)
                self._auto_scroll_timer.stop()
                self._scroll_speed = 0
        return super().eventFilter(source, event)

    def _do_auto_scroll(self) -> None:
        """Handles the continuous scrolling when a header is dragged to the edge of the viewport"""
        scrollbar = self.table_mimic.horizontalScrollBar()
        if not scrollbar:
            return

        current_val = scrollbar.value()
        new_val = current_val + self._scroll_speed

        new_val = max(scrollbar.minimum(), min(new_val, scrollbar.maximum()))

        if current_val != new_val:
            scrollbar.setValue(new_val)

            cursor_pos = self.header.viewport().mapFromGlobal(self.header.cursor().pos())
            move_event = QMouseEvent(
                QEvent.Type.MouseMove,
                cursor_pos,
                Qt.MouseButton.NoButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            QApplication.postEvent(self.header.viewport(), move_event)
        else:
            self._auto_scroll_timer.stop()
    
    def reset_order(self) -> None:
        """
        Resets the visual order of the headers back to the original dataframe
        """
        for logical_index in range(self.table_mimic.columnCount()):
            visual_index = self.header.visualIndex(logical_index)
            if visual_index != logical_index:
                self.header.moveSection(visual_index, logical_index)
        self.update_header_labels()
        
        self._reset_btn_original_text = "Reset Order"
        self._reset_btn_original_icon = self.reset_btn.icon()
        
        self.reset_btn.setText("Order Reset!")
        self.reset_btn.setIcon(IconBuilder.build(IconType.Checkmark))
        
        self._reset_timer.start()
    
    def _revert_reset_button(self) -> None:
        """Reverts the reset button to its default state"""
        try:
            self.reset_btn.setText(self._reset_btn_original_text)
            if self._reset_btn_original_icon:
                self.reset_btn.setIcon(self._reset_btn_original_icon)
        except RuntimeError:
            pass

    def _perform_search(self) -> None:
        """Executes the search query after the search timer ends"""
        self.jump_to_column(self.search_input.text())

    def _clear_previous_highlights(self) -> None:
        """Stops and clears running animations and restores the original styling"""
        for anim in self._animations:
            anim.stop()
            anim.deleteLater()
        self._animations.clear()

        if self._highlighted_header_item and self._highlighted_original_font:
            self._highlighted_header_item.setFont(self._highlighted_original_font)

        for cell in self._highlighted_cells:
            if cell:
                cell.setBackground(QBrush())

        self._highlighted_header_item = None
        self._highlighted_original_font = None
        self._highlighted_cells = []

    def update_header_labels(self) -> None:
        """
        Updates the header label text with its visual index
        e.g., if 'Age' is dragged to the 3rd position, it becomes '3. Age'.
        """
        for visual_index in range(self.table_mimic.columnCount()):
            logical_index = self.header.logicalIndex(visual_index)
            original_name = self._original_columns[logical_index]
            
            new_label = f"{visual_index + 1}. {original_name}"
            
            item = self.table_mimic.horizontalHeaderItem(logical_index)
            if item:
                item.setText(new_label)
                col_dtype = str(self.df[original_name].dtype)
                tooltip_text = f"Column: {original_name}\nDatatype: {col_dtype}\nPosition: {visual_index + 1}"
                item.setToolTip(tooltip_text)
    
    def jump_to_column(self, text: str) -> None:
        """
        Scrolls to the header of the first column matching the search text
        """
        self._clear_previous_highlights()

        if not text.strip():
            self.search_input.setProperty("searchState", "default")
            self.search_input.style().unpolish(self.search_input)
            self.search_input.style().polish(self.search_input)
            return

        search_query = text.lower()
        match_found = False

        for visual_index in range(self.table_mimic.columnCount()):
            logical_index = self.header.logicalIndex(visual_index)
            col_name = self._original_columns[logical_index]

            if search_query in col_name.lower():
                match_found = True
                x_pos = self.header.sectionPosition(visual_index)

                scroll_bar = self.table_mimic.horizontalScrollBar()
                scroll_anim = QPropertyAnimation(scroll_bar, b"value", self)
                scroll_anim.setDuration(400)
                scroll_anim.setStartValue(scroll_bar.value())
                scroll_anim.setEndValue(x_pos)
                scroll_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

                self._animations.append(scroll_anim)
                scroll_anim.start()

                header_item = self.table_mimic.horizontalHeaderItem(logical_index)
                cells = [self.table_mimic.item(row, logical_index) for row in range(self.table_mimic.rowCount())]

                original_font = header_item.font() if header_item else QFont()
                if header_item:
                    highlight_font = QFont(original_font)
                    highlight_font.setBold(True)
                    header_item.setFont(highlight_font)

                    self._highlighted_header_item = header_item
                    self._highlighted_original_font = original_font
                    self._highlighted_cells = cells

                anim = QVariantAnimation(self)
                anim.setDuration(1800)
                try:
                    base_color = QColor(ThemeColors.MainColor)
                except Exception:
                    base_color = QColor("#3b82f6")

                peak_color = QColor(base_color)
                peak_color.setAlpha(200)
                mid_color = QColor(base_color)
                mid_color.setAlpha(80)
                end_color = QColor(255, 255, 255, 0)

                anim.setKeyValueAt(0.0, end_color)
                anim.setKeyValueAt(0.2, peak_color)
                anim.setKeyValueAt(0.4, mid_color)
                anim.setKeyValueAt(0.6, peak_color)
                anim.setKeyValueAt(1.0, end_color)

                anim.valueChanged.connect(lambda color, t_cells=cells: self._update_beam(color, t_cells))
                anim.finished.connect(lambda a=anim: self._finalize_highlight(a))

                self._animations.append(anim)
                anim.start()
                break

        state_value = "valid" if match_found else "invalid"
        self.search_input.setProperty("searchState", state_value)
        self.search_input.style().unpolish(self.search_input)
        self.search_input.style().polish(self.search_input)

    def _update_beam(self, color: QColor, target_cells: list) -> None:
        """Updates the background color of target cells during the highlighting animation"""
        for cell in target_cells:
            if cell:
                cell.setBackground(color)

    def _finalize_highlight(self, anim: QVariantAnimation) -> None:
        """Cleanup callback when animation finishes"""
        self._clear_previous_highlights()
    
    def _populate_table(self) -> None:
        """
        Populates the widget with dataframe columns and a few rows of data
        """
        self.table_mimic.setColumnCount(len(self._original_columns))
        self.table_mimic.setHorizontalHeaderLabels(self._original_columns)
        
        # hmmm loading max 9 rows to avoid large datasets freezing the ui
        preview_rows = min(9, len(self.df))
        self.table_mimic.setRowCount(preview_rows)
        
        for row in range(preview_rows):
            for col, _ in enumerate(self._original_columns):
                raw_val = self.df.iloc[row, col]
                if pd.isna(raw_val):
                    item = QTableWidgetItem("NaN")
                    font = item.font()
                    font.setItalic(True)
                    item.setFont(font)
                    item.setForeground(Qt.GlobalColor.gray)
                else:
                    item = QTableWidgetItem(str(raw_val))
                
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_mimic.setItem(row, col, item)
        
        self.table_mimic.resizeColumnsToContents()
        
        max_col_width = 250
        for visual_index in range(self.table_mimic.columnCount()):
            if self.table_mimic.columnWidth(visual_index) > max_col_width:
                self.table_mimic.setColumnWidth(visual_index, max_col_width)
    
    def get_new_order(self) -> list[str]:
        """
        Retrieves the new column order\n
        :return (list[str]): The column names in their new order
        """
        header = self.table_mimic.horizontalHeader()
        ordered_columns: list[str] = []
        
        for visual_index in range(self.table_mimic.columnCount()):
            logical_index = header.logicalIndex(visual_index)
            ordered_columns.append(self._original_columns[logical_index])
        
        return ordered_columns