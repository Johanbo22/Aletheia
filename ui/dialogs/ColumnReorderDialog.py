from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QDialogButtonBox, QFrame, QPushButton, QHBoxLayout, QGraphicsDropShadowEffect, QSizePolicy
from PyQt6.QtCore import Qt, QEvent, QTimer, QVariantAnimation
from PyQt6.QtGui import QIcon, QFont, QColor

import pandas as pd
from pygments import highlight

from core.resource_loader import get_resource_path
from ui.icons.icon_registry import IconBuilder, IconType
from ui.widgets import DataPlotStudioButton
from ui.theme import ThemeColors
from ui.widgets.ControlElements import DataPlotStudioLineEdit

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
        
        self.search_input = DataPlotStudioLineEdit()
        self.search_input.setPlaceholderText("Search column...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMaximumWidth(220)
        self.search_input.textChanged.connect(self.jump_to_column)
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
        self.header.setCursor(Qt.CursorShape.OpenHandCursor)
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
        
        self.cancel_btn = DataPlotStudioButton("Cancel", parent=self)
        self.cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(self.cancel_btn)
        
        self.apply_btn = DataPlotStudioButton("Apply Column Order", parent=self, base_color_hex=ThemeColors.MainColor, text_color_hex="white")
        self.apply_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.apply_btn)
        
        layout.addLayout(bottom_layout)
    
    def eventFilter(self, source, event: QEvent) -> bool:
        if hasattr(self, "header") and source is self.header.viewport():
            if event.type() == QEvent.Type.MouseButtonPress:
                self.header.setCursor(Qt.CursorShape.ClosedHandCursor)
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self.header.setCursor(Qt.CursorShape.OpenHandCursor)
        return super().eventFilter(source, event)
    
    def reset_order(self) -> None:
        """
        Resets the visua order of the headers back to the original dataframe
        """
        for logical_index in range(self.table_mimic.columnCount()):
            visual_index = self.header.visualIndex(logical_index)
            if visual_index != logical_index:
                self.header.moveSection(visual_index, logical_index)
        self.update_header_labels()
        
        reset_btn_original_text = "Reset Order"
        reset_btn_original_icon = self.reset_btn.icon()
        
        self.reset_btn.setText("Order Reset!")
        self.reset_btn.setIcon(IconBuilder.build(IconType.Checkmark))
        
        QTimer.singleShot(1500, lambda: self._revert_reset_button(reset_btn_original_text, reset_btn_original_icon))
    
    def _revert_reset_button(self, original_text: str, original_icon: QIcon) -> None:
        self.reset_btn.setText(original_text)
        self.reset_btn.setIcon(original_icon)
    
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
        if not text.strip():
            return
        
        search_query = text.lower()
        for visual_index in range(self.table_mimic.columnCount()):
            logical_index = self.header.logicalIndex(visual_index)
            col_name = self._original_columns[logical_index]
            
            if search_query in col_name.lower():
                x_pos = self.header.sectionPosition(visual_index)
                self.table_mimic.horizontalScrollBar().setValue(x_pos)
                
                header_item = self.table_mimic.horizontalHeaderItem(logical_index)
                cells = [self.table_mimic.item(row, logical_index) for row in range(self.table_mimic.rowCount())]
                
                original_font = header_item.font() if header_item else QFont()
                if header_item:
                    highlight_font = QFont(original_font)
                    highlight_font.setBold(True)
                    header_item.setFont(highlight_font)
                
                anim = QVariantAnimation(self)
                anim.setDuration(1500)
                try:
                    start_color = QColor(ThemeColors.MainColor)
                except Exception:
                    start_color = QColor("#3b82f6")
                start_color.setAlpha(120)
                
                end_color = QColor(255, 255, 255, 0)
                
                anim.setStartValue(start_color)
                anim.setEndValue(end_color)
                
                def update_beam(color, target_cells=cells):
                    for cell in target_cells:
                        if cell:
                            cell.setBackground(color)
                
                anim.valueChanged.connect(update_beam)
                anim.finished.connect(lambda hi=header_item, of=original_font, a=anim, cs=cells: self._finalize_highlight(hi, of, a, cs))
                self._animations.append(anim)
                anim.start()
                break
    
    def _finalize_highlight(self, header_item: QTableWidgetItem, original_font: QFont, anim: QVariantAnimation, cells: list) -> None:
        if header_item:
            header_item.setFont(original_font)
            
        from PyQt6.QtGui import QBrush
        for cell in cells:
            if cell:
                cell.setBackground(QBrush())
                
        if anim in self._animations:
            self._animations.remove(anim)
    
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