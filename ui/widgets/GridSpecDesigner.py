from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QMenu, QSpinBox, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt, QEvent, QPoint
from PyQt6.QtGui import QKeyEvent, QColor, QBrush, QFont

from typing import List, Tuple, Optional
from dataclasses import dataclass

from ui.theme import ThemeColors

@dataclass
class GridSpan:
    row_start: int
    row_end: int
    col_start: int
    col_end: int
    
    def overlaps_with(self, other: "GridSpan") -> bool:
        """Determines if this span intersects with another span using AABB collison logic"""
        return not (self.row_start >= other.row_end or 
                    self.row_end <= other.row_start or
                    self.col_start >= other.col_end or
                    self.col_end <= other.col_start)
    
    def as_tuple(self) -> Tuple[int, int, int, int]:
        return (self.row_start, self.row_end, self.col_start, self.col_end)

class GridSpecDesignerWidget(QWidget):
    """
    A visual widget to design GridSpec layouts.
    Uses a QTableWidget to act as an grid builder.
    """
    
    layout_applied = pyqtSignal(int, int, list)
    
    PLOT_PALETTE: List[QColor] = [
        QColor(58, 134, 255, 40),  
        QColor(46, 196, 182, 40),  
        QColor(155, 93, 229, 40),  
        QColor(243, 167, 18, 40), 
        QColor(231, 29, 54, 40),   
        QColor(0, 187, 249, 40)    
    ]
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("GridSpecDesignerWidget")
        self._defined_spans: List[GridSpan] = []
        self._sharex: bool = False
        self._sharey: bool = False
        
        self._init_ui()
        self._connect_signals()
        self._update_grid_data()
        
    def _init_ui(self) -> None:
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        self.controls_layout = QHBoxLayout()
        self.rows_spin = QSpinBox()
        self.rows_spin.setObjectName("gridRowsSpinBox")
        self.rows_spin.setRange(1, 10)
        self.rows_spin.setValue(2)
        
        self.cols_spin = QSpinBox()
        self.cols_spin.setObjectName("gridColsSpinBox")
        self.cols_spin.setRange(1, 10)
        self.cols_spin.setValue(2)
        
        row_label = QLabel("Grid Rows:")
        row_label.setProperty("styleClass", "settings_label")
        col_label = QLabel("Grid Columns:")
        col_label.setProperty("styleClass", "settings_label")

        self.controls_layout.addWidget(row_label)
        self.controls_layout.addWidget(self.rows_spin)
        self.controls_layout.addWidget(col_label)
        self.controls_layout.addWidget(self.cols_spin)
        self.controls_layout.addStretch()
        
        self.grid_table = QTableWidget()
        self.grid_table.setObjectName("layoutGridTable")
        self.grid_table.setSelectionMode(QTableWidget.SelectionMode.ContiguousSelection)
        self.grid_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.grid_table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.grid_table.setShowGrid(True)
        self.grid_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.grid_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.grid_table.horizontalHeader().setVisible(False)
        self.grid_table.verticalHeader().setVisible(False)
        self.grid_table.setMinimumHeight(150)
        
        self.grid_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        self.actions_layout = QHBoxLayout()
        self.merge_cells_btn = QPushButton("Add / Merge Plot")
        self.merge_cells_btn.setObjectName("mergeCellsBtn")
        self.merge_cells_btn.setToolTip("Create a new plot or merge existing ones in the selected area.")
        
        self.remove_cells_btn = QPushButton("Remove Plot")
        self.remove_cells_btn.setObjectName("removeCellsBtn")
        self.remove_cells_btn.setToolTip("Remove the plot from the selected area, leaving an empty space.")
        
        self.reset_grid_btn = QPushButton("Reset Grid")
        self.reset_grid_btn.setObjectName("resetGridBtn")
        
        self.apply_layout_btn = QPushButton("Apply Layout")
        self.apply_layout_btn.setObjectName("MainActionButton")
        self.apply_layout_btn.setProperty("actionType", "primary")

        self.actions_layout.addWidget(self.merge_cells_btn)
        self.actions_layout.addWidget(self.remove_cells_btn)
        self.actions_layout.addWidget(self.reset_grid_btn)
        self.actions_layout.addStretch()
        self.actions_layout.addWidget(self.apply_layout_btn)

        self.main_layout.addLayout(self.controls_layout)
        self.main_layout.addWidget(self.grid_table)
        self.main_layout.addLayout(self.actions_layout)
        
        self.setLayout(self.main_layout)
    
    def _connect_signals(self) -> None:
        self.rows_spin.valueChanged.connect(self._update_grid_data)
        self.cols_spin.valueChanged.connect(self._update_grid_data)
        self.merge_cells_btn.clicked.connect(self._merge_selected)
        self.remove_cells_btn.clicked.connect(self._remove_selected)
        self.reset_grid_btn.clicked.connect(self._confirm_reset_grid)
        self.apply_layout_btn.clicked.connect(self._emit_layout)
        
        self.grid_table.cellDoubleClicked.connect(self._handle_double_click)
        self.grid_table.customContextMenuRequested.connect(self._show_context_menu)
        
        self.grid_table.installEventFilter(self)
        
    def eventFilter(self, source: QWidget, event: QEvent) -> bool:
        if source is self.grid_table and event.type() == QEvent.Type.KeyPress:
            if isinstance(event, QKeyEvent):
                key = event.key()
                if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                    self._remove_selected()
                    return True
                elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self._merge_selected()
                    return True
        return super().eventFilter(source, event)
    
    def _handle_double_click(self, row: int, col: int) -> None:
        """
        Handles the double clicking on a cell to change 
        its state from empty to plot and vice-versa
        """
        target_point = GridSpan(row_start=row, row_end=row+1, col_start=col, col_end=col+1)
        span_to_remove: Optional[GridSpan] = None
        
        for span in self._defined_spans:
            if target_point.overlaps_with(span):
                span_to_remove = span
                break
        
        if span_to_remove:
            self._defined_spans.remove(span_to_remove)
        else:
            self._defined_spans.append(target_point)
        
        self._redraw_table()
        
    def _show_context_menu(self, position: QPoint) -> None:
        menu = QMenu(self)
        
        merge_action = menu.addAction("Add / Merge Selected")
        remove_action = menu.addAction("Remove Selected")
        menu.addSeparator()
        reset_action = menu.addAction("Reset Grid")
        
        target_span = self._get_selected_span()
        has_selection = target_span is not None
        
        if has_selection:
            overlaps_existing = any(span.overlaps_with(target_span) for span in self._defined_spans)
            remove_action.setEnabled(overlaps_existing)
        else:
            merge_action.setEnabled(False)
            remove_action.setEnabled(False)
        
        merge_action.triggered.connect(self._merge_selected)
        remove_action.triggered.connect(self._remove_selected)
        reset_action.triggered.connect(self._update_grid_data)
        
        menu.exec(self.grid_table.mapToGlobal(position))
    
    def _update_grid_data(self) -> None:
        """
        Rebuilds the table structure to reflect changes in rows/cols
        """
        rows = self.rows_spin.value()
        cols = self.cols_spin.value()
        
        self._defined_spans.clear()
        for r in range(rows):
            for c in range(cols):
                self._defined_spans.append(GridSpan(row_start=r, row_end=r + 1, col_start=c, col_end=c +1))
        self._redraw_table()
    
    def _confirm_reset_grid(self) -> None:
        """Prompts before destroying a customized layout"""
        rows = self.rows_spin.value()
        cols = self.cols_spin.value()
        total_default_cells = rows * cols
        
        if len(self._defined_spans) != total_default_cells:
            reply = QMessageBox.question(
                self,
                "Reset Grid Layout",
                "Are you sure you want to reset the grid? This will discard all changes",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        self._update_grid_data()
    
    def set_shared_axes(self, sharex: bool, sharey: bool) -> None:
        self._sharex = sharex
        self._sharey = sharey
        
        self.grid_table.setProperty("sharex", sharex)
        self.grid_table.setProperty("sharey", sharey)
        self.grid_table.style().unpolish(self.grid_table)
        self.grid_table.style().polish(self.grid_table)
        
        self._redraw_table()
    
    def _generate_plot_tooltip(self, index: int, row_span: int, col_span: int, has_x: bool, has_y: bool) -> str:
        """Generates a tooltip for a plot cell indicating its span and active axes"""
        span_description = f"{row_span}x{col_span} block" if (row_span > 1 or col_span > 1) else "1x1 blcok"
        
        axes_status: List[str] = []
        if has_x:
            axes_status.append("X")
        if has_y:
            axes_status.append("Y")
        
        axis_description = f"Active Axes: {' & '.join(axes_status)}" if axes_status else "Active Axes: None (Fully Shared)"
        return f"Plot {index + 1} ({span_description})\n{axis_description}\nDouble-click to remove this plot"

    def _redraw_table(self) -> None:
        """
        Repaints the table using span state and numerical order
        """
        rows = self.rows_spin.value()
        cols = self.cols_spin.value()
        
        self.grid_table.setRowCount(rows)
        self.grid_table.setColumnCount(cols)
        self.grid_table.clearSpans()
        self.grid_table.clearContents()
        
        for r in range(rows):
            for c in range(cols):
                empty_item = QTableWidgetItem()
                self.grid_table.setItem(r, c, empty_item)
                
                empty_widget = QLabel("Empty Space")
                empty_widget.setObjectName(f"emptyCellWidget_{r}_{c}")
                empty_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                empty_widget.setProperty("styleClass", "empty_plot_cell")
                
                self.grid_table.setCellWidget(r, c, empty_widget)

        self._defined_spans.sort(key=lambda span: (span.row_start, span.col_start))

        for idx, span in enumerate(self._defined_spans):
            has_x = not self._sharex or span.row_end == rows
            has_y = not self._sharey or span.col_start == 0
            
            item = QTableWidgetItem()
            bg_color = self.PLOT_PALETTE[idx % len(self.PLOT_PALETTE)]
            item.setBackground(QBrush(bg_color))
            
            row_span = span.row_end - span.row_start
            col_span = span.col_end - span.col_start
            
            item.setToolTip(self._generate_plot_tooltip(idx, row_span, col_span, has_x, has_y))
            self.grid_table.setItem(span.row_start, span.col_start, item)
            
            cell_widget = QLabel(f"Plot {idx + 1}")
            cell_widget.setObjectName(f"plotCellWidget_{idx}")
            cell_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            
            cell_widget.setProperty("styleClass", "plot_cell_label")
            cell_widget.setProperty("has_x_axis", has_x)
            cell_widget.setProperty("has_y_axis", has_y)
            
            cell_widget.style().unpolish(cell_widget)
            cell_widget.style().polish(cell_widget)
            
            self.grid_table.setCellWidget(span.row_start, span.col_start, cell_widget)
                        
            if row_span > 1 or col_span > 1:
                self.grid_table.setSpan(span.row_start, span.col_start, row_span, col_span)
    
    def _get_selected_span(self) -> Optional[GridSpan]:
        """Extracts the currently selected range as GridSpan"""
        selected_ranges = self.grid_table.selectedRanges()
        if not selected_ranges:
            return None
        
        selection = selected_ranges[0]
        return GridSpan(
            row_start=selection.topRow(),
            row_end=selection.bottomRow() +1,
            col_start=selection.leftColumn(),
            col_end=selection.rightColumn() +1
        )
    
    def _merge_selected(self) -> None:
        """Consumes the selected cells and combines them into a single subplot block"""
        target_span = self._get_selected_span()
        if not target_span:
            return
        
        # Filter out any spans that overlap with new merged area
        self._defined_spans = [span for span in self._defined_spans if not span.overlaps_with(target_span)]
        self._defined_spans.append(target_span)
        self._redraw_table()
        
    def _remove_selected(self) -> None:
        """Removes any spans that intersect with current selected spans"""
        target_span = self._get_selected_span()
        if not target_span:
            return
        
        # Keep only the spans that do not overlap with the selection
        self._defined_spans = [span for span in self._defined_spans if not span.overlaps_with(target_span)]
        self._redraw_table()
    
    def _emit_layout(self) -> None:
        if not self._defined_spans:
            QMessageBox.warning(
                self,
                "Invalid Layout",
                "Cannot apply an empty layout. Please ensure at least one plot is defined in the grid"
            )
            return
        
        rows = self.rows_spin.value()
        cols = self.cols_spin.value()
        
        tuple_spans = [span.as_tuple() for span in self._defined_spans]
        self.layout_applied.emit(rows, cols, tuple_spans)
        