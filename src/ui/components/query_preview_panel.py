from enum import StrEnum

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView, QLabel,
    QPushButton,
    QStyle,
    QTableView,
    QVBoxLayout,
    QWidget
)

from icons import IconBuilder, IconType
from src.core.database_query_preview import PREVIEW_ROW_LIMIT, QueryPreviewResult
from src.ui.models.query_preview_table_model import QueryPreviewTableModel

PREVIEW_TABLE_MIN_HEIGHT: int = 185
MIN_PREVIEW_COLUMN_WIDTH: int = 70
MAX_PREVIEW_COLUMN_WIDTH: int = 280

DEFAULT_IDLE_STATUS_TEXT: str = f"Run preview to inspect up to {PREVIEW_ROW_LIMIT} records"
LOADING_STATUS_TEXT: str = "Executing query..."
STALE_STATUS_TEXT: str = "Query has changed since last preview. Click 'Run Query' to refresh"

class PreviewStatusState(StrEnum):
    MUTED = "muted"
    VALID = "valid"
    STALE = "stale"
    INVALID = "invalid"

class QueryPreviewPanel(QGroupBox):
    """Read-only panel showing the table view of 5 records in a query"""
    previewRequested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(f"Query Preview", parent)
        self._has_populated_preview: bool = False
        self._is_state: bool = False

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.addLayout(self._create_toolbar_layout())
        layout.addWidget(self._create_table_view())

        self._apply_status(DEFAULT_IDLE_STATUS_TEXT, PreviewStatusState.MUTED)

    def _create_toolbar_layout(self) -> QHBoxLayout:
        toolbar_layout: QHBoxLayout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(8)

        self.preview_status_label: QLabel = QLabel(DEFAULT_IDLE_STATUS_TEXT, self)
        self.preview_status_label.setObjectName("query_preview_status_label")
        self.preview_status_label.setWordWrap(True)
        toolbar_layout.addWidget(self.preview_status_label, stretch=1)

        self.preview_button: QPushButton = QPushButton("Run Query", self)
        self.preview_button.setObjectName("previewQueryButton")
        self.preview_button.setIcon(IconBuilder.build(IconType.ViewItem))
        self.preview_button.setToolTip(
            f"Execute the query and show the first {PREVIEW_ROW_LIMIT} records.\n (Ctrl+Shift+Enter / F5)"
        )
        self.preview_button.setEnabled(False)
        self.preview_button.clicked.connect(self.previewRequested.emit)
        toolbar_layout.addWidget(self.preview_button)

        return toolbar_layout

    def _create_table_view(self) -> QTableView:
        self.table_model: QueryPreviewTableModel = QueryPreviewTableModel(self)
        self.preview_table: QTableView = QTableView(self)
        self.preview_table.setObjectName("queryPreviewTable")
        self.preview_table.setModel(self.table_model)
        self.preview_table.setMinimumHeight(PREVIEW_TABLE_MIN_HEIGHT)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.preview_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        horizontal_header: QHeaderView | None = self.preview_table.horizontalHeader()
        if horizontal_header is not None:
            horizontal_header.setObjectName("MainDataHeader")
            horizontal_header.setMinimumSectionSize(MIN_PREVIEW_COLUMN_WIDTH)
            horizontal_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            horizontal_header.setStretchLastSection(False)

        vertical_header: QHeaderView | None = self.preview_table.verticalHeader()
        if vertical_header is not None:
            vertical_header.setObjectName("MainDataHeader")
            vertical_header.setDefaultSectionSize(28)

        return self.preview_table

    def _apply_status(self, message: str, state: PreviewStatusState) -> None:
        self.preview_status_label.setText(message)
        self.preview_status_label.setProperty("status", state.value)
        label_style: QStyle | None = self.preview_status_label.style()
        if label_style is not None:
            label_style.unpolish(self.preview_status_label)
            label_style.polish(self.preview_status_label)

    def _resize_columns_bounded(self) -> None:
        self.preview_table.resizeColumnsToContents()
        horizontal_header: QHeaderView | None = self.preview_table.horizontalHeader()
        if horizontal_header is None:
            return
        for col_idx in range(self.table_model.columnCount()):
            width: int = self.preview_table.columnWidth(col_idx)
            if width > MAX_PREVIEW_COLUMN_WIDTH:
                self.preview_table.setColumnWidth(col_idx, MAX_PREVIEW_COLUMN_WIDTH)

    @staticmethod
    def _build_result_summary(result: QueryPreviewResult) -> str:
        row_count: int = len(result.rows)
        record_word: str = "record" if row_count == 1 else "records"
        column_count: int = len(result.columns)
        column_word: str = "column" if column_count == 1 else "columns"
        source_suffix: str = f" from {result.source_label}" if result.source_label else ""

        if row_count == 0:
            return f"Query returned 0 records ({column_count} {column_word}){source_suffix}"
        if result.has_more_rows:
            return f"Showing first {row_count} records ({column_count} {column_word}){source_suffix}"
        return f"Showing all {row_count} {record_word} ({column_count} {column_word}){source_suffix}"

    def set_can_execute(self, can_execute: bool) -> None:
        """Enable or disable the run query button"""
        self.preview_button.setEnabled(can_execute)

    def set_loading_state(self) -> None:
        """Change preview label into loading state"""
        self.preview_button.setEnabled(False)
        self.preview_button.setText("Running...")
        self._apply_status(LOADING_STATUS_TEXT, PreviewStatusState.MUTED)

    def display_preview_result(self, result: QueryPreviewResult) -> None:
        """Populate the table with the preview records and upate the summary"""
        self.preview_button.setText("Run Query")
        self.table_model.set_preview_result(result)
        self._resize_columns_bounded()
        self._has_populated_preview = True
        self._is_state = False
        summary: str = self._build_result_summary(result)
        status_state: PreviewStatusState = (
            PreviewStatusState.VALID if len(result.rows) > 0 else PreviewStatusState.MUTED
        )
        self._apply_status(summary, status_state)

    def set_error_state(self, message: str) -> None:
        """Display an error status when preview query fails"""
        self.preview_button.setText("Run Query")
        self._is_state = False
        self._apply_status(message, PreviewStatusState.INVALID)

    def mark_state_if_populated(self) -> None:
        """Mark the displayed preview as outdated when SQL query changes"""
        if not self._has_populated_preview or self._is_state:
            return
        self._is_state = True
        self._apply_status(STALE_STATUS_TEXT, PreviewStatusState.STALE)

    def clear_preview(self) -> None:
        """Clear all preview records and restore to default"""
        self.preview_button.setText("Run Query")
        self.table_model.clear()
        self._has_populated_preview = False
        self._is_state = False
        self._apply_status(DEFAULT_IDLE_STATUS_TEXT, PreviewStatusState.MUTED)
