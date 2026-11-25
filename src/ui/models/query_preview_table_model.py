from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QObject, Qt
from PyQt6.QtGui import QColor, QFont

from src.core.database_query_preview import QueryPreviewResult

NULL_FOREGROUND_HEX: str = "#8c929d"

class QueryPreviewTableModel(QAbstractTableModel):
    """
    Read only Qt table model for displaying a SQL query preview
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._columns: tuple[str, ...] = ()
        self._rows: tuple[tuple[str, ...], ...] = ()
        self._tooltips: tuple[tuple[str, ...], ...] = ()
        self._null_mask: tuple[tuple[bool, ...], ...] = ()
        self._numeric_columns: tuple[bool, ...] = ()

        self._null_color: QColor = QColor(NULL_FOREGROUND_HEX)
        self._null_font: QFont = QFont()
        self._null_font.setItalic(True)

    def set_preview_result(self, result: QueryPreviewResult) -> None:
        """Replaces the model contents with the preview result"""
        self.beginResetModel()
        self._columns = result.columns
        self._rows = result.rows
        self._tooltips = result.tooltips
        self._null_mask = result.null_mask
        self._numeric_columns = result.numeric_columns
        self.endResetModel()

    def clear(self) -> None:
        """Clear all rows and column headers from the preview model"""
        if not self._columns and not self._rows:
            return
        self.beginResetModel()
        self._columns = ()
        self._rows = ()
        self._tooltips = ()
        self._null_mask = ()
        self._numeric_columns = ()
        self.endResetModel()

    def has_data(self) -> bool:
        """Check whether a preview result is currently loaded"""
        return len(self._columns) > 0

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of preview records currently stored"""
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Retrun the number of preview columns currently stored"""
        if parent.isValid():
            return 0
        return len(self._columns)

    def _is_null_cell(self, row: int, column: int) -> bool:
        if row < 0 or row >= len(self._null_mask):
            return False

        row_mask: tuple[bool, ...] = self._null_mask[row]
        if column < 0 or column >= len(row_mask):
            return False
        return row_mask[column]

    def _alignment_for_column(self, column: int) -> Qt.AlignmentFlag:
        if 0 <= column < len(self._numeric_columns) and self._numeric_columns[column]:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

    def data(
            self,
            index: QModelIndex,
            role: int = int(Qt.ItemDataRole.DisplayRole)
    ) -> str | Qt.AlignmentFlag | QFont | QColor | None:
        """Retrieve display, tooltip, alignment, font or foreground data for a cell"""
        if not index.isValid():
            return None

        row: int = index.row()
        column: int = index.column()
        if row < 0 or row >= len(self._rows) or column < 0 or column >= len(self._columns):
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            return self._rows[row][column]
        if role == Qt.ItemDataRole.ToolTipRole:
            return self._tooltips[row][column]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return self._alignment_for_column(column)
        if role == Qt.ItemDataRole.FontRole and self._is_null_cell(row, column):
            return self._null_font
        if role == Qt.ItemDataRole.ForegroundRole and self._is_null_cell(row, column):
            return self._null_color

        return None

    def headerData(
            self,
            section: int,
            orientation: Qt.Orientation,
            role: int = int(Qt.ItemDataRole.DisplayRole)
    ) -> str | None:
        """Provide column names for the horizontal header and 1-.based row numbers vertically"""
        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            return None

        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._columns):
                return self._columns[section]
            return None

        if 0 <= section < len(self._rows):
            return str(section + 1)
        return None
